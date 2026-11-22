from datetime import datetime

from app.api.authority_intelligence import _citation_groups, quality_summary
from app.models import AiVisibilityObservation


def test_directory_quality_never_assumes_authority():
    x = quality_summary({"relevance": "3", "editorial_value": "2", "cost_eur": "120", "referral_visits": "6"})
    assert x["manual_quality_label"] == "prüfenswert"
    assert x["cost_per_visit"] == 20.0
    assert x["verified"] is False
    assert quality_summary({"relevance": "excellent", "editorial_value": ""})["manual_quality_label"] == "Bewertung fehlt"


def test_citation_stability_comparisons_are_per_prompt():
    obs = [AiVisibilityObservation(platform="chatgpt", prompt="Examples?",
        cited_url="https://one.example/", observed_at=datetime(2026, 11, day))
        for day in (1, 3)]
    obs.append(AiVisibilityObservation(platform="chatgpt", prompt="Different question",
        cited_url="https://one.example/", observed_at=datetime(2026, 11, 3)))
    out = _citation_groups(obs, [])
    assert len(out) == 2
    assert out[0]["sources"][0]["repeated_on_multiple_days"] is False
    assert out[1]["sources"][0]["distinct_days_cited"] == 2


def test_authority_tenant_scope(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Authority", "url": fixture_site.url + "/"}).json()
    base = f"/api/sites/{site['id']}"
    entry = client.post(base + "/research", headers=auth, json={
        "kind": "directory_assessment", "title": "Useful directory",
        "payload": {"directory": "Business portal", "listing_url": "https://example.net/",
                    "relevance": "3", "editorial_value": "2", "cost_eur": "100"}})
    assert entry.status_code == 201, entry.text
    result = client.get(base + "/authority/directories", headers=auth)
    assert result.status_code == 200, result.text
    assert result.json()["items"][0]["matched_backlink_count"] == 0
    assert result.json()["items"][0]["verified"] is False
    assert client.get(base + "/authority/ai-source-stability", headers=auth).status_code == 200
    other = client.post("/api/auth/register", json={
        "email": "authority-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(base + "/authority/directories", headers=h).status_code == 404
    assert client.get(base + "/authority/ai-source-stability", headers=h).status_code == 404
