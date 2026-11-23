"""Regression checks for redirect API policy, log parsing and schema delivery."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.api import logs as log_api
from app.db import session_scope
from app.models import RedirectRule
from app.services.log_parser import MAX_LINE_BYTES, parse_file, parse_line
from app.services.redirects import export_rules


def test_redirect_api_conflicts_export_and_tenant_boundary(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Redirect Quality", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    base = f"/api/sites/{sid}/redirects"
    src, target = fixture_site.url + "/old-url", fixture_site.url + "/new-url"
    payload = {"source_url": src, "target_url": target, "status_code": 301}
    created = client.post(base, headers=auth, json=payload)
    assert created.status_code == 201, created.text
    first_id = created.json()["id"]
    assert client.post(base, headers=auth, json=payload).status_code == 409
    assert client.get(base + "/export?format=csv", headers=auth).text.splitlines() == ["source,target,code"]
    approved = client.post(f"{base}/{first_id}/approve", headers=auth)
    assert approved.status_code == 200, approved.text
    exported = client.get(base + "/export?format=csv", headers=auth)
    assert exported.status_code == 200 and src in exported.text and target in exported.text
    assert client.post(f"{base}/{first_id}/approve", headers=auth).status_code == 409
    assert client.patch(f"{base}/{first_id}", headers=auth, json={"target_url": src}).status_code == 409

    chain = client.post(base, headers=auth, json={
        "source_url": fixture_site.url + "/another", "target_url": src})
    assert chain.status_code == 201
    assert client.post(f"{base}/{chain.json()['id']}/approve", headers=auth).status_code == 409
    assert target in client.get(base + "/export?format=apache", headers=auth).text
    apache = client.get(base + "/export?format=apache", headers=auth).text
    assert apache.count("RewriteEngine On") == 1
    assert ".htaccess" in apache

    other = client.post("/api/auth/register", json={
        "email": "redirect-quality-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(base, headers=h).status_code == 404
    assert client.post(base, headers=h, json=payload).status_code == 404
    assert client.get(base + "/export?format=csv", headers=h).status_code == 404


def test_redirect_db_unique_index(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Redirect DB unique", "url": fixture_site.url + "/"}).json()
    with session_scope() as db:
        first = RedirectRule(site_id=site["id"], source_url=fixture_site.url + "/once",
                             target_url=fixture_site.url + "/target-a", state="proposed")
        db.add(first)
    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(RedirectRule(site_id=site["id"], source_url=fixture_site.url + "/once",
                                target_url=fixture_site.url + "/target-b", state="proposed"))


def test_log_import_start_failure_cleans_temp_and_marks_failed(
    client, auth, fixture_site, monkeypatch, tmp_path: Path
):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Log startup failures", "url": fixture_site.url + "/"}).json()
    sid = site["id"]

    def crash(*args, **kwargs):
        raise RuntimeError("Job engine unavailable")

    monkeypatch.setattr(log_api.jobs, "start", crash)
    monkeypatch.setattr(log_api.tempfile, "gettempdir", lambda: str(tmp_path))
    sample = ('192.0.2.2 - - [10/Oct/2026:13:55:36 +0200] '
              '"GET /old HTTP/1.1" 404 123 "-" "Googlebot/2.1"\n')
    failed = client.post(f"/api/sites/{sid}/logs/import", headers=auth,
                         files={"file": ("access.log", sample.encode(), "text/plain")})
    assert failed.status_code == 500
    assert not list(tmp_path.glob("seo-log-import-*"))
    imports = client.get(f"/api/sites/{sid}/logs", headers=auth).json()
    assert len(imports) == 1 and imports[0]["state"] == "failed"
    assert client.delete(f"/api/sites/{sid}/logs/{imports[0]['id']}", headers=auth).status_code == 204


def test_extended_combined_log_and_oversized_line(tmp_path: Path):
    extra = ('192.0.2.4 - - [10/Oct/2026:13:55:36 +0200] '
             '"GET /safe HTTP/1.1" 200 32 "https://ref.example/" '
             '"Googlebot/2.1" "192.0.2.8"\n')
    assert parse_line(extra, "combined") is not None
    assert parse_line(extra, "common") is None
    path = tmp_path / "access.log"
    path.write_bytes(b"z" * (MAX_LINE_BYTES * 3) + b"\n" + extra.encode())
    parsed = parse_file(path, fmt="auto")
    assert parsed["lines_total"] == 2
    assert parsed["lines_skipped"] == 1
    assert parsed["lines_parsed"] == 1
    assert "192.0.2.8" not in str(parsed)


def test_schema_proposal_delivers_escaped_html(client, auth, crawled):
    sid = crawled["site"]["id"]
    url = crawled["base"] + "/about"
    payload = {"url": url, "jsonld": {
        "@context": "https://schema.org", "@type": "WebPage",
        "name": "</script><script>unsafe()</script>"},
        "rationale": "Escape regression"}
    result = client.post(f"/api/sites/{sid}/schema-manager/proposals", json=payload, headers=auth)
    assert result.status_code == 201, result.text
    item_id = result.json()["work_item_id"]
    saved = client.get(f"/api/sites/{sid}/seo-work/{item_id}/content-proposal", headers=auth)
    assert saved.status_code == 200
    data = saved.json()
    assert "</script>" in data["proposed_text"]
    assert data["safe_html"].count("</script>") == 1
    assert "</script><script>unsafe" not in data["safe_html"]
    assert r"\u003c/script" in data["safe_html"]


def test_apache_export_has_single_engine_and_explicit_context():
    out = export_rules([
        {"source_url": "https://example.de/a", "target_url": "https://example.de/b", "status_code": 301},
        {"source_url": "https://example.de/c", "target_url": "https://example.de/d", "status_code": 308},
    ], "apache")
    assert out.count("RewriteEngine On") == 1
    assert "DocumentRoot" in out and ".htaccess" in out
