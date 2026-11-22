"""Provider records must retain provenance, preserve empty metrics and isolate sites."""
from datetime import date

import pytest

from app.db import session_scope
from app.models import Backlink, GscRow, Keyword
from app.services.seo_data_providers import provider_catalogue, provider_data


def test_provider_catalogue():
    catalogue = provider_catalogue()
    assert {p["id"] for p in catalogue} == {"keyword_import", "gsc", "backlink_records"}
    assert all(p["origin"] and p["scope"] for p in catalogue)


def test_provider_provenance_and_scope(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Provider test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    with session_scope() as db:
        db.add_all([
            Keyword(site_id=sid, keyword="test import", source="import",
                    metrics={"imported": {"search_volume": 100, "file": "planner.csv", "cpc_low": 0.9}}),
            Keyword(site_id=sid, keyword="no volume", source="manual", metrics={}),
            GscRow(site_id=sid, dataset="query_page", source="api", query="test keyword",
                   page=fixture_site.url + "/", day=date(2026, 11, 20),
                   clicks=6, impressions=120, position=7),
            GscRow(site_id=sid, dataset="query_page", source="csv", query="test keyword",
                   page=fixture_site.url + "/", day=date(2026, 11, 20),
                   clicks=100, impressions=1000, position=2),
            Backlink(site_id=sid, source_url="https://other.example/post",
                     source_domain="other.example", target_url=fixture_site.url + "/",
                     origin="import", status="unverified"),
        ])
    root = f"/api/sites/{sid}/seo-data/"
    imported = client.get(root + "keyword_import", headers=auth)
    assert imported.status_code == 200, imported.text
    assert imported.json()["data"]["items"][0]["volume"] == 100
    assert imported.json()["data"]["items"][0]["source_file"] == "planner.csv"
    assert imported.json()["data"]["items"][0]["position"] is None
    gsc = client.get(root + "gsc", headers=auth)
    assert gsc.status_code == 200, gsc.text
    d = gsc.json()["data"]
    assert d["record_source"] == "api"
    assert d["items"][0]["impressions"] == 120
    assert d["items"][0]["search_volume"] is None
    backlinks = client.get(root + "backlink_records", headers=auth)
    assert backlinks.status_code == 200, backlinks.text
    assert backlinks.json()["data"]["items"][0]["verification_status"] == "unverified"
    assert client.get(root + "invented", headers=auth).status_code == 404
    assert client.get(root + "gsc", headers=auth, params={"limit": 1000}).status_code == 422
    assert client.get("/api/seo-data/providers").status_code == 401

    other = client.post("/api/auth/register", json={
        "email": "provider-scope@example.com", "password": "correct horse battery"}).json()
    other_auth = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(root + "gsc", headers=other_auth).status_code == 404
    assert client.get(root + "keyword_import", headers=other_auth).status_code == 404


def test_registry_rejects_unknown_and_extreme_limits(client, auth, fixture_site):
    with session_scope() as db:
        with pytest.raises(ValueError, match="Unknown"):
            provider_data(db, 1, "other")
