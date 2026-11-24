"""Microsoft Bing Webmaster Tools API and the IndexNow protocol.

Bing Webmaster Tools (JSON API, API key from Bing Webmaster -> Settings -> API access):
query stats and crawl stats for a verified site. URL submission goes through IndexNow, which Microsoft recommends.

IndexNow notifies participating engines (Bing, Yandex, Seznam, Naver, Yep ...) about added, changed or
deleted URLs. A submission is a *hint*: it does not guarantee crawling or indexing. The key must be
published as a text file on the site itself, so this module also checks that file.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from ..config import get_settings
from ..security.ssrf import validate_url

BING_API = "https://ssl.bing.com/webmaster/api.svc/json/"
INDEXNOW_API = "https://api.indexnow.org/indexnow"
INDEXNOW_MAX_URLS = 10_000
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
DOCS = {
    "bing_api": "https://learn.microsoft.com/en-us/bingwebmaster/getting-access",
    "indexnow": "https://www.indexnow.org/documentation",
}
# IndexNow HTTP responses as documented on indexnow.org.
INDEXNOW_STATUS = {
    200: "OK – URLs übermittelt.",
    202: "Angenommen – Schlüsselprüfung steht noch aus.",
    400: "Ungültige Anfrage (Format).",
    403: "Schlüssel ungültig (Schlüsseldatei nicht gefunden oder Inhalt passt nicht).",
    422: "URLs gehören nicht zum Host oder Schlüssel passt nicht zum Schema.",
    429: "Zu viele Anfragen – später erneut versuchen.",
}


class BingError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- helpers
def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def site_root(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}/"


def parse_ms_date(value: object) -> str | None:
    """'/Date(1316156400000-0700)/' -> '2011-09-16' (UTC date)."""
    if not isinstance(value, str):
        return None
    m = re.search(r"/Date\((-?\d+)", value)
    if not m:
        return value[:10] or None
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=UTC).date().isoformat()


def match_site(bing_sites: list[dict], site_url: str) -> str | None:
    """Pick the Bing site whose host matches ours (ignoring www.); prefer verified, exact-scheme entries."""
    want = host_of(site_url).removeprefix("www.")
    scheme = urlsplit(site_url).scheme
    hits = [s for s in bing_sites if host_of(s["url"]).removeprefix("www.") == want]
    hits.sort(key=lambda s: (not s.get("verified"), urlsplit(s["url"]).scheme != scheme, host_of(s["url"]) != host_of(site_url)))
    return hits[0]["url"] if hits else None


def same_host_urls(urls: list[str], site_url: str) -> tuple[list[str], list[str]]:
    """Split into URLs on the site's host (http/https) and rejected ones; de-duplicated, order kept."""
    host = host_of(site_url)
    ok, rejected, seen = [], [], set()
    for raw in urls:
        u = (raw or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        p = urlsplit(u)
        (ok if p.scheme in ("http", "https") and (p.hostname or "").lower() == host else rejected).append(u)
    return ok, rejected


# ----------------------------------------------------------------------------- Bing Webmaster API
def _api_key(settings: dict) -> str:
    key = (settings.get("api_key") or "").strip()
    if not key:
        raise BingError("Bing Webmaster Tools ist nicht eingerichtet: API-Schlüssel unter Einstellungen hinterlegen.")
    return key


async def call(settings: dict, method: str, *, params: dict | None = None, body: dict | None = None,
               client: httpx.AsyncClient | None = None) -> object:
    # Bing's JSON API only accepts the key as query parameter; it is never logged or returned.
    query = {"apikey": _api_key(settings), **(params or {})}
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
    try:
        if body is None:
            r = await client.get(BING_API + method, params=query)
        else:
            r = await client.post(BING_API + method, params=query, json=body,
                                  headers={"Content-Type": "application/json; charset=utf-8"})
    except httpx.HTTPError as exc:
        raise BingError(f"Bing Webmaster API nicht erreichbar: {type(exc).__name__}") from exc
    finally:
        if own:
            await client.aclose()
    try:
        out = r.json() if r.content else {}
    except ValueError:
        out = {}
    if r.status_code != 200:
        msg = None  # Provider errors may echo credential-bearing URLs.
        if r.status_code in (401, 403):
            msg = msg or "API-Schlüssel ungültig oder ohne Zugriff auf diese Website"
        raise BingError(f"Bing Webmaster API: HTTP {r.status_code}" + (f" – {msg}" if msg else ""))
    return out.get("d") if isinstance(out, dict) and "d" in out else out


async def sites(settings: dict, client: httpx.AsyncClient | None = None) -> list[dict]:
    rows = await call(settings, "GetUserSites", client=client) or []
    return [{"url": s.get("Url"), "verified": bool(s.get("IsVerified"))} for s in rows if s.get("Url")]


def _queries(rows: list[dict]) -> list[dict]:
    """Aggregate Bing's weekly query rows per query (clicks/impressions summed, positions impression-weighted)."""
    agg: dict[str, dict] = {}
    for r in rows or []:
        q = r.get("Query") or ""
        imp, clk = int(r.get("Impressions") or 0), int(r.get("Clicks") or 0)
        a = agg.setdefault(q, {"query": q, "clicks": 0, "impressions": 0, "_pos": 0.0})
        a["clicks"] += clk
        a["impressions"] += imp
        a["_pos"] += float(r.get("AvgImpressionPosition") or 0) * imp
    out = []
    for a in agg.values():
        pos = a.pop("_pos")
        a["position"] = round(pos / a["impressions"], 1) if a["impressions"] else None
        a["ctr"] = round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0.0
        out.append(a)
    return sorted(out, key=lambda a: (-a["clicks"], -a["impressions"]))


def _crawl_stats(rows: list[dict]) -> list[dict]:
    out = [{"date": parse_ms_date(r.get("Date")), "crawled": r.get("CrawledPages"), "errors": r.get("CrawlErrors"),
            "in_index": r.get("InIndex"), "blocked_by_robots": r.get("BlockedByRobotsTxt"),
            "code_4xx": r.get("Code4xx"), "code_5xx": r.get("Code5xx")} for r in rows or []]
    return sorted((r for r in out if r["date"]), key=lambda r: r["date"])


async def overview(settings: dict, site_url: str, client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
    try:
        params = {"siteUrl": site_url}
        queries = await call(settings, "GetQueryStats", params=params, client=client)
        crawl = await call(settings, "GetCrawlStats", params=params, client=client)
    finally:
        if own:
            await client.aclose()
    q = _queries(queries or [])
    return {
        "site_url": site_url,
        "queries": q[:1000],
        "totals": {"clicks": sum(r["clicks"] for r in q), "impressions": sum(r["impressions"] for r in q), "queries": len(q)},
        "crawl_stats": _crawl_stats(crawl or []),
    }


# ----------------------------------------------------------------------------- IndexNow
def indexnow_key(settings: dict) -> str:
    key = (settings.get("key") or "").strip()
    if not key:
        raise BingError("Kein IndexNow-Schlüssel hinterlegt (Einstellungen → IndexNow).")
    if not KEY_RE.fullmatch(key):
        raise BingError("IndexNow-Schlüssel muss 8–128 Zeichen aus a–z, A–Z, 0–9 und '-' haben.")
    return key


def key_location(settings: dict, site_url: str) -> str:
    """Key file URL: the configured location if it is on the site's host, else <root>/<key>.txt."""
    key = indexnow_key(settings)
    custom = (settings.get("key_location") or "").strip()
    if custom:
        if host_of(custom) != host_of(site_url):
            raise BingError("Der Ort der Schlüsseldatei muss auf derselben Domain wie die Website liegen.")
        return custom
    return site_root(site_url) + f"{key}.txt"


async def check_key_file(settings: dict, site_url: str, client: httpx.AsyncClient | None = None) -> dict:
    key = indexnow_key(settings)
    location = key_location(settings, site_url)
    url = validate_url(location, get_settings().allow_private_networks)
    own = client is None
    client = client or httpx.AsyncClient(timeout=20, follow_redirects=False)
    try:
        r = await client.get(url, headers={"User-Agent": "SEO-Werkbank IndexNow-Check"})
    except httpx.HTTPError as exc:
        return {"key_location": location, "ok": False, "status_code": None, "message": f"Nicht erreichbar: {type(exc).__name__}"}
    finally:
        if own:
            await client.aclose()
    if r.status_code != 200:
        hint = " (Weiterleitung – die Datei muss direkt erreichbar sein)" if 300 <= r.status_code < 400 else ""
        return {"key_location": location, "ok": False, "status_code": r.status_code, "message": f"HTTP {r.status_code}{hint}"}
    ok = r.text.strip() == key
    return {"key_location": location, "ok": ok, "status_code": 200,
            "message": "Schlüsseldatei gefunden und gültig." if ok else "Datei gefunden, Inhalt entspricht nicht dem Schlüssel."}


async def indexnow_submit(settings: dict, site_url: str, urls: list[str], client: httpx.AsyncClient | None = None) -> dict:
    key = indexnow_key(settings)
    body = {"host": host_of(site_url), "key": key, "keyLocation": key_location(settings, site_url), "urlList": urls[:INDEXNOW_MAX_URLS]}
    own = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False)
    try:
        r = await client.post(INDEXNOW_API, json=body, headers={"Content-Type": "application/json; charset=utf-8"})
    except httpx.HTTPError as exc:
        raise BingError(f"IndexNow nicht erreichbar: {type(exc).__name__}") from exc
    finally:
        if own:
            await client.aclose()
    return {"status_code": r.status_code, "ok": r.status_code in (200, 202), "submitted": len(body["urlList"]),
            "message": INDEXNOW_STATUS.get(r.status_code, f"Unerwartete Antwort HTTP {r.status_code}")}

# Microsoft JSON API read operations, kept separate from Google metrics.
READ_OPERATIONS = {
    "traffic": ("GetRankAndTrafficStats", None),
    "pages": ("GetPageStats", None),
    "query_pages": ("GetQueryPageStats", "query"),
    "url_info": ("GetUrlInfo", "url"),
    "sitemaps": ("GetFeeds", None),
    "backlink_counts": ("GetLinkCounts", None),
    "backlinks": ("GetUrlLinks", "url"),
    "crawl_settings": ("GetCrawlSettings", None),
    "submission_quota": ("GetUrlSubmissionQuota", None),
    "page_queries": ("GetPageQueryStats", "page"),
}


async def read_intelligence(settings: dict, site_url: str, operation: str, *,
                            keyword: str | None = None, url: str | None = None,
                            client: httpx.AsyncClient | None = None) -> dict:
    if operation not in READ_OPERATIONS:
        raise BingError("Nicht unterstützte Bing-Operation.")
    method, required = READ_OPERATIONS[operation]
    params = {"siteUrl": site_url}
    if required == "query":
        if not keyword or not keyword.strip():
            raise BingError("Suchanfrage erforderlich.")
        params["query"] = keyword.strip()
    elif required in ("url", "page"):
        if not url or not same_host_urls([url], site_url)[0]:
            raise BingError("URL derselben Website erforderlich.")
        params[required] = url
    if operation in ("backlink_counts", "backlinks"):
        params["page"] = 0
    data = await call(settings, method, params=params, client=client)
    return {"provider": "bing", "operation": operation, "site_url": site_url,
            "data": data, "retrieved_at": datetime.now(UTC).isoformat()}
