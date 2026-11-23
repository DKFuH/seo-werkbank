"""Google Search Console: OAuth 2.0 (user-supplied client), Search Analytics sync, CSV import and insights."""
from __future__ import annotations

import secrets
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlencode, urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import GscRow
from ..security.auth import create_access_token, decode_payload
from ..services.settings_store import get_private, get_setting, set_private

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - an endpoint URL, not a credential
API = "https://www.googleapis.com/webmasters/v3"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
# Approximate organic CTR by position, used only to *estimate* upside. Real CTR varies by query and SERP layout.
EXPECTED_CTR = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018}


class GscError(RuntimeError):
    pass


class GscForbidden(GscError):
    """The authorisation was started by a different account (or was already used)."""


# One-time nonces of OAuth flows in progress: nonce -> (user id, expiry). In memory is enough: a restart only
# means the person clicks "Connect" again.
_pending: dict[str, tuple[int, float]] = {}
STATE_MINUTES = 15


def issue_state(user_id: int) -> str:
    now = time.time()
    for nonce in [n for n, (_u, exp) in _pending.items() if exp < now]:
        _pending.pop(nonce, None)
    if len(_pending) > 1000:
        _pending.pop(next(iter(_pending)), None)
    nonce = secrets.token_urlsafe(16)
    _pending[nonce] = (user_id, now + STATE_MINUTES * 60)
    return create_access_token(user_id, purpose="gsc_oauth", minutes=STATE_MINUTES, nonce=nonce)


def consume_state(state: str, user_id: int) -> None:
    """Accept ``state`` only for the account that requested it, and only once.

    The Google redirect carries no credentials of its own, so without this check anyone could send a victim
    their own consent link and have the victim's Google access stored under the sender's account.
    """
    try:
        payload = decode_payload(state, purpose="gsc_oauth")
    except HTTPException as exc:  # not a 401: that would sign the person out of the app for a bad link
        raise GscForbidden("Dieser Google-Autorisierungslink ist ungültig. Verbindung neu starten.") from exc
    entry = _pending.pop(str(payload.get("nonce", "")), None)
    if entry is None or entry[1] < time.time() or entry[0] != user_id or int(payload["sub"]) != user_id:
        raise GscForbidden("Diese Google-Autorisierung stammt nicht von deinem Konto oder ist abgelaufen. Verbindung neu starten.")


def redirect_uri() -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/api/gsc/callback"


def auth_url(db: Session, state: str) -> str:
    cfg = get_setting(db, "gsc")
    if not cfg.get("client_id") or not cfg.get("client_secret"):
        raise GscError("Zuerst Google-OAuth-Client-ID und -Secret in den Einstellungen hinterlegen.")
    return AUTH_URL + "?" + urlencode({
        "client_id": cfg["client_id"], "redirect_uri": redirect_uri(), "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state})


async def exchange_code(db: Session, user_id: int, code: str) -> None:
    cfg = get_setting(db, "gsc")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data={"code": code, "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                                               "redirect_uri": redirect_uri(), "grant_type": "authorization_code"})
    if r.status_code != 200:
        raise GscError(f"Google hat den Autorisierungscode abgelehnt: {r.text[:200]}")
    tok = r.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    set_private(db, f"gsc_tokens:{user_id}", tok)


async def _access_token(db: Session, user_id: int) -> str:
    tok = get_private(db, f"gsc_tokens:{user_id}")
    if not tok:
        raise GscError("Die Search Console ist für dieses Konto nicht verbunden.")
    if tok.get("expires_at", 0) > time.time():
        return tok["access_token"]
    if not tok.get("refresh_token"):
        raise GscError("Die Search-Console-Sitzung ist abgelaufen. In den Einstellungen neu verbinden.")
    cfg = get_setting(db, "gsc")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data={"client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                                               "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise GscError("Search-Console-Token konnte nicht erneuert werden. In den Einstellungen neu verbinden.")
    new = r.json()
    tok.update(access_token=new["access_token"], expires_at=time.time() + new.get("expires_in", 3600) - 60)
    set_private(db, f"gsc_tokens:{user_id}", tok)
    db.commit()
    return tok["access_token"]


def is_connected(db: Session, user_id: int) -> bool:
    return bool(get_private(db, f"gsc_tokens:{user_id}"))


def disconnect(db: Session, user_id: int) -> None:
    set_private(db, f"gsc_tokens:{user_id}", {})


async def list_properties(db: Session, user_id: int) -> list[dict]:
    token = await _access_token(db, user_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API}/sites", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise GscError(f"Fehler der Search-Console-API {r.status_code}: {r.text[:200]}")
    return [{"property": s["siteUrl"], "permission": s.get("permissionLevel")} for s in r.json().get("siteEntry", [])]


async def _query(client: httpx.AsyncClient, token: str, prop: str, body: dict) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        r = await client.post(f"{API}/sites/{quote(prop, safe='')}/searchAnalytics/query",
                              headers={"Authorization": f"Bearer {token}"}, json={**body, "rowLimit": 25000, "startRow": start})
        if r.status_code != 200:
            raise GscError(f"Fehler der Search-Console-API {r.status_code}: {r.text[:200]}")
        batch = r.json().get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000 or len(rows) >= 200_000:
            return rows
        start += 25000


DATASETS = {"query_page": ["date", "query", "page"], "country": ["date", "country"], "device": ["date", "device"],
            "appearance": ["searchAppearance"]}


async def sync(db: Session, user_id: int, site_id: int, prop: str, days: int = 90) -> dict:
    """Pull Search Analytics data for the last ``days`` days and replace stored API rows for that period."""
    token = await _access_token(db, user_id)
    end = date.today() - timedelta(days=2)  # GSC data lags ~2 days
    start = end - timedelta(days=days - 1)
    counts = {}
    async with httpx.AsyncClient(timeout=120) as client:
        for dataset, dims in DATASETS.items():
            rows = await _query(client, token, prop, {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dims})
            payload = []
            for r in rows:
                keys = dict(zip(dims, r.get("keys", []), strict=False))
                payload.append({
                    "site_id": site_id, "dataset": dataset, "source": "api",
                    "day": date.fromisoformat(keys["date"]) if "date" in keys else None,
                    "query": keys.get("query"), "page": keys.get("page"), "country": keys.get("country"),
                    "device": (keys.get("device") or "").lower() or None, "appearance": keys.get("searchAppearance"),
                    "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0), "position": r.get("position"),
                })
            cond = [GscRow.site_id == site_id, GscRow.dataset == dataset, GscRow.source == "api"]
            if dataset != "appearance":
                cond += [GscRow.day >= start, GscRow.day <= end]
            db.execute(delete(GscRow).where(*cond))
            for i in range(0, len(payload), 5000):
                db.execute(insert(GscRow), payload[i : i + 5000])
            counts[dataset] = len(payload)
    db.commit()
    return {"property": prop, "start": start.isoformat(), "end": end.isoformat(), "rows": counts}


# --------------------------------------------------------------------------- CSV import
_ALIASES = {
    "query": ("query", "top queries", "queries", "keyword", "search term",
              "häufigste suchanfragen", "suchanfragen", "suchanfrage", "top-suchanfragen"),
    "page": ("page", "top pages", "pages", "url", "landing page",
             "top-seiten", "häufigste seiten", "seiten", "seite"),
    "country": ("country", "land", "länder"), "device": ("device", "gerät", "geräte"),
    "appearance": ("search appearance", "darstellung in der suche", "suchdarstellung"),
    "day": ("date", "day", "datum", "tag"), "clicks": ("clicks", "klicks"), "impressions": ("impressions", "impressionen"),
    "position": ("position", "avg position", "average position", "durchschnittliche position", "ø position"),
}
# German Search Console exports name the columns in German and write numbers as 1.234 and 8,47.
_GERMAN_HEADERS = {"häufigste suchanfragen", "suchanfragen", "suchanfrage", "top-suchanfragen", "top-seiten", "häufigste seiten",
                   "seiten", "seite", "land", "länder", "gerät", "geräte", "darstellung in der suche", "suchdarstellung",
                   "datum", "tag", "klicks", "impressionen", "durchschnittliche position", "ø position"}
_DEVICES = {"mobilgerät": "mobile", "mobilgeräte": "mobile", "computer": "desktop", "desktop": "desktop", "tablet": "tablet"}


def parse_number(v: str, german: bool = False, strict: bool = False) -> float:
    """Parse 1,234.5 (English) or 1.234,5 (German) exports. ``strict`` raises ValueError instead of returning 0."""
    v = (v or "").replace("%", "").replace(" ", "").replace(" ", "").strip()
    if german or ("," in v and "." not in v and len(v.rsplit(",", 1)[1]) != 3):
        v = v.replace(".", "").replace(",", ".")  # 1.234,5 -> 1234.5 ; 8,47 -> 8.47
    else:
        v = v.replace(",", "")  # 1,234.5 -> 1234.5
    try:
        return float(v)
    except ValueError:
        if strict:
            raise
        return 0.0


_num = parse_number


def _day(v: str):
    v = (v or "").strip()
    for fmt, size in (("%Y-%m-%d", 10), ("%d.%m.%Y", 10), ("%d.%m.%y", 8)):
        try:
            return datetime.strptime(v[:size], fmt).date()
        except ValueError:
            continue
    return None


def import_csv(db: Session, site_id: int, raw: bytes, replace: bool = False, mapping: str | None = None,
               number_format: str = "auto") -> dict:
    """Import a Search Console performance export (Queries.csv, Pages.csv, Dates.csv ...) or any CSV with
    query/page/date/clicks/impressions/position columns. ``mapping`` (JSON {field: column}) overrides the detected
    columns; ``number_format`` "de"/"en" overrides the detection of 1.234,5 vs 1,234.5."""
    from ..services import csv_import

    try:
        header, rows, cols = csv_import.resolve(raw, "gsc", mapping)
    except csv_import.ImportFormatError as exc:
        raise GscError(str(exc)) from exc
    german = number_format == "de" or (number_format == "auto" and csv_import.german_numbers(header, "gsc"))
    reader = iter(rows)
    dims = [d for d in ("query", "page", "country", "device", "appearance", "day") if d in cols]
    dataset = ("query_page" if ("query" in cols or "page" in cols) else "country" if "country" in cols
               else "device" if "device" in cols else "appearance" if "appearance" in cols else "query_page")
    if replace:
        db.execute(delete(GscRow).where(GscRow.site_id == site_id, GscRow.source == "csv", GscRow.dataset == dataset))
    payload = []
    needed = max(cols.values()) + 1
    for row in reader:
        if len(row) < needed or len(payload) >= 500_000:
            continue
        def get(f, row=row):
            return row[cols[f]].strip() if f in cols else None
        day = None
        if get("day"):
            day = _day(get("day"))
            if day is None:
                continue
        device = (get("device") or "").lower()
        payload.append({"site_id": site_id, "dataset": dataset, "source": "csv", "day": day, "query": (get("query") or None),
                        "page": get("page") or None, "country": (get("country") or "").lower()[:8] or None,
                        "device": _DEVICES.get(device, device)[:12] or None, "appearance": get("appearance") or None,
                        "clicks": _num(get("clicks"), german), "impressions": _num(get("impressions"), german),
                        "position": _num(get("position"), german) if "position" in cols else None})
    for i in range(0, len(payload), 5000):
        db.execute(insert(GscRow), payload[i : i + 5000])
    db.commit()
    return {"rows": len(payload), "dataset": dataset, "dimensions": dims, "has_dates": "day" in cols}


# --------------------------------------------------------------------------- reporting
def _agg(db: Session, site_id: int, dataset: str, dim, start: date | None, end: date | None, limit: int = 1000) -> list[dict]:
    cond = [GscRow.site_id == site_id, GscRow.dataset == dataset, dim.isnot(None)]
    if start and end:
        cond.append((GscRow.day.between(start, end)) | (GscRow.day.is_(None)))
    clicks, imps = func.sum(GscRow.clicks), func.sum(GscRow.impressions)
    pos = func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0)
    rows = db.execute(select(dim, clicks, imps, pos).where(*cond).group_by(dim).order_by(clicks.desc(), imps.desc()).limit(limit)).all()
    return [{"key": k, "clicks": round(c or 0), "impressions": round(i or 0), "ctr": round((c or 0) / i, 4) if i else 0.0,
             "position": round(p, 1) if p is not None else None} for k, c, i, p in rows]


def date_range(db: Session, site_id: int) -> tuple[date | None, date | None]:
    return db.execute(select(func.min(GscRow.day), func.max(GscRow.day)).where(GscRow.site_id == site_id)).one()


def performance(db: Session, site_id: int, start: date | None = None, end: date | None = None) -> dict:
    lo, hi = date_range(db, site_id)
    total_rows = db.scalar(select(func.count()).select_from(GscRow).where(GscRow.site_id == site_id)) or 0
    if not total_rows:
        return {"has_data": False}
    dated = lo is not None
    if dated:
        end = min(end or hi, hi)
        start = max(start or (end - timedelta(days=27)), lo)
        span = (end - start).days + 1
        prev_end, prev_start = start - timedelta(days=1), start - timedelta(days=span)
    else:
        start = end = prev_start = prev_end = None

    def totals(s, e):
        cond = [GscRow.site_id == site_id, GscRow.dataset == "query_page"]
        if s and e:
            cond.append(GscRow.day.between(s, e))
        c, i, p = db.execute(select(func.sum(GscRow.clicks), func.sum(GscRow.impressions),
                                    func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0)).where(*cond)).one()
        return {"clicks": round(c or 0), "impressions": round(i or 0), "ctr": round((c or 0) / i, 4) if i else 0.0,
                "position": round(p, 1) if p is not None else None}

    series = []
    if dated:
        q = (select(GscRow.day, func.sum(GscRow.clicks), func.sum(GscRow.impressions),
                    func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0))
             .where(GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.day.between(start, end))
             .group_by(GscRow.day).order_by(GscRow.day))
        series = [{"date": d.isoformat(), "clicks": round(c or 0), "impressions": round(i or 0),
                   "ctr": round((c or 0) / i, 4) if i else 0.0, "position": round(p, 1) if p is not None else None}
                  for d, c, i, p in db.execute(q)]
    current = totals(start, end)
    previous = totals(prev_start, prev_end) if dated else None
    return {
        "has_data": True, "dated": dated,
        "range": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None,
                  "available_start": lo.isoformat() if lo else None, "available_end": hi.isoformat() if hi else None},
        "totals": current, "previous": previous, "series": series,
        "queries": _agg(db, site_id, "query_page", GscRow.query, start, end, 500),
        "pages": _agg(db, site_id, "query_page", GscRow.page, start, end, 500),
        "countries": _agg(db, site_id, "country", GscRow.country, start, end, 100),
        "devices": _agg(db, site_id, "device", GscRow.device, start, end, 10),
        "appearance": _agg(db, site_id, "appearance", GscRow.appearance, None, None, 50),
        "note": "Anonymisierte Suchanfragen fehlen in den Zeilen, daher können die Summen unter den Property-Summen der Search Console liegen.",
    }


def expected_ctr(position: float) -> float:
    return EXPECTED_CTR.get(max(1, min(10, round(position))), 0.01) if position <= 10.5 else 0.008


def insights(db: Session, site_id: int, days: int = 28) -> dict:
    """Declining queries/pages, quick-win opportunities, new queries and cannibalisation (all from measured GSC data)."""
    lo, hi = date_range(db, site_id)
    has_rows = db.scalar(select(func.count()).select_from(GscRow).where(GscRow.site_id == site_id, GscRow.dataset == "query_page"))
    if not has_rows:
        return {"has_data": False}
    dated = hi is not None and lo is not None and (hi - lo).days + 1 >= days * 2
    cur = _agg(db, site_id, "query_page", GscRow.query, hi - timedelta(days=days - 1) if hi else None, hi, 5000)
    opportunities = []
    for q in cur:
        if q["position"] is None or q["impressions"] < 20:
            continue
        if 4 <= q["position"] <= 20:
            target = max(1, min(3, round(q["position"]) - 3))
            upside = q["impressions"] * expected_ctr(target) - q["clicks"]
            if upside > 1:
                opportunities.append({**q, "type": "striking distance", "estimated_extra_clicks": round(upside),
                                      "basis": f"Schätzung, falls die Suchanfrage Position {target} erreicht (allgemeine CTR-Kurve)"})
        elif q["position"] < 4 and q["ctr"] < expected_ctr(q["position"]) * 0.5 and q["impressions"] >= 100:
            opportunities.append({**q, "type": "low CTR for position", "estimated_extra_clicks": round(q["impressions"] * expected_ctr(q["position"]) - q["clicks"]),
                                  "basis": "CTR is under half the generic curve for this position; review title and description"})
    opportunities.sort(key=lambda o: -o["estimated_extra_clicks"])
    result = {"has_data": True, "dated": dated, "window_days": days, "opportunities": opportunities[:100],
              "declining_queries": [], "declining_pages": [], "new_queries": [], "lost_queries": []}
    if dated:
        cur_s, cur_e = hi - timedelta(days=days - 1), hi
        prev_s, prev_e = cur_s - timedelta(days=days), cur_s - timedelta(days=1)
        for dim, key in ((GscRow.query, "queries"), (GscRow.page, "pages")):
            now = {r["key"]: r for r in _agg(db, site_id, "query_page", dim, cur_s, cur_e, 5000)}
            before = {r["key"]: r for r in _agg(db, site_id, "query_page", dim, prev_s, prev_e, 5000)}
            declines = []
            for k, b in before.items():
                n = now.get(k, {"clicks": 0, "impressions": 0, "position": None, "ctr": 0})
                drop = b["clicks"] - n["clicks"]
                if drop >= 3 and (b["clicks"] == 0 or drop / max(b["clicks"], 1) >= 0.2):
                    declines.append({"key": k, "clicks": n["clicks"], "previous_clicks": b["clicks"], "click_change": -drop,
                                     "impressions": n["impressions"], "previous_impressions": b["impressions"],
                                     "position": n["position"], "previous_position": b["position"]})
            declines.sort(key=lambda d: d["click_change"])
            result[f"declining_{key}"] = declines[:100]
            if key == "queries":
                result["new_queries"] = sorted((r for k, r in now.items() if k not in before and r["impressions"] >= 10),
                                               key=lambda r: -r["impressions"])[:100]
                result["lost_queries"] = sorted((r for k, r in before.items() if k not in now and r["clicks"] >= 1),
                                                key=lambda r: -r["clicks"])[:100]
    # Cannibalisation: one query, several pages with a meaningful share of impressions
    pairs = db.execute(select(GscRow.query, GscRow.page, func.sum(GscRow.clicks), func.sum(GscRow.impressions),
                              func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0))
                       .where(GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.query.isnot(None), GscRow.page.isnot(None))
                       .group_by(GscRow.query, GscRow.page)).all()
    by_query: dict[str, list] = defaultdict(list)
    for q, p, c, i, pos in pairs:
        by_query[q].append({"page": p, "clicks": round(c or 0), "impressions": round(i or 0), "position": round(pos, 1) if pos else None})
    cannibal = []
    for q, plist in by_query.items():
        total = sum(p["impressions"] for p in plist)
        strong = [p for p in plist if total and p["impressions"] / total >= 0.2]
        if len(strong) >= 2 and total >= 50:
            cannibal.append({"query": q, "impressions": total, "pages": sorted(strong, key=lambda p: -p["impressions"])})
    result["cannibalisation"] = sorted(cannibal, key=lambda c: -c["impressions"])[:100]
    return result


# --------------------------------------------------------------------------- ranking page per query
def _norm_page(url: str | None) -> str:
    p = urlsplit((url or "").strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/') or '/'}"


def ranking_pages(db: Session, site_id: int, queries: list[str], days: int = 90) -> dict[str, dict]:
    """For each query: the page with the most impressions in Search Console, plus all pages that received
    impressions. Needs rows that combine query and page (API sync or a query+page export)."""
    wanted = {" ".join(q.lower().split()) for q in queries if q.strip()}
    if not wanted:
        return {}
    cond = [GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.query.isnot(None), GscRow.page.isnot(None)]
    latest = db.scalar(select(func.max(GscRow.day)).where(*cond))
    if latest is not None:
        cond.append(GscRow.day >= latest - timedelta(days=days))
    rows = db.execute(
        select(func.lower(GscRow.query), GscRow.page, func.sum(GscRow.clicks), func.sum(GscRow.impressions),
               func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0))
        .where(*cond, func.lower(GscRow.query).in_(wanted))
        .group_by(func.lower(GscRow.query), GscRow.page)).all()
    out: dict[str, dict] = {}
    for q, page, clicks, imps, pos in rows:
        entry = out.setdefault(" ".join((q or "").split()), {"pages": []})
        entry["pages"].append({"url": page, "clicks": round(clicks or 0), "impressions": round(imps or 0),
                               "position": round(pos, 1) if pos is not None else None})
    for entry in out.values():
        entry["pages"].sort(key=lambda p: (-p["impressions"], -p["clicks"]))
        entry["top"] = entry["pages"][0]
        entry["pages"] = entry["pages"][:5]
    return out


def same_page(a: str | None, b: str | None) -> bool:
    return bool(a and b) and _norm_page(a) == _norm_page(b)

async def inspect_url(db: Session, user_id: int, prop: str, url: str) -> dict:
    """Index status from Google URL Inspection API; not Google's Live URL Test."""
    token = await _access_token(db, user_id)
    endpoint = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    async with httpx.AsyncClient(timeout=35) as client:
        r = await client.post(endpoint, json={"inspectionUrl": url, "siteUrl": prop, "languageCode": "de-DE"},
                              headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise GscError(f"Google URL Inspection nicht verfügbar (HTTP {r.status_code}). Property, Berechtigungen und Kontingent prüfen.")
    data = r.json().get("inspectionResult", {})
    idx = data.get("indexStatusResult") or {}
    return {"inspected_url": url, "property": prop, "inspection_result_link": data.get("inspectionResultLink"),
            "index": {k: idx.get(k) for k in ("verdict", "coverageState", "robotsTxtState", "indexingState",
                     "pageFetchState", "lastCrawlTime", "googleCanonical", "userCanonical", "crawledAs", "sitemap")},
            "source": "google_url_inspection_api",
            "method": "Google Index-Snapshot, kein Live-URL-Test. Daten können verzögert sein; API-Kontingent beachten."}

