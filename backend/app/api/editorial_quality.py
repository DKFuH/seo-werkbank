"""Editorial policy checks for user-entered or stored content proposals."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SeoContentProposal, SeoWorkItem, User
from ..security.auth import current_user, get_site_for
from ..services.editorial_quality import review

router = APIRouter(tags=["editorial-quality"])


class DraftIn(BaseModel):
    original_text: str = Field("", max_length=100000)
    proposed_text: str = Field(min_length=1, max_length=100000)
    rationale: str = Field("", max_length=10000)


def _work(db: Session, site_id: int, item_id: int) -> SeoWorkItem:
    item = db.scalar(select(SeoWorkItem).where(SeoWorkItem.id == item_id,
                                               SeoWorkItem.site_id == site_id,
                                               SeoWorkItem.kind == "content"))
    if item is None:
        raise HTTPException(404, "Content-Vorgang nicht gefunden")
    return item


@router.post("/sites/{site_id}/seo-work/{item_id}/editorial-qa")
def editorial_preview(site_id: int, item_id: int, body: DraftIn,
                      user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    _work(db, site.id, item_id)
    return review(body.original_text, body.proposed_text, body.rationale)


@router.get("/sites/{site_id}/seo-work/{item_id}/editorial-qa")
def editorial_saved(site_id: int, item_id: int, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    _work(db, site.id, item_id)
    row = db.scalar(select(SeoContentProposal).where(SeoContentProposal.work_item_id == item_id))
    if row is None:
        raise HTTPException(404, "Kein gespeicherter Entwurf")
    if row.content_type == "application/ld+json":
        return {"findings": [], "finding_count": 0, "needs_review": False,
                "note": "JSON-LD wird durch den separaten Schema-Validator geprüft."}
    return review(row.original_text, row.proposed_text, row.rationale)
