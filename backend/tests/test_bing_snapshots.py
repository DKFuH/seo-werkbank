"""Bing intelligence endpoints keep provider evidence inside the owning tenant."""
from __future__ import annotations

from app.integrations import bing


def _other_auth(client) -> dict[str, str]:
    response = client.post("/api/auth/register", json={
        "email": "bing-snapshot-other@example.com",
        "password": "correct horse battery",
    })
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_bing_endpoints_reject_cross_tenant_access(client, crawled):
    site_id = crawled["site"]["id"]
    other = _other_auth(client)
    paths = [
        f"/api/sites/{site_id}/bing/overview",
        f"/api/sites/{site_id}/bing/intelligence/traffic",
        f"/api/sites/{site_id}/bing/content-analysis",
        f"/api/sites/{site_id}/bing/snapshots",
        f"/api/sites/{site_id}/bing/snapshots/1",
    ]
    for path in paths:
        assert client.get(path, headers=other).status_code == 404, path
    assert client.post(
        f"/api/sites/{site_id}/bing/snapshots",
        headers=other,
        json={"operation": "traffic"},
    ).status_code == 404


def test_snapshot_capture_list_and_detail_are_site_scoped(
    client, auth, crawled, monkeypatch,
):
    site_id = crawled["site"]["id"]
    property_url = crawled["site"]["url"]

    async def fake_sites(settings):
        return [{"url": property_url, "verified": True}]

    async def fake_read(settings, site_url, operation, **kwargs):
        assert site_url == property_url
        assert operation == "traffic"
        return {"provider": "bing", "operation": operation, "data": [{"Clicks": 3}]}

    monkeypatch.setattr(bing, "sites", fake_sites)
    monkeypatch.setattr(bing, "read_intelligence", fake_read)

    created = client.post(
        f"/api/sites/{site_id}/bing/snapshots",
        headers=auth,
        json={"operation": "traffic"},
    )
    assert created.status_code == 201, created.text
    snapshot_id = created.json()["id"]

    history = client.get(f"/api/sites/{site_id}/bing/snapshots", headers=auth)
    assert history.status_code == 200, history.text
    item = next(row for row in history.json()["items"] if row["id"] == snapshot_id)
    assert item["provider"] == "bing"
    assert item["property_url"] == property_url

    detail = client.get(
        f"/api/sites/{site_id}/bing/snapshots/{snapshot_id}", headers=auth,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["payload"]["data"] == [{"Clicks": 3}]
