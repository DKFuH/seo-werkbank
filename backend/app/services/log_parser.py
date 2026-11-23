"""Bounded, privacy-minimising Apache/Nginx access-log parser.

Only aggregates leave this module; original line, IP and full User-Agent are discarded.
"""
from __future__ import annotations

import gzip
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

_LOG = re.compile(
    r'^\S+ \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<request>[^"]*)" (?P<status>\d{3}) (?:\d+|-)'
    r'(?: "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"(?: "[^"]*"){0,2})?'
    r'\s*
)
_REQUEST = re.compile(r"^[A-Z]+\s+(\S+)\s+HTTP/\d(?:\.\d)?$")
_SENSITIVE_SEGMENT = re.compile(
    r"^(?:[0-9]{6,}|[0-9a-f]{16,}|[0-9a-f]{8}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[^/]+@[^/]+)$", re.I
)
MAX_DECOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_ROWS = 5_000_000
MAX_GROUPS = 200_000
MAX_LINE_BYTES = 64 * 1024


def classify_agent(raw: str) -> str:
    """User-Agent claim only. Never call a result a verified crawler."""
    agent = raw.casefold()
    if "bingbot" in agent or "adidxbot" in agent:
        return "bingbot_claim"
    if "googlebot" in agent or "google-inspectiontool" in agent:
        return "googlebot_claim"
    if any(token in agent for token in (
        "oai-searchbot", "gptbot", "claudebot", "claude-searchbot",
        "perplexitybot", "bytespider", "ccbot", "anthropic-ai",
    )):
        return "ai_bot_claim"
    if any(token in agent for token in ("bot", "crawler", "spider", "slurp")):
        return "other_bot_claim"
    return "browser_or_unknown"


def scrub_path(request_path: str) -> str:
    """Remove query/fragment and redact obvious tokens/identifiers; not guaranteed anonymisation."""
    if not request_path or request_path == "*":
        return "/[redacted]"
    p = urlsplit(request_path)
    path = p.path or "/"
    if not path.startswith("/"):
        return "/[redacted]"
    segments = []
    for s in path.split("/"):
        if _SENSITIVE_SEGMENT.fullmatch(s) or "%" in s or len(s) > 120:
            segments.append("[redacted]")
        else:
            segments.append(s)
    result = "/".join(segments)
    return result[:2048]


def referrer_host(referrer: str) -> str:
    if not referrer or referrer == "-":
        return ""
    parts = urlsplit(referrer)
    if parts.scheme not in ("https", "http"):
        return ""
    return (parts.hostname or "").lower()[:255]


def parse_line(raw: str, fmt: str = "auto") -> tuple | None:
    match = _LOG.fullmatch(raw.strip())
    if not match:
        return None
    if fmt == "combined" and match.group("agent") is None:
        return None
    if fmt == "common" and match.group("agent") is not None:
        return None
    request = _REQUEST.fullmatch(match.group("request"))
    if not request:
        return None
    try:
        dt = datetime.strptime(match.group("time"), "%d/%b/%Y:%H:%M:%S %z")
        dt = dt.astimezone(UTC).replace(tzinfo=None)
        status = int(match.group("status"))
    except (ValueError, OverflowError):
        return None
    if not 100 <= status <= 599:
        return None
    return (dt.date(), scrub_path(request.group(1)), status,
            classify_agent(match.group("agent") or ""), referrer_host(match.group("referer") or ""), dt)


def parse_file(path: str | Path, *, compressed: bool = False, fmt: str = "auto") -> dict:
    """Parse line by line with decompression/row/cardinality limits, never return raw lines."""
    if fmt not in ("auto", "combined", "common"):
        raise ValueError("Unbekanntes Logformat")
    groups: Counter = Counter()
    not_found: dict[tuple, tuple[int, datetime, datetime]] = {}
    total = parsed = skipped = decompressed = 0
    first = last = None
    opener = gzip.open if compressed else open
    with opener(path, "rb") as fh:
        while raw := fh.readline(MAX_LINE_BYTES + 1):
            decompressed += len(raw)
            total += 1
            if decompressed > MAX_DECOMPRESSED_BYTES or total > MAX_ROWS:
                raise ValueError("Logdatei überschreitet Verarbeitungsgrenzen")
            if len(raw) > MAX_LINE_BYTES:
                # Drain a long line in bounded chunks. Never build a 500 MB string.
                while raw and not raw.endswith(b"\n"):
                    raw = fh.readline(MAX_LINE_BYTES + 1)
                    decompressed += len(raw)
                    if decompressed > MAX_DECOMPRESSED_BYTES:
                        raise ValueError("Logdatei überschreitet Verarbeitungsgrenzen")
                skipped += 1
                continue
            line = raw.decode("utf-8", errors="replace")
            item = parse_line(line, fmt)
            if item is None:
                skipped += 1
                continue
            day, clean_path, status, agent, host, when = item
            parsed += 1
            first = min(first, day) if first else day
            last = max(last, day) if last else day
            groups[(day, clean_path, status, agent)] += 1
            if status == 404:
                key = (clean_path, host, agent)
                if key in not_found:
                    count, low, high = not_found[key]
                    not_found[key] = (count + 1, min(low, when), max(high, when))
                else:
                    not_found[key] = (1, when, when)
            if len(groups) + len(not_found) > MAX_GROUPS:
                raise ValueError("Zu viele unterschiedliche URLs / Aggregate")
    return {"lines_total": total, "lines_parsed": parsed, "lines_skipped": skipped,
            "period_start": first, "period_end": last,
            "groups": groups, "not_found": not_found,
            "privacy": "IP, Querystrings, vollständiger Referrer und User-Agent verworfen; offensichtliche IDs maskiert"}

)
_REQUEST = re.compile(r"^[A-Z]+\s+(\S+)\s+HTTP/\d(?:\.\d)?$")
_SENSITIVE_SEGMENT = re.compile(
    r"^(?:[0-9]{6,}|[0-9a-f]{16,}|[0-9a-f]{8}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[^/]+@[^/]+)$", re.I
)
MAX_DECOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_ROWS = 5_000_000
MAX_GROUPS = 200_000


def classify_agent(raw: str) -> str:
    """User-Agent claim only. Never call a result a verified crawler."""
    agent = raw.casefold()
    if "bingbot" in agent or "adidxbot" in agent:
        return "bingbot_claim"
    if "googlebot" in agent or "google-inspectiontool" in agent:
        return "googlebot_claim"
    if any(token in agent for token in (
        "oai-searchbot", "gptbot", "claudebot", "claude-searchbot",
        "perplexitybot", "bytespider", "ccbot", "anthropic-ai",
    )):
        return "ai_bot_claim"
    if any(token in agent for token in ("bot", "crawler", "spider", "slurp")):
        return "other_bot_claim"
    return "browser_or_unknown"


def scrub_path(request_path: str) -> str:
    """Remove query/fragment and redact obvious tokens/identifiers; not guaranteed anonymisation."""
    if not request_path or request_path == "*":
        return "/[redacted]"
    p = urlsplit(request_path)
    path = p.path or "/"
    if not path.startswith("/"):
        return "/[redacted]"
    segments = []
    for s in path.split("/"):
        if _SENSITIVE_SEGMENT.fullmatch(s) or "%" in s or len(s) > 120:
            segments.append("[redacted]")
        else:
            segments.append(s)
    result = "/".join(segments)
    return result[:2048]


def referrer_host(referrer: str) -> str:
    if not referrer or referrer == "-":
        return ""
    parts = urlsplit(referrer)
    if parts.scheme not in ("https", "http"):
        return ""
    return (parts.hostname or "").lower()[:255]


def parse_line(raw: str, fmt: str = "auto") -> tuple | None:
    match = _LOG.fullmatch(raw.strip())
    if not match:
        return None
    if fmt == "combined" and match.group("agent") is None:
        return None
    if fmt == "common" and match.group("agent") is not None:
        return None
    request = _REQUEST.fullmatch(match.group("request"))
    if not request:
        return None
    try:
        dt = datetime.strptime(match.group("time"), "%d/%b/%Y:%H:%M:%S %z")
        dt = dt.astimezone(UTC).replace(tzinfo=None)
        status = int(match.group("status"))
    except (ValueError, OverflowError):
        return None
    if not 100 <= status <= 599:
        return None
    return (dt.date(), scrub_path(request.group(1)), status,
            classify_agent(match.group("agent") or ""), referrer_host(match.group("referer") or ""), dt)


def parse_file(path: str | Path, *, compressed: bool = False, fmt: str = "auto") -> dict:
    """Parse line by line with decompression/row/cardinality limits, never return raw lines."""
    if fmt not in ("auto", "combined", "common"):
        raise ValueError("Unbekanntes Logformat")
    groups: Counter = Counter()
    not_found: dict[tuple, tuple[int, datetime, datetime]] = {}
    total = parsed = skipped = decompressed = 0
    first = last = None
    opener = gzip.open if compressed else open
    with opener(path, "rb") as fh:
        for raw in fh:
            decompressed += len(raw)
            total += 1
            if decompressed > MAX_DECOMPRESSED_BYTES or total > MAX_ROWS:
                raise ValueError("Logdatei überschreitet Verarbeitungsgrenzen")
            line = raw.decode("utf-8", errors="replace")
            item = parse_line(line, fmt)
            if item is None:
                skipped += 1
                continue
            day, clean_path, status, agent, host, when = item
            parsed += 1
            first = min(first, day) if first else day
            last = max(last, day) if last else day
            groups[(day, clean_path, status, agent)] += 1
            if status == 404:
                key = (clean_path, host, agent)
                if key in not_found:
                    count, low, high = not_found[key]
                    not_found[key] = (count + 1, min(low, when), max(high, when))
                else:
                    not_found[key] = (1, when, when)
            if len(groups) + len(not_found) > MAX_GROUPS:
                raise ValueError("Zu viele unterschiedliche URLs / Aggregate")
    return {"lines_total": total, "lines_parsed": parsed, "lines_skipped": skipped,
            "period_start": first, "period_end": last,
            "groups": groups, "not_found": not_found,
            "privacy": "IP, Querystrings, vollständiger Referrer und User-Agent verworfen; offensichtliche IDs maskiert"}
