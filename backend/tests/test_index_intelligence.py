"""Google Index Inspection historical snapshots, quotas and sitemap crawl history."""
from __future__ import annotations

from app.api import index_intelligence as ix
from app.db import session_scope
from app.models import Site
from tests.conftest import wait_for_job


def test_property_scope_and_subdomains():
    assert ix._same_property("sc-domain:example.de", "https://shop.example.de/kueche/")
    assert not ix._same_property("sc-domain:example.de", "https://evil-example.de/")
    assert not ix._same_property("https://example.de/", "https://example.de.evil.test/")
    assert not ix._same_property("sc-domain:example.de", "https://user@example.de/")


def test_sitemap_history_and_site_isolation(client, auth, crawled):
    sid = crawled["site"]["id"]
    response = client.get(f"/api/sites/{sid}/index-intelligence/sitemap-history", headers=auth)
    assert response.status_code == 200
    assert response.json()["items"]
    assert any(item["crawl_id"] == crawled["crawl_id"] for item in response.json()["items"])
    other = client.post("/api/auth/register", json={
        "email": "index-intel-other@example.com", "password": "correct horse battery"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/sites/{sid}/index-intelligence/history", headers=headers).status_code == 404


def test_bounded_inspection_batch_uses_real_api_response_only(client, auth, crawled, monkeypatch):
    sid = crawled["site"]["id"]
    with session_scope() as db:
        site = db.get(Site, sid)
        site.gsc_property = "sc-domain:127.0.0.1"

    monkeypatch.setattr(ix.gsc, "is_connected", lambda *args, **kwargs: True)

    async def inspected(*args, **kwargs):
        return {"index": {"verdict": "PASS", "coverageState": "Submitted and indexed"},
                "source": "google_url_inspection_api"}

    monkeypatch.setattr(ix.gsc, "inspect_url", inspected)
    base = f"/api/sites/{sid}/index-intelligence"
    candidates = client.get(base + "/candidates", headers=auth)
    assert candidates.status_code == 200
    assert candidates.json()["items"]
    result = client.post(base + "/inspect", headers=auth, json={"limit": 1})
    assert result.status_code == 202, result.text
    job = wait_for_job(client, auth, result.json()["job_id"])
    assert job["status"] == "completed", job
    data = client.get(base + "/history", headers=auth).json()
    assert data["items"][0]["verdict"] == "PASS"
    assert data["items"][0]["index_loss_alert"] is False
    assert client.post(base + "/inspect", headers=auth, json={"limit": 11}).status_code == 422


def test_index_loss_alert_only_between_google_verdicts(client, auth, crawled, monkeypatch):
    sid = crawled["site"]["id"]
    with session_scope() as db:
        db.get(Site, sid).gsc_property = "sc-domain:127.0.0.1"
    monkeypatch.setattr(ix.gsc, "is_connected", lambda *args, **kwargs: True)

    async def failing(*args, **kwargs):
        return {"index": {"verdict": "FAIL", "coverageState": "Crawled - currently not indexed"}}

    monkeypatch.setattr(ix.gsc, "inspect_url", failing)
    base = f"/api/sites/{sid}/index-intelligence"
    response = client.post(base + "/inspect", headers=auth, json={"limit": 1})
    assert response.status_code == 202
    assert wait_for_job(client, auth, response.json()["job_id"])["status"] == "completed"
    history = client.get(base + "/history", headers=auth).json()["items"]
    assert history[0]["verdict"] == "FAIL"
    assert history[0]["index_loss_alert"] is True
