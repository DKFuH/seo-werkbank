"""Generic research planning must be site-isolated and provenance-aware."""
def test_topic_question_journey_and_tenant(client, auth, crawled):
    sid = crawled["site"]["id"]
    path = f"/api/sites/{sid}/research"
    topic = client.post(path, headers=auth, json={
        "kind": "topic_map", "title": "Ceramic surfaces", "payload": {
            "offer": "Design surfaces", "attributes": ["ceramic countertop", "stone finish"]}})
    assert topic.status_code == 201, topic.text
    question = client.post(path, headers=auth, json={
        "kind": "paa_question", "title": "How to care", "payload": {
            "topic": "Ceramic surfaces", "question": "How do I clean ceramic surfaces?"}})
    assert question.status_code == 201, question.text
    journey = client.post(path, headers=auth, json={
        "kind": "search_journey", "title": "Read to choose", "payload": {
            "source_url": crawled["base"] + "/", "target_url": crawled["base"] + "/about/",
            "stage": "consideration"}})
    assert journey.status_code == 201, journey.text
    assert client.get(f"{path}/topic-coverage", headers=auth).status_code == 200
    assert client.get(f"{path}/question-tree", headers=auth).json()["topics"][0]["questions"][0]["question"].startswith("How")
    assert client.get(f"{path}/journeys", headers=auth).json()["items"][0]["stage"] == "consideration"
    invalid = client.post(path, headers=auth, json={
        "kind": "topic_map", "title": "Unknown", "payload": {"offer": "x"}})
    assert invalid.status_code == 422
    invalid_stage = client.post(path, headers=auth, json={
        "kind": "search_journey", "title": "Unknown", "payload": {"source_url": "a", "target_url": "b", "stage": "magic"}})
    assert invalid_stage.status_code == 422
    edited = client.patch(f"{path}/{topic.json()['id']}", headers=auth, json={"title": "Better topic"})
    assert edited.status_code == 200 and edited.json()["title"] == "Better topic"
    other = client.post("/api/auth/register", json={
        "email": "research-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path, headers=h).status_code == 404
    assert client.get(f"{path}/topic-coverage", headers=h).status_code == 404
    assert client.patch(f"{path}/{topic.json()['id']}", headers=h, json={"title": "Steal"}).status_code == 404
    assert client.delete(f"{path}/{topic.json()['id']}", headers=h).status_code == 404
