"""Read-only GSC page/query opportunities for an editorial content refresh.

Never infer a page from an unpaired GSC query row. All metrics are measured unless
explicitly marked as a hypothetical CTR-based estimate.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from ..integrations.gsc import expected_ctr
from ..text import content_tokens, stem


def page_key(url: str | None) -> str | None:
    """Conservatively match a crawl URL to its GSC URL (not a canonical resolver)."""
    try:
        u = urlsplit(url or "")
        if u.scheme.lower() not in ("http", "https") or not u.hostname or u.username or u.password:
            return None
        host = u.hostname.lower()
        port = u.port
    except ValueError:
        return None
    if port and (u.scheme.lower(), port) not in (("http", 80), ("https", 443)):
        host += f":{port}"
    path = u.path or "/"
    return f"{u.scheme.lower()}://{host}{path}" + (f"?{u.query}" if u.query else "")


def build_refresh_pages(pairs: list[dict], crawled: dict[str, dict] | None = None, *,
                        min_impressions: int = 20, limit: int = 50) -> dict:
    """Group *observed* query/page pairs, returning review prompts, never auto-written content.

    Pairs are already aggregated by the database for one source and one period.
    Crawled pages are keyed by page_key. Presence of a word is a weak lexical signal,
    not proof that the page covers (or does not cover) the user's question.
    """
    crawled = crawled or {}
    buckets: dict[str, dict] = {}
    for row in pairs:
        key = page_key(row.get("page"))
        query = (row.get("query") or "").strip()
        impressions = float(row.get("impressions") or 0)
        clicks = float(row.get("clicks") or 0)
        position = row.get("position")
        if not key or not query or impressions < min_impressions or position is None:
            continue
        position = float(position)
        ctr = clicks / impressions if impressions else 0
        if 4 <= position <= 20:
            kind = "striking_distance"
            target = 3
        elif 1 <= position < 4 and impressions >= 100 and ctr < expected_ctr(position) * 0.5:
            kind = "low_ctr"
            target = round(position)
        else:
            continue
        potential = max(0, round(impressions * expected_ctr(target) - clicks))
        if potential < 1:
            continue
        page = buckets.setdefault(key, {"url": row["page"], "impressions": 0, "clicks": 0,
                                        "estimated_extra_clicks": 0, "queries": []})
        page["impressions"] += impressions
        page["clicks"] += clicks
        page["estimated_extra_clicks"] += potential
        meta = crawled.get(key)
        tokens = list(dict.fromkeys(stem(w) for w in content_tokens(query)))
        headings = " ".join(h.get("text", "") for h in (meta or {}).get("headings", []) if isinstance(h, dict))
        heading_tokens = {stem(w) for w in content_tokens(headings)}
        body_tokens = {stem(w) for w in content_tokens(((meta or {}).get("text") or "")[:25000])}
        # Do not claim a missing topic from a stemmer calibrated mainly for English.
        terms_to_review = [w for w in tokens if w not in heading_tokens] if meta else []
        page["queries"].append({"query": query, "impressions": round(impressions), "clicks": round(clicks),
                                "position": round(position, 1), "ctr": round(ctr, 4), "type": kind,
                                "estimated_extra_clicks": potential, "review_terms": terms_to_review[:8],
                                "mentioned_in_body": bool(tokens and all(w in body_tokens for w in tokens)) if meta else None,
                                "editorial_action": "Suchintention und Snippet prüfen" if kind == "low_ctr"
                                else "Suchintention prüfen; bei echtem Bedarf Abschnitt ergänzen"})
    out = []
    for key, page in buckets.items():
        meta = crawled.get(key)
        page["crawl_found"] = meta is not None
        page["title"] = (meta or {}).get("title")
        page["impressions"] = round(page["impressions"])
        page["clicks"] = round(page["clicks"])
        page["queries"].sort(key=lambda q: -q["estimated_extra_clicks"])
        page["queries"] = page["queries"][:10]
        out.append(page)
    out.sort(key=lambda p: -p["estimated_extra_clicks"])
    return {"pages": out[:limit], "total_pages": len(out),
            "method": "Nur gemessene GSC-Query-URL-Paare. Zusatzklicks: unverbindliches Szenario aus allgemeiner CTR-Kurve; "
                      "Wortabgleich mit Crawl-Text ist lexikalisch und keine Content-Gap-Feststellung."}
