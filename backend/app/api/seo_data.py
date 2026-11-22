"""Explicit, user-scoped SEO provider catalogue and data endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security.auth import current_user, get_site_for
from ..services.seo_data_providers import provider_catalogue, provider_data

router = APIRouter(tags=["seo-data"])


@router.get("/seo-data/providers")
def available_providers(user: User = Depends(current_user)) -> dict:
    return {"providers": provider_catalogue(), "note": "These adapters read existing GSC and imported data; no external paid APIs."}


@router.get("/sites/{site_id}/seo-data/{source}")
def read_provider_data(site_id: int, source: str,
                       limit: int = Query(100, ge=1, le=200),
                       days: int = Query(28, ge=7, le=180),
                       user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    try:
        return provider_data(db, site.id, source, limit=limit, days=days)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
