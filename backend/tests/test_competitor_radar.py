"""Competitor radar uses actual crawled pages, with strict site ownership."""
from app.db import session_scope
from app.models import Competitor, Crawl, Page


def test_competitor_radar_requires_crawl_and_scope(client, auth, fixture_site):
    url = fixture_site.url + "/"
    site = client.post("/api/sites", headers=auth, json={"name": "Radar test", "url": url}).json()
    sid = site["id"]
    endpoint = f"/api/sites/{sid}/competitor-topic-radar"
    missing = client.get(endpoint, headers=auth)
    assert missing.status_code == 200
    assert not missing.json()["has_data"]
    with session_scope() as db:
        own = Crawl(site_id=sid, start_url=url, status="completed")
        db.add(own)
        db.flush()
        db.add(Page(crawl_id=own.id, url=url, title="Lokale Küche nach Maß", h1="Küche",
                    indexable=True, is_html=True, status_code=200))
        competitor = Competitor(site_id=sid, name="Example competitor", url="https://competitor.example",
                                domain="competitor.example")
        db.add(competitor)
        db.flush()
        crawl = Crawl(site_id=sid, competitor_id=competitor.id, start_url=competitor.url, status="completed")
        db.add(crawl)
        db.flush()
        db.add(Page(crawl_id=crawl.id, url="https://competitor.example/keramik",
                    title="Keramik Arbeitsplatten pflegen", h1="Keramik Arbeitsplatten pflegen",
                    indexable=True, is_html=True, status_code=200))
    r = client.get(endpoint, headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_data"] and data["competitors_with_crawl"] == 1
    assert any(t["term"] == "keramik arbeitsplatten" for t in data["topics"])
    assert all(t["examples"][0]["competitor"] == "Example competitor" for t in data["topics"])
    other = client.post("/api/auth/register", json={
        "email": "radar-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(endpoint, headers=h).status_code == 404
    assert client.get(endpoint, headers=auth, params={"limit": 400}).status_code == 422
