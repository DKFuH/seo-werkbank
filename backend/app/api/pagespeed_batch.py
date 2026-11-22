"""Bounded PageSpeed batches and measured field-vitals overview.

All results are stored as ordinary PageSpeedResult records. Site summaries
never conflate PSI field data with Lighthouse simulated lab measurements.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db, session_scope
from ..integrations import pagespeed as psi
from ..jobs import jobs
from ..models import Crawl, Page, PageSpeedResult, User
from ..security.auth import current_user, get_site_for
from ..services.settings_store import get_setting

router = APIRouter(tags=["pagespeed-batch"])


class BatchIn(BaseModel):
    limit: int = Field(5, ge=1, le=10)
    strategy: str = Field("mobile", pattern="^(mobile|desktop)$")


def measured_summary(rows: list[PageSpeedResult]) -> dict:
    """Latest per-URL field value, not the average of multiple lab runs."""
    latest = {}
    for r in rows:
        latest.setdefault(r.url, r)
    metrics = ("LCP", "INP", "CLS")
    counts = {k: Counter() for k in metrics}
    coverage = Counter()
    for record in latest.values():
        field = (record.data or {}).get("field", {})
        for metric in metrics:
            item = field.get(metric)
            if item and item.get("p75") is not None:
                coverage[metric] += 1
                counts[metric][item.get("rating") or "unknown"] += 1
    return {"sampled_urls": len(latest), "field_coverage": dict(coverage),
            "field_ratings_by_url": {k: dict(v) for k, v in counts.items()},
            "method": "Latest per-URL Chrome UX Report field p75 per metric, where available; no aggregate "
                      "site-wide CrUX origin metric and no arithmetic average of lab Lighthouse values."}


@router.post("/sites/{site_id}/pagespeed/batch", status_code=202)
async def batch_pagespeed(site_id: int, body: BatchIn, user: User = Depends(current_user),
                          db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = db.scalar(select(Crawl).where(Crawl.site_id == site.id, Crawl.competitor_id.is_(None),
                                         Crawl.status == "completed").order_by(Crawl.id.desc()))
    if crawl is None:
        raise HTTPException(400, "Zuerst einen Crawl abschließen")
    # Only indexable HTML from this user's most recent crawl, deduplicated by URL.
    pages = db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.is_html.is_(True),
                                         Page.indexable.is_(True), Page.status_code == 200)
                       .order_by(Page.pagerank.desc(), Page.id.asc()).limit(100)).all()
    urls = []
    for p in pages:
        if p.url not in urls and urlsplit(p.url).scheme in ("http", "https"):
            urls.append(p.url)
        if len(urls) >= body.limit:
            break
    if not urls:
        raise HTTPException(400, "Keine indexierbaren HTML-Seiten im letzten Crawl")
    # Freeze the API key for the job; never pass secret data into stored job results.
    api_key = get_setting(db, "pagespeed").get("api_key") or ""
    sid, uid = site.id, user.id

    async def task(ctx):
        passed, failed = 0, 0
        for i, url in enumerate(urls):
            ctx.update(i / len(urls), f"PageSpeed {i + 1}/{len(urls)}", force=True)
            try:
                result = await psi.run_psi(url, body.strategy, api_key)
                with session_scope() as session:
                    session.add(PageSpeedResult(site_id=sid, owner_id=uid, url=url,
                                strategy=body.strategy, source=result["source"], data=result))
                passed += 1
            except Exception:
                # Do not expose token-bearing exception messages in persisted job results.
                failed += 1
            if i + 1 < len(urls):
                await asyncio.sleep(1.5)  # basic request spacing; no unlimited parallel API fan-out
        return {"tested": len(urls), "succeeded": passed, "failed": failed, "strategy": body.strategy}

    return {"job_id": jobs.start("pagespeed_batch", task, owner_id=uid, site_id=sid),
            "queued_urls": len(urls), "source": "psi_api"}


@router.get("/sites/{site_id}/pagespeed/summary")
def pagespeed_summary(site_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    rows = db.scalars(select(PageSpeedResult).where(PageSpeedResult.site_id == site.id,
                     PageSpeedResult.owner_id == user.id, PageSpeedResult.source == "psi_api",
                     PageSpeedResult.strategy == "mobile").order_by(PageSpeedResult.id.desc()).limit(500)).all()
    return measured_summary(rows)
