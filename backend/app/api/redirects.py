"""Site-scoped redirect proposal review and safe configuration exports."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Page, RedirectRule, User, utcnow
from ..security.auth import current_user, get_site_for
from ..services.redirects import export_rules, normalise_url, propose_from_crawl, simulate
from .deps import latest_crawl

router = APIRouter(tags=["redirects"])


class RedirectIn(BaseModel):
    source_url: str = Field(max_length=2048)
    target_url: str = Field(max_length=2048)
    status_code: Literal[301, 308] = 301
    note: str = Field("", max_length=2000)


class RedirectPatch(BaseModel):
    target_url: str | None = Field(None, max_length=2048)
    status_code: Literal[301, 308] | None = None
    note: str | None = Field(None, max_length=2000)


def _out(r: RedirectRule) -> dict:
    return {"id": r.id, "source_url": r.source_url, "target_url": r.target_url,
            "status_code": r.status_code, "origin": r.origin, "state": r.state,
            "confidence": r.confidence, "note": r.note,
            "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}


def _rule(db: Session, site_id: int, rule_id: int) -> RedirectRule:
    r = db.scalar(select(RedirectRule).where(RedirectRule.site_id == site_id, RedirectRule.id == rule_id))
    if r is None:
        raise HTTPException(404, "Weiterleitungsregel nicht gefunden")
    return r


def _all(db: Session, site_id: int) -> list[RedirectRule]:
    return list(db.scalars(select(RedirectRule).where(RedirectRule.site_id == site_id).order_by(RedirectRule.id.desc())))


@router.get("/sites/{site_id}/redirects")
def list_redirects(site_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> list[dict]:
    site = get_site_for(db, user, site_id)
    return [_out(r) for r in _all(db, site.id)]


@router.post("/sites/{site_id}/redirects", status_code=201)
def create_redirect(site_id: int, body: RedirectIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    src, dst = normalise_url(site, body.source_url), normalise_url(site, body.target_url)
    if src == dst:
        raise HTTPException(422, "Quelle und Ziel müssen verschieden sein")
    if db.scalar(select(RedirectRule.id).where(RedirectRule.site_id == site.id, RedirectRule.source_url == src)):
        raise HTTPException(409, "Für diese Quelle existiert bereits ein Entwurf")
    row = RedirectRule(site_id=site.id, source_url=src, target_url=dst, status_code=body.status_code,
                       origin="manual", state="proposed", note=body.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/sites/{site_id}/redirects/{rule_id}")
def update_redirect(site_id: int, rule_id: int, body: RedirectPatch,
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    row = _rule(db, site.id, rule_id)
    if row.state != "proposed":
        raise HTTPException(409, "Nur Entwürfe sind bearbeitbar")
    if body.target_url is not None:
        row.target_url = normalise_url(site, body.target_url)
        if row.target_url == row.source_url:
            raise HTTPException(422, "Quelle und Ziel müssen verschieden sein")
    if body.status_code is not None:
        row.status_code = body.status_code
    if body.note is not None:
        row.note = body.note
    row.updated_at = utcnow()
    db.commit()
    return _out(row)


@router.post("/sites/{site_id}/redirects/{rule_id}/{decision}")
def decide_redirect(site_id: int, rule_id: int, decision: Literal["approve", "reject", "reopen"],
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    row = _rule(db, site.id, rule_id)
    if decision == "reopen":
        if row.state not in ("approved", "rejected"):
            raise HTTPException(409, "Regel ist bereits ein Entwurf")
        row.state = "proposed"
    elif row.state != "proposed":
        raise HTTPException(409, "Nur Entwürfe können entschieden werden")
    elif decision == "reject":
        row.state = "rejected"
    else:
        active = [r for r in _all(db, site.id) if r.state == "approved" and r.id != row.id]
        simulation = simulate([_out(row), *[_out(r) for r in active]])
        blocking = [x for x in simulation if x["issue"] in ("self_redirect", "duplicate_source", "redirect_loop", "redirect_chain")]
        if blocking:
            raise HTTPException(409, {"message": "Weiterleitungskonflikt", "findings": blocking})
        row.state = "approved"
    row.updated_at = utcnow()
    db.commit()
    return _out(row)


@router.post("/sites/{site_id}/redirects/suggest")
def suggest_redirects(site_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if crawl is None:
        raise HTTPException(409, "Zuerst einen Crawl abschließen")
    proposals = propose_from_crawl(db, crawl, site)
    existing = {r.source_url for r in _all(db, site.id)}
    created = []
    for data in proposals:
        if data["source_url"] in existing:
            continue
        row = RedirectRule(site_id=site.id, state="proposed", **data)
        db.add(row)
        existing.add(data["source_url"])
        created.append(row)
    db.commit()
    return {"created": len(created), "crawl_id": crawl.id, "items": [_out(r) for r in created]}


@router.post("/sites/{site_id}/redirects/simulate")
def simulate_redirects(site_id: int, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    rows = [_out(r) for r in _all(db, site.id) if r.state != "rejected"]
    crawl = latest_crawl(db, site.id)
    status = {}
    if crawl:
        status = {p.url: (p.status_code, p.indexable) for p in db.scalars(select(Page).where(Page.crawl_id == crawl.id))}
    return {"rules": len(rows), "crawl_id": crawl.id if crawl else None,
            "findings": simulate(rows, status),
            "note": "Nur Snapshot-Prüfung; kein Abruf und keine Serveränderung."}


@router.get("/sites/{site_id}/redirects/export")
def export_redirects(site_id: int, format: Literal["apache", "nginx", "csv"] = "csv",
                     user: User = Depends(current_user), db: Session = Depends(get_db)) -> PlainTextResponse:
    site = get_site_for(db, user, site_id)
    rules = [_out(r) for r in _all(db, site.id) if r.state == "approved"]
    for row in rules:
        normalise_url(site, row["source_url"])
        normalise_url(site, row["target_url"])
    findings = simulate(rules)
    if any(f["issue"] in ("redirect_loop", "redirect_chain", "duplicate_source", "self_redirect") for f in findings):
        raise HTTPException(409, "Freigegebene Regeln enthalten Konflikte")
    ext = "csv" if format == "csv" else "conf" if format == "nginx" else "htaccess"
    return PlainTextResponse(export_rules(rules, format),
                             media_type="text/csv" if format == "csv" else "text/plain",
                             headers={"Content-Disposition": f'attachment; filename="redirects.{ext}"'})
