"""Editorial evidence-led content studio and marketing experiment log.

No fabricated outcomes, personal customer data, third-party crawling,
AI-generated case studies or automatic publication.
"""
from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SeoContentProposal, SeoResearchRecord, SeoWorkItem, User
from ..security.auth import current_user, get_site_for

router = APIRouter(tags=["content-studio"])


def _records(db: Session, site_id: int, kind: str) -> list[SeoResearchRecord]:
    return db.scalars(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site_id, SeoResearchRecord.kind == kind)
        .order_by(SeoResearchRecord.id.desc()).limit(1000)).all()


def _item(db: Session, site_id: int, item_id: int, kind: str) -> SeoResearchRecord:
    item = db.scalar(select(SeoResearchRecord).where(
        SeoResearchRecord.site_id == site_id, SeoResearchRecord.id == item_id,
        SeoResearchRecord.kind == kind))
    if item is None:
        raise HTTPException(404, "Research record not found")
    return item


def _numeric(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (float, int)):
        result = float(value)
    elif isinstance(value, str):
        try:
            result = float(value.strip().replace(",", "."))
        except ValueError:
            return None
    else:
        return None
    return result if -1e12 <= result <= 1e12 else None


def _case_text(record: SeoResearchRecord) -> str:
    """A mechanical formatting of actual user-provided fields, not generative copy."""
    p = record.payload
    parts = [
        "# " + record.title,
        "## Ausgangslage\n" + str(p["challenge"]),
        "## Vorgehen\n" + str(p["approach"]),
        "## Dokumentiertes Ergebnis (redaktionell prüfen)\n" + str(p["outcome"]),
        "## Projekt\n" + str(p["project"]),
    ]
    if p.get("evidence_url"):
        parts.append("## Nachweis (nicht automatisch verifiziert)\n" + str(p["evidence_url"]))
    if p.get("evidence_note"):
        parts.append("## Prüfhinweis\n" + str(p["evidence_note"]))
    return "\n\n".join(parts)


@router.get("/sites/{site_id}/content-studio")
def content_studio(site_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    cases = []
    for r in _records(db, site.id, "case_study"):
        p = r.payload
        cases.append({
            "id": r.id, "title": r.title, "target_url": p["target_url"],
            "has_evidence": bool(p.get("evidence_url")), "verified": False,
            "draft_preview": _case_text(r), "source": r.source,
        })
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in _records(db, site.id, "buyer_question"):
        p = r.payload
        audience = str(p["audience"])
        grouped[audience].append({
            "id": r.id, "question": p["question"], "context": p["context"],
            "suggested_url": p.get("suggested_url"),
            "source_note": p.get("source_note"), "fact_checked": False,
        })
    brands = []
    for r in _records(db, site.id, "brand_claim"):
        p = r.payload
        expected = str(p.get("expected_statement") or "").strip()
        claim = str(p["claim"]).strip()
        matches = bool(expected) and re.sub(r"\s+", " ", claim).casefold() == re.sub(r"\s+", " ", expected).casefold()
        brands.append({
            "id": r.id, "subject": p["subject"], "claim": claim,
            "source_url": p["source_url"], "expected_statement": expected or None,
            "lexically_matching": matches if expected else None,
            "source_verified": False, "reason": "Only literal comparison of user-entered statements.",
        })
    experiments = []
    for r in _records(db, site.id, "marketing_experiment"):
        p = r.payload
        before, after = _numeric(p.get("baseline")), _numeric(p.get("followup"))
        delta = round(after - before, 4) if before is not None and after is not None else None
        experiments.append({
            "id": r.id, "title": r.title, "hypothesis": p["hypothesis"],
            "metric": p["metric"], "unit": p["unit"], "start_date": p["start_date"],
            "end_date": p.get("end_date"), "baseline": before, "followup": after,
            "observed_difference": delta, "cost": _numeric(p.get("cost")),
            "source_note": p.get("source_note"), "source": r.source,
            "causal_effect_established": False,
        })
    return {
        "cases": cases,
        "buyer_questions": [{"audience": audience, "questions": questions} for audience, questions in sorted(grouped.items())],
        "brand_claims": brands,
        "experiments": experiments,
        "method": "User-entered source records and mechanical formatting. No fact validation, rankings, "
                  "privacy consent verification, statistically proven lift, or automatic publication.",
    }


@router.post("/sites/{site_id}/content-studio/case-studies/{record_id}/draft", status_code=201)
def create_case_draft(site_id: int, record_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    record = _item(db, site.id, record_id, "case_study")
    target = str(record.payload["target_url"]).strip()
    site_host = (urlsplit(site.url).hostname or "").lower().removeprefix("www.")
    parsed = urlsplit(target)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.hostname.lower().removeprefix("www.") != site_host:
        raise HTTPException(422, "Case study target URL must belong to the selected website")
    if parsed.username or parsed.password:
        raise HTTPException(422, "Credentials in target URL are not allowed")
    existing = db.scalar(select(SeoWorkItem.id).where(
        SeoWorkItem.site_id == site.id, SeoWorkItem.kind == "content", SeoWorkItem.target_url == target,
        SeoWorkItem.title == record.title))
    if existing:
        raise HTTPException(409, "A content work item with this title and target URL already exists")
    item = SeoWorkItem(site_id=site.id, kind="content", status="draft",
                       title=record.title, target_url=target,
                       evidence_url=str(record.payload.get("evidence_url") or "") or None,
                       notes="Created from manually supplied case-study record #" + str(record.id))
    db.add(item)
    db.flush()
    proposal = SeoContentProposal(work_item_id=item.id, original_text="", proposed_text=_case_text(record),
                                  rationale="Mechanical transcription of submitted case facts. "
                                            "Editorial verification and separate approval mandatory.",
                                  status="draft")
    db.add(proposal)
    db.commit()
    return {"work_item_id": item.id, "proposal_status": "draft",
            "remote_publication": False,
            "note": "Case draft created. It must be reviewed and separately approved before any external publication."}
