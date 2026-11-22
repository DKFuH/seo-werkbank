"""Conservative, quoteable editorial contexts for *existing* internal link suggestions.

No link is inserted automatically. A candidate is only returned when every matched
lexical term appears in one short source-text passage; no semantic promises.
"""
from __future__ import annotations

import re

from ..text import stem

_WORD = re.compile(r"[^\W_]+(?:[’-][^\W_]+)*", re.UNICODE)


def link_context(text: str, significant_terms: list[str]) -> dict | None:
    terms = set(significant_terms)
    if len(terms) < 2 or not (text or "").strip():
        return None
    paragraphs = re.split(r"(?<=[.!?])\s+|\n{2,}", (text or "")[:25_000])
    for paragraph in paragraphs[:1500]:
        paragraph = " ".join(paragraph.split())
        if len(paragraph) > 1000 or len(paragraph) < 20:
            continue
        words = [(m.group(), m.start(), m.end()) for m in _WORD.finditer(paragraph)]
        if len(words) <= len(terms):
            continue
        matches = [(word, start, end, stem(word.lower())) for word, start, end in words]
        matched = [m for m in matches if m[3] in terms]
        if len({m[3] for m in matched}) < len(terms):
            continue
        selected = [next(m for m in matched if m[3] == term) for term in sorted(terms)]
        begin = min(m[1] for m in selected)
        end = max(m[2] for m in selected)
        # Do not suggest an anchor if the words are scattered over too much text.
        candidate = paragraph[begin:end] if end - begin <= 85 else None
        left = max(0, begin - 70)
        right = min(len(paragraph), end + 70)
        excerpt = ("…" if left else "") + paragraph[left:right] + ("…" if right < len(paragraph) else "")
        return {"context_snippet": excerpt, "anchor_candidate": candidate,
                "context_basis": "Alle lexikalischen Treffer in einer Textpassage; Kontext und Anker redaktionell prüfen."}
    return None
