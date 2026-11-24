"""Optional provider credentials, live data parsing, local SERP cost gate."""
from __future__ import annotations


import httpx

from app.db import session_scope
from app.models import RankTarget
from app.services import external_intelligence as ext


def test_per_site_provider_secrets_not_returned(client, auth):
    site = client.post("/api/sites", headers=auth, json={"name": "External Provider",
        "url": "https://external-intel.example.org/"}).json()
    sid = site["id"]
    base = f"/api/sites/{sid}/external-intelligence"
    response = client.put(base + "/config", headers=auth, json={
        "provider": "clarity", "token": "private-token-secret"})
    assert response.status_code == 200, response.text
    result = client.get(base + "/status", headers=auth).json()
    assert result["providers"][1]["connected"] is True
    assert "private-token-secret" not in str(result)
    with session_scope() as db:
        assert ext.config(db, "clarity", 1, sid)["token"] == "private-token-secret"
    disconnected = client.delete(base + "/config/clarity", headers=auth)
    assert disconnected.status_code == 200
    assert disconnected.json()["connected"] is False
    second = client.post("/api/auth/register", json={
        "email": "external-provider-guest@example.com",
        "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + second["access_token"]}
    assert client.get(base + "/status", headers=h).status_code == 404


def test_paid_local_rank_requires_credential_and_acknowledgement(client, auth):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Local SERP", "url": "https://local-serp.example.org/"}).json()
    sid = site["id"]
    with session_scope() as db:
        target = RankTarget(site_id=sid, keyword="küchenstudio sohren",
                            engine="google", country="de", language="de",
                            location="Sohren,Rhineland-Palatinate,Germany")
        db.add(target)
        db.flush()
        target_id = target.id
    endpoint = f"/api/sites/{sid}/external-intelligence/local-rank"
    assert client.post(endpoint, headers=auth, json={"target_id": target_id}).status_code == 422
    assert client.post(endpoint, headers=auth, json={
        "target_id": target_id, "acknowledge_cost": True}).status_code == 409


def test_dataforseo_response_parses_only_exact_domain(monkeypatch):
    async def mock_send(self, url, **kwargs):
        if "/organic/" in url:
            items = [{"type": "organic", "domain": "evil-example.de",
                      "url": "https://evil-example.de/", "rank_absolute": 1},
                     {"type": "organic", "domain": "example.de",
                      "url": "https://example.de/p", "rank_absolute": 4}]
        else:
            items = [{"type": "maps_search", "domain": "example.de",
                      "url": "https://example.de", "rank_absolute": 3}]
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"tasks": [{"status_code": 20000,
            "result": [{"items": items}]}]}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_send)
    import asyncio
    result = asyncio.run(ext.local_serp({"login": "u", "password": "p"}, keyword="küchenstudio",
        location="Sohren,Rhineland-Palatinate,Germany", language="de", own_host="example.de"))
    assert result["organic"]["position"] == 4
    assert result["maps"]["position"] == 3
    assert "kostenpflichtig" in result["note"]


def test_clarity_response_is_aggregated_and_filters_unknown_fields(monkeypatch):
    async def mock_get(self, url, **kwargs):
        assert url == ext.CLARITY_API
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=[{"metricName": "Traffic",
            "information": [{"Device": "mobile", "totalSessionCount": "12",
                             "visitorEmail": "sensitive@example.com"}]}], request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    import asyncio
    result = asyncio.run(ext.clarity_overview({"token": "secret"}, days=3))
    assert result["metrics"][0]["rows"][0]["totalSessionCount"] == "12"
    assert "visitorEmail" not in str(result)
