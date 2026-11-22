from app.api.diagnostics import image_hints


def test_image_hints_provenance():
    records = [
        {"src": "/hero.jpg", "loading": "lazy", "has_dimensions": False},
        {"src": "/second.jpg", "loading": "eager", "has_dimensions": True},
        {"src": "/third.jpg", "loading": "lazy", "has_dimensions": True},
    ]
    flagged = image_hints(records)
    assert len(flagged) == 1
    assert len(flagged[0]["warnings"]) == 2
    assert flagged[0]["confirmed_lcp"] is False


def test_diagnostics_ownership_and_no_crawl(client, auth, fixture_site):
    own = client.post("/api/sites", headers=auth, json={"name": "Scan", "url": fixture_site.url}).json()
    url = f"/api/sites/{own['id']}/diagnostics"
    response = client.get(url + "/images", headers=auth)
    assert response.status_code == 200
    assert response.json()["pages"] == []
    other = client.post("/api/auth/register", json={
        "email": "diagnostics-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(url + "/images", headers=h).status_code == 404
    assert client.post(url + "/render", headers=h, json={"url": fixture_site.url}).status_code == 404
    assert client.post(url + "/consent", headers=auth, json={"url": "https://not-owned.example"}).status_code == 422
    assert client.post(url + "/consent", headers=auth, json={
        "url": fixture_site.url, "choices": ["initial", "initial"]}).status_code == 422
