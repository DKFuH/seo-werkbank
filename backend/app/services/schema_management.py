"""Evidence-led JSON-LD draft generation and diff. No publication or invented facts."""
from __future__ import annotations

import difflib
import fnmatch
import json
from urllib.parse import urlsplit

from ..audit.schema_validator import TEMPLATES, all_types, recommend_types, validate_jsonld

TOKENS = {
    "title", "h1", "description", "url", "canonical",
    "lang", "og_image", "site_name", "site_url",
}
FIELDS = {"name", "headline", "url", "description", "image", "inLanguage"}


def page_values(page, site) -> dict[str, str]:
    og = (page.data or {}).get("og") or {}
    return {
        "title": page.title or "", "h1": page.h1 or "",
        "description": page.meta_description or "", "url": page.url,
        "canonical": page.canonical or "", "lang": page.lang or "",
        "og_image": og.get("og:image", "") if isinstance(og, dict) else "",
        "site_name": site.name or "", "site_url": site.url,
    }


def recommended(page) -> list[dict]:
    existing = (page.data or {}).get("jsonld") or []
    headings = (page.data or {}).get("headings") or []
    questions = sum(1 for h in headings if isinstance(h, dict) and
                    str(h.get("text", "")).rstrip().endswith("?"))
    return recommend_types({"url": page.url, "depth": page.depth or 0,
                            "types": all_types(existing), "question_headings": questions})


def prefill(page, site, schema_type: str | None = None, mapping: dict[str, str] | None = None) -> dict:
    choices = recommended(page)
    selected = schema_type or next((x["type"] for x in choices if x["type"] in TEMPLATES), "WebPage")
    if selected not in TEMPLATES:
        raise ValueError("Schema-Typ nicht unterstützt")
    values = page_values(page, site)
    doc: dict = {"@context": "https://schema.org", "@type": selected}
    title = values["h1"] or values["title"]
    if selected in {"Article", "BlogPosting"} and title:
        doc["headline"] = title
    elif selected in {"Product", "Event", "Service", "WebPage", "Organization",
                      "WebSite", "LocalBusiness", "Person"} and title:
        doc["name"] = values["site_name"] if selected in {"Organization", "WebSite", "LocalBusiness"} else title
    if selected in {"Organization", "WebSite", "LocalBusiness"}:
        doc["name"] = values["site_name"] or doc.get("name", "")
        doc["url"] = values["site_url"]
    elif selected not in {"BreadcrumbList", "FAQPage"}:
        doc["url"] = values["canonical"] or values["url"]
    if selected not in {"BreadcrumbList", "FAQPage", "Organization", "Person"} and values["description"]:
        doc["description"] = values["description"]
    if selected in {"WebPage", "Article", "BlogPosting"} and values["lang"]:
        doc["inLanguage"] = values["lang"]
    if selected in {"Product", "Article", "BlogPosting", "Event"} and values["og_image"]:
        doc["image"] = [values["og_image"]]
    warnings = []
    if selected == "BreadcrumbList":
        parts = [p for p in urlsplit(page.url).path.split("/") if p]
        base = urlsplit(site.url)
        origin = f"{base.scheme}://{base.netloc}"
        items = [{"@type": "ListItem", "position": 1, "name": "Startseite", "item": origin + "/"}]
        prefix = ""
        for i, part in enumerate(parts, 2):
            prefix += "/" + part
            items.append({"@type": "ListItem", "position": i,
                          "name": part.replace("-", " ").replace("_", " "),
                          "item": origin + prefix + "/"})
        doc["itemListElement"] = items
        warnings.append("Breadcrumb-Namen aus URLs abgeleitet; sichtbare Navigation und Ziel-URLs prüfen")
    if selected in {"Product", "Event", "LocalBusiness", "FAQPage"}:
        warnings.append("Nicht belegte Preise, Verfügbarkeit, Anschriften und Antworten bewusst nicht ausgefüllt")
    if mapping:
        for field, placeholder in mapping.items():
            if field not in FIELDS or placeholder.strip("{}") not in TOKENS or not placeholder.startswith("{") or not placeholder.endswith("}"):
                raise ValueError("Nicht erlaubte Feldzuordnung")
            value = values[placeholder[1:-1]]
            if value:
                doc[field] = [value] if field == "image" else value
    doc = {k: v for k, v in doc.items() if v not in (None, "", [], {})}
    existing = (page.data or {}).get("jsonld") or []
    return {"url": page.url, "type": selected, "jsonld": doc, "existing": existing,
            "diff": schema_diff(existing, doc),
            "validation": validate_jsonld([doc]), "recommendations": choices,
            "warnings": warnings, "rich_result_eligibility_confirmed": False,
            "source": "last_completed_crawl", "remote_publication": False}


def schema_diff(existing: list | dict, proposed: dict) -> list[str]:
    before = json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True)
    after = json.dumps(proposed, ensure_ascii=False, indent=2, sort_keys=True)
    return list(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                    fromfile="Crawl JSON-LD", tofile="Entwurf",
                                    lineterm=""))[:400]


def matching_pages(pages, url_pattern: str):
    """Glob matching only the URL path, never execute patterns as regex or code."""
    if not url_pattern.startswith("/") or len(url_pattern) > 300:
        raise ValueError("URL-Muster muss ein Pfad ab / sein")
    return [p for p in pages if fnmatch.fnmatchcase(urlsplit(p.url).path, url_pattern)]
