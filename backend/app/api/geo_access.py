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

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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
