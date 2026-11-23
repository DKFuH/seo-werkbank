"""Website Health: uptime statistics, response-time candles and incidents of an uptime monitor."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Monitor, User
from ..security.auth import current_user, get_site_for
from ..services import uptime

router = APIRouter(tags=["website-health"])
# period -> (hours, bucket minutes): 48 bars for a day, hourly candles for a week, 6-hour candles for a month
PERIODS = {"24h": (24, 30), "7d": (24 * 7, 180), "30d": (24 * 30, 720)}


@router.get("/sites/{site_id}/website-health")
def website_health(site_id: int, period: Literal["24h", "7d", "30d"] = "24h", monitor_id: int | None = None,
                   url: str | None = Query(None, max_length=2048), user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    monitors = list(db.scalars(select(Monitor).where(Monitor.site_id == site.id, Monitor.kind == "uptime").order_by(Monitor.id)))
    if not monitors:
        return {"has_monitor": False, "monitors": []}
    mon = next((m for m in monitors if m.id == monitor_id), monitors[0]) if monitor_id else monitors[0]
    if monitor_id and mon.id != monitor_id:
        raise HTTPException(404, "Monitor nicht gefunden")
    urls = (mon.config or {}).get("urls") or [site.url]
    target = url if url in urls else urls[0]
    hours, bucket = PERIODS[period]
    slow_ms = int((mon.config or {}).get("slow_ms") or uptime.DEFAULT_SLOW_MS)
    data = uptime.stats(db, mon.id, target, hours=hours, bucket_minutes=bucket, slow_ms=slow_ms)
    return {"has_monitor": True, "period": period, "urls": urls,
            "monitor": {"id": mon.id, "name": mon.name, "interval_minutes": round(mon.interval_hours * 60),
                        "enabled": mon.enabled, "slow_ms": slow_ms,
                        "slow_repeat": int((mon.config or {}).get("slow_repeat") or uptime.DEFAULT_SLOW_REPEAT),
                        "last_run": mon.last_run.isoformat() if mon.last_run else None},
            "monitors": [{"id": m.id, "name": m.name} for m in monitors], **data}
