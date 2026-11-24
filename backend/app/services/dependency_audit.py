"""Deterministic Klumpenrisiko (Dependency & Concentration) Audit.

Calculates:
1. Landingpage concentration: Top-1, Top-3, Top-5, Top-10 URL traffic share, Pareto ratio.
2. Brand vs. Non-Brand dependency: Share of traffic from branded queries vs. generic keywords.
3. Keyword concentration: Dependency on individual top queries.
4. Channel resilience: Reliance on a single search engine (Google vs. Bing Webmaster Tools).

Supports Google Search Console and Bing Webmaster Tools as equal search intelligence sources.
All metrics are 100% mathematically derived from real GSC and Bing data. No made-up scores.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Literal
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GscRow, Site
from .bing_content import get_bing_observations

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
    words = set(query.casefold().replace("-", " ").replace(".", " ").split())
    for t in brand_tokens:
        if t in words:
            return True
        if len(t) >= 4 and t in query:
            return True
    return False


def _recent_totals(rows: list[dict], days: int) -> tuple[int, int]:
    dated = [row for row in rows if isinstance(row.get("day"), date)]
    if not dated:
        return 0, 0
    end = max(row["day"] for row in dated)
    start = end - timedelta(days=days - 1)
    sample = [row for row in dated if start <= row["day"] <= end]
    return (round(sum(float(row.get("clicks") or 0) for row in sample)),
            round(sum(float(row.get("impressions") or 0) for row in sample)))


def _compute_concentration_from_rows(
    rows: list[dict],
    brand_tokens: list[str],
    site: Site,
    days: int,
    provider_name: str,
    channel_info: dict[str, Any],
) -> dict[str, Any]:
    dated_rows = [r for r in rows if isinstance(r.get("day"), date)]
    if not dated_rows:
        return {
            "has_data": False,
            "provider": provider_name,
            "reason": f"Keine {provider_name}-Zeilen im gewählten Zeitraum gefunden.",
            "channel_resilience": channel_info,
        }

    end_day = max(r["day"] for r in dated_rows)
    start_day = end_day - timedelta(days=days - 1)
    sample_rows = [r for r in dated_rows if start_day <= r["day"] <= end_day]

    if not sample_rows:
        return {
            "has_data": False,
            "provider": provider_name,
            "reason": f"Keine {provider_name}-Daten zwischen {start_day} und {end_day}.",
            "channel_resilience": channel_info,
        }

    page_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0})
    query_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0})

    brand_clicks = 0.0
    brand_impressions = 0.0
    non_brand_clicks = 0.0
    non_brand_impressions = 0.0

    total_clicks = 0.0
    total_impressions = 0.0

    for r in sample_rows:
        c = float(r.get("clicks") or 0)
        imp = float(r.get("impressions") or 0)
        total_clicks += c
        total_impressions += imp

        page_val = r.get("page")
        if page_val:
            page_stats[page_val]["clicks"] += c
            page_stats[page_val]["impressions"] += imp

        q_val = r.get("query")
        if q_val:
            q_clean = " ".join(q_val.casefold().split())
            query_stats[q_clean]["clicks"] += c
            query_stats[q_clean]["impressions"] += imp

            is_brand = _is_brand_query(q_clean, brand_tokens)
            if is_brand:
                brand_clicks += c
                brand_impressions += imp
            else:
                non_brand_clicks += c
                non_brand_impressions += imp

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

    pareto_pages_count = 0
    running_clicks = 0.0
    eighty_pct_target = 0.8 * total_clicks
    for _, stats in sorted_pages:
        running_clicks += stats["clicks"]
        pareto_pages_count += 1
        if running_clicks >= eighty_pct_target:
            break

    pareto_ratio = round(pareto_pages_count / total_pages, 3) if total_pages > 0 else 0.0

    if top_3_share >= 0.65 or top_1_share >= 0.45:
        page_risk_level = "kritisch"
        page_risk_text = f"Hohes Klumpenrisiko ({provider_name}): {round(top_3_share * 100)} % aller Klicks hängen an nur 3 URLs."
    elif top_3_share >= 0.45:
        page_risk_level = "moderat"
        page_risk_text = f"Moderates Klumpenrisiko ({provider_name}): Top-3 URLs erzielen {round(top_3_share * 100)} % der Klicks."
    else:
        page_risk_level = "ausgewogen"
        page_risk_text = f"Gesunde Traffic-Verteilung ({provider_name}): Top-3 URLs erzielen {round(top_3_share * 100)} % der Klicks."

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

    sorted_queries = sorted(query_stats.items(), key=lambda x: (-x[1]["clicks"], -x[1]["impressions"], x[0]))
    total_queries = len(sorted_queries)

    top_1_q_clicks = sum(q[1]["clicks"] for q in sorted_queries[:1])
    top_3_q_clicks = sum(q[1]["clicks"] for q in sorted_queries[:3])
    top_1_q_share = round(top_1_q_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    top_3_q_share = round(top_3_q_clicks / total_clicks, 3) if total_clicks > 0 else 0.0

    brand_share = round(brand_clicks / total_clicks, 3) if total_clicks > 0 else 0.0
    non_brand_share = round(non_brand_clicks / total_clicks, 3) if total_clicks > 0 else 0.0

    if brand_share >= 0.70:
        brand_risk_level = "hohe_markenabhaengigkeit"
        brand_risk_text = (
            f"{round(brand_share * 100)} % der {provider_name}-Klicks stammen aus Markensuchen. "
            "Geringe unbezahlte Neukundengewinnung über generische Fachbegriffe."
        )
    elif brand_share <= 0.15:
        brand_risk_level = "geringe_markenbindung"
        brand_risk_text = (
            f"Nur {round(brand_share * 100)} % Markensuchen auf {provider_name}. "
            "Hohe Abhängigkeit von hart umkämpften generischen Rankings."
        )
    else:
        brand_risk_level = "ausgewogen"
        brand_risk_text = f"Gesunder Mix: {round(brand_share * 100)} % Brand, {round(non_brand_share * 100)} % Non-Brand."

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

    return {
        "has_data": True,
        "provider": provider_name,
        "site_id": site.id,
        "site_name": site.name,
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
        "days_evaluated": days,
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
        "channel_resilience": channel_info,
        "method": f"Deterministische Pareto- und Konzentrationsanalyse auf tatsächlichen {provider_name}-Daten. Keine geschätzten Werte.",
    }


def audit_dependencies(
    db: Session,
    site: Site,
    days: int = 28,
    custom_brand_term: str | None = None,
    provider: Literal["google", "bing"] = "google",
) -> dict[str, Any]:
    """Calculates landingpage, brand, and keyword concentration from Google and Bing Webmaster data."""
    brand_tokens = [custom_brand_term.casefold().strip()] if custom_brand_term else _extract_default_brand_tokens(site)

    # 1. Load Google Search Console rows
    base_criteria = [
        GscRow.site_id == site.id,
        GscRow.dataset == "query_page",
        GscRow.day.is_not(None),
        GscRow.impressions > 0,
    ]
    sources = {r[0] for r in db.execute(select(GscRow.source).where(*base_criteria).distinct())}
    google_source = "api" if "api" in sources else "csv" if sources else None
    google_rows = []
    google_clicks = 0
    google_impressions = 0

    if google_source:
        criteria = [*base_criteria, GscRow.source == google_source]
        g_fetched = list(db.scalars(select(GscRow).where(*criteria).limit(50000)))
        google_rows = [
            {"day": r.day, "query": r.query, "page": r.page, "clicks": r.clicks, "impressions": r.impressions, "position": r.position}
            for r in g_fetched
        ]
        google_clicks, google_impressions = _recent_totals(google_rows, days)

    # 2. Load Bing observations & traffic totals
    # Concentration requires paired query/page facts. Site-wide traffic snapshots
    # are used for channel shares only and must not be added to these rows.
    bing_observations = get_bing_observations(db, site.id)
    bing_rows = [row for row in bing_observations
                 if row.get("query") and row.get("page")]
    bing_traffic_rows = [row for row in bing_observations if row.get("provider_operation") == "traffic"]
    bing_clicks, bing_impressions = _recent_totals(bing_traffic_rows or bing_rows, days)

    # 3. Channel resilience comparison
    total_combined_clicks = google_clicks + bing_clicks
    google_share = round(google_clicks / total_combined_clicks, 3) if total_combined_clicks > 0 else (1.0 if google_clicks > 0 else 0.0)
    bing_share = round(bing_clicks / total_combined_clicks, 3) if total_combined_clicks > 0 else (1.0 if bing_clicks > 0 else 0.0)

    if bing_clicks > 0 and google_clicks > 0:
        channel_assessment = (
            f"Google Search Console: {round(google_share * 100, 1)} % ({google_clicks} Klicks) · "
            f"Bing Webmaster Tools: {round(bing_share * 100, 1)} % ({bing_clicks} Klicks). "
            "Beide Suchmaschinen liefern aktive organische Klicks."
        )
    elif bing_clicks > 0 and google_clicks == 0:
        channel_assessment = f"Aktuell ausschließlich Bing Webmaster Tools Daten vorhanden ({bing_clicks} Klicks)."
    elif google_clicks > 0 and bing_clicks == 0:
        channel_assessment = (
            f"Ausschließlich Google Search Console Daten vorhanden ({google_clicks} Klicks, 100 % Google-Abhängigkeit). "
            "Bing Webmaster Tools im Bing-Modul anbinden, um Suchmaschinen-Diversifizierung zu messen."
        )
    else:
        channel_assessment = "Weder Google Search Console noch Bing Webmaster Daten vorhanden."

    channel_info = {
        "google": {
            "active": google_clicks > 0,
            "clicks": google_clicks,
            "impressions": google_impressions,
            "click_share": google_share,
            "source": google_source,
        },
        "bing": {
            "active": bing_clicks > 0 or bool(bing_rows),
            "clicks": bing_clicks,
            "impressions": bing_impressions,
            "click_share": bing_share,
        },
        "total_clicks": total_combined_clicks,
        "window_note": f"Je Anbieter die neuesten {days} Tage; Zeiträume können wegen unterschiedlicher Aktualität abweichen.",
        "channel_assessment": channel_assessment,
    }

    # Evaluate according to provider selection
    if provider == "bing":
        if not bing_rows:
            return {
                "has_data": False,
                "provider": "Bing Webmaster Tools",
                "reason": "Keine Bing-Webmaster-Snapshots oder Query-Daten für diese Website vorhanden.",
                "channel_resilience": channel_info,
            }
        return _compute_concentration_from_rows(
            bing_rows, brand_tokens, site, days, "Bing Webmaster Tools", channel_info
        )

    # Google remains the backwards-compatible default; the UI makes the source explicit.
    if google_rows:
        return _compute_concentration_from_rows(
            google_rows, brand_tokens, site, days, "Google Search Console", channel_info
        )

    return {
        "has_data": False,
        "provider": "Google Search Console",
        "reason": "Keine datierten Google-Search-Console-Suchanfrage-URL-Daten vorhanden.",
        "channel_resilience": channel_info,
    }
