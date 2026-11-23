"""Shared CSV reading and column mapping for all CSV imports.

Every import (Search Console, backlinks, local listings, keywords) first reads the file the same way (encoding,
delimiter, optional preamble lines), suggests a column for each target field from known header names, and accepts a
user-chosen mapping {field: column index} that overrides the suggestion. The preview lets the user check and correct
the mapping before anything is written.
"""
from __future__ import annotations

import csv
import io
import json

from ..integrations.gsc import _ALIASES as GSC_ALIASES
from ..integrations.gsc import _GERMAN_HEADERS as GSC_GERMAN
from .backlinks import _COLS as BACKLINK_ALIASES

KEYWORD_ALIASES = {
    "keyword": ("keyword", "keywords", "search term", "query", "suchbegriff", "suchanfrage"),
    "search_volume": ("avg. monthly searches", "search volume", "volume", "avg monthly searches",
                      "durchschnittl. monatliche suchanfragen", "durchschn. monatliche suchanfragen", "suchvolumen",
                      "monatliche suchanfragen"),
    "competition": ("competition", "competition (indexed value)", "wettbewerb", "wettbewerb (indexierter wert)"),
    "cpc_low": ("top of page bid (low range)", "gebot für obere positionen auf der seite (niedriger bereich)"),
    "cpc_high": ("top of page bid (high range)", "cpc", "gebot für obere positionen auf der seite (hoher bereich)"),
}
KEYWORD_GERMAN = {"suchbegriff", "wettbewerb", "durchschnittl. monatliche suchanfragen", "durchschn. monatliche suchanfragen", "suchvolumen"}
CITATION_ALIASES = {
    "source": ("source", "directory", "site", "platform", "verzeichnis", "quelle", "plattform", "portal"),
    "url": ("url", "listing url", "profil-url", "eintrag-url", "link"),
    "name": ("name", "business name", "firmenname", "unternehmen", "firma"),
    "address": ("address", "adresse", "anschrift"),
    "phone": ("phone", "telephone", "telefon", "tel", "telefonnummer"),
}

# kind -> (fields [(key, label, required)], aliases, German header names for number format detection)
SCHEMAS: dict[str, tuple[list[tuple[str, str, bool]], dict[str, tuple[str, ...]], set[str]]] = {
    "gsc": ([("query", "Suchanfrage", False), ("page", "Seite (URL)", False), ("day", "Datum", False),
             ("country", "Land", False), ("device", "Gerät", False), ("appearance", "Darstellung in der Suche", False),
             ("clicks", "Klicks", True), ("impressions", "Impressionen", True), ("position", "Position", False)],
            GSC_ALIASES, GSC_GERMAN),
    "backlinks": ([("source", "Quell-URL (verlinkende Seite)", False), ("site", "Verlinkende Domain", False),
                   ("target", "Ziel-URL", False), ("anchor", "Ankertext", False), ("nofollow", "rel / nofollow", False)],
                  BACKLINK_ALIASES, set()),
    "citations": ([("source", "Verzeichnis / Quelle", True), ("url", "Eintrag-URL", False), ("name", "Firmenname", False),
                   ("address", "Adresse", False), ("phone", "Telefon", False)], CITATION_ALIASES, set()),
    "keywords": ([("keyword", "Keyword", True), ("search_volume", "Suchvolumen", False), ("competition", "Wettbewerb", False),
                  ("cpc_low", "CPC von", False), ("cpc_high", "CPC bis", False)], KEYWORD_ALIASES, KEYWORD_GERMAN),
}
# Search Console needs one of these; backlinks one of source/site.
ONE_OF = {"gsc": ("query", "page", "day", "country", "device", "appearance"), "backlinks": ("source", "site")}


class ImportFormatError(ValueError):
    pass


def decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")  # Excel on Windows saves CSV as Windows-1252


def _header_line(lines: list[str], aliases: dict[str, tuple[str, ...]]) -> int:
    """Index of the header line: the first of the first 10 lines that contains a known column name.

    Keyword Planner exports start with two title lines before the header."""
    known = {a for names in aliases.values() for a in names}
    for i, line in enumerate(lines[:10]):
        cells = {c.strip().strip('"').lower() for c in line.replace(";", ",").replace("\t", ",").split(",")}
        if cells & known:
            return i
    return 0


def read_table(raw: bytes, kind: str) -> tuple[list[str], list[list[str]]]:
    text = decode(raw)
    lines = text.splitlines()
    start = _header_line(lines, SCHEMAS[kind][1])
    body = "\n".join(lines[start:])
    try:
        dialect = csv.Sniffer().sniff(body[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(body), dialect))
    if not rows or not any(c.strip() for c in rows[0]):
        raise ImportFormatError("Die CSV-Datei ist leer.")
    return [c.strip() for c in rows[0]], rows[1:]


def auto_map(header: list[str], kind: str) -> dict[str, int]:
    aliases = SCHEMAS[kind][1]
    out: dict[str, int] = {}
    for i, name in enumerate(header):
        n = name.strip().lower()
        for field, names in aliases.items():
            if n in names and field not in out:
                out[field] = i
    return out


def german_numbers(header: list[str], kind: str) -> bool:
    return any(h.strip().lower() in SCHEMAS[kind][2] for h in header)


def parse_mapping(value: str | None, header: list[str], kind: str) -> dict[str, int] | None:
    """User mapping from the upload form: JSON {field: column index | null}. None = use the automatic mapping."""
    if not value:
        return None
    try:
        data = json.loads(value)
    except ValueError as exc:
        raise ImportFormatError("Spaltenzuordnung ist kein gültiges JSON.") from exc
    if not isinstance(data, dict):
        raise ImportFormatError("Spaltenzuordnung muss ein Objekt sein.")
    fields = {f for f, _, _ in SCHEMAS[kind][0]}
    out: dict[str, int] = {}
    for field, idx in data.items():
        if field not in fields:
            raise ImportFormatError(f"Unbekanntes Feld '{field}'.")
        if idx is None:
            continue
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(header):
            raise ImportFormatError(f"Spalte für '{field}' existiert nicht.")
        out[field] = idx
    return out


def check_required(mapping: dict[str, int], kind: str) -> None:
    labels = {f: label for f, label, _ in SCHEMAS[kind][0]}
    missing = [labels[f] for f, _, required in SCHEMAS[kind][0] if required and f not in mapping]
    if missing:
        raise ImportFormatError("Pflichtfeld ohne Spalte: " + ", ".join(missing))
    one_of = ONE_OF.get(kind)
    if one_of and not any(f in mapping for f in one_of):
        raise ImportFormatError("Mindestens eine dieser Spalten zuordnen: " + ", ".join(labels[f] for f in one_of))


def resolve(raw: bytes, kind: str, mapping_json: str | None) -> tuple[list[str], list[list[str]], dict[str, int]]:
    """Read the file and return header, rows and the effective mapping (user's or automatic), checked for required fields."""
    header, rows = read_table(raw, kind)
    mapping = parse_mapping(mapping_json, header, kind)
    effective = mapping if mapping is not None else auto_map(header, kind)
    check_required(effective, kind)
    return header, rows, effective


def preview(raw: bytes, kind: str, sample_rows: int = 5) -> dict:
    header, rows = read_table(raw, kind)
    suggested = auto_map(header, kind)
    samples = rows[:sample_rows]
    return {
        "kind": kind,
        "columns": [{"index": i, "name": name or f"Spalte {i + 1}",
                     "samples": [r[i].strip() for r in samples if i < len(r) and r[i].strip()][:3]} for i, name in enumerate(header)],
        "fields": [{"key": f, "label": label, "required": req, "suggested": suggested.get(f)} for f, label, req in SCHEMAS[kind][0]],
        "one_of": list(ONE_OF.get(kind, ())),
        "rows": len(rows),
        "number_format": "de" if german_numbers(header, kind) else "en" if SCHEMAS[kind][2] else None,
    }
