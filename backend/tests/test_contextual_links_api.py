"""API verifies contextual link suggestions respect crawl ownership."""
def test_contextual_link_opportunities_scoped(client, auth, crawled):
    crawl_id = crawled["crawl_id"]
    r = client.get(f"/api/crawls/{crawl_id}/link-opportunities/context", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and "method" in data
    assert all("context_snippet" in item for item in data["items"])
    assert client.get(f"/api/crawls/{crawl_id}/link-opportunities/context", headers=auth,
                      params={"limit": 300}).status_code == 422
    other = client.post("/api/auth/register", json={
        "email": "context-links-tenant@example.com", "password": "correct horse battery"})
    assert other.status_code == 201
    h = {"Authorization": "Bearer " + other.json()["access_token"]}
    assert client.get(f"/api/crawls/{crawl_id}/link-opportunities/context", headers=h).status_code == 404
