import asyncio

import httpx
import pytest

from app.integrations import bing


def test_read_intelligence_query_pages():
    async def run():
        def handler(request):
            assert request.url.path.endswith("/GetQueryPageStats")
            assert request.url.params["siteUrl"] == "https://example.com/"
            assert request.url.params["query"] == "kitchen"
            return httpx.Response(200, json={"d": [{"Query": "kitchen"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await bing.read_intelligence(
                {"api_key": "test"}, "https://example.com/", "query_pages",
                keyword="kitchen", client=client,
            )
        assert result["provider"] == "bing"
        assert result["data"] == [{"Query": "kitchen"}]

    asyncio.run(run())


@pytest.mark.parametrize("operation,method", [
    ("backlink_counts", "GetLinkCounts"),
    ("backlinks", "GetUrlLinks"),
])
def test_paginated_link_operations_start_with_first_page(operation, method):
    async def run():
        def handler(request):
            assert request.url.path.endswith("/" + method)
            assert request.url.params["page"] == "0"
            return httpx.Response(200, json={"d": {"Links": [], "TotalPages": 0}})

        kwargs = {"url": "https://example.com/page"} if operation == "backlinks" else {}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await bing.read_intelligence(
                {"api_key": "test"}, "https://example.com/", operation,
                client=client, **kwargs,
            )

    asyncio.run(run())


@pytest.mark.parametrize("operation,kwargs", [
    ("SubmitUrl", {}),
    ("query_pages", {}),
    ("url_info", {"url": "https://other.example/"}),
])
def test_read_intelligence_rejects_invalid_requests(operation, kwargs):
    with pytest.raises(bing.BingError):
        asyncio.run(bing.read_intelligence(
            {"api_key": "test"}, "https://example.com/", operation, **kwargs,
        ))
