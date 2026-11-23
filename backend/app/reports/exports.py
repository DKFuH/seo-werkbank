"""CSV / XLSX / PDF export builders."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..audit.rules import CLASSIFICATION_LABELS, PROFILE_RULE_IDS, RULES, SEVERITIES, classify_rule, rule_profiles
from ..audit.engine_guidance import engine_guidance
from ..config import APP_NAME

_FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: Any) -> Any:
    """Neutralise spreadsheet formula injection: crawled text must never be executed by Excel/Sheets."""
    if isinstance(value, dict | list):
        value = json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, str):
        if value.startswith(_FORMULA_PREFIX):
            value = "'" + value
        return value[:32000]
    return value


def to_csv(rows: list[dict], columns: list[str] | None = None) -> bytes:
    columns = columns or (list(rows[0].keys()) if rows else [])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([safe_cell(r.get(c)) for c in columns])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def to_xlsx(sheets: dict[str, list[dict]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    head_fill = PatternFill("solid", fgColor="1F2937")
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name[:31])
        if not rows:
            ws.append(["No data"])
            continue
        columns = list(rows[0].keys())
        ws.append(columns)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = head_fill
            cell.alignment = Alignment(vertical="center")
        for r in rows:
            ws.append([safe_cell(r.get(c)) for c in columns])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, col in enumerate(columns, 1):
            width = max([len(str(col))] + [len(str(r.get(col) or "")) for r in rows[:200]])
            ws.column_dimensions[get_column_letter(i)].width = max(10, min(70, width + 2))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- PDF
_SEV_HEX = {"critical": "#B91C1C", "high": "#C2410C", "medium": "#A16207", "low": "#475569"}
_styles = getSampleStyleSheet()
_H1 = ParagraphStyle("H1x", parent=_styles["Title"], fontSize=22, leading=26, alignment=0, spaceAfter=6)
_H2 = ParagraphStyle("H2x", parent=_styles["Heading2"], fontSize=14, leading=18, spaceBefore=12, spaceAfter=6)
_H3 = ParagraphStyle("H3x", parent=_styles["Heading3"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=3)
_P = ParagraphStyle("Px", parent=_styles["BodyText"], fontSize=9.5, leading=13)
_SMALL = ParagraphStyle("Sx", parent=_P, fontSize=8, leading=10.5, textColor=colors.HexColor("#475569"))
_CELL = ParagraphStyle("Cx", parent=_P, fontSize=8.5, leading=11)


def _p(text: Any, style=_P) -> Paragraph:
    return Paragraph(escape(str(text if text is not None else "")), style)


def _table(data: list[list], widths: list[float], header: bool = True) -> Table:
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(18 * mm, 10 * mm, f"Erstellt mit {APP_NAME}")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def _build(story: list, title: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title=title)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


_BASIS = CLASSIFICATION_LABELS
_SCHWERE = {"critical": "Kritisch", "high": "Hoch", "medium": "Mittel", "low": "Niedrig"}
_PROFILE_NAMEN = {"google": "Google", "bing": "Bing", "brave": "Brave", "geo": "GEO"}
_EVIDENZ = {"quoted": "Zitat", "topic": "Themenbezug"}


def _evidence_for(rule_id: str) -> list[tuple[str, dict]]:
    """Search-engine evidence only where a public guidance mapping exists."""
    evidence = engine_guidance(rule_id)
    return [(name, evidence[name]) for name in ("bing", "brave")
            if evidence[name].get("status") == "related_guidance"]


def audit_pdf(site_name: str, site_url: str, crawl: dict, issue_groups: list[dict]) -> bytes:
    """German audit PDF: scores, all triggered findings and per-engine source evidence.

    Crawl input is the stored completed snapshot; no live API lookup or claim
    of Google/Bing/Brave approval is made.
    """
    stats = crawl.get("stats") or {}
    sev = stats.get("issues_by_severity") or {}
    W = A4[0] - 36 * mm
    crawl_number = crawl.get("number") or crawl.get("id")
    story: list = [
        _p("Technischer SEO-Auditbericht", _H1),
        _p(f"{site_name} - {site_url}"),
        _p(f"Crawl {crawl_number} vom {crawl.get('finished_at') or 'unbekannt'} | "
           f"Bericht erstellt am {datetime.now():%d.%m.%Y %H:%M}", _SMALL),
        Spacer(1, 8),
    ]
    score = crawl.get("score")
    verdict = ("kein Wert" if score is None else "Gut" if score >= 85
               else "Prüfbedarf" if score >= 65 else "Hoher Prüfbedarf")
    story.append(_table([
        ["SEO-Score", "URLs erfasst", "Indexierbar", "Kritisch", "Hoch", "Mittel", "Niedrig"],
        [f"{score if score is not None else '-'} / 100 ({verdict})",
         stats.get("total_urls", 0), stats.get("indexable_pages", 0),
         sev.get("critical", 0), sev.get("high", 0), sev.get("medium", 0), sev.get("low", 0)],
    ], [W * 0.26, W * 0.14, W * 0.16, W * 0.11, W * 0.11, W * 0.11, W * 0.11]))
    story += [Spacer(1, 6), _p(
        "Der SEO-Score ist eine Kennzahl der Werkbank, kein offizieller Suchmaschinenwert. "
        "Jede Seite startet bei 100 Punkten; kritische/hohe/mittlere/niedrige Befunde "
        "kosten 25/10/4/1 Punkte. Für websiteweite Befunde werden zusätzlich "
        "10/5/2/0,5 Punkte vom durchschnittlichen Seitenscore abgezogen. "
        "Prioritäten und Ursachen immer am konkreten Befund prüfen.", _SMALL)]
    if stats.get("limit_reached"):
        story.append(_p("Hinweis: Das URL-Limit wurde erreicht. Der Crawl deckt möglicherweise nicht alle Seiten ab.", _SMALL))

    profiles = crawl.get("profile_scores") or stats.get("profile_scores") or {}
    profile_ids = ("google", "bing", "brave", "geo")
    story.append(_p("Suchmaschinen- und GEO-Profile", _H2))
    profile_rows = [
        ["Kennzahl", "Google", "Bing", "Brave", "GEO"],
        ["Profil-Score / 100"] + [
            str((profiles.get(key) or {}).get("score"))
            if (profiles.get(key) or {}).get("score") is not None else "-"
            for key in profile_ids
        ],
        ["Zugeordnete Regeln"] + [str(len(PROFILE_RULE_IDS[key])) for key in profile_ids],
    ]
    story.append(_table(profile_rows, [W * 0.2] * 5))
    story.append(_p(
        "Der Katalog enthält " + str(len(RULES)) + " Audit-Regeln. "
        "Zugeordnete Regeln sind nicht gleichbedeutend mit offiziellen Vorgaben. "
        "Profil-Scores nutzen dieselben Punktabzüge, aber unterschiedliche Regelsätze "
        "und sind weder direkt miteinander vergleichbar noch Rankingprognosen. "
        "Bei Bing/Brave fließen derzeit auch Regeln mit bloßem Themenbezug in den Score ein.", _SMALL))

    story.append(_p("Crawl-Überblick", _H2))
    sc = stats.get("status_classes") or {}
    links = stats.get("links") or {}
    redirects = stats.get("redirects") or {}
    story.append(_table([
        ["Kennzahl", "Wert", "Kennzahl", "Wert"],
        ["HTML-Seiten (200)", stats.get("html_pages", 0), "Nicht indexierbar", stats.get("non_indexable_pages", 0)],
        ["2xx / 3xx", f"{sc.get('2xx', 0)} / {sc.get('3xx', 0)}", "4xx / 5xx / Fehler", f"{sc.get('4xx', 0)} / {sc.get('5xx', 0)} / {sc.get('error', 0)}"],
        ["Interne Links", links.get("internal", 0), "Defekte interne Links", links.get("broken_internal", 0)],
        ["Externe Links", links.get("external", 0), "Defekte externe Links", links.get("broken_external", 0)],
        ["Weiterleitungen", redirects.get("total", 0), "Ketten / Schleifen", f"{redirects.get('chains', 0)} / {redirects.get('loops', 0)}"],
        ["Wörter je Seite (Ø)", stats.get("avg_word_count", 0), "Antwortzeit (Ø)", f"{stats.get('avg_response_ms', 0)} ms"],
        ["Sitemap-URLs", (stats.get("sitemap") or {}).get("url_count", 0),
         "Seiten mit strukturierten Daten", (stats.get("schema") or {}).get("pages_with_schema", 0)],
    ], [W * 0.3, W * 0.2, W * 0.3, W * 0.2]))

    order = {s: i for i, s in enumerate(SEVERITIES)}
    groups = sorted((g for g in issue_groups if g.get("rule_id") in RULES),
                    key=lambda g: (order[RULES[g["rule_id"]].severity], -g["count"], g["rule_id"]))
    story.append(_p("Befunde nach Priorität", _H2))
    story.append(_p(
        "Die folgende Übersicht enthält alle im Crawl ausgelösten Regelarten, "
        "nicht sämtliche Regeln des Katalogs. Die Einordnung unterscheidet technische "
        "Probleme, Google-Empfehlungen, SEO-Heuristiken und GEO-Hypothesen.", _SMALL))
    if not groups:
        story.append(_p("In diesem Crawl wurden keine Audit-Befunde festgestellt."))
    else:
        issue_rows = [["Priorität", "Befund", "Einordnung und Profile", "URLs", "Empfohlene Maßnahme"]]
        for g in groups:
            rule = RULES[g["rule_id"]]
            basis = _BASIS[classify_rule(rule.id)]
            profiles_for_rule = ", ".join(_PROFILE_NAMEN[k] for k in rule_profiles(rule.id))
            evidences = _evidence_for(rule.id)
            proof = ", ".join(f"{_PROFILE_NAMEN[engine]}: {_EVIDENZ.get(data.get('evidence'), 'Hinweis')}"
                              for engine, data in evidences)
            annotation = "; ".join(part for part in (basis, profiles_for_rule, proof) if part)
            issue_rows.append([
                Paragraph(f'<font color="{_SEV_HEX[rule.severity]}"><b>{_SCHWERE[rule.severity]}</b></font>', _CELL),
                _p(rule.title, _CELL), _p(annotation, _CELL), str(g["count"]), _p(rule.fix, _CELL),
            ])
        story.append(_table(issue_rows, [W * 0.11, W * 0.24, W * 0.22, W * 0.08, W * 0.35]))

    high = [g for g in groups if RULES[g["rule_id"]].severity in ("critical", "high")]
    if high:
        story += [PageBreak(), _p("Kritische und hohe Befunde im Detail", _H2)]
        for g in high:
            rule = RULES[g["rule_id"]]
            story.append(_p(f"{rule.title} ({g['count']} betroffene URLs)", _H3))
            story.append(_p(rule.description))
            story.append(Paragraph(f"<b>Maßnahme:</b> {escape(rule.fix)}", _P))
            story.append(_p("Regelkennung: " + rule.id + " | Einordnung: " + _BASIS[classify_rule(rule.id)], _SMALL))
            for u in (g.get("urls") or [])[:15]:
                story.append(_p(u, _SMALL))
            if g["count"] > 15:
                story.append(_p(
                    f"Weitere {g['count'] - 15} Treffer: vollständige Liste im CSV-/Excel-Export.", _SMALL))

    evidenced_groups = [(g, _evidence_for(g["rule_id"])) for g in groups if _evidence_for(g["rule_id"])]
    if evidenced_groups:
        story += [PageBreak(), _p("Bing-/Brave-Quellen zu ausgelösten Befunden", _H2)]
        story.append(_p(
            "Zitat (quoted): Der Richtliniensatz beschreibt die konkrete Prüfung. "
            "Themenbezug (topic): Die Quelle behandelt nur das Themenfeld und ist "
            "kein Beleg für die einzelne Regel, den Schweregrad oder einen Schwellenwert. "
            "Quellenstand und Abschnitte stammen aus dem dokumentierten Regelkatalog.", _SMALL))
        for g, found in evidenced_groups:
            rule = RULES[g["rule_id"]]
            story.append(_p(f"{rule.title} [{rule.id}]", _H3))
            for engine, evidence in found:
                label = _EVIDENZ.get(evidence.get("evidence"), "Nicht bewertet")
                story.append(_p(
                    f"{_PROFILE_NAMEN[engine]} - {label} | Abschnitt: {evidence.get('section') or 'nicht angegeben'}", _P))
                if evidence.get("quote"):
                    story.append(_p("Originalzitat: " + evidence["quote"], _SMALL))
                else:
                    story.append(_p("Nur Themenbezug; kein passender wörtlicher Satz zur konkreten Prüfung hinterlegt.", _SMALL))
                story.append(_p("Quellenstand: " + str(evidence.get("source_status") or "unbekannt"), _SMALL))
                story.append(_p("Primärquelle: " + str(evidence.get("documentation") or "-"), _SMALL))

    story.append(Spacer(1, 8))
    story.append(_p(
        "Methodik: Datenstand ist der abgeschlossene Crawl. Ein Befund ist nicht "
        "automatisch ein Verstoß gegen eine Suchmaschinenrichtlinie. "
        "Auch ein Ergebnis ohne Befunde garantiert keine Indexierung oder Sichtbarkeit. "
        "Mehr: docs/SEARCH_ENGINE_RULES.md im Repository.", _SMALL))
    return _build(story, f"Technischer SEO-Auditbericht - {site_name}")


def competitor_pdf(comparison: dict) -> bytes:
    """German competitor comparison, without manufacturing external measurements."""
    site = comparison["site"]
    W = A4[0] - 36 * mm
    story: list = [
        _p("SEO-Wettbewerbervergleich", _H1),
        _p(f"{site['name']} - {site['url']}"),
        _p(f"Bericht erstellt am {datetime.now():%d.%m.%Y %H:%M}", _SMALL),
        Spacer(1, 8),
    ]
    cols = [
        ("SEO-Score", "score"), ("Gecrawlte URLs", "urls_crawled"),
        ("Indexierbare Seiten", "indexable_pages"), ("Sitemap-URLs", "sitemap_urls"),
        ("Wörter je Seite (Ø)", "avg_word_count"),
        ("Titellänge (Ø)", "avg_title_length"),
        ("Beschreibungslänge (Ø)", "avg_description_length"),
        ("Seiten ohne Beschreibung", "pages_missing_description"),
        ("Ausgehende interne Links (Ø)", "avg_internal_links_out"),
        ("H2 je Seite (Ø)", "avg_h2_per_page"),
        ("Antwortzeit (Ø, ms)", "avg_response_ms"),
    ]
    entities = [("Eigene Website", site.get("profile"))] + [
        (competitor["name"], competitor.get("profile")) for competitor in comparison["competitors"]
    ]
    entities = [(name, profile) for name, profile in entities if profile][:5]
    if len(entities) < 2:
        story.append(_p("Für den Vergleich müssen die eigene Website und mindestens ein Wettbewerber gecrawlt werden."))
        return _build(story, "SEO-Wettbewerbervergleich")
    rows = [["Kennzahl (gemessen / berechnet)"] + [_p(name, _CELL) for name, _ in entities]]
    for label, key in cols:
        rows.append([_p(label, _CELL)] + [str(profile.get(key, "-")) for _, profile in entities])
    rows.append([_p("Kritische / hohe Befunde", _CELL)] + [
        f"{(profile.get('issues_by_severity') or {}).get('critical', 0)} / "
        f"{(profile.get('issues_by_severity') or {}).get('high', 0)}"
        for _, profile in entities
    ])
    cw = (W - W * 0.28) / len(entities)
    story.append(_table(rows, [W * 0.28] + [cw] * len(entities)))
    for competitor in comparison["competitors"]:
        profile = competitor.get("profile") or {}
        overlap = profile.get("keyword_overlap")
        if not overlap:
            continue
        story.append(_p(f"{competitor['name']}: Themenlücken und Chancen", _H2))
        story.append(_p(
            f"Gemeinsame Begriffe in Titel/H1: {overlap['shared_terms']} "
            f"(Überschneidung {round(overlap['overlap_share'] * 100)} %). "
            f"{overlap['method']}", _SMALL))
        gaps = ", ".join(g["term"] for g in overlap["gaps"][:40]) or "keine ermittelt"
        story.append(Paragraph(f"<b>Themen, die Wettbewerber behandeln:</b> {escape(gaps)}", _P))
        opportunities = profile.get("content_opportunities") or []
        if opportunities:
            opportunity_rows = [["Wettbewerberseite", "Fehlende Themen"]] + [
                [_p(f"{item['title']} - {item['url']}", _CELL),
                 _p(", ".join(item["topics_you_lack"]), _CELL)]
                for item in opportunities[:12]
            ]
            story += [Spacer(1, 4), _table(opportunity_rows, [W * 0.6, W * 0.4])]
    for note in comparison.get("notes", []):
        story.append(_p("Hinweis: " + str(note), _SMALL))
    story.append(_p(
        "Vergleichswerte stammen aus den gespeicherten Crawls. "
        "Unterschiedliche Crawl-Zeitpunkte oder Limits schränken die Vergleichbarkeit ein.", _SMALL))
    return _build(story, "SEO-Wettbewerbervergleich")
