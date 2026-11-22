"""Content evidence, conversion review, comparison quality and asset briefs.

Analyses are transparent checklists with explicitly unverified user evidence;
technical text signals are weak indicators, never a promise of SEO/CRO impact.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Page, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for
from .deps import latest_crawl

router = APIRouter(tags=["research-quality"])


def _records(db: Session, site_id: int, kind: str) -> list[SeoResearchRecord]:
    return db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site_id, SeoResearchRecord.kind == kind)
        .order_by(SeoResearchRecord.id.desc()).limit(1000)).all()


@router.get("/sites/{site_id}/research/content-evidence")
def evidence_review(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in _records(db, site.id, "content_evidence"):
        p = item.payload
        supplied = bool(p.get("evidence_url"))
        groups[str(p["page_url"])].append({
            "id": item.id, "claim": p["claim"], "evidence_type": p.get("evidence_type"),
            "evidence_url": p.get("evidence_url"), "evidence_supplied": supplied,
            "verified": False, "editorial_action": "Source and claim manually verify" if supplied
            else "Supply a verifiable source for this claim",
        })
    out = [{"page_url": u, "claims": v, "source_links_missing": sum(not c["evidence_supplied"] for c in v)}
           for u, v in sorted(groups.items())]
    return {"items": out, "method": "Submitted evidence links are not externally verified. No official Google Content Effort score exists in this analysis."}


@router.get("/sites/{site_id}/research/cro-audit")
def cro_audit(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    manual = _records(db, site.id, "cro_review")
    by_url: dict[str, list[dict]] = defaultdict(list)
    for record in manual:
        p = record.payload
        by_url[str(p["page_url"])].append({"criterion": p["criterion"], "result": p["result"],
                                            "evidence_url": p.get("evidence_url"), "source": record.source})
    if not crawl:
        return {"crawl_id": None, "items": [], "manual_reviews": by_url,
                "method": "No completed crawl; CRO visual layout and conversion rates cannot be inferred."}
    pages = db.scalars(select(Page).where(
        Page.crawl_id == crawl.id, Page.is_html.is_(True), Page.indexable.is_(True))
        .order_by(Page.pagerank.desc()).limit(200)).all()
    results = []
    cta_words = ("contact", "anfragen", "angebot", "termin", "subscribe", "get started", "jetzt", "book", "kaufen", "bestellen")
    for page in pages:
        excerpt = (page.text or "")[:20000].casefold()
        results.append({
            "url": page.url, "title": page.title, "h1_present": bool(page.h1),
            "meta_description_present": bool(page.meta_description),
            "text_contains_possible_cta": any(word in excerpt for word in cta_words),
            "manual_reviews": by_url.get(page.url, []),
            "not_examined": ["visual hierarchy above the fold", "mobile layout", "actual form completion",
                             "visitor intent", "trustworthiness of testimonials", "conversion rate"],
        })
    return {"crawl_id": crawl.id, "items": results, "manual_reviews": by_url,
            "method": "H1, meta description and CTA word matches are weak technical signals. "
                      "Visual/UX conclusions require screenshots or actual human review; conversions need analytics."}


@router.get("/sites/{site_id}/research/comparison-review")
def comparison_review(site_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    items = []
    for record in _records(db, site.id, "comparison"):
        p = record.payload
        source = p.get("source_url")
        items.append({"id": record.id, "title": record.title, "subject_a": p["subject_a"],
                      "subject_b": p["subject_b"], "criterion": p["criterion"],
                      "observed_value": p.get("observed_value"),
                      "source_url": source, "needs_source": not bool(source), "verified": False})
    return {"items": items, "method": "Comparison facts and prices are user-supplied; source presence is not factual verification."}


@router.get("/sites/{site_id}/research/asset-briefs")
def asset_briefs(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    rows = []
    for record in _records(db, site.id, "asset_brief"):
        p = record.payload
        missing = [k for k in ("success_metric", "target_url") if not p.get(k)]
        rows.append({
            "id": record.id, "title": record.title, "purpose": p["purpose"],
            "audience": p["audience"], "format": p["format"],
            "target_url": p.get("target_url"), "success_metric": p.get("success_metric"),
            "missing_specifications": missing,
            "review_checklist": ["Original utility rather than copied competitor material",
                                 "Accessibility and mobile usability", "Data sources and freshness",
                                 "Performance and tracking consent", "Embed and attribution rights",
                                 "Actual user value before any outreach"],
        })
    return {"items": rows, "method": "A planning and QA laboratory, not a website/code generator or guarantee of earned backlinks."}
