"""Advanced SEO: provider-qualified SERP overlap and crawl snapshot diagnostics."""
from __future__ import annotations

from collections import Counter
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.schema_validator import validate_jsonld
from ..db import get_db
from ..models import Crawl, Page, User
from ..security.auth import current_user, get_site_for
from ..serp import analyzer as serp
from ..services.settings_store import get_setting

router = APIRouter(tags=["advanced-seo"])


class OverlapIn(BaseModel):
    first_keyword: str = Field(min_length=2, max_length=300)
    second_keyword: str = Field(min_length=2, max_length=300)
    country: str = Field("de", pattern=r"^[a-z]{2}$")
    language: str = Field("de", pattern=r"^[a-z]{2}$")
    manual_urls_first: list[str] = Field(default_factory=list, max_length=20)
    manual_urls_second: list[str] = Field(default_factory=list, max_length=20)


def overlap(a: list[str], b: list[str]) -> dict:
    first = list(dict.fromkeys(x.strip().rstrip("/") for x in a if x.strip()))
    second = list(dict.fromkeys(x.strip().rstrip("/") for x in b if x.strip()))
    common = sorted(set(first) & set(second))
    union = set(first) | set(second)
    return {"count_a": len(first), "count_b": len(second), "common_urls": common,
            "common_count": len(common), "jaccard": round(len(common) / len(union), 3) if union else None,
            "overlap_of_smaller": round(len(common) / min(len(first), len(second)), 3) if first and second else None,
            "interpretation": "SERP overlap is a content-mapping hint, not a rule requiring one or two pages."}


@router.post("/sites/{site_id}/advanced/serp-overlap")
async def serp_overlap(site_id: int, body: OverlapIn, user: User = Depends(current_user),
                       db: Session = Depends(get_db)) -> dict:
    get_site_for(db, user, site_id)
    provided = bool(body.manual_urls_first) and bool(body.manual_urls_second)
    if bool(body.manual_urls_first) != bool(body.manual_urls_second):
        raise HTTPException(422, "Bei manuellen Listen sind beide Ergebnislisten nötig")
    if provided:
        for raw in [*body.manual_urls_first, *body.manual_urls_second]:
            parts = urlsplit(raw)
            if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
                raise HTTPException(422, "Nur vollständige http(s)-Ergebnis-URLs erlaubt")
        first = body.manual_urls_first
        second = body.manual_urls_second
        provider = "manual"
    else:
        settings = get_setting(db, "serp")
        if settings.get("provider", "none") == "none":
            raise HTTPException(422, "SERP-Anbieter konfigurieren oder zwei manuelle URL-Listen übergeben")
        try:
            results = [await serp.search(settings, kw, country=body.country, lang=body.language, num=10)
                       for kw in (body.first_keyword, body.second_keyword)]
        except serp.SerpError as exc:
            raise HTTPException(502, "SERP-Abfrage fehlgeschlagen") from exc
        first, second = ([r["url"] for r in item["results"]] for item in results)
        provider = results[0]["provider"]
    result = overlap(first, second)
    return {"first_keyword": body.first_keyword, "second_keyword": body.second_keyword,
            "country": body.country, "language": body.language, "provider": provider,
            "result": result, "method": "Exact URL intersection within two same-provider or manually supplied result lists. "
                                         "SearXNG, Brave and Programmable Search are not verified Google SERP rankings."}


class Mapping(BaseModel):
    old_url: str = Field(max_length=2048)
    new_url: str = Field(max_length=2048)


class RelaunchIn(BaseModel):
    old_crawl_id: int = Field(ge=1)
    new_crawl_id: int = Field(ge=1)
    mappings: list[Mapping] = Field(default_factory=list, max_length=300)


def _snapshot(db: Session, site_id: int, crawl_id: int) -> Crawl:
    crawl = db.scalar(select(Crawl).where(Crawl.id == crawl_id, Crawl.site_id == site_id,
                                          Crawl.competitor_id.is_(None), Crawl.status == "completed"))
    if not crawl:
        raise HTTPException(404, "Completed crawl not found for this website")
    return crawl


@router.post("/sites/{site_id}/advanced/relaunch")
def relaunch(site_id: int, body: RelaunchIn, user: User = Depends(current_user),
             db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    if body.old_crawl_id == body.new_crawl_id:
        raise HTTPException(422, "Zwei unterschiedliche Crawl-Snapshots wählen")
    old = _snapshot(db, site.id, body.old_crawl_id)
    new = _snapshot(db, site.id, body.new_crawl_id)
    if old.created_at > new.created_at:
        raise HTTPException(422, "Neuer Crawl muss zeitlich nach dem alten liegen")
    olds = db.scalars(select(Page).where(Page.crawl_id == old.id, Page.is_html.is_(True)).limit(5000)).all()
    news = db.scalars(select(Page).where(Page.crawl_id == new.id).limit(7000)).all()
    newer = {p.url.rstrip("/"): p for p in news}
    mapped = {m.old_url.rstrip("/"): m.new_url.rstrip("/") for m in body.mappings}
    rows = []
    for p in olds:
        if not p.indexable:
            continue
        old_key = p.url.rstrip("/")
        target_key = mapped.get(old_key, old_key)
        target = newer.get(target_key)
        status = "target_absent_in_new_crawl"
        if target:
            if target.redirect_to:
                status = "redirect_observed"
            elif target.status_code != 200:
                status = "non_200_target"
            elif not target.indexable:
                status = "target_not_indexable"
            elif target.canonical and target.canonical.rstrip("/") != target_key:
                status = "canonical_differs"
            elif p.title and target.title and p.title != target.title:
                status = "title_changed_review"
            else:
                status = "observed_ok"
        rows.append({"old_url": p.url, "intended_new_url": target_key, "status": status,
                     "target_http_status": target.status_code if target else None,
                     "target_canonical": target.canonical if target else None,
                     "target_indexable": target.indexable if target else None,
                     "old_title": p.title, "new_title": target.title if target else None})
    counts = dict(Counter(r["status"] for r in rows))
    return {"old_crawl_id": old.id, "new_crawl_id": new.id, "items": rows[:5000], "counts": counts,
            "method": "Comparing two stored crawls only. Absent URL is not proof a redirect is missing; "
                      "no live cross-domain checks, no automatic redirect deployment."}


def _pagination_signal(page: Page) -> bool:
    path = urlsplit(page.url).path.casefold()
    query = urlsplit(page.url).query.casefold()
    data = page.data or {}
    return bool(data.get("rel_next") or data.get("rel_prev") or
                "page=" in query or "paged=" in query or "/page/" in path)


@router.get("/sites/{site_id}/advanced/pagination")
def pagination(site_id: int, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = db.scalar(select(Crawl).where(
        Crawl.site_id == site.id, Crawl.status == "completed", Crawl.competitor_id.is_(None))
        .order_by(Crawl.id.desc()))
    if crawl is None:
        return {"crawl_id": None, "items": [], "method": "Ein Crawl fehlt"}
    pages = db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.is_html.is_(True))
                       .order_by(Page.id).limit(4000)).all()
    out = []
    for page in pages:
        if not _pagination_signal(page):
            continue
        data = page.data or {}
        hints = []
        if not page.indexable:
            hints.append("Pagination URL not technically indexable; inspect intent and discoverability")
        if page.depth is not None and page.depth >= 5:
            hints.append("Page discovered at crawl depth >= 5; review other paths")
        if page.inlinks <= 1:
            hints.append("Few incoming crawl links; check archive link paths")
        out.append({"url": page.url, "depth": page.depth, "inlinks": page.inlinks,
                    "indexable": page.indexable, "rel_next": data.get("rel_next"),
                    "rel_prev": data.get("rel_prev"), "hints": hints})
    return {"crawl_id": crawl.id, "items": out,
            "method": "Heuristic pagination detection from URL and rel next/prev, not proof of crawlability in Google. "
                      "Google does not require rel next/prev for indexing."}


RICH_POTENTIAL = {
    "Article", "BlogPosting", "NewsArticle", "Product", "Recipe", "Event", "JobPosting",
    "BreadcrumbList", "VideoObject", "LocalBusiness", "FAQPage",
}


@router.get("/sites/{site_id}/advanced/schema-review")
def schema_review(site_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = db.scalar(select(Crawl).where(Crawl.site_id == site.id, Crawl.status == "completed",
                                          Crawl.competitor_id.is_(None)).order_by(Crawl.id.desc()))
    if crawl is None:
        return {"crawl_id": None, "items": [], "method": "Ein Crawl fehlt"}
    pages = db.scalars(select(Page).where(Page.crawl_id == crawl.id, Page.is_html.is_(True))
                       .order_by(Page.id).limit(350)).all()
    result = []
    for page in pages:
        jsonld = (page.data or {}).get("jsonld") or []
        if not jsonld:
            continue
        validation = validate_jsonld(jsonld)
        types = set()
        for item in jsonld:
            if isinstance(item, dict):
                raw = item.get("@type")
                values = raw if isinstance(raw, list) else [raw]
                types.update(str(x).split("/")[-1] for x in values if isinstance(x, str))
        result.append({"url": page.url, "types": sorted(types),
                       "potential_google_feature_types": sorted(types & RICH_POTENTIAL),
                       "other_schema_types": sorted(types - RICH_POTENTIAL),
                       "validator_result": validation, "google_eligibility_confirmed": False})
    return {"crawl_id": crawl.id, "items": result, "method": "Schema validation vs. a non-exhaustive list of possible "
            "Google-visible types. Actual rich result policy, visibility, availability and eligibility are not tested; "
            "consult current Google Search Central documentation."}
