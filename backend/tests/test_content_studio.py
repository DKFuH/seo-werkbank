"""Case studies create review-only drafts and experiments do not infer causality."""
def test_content_studio_evidence_and_tenant(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Content studio test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    path = f"/api/sites/{sid}"
    entries = [
        {"kind": "case_study", "title": "Test case", "payload": {
            "project": "Demo project", "challenge": "Small space",
            "approach": "Measured twice", "outcome": "Customer reported useful layout",
            "target_url": fixture_site.url + "/case-study"}},
        {"kind": "buyer_question", "title": "Real question", "payload": {
            "question": "What is the cost?", "context": "General consultation", "audience": "Homeowners"}},
        {"kind": "brand_claim", "title": "Review a claim", "payload": {
            "subject": "Company", "claim": "Full service", "source_url": "https://example.org/company",
            "expected_statement": "Full service"}},
        {"kind": "marketing_experiment", "title": "Test CTA", "payload": {
            "hypothesis": "CTA raises inquiries", "metric": "forms", "unit": "submissions",
            "start_date": "2026-11-01", "baseline": "3", "followup": "5", "cost": "25.5"}},
    ]
    case_id = None
    for entry in entries:
        r = client.post(path + "/research", headers=auth, json=entry)
        assert r.status_code == 201, r.text
        if entry["kind"] == "case_study":
            case_id = r.json()["id"]
    data = client.get(path + "/content-studio", headers=auth)
    assert data.status_code == 200, data.text
    result = data.json()
    assert result["cases"][0]["verified"] is False
    assert result["buyer_questions"][0]["questions"][0]["question"] == "What is the cost?"
    assert result["brand_claims"][0]["lexically_matching"] is True
    assert result["brand_claims"][0]["source_verified"] is False
    assert result["experiments"][0]["observed_difference"] == 2
    assert result["experiments"][0]["causal_effect_established"] is False
    draft = client.post(f"{path}/content-studio/case-studies/{case_id}/draft", headers=auth)
    assert draft.status_code == 201, draft.text
    response = draft.json()
    assert response["proposal_status"] == "draft"
    assert response["remote_publication"] is False
    proposal = client.get(f"{path}/seo-work/{response['work_item_id']}/content-proposal", headers=auth)
    assert proposal.status_code == 200
    assert proposal.json()["status"] == "draft"
    assert "Measured twice" in proposal.json()["proposed_text"]
    assert client.post(f"{path}/content-studio/case-studies/{case_id}/draft", headers=auth).status_code == 409
    other = client.post("/api/auth/register", json={
        "email": "content-studio-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path + "/content-studio", headers=h).status_code == 404
    assert client.post(f"{path}/content-studio/case-studies/{case_id}/draft", headers=h).status_code == 404
