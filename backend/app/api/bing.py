"""Bing Webmaster Tools data and IndexNow submissions per site."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..integrations import bing
from ..models import Crawl, Page, User
from ..security.auth import current_user, get_site_for
from ..security.ssrf import UnsafeURLError
from ..services.settings_store import get_setting

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
        return await bing.overview(settings, site_url)
    except bing.BingError as exc:
        raise _bad(exc) from exc


# ----------------------------------------------------------------------------- IndexNow
def _completed_crawls(db: Session, site_id: int) -> list[Crawl]:
    return list(db.scalars(select(Crawl).where(Crawl.site_id == site_id, Crawl.competitor_id.is_(None), Crawl.status == "completed")
                           .order_by(Crawl.id.desc()).limit(2)))


def _candidates(db: Session, site_id: int) -> dict:
    """Indexable HTML URLs of the latest crawl that are new or whose content hash changed since the previous crawl."""
    crawls = _completed_crawls(db, site_id)
    if not crawls:
        return {"crawl_id": None, "previous_crawl_id": None, "new": [], "changed": []}
    latest = crawls[0]
    current = {u: h for u, h in db.execute(select(Page.url, Page.content_hash).where(
        Page.crawl_id == latest.id, Page.is_html.is_(True), Page.indexable.is_(True)))}
    if len(crawls) < 2:
        return {"crawl_id": latest.id, "previous_crawl_id": None, "new": [], "changed": []}
    previous = {u: h for u, h in db.execute(select(Page.url, Page.content_hash).where(Page.crawl_id == crawls[1].id))}
    new = sorted(u for u in current if u not in previous)
    changed = sorted(u for u, h in current.items() if u in previous and h and previous[u] and h != previous[u])
    return {"crawl_id": latest.id, "previous_crawl_id": crawls[1].id, "new": new, "changed": changed}


@router.get("/sites/{site_id}/indexnow/status")
async def indexnow_status(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "indexnow")
    cand = _candidates(db, site.id)
    base = {"configured": bool((settings.get("key") or "").strip()), "docs": bing.DOCS["indexnow"],
            "candidates": {**cand, "new": cand["new"][:500], "changed": cand["changed"][:500],
                           "new_count": len(cand["new"]), "changed_count": len(cand["changed"])}}
    if not base["configured"]:
        return {**base, "key_file": None}
    try:
        return {**base, "key_file": await bing.check_key_file(settings, site.url)}
    except (bing.BingError, UnsafeURLError) as exc:
        return {**base, "key_file": {"ok": False, "status_code": None, "key_location": None, "message": str(exc)}}


class IndexNowIn(BaseModel):
    source: Literal["manual", "new", "changed", "new_changed"] = "manual"
    urls: list[str] = Field(default_factory=list, max_length=bing.INDEXNOW_MAX_URLS)


@router.post("/sites/{site_id}/indexnow/submit")
async def indexnow_submit(site_id: int, body: IndexNowIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "indexnow")
    if body.source == "manual":
        urls = body.urls
    else:
        cand = _candidates(db, site.id)
        urls = (cand["new"] if body.source in ("new", "new_changed") else []) + (cand["changed"] if body.source in ("changed", "new_changed") else [])
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
