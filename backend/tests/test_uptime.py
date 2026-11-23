"""Website Health: classification, incidents with slow streak, statistics and candles, API."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.crawler.fetcher import FetchResult
from app.db import session_scope
from app.models import Monitor, Site, UptimeIncident, User
from app.services import uptime
from tests.conftest import wait_for_job

URL = "https://m.de/"


def _res(status=200, body=b"x" * 1000, error=None, headers=None, truncated=False, redirect_loop=False):
    return FetchResult(url=URL, status=status, body=body, error=error, headers=headers or {},
                       truncated=truncated, redirect_loop=redirect_loop)


def test_classify_outcomes():
    c = uptime.classify
    assert c(_res(), 100)[0] == "ok"
    assert c(_res(), 2500) == ("slow", "HTTP Status Code 200 (Hohe Antwortzeit)")
    assert c(_res(None, b"", "timeout"), 20000)[0] == "timeout"
    assert c(_res(None, b"", "ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"), 50)[0] == "ssl"
    assert c(_res(None, b"", "ConnectError: DNS resolution failed for m.de: [Errno 11001] getaddrinfo failed"), 50)[0] == "dns"
    assert c(_res(None, b"", "ConnectError: Connection refused"), 50)[0] == "connection"
    assert c(_res(None, b"", "too many redirects"), 50)[0] == "redirect"
    assert c(_res(404), 50)[0] == "not_found"
    assert c(_res(503), 50)[0] == "server_error"
    assert c(_res(403), 50)[0] == "http_error"
    assert c(_res(200, truncated=True), 50)[0] == "too_large"
    assert c(_res(200, body=b"abc", headers={"content-length": "999"}), 50)[0] == "incomplete"
    assert c(_res(200, body=b"abc", headers={"content-length": "999", "content-encoding": "gzip"}), 50)[0] == "ok"


def _monitor(db) -> int:
    site = db.scalar(select(Site).limit(1))
    if site is None:
        user = User(email="uptime-unit@example.com", password_hash="x")
        db.add(user)
        db.flush()
        site = Site(owner_id=user.id, name="U", url=URL, domain="m.de")
        db.add(site)
        db.flush()
    mon = Monitor(site_id=site.id, kind="uptime", name="Health", interval_hours=0.25, config={}, state={})
    db.add(mon)
    db.flush()
    return mon.id


def _record(db, mid, state, outcome, minute, ms=100, now=None):
    t0 = now or datetime(2026, 11, 20, 12, 0)
    return uptime.record(db, mid, URL, outcome, uptime.OUTCOMES[outcome][0], status=200 if outcome in uptime.UP else None,
                         response_ms=ms, error=None, state=state, slow_repeat=2, now=t0 + timedelta(minutes=minute))


def test_incident_lifecycle_with_slow_streak(client):
    with session_scope() as db:
        mid = _monitor(db)
        state: dict = {}
        assert _record(db, mid, state, "ok", 0) == []
        assert _record(db, mid, state, "slow", 15, 2500) == []  # first slow check: no alert yet
        opened = _record(db, mid, state, "slow", 30, 2600)
        assert len(opened) == 1 and opened[0]["severity"] == "medium"
        inc = db.get(UptimeIncident, opened[0]["data"]["incident_id"])
        assert inc.started_at == datetime(2026, 11, 20, 12, 15)  # incident starts at the first slow check
        switched = _record(db, mid, state, "timeout", 45)
        assert [a["severity"] for a in switched] == ["low", "critical"]  # slow resolved, outage opened
        resolved = _record(db, mid, state, "ok", 75)
        assert len(resolved) == 1 and resolved[0]["title"].startswith("[Behoben]") and "30m" in resolved[0]["message"]
        assert state["ok"] and state["slow_streak"] == 0


def test_stats_buckets_candles_and_overview(client):
    now = datetime(2026, 11, 20, 12, 0)
    with session_scope() as db:
        mid = _monitor(db)
        state: dict = {}
        series = [("ok", 120), ("ok", 180), ("slow", 2500), ("ok", 140), ("timeout", None), ("ok", 160)]
        for i, (outcome, ms) in enumerate(series):
            uptime.record(db, mid, URL, outcome, "x", status=200 if ms else None, response_ms=ms, error=None,
                          state=state, slow_repeat=1, now=now - timedelta(minutes=170 - 30 * i))
        s = uptime.stats(db, mid, URL, hours=24, bucket_minutes=30, slow_ms=2000, now=now)
    assert len(s["bars"]) == 48 and len(s["candles"]) == 48
    assert s["summary"]["checks"] == 6 and s["summary"]["uptime_pct"] == round(100 * 5 / 6, 2)
    assert s["summary"]["avg_ms"] == round((120 + 180 + 2500 + 140 + 160) / 5) and s["summary"]["status"] == "up"
    statuses = [b["status"] for b in s["bars"] if b["status"] != "none"]
    assert statuses.count("down") == 1 and statuses.count("slow") == 1
    filled = [c for c in s["candles"] if c["open"] is not None]
    assert filled and all(c["low"] <= c["open"] <= c["high"] and c["low"] <= c["close"] <= c["high"] for c in filled)
    access = next(g for g in s["overview"] if g["key"] == "access")
    counts = {i["label"]: i["incidents"] for i in access["items"]}
    assert counts["Timeouts"] == 1 and counts["Ladezeit"] == 1
    assert {i["status"] for i in s["incidents"]} == {"resolved"}


def test_website_health_api(client, auth, fixture_site):
    # Own site: the shared crawled site is used by other tests that count alerts.
    base = fixture_site.url
    sid = client.post("/api/sites", headers=auth, json={"name": "Health", "url": base + "/"}).json()["id"]
    mon = client.post(f"/api/sites/{sid}/monitors", headers=auth, json={
        "kind": "uptime", "config": {"urls": [base + "/slow", base + "/server-error"], "slow_ms": 1000, "slow_repeat": 1}}).json()
    assert mon["interval_hours"] == 0.25
    job = wait_for_job(client, auth, client.post(f"/api/monitors/{mon['id']}/run", headers=auth).json()["job_id"])
    assert job["status"] == "completed", job
    r = client.get(f"/api/sites/{sid}/website-health", headers=auth, params={"monitor_id": mon["id"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["has_monitor"] and d["url"] == base + "/slow" and d["monitor"]["slow_ms"] == 1000
    assert d["summary"]["status"] == "slow" and d["incidents"][0]["description"] == "HTTP Status Code 200 (Hohe Antwortzeit)"
    err = client.get(f"/api/sites/{sid}/website-health", headers=auth,
                     params={"monitor_id": mon["id"], "url": base + "/server-error", "period": "7d"}).json()
    assert err["summary"]["status"] == "down" and err["incidents"][0]["outcome"] == "server_error" and len(err["bars"]) == 56
    other = client.post("/api/auth/register", json={"email": "health-other@example.com", "password": "correct horse battery"}).json()
    assert client.get(f"/api/sites/{sid}/website-health",
                      headers={"Authorization": "Bearer " + other["access_token"]}).status_code == 404
