from types import SimpleNamespace

from app.api.pagespeed_batch import measured_summary


def test_cwv_summary_does_not_mix_lab_measurements():
    rows = [
        SimpleNamespace(url="https://example.org/", data={"lab": {"LCP": {"value": 600}},
            "field": {"LCP": {"p75": 1500, "rating": "good"}}}),
        SimpleNamespace(url="https://example.org/page", data={"lab": {"LCP": {"value": 800}},
            "field": {}}),
    ]
    result = measured_summary(rows)
    assert result["sampled_urls"] == 2
    assert result["field_coverage"]["LCP"] == 1
    assert result["field_ratings_by_url"]["LCP"]["good"] == 1
    assert result["field_ratings_by_url"]["INP"] == {}


def test_pagespeed_batch_scoping(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "Speed", "url": fixture_site.url}).json()
    prefix = f"/api/sites/{site['id']}/pagespeed"
    assert client.get(prefix + "/summary", headers=auth).status_code == 200
    assert client.post(prefix + "/batch", headers=auth, json={"limit": 5}).status_code == 400
    other = client.post("/api/auth/register", json={
        "email": "batch-other@example.org", "password": "correct horse battery"}).json()
    secret = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(prefix + "/summary", headers=secret).status_code == 404
    assert client.post(prefix + "/batch", headers=secret, json={"limit": 5}).status_code == 404
