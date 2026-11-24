"""Content-gap classification and GSC/crawl integration regression tests."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.db import session_scope
from app.models import GscRow, Page
from app.services.content_gap import analyze


def _page(url: str, title: str, h1: str, body: str) -> dict:
    return {"url": url, "title": title, "h1": h1,
            "headings": [{"level": 2, "text": h1}], "text": body}


def _pair(query: str, url: str, impressions: int = 100, position: float = 8) -> dict:
    return {"query": query, "page": url, "impressions": impressions,
            "clicks": 3, "position": position}


def test_no_false_gap_when_ranked_page_covers_topic():
    pages = [_page("https://example.de/ratgeber/installationszonen/", "Installationszonen Küche",
                   "Installationszonen Küche", "Installationszonen Küche Vorschriften")]
    x = analyze([_pair("installationszonen küche", pages[0]["url"])], pages)
    assert x["clusters"][0]["category"] == "no_action"
    assert x["clusters"][0]["queries"][0]["ranked_crawl_found"]


def test_partial_coverage_suggests_expanding_not_new_page():
    pages = [_page("https://example.de/elektro/", "Elektro Küche", "Elektro Küche",
                   "Stromkreise für eine Küche")]
    x = analyze([_pair("stromkreise küche", pages[0]["url"])], pages)
    assert x["clusters"][0]["category"] in ("expand", "review")
    assert x["clusters"][0]["category"] != "new_candidate"


def test_uncrawled_ranked_url_is_review_not_new_article():
    pages = [_page("https://example.de/a/", "Andere Seite", "Sonstiges", "Sonstiges")]
    x = analyze([_pair("installationszonen küche", "https://example.de/missing/")], pages)
    assert x["clusters"][0]["category"] == "review"
    assert x["clusters"][0]["queries"][0]["ranked_crawl_found"] is False


def test_multiple_gsc_landing_urls_flagged_not_declared_cannibalisation():
    pages = [
        _page("https://example.de/a/", "Stromkreise", "Stromkreise", "Elektro"),
        _page("https://example.de/b/", "Elektro", "Elektro", "Stromkreise"),
    ]
    x = analyze([_pair("stromkreise küche", pages[0]["url"], 60),
                 _pair("stromkreise küche", pages[1]["url"], 40)], pages)
    q = x["clusters"][0]["queries"][0]
    assert q["multiple_landing_urls"]
    assert q["ranked_url"] == pages[0]["url"]
    assert q["impressions"] == 100
    assert q["position"] == 8
    assert len(q["landing_urls"]) == 2


def test_german_diacritics_and_keyword_variants_are_not_search_volume():
    pages = [_page("https://example.de/kuche/", "Küche", "Küche", "Küchen")]
    x = analyze([_pair("küche elektro installation", pages[0]["url"], 30),
                 _pair("elektro installation küche", pages[0]["url"], 40)], pages)
    assert x["total_clusters"] == 1
    assert x["clusters"][0]["impressions"] == 70
    assert "Suchvolumen" in x["method"]


def test_zero_impressions_and_unknown_page_not_invented():
    x = analyze([_pair("neue küche", "https://example.de/a/", 0),
                 {"query": "küche", "page": None, "impressions": 50}], [])
    assert x["total_clusters"] == 0


def test_api_requires_paired_rows_last_crawl_and_site_isolation(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = crawled["base"]
    endpoint = f"/api/sites/{sid}/content-gap"
    response = client.get(endpoint, headers=auth)
    assert response.status_code == 200
    assert response.json()["has_data"] is False

    with session_scope() as db:
        db.add_all([
            GscRow(site_id=sid, dataset="query_page", source="csv",
                   day=date(2026, 11, 20), query="installationszonen küche",
                   page=base + "/about", impressions=60, clicks=2, position=9),
            GscRow(site_id=sid, dataset="query_page", source="api",
                   day=date(2026, 11, 21), query="installationszonen küche",
                   page=base + "/about", impressions=40, clicks=1, position=11),
            GscRow(site_id=sid, dataset="query_page", source="csv",
                   day=date(2026, 11, 21), query="ohne url",
                   page=None, impressions=900, clicks=0, position=3),
        ])
    x = client.get(endpoint, headers=auth).json()
    assert x["has_data"] is True
    assert x["source"] == "api"
    assert x["queries_considered"] == 1
    assert x["clusters"][0]["queries"][0]["impressions"] == 40
    assert x["clusters"][0]["queries"][0]["ranked_url"] == base + "/about"
    assert any("nicht doppelt" in note for note in x["notes"])
    assert client.get(endpoint).status_code == 401
    other = client.post("/api/auth/register", json={
        "email": "content-gap-isolation@example.com", "password": "correct horse battery"}).json()
    another_auth = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(endpoint, headers=another_auth).status_code == 404


def test_content_gap_work_item_is_manual_and_host_restricted(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = crawled["base"]
    endpoint = f"/api/sites/{sid}/content-gap/work"
    payload = {"query": "installationszonen küche", "action": "expand",
               "target_url": base + "/about"}
    bad = client.post(endpoint, headers=auth, json={**payload,
                      "target_url": "https://example.org/external/"})
    assert bad.status_code == 422
    created = client.post(endpoint, headers=auth, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "planned"
    assert created.json()["remote_publication"] is False
    items = client.get(f"/api/sites/{sid}/seo-work", headers=auth).json()["items"]
    assert any(item["id"] == created.json()["id"] and item["kind"] == "content" for item in items)
