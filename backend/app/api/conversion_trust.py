"""Evidence-based conversion funnel and brand trust reviews.

Audits are deliberately non-causal. They use site-owned crawl metadata and
explicitly supplied editorial records, never invented conversion rates or
automated assertions that a review/testimonial is genuine.
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Page, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for
from .deps import latest_crawl

router = APIRouter(tags=["conversion-trust"])

CTA_WORDS = ("contact", "anfrage", "anfragen", "termin", "book", "buy", "kaufen", "beratung",
             "angebot", "subscribe", "get started", "jetzt", "anmelden")
STAGES = ("awareness", "consideration", "decision", "conversion")


def _records(db: Session, site_id: int, kind: str) -> list[SeoResearchRecord]:
    return db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site_id, SeoResearchRecord.kind == kind)
        .order_by(SeoResearchRecord.id.desc()).limit(1000)).all()


def _hostname(value: str | None) -> str | None:
    try:
        return (urlsplit(value or "").hostname or "").casefold() or None
    except ValueError:
        return None


@router.get("/sites/{site_id}/conversion-trust")
def conversion_trust(site_id: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    profiles = _records(db, site.id, "brand_profile")
    steps = _records(db, site.id, "funnel_step")
    proofs = _records(db, site.id, "trust_proof")
    by_page: dict[str, dict] = defaultdict(lambda: {"steps": [], "proofs": []})

    for record in steps:
        p = record.payload
        by_page[str(p["page_url"])]["steps"].append({
            "id": record.id, "stage": p["stage"], "action": p["action"],
            "friction": p.get("friction"), "form_fields": p.get("form_fields"),
            "action_url": p.get("action_url"), "evidence_url": p.get("evidence_url"),
            "source": record.source,
        })
    for record in proofs:
        p = record.payload
        by_page[str(p["page_url"])]["proofs"].append({
            "id": record.id, "claim": p["claim"], "proof_type": p.get("proof_type"),
            "proof_url": p.get("proof_url"),
            "link_recorded": bool(p.get("proof_url")),
            "genuineness_verified": False,
        })
    pages: dict[str, Page] = {}
    if crawl and by_page:
        pages = {p.url: p for p in db.scalars(select(Page).where(
            Page.crawl_id == crawl.id, Page.url.in_(set(by_page))).limit(1000))}
    reviews = []
    for url, info in sorted(by_page.items()):
        page = pages.get(url)
        text = (page.text or "").casefold()[:20000] if page else ""
        actions = info["steps"]
        recorded_stages = {str(a["stage"]) for a in actions}
        has_link = bool(actions) and all(a.get("action_url") for a in actions)
        reviews.append({
            "url": url, "crawl_found": page is not None, "title": page.title if page else None,
            "h1": page.h1 if page else None, "meta_description_present": bool(page.meta_description) if page else None,
            "cta_lexical_hint": any(word in text for word in CTA_WORDS) if page else None,
            "recorded_stages": sorted(recorded_stages),
            "missing_stages": [s for s in STAGES if s not in recorded_stages],
            "actions_have_target_url": has_link if actions else None,
            "steps": actions, "proofs": info["proofs"],
            "proofs_without_source": sum(not x["link_recorded"] for x in info["proofs"]),
            "requires_manual_review": [
                "Mobile visual hierarchy", "Form completion and validation errors",
                "Actual conversion events and consent", "Truth of testimonials and certifications",
                "Usability of the primary call-to-action",
            ],
        })
    brands = []
    for record in profiles:
        p = record.payload
        link = p.get("evidence_url")
        brands.append({
            "id": record.id, "brand_name": p["brand_name"], "positioning": p["positioning"],
            "offer": p["offer"], "audience": p.get("audience"), "tone": p.get("tone"),
            "evidence_url": link, "source_recorded": bool(link), "verified": False,
            "site_domain": _hostname(site.url),
        })
    return {
        "crawl_id": crawl.id if crawl else None, "pages": reviews, "brand_profiles": brands,
        "sources": {"funnel_steps": len(steps), "trust_proofs": len(proofs), "brand_profiles": len(profiles)},
        "method": "Submitted funnel and trust evidence plus weak crawler text signals. No visual CRO audit, "
                  "independent authenticity verification, premium-price score, or measured conversion lift.",
    }
