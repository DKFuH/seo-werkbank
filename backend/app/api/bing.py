"""Bing Webmaster Tools data and IndexNow submissions per site."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from ..db import get_db
from ..integrations import bing
from ..models import Crawl, Page, SearchProviderSnapshot, User
from ..security.auth import current_user, get_site_for
from ..security.ssrf import UnsafeURLError
from ..services.bing_content import analyze_sample, normalize_page_queries
from ..services.settings_store import get_setting

BingOperation = Literal[
    "traffic", "pages", "query_pages", "url_info", "sitemaps",
    "backlink_counts", "backlinks", "crawl_settings", "submission_quota", "page_queries",
]

router = APIRouter(tags=["bing"])


def _bad(exc: Exception) -> HTTPException:
    return HTTPException(400, str(exc))


# ----------------------------------------------------------------------------- Bing Webmaster Tools
@router.get("/bing/sites")
async def bing_sites(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return {"sites": await bing.sites(get_setting(db, "bing"))}
    except bing.BingError as exc:
        raise _bad(exc) from exc


@router.get("/sites/{site_id}/bing/overview")
async def bing_overview(site_id: int, site_url: str | None = Query(None, max_length=2048),
                        user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "bing")
    try:
        if not site_url:
            site_url = bing.match_site(await bing.sites(settings), site.url)
            if site_url is None:
                raise HTTPException(400, "Keine Website mit gleicher Domain in Bing Webmaster Tools gefunden; bitte Website wählen.")
        registered = [s for s in await bing.sites(settings) if s.get("verified")]
        if site_url != bing.match_site(registered, site.url):
            raise HTTPException(403, "Bing-Property gehört nicht zur gewählten Website.")
        return await bing.overview(settings, site_url)
    except bing.BingError as exc:
        raise _bad(exc) from exc



# Read-only, documented JSON operations. Never accept arbitrary provider methods.
@router.get("/sites/{site_id}/bing/intelligence/{operation}")
async def bing_intelligence(
    site_id: int,
    operation: BingOperation,
    keyword: str | None = Query(None, max_length=512),
    url: str | None = Query(None, max_length=2048),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "bing")
    try:
        registered = [s for s in await bing.sites(settings) if s.get("verified")]
        site_url = bing.match_site(registered, site.url)
        if site_url is None:
            raise HTTPException(400, "Keine verifizierte Bing-Website gefunden.")
        result = await bing.read_intelligence(settings, site_url, operation, keyword=keyword, url=url)
        return result
    except bing.BingError as exc:
        raise _bad(exc) from exc



@router.get("/sites/{site_id}/bing/content-analysis")
async def bing_content_analysis(
    site_id: int, weeks: int = Query(4, ge=2, le=12),
    page_limit: int = Query(10, ge=1, le=25),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    """Bounded, on-demand sample of actual Bing page-query pairs."""
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "bing")
    crawls = _completed_crawls(db, site.id)
    if not crawls:
        return {"provider": "bing", "has_data": False, "reason": "Website-Crawl erforderlich."}
    try:
        site_url = bing.match_site([s for s in await bing.sites(settings) if s.get("verified")], site.url)
        if site_url is None:
            raise HTTPException(400, "Keine verifizierte Bing-Website gefunden.")
        ranking = await bing.read_intelligence(settings, site_url, "pages")
        raw = ranking.get("data")
        if not isinstance(raw, list):
            raise bing.BingError("Unerwartetes Bing-Seitendatenformat.")
        totals = {}
        for row in raw:
            if isinstance(row, dict) and isinstance(row.get("Query"), str):
                page = row["Query"]
                if bing.same_host_urls([page], site_url)[0]:
                    totals[page] = totals.get(page, 0) + int(row.get("Impressions") or 0)
        targets = sorted(totals, key=lambda p: (-totals[p], p))[:page_limit]
        rows = []
        for page in targets:
            response = await bing.read_intelligence(
                settings, site_url, "page_queries", url=page,
            )
            data = response.get("data")
            if not isinstance(data, list):
                raise bing.BingError("Unerwartetes Bing-Query-Datenformat.")
            rows.extend(normalize_page_queries(page, data))
        pages = list(db.scalars(select(Page).options(undefer(Page.text)).where(
            Page.crawl_id == crawls[0].id, Page.indexable.is_(True),
            Page.is_html.is_(True), Page.status_code == 200).order_by(Page.id).limit(4000)))
        metadata = [{"url": p.url, "title": p.title, "h1": p.h1,
                     "headings": (p.data or {}).get("headings") or [],
                     "text": p.text or "", "description": p.meta_description} for p in pages]
        result = analyze_sample(rows, metadata, weeks=weeks)
        return {**result, "sampled_pages": targets, "available_pages": len(totals),
                "crawl_id": crawls[0].id}
    except (bing.BingError, ValueError, TypeError) as exc:
        raise _bad(exc) from exc


# ----------------------------------------------------------------------------- IndexNow
def _completed_crawls(db: Session, site_id: int) -> list[Crawl]:
    return list(db.scalars(select(Crawl).where(Crawl.site_id == site_id, Crawl.competitor_id.is_(None), Crawl.status == "completed")
                           .order_by(Crawl.id.desc()).limit(2)))


def _candidates(db: Session, site_id: int) -> dict:
    """URLs for IndexNow since the previous crawl: new, content changed, and removed (404/410 now, indexable before)."""
    crawls = _completed_crawls(db, site_id)
    if not crawls:
        return {"crawl_id": None, "previous_crawl_id": None, "new": [], "changed": [], "removed": []}
    latest = crawls[0]
    current = {u: h for u, h in db.execute(select(Page.url, Page.content_hash).where(
        Page.crawl_id == latest.id, Page.is_html.is_(True), Page.indexable.is_(True)))}
    if len(crawls) < 2:
        return {"crawl_id": latest.id, "previous_crawl_id": None, "new": [], "changed": [], "removed": []}
    previous = {u: h for u, h in db.execute(select(Page.url, Page.content_hash).where(Page.crawl_id == crawls[1].id))}
    was_indexable = {u for (u,) in db.execute(select(Page.url).where(
        Page.crawl_id == crawls[1].id, Page.is_html.is_(True), Page.indexable.is_(True)))}
    gone = {u for (u,) in db.execute(select(Page.url).where(Page.crawl_id == latest.id, Page.status_code.in_((404, 410))))}
    removed = sorted(was_indexable & gone)
    new = sorted(u for u in current if u not in previous)
    changed = sorted(u for u, h in current.items() if u in previous and h and previous[u] and h != previous[u])
    return {"crawl_id": latest.id, "previous_crawl_id": crawls[1].id, "new": new, "changed": changed, "removed": removed}


@router.get("/sites/{site_id}/indexnow/status")
async def indexnow_status(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "indexnow")
    cand = _candidates(db, site.id)
    base = {"configured": bool((settings.get("key") or "").strip()), "docs": bing.DOCS["indexnow"],
            "candidates": {**cand, "new": cand["new"][:500], "changed": cand["changed"][:500], "removed": cand["removed"][:500],
                           "new_count": len(cand["new"]), "changed_count": len(cand["changed"]),
                           "removed_count": len(cand["removed"])}}
    if not base["configured"]:
        return {**base, "key_file": None}
    try:
        return {**base, "key_file": await bing.check_key_file(settings, site.url)}
    except (bing.BingError, UnsafeURLError) as exc:
        return {**base, "key_file": {"ok": False, "status_code": None, "key_location": None, "message": str(exc)}}


class IndexNowIn(BaseModel):
    source: Literal["manual", "new", "changed", "removed", "new_changed", "all"] = "manual"
    urls: list[str] = Field(default_factory=list, max_length=bing.INDEXNOW_MAX_URLS)


@router.post("/sites/{site_id}/indexnow/submit")
async def indexnow_submit(site_id: int, body: IndexNowIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "indexnow")
    if body.source == "manual":
        urls = body.urls
    else:
        cand = _candidates(db, site.id)
        urls = ((cand["new"] if body.source in ("new", "new_changed", "all") else [])
                + (cand["changed"] if body.source in ("changed", "new_changed", "all") else [])
                + (cand["removed"] if body.source in ("removed", "all") else []))
    ok, rejected = bing.same_host_urls(urls, site.url)
    if not ok:
        raise HTTPException(422, "Keine URLs dieser Website zum Melden." + (f" {len(rejected)} URL(s) gehören zu einem anderen Host." if rejected else ""))
    if len(ok) > bing.INDEXNOW_MAX_URLS:
        raise HTTPException(422, f"Höchstens {bing.INDEXNOW_MAX_URLS} URLs je Meldung.")
    try:
        result = await bing.indexnow_submit(settings, site.url, ok)
    except bing.BingError as exc:
        raise _bad(exc) from exc
    return {**result, "rejected": rejected[:50], "rejected_count": len(rejected)}


class BingSnapshotRequest(BaseModel):
    operation: BingOperation
    keyword: str | None = Field(None, max_length=512)
    url: str | None = Field(None, max_length=2048)


@router.post("/sites/{site_id}/bing/snapshots", status_code=201)
async def capture_bing_snapshot(site_id: int, body: BingSnapshotRequest,
                                user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "bing")
    try:
        property_url = bing.match_site([s for s in await bing.sites(settings) if s.get("verified")], site.url)
        if property_url is None:
            raise HTTPException(400, "Keine verifizierte Bing-Website gefunden.")
        payload = await bing.read_intelligence(settings, property_url, body.operation,
                                               keyword=body.keyword, url=body.url)
        if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 2_000_000:
            raise HTTPException(413, "Bing-Antwort zu groß für einen Snapshot.")
        snapshot = SearchProviderSnapshot(site_id=site.id, provider="bing",
                                          operation=body.operation, property_url=property_url,
                                          parameters={"keyword": body.keyword, "url": body.url}, payload=payload)
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return {"id": snapshot.id, "provider": snapshot.provider, "operation": snapshot.operation}
    except bing.BingError as exc:
        raise _bad(exc) from exc


@router.get("/sites/{site_id}/bing/snapshots")
def list_bing_snapshots(site_id: int, limit: int = Query(25, ge=1, le=100),
                       user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    rows = db.scalars(select(SearchProviderSnapshot).where(
        SearchProviderSnapshot.site_id == site.id, SearchProviderSnapshot.provider == "bing"
    ).order_by(SearchProviderSnapshot.id.desc()).limit(limit))
    return {"items": [{"id": r.id, "provider": r.provider, "operation": r.operation,
                       "property_url": r.property_url, "parameters": r.parameters,
                       "created_at": r.created_at.isoformat()} for r in rows]}


@router.get("/sites/{site_id}/bing/snapshots/{snapshot_id}")
def get_bing_snapshot(site_id: int, snapshot_id: int,
                      user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    row = db.scalar(select(SearchProviderSnapshot).where(
        SearchProviderSnapshot.site_id == site.id, SearchProviderSnapshot.provider == "bing",
        SearchProviderSnapshot.id == snapshot_id))
    if row is None:
        raise HTTPException(404, "Snapshot nicht gefunden.")
    return {"id": row.id, "provider": row.provider, "operation": row.operation,
            "created_at": row.created_at.isoformat(), "payload": row.payload}
