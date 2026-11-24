"""API endpoints for SEO Experiment Tracking and GSC-based Before/After evaluations."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SeoResearchRecord, User, utcnow
from ..security.auth import current_user, get_site_for
from ..services.seo_experiments import evaluate_experiment

router = APIRouter(tags=["seo-experiments"])

Category = Literal["title_meta", "content", "internal_links", "schema", "technical", "other"]


class ExperimentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: Category = "content"
    hypothesis: str = Field("", max_length=2000)
    applied_date: date
    target_url: str | None = Field(None, max_length=2048)
    notes: str = Field("", max_length=12000)


class ExperimentPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    category: Category | None = None
    hypothesis: str | None = Field(None, max_length=2000)
    applied_date: date | None = None
    target_url: str | None = Field(None, max_length=2048)
    notes: str | None = Field(None, max_length=12000)
    conclusions: str | None = Field(None, max_length=5000)


def _experiment_for(db: Session, site_id: int, experiment_id: int) -> SeoResearchRecord:
    item = db.scalar(
        select(SeoResearchRecord).where(
            SeoResearchRecord.id == experiment_id,
            SeoResearchRecord.site_id == site_id,
            SeoResearchRecord.kind == "seo_experiment",
        )
    )
    if item is None:
        raise HTTPException(404, "SEO-Experiment nicht gefunden")
    return item


def _record_to_dict(r: SeoResearchRecord) -> dict:
    p = r.payload or {}
    return {
        "id": r.id,
        "site_id": r.site_id,
        "title": r.title,
        "category": p.get("category", "other"),
        "hypothesis": p.get("hypothesis", ""),
        "applied_date": p.get("applied_date", r.observed_at.date().isoformat() if r.observed_at else None),
        "target_url": p.get("target_url"),
        "notes": r.notes,
        "conclusions": p.get("conclusions", ""),
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


@router.get("/sites/{site_id}/experiments")
def list_experiments(
    site_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    records = db.scalars(
        select(SeoResearchRecord)
        .where(SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "seo_experiment")
        .order_by(SeoResearchRecord.id.desc())
        .limit(200)
    ).all()

    items = [_record_to_dict(r) for r in records]
    items.sort(key=lambda x: str(x.get("applied_date") or ""), reverse=True)

    return {
        "items": items,
        "count": len(items),
        "method": "Dokumentierte SEO-Maßnahmen mit Datum zur empirischen Vorher-Nachher-Prüfung.",
    }


@router.post("/sites/{site_id}/experiments", status_code=201)
def create_experiment(
    site_id: int,
    body: ExperimentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    payload = {
        "category": body.category,
        "hypothesis": body.hypothesis,
        "applied_date": body.applied_date.isoformat(),
        "target_url": body.target_url,
        "conclusions": "",
    }
    observed = datetime.combine(body.applied_date, datetime.min.time())
    record = SeoResearchRecord(
        site_id=site.id,
        kind="seo_experiment",
        title=body.title,
        source="manual",
        payload=payload,
        notes=body.notes,
        observed_at=observed,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_to_dict(record)


@router.patch("/sites/{site_id}/experiments/{experiment_id}")
def update_experiment(
    site_id: int,
    experiment_id: int,
    body: ExperimentPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    record = _experiment_for(db, site.id, experiment_id)
    payload = dict(record.payload or {})

    if body.title is not None:
        record.title = body.title
    if body.notes is not None:
        record.notes = body.notes
    if body.category is not None:
        payload["category"] = body.category
    if body.hypothesis is not None:
        payload["hypothesis"] = body.hypothesis
    if body.applied_date is not None:
        payload["applied_date"] = body.applied_date.isoformat()
        record.observed_at = datetime.combine(body.applied_date, datetime.min.time())
    if body.target_url is not None:
        payload["target_url"] = body.target_url
    if body.conclusions is not None:
        payload["conclusions"] = body.conclusions

    record.payload = payload
    record.updated_at = utcnow()
    db.commit()
    db.refresh(record)
    return _record_to_dict(record)


@router.delete("/sites/{site_id}/experiments/{experiment_id}", status_code=204)
def delete_experiment(
    site_id: int,
    experiment_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    site = get_site_for(db, user, site_id)
    record = _experiment_for(db, site.id, experiment_id)
    db.delete(record)
    db.commit()


@router.get("/sites/{site_id}/experiments/{experiment_id}/metrics")
def experiment_metrics(
    site_id: int,
    experiment_id: int,
    days: int = Query(28, ge=7, le=90),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    record = _experiment_for(db, site.id, experiment_id)
    return evaluate_experiment(db, site.id, record, window_days=days)


@router.get("/sites/{site_id}/experiments/timeline-annotations")
def timeline_annotations(
    site_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Lightweight endpoint returning experiment dates and titles for timeline overlays."""
    site = get_site_for(db, user, site_id)
    records = db.scalars(
        select(SeoResearchRecord)
        .where(SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "seo_experiment")
        .order_by(SeoResearchRecord.id.desc())
        .limit(100)
    ).all()

    out = []
    for r in records:
        p = r.payload or {}
        d_str = p.get("applied_date")
        if d_str:
            out.append({
                "id": r.id,
                "title": r.title,
                "date": str(d_str)[:10],
                "category": p.get("category", "other"),
                "target_url": p.get("target_url"),
            })
    out.sort(key=lambda x: x["date"])
    return out
