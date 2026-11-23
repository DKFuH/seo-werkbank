"""Regression tests for interrupted imports, bounded redirect matching and safe JSON-LD HTML."""
from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.audit.schema_validator import jsonld_script_element, serialize_jsonld_for_html
from app.db import session_scope
from app.jobs import mark_interrupted_jobs
from app.models import LogImport
from app.services import redirects


def test_interrupted_log_can_be_deleted_and_temp_removed(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Interrupted logs", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    with session_scope() as db:
        record = LogImport(site_id=sid, filename="lost.log", format="auto", state="processing")
        db.add(record)
        db.flush()
        import_id = record.id
    temporary = Path(tempfile.gettempdir()) / f"seo-log-import-{import_id}-orphan.tmp"
    temporary.write_text("temporary content", encoding="utf-8")
    try:
        assert client.delete(f"/api/sites/{sid}/logs/{import_id}", headers=auth).status_code == 409
        mark_interrupted_jobs()
        assert not temporary.exists()
        records = client.get(f"/api/sites/{sid}/logs", headers=auth).json()
        assert next(x for x in records if x["id"] == import_id)["state"] == "failed"
        assert client.delete(f"/api/sites/{sid}/logs/{import_id}", headers=auth).status_code == 204
    finally:
        temporary.unlink(missing_ok=True)


def test_bounded_404_candidates_even_for_large_crawl(monkeypatch):
    valid = [
        SimpleNamespace(url=f"https://example.de/ratgeber/kueche-idee-{i}/",
                        status_code=200, indexable=True, redirect_to=None, inlinks=1)
        for i in range(1500)
    ]
    missing = [
        SimpleNamespace(url=f"https://example.de/ratgeber/kueche-idee-{i}/alt/",
                        status_code=404, indexable=False, redirect_to=None, inlinks=2)
        for i in range(600)
    ]
    db = SimpleNamespace(scalars=lambda _: iter(valid + missing))
    crawl = SimpleNamespace(id=1)
    site = SimpleNamespace(url="https://example.de/")
    calls = [0]
    real_matcher = redirects.SequenceMatcher

    def counted_matcher(*args, **kwargs):
        calls[0] += 1
        return real_matcher(*args, **kwargs)

    monkeypatch.setattr(redirects, "SequenceMatcher", counted_matcher)
    redirects.propose_from_crawl(db, crawl, site)
    assert calls[0] <= 500 * 32


def test_jsonld_html_escapes_script_breakout_and_retains_values():
    suspicious = '</script><script>alert("example")</script> & < > \u2028 \u2029'
    doc = {"@context": "https://schema.org", "@type": "WebPage", "name": suspicious}
    html = jsonld_script_element(doc)
    assert html.count("</script>") == 1
    assert "<script>alert" not in html
    assert r"\u003c/script\u003e" in html
    assert r"\u0026" in html
    assert suspicious not in html
    import json
    recovered = json.loads(serialize_jsonld_for_html(doc))
    assert recovered == doc


def test_schema_generator_endpoint_safe_markup(client, auth):
    payload = {"type": "WebPage", "values": {"name": "</script><img src=x>"}}
    response = client.post("/api/schema/generate", json=payload, headers=auth)
    assert response.status_code == 200, response.text
    html = response.json()["html"]
    assert html.count("</script>") == 1
    assert "</script><img" not in html
