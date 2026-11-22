"""AI prompt sampling is site-isolated and distinguishes provider replies from search."""
from app.api.ai_recommendations import _extract_referrals


def test_referral_classifier_keeps_only_known_hosts():
    rows = [
        {"label": "https://chatgpt.com/example", "nb_visits": 6},
        {"label": "chatgpt.com.evil.invalid", "nb_visits": 500},
        {"label": "https://perplexity.ai", "nb_visits": 2, "nb_conversions": 1},
        {"label": "unrelated.example", "nb_visits": 20},
    ]
    result = _extract_referrals(rows)
    assert len(result) == 2
    assert result[0]["host"] == "chatgpt.com"
    assert result[0]["recorded_conversions"] is None
    assert result[1]["recorded_conversions"] == 1


def test_prompt_observations_and_permissions(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "AI test site", "url": fixture_site.url + "/"}).json()
    root = f"/api/sites/{site['id']}/ai-prompt-tests"
    created = client.post(root, headers=auth, json={
        "prompt": "Which providers exist?",
        "brand_terms": ["First Brand"], "competitor_terms": ["Other Brand"]})
    assert created.status_code == 201, created.text
    prompt_id = created.json()["id"]
    saved = client.post(f"{root}/{prompt_id}/samples", headers=auth, json={
        "provider": "chatgpt", "model_name": "unknown",
        "answer": "First Brand provides services. Other Brand is also present."})
    assert saved.status_code == 201, saved.text
    assert saved.json()["brand_matches"] == ["First Brand"]
    assert saved.json()["competitor_matches"] == ["Other Brand"]
    assert saved.json()["verified_search"] is False
    results = client.get(root, headers=auth)
    assert len(results.json()["items"][0]["samples"]) == 1
    assert client.post(f"{root}/{prompt_id}/run", headers=auth).status_code == 422
    assert client.post(root, headers=auth, json={
        "prompt": "abc", "brand_terms": ["A"]}).status_code == 422
    other = client.post("/api/auth/register", json={
        "email": "ai-sample-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(root, headers=h).status_code == 404
    assert client.post(f"{root}/{prompt_id}/samples", headers=h,
                       json={"provider": "manual", "answer": "steal"}).status_code == 404
    assert client.get(f"/api/sites/{site['id']}/ai-referrals", headers=h).status_code == 404
    assert client.delete(f"{root}/{prompt_id}", headers=h).status_code == 404
    # Instance-wide provider credentials must never be usable by regular tenants.
    own_site = client.post("/api/sites", headers=h, json={
        "name": "Non-admin project", "url": fixture_site.url + "/"}).json()
    other_root = f"/api/sites/{own_site['id']}/ai-prompt-tests"
    own_test = client.post(other_root, headers=h, json={
        "prompt": "Who provides this service?", "brand_terms": ["Example"]}).json()
    assert client.post(f"{other_root}/{own_test['id']}/run", headers=h).status_code == 403
    assert client.get(f"/api/sites/{own_site['id']}/ai-referrals", headers=h).status_code == 403
    assert client.delete(f"{root}/{prompt_id}", headers=auth).status_code == 204
