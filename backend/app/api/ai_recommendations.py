"""Reproducible prompt samples with strict provenance and optional Matomo referral evidence.

A configured chat model is not an AI search engine. Model samples are labelled
as model responses, with no citation, live-web-search or ranking claims.
"""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..integrations import ai
from ..integrations import matomo as mt
from ..models import AiPromptSample, AiPromptTest, User, utcnow
from ..security.auth import current_user, get_site_for
from ..services.settings_store import get_setting

router = APIRouter(tags=["ai-recommendations"])

KNOWN_AI_REFERRERS = (
    "chatgpt.com", "chat.openai.com", "perplexity.ai", "claude.ai",
    "gemini.google.com", "copilot.microsoft.com", "poe.com",
)


class PromptTestIn(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    brand_terms: list[str] = Field(min_length=1, max_length=12)
    competitor_terms: list[str] = Field(default_factory=list, max_length=12)


class SampleIn(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    model_name: str | None = Field(None, max_length=120)
    answer: str = Field(min_length=1, max_length=20000)
    observed_at: datetime | None = None


def _test(db: Session, site_id: int, test_id: int) -> AiPromptTest:
    test = db.scalar(select(AiPromptTest).where(AiPromptTest.id == test_id, AiPromptTest.site_id == site_id))
    if test is None:
        raise HTTPException(404, "Prompt test not found")
    return test


def _term_present(text: str, term: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).casefold()
    target = re.sub(r"\s+", " ", term).casefold().strip()
    if not target:
        return False
    return re.search(r"(?<!\w)" + re.escape(target) + r"(?!\w)", normalized) is not None


def _out(t: AiPromptTest, samples: list[AiPromptSample]) -> dict:
    return {
        "id": t.id, "prompt": t.prompt, "brand_terms": t.brand_terms,
        "competitor_terms": t.competitor_terms, "samples": [
            {"id": s.id, "source": s.source, "provider": s.provider, "model_name": s.model_name,
             "answer": s.answer, "observed_at": s.observed_at.isoformat(),
             "brand_matches": [term for term in t.brand_terms if _term_present(s.answer, term)],
             "competitor_matches": [term for term in t.competitor_terms if _term_present(s.answer, term)],
             "verified_search": False,
             "method": "Literal text mentions in a single answer; no ranking or recommendation verification."}
            for s in samples
        ], "source_warning": "Manually submitted answers and sandbox-model replies are not verifiable live AI-search results.",
    }


@router.post("/sites/{site_id}/ai-prompt-tests", status_code=201)
def create_test(site_id: int, body: PromptTestIn, user: User = Depends(current_user),
                db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    for term in [*body.brand_terms, *body.competitor_terms]:
        if len(term.strip()) < 2 or len(term) > 120:
            raise HTTPException(422, "Terms must be 2 to 120 characters")
    obj = AiPromptTest(site_id=site.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _out(obj, [])


@router.get("/sites/{site_id}/ai-prompt-tests")
def list_tests(site_id: int, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    tests = db.scalars(select(AiPromptTest).where(AiPromptTest.site_id == site.id)
                       .order_by(AiPromptTest.id.desc()).limit(100)).all()
    out = []
    for test in tests:
        samples = db.scalars(select(AiPromptSample).where(AiPromptSample.test_id == test.id)
                             .order_by(AiPromptSample.observed_at, AiPromptSample.id).limit(100)).all()
        out.append(_out(test, samples))
    return {"items": out, "method": "Repeated prompt observations; sample sizes and provider names are visible. No automated search platform rankings."}


@router.post("/sites/{site_id}/ai-prompt-tests/{test_id}/samples", status_code=201)
def add_sample(site_id: int, test_id: int, body: SampleIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    test = _test(db, site.id, test_id)
    when = body.observed_at.replace(tzinfo=None) if body.observed_at else utcnow()
    if when > utcnow():
        raise HTTPException(422, "Future sampling time not allowed")
    obj = AiPromptSample(test_id=test.id, source="manual", provider=body.provider,
                         model_name=body.model_name, answer=body.answer, observed_at=when)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _out(test, [obj])["samples"][0]


@router.post("/sites/{site_id}/ai-prompt-tests/{test_id}/run", status_code=201)
async def run_sample(site_id: int, test_id: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    test = _test(db, site.id, test_id)
    settings = get_setting(db, "ai")
    if settings.get("provider") not in ("ollama", "openai_compatible"):
        raise HTTPException(422, "A chat model is not configured")
    try:
        answer = await ai.complete(
            settings, test.prompt,
            system="Answer the user's prompt concisely. Do not claim access to live search unless actually available. "
                   "Do not fabricate citations. You are completing a test prompt, not browsing the web.",
        )
    except ai.AIError as exc:
        raise HTTPException(502, "Configured chat model did not return a usable response") from exc
    if not answer:
        raise HTTPException(502, "Empty chat response")
    obj = AiPromptSample(test_id=test.id, source="configured_chat_model_non_search",
                         provider=settings["provider"], model_name=str(settings.get("model") or "")[:120],
                         answer=answer[:20000], observed_at=utcnow())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _out(test, [obj])["samples"][0]


@router.delete("/sites/{site_id}/ai-prompt-tests/{test_id}", status_code=204)
def delete_test(site_id: int, test_id: int, user: User = Depends(current_user),
                db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    test = _test(db, site.id, test_id)
    db.delete(test)
    db.commit()


def _referral_host(label: str) -> str | None:
    label = label.strip().lower()
    if "://" not in label:
        label = "https://" + label
    try:
        return (urlsplit(label).hostname or "").removeprefix("www.")
    except ValueError:
        return None


def _number(value) -> float | None:
    try:
        return float(str(value).strip().replace(",", ".")) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_referrals(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows[:1000]:
        host = _referral_host(str(row.get("label") or ""))
        if host not in KNOWN_AI_REFERRERS:
            continue
        visits = _number(row.get("nb_visits"))
        conversions = _number(row.get("nb_conversions"))
        results.append({"host": host, "visits": visits, "recorded_conversions": conversions,
                        "conversion_source": "matomo_referrer_report" if conversions is not None else None,
                        "source": "matomo_referrers_websites"})
    return results


@router.get("/sites/{site_id}/ai-referrals")
async def ai_referrals(site_id: int, days: int = Query(30, ge=1, le=180),
                       id_site: int | None = Query(None, ge=1),
                       user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    settings = get_setting(db, "matomo")
    try:
        # Never silently use an unrelated Matomo site ID: match to registered site domain.
        matomo_sites = await mt.sites(settings)
        matching = mt.match_site(matomo_sites, site.url)
        if matching is None or (id_site is not None and id_site != matching):
            raise HTTPException(400, "Matomo site must have the same registered domain")
        rows = await mt.call(settings, "Referrers.getWebsites", idSite=matching,
                             period="range", date=f"last{days}", filter_limit=1000)
    except mt.MatomoError as exc:
        raise HTTPException(400, "Matomo integration unavailable") from exc
    if not isinstance(rows, list):
        raise HTTPException(502, "Unexpected Matomo referral data")
    data = _extract_referrals(rows)
    return {"id_site": matching, "days": days, "referrals": data,
            "known_host_filter": list(KNOWN_AI_REFERRERS),
            "method": "Matomo website referrers. Only recognized referral domains, no dark traffic or direct visits. "
                      "Conversions shown only when returned by Matomo for that referrer; no lead-to-sale attribution.",
            "no_causal_claim": True}
