"""Content proposals remain human-controlled, with no remote publication."""
def test_content_proposal_approval_and_isolation(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Editorial workflow", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    item = client.post(f"/api/sites/{sid}/seo-work", headers=auth, json={
        "kind": "content", "title": "Rewrite intro", "target_url": fixture_site.url + "/"}).json()
    path = f"/api/sites/{sid}/seo-work/{item['id']}/content-proposal"
    r = client.get(path, headers=auth)
    assert r.status_code == 200 and r.json()["exists"] is False

    assert client.post(path + "/approve", headers=auth).status_code == 409
    assert client.post(path + "/mark-published", headers=auth).status_code == 409

    created = client.put(path, headers=auth, json={
        "original_text": "Original intro", "proposed_text": "Helpful revised intro", "rationale": "Add clarity"})
    assert created.status_code == 200, created.text
    draft = created.json()
    assert draft["status"] == "draft" and draft["remote_publication"] is False
    assert any("Helpful revised intro" in line for line in draft["diff"])
    assert client.post(path + "/mark-published", headers=auth).status_code == 409

    approved = client.post(path + "/approve", headers=auth)
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert approved.json()["approved_at"]
    assert client.put(path, headers=auth, json={"proposed_text": "Overwrite approved"}).status_code == 409

    reopened = client.post(path + "/reopen", headers=auth)
    assert reopened.status_code == 200 and reopened.json()["status"] == "draft"
    assert reopened.json()["approved_at"] is None
    edited = client.put(path, headers=auth, json={"original_text": "Original intro",
                                                   "proposed_text": "New reviewed draft", "rationale": "Better"})
    assert edited.status_code == 200
    assert client.post(path + "/approve", headers=auth).status_code == 200
    published = client.post(path + "/mark-published", headers=auth)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["marked_published_at"]
    assert published.json()["remote_publication"] is False
    assert client.post(path + "/reopen", headers=auth).status_code == 409

    other = client.post("/api/auth/register", json={"email": "proposal-other@example.com",
                                                    "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path, headers=h).status_code == 404
    assert client.put(path, headers=h, json={"proposed_text": "Steal"}).status_code == 404
    assert client.post(path + "/approve", headers=h).status_code == 404
