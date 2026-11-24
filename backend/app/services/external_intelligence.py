"""Optional real GA4, Microsoft Clarity and paid geo-targeted SERP adapters.

All requests go to allowlisted provider URLs and use credentials encrypted in
per-owner/per-site private settings. No fake fallback measurements.
"""
from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
import jwt

from ..services.settings_store import get_private, set_private

GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GA4_TOKEN = "https://oauth2.googleapis.com/token"
GA4_API = "https://analyticsdata.googleapis.com/v1beta/properties"
CLARITY_API = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
DATAFORSEO_ROOT = "https://api.dataforseo.com/v3/serp/google"
PROVIDERS = ("ga4", "clarity", "dataforseo")


class ProviderError(ValueError):
    pass


def credential_key(provider: str, owner_id: int, site_id: int) -> str:
    if provider not in PROVIDERS:
        raise ProviderError("Unbekannter Datenanbieter")
    return f"external_intel:{provider}:{owner_id}:{site_id}"


def configure(db, provider: str, owner_id: int, site_id: int, values: dict) -> None:
    set_private(db, credential_key(provider, owner_id, site_id), values)


def config(db, provider: str, owner_id: int, site_id: int) -> dict:
    return get_private(db, credential_key(provider, owner_id, site_id))


def status(db, provider: str, owner_id: int, site_id: int) -> dict:
    cfg = config(db, provider, owner_id, site_id)
    required = {"ga4": ("property_id", "client_email", "private_key"),
                "clarity": ("token",), "dataforseo": ("login", "password")}[provider]
    return {"provider": provider, "connected": all(cfg.get(k) for k in required),
            "note": "Konfiguration vorhanden, Live-Zugriff und Berechtigungen noch nicht garantiert."}


async def ga4_overview(settings: dict, *, days: int = 28) -> dict:
    property_id = settings["property_id"]
    if not property_id.isdigit():
        raise ProviderError("GA4-Property-ID muss numerisch sein")
    now = int(datetime.now(UTC).timestamp())
    claim = {"iss": settings["client_email"], "scope": GA4_SCOPE, "aud": GA4_TOKEN,
             "iat": now, "exp": now + 3500}
    try:
        assertion = jwt.encode(claim, settings["private_key"], algorithm="RS256")
    except Exception as exc:
        raise ProviderError("Ungültiger GA4-Service-Account-Schlüssel") from exc
    async with httpx.AsyncClient(timeout=35) as client:
        token_res = await client.post(GA4_TOKEN, data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
        if token_res.status_code != 200:
            raise ProviderError(f"Google OAuth verweigert Token (HTTP {token_res.status_code}). Berechtigung prüfen.")
        token = token_res.json().get("access_token")
        if not token:
            raise ProviderError("Google OAuth hat keinen Access-Token geliefert")
        payload = {"dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "yesterday"}],
                   "metrics": [{"name": name} for name in ("sessions", "activeUsers", "screenPageViews", "conversions")]}
        response = await client.post(f"{GA4_API}/{property_id}:runReport",
                                     json=payload, headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            raise ProviderError(f"GA4 Data API meldet HTTP {response.status_code}")
    data = response.json()
    vals = (data.get("rows") or [{}])[0].get("metricValues") or []
    result = {name: None for name in ("sessions", "activeUsers", "screenPageViews", "conversions")}
    for i, name in enumerate(result):
        if i < len(vals):
            try:
                result[name] = float(vals[i]["value"])
            except (ValueError, TypeError, KeyError):
                pass
    return {"source": "google_analytics_data_api", "property_id": property_id,
            "days": days, "metrics": result,
            "note": "Aggregierte GA4-Messwerte, nicht mit GSC-Klicks gleichzusetzen."}


async def clarity_overview(settings: dict, *, days: int = 3) -> dict:
    if days not in (1, 2, 3):
        raise ProviderError("Clarity erlaubt nur 1, 2 oder 3 Tage")
    async with httpx.AsyncClient(timeout=35) as client:
        res = await client.get(CLARITY_API, params={"numOfDays": days, "dimension1": "Device"},
                               headers={"Authorization": f"Bearer {settings['token']}"})
    if res.status_code != 200:
        raise ProviderError(f"Clarity API meldet HTTP {res.status_code}; Tageskontingent/Berechtigung prüfen")
    data = res.json()
    if not isinstance(data, list):
        raise ProviderError("Clarity-Antwort hat unerwartetes Format")
    aggregates = []
    for group in data[:40]:
        if not isinstance(group, dict):
            continue
        records = group.get("information") or []
        if not isinstance(records, list):
            continue
        aggregates.append({"metric": str(group.get("metricName", ""))[:100],
                           "rows": [{k: v for k, v in entry.items()
                                     if k in {"Device", "device", "totalSessionCount", "sessions",
                                              "percentage", "metricName", "value", "average", "totalCount"}}
                                    for entry in records[:40] if isinstance(entry, dict)]})
    return {"source": "microsoft_clarity_export_api", "days": days, "metrics": aggregates,
            "note": "Aus der echten Clarity-API; zeitlich auf 1–3 Tage und Anbieterquoten begrenzt."}


def _same_site(url: str | None, target_host: str) -> bool:
    try:
        host = (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    except ValueError:
        return False
    return bool(host and host == target_host.removeprefix("www."))


async def local_serp(settings: dict, *, keyword: str, location: str, language: str,
                     own_host: str, depth: int = 20) -> dict:
    """Two paid DataForSEO endpoint calls, only after explicit user acknowledgement."""
    raw = f"{settings['login']}:{settings['password']}".encode()
    basic = base64.b64encode(raw).decode()
    body = [{"keyword": keyword, "location_name": location, "language_code": language,
             "depth": depth}]
    result = {}
    async with httpx.AsyncClient(timeout=50) as client:
        for mode in ("organic", "maps"):
            res = await client.post(f"{DATAFORSEO_ROOT}/{mode}/live/advanced", json=body,
                                    headers={"Authorization": f"Basic {basic}"})
            if res.status_code != 200:
                raise ProviderError(f"DataForSEO {mode}: HTTP {res.status_code}")
            task = (res.json().get("tasks") or [{}])[0]
            if task.get("status_code") != 20000:
                raise ProviderError(f"DataForSEO {mode}: Aufgabe fehlgeschlagen (Code {task.get('status_code')})")
            items = ((task.get("result") or [{}])[0].get("items") or [])
            matches = []
            for entry in items[:depth * 3]:
                if not isinstance(entry, dict):
                    continue
                if mode == "organic" and entry.get("type") != "organic":
                    continue
                if mode == "maps" and entry.get("type") not in ("maps_search", "maps"):
                    continue
                url = entry.get("url")
                domain = str(entry.get("domain") or "")
                if _same_site(url, own_host) or _same_site("https://" + domain, own_host):
                    matches.append({"position": entry.get("rank_absolute"),
                                    "url": url, "name": entry.get("title")})
            matches.sort(key=lambda e: e["position"] if isinstance(e["position"], int) else 99999)
            result[mode] = matches[0] if matches else None
    return {"source": "dataforseo_paid_serp_api", "keyword": keyword, "location": location,
            "language": language, "depth": depth, "organic": result["organic"], "maps": result["maps"],
            "note": "Geografische SERP-Stichprobe vom Datenanbieter. Maps-Treffer ohne Website-Domain "
                    "lassen sich nicht zuverlässig einem Betrieb zuordnen. Anbieteraufrufe sind kostenpflichtig."}
