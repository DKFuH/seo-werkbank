"""Store redaction-ready content revisions with explicit human approval.

All input is supplied by a user. No AI-generated copy, remote CMS write, or publication.
"""
from __future__ import annotations

import difflib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.schema_validator import validate_jsonld
from ..db import get_db
from ..models import SeoContentProposal, SeoWorkItem, User, utcnow
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["content-proposals"])


class ProposalIn(BaseModel):
    original_text: str = Field("", max_length=100000)
    proposed_text: str = Field(min_length=1, max_length=100000)
    rationale: str = Field("", max_length=10000)


def _content_work(db: Session, site_id: int, item_id: int) -> SeoWorkItem:
    item = db.scalar(select(SeoWorkItem).where(SeoWorkItem.id == item_id,
                                               SeoWorkItem.site_id == site_id, SeoWorkItem.kind == "content"))
    if item is None:
        raise HTTPException(404, "Content-Vorgang nicht gefunden")
    return item


def _proposal(db: Session, item_id: int) -> SeoContentProposal | None:
    return db.scalar(select(SeoContentProposal).where(SeoContentProposal.work_item_id == item_id))


def _out(p: SeoContentProposal) -> dict:
    diff = list(difflib.unified_diff(p.original_text.splitlines(), p.proposed_text.splitlines(),
                                     fromfile="Vom Nutzer eingegebener Ausgangstext", tofile="Entwurf", lineterm=""))
    return {"exists": True, "id": p.id, "work_item_id": p.work_item_id, "original_text": p.original_text,
            "proposed_text": p.proposed_text, "rationale": p.rationale,
            "content_type": p.content_type, "status": p.status,
            "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            "marked_published_at": p.marked_published_at.isoformat() if p.marked_published_at else None,
            "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat(),
            "diff": diff[:350], "diff_truncated": len(diff) > 350,
            "source": "manually_entered", "remote_publication": False}


@router.get("/sites/{site_id}/seo-work/{item_id}/content-proposal")
def get_proposal(site_id: int, item_id: int, user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    _content_work(db, site.id, item_id)
    proposal = _proposal(db, item_id)
    return _out(proposal) if proposal else {"exists": False, "work_item_id": item_id}


@router.put("/sites/{site_id}/seo-work/{item_id}/content-proposal")
def save_proposal(site_id: int, item_id: int, body: ProposalIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    work = _content_work(db, site.id, item_id)
    current = _proposal(db, item_id)
    if current and current.status != "draft":
        raise HTTPException(409, "Freigegebene Entwürfe sind unveränderlich. Zum Bearbeiten zuerst wieder öffnen.")
    if work.status == "published":
        raise HTTPException(409, "Bereits veröffentlichte Vorgänge nicht überschreiben; neuen Vorgang anlegen.")
    if current is not None and current.content_type == "application/ld+json":
        try:
            doc = json.loads(body.proposed_text)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "Ungültiges JSON-LD") from exc
        if not isinstance(doc, dict) or doc.get("@context") != "https://schema.org" or not doc.get("@type"):
            raise HTTPException(422, "Schema-Entwurf braucht @context und @type")
    if current is None:
        current = SeoContentProposal(work_item_id=item_id, **body.model_dump(), status="draft")
        db.add(current)
    else:
        for key, value in body.model_dump().items():
            setattr(current, key, value)
        current.updated_at = utcnow()
    work.status = "draft"
    work.updated_at = utcnow()
    db.commit()
    db.refresh(current)
    return _out(current)


@router.post("/sites/{site_id}/seo-work/{item_id}/content-proposal/approve")
def approve_proposal(site_id: int, item_id: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    work = _content_work(db, site.id, item_id)
    p = _proposal(db, item_id)
    if p is None or p.status != "draft":
        raise HTTPException(409, "Nur ein gespeicherter Entwurf kann separat freigegeben werden.")
    if p.content_type == "application/ld+json":
        try:
            doc = json.loads(p.proposed_text)
        except json.JSONDecodeError as exc:
            raise HTTPException(409, "JSON-LD ist ungültig") from exc
        if not isinstance(doc, dict) or validate_jsonld([doc])["errors"]:
            raise HTTPException(409, "Schema-Prüfung enthält Fehler; erst Entwurf korrigieren")
    p.status = "approved"
    p.approved_at = utcnow()
    p.updated_at = utcnow()
    work.status = "approved"
    work.updated_at = utcnow()
    db.commit()
    return _out(p)


@router.post("/sites/{site_id}/seo-work/{item_id}/content-proposal/reopen")
def reopen_proposal(site_id: int, item_id: int, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    work = _content_work(db, site.id, item_id)
    p = _proposal(db, item_id)
    if p is None or p.status != "approved":
        raise HTTPException(409, "Nur freigegebene, noch nicht als veröffentlicht markierte Entwürfe öffnen.")
    p.status = "draft"
    p.approved_at = None
    p.updated_at = utcnow()
    work.status = "draft"
    work.updated_at = utcnow()
    db.commit()
    return _out(p)


@router.post("/sites/{site_id}/seo-work/{item_id}/content-proposal/mark-published")
def mark_published(site_id: int, item_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    work = _content_work(db, site.id, item_id)
    p = _proposal(db, item_id)
    if p is None or p.status != "approved":
        raise HTTPException(409, "Eine gesonderte Freigabe ist vor dem Abschluss erforderlich.")
    p.status = "published"
    p.marked_published_at = utcnow()
    p.updated_at = utcnow()
    work.status = "published"
    work.updated_at = utcnow()
    db.commit()
    out = _out(p)
    out["note"] = "Nur manuell als veröffentlicht markiert; keine CMS-Aktion wurde ausgeführt."
    return out
