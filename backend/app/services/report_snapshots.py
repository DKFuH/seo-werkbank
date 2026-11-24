"""Freeze site metrics into immutable report payloads; render exclusively stored data."""
from __future__ import annotations

import io
from datetime import timedelta
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Crawl, GscRow, ReportSnapshot, Site, utcnow


def capture(db: Session, site: Site, title: str = "SEO-Monatsbericht",
            origin: str = "manual", days: int = 28) -> ReportSnapshot:
    """No writes to external systems; GSC and crawl numbers are frozen at capture time."""
    crawl = db.scalar(select(Crawl).where(Crawl.site_id == site.id, Crawl.status == "completed",
                                          Crawl.competitor_id.is_(None)).order_by(Crawl.id.desc()))
    if crawl is None:
        raise ValueError("Abgeschlossener Crawl erforderlich")
    sources = {src for (src,) in db.execute(select(GscRow.source).where(
        GscRow.site_id == site.id, GscRow.dataset == "query_page").distinct())}
    source = "api" if "api" in sources else "csv" if "csv" in sources else None
    gsc = {"source": source, "start": None, "end": None, "clicks": None, "impressions": None}
    if source:
        latest = db.scalar(select(func.max(GscRow.day)).where(
            GscRow.site_id == site.id, GscRow.dataset == "query_page", GscRow.source == source))
        if latest:
            first = latest - timedelta(days=days - 1)
            clicks, impressions = db.execute(select(func.sum(GscRow.clicks), func.sum(GscRow.impressions)).where(
                GscRow.site_id == site.id, GscRow.dataset == "query_page", GscRow.source == source,
                GscRow.day.between(first, latest))).one()
            gsc.update(start=first.isoformat(), end=latest.isoformat(),
                       clicks=round(clicks or 0), impressions=round(impressions or 0))
    stats = crawl.stats or {}
    payload = {
        "site": {"name": site.name, "url": site.url},
        "crawl": {"id": crawl.id, "completed_at": crawl.finished_at.isoformat() if crawl.finished_at else None,
                  "score": crawl.score, "pages_crawled": crawl.pages_crawled,
                  "indexable_pages": stats.get("indexable_pages"),
                  "issues_by_severity": dict(stats.get("issues_by_severity") or {})},
        "gsc": gsc, "generated_at": utcnow().isoformat(),
        "method": "Gefrorener Datenstand aus Crawl und GSC-Query-URL-Zeilen; "
                  "diese GSC-Impressionen können bei mehreren URLs je Query überlappen. "
                  "Kein Suchvolumen, keine ursächliche Wirkungsmessung.",
    }
    row = ReportSnapshot(site_id=site.id, title=title[:200], origin=origin, payload=payload)
    db.add(row)
    db.flush()
    return row


def render_html(snapshot: ReportSnapshot) -> str:
    payload = snapshot.payload or {}
    site, crawl, gsc = payload["site"], payload["crawl"], payload["gsc"]
    def val(value):
        return escape(str(value)) if value is not None else "–"
    fields = [
        ("Website", site["name"]), ("URL", site["url"]),
        ("Crawl", crawl["id"]), ("Stand", crawl["completed_at"]),
        ("SEO-Score", crawl["score"]), ("Crawl-URLs", crawl["pages_crawled"]),
        ("Indexierbar", crawl["indexable_pages"]),
        ("GSC-Quelle", gsc["source"]), ("GSC-Zeitraum", f"{gsc['start']} bis {gsc['end']}"),
        ("GSC-Klicks", gsc["clicks"]), ("GSC-Impressionen", gsc["impressions"]),
    ]
    rows = "".join(f"<tr><th>{val(k)}</th><td>{val(v)}</td></tr>" for k, v in fields)
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<title>' + val(snapshot.title) + '</title><style>'
            'body{font:16px system-ui;max-width:800px;margin:2rem auto;padding:1rem;}'
            'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:9px;text-align:left}'
            'th{background:#eee;width:45%}small{color:#666}</style></head><body>'
            '<h1>' + val(snapshot.title) + '</h1><small>Erstellt: ' + val(payload["generated_at"]) +
            ' · Snapshot #' + str(snapshot.id) + '</small><table>' + rows + '</table><p>' +
            val(payload["method"]) + '</p></body></html>')


def render_pdf(snapshot: ReportSnapshot) -> bytes:
    """PDF is built from immutable payload, not a newer crawl or changed GSC."""
    data = snapshot.payload
    site, crawl, gsc = data["site"], data["crawl"], data["gsc"]
    buf = io.BytesIO()
    document = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm,
                                 rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    style = getSampleStyleSheet()
    def para(value):
        return Paragraph(escape(str(value if value is not None else "–")), style["BodyText"])
    rows = [
        [para("Website"), para(site["name"])],
        [para("URL"), para(site["url"])],
        [para("Crawl-Nummer"), para(crawl["id"])],
        [para("Score"), para(crawl["score"])],
        [para("Crawl-URLs"), para(crawl["pages_crawled"])],
        [para("Indexierbare Seiten"), para(crawl["indexable_pages"])],
        [para("GSC-Klicks"), para(gsc["clicks"])],
        [para("GSC-Impressionen"), para(gsc["impressions"])],
        [para("GSC-Quelle"), para(gsc["source"])],
        [para("GSC-Zeitraum"), para(f"{gsc['start']} bis {gsc['end']}")],
    ]
    table = Table(rows, colWidths=[57 * mm, 112 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    document.build([
        Paragraph(escape(snapshot.title), style["Title"]),
        Paragraph("Gespeicherter Datenstand: " + escape(data["generated_at"]), style["Normal"]),
        Spacer(1, 10), table, Spacer(1, 10), para(data["method"]),
    ])
    return buf.getvalue()
