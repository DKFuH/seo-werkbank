"""API router for Klumpenrisiko (Traffic & Dependency Concentration Audit)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security.auth import current_user, get_site_for
from ..services.dependency_audit import audit_dependencies

router = APIRouter(tags=["dependency-audit"])


@router.get("/sites/{site_id}/dependency-audit")
def dependency_audit(
    site_id: int,
    days: int = Query(28, ge=7, le=90),
    brand_term: str | None = Query(None, max_length=100),
    provider: Literal["google", "bing"] = Query("google"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Calculates landingpage concentration, brand vs. non-brand share, and search engine resilience (Google vs. Bing)."""
    site = get_site_for(db, user, site_id)
    return audit_dependencies(db, site, days=days, custom_brand_term=brand_term, provider=provider)
