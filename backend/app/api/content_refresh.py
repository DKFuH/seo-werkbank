"""Read-only GSC -> page-specific editorial opportunities."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GscRow, Page, User
from ..security.auth import current_user, get_site_for
from ..services.content_refresh import build_refresh_pages, page_key
from .deps import latest_crawl

router = APIRouter(tags=["content-refresh"])


@router.get("/sites/{site_id}/content-refresh")
def content_refresh(site_id: int, days: int = Query(28, ge=7, le=180),
                    min_impressions: int = Query(20, ge=1, le=100000),
                    limit: int = Query(50, ge=1, le=100),
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    base = [GscRow.site_id == site.id, GscRow.dataset == "query_page"]
    paired = [*base, GscRow.page.is_not(None), GscRow.query.is_not(None), GscRow.impressions > 0]
    # Prefer API pairs if available. NEVER add API and CSV copies together.
    sources = db.execute(select(GscRow.source, func.count()).where(*paired).group_by(GscRow.source)).all()
    found = {name: count for name, count in sources}
    source = "api" if found.get("api") else "csv" if found.get("csv") else None
    unpaired = db.scalar(select(func.count()).select_from(GscRow).where(*base,
        (GscRow.page.is_(None) | GscRow.query.is_(None)))) or 0
    if not source:
        return {"has_data": False, "reason": "GSC-Daten mit Suchanfrage UND URL benötigt. "
                "Einzelne Suchanfragen- oder Seiten-Exporte erlauben keine Zuordnung.", "unpaired_rows": unpaired,
                "pages": [], "total_pages": 0}

    source_pairs = [*paired, GscRow.source == source]
    last_day = db.scalar(select(func.max(GscRow.day)).where(*source_pairs))
    if last_day:
        first_day = last_day - timedelta(days=days - 1)
        source_pairs.append(GscRow.day.between(first_day, last_day))
    else:
        first_day = None
        source_pairs.append(GscRow.day.is_(None))

    weighted_position = func.sum(case((GscRow.position.is_not(None), GscRow.position * GscRow.impressions), else_=0))
    position_weight = func.sum(case((GscRow.position.is_not(None), GscRow.impressions), else_=0))
    rows = db.execute(select(GscRow.page, GscRow.query, func.sum(GscRow.clicks),
                             func.sum(GscRow.impressions), weighted_position, position_weight)
                      .where(*source_pairs).group_by(GscRow.page, GscRow.query)
                      .order_by(func.sum(GscRow.impressions).desc()).limit(10001)).all()
    clipped = len(rows) > 10000
    pairs = [{"page": page, "query": query, "clicks": clicks, "impressions": impressions,
              "position": weighted / weight if weight else None}
             for page, query, clicks, impressions, weighted, weight in rows[:10000]]

    crawl = latest_crawl(db, site.id)
    wanted = {page_key(r["page"]) for r in pairs}
    crawled: dict[str, dict] = {}
    if crawl:
        for p in db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.indexable.is_(True)).limit(10001)):
            key = page_key(p.url)
            if key in wanted:
                crawled[key] = {"title": p.title, "headings": (p.data or {}).get("headings", []), "text": p.text or ""}

    result = build_refresh_pages(pairs, crawled, min_impressions=min_impressions, limit=limit)
    result.update(has_data=True, source=source, start_date=first_day.isoformat() if first_day else None,
                  end_date=last_day.isoformat() if last_day else None, days=days, unpaired_rows=unpaired,
                  truncated=clipped, crawl_id=crawl.id if crawl else None,
                  notes=["Keine Zuordnung für GSC-Zeilen ohne gleichzeitige Suchanfrage und URL."
                         ] if unpaired else [])
    if clipped:
        result["notes"].append("Auf die 10.000 Query-URL-Paare mit den meisten Impressionen begrenzt.")
    if not last_day:
        result["notes"].append("CSV ohne Datum: Zeitraum ist nicht bekannt; Filter 'Tage' hat keine Wirkung.")
    if source == "api" and found.get("csv"):
        result["notes"].append("CSV-Duplikate nicht addiert; nur API-Daten ausgewertet.")
    return result
