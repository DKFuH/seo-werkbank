"""PDF report regressions: German labels, profile scores, engine evidence and valid PDF output."""
from __future__ import annotations

from reportlab.platypus import Paragraph, Table

from app.reports import exports


def _story_text(story) -> str:
    """Inspect the exact content handed to ReportLab, without a PDF extraction dependency."""
    parts = []
    for item in story:
        if isinstance(item, Paragraph):
            parts.append(item.getPlainText())
        if isinstance(item, Table):
            for row in item._cellvalues:
                for cell in row:
                    parts.append(cell.getPlainText() if isinstance(cell, Paragraph) else str(cell))
    return "\n".join(parts)


def test_audit_pdf_localized_with_google_bing_brave_and_source_evidence(monkeypatch):
    captured = {}

    def intercept(story, title):
        captured["story"] = story
        captured["title"] = title
        return b"%PDF-FAKE"

    monkeypatch.setattr(exports, "_build", intercept)
    report = exports.audit_pdf(
        "Beispiel Küche", "https://example.de/",
        {
            "id": 77, "number": 2, "finished_at": "2026-11-23 10:00",
            "score": 76,
            "stats": {
                "total_urls": 12, "indexable_pages": 8,
                "issues_by_severity": {"high": 2, "low": 1},
                "sitemap": {"url_count": 10},
            },
            "profile_scores": {
                "google": {"score": 90}, "bing": {"score": 66},
                "brave": {"score": 85}, "geo": {"score": 70},
            },
        },
        [
            {"rule_id": "redirect_temporary", "count": 2, "urls": ["https://example.de/alt"]},
            {"rule_id": "robots_googlebot_blocked", "count": 1, "urls": ["https://example.de/"]},
            {"rule_id": "robots_unreachable", "count": 1, "urls": ["https://example.de/robots.txt"]},
            {"rule_id": "sitemap_lastmod_missing", "count": 1, "urls": []},
        ],
    )
    assert report == b"%PDF-FAKE"
    txt = _story_text(captured["story"])
    assert "Technischer SEO-Auditbericht" in txt
    assert "Befunde nach Priorität" in txt
    assert "Suchmaschinen- und GEO-Profile" in txt
    assert "Zugeordnete Regeln" in txt
    assert "Bing" in txt and "Brave" in txt and "Google" in txt
    assert str(len(exports.RULES)) in txt
    assert "Zitat" in txt
    assert "Themenbezug" in txt
    assert "Quellenstand:" in txt
    assert "Primärquelle:" in txt
    assert "sitemap_lastmod_missing" in txt
    assert "https://www.bing.com/webmasters/help/" in txt
    assert "https://search.brave.com/help/" in txt
    assert "Technical SEO Audit Report" not in txt
    assert "Issues by priority" not in txt
    assert captured["title"].startswith("Technischer SEO-Auditbericht")


def test_audit_pdf_produces_actual_pdf_with_many_evidence_items():
    findings = [
        {"rule_id": rid, "count": 1, "urls": [f"https://example.de/{rid}/"]}
        for rid in exports.RULES
        if exports._evidence_for(rid)
    ]
    report = exports.audit_pdf(
        "Atelier", "https://example.de/",
        {"id": 1, "score": 82, "finished_at": "2026-11-23", "stats": {"total_urls": 10}},
        findings,
    )
    assert report.startswith(b"%PDF-")
    assert len(report) > 2000


def test_audit_pdf_without_issues_or_profile_scores_is_valid():
    report = exports.audit_pdf("Beispiel", "https://example.de", {"id": 1, "stats": {}}, [])
    assert report.startswith(b"%PDF-")


def test_competitor_pdf_labels_are_german(monkeypatch):
    captured = {}

    def intercept(story, title):
        captured["text"] = _story_text(story)
        captured["title"] = title
        return b"%PDF-FAKE"

    monkeypatch.setattr(exports, "_build", intercept)
    data = {
        "site": {"name": "Atelier", "url": "https://example.de", "profile": {"score": 70, "urls_crawled": 20}},
        "competitors": [{"name": "Konkurrent", "profile": {"score": 65, "urls_crawled": 10}}],
    }
    assert exports.competitor_pdf(data) == b"%PDF-FAKE"
    assert "SEO-Wettbewerbervergleich" in captured["text"]
    assert "Eigene Website" in captured["text"]
    assert "Gecrawlte URLs" in captured["text"]
    assert "Competitor Comparison Report" not in captured["text"]


def test_audit_pdf_endpoint_returns_pdf_for_completed_crawl(client, auth, crawled):
    response = client.get(f"/api/crawls/{crawled['crawl']['id']}/report.pdf", headers=auth)
    assert response.status_code == 200, response.text[:200] if response.status_code != 200 else ""
    assert response.content.startswith(b"%PDF-")
    assert response.headers.get("content-type") == "application/pdf"
