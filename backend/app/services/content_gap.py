"""Conservative, reproducible content-gap candidates from *paired* GSC and crawl data.

No semantics/volume estimates, ranking prediction, automatic page creation or
claims of actual cannibalisation. Every recommendation requires editorial review.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .content_refresh import page_key

# These words are too generic to imply an independent search intent.
STOPWORDS = frozenset("""
der die das den dem des ein eine einer eines und oder im in am an auf aus für fuer
von mit ohne zu zur zum bei nach vor welche welcher welches wie was warum wann
wo ist sind wird werden kann können koennen sollte man als beim durch über ueber
the and for with from what how best why where a of
""".split())
_TOKEN = re.compile(r"[a-z0-9äöüß]+", re.I)
MAX_CANDIDATES = 800
MAX_PAGES = 4000
MAX_PAIRS = 10000


def words(value: str) -> set[str]:
    return {t for t in _TOKEN.findall((value or "").lower()) if len(t) >= 3 and t not in STOPWORDS}


def overlap(query: set[str], text: set[str]) -> float:
    """Query coverage is a *lexical proxy*; no semantic verification implied."""
    return len(query & text) / len(query) if query else 0.0


def _page_metadata(p: dict) -> dict:
    return {"url": p["url"], "title": p.get("title") or "", "h1": p.get("h1") or "",
            "description": p.get("description") or "",
            "headings": p.get("headings") or [],
            "text": (p.get("text") or "")[:20000]}


def analyze(pairs: list[dict], pages: list[dict], *,
            min_impressions: int = 10, max_results: int = 80) -> dict:
    """Return documented evidence for each query, clustered only by near-token overlap.

    Pairs *already* aggregated by a site-scoped SQL query for the chosen period.
    A query may rank on many URLs; the strongest URL is the one with most
    impressions, not necessarily the best content target.
    """
    available = {}
    indexed = []
    for p in pages[:MAX_PAGES]:
        url = page_key(p.get("url"))
        if not url:
            continue
        meta = _page_metadata(p)
        primary = words(" ".join([meta["title"], meta["h1"],
                                 " ".join(h.get("text", "") for h in meta["headings"] if isinstance(h, dict))]))
        body = words(meta["text"])
        meta["title_terms"] = primary
        meta["body_terms"] = body
        available[url] = meta
        indexed.append(meta)

    queries: dict[str, dict] = {}
    for row in pairs[:MAX_PAIRS]:
        key = " ".join((row.get("query") or "").casefold().split())
        url = page_key(row.get("page"))
        impressions = float(row.get("impressions") or 0)
        if not key or not url or impressions <= 0:
            continue
        bucket = queries.setdefault(key, {"query": key, "clicks": 0.0,
                                           "impressions": 0.0, "weighted": 0.0, "weight": 0.0,
                                           "urls": defaultdict(lambda: {"impressions": 0.0, "clicks": 0.0})})
        bucket["clicks"] += float(row.get("clicks") or 0)
        bucket["impressions"] += impressions
        if row.get("position") is not None:
            bucket["weighted"] += float(row["position"]) * impressions
            bucket["weight"] += impressions
        landing = bucket["urls"][url]
        landing["impressions"] += impressions
        landing["clicks"] += float(row.get("clicks") or 0)

    items = []
    for q in queries.values():
        if q["impressions"] < min_impressions:
            continue
        tokens = words(q["query"])
        if not tokens:
            continue
        landings = sorted(q["urls"].items(), key=lambda x: (-x[1]["impressions"], x[0]))
        strongest_url = landings[0][0]
        ranked = available.get(strongest_url)
        # Fetch a bounded list of plausible *existing* targets independently of
        # whichever page happens to rank for the query.
        candidates = []
        for p in indexed:
            title_cover = overlap(tokens, p["title_terms"])
            body_cover = overlap(tokens, p["body_terms"])
            signal = 0.7 * title_cover + 0.3 * body_cover
            if signal >= 0.25:
                candidates.append((signal, title_cover, body_cover, p))
        candidates.sort(key=lambda x: (-x[0], x[3]["url"]))
        best = candidates[0] if candidates else None
        ranked_title = overlap(tokens, ranked["title_terms"]) if ranked else 0.0
        ranked_body = overlap(tokens, ranked["body_terms"]) if ranked else 0.0
        best_url = best[3]["url"] if best else None

        # Multiple landing URLs *may* reflect site links / GSC aggregation.
        substantial = [(url, d) for url, d in landings
                       if d["impressions"] >= max(10, 0.2 * q["impressions"])]
        overlap_warning = len(substantial) > 1
        if not ranked:
            category = "review"
            reasoning = "Rankende GSC-URL fehlt im letzten indexierbaren Crawl; erst URL/Crawl prüfen."
        elif ranked_title >= 0.75 and ranked_body >= 0.5:
            category = "no_action"
            reasoning = "Suchbegriffe kommen in Überschriften und Text vor; Suchintention trotzdem prüfen."
        elif ranked_title >= 0.4 or ranked_body >= 0.4:
            category = "expand"
            reasoning = "Teilabdeckung der rankenden Seite; bestehenden Inhalt und Suchintention prüfen."
        elif best and best[0] >= 0.5:
            category = "review"
            reasoning = "Andere vorhandene Seite hat stärkere lexikalische Abdeckung; URL-Zuordnung prüfen."
        else:
            category = "new_candidate"
            reasoning = "Keine deutliche lexikalische Abdeckung gefunden; neue Seite erst nach Intent- und SERP-Prüfung erwägen."
        if overlap_warning:
            reasoning += " Mehrere URLs erhalten relevante Impressionen; mögliche Überschneidung manuell prüfen."
        items.append({
            "query": q["query"], "tokens": tokens, "category": category,
            "reason": reasoning, "impressions": round(q["impressions"]),
            "clicks": round(q["clicks"]),
            "position": round(q["weighted"] / q["weight"], 2) if q["weight"] else None,
            "ranked_url": strongest_url, "ranked_crawl_found": bool(ranked),
            "ranked_title_coverage": round(ranked_title, 2) if ranked else None,
            "ranked_body_coverage": round(ranked_body, 2) if ranked else None,
            "best_existing_url": best_url,
            "best_existing_coverage": round(best[0], 2) if best else 0,
            "multiple_landing_urls": overlap_warning,
            "landing_urls": [{"url": u, "impressions": round(d["impressions"]),
                              "clicks": round(d["clicks"])} for u, d in landings[:5]],
        })

    # Pairwise grouping is bounded by a small candidate cap and only combines
    # queries with closely matching token sets. It never sums different queries
    # into a fictitious search volume or SEO score.
    items.sort(key=lambda x: (-x["impressions"], x["query"]))
    clusters: list[dict] = []
    for item in items[:MAX_CANDIDATES]:
        nearest = None
        best_sim = 0.0
        for cluster in clusters:
            anchor = cluster["_tokens"]
            similarity = len(item["tokens"] & anchor) / max(1, len(item["tokens"] | anchor))
            if similarity >= 0.65 and similarity > best_sim:
                nearest, best_sim = cluster, similarity
        if nearest is None:
            nearest = {"id": len(clusters) + 1, "_tokens": item["tokens"],
                       "query": item["query"], "queries": [], "impressions": 0,
                       "clicks": 0, "categories": set()}
            clusters.append(nearest)
        nearest["queries"].append({k: v for k, v in item.items() if k != "tokens"})
        nearest["impressions"] += item["impressions"]
        nearest["clicks"] += item["clicks"]
        nearest["categories"].add(item["category"])
    category_order = ("review", "expand", "new_candidate", "no_action")
    for c in clusters:
        c["category"] = next((k for k in category_order if k in c["categories"]), "review")
        c["queries"].sort(key=lambda x: (-x["impressions"], x["query"]))
        c["ranked_url"] = c["queries"][0]["ranked_url"]
        c["best_existing_url"] = c["queries"][0]["best_existing_url"]
        c["multiple_landing_urls"] = any(q["multiple_landing_urls"] for q in c["queries"])
        c["categories"] = sorted(c["categories"])
        del c["_tokens"]
    clusters.sort(key=lambda x: (-x["impressions"], x["query"]))
    return {"clusters": clusters[:max_results], "total_clusters": len(clusters),
            "queries_considered": len(items), "truncated": len(items) > MAX_CANDIDATES,
            "crawl_pages_compared": len(indexed),
            "method": "GSC-Query-URL-Paare (Impressionen und positionsgewichteter Mittelwert), "
                      "lexikalische Token-Abdeckung in Title/H1/Headings/Body, "
                      "vorsichtige Query-Gruppierung. Keine semantische Intent-Bestätigung, "
                      "keine GSC-Suchvolumen oder garantierte Content-Lücke."}
