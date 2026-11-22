"""Directory listing quality and stability of manually observed AI citation sources.

No fabricated domain authority, link equity, AI coverage or actual traffic.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AiVisibilityObservation, Backlink, Citation, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["authority-intelligence"])


def _numeric(value: object) -> float | None:
    try:
        n = float(value) if value not in (None, "") else None
        return n if n is not None and 0 <= n <= 1_000_000 else None
    except (ValueError, TypeError):
        return None


def _rating(value: object) -> int | None:
    try:
        if isinstance(value, bool) or str(value).strip() not in ("0", "1", "2", "3"):
            return None
        return int(str(value))
    except (ValueError, TypeError):
        return None


def quality_summary(payload: dict) -> dict:
    relevance = _rating(payload.get("relevance"))
    editorial = _rating(payload.get("editorial_value"))
    cost = _numeric(payload.get("cost_eur"))
    visitors = _numeric(payload.get("referral_visits"))
    return {"relevance_assessed": relevance, "editorial_value_assessed": editorial,
            "cost_eur_reported": cost, "referral_visits_reported": visitors,
            "manual_quality_label": ("prüfenswert" if relevance >= 2 and editorial >= 2 else "niedrige subjektive Priorität")
            if relevance is not None and editorial is not None else "Bewertung fehlt",
            "cost_per_visit": round(cost / visitors, 2) if cost is not None and visitors and visitors > 0 else None,
            "verified": False}


def _norm(url: str | None) -> str:
    return (url or "").strip().rstrip("/").casefold()


@router.get("/sites/{site_id}/authority/directories")
def directory_quality(site_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    records = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "directory_assessment")
        .order_by(SeoResearchRecord.id.desc()).limit(1000)).all()
    backlinks = db.scalars(select(Backlink).where(Backlink.site_id == site.id).limit(20000)).all()
    citations = db.scalars(select(Citation).where(Citation.site_id == site.id).limit(5000)).all()
    by_link: dict[str, list[Backlink]] = defaultdict(list)
    for link in backlinks:
        by_link[_norm(link.source_url)].append(link)
    known_citations = {_norm(c.url) for c in citations if c.url}
    result = []
    for r in records:
        p = r.payload
        url = str(p["listing_url"])
        matching = by_link.get(_norm(url), [])
        result.append({"id": r.id, "directory": p["directory"], "listing_url": url,
                       **quality_summary(p), "listed_in_imported_citations": _norm(url) in known_citations,
                       "matched_backlink_count": len(matching),
                       "backlink_statuses": dict(Counter(x.status for x in matching)),
                       "source_note": p.get("source_note")})
    return {"items": result, "method": "Relevance and editorial merit are self-assessed 0–3 values; backlink/citation "
            "evidence is imported or explicitly checked. No domain authority score, Google ranking effect or predicted "
            "referrals. Cost-per-visit only calculated from supplied values with matching units."}


def _citation_groups(observations: list[AiVisibilityObservation], manual: list[SeoResearchRecord]) -> list[dict]:
    by_test: dict[tuple[str, str], dict] = defaultdict(lambda: {"samples": 0, "sources": defaultdict(set), "dates": set()})
    for obs in observations:
        key = ((obs.platform or "").casefold(), " ".join((obs.prompt or "").casefold().split())[:300])
        if not key[1]:
            continue
        bucket = by_test[key]
        bucket["samples"] += 1
        bucket["dates"].add(obs.observed_at.date().isoformat())
        if obs.cited_url:
            bucket["sources"][_norm(obs.cited_url)].add(obs.observed_at.date().isoformat())
    for record in manual:
        p = record.payload
        key = (str(p.get("platform") or "").casefold(), " ".join(str(p.get("prompt") or "").casefold().split())[:300])
        if not key[1]:
            continue
        bucket = by_test[key]
        bucket["samples"] += 1
        bucket["dates"].add(record.observed_at.date().isoformat())
        urls = p.get("cited_urls") or []
        if isinstance(urls, str):
            urls = [urls]
        for url in urls[:50]:
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                bucket["sources"][_norm(url)].add(record.observed_at.date().isoformat())
    out = []
    for (platform, prompt), bucket in sorted(by_test.items()):
        sources = [{"url": url, "distinct_days_cited": len(days),
                    "repeated_on_multiple_days": len(days) >= 2}
                   for url, days in bucket["sources"].items()]
        sources.sort(key=lambda x: (-x["distinct_days_cited"], x["url"]))
        out.append({"platform": platform, "prompt": prompt, "sample_count": bucket["samples"],
                    "sampled_days": len(bucket["dates"]), "sources": sources,
                    "interpretation": "Repeated source in manually recorded samples only; not representative of AI-search traffic."})
    return out


@router.get("/sites/{site_id}/authority/ai-source-stability")
def ai_source_stability(site_id: int, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    observations = db.scalars(select(AiVisibilityObservation).where(
        AiVisibilityObservation.site_id == site.id).order_by(AiVisibilityObservation.id.desc()).limit(1500)).all()
    manual = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "geo_sample")
        .order_by(SeoResearchRecord.id.desc()).limit(1500)).all()
    return {"items": _citation_groups(observations, manual),
            "observations_considered": len(observations) + len(manual),
            "method": "Platform + normalized identical prompt with unique sampled dates; URL observations from manual "
                      "entries only. No live AI browsing, citation-verification, trend projection or market share."}
