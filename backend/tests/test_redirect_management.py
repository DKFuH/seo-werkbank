"""Redirect-planner unit tests, no server writes."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.redirects import export_rules, normalise_url, simulate

SITE = SimpleNamespace(url="https://example.de/")


def test_normalise_only_same_host():
    assert normalise_url(SITE, "https://example.de/alt") == "https://example.de/alt"
    for candidate in ("https://evil.test/alt", "https://example.de/a?next=evil",
                      "https://example.de/a%0d%0a", "https://example.de/a#fragment",
                      "https://user@example.de/a"):
        with pytest.raises(HTTPException):
            normalise_url(SITE, candidate)


def test_simulate_loops_chains_and_self():
    rules = [
        {"source_url": "https://example.de/a", "target_url": "https://example.de/b"},
        {"source_url": "https://example.de/b", "target_url": "https://example.de/a"},
    ]
    found = simulate(rules)
    assert any(f["issue"] == "redirect_loop" for f in found)
    assert any(f["issue"] == "redirect_chain" for f in found)
    assert any(f["issue"] == "self_redirect" for f in simulate([{
        "source_url": "https://example.de/a", "target_url": "https://example.de/a",
    }]))


def test_status_snapshots_are_caveated():
    rule = [{"source_url": "https://example.de/a", "target_url": "https://example.de/b"}]
    assert any(x["issue"] == "target_not_verified" for x in simulate(rule))
    found = simulate(rule, {"https://example.de/b": (404, False)})
    assert any(x["issue"] == "target_not_indexable" for x in found)


def test_exports_are_exact_path_and_never_automatically_applied():
    rows = [{"source_url": "https://example.de/a.b", "target_url": "https://example.de/neu",
             "status_code": 301}]
    apache = export_rules(rows, "apache")
    nginx = export_rules(rows, "nginx")
    assert "a\\.b$" in apache
    assert "location = /a.b" in nginx
    assert "ENTWURF" in apache and "ENTWURF" in nginx
    assert "source,target,code" in export_rules(rows, "csv")
