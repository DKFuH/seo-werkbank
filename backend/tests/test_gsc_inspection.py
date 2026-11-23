"""URL Inspection API with mocked Google HTTP response, never a fake live Google authorization."""
import pytest

from app.integrations import gsc


@pytest.mark.asyncio
async def test_inspection_http_shape(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {"inspectionResult": {"inspectionResultLink": "https://search.google.com/inspection",
                "indexStatusResult": {"verdict": "PASS", "coverageState": "Submitted and indexed",
                                      "googleCanonical": "https://example.org/"} }}
    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, endpoint, json, headers):
            assert endpoint.endswith("/urlInspection/index:inspect")
            assert json["siteUrl"] == "sc-domain:example.org"
            assert headers["Authorization"] == "Bearer test-access-token"
            return Response()
    async def token(*args):
        return "test-access-token"
    monkeypatch.setattr(gsc, "_access_token", token)
    monkeypatch.setattr(gsc.httpx, "AsyncClient", lambda **kw: Client())
    r = await gsc.inspect_url(None, 1, "sc-domain:example.org", "https://example.org/")
    assert r["index"]["verdict"] == "PASS"
    assert r["source"] == "google_url_inspection_api"


def test_inspection_site_validation(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "Inspect", "url": fixture_site.url}).json()
    p = f"/api/sites/{site['id']}/gsc/inspect"
    assert client.post(p, headers=auth, json={"url": "https://unrelated.example.org/"}).status_code == 422
    assert client.post(p, headers=auth, json={"url": fixture_site.url + "/"}).status_code == 400
