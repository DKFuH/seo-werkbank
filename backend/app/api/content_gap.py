"""GSC + last completed crawl: transparent content-gap research, no auto-publishing."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GscRow, Page, SeoWorkItem, User
from ..security.auth import current_user, get_site_for
from ..services.content_gap import analyze
from .deps import latest_crawl

router = APIRouter(tags=["content-gap"])


@router.get("/sites/{site_id}/content-gap")
def content_gap(
    site_id: int,
    days: int = Query(90, ge=7, le=365),
    min_impressions: int = Query(10, ge=1, le=100000),
    limit: int = Query(80, ge=1, le=150),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if crawl is None:
        return {"has_data": False, "reason": "Zuerst einen vollständigen Website-Crawl durchführen.",
                "crawl_id": None, "clusters": []}
    paired = [GscRow.site_id == site.id, GscRow.dataset == "query_page",
              GscRow.query.is_not(None), GscRow.page.is_not(None), GscRow.impressions > 0]
    sources = {source for (source,) in db.execute(select(GscRow.source).where(*paired).distinct())}
    source = "api" if "api" in sources else "csv" if "csv" in sources else None
    if source is None:
        return {"has_data": False,
                "reason": "GSC-Suchanfragen mit tatsächlich rankender URL (query_page) benötigt. "
                          "Getrennte Suchanfragen- und Seitenexporte dürfen nicht zugeordnet werden.",
                "crawl_id": crawl.id, "clusters": []}

    conditions = [*paired, GscRow.source == source]
    last_day = db.scalar(select(func.max(GscRow.day)).where(*conditions))
    undated = last_day is None
    if last_day is not None:
        first_day = last_day - timedelta(days=days - 1)
        conditions.append(GscRow.day.between(first_day, last_day))
    else:
        first_day = None
        conditions.append(GscRow.day.is_(None))

    wp = func.sum(case((GscRow.position.is_not(None), GscRow.position * GscRow.impressions), else_=0))
    wi = func.sum(case((GscRow.position.is_not(None), GscRow.impressions), else_=0))
    raw = db.execute(
        select(GscRow.query, GscRow.page, func.sum(GscRow.clicks),
               func.sum(GscRow.impressions), wp, wi)
        .where(*conditions).group_by(GscRow.query, GscRow.page)
        .order_by(func.sum(GscRow.impressions).desc()).limit(10001)
    ).all()
    truncated_pairs = len(raw) > 10000
    paired_rows = [
        {"query": query, "page": url, "clicks": clicks, "impressions": impressions,
         "position": weighted / weight if weight else None}
        for query, url, clicks, impressions, weighted, weight in raw[:10000]
    ]
    pages = list(db.scalars(
        select(Page).where(Page.crawl_id == crawl.id, Page.indexable.is_(True),
                           Page.status_code == 200, Page.is_html.is_(True))
        .order_by(Page.id).limit(4001)
    ))
    truncated_pages = len(pages) > 4000
    crawl_pages = [
        {"url": page.url, "title": page.title, "h1": page.h1,
         "headings": (page.data or {}).get("headings") or [],
         "description": page.meta_description, "text": page.text or ""}
        for page in pages[:4000]
    ]
    result = analyze(paired_rows, crawl_pages, min_impressions=min_impressions, max_results=limit)
    result.update(
        has_data=True, source=source, crawl_id=crawl.id,
        start_date=first_day.isoformat() if first_day else None,
        end_date=last_day.isoformat() if last_day else None,
        days=days, undated=undated, truncated_pairs=truncated_pairs,
        truncated_pages=truncated_pages,
        notes=[
            "Nur gemessene GSC-Daten: Impressionen sind keine monatlichen Suchvolumina.",
            "Google anonymisiert einige Suchanfragen und die API kann Ergebniszeilen begrenzen.",
            "Mehrere rankende URLs sind ein Kannibalisierungs-Indiz, kein Beweis.",
            "Ein fehlender Worttreffer beweist keine fehlende Suchintention oder fehlenden Inhalt.",
        ] + (["CSV-Daten ohne Datum: Der Zeitraumfilter gilt hier nicht."] if undated else [])
          + (["Maximal 10.000 Query-URL-Paare berücksichtigt."] if truncated_pairs else [])
          + (["Maximal 4.000 indexierbare HTML-Seiten berücksichtigt."] if truncated_pages else [])
          + (["API-Zeilen bevorzugt; CSV-Zeilen nicht doppelt addiert."] if source == "api" and "csv" in sources else []),
    )
    return result


class WorkFromGap(BaseModel):
    query: str = Field(min_length=2, max_length=700)
    target_url: str = Field(min_length=8, max_length=2048)
    action: str = Field(pattern=r"^(expand|new_candidate|review)$")


@router.post("/sites/{site_id}/content-gap/work", status_code=201)
def save_gap_work(site_id: int, body: WorkFromGap, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> dict:
    """Only create a reviewed *task*, never a page or publishing proposal."""
    site = get_site_for(db, user, site_id)
    from ..services.content_refresh import page_key
    from urllib.parse import urlsplit
    site_host = urlsplit(site.url).hostname
    target = urlsplit(body.target_url)
    if (target.scheme not in ("https", "http") or target.hostname != site_host or
            target.username or target.password or target.query or target.fragment):
        raise HTTPException(422, "Ziel-URL muss zur eigenen Website gehören")
    item = SeoWorkItem(
        site_id=site.id, kind="content", status="planned",
        title=("Content-Gap prüfen: " + body.query)[:300],
        target_url=page_key(body.target_url),
        notes=f"Herkunft: Content-Gap; vorgeschlagene Aktion: {body.action}. "
              "Suchintention, bestehende Inhalte und mögliche Kannibalisierung manuell prüfen. "
              "Keine automatische Erstellung oder Veröffentlichung.",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": item.status, "target_url": item.target_url,
            "remote_publication": False}
