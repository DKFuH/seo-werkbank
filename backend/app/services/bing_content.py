"""Bing weekly page-query observations, never inferred from separate totals."""
from __future__ import annotations

from datetime import date, timedelta
import math

from ..integrations.bing import parse_ms_date
from .content_gap import analyze
from .content_intelligence import decay, cannibalisation, trends


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


def analyze_sample(rows: list[dict], pages: list[dict], weeks: int = 4, limit: int = 60) -> dict:
    if not rows:
        return {"provider": "bing", "has_data": False, "clusters": [], "decay": [],
                "cannibalisation": [], "trends": []}
    end = max(row["day"] for row in rows)
    split = end - timedelta(weeks=weeks) + timedelta(days=1)
    start = end - timedelta(weeks=2 * weeks) + timedelta(days=1)
    sample = [r for r in rows if start <= r["day"] <= end]
    recent = [r for r in sample if r["day"] >= split]
    # Weekly samples are not daily observations. Absence is not confirmed zero.
    observed = {r["day"] for r in sample}
    before_dates = {d for d in observed if d < split}
    after_dates = {d for d in observed if d >= split}
    comparable = len(before_dates) >= weeks and len(after_dates) >= weeks
    gaps = analyze(recent, pages, max_results=limit)
    # The shared algorithms assume missing rows are zero. For incomplete
    # provider samples, do not assert decay or trends without coverage.
    return {**gaps, "provider": "bing", "has_data": True, "granularity": "weekly",
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "comparable_windows": comparable,
            "decay": decay(sample, split, limit=limit) if comparable else [],
            "cannibalisation": cannibalisation(sample, split, limit=limit) if comparable else [],
            "trends": trends(sample, split, limit=limit) if comparable else [],
            "method": "Bing page-query observations and lexical crawl coverage",
            "notes": ["Bounded Bing sample, not complete site traffic; missing rows are not verified zero. "
                      "Signals are descriptive, not proof of cannibalisation or missing content."]}
