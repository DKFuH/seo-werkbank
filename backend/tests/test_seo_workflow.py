"""API tests for multi-tenant manual SEO workflows and measured performance snapshots."""
from datetime import date

from app.db import session_scope
from app.models import GscRow


def test_workflow_lifecycle_and_site_isolation(client, auth, fixture_site):
    url = fixture_site.url + "/"
    site = client.post("/api/sites", headers=auth, json={"name": "Workflow test", "url": url}).json()
    sid = site["id"]
    item_url = f"/api/sites/{sid}/seo-work"
    r = client.post(item_url, headers=auth, json={"kind": "content", "title": "Refresh example", "target_url": url,
                                                  "status": "draft", "notes": "Editorial brief"})
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["kind"] == "content" and item["status"] == "draft"
    assert client.patch(f"{item_url}/{item['id']}", headers=auth, json={"status": "received"}).status_code == 422
    approved = client.patch(f"{item_url}/{item['id']}", headers=auth, json={"status": "approved"})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert client.get(item_url, headers=auth).json()["items"][0]["id"] == item["id"]

    review = client.post(item_url, headers=auth, json={"kind": "review", "title": "Ask all customers for honest feedback"})
    assert review.status_code == 201
    assert client.patch(f"{item_url}/{review.json()['id']}", headers=auth, json={"status": "requested"}).status_code == 200
    assert client.post(item_url, headers=auth, json={"kind": "competitor", "title": "Competitor research", "status": "planned"}).status_code == 422
    assert client.post(item_url, headers=auth, json={"kind": "content", "title": "Missing target"}).status_code == 422

    other = client.post("/api/auth/register", json={"email": "workflow-other@example.com", "password": "correct horse battery"})
    assert other.status_code == 201
    other_auth = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get(item_url, headers=other_auth).status_code == 404
    assert client.patch(f"{item_url}/{item['id']}", headers=other_auth, json={"status": "published"}).status_code == 404
    assert client.delete(f"{item_url}/{item['id']}", headers=other_auth).status_code == 404
    assert client.get(f"{item_url}/{item['id']}/snapshots", headers=other_auth).status_code == 404
    assert client.get(item_url).status_code == 401
    assert client.delete(f"{item_url}/{item['id']}", headers=auth).status_code == 204
    assert client.get(item_url, headers=auth).json()["items"][0]["kind"] == "review"


def test_workflow_snapshot_uses_paired_dated_data_only(client, auth, fixture_site):
    base = fixture_site.url + "/"
    site = client.post("/api/sites", headers=auth, json={"name": "Snapshot test", "url": base}).json()
    sid = site["id"]
    work = client.post(f"/api/sites/{sid}/seo-work", headers=auth, json={
        "kind": "content", "title": "GSC baseline", "target_url": base, "status": "draft"}).json()
    with session_scope() as db:
        db.add_all([
            GscRow(site_id=sid, dataset="query_page", source="csv", day=date(2026, 11, 21), page=base,
                   query="example query", clicks=100, impressions=1000, position=5),
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 21), page=base,
                   query="example query", clicks=4, impressions=80, position=8),
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 20), page=base,
                   query="example query", clicks=6, impressions=120, position=4),
            # Cannot attribute to page if query is missing.
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 21), page=base,
                   query=None, clicks=999, impressions=999, position=1),
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 1, 1), page=base,
                   query="outdated", clicks=999, impressions=999, position=1),
        ])
    path = f"/api/sites/{sid}/seo-work/{work['id']}/snapshots"
    snapshot = client.post(path, headers=auth, json={"label": "baseline", "days": 28})
    assert snapshot.status_code == 201, snapshot.text
    s = snapshot.json()
    assert s["clicks"] == 10 and s["impressions"] == 200
    assert s["position"] == 5.6 and s["source"] == "api"
    assert client.post(path, headers=auth, json={"label": "baseline"}).status_code == 409
    assert len(client.get(path, headers=auth).json()) == 1
    assert client.post(path, headers=auth, json={"label": "followup"}).status_code == 201
    assert len(client.get(path, headers=auth).json()) == 2


def test_snapshot_window_ends_at_latest_site_day_not_page_day(client, auth, fixture_site):
    base = fixture_site.url + "/"
    site = client.post("/api/sites", headers=auth, json={"name": "Stale page snapshot", "url": base}).json()
    sid = site["id"]
    work = client.post(f"/api/sites/{sid}/seo-work", headers=auth, json={
        "kind": "content", "title": "Stale page", "target_url": base, "status": "draft"}).json()
    with session_scope() as db:
        db.add_all([
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 9, 1), page=base,
                   query="old query", clicks=5, impressions=50, position=6),
            # Newer data exists for another URL of the same site; the page itself had no impressions since.
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 21), page=base + "other",
                   query="other query", clicks=1, impressions=10, position=3),
        ])
    path = f"/api/sites/{sid}/seo-work/{work['id']}/snapshots"
    # The 28-day window ends 2026-11-21, so the September row is outside it: no silent reuse of old data.
    r = client.post(path, headers=auth, json={"label": "followup", "days": 28})
    assert r.status_code == 422, r.text
