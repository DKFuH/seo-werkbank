"""Keyword research, SERP analysis, content optimiser, schema tools and page speed."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..audit.geo import analyse_geo
from ..audit.schema_validator import SPECS, TEMPLATES, all_types, generate_template, validate_jsonld
from ..content.optimizer import analyse_content, parse_draft
from ..content.wdf_idf import analyse_wdf_idf
from ..crawler.fetcher import Fetcher
from ..crawler.parser import parse_html
from ..db import get_db
from ..integrations import gsc
from ..integrations import pagespeed as psi
from ..integrations.gsc import parse_number
from ..keywords import research
from ..models import GscRow, Keyword, Page, PageSpeedResult, User
from ..reports.exports import to_csv, to_xlsx
from ..security.auth import current_user, get_site_for
from ..serp import analyzer as serp
from ..services.settings_store import get_setting
from .deps import checked_url, download, latest_crawl, read_upload

router = APIRouter(tags=["tools"])


# ----------------------------------------------------------------------------- keywords
class SuggestIn(BaseModel):
    seed: str = Field(min_length=1, max_length=120)
    lang: str = Field("en", pattern=r"^[a-z]{2}$")
    country: str = Field("us", pattern=r"^[a-zA-Z]{2}$")
    sources: list[Literal["google", "bing", "duckduckgo"]] = ["google", "bing", "duckduckgo"]
    depth: Literal["basic", "deep"] = "basic"


class ClusterIn(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=3000)
    seed: str | None = Field(None, max_length=120)
    threshold: float = Field(0.5, ge=0.1, le=1.0)


class KeywordsIn(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=2000)
    source: str = Field("manual", max_length=40)


@router.post("/keywords/suggest")
async def keyword_suggest(body: SuggestIn, user: User = Depends(current_user)) -> dict:
    result = await research.suggest(body.seed, body.lang, body.country.lower(), list(body.sources), body.depth)
    result["clusters"] = research.cluster_keywords([k["keyword"] for k in result["keywords"]], seed=body.seed)[:60]
    result["data_notes"] = [
        "Die Vorschläge sind echte Vervollständigungen der genannten öffentlichen Dienste zum Abfragezeitpunkt.",
        "Suchvolumen, CPC und Wettbewerb liefern diese Quellen NICHT, und hier wird nichts davon geschätzt. "
        "Für gemessene Nachfrage eine Keyword-Planer-CSV importieren oder Search-Console-Impressionen nutzen.",
        "Suchintentionen sind regelbasierte Schätzungen.",
    ]
    return result


@router.post("/keywords/cluster")
def keyword_cluster(body: ClusterIn, user: User = Depends(current_user)) -> dict:
    return {"clusters": research.cluster_keywords(body.keywords, body.threshold, body.seed), "method": "Lexikalisch (gemeinsame Wortstämme, Jaccard-Ähnlichkeit)"}



class SerpClusterIn(BaseModel):
    keywords: list[str] = Field(min_length=2, max_length=15)
    country: str = Field("de", pattern=r"^[a-z]{2}$")
    lang: str = Field("de", pattern=r"^[a-z]{2}$")
    min_overlap: int = Field(3, ge=1, le=10)
    manual_results: dict[str, list[str]] | None = None


@router.post("/keywords/serp-clusters")
async def keyword_serp_clusters(body: SerpClusterIn, user: User = Depends(current_user),
                                db: Session = Depends(get_db)) -> dict:
    """Request 2–15 identical-provider SERPs, or cluster complete supplied URL sets."""
    keywords = [" ".join(k.strip().split()) for k in body.keywords]
    if any(not k or len(k) > 200 for k in keywords) or len(set(keywords)) != len(keywords):
        raise HTTPException(422, "2–15 unterschiedliche Keywords mit höchstens 200 Zeichen eingeben")
    if body.manual_results is not None:
        if set(body.manual_results) != set(keywords):
            raise HTTPException(422, "Manuelle SERP-Listen müssen exakt zu allen Keywords vorliegen")
        results = {kw: urls[:10] for kw, urls in body.manual_results.items()}
        for urls in results.values():
            if not urls:
                raise HTTPException(422, "Leere Ergebnisliste")
            for url in urls:
                parts = urlsplit(url)
                if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
                    raise HTTPException(422, "Ungültige Ergebnis-URL")
        provider = "manual"
    else:
        settings = get_setting(db, "serp")
        if settings.get("provider", "none") == "none":
            raise HTTPException(422, "SERP-Anbieter konfigurieren oder manuelle Ergebnisse liefern")
        results = {}
        for kw in keywords:
            try:
                result = await serp.search(settings, kw, country=body.country, lang=body.lang, num=10)
            except serp.SerpError as exc:
                raise HTTPException(502, "SERP-Anbieter konnte nicht alle Keywords abrufen") from exc
            results[kw] = [r["url"] for r in result["results"]]
        provider = settings["provider"]
    return {"provider": provider, "clusters": research.cluster_by_serp(results, body.min_overlap),
            "keywords_count": len(results), "min_overlap": body.min_overlap,
            "method": "Identische URL-Überschneidungen in erfassten Top-10-Listen, transitive Gruppierung; "
                      "keine bestätigten Google-Rankings und keine automatische Seitenarchitektur-Entscheidung."}


@router.post("/keywords/intent")
def keyword_intent(body: KeywordsIn, user: User = Depends(current_user)) -> dict:
    return {"items": [{"keyword": k, **research.classify_intent(k)} for k in body.keywords[:2000]]}


def _gsc_metrics(db: Session, site_id: int) -> dict[str, dict]:
    rows = db.execute(select(GscRow.query, func.sum(GscRow.clicks), func.sum(GscRow.impressions),
                             func.sum(GscRow.position * GscRow.impressions) / func.nullif(func.sum(GscRow.impressions), 0))
                      .where(GscRow.site_id == site_id, GscRow.dataset == "query_page", GscRow.query.isnot(None)).group_by(GscRow.query)).all()
    return {q.lower(): {"clicks": round(c or 0), "impressions": round(i or 0), "position": round(p, 1) if p else None} for q, c, i, p in rows}


@router.get("/sites/{site_id}/keywords")
def list_keywords(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    gsc = _gsc_metrics(db, site.id)
    items = []
    for k in db.scalars(select(Keyword).where(Keyword.site_id == site.id).order_by(Keyword.keyword)):
        measured = gsc.get(k.keyword.lower())
        imported = (k.metrics or {}).get("imported") or {}
        items.append({"id": k.id, "keyword": k.keyword, "source": k.source, "intent": k.intent, "cluster": k.cluster,
                      "gsc": measured, "imported": imported,
                      "search_volume": imported.get("search_volume"),
                      "volume_status": "imported" if imported.get("search_volume") is not None else "unavailable",
                      "created_at": k.created_at.isoformat()})
    return {"items": items, "has_gsc_data": bool(gsc),
            "legend": {"gsc": "Von der Google Search Console für deine Website gemessen", "imported": "Werte aus einer importierten Datei",
                       "unavailable": "Keine legitime kostenlose Quelle; lieber leer als geraten"}}


@router.post("/sites/{site_id}/keywords", status_code=201)
def save_keywords(site_id: int, body: KeywordsIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    existing = {k.lower() for k in db.scalars(select(Keyword.keyword).where(Keyword.site_id == site.id))}
    added = 0
    for kw in dict.fromkeys(" ".join(k.lower().split())[:500] for k in body.keywords):
        if kw and kw not in existing:
            db.add(Keyword(site_id=site.id, keyword=kw, source=body.source, intent=research.classify_intent(kw)["intent"]))
            existing.add(kw)
            added += 1
    db.flush()
    all_kw = list(db.scalars(select(Keyword).where(Keyword.site_id == site.id)))
    label_of = {k: c["label"] for c in research.cluster_keywords([k.keyword for k in all_kw]) for k in c["keywords"]}
    for k in all_kw:
        k.cluster = label_of.get(k.keyword)
    db.commit()
    return {"added": added, "total": len(all_kw)}


@router.post("/sites/{site_id}/keywords/import")
async def import_keywords(site_id: int, file: UploadFile, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Import a keyword list with metrics, e.g. a Google Ads Keyword Planner export (Keyword, Avg. monthly searches, Competition, bids)."""
    import csv
    import io

    site = get_site_for(db, user, site_id)
    raw = await read_upload(file)
    text = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig", "replace")
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines[:10]) if "keyword" in ln.lower()), 0)
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[start : start + 5]), delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])), dialect=dialect)
    alias = {"keyword": ("keyword", "keywords", "search term", "query", "suchbegriff", "suchanfrage"),
             "search_volume": ("avg. monthly searches", "search volume", "volume", "avg monthly searches",
                               "durchschnittl. monatliche suchanfragen", "durchschn. monatliche suchanfragen", "suchvolumen", "monatliche suchanfragen"),
             "competition": ("competition", "competition (indexed value)", "wettbewerb", "wettbewerb (indexierter wert)"),
             "cpc_low": ("top of page bid (low range)", "gebot für obere positionen auf der seite (niedriger bereich)"),
             "cpc_high": ("top of page bid (high range)", "cpc", "gebot für obere positionen auf der seite (hoher bereich)")}
    german = any(
        (h or "").strip().lower() in ("suchbegriff", "wettbewerb", "durchschnittl. monatliche suchanfragen", "durchschn. monatliche suchanfragen", "suchvolumen")
        for h in (reader.fieldnames or []))
    existing = {k.keyword: k for k in db.scalars(select(Keyword).where(Keyword.site_id == site.id))}
    added = updated = 0
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        rec: dict[str, Any] = {}
        for field, names in alias.items():
            for n in names:
                if norm.get(n):
                    rec[field] = norm[n]
                    break
        kw = " ".join(rec.pop("keyword", "").lower().split())[:500]
        if not kw:
            continue
        for f in ("search_volume", "cpc_low", "cpc_high"):
            if f in rec:
                try:
                    rec[f] = parse_number(rec[f].replace("$", "").replace("€", ""), german, strict=True)
                except ValueError:
                    rec.pop(f)
        rec["file"] = (file.filename or "")[:120]
        if kw in existing:
            existing[kw].metrics = {**(existing[kw].metrics or {}), "imported": rec}
            updated += 1
        elif added < 20_000:
            k = Keyword(site_id=site.id, keyword=kw, source="import", intent=research.classify_intent(kw)["intent"], metrics={"imported": rec})
            db.add(k)
            existing[kw] = k
            added += 1
    db.commit()
    return {"added": added, "updated": updated}


@router.delete("/sites/{site_id}/keywords", status_code=204)
def delete_keywords(site_id: int, ids: list[int], user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    db.execute(delete(Keyword).where(Keyword.site_id == site.id, Keyword.id.in_(ids[:5000])))
    db.commit()


@router.get("/sites/{site_id}/keywords/mapping")
def keyword_mapping(site_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Keyword-to-page mapping and cannibalisation risks, based on the latest crawl (on-page relevance estimate)."""
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    keywords = list(db.scalars(select(Keyword.keyword).where(Keyword.site_id == site.id).order_by(Keyword.keyword).limit(500)))
    if not crawl:
        return {"items": [], "crawl_id": None, "message": "Zuerst crawlen, damit Keywords Seiten zugeordnet werden können."}
    pages = [{"url": u, "title": t, "h1": h, "meta_description": d, "text": (x or "")[:6000]} for u, t, h, d, x in db.execute(
        select(Page.url, Page.title, Page.h1, Page.meta_description, Page.text).where(Page.crawl_id == crawl.id, Page.indexable.is_(True)).order_by(Page.pagerank.desc()).limit(1500))]
    items = research.map_keywords(keywords, pages)
    # Compare the intended page (best on-page match) with the page Google actually shows for the query.
    ranking = gsc.ranking_pages(db, site.id, keywords)
    for item in items:
        r = ranking.get(" ".join(item["keyword"].lower().split()))
        item["gsc"] = r
        intended = (item.get("best_page") or {}).get("url")
        item["target_mismatch"] = bool(r and intended and not gsc.same_page(r["top"]["url"], intended))
    summary = {s: sum(1 for i in items if i["status"] == s) for s in ("mapped", "cannibalisation risk", "no matching page")}
    summary["target mismatch"] = sum(1 for i in items if i["target_mismatch"])
    return {"items": items, "crawl_id": crawl.id, "pages_considered": len(pages), "summary": summary,
            "gsc_available": bool(ranking),
            "gsc_note": None if ranking else "Für den Abgleich mit Google braucht es Search-Console-Zeilen mit Suchanfrage und Seite (API-Synchronisierung)."}


@router.get("/sites/{site_id}/keywords/export")
def export_keywords(site_id: int, format: str = "csv", user: User = Depends(current_user), db: Session = Depends(get_db)):
    site = get_site_for(db, user, site_id)
    rows = [{"keyword": i["keyword"], "cluster": i["cluster"], "intent (estimate)": i["intent"], "source": i["source"],
             "gsc_clicks (measured)": (i["gsc"] or {}).get("clicks"), "gsc_impressions (measured)": (i["gsc"] or {}).get("impressions"),
             "gsc_avg_position (measured)": (i["gsc"] or {}).get("position"), "search_volume (imported)": i["search_volume"],
             "competition (imported)": i["imported"].get("competition")} for i in list_keywords(site_id, user, db)["items"]]
    if format == "xlsx":
        mapping = [{"keyword": m["keyword"], "status": m["status"], "best_page": (m["best_page"] or {}).get("url"),
                    "competing_pages": ", ".join(c["url"] for c in m["competing_pages"])} for m in keyword_mapping(site_id, user, db)["items"]]
        return download(to_xlsx({"Keywords": rows, "Page mapping": mapping}), f"keywords-{site.domain}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return download(to_csv(rows), f"keywords-{site.domain}.csv", "text/csv")


# ----------------------------------------------------------------------------- SERP
class SerpIn(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    country: str = Field("us", pattern=r"^[a-zA-Z]{2}$")
    lang: str = Field("en", pattern=r"^[a-z]{2}$")
    urls: list[str] = Field(default_factory=list, max_length=20)  # manual mode: paste the ranking URLs
    my_url: str | None = Field(None, max_length=2048)
    fetch_pages: bool = True


@router.get("/serp/providers")
def serp_providers(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return {"configured": get_setting(db, "serp").get("provider", "none"), "providers": serp.PROVIDERS}


@router.post("/serp/analyze")
async def serp_analyze(body: SerpIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    features: list[str] = []
    if body.urls:
        results = [{"position": i + 1, "url": checked_url(u), "title": "", "snippet": ""} for i, u in enumerate(body.urls)]
        source = {"provider": "manual", "note": "URLs supplied manually; positions follow the order you entered."}
    else:
        try:
            found = await serp.search(get_setting(db, "serp"), body.keyword, body.country.lower(), body.lang)
        except serp.SerpError as exc:
            raise HTTPException(400, str(exc)) from exc
        results, features = found["results"], found["features"]
        source = {"provider": found["provider"], "note": found["note"]}
    my_url = checked_url(body.my_url) if body.my_url else None
    pages = {}
    if body.fetch_pages and results:
        targets = [r["url"] for r in results[:10]] + ([my_url] if my_url else [])
        pages = await serp.fetch_pages(list(dict.fromkeys(targets)), limit=11)
    out = serp.analyse(body.keyword, results, pages, features, my_url)
    out["source"] = source
    out["feature_note"] = "SERP features are only those the provider's API reports; absence here does not prove absence on Google."
    return out


# ----------------------------------------------------------------------------- content optimiser
class ContentIn(BaseModel):
    content: str = Field(min_length=1, max_length=400_000)
    keyword: str = Field(min_length=1, max_length=200)
    title: str | None = Field(None, max_length=500)
    meta_description: str | None = Field(None, max_length=1000)
    url: str | None = Field(None, max_length=2048)
    secondary_keywords: list[str] = Field(default_factory=list, max_length=30)
    competitor_urls: list[str] = Field(default_factory=list, max_length=10)
    use_serp: bool = False
    site_id: int | None = None
    suggest_questions: bool = False


@router.post("/content/analyze")
async def content_analyze(body: ContentIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    competitors: list[dict] = []
    notes: list[str] = []
    urls = [checked_url(u) for u in body.competitor_urls]
    if body.use_serp and not urls:
        try:
            urls = [r["url"] for r in (await serp.search(get_setting(db, "serp"), body.keyword))["results"][:8]]
        except serp.SerpError as exc:
            notes.append(f"SERP-Abfrage übersprungen: {exc}")
    if urls:
        pages = await serp.fetch_pages(urls, limit=10)
        competitors = [{"url": u, **p} for u, p in pages.items() if p.get("status") == 200]
        failed = [u for u, p in pages.items() if p.get("status") != 200]
        if failed:
            notes.append(f"{len(failed)} Wettbewerberseite(n) nicht ladbar.")
    site_pages = None
    if body.site_id:
        site = get_site_for(db, user, body.site_id)
        crawl = latest_crawl(db, site.id)
        if crawl:
            site_pages = [{"url": u, "title": t, "h1": h} for u, t, h in db.execute(
                select(Page.url, Page.title, Page.h1).where(Page.crawl_id == crawl.id, Page.indexable.is_(True)).limit(3000))]
    questions = None
    if body.suggest_questions:
        try:
            sug = await research.suggest(body.keyword, sources=["google", "bing"], depth="basic")
            questions = [k["keyword"] for k in sug["keywords"] if k["type"] == "question"][:15]
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Fragevorschläge nicht verfügbar: {exc}")
    result = analyse_content(body.content, body.keyword, title=body.title, meta_description=body.meta_description, url=body.url,
                             secondary_keywords=body.secondary_keywords, competitors=competitors, site_pages=site_pages,
                             question_keywords=questions)
    result["notes"] += notes
    result["competitors"] = [{"url": c["url"], "title": c.get("title"), "word_count": c.get("word_count")} for c in competitors]
    # WDF*IDF des Entwurfs gegen dieselben Wettbewerberseiten (keine zusätzlichen Abrufe).
    if competitors:
        draft = parse_draft(body.content, body.url or "https://draft.invalid/")
        own = {"url": body.url or "Entwurf", "text": draft["text"], "headings": draft["headings"], "title": body.title}
        result["wdf_idf"] = analyse_wdf_idf(own, competitors, keyword=body.keyword, lang="de", limit=40)
    return result


class WdfIdfIn(BaseModel):
    keyword: str = Field("", max_length=200)
    my_url: str | None = Field(None, max_length=2048)
    my_content: str | None = Field(None, max_length=400_000)
    competitor_urls: list[str] = Field(default_factory=list, max_length=10)
    use_serp: bool = False
    lang: str = Field("de", pattern=r"^[a-z]{2}$")
    country: str = Field("de", pattern=r"^[a-zA-Z]{2}$")
    ngram: int = Field(1, ge=1, le=2)
    limit: int = Field(50, ge=10, le=150)


@router.post("/content/wdf-idf")
async def content_wdf_idf(body: WdfIdfIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """WDF*IDF of the own page (URL or pasted text) against competitor pages."""
    notes: list[str] = []
    urls = [checked_url(u) for u in body.competitor_urls]
    if body.use_serp and not urls:
        if not body.keyword.strip():
            raise HTTPException(400, "Für die SERP-Abfrage wird ein Keyword benötigt.")
        try:
            found = await serp.search(get_setting(db, "serp"), body.keyword, body.country.lower(), body.lang)
            urls = [r["url"] for r in found["results"][:10]]
        except serp.SerpError as exc:
            raise HTTPException(400, str(exc)) from exc
    my_url = checked_url(body.my_url) if body.my_url else None
    urls = [u for u in dict.fromkeys(urls) if u != my_url]
    if not urls:
        raise HTTPException(400, "Mindestens eine Wettbewerber-URL angeben (oder SERP-Anbieter nutzen).")
    pages = await serp.fetch_pages(urls + ([my_url] if my_url and not body.my_content else []), limit=11)
    own = None
    if body.my_content and body.my_content.strip():
        draft = parse_draft(body.my_content, my_url or "https://draft.invalid/")
        own = {"url": my_url or "Eigener Text", "text": draft["text"], "headings": draft["headings"], "title": draft["title"]}
    elif my_url:
        p = pages.get(my_url, {})
        if p.get("status") == 200:
            own = {"url": my_url, **p}
        else:
            notes.append(f"Eigene URL nicht ladbar: {p.get('error') or 'unbekannter Fehler'}")
    competitors = [{"url": u, **pages[u]} for u in urls if pages.get(u, {}).get("status") == 200]
    failed = [{"url": u, "error": pages.get(u, {}).get("error")} for u in urls if pages.get(u, {}).get("status") != 200]
    result = analyse_wdf_idf(own, competitors, keyword=body.keyword, lang=body.lang, limit=body.limit, ngram=body.ngram)
    result["notes"] = notes + result["notes"]
    result["failed"] = failed
    return result


class GeoIn(BaseModel):
    url: str = Field(max_length=2048)


@router.post("/geo/check")
async def geo_check(body: GeoIn, user: User = Depends(current_user)) -> dict:
    """GEO checklist for one URL: AI crawler access, llms.txt, entity data, answer structure and evidence."""
    url = checked_url(body.url)
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    async with Fetcher(timeout_s=20, retries=1) as fetcher:
        res = await fetcher.fetch_following(url, max_body=5_000_000)
        if res.status != 200 or not res.is_html:
            raise HTTPException(400, f"Seite nicht ladbar: {res.error or f'HTTP {res.status}'}")
        robots, llms, ai_txt = await asyncio.gather(
            fetcher.fetch_following(root + "/robots.txt", max_body=500_000),
            fetcher.fetch_following(root + "/llms.txt", max_body=500_000),
            fetcher.fetch_following(root + "/.well-known/ai.txt", max_body=200_000),
        )
    final = res.final_url or url
    parsed = await asyncio.to_thread(parse_html, res.body, final, res.headers.get("content-type", ""))
    robots_text = robots.body.decode("utf-8", "replace") if robots.status == 200 else ""
    llms_text = llms.body.decode("utf-8", "replace")[:5000] if llms.status == 200 else ""
    return analyse_geo(final, res.body, parsed, robots_text=robots_text, robots_status=robots.status,
                       llms_status=llms.status, llms_text=llms_text, ai_txt_status=ai_txt.status, headers=res.headers)


class FetchIn(BaseModel):
    url: str = Field(max_length=2048)


@router.post("/content/fetch")
async def content_fetch(body: FetchIn, user: User = Depends(current_user)) -> dict:
    """Load an existing page into the editor (title, description, headings and main text)."""
    url = checked_url(body.url)
    async with Fetcher(timeout_s=20, retries=1) as fetcher:
        res = await fetcher.fetch_following(url, max_body=3_000_000)
    if res.status != 200 or not res.is_html:
        raise HTTPException(400, f"Seite nicht ladbar: {res.error or f'HTTP {res.status}'}")
    p = await asyncio.to_thread(parse_html, res.body, res.final_url or url, res.headers.get("content-type", ""))
    md = "\n\n".join(f"{'#' * h['level']} {h['text']}" for h in p.headings[:3]) if not p.text else ""
    try:
        import trafilatura
        md = await asyncio.to_thread(
            trafilatura.extract, res.body.decode("utf-8", "replace"), output_format="markdown", include_links=True, include_images=True) or md
    except Exception:  # noqa: BLE001 - fall back to plain text below
        pass
    return {"url": res.final_url or url, "title": p.title, "meta_description": p.meta_description, "content": md or p.text, "word_count": p.word_count}


# ----------------------------------------------------------------------------- schema tools
class SchemaValidateIn(BaseModel):
    url: str | None = Field(None, max_length=2048)
    jsonld: str | None = Field(None, max_length=500_000)


class SchemaGenerateIn(BaseModel):
    type: str = Field(max_length=40)
    values: dict[str, Any] = Field(default_factory=dict)


@router.get("/schema/types")
def schema_types(user: User = Depends(current_user)) -> dict:
    return {"templates": sorted(TEMPLATES), "validated_types": {t: {"required": s["required"], "recommended": s["recommended"]} for t, s in SPECS.items()}}


@router.post("/schema/validate")
async def schema_validate(body: SchemaValidateIn, user: User = Depends(current_user)) -> dict:
    items, parse_errors, microdata = [], [], []
    if body.jsonld:
        raw = body.jsonld.strip()
        if raw.lower().startswith("<script"):
            page = await asyncio.to_thread(parse_html, f"<html><head>{raw}</head><body></body></html>".encode(), "https://input.invalid/")
            items, parse_errors = page.jsonld, page.jsonld_errors
        else:
            try:
                from ..crawler.parser import _flatten_jsonld
                items = _flatten_jsonld(json.loads(raw))
            except json.JSONDecodeError as exc:
                parse_errors = [f"Ungültiges JSON: {exc.msg} (Zeile {exc.lineno}, Spalte {exc.colno})"]
    elif body.url:
        url = checked_url(body.url)
        async with Fetcher(timeout_s=20, retries=1) as fetcher:
            res = await fetcher.fetch_following(url, max_body=3_000_000)
        if res.status != 200 or not res.is_html:
            raise HTTPException(400, f"Seite nicht ladbar: {res.error or f'HTTP {res.status}'}")
        page = await asyncio.to_thread(parse_html, res.body, res.final_url or url, res.headers.get("content-type", ""))
        items, parse_errors, microdata = page.jsonld, page.jsonld_errors, page.microdata_types
    else:
        raise HTTPException(422, "URL oder JSON-LD-Markup angeben")
    result = validate_jsonld(items)
    return {**result, "parse_errors": parse_errors, "items": items[:40], "all_types": all_types(items), "microdata_types": microdata,
            "valid": not parse_errors and result["errors"] == 0}


@router.post("/schema/generate")
def schema_generate(body: SchemaGenerateIn, user: User = Depends(current_user)) -> dict:
    try:
        doc = generate_template(body.type, body.values)
    except KeyError:
        raise HTTPException(404, f"Keine Vorlage für '{body.type}'") from None
    text = json.dumps(doc, indent=2, ensure_ascii=False).replace("</", "<\\/")  # safe to embed inside <script>
    return {"jsonld": doc, "html": f'<script type="application/ld+json">\n{text}\n</script>', "validation": validate_jsonld([doc])}


# ----------------------------------------------------------------------------- page speed
class SpeedIn(BaseModel):
    url: str = Field(max_length=2048)
    strategy: Literal["mobile", "desktop"] = "mobile"
    source: Literal["psi", "local"] = "psi"
    site_id: int | None = None


@router.get("/pagespeed/status")
def pagespeed_status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return {"psi_key_configured": bool(get_setting(db, "pagespeed").get("api_key")), "local_lighthouse": bool(psi.lighthouse_path()),
            "notes": ["Die PageSpeed-Insights-API ist kostenlos; ohne Schlüssel ist das anonyme Kontingent klein und geteilt.",
                      "Felddaten (Core Web Vitals echter Nutzer inkl. INP) stammen aus dem Chrome UX Report und gibt es nur für Seiten mit genug Traffic.",
                      "Lokales Lighthouse liefert nur Labordaten; Installation: npm install -g lighthouse"]}


@router.post("/pagespeed/run")
async def pagespeed_run(body: SpeedIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    url = checked_url(body.url)
    site_id = get_site_for(db, user, body.site_id).id if body.site_id else None
    try:
        if body.source == "local":
            if not user.is_admin:  # starts a full Chrome on the server
                raise HTTPException(403, "Lokale Lighthouse-Läufe sind Administratoren vorbehalten")
            data = await psi.run_local_lighthouse(url, body.strategy)
        else:
            data = await psi.run_psi(url, body.strategy, get_setting(db, "pagespeed").get("api_key", ""))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a failed run
        raise HTTPException(502, str(exc)) from exc
    row = PageSpeedResult(site_id=site_id, owner_id=user.id, url=url, strategy=body.strategy, source=data["source"], data=data)
    db.add(row)
    db.commit()
    return {"id": row.id, "url": url, "created_at": row.created_at.isoformat(), **data}


@router.get("/pagespeed/history")
def pagespeed_history(site_id: int | None = None, url: str | None = None, limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(PageSpeedResult).where(PageSpeedResult.owner_id == user.id)
    if site_id:
        stmt = stmt.where(PageSpeedResult.site_id == site_id)
    if url:
        stmt = stmt.where(PageSpeedResult.url == url)
    return [{"id": r.id, "url": r.url, "strategy": r.strategy, "source": r.source, "created_at": r.created_at.isoformat(),
             "scores": (r.data or {}).get("scores"), "lab": (r.data or {}).get("lab"), "field": (r.data or {}).get("field")}
            for r in db.scalars(stmt.order_by(PageSpeedResult.id.desc()).limit(min(limit, 200)))]


@router.get("/pagespeed/{result_id}")
def pagespeed_result(result_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    r = db.get(PageSpeedResult, result_id)
    if r is None or r.owner_id != user.id:
        raise HTTPException(404, "Ergebnis nicht gefunden")
    return {"id": r.id, "url": r.url, "created_at": r.created_at.isoformat(), **(r.data or {})}
