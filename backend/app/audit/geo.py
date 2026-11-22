"""GEO check: how well a page can be found, read and cited by AI search systems (ChatGPT, Perplexity, Claude,
Gemini, Copilot).

Everything here is measured from the live HTML, robots.txt and a few well-known files. The checks encode
widely published recommendations (crawler access, server-rendered text, structured data, answer-first
paragraphs, sources, freshness). None of them is a documented ranking factor of any AI system, so the score is a
checklist, not a prediction.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import lxml.html

from ..crawler.robots import RobotsRules
from .schema_validator import all_types

AI_CRAWLERS: list[tuple[str, str, str]] = [
    # (user agent token, operator, purpose)
    ("OAI-SearchBot", "OpenAI", "Suche in ChatGPT"),
    ("ChatGPT-User", "OpenAI", "Abruf auf Nutzeranfrage"),
    ("GPTBot", "OpenAI", "Training"),
    ("Claude-SearchBot", "Anthropic", "Suche in Claude"),
    ("Claude-User", "Anthropic", "Abruf auf Nutzeranfrage"),
    ("ClaudeBot", "Anthropic", "Training"),
    ("PerplexityBot", "Perplexity", "Suchindex"),
    ("Perplexity-User", "Perplexity", "Abruf auf Nutzeranfrage"),
    ("Google-Extended", "Google", "Gemini/KI-Nutzung"),
    ("Googlebot", "Google", "Suche und AI Overviews"),
    ("Bingbot", "Microsoft", "Bing und Copilot"),
    ("Applebot-Extended", "Apple", "Apple Intelligence"),
    ("Meta-ExternalAgent", "Meta", "Meta AI"),
    ("CCBot", "Common Crawl", "offener Datensatz"),
]
SEARCH_CRITICAL = {"OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Googlebot", "Bingbot"}
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:%|prozent|percent|€|eur|euro|cm|mm|m²|qm|kg|kwh|jahre?n?|years?)\b", re.I)
_DATE_KEYS = ("dateModified", "datePublished", "uploadDate")


def _check(cid: str, group: str, label: str, status: str, detail: str, fix: str = "", weight: int = 5) -> dict:
    return {"id": cid, "group": group, "label": label, "status": status, "detail": detail,
            "recommendation": fix if status != "pass" else "", "weight": weight}


def _nodes(items) -> list[dict]:
    out: list[dict] = []

    def walk(node, depth=0):
        if depth > 6:
            return
        if isinstance(node, dict):
            out.append(node)
            for v in node.values():
                walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node[:80]:
                walk(v, depth + 1)

    walk(items)
    return out


def _types(node: dict) -> set[str]:
    t = node.get("@type")
    return set(t) if isinstance(t, list) else {t} if isinstance(t, str) else set()


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%d"):
        try:
            d = datetime.strptime(value[:25].replace("Z", "+0000"), fmt)
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except ValueError:
        return None


def _main_tree(html: bytes):
    try:
        doc = lxml.html.fromstring(html)
    except (ValueError, lxml.etree.ParserError):
        return None
    for bad in doc.xpath("//script|//style|//noscript|//template|//svg|//nav|//header|//footer|//aside|//form"):
        bad.drop_tree()
    main = doc.xpath("//main|//article|//*[@role='main']")
    return main[0] if main else (doc.find("body") if doc.find("body") is not None else doc)


def robots_report(robots_text: str, robots_status: int | None, page_url: str) -> list[dict]:
    rules = RobotsRules(robots_text, robots_status)
    return [{"agent": ua, "operator": op, "purpose": purpose, "allowed": rules.allowed(page_url, ua),
             "search_critical": ua in SEARCH_CRITICAL} for ua, op, purpose in AI_CRAWLERS]


def analyse_geo(page_url: str, html: bytes, parsed, *, robots_text: str = "", robots_status: int | None = 404,
                llms_status: int | None = None, llms_text: str = "", ai_txt_status: int | None = None,
                headers: dict | None = None, now: datetime | None = None) -> dict:
    """``parsed`` is the crawler's ParsedPage for ``html``. Returns score, grouped checks and the crawler table."""
    now = now or datetime.now(UTC)
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    checks: list[dict] = []
    host = urlsplit(page_url).hostname or ""

    # ---------------------------------------------------------------- access
    bots = robots_report(robots_text, robots_status, page_url)
    blocked_search = [b["agent"] for b in bots if b["search_critical"] and not b["allowed"]]
    blocked_other = [b["agent"] for b in bots if not b["search_critical"] and not b["allowed"]]
    checks.append(_check("ai_search_bots", "Zugang", "Such-Crawler der KI-Dienste dürfen die Seite abrufen",
                         "fail" if blocked_search else "pass",
                         f"Gesperrt: {', '.join(blocked_search)}" if blocked_search else "OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot und Bingbot erlaubt",
                         "robots.txt so anpassen, dass die Such-Crawler die Seite abrufen dürfen; sonst kann die Seite dort nicht als Quelle erscheinen.", 15))
    if blocked_other:
        checks.append(_check("ai_training_bots", "Zugang", "Trainings- und Nutzer-Crawler", "warn",
                             f"Gesperrt: {', '.join(blocked_other)}",
                             "Bewusste Entscheidung? Training zu sperren ist legitim; Nutzer-Abrufe (ChatGPT-User, Claude-User, Perplexity-User) zu sperren verhindert, dass Antworten die Seite live lesen.", 3))
    x_robots = (headers.get("x-robots-tag") or "").lower()
    meta_robots = (parsed.meta_robots or "").lower()
    noindex = "noindex" in x_robots or "noindex" in meta_robots
    nosnippet = "nosnippet" in x_robots or "nosnippet" in meta_robots
    checks.append(_check("indexable", "Zugang", "Indexierbar und zitierbar", "fail" if noindex else "warn" if nosnippet else "pass",
                         "noindex gesetzt" if noindex else "nosnippet gesetzt" if nosnippet else "kein noindex/nosnippet",
                         "noindex/nosnippet entfernen, wenn die Seite in KI-Antworten zitiert werden soll.", 10))
    words = parsed.word_count
    checks.append(_check("server_text", "Zugang", "Inhalt ohne JavaScript lesbar", "pass" if words >= 300 else "warn" if words >= 120 else "fail",
                         f"{words} Wörter im ausgelieferten HTML",
                         "Viele KI-Crawler führen kein JavaScript aus. Hauptinhalt serverseitig ausliefern.", 10))
    llms_ok = llms_status == 200 and llms_text.lstrip().startswith("#")
    checks.append(_check("llms_txt", "Zugang", "/llms.txt vorhanden", "pass" if llms_ok else "warn",
                         "vorhanden" if llms_ok else f"nicht gefunden (HTTP {llms_status})" if llms_status != 200 else "vorhanden, aber ohne Markdown-Überschrift",
                         "Optionaler Vorschlag (llmstxt.org): kurze Markdown-Übersicht der wichtigsten Seiten. Kein offizieller Standard der großen Anbieter.", 2))
    if ai_txt_status is not None:
        checks.append(_check("ai_txt", "Zugang", "/.well-known/ai.txt", "pass" if ai_txt_status == 200 else "info",
                             "vorhanden" if ai_txt_status == 200 else "nicht vorhanden", "", 0))

    # ---------------------------------------------------------------- entity & trust
    nodes = _nodes(parsed.jsonld)
    types = set(all_types(parsed.jsonld))
    org = [n for n in nodes if _types(n) & {"Organization", "LocalBusiness", "HomeAndConstructionBusiness", "Corporation",
                                            "ProfessionalService", "Store", "Restaurant", "Person"} and (n.get("name") or n.get("sameAs"))]
    same_as = sorted({s for n in org for s in ([n["sameAs"]] if isinstance(n.get("sameAs"), str) else n.get("sameAs") or [])
                      if isinstance(s, str)})
    checks.append(_check("entity", "Entität", "Organisation/Person als strukturierte Daten", "pass" if org else "fail",
                         f"{len(org)} Knoten" if org else "kein Organization/LocalBusiness/Person-Knoten",
                         "Organization bzw. LocalBusiness mit Name, Adresse und Logo auszeichnen, damit die Marke als Entität erkannt wird.", 8))
    checks.append(_check("same_as", "Entität", "sameAs-Profile verknüpft", "pass" if len(same_as) >= 2 else "warn",
                         f"{len(same_as)} Profil(e)", "Offizielle Profile (LinkedIn, Wikidata, Branchenverzeichnisse, Social) per sameAs verknüpfen.", 4))
    authors = [n.get("author") for n in nodes if n.get("author")]
    meta_author = None
    tree = _main_tree(html)
    try:
        full = lxml.html.fromstring(html)
        meta_author = (full.xpath("string(//meta[@name='author']/@content)") or "").strip() or None
        time_values = [t.get("datetime") for t in full.xpath("//time[@datetime]")]
        og_mod = (full.xpath("string(//meta[@property='article:modified_time']/@content)") or "").strip()
    except (ValueError, lxml.etree.ParserError):
        time_values, og_mod = [], ""
    checks.append(_check("author", "Entität", "Autor erkennbar", "pass" if authors or meta_author else "warn",
                         "author in strukturierten Daten" if authors else f"meta author: {meta_author}" if meta_author else "kein Autor",
                         "Autor mit Name (und Profilseite) angeben; Expertise ist ein häufig genanntes Vertrauenssignal.", 4))
    dates = [d for d in (_parse_date(str(n.get(k))) for n in nodes for k in _DATE_KEYS if n.get(k)) if d]
    dates += [d for d in (_parse_date(v) for v in [og_mod, *time_values] if v) if d]
    newest = max(dates) if dates else None
    age_days = (now - newest).days if newest else None
    checks.append(_check("freshness", "Entität", "Aktualität ausgewiesen",
                         "pass" if age_days is not None and age_days <= 365 else "warn",
                         f"zuletzt geändert vor {age_days} Tagen ({newest.date().isoformat()})" if newest else "kein Datum gefunden",
                         "dateModified (Schema) und ein sichtbares Aktualisierungsdatum pflegen; KI-Antworten bevorzugen aktuelle Quellen.", 5))

    # ---------------------------------------------------------------- content structure
    paragraphs, lists, tables, questions_h = [], 0, 0, 0
    first_answer_words = None
    if tree is not None:
        paragraphs = [re.sub(r"\s+", " ", p.text_content()).strip() for p in tree.iter("p")]
        paragraphs = [p for p in paragraphs if len(p.split()) >= 8]
        lists = len(tree.xpath(".//ul[count(li)>=2]|.//ol[count(li)>=2]"))
        tables = len(tree.xpath(".//table"))
        if paragraphs:
            first_answer_words = len(paragraphs[0].split())
    headings = parsed.headings or []
    h2plus = [h for h in headings if h["level"] in (2, 3)]
    questions_h = sum(1 for h in h2plus if h["text"].strip().endswith("?"))
    h1 = [h for h in headings if h["level"] == 1]
    checks.append(_check("h1", "Struktur", "Genau eine H1", "pass" if len(h1) == 1 else "warn", f"{len(h1)} H1", "Eine H1, die das Thema klar benennt.", 3))
    checks.append(_check("answer_first", "Struktur", "Direkte Antwort am Anfang",
                         "pass" if first_answer_words and 20 <= first_answer_words <= 90 else "warn",
                         f"erster Absatz: {first_answer_words} Wörter" if first_answer_words else "kein Absatz gefunden",
                         "Den ersten Absatz als eigenständige Antwort in 40–60 Wörtern formulieren; solche Passagen lassen sich leicht zitieren.", 8))
    checks.append(_check("subheadings", "Struktur", "Gliederung mit Zwischenüberschriften",
                         "pass" if len(h2plus) >= max(2, words // 450) else "warn",
                         f"{len(h2plus)} H2/H3 bei {words} Wörtern", "Abschnitte mit aussagekräftigen H2/H3 gliedern (etwa alle 300 Wörter).", 5))
    checks.append(_check("question_headings", "Struktur", "Überschriften als Fragen", "pass" if questions_h >= 2 else "warn",
                         f"{questions_h} Frage-Überschrift(en)", "Einige H2/H3 als echte Nutzerfragen formulieren, direkt darunter die Antwort.", 4))
    checks.append(_check("lists_tables", "Struktur", "Listen oder Tabellen", "pass" if lists + tables >= 1 else "warn",
                         f"{lists} Liste(n), {tables} Tabelle(n)", "Schritte, Vergleiche und Kennzahlen als Liste oder Tabelle aufbereiten.", 4))
    long_paras = sum(1 for p in paragraphs if len(p.split()) > 120)
    checks.append(_check("paragraph_length", "Struktur", "Kurze, eigenständige Absätze", "pass" if long_paras == 0 else "warn",
                         f"{long_paras} Absatz/Absätze über 120 Wörter", "Lange Absätze teilen; jeder Absatz sollte für sich verständlich sein.", 3))
    faq = bool(types & {"FAQPage", "QAPage", "HowTo"})
    checks.append(_check("faq_schema", "Struktur", "FAQ/HowTo-Auszeichnung", "pass" if faq else "info",
                         "vorhanden" if faq else "nicht vorhanden",
                         "Wenn die Seite echte Fragen beantwortet: FAQPage auszeichnen (Google zeigt sie kaum noch als Rich Result, Maschinen lesen sie trotzdem).", 2))

    # ---------------------------------------------------------------- evidence
    text = parsed.text or ""
    figures = len(_NUMBER.findall(text))
    checks.append(_check("figures", "Belege", "Konkrete Zahlen und Maße", "pass" if figures >= 3 else "warn",
                         f"{figures} Zahl(en) mit Einheit", "Konkrete Werte (Maße, Prozent, Zeiträume) nennen; sie machen Aussagen überprüfbar.", 4))
    external = [lk for lk in parsed.links if (urlsplit(lk["url"]).hostname or "") not in ("", host)
                and not (urlsplit(lk["url"]).hostname or "").endswith("." + host)]
    ext_hosts = sorted({urlsplit(lk["url"]).hostname for lk in external})
    checks.append(_check("sources", "Belege", "Externe Quellen verlinkt", "pass" if len(ext_hosts) >= 2 else "warn",
                         f"{len(ext_hosts)} externe Domain(s)", "Aussagen mit Herstellerangaben, Normen oder Studien belegen und verlinken.", 4))
    checks.append(_check("meta_description", "Belege", "Meta-Description vorhanden", "pass" if parsed.meta_description else "warn",
                         f"{len(parsed.meta_description or '')} Zeichen", "Prägnante Zusammenfassung der Seite als Meta-Description.", 2))

    scored = [c for c in checks if c["status"] in ("pass", "warn", "fail") and c["weight"]]
    total = sum(c["weight"] for c in scored)
    earned = sum(c["weight"] * (1.0 if c["status"] == "pass" else 0.5 if c["status"] == "warn" else 0.0) for c in scored)
    return {
        "url": page_url, "score": round(100 * earned / total) if total else 0,
        "checks": checks, "crawlers": bots,
        "stats": {"words": words, "paragraphs": len(paragraphs), "lists": lists, "tables": tables, "question_headings": questions_h,
                  "external_domains": ext_hosts[:30], "schema_types": sorted(types), "same_as": same_as[:20],
                  "newest_date": newest.isoformat() if newest else None},
        "notes": ["Checkliste nach veröffentlichten Empfehlungen; kein KI-Anbieter dokumentiert diese Punkte als Rankingfaktoren.",
                  "Gemessen am ausgelieferten HTML ohne JavaScript, wie die meisten KI-Crawler es sehen."],
    }
