"""Parser unit tests including compressed logs, redaction and untrusted bot identity."""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from app.services.log_parser import classify_agent, parse_file, parse_line, scrub_path

COMBINED = (
    '203.0.113.90 - - [10/Oct/2026:13:55:36 +0200] '
    '"GET /missing?secret=private HTTP/1.1" 404 123 '
    '"https://ref.example/source?token=private" "Googlebot/2.1"\n'
)
COMMON = (
    '203.0.113.10 - - [10/Oct/2026:13:55:36 +0200] '
    '"GET /okay HTTP/1.1" 200 123\n'
)


def test_combined_discards_sensitive_details(tmp_path: Path):
    f = tmp_path / "access.log"
    f.write_text(COMBINED + "broken row\n", encoding="utf-8")
    report = parse_file(f, fmt="auto")
    assert (report["lines_total"], report["lines_parsed"], report["lines_skipped"]) == (2, 1, 1)
    assert report["groups"]
    assert report["not_found"]
    flat = repr(report)
    assert "203.0.113.90" not in flat
    assert "private" not in flat
    assert "Googlebot/2.1" not in flat
    assert "https://ref.example/source" not in flat
    assert "ref.example" in flat


def test_common_and_gzip(tmp_path: Path):
    p = tmp_path / "example.gz"
    with gzip.open(p, "wb") as f:
        f.write(COMMON.encode())
    report = parse_file(p, compressed=True, fmt="common")
    assert report["lines_parsed"] == 1
    assert report["groups"]
    assert parse_line(COMMON, "combined") is None


def test_bot_claims_not_verified():
    assert classify_agent("Googlebot/2.1") == "googlebot_claim"
    assert classify_agent("bingbot") == "bingbot_claim"
    assert classify_agent("OAI-SearchBot") == "ai_bot_claim"
    assert classify_agent("Brave/1.0") == "browser_or_unknown"
    assert scrub_path("/user/12345678?token=secret") == "/user/[redacted]"
    assert scrub_path("/foo%2fbar") == "/[redacted]"


def test_invalid_and_unsupported_format(tmp_path: Path):
    f = tmp_path / "test.log"
    f.write_text("bad\n", encoding="utf-8")
    assert parse_file(f)["lines_skipped"] == 1
    with pytest.raises(ValueError):
        parse_file(f, fmt="something")
