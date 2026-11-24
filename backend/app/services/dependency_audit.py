"""Deterministic Klumpenrisiko (Dependency & Concentration) Audit.

Calculates:
1. Landingpage concentration: Top-1, Top-3, Top-5, Top-10 URL traffic share, Pareto ratio.
2. Brand vs. Non-Brand dependency: Share of traffic from branded queries vs. generic keywords.
3. Keyword concentration: Dependency on individual top queries.
4. Channel resilience: Reliance on a single search engine (Google vs. Bing).

All metrics are 100% mathematically derived from real GSC and Bing data. No made-up scores.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import GscRow, SeoResearchRecord, Site

GENERIC_INDUSTRY_WORDS = {
    "gmbh", "ag", "ug", "ltd", "inc", "und", "der", "die", "das", "von", "vom", "fuer", "für",
    "kueche", "küche", "kuechen", "küchen", "shop", "online", "store", "agentur", "beratung",
    "service", "consulting", "team", "studio", "atelier", "werkstatt", "office", "gbr", "partner",
}


def _extract_default_brand_tokens(site: Site) -> list[str]:
    tokens = set()
    if site.name:
        for part in site.name.casefold().replace("-", " ").replace(".", " ").split():
            cleaned = part.strip()
            if len(cleaned) >= 3 and cleaned not in GENERIC_INDUSTRY_WORDS:
                tokens.add(cleaned)

    if site.url:
        host = (urlsplit(site.url).hostname or "").casefold().removeprefix("www.")
        domain_name = host.split(".")[0]
        if len(domain_name) >= 3 and domain_name not in GENERIC_INDUSTRY_WORDS:
            tokens.add(domain_name)

    return sorted(tokens)


def _is_brand_query(query: str, brand_tokens: list[str]) -> bool:
    if not brand_tokens:
        return False
    # Check whole word match or clean token presence
    words = set(query.casefold().replace("-", " ").replace(".", " ").split())
    for t in brand_tokens:
        if t in words:
            return True
        if len(t) >= 4 and t in query:
            return True
    return False



def audit_dependencies(
    db: Session,
    site: Site,
    days: int = 28,
    custom_brand_term: str | None = None,
) -> dict[str, Any]:
    """Calculates landingpage, brand, and keyword concentration from dated GSC rows."""
    base_criteria = [
        GscRow.site_id == site.id,
        GscRow.dataset == "query_page",
        GscRow.day.is_not(None),
        GscRow.impressions > 0,
    ]

    sources = {r[0] for r in db.execute(select(GscRow.source).where(*base_criteria).distinct())}
    if not sources:
        return {
            "has_data": False,
            "reason": "Keine datierten GSC-Query-URL-Paare vorhanden.",
        }

    source = "api" if "api" in sources else "csv"
    criteria = [*base_criteria, GscRow.source == source]

    end_day = db.scalar(select(func.max(GscRow.day)).where(*criteria))
    if not end_day:
        return {"has_data": False, "reason": "Keine datierten GSC-Zeilen gefunden."}

    start_day = end_day - timedelta(days=days - 1)

    fetched = list(
        db.scalars(
            select(GscRow)
            .where(*criteria, GscRow.day.between(start_day, end_day))
            .limit(50000)
        )
    )

    if not fetched:
        return {
            "has_data": False,
            "reason": f"Keine GSC-Daten im gewählten Zeitraum ({start_day} bis {end_day}).",
        }

    # Brand tokens
    brand_tokens = [custom_brand_term.casefold().strip()] if custom_brand_term else _extract_default_brand_tokens(site)

    # 1. Page aggregations
    page_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0})
    query_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0})

    brand_clicks = 0.0
    brand_impressions = 0.0
    non_brand_clicks = 0.0
    non_brand_impressions = 0.0

    total_clicks = 0.0
    total_impressions = 0.0

    for r in fetched:
        c = float(r.clicks or 0)
        imp = float(r.impressions or 0)
        total_clicks += c
        total_impressions += imp

        if r.page:
            page_stats[r.page]["clicks"] += c
            page_stats[r.page]["impressions"] += imp

        if r.query:
            q_clean = " ".join(r.query.casefold().split())
            query_stats[q_clean]["clicks"] += c
            query_stats[q_clean]["impressions"] += imp

            is_brand = _is_brand_query(q_clean, brand_tokens)
            if is_brand:
                brand_clicks += c
                brand_impressions += imp
            else:
                non_brand_clicks += c
                non_brand_impressions += imp

    # Sort pages by clicks
    sorted_pages = sorted(page_stats.items(), key=lambda x: (-x[1]["clicks"], -x[1]["impressions"], x[0]))
    total_pages = len(sorted_pages)

    top_1_clicks = sum(p[1]["clicks"] for p in sorted_pages[:1])
    top_3_clicks = sum(p[1]["clicks"] for p in sorted_pages[:3])
    top_5_clicks = sum(p[1]["clicks"] for p in sorted_pages[:5])
    top_10_clicks = sum(p[1]["clicks"] for p in sorted_pages[:10])

    top_1_share = round(top_1_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    top_3_share = round(top_3_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    top_5_share = round(top_5_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    top_10_share = round(top_10_clicks / total_clicks, 3) if total_clicks > 0 else 0.0

    # Pareto: How many pages generate 80% of clicks?
    pareto_pages_count = 0
    running_clicks = 0.0
    eighty_pct_target = 0.8 * total_clicks
    for _, stats in sorted_pages:
        running_clicks += stats["clicks"]
        pareto_pages_count += 1
        if running_clicks >= eighty_pct_target:
            break

    pareto_ratio = round(pareto_pages_count / total_pages, 3) if total_pages > 0 else 0.0

    # Risk level for landingpages
    if top_3_share >= 0.65 or top_1_share >= 0.45:
        page_risk_level = "kritisch"
        page_risk_text = f"Hohes Klumpenrisiko: {round(top_3_share * 100)} % aller Klicks hängen an nur 3 URLs."
    elif top_3_share >= 0.45:
        page_risk_level = "moderat"
        page_risk_text = f"Moderates Klumpenrisiko: Top-3 URLs erzielen {round(top_3_share * 100)} % der Klicks."
    else:
        page_risk_level = "ausgewogen"
        page_risk_text = f"Gesunde Traffic-Verteilung: Top-3 URLs erzielen {round(top_3_share * 100)} % der Klicks."

    # Top pages detail table
    top_pages_table = []
    for url, stats in sorted_pages[:10]:
        c = stats["clicks"]
        share = round(c / total_clicks, 3) if total_clicks > 0 else 0.0
        top_pages_table.append({
            "url": url,
            "clicks": round(c),
            "impressions": round(stats["impressions"]),
            "click_share": share,
            "single_point_of_failure": share >= 0.25,
        })

    # 2. Sort queries by clicks
    sorted_queries = sorted(query_stats.items(), key=lambda x: (-x[1]["clicks"], -x[1]["impressions"], x[0]))
    total_queries = len(sorted_queries)

    top_1_q_clicks = sum(q[1]["clicks"] for q in sorted_queries[:1])
    top_3_q_clicks = sum(q[1]["clicks"] for q in sorted_queries[:3])
    top_1_q_share = round(top_1_q_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    top_3_q_share = round(top_3_q_clicks / total_clicks, 3) if total_clicks > 0 else 0.0

    # Brand vs. Non-Brand
    brand_share = round(brand_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    non_brand_share = round(non_brand_clicks / total_clicks, 3) if total_clicks > 0 else 0.0

    if brand_share >= 0.70:
        brand_risk_level = "hohe_markenabhaengigkeit"
        brand_risk_text = (
            f"{round(brand_share * 100)} % der Klicks stammen aus Markensuchen. "
            "Geringe unbezahlte Neukundengewinnung über generische Fachbegriffe."
        )
    elif brand_share <= 0.15:
        brand_risk_level = "geringe_markenbindung"
        brand_risk_text = (
            f"Nur {round(brand_share * 100)} % Markensuchen. Hohe Abhängigkeit von "
            "hart umkämpften generischen Rankings."
        )
    else:
        brand_risk_level = "ausgewogen"
        brand_risk_text = f"Gesunder Mix: {round(brand_share * 100)} % Brand, {round(non_brand_share * 100)} % Non-Brand."

    # Top queries table
    top_queries_table = []
    for q, stats in sorted_queries[:10]:
        c = stats["clicks"]
        is_b = _is_brand_query(q, brand_tokens)
        top_queries_table.append({
            "query": q,
            "clicks": round(c),
            "impressions": round(stats["impressions"]),
            "click_share": round(c / total_clicks, 3) if total_clicks > 0 else 0.0,
            "is_brand": is_b,
        })

    # 3. Channel distribution: Google vs. Bing
    bing_records_count = db.scalar(
        select(func.count())
        .select_from(SeoResearchRecord)
        .where(SeoResearchRecord.site_id == site.id, SeoResearchRecord.kind == "bing_query_stats")
    ) or 0

    return {
        "has_data": True,
        "site_id": site.id,
        "site_name": site.name,
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
        "days_evaluated": days,
        "gsc_source": source,
        "total_clicks": round(total_clicks),
        "total_impressions": round(total_impressions),
        "landingpage_concentration": {
            "total_landing_pages": total_pages,
            "top_1_share": top_1_share,
            "top_3_share": top_3_share,
            "top_5_share": top_5_share,
            "top_10_share": top_10_share,
            "pareto": {
                "pages_for_80_pct_clicks": pareto_pages_count,
                "percentage_of_all_pages": round(pareto_ratio * 100, 1),
                "summary": f"{pareto_pages_count} von {total_pages} URLs ({round(pareto_ratio * 100, 1)} %) erzielen 80 % aller Klicks.",
            },
            "risk_level": page_risk_level,
            "risk_assessment": page_risk_text,
            "top_pages": top_pages_table,
        },
        "search_term_concentration": {
            "total_queries": total_queries,
            "top_1_query_share": top_1_q_share,
            "top_3_query_share": top_3_q_share,
            "brand_tokens_used": brand_tokens,
            "brand_clicks": round(brand_clicks),
            "brand_share": brand_share,
            "non_brand_clicks": round(non_brand_clicks),
            "non_brand_share": non_brand_share,
            "brand_risk_level": brand_risk_level,
            "brand_risk_assessment": brand_risk_text,
            "top_queries": top_queries_table,
        },
        "channel_resilience": {
            "google_gsc_active": True,
            "bing_webmaster_active": bing_records_count > 0,
            "channel_assessment": (
                "Bing Webmaster Tools ist verknüpft; Daten werden im Bing-Modul erfasst."
                if bing_records_count > 0
                else "Ausschließlich Google Search Console angebunden. 100 % Suchmaschinen-Abhängigkeit von Google."
            ),
        },
        "method": "Deterministische Pareto- und Konzentrationsanalyse auf tatsächlichen GSC-Suchanfrage-URL-Paaren. Keine geschätzten Werte.",
    }
