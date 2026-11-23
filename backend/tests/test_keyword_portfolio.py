"""Keyword portfolio from Search Console: summary, movement, buckets, discoveries, adoption, device filter, journal."""
from __future__ import annotations

from datetime import date, timedelta

from app.db import session_scope
from app.models import GscRow

END = date(2026, 11, 20)


def _rows(site_id: int, query: str, page: str, position_now: float, position_before: float, impressions: int, clicks: int = 1,
          device_rows: bool = False) -> list[GscRow]:
    out = []
    for offset, pos in ((0, position_now), (28, position_before)):  # one day in the current and one in the previous 28-day period
        day = END - timedelta(days=offset)
        out.append(GscRow(site_id=site_id, dataset="query_page", source="api", day=day, query=query, page=page,
                          clicks=clicks, impressions=impressions, position=pos))
        if device_rows:
            out.append(GscRow(site_id=site_id, dataset="query_device", source="api", day=day, query=query, device="mobile",
                              clicks=clicks, impressions=impressions, position=pos + 1))
    return out


def _site(client, auth, fixture_site, name: str) -> int:
    return client.post("/api/sites", headers=auth, json={"name": name, "url": fixture_site.url + "/"}).json()["id"]


def test_portfolio_and_all_queries(client, auth, fixture_site):
    sid = _site(client, auth, fixture_site, "Portfolio")
    base = fixture_site.url
    with session_scope() as db:
        db.add_all([
            *_rows(sid, "Küche planen", base + "/kuechen", 4.0, 9.0, 200, 10, device_rows=True),    # tracked, improved
            *_rows(sid, "einbauschrank", base + "/schrank", 15.0, 12.0, 80, 2),                     # tracked, worsened, wrong URL
            *_rows(sid, "tischler simmern", base + "/", 2.0, 2.0, 50, 9),                           # untracked top-3 discovery
            *_rows(sid, "küchenarbeitsplatte", base + "/platten", 8.0, 11.0, 30, 1),                # untracked opportunity
            *_rows(sid, "seltene suche", base + "/x", 6.0, 6.0, 4, 0),                              # untracked, small sample
        ])
    root = f"/api/sites/{sid}/rank-gsc"
    assert client.post(f"{root}/keywords", headers=auth, json={"keyword": "küche planen", "label": "lokal", "target_url": "/kuechen"}).status_code == 201
    assert client.post(f"{root}/keywords", headers=auth, json={"keyword": "Einbauschrank", "label": "national", "target_url": "/einbauschrank/", "priority": 1}).status_code == 201

    r = client.get(f"{root}/portfolio", headers=auth, params={"days": 28})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["has_data"] and p["period"]["end"] == END.isoformat() and p["labels"] == ["lokal", "national"]
    rows = {r["keyword"]: r for r in p["rows"]}
    assert rows["küche planen"]["position"] == 4.0 and rows["küche planen"]["movement"] == 5.0 and rows["küche planen"]["bucket"] == "4–10"
    assert rows["einbauschrank"]["movement"] == -3.0 and rows["einbauschrank"]["url_mismatch"] is True
    assert rows["küche planen"]["url_mismatch"] is False and rows["küche planen"]["best_url"] == base + "/kuechen"
    s = p["summary"]
    assert s["improved"] == 1 and s["worsened"] == 1 and s["buckets"]["4–10"] == 1 and s["buckets"]["11–20"] == 1
    assert s["impressions"] == 280 and s["position"] == round((4 * 200 + 15 * 80) / 280, 2)
    assert p["trend"] and p["granularity"] == "day"
    assert [r["keyword"] for r in p["rows"]][0] == "einbauschrank"  # priority 1 first
    assert len(client.get(f"{root}/portfolio", headers=auth, params={"label": "lokal"}).json()["rows"]) == 1

    a = client.get(f"{root}/queries", headers=auth).json()
    by_q = {r["query"]: r for r in a["rows"]}
    assert a["summary"]["queries"] == 5 and a["summary"]["untracked"] == 3
    assert a["summary"]["top_discoveries"] == 1 and a["summary"]["opportunities"] == 1
    assert by_q["tischler simmern"]["top_discovery"] and by_q["küchenarbeitsplatte"]["opportunity"]
    assert not by_q["seltene suche"]["opportunity"]  # under 10 impressions
    assert by_q["küche planen"]["tracked"] and by_q["küche planen"]["keyword_id"]
    only = client.get(f"{root}/queries", headers=auth, params={"bucket": "opportunity"}).json()
    assert [r["query"] for r in only["rows"]] == ["küchenarbeitsplatte"]
    by_pos = client.get(f"{root}/queries", headers=auth, params={"sort": "position", "dir": "asc", "scope": "untracked"}).json()
    assert [r["query"] for r in by_pos["rows"]] == ["tischler simmern", "seltene suche", "küchenarbeitsplatte"]

    adopted = client.post(f"{root}/adopt", headers=auth, json={"query": "tischler simmern"})
    assert adopted.status_code == 201
    kid = adopted.json()["id"]
    p2 = client.get(f"{root}/portfolio", headers=auth).json()
    assert {r["keyword"]: r for r in p2["rows"]}["tischler simmern"]["position"] == 2.0  # history comes along

    mobile = client.get(f"{root}/portfolio", headers=auth, params={"device": "mobile"}).json()
    assert {r["keyword"]: r for r in mobile["rows"]}["küche planen"]["position"] == 5.0 and mobile["device_data"]

    note = client.post(f"{root}/keywords/{kid}/notes", headers=auth, json={"event_date": "2026-11-10", "title": "Title überarbeitet"})
    assert note.status_code == 201
    d = client.get(f"{root}/keywords/{kid}", headers=auth, params={"days": 28}).json()
    assert d["keyword"]["keyword"] == "tischler simmern" and d["notes"][0]["title"] == "Title überarbeitet" and d["trend"]
    assert client.delete(f"{root}/keywords/{kid}/notes/{note.json()['id']}", headers=auth).status_code == 204
    assert client.patch(f"{root}/keywords/{kid}", headers=auth, json={"tracked": False}).json()["tracked"] is False


def test_german_sharp_s_is_kept():
    from app.services.rank_portfolio import norm
    assert norm("  Einbauschrank nach  Maß ") == "einbauschrank nach maß"


def test_portfolio_without_data_and_isolation(client, auth, fixture_site):
    sid = _site(client, auth, fixture_site, "Leer")
    root = f"/api/sites/{sid}/rank-gsc"
    client.post(f"{root}/keywords", headers=auth, json={"keyword": "küche"})
    p = client.get(f"{root}/portfolio", headers=auth).json()
    assert p["has_data"] is False and p["rows"][0]["position"] is None
    assert client.get(f"{root}/portfolio", headers=auth, params={"device": "mobile"}).status_code == 200
    other = client.post("/api/auth/register", json={"email": "portfolio-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(f"{root}/portfolio", headers=h).status_code == 404
    assert client.post(f"{root}/adopt", headers=h, json={"query": "x"}).status_code == 404
