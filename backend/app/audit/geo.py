"""GEO check: how well a page can be found, read and cited by AI search systems (ChatGPT, Perplexity, Claude,
Gemini, Copilot).

Everything here is measured from the live HTML, robots.txt and a few well-known files. The checks encode
widely published recommendations (crawler access, server-rendered text, structured data, answer-first
paragraphs, sources, freshness). None of them is a documented ranking factor of any AI system, so the score is a
checklist, not a prediction.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
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
    ("Applebot", "Apple", "Siri und Spotlight-Suche"),
    ("Applebot-Extended", "Apple", "Apple Intelligence (Training)"),
    ("DuckAssistBot", "DuckDuckGo", "DuckAssist-Antworten"),
    ("Amazonbot", "Amazon", "Alexa und Rufus"),
    ("Meta-ExternalAgent", "Meta", "Meta AI"),
    ("CCBot", "Common Crawl", "offener Datensatz"),
]
SEARCH_CRITICAL = {"OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Googlebot", "Bingbot", "Applebot"}
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


def _faq_questions(tree) -> int:
    """Questions in FAQ markup (details/summary, definition lists, H4) that are not H2/H3."""
    if tree is None:
        return 0
    return sum(1 for el in tree.xpath(".//summary|.//dt|.//h4") if el.text_content().strip().endswith("?"))


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
                headers: dict | None = None, now: datetime | None = None, llms_full_status: int | None = None) -> dict:
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
                         f"Gesperrt: {', '.join(blocked_search)}" if blocked_search else "OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, Bingbot und Applebot erlaubt",
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
    full_doc = _doc(html)
    limits = snippet_limits(x_robots, meta_robots, full_doc)
    limit_issues = [p for p in snippet_problems(limits) if not p.startswith("nosnippet")]
    if limits["max_image_preview"] == "none":
        limit_issues.append("max-image-preview:none (keine Bildvorschau)")
    checks.append(_check("snippet_limits", "Zugang", "Textauszüge nicht eingeschränkt", "warn" if limit_issues else "pass",
                         "; ".join(limit_issues) if limit_issues else "kein max-snippet unter 50, kaum data-nosnippet",
                         "Snippet-Grenzen lockern: max-snippet:-1 oder mindestens 50 Zeichen, data-nosnippet nur für Nebensachen.", 4))
    words = parsed.word_count
    checks.append(_check("server_text", "Zugang", "Inhalt ohne JavaScript lesbar", "pass" if words >= 300 else "warn" if words >= 120 else "fail",
                         f"{words} Wörter im ausgelieferten HTML",
                         "Viele KI-Crawler führen kein JavaScript aus. Hauptinhalt serverseitig ausliefern.", 10))
    robots_signals = robots_ai_signals(RobotsRules(robots_text, robots_status))
    signal_issues = list(robots_signals["restrictive"])
    if robots_signals["cloudflare_blocks"]:
        signal_issues.insert(0, "Cloudflare-verwalteter Abschnitt sperrt " + ", ".join(robots_signals["cloudflare_blocks"]))
    signal_info = [f"Content-Signal {', '.join(f'{k}={v}' for k, v in c['signals'].items())}" for c in robots_signals["content_signals"]]
    if robots_signals["cloudflare_managed"] or robots_signals["content_signals"]:
        checks.append(_check("robots_signals", "Zugang", "KI-Signale in robots.txt", "warn" if signal_issues else "pass",
                             "; ".join(signal_issues or signal_info) or "Cloudflare-Abschnitt ohne KI-Sperren",
                             "Cloudflare: unter Security → Bots bzw. AI Crawl Control prüfen, ob die Sperren gewollt sind. "
                             "Content-Signal search=no oder ai-input=no hält die Seite aus KI-Antworten heraus.", 4))
    meta_ai = ai_meta(_doc(html), headers.get("x-robots-tag", ""), parsed.meta_robots or "")
    meta_issues = ai_meta_problems(meta_ai)
    checks.append(_check("ai_meta", "Zugang", "Keine KI-Sperren per Meta-Tag oder Header",
                         "fail" if meta_ai["blocked_search"] else "warn" if meta_issues else "pass",
                         "; ".join(meta_issues) if meta_issues else "kein noai/noimageai, keine Crawler-spezifischen Sperren",
                         "Crawler-spezifische noindex/none-Angaben (z. B. <meta name=\"GPTBot\" content=\"noindex\">) entfernen, wenn "
                         "die Seite dort erscheinen soll. noai/noimageai sind kein Standard, zeigen aber eine Absicht an.", 6))
    llms_info = llms_validate(llms_text) if llms_status == 200 else None
    llms_ok = bool(llms_info) and not llms_info["issues"]
    llms_detail = ("vollständig: Titel, Kurzbeschreibung, " + f"{llms_info['sections']} Abschnitt(e), {llms_info['links']} Link(s)") if llms_ok         else "; ".join(llms_info["issues"]) if llms_info else f"nicht gefunden (HTTP {llms_status})"
    if llms_full_status is not None:
        llms_detail += " · /llms-full.txt " + ("vorhanden" if llms_full_status == 200 else "nicht vorhanden")
    checks.append(_check("llms_txt", "Zugang", "/llms.txt vorhanden und gegliedert", "pass" if llms_ok else "warn", llms_detail,
                         "Optionaler Vorschlag (llmstxt.org): '# Name', '> Kurzbeschreibung', '## Abschnitte' mit "
                         "'- [Titel](URL): Beschreibung'. Kein offizieller Standard der großen Anbieter. "
                         "Einen Entwurf aus dem letzten Crawl erzeugt die Karte „llms.txt-Entwurf“.", 2))
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
            answer = next((p for p in paragraphs[:3] if 20 <= len(p.split()) <= 90), paragraphs[0])
            first_answer_words = len(answer.split())
    headings = parsed.headings or []
    h2plus = [h for h in headings if h["level"] in (2, 3)]
    questions_h = sum(1 for h in h2plus if h["text"].strip().endswith("?"))
    h1 = [h for h in headings if h["level"] == 1]
    checks.append(_check("h1", "Struktur", "Genau eine H1", "pass" if len(h1) == 1 else "warn", f"{len(h1)} H1", "Eine H1, die das Thema klar benennt.", 3))
    checks.append(_check("answer_first", "Struktur", "Direkte Antwort am Anfang",
                         "pass" if first_answer_words and 20 <= first_answer_words <= 90 else "warn",
                         f"Antwortabsatz: {first_answer_words} Wörter" if first_answer_words else "kein Absatz gefunden",
                         "Den ersten Absatz als eigenständige Antwort in 40–60 Wörtern formulieren; solche Passagen lassen sich leicht zitieren.", 8))
    checks.append(_check("subheadings", "Struktur", "Gliederung mit Zwischenüberschriften",
                         "pass" if len(h2plus) >= max(2, words // 450) else "warn",
                         f"{len(h2plus)} H2/H3 bei {words} Wörtern", "Abschnitte mit aussagekräftigen H2/H3 gliedern (etwa alle 300 Wörter).", 5))
    faq_q = _faq_questions(tree)
    checks.append(_check("question_headings", "Struktur", "Fragen als Überschrift oder FAQ", "pass" if questions_h + faq_q >= 2 else "warn",
                         f"{questions_h} Frage-Überschrift(en), {faq_q} FAQ-Frage(n)", "Einige H2/H3 als echte Nutzerfragen formulieren, direkt darunter die Antwort.", 4))
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

    # ---------------------------------------------------------------- integrity
    injections = hidden_instructions(full_doc)
    checks.append(_check("hidden_instructions", "Integrität", "Keine versteckten Anweisungen an KI-Systeme",
                         "fail" if injections else "pass",
                         "; ".join(f"{i['where']}: „{i['sample']}“" for i in injections[:3]) if injections else "nichts gefunden",
                         "Text prüfen und entfernen. Anweisungen an Sprachmodelle in versteckten Bereichen gelten als Manipulation "
                         "und können auf eine gehackte Seite hindeuten.", 10))
    visible = _visible_text(full_doc)
    not_visible = schema_not_visible(nodes, visible)
    checks.append(_check("schema_visible", "Integrität", "Strukturierte Daten sichtbar auf der Seite",
                         "warn" if not_visible else "pass" if nodes else "info",
                         "; ".join(f"{m['kind']}: {m['value']}" for m in not_visible[:4]) if not_visible
                         else "Überschrift, Produktname, Preis und FAQ-Fragen auch im Text" if nodes else "keine strukturierten Daten",
                         "Ausgezeichnete Inhalte müssen für Nutzer sichtbar sein (Google-Richtlinien für strukturierte Daten).", 4))
    main_times = [t.get("datetime") for t in tree.xpath(".//time[@datetime]")] if tree is not None else []
    date_issues = date_problems(nodes, main_times, now)
    if dates:
        checks.append(_check("date_coherence", "Integrität", "Datumsangaben stimmig", "warn" if date_issues else "pass",
                             "; ".join(date_issues) if date_issues else "keine Widersprüche",
                             "datePublished, dateModified und das sichtbare Datum aufeinander abstimmen; keine Daten in der Zukunft.", 3))
    brand = brand_problems(nodes, parsed.title, parsed.og)
    if brand or org or parsed.og.get("og:site_name"):
        checks.append(_check("brand_consistency", "Integrität", "Markenname einheitlich", "warn" if brand else "pass",
                             "; ".join(brand["issues"]) if brand else "Markenname in Title/Open Graph wie in den strukturierten Daten",
                             "Denselben Markennamen in Title, og:site_name und Organization-Schema verwenden.", 3))

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


# --------------------------------------------------------------------------- integrity signals
# Shared by the GEO check and the crawl audit. Each function works on the delivered HTML only and returns facts;
# callers decide on status and wording.

_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>")


def _doc(html: bytes):
    """Parse as text: lxml guesses Latin-1 for bytes without a charset declaration, which breaks umlauts and the
    detection of invisible characters. UTF-8 first, Windows-1252 as fallback."""
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError:
        text = html.decode("cp1252", "replace")
    try:
        return lxml.html.fromstring(_XML_DECL.sub("", text, count=1))
    except (ValueError, lxml.etree.ParserError):
        return None


def _visible_text(doc) -> str:
    """Body text without scripts, styles and templates, casefolded and whitespace-collapsed."""
    if doc is None:
        return ""
    doc = lxml.html.fromstring(lxml.html.tostring(doc))  # work on a copy
    for bad in doc.xpath("//script|//style|//noscript|//template|//head"):
        bad.drop_tree()
    return " ".join(doc.text_content().split()).casefold()


_MAX_SNIPPET = re.compile(r"max-snippet\s*:\s*(-?\d+)")
_MAX_IMAGE = re.compile(r"max-image-preview\s*:\s*(none|standard|large)")


def snippet_limits(x_robots: str, meta_robots: str, doc) -> dict:
    """Robots snippet controls that limit how much of the page Google (and AI Overviews) may quote.

    max-snippet:-1 means "no limit". data-nosnippet is measured as a share of the visible body text.
    """
    directives = f"{(x_robots or '').lower()} {(meta_robots or '').lower()}"
    m = _MAX_SNIPPET.search(directives)
    img = _MAX_IMAGE.search(directives)
    share = 0.0
    if doc is not None:
        total = len(_visible_text(doc))
        hidden = sum(len(" ".join(el.text_content().split())) for el in doc.xpath("//*[@data-nosnippet]")
                     if not el.xpath("ancestor::*[@data-nosnippet]"))
        share = round(min(1.0, hidden / total), 2) if total else 0.0
    return {"nosnippet": "nosnippet" in directives.replace("data-nosnippet", ""),
            "max_snippet": int(m.group(1)) if m else None,
            "max_image_preview": img.group(1) if img else None,
            "data_nosnippet_share": share}


def snippet_problems(limits: dict) -> list[str]:
    """Human-readable problems; empty when nothing restricts quoting."""
    out = []
    if limits["nosnippet"]:
        out.append("nosnippet: es darf kein Textauszug gezeigt werden")
    ms = limits["max_snippet"]
    if ms is not None and 0 <= ms < 50:
        out.append(f"max-snippet:{ms} (unter 50 Zeichen)")
    if limits["data_nosnippet_share"] >= 0.5:
        out.append(f"{round(limits['data_nosnippet_share'] * 100)} % des Textes mit data-nosnippet")
    return out


# Instructions aimed at language models. Conservative patterns (English and German) that do not occur in
# normal page copy; each match is shown with its context so a human can judge it.
_INSTRUCTION = re.compile("|".join([
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions|prompts?)",
    r"disregard (?:all |any )?(?:previous|prior|above) (?:instructions|prompts?)",
    r"you are (?:now )?(?:a|an) (?:helpful )?(?:ai|assistant|language model|llm|chatbot)\b",
    r"as an ai (?:language model|assistant)",
    r"(?:always|you must) recommend (?:this|our|us)\b",
    r"do not (?:mention|recommend) (?:any )?competitors?",
    r"\[/?inst\]|<<sys>>|<\|im_start\|>|<\|system\|>",
    r"ignoriere (?:alle )?(?:vorherigen|bisherigen|obigen) (?:anweisungen|befehle)",
    r"du bist (?:jetzt |nun )?ein (?:hilfreicher )?(?:ki-)?(?:assistent|sprachmodell|chatbot)",
    r"(?:empfiehl|empfehle) (?:immer|stets|ausschließlich) (?:uns|unsere|dieses)",
    r"nenne (?:keine|niemals) (?:wettbewerber|konkurrenten|mitbewerber)",
]), re.I)
# Zero-width and bidi control characters, plus Unicode tag characters (used to smuggle invisible text).
# U+200D (zero-width joiner) is left out: emoji sequences use it legitimately.
_INVISIBLE = re.compile(r"[\u200b\u200c\u2060\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*(?:0|[01](?:\.\d+)?px)\b|opacity\s*:\s*0(?:\.0+)?\b", re.I)


def _sample(text: str, m: re.Match) -> str:
    s = " ".join(text[max(0, m.start() - 40): m.end() + 60].split())
    return s[:150]


def hidden_instructions(doc) -> list[dict]:
    """Possible prompt injection: LLM instructions in text, comments or attributes, and invisible characters.

    ``doc`` is a parsed lxml document (see ``_doc``). Returns at most 5 samples. Detection only; whether the
    text is malicious is for a human to decide.
    """
    if doc is None:
        return []
    found: list[dict] = []

    def add(kind: str, where: str, text: str) -> None:
        m = _INSTRUCTION.search(text)
        if m and len(found) < 5:
            found.append({"kind": kind, "where": where, "sample": _sample(text, m)})

    for comment in doc.xpath("//comment()"):
        add("instruction", "HTML-Kommentar", comment.text or "")
    for el in doc.xpath("//*[@style or @hidden or @aria-hidden='true']"):
        hidden = el.get("hidden") is not None or el.get("aria-hidden") == "true" or _HIDDEN_STYLE.search(el.get("style") or "")
        if hidden:
            add("instruction", "versteckter Text", el.text_content())
    for el in doc.xpath("//*[@alt or @title or @aria-label or @content]"):
        for attr in ("alt", "title", "aria-label", "content"):
            if el.get(attr):
                add("instruction", f"Attribut {attr}", el.get(attr))
    body = doc.find("body")
    text = body.text_content() if body is not None else doc.text_content()
    if not any(f["kind"] == "instruction" for f in found):
        add("instruction", "sichtbarer Text", text)
    invisible = len(_INVISIBLE.findall(text))
    if invisible >= 5 and len(found) < 5:
        found.append({"kind": "invisible_chars", "where": "Text", "sample": f"{invisible} unsichtbare Steuerzeichen"})
    return found


def _price_variants(value) -> list[str]:
    try:
        v = float(str(value).replace(",", "."))
    except ValueError:
        return [str(value)]
    whole = int(v)
    variants = {f"{v:.2f}", f"{v:.2f}".replace(".", ","), f"{whole:,}".replace(",", "."), f"{whole:,}"}
    if v == whole:
        variants.add(str(whole))
    return sorted(variants)


def schema_not_visible(nodes: list[dict], visible: str) -> list[dict]:
    """Structured-data values that do not appear in the visible text (headline, product name, FAQ question, price).

    Google's structured-data guidelines require marked-up content to be visible to users.
    """
    missing: list[dict] = []

    def check(kind: str, value) -> None:
        if not isinstance(value, str):
            return
        needle = " ".join(value.split()).casefold()
        if len(needle) < 3:
            return
        if needle[:80] not in visible and len(missing) < 10:
            missing.append({"kind": kind, "value": value[:120]})

    for n in nodes:
        t = _types(n)
        if t & _ARTICLE_TYPES:
            check("Überschrift (headline)", n.get("headline"))
        if "Product" in t:
            check("Produktname", n.get("name"))
            offers = n.get("offers")
            for offer in ([offers] if isinstance(offers, dict) else offers if isinstance(offers, list) else [])[:3]:
                if isinstance(offer, dict) and offer.get("price") not in (None, ""):
                    if not any(v in visible for v in _price_variants(offer["price"])) and len(missing) < 10:
                        missing.append({"kind": "Preis", "value": str(offer["price"])})
        if "FAQPage" in t:
            entities = n.get("mainEntity")
            for q in ([entities] if isinstance(entities, dict) else entities if isinstance(entities, list) else [])[:30]:
                if isinstance(q, dict):
                    check("FAQ-Frage", q.get("name"))
    return missing


def date_problems(nodes: list[dict], visible_times: list[str], now: datetime) -> list[str]:
    """Dates in the page's own structured data that contradict each other, lie in the future or differ from the
    visible date. ``visible_times`` are datetime attributes of <time> elements in the main content."""
    out = []
    published = [d for d in (_parse_date(str(n.get("datePublished"))) for n in nodes if n.get("datePublished")) if d]
    modified = [d for d in (_parse_date(str(n.get("dateModified"))) for n in nodes if n.get("dateModified")) if d]
    future = [d for d in published + modified if (d - now).days >= 1]
    if future:
        out.append(f"Datum in der Zukunft: {max(future).date().isoformat()}")
    if published and modified and min(modified) < min(published) - timedelta(days=1):
        out.append("dateModified liegt vor datePublished")
    schema_dates = published + modified
    visible = [d for d in (_parse_date(v) for v in visible_times) if d]
    # Only judge a single visible date (or two: published + updated); lists of teasers carry many dates.
    if schema_dates and visible and len(visible) <= 2:
        gap = min(abs((v - s).days) for v in visible for s in schema_dates)
        if gap > 30:
            out.append(f"sichtbares Datum weicht {gap} Tage von den strukturierten Daten ab")
    return out


_LEGAL = re.compile(r"\b(?:gmbh(?: & co\.? kg)?|ug(?: \(haftungsbeschränkt\))?|ag|kg|ohg|gbr|e\.k\.|e\.v\.|inc|ltd|llc|plc|corp|co|sa|srl|spa|bv|nv)\.?$", re.I)


def _brand_key(name: str) -> str:
    s = " ".join((name or "").split()).casefold()
    s = _LEGAL.sub("", s).strip(" ,.-–|")
    return re.sub(r"[^\w]+", " ", s).strip()


def brand_problems(nodes: list[dict], title: str | None, og: dict[str, str]) -> dict | None:
    """Brand name from the Organization/LocalBusiness node (or og:site_name) compared with title and Open Graph.

    Returns None when there is no brand name to compare or when it appears consistently."""
    org = next((n.get("name") for n in nodes if _types(n) & _ENTITY_TYPES and isinstance(n.get("name"), str)), None)
    site_name = og.get("og:site_name")
    brand = org or site_name
    if not brand or len(_brand_key(brand)) < 2:
        return None
    key = _brand_key(brand)
    places = {"Title": title or "", "og:title": og.get("og:title", ""), "og:site_name": site_name or ""}
    found = [k for k, v in places.items() if v and key in _brand_key(v)]
    issues = []
    if not found:
        issues.append(f"„{brand}“ steht weder im Title noch in og:title/og:site_name")
    if org and site_name and _brand_key(org) not in _brand_key(site_name) and _brand_key(site_name) not in _brand_key(org):
        issues.append(f"Schema-Name „{org}“ und og:site_name „{site_name}“ unterscheiden sich")
    return {"brand": brand, "found_in": found, "issues": issues} if issues else None


# --------------------------------------------------------------------------- robots.txt signals, AI meta tags, llms.txt

# Content-Signal values that keep a site out of AI answers. ai-train=no is a legitimate choice and not flagged.
_RESTRICTIVE_SIGNALS = {"search": "Suche", "ai-input": "Nutzung in KI-Antworten"}
_AI_AGENTS = {ua.lower() for ua, _, _ in AI_CRAWLERS}


def robots_ai_signals(rules: RobotsRules | None) -> dict:
    """Cloudflare-managed AI blocks and Content-Signal directives that apply to everyone or to AI crawlers."""
    if rules is None:
        return {"cloudflare_blocks": None, "content_signals": [], "restrictive": []}
    signals, restrictive = [], []
    for agents, values in rules.content_signals:
        relevant = [a for a in agents if a == "*" or a in _AI_AGENTS]
        if not relevant:
            continue
        signals.append({"agents": relevant, "signals": values})
        for key, label in _RESTRICTIVE_SIGNALS.items():
            if values.get(key) == "no":
                restrictive.append(f"{key}=no ({label}) für {', '.join(relevant)}")
    cf = rules.cloudflare_managed_blocks
    return {"cloudflare_blocks": [a for a in cf if a in _AI_AGENTS] if cf is not None else None,
            "cloudflare_managed": cf is not None, "content_signals": signals, "restrictive": restrictive}


_BOT_HEADER = re.compile(r"([a-z][a-z0-9._-]*)\s*:\s*([a-z0-9_,:\s-]+?)(?=(?:,\s*[a-z][a-z0-9._-]*\s*:)|$)", re.I)


def ai_meta(doc, x_robots: str, meta_robots: str) -> dict:
    """noai/noimageai and crawler-specific robots rules for AI crawlers, from meta tags and the X-Robots-Tag header.

    noai/noimageai are not part of any standard and the large providers do not document support; they are
    reported because they signal an intent. Crawler-specific noindex/none for a search crawler is a real block.
    """
    general = f"{(x_robots or '').lower()} {(meta_robots or '').lower()}"
    per_agent: dict[str, str] = {}
    if doc is not None:
        for el in doc.xpath("//meta[@name and @content]"):
            name = (el.get("name") or "").strip().lower()
            if name in _AI_AGENTS:
                per_agent[name] = " ".join(el.get("content", "").lower().split())
    for agent, directives in _BOT_HEADER.findall(x_robots or ""):
        if agent.lower() in _AI_AGENTS:
            per_agent[agent.lower()] = " ".join(directives.lower().split())
    canonical = {ua.lower(): ua for ua, _, _ in AI_CRAWLERS}
    blocked = sorted(canonical[a] for a, d in per_agent.items()
                     if canonical[a] in SEARCH_CRITICAL and re.search(r"\b(noindex|none|nosnippet)\b", d))
    return {"noai": bool(re.search(r"\bnoai\b", general)), "noimageai": "noimageai" in general,
            "per_agent": {canonical[a]: d for a, d in per_agent.items()}, "blocked_search": blocked}


def ai_meta_problems(meta: dict) -> list[str]:
    out = []
    if meta["blocked_search"]:
        out.append("Such-Crawler per Meta/Header ausgeschlossen: " + ", ".join(
            f"{a} ({meta['per_agent'][a]})" for a in meta["blocked_search"]))
    if meta["noai"]:
        out.append("noai gesetzt")
    if meta["noimageai"]:
        out.append("noimageai gesetzt")
    return out


_LLMS_LINK = re.compile(r"^\s*[-*]\s*\[[^\]]+\]\([^)\s]+\)", re.M)


def llms_validate(text: str) -> dict:
    """Structure of /llms.txt per llmstxt.org: H1 title, '>' summary, '##' sections, '- [title](url)' links."""
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    content = [ln for ln in lines if ln.strip()]
    title = bool(content) and content[0].startswith("# ")
    summary = any(ln.lstrip().startswith(">") for ln in content[:10])
    sections = sum(1 for ln in content if ln.startswith("## "))
    links = len(_LLMS_LINK.findall(text or ""))
    issues = []
    if not title:
        issues.append("erste Zeile ist keine H1-Überschrift ('# Name')")
    if not summary:
        issues.append("keine Kurzbeschreibung ('> …')")
    if not sections:
        issues.append("keine Abschnitte ('## …')")
    if not links:
        issues.append("keine Linkliste ('- [Titel](URL): Beschreibung')")
    return {"title": title, "summary": summary, "sections": sections, "links": links, "issues": issues}


# --------------------------------------------------------------------------- crawl integration
# The same signals as the standalone GEO check, as audit findings for every crawled page. Thresholds are
# conservative so short service pages are not flagged for missing lists or sources.
_ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle", "TechArticle", "Report"}
_ENTITY_TYPES = {"Organization", "LocalBusiness", "HomeAndConstructionBusiness", "Corporation", "ProfessionalService",
                 "Store", "Restaurant", "Person"}
USER_FETCHERS = {"ChatGPT-User", "Claude-User", "Perplexity-User"}


def page_findings(url: str, html: bytes, parsed, *, is_start: bool = False, now: datetime | None = None,
                  headers: dict | None = None) -> list[tuple[str, dict]]:
    """GEO findings for one indexable HTML page of a crawl."""
    now = now or datetime.now(UTC)
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    out: list[tuple[str, dict]] = []
    words = parsed.word_count
    nodes = _nodes(parsed.jsonld)
    types = set(all_types(parsed.jsonld))
    tree = _main_tree(html)
    paragraphs: list[str] = []
    lists = tables = 0
    if tree is not None:
        paragraphs = [re.sub(r"\s+", " ", p.text_content()).strip() for p in tree.iter("p")]
        paragraphs = [p for p in paragraphs if len(p.split()) >= 8]
        lists = len(tree.xpath(".//ul[count(li)>=2]|.//ol[count(li)>=2]"))
        tables = len(tree.xpath(".//table"))
    host = urlsplit(url).hostname or ""
    ext_hosts = {urlsplit(lk["url"]).hostname for lk in parsed.links
                 if (urlsplit(lk["url"]).hostname or "") not in ("", host) and not (urlsplit(lk["url"]).hostname or "").endswith("." + host)}
    q_heads = sum(1 for h in (parsed.headings or []) if h["level"] in (2, 3) and h["text"].strip().endswith("?"))
    long_form = words >= 600

    # A short teaser or eyebrow line often comes first; an answer paragraph among the first three counts.
    if words >= 300 and paragraphs and not any(20 <= len(p.split()) <= 90 for p in paragraphs[:3]):
        out.append(("geo_no_answer_first", {"first_paragraphs_words": [len(p.split()) for p in paragraphs[:3]]}))
    if long_form and q_heads == 0 and "FAQPage" not in types and _faq_questions(tree) < 2:
        out.append(("geo_no_question_headings", {"words": words}))
    if long_form and lists + tables == 0:
        out.append(("geo_no_lists_tables", {"words": words}))
    if words >= 800 and not ext_hosts:
        out.append(("geo_no_sources", {"words": words}))
    long_paras = [len(p.split()) for p in paragraphs if len(p.split()) > 120]
    if long_paras:
        out.append(("geo_long_paragraphs", {"paragraphs_over_120_words": len(long_paras), "longest": max(long_paras)}))
    # Only the page's own article: hub pages list other articles via hasPart/itemListElement, and those
    # references carry their dates and authors on their own pages.
    own_url = url.rstrip("/")
    articles = [n for n in nodes if _types(n) & _ARTICLE_TYPES
                and (not n.get("url") or str(n.get("url")).rstrip("/") == own_url or n.get("mainEntityOfPage"))]
    if articles:
        dates = [d for d in (_parse_date(str(n.get(k))) for n in articles for k in ("dateModified", "datePublished") if n.get(k)) if d]
        if not dates:
            out.append(("geo_no_date", {}))
        elif (now - max(dates)).days > 548:
            out.append(("geo_stale", {"last_modified": max(dates).date().isoformat(), "days": (now - max(dates)).days}))
        if not any(n.get("author") for n in articles):
            out.append(("geo_no_author", {}))
    if is_start and not (types & _ENTITY_TYPES):
        out.append(("geo_entity_missing", {"schema_types": sorted(types)[:20]}))

    doc = _doc(html)
    meta_issues = ai_meta_problems(ai_meta(doc, headers.get("x-robots-tag", ""), parsed.meta_robots or ""))
    if meta_issues:
        out.append(("geo_ai_meta_restricted", {"issues": meta_issues}))
    limit_issues = snippet_problems(snippet_limits(headers.get("x-robots-tag", ""), parsed.meta_robots or "", doc))
    if limit_issues:
        out.append(("geo_snippet_limited", {"limits": limit_issues}))
    injections = hidden_instructions(doc)
    if injections:
        out.append(("geo_hidden_instructions", {"samples": injections}))
    not_visible = schema_not_visible(nodes, _visible_text(doc)) if nodes else []
    if not_visible:
        out.append(("geo_schema_not_visible", {"values": not_visible}))
    if articles:
        main_times = [t.get("datetime") for t in tree.xpath(".//time[@datetime]")] if tree is not None else []
        date_issues = date_problems(articles, main_times, now)
        if date_issues:
            out.append(("geo_date_inconsistent", {"issues": date_issues}))
    if is_start:
        brand = brand_problems(nodes, parsed.title, parsed.og)
        if brand:
            out.append(("geo_brand_inconsistent", brand))
    return out


def site_findings(robots: RobotsRules | None, start_url: str, llms_status: int | None, llms_text: str) -> dict:
    """Site-level GEO facts stored with the crawl's site checks."""
    blocked = [ua for ua, _, _ in AI_CRAWLERS if robots is not None and not robots.allowed(start_url, ua)]
    return {"blocked_search": [ua for ua in blocked if ua in SEARCH_CRITICAL],
            "blocked_user": [ua for ua in blocked if ua in USER_FETCHERS],
            "blocked_other": [ua for ua in blocked if ua not in SEARCH_CRITICAL and ua not in USER_FETCHERS],
            "llms_status": llms_status, "llms_ok": llms_status == 200 and llms_text.lstrip().startswith("#"),
            "llms_issues": llms_validate(llms_text)["issues"] if llms_status == 200 else [],
            **robots_ai_signals(robots)}
