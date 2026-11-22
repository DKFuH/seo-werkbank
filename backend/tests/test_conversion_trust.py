"""Review funnel records, trust sources, and site tenant boundaries."""
def test_conversion_trust_evidence_and_isolation(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = f"/api/sites/{sid}"
    page = crawled["base"] + "/"
    for item in (
        {"kind": "funnel_step", "title": "Request consultation",
         "payload": {"page_url": page, "stage": "conversion", "action": "Submit form",
                     "action_url": crawled["base"] + "/contact/"}},
        {"kind": "trust_proof", "title": "Certification",
         "payload": {"page_url": page, "claim": "Certified professional"}},
        {"kind": "brand_profile", "title": "Positioning",
         "payload": {"brand_name": "Test", "positioning": "Professional", "offer": "Consulting"}},
    ):
        r = client.post(base + "/research", headers=auth, json=item)
        assert r.status_code == 201, r.text
    result = client.get(base + "/conversion-trust", headers=auth)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["sources"] == {"funnel_steps": 1, "trust_proofs": 1, "brand_profiles": 1}
    assert data["pages"][0]["proofs_without_source"] == 1
    assert data["pages"][0]["steps"][0]["stage"] == "conversion"
    assert "awareness" in data["pages"][0]["missing_stages"]
    assert data["brand_profiles"][0]["verified"] is False
    assert data["pages"][0]["requires_manual_review"]
    r = client.post(base + "/research", headers=auth, json={
        "kind": "funnel_step", "title": "Missing action", "payload": {"page_url": page, "stage": "decision"}})
    assert r.status_code == 422
    other = client.post("/api/auth/register", json={
        "email": "trust-other@example.com", "password": "correct horse battery"}).json()
    other_auth = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(base + "/conversion-trust", headers=other_auth).status_code == 404
