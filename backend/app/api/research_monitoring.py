"""Observed SEO change events and provider-labelled SERP features."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import RankObservation, RankTarget, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["seo-changes"])


@router.get("/sites/{site_id}/research/change-timeline")
def change_timeline(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    events = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "update_event").limit(300)).all()
    targets = db.scalars(select(RankTarget).where(RankTarget.site_id == site.id).limit(200)).all()
    dated: dict[int, date] = {}
    for event in events:
        try:
            dated[event.id] = date.fromisoformat(str(event.payload["event_date"]))
        except ValueError:
            pass
    # One query for every observation that can fall into any event window (instead of events x targets queries).
    by_target: dict[int, list[RankObservation]] = defaultdict(list)
    if dated and targets:
        lo = datetime.combine(min(dated.values()) - timedelta(days=14), time.min)
        hi = datetime.combine(max(dated.values()) + timedelta(days=15), time.min)
        for obs in db.scalars(select(RankObservation).where(
                RankObservation.target_id.in_([t.id for t in targets]),
                RankObservation.observed_at >= lo, RankObservation.observed_at < hi)
                .order_by(RankObservation.observed_at, RankObservation.id).limit(100_000)):
            by_target[obs.target_id].append(obs)
    out = []
    for event in events:
        when = dated.get(event.id)
        if when is None:
            out.append({"id": event.id, "title": event.title, "date": event.payload["event_date"],
                        "comparison": [], "warning": "Invalid date; use YYYY-MM-DD"})
            continue
        start = datetime.combine(when - timedelta(days=14), time.min)
        stop = datetime.combine(when + timedelta(days=15), time.min)
        comparisons = []
        for target in targets:
            observations = [x for x in by_target.get(target.id, []) if start <= x.observed_at < stop]
            before = [x for x in observations if x.observed_at.date() < when and x.position is not None]
            after = [x for x in observations if x.observed_at.date() > when and x.position is not None]
            if before and after and before[-1].provider == after[0].provider:
                comparisons.append({"keyword": target.keyword, "provider": before[-1].provider,
                                    "before": before[-1].position, "after": after[0].position,
                                    "delta": before[-1].position - after[0].position})
        out.append({"id": event.id, "title": event.title, "date": when.isoformat(),
                    "event_type": event.payload["event_type"], "comparison": comparisons[:100],
                    "warning": "Only a temporal association, not proof of causality."})
    return {"items": out, "method": "User-entered events and same-provider snapshots within 14 days; no automatic Google update calendar."}


@router.get("/sites/{site_id}/research/serp-features")
def serp_features(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    manual = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "serp_feature").limit(1000)).all()
    target_ids = db.scalars(select(RankTarget.id).where(RankTarget.site_id == site.id).limit(200)).all()
    sources: dict[str, Counter] = defaultdict(Counter)
    for record in manual:
        features = record.payload.get("features", [])
        for feature in features if isinstance(features, list) else [features]:
            sources["manual:" + str(record.payload["provider"])][str(feature)] += 1
    for target_id in target_ids:
        for obs in db.scalars(select(RankObservation).where(
            RankObservation.target_id == target_id).order_by(RankObservation.id.desc()).limit(100)):
            for feature in obs.serp_features or []:
                sources[obs.provider][str(feature)] += 1
    return {"sources": [{"provider": name, "features": dict(counts)}
                        for name, counts in sorted(sources.items())],
            "method": "Feature occurrence counts in recorded snapshots, not total SERPs or AI Overview market share."}
