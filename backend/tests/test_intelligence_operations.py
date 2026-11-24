"""Editorial review hints, immutable report exports and lost-link recovery."""
from __future__ import annotations

from app.db import session_scope
from app.models import Backlink, SeoResearchRecord, SeoWorkItem
from app.services.editorial_quality import review
from tests.conftest import wait_for_job


def test_editorial_detects_new_numbers_urls_and_dates_without_claiming_truth():
    x = review("## Küche\nEine Anleitung.", "## Küche\n20 % sparen bis 2027. https://example.org/test",
               "Recherche noch prüfen")
    assert x["needs_review"]
    kinds = {row["kind"] for row in x["findings"]}
    assert "new_numbers" in kinds
    assert "new_dates" in kinds
    assert "new_urls" in kinds
    assert x["rationale_present"] is True
    assert "kein semantischer Wahrheitsbeweis" in x["method"]


def test_editorial_preview_requires_owner_and_content_item(client, auth):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Editorial QA", "url": "https://editorial.example.org/"}).json()
    sid = site["id"]
    with session_scope() as db:
        obj = SeoWorkItem(site_id=sid, kind="content", status="planned",
                          title="Artikel", target_url="https://editorial.example.org/test")
        db.add(obj)
        db.flush()
        item = obj.id
    url = f"/api/sites/{sid}/seo-work/{item}/editorial-qa"
    response = client.post(url, headers=auth, json={
        "original_text": "alt", "proposed_text": "Preis 500 €"})
    assert response.status_code == 200, response.text
    assert response.json()["finding_count"] >= 1
    other = client.post("/api/auth/register", json={
        "email": "qa-isolation@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.post(url, headers=h, json={
        "original_text": "alt", "proposed_text": "neu"}).status_code == 404


def test_report_snapshot_persists_and_formats(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Freeze Report", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    start = client.post(f"/api/sites/{sid}/crawls", headers=auth, json={
        "delay_ms": 0, "concurrency": 8, "max_urls": 30, "exclude_patterns": ["/big/"]})
    assert start.status_code == 202, start.text
    assert wait_for_job(client, auth, start.json()["job_id"])["status"] == "completed"
    base = f"/api/sites/{sid}/reports/snapshots"
    created = client.post(base, headers=auth, json={"title": "Monatsüberblick"})
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]
    assert created.json()["origin"] == "manual"
    html = client.get(f"{base}/{report_id}.html", headers=auth)
    assert html.status_code == 200
    assert "Monatsüberblick" in html.text
    assert "attachment" in html.headers.get("content-disposition", "")
    pdf = client.get(f"{base}/{report_id}.pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    history = client.get(base, headers=auth).json()["items"]
    assert history[0]["id"] == report_id
    other = client.post("/api/auth/register", json={
        "email": "report-isolation@example.com", "password": "correct horse battery"}).json()
    assert client.get(f"{base}/{report_id}.pdf", headers={
        "Authorization": "Bearer " + other["access_token"]}).status_code == 404


def test_link_recovery_separates_once_live_from_unconfirmed(client, auth):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Link Recovery", "url": "https://link-recovery.example.org/"}).json()
    sid = site["id"]
    with session_scope() as db:
        proven = Backlink(site_id=sid, source_url="https://publisher.example.org/article",
                          source_domain="publisher.example.org", status="lost",
                          target_url="https://link-recovery.example.org/old/")
        unconfirmed = Backlink(site_id=sid, source_url="https://other.example.org/page",
                               source_domain="other.example.org", status="lost")
        db.add_all([proven, unconfirmed])
        db.flush()
        proven_id = proven.id
        db.add(SeoResearchRecord(site_id=sid, kind="link_transition", source="verification",
                                 title="Veränderung", payload={
                                     "backlink_id": proven_id, "previous_status": "live",
                                     "current_status": "lost"}))
    base = f"/api/sites/{sid}/link-recovery"
    response = client.get(base, headers=auth)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2 and items[0]["confirmed_live_before"] is True
    created = client.post(f"{base}/{proven_id}/work", headers=auth)
    assert created.status_code == 201
    assert created.json()["automatic_contact"] is False
    other = client.post("/api/auth/register", json={
        "email": "link-recovery-other@example.com", "password": "correct horse battery"}).json()
    assert client.get(base, headers={"Authorization": "Bearer " + other["access_token"]}).status_code == 404
