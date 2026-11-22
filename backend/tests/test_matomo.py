"""Matomo integration: URL matching, crawl join and the overview aggregation with a mocked API."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.integrations import matomo as mt


def test_norm_url_and_match_site():
    assert mt.norm_url("https://www.Example.de/a/b/?x=1#y") == "example.de/a/b"
    assert mt.norm_url("http://example.de") == "example.de/"
    sites = [{"id": 1, "url": "https://other.de"}, {"id": 2, "url": "https://www.kueche.example"}]
    assert mt.match_site(sites, "https://kueche.example/") == 2
    assert mt.match_site(sites, "https://none.example/") is None


def test_join_crawl_and_pages_without_visits():
    pages = [{"url": "https://k.example/a/", "key": mt.norm_url("https://k.example/a/"), "visits": 10}]
    crawl = [{"id": 1, "url": "https://k.example/a", "title": "A", "indexable": True, "word_count": 500, "inlinks": 4, "issue_count": 0},
             {"id": 2, "url": "https://k.example/b/", "title": "B", "indexable": True, "word_count": 300, "inlinks": 1, "issue_count": 2},
             {"id": 3, "url": "https://k.example/c/", "title": "C", "indexable": False, "word_count": 10, "inlinks": 0, "issue_count": 0}]
    out = mt.join_crawl(pages, crawl)
    assert out["pages"][0]["in_crawl"] is True and out["pages"][0]["title"] == "A"
    assert [p["url"] for p in out["no_traffic"]] == ["https://k.example/b/"]


def test_endpoint_requires_configuration():
    with pytest.raises(mt.MatomoError):
        mt._endpoint({"url": "", "token_auth": ""})
    assert mt._endpoint({"url": "https://stats.example.de/", "token_auth": "x"}) == "https://stats.example.de/index.php"


def test_overview_with_mocked_api(monkeypatch):
    seen_tokens = []

    def handler(request: httpx.Request) -> httpx.Response:
        form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
        seen_tokens.append(form.get("token_auth"))
        assert "token_auth" not in str(request.url)
        method = form["method"]
        data = {
            "VisitsSummary.get": {"nb_visits": 120, "nb_uniq_visitors": 100, "nb_actions_per_visit": 2.5, "avg_time_on_site": 61, "bounce_rate": "55%"}
            if form.get("period") == "range" else {"2026-11-20": {"nb_visits": 4}, "2026-11-21": []},
            "Referrers.getReferrerType": [{"label": "Suchmaschinen", "nb_visits": 80}],
            "Actions.getPageUrls": [{"label": "/a", "url": "https://k.example/a/", "nb_visits": 30, "nb_hits": 40, "bounce_rate": "50%",
                                     "avg_time_on_page": 42, "exit_rate": "40%"},
                                    {"label": "/a?x", "url": "https://k.example/a/?utm=1", "nb_visits": 5, "nb_hits": 5}],
            "Actions.getEntryPageUrls": [{"url": "https://k.example/a/", "entry_nb_visits": 25, "bounce_rate": "48%"}],
            "Referrers.getSearchEngines": [{"label": "Google", "nb_visits": 70}],
            "Referrers.getWebsites": [],
            "Goals.getGoals": {"1": {"idgoal": "1", "name": "Kontakt"}},
            "Goals.get": {"nb_conversions": 3, "conversion_rate": "2.5%", "idgoal=1": {"nb_conversions": 3, "conversion_rate": "2.5%"}},
            "DevicesDetection.getType": [{"label": "Smartphone", "nb_visits": 70}, {"label": "TV", "nb_visits": 0}],
        }[method]
        return httpx.Response(200, json=data)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(mt.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    out = asyncio.run(mt.overview({"url": "https://stats.example.de", "token_auth": "secret"}, 1, 30))
    assert set(seen_tokens) == {"secret"}
    assert out["summary"]["visits"] == 120 and out["summary"]["bounce_rate"] == 55.0
    assert out["pages"][0]["visits"] == 35 and out["pages"][0]["entries"] == 25  # query-string variant merged
    assert out["goals"]["per_goal"] == [{"id": "1", "name": "Kontakt", "conversions": 3, "rate": 2.5}]
    assert out["devices"] == [{"label": "Smartphone", "visits": 70}]
    assert out["series"][0] == {"date": "2026-11-20", "visits": 4}


def test_matomo_error_message(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"result": "error", "message": "token_auth ungültig"})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(mt.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    with pytest.raises(mt.MatomoError, match="token_auth ungültig"):
        asyncio.run(mt.sites({"url": "https://stats.example.de", "token_auth": "x"}))


def test_settings_mask_token(client, auth):
    r = client.put("/api/settings", headers=auth, json={"matomo": {"url": "https://stats.example.de", "token_auth": "geheim"}})
    assert r.status_code == 200, r.text
    assert r.json()["matomo"]["token_auth"] == "********"
    assert client.get("/api/settings", headers=auth).json()["matomo"]["url"] == "https://stats.example.de"
    client.put("/api/settings", headers=auth, json={"matomo": {"url": "", "token_auth": ""}})


# ------------------------------------------------------------------ German CSV exports
def test_parse_number_german_and_english():
    from app.integrations.gsc import parse_number
    assert parse_number("1.234", german=True) == 1234
    assert parse_number("8,47", german=True) == 8.47
    assert parse_number("4,5 %", german=True) == 4.5
    assert parse_number("1,234") == 1234
    assert parse_number("8,47") == 8.47  # unambiguous decimal comma even without German headers
    assert parse_number("1,234.5") == 1234.5


def test_gsc_csv_import_german_export(client, auth, crawled):
    site_id = crawled["site"]["id"]
    csv_text = ("Häufigste Suchanfragen,Klicks,Impressionen,CTR,Position\n"
                "küche planen,\"1.234\",\"56.789\",\"2,17 %\",\"8,47\"\n"
                "küchenstudio,12,340,\"3,5 %\",\"3,2\"\n")
    r = client.post(f"/api/sites/{site_id}/gsc/import", headers=auth,
                    files={"file": ("Suchanfragen.csv", csv_text.encode("utf-8"), "text/csv")}, params={"replace": "true"})
    assert r.status_code in (200, 201), r.text
    assert r.json()["rows"] == 2
    perf = client.get(f"/api/sites/{site_id}/gsc/performance", headers=auth).json()
    rows = {q["key"]: q for q in perf["queries"]}
    assert rows["küche planen"]["clicks"] == 1234 and rows["küche planen"]["impressions"] == 56789
    assert rows["küche planen"]["position"] == 8.5 and rows["küchenstudio"]["position"] == 3.2


def test_gsc_csv_import_german_dates_and_devices():
    from app.integrations.gsc import _DEVICES, _day
    assert str(_day("21.11.2026")) == "2026-11-21" and str(_day("2026-11-21")) == "2026-11-21"
    assert _DEVICES["mobilgerät"] == "mobile"
