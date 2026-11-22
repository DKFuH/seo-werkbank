"""Manual SEO workflow tracking, with measured GSC snapshots for content items."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GscRow, SeoPerformanceSnapshot, SeoWorkItem, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["seo-workflow"])

Kind = Literal["content", "review", "publication", "local", "competitor"]
Status = Literal["planned", "draft", "approved", "published", "measured", "requested", "received",
                 "pitched", "accepted", "verified", "lost", "in_progress", "completed",
                 "observed", "investigating", "actioned", "dismissed"]
STATES = {
    "content": ("planned", "draft", "approved", "published", "measured"),
    "review": ("planned", "requested", "received"),
    "publication": ("planned", "pitched", "accepted", "published", "verified", "lost"),
    "local": ("planned", "in_progress", "completed"),
    "competitor": ("observed", "investigating", "actioned", "dismissed"),
}


class ItemIn(BaseModel):
    kind: Kind
    title: str = Field(min_length=1, max_length=300)
    status: Status = "planned"
    target_url: str | None = Field(None, max_length=2048)
    source_url: str | None = Field(None, max_length=2048)
    evidence_url: str | None = Field(None, max_length=2048)
    notes: str = Field("", max_length=12000)

    @model_validator(mode="after")
    def valid_state(self):
        if self.status not in STATES[self.kind]:
            raise ValueError("Status für diesen Vorgangstyp ungültig")
        if self.kind == "content" and not self.target_url:
            raise ValueError("Content-Aufgaben benötigen eine Ziel-URL")
        return self


class ItemPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    status: Status | None = None
    target_url: str | None = Field(None, max_length=2048)
    source_url: str | None = Field(None, max_length=2048)
    evidence_url: str | None = Field(None, max_length=2048)
    notes: str | None = Field(None, max_length=12000)


class SnapshotIn(BaseModel):
    label: Literal["baseline", "followup"]
    days: int = Field(28, ge=7, le=180)


def _item_for(db: Session, site_id: int, item_id: int) -> SeoWorkItem:
    item = db.scalar(select(SeoWorkItem).where(SeoWorkItem.id == item_id, SeoWorkItem.site_id == site_id))
    if item is None:
        raise HTTPException(404, "Vorgang nicht gefunden")
    return item


def _item_out(item: SeoWorkItem) -> dict:
    return {"id": item.id, "site_id": item.site_id, "kind": item.kind, "title": item.title,
            "status": item.status, "target_url": item.target_url, "source_url": item.source_url,
            "evidence_url": item.evidence_url, "notes": item.notes,
            "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}


@router.get("/sites/{site_id}/seo-work")
def list_items(site_id: int, kind: Kind | None = None, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    stmt = select(SeoWorkItem).where(SeoWorkItem.site_id == site.id)
    if kind:
        stmt = stmt.where(SeoWorkItem.kind == kind)
    rows = db.scalars(stmt.order_by(SeoWorkItem.updated_at.desc(), SeoWorkItem.id.desc()).limit(1000)).all()
    return {"items": [_item_out(p) for p in rows], "states": STATES,
            "note": "Einträge und Zustände sind manuell gepflegt; keine Veröffentlichung oder Review-Anfrage erfolgt automatisch."}


@router.post("/sites/{site_id}/seo-work", status_code=201)
def create_item(site_id: int, body: ItemIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    item = SeoWorkItem(site_id=site.id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_out(item)


@router.patch("/sites/{site_id}/seo-work/{item_id}")
def update_item(site_id: int, item_id: int, body: ItemPatch,
                user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    item = _item_for(db, site.id, item_id)
    updated = {**_item_out(item), **body.model_dump(exclude_unset=True)}
    # Reuse validation to enforce the per-kind allowed states and required content URL.
    if updated["status"] not in STATES[item.kind]:
        raise HTTPException(422, "Status für diesen Vorgangstyp ungültig")
    if item.kind == "content" and not updated["target_url"]:
        raise HTTPException(422, "Content-Aufgaben benötigen eine Ziel-URL")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    from ..models import utcnow
    item.updated_at = utcnow()
    db.commit()
    db.refresh(item)
    return _item_out(item)


@router.delete("/sites/{site_id}/seo-work/{item_id}", status_code=204)
def delete_item(site_id: int, item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    item = _item_for(db, site.id, item_id)
    db.delete(item)
    db.commit()


def _snapshot_out(s: SeoPerformanceSnapshot) -> dict:
    return {"id": s.id, "work_item_id": s.work_item_id, "label": s.label, "source": s.source,
            "start_date": s.start_date.isoformat(), "end_date": s.end_date.isoformat(),
            "clicks": round(s.clicks, 2), "impressions": round(s.impressions, 2),
            "position": round(s.position, 2) if s.position is not None else None,
            "captured_at": s.captured_at.isoformat()}


@router.get("/sites/{site_id}/seo-work/{item_id}/snapshots")
def list_snapshots(site_id: int, item_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> list[dict]:
    site = get_site_for(db, user, site_id)
    item = _item_for(db, site.id, item_id)
    return [_snapshot_out(s) for s in db.scalars(select(SeoPerformanceSnapshot).where(
        SeoPerformanceSnapshot.work_item_id == item.id).order_by(SeoPerformanceSnapshot.captured_at, SeoPerformanceSnapshot.id))]


@router.post("/sites/{site_id}/seo-work/{item_id}/snapshots", status_code=201)
def create_snapshot(site_id: int, item_id: int, body: SnapshotIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    item = _item_for(db, site.id, item_id)
    if item.kind != "content":
        raise HTTPException(422, "GSC-Snapshots sind nur für Content-Vorgänge verfügbar")
    if body.label == "baseline" and db.scalar(select(SeoPerformanceSnapshot.id).where(
            SeoPerformanceSnapshot.work_item_id == item.id, SeoPerformanceSnapshot.label == "baseline")):
        raise HTTPException(409, "Eine Baseline existiert bereits")
    # Search Console exports that do not pair query+page must never be projected onto a page.
    criteria = [GscRow.site_id == site.id, GscRow.dataset == "query_page", GscRow.query.is_not(None),
                GscRow.page == item.target_url, GscRow.day.is_not(None)]
    sources = {r[0] for r in db.execute(select(GscRow.source).where(*criteria).distinct())}
    if not sources:
        raise HTTPException(422, "Keine datierten GSC-Query-URL-Paare für diese URL")
    source = "api" if "api" in sources else "csv"
    source_criteria = [*criteria, GscRow.source == source]
    end = db.scalar(select(func.max(GscRow.day)).where(*source_criteria))
    start = end - timedelta(days=body.days - 1)
    range_criteria = [*source_criteria, GscRow.day.between(start, end)]
    weighted = func.sum(case((GscRow.position.is_not(None), GscRow.position * GscRow.impressions), else_=0))
    weight = func.sum(case((GscRow.position.is_not(None), GscRow.impressions), else_=0))
    clicks, impressions, numerator, denominator = db.execute(select(
        func.sum(GscRow.clicks), func.sum(GscRow.impressions), weighted, weight).where(*range_criteria)).one()
    if not impressions:
        raise HTTPException(422, "Keine Impressionen im gewählten Zeitraum")
    snap = SeoPerformanceSnapshot(work_item_id=item.id, label=body.label, source=source, start_date=start, end_date=end,
                                  clicks=float(clicks or 0), impressions=float(impressions),
                                  position=float(numerator / denominator) if denominator else None)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return _snapshot_out(snap)
