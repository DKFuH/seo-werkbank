"""Content proof and CRO checks must distinguish evidence presence from verification."""
def test_content_evidence_cro_and_asset_review(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = f"/api/sites/{sid}/research"
    page = crawled["base"] + "/"
    data = [
        {"kind": "content_evidence", "title": "Manufacturing claim",
         "payload": {"page_url": page, "claim": "Made of material X"}},
        {"kind": "cro_review", "title": "Hero review",
         "payload": {"page_url": page, "criterion": "clear CTA", "result": "not checked"}},
        {"kind": "comparison", "title": "Material difference",
         "payload": {"subject_a": "A", "subject_b": "B", "criterion": "durability"}},
        {"kind": "asset_brief", "title": "Useful widget",
         "payload": {"purpose": "help calculate", "audience": "homeowners", "format": "calculator"}},
    ]
    for entry in data:
        r = client.post(base, json=entry, headers=auth)
        assert r.status_code == 201, r.text
    evidence = client.get(base + "/content-evidence", headers=auth).json()
    assert evidence["items"][0]["source_links_missing"] == 1
    assert evidence["items"][0]["claims"][0]["verified"] is False
    cro = client.get(base + "/cro-audit", headers=auth)
    assert cro.status_code == 200, cro.text
    assert cro.json()["crawl_id"] is not None
    assert cro.json()["items"][0]["not_examined"]
    comparison = client.get(base + "/comparison-review", headers=auth).json()
    assert comparison["items"][0]["needs_source"] is True
    assets = client.get(base + "/asset-briefs", headers=auth).json()
    assert "success_metric" in assets["items"][0]["missing_specifications"]
    other = client.post("/api/auth/register", json={
        "email": "research-content-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    for path in ("/content-evidence", "/cro-audit", "/comparison-review", "/asset-briefs"):
        assert client.get(base + path, headers=h).status_code == 404
