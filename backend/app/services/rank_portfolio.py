"""Keyword portfolio from Search Console: real positions where Google showed the site, not a scraped ranking.

Positions are impression-weighted averages of GSC rows (lower is better). The current period ends at the newest GSC
day of the site; the previous period has the same length directly before it. API rows win over CSV rows so imports
and syncs of the same days are never added together.
"""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlsplit

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import GscRow, Keyword, KeywordNote

SMALL_SAMPLE = 10  # fewer impressions: shown, but flagged and not counted as discovery/opportunity
BUCKETS = (("1–3", 3), ("4–10", 10), ("11–20", 20), ("21–50", 50), ("51+", 10**9))
DEVICES = ("desktop", "mobile", "tablet")


def norm(q: str | None) -> str:
    # lower(), not casefold(): casefold turns "maß" into "mass", which would change German keywords.
    return " ".join((q or "").lower().split())


def _source(db: Session, site_id: int, dataset: str) -> str | None:
    found = {s for (s,) in db.execute(select(GscRow.source).where(GscRow.site_id == site_id, GscRow.dataset == dataset,
                                                                    GscRow.query.is_not(None), GscRow.day.is_not(None)).distinct())}
    return "api" if "api" in found else "csv" if "csv" in found else None


def bounds(db: Session, site_id: int, days: int) -> dict | None:
    source = _source(db, site_id, "query_page")
    if not source:
        return None
    end = db.scalar(select(func.max(GscRow.day)).where(GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.source == source))
    if end is None:
        return None
    start = end - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    return {"source": source, "start": start, "end": end, "prev_start": prev_end - timedelta(days=days - 1), "prev_end": prev_end}


def _base(db: Session, site_id: int, b: dict, device: str | None) -> tuple[list, str]:
    """Filter for the rows to aggregate; with a device filter the query_device dataset (date, query, device)."""
    if device:
        src = _source(db, site_id, "query_device")
        if src:
            return [GscRow.site_id == site_id, GscRow.dataset == "query_device", GscRow.source == src, GscRow.device == device,
                    GscRow.query.is_not(None)], "query_device"
        return [GscRow.site_id == site_id, GscRow.id == -1], "none"  # no device data: empty result, flagged by caller
    return [GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.source == b["source"], GscRow.query.is_not(None)], "query_page"


def _period_sums(lo: date, hi: date):
    in_period = GscRow.day.between(lo, hi)
    weighted = case((GscRow.position.is_not(None), GscRow.position * GscRow.impressions), else_=0)
    weight = case((GscRow.position.is_not(None), GscRow.impressions), else_=0)
    return (func.sum(case((in_period, GscRow.impressions), else_=0)), func.sum(case((in_period, GscRow.clicks), else_=0)),
            func.sum(case((in_period, weighted), else_=0)), func.sum(case((in_period, weight), else_=0)))


def query_stats(db: Session, site_id: int, b: dict, device: str | None, queries: set[str] | None = None) -> tuple[dict[str, dict], str]:
    """Per normalised query: current/previous impressions, clicks, position and movement (positive = improved)."""
    cond, dataset = _base(db, site_id, b, device)
    cond.append(GscRow.day.between(b["prev_start"], b["end"]))
    cur, prev = _period_sums(b["start"], b["end"]), _period_sums(b["prev_start"], b["prev_end"])
    rows = db.execute(select(func.lower(GscRow.query), *cur, *prev).where(*cond).group_by(func.lower(GscRow.query))).all()
    out: dict[str, dict] = {}
    for q, ci, cc, cw, cwt, pi, pc, pw, pwt in rows:
        key = norm(q)
        if queries is not None and key not in queries:
            continue
        e = out.setdefault(key, {"query": key, "ci": 0.0, "cc": 0.0, "cw": 0.0, "cwt": 0.0, "pi": 0.0, "pc": 0.0, "pw": 0.0, "pwt": 0.0})
        for k, v in zip(("ci", "cc", "cw", "cwt", "pi", "pc", "pw", "pwt"), (ci, cc, cw, cwt, pi, pc, pw, pwt), strict=True):
            e[k] += float(v or 0)
    result = {}
    for key, e in out.items():
        pos = e["cw"] / e["cwt"] if e["cwt"] else None
        prev_pos = e["pw"] / e["pwt"] if e["pwt"] else None
        result[key] = {"query": key, "impressions": round(e["ci"]), "clicks": round(e["cc"]),
                       "ctr": round(100 * e["cc"] / e["ci"], 2) if e["ci"] else None,
                       "position": round(pos, 2) if pos is not None else None,
                       "previous_position": round(prev_pos, 2) if prev_pos is not None else None,
                       "previous_impressions": round(e["pi"]),
                       "movement": round(prev_pos - pos, 2) if pos is not None and prev_pos is not None else None,
                       "_w": e["cw"], "_wt": e["cwt"], "_pw": e["pw"], "_pwt": e["pwt"]}
    return result, dataset


def best_urls(db: Session, site_id: int, b: dict, queries: set[str] | None = None) -> dict[str, str]:
    """Page with the most impressions per query in the current period (query_page rows)."""
    rows = db.execute(select(func.lower(GscRow.query), GscRow.page, func.sum(GscRow.impressions)).where(
        GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.source == b["source"], GscRow.page.is_not(None),
        GscRow.query.is_not(None), GscRow.day.between(b["start"], b["end"])).group_by(func.lower(GscRow.query), GscRow.page)).all()
    best: dict[str, tuple[float, str]] = {}
    for q, page, imps in rows:
        key = norm(q)
        if queries is not None and key not in queries:
            continue
        if key not in best or float(imps or 0) > best[key][0]:
            best[key] = (float(imps or 0), page)
    return {k: v[1] for k, v in best.items()}


def bucket_of(position: float | None) -> str | None:
    if position is None:
        return None
    return next(label for label, limit in BUCKETS if position <= limit)


def same_path(a: str | None, b: str | None) -> bool:
    def path(u: str) -> str:
        p = urlsplit(u)
        return (p.path if p.scheme else u.split("?")[0]).rstrip("/") or "/"
    return bool(a and b) and path(a) == path(b)


def trend(db: Session, site_id: int, b: dict, device: str | None, queries: set[str] | None, days: int) -> list[dict]:
    """Impression-weighted position per day (up to 28 days) or per week, over the given queries."""
    cond, _ = _base(db, site_id, b, device)
    cond += [GscRow.day.between(b["start"], b["end"]), GscRow.position.is_not(None)]
    if queries is not None:
        if not queries:
            return []
        cond.append(func.lower(GscRow.query).in_(list(queries)))
    rows = db.execute(select(GscRow.day, func.sum(GscRow.position * GscRow.impressions), func.sum(GscRow.impressions),
                             func.sum(GscRow.clicks)).where(*cond).group_by(GscRow.day).order_by(GscRow.day)).all()
    weekly = days > 28
    agg: dict[date, list[float]] = {}
    for day, w, imps, clicks in rows:
        key = day - timedelta(days=day.weekday()) if weekly else day
        a = agg.setdefault(key, [0.0, 0.0, 0.0])
        a[0] += float(w or 0)
        a[1] += float(imps or 0)
        a[2] += float(clicks or 0)
    return [{"date": d.isoformat(), "position": round(w / i, 2) if i else None, "impressions": round(i), "clicks": round(c)}
            for d, (w, i, c) in sorted(agg.items())]


def _keyword_out(k: Keyword, s: dict | None, url: str | None) -> dict:
    s = s or {}
    pos = s.get("position")
    return {"id": k.id, "keyword": k.keyword, "label": k.label, "target_url": k.target_url, "measurement": k.measurement,
            "priority": k.priority, "position": pos, "movement": s.get("movement"), "bucket": bucket_of(pos),
            "impressions": s.get("impressions", 0), "clicks": s.get("clicks", 0), "ctr": s.get("ctr"),
            "best_url": url, "small_sample": 0 < s.get("impressions", 0) < SMALL_SAMPLE,
            "url_mismatch": bool(url and k.target_url and not same_path(url, k.target_url))}


def portfolio(db: Session, site_id: int, *, days: int, device: str | None, label: str | None, q: str | None) -> dict:
    b = bounds(db, site_id, days)
    stmt = select(Keyword).where(Keyword.site_id == site_id, Keyword.tracked.is_(True))
    if label:
        stmt = stmt.where(Keyword.label == label)
    keywords = [k for k in db.scalars(stmt.order_by(Keyword.priority, Keyword.keyword)) if not q or norm(q) in norm(k.keyword)]
    labels = sorted({k.label for k in db.scalars(select(Keyword).where(Keyword.site_id == site_id, Keyword.tracked.is_(True))) if k.label})
    if b is None:
        return {"has_data": False, "labels": labels, "rows": [_keyword_out(k, None, None) for k in keywords]}
    wanted = {norm(k.keyword) for k in keywords}
    stats, dataset = query_stats(db, site_id, b, device, wanted)
    urls = best_urls(db, site_id, b, wanted)
    rows = [_keyword_out(k, stats.get(norm(k.keyword)), urls.get(norm(k.keyword))) for k in keywords]
    w = sum(s["_w"] for s in stats.values())
    wt = sum(s["_wt"] for s in stats.values())
    pw = sum(s["_pw"] for s in stats.values())
    pwt = sum(s["_pwt"] for s in stats.values())
    imps = sum(r["impressions"] for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    buckets = {label_: 0 for label_, _ in BUCKETS}
    for r in rows:
        if r["bucket"]:
            buckets[r["bucket"]] += 1
    avg, prev = (w / wt if wt else None), (pw / pwt if pwt else None)
    return {
        "has_data": True, "dataset": dataset, "device_data": dataset != "none", "labels": labels,
        "period": {k: v.isoformat() for k, v in b.items() if k != "source"}, "source": b["source"],
        "summary": {"position": round(avg, 2) if avg is not None else None,
                    "movement": round(prev - avg, 2) if avg is not None and prev is not None else None,
                    "buckets": buckets, "not_observed": sum(1 for r in rows if r["position"] is None),
                    "improved": sum(1 for r in rows if (r["movement"] or 0) > 0.05),
                    "worsened": sum(1 for r in rows if (r["movement"] or 0) < -0.05),
                    "impressions": imps, "clicks": clicks, "ctr": round(100 * clicks / imps, 2) if imps else None,
                    "keywords": len(rows)},
        "trend": trend(db, site_id, b, device, wanted, days), "granularity": "week" if days > 28 else "day",
        "rows": rows,
    }


def all_queries(db: Session, site_id: int, *, days: int, device: str | None, scope: str, bucket: str, min_impressions: int,
                q: str | None, sort: str, direction: str, page: int, per_page: int = 100) -> dict:
    b = bounds(db, site_id, days)
    if b is None:
        return {"has_data": False, "rows": [], "total": 0, "summary": {}}
    stats, dataset = query_stats(db, site_id, b, device)
    tracked = {norm(k.keyword): k.id for k in db.scalars(select(Keyword).where(Keyword.site_id == site_id, Keyword.tracked.is_(True)))}
    rows = []
    summary = {"queries": 0, "untracked": 0, "top_discoveries": 0, "opportunities": 0, "untracked_impressions": 0, "untracked_clicks": 0}
    for key, s in stats.items():
        if not s["impressions"] and not s["previous_impressions"]:
            continue
        is_tracked = key in tracked
        solid = s["impressions"] >= SMALL_SAMPLE and s["position"] is not None
        top = not is_tracked and solid and s["position"] <= 3
        chance = not is_tracked and solid and 3 < s["position"] <= 20
        summary["queries"] += 1
        if not is_tracked:
            summary["untracked"] += 1
            summary["untracked_impressions"] += s["impressions"]
            summary["untracked_clicks"] += s["clicks"]
        summary["top_discoveries"] += top
        summary["opportunities"] += chance
        rows.append({k: v for k, v in s.items() if not k.startswith("_")} |
                    {"tracked": is_tracked, "keyword_id": tracked.get(key), "top_discovery": top, "opportunity": chance,
                     "bucket": bucket_of(s["position"])})
    needle = norm(q)

    def keep(r: dict) -> bool:
        p = r["position"]
        if scope == "tracked" and not r["tracked"] or scope == "untracked" and r["tracked"]:
            return False
        if r["impressions"] < min_impressions or needle and needle not in r["query"]:
            return False
        limits = {"top3": 3, "top10": 10, "top20": 20, "top50": 50}
        if bucket in limits:
            return p is not None and p <= limits[bucket]
        if bucket == "opportunity":
            return r["opportunity"]
        if bucket == "51plus":
            return p is not None and p > 50
        return True
    rows = [r for r in rows if keep(r)]
    keys = {"query": lambda r: r["query"], "position": lambda r: (r["position"] is None, r["position"] or 0),
            "movement": lambda r: (r["movement"] is None, r["movement"] or 0), "impressions": lambda r: r["impressions"],
            "clicks": lambda r: r["clicks"], "ctr": lambda r: (r["ctr"] is None, r["ctr"] or 0)}
    rows.sort(key=keys.get(sort, keys["impressions"]), reverse=direction == "desc")
    total = len(rows)
    shown = rows[(page - 1) * per_page: page * per_page]
    urls = best_urls(db, site_id, b, {r["query"] for r in shown})
    for r in shown:
        r["best_url"] = urls.get(r["query"])
    return {"has_data": True, "device_data": dataset != "none", "period": {k: v.isoformat() for k, v in b.items() if k != "source"},
            "summary": summary, "rows": shown, "total": total, "page": page, "pages": max(1, -(-total // per_page))}


def keyword_detail(db: Session, site_id: int, k: Keyword, *, days: int, device: str | None) -> dict:
    notes = [{"id": n.id, "date": n.event_date.isoformat(), "title": n.title, "details": n.details}
             for n in db.scalars(select(KeywordNote).where(KeywordNote.keyword_id == k.id).order_by(KeywordNote.event_date.desc(), KeywordNote.id.desc()))]
    b = bounds(db, site_id, days)
    if b is None:
        return {"has_data": False, "keyword": _keyword_out(k, None, None), "trend": [], "notes": notes}
    key = norm(k.keyword)
    stats, dataset = query_stats(db, site_id, b, device, {key})
    url = best_urls(db, site_id, b, {key}).get(key)
    return {"has_data": True, "device_data": dataset != "none", "period": {k_: v.isoformat() for k_, v in b.items() if k_ != "source"},
            "keyword": _keyword_out(k, stats.get(key), url), "trend": trend(db, site_id, b, device, {key}, days),
            "granularity": "week" if days > 28 else "day", "notes": notes}
