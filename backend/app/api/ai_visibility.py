"""Site-isolated recording of manually observed AI citations and brand mentions."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AiVisibilityObservation, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["ai-visibility"])

Platform = Literal["chatgpt", "perplexity", "claude", "gemini", "copilot", "google_ai", "other"]


class ObservationIn(BaseModel):
    platform: Platform
    model_name: str | None = Field(None, max_length=100)
    prompt: str = Field(min_length=1, max_length=2000)
    brand_mentioned: bool = False
    cited_url: str | None = Field(None, max_length=2048)
    evidence_url: str | None = Field(None, max_length=2048)
    response_excerpt: str = Field("", max_length=5000)
    notes: str = Field("", max_length=5000)
    observed_at: datetime | None = None


def _out(o: AiVisibilityObservation) -> dict:
    return {"id": o.id, "site_id": o.site_id, "platform": o.platform, "model_name": o.model_name, "prompt": o.prompt,
            "brand_mentioned": o.brand_mentioned, "cited_url": o.cited_url, "evidence_url": o.evidence_url,
            "response_excerpt": o.response_excerpt, "notes": o.notes, "observed_at": o.observed_at.isoformat(),
            "created_at": o.created_at.isoformat(), "source": "manual", "verified": False}


@router.get("/sites/{site_id}/ai-visibility/observations")
def list_observations(site_id: int, platform: Platform | None = None,
                      limit: int = Query(200, ge=1, le=1000),
                      user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    stmt = select(AiVisibilityObservation).where(AiVisibilityObservation.site_id == site.id)
    if platform:
        stmt = stmt.where(AiVisibilityObservation.platform == platform)
    rows = db.scalars(stmt.order_by(AiVisibilityObservation.observed_at.desc(), AiVisibilityObservation.id.desc()).limit(limit)).all()
    return {"items": [_out(o) for o in rows],
            "source": "manual",
            "method": "Ausschließlich manuelle Stichproben. Keine API-Anbindung, keine repräsentative Sichtbarkeitsmessung. "
                      "Eine Marken-Erwähnung ist von einer konkreten URL-Zitation zu unterscheiden."}


@router.post("/sites/{site_id}/ai-visibility/observations", status_code=201)
def create_observation(site_id: int, body: ObservationIn, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    from ..models import utcnow

    site = get_site_for(db, user, site_id)
    payload = body.model_dump(exclude={"observed_at"})
    observed_at = body.observed_at.replace(tzinfo=None) if body.observed_at else utcnow()
    if observed_at > utcnow():
        raise HTTPException(422, "Zukünftiges Beobachtungsdatum nicht zulässig")
    observation = AiVisibilityObservation(site_id=site.id, observed_at=observed_at, **payload)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return _out(observation)


@router.delete("/sites/{site_id}/ai-visibility/observations/{observation_id}", status_code=204)
def delete_observation(site_id: int, observation_id: int, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    observation = db.scalar(select(AiVisibilityObservation).where(
        AiVisibilityObservation.id == observation_id, AiVisibilityObservation.site_id == site.id))
    if observation is None:
        raise HTTPException(404, "Beobachtung nicht gefunden")
    db.delete(observation)
    db.commit()
