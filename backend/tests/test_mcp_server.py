"""The MCP entrypoint is strictly read-only and cannot leak credentials on redirects."""
from __future__ import annotations

import json

import httpx
import pytest

from app import mcp_server as m


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:8000", "http://example.com:8000", "http://127.0.0.1",
    "http://127.0.0.1:8000/path", "http://127.0.0.1:8000?q=1",
    "http://user:pass@127.0.0.1:8000", "http://127.0.0.1:8000#fragment",
    "http://169.254.169.254:8000",
])
def test_reject_nonlocal_or_ambiguous_api(url):
    with pytest.raises(ValueError):
        m.local_api_origin(url)


def test_local_origins():
    assert m.local_api_origin("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert m.local_api_origin("http://[::1]:8080") == "http://[::1]:8080"


def test_token_required(monkeypatch):
    monkeypatch.delenv("SEO_MCP_API_TOKEN", raising=False)
    with pytest.raises(ValueError):
        m.api_config()


@pytest.mark.asyncio
async def test_readonly_paths_auth_and_redirect(monkeypatch):
    seen = []

    async def handler(request):
        seen.append(request)
        if request.url.path.endswith("/redirect"):
            return httpx.Response(302, headers={"location": "https://evil.example/steal"})
        return httpx.Response(200, json={"items": [{"id": 2}]})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return original(*args, transport=transport, **kwargs)

    monkeypatch.setenv("SEO_MCP_API_TOKEN", "test-local-user-token")
    monkeypatch.setenv("SEO_MCP_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(m.httpx, "AsyncClient", client_factory)
    assert await m.get_backlinks(2) == {"items": [{"id": 2}]}
    assert seen[0].method == "GET"
    assert seen[0].headers["authorization"] == "Bearer test-local-user-token"
    assert seen[0].url.path == "/api/sites/2/backlinks"
    with pytest.raises(ValueError):
        await m.api_get("/api/redirect")
    assert len(seen) == 2
    with pytest.raises(ValueError):
        await m.api_get("/api/sites/../settings")
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_wrong_type_and_limits_without_http(monkeypatch):
    monkeypatch.setenv("SEO_MCP_API_TOKEN", "token")
    with pytest.raises(ValueError):
        await m.get_crawl_pages(1, limit=101)
    with pytest.raises(ValueError):
        await m.get_crawl_issues(-1)
    with pytest.raises(ValueError):
        await m.get_gsc_insights(1, days=181)


def test_mcp_tool_registration_if_installed():
    pytest.importorskip("mcp")
    server = m.build_server()
    assert server is not None
