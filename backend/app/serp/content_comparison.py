"""Lexical SERP comparison. No ranking score or entity recognition is implied."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..text import tfidf_terms


def page_kind(url: str, page: dict) -> str:
    path = urlsplit(url).path.lower()
    schema = set(page.get("schema_types") or [])
    if "Product" in schema or any(x in path for x in ("/shop/", "/product/", "/produkt/")):
        return "product"
    if schema & {"Article", "BlogPosting", "NewsArticle", "HowTo"} or any(
        x in path for x in ("/ratgeber/", "/blog/", "/guide/", "/magazin/", "/wiki/")
    ):
        return "guide"
    if path in ("", "/"):
        return "homepage"
    return "unknown"


def tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def occurrences(phrase: str, value: str) -> int:
    needle, hay = tokens(phrase), tokens(value)
    if not needle:
        return 0
    return sum(hay[i:i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def prominence(keyword: str, page: dict) -> dict:
    body = page.get("text") or ""
    headings = page.get("headings") or []
    return {
        "title": bool(occurrences(keyword, page.get("title") or "")),
        "description": bool(occurrences(keyword, page.get("meta_description") or "")),
        "h1": any(occurrences(keyword, h["text"]) for h in headings if h["level"] == 1),
        "h2_h3": any(occurrences(keyword, h["text"]) for h in headings if h["level"] in (2, 3)),
        "first_100": bool(occurrences(keyword, " ".join(tokens(body)[:100]))),
        "last_100_of_sample": bool(occurrences(keyword, " ".join(tokens(body)[-100:]))),
        "mentions_in_sample": occurrences(keyword, body),
        "sample_words": len(tokens(body)),
    }


def compare(keyword: str, results: list[dict], pages: dict[str, dict], my_url: str | None) -> dict:
    own = pages.get(my_url or "", {})
    own_ok = own.get("status") == 200
    target_kind = page_kind(my_url or "", own) if own_ok else "unknown"
    rows = []
    seen = set()
    for result in results[:10]:
        url = result["url"]
        if url == my_url or url in seen:
            continue
        seen.add(url)
        page = pages.get(url, {})
        loaded = page.get("status") == 200
        kind = page_kind(url, page) if loaded else "unknown"
        rows.append({
            "url": url, "position": result["position"], "kind": kind,
            "loaded": loaded,
            "comparable": loaded and (target_kind == "unknown" or kind == target_kind),
            "prominence": prominence(keyword, page) if loaded else None,
            "images": page.get("images") if loaded else None,
            "word_count": page.get("word_count") if loaded else None,
        })
    selected = [r for r in rows if r["comparable"]]
    documents = [pages[r["url"]].get("text") or "" for r in selected]
    terms = tfidf_terms(documents, limit=25)
    matrix = []
    for item in terms:
        term = item["term"]
        hits = [bool(occurrences(term, doc)) for doc in documents]
        matrix.append({
            "term": term, "hits": hits, "coverage": sum(hits),
            "own": bool(occurrences(term, own.get("text") or "")) if own_ok else None,
        })
    return {
        "method": "Lexikalische Stichprobe; Seitentyp aus URL und Schema geschätzt, keine Intent- oder Entitätenerkennung.",
        "target_kind": target_kind, "rows": rows,
        "selected_urls": [r["url"] for r in selected], "matrix": matrix,
        "own_prominence": prominence(keyword, own) if own_ok else None,
        "own_url": my_url,
        "backlink_status": "unavailable",
        "briefing_candidates": [m["term"] for m in matrix if m["own"] is False
                                and m["coverage"] >= 2 and m["coverage"] / len(selected) >= 0.4],
    }
