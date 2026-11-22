"""Matomo Reporting API client.

Reads visits, channels, page and entry-page metrics, goals and devices for one Matomo site and joins the page
metrics with the latest crawl, so traffic can be read next to indexability, word count and internal links.
The token is sent in the POST body (Matomo's recommendation), never in the URL.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlsplit, urlunsplit

import httpx

from ..config import get_settings
from ..security.ssrf import validate_url


class MatomoError(RuntimeError):
    pass


def _endpoint(settings: dict) -> str:
    base = (settings.get("url") or "").strip().rstrip("/")
    if not base or not settings.get("token_auth"):
        raise MatomoError("Matomo ist nicht eingerichtet: URL und token_auth unter Einstellungen hinterlegen.")
    if base.endswith("index.php"):
        base = base[: -len("index.php")].rstrip("/")
    return validate_url(base + "/index.php", get_settings().allow_private_networks)


async def call(settings: dict, method: str, client: httpx.AsyncClient | None = None, **params) -> object:
    url = _endpoint(settings)
    data = {"module": "API", "method": method, "format": "JSON", "token_auth": settings["token_auth"],
            **{k: str(v) for k, v in params.items() if v is not None}}
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
    try:
        r = await client.post(url, data=data)
    except httpx.HTTPError as exc:
        raise MatomoError(f"Matomo nicht erreichbar: {exc}") from exc
    finally:
        if own:
            await client.aclose()
    if r.status_code != 200:
        raise MatomoError(f"Matomo antwortete mit HTTP {r.status_code}")
    try:
        out = r.json()
    except ValueError as exc:
        raise MatomoError("Matomo lieferte kein JSON (URL prüfen)") from exc
    if isinstance(out, dict) and out.get("result") == "error":
        raise MatomoError(f"Matomo: {out.get('message', 'Fehler')}")
    return out


async def sites(settings: dict) -> list[dict]:
    rows = await call(settings, "SitesManager.getSitesWithAtLeastViewAccess")
    return [{"id": int(s["idsite"]), "name": s.get("name"), "url": s.get("main_url")} for s in rows or []]


def match_site(matomo_sites: list[dict], site_url: str) -> int | None:
    host = (urlsplit(site_url).hostname or "").removeprefix("www.")
    for s in matomo_sites:
        if (urlsplit(s.get("url") or "").hostname or "").removeprefix("www.") == host:
            return s["id"]
    return None


def norm_url(url: str) -> str:
    """Comparable key: scheme-less host without www, path without trailing slash, no query or fragment."""
    p = urlsplit((url or "").strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    return urlunsplit(("", host, path, "", "")).lstrip("/")


def _num(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip().rstrip("%").replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return 0.0
    return 0.0


async def overview(settings: dict, id_site: int, days: int = 30) -> dict:
    """Aggregated Matomo data for the last ``days`` days (yesterday as the last day)."""
    rng = {"idSite": id_site, "period": "range", "date": f"last{days}"}
    async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
        def c(method, **p):
            return call(settings, method, client=client, **{**rng, **p})
        (summary, channels, pages, entries, engines, websites, goals_meta, goals, devices, daily) = await asyncio.gather(
            c("VisitsSummary.get"),
            c("Referrers.getReferrerType"),
            c("Actions.getPageUrls", flat=1, filter_limit=2000, filter_sort_column="nb_visits", filter_sort_order="desc"),
            c("Actions.getEntryPageUrls", flat=1, filter_limit=500, filter_sort_column="entry_nb_visits", filter_sort_order="desc"),
            c("Referrers.getSearchEngines", filter_limit=15),
            c("Referrers.getWebsites", filter_limit=20),
            call(settings, "Goals.getGoals", client=client, idSite=id_site),
            c("Goals.get"),
            c("DevicesDetection.getType"),
            call(settings, "VisitsSummary.get", client=client, idSite=id_site, period="day", date=f"last{days}"),
        )
    summary = summary if isinstance(summary, dict) else {}
    entry_by_url = {}
    for e in entries or []:
        if e.get("url"):
            entry_by_url[norm_url(e["url"])] = e
    page_rows = []
    for p in pages or []:
        if not p.get("url"):
            continue
        key = norm_url(p["url"])
        e = entry_by_url.get(key, {})
        page_rows.append({
            "url": p["url"], "key": key, "label": p.get("label"),
            "visits": int(_num(p.get("nb_visits"))), "hits": int(_num(p.get("nb_hits"))),
            "avg_time": round(_num(p.get("avg_time_on_page"))), "bounce_rate": _num(p.get("bounce_rate")),
            "exit_rate": _num(p.get("exit_rate")),
            "entries": int(_num(e.get("entry_nb_visits"))), "entry_bounce_rate": _num(e.get("bounce_rate")),
        })
    # the same normalised URL can appear several times (query strings): merge them
    merged: dict[str, dict] = {}
    for r in page_rows:
        m = merged.get(r["key"])
        if m is None:
            merged[r["key"]] = dict(r)
        else:
            for k in ("visits", "hits"):
                m[k] += r[k]
            m["entries"] = max(m["entries"], r["entries"])
    goal_names = {str(g.get("idgoal")): g.get("name") for g in (goals_meta or {}).values()} if isinstance(goals_meta, dict) else \
        {str(g.get("idgoal")): g.get("name") for g in (goals_meta or [])}
    goals = goals if isinstance(goals, dict) else {}
    per_goal = []
    for k, v in goals.items():
        if k.startswith("idgoal=") and isinstance(v, dict):
            gid = k.split("=", 1)[1]
            per_goal.append({"id": gid, "name": goal_names.get(gid, f"Ziel {gid}"), "conversions": int(_num(v.get("nb_conversions"))),
                             "rate": _num(v.get("conversion_rate"))})
    series = [{"date": d, "visits": int(_num((v or {}).get("nb_visits"))) if isinstance(v, dict) else 0}
              for d, v in (daily or {}).items()] if isinstance(daily, dict) else []
    return {
        "id_site": id_site, "days": days,
        "summary": {"visits": int(_num(summary.get("nb_visits"))), "visitors": int(_num(summary.get("nb_uniq_visitors"))),
                    "actions_per_visit": _num(summary.get("nb_actions_per_visit")), "avg_time": round(_num(summary.get("avg_time_on_site"))),
                    "bounce_rate": _num(summary.get("bounce_rate"))},
        "channels": [{"label": c.get("label"), "visits": int(_num(c.get("nb_visits")))} for c in channels or []],
        "search_engines": [{"label": c.get("label"), "visits": int(_num(c.get("nb_visits")))} for c in engines or []],
        "websites": [{"label": c.get("label"), "visits": int(_num(c.get("nb_visits")))} for c in websites or []],
        "devices": [{"label": c.get("label"), "visits": int(_num(c.get("nb_visits")))} for c in devices or [] if _num(c.get("nb_visits"))],
        "goals": {"conversions": int(_num(goals.get("nb_conversions"))), "rate": _num(goals.get("conversion_rate")), "per_goal": per_goal},
        "series": series,
        "pages": sorted(merged.values(), key=lambda r: r["visits"], reverse=True),
    }


def join_crawl(pages: list[dict], crawl_pages: list[dict]) -> dict:
    """Attach crawl facts to Matomo pages and list indexable crawled pages without a single visit."""
    by_key = {norm_url(p["url"]): p for p in crawl_pages}
    seen = set()
    rows = []
    for p in pages:
        c = by_key.get(p["key"])
        if c:
            seen.add(p["key"])
        rows.append({**p, "in_crawl": bool(c), "title": (c or {}).get("title"), "indexable": (c or {}).get("indexable"),
                     "word_count": (c or {}).get("word_count"), "inlinks": (c or {}).get("inlinks"),
                     "issues": (c or {}).get("issue_count"), "page_id": (c or {}).get("id")})
    no_traffic = [{"url": c["url"], "title": c.get("title"), "word_count": c.get("word_count"), "inlinks": c.get("inlinks"),
                   "page_id": c.get("id")}
                  for k, c in by_key.items() if k not in seen and c.get("indexable")]
    no_traffic.sort(key=lambda r: (r.get("inlinks") or 0))
    return {"pages": rows, "no_traffic": no_traffic}
