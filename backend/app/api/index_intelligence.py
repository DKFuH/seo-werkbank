"""Quota-bounded Google index inspections and historical sitemap crawl diffs.

No indexation requests are sent. Only Google's actual Inspection API may
supply a Google index verdict. Sitemap history compares *observed crawl*
data rather than promising exhaustive XML sitemap coverage.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db, session_scope
from ..integrations import gsc
from ..jobs import JobLimitError, jobs
from ..models import Crawl, Page, SeoResearchRecord, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["index-intelligence"])


def _same_property(property_name: str, url: str) -> bool:
    target = urlsplit(url)
    if target.scheme not in ("http", "https") or target.username or target.password:
        return False
    host = (target.hostname or "").lower()
    if property_name.startswith("sc-domain:"):
        domain = property_name[10:].lower()
        return host == domain or host.endswith("." + domain)
    return url.startswith(property_name)


def _candidate_urls(db: Session, site_id: int, limit: int) -> list[dict]:
    crawls = list(db.scalars(
        select(Crawl).where(Crawl.site_id == site_id, Crawl.competitor_id.is_(None),
                            Crawl.status == "completed").order_by(Crawl.id.desc()).limit(2)
    ))
    if not crawls:
        return []
    current = list(db.scalars(select(Page).where(Page.crawl_id == crawls[0].id,
                                                    Page.indexable.is_(True), Page.status_code == 200,
                                                    Page.is_html.is_(True)).order_by(Page.id).limit(10001)))
    prior_hashes = {}
    if len(crawls) > 1:
        prior_hashes = {p.url: p.content_hash for p in db.scalars(
            select(Page).where(Page.crawl_id == crawls[1].id).limit(10001))}
    candidates = []
    for p in current[:10000]:
        if p.url not in prior_hashes:
            reason, priority = "Neu im letzten Crawl", 0
        elif p.content_hash and prior_hashes[p.url] and p.content_hash != prior_hashes[p.url]:
            reason, priority = "Content-Hash geändert", 1
        else:
            reason, priority = "Indexierbare Seite (Stichprobe)", 2
        candidates.append({"url": p.url, "reason": reason, "priority": priority, "inlinks": p.inlinks or 0})
    candidates.sort(key=lambda p: (p["priority"], -p["inlinks"], p["url"]))
    return candidates[:limit]


@router.get("/sites/{site_id}/index-intelligence/candidates")
def inspection_candidates(site_id: int, limit: int = Query(20, ge=1, le=100),
                          user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    return {"items": _candidate_urls(db, site.id, limit),
            "source": "last_two_completed_crawls", "note": "Priorität nach neuen/geänderten Crawl-Seiten; nicht Googles Indexstatus."}


class BatchIn(BaseModel):
    limit: int = Field(5, ge=1, le=10)


@router.post("/sites/{site_id}/index-intelligence/inspect", status_code=202)
async def inspect_batch(site_id: int, body: BatchIn, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if not site.gsc_property or not gsc.is_connected(db, user.id):
        raise HTTPException(400, "Google Search Console verbinden und Property auswählen")
    urls = [p for p in _candidate_urls(db, site.id, body.limit)
            if _same_property(site.gsc_property, p["url"])]
    if not urls:
        raise HTTPException(409, "Keine prüfbaren URLs aus dem letzten Crawl")
    property_name = site.gsc_property
    user_id = user.id
    site_id_owned = site.id

    async def work(ctx):
        checked = errors = 0
        for i, entry in enumerate(urls):
            ctx.update(i / len(urls), f"Google URL Inspection: {i + 1}/{len(urls)}")
            try:
                with session_scope() as work_db:
                    result = await gsc.inspect_url(work_db, user_id, property_name, entry["url"])
                index = result.get("index") or {}
                now = datetime.now(UTC).isoformat()
                with session_scope() as work_db:
                    work_db.add(SeoResearchRecord(
                        site_id=site_id_owned, kind="index_auto",
                        title=entry["url"][:300], source="google_url_inspection_api",
                        payload={"page_url": entry["url"], "checked_at": now,
                                 "verdict": index.get("verdict"),
                                 "coverage": index.get("coverageState"),
                                 "google_canonical": index.get("googleCanonical"),
                                 "last_google_crawl": index.get("lastCrawlTime"),
                                 "priority_reason": entry["reason"]},
                        notes="Google-Index-Snapshot, kein Live-Test oder Indexierungsantrag.",
                    ))
                checked += 1
            except gsc.GscError:
                errors += 1
                # Fail closed on quota/permission errors; do not retry aggressively.
                break
            await asyncio.sleep(0.25)
        ctx.update(1, "Batch abgeschlossen", force=True)
        return {"checked": checked, "errors": errors, "requested": len(urls),
                "note": "Nur Google-Index-Snapshots, keine Indexierungsanträge."}

    try:
        job_id = jobs.start("index_inspection", work, owner_id=user_id, site_id=site_id_owned)
    except JobLimitError as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"job_id": job_id, "queued": len(urls), "urls": urls,
            "note": "Manuell gestarteter, quotenbegrenzter Job. Google-API-Limits zusätzlich beachten."}


@router.get("/sites/{site_id}/index-intelligence/history")
def index_history(site_id: int, limit: int = Query(200, ge=1, le=500),
                  user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    records = list(db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "index_auto",
        SeoResearchRecord.source == "google_url_inspection_api"
    ).order_by(SeoResearchRecord.id.desc()).limit(5000)))
    previous: dict[str, str | None] = {}
    out = []
    for record in reversed(records):
        info = record.payload or {}
        url = str(info.get("page_url") or "")
        verdict = info.get("verdict")
        old = previous.get(url)
        out.append({"id": record.id, "url": url, "checked_at": info.get("checked_at"),
                    "verdict": verdict, "coverage": info.get("coverage"),
                    "previous_verdict": old, "index_loss_alert": old == "PASS" and verdict != "PASS",
                    "priority_reason": info.get("priority_reason"),
                    "google_canonical": info.get("google_canonical")})
        previous[url] = verdict
    out.reverse()
    return {"items": out[:limit], "total_stored": len(records),
            "note": "Echte Google-URL-Inspection-Antworten; PASS-Übergänge sind Prüfhinweise, nicht Echtzeitstatus."}


@router.get("/sites/{site_id}/index-intelligence/sitemap-history")
def sitemap_history(site_id: int, limit: int = Query(10, ge=2, le=20),
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawls = list(db.scalars(select(Crawl).where(
        Crawl.site_id == site.id, Crawl.competitor_id.is_(None), Crawl.status == "completed"
    ).order_by(Crawl.id.desc()).limit(limit)))
    snapshots = []
    for crawl in reversed(crawls):
        urls = {url for (url,) in db.execute(
            select(Page.url).where(Page.crawl_id == crawl.id, Page.in_sitemap.is_(True)).limit(20001)
        )}
        sm = (crawl.stats or {}).get("sitemap") or {}
        snapshots.append({"crawl_id": crawl.id,
                          "date": crawl.finished_at.isoformat() if crawl.finished_at else None,
                          "sitemap_url_count": sm.get("url_count", 0),
                          "with_lastmod": sm.get("with_lastmod", 0),
                          "observed_urls": len(urls),
                          "_urls": urls, "truncated": len(urls) > 20000})
    previous = None
    for snap in snapshots:
        urls = snap.pop("_urls")
        if previous is None:
            snap["added"] = snap["removed"] = []
            snap["compare_available"] = False
        else:
            snap["added"] = sorted(urls - previous)[:50]
            snap["removed"] = sorted(previous - urls)[:50]
            snap["added_count"] = len(urls - previous)
            snap["removed_count"] = len(previous - urls)
            snap["compare_available"] = True
        previous = urls
    return {"items": list(reversed(snapshots)), "note":
            "Historie der im Crawl beobachteten Sitemap-URLs, keine vollständige Google-Indexhistorie. "
            "Bei Crawl-Limit/Fehlern können Änderungen scheinbar entstehen."}
