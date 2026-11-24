"""Per-site technical diagnostics: browser consent trace, raw/rendered HTML, and image hints.

Only explicitly requested scans run. Third-party request *hostnames* are reported,
never full request URLs, cookies, query parameters, tokens or response bodies.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crawler.fetcher import Fetcher
from ..crawler.parser import parse_html
from ..crawler.render import Renderer, playwright_available
from ..db import get_db
from ..models import Link, Page, User
from ..security.auth import current_user, get_site_for
from ..services.tracking_audit import evaluate_consent_requests, inspect_html_tracking
from .deps import checked_url, latest_crawl

router = APIRouter(tags=["technical-diagnostics"])
CONSENT_LABELS = {
    "accept": re.compile(r"^(alle akzeptieren|alles akzeptieren|akzeptieren|accept all|allow all|agree to all)$", re.I),
    "reject": re.compile(r"^(alle ablehnen|alles ablehnen|ablehnen|reject all|deny all|refuse all)$", re.I),
}
TRACKER_WORDS = ("analytics", "collect", "pixel", "gtm", "matomo", "tagmanager", "doubleclick", "facebook", "clarity")


class ScanIn(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    choices: list[str] = Field(default_factory=lambda: ["initial"], min_length=1, max_length=3)


class TrackingAuditIn(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    run_browser_consent: bool = Field(default=False)
    choices: list[str] = Field(default_factory=lambda: ["initial", "accept", "reject"], min_length=1, max_length=3)



def _site_url(site, url: str) -> str:
    candidate = checked_url(url)
    own_host = (urlsplit(site.url).hostname or "").lower().removeprefix("www.")
    host = (urlsplit(candidate).hostname or "").lower().removeprefix("www.")
    if host != own_host:
        raise HTTPException(422, "Nur Seiten der ausgewählten Website sind für diese Diagnose zulässig")
    return candidate


def image_hints(images: list[dict]) -> list[dict]:
    """HTML markup heuristics: first image is NOT proven to be the real LCP element."""
    out = []
    for index, img in enumerate(images[:80]):
        if not isinstance(img, dict):
            continue
        warnings = []
        if not img.get("has_dimensions"):
            warnings.append("width/height fehlen im HTML (CSS-Größen nicht geprüft)")
        if index < 2 and str(img.get("loading") or "").lower() == "lazy":
            warnings.append("frühes Bild lädt lazy: möglichen LCP-Kandidaten prüfen")
        if warnings:
            out.append({"src": img.get("src"), "position_in_markup": index + 1,
                        "warnings": warnings, "confirmed_lcp": False})
    return out


async def _render_scan(url: str, user_agent: str, choice: str) -> dict:
    renderer = Renderer(user_agent=user_agent, allow_private=False, timeout_s=18)
    await renderer.start()
    try:
        page = await renderer._context.new_page()
        events = []
        start = asyncio.get_running_loop().time()

        def track(request):
            if len(events) >= 120:
                return
            host = (urlsplit(request.url).hostname or "").lower()
            site_host = (urlsplit(url).hostname or "").lower()
            events.append({"elapsed_ms": round((asyncio.get_running_loop().time() - start) * 1000),
                           "host": host[:255], "third_party": host != site_host,
                           "resource": str(request.resource_type)[:30],
                           "tracker_hint": any(k in host for k in TRACKER_WORDS)})

        page.on("request", track)
        action = "not_requested" if choice == "initial" else "not_found"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=18000)
            await page.wait_for_timeout(1200)
            if choice in CONSENT_LABELS:
                button = page.get_by_role("button", name=CONSENT_LABELS[choice]).first
                if await button.count() and await button.is_visible():
                    await button.click(timeout=3000)
                    action = "clicked_candidate_button"
                    await page.wait_for_timeout(1200)
            rendered = await renderer._safe_content(page)
            parsed = parse_html(rendered.encode("utf8"), url) if rendered else None
        except Exception:  # noqa: BLE001 - render failure must not leak page text/query
            parsed = None
            action = "scan_incomplete" if choice == "initial" else action
        finally:
            await page.close()
        third = [x for x in events if x["third_party"]]
        return {"choice": choice, "consent_action": action,
                "request_count_capped": len(events), "third_party_requests": len(third),
                "tracker_hint_requests": sum(x["tracker_hint"] for x in third),
                "requests": events, "rendered_words": parsed.word_count if parsed else None,
                "limits": "Requests include load activity; classification is only hostname-based. "
                          "A click is not proof that a CMP stored consent. No legal compliance verdict."}
    finally:
        await renderer.close()


@router.post("/sites/{site_id}/diagnostics/consent")
async def consent_scan(site_id: int, body: ScanIn, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    url = _site_url(site, body.url)
    if len(body.choices) != len(set(body.choices)) or any(x not in ("initial", "accept", "reject") for x in body.choices):
        raise HTTPException(422, "Erlaubt: initial, accept, reject – jeweils höchstens einmal")
    if not playwright_available():
        raise HTTPException(422, "Playwright/Chromium ist in dieser Installation nicht verfügbar")
    # No automated site interaction without an explicitly requested choice.
    result = [await _render_scan(url, "SEO-Werkbank-Diagnostic/1.0", choice) for choice in body.choices]
    return {"url": url, "samples": result, "method": "Isolated fresh browser contexts; clicks only for explicit accept/reject. "
            "Missing banners are recorded, not assumed. No tracker legality conclusions."}


@router.post("/sites/{site_id}/diagnostics/render")
async def render_comparison(site_id: int, body: ScanIn, user: User = Depends(current_user),
                            db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    url = _site_url(site, body.url)
    if not playwright_available():
        raise HTTPException(422, "Playwright/Chromium ist nicht verfügbar")
    async with Fetcher(timeout_s=18, retries=0, concurrency=1, max_body_bytes=2_000_000) as fetcher:
        response = await fetcher.fetch_following(url, max_body=2_000_000)
    if response.status != 200 or not response.is_html:
        raise HTTPException(422, "Die URL liefert keine abrufbare HTML-Seite")
    raw = parse_html(response.body, url, response.headers.get("content-type", ""))
    renderer = Renderer(user_agent="SEO-Werkbank-Diagnostic/1.0", allow_private=False, timeout_s=18)
    await renderer.start()
    try:
        html = await renderer.render(url)
    finally:
        await renderer.close()
    if not html:
        raise HTTPException(422, "Browser-Rendering fehlgeschlagen; kein Vergleich möglich")
    rendered = parse_html(html.encode("utf8"), url)
    return {"url": url, "raw": {"words": raw.word_count, "title": raw.title,
                               "headings": [x.get("text") for x in raw.headings[:10]], "links": len(raw.links)},
            "rendered": {"words": rendered.word_count, "title": rendered.title,
                         "headings": [x.get("text") for x in rendered.headings[:10]], "links": len(rendered.links)},
            "changes": {"words": rendered.word_count - raw.word_count,
                        "title_changed": rendered.title != raw.title,
                        "new_headings": [x.get("text") for x in rendered.headings[:10] if x not in raw.headings][:10]},
            "method": "Raw HTML versus one isolated Playwright render; not a simulation of a particular AI crawler."}


@router.get("/sites/{site_id}/diagnostics/images")
def images(site_id: int, limit: int = Query(200, ge=1, le=300),
           user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if crawl is None:
        return {"crawl_id": None, "pages": [], "method": "Erst einen Crawl ausführen"}
    pages = db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.is_html.is_(True))
                       .order_by(Page.id).limit(limit)).all()
    rows = [{"url": p.url, "issues": image_hints((p.data or {}).get("images") or [])}
            for p in pages]
    return {"crawl_id": crawl.id, "pages": [x for x in rows if x["issues"]],
            "method": "HTML image markup only. The first image is not proven to be LCP, no real viewport or CLS measurement."}


@router.post("/sites/{site_id}/diagnostics/tracking-audit")
async def tracking_audit(site_id: int, body: TrackingAuditIn, user: User = Depends(current_user),
                         db: Session = Depends(get_db)) -> dict:
    """Detailed deterministic audit of tracking tags, CMPs, duplicate configurations, and consent leakage."""
    site = get_site_for(db, user, site_id)
    url = _site_url(site, body.url)

    # 1. Fetch raw HTML for deterministic static tag inspection
    async with Fetcher(timeout_s=18, retries=0, concurrency=1, max_body_bytes=2_000_000) as fetcher:
        response = await fetcher.fetch_following(url, max_body=2_000_000)
    if response.status != 200 or not response.is_html:
        raise HTTPException(422, "Die angegebene URL liefert keine abrufbare HTML-Seite")

    html = response.body.decode("utf-8", "replace")
    static_report = inspect_html_tracking(html, url)

    # 2. Optional Playwright dynamic network consent trace
    browser_report = None
    if body.run_browser_consent:
        if not playwright_available():
            raise HTTPException(422, "Playwright/Chromium ist für den Browser-Consent-Trace nicht verfügbar")
        valid_choices = [c for c in body.choices if c in ("initial", "accept", "reject")]
        if not valid_choices:
            valid_choices = ["initial"]
        samples = [await _render_scan(url, "SEO-Werkbank-Diagnostic/1.0", choice) for choice in valid_choices]
        browser_report = {
            "samples": samples,
            "evaluation": evaluate_consent_requests(samples),
        }

    return {
        "url": url,
        "static_inspection": static_report,
        "browser_trace": browser_report,
        "playwright_supported": playwright_available(),
        "method": "Kombinierte statische HTML-Analyse (Tags, CMPs, Doppelungen, tel/mailto) "
                  "und optionaler isolierter Playwright-Netzwerk-Trace. Keine Rechtsberatung.",
    }


@router.get("/sites/{site_id}/diagnostics/tracking-overview")
def tracking_overview(site_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    """Aggregates tracking signals and contact links across pages from the latest crawl."""
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if crawl is None:
        return {
            "crawl_id": None,
            "pages_audited": 0,
            "summary": None,
            "conversion_links": {"tel_count": 0, "tel_examples": [], "mailto_count": 0, "mailto_examples": []},
            "method": "Erst einen Crawl ausführen",
        }

    pages = db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.is_html.is_(True))
                       .order_by(Page.id).limit(500)).all()

    # Aggregate tel: and mailto: links from crawl links
    tel_links = db.execute(
        select(Link.target_url, Page.url)
        .join(Page, Link.source_page_id == Page.id)
        .where(Page.crawl_id == crawl.id, Link.target_url.like("tel:%"))
        .limit(200)
    ).all()

    mailto_links = db.execute(
        select(Link.target_url, Page.url)
        .join(Page, Link.source_page_id == Page.id)
        .where(Page.crawl_id == crawl.id, Link.target_url.like("mailto:%"))
        .limit(200)
    ).all()

    return {
        "crawl_id": crawl.id,
        "pages_audited": len(pages),
        "conversion_links": {
            "tel_count": len(tel_links),
            "tel_examples": [{"target": t[0], "page": t[1]} for t in tel_links[:10]],
            "mailto_count": len(mailto_links),
            "mailto_examples": [{"target": m[0], "page": m[1]} for m in mailto_links[:10]],
        },
        "method": "Gecrawlte HTML-Seiten und interne Link-Ziele aus der Datenbank.",
    }

