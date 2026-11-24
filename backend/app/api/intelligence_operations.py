"""Frozen report exports and traceable lost-link recovery tasks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Backlink, ReportSnapshot, SeoResearchRecord, SeoWorkItem, User
from ..security.auth import current_user, get_site_for
from ..services.report_snapshots import capture, render_html, render_pdf

router = APIRouter(tags=["intelligence-reports-links"])


class CaptureIn(BaseModel):
    title: str = Field("SEO-Monatsbericht", min_length=2, max_length=200)


def _snapshot(db: Session, site_id: int, snapshot_id: int) -> ReportSnapshot:
    obj = db.scalar(select(ReportSnapshot).where(ReportSnapshot.site_id == site_id,
                                                 ReportSnapshot.id == snapshot_id))
    if obj is None:
        raise HTTPException(404, "Berichtssnapshot nicht gefunden")
    return obj


def _snap_out(s: ReportSnapshot) -> dict:
    return {"id": s.id, "title": s.title, "origin": s.origin,
            "created_at": s.created_at.isoformat(),
            "crawl_id": (s.payload.get("crawl") or {}).get("id")}


@router.post("/sites/{site_id}/reports/snapshots", status_code=201)
def create_snapshot(site_id: int, body: CaptureIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    try:
        snap = capture(db, site, body.title)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    db.refresh(snap)
    return _snap_out(snap)


@router.get("/sites/{site_id}/reports/snapshots")
def list_snapshots(site_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    records = list(db.scalars(select(ReportSnapshot).where(
        ReportSnapshot.site_id == site.id).order_by(ReportSnapshot.id.desc()).limit(200)))
    return {"items": [_snap_out(s) for s in records],
            "method": "Berichte enthalten unveränderliche Datenstände, keine aktuellen Live-Kennzahlen."}


@router.get("/sites/{site_id}/reports/snapshots/{snapshot_id}.html")
def download_html(site_id: int, snapshot_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> Response:
    site = get_site_for(db, user, site_id)
    report = _snapshot(db, site.id, snapshot_id)
    return Response(content=render_html(report), media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="seo-snapshot-{report.id}.html"',
                             "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"})


@router.get("/sites/{site_id}/reports/snapshots/{snapshot_id}.pdf")
def download_pdf(site_id: int, snapshot_id: int, user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> Response:
    site = get_site_for(db, user, site_id)
    report = _snapshot(db, site.id, snapshot_id)
    return Response(content=render_pdf(report), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="seo-snapshot-{report.id}.pdf"'})


@router.get("/sites/{site_id}/link-recovery")
def recovery_candidates(site_id: int, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    lost = list(db.scalars(select(Backlink).where(
        Backlink.site_id == site.id, Backlink.status == "lost"
    ).order_by(Backlink.last_checked.desc()).limit(500)))
    events = list(db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "link_transition",
        SeoResearchRecord.source == "verification"
    ).order_by(SeoResearchRecord.id.desc()).limit(2000)))
    proven_lost = {e.payload.get("backlink_id") for e in events
                   if e.payload.get("previous_status") == "live"
                   and e.payload.get("current_status") == "lost"}
    rows = [{"id": b.id, "source_url": b.source_url, "source_domain": b.source_domain,
             "target_url": b.target_url, "last_checked": b.last_checked.isoformat() if b.last_checked else None,
             "confirmed_live_before": b.id in proven_lost,
             "evidence": "Verifizierter Wechsel live → lost" if b.id in proven_lost
             else "Link derzeit nicht gefunden, früheres live nicht nachgewiesen"} for b in lost]
    rows.sort(key=lambda x: (not x["confirmed_live_before"], x["source_domain"], x["source_url"]))
    return {"items": rows[:100], "total_lost": len(rows),
            "note": "Nur zuvor importierte und geprüfte Links, kein Web-Index. "
                    "Verlorene Links können sich durch temporäre Serverfehler oder geänderte HTML-Darstellung ergeben."}


@router.post("/sites/{site_id}/link-recovery/{backlink_id}/work", status_code=201)
def create_recovery_work(site_id: int, backlink_id: int, user: User = Depends(current_user),
                         db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    link = db.scalar(select(Backlink).where(Backlink.site_id == site.id,
                                            Backlink.id == backlink_id))
    if link is None:
        raise HTTPException(404, "Backlink nicht gefunden")
    if link.status != "lost":
        raise HTTPException(409, "Dieser Backlink ist aktuell nicht als verloren eingestuft")
    item = SeoWorkItem(site_id=site.id, kind="publication", status="planned",
                       title=("Link-Recovery: " + link.source_domain)[:300],
                       source_url=link.source_url, target_url=link.target_url,
                       notes="Bitte Quellseite und passende Ziel-URL redaktionell prüfen. "
                             "Kein automatischer Kontakt, kein Disavow und kein automatischer Redirect.")
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"work_item_id": item.id, "status": "planned", "automatic_contact": False}
