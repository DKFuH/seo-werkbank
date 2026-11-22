"""Local-only, read-only MCP bridge to the authenticated SEO-Werkbank REST API.

Stdio transport is deliberately separate from the web process. No database bypass,
no model-controlled URL fetches, and no write tools. The caller must provide a
normal, user-scoped short-lived SEO-Werkbank access token via environment.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE_BYTES = 512_000
MAX_LIMIT = 100


def local_api_origin(value: str) -> str:
    """Only loopback HTTP, with no path, user-info, fragment or query."""
    try:
        u = urlsplit(value.strip())
        port = u.port
    except ValueError as exc:
        raise ValueError("Invalid SEO_MCP_API_URL") from exc
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("SEO_MCP_API_URL must be a loopback HTTP address")
    if u.username is not None or u.password is not None or u.path not in ("", "/") or u.query or u.fragment:
        raise ValueError("SEO_MCP_API_URL must be an origin without path or credentials")
    if port is None:
        raise ValueError("SEO_MCP_API_URL must include an explicit port")
    return value.strip().rstrip("/")


def api_config() -> tuple[str, str]:
    url = local_api_origin(os.getenv("SEO_MCP_API_URL", "http://127.0.0.1:8000"))
    token = os.getenv("SEO_MCP_API_TOKEN", "").strip()
    if not token or len(token) > 8192 or any(c.isspace() for c in token):
        raise ValueError("Provide a valid user-scoped SEO_MCP_API_TOKEN; do not use the server secret")
    return url, token


async def api_get(path: str, *, params: dict | None = None) -> dict | list:
    """Fixed-path GET only. Reject redirects to keep credentials on loopback."""
    if not path.startswith("/api/") or "?" in path or "#" in path or ".." in path or "//" in path:
        raise ValueError("Invalid API path")
    base, token = api_config()
    async with httpx.AsyncClient(base_url=base, timeout=12, follow_redirects=False, trust_env=False) as client:
        async with client.stream("GET", path, headers={"Authorization": f"Bearer {token}"}, params=params) as response:
            if response.status_code in (401, 403, 404):
                raise ValueError("Not authenticated or resource not accessible")
            if response.status_code != 200:
                raise ValueError(f"SEO-Werkbank API returned HTTP {response.status_code}")
            if "application/json" not in response.headers.get("content-type", ""):
                raise ValueError("Unexpected API response content type")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ValueError("API response too large; reduce the requested scope")
            try:
                payload = response.json() if not data else __import__("json").loads(data)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Invalid API JSON") from exc
            if not isinstance(payload, (dict, list)):
                raise ValueError("Unexpected API response")
            return payload


def _id(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise ValueError("Invalid numeric identifier")
    return value


def _page(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 1000:
        raise ValueError("Page must be between 1 and 1000")
    return value


def _limit(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_LIMIT:
        raise ValueError("Limit must be 1..100")
    return value


async def list_owned_sites() -> dict:
    """List only websites owned by the account behind SEO_MCP_API_TOKEN."""
    sites = await api_get("/api/sites")
    if not isinstance(sites, list):
        raise ValueError("Malformed site list")
    return {"items": sites[:100], "truncated": len(sites) > 100}


async def get_site_overview(site_id: int) -> dict:
    """Read overview, last crawl and statistics for one owned website."""
    return await api_get(f"/api/sites/{_id(site_id)}/overview")


async def get_crawl_issues(crawl_id: int) -> dict:
    """Read the technical SEO issue summary for an owned crawl."""
    return await api_get(f"/api/crawls/{_id(crawl_id)}/issues")


async def get_crawl_pages(crawl_id: int, page: int = 1, limit: int = 25) -> dict:
    """Browse a bounded page of crawled URLs without exposing full page texts."""
    return await api_get(f"/api/crawls/{_id(crawl_id)}/pages",
                         params={"page": _page(page), "per_page": _limit(limit)})


async def get_gsc_insights(site_id: int, days: int = 28) -> dict:
    """Read measured Search Console insights (not independent Google rankings)."""
    if type(days) is not int or not 7 <= days <= 180:
        raise ValueError("Days must be 7..180")
    return await api_get(f"/api/sites/{_id(site_id)}/gsc/insights", params={"days": days})


async def get_backlinks(site_id: int, page: int = 1, limit: int = 25) -> dict:
    """Read imported and locally verified backlinks; not a web-scale link index."""
    return await api_get(f"/api/sites/{_id(site_id)}/backlinks",
                         params={"page": _page(page), "per_page": _limit(limit)})


async def get_keywords(site_id: int) -> dict:
    """Read owned keyword records with clearly sourced GSC/imported metrics."""
    data = await api_get(f"/api/sites/{_id(site_id)}/keywords")
    if not isinstance(data, dict):
        raise ValueError("Malformed keyword payload")
    # The current keyword REST endpoint is unpaginated. Never expose unbounded output.
    if len(data.get("items", [])) > 100:
        raise ValueError("Too many keyword records for MCP. Use the web dashboard.")
    return data


def build_server():
    """Create the optional MCP v2 server only when explicitly started."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError('Install optional dependency: pip install -e ".[mcp]"') from exc

    server = MCPServer("SEO-Werkbank (read-only)")
    for tool in (list_owned_sites, get_site_overview, get_crawl_issues, get_crawl_pages,
                 get_gsc_insights, get_backlinks, get_keywords):
        server.tool()(tool)
    return server


def main() -> None:
    # Fail on missing credentials before announcing a working MCP transport.
    api_config()
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
