"""Manual redirect planning. Never updates live web-server configuration."""
from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import select

from ..models import Page

SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~!&'()*+,=:@/-]*$")


def normalise_url(site, raw: str) -> str:
    """Forbid cross-host redirects, credentials, queries, control chars and unsafe paths."""
    p = urlsplit(raw.strip())
    origin = urlsplit(site.url)
    if (p.scheme not in ("https", "http") or not p.hostname or p.username or p.password
            or p.hostname.lower() != origin.hostname.lower() or p.port != origin.port
            or p.query or p.fragment or not SAFE_PATH.fullmatch(p.path or "/")
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in raw)):
        raise HTTPException(422, "Nur sichere URLs derselben Website ohne Query/Fragment erlaubt")
    if "%" in p.path or "//" in p.path or any(segment in (".", "..") for segment in p.path.split("/")):
        raise HTTPException(422, "Mehrdeutige URL-Kodierung oder Pfadsegmente nicht erlaubt")
    return p._replace(scheme=origin.scheme, netloc=origin.netloc, path=p.path or "/", query="", fragment="").geturl()


def simulate(rules: list[dict], statuses: dict[str, tuple[int | None, bool]] | None = None) -> list[dict]:
    """Find cycles, intermediary redirects and unknown/bad targets without fetching URLs."""
    statuses = statuses or {}
    targets: dict[str, str] = {}
    warnings: list[dict] = []
    for r in rules:
        source, target = r["source_url"], r["target_url"]
        if source in targets:
            warnings.append({"source_url": source, "issue": "duplicate_source"})
        targets[source] = target
        if source == target:
            warnings.append({"source_url": source, "issue": "self_redirect"})
    for source, target in targets.items():
        seen, current = {source}, target
        for _ in range(len(targets) + 1):
            if current in seen:
                warnings.append({"source_url": source, "issue": "redirect_loop"})
                break
            seen.add(current)
            if current not in targets:
                break
            warnings.append({"source_url": source, "issue": "redirect_chain"})
            current = targets[current]
        if current in statuses:
            status, indexable = statuses[current]
            if status != 200 or not indexable:
                warnings.append({"source_url": source, "issue": "target_not_indexable", "status": status})
        else:
            warnings.append({"source_url": source, "issue": "target_not_verified"})
    return warnings


def propose_from_crawl(db, crawl, site) -> list[dict]:
    pages = list(db.scalars(select(Page).where(Page.crawl_id == crawl.id).limit(10000)))
    by_url = {p.url: p for p in pages}
    good = [p for p in pages if p.status_code == 200 and p.indexable]
    suggestions: list[dict] = []
    for page in pages:
        if not page.redirect_to or page.status_code not in (301, 302, 303, 307, 308):
            continue
        visited, destination, hops = {page.url}, page.redirect_to, 0
        while destination in by_url and by_url[destination].redirect_to and destination not in visited:
            visited.add(destination)
            destination = by_url[destination].redirect_to
            hops += 1
        if destination in visited or destination not in by_url:
            continue
        final = by_url[destination]
        if final.status_code != 200 or not final.indexable:
            continue
        if hops > 0 or page.status_code in (302, 303, 307):
            try:
                source = normalise_url(site, page.url)
                target = normalise_url(site, destination)
            except HTTPException:
                continue
            suggestions.append({
                "source_url": source, "target_url": target, "status_code": 301,
                "confidence": 0.9 if hops else 0.55, "origin": "crawl",
                "note": "Kette kürzen" if hops else "Temporäre Weiterleitung: Dauerhaftigkeit manuell prüfen",
            })
    # Inverted token index avoids comparing every 404 with every healthy page.
    # Exclude very common terms, cap postings and expensive similarity calls.
    stopwords = {"html", "php", "de", "www", "index", "seite", "page", "shop"}
    def tokens(url: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", urlsplit(url).path.lower())) - stopwords

    indexed: dict[str, list[int]] = defaultdict(list)
    healthy_tokens = [tokens(p.url) for p in good]
    for i, words in enumerate(healthy_tokens):
        for word in words:
            indexed[word].append(i)

    missing = [p for p in pages if p.status_code in (404, 410) and p.inlinks]
    for page in missing[:500]:
        words = tokens(page.url)
        if not words:
            continue
        candidates: Counter[int] = Counter()
        for word in words:
            matches = indexed.get(word, [])
            if len(matches) <= 256:
                candidates.update(matches)
        if not candidates:
            continue
        # Check at most the 32 strongest overlapping URL candidates.
        shortlist = sorted(candidates, key=lambda i: (
            -candidates[i], abs(len(healthy_tokens[i]) - len(words)), good[i].url
        ))[:32]
        best = None
        for i in shortlist:
            target = good[i]
            overlap = len(words & healthy_tokens[i]) / max(1, len(words | healthy_tokens[i]))
            lexical = SequenceMatcher(None, urlsplit(page.url).path, urlsplit(target.url).path).ratio()
            score = 0.7 * overlap + 0.3 * lexical
            if score >= 0.45 and (best is None or score > best[0]):
                best = (score, target)
        if best is not None:
            confidence, target = best
            try:
                suggestions.append({
                    "source_url": normalise_url(site, page.url),
                    "target_url": normalise_url(site, target.url),
                    "status_code": 301, "origin": "crawl",
                    "confidence": round(confidence, 2),
                    "note": "404-Zielkandidat nach URL-Ähnlichkeit, fachlich prüfen",
                })
            except HTTPException:
                pass
    return suggestions


def export_rules(rules: list[dict], format: str) -> str:
    """Exact-path rules only; output is a reviewed configuration draft."""
    if format == "csv":
        f = io.StringIO()
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("source", "target", "code"))
        for r in rules:
            writer.writerow((r["source_url"], r["target_url"], r["status_code"]))
        return f.getvalue()
    if format not in ("apache", "nginx"):
        raise HTTPException(422, "Format unbekannt")
    out = ["# ENTWURF: erst in einer Testumgebung prüfen"]
    for r in rules:
        path = urlsplit(r["source_url"]).path
        target = r["target_url"]
        code = r["status_code"]
        # Already validated input: no spaces, quotes, control chars, regex or query parts.
        if format == "apache":
            # Redirect directive is exact/prefix matching; RewriteRule anchors the exact path.
            out.append("RewriteEngine On")
            out.append(f"RewriteRule ^{re.escape(path.lstrip('/'))}$ {target} [R={code},L,NE]")
        else:
            out.append(f"location = {path} {{ return {code} {target}; }}")
    return "\n".join(out) + "\n"
