"""Keyword portfolio from Search Console: tracked target keywords, all GSC queries, keyword detail and change journal."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..keywords import research
from ..models import Keyword, KeywordNote, User
from ..security.auth import current_user, get_site_for
from ..services import rank_portfolio as rp

router = APIRouter(tags=["keyword-portfolio"])
ALLOWED_DAYS = (7, 28, 90, 180, 365)
Device = Literal["all", "desktop", "mobile", "tablet"]
Measurement = Literal["national", "lokal", "marke"]


def _device(d: str) -> str | None:
    return None if d == "all" else d


def _days(d: int) -> int:
    if d not in ALLOWED_DAYS:
        raise HTTPException(422, "Zeitraum muss 7, 28, 90, 180 oder 365 Tage sein")
    return d


class KeywordIn(BaseModel):
    keyword: str = Field(min_length=1, max_length=160)
    label: str | None = Field(None, max_length=40)
    target_url: str | None = Field(None, max_length=2048)
    measurement: Measurement = "national"
    priority: int = Field(2, ge=1, le=3)


class KeywordPatch(BaseModel):
    tracked: bool | None = None
    label: str | None = Field(None, max_length=40)
    target_url: str | None = Field(None, max_length=2048)
    measurement: Measurement | None = None
    priority: int | None = Field(None, ge=1, le=3)


class NoteIn(BaseModel):
    event_date: date
    title: str = Field(min_length=1, max_length=160)
    details: str = Field("", max_length=2000)


def _keyword(db: Session, site_id: int, keyword_id: int) -> Keyword:
    k = db.scalar(select(Keyword).where(Keyword.id == keyword_id, Keyword.site_id == site_id))
    if k is None:
        raise HTTPException(404, "Keyword nicht gefunden")
    return k


def _track(db: Session, site_id: int, text: str, **fields) -> Keyword:
    """Track an existing keyword of the site (same normalised text) or create it; keeps the GSC history by text."""
    key = rp.norm(text)
    if not key:
        raise HTTPException(422, "Keyword fehlt")
    k = next((x for x in db.scalars(select(Keyword).where(Keyword.site_id == site_id)) if rp.norm(x.keyword) == key), None)
    if k is None:
        k = Keyword(site_id=site_id, keyword=key[:500], source="tracking", intent=research.classify_intent(key)["intent"], metrics={})
        db.add(k)
    k.tracked = True
    for name, value in fields.items():
        if value is not None:
            setattr(k, name, value)
    db.commit()
    db.refresh(k)
    return k


@router.get("/sites/{site_id}/rank-gsc/portfolio")
def portfolio(site_id: int, days: int = 28, device: Device = "all", label: str | None = Query(None, max_length=40),
              q: str | None = Query(None, max_length=160), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    return rp.portfolio(db, site.id, days=_days(days), device=_device(device), label=label or None, q=q)


@router.get("/sites/{site_id}/rank-gsc/queries")
def queries(site_id: int, days: int = 28, device: Device = "all", scope: Literal["all", "tracked", "untracked"] = "all",
            bucket: Literal["all", "opportunity", "top3", "top10", "top20", "top50", "51plus"] = "all",
            min_impressions: int = Query(0, ge=0, le=100000), q: str | None = Query(None, max_length=160),
            sort: Literal["query", "position", "movement", "impressions", "clicks", "ctr"] = "impressions",
            dir: Literal["asc", "desc"] = "desc", page: int = Query(1, ge=1, le=10000),
            user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    return rp.all_queries(db, site.id, days=_days(days), device=_device(device), scope=scope, bucket=bucket,
                          min_impressions=min_impressions, q=q, sort=sort, direction=dir, page=page)


@router.get("/sites/{site_id}/rank-gsc/keywords/{keyword_id}")
def keyword_detail(site_id: int, keyword_id: int, days: int = 90, device: Device = "all",
                   user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    return rp.keyword_detail(db, site.id, _keyword(db, site.id, keyword_id), days=_days(days), device=_device(device))


@router.post("/sites/{site_id}/rank-gsc/keywords", status_code=201)
def add_keyword(site_id: int, body: KeywordIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    k = _track(db, site.id, body.keyword, label=body.label or None, target_url=body.target_url or None,
               measurement=body.measurement, priority=body.priority)
    return {"id": k.id, "keyword": k.keyword, "tracked": k.tracked}


class AdoptIn(BaseModel):
    query: str = Field(min_length=1, max_length=160)
    label: str | None = Field(None, max_length=40)


@router.post("/sites/{site_id}/rank-gsc/adopt", status_code=201)
def adopt(site_id: int, body: AdoptIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Move a GSC query into the portfolio; its GSC history is used as is (matched by text)."""
    site = get_site_for(db, user, site_id)
    k = _track(db, site.id, body.query, label=body.label or "gsc")
    return {"id": k.id, "keyword": k.keyword, "tracked": True}


@router.patch("/sites/{site_id}/rank-gsc/keywords/{keyword_id}")
def update_keyword(site_id: int, keyword_id: int, body: KeywordPatch, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    k = _keyword(db, site.id, keyword_id)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(k, name, value if value != "" else None)
    db.commit()
    return {"id": k.id, "tracked": k.tracked, "label": k.label, "target_url": k.target_url,
            "measurement": k.measurement, "priority": k.priority}


@router.post("/sites/{site_id}/rank-gsc/keywords/{keyword_id}/notes", status_code=201)
def add_note(site_id: int, keyword_id: int, body: NoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    k = _keyword(db, site.id, keyword_id)
    note = KeywordNote(keyword_id=k.id, event_date=body.event_date, title=body.title, details=body.details)
    db.add(note)
    db.commit()
    return {"id": note.id, "date": note.event_date.isoformat(), "title": note.title, "details": note.details}


@router.delete("/sites/{site_id}/rank-gsc/keywords/{keyword_id}/notes/{note_id}", status_code=204)
def delete_note(site_id: int, keyword_id: int, note_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    k = _keyword(db, site.id, keyword_id)
    note = db.scalar(select(KeywordNote).where(KeywordNote.id == note_id, KeywordNote.keyword_id == k.id))
    if note is None:
        raise HTTPException(404, "Notiz nicht gefunden")
    db.delete(note)
    db.commit()
