"""Owned keyword rank targets and provenance-aware observation history.

Manual observations and provider responses are not interchangeable with Search
Console average positions. Search results are not scraped from Google.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import RankObservation, RankTarget, User, utcnow
from ..security.auth import current_user, get_site_for
from ..serp import analyzer as serp
from ..services.settings_store import get_setting

router = APIRouter(tags=["rank-tracking"])


class TargetIn(BaseModel):
    keyword: str = Field(min_length=2, max_length=500)
    engine: Literal["google", "brave", "searxng", "google_cse"] = "google"
    country: str = Field("de", pattern=r"^[a-z]{2}$")
    language: str = Field("de", pattern=r"^[a-z]{2}$")
    device: Literal["desktop", "mobile"] = "desktop"
    location: str | None = Field(None, max_length=120)
    landing_url: str | None = Field(None, max_length=2048)


class ObservationIn(BaseModel):
    provider: Literal["manual", "serp_import"] = "manual"
    position: int | None = Field(None, ge=1, le=1000)
    result_url: str | None = Field(None, max_length=2048)
    search_depth: int = Field(10, ge=1, le=1000)
    serp_features: list[str] = Field(default_factory=list, max_length=30)
    observed_at: datetime | None = None
    notes: str = Field("", max_length=1000)


def _target(db: Session, site_id: int, target_id: int) -> RankTarget:
    target = db.scalar(select(RankTarget).where(RankTarget.id == target_id, RankTarget.site_id == site_id))
    if target is None:
        raise HTTPException(404, "Rank target not found")
    return target


def _target_out(t: RankTarget, history: list[RankObservation]) -> dict:
    rows = [{"id": x.id, "observed_at": x.observed_at.isoformat(), "position": x.position,
             "provider": x.provider, "result_url": x.result_url, "search_depth": x.search_depth,
             "serp_features": x.serp_features or [], "notes": x.notes} for x in history]
    newest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) > 1 else None
    delta = (previous["position"] - newest["position"] if newest and previous
             and newest["position"] is not None and previous["position"] is not None
             and newest["provider"] == previous["provider"] else None)
    return {"id": t.id, "keyword": t.keyword, "engine": t.engine, "country": t.country,
            "language": t.language, "device": t.device, "location": t.location,
            "landing_url": t.landing_url, "history": rows, "latest": newest,
            "position_delta": delta, "delta_note": "Nur Positionen desselben Datenanbieters vergleichbar. Keine Kausalitätsaussage."}


@router.post("/sites/{site_id}/rank-targets", status_code=201)
def add_target(site_id: int, body: TargetIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if db.scalar(select(RankTarget.id).where(RankTarget.site_id == site.id, RankTarget.keyword == body.keyword,
                  RankTarget.engine == body.engine, RankTarget.country == body.country,
                  RankTarget.language == body.language, RankTarget.device == body.device,
                  RankTarget.location == body.location)):
        raise HTTPException(409, "Target already exists")
    obj = RankTarget(site_id=site.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _target_out(obj, [])


@router.get("/sites/{site_id}/rank-targets")
def list_targets(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    targets = db.scalars(select(RankTarget).where(RankTarget.site_id == site.id).order_by(RankTarget.id.desc()).limit(300)).all()
    out = []
    for target in targets:
        history = db.scalars(select(RankObservation).where(RankObservation.target_id == target.id)
                             .order_by(RankObservation.observed_at, RankObservation.id).limit(1000)).all()
        out.append(_target_out(target, history))
    return {"items": out, "method": "Rank observations are manual or provider-specific snapshots, not official Google rankings."}


@router.delete("/sites/{site_id}/rank-targets/{target_id}", status_code=204)
def remove_target(site_id: int, target_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    target = _target(db, site.id, target_id)
    db.delete(target)
    db.commit()


@router.post("/sites/{site_id}/rank-targets/{target_id}/observations", status_code=201)
def add_observation(site_id: int, target_id: int, body: ObservationIn,
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    target = _target(db, site.id, target_id)
    when = body.observed_at.replace(tzinfo=None) if body.observed_at else utcnow()
    if when > utcnow():
        raise HTTPException(422, "Future observation not allowed")
    if body.position is not None and body.position > body.search_depth:
        raise HTTPException(422, "Position exceeds observed result depth")
    if body.result_url and urlsplit(body.result_url).scheme not in ("http", "https"):
        raise HTTPException(422, "Unsupported URL scheme")
    obj = RankObservation(target_id=target.id, observed_at=when, **body.model_dump(exclude={"observed_at"}))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _target_out(target, [obj])["history"][0]


@router.post("/sites/{site_id}/rank-targets/{target_id}/capture", status_code=201)
async def capture_rank(site_id: int, target_id: int, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    target = _target(db, site.id, target_id)
    provider = get_setting(db, "serp")
    if provider.get("provider", "none") == "none":
        raise HTTPException(422, "Configure a supported SERP provider first")
    if target.device != "desktop" or target.location:
        raise HTTPException(422, "Provider does not support guaranteed device/city targeting; use desktop without a city")
    # This is provider-specific ordering, not a verified Google SERP position.
    try:
        result = await serp.search(provider, target.keyword, country=target.country,
                                   lang=target.language, num=10)
    except serp.SerpError as exc:
        raise HTTPException(502, "SERP provider did not return usable results") from exc
    host = urlsplit(site.url).hostname or ""
    matching = [r for r in result["results"] if urlsplit(r["url"]).hostname == host or
                (urlsplit(r["url"]).hostname or "").endswith("." + host)]
    found = matching[0] if matching else None
    obj = RankObservation(target_id=target.id, observed_at=utcnow(), provider=result["provider"],
                          position=found["position"] if found else None,
                          result_url=found["url"] if found else None,
                          search_depth=len(result["results"]), serp_features=result.get("features") or [],
                          notes="Position based on this provider's result ordering; not an official Google rank")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _target_out(target, [obj])["history"][0]
