"""Read-only Content Intelligence on dated, paired GSC observations."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GscRow, User
from ..security.auth import current_user, get_site_for
from ..services.content_intelligence import cannibalisation, decay, trends

router = APIRouter(tags=["content-intelligence"])


@router.get("/sites/{site_id}/content-intelligence")
def content_intelligence(
    site_id: int, days: int = Query(28, ge=7, le=90),
    limit: int = Query(60, ge=1, le=100),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    site = get_site_for(db, user, site_id)
    base = [
        GscRow.site_id == site.id, GscRow.dataset == "query_page",
        GscRow.day.is_not(None), GscRow.query.is_not(None), GscRow.page.is_not(None),
        GscRow.impressions > 0,
    ]
    available = {x for (x,) in db.execute(select(GscRow.source).where(*base).distinct())}
    source = "api" if "api" in available else "csv" if "csv" in available else None
    if source is None:
        return {"has_data": False, "reason": "Datierte GSC-Suchanfrage-URL-Paare erforderlich.",
                "decay": [], "cannibalisation": [], "trends": []}
    conditions = [*base, GscRow.source == source]
    end = db.scalar(select(func.max(GscRow.day)).where(*conditions))
    if not end:
        return {"has_data": False, "reason": "Datierte GSC-Daten erforderlich.",
                "decay": [], "cannibalisation": [], "trends": []}
    first = end - timedelta(days=2 * days - 1)
    split = end - timedelta(days=days - 1)
    fetched = list(db.scalars(select(GscRow).where(*conditions, GscRow.day.between(first, end))
                              .order_by(GscRow.impressions.desc()).limit(50001)))
    clipped = len(fetched) > 50000
    rows = [{"day": row.day, "query": row.query, "page": row.page,
             "clicks": row.clicks, "impressions": row.impressions,
             "position": row.position} for row in fetched[:50000]]
    return {
        "has_data": True, "source": source, "start_date": first.isoformat(),
        "split_date": split.isoformat(), "end_date": end.isoformat(),
        "days_per_window": days, "truncated": clipped, "observations": len(rows),
        "decay": decay(rows, split, limit=limit),
        "cannibalisation": cannibalisation(rows, split, limit=limit),
        "trends": trends(rows, split, limit=limit),
        "notes": [
            "Zeitfenster gleich lang, jedoch nicht saisonbereinigt. Ursachen sind Hypothesen.",
            "GSC liefert nur einen Teil aller Queries; Query-URL-Metriken können gegenüber Query-Metriken abweichen.",
            "URL-Wechsel und mehrere Landingpages sind kein Beweis einer schädlichen Kannibalisierung.",
            "GSC-Query-URL-Paare werden nach Datenquelle getrennt, API hat Vorrang vor CSV.",
        ] + (["Wegen 50.000 Zeilenlimit gekürzt; Interpretationen können verzerrt sein."] if clipped else [])
          + (["Zusätzliche CSV-Daten nicht doppelt addiert."] if source == "api" and "csv" in available else []),
    }
