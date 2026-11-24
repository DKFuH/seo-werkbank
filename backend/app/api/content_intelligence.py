"""Read-only Content Intelligence on dated, paired search-provider observations."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GscRow, User
from ..security.auth import current_user, get_site_for
from ..services.bing_content import analyze_sample, get_bing_observations
from ..services.content_intelligence import cannibalisation, decay, trends

router = APIRouter(tags=["content-intelligence"])


@router.get("/sites/{site_id}/content-intelligence")
def content_intelligence(
    site_id: int, days: int = Query(28, ge=7, le=90),
    limit: int = Query(60, ge=1, le=100),
    provider: Literal["google", "bing"] = Query("google"),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    if provider == "bing":
        rows = [row for row in get_bing_observations(db, site.id) if row.get("page")]
        weeks = max(2, min(12, round(days / 7)))
        result = analyze_sample(rows, [], weeks=weeks, limit=limit)
        return {**result, "provider": "bing", "provider_label": "Bing Webmaster Tools",
                "source": "snapshot", "days_per_window": weeks * 7,
                "observations": len(rows)}

    base = [
        GscRow.site_id == site.id, GscRow.dataset == "query_page",
        GscRow.day.is_not(None), GscRow.query.is_not(None), GscRow.page.is_not(None),
        GscRow.impressions > 0,
    ]
    available = {x for (x,) in db.execute(select(GscRow.source).where(*base).distinct())}
    source = "api" if "api" in available else "csv" if "csv" in available else None
    if source is None:
        return {"has_data": False, "provider": "google", "provider_label": "Google Search Console", "source": None,
                "reason": "Datierte Google-Search-Console-Suchanfrage-URL-Paare erforderlich.",
                "decay": [], "cannibalisation": [], "trends": []}
    conditions = [*base, GscRow.source == source]
    end = db.scalar(select(func.max(GscRow.day)).where(*conditions))
    if not end:
        return {"has_data": False, "provider": "google", "provider_label": "Google Search Console", "source": source,
                "reason": "Datierte Google-Search-Console-Daten erforderlich.",
                "decay": [], "cannibalisation": [], "trends": []}
    first = end - timedelta(days=2 * days - 1)
    fetched = list(db.scalars(select(GscRow).where(*conditions, GscRow.day.between(first, end))
                              .order_by(GscRow.impressions.desc()).limit(50001)))
    clipped = len(fetched) > 50000
    rows = [{"day": row.day, "query": row.query, "page": row.page,
             "clicks": row.clicks, "impressions": row.impressions,
             "position": row.position} for row in fetched[:50000]]
    result = _analyse_rows(rows, days, limit, provider="google", source=source)
    result["truncated"] = clipped
    result["notes"] = ([
            "Zeitfenster gleich lang, jedoch nicht saisonbereinigt. Ursachen sind Hypothesen.",
            "GSC liefert nur einen Teil aller Queries; Query-URL-Metriken können gegenüber Query-Metriken abweichen.",
            "URL-Wechsel und mehrere Landingpages sind kein Beweis einer schädlichen Kannibalisierung.",
            "GSC-Query-URL-Paare werden nach Datenquelle getrennt, API hat Vorrang vor CSV.",
        ] + (["Wegen 50.000 Zeilenlimit gekürzt; Interpretationen können verzerrt sein."] if clipped else [])
          + (["Zusätzliche CSV-Daten nicht doppelt addiert."] if source == "api" and "csv" in available else []))
    return result


def _analyse_rows(rows: list[dict], days: int, limit: int, *, provider: str, source: str) -> dict:
    dated = [row for row in rows if isinstance(row.get("day"), date)]
    label = "Google Search Console" if provider == "google" else "Bing Webmaster Tools"
    if not dated:
        return {"has_data": False, "provider": provider, "source": source,
                "reason": f"Datierte {label}-Suchanfrage-URL-Paare erforderlich.",
                "decay": [], "cannibalisation": [], "trends": []}
    end = max(row["day"] for row in dated)
    first = end - timedelta(days=2 * days - 1)
    split = end - timedelta(days=days - 1)
    sample = [row for row in dated if first <= row["day"] <= end]
    source_label = "GSC" if provider == "google" else "Bing"
    return {
        "has_data": True, "provider": provider, "provider_label": label, "source": source,
        "start_date": first.isoformat(), "split_date": split.isoformat(), "end_date": end.isoformat(),
        "days_per_window": days, "truncated": False, "observations": len(sample),
        "decay": decay(sample, split, limit=limit),
        "cannibalisation": cannibalisation(sample, split, limit=limit, source_label=source_label),
        "trends": trends(sample, split, limit=limit, source_label=source_label),
        "notes": [
            "Google- und Bing-Metriken werden getrennt ausgewertet; Positionen werden nicht suchmaschinenübergreifend gemittelt.",
            "Gespeicherte Bing-Snapshots sind eine begrenzte Stichprobe; fehlende Zeilen sind keine bestätigten Nullwerte.",
        ] if provider == "bing" else [],
    }
