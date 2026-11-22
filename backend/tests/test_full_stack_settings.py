"""Optional Docker integration is an effective default, never a forced provider."""
from unittest.mock import patch

from app.models import Setting
from app.services.settings_store import get_setting


def test_searxng_env_only_applies_when_unconfigured():
    class FakeSession:
        def __init__(self, row=None):
            self.row = row

        def get(self, model, key):
            assert model is Setting
            return self.row

    # The helper takes the normal SQLAlchemy Session interface.
    with patch.dict("os.environ", {"SEO_SEARXNG_URL": "http://searxng:8080"}):
        value = get_setting(FakeSession(), "serp")
        assert value["provider"] == "searxng"
        assert value["searxng_url"] == "http://searxng:8080"
        disabled = get_setting(FakeSession(Setting(key="serp", value={
            "provider": "none", "searxng_url": ""})), "serp")
        assert disabled["provider"] == "none"
        configured = get_setting(FakeSession(Setting(key="serp", value={
            "provider": "brave", "brave_key": "test"})), "serp")
        assert configured["provider"] == "brave"
    assert get_setting(FakeSession(), "serp")["provider"] == "none"
