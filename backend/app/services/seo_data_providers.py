"""Source-aware SEO data adapters.

No invented metrics and no privileged dynamic plug-in imports. The registry is
explicit, with a consistent read-only output shape for additional providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Backlink, GscRow, Keyword


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    kind: str
    origin: str
    unit: str
    scope: str
    notes: str

    def as_dict(self) -> dict:
        return vars(self)


class Provider(Protocol):
    info: ProviderInfo

    def rows(self, db: Session, site_id: int, limit: int, days: int) -> dict: ...


class ImportedKeywordProvider:
    info = ProviderInfo(
        "keyword_import", "keyword_metrics", "imported_file", "searches_per_month",
        "imported_keywords_only", "Search volume and bids originate in a user-supplied CSV; no independent validation.",
    )

    def rows(self, db: Session, site_id: int, limit: int, days: int) -> dict:
        records = db.scalars(select(Keyword).where(Keyword.site_id == site_id)
                             .order_by(Keyword.keyword).limit(limit + 1)).all()
        result = []
        for kw in records[:limit]:
            imported = (kw.metrics or {}).get("imported") or {}
            if not imported:
                continue
            result.append({
                "keyword": kw.keyword,
                "volume": imported.get("search_volume"),
                "cpc_low": imported.get("cpc_low"),
                "cpc_high": imported.get("cpc_high"),
                "competition": imported.get("competition"),
                "source_file": imported.get("file"),
                "measured_for_site": False,
                "position": None,
            })
        return {"items": result, "truncated": len(records) > limit}


class GscKeywordProvider:
    info = ProviderInfo(
        "gsc", "keyword_performance", "google_search_console", "clicks_and_impressions",
        "verified_site_only", "GSC impressions are not total monthly search volume. Positions are impression-weighted averages.",
    )

    def rows(self, db: Session, site_id: int, limit: int, days: int) -> dict:
        paired = [GscRow.site_id == site_id, GscRow.dataset == "query_page",
                  GscRow.query.is_not(None), GscRow.page.is_not(None),
                  GscRow.impressions > 0, GscRow.day.is_not(None)]
        sources = {row[0] for row in db.execute(select(GscRow.source).where(*paired).distinct())}
        source = "api" if "api" in sources else "csv" if "csv" in sources else None
        if source is None:
            return {"items": [], "truncated": False, "record_source": None, "period": None}
        criteria = [*paired, GscRow.source == source]
        last = db.scalar(select(func.max(GscRow.day)).where(*criteria))
        first = last - timedelta(days=days - 1)
        criteria.append(GscRow.day.between(first, last))
        num = func.sum(case((GscRow.position.is_not(None), GscRow.position * GscRow.impressions), else_=0))
        den = func.sum(case((GscRow.position.is_not(None), GscRow.impressions), else_=0))
        result = db.execute(
            select(GscRow.query, func.sum(GscRow.clicks), func.sum(GscRow.impressions), num, den)
            .where(*criteria).group_by(GscRow.query)
            .order_by(func.sum(GscRow.impressions).desc()).limit(limit + 1)
        ).all()
        return {"items": [{
            "keyword": q, "clicks": round(float(clicks or 0), 2),
            "impressions": round(float(imp), 2),
            "average_position": round(float(numerator / denominator), 2) if denominator else None,
            "search_volume": None,
            "measured_for_site": True,
        } for q, clicks, imp, numerator, denominator in result[:limit]],
                "truncated": len(result) > limit, "record_source": source,
                "period": {"start": first.isoformat(), "end": last.isoformat()}}


class ImportedBacklinkProvider:
    info = ProviderInfo(
        "backlink_records", "backlink", "import_or_local_verification", "links",
        "known_links_only", "Records do not indicate web-scale backlink discovery or third-party authority scores.",
    )

    def rows(self, db: Session, site_id: int, limit: int, days: int) -> dict:
        records = db.scalars(select(Backlink).where(Backlink.site_id == site_id)
                             .order_by(Backlink.id.desc()).limit(limit + 1)).all()
        return {"items": [{
            "source_url": b.source_url, "target_url": b.target_url, "anchor": b.anchor,
            "nofollow": b.nofollow, "verification_status": b.status, "origin": b.origin,
            "last_checked": b.last_checked.isoformat() if b.last_checked else None,
        } for b in records[:limit]], "truncated": len(records) > limit}


PROVIDERS: dict[str, Provider] = {
    p.info.id: p for p in (ImportedKeywordProvider(), GscKeywordProvider(), ImportedBacklinkProvider())
}


def provider_catalogue() -> list[dict]:
    return [p.info.as_dict() for p in PROVIDERS.values()]


def provider_data(db: Session, site_id: int, source: str, limit: int = 100, days: int = 28) -> dict:
    if source not in PROVIDERS:
        raise ValueError("Unknown SEO data provider")
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("Limit must be 1..200")
    if type(days) is not int or not 7 <= days <= 180:
        raise ValueError("Days must be 7..180")
    provider = PROVIDERS[source]
    return {"provider": provider.info.as_dict(),
            "data": provider.rows(db, site_id, limit, days),
            "provenance": "Existing site-scoped database records; never generated rankings or search-volume estimates"}
