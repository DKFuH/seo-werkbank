"""Bing weekly page-query observations, never inferred from separate totals."""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Hashable
from datetime import date, timedelta

from ..integrations.bing import parse_ms_date
from .content_gap import analyze
from .content_intelligence import cannibalisation, decay, trends


def normalize_page_queries(page: str, data: list[dict]) -> list[dict]:
    observations = {}
    for raw in data:
        try:
            day = date.fromisoformat(parse_ms_date(raw.get("Date")) or "")
            query = raw["Query"].strip()
            impressions = int(raw["Impressions"])
            clicks = int(raw["Clicks"])
            position = raw.get("AvgImpressionPosition")
            position = float(position) if position is not None else None
            if not query or impressions <= 0 or clicks < 0 or clicks > impressions:
                continue
            if position is not None and (not math.isfinite(position) or position <= 0):
                position = None
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            continue
        key = (day, query, page)
        row = {"day": day, "query": query, "page": page, "impressions": impressions,
               "clicks": clicks, "position": position}
        if key in observations and observations[key] != row:
            raise ValueError("Conflicting Bing observations for identical page/query/week")
        observations[key] = row
    return list(observations.values())


def _complete_series(rows: list[dict], split: date, before_dates: set[date],
                     after_dates: set[date], key: Callable[[dict], Hashable]) -> list[dict]:
    """Keep only series observed in every expected week of both windows."""
    coverage: dict[Hashable, dict[str, set[date]]] = defaultdict(
        lambda: {"before": set(), "after": set()})
    for row in rows:
        coverage[key(row)]["before" if row["day"] < split else "after"].add(row["day"])
    complete = {series for series, windows in coverage.items()
                if before_dates <= windows["before"] and after_dates <= windows["after"]}
    return [row for row in rows if key(row) in complete]


def analyze_sample(rows: list[dict], pages: list[dict], weeks: int = 4, limit: int = 60) -> dict:
    if not rows:
        return {"provider": "bing", "has_data": False, "clusters": [], "decay": [],
                "cannibalisation": [], "trends": []}
    end = max(row["day"] for row in rows)
    after_dates = {end - timedelta(weeks=offset) for offset in range(weeks)}
    before_dates = {end - timedelta(weeks=offset) for offset in range(weeks, 2 * weeks)}
    expected_dates = before_dates | after_dates
    split = min(after_dates)
    start = min(before_dates)
    sample = [r for r in rows if r["day"] in expected_dates]
    recent = [r for r in sample if r["day"] >= split]
    # Weekly samples are not daily observations. Absence is not confirmed zero.
    observed = {r["day"] for r in sample}
    comparable = expected_dates <= observed
    gaps = analyze(recent, pages, max_results=limit, source_label="Bing")
    decay_rows = _complete_series(
        sample, split, before_dates, after_dates, lambda row: row["page"])
    trend_rows = _complete_series(
        sample, split, before_dates, after_dates,
        lambda row: " ".join(row["query"].casefold().split()))
    overlap_rows = _complete_series(
        sample, split, before_dates, after_dates,
        lambda row: (" ".join(row["query"].casefold().split()), row["page"]))
    # The shared algorithms assume missing rows are zero. For incomplete
    # provider samples, do not assert decay or trends without coverage.
    return {**gaps, "provider": "bing", "has_data": True, "granularity": "weekly",
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "comparable_windows": comparable,
            "decay": decay(decay_rows, split, limit=limit) if comparable else [],
            "cannibalisation": cannibalisation(
                overlap_rows, split, limit=limit, source_label="Bing") if comparable else [],
            "trends": trends(
                trend_rows, split, limit=limit, source_label="Bing") if comparable else [],
            "method": "Bing page-query observations and lexical crawl coverage",
            "notes": ["Bounded Bing sample, not complete site traffic; missing rows are not verified zero. "
                      "Signals are descriptive, not proof of cannibalisation or missing content."]}


def get_bing_observations(db, site_id: int) -> list[dict]:
    """Loads and normalizes all stored Bing query/page observations from SearchProviderSnapshots."""
    from sqlalchemy import select

    from ..models import SearchProviderSnapshot

    snapshots = db.scalars(
        select(SearchProviderSnapshot).where(
            SearchProviderSnapshot.site_id == site_id,
            SearchProviderSnapshot.provider == "bing",
        ).order_by(SearchProviderSnapshot.id.desc())
    ).all()

    observations = []
    seen = set()

    for snap in snapshots:
        payload = snap.payload or {}
        raw_list = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(raw_list, list):
            raw_list = payload.get("d") if isinstance(payload, dict) else None
        if not isinstance(raw_list, list):
            continue

        if snap.operation == "page_queries":
            page = (snap.parameters or {}).get("url") or snap.property_url
            for row in normalize_page_queries(page, raw_list):
                row["provider_operation"] = snap.operation
                key = (row["day"], row["query"], row["page"])
                if key not in seen:
                    seen.add(key)
                    observations.append(row)
        elif snap.operation in ("traffic", "pages", "query_pages"):
            for raw in raw_list:
                if not isinstance(raw, dict):
                    continue
                d_str = parse_ms_date(raw.get("Date"))
                if not d_str:
                    continue
                try:
                    day = date.fromisoformat(d_str[:10])
                    query = str(raw.get("Query") or "").strip()
                    clicks = int(raw.get("Clicks") or 0)
                    impressions = int(raw.get("Impressions") or 0)
                    pos = raw.get("AvgImpressionPosition")
                    position = float(pos) if pos is not None and math.isfinite(float(pos)) and float(pos) > 0 else None
                except (ValueError, TypeError, OverflowError):
                    continue
                page = str(raw.get("Page") or raw.get("Url") or "").strip()
                key = (day, query, page)
                if key not in seen:
                    seen.add(key)
                    observations.append({
                        "day": day, "query": query, "page": page,
                        "clicks": clicks, "impressions": impressions, "position": position,
                        "provider_operation": snap.operation,
                    })
    return observations
