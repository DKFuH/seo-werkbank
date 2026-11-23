"""Local Lighthouse smoke test: real CLI and Chrome, not mocked PSI scores."""
from __future__ import annotations

import pytest

from app.integrations.pagespeed import lighthouse_path, run_local_lighthouse


@pytest.mark.asyncio
async def test_real_local_lighthouse(fixture_site, monkeypatch):
    if not lighthouse_path():
        pytest.skip("Lighthouse CLI not installed")
    # Local fixture testing is explicitly opt-in via the normal SSRF configuration.
    monkeypatch.setenv("SEO_ALLOW_PRIVATE_NETWORKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        result = await run_local_lighthouse(fixture_site.url + "/", timeout_s=180)
        assert result["source"] == "local_lighthouse"
        assert result["scores"]["performance"] is not None
        assert "lab" in result
    finally:
        get_settings.cache_clear()
