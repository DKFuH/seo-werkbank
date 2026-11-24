"""Explicitly configured analytics and paid local SERP provider integrations."""
from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import RankObservation, RankTarget, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for
from ..services import external_intelligence as ext

router = APIRouter(tags=["external-intelligence"])


class ProviderConfig(BaseModel):
    provider: str
    property_id: str | None = Field(None, max_length=40)
    client_email: str | None = Field(None, max_length=300)
    private_key: str | None = Field(None, max_length=6000)
    token: str | None = Field(None, max_length=4000)
    login: str | None = Field(None, max_length=300)
    password: str | None = Field(None, max_length=1000)


@router.get("/sites/{site_id}/external-intelligence/status")
def provider_status(site_id: int, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    return {"providers": [ext.status(db, provider, user.id, site.id) for provider in ext.PROVIDERS],
            "note": "Zugangsdaten werden verschlüsselt gespeichert; Konfiguration beweist keinen Live-Zugriff."}


@router.put("/sites/{site_id}/external-intelligence/config")
def configure_provider(site_id: int, body: ProviderConfig, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if body.provider not in ext.PROVIDERS:
        raise HTTPException(422, "Unbekannter Datenanbieter")
    required = {"ga4": ("property_id", "client_email", "private_key"),
                "clarity": ("token",), "dataforseo": ("login", "password")}[body.provider]
    values = body.model_dump(exclude_none=True, exclude={"provider"})
    current = ext.config(db, body.provider, user.id, site.id)
    if any(not (values.get(key) or current.get(key)) for key in required):
        raise HTTPException(422, "Erforderliche Zugangsdaten fehlen")
    if body.provider == "ga4" and not str(values.get("property_id") or current.get("property_id")).isdigit():
        raise HTTPException(422, "GA4-Property-ID muss numerisch sein")
    ext.configure(db, body.provider, user.id, site.id, {**current, **values})
    db.commit()
    return ext.status(db, body.provider, user.id, site.id)


@router.delete("/sites/{site_id}/external-intelligence/config/{provider}")
def disconnect_provider(site_id: int, provider: str, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if provider not in ext.PROVIDERS:
        raise HTTPException(422, "Unbekannter Datenanbieter")
    ext.configure(db, provider, user.id, site.id, {})
    db.commit()
    return ext.status(db, provider, user.id, site.id)


@router.get("/sites/{site_id}/external-intelligence/ga4")
async def ga4(site_id: int, days: int = Query(28, ge=7, le=90),
              user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if not ext.status(db, "ga4", user.id, site.id)["connected"]:
        raise HTTPException(409, "GA4-Service-Account zuerst verbinden")
    try:
        return await ext.ga4_overview(ext.config(db, "ga4", user.id, site.id), days=days)
    except ext.ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/sites/{site_id}/external-intelligence/clarity")
async def clarity(site_id: int, days: int = Query(3, ge=1, le=3),
                  user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if not ext.status(db, "clarity", user.id, site.id)["connected"]:
        raise HTTPException(409, "Clarity API-Token zuerst verbinden")
    # Clarity restricts requests per project per day; locally stop after eight.
    today = datetime.now(UTC).date()
    key = f"{user.id}:{today.isoformat()}"
    used = db.scalar(select(func.count()).select_from(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "clarity_call",
        SeoResearchRecord.title == key)) or 0
    if used >= 8:
        raise HTTPException(429, "Lokales Clarity-Tagesbudget erreicht (8 Anfragen)")
    # Reserve a slot before doing I/O, including on provider failure.
    db.add(SeoResearchRecord(site_id=site.id, kind="clarity_call", source="api",
                             title=key, payload={"days": days, "date": today.isoformat()}))
    db.commit()
    try:
        return await ext.clarity_overview(ext.config(db, "clarity", user.id, site.id), days=days)
    except ext.ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc


class LocalRankIn(BaseModel):
    target_id: int = Field(ge=1)
    acknowledge_cost: bool = False


@router.post("/sites/{site_id}/external-intelligence/local-rank")
async def local_rank(site_id: int, body: LocalRankIn, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if not body.acknowledge_cost:
        raise HTTPException(422, "Kostenpflichtige Anbieterabfragen ausdrücklich bestätigen")
    if not ext.status(db, "dataforseo", user.id, site.id)["connected"]:
        raise HTTPException(409, "DataForSEO-Zugang zuerst verbinden")
    target = db.scalar(select(RankTarget).where(RankTarget.id == body.target_id,
                                                RankTarget.site_id == site.id))
    if not target:
        raise HTTPException(404, "Rank-Target nicht gefunden")
    if target.engine != "google" or not target.location or len(target.location.strip()) < 3:
        raise HTTPException(422, "Google-Target mit konkreter Ortsangabe erforderlich")
    host = (urlsplit(site.url).hostname or "").lower().removeprefix("www.")
    try:
        result = await ext.local_serp(ext.config(db, "dataforseo", user.id, site.id),
                                      keyword=target.keyword, location=target.location,
                                      language=target.language, own_host=host)
    except ext.ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc
    now = datetime.now(UTC).replace(tzinfo=None)
    for mode in ("organic", "maps"):
        match = result[mode]
        db.add(RankObservation(target_id=target.id, observed_at=now,
                               provider=f"dataforseo:{mode}",
                               position=int(match["position"]) if match and isinstance(match["position"], int) else None,
                               result_url=match.get("url") if match else None,
                               search_depth=result["depth"], serp_features=[mode],
                               notes=f"Standort: {target.location}; Anbieter-API; nicht GSC"))
    db.commit()
    return result
