"""Notification delivery cannot be triggered by default; severity filter is explicit."""
import pytest

from app.services import notifications


@pytest.mark.asyncio
async def test_notifications_default_off(monkeypatch):
    monkeypatch.setattr(notifications, "get_setting", lambda db, key: {"enabled": "false"})
    result = await notifications.deliver_alerts(None, "A site", [{"severity": "critical", "title": "Oops"}])
    assert result["sent"] is False


@pytest.mark.asyncio
async def test_notifications_aggregate_and_filter(monkeypatch):
    sent = []
    monkeypatch.setattr(notifications, "get_setting", lambda db, key: {
        "enabled": "true", "min_severity": "high", "smtp_host": "smtp.example.org",
        "from_email": "alerts@example.org", "to_email": "owner@example.org"})
    monkeypatch.setattr(notifications, "_smtp_send", lambda cfg, title, body: sent.append((title, body)))
    x = await notifications.deliver_alerts(None, "Example", [
        {"severity": "low", "title": "Low"}, {"severity": "critical", "title": "Down"}])
    assert x["sent"] and x["selected"] == 1
    assert len(sent) == 1 and "Down" in sent[0][1] and "Low" not in sent[0][1]
