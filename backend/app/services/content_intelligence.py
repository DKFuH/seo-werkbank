"""Reproducible GSC content decay, keyword URL switching and trend signals.

GSC data is incomplete; outcomes are descriptive, not causal or proof of
cannibalisation. Input is pre-aggregated by source and date.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date


def _metrics(rows: list[dict]) -> dict:
    impressions = sum(float(r.get("impressions") or 0) for r in rows)
    clicks = sum(float(r.get("clicks") or 0) for r in rows)
    pos_rows = [r for r in rows if r.get("position") is not None and r.get("impressions")]
    weight = sum(float(r["impressions"]) for r in pos_rows)
    position = sum(float(r["position"]) * float(r["impressions"]) for r in pos_rows) / weight if weight else None
    return {"impressions": round(impressions), "clicks": round(clicks),
            "ctr": round(clicks / impressions, 4) if impressions else None,
            "position": round(position, 2) if position is not None else None}


def _difference(before: dict, after: dict) -> dict:
    def pct(a: float, b: float) -> float | None:
        return round((b - a) * 100 / a, 1) if a > 0 else None
    return {"clicks_pct": pct(before["clicks"], after["clicks"]),
            "impressions_pct": pct(before["impressions"], after["impressions"]),
            "position_change": round(after["position"] - before["position"], 2)
            if before["position"] is not None and after["position"] is not None else None,
            "ctr_change_pp": round((after["ctr"] - before["ctr"]) * 100, 2)
            if before["ctr"] is not None and after["ctr"] is not None else None}


def decay(rows: list[dict], split: date, min_previous_impressions: int = 40,
          limit: int = 100) -> list[dict]:
    """Compare equally long windows for individual URLs. Includes all query-page rows."""
    buckets: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"before": [], "after": []})
    for row in rows:
        if row.get("page") and isinstance(row.get("day"), date):
            buckets[row["page"]]["before" if row["day"] < split else "after"].append(row)
    out = []
    for page, sets in buckets.items():
        b, a = _metrics(sets["before"]), _metrics(sets["after"])
        if b["impressions"] < min_previous_impressions:
            continue
        delta = _difference(b, a)
        if delta["clicks_pct"] is None or delta["clicks_pct"] >= -15:
            continue
        pos_delta = delta["position_change"]
        if pos_delta is not None and pos_delta >= 1.5:
            reason = "positionsverlust"
        elif delta["impressions_pct"] is not None and delta["impressions_pct"] <= -15:
            reason = "impressionsrueckgang"
        elif delta["ctr_change_pp"] is not None and delta["ctr_change_pp"] <= -1.0:
            reason = "ctr_rueckgang"
        else:
            reason = "unklar"
        out.append({"url": page, "before": b, "after": a, "delta": delta,
                    "signal": reason, "review": "Query-Mix, Saisonalität, Suchnachfrage und Snippet manuell prüfen."})
    return sorted(out, key=lambda item: (item["delta"]["clicks_pct"], -item["before"]["impressions"]))[:limit]


def cannibalisation(rows: list[dict], split: date, min_impressions: int = 20,
                    limit: int = 100) -> list[dict]:
    """URL share and winner changes are overlap signals, *not* proof of harmful cannibalisation."""
    groups: dict[str, dict[str, dict[str, list[dict]]]] = defaultdict(
        lambda: defaultdict(lambda: {"before": [], "after": []}))
    for row in rows:
        if row.get("query") and row.get("page") and isinstance(row.get("day"), date):
            key = " ".join(row["query"].casefold().split())
            groups[key][row["page"]]["before" if row["day"] < split else "after"].append(row)
    out = []
    for query, landing in groups.items():
        if len(landing) < 2:
            continue
        entries = []
        for url, sets in landing.items():
            before, after = _metrics(sets["before"]), _metrics(sets["after"])
            if before["impressions"] + after["impressions"] > 0:
                entries.append({"url": url, "before": before, "after": after,
                                "total": before["impressions"] + after["impressions"]})
        total = sum(x["total"] for x in entries)
        substantial = [x for x in entries if x["total"] >= max(min_impressions, 0.15 * total)]
        if len(substantial) < 2:
            continue
        for x in entries:
            x["impression_share"] = round(x["total"] / total, 3) if total else 0
        first_previous = sorted(entries, key=lambda row: (-row["before"]["impressions"], row["url"]))[0]
        first_current = sorted(entries, key=lambda row: (-row["after"]["impressions"], row["url"]))[0]
        previous = first_previous["url"] if first_previous["before"]["impressions"] else None
        current = first_current["url"] if first_current["after"]["impressions"] else None
        out.append({"query": query, "impressions": round(total),
                    "urls": sorted(entries, key=lambda x: -x["total"])[:8],
                    "previous_leader": previous, "current_leader": current,
                    "leader_changed": bool(previous and current and previous != current),
                    "interpretation": "Mehrere GSC-URLs sind ein Überschneidungs-Indiz; Site-Links, Gerätemix und "
                                      "Suchintention können dies ohne schädliche Kannibalisierung erklären."})
    return sorted(out, key=lambda x: (-int(x["leader_changed"]), -x["impressions"], x["query"]))[:limit]


def trends(rows: list[dict], split: date, min_recent_impressions: int = 10, limit: int = 100) -> list[dict]:
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"before": [], "after": []})
    for row in rows:
        if row.get("query") and isinstance(row.get("day"), date):
            key = " ".join(row["query"].casefold().split())
            groups[key]["before" if row["day"] < split else "after"].append(row)
    out = []
    for query, sets in groups.items():
        b, a = _metrics(sets["before"]), _metrics(sets["after"])
        if a["impressions"] < min_recent_impressions:
            continue
        pct = round((a["impressions"] - b["impressions"]) / b["impressions"] * 100, 1) if b["impressions"] else None
        if b["impressions"] and (pct is None or pct < 40):
            continue
        out.append({"query": query, "before": b, "after": a,
                    "growth_pct": pct, "new_in_sample": b["impressions"] == 0,
                    "interpretation": "Nur neu oder zunehmend in den vorhandenen GSC-Daten; "
                                      "keine Aussage über externen Suchtrend oder Suchvolumen."})
    return sorted(out, key=lambda x: (-x["after"]["impressions"], x["query"]))[:limit]
