"""Deterministic pre-approval editorial difference checks.

Findings are review prompts, never factual adjudication or plagiarism detection.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

_NUMBER = re.compile(r"(?<!\w)(?:\d{1,3}(?:[.,]\d{3})+|\d+(?:[,.]\d+)?)(?:\s?[%€$]|\s?(?:Jahre|Tage|Stunden|mm|cm|m²|kWh))?", re.I)
_DATE = re.compile(r"\b(?:[0-3]?\d[./-][01]?\d[./-](?:20)?\d\d|20\d\d)\b")
_URL = re.compile(r"https?://[^\s)\]<>\"']+", re.I)
_HEAD = re.compile(r"(?m)^#{1,6}\s+(.+)$")
_BRAND = re.compile(r"\b(?:[A-ZÄÖÜ][a-zäöüß]{2,}(?:\s+[A-ZÄÖÜ][a-zäöüß]{2,})?)\b")


def review(original: str, proposed: str, rationale: str = "") -> dict:
    """Return bounded diffs in claims that could merit source/reviewer attention."""
    if len(original) > 100000 or len(proposed) > 100000:
        raise ValueError("Redaktionelle Prüfung unterstützt höchstens 100.000 Zeichen je Text")
    findings = []
    def delta(regex: re.Pattern[str], kind: str, label: str, severity: str, limit: int = 20):
        before = {m.group(0).strip() for m in regex.finditer(original)}
        found = list(dict.fromkeys(m.group(0).strip() for m in regex.finditer(proposed)
                                   if m.group(0).strip() not in before))
        if found:
            findings.append({"kind": kind, "severity": severity, "title": label,
                             "examples": found[:limit], "total": len(found),
                             "review": "Neue Angaben gegen Originalquellen und tatsächliche Produktdaten prüfen."})
    delta(_NUMBER, "new_numbers", "Neue Zahlen, Maße oder Preisangaben", "high")
    delta(_DATE, "new_dates", "Neue Datums- oder Jahresangaben", "medium")
    delta(_URL, "new_urls", "Neue externe Quellen/URLs", "medium")
    titles_before = set(_HEAD.findall(original))
    titles_after = list(_HEAD.findall(proposed))
    new_headings = [h for h in titles_after if h not in titles_before]
    if new_headings:
        findings.append({"kind": "new_headings", "severity": "low",
                         "title": "Neue oder geänderte Überschriften",
                         "examples": new_headings[:20], "total": len(new_headings),
                         "review": "Überschriftenhierarchie und Suchintention prüfen."})
    brands_before = set(_BRAND.findall(original))
    new_brands = list(dict.fromkeys(x for x in _BRAND.findall(proposed) if x not in brands_before
                                    and x.lower() not in {"das", "die", "der", "und", "ein", "eine"}))
    if new_brands:
        findings.append({"kind": "new_names", "severity": "medium",
                         "title": "Neue mögliche Eigen- oder Markennamen",
                         "examples": new_brands[:15], "total": len(new_brands),
                         "review": "Erkennung ist heuristisch: Namen und Herstellerangaben manuell bestätigen."})
    before_hosts = {urlsplit(x).hostname for x in _URL.findall(original)}
    after_hosts = {urlsplit(x).hostname for x in _URL.findall(proposed)}
    added_hosts = sorted(host for host in after_hosts - before_hosts if host)
    return {
        "findings": findings, "finding_count": len(findings),
        "new_external_domains": added_hosts[:30],
        "rationale_present": bool(rationale.strip()),
        "needs_review": bool(findings),
        "method": "Vergleich von Textmustern, kein semantischer Wahrheitsbeweis, "
                  "keine juristische/fachliche Prüfung. Freigabe bleibt menschlich.",
    }
