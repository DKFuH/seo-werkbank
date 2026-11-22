"""Evidence-first topical planning, PAA question logs and internal search journeys.

All records are editable user observations/plans, never automatically scraped
Google People Also Ask results. Site ownership is checked on every operation.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Link, Page, SeoResearchRecord, User, utcnow
from ..security.auth import current_user, get_site_for
from ..text import content_tokens, stem
from .deps import latest_crawl

router = APIRouter(tags=["seo-research"])
Kinds = Literal["topic_map", "paa_question", "search_journey", "content_evidence", "cro_review",
                "comparison", "asset_brief", "indexing", "serp_feature", "update_event", "geo_sample"]
REQUIRED = {
    "topic_map": ("offer", "attributes"),
    "paa_question": ("question", "topic"),
    "search_journey": ("source_url", "target_url", "stage"),
    "content_evidence": ("page_url", "claim"),
    "cro_review": ("page_url", "criterion", "result"),
    "comparison": ("subject_a", "subject_b", "criterion"),
    "asset_brief": ("purpose", "audience", "format"),
    "indexing": ("page_url", "status"),
    "serp_feature": ("keyword", "provider", "features"),
    "update_event": ("event_date", "event_type", "description"),
    "geo_sample": ("platform", "prompt", "response"),
}
STAGES = ("awareness", "consideration", "decision", "conversion")
SOURCE = ("manual", "import", "crawl", "provider")
MAX_PAYLOAD = 16000


class RecordIn(BaseModel):
    kind: Kinds
    title: str = Field(min_length=1, max_length=300)
    payload: dict[str, Any]
    source: Literal["manual", "import"] = "manual"
    notes: str = Field("", max_length=5000)
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def valid_payload(self):
        if len(json.dumps(self.payload, ensure_ascii=False)) > MAX_PAYLOAD:
            raise ValueError("Payload too large")
        missing = [key for key in REQUIRED[self.kind] if not self.payload.get(key)]
        if missing:
            raise ValueError("Missing fields: " + ", ".join(missing))
        for key, value in self.payload.items():
            if not isinstance(key, str) or len(key) > 100:
                raise ValueError("Invalid field name")
            if isinstance(value, str) and len(value) > 3000:
                raise ValueError("Field too long")
            if isinstance(value, list) and (len(value) > 100 or any(not isinstance(v, str) or len(v) > 500 for v in value)):
                raise ValueError("Invalid list field")
            if isinstance(value, (dict, list)) and not isinstance(value, list):
                raise ValueError("Nested objects not supported")
        if self.kind == "search_journey" and self.payload.get("stage") not in STAGES:
            raise ValueError("Unknown journey stage")
        return self


class RecordPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    payload: dict[str, Any] | None = None
    notes: str | None = Field(None, max_length=5000)


def _record(db: Session, site_id: int, record_id: int) -> SeoResearchRecord:
    found = db.scalar(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site_id, SeoResearchRecord.id == record_id))
    if not found:
        raise HTTPException(404, "Research record not found")
    return found


def _out(r: SeoResearchRecord) -> dict:
    return {"id": r.id, "site_id": r.site_id, "kind": r.kind, "title": r.title, "source": r.source,
            "payload": r.payload, "notes": r.notes, "observed_at": r.observed_at.isoformat(),
            "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
            "verification": "manual_or_imported_not_independently_verified"}


@router.get("/sites/{site_id}/research")
def list_records(site_id: int, kind: Kinds | None = None, limit: int = Query(200, ge=1, le=500),
                 user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    query = select(SeoResearchRecord).where(SeoResearchRecord.site_id == site.id)
    if kind:
        query = query.where(SeoResearchRecord.kind == kind)
    rows = db.scalars(query.order_by(SeoResearchRecord.id.desc()).limit(limit)).all()
    return {"items": [_out(r) for r in rows], "categories": list(REQUIRED),
            "method": "Research notes and imported observations, not verified third-party rankings or Google factors."}


@router.post("/sites/{site_id}/research", status_code=201)
def create_record(site_id: int, body: RecordIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    when = body.observed_at.replace(tzinfo=None) if body.observed_at else utcnow()
    if when > utcnow():
        raise HTTPException(422, "Future observations not accepted")
    record = SeoResearchRecord(site_id=site.id, kind=body.kind, title=body.title,
                               source=body.source, payload=body.payload, notes=body.notes,
                               observed_at=when)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _out(record)


@router.patch("/sites/{site_id}/research/{record_id}")
def edit_record(site_id: int, record_id: int, body: RecordPatch, user: User = Depends(current_user),
                db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    record = _record(db, site.id, record_id)
    changes = body.model_dump(exclude_unset=True)
    merged = {"kind": record.kind, "title": changes.get("title", record.title),
              "payload": changes.get("payload", record.payload), "source": record.source,
              "notes": changes.get("notes", record.notes)}
    RecordIn.model_validate(merged)
    for key, value in changes.items():
        setattr(record, key, value)
    record.updated_at = utcnow()
    db.commit()
    return _out(record)


@router.delete("/sites/{site_id}/research/{record_id}", status_code=204)
def delete_record(site_id: int, record_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    record = _record(db, site.id, record_id)
    db.delete(record)
    db.commit()


def _words(text: str) -> set[str]:
    return {stem(t) for t in content_tokens(text or "")}


@router.get("/sites/{site_id}/research/topic-coverage")
def topic_coverage(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    topics = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "topic_map").limit(300)).all()
    titles = []
    if crawl:
        titles = db.execute(select(Page.url, Page.title, Page.h1).where(
            Page.crawl_id == crawl.id, Page.indexable.is_(True)).limit(3000)).all()
    results = []
    for topic in topics:
        offer = str(topic.payload["offer"])
        attrs = topic.payload["attributes"]
        if not isinstance(attrs, list):
            attrs = [str(attrs)]
        for attribute in attrs[:100]:
            terms = _words(str(attribute))
            matched = [{"url": url, "title": title or h1} for url, title, h1 in titles
                       if terms and terms <= _words(" ".join([title or "", h1 or ""]))][:5]
            results.append({"topic_id": topic.id, "offer": offer, "attribute": attribute,
                            "heading_matches": matched, "heading_match_count": len(matched)})
    return {"crawl_id": crawl.id if crawl else None, "items": results,
            "method": "Only literal/stemmed heading matches. No semantic coverage, keyword volume or rankings are claimed."}


@router.get("/sites/{site_id}/research/question-tree")
def question_tree(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    records = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "paa_question").limit(1000)).all()
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen = set()
    for record in records:
        topic = str(record.payload["topic"]).strip()
        question = str(record.payload["question"]).strip()
        key = (topic.casefold(), question.casefold())
        if key in seen:
            continue
        seen.add(key)
        grouped[topic].append({"id": record.id, "question": question, "source": record.source,
                               "evidence_url": record.payload.get("evidence_url")})
    return {"topics": [{"topic": k, "questions": v} for k, v in sorted(grouped.items())],
            "method": "Manually entered or imported questions; not a live People Also Ask API."}


@router.get("/sites/{site_id}/research/journeys")
def journey_review(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    records = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "search_journey").limit(1000)).all()
    found = set()
    if crawl and records:
        sources = {r.payload["source_url"] for r in records}
        targets = {r.payload["target_url"] for r in records}
        found = set(db.execute(select(Link.source_url, Link.target_url).where(
            Link.crawl_id == crawl.id, Link.is_internal.is_(True),
            Link.source_url.in_(sources), Link.target_url.in_(targets))))
    return {"crawl_id": crawl.id if crawl else None,
            "items": [{"id": r.id, "title": r.title, "stage": r.payload["stage"],
                       "source_url": r.payload["source_url"], "target_url": r.payload["target_url"],
                       "link_observed": (r.payload["source_url"], r.payload["target_url"]) in found if crawl else None}
                      for r in records],
            "method": "Manually planned journey transitions checked against actual internal links of the last crawl. "
                      "No claim about real visitor behavior or conversion."}
