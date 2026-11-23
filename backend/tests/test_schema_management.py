"""Schema drafts are sourced from crawls, validated and separately approved."""
from __future__ import annotations

from types import SimpleNamespace

from app.audit.schema_validator import generate_template
from app.services.schema_management import matching_pages, prefill, schema_diff


def test_german_template_defaults_do_not_claim_stock():
    assert generate_template("Product")["offers"]["priceCurrency"] == "EUR"
    assert generate_template("Product")["offers"]["availability"] == ""
    assert generate_template("LocalBusiness")["address"]["addressCountry"] == "DE"
    assert generate_template("Article")["inLanguage"] == "de"


def test_prefill_uses_observed_page_data_without_fabricated_offers():
    site = SimpleNamespace(name="Studio", url="https://example.de/")
    page = SimpleNamespace(url="https://example.de/shop/kueche/", h1="Küche Eiche", title="Küche Eiche",
        meta_description="Modellbeschreibung", canonical="https://example.de/shop/kueche/",
        lang="de", depth=2, data={"og": {"og:image": "https://example.de/img.webp"}, "jsonld": []})
    result = prefill(page, site, "Product")
    assert result["jsonld"]["name"] == "Küche Eiche"
    assert result["jsonld"]["image"] == ["https://example.de/img.webp"]
    assert "offers" not in result["jsonld"]
    assert result["rich_result_eligibility_confirmed"] is False
    assert schema_diff([], result["jsonld"])
    assert len(matching_pages([page], "/shop/*")) == 1
    assert matching_pages([page], "/blog/*") == []


def test_schema_proposal_api_approval_and_tenant_boundary(client, auth, crawled):
    sid = crawled["site"]["id"]
    url = crawled["base"] + "/about"
    pre = client.post(f"/api/sites/{sid}/schema-manager/prefill", headers=auth,
                      json={"url": url, "schema_type": "WebPage"})
    assert pre.status_code == 200, pre.text
    doc = pre.json()["jsonld"]
    assert doc["@type"] == "WebPage" and doc.get("name")
    response = client.post(f"/api/sites/{sid}/schema-manager/proposals", headers=auth,
                           json={"url": url, "jsonld": doc, "rationale": "Test"})
    assert response.status_code == 201, response.text
    item_id = response.json()["work_item_id"]
    path = f"/api/sites/{sid}/seo-work/{item_id}/content-proposal"
    stored = client.get(path, headers=auth).json()
    assert stored["content_type"] == "application/ld+json"
    assert stored["status"] == "draft"
    approved = client.post(path + "/approve", headers=auth)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    second = client.post("/api/auth/register", json={
        "email": "schema-second@example.com", "password": "correct horse battery"}).json()
    other_headers = {"Authorization": "Bearer " + second["access_token"]}
    assert client.post(f"/api/sites/{sid}/schema-manager/prefill", headers=other_headers,
                       json={"url": url}).status_code == 404
    assert client.get(path, headers=other_headers).status_code == 404


def test_template_preview_and_delete(client, auth, crawled):
    sid = crawled["site"]["id"]
    base = f"/api/sites/{sid}/schema-manager/templates"
    create = client.post(base, headers=auth, json={
        "name": "Artikel", "schema_type": "Article",
        "url_pattern": "/about", "field_mapping": {"headline": "{title}"}})
    assert create.status_code == 201, create.text
    template_id = create.json()["id"]
    preview = client.post(f"{base}/{template_id}/preview", headers=auth)
    assert preview.status_code == 200, preview.text
    assert preview.json()["matched"] >= 1
    assert preview.json()["items"][0]["jsonld"]["@type"] == "Article"
    assert client.delete(f"{base}/{template_id}", headers=auth).status_code == 204
    assert client.post(f"{base}/{template_id}/preview", headers=auth).status_code == 404
    invalid = client.post(base, headers=auth, json={"name": "Unsafe", "schema_type": "Article",
        "url_pattern": "/about", "field_mapping": {"hack": "{title}"}})
    assert invalid.status_code == 422
