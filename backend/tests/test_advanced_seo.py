from app.api.advanced_seo import overlap


def test_overlap_math_without_claiming_page_strategy():
    out = overlap(["https://a.test/x", "https://b.test/y"], ["https://b.test/y", "https://c.test/z"])
    assert out["common_count"] == 1
    assert out["jaccard"] == 0.333
    assert out["overlap_of_smaller"] == 0.5
    assert "hint" in out["interpretation"]


def test_advanced_site_isolation(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Advanced audits", "url": fixture_site.url}).json()
    path = f"/api/sites/{site['id']}/advanced"
    check = client.post(path + "/serp-overlap", headers=auth, json={
        "first_keyword": "furniture design", "second_keyword": "office furniture",
        "manual_urls_first": ["https://example.org/a", "https://example.org/b"],
        "manual_urls_second": ["https://example.org/b"]})
    assert check.status_code == 200, check.text
    assert check.json()["result"]["common_count"] == 1
    assert check.json()["provider"] == "manual"
    for endpoint in ("pagination", "schema-review"):
        assert client.get(path + "/" + endpoint, headers=auth).json()["crawl_id"] is None
    other = client.post("/api/auth/register", json={
        "email": "advanced-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path + "/pagination", headers=h).status_code == 404
    assert client.post(path + "/serp-overlap", headers=h, json={
        "first_keyword": "furniture design", "second_keyword": "office furniture"}).status_code == 404
    assert client.post(path + "/relaunch", headers=h, json={
        "old_crawl_id": 1, "new_crawl_id": 2}).status_code == 404
