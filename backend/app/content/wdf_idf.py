"""WDF*IDF term analysis for one page against the pages that rank for the same keyword.

Formulas (as used by German SEO tools since Karl Kratz popularised them):

* WDF(t, d) = log2(freq(t, d) + 1) / log2(L(d) + 1), where L(d) is the number of words in document d.
  The logarithm dampens repetition, so a term used 40 times does not count ten times as much as one used 4 times.
* IDF(t)    = log10(1 + N / n(t)), where N is the number of analysed documents and n(t) the number containing t.
  With a small corpus (own page + up to 10 competitors) IDF mainly separates "everyone uses it" from "rare".
* WDF*IDF   = WDF * IDF.

The result is a *comparison*, not a target: a term far above the competitor maximum can read as stuffing, a term
the competitors share but the own page lacks is a candidate topic. Nothing here predicts rankings.
"""
from __future__ import annotations

import math
from collections import Counter

from ..text import DE_STOPWORDS, EN_STOPWORDS, tokens


def stopwords_for(lang: str) -> set[str]:
    return DE_STOPWORDS | EN_STOPWORDS if (lang or "de").lower().startswith("de") else set(EN_STOPWORDS)


def _content_terms(text: str, stop: set[str], ngram: int) -> list[str]:
    toks = tokens(text)
    words = [t for t in toks if t not in stop and len(t) > 2 and not t.isdigit()]
    if ngram < 2:
        return words
    grams = []
    for i in range(len(toks) - 1):
        a, b = toks[i], toks[i + 1]
        if a in stop or b in stop or len(a) < 3 or len(b) < 3 or a.isdigit() or b.isdigit():
            continue
        grams.append(f"{a} {b}")
    return words + grams


def wdf(freq: int, length: int) -> float:
    if freq <= 0 or length <= 0:
        return 0.0
    return math.log2(freq + 1) / math.log2(length + 1)


def idf(n_docs: int, docs_with_term: int) -> float:
    if n_docs <= 0 or docs_with_term <= 0:
        return 0.0
    return math.log10(1 + n_docs / docs_with_term)


def thirds(text: str, terms: list[str], stop: set[str]) -> dict[str, list[int]]:
    """Occurrences of each term in the first, middle and last third of the (stopword-free) text."""
    words = [t for t in tokens(text) if t not in stop and len(t) > 2 and not t.isdigit()]
    if not words:
        return {t: [0, 0, 0] for t in terms}
    size = math.ceil(len(words) / 3)
    parts = [words[i * size:(i + 1) * size] for i in range(3)]
    joined = [" " + " ".join(p) + " " for p in parts]
    return {t: [j.count(f" {t} ") for j in joined] for t in terms}


def analyse_wdf_idf(own: dict | None, competitors: list[dict], *, keyword: str = "", lang: str = "de",
                    limit: int = 50, ngram: int = 1) -> dict:
    """``own`` and each competitor: {url, text, headings, title?, word_count?}. ``own`` may be None (competitors only)."""
    stop = stopwords_for(lang)
    for kw in tokens(keyword):
        stop.discard(kw)  # the focus keyword itself must stay countable even if it is a stopword
    docs = [d for d in competitors if (d.get("text") or "").strip()]
    if own and (own.get("text") or "").strip():
        docs_all = [own, *docs]
    else:
        own = None
        docs_all = docs
    if not docs:
        return {"terms": [], "documents": [], "notes": ["Keine Wettbewerberseite konnte geladen werden."]}

    counts: list[Counter] = []
    lengths: list[int] = []
    for d in docs_all:
        all_tokens = tokens(d["text"])
        lengths.append(len(all_tokens))
        counts.append(Counter(_content_terms(d["text"], stop, ngram)))
    n = len(docs_all)
    df: Counter = Counter()
    for c in counts:
        df.update(c.keys())

    comp_offset = 1 if own else 0
    comp_n = len(docs)
    min_df = 1 if comp_n < 3 else 2
    scores: dict[str, list[float]] = {}
    for term, d_count in df.items():
        comp_hits = sum(1 for c in counts[comp_offset:] if c.get(term))
        if comp_hits < min_df:
            continue
        term_idf = idf(n, d_count)
        scores[term] = [wdf(c.get(term, 0), lengths[i]) * term_idf for i, c in enumerate(counts)]

    def comp_values(vals: list[float]) -> list[float]:
        return vals[comp_offset:]

    ranked = sorted(scores, key=lambda t: sum(comp_values(scores[t])) / comp_n, reverse=True)
    kw_terms = [t for t in [" ".join(tokens(keyword)), *tokens(keyword)] if t and t in scores]
    selected = list(dict.fromkeys(kw_terms + ranked))[:limit]

    rows = []
    for term in selected:
        vals = scores[term]
        comp = comp_values(vals)
        mean = sum(comp) / comp_n
        mx = max(comp)
        row = {
            "term": term,
            "competitor_mean": round(mean, 4),
            "competitor_max": round(mx, 4),
            "competitors_using": sum(1 for v in comp if v > 0),
            "competitor_share": round(sum(1 for v in comp if v > 0) / comp_n, 2),
            "values": [round(v, 4) for v in vals],
            "counts": [c.get(term, 0) for c in counts],
            "is_keyword": term in kw_terms,
        }
        if own:
            mine = vals[0]
            row["own"] = round(mine, 4)
            row["own_count"] = counts[0].get(term, 0)
            if mine == 0:
                row["status"] = "fehlt" if row["competitor_share"] >= 0.5 else "selten"
            elif mx > 0 and mine > mx * 1.15:
                row["status"] = "über Maximum"
            elif mine < mean * 0.5:
                row["status"] = "deutlich unter Schnitt"
            else:
                row["status"] = "im Rahmen"
        rows.append(row)

    documents = [{
        "url": d.get("url"), "title": d.get("title"), "is_own": own is not None and i == 0,
        "words": lengths[i], "content_terms": sum(counts[i].values()),
        "headings": [h for h in (d.get("headings") or []) if h.get("level", 9) <= 4][:60],
    } for i, d in enumerate(docs_all)]

    summary = None
    if own:
        status = Counter(r["status"] for r in rows)
        summary = {"status_counts": dict(status),
                   "missing": [r["term"] for r in rows if r["status"] == "fehlt"][:25],
                   "over_max": [r["term"] for r in rows if r["status"] == "über Maximum"][:25]}

    return {
        "keyword": keyword, "lang": lang, "ngram": ngram,
        "documents": documents, "terms": rows, "summary": summary,
        "distribution": thirds(own["text"], [r["term"] for r in rows if " " not in r["term"]][:30], stop) if own else None,
        "method": "WDF = log2(Häufigkeit+1) / log2(Wörter+1); IDF = log10(1 + N/n); N = analysierte Seiten inkl. eigener.",
        "notes": ([f"Nur {comp_n} Wettbewerberseite(n) ausgewertet: Werte sind wenig belastbar, 5–10 Seiten empfohlen."]
                  if comp_n < 3 else [])
                 + ["Vergleichswerte, keine Zielvorgaben: WDF*IDF sagt nichts über Rankings voraus.",
                  "Text ohne Navigation, Kopf- und Fußbereich (nav/header/footer/aside/form werden entfernt)."],
    }
