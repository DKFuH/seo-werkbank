"""Content-refresh query/page matching and editorial signal tests."""
from __future__ import annotations

from datetime import date

from app.db import session_scope
from app.models import GscRow
from app.services.content_refresh import build_refresh_pages, page_key


def test_page_keys_are_conservative():
    assert page_key("https://Example.de/ratgeber/a/") == page_key("https://example.de/ratgeber/a/")
    assert page_key("https://example.de/ratgeber/a/") != page_key("https://example.de/ratgeber/a")
    assert page_key("https://example.de/a?x=1") != page_key("https://example.de/a?x=2")
    assert page_key("http://example.de/a") != page_key("https://example.de/a")
    assert page_key("file:///etc/passwd") is None
    assert page_key("https://u:p@example.de/x") is None


def test_editorial_signals_not_claims():
    rows = [{"page": "https://example.de/kueche/", "query": "keramik arbeitsplatte pflegen",
             "clicks": 3, "impressions": 250, "position": 8.2}]
    crawled = {page_key("https://example.de/kueche/"): {"title": "Küche", "headings": [
        {"level": 2, "text": "Keramik-Arbeitsplatten"}], "text": "Arbeitsplatte aus Keramik pflegen"}}
    out = build_refresh_pages(rows, crawled)
    assert out["total_pages"] == 1
    q = out["pages"][0]["queries"][0]
    assert q["type"] == "striking_distance"
    assert q["estimated_extra_clicks"] > 0
    assert q["mentioned_in_body"] is True
    assert q["review_terms"]  # this remains a lexical hint, not a fact claim


def test_no_inferred_page_and_no_unqualified_opportunity():
    rows = [{"page": None, "query": "küche", "impressions": 9000, "clicks": 0, "position": 8},
            {"page": "https://example.de/", "query": "unrelevant", "impressions": 9, "clicks": 0, "position": 8}]
    assert build_refresh_pages(rows)["pages"] == []


def test_content_refresh_api_and_unpaired_csv(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "Content refresh test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    csv = ("Suchanfrage,Seite,Datum,Klicks,Impressionen,Position\n"
           f"keramik arbeitsplatte,{fixture_site.url}/about/,20.11.2026,2,40,10\n"
           f"keramik arbeitsplatte,{fixture_site.url}/about/,21.11.2026,8,160,5\n"
           f"historisch,{fixture_site.url}/about/,01.06.2026,1,100,5\n")
    upload = client.post(f"/api/sites/{sid}/gsc/import", headers=auth,
                         files={"file": ("pairs.csv", csv.encode("utf-8"), "text/csv")})
    assert upload.status_code in (200, 201), upload.text
    r = client.get(f"/api/sites/{sid}/content-refresh", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_data"] and data["source"] == "csv"
    assert data["start_date"] == "2026-10-25" and data["end_date"] == "2026-11-21"
    assert len(data["pages"]) == 1
    q = data["pages"][0]["queries"][0]
    assert q["impressions"] == 200 and q["clicks"] == 10 and q["position"] == 6.0

    # Same query/page appears in API and CSV: never double count the two sources.
    with session_scope() as db:
        db.add(GscRow(site_id=sid, dataset="query_page", source="api", day=date(2026, 11, 21),
                      query="keramik arbeitsplatte", page=f"{fixture_site.url}/about/",
                      clicks=1, impressions=100, position=7))
    only_api = client.get(f"/api/sites/{sid}/content-refresh", headers=auth).json()
    assert only_api["source"] == "api"
    assert only_api["pages"][0]["queries"][0]["impressions"] == 100
    assert any("nicht addiert" in n for n in only_api["notes"])

    other = client.post("/api/auth/register", json={
        "email": "content-refresh-scope@example.com", "password": "correct horse battery"})
    assert other.status_code == 201, other.text
    other_auth = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get(f"/api/sites/{sid}/content-refresh", headers=other_auth).status_code == 404

    lone = client.post("/api/sites", headers=auth, json={"name": "Unpaired GSC", "url": fixture_site.url + "/"}).json()
    unpaired = "Suchanfrage,Klicks,Impressionen,Position\nkeramik,1,40,8\n"
    assert client.post(f"/api/sites/{lone['id']}/gsc/import", headers=auth,
                       files={"file": ("queries.csv", unpaired.encode(), "text/csv")}).status_code in (200, 201)
    u = client.get(f"/api/sites/{lone['id']}/content-refresh", headers=auth).json()
    assert u["has_data"] is False and u["unpaired_rows"] >= 1
    assert client.get(f"/api/sites/{sid}/content-refresh").status_code == 401
