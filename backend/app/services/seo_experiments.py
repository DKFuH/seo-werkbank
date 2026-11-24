"""SEO Experiment Tracking and Before/After performance analysis for Google and Bing.

Tracks dated SEO changes (e.g. Title/H1 updates, content expansion, internal links, schema)
and measures actual impressions, clicks, CTR and average position across equal time windows.
Supports Google Search Console and Microsoft Bing Webmaster Tools as equal search providers.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GscRow, SeoResearchRecord
from .bing_content import get_bing_observations


def calculate_window_metrics(rows: list[dict]) -> dict[str, Any]:
    impressions = sum(float(r.get("impressions") or 0) for r in rows)
    clicks = sum(float(r.get("clicks") or 0) for r in rows)
    pos_rows = [r for r in rows if r.get("position") is not None and r.get("impressions")]
    weight = sum(float(r["impressions"]) for r in pos_rows)
    position = sum(float(r["position"]) * float(r["impressions"]) for r in pos_rows) / weight if weight else None
    return {
        "impressions": round(impressions),
        "clicks": round(clicks),
        "ctr": round(clicks / impressions, 4) if impressions else None,
        "position": round(position, 2) if position is not None else None,
        "days_with_data": len({r["day"] for r in rows if r.get("day")}),
    }


def calculate_metrics_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    def pct(a: float, b: float) -> float | None:
        return round((b - a) * 100 / a, 1) if a > 0 else None

    return {
        "clicks_pct": pct(before["clicks"], after["clicks"]),
        "impressions_pct": pct(before["impressions"], after["impressions"]),
        "position_change": (
            round(after["position"] - before["position"], 2)
            if before["position"] is not None and after["position"] is not None
            else None
        ),
        "ctr_change_pp": (
            round((after["ctr"] - before["ctr"]) * 100, 2)
            if before["ctr"] is not None and after["ctr"] is not None
            else None
        ),
    }


def _evaluate_row_series(
    rows: list[dict],
    applied_date: date,
    window_days: int,
    source_label: str,
    target_url: str | None = None,
) -> dict[str, Any]:
    if target_url:
        rows = [r for r in rows if r.get("page") == target_url]

    if not rows:
        return {
            "has_data": False,
            "provider": source_label,
            "reason": f"Keine {source_label}-Daten für den Zielbereich gefunden",
            "applied_date": applied_date.isoformat(),
            "target_url": target_url,
        }

    dated_rows = [r for r in rows if isinstance(r.get("day"), date)]
    if not dated_rows:
        return {
            "has_data": False,
            "provider": source_label,
            "reason": f"Keine datierten {source_label}-Zeilen gefunden",
        }

    newest_day = max(r["day"] for r in dated_rows)

    before_start = applied_date - timedelta(days=window_days)
    before_end = applied_date - timedelta(days=1)
    after_start = applied_date
    after_end = applied_date + timedelta(days=window_days - 1)

    if newest_day < applied_date:
        run_status = "waiting_for_data"
        days_elapsed = 0
    elif newest_day < after_end:
        run_status = "in_progress"
        days_elapsed = (newest_day - applied_date).days + 1
    else:
        run_status = "completed"
        days_elapsed = window_days

    fetch_end = min(newest_day, after_end)

    before_rows = [r for r in dated_rows if before_start <= r["day"] <= before_end]
    after_rows = [r for r in dated_rows if after_start <= r["day"] <= fetch_end]

    before_metrics = calculate_window_metrics(before_rows)
    after_metrics = calculate_window_metrics(after_rows)
    delta = calculate_metrics_delta(before_metrics, after_metrics)

    daily: dict[str, dict[str, Any]] = defaultdict(lambda: {"clicks": 0, "impressions": 0, "positions": []})
    for r in dated_rows:
        if before_start <= r["day"] <= fetch_end:
            d_str = r["day"].isoformat()
            daily[d_str]["clicks"] += int(r.get("clicks") or 0)
            daily[d_str]["impressions"] += int(r.get("impressions") or 0)
            if r.get("position") is not None:
                daily[d_str]["positions"].append((float(r["position"]), float(r.get("impressions") or 1)))

    timeline = []
    curr = before_start
    while curr <= fetch_end:
        d_str = curr.isoformat()
        info = daily.get(d_str, {"clicks": 0, "impressions": 0, "positions": []})
        pos_list = info["positions"]
        avg_pos = None
        if pos_list:
            total_weight = sum(w for _, w in pos_list)
            avg_pos = round(sum(p * w for p, w in pos_list) / total_weight, 2) if total_weight else None

        timeline.append({
            "date": d_str,
            "is_experiment_marker": curr == applied_date,
            "period": "before" if curr < applied_date else "after",
            "clicks": info["clicks"],
            "impressions": info["impressions"],
            "avg_position": avg_pos,
        })
        curr += timedelta(days=1)

    return {
        "has_data": True,
        "provider": source_label,
        "applied_date": applied_date.isoformat(),
        "run_status": run_status,
        "window_days": window_days,
        "days_elapsed_post_change": days_elapsed,
        "before_window": {
            "start": before_start.isoformat(),
            "end": before_end.isoformat(),
            "metrics": before_metrics,
        },
        "after_window": {
            "start": after_start.isoformat(),
            "end": (after_start + timedelta(days=days_elapsed - 1)).isoformat() if days_elapsed > 0 else None,
            "target_end": after_end.isoformat(),
            "metrics": after_metrics,
        },
        "delta": delta,
        "timeline": timeline,
        "interpretation": _interpret_delta(delta, run_status, days_elapsed, window_days, source_label),
    }


def _get_google_rows(db: Session, site_id: int, target_url: str | None) -> tuple[list[dict], str | None]:
    base_criteria = [
        GscRow.site_id == site_id,
        GscRow.dataset == "query_page",
        GscRow.day.is_not(None),
        GscRow.impressions > 0,
    ]
    if target_url:
        base_criteria.append(GscRow.page == target_url)

    sources = {r[0] for r in db.execute(select(GscRow.source).where(*base_criteria).distinct())}
    if not sources:
        return [], None

    source = "api" if "api" in sources else "csv"
    criteria = [*base_criteria, GscRow.source == source]

    fetched = list(
        db.scalars(
            select(GscRow)
            .where(*criteria)
            .order_by(GscRow.day.asc())
            .limit(30000)
        )
    )
    rows = [
        {
            "day": r.day,
            "query": r.query,
            "page": r.page,
            "clicks": r.clicks,
            "impressions": r.impressions,
            "position": r.position,
        }
        for r in fetched
    ]
    return rows, f"Google Search Console ({source.upper()})"


def evaluate_experiment(
    db: Session,
    site_id: int,
    experiment: SeoResearchRecord,
    window_days: int = 28,
    engine: Literal["google", "bing", "both"] = "google",
) -> dict[str, Any]:
    """Calculates before/after performance for a dated SEO experiment using Google or Bing."""
    payload = experiment.payload or {}
    applied_str = payload.get("applied_date")
    if not applied_str:
        return {
            "has_data": False,
            "reason": "Kein Änderungsdatum (applied_date) im Experiment hinterlegt",
        }

    try:
        if isinstance(applied_str, datetime):
            applied_date = applied_str.date()
        elif isinstance(applied_str, date):
            applied_date = applied_str
        else:
            applied_date = date.fromisoformat(str(applied_str)[:10])
    except ValueError:
        return {"has_data": False, "reason": f"Ungültiges Datumsformat: {applied_str}"}

    target_url = payload.get("target_url")
    google_rows, google_label = _get_google_rows(db, site_id, target_url)
    bing_observations = get_bing_observations(db, site_id)
    if target_url:
        bing_rows = [row for row in bing_observations if row.get("page") == target_url]
    else:
        traffic_rows = [row for row in bing_observations if row.get("provider_operation") == "traffic"]
        bing_rows = traffic_rows or [row for row in bing_observations if row.get("provider_operation") == "page_queries"]

    if engine == "bing":
        eval_bing = _evaluate_row_series(
            bing_rows, applied_date, window_days, "Bing Webmaster Tools", target_url
        )
        return {
            **eval_bing,
            "experiment_id": experiment.id,
            "title": experiment.title,
            "category": payload.get("category", "other"),
            "target_url": target_url,
            "active_engine": "bing",
        }

    if engine == "both":
        eval_google = _evaluate_row_series(
            google_rows, applied_date, window_days, google_label or "Google Search Console", target_url
        )
        eval_bing = _evaluate_row_series(
            bing_rows, applied_date, window_days, "Bing Webmaster Tools", target_url
        )
        return {
            "has_data": eval_google["has_data"] or eval_bing["has_data"],
            "experiment_id": experiment.id,
            "title": experiment.title,
            "category": payload.get("category", "other"),
            "target_url": target_url,
            "active_engine": "both",
            "applied_date": applied_date.isoformat(),
            "google": eval_google,
            "bing": eval_bing,
        }

    # Default: Google
    eval_google = _evaluate_row_series(
        google_rows, applied_date, window_days, google_label or "Google Search Console", target_url
    )
    return {
        **eval_google,
        "experiment_id": experiment.id,
        "title": experiment.title,
        "category": payload.get("category", "other"),
        "target_url": target_url,
        "active_engine": "google",
    }


def _interpret_delta(delta: dict[str, Any], status: str, elapsed: int, total_days: int, provider: str) -> str:
    c_pct = delta.get("clicks_pct")
    i_pct = delta.get("impressions_pct")
    pos_ch = delta.get("position_change")

    if status == "waiting_for_data":
        return f"Experiment angelegt. Noch keine {provider}-Daten nach dem Änderungsdatum vorhanden."

    prefix = f"{provider} Zwischenstand ({elapsed} von {total_days} Tagen): " if status == "in_progress" else f"{provider} Auswertung: "

    points = []
    if c_pct is not None:
        points.append(f"{'+' if c_pct > 0 else ''}{c_pct} % Klicks")
    if i_pct is not None:
        points.append(f"{'+' if i_pct > 0 else ''}{i_pct} % Impressionen")
    if pos_ch is not None:
        points.append(f"Position {'verbessert um ' + str(abs(pos_ch)) if pos_ch < 0 else 'verschlechtert um ' + str(pos_ch)}")

    if not points:
        return prefix + "Zu wenige Daten für eine belastbare Vorher-Nachher-Differenz."

    return prefix + "; ".join(points) + ". Externe Einflüsse (Saisonalität, Algorithmus-Updates) berücksichtigen."
