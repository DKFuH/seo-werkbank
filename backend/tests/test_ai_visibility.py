"""AI visibility is manual, site-isolated and does not imply live provider measurements."""
def test_manual_ai_visibility_lifecycle(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "AI sample site", "url": fixture_site.url + "/"}).json()
    path = f"/api/sites/{site['id']}/ai-visibility/observations"
    r = client.post(path, headers=auth, json={"platform": "chatgpt", "prompt": "Was ist die beste Lösung?",
                                               "brand_mentioned": True, "cited_url": "https://example.com/story",
                                               "response_excerpt": "Beispielantwort"})
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["source"] == "manual" and o["verified"] is False
    assert o["brand_mentioned"] is True and o["cited_url"] == "https://example.com/story"
    assert client.get(path, headers=auth).json()["items"][0]["id"] == o["id"]
    assert not client.get(path, headers=auth, params={"platform": "claude"}).json()["items"]
    assert client.post(path, headers=auth, json={"platform": "made_up", "prompt": "Test"}).status_code == 422
    other = client.post("/api/auth/register", json={"email": "ai-visibility-tenant@example.com",
                                                  "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path, headers=h).status_code == 404
    assert client.delete(path + "/" + str(o["id"]), headers=h).status_code == 404
    assert client.delete(path + "/" + str(o["id"]), headers=auth).status_code == 204
    assert client.get(path, headers=auth).json()["items"] == []
