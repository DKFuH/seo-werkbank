"""Research monitoring stays site-scoped and does not fabricate Google or AI measurements."""
from datetime import datetime

from app.db import session_scope
from app.models import AiVisibilityObservation, RankObservation, RankTarget


def test_change_index_serp_and_geo(client, auth, crawled):
    sid = crawled["site"]["id"]
    path = f"/api/sites/{sid}/research"
    entries = [
        ("update_event", {"event_date": "2026-11-15", "event_type": "site change", "description": "new content"}),
        ("serp_feature", {"keyword": "example", "provider": "manual", "features": ["FAQ"]}),
        ("indexing", {"page_url": crawled["base"] + "/", "status": "indexed"}),
        ("geo_sample", {"platform": "chatgpt", "prompt": "test", "response": "example",
                        "cited_urls": ["https://source.example/"]}),
    ]
    for kind, payload in entries:
        r = client.post(path, headers=auth, json={"kind": kind, "title": kind, "payload": payload})
        assert r.status_code == 201, r.text
    with session_scope() as db:
        target = RankTarget(site_id=sid, keyword="tracked", engine="google", country="de",
                            language="de", device="desktop")
        db.add(target)
        db.flush()
        db.add_all([
            RankObservation(target_id=target.id, observed_at=datetime(2026, 11, 12),
                            provider="manual", position=8, search_depth=10),
            RankObservation(target_id=target.id, observed_at=datetime(2026, 11, 18),
                            provider="manual", position=5, search_depth=10, serp_features=["FAQ"]),
            AiVisibilityObservation(site_id=sid, platform="chatgpt", prompt="test",
                                    brand_mentioned=True, cited_url="https://source.example/"),
        ])
    timeline = client.get(path + "/change-timeline", headers=auth)
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["items"][0]["comparison"][0]["delta"] == 3
    features = client.get(path + "/serp-features", headers=auth).json()
    assert any("FAQ" in p["features"] for p in features["sources"])
    indexing = client.get(path + "/indexing-review", headers=auth).json()
    assert indexing["items"][0]["verified_google_index_status"] is False
    citations = client.get(path + "/geo-citations", headers=auth).json()
    assert citations["platforms"][0]["citations"][0]["sample_count"] == 2
    other = client.post("/api/auth/register", json={
        "email": "research-monitor-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    for name in ["change-timeline", "serp-features", "indexing-review", "geo-citations"]:
        assert client.get(path + "/" + name, headers=h).status_code == 404
