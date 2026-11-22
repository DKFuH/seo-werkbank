"""Indexing status comparisons and user-recorded AI citation patterns."""
from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AiVisibilityObservation, Page, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for
from .deps import latest_crawl

router = APIRouter(tags=["index-geo-research"])


@router.get("/sites/{site_id}/research/indexing-review")
def indexing_review(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    entries = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "indexing")
        .order_by(SeoResearchRecord.id.desc()).limit(1000)).all()
    urls = {str(x.payload["page_url"]) for x in entries}
    pages = {}
    if crawl and urls:
        pages = {p.url: p for p in db.scalars(select(Page).where(
            Page.crawl_id == crawl.id, Page.url.in_(urls)).limit(2000))}
    out = []
    for entry in entries:
        p = entry.payload
        page = pages.get(str(p["page_url"]))
        out.append({"id": entry.id, "url": p["page_url"], "reported_status": p["status"],
                    "status_source": entry.source, "evidence_url": p.get("evidence_url"),
                    "crawl_found": page is not None, "technically_indexable": page.indexable if page else None,
                    "technical_reason": page.indexability_reason if page else None,
                    "canonical": page.canonical if page else None,
                    "discrepancy_to_review": page is not None and not page.indexable and p["status"] == "indexed",
                    "verified_google_index_status": False})
    return {"crawl_id": crawl.id if crawl else None, "items": out,
            "method": "Manually reported indexing vs. crawl signals; not Google URL Inspection API results."}


@router.get("/sites/{site_id}/research/geo-citations")
def geo_citations(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    observations = db.scalars(select(AiVisibilityObservation).where(
        AiVisibilityObservation.site_id == site.id).order_by(AiVisibilityObservation.id.desc()).limit(1000)).all()
    samples = db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "geo_sample").limit(1000)).all()
    sources: dict[str, Counter] = defaultdict(Counter)
    for o in observations:
        if o.cited_url:
            sources[o.platform][o.cited_url] += 1
    for record in samples:
        p = record.payload
        urls = p.get("cited_urls", [])
        if isinstance(urls, str):
            urls = [urls]
        for url in urls[:50]:
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                sources[str(p["platform"])][url] += 1
    return {"platforms": [{"platform": platform,
                           "citations": [{"url": url, "sample_count": count} for url, count in counts.most_common(100)]}
                          for platform, counts in sorted(sources.items())],
            "samples_reviewed": len(observations) + len(samples),
            "method": "Manually reported citations per platform. Not verified, representative AI visibility or referral visits."}
