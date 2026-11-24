"""Content Intelligence: measured change, URL share and trend signals."""
from datetime import date, timedelta

from app.db import session_scope
from app.models import GscRow, SearchProviderSnapshot
from app.services.content_intelligence import cannibalisation, decay, trends


def row(day, query, page, impressions, clicks, position):
    return {"day": day, "query": query, "page": page,
            "impressions": impressions, "clicks": clicks, "position": position}


def test_decay_signal_and_equal_period_comparison():
    split = date(2026, 11, 10)
    records = [
        row(split - timedelta(days=3), "küche", "https://example.de/a", 150, 30, 3),
        row(split + timedelta(days=3), "küche", "https://example.de/a", 140, 8, 11),
    ]
    found = decay(records, split)
    assert len(found) == 1
    assert found[0]["signal"] == "positionsverlust"
    assert found[0]["delta"]["clicks_pct"] < -50


def test_url_switch_is_not_called_proven_cannibalisation():
    split = date(2026, 11, 10)
    a, b = "https://example.de/a", "https://example.de/b"
    rows = [
        row(split - timedelta(days=2), "küche modern", a, 100, 5, 5),
        row(split - timedelta(days=2), "küche modern", b, 25, 1, 9),
        row(split + timedelta(days=2), "küche modern", a, 20, 1, 11),
        row(split + timedelta(days=2), "küche modern", b, 140, 8, 4),
    ]
    found = cannibalisation(rows, split)
    assert found[0]["leader_changed"] is True
    assert found[0]["previous_leader"] == a
    assert found[0]["current_leader"] == b
    assert "ohne schädliche" in found[0]["interpretation"].lower()


def test_trend_marks_new_only_in_observed_sample():
    split = date(2026, 11, 10)
    rows = [row(split + timedelta(days=2), "küchenfronten", "https://example.de/a", 110, 3, 5)]
    found = trends(rows, split)
    assert len(found) == 1
    assert found[0]["new_in_sample"] is True
    assert "GSC" in found[0]["interpretation"]


def test_site_isolation_and_api_preference(client, auth, fixture_site):
    base = fixture_site.url
    created = client.post("/api/sites", headers=auth, json={"name": "Content Intelligence isolated", "url": base + "/"})
    assert created.status_code == 201, created.text
    sid = created.json()["id"]
    with session_scope() as db:
        db.add_all([
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 10, 15),
                   query="küchen Ideen", page=base + "/about", impressions=100,
                   clicks=30, position=3),
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 25),
                   query="küchen Ideen", page=base + "/about", impressions=90,
                   clicks=5, position=10),
            GscRow(site_id=sid, dataset="query_page", source="csv", day=date(2026, 11, 25),
                   query="küchen Ideen", page=base + "/about", impressions=1000,
                   clicks=300, position=1),
        ])
    r = client.get(f"/api/sites/{sid}/content-intelligence?days=28", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_data"] and data["source"] == "api"
    assert data["decay"] and data["decay"][0]["url"] == base + "/about"
    another = client.post("/api/auth/register", json={
        "email": "content-intelligence-other@example.com",
        "password": "correct horse battery"}).json()
    other_auth = {"Authorization": "Bearer " + another["access_token"]}
    assert client.get(f"/api/sites/{sid}/content-intelligence", headers=other_auth).status_code == 404


def test_content_intelligence_can_select_bing(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "Bing Content", "url": fixture_site.url}).json()
    target = fixture_site.url + "/bing-content"
    with session_scope() as db:
        db.add(SearchProviderSnapshot(
            site_id=site["id"], provider="bing", operation="page_queries",
            property_url=fixture_site.url, parameters={"url": target},
            payload={"data": [
                {"Date": "2026-10-11", "Query": "bing content", "Clicks": 10, "Impressions": 50, "AvgImpressionPosition": 3},
                {"Date": "2026-10-18", "Query": "bing content", "Clicks": 10, "Impressions": 50, "AvgImpressionPosition": 3},
                {"Date": "2026-10-25", "Query": "bing content", "Clicks": 2, "Impressions": 45, "AvgImpressionPosition": 10},
                {"Date": "2026-11-01", "Query": "bing content", "Clicks": 5, "Impressions": 90, "AvgImpressionPosition": 10},
            ]},
        ))
        db.commit()
    response = client.get(
        f"/api/sites/{site['id']}/content-intelligence?days=14&provider=bing", headers=auth,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["has_data"] is True
    assert result["provider"] == "bing"
    assert result["provider_label"] == "Bing Webmaster Tools"
    assert result["source"] == "snapshot"
    assert result["decay"][0]["url"] == target
