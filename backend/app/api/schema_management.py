"""Site-scoped JSON-LD draft management; no automatic CMS writes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.schema_validator import TEMPLATES, validate_jsonld
from ..db import get_db
from ..models import Page, SchemaTemplate, SeoContentProposal, SeoWorkItem, User
from ..security.auth import current_user, get_site_for
from ..services.schema_management import FIELDS, TOKENS, matching_pages, prefill
from .deps import latest_crawl

router = APIRouter(tags=["schema-management"])


class PrefillIn(BaseModel):
    url: str = Field(min_length=5, max_length=2048)
    schema_type: str | None = Field(None, max_length=80)


class ProposalIn(PrefillIn):
    jsonld: dict
    rationale: str = Field("Schema-Entwurf aus Crawl und manueller Prüfung", max_length=4000)


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    schema_type: str = Field(min_length=1, max_length=80)
    url_pattern: str = Field("*", max_length=300)
    field_mapping: dict[str, str] = Field(default_factory=dict, max_length=12)


def _page(db: Session, site_id: int, url: str) -> Page:
    crawl = latest_crawl(db, site_id)
    if not crawl:
        raise HTTPException(409, "Abgeschlossener Crawl erforderlich")
    page = db.scalar(select(Page).where(Page.crawl_id == crawl.id, Page.url == url))
    if not page:
        raise HTTPException(404, "URL im letzten Crawl nicht vorhanden")
    return page


def _template(db: Session, site_id: int, template_id: int) -> SchemaTemplate:
    t = db.scalar(select(SchemaTemplate).where(SchemaTemplate.site_id == site_id,
                                                 SchemaTemplate.id == template_id))
    if t is None:
        raise HTTPException(404, "Schema-Vorlage nicht gefunden")
    return t


def _template_out(t: SchemaTemplate) -> dict:
    return {"id": t.id, "name": t.name, "schema_type": t.schema_type,
            "url_pattern": t.url_pattern, "field_mapping": t.field_mapping}


def _validate_template(body: TemplateIn) -> None:
    if body.schema_type not in TEMPLATES:
        raise HTTPException(422, "Schema-Typ nicht als Vorlage verfügbar")
    if not body.url_pattern.startswith("/"):
        raise HTTPException(422, "Glob-Muster muss mit / beginnen")
    if any(k not in FIELDS or v not in {f"{{{token}}}" for token in TOKENS}
           for k, v in body.field_mapping.items()):
        raise HTTPException(422, "Nur erlaubte Felder und Platzhalter zulässig")


@router.get("/sites/{site_id}/schema-manager/pages")
def pages(site_id: int, user: User = Depends(current_user),
          db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    crawl = latest_crawl(db, site.id)
    if not crawl:
        return {"pages": [], "crawl_id": None}
    rows = list(db.scalars(select(Page).where(Page.crawl_id == crawl.id,
                                              Page.status_code == 200, Page.is_html.is_(True))
                           .order_by(Page.url).limit(500)))
    return {"crawl_id": crawl.id,
            "pages": [{"url": p.url, "title": p.title or ""} for p in rows]}


@router.post("/sites/{site_id}/schema-manager/prefill")
def prefill_endpoint(site_id: int, body: PrefillIn, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    page = _page(db, site.id, body.url)
    try:
        return prefill(page, site, body.schema_type)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/sites/{site_id}/schema-manager/proposals", status_code=201)
def save_proposal(site_id: int, body: ProposalIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    page = _page(db, site.id, body.url)
    if body.jsonld.get("@context") != "https://schema.org" or not body.jsonld.get("@type"):
        raise HTTPException(422, "@context=https://schema.org und @type erforderlich")
    text = json.dumps(body.jsonld, ensure_ascii=False, indent=2)
    if len(text) > 100000:
        raise HTTPException(413, "Schema-Entwurf zu groß")
    validation = validate_jsonld([body.jsonld])
    original = json.dumps((page.data or {}).get("jsonld") or [], ensure_ascii=False, indent=2)
    item = SeoWorkItem(site_id=site.id, kind="content", status="draft",
                       title="JSON-LD: " + (page.title or page.url)[:270],
                       target_url=page.url, notes="content_type:application/ld+json")
    db.add(item)
    db.flush()
    proposal = SeoContentProposal(work_item_id=item.id, original_text=original,
                                  proposed_text=text, rationale=body.rationale,
                                  content_type="application/ld+json", status="draft")
    db.add(proposal)
    db.commit()
    return {"work_item_id": item.id, "proposal_id": proposal.id, "status": "draft",
            "content_type": proposal.content_type, "validation": validation,
            "remote_publication": False, "approval_required": True}


@router.get("/sites/{site_id}/schema-manager/templates")
def list_templates(site_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> list[dict]:
    site = get_site_for(db, user, site_id)
    return [_template_out(t) for t in db.scalars(select(SchemaTemplate).where(
        SchemaTemplate.site_id == site.id).order_by(SchemaTemplate.id.desc()).limit(100))]


@router.post("/sites/{site_id}/schema-manager/templates", status_code=201)
def create_template(site_id: int, body: TemplateIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    _validate_template(body)
    t = SchemaTemplate(site_id=site.id, name=body.name, schema_type=body.schema_type,
                       url_pattern=body.url_pattern, field_mapping=body.field_mapping)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _template_out(t)


@router.put("/sites/{site_id}/schema-manager/templates/{template_id}")
def update_template(site_id: int, template_id: int, body: TemplateIn,
                    user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    t = _template(db, site.id, template_id)
    _validate_template(body)
    for key, value in body.model_dump().items():
        setattr(t, key, value)
    db.commit()
    return _template_out(t)


@router.delete("/sites/{site_id}/schema-manager/templates/{template_id}", status_code=204)
def delete_template(site_id: int, template_id: int, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> None:
    site = get_site_for(db, user, site_id)
    db.delete(_template(db, site.id, template_id))
    db.commit()


@router.post("/sites/{site_id}/schema-manager/templates/{template_id}/preview")
def preview_template(site_id: int, template_id: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> dict:
    site = get_site_for(db, user, site_id)
    template = _template(db, site.id, template_id)
    crawl = latest_crawl(db, site.id)
    if not crawl:
        raise HTTPException(409, "Abgeschlossener Crawl erforderlich")
    pages = list(db.scalars(select(Page).where(Page.crawl_id == crawl.id,
                                               Page.status_code == 200, Page.is_html.is_(True)).limit(10000)))
    matched = matching_pages(pages, template.url_pattern)
    result = [prefill(p, site, template.schema_type, template.field_mapping) for p in matched[:30]]
    return {"matched": len(matched), "shown": len(result), "crawl_id": crawl.id,
            "items": result, "note": "Nur Vorschau: keine Schema-Markups gespeichert oder veröffentlicht"}
