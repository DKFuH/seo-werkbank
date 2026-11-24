"""Content Intelligence: measured change, URL share and trend signals."""
from datetime import date, timedelta

from app.db import session_scope
from app.models import GscRow
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
    assert "kein" in found[0]["interpretation"].lower()


def test_trend_marks_new_only_in_observed_sample():
    split = date(2026, 11, 10)
    rows = [row(split + timedelta(days=2), "küchenfronten", "https://example.de/a", 110, 3, 5)]
    found = trends(rows, split)
    assert len(found) == 1
    assert found[0]["new_in_sample"] is True
    assert "GSC" in found[0]["interpretation"]


def test_site_isolation_and_api_preference(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = crawled["base"]
    with session_scope() as db:
        db.add_all([
            GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 2),
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
