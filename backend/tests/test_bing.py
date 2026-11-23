"""Bing Webmaster Tools client and IndexNow submissions with mocked HTTP."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.integrations import bing


def _mock(monkeypatch, handler):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(bing.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler)))


def test_helpers():
    assert bing.parse_ms_date("/Date(1763856000000-0800)/") == "2025-11-23"
    assert bing.parse_ms_date(None) is None
    sites = [{"url": "http://example.de/", "verified": True}, {"url": "https://www.example.de/", "verified": True},
             {"url": "https://other.de/", "verified": True}]
    assert bing.match_site(sites, "https://example.de/") == "https://www.example.de/"
    assert bing.match_site(sites, "https://none.de/") is None
    ok, rejected = bing.same_host_urls(["https://example.de/a", "https://example.de/a", "https://evil.de/x", "ftp://example.de/f", ""],
                                       "https://example.de/")
    assert ok == ["https://example.de/a"] and rejected == ["https://evil.de/x", "ftp://example.de/f"]


def test_key_validation_and_location():
    with pytest.raises(bing.BingError):
        bing.indexnow_key({"key": ""})
    with pytest.raises(bing.BingError):
        bing.indexnow_key({"key": "kurz"})
    key = "a1b2c3d4e5f6a7b8"
    assert bing.key_location({"key": key}, "https://www.example.de/shop/") == f"https://www.example.de/{key}.txt"
    with pytest.raises(bing.BingError):
        bing.key_location({"key": key, "key_location": "https://cdn.other.de/k.txt"}, "https://example.de/")


def test_overview_aggregates_weekly_query_rows(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["apikey"] == "secret"
        method = request.url.path.rsplit("/", 1)[-1]
        data = {
            "GetQueryStats": [
                {"Query": "küche", "Clicks": 3, "Impressions": 100, "AvgImpressionPosition": 4.0, "Date": "/Date(1763856000000)/"},
                {"Query": "küche", "Clicks": 1, "Impressions": 100, "AvgImpressionPosition": 6.0, "Date": "/Date(1764460800000)/"},
                {"Query": "tischler", "Clicks": 0, "Impressions": 10, "AvgImpressionPosition": 12.0},
            ],
            "GetCrawlStats": [{"Date": "/Date(1764460800000)/", "CrawledPages": 40, "CrawlErrors": 2, "InIndex": 30},
                              {"Date": "/Date(1763856000000)/", "CrawledPages": 35, "CrawlErrors": 0, "InIndex": 29}],
        }[method]
        return httpx.Response(200, json={"d": data})

    _mock(monkeypatch, handler)
    out = asyncio.run(bing.overview({"api_key": "secret"}, "https://example.de/"))
    assert out["queries"][0] == {"query": "küche", "clicks": 4, "impressions": 200, "position": 5.0, "ctr": 2.0}
    assert out["totals"] == {"clicks": 4, "impressions": 210, "queries": 2}
    assert [r["date"] for r in out["crawl_stats"]] == ["2025-11-23", "2025-11-30"]


def test_bing_errors_are_readable(monkeypatch):
    _mock(monkeypatch, lambda r: httpx.Response(401, json={"ErrorCode": 3, "Message": "InvalidApiKey"}))
    with pytest.raises(bing.BingError, match="HTTP 401 – InvalidApiKey"):
        asyncio.run(bing.sites({"api_key": "falsch"}))
    with pytest.raises(bing.BingError, match="nicht eingerichtet"):
        asyncio.run(bing.sites({"api_key": ""}))


def test_indexnow_submit_payload(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(202)

    _mock(monkeypatch, handler)
    key = "a1b2c3d4e5f6a7b8"
    out = asyncio.run(bing.indexnow_submit({"key": key}, "https://example.de/", ["https://example.de/a"]))
    assert seen["url"] == bing.INDEXNOW_API
    assert seen["body"] == {"host": "example.de", "key": key, "keyLocation": f"https://example.de/{key}.txt", "urlList": ["https://example.de/a"]}
    assert out["ok"] is True and out["status_code"] == 202 and "Schlüsselprüfung" in out["message"]


def test_settings_validation_and_masking(client, auth):
    assert client.put("/api/settings", headers=auth, json={"indexnow": {"key": "kurz"}}).status_code == 422
    assert client.put("/api/settings", headers=auth, json={"indexnow": {"key": "a1b2c3d4e5f6a7b8", "key_location": "http://x.de/k.txt"}}).status_code == 422
    r = client.put("/api/settings", headers=auth, json={"bing": {"api_key": "geheim"}, "indexnow": {"key": "a1b2c3d4e5f6a7b8"}})
    assert r.status_code == 200, r.text
    assert r.json()["bing"]["api_key"] == "********"
    assert r.json()["indexnow"]["key"] == "a1b2c3d4e5f6a7b8"
    client.put("/api/settings", headers=auth, json={"bing": {"api_key": ""}, "indexnow": {"key": "", "key_location": ""}})


def test_indexnow_endpoints(client, auth, crawled, monkeypatch):
    site_id = crawled["site"]["id"]
    status = client.get(f"/api/sites/{site_id}/indexnow/status", headers=auth).json()
    assert status["configured"] is False and status["key_file"] is None
    assert status["candidates"]["crawl_id"] >= crawled["crawl_id"]  # other tests may re-crawl the fixture site

    client.put("/api/settings", headers=auth, json={"indexnow": {"key": "a1b2c3d4e5f6a7b8"}})
    try:
        status = client.get(f"/api/sites/{site_id}/indexnow/status", headers=auth).json()
        assert status["configured"] is True
        assert status["key_file"]["ok"] is False and status["key_file"]["status_code"] == 404  # fixture site has no key file

        async def fake_submit(settings, site_url, urls, client=None):
            return {"status_code": 200, "ok": True, "submitted": len(urls), "message": "OK"}

        monkeypatch.setattr(bing, "indexnow_submit", fake_submit)
        base = crawled["base"]
        r = client.post(f"/api/sites/{site_id}/indexnow/submit", headers=auth,
                        json={"source": "manual", "urls": [f"{base}/", "https://fremd.example/x"]})
        assert r.status_code == 200, r.text
        assert r.json()["submitted"] == 1 and r.json()["rejected_count"] == 1
        r = client.post(f"/api/sites/{site_id}/indexnow/submit", headers=auth, json={"source": "manual", "urls": ["https://fremd.example/x"]})
        assert r.status_code == 422
    finally:
        client.put("/api/settings", headers=auth, json={"indexnow": {"key": "", "key_location": ""}})


def test_issue_export_contains_provenance(client, auth, crawled):
    r = client.get(f"/api/crawls/{crawled['crawl_id']}/export", headers=auth, params={"dataset": "issues", "format": "json"})
    rows = r.json()["issues"]
    assert rows and {"classification", "profiles"} <= set(rows[0])
    assert client.get(f"/api/crawls/{crawled['crawl_id']}/report.pdf", headers=auth).status_code == 200
