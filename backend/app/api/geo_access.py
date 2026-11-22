"""Does a CDN or firewall treat AI crawlers differently from browsers?

robots.txt can allow every AI crawler while Cloudflare, Akamai or a WAF still blocks them by user agent. This
check requests one page of the user's own site once with a browser user agent and once per AI crawler user agent
and compares status, challenge pages and body size.

Limits: the requests come from this server's IP address, not from the crawler operators' networks. CDNs that
verify crawlers by IP (e.g. Cloudflare "verified bots") may treat the real crawler differently in both
directions. A block found here is a strong hint, not proof; "ok" does not prove the real crawler gets through.
Runs only on explicit user action and only against the selected site.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crawler.fetcher import Fetcher, FetchResult
from ..db import get_db
from ..models import User
from ..security.auth import current_user, get_site_for
from .diagnostics import _site_url

router = APIRouter(tags=["geo"])

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
_COMPAT = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; {agent}/1.0; +{url})"
# (token, operator, full user agent string as published by the operator, simplified where versions change often)
BOTS: list[tuple[str, str, str]] = [
    ("OAI-SearchBot", "OpenAI", _COMPAT.format(agent="OAI-SearchBot", url="https://openai.com/searchbot")),
    ("ChatGPT-User", "OpenAI", _COMPAT.format(agent="ChatGPT-User", url="https://openai.com/bot")),
    ("GPTBot", "OpenAI", _COMPAT.format(agent="GPTBot", url="https://openai.com/gptbot")),
    ("Claude-SearchBot", "Anthropic", _COMPAT.format(agent="Claude-SearchBot", url="claude-searchbot@anthropic.com")),
    ("Claude-User", "Anthropic", _COMPAT.format(agent="Claude-User", url="claude-user@anthropic.com")),
    ("ClaudeBot", "Anthropic", _COMPAT.format(agent="ClaudeBot", url="claudebot@anthropic.com")),
    ("PerplexityBot", "Perplexity", _COMPAT.format(agent="PerplexityBot", url="https://perplexity.ai/perplexitybot")),
    ("Perplexity-User", "Perplexity", _COMPAT.format(agent="Perplexity-User", url="https://perplexity.ai/perplexity-user")),
    ("Googlebot", "Google", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("Bingbot", "Microsoft", "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
    ("Applebot", "Apple", "Mozilla/5.0 (compatible; Applebot/0.1; +http://www.apple.com/go/applebot)"),
]
_CHALLENGE = re.compile(rb"cf-chl|challenge-platform|just a moment\.\.\.|attention required|captcha|_incapsula_|px-captcha|access denied", re.I)
BLOCK_STATUS = {401, 403, 406, 429, 451, 503}


class AccessIn(BaseModel):
    url: str | None = Field(None, max_length=2048)


def classify(baseline: FetchResult, res: FetchResult) -> tuple[str, str]:
    """(verdict, reason) for one bot response compared with the browser response."""
    if res.error and res.status is None:
        return "error", res.error
    if res.status in BLOCK_STATUS and baseline.status == 200:
        return "blocked", f"HTTP {res.status}, Browser bekommt 200"
    challenged = bool(_CHALLENGE.search(res.body[:200_000]))
    if challenged and not _CHALLENGE.search(baseline.body[:200_000]):
        return "challenge", "Prüfseite (Captcha/JavaScript-Challenge) statt Inhalt"
    if res.status != baseline.status:
        return "different", f"HTTP {res.status}, Browser bekommt {baseline.status}"
    if baseline.status == 200 and len(baseline.body) > 2000 and len(res.body) < 0.4 * len(baseline.body):
        return "different", f"nur {len(res.body)} statt {len(baseline.body)} Bytes"
    return "ok", f"HTTP {res.status}"


async def _fetch(url: str, ua: str) -> FetchResult:
    async with Fetcher(user_agent=ua, timeout_s=15, retries=0, concurrency=1, max_body_bytes=3_000_000) as fetcher:
        return await fetcher.fetch_following(url, max_body=3_000_000)


@router.post("/sites/{site_id}/geo/bot-access")
async def bot_access(site_id: int, body: AccessIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    url = _site_url(site, body.url or site.url)
    baseline = await _fetch(url, BROWSER_UA)
    results: list[dict] = []
    # Small batches: a dozen requests to one's own site, not a load test.
    for i in range(0, len(BOTS), 3):
        batch = BOTS[i:i + 3]
        responses = await asyncio.gather(*(_fetch(url, ua) for _, _, ua in batch))
        for (token, operator, _), res in zip(batch, responses, strict=True):
            verdict, reason = classify(baseline, res)
            results.append({"agent": token, "operator": operator, "status": res.status, "bytes": len(res.body),
                            "verdict": verdict, "reason": reason})
    blocked = [r["agent"] for r in results if r["verdict"] in ("blocked", "challenge")]
    return {
        "url": url, "browser": {"status": baseline.status, "bytes": len(baseline.body), "error": baseline.error},
        "items": results, "blocked": blocked,
        "method": "Abruf derselben Seite mit Browser- und Bot-Kennung von diesem Server aus. CDNs, die Crawler über ihre "
                  "IP-Adressen prüfen, können echte Crawler anders behandeln. Eine Sperre hier ist ein starker Hinweis, "
                  "kein Beweis; „ok“ garantiert nicht, dass der echte Crawler durchkommt.",
    }


# --------------------------------------------------------------------------- llms.txt draft from the last crawl
_SKIP_SEGMENTS = {"tag", "tags", "category", "kategorie", "author", "autor", "page", "seite", "feed", "search", "suche",
                  "wp-admin", "wp-content", "login", "cart", "warenkorb", "checkout", "kasse", "account", "konto"}
_LEGAL = {"impressum", "datenschutz", "datenschutzerklaerung", "agb", "privacy", "imprint", "terms", "cookie", "cookies"}


def _section(path: str) -> str | None:
    """First path segment as section name; None for pages that do not belong in llms.txt."""
    segments = [s for s in path.strip("/").split("/") if s]
    if not segments:
        return "Start"
    first = segments[0].lower()
    if first in _SKIP_SEGMENTS or any(s.isdigit() for s in segments):
        return None
    if first in _LEGAL:
        return "Rechtliches"
    return first.replace("-", " ").replace("_", " ").strip().capitalize() if len(segments) > 1 else "Wichtige Seiten"


def build_llms_txt(name: str, summary: str | None, pages: list[dict], *, per_section: int = 15, max_sections: int = 10) -> dict:
    """Markdown per llmstxt.org from crawled pages (url, title, meta_description, pagerank), best-linked first.

    Only data the crawl actually found; pages without a title are skipped. A draft to edit, not to publish blindly.
    """
    sections: dict[str, list[dict]] = {}
    for p in sorted(pages, key=lambda x: -(x.get("pagerank") or 0)):
        parts = urlsplit(p["url"])
        if parts.query or not (p.get("title") or "").strip():
            continue
        sec = _section(parts.path)
        if sec is None or sec == "Start":
            continue
        bucket = sections.setdefault(sec, [])
        if len(bucket) < per_section:
            bucket.append(p)
    topical = sorted((s for s in sections if s not in ("Wichtige Seiten", "Rechtliches")), key=lambda s: -len(sections[s]))
    order = ["Wichtige Seiten", *topical][:max_sections]
    if "Rechtliches" in sections:
        order.append("Rechtliches")
    lines = [f"# {name.strip()}", ""]
    if summary and summary.strip():
        lines += [f"> {' '.join(summary.split())}", ""]
    count = 0
    for sec in order:
        if sec not in sections:
            continue
        lines.append(f"## {sec}")
        for p in sections[sec]:
            title = " ".join(p["title"].split()).replace("[", "(").replace("]", ")")
            desc = " ".join((p.get("meta_description") or "").split())
            lines.append(f"- [{title}]({p['url']})" + (f": {desc}" if desc else ""))
            count += 1
        lines.append("")
    return {"text": "\n".join(lines).rstrip() + "\n", "pages": count, "sections": [s for s in order if s in sections],
            "summary_missing": not (summary and summary.strip())}


@router.get("/sites/{site_id}/geo/llms-txt-draft")
def llms_txt_draft(site_id: int, download: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import Page
    from .deps import download as download_response
    from .deps import latest_crawl

    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if crawl is None:
        raise HTTPException(422, "Zuerst einen Crawl abschließen")
    rows = db.execute(select(Page.url, Page.title, Page.meta_description, Page.pagerank, Page.depth).where(
        Page.crawl_id == crawl.id, Page.indexable.is_(True), Page.is_html.is_(True), Page.status_code == 200)
        .order_by(Page.pagerank.desc()).limit(2000)).all()
    pages = [{"url": u, "title": t, "meta_description": d, "pagerank": pr} for u, t, d, pr, _ in rows]
    start = next((p for p in pages if urlsplit(p["url"]).path in ("", "/")), None)
    result = build_llms_txt(site.name, start["meta_description"] if start else None, pages)
    if download:
        return download_response(result["text"].encode("utf-8"), "llms.txt", "text/markdown; charset=utf-8")
    return {**result, "crawl_id": crawl.id,
            "method": "Entwurf aus indexierbaren Seiten des letzten Crawls, gruppiert nach erstem Pfadabschnitt und sortiert "
                      "nach interner Verlinkung. Titel und Beschreibungen stammen aus den Seiten. Vor dem Veröffentlichen "
                      "kürzen und eine eigene Kurzbeschreibung prüfen."}
