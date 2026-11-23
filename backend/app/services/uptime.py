"""Website Health: uptime checks with response time, incidents and statistics.

Each probe is classified into one outcome (ok, slow, or a failure class). Failures open an incident at once (the
fetcher already retried once); slowness opens one only after ``slow_repeat`` consecutive slow checks so that a single
blip does not alert. An incident is resolved by the first good check. Alerts are created on open and on resolve;
delivery beyond the app (e-mail, webhook) is up to the alert channels.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..crawler.fetcher import FetchResult
from ..models import UptimeCheck, UptimeIncident, utcnow

DEFAULT_SLOW_MS = 2000
DEFAULT_SLOW_REPEAT = 2
MAX_BYTES = 5_000_000
RETENTION_DAYS = 90

# outcome -> (German description, overview category, overview label)
OUTCOMES: dict[str, tuple[str, str, str]] = {
    "ok": ("Erreichbar", "", ""),
    "slow": ("Hohe Antwortzeit", "access", "Ladezeit"),
    "timeout": ("Timeout", "access", "Timeouts"),
    "ssl": ("SSL-Fehler", "access", "Sicherheit (SSL)"),
    "dns": ("DNS-Fehler", "access", "DNS"),
    "connection": ("Verbindungsfehler", "access", "Verbindungsstatus"),
    "redirect": ("Weiterleitungsfehler", "visitor", "Weiterleitungen"),
    "not_found": ("Seite nicht gefunden", "visitor", "Seite nicht gefunden"),
    "server_error": ("Serverfehler", "visitor", "Serverfehler"),
    "http_error": ("Client-Fehler", "visitor", "Client-Fehler"),
    "encoding": ("Content-Encoding-Fehler", "integrity", "Content-Encoding"),
    "incomplete": ("Unvollständig geladen", "integrity", "Unvollständige Ladevorgänge"),
    "too_large": ("Zu großer Inhalt", "integrity", "Zu große Inhalte"),
}
CATEGORIES = {
    "visitor": ("Besuchererlebnis", "Fehler, die verhindern, dass Besucher Inhalte aufrufen können."),
    "access": ("Erreichbarkeit und Sicherheit", "Ob die Website erreichbar, schnell und sicher ist."),
    "integrity": ("Seitenintegrität", "Ob die Seite vollständig und korrekt geladen wird."),
}
UP = {"ok", "slow"}


def classify(res: FetchResult, total_ms: int, slow_ms: int = DEFAULT_SLOW_MS, max_bytes: int = MAX_BYTES) -> tuple[str, str]:
    """(outcome, description) for one probe, e.g. ("slow", "HTTP Status Code 200 (Hohe Antwortzeit)")."""
    err = (res.error or "").lower()
    if res.status is None or res.error and not res.status:
        if "timeout" in err or "timed out" in err:
            return "timeout", "Timeout"
        if "ssl" in err or "certificate" in err or "tls" in err:
            return "ssl", "SSL-Fehler"
        if "dns" in err or "getaddrinfo" in err or "name or service" in err or "nodename" in err:
            return "dns", "DNS-Fehler"
        if "redirect" in err:
            return "redirect", "Weiterleitungsfehler (" + (res.error or "")[:80] + ")"
        if "decod" in err or "encoding" in err:
            return "encoding", "Content-Encoding-Fehler"
        return "connection", "Verbindungsfehler" + (f" ({res.error[:80]})" if res.error else "")
    status = res.status
    if res.redirect_loop or status in (301, 302, 303, 307, 308):
        return "redirect", f"HTTP Status Code {status} (Weiterleitungsfehler)"
    if status in (404, 410):
        return "not_found", f"HTTP Status Code {status} (Seite nicht gefunden)"
    if status >= 500:
        return "server_error", f"HTTP Status Code {status} (Serverfehler)"
    if status >= 400:
        return "http_error", f"HTTP Status Code {status}"
    if res.truncated or len(res.body) >= max_bytes:
        return "too_large", f"HTTP Status Code {status} (Inhalt über {max_bytes // 1_000_000} MB)"
    declared = res.headers.get("content-length")
    if declared and declared.isdigit() and not res.headers.get("content-encoding") and len(res.body) < int(declared):
        return "incomplete", f"HTTP Status Code {status} (unvollständig: {len(res.body)} von {declared} Bytes)"
    if total_ms > slow_ms:
        return "slow", f"HTTP Status Code {status} (Hohe Antwortzeit)"
    return "ok", f"HTTP Status Code {status}"


def _fmt_duration(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = [f"{d}d"] if d else []
    if h:
        parts.append(f"{h}h")
    if m and not d:
        parts.append(f"{m}m")
    if s and not d and not h:
        parts.append(f"{s}s")
    return " ".join(parts) or "0s"


def record(db: Session, monitor_id: int, url: str, outcome: str, description: str, *, status: int | None,
           response_ms: int | None, error: str | None, state: dict, slow_repeat: int = DEFAULT_SLOW_REPEAT,
           now: datetime | None = None) -> list[dict]:
    """Store one check, update the URL's open incident and return alerts to create.

    ``state`` is the monitor's per-URL state dict; it keeps the slow streak between runs and is updated in place.
    """
    now = now or utcnow()
    db.add(UptimeCheck(monitor_id=monitor_id, url=url, checked_at=now, outcome=outcome, status_code=status,
                       response_ms=response_ms, error=(error or None) and error[:300]))
    open_inc = db.scalar(select(UptimeIncident).where(UptimeIncident.monitor_id == monitor_id, UptimeIncident.url == url,
                                                      UptimeIncident.resolved_at.is_(None)).order_by(UptimeIncident.id.desc()))
    streak = state.get("slow_streak", 0) + 1 if outcome == "slow" else 0
    state["slow_streak"] = streak
    if outcome == "slow" and streak == 1 and not open_inc:
        state["slow_since"] = now.isoformat()
    alerts: list[dict] = []
    problem = outcome != "ok" and (outcome != "slow" or streak >= slow_repeat)

    def resolve(inc: UptimeIncident) -> None:
        inc.resolved_at = now
        good = "wieder erreichbar" if inc.outcome not in ("slow",) else "wieder schnell"
        alerts.append({"severity": "low", "title": f"[Behoben] {url} ist {good}",
                       "message": f"{inc.description} seit {inc.started_at:%d.%m.%Y %H:%M} UTC, Dauer {_fmt_duration(now - inc.started_at)}.",
                       "data": {"url": url, "incident_id": inc.id, "outcome": inc.outcome, "resolved": True}})

    # A good check, or a different problem, ends the open incident (an outage followed by a slow answer counts as
    # reachable again; the slow streak then builds up on its own).
    if open_inc and (not problem or open_inc.outcome != outcome):
        resolve(open_inc)
        open_inc = None
    if problem and open_inc:
        open_inc.checks += 1
    elif problem:
        started = datetime.fromisoformat(state["slow_since"]) if outcome == "slow" and state.get("slow_since") else now
        inc = UptimeIncident(monitor_id=monitor_id, url=url, outcome=outcome, description=description, started_at=started,
                             checks=streak if outcome == "slow" else 1)
        db.add(inc)
        db.flush()
        severity = "medium" if outcome == "slow" else "critical"
        alerts.append({"severity": severity, "title": f"{url}: {OUTCOMES[outcome][0]}",
                       "message": f"{description}" + (f" – {response_ms} ms" if response_ms is not None and outcome == "slow" else ""),
                       "data": {"url": url, "incident_id": inc.id, "outcome": outcome, "status": status, "error": error}})
    if outcome != "slow":
        state.pop("slow_since", None)
    state.update({"ok": outcome in UP, "status": status, "response_ms": response_ms, "outcome": outcome,
                  "checked": now.isoformat()})
    db.flush()  # sessions here do not autoflush; later queries in the same session must see this check
    return alerts


def prune(db: Session, monitor_id: int, now: datetime | None = None) -> None:
    cutoff = (now or utcnow()) - timedelta(days=RETENTION_DAYS)
    db.execute(delete(UptimeCheck).where(UptimeCheck.monitor_id == monitor_id, UptimeCheck.checked_at < cutoff))


def rating(avg_ms: float | None) -> str | None:
    if avg_ms is None:
        return None
    return "Gut" if avg_ms < 500 else "Mittel" if avg_ms < 1000 else "Langsam" if avg_ms < 2000 else "Sehr langsam"


def stats(db: Session, monitor_id: int, url: str, *, hours: int, bucket_minutes: int, slow_ms: int,
          now: datetime | None = None) -> dict:
    """Summary, status bar buckets, response-time candles (open/high/low/close per bucket) and incidents."""
    now = now or utcnow()
    since = now - timedelta(hours=hours)
    checks = list(db.scalars(select(UptimeCheck).where(UptimeCheck.monitor_id == monitor_id, UptimeCheck.url == url,
                                                       UptimeCheck.checked_at >= since).order_by(UptimeCheck.checked_at)))
    step = timedelta(minutes=bucket_minutes)
    n_buckets = max(1, int(timedelta(hours=hours) / step))
    first = now - n_buckets * step
    buckets = [{"start": (first + i * step).isoformat(), "checks": 0, "down": 0, "slow": 0, "times": []} for i in range(n_buckets)]
    for c in checks:
        i = min(n_buckets - 1, max(0, int((c.checked_at - first) / step)))
        b = buckets[i]
        b["checks"] += 1
        if c.outcome not in UP:
            b["down"] += 1
        elif c.outcome == "slow":
            b["slow"] += 1
        if c.outcome in UP and c.response_ms is not None:
            b["times"].append(c.response_ms)
    bars, candles = [], []
    for b in buckets:
        status = "none" if not b["checks"] else "down" if b["down"] else "slow" if b["slow"] else "up"
        bars.append({"start": b["start"], "status": status, "checks": b["checks"], "down": b["down"]})
        t = b["times"]
        candles.append({"start": b["start"], "open": t[0] if t else None, "close": t[-1] if t else None,
                        "high": max(t) if t else None, "low": min(t) if t else None,
                        "avg": round(sum(t) / len(t)) if t else None, "down": b["down"]})
    up_checks = [c for c in checks if c.outcome in UP]
    times = [c.response_ms for c in up_checks if c.response_ms is not None]
    avg = round(sum(times) / len(times)) if times else None
    incidents = list(db.scalars(select(UptimeIncident).where(
        UptimeIncident.monitor_id == monitor_id, UptimeIncident.url == url,
        (UptimeIncident.resolved_at.is_(None)) | (UptimeIncident.resolved_at >= now - timedelta(days=RETENTION_DAYS)))
        .order_by(UptimeIncident.started_at.desc()).limit(500)))
    in_period = [i for i in incidents if (i.resolved_at or now) >= since]
    overview: dict[str, dict] = {k: {"title": t, "description": d, "items": {}} for k, (t, d) in CATEGORIES.items()}
    for key, (_, cat, label) in OUTCOMES.items():
        if cat:
            overview[cat]["items"][key] = {"label": label, "incidents": sum(1 for i in in_period if i.outcome == key)}
    last = checks[-1] if checks else None
    current = "unknown" if not last else "up" if last.outcome == "ok" else "slow" if last.outcome == "slow" else "down"
    return {
        "url": url, "hours": hours, "bucket_minutes": bucket_minutes, "slow_ms": slow_ms,
        "summary": {"status": current, "uptime_pct": round(100 * len(up_checks) / len(checks), 2) if checks else None,
                    "checks": len(checks), "avg_ms": avg, "rating": rating(avg),
                    "last_check": last.checked_at.isoformat() if last else None,
                    "last_status_code": last.status_code if last else None},
        "bars": bars, "candles": candles,
        "incidents": [{"id": i.id, "status": "open" if i.resolved_at is None else "resolved", "outcome": i.outcome,
                       "description": i.description, "started_at": i.started_at.isoformat(),
                       "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                       "duration": _fmt_duration((i.resolved_at or now) - i.started_at),
                       "duration_s": int(((i.resolved_at or now) - i.started_at).total_seconds())} for i in incidents],
        "overview": [{"key": k, **v, "items": list(v["items"].values())} for k, v in overview.items()],
        "method": "Antwortzeit = Gesamtzeit des Abrufs von diesem Server aus (inkl. Weiterleitungen, Inhalt bis 5 MB). "
                  "Verfügbarkeit = Anteil der Prüfungen ohne Fehler; hohe Antwortzeit zählt als erreichbar.",
    }
