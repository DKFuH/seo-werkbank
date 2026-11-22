"""Observed topic overlaps among crawled competitors; no fabricated search volumes or rankings."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Competitor, Crawl, Page, User
from ..security.auth import current_user, get_site_for
from ..text import term_counts

router = APIRouter(tags=["competitor-radar"])


def _terms(title: str | None, h1: str | None) -> set[str]:
    # Longish word pairs from titles and H1s; only lexical coverage, not semantic equivalence.
    return {t for t in term_counts((title or "") + " " + (h1 or ""), max_n=2)
            if " " in t and 7 <= len(t) <= 70}


@router.get("/sites/{site_id}/competitor-topic-radar")
def competitor_topic_radar(site_id: int, limit: int = Query(100, ge=1, le=300),
                           user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    own_crawl = db.scalar(select(Crawl).where(Crawl.site_id == site.id, Crawl.competitor_id.is_(None),
                                             Crawl.status == "completed").order_by(Crawl.id.desc()))
    if not own_crawl:
        return {"has_data": False, "reason": "Eigenen Crawl zuerst abschließen", "topics": []}
    own_pages = db.execute(select(Page.title, Page.h1).where(
        Page.crawl_id == own_crawl.id, Page.indexable.is_(True)).limit(5000))
    covered = set()
    for title, h1 in own_pages:
        covered.update(_terms(title, h1))

    data: dict[str, dict] = defaultdict(lambda: {"competitors": set(), "examples": [], "pages": set()})
    checked = 0
    for competitor in db.scalars(select(Competitor).where(Competitor.site_id == site.id).order_by(Competitor.id).limit(100)):
        crawl = db.scalar(select(Crawl).where(Crawl.site_id == site.id, Crawl.competitor_id == competitor.id,
                                            Crawl.status == "completed").order_by(Crawl.id.desc()))
        if not crawl:
            continue
        checked += 1
        pages = db.execute(select(Page.url, Page.title, Page.h1).where(
            Page.crawl_id == crawl.id, Page.indexable.is_(True)).limit(2500))
        for url, title, h1 in pages:
            for term in _terms(title, h1) - covered:
                item = data[term]
                item["competitors"].add(competitor.id)
                item["pages"].add(url)
                if len(item["examples"]) < 5 and not any(v["competitor_id"] == competitor.id for v in item["examples"]):
                    item["examples"].append({"competitor_id": competitor.id, "competitor": competitor.name,
                                             "url": url, "title": title or h1})
    topics = [
        {"term": term, "competitor_count": len(d["competitors"]), "observed_page_count": len(d["pages"]),
         "examples": d["examples"]}
        for term, d in data.items()
    ]
    topics.sort(key=lambda t: (-t["competitor_count"], -t["observed_page_count"], t["term"]))
    return {
        "has_data": checked > 0, "own_crawl_id": own_crawl.id,
        "competitors_with_crawl": checked, "topics": topics[:limit], "total_topics": len(topics),
        "method": "Wortpaare aus Titeln/H1 indexierbarer gecrawlter Wettbewerberseiten fehlen in Titeln/H1 "
                  "des eigenen Crawls. Dies ist eine lexikalische Recherchehilfe, kein Beweis für Themenlücken, "
                  "Keyword-Rankings, Suchvolumen, Nachfrage oder monetäre Chancen.",
    }
