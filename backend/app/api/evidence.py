"""Evidence-backed local SEO checklist and publication reconciliation.

No Google Business Profile access, automatic review gating, or claimed ranking signals.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Backlink, Citation, SeoWorkItem, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["seo-evidence"])


def _norm(value: str | None, kind: str) -> str:
    s = " ".join((value or "").casefold().split())
    if kind == "phone":
        return re.sub(r"[^0-9+]", "", s)
    return s


def local_summary(citations: list[Citation]) -> dict:
    if not citations:
        return {"count": 0, "missing": {}, "inconsistent": [], "duplicates": 0}
    missing = {field: sum(not getattr(c, field) for c in citations) for field in ("name", "address", "phone", "url")}
    inconsistent = [field for field in ("name", "address", "phone")
                    if len({_norm(getattr(c, field), field) for c in citations if getattr(c, field)}) > 1]
    sources = [c.source.casefold().strip() for c in citations]
    return {"count": len(citations), "missing": missing, "inconsistent": inconsistent,
            "duplicates": len(sources) - len(set(sources))}


@router.get("/sites/{site_id}/local-action-plan")
def local_action_plan(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    citations = db.scalars(select(Citation).where(Citation.site_id == site.id).limit(5000)).all()
    summary = local_summary(citations)
    actions = []
    if not citations:
        actions.append({"priority": "high", "title": "Branchenverzeichnisse erst erfassen",
                        "basis": "Keine importierten Citation-Datensätze vorhanden", "type": "data_gap"})
    else:
        if summary["inconsistent"]:
            actions.append({"priority": "high", "title": "Abweichende Geschäftsangaben manuell abgleichen",
                            "basis": "Unterschiedliche Angaben in: " + ", ".join(summary["inconsistent"]),
                            "type": "inconsistency"})
        total_missing = sum(summary["missing"].values())
        if total_missing:
            actions.append({"priority": "medium", "title": "Unvollständige Branchenprofile kontrollieren",
                            "basis": str(total_missing) + " leere Felder in importierten Einträgen", "type": "missing"})
        if summary["duplicates"]:
            actions.append({"priority": "medium", "title": "Mehrfache Quellen-Einträge prüfen",
                            "basis": str(summary["duplicates"]) + " wiederholte Quellennamen (können legitime Standorte sein)",
                            "type": "duplicate"})
    actions.extend([
        {"priority": "manual", "title": "Google Business Profile mit realem Standort/Einzugsgebiet prüfen",
         "basis": "Keine verbundene Google-Business-Profile-API – keine automatische Behauptung zur Profilqualität",
         "type": "manual_check"},
        {"priority": "manual", "title": "Authentische Kundenbewertungen ohne Review-Gating anfragen",
         "basis": "Alle Kunden gleichermaßen um ehrliches Feedback bitten; keine Anreize oder selektive Weiterleitung",
         "type": "manual_check"},
    ])
    reviews = db.scalars(select(SeoWorkItem).where(
        SeoWorkItem.site_id == site.id, SeoWorkItem.kind == "review").limit(1000)).all()
    states = Counter(r.status for r in reviews)
    return {"citations": summary, "review_requests": {"total": len(reviews), "by_status": dict(states),
                                                       "source": "manually_tracked_work_items"},
            "actions": actions, "source": "imported_citations_and_manual_work",
            "limitations": ["Importdaten sind nicht mit Google Maps synchronisiert.",
                            "Unterschiedliche Schreibweisen sind Prüfhinweise, keine bestätigten Fehler.",
                            "Kein Zugriff auf echte Bewertungen, GBP-Kategorien oder GBP-Insights.",
                            "Es wird keine Ranking- oder Bewertungsanzahl als Mindestschwelle behauptet."]}


@router.get("/sites/{site_id}/publication-evidence")
def publication_evidence(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    items = db.scalars(select(SeoWorkItem).where(
        SeoWorkItem.site_id == site.id, SeoWorkItem.kind == "publication").order_by(SeoWorkItem.id.desc()).limit(1000)).all()
    backlinks = db.scalars(select(Backlink).where(Backlink.site_id == site.id).limit(50000)).all()
    by_source: dict[str, list[Backlink]] = defaultdict(list)
    for backlink in backlinks:
        if backlink.source_url:
            by_source[backlink.source_url.rstrip("/")].append(backlink)
    rows = []
    for item in items:
        sources = by_source.get((item.source_url or "").rstrip("/"), []) if item.source_url else []
        if item.target_url:
            sources = [b for b in sources if b.target_url and b.target_url.rstrip("/") == item.target_url.rstrip("/")]
        sources.sort(key=lambda b: (b.last_checked is not None, b.last_checked or b.first_seen), reverse=True)
        chosen = sources[0] if sources else None
        rows.append({
            "id": item.id, "title": item.title, "status": item.status, "source_url": item.source_url,
            "target_url": item.target_url, "evidence_url": item.evidence_url,
            "backlink_record": ({"status": chosen.status, "nofollow": chosen.nofollow,
                                 "last_checked": chosen.last_checked.isoformat() if chosen.last_checked else None,
                                 "origin": chosen.origin} if chosen else None),
            "interpretation": ("Ein vorhandener Backlink-Datensatz berichtet Status '" + chosen.status +
                               "'; redaktionelle Qualität oder tatsächliche Reichweite sind nicht bestätigt.")
                              if chosen else "Kein exakt passender Backlink-Datensatz – nicht gleichbedeutend mit fehlender Veröffentlichung.",
        })
    return {"items": rows, "source": "manually_tracked_publications_and_existing_backlink_records",
            "method": "Abgleich per exakter Quell-URL und optional Ziel-URL. Keine Live-Verifikation, "
                      "kein garantierter Indexierungsstatus und keine Gleichsetzung von PR-Links und redaktioneller Berichterstattung."}
