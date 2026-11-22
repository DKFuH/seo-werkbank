"""Content optimisation: scores a draft against on-page best practice and (optionally) competing pages."""
from __future__ import annotations

import re

from ..audit.schema_validator import recommend_types
from ..crawler.parser import parse_html
from ..keywords.research import classify_intent
from ..text import content_tokens, is_question, readability, stem, tfidf_terms, tokens

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def parse_draft(content: str, url: str = "https://draft.invalid/") -> dict:
    """Accept HTML, Markdown or plain text and return {text, headings, links, images, title, meta_description}."""
    if re.search(r"<(?:p|h[1-6]|div|html|body|article|ul|a)\b", content, re.I):
        p = parse_html(content.encode("utf-8"), url, "text/html; charset=utf-8")
        return {"text": p.text, "headings": p.headings, "links": [{"url": lk["url"], "anchor": lk["anchor"]} for lk in p.links],
                "images": [{"alt": i["alt"]} for i in p.images], "title": p.title, "meta_description": p.meta_description,
                "format": "html"}
    headings, body_lines = [], []
    for line in content.splitlines():
        m = _MD_HEADING.match(line.strip())
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip()})
        else:
            body_lines.append(line)
    body = "\n".join(body_lines)
    images = [{"alt": alt or None} for alt, _ in _MD_IMAGE.findall(body)]
    body = _MD_IMAGE.sub(" ", body)
    links = [{"url": href, "anchor": anchor} for anchor, href in _MD_LINK.findall(body)]
    text = _MD_LINK.sub(r"\1", body)
    text = re.sub(r"[*_`>]+", " ", text)
    full = " ".join(h["text"] + "." for h in headings) + " " + text
    return {"text": re.sub(r"[ \t]+", " ", full).strip(), "headings": headings, "links": links, "images": images,
            "title": None, "meta_description": None, "format": "markdown" if headings else "text"}


def _contains(haystack: str, keyword: str) -> bool:
    kw = [stem(t) for t in content_tokens(keyword)] or [stem(t) for t in tokens(keyword)]
    have = {stem(t) for t in tokens(haystack or "")}
    return bool(kw) and all(t in have for t in kw)


def _check(cid: str, label: str, status: str, detail: str, fix: str = "", weight: int = 5) -> dict:
    return {"id": cid, "label": label, "status": status, "detail": detail, "recommendation": fix if status != "pass" else "", "weight": weight}


def analyse_content(content: str, keyword: str, *, title: str | None = None, meta_description: str | None = None,
                    url: str | None = None, secondary_keywords: list[str] | None = None,
                    competitors: list[dict] | None = None, site_pages: list[dict] | None = None,
                    question_keywords: list[str] | None = None) -> dict:
    """Return score, checks, readability, term suggestions, FAQ ideas, schema and internal-link suggestions.

    ``competitors``: [{url, text, headings, word_count}] of ranking pages (optional, from the SERP module).
    ``site_pages``: [{url, title, h1}] of the user's crawled pages (optional, for internal-link ideas).
    """
    draft = parse_draft(content, url or "https://draft.invalid/")
    title = title or draft["title"]
    meta_description = meta_description or draft["meta_description"]
    text, headings = draft["text"], draft["headings"]
    words = tokens(text)
    n_words = len(words)
    kw_phrase = " ".join(tokens(keyword))
    body_joined = " ".join(words)
    occurrences = body_joined.count(kw_phrase) if kw_phrase else 0
    density = round(100 * occurrences * max(len(kw_phrase.split()), 1) / n_words, 2) if n_words else 0.0
    read = readability(text)
    intent = classify_intent(keyword)
    h1s = [h["text"] for h in headings if h["level"] == 1]
    subheads = [h["text"] for h in headings if h["level"] in (2, 3)]
    comp = [c for c in (competitors or []) if c.get("text")]
    comp_counts = sorted(c.get("word_count") or len(tokens(c["text"])) for c in comp)
    target_words = comp_counts[len(comp_counts) // 2] if comp_counts else None

    checks: list[dict] = []
    # --- keyword placement
    if title is not None:
        checks.append(_check("kw_title", "Keyword im Title", "pass" if _contains(title, keyword) else "fail",
                             f"Title: „{title}“", "Ziel-Keyword (oder eine nahe Variante) weit vorn in den Title setzen.", 10))
        tl = len(title)
        checks.append(_check("title_length", "Title-Länge", "pass" if 30 <= tl <= 60 else "warn", f"{tl} Zeichen",
                             "Etwa 30–60 Zeichen anpeilen, damit der Title nicht abgeschnitten wird.", 4))
    else:
        checks.append(_check("kw_title", "Keyword im Title", "warn", "Kein Title angegeben", "Title ergänzen, um ihn zu bewerten.", 10))
    if meta_description:
        dl = len(meta_description)
        checks.append(_check("kw_description", "Keyword in der Meta-Description", "pass" if _contains(meta_description, keyword) else "warn",
                             f"{dl} Zeichen", "Keyword natürlich in der Meta-Description erwähnen.", 4))
        checks.append(_check("description_length", "Länge der Meta-Description", "pass" if 70 <= dl <= 160 else "warn",
                             f"{dl} Zeichen", "Etwa 70–160 Zeichen anpeilen.", 3))
    else:
        checks.append(_check("kw_description", "Meta-Description", "warn", "Keine Meta-Description angegeben", "Zusammenfassung mit 70–160 Zeichen inklusive Keyword schreiben.", 4))
    checks.append(_check("h1", "Genau eine H1", "pass" if len(h1s) == 1 else "fail" if not h1s else "warn",
                         f"{len(h1s)} H1-Überschrift(en)", "Genau eine H1 verwenden, die das Thema benennt.", 6))
    if h1s:
        checks.append(_check("kw_h1", "Keyword in der H1", "pass" if any(_contains(h, keyword) for h in h1s) else "warn",
                             f"H1: „{h1s[0]}“", "Keyword in die H1 einbauen.", 6))
    first = " ".join(words[:100])
    checks.append(_check("kw_intro", "Keyword in den ersten 100 Wörtern", "pass" if _contains(first, keyword) else "warn",
                         "Anfang des Textes geprüft", "Thema früh nennen, damit Leser und Suchmaschinen die Relevanz sofort sehen.", 6))
    checks.append(_check("kw_subheadings", "Keyword in einer Zwischenüberschrift", "pass" if any(_contains(h, keyword) for h in subheads) else "warn",
                         f"{len(subheads)} H2/H3-Zwischenüberschrift(en)", "Keyword oder Variante in mindestens einer H2/H3 nutzen.", 4))
    if url:
        checks.append(_check("kw_url", "Keyword in der URL", "pass" if _contains(url.replace("-", " ").replace("/", " "), keyword) else "warn",
                             url, "Kurzen, sprechenden Slug mit Keyword verwenden.", 3))
    if n_words:
        status = "pass" if 0 < density <= 2.5 else "warn" if density == 0 else "fail"
        checks.append(_check("kw_density", "Keyword-Nutzung", status, f"Exakte Phrase {occurrences}× genutzt ({density} % der Wörter)",
                             "Phrase ein paar Mal natürlich verwenden." if density == 0 else "Phrase zu oft wiederholt; einige Nennungen mit Varianten umschreiben.", 6))
    for sk in (secondary_keywords or [])[:15]:
        checks.append(_check(f"secondary:{sk}", f"Neben-Keyword: {sk}", "pass" if _contains(text, sk) else "warn",
                             "Im Text vorhanden" if _contains(text, sk) else "Nicht im Text gefunden", f"„{sk}“ abdecken, wo es passt.", 2))

    # --- depth and structure
    if target_words:
        ratio = n_words / target_words if target_words else 1
        checks.append(_check("length", "Textlänge im Vergleich", "pass" if ratio >= 0.8 else "warn" if ratio >= 0.5 else "fail",
                             f"{n_words} Wörter; Median der Wettbewerber: {target_words}",
                             f"Die Wettbewerberseiten sind länger. Wenn das Thema es hergibt, Richtung ~{target_words} Wörter ausbauen.", 10))
    else:
        checks.append(_check("length", "Textlänge", "pass" if n_words >= 300 else "warn" if n_words >= 150 else "fail",
                             f"{n_words} Wörter", "Seiten unter ~300 Wörtern decken ein Thema selten ab. Substanz ergänzen, kein Füllmaterial.", 10))
    checks.append(_check("subheadings", "Zwischenüberschriften", "pass" if len(subheads) >= max(2, n_words // 400) else "warn",
                         f"{len(subheads)} Zwischenüberschrift(en) bei {n_words} Wörtern", "Text etwa alle 300 Wörter mit aussagekräftigen H2/H3 gliedern.", 5))
    prev, skipped = 0, False
    for h in headings:
        if prev and h["level"] > prev + 1:
            skipped = True
        prev = h["level"]
    checks.append(_check("heading_order", "Überschriften-Hierarchie", "warn" if skipped else "pass",
                         "Eine Ebene wird übersprungen" if skipped else "Ebenen sind fortlaufend", "Nicht von H2 auf H4 springen.", 2))
    imgs = draft["images"]
    if imgs:
        missing = sum(1 for i in imgs if not i["alt"])
        checks.append(_check("img_alt", "Alt-Texte der Bilder", "pass" if not missing else "warn", f"{missing} von {len(imgs)} Bild(ern) ohne Alt-Text",
                             "Jedes aussagekräftige Bild im alt-Attribut beschreiben.", 3))
    elif n_words >= 600:
        checks.append(_check("images", "Bilder", "warn", "Keine Bilder gefunden", "Mindestens ein passendes Bild, Diagramm oder eine Grafik ergänzen.", 2))
    internal = [lk for lk in draft["links"] if lk["url"].startswith("/") or (url and lk["url"].split("/")[2:3] == url.split("/")[2:3])]
    external = [lk for lk in draft["links"] if lk not in internal]
    checks.append(_check("internal_links", "Interne Links", "pass" if internal else "warn", f"{len(internal)} interne(r) Link(s)",
                         "Auf verwandte eigene Seiten mit beschreibendem Ankertext verlinken.", 4))
    checks.append(_check("external_links", "Externe Quellen", "pass" if external else "warn", f"{len(external)} externe(r) Link(s)",
                         "Vertrauenswürdige Quelle verlinken, wo sie eine Aussage stützt.", 2))

    # --- readability
    if read["flesch_reading_ease"] is not None:
        ease = read["flesch_reading_ease"]
        checks.append(_check("readability", "Lesbarkeit (Flesch)", "pass" if ease >= 50 else "warn" if ease >= 30 else "fail",
                             f"Lesbarkeitsindex {ease} ({read['label']}), Klassenstufe {read['flesch_kincaid_grade']}. Formel für Englisch geeicht – bei deutschen Texten nur grob.",
                             "Sätze kürzen und geläufige Wörter bevorzugen.", 6))
        checks.append(_check("sentence_length", "Satzlänge", "pass" if read["long_sentence_share"] <= 0.25 else "warn",
                             f"{round(read['long_sentence_share'] * 100)} % der Sätze über 25 Wörter", "Lange Sätze teilen.", 3))

    # --- intent match
    q_heads = sum(1 for h in headings if is_question(h["text"]))
    if intent["intent"] == "informational":
        ok = bool(subheads) and n_words >= 300
        checks.append(_check("intent", "Passt zur informationalen Suchintention", "pass" if ok else "warn",
                             "Informationale Suchanfragen erwarten eine erklärende, gut gegliederte Antwort",
                             "Frage oben direkt beantworten, dann in gegliederten Abschnitten vertiefen.", 6))
    elif intent["intent"] in ("transactional", "commercial"):
        cues = sum(1 for w in ("price", "pricing", "buy", "order", "compare", "review", "features", "benefits", "quote", "contact",
                                "preis", "preise", "kosten", "kaufen", "bestellen", "vergleich", "angebot", "termin", "beratung", "kontakt", "anfrage") if w in words)
        checks.append(_check("intent", "Passt zur kommerziellen Suchintention", "pass" if cues >= 2 else "warn",
                             f"{cues} kommerzielle(s) Signalwort/-wörter gefunden (Preis, Kosten, Vergleich, Angebot, Termin …)",
                             "Abdecken, was Käufer suchen: Optionen, Preise, Vergleiche, Belege und eine klare Handlungsaufforderung.", 6))

    # --- competitor-derived suggestions
    semantic, coverage = [], None
    if comp:
        my_terms = set(content_tokens(text)) | {" ".join(g) for g in zip(words, words[1:], strict=False)}
        for t in tfidf_terms([c["text"] for c in comp], limit=60):
            if t["term"] in kw_phrase:
                continue
            used = body_joined.count(t["term"])
            semantic.append({**t, "used": used, "status": "present" if used else "missing"})
        heading_docs = [" . ".join(h["text"] for h in c.get("headings", []) if h.get("level") in (2, 3)) for c in comp]
        topics = tfidf_terms(heading_docs, limit=20)
        covered = [t for t in topics if t["term"] in my_terms or t["term"] in body_joined]
        coverage = {"topics": [{**t, "covered": t in covered} for t in topics],
                    "covered_share": round(len(covered) / len(topics), 2) if topics else None}
        if topics:
            share = coverage["covered_share"]
            checks.append(_check("topic_coverage", "Themenabdeckung im Vergleich", "pass" if share >= 0.6 else "warn" if share >= 0.35 else "fail",
                                 f"Deckt {len(covered)} von {len(topics)} Themen ab, die Wettbewerber in Zwischenüberschriften nutzen",
                                 "Abschnitte für die fehlenden Themen unter Themenabdeckung ergänzen.", 10))
        missing_terms = [s for s in semantic if s["status"] == "missing" and s["share"] >= 0.5]
        if semantic:
            checks.append(_check("semantic_terms", "Verwandte Begriffe der rankenden Seiten", "pass" if len(missing_terms) <= 5 else "warn",
                                 f"{len(missing_terms)} Begriff(e), die mindestens die Hälfte der Wettbewerber nutzt, fehlen",
                                 "Fehlende verwandte Begriffe einbauen, wo sie natürlich passen.", 6))

    # --- FAQ, schema, internal links
    faq = list(dict.fromkeys(
        [q for q in (question_keywords or []) if not _contains(text, q)][:10]
        + [h["text"] for c in comp for h in c.get("headings", []) if is_question(h.get("text", "")) and 15 < len(h["text"]) < 140][:10]
    ))[:12]
    schema = recommend_types({"url": url or "", "depth": 1, "types": [], "question_headings": q_heads})
    if not any(s["type"] in ("BlogPosting", "Product", "Service") for s in schema) and intent["intent"] == "informational":
        schema.append({"type": "Article", "reason": "Informationale Inhalte profitieren von Article/BlogPosting-Markup"})
    link_ideas = []
    for p in (site_pages or [])[:3000]:
        if url and p["url"] == url:
            continue
        label = p.get("h1") or p.get("title") or ""
        key = [stem(t) for t in content_tokens(label)][:4]
        if len(key) >= 2 and all(k in {stem(w) for w in words} for k in key) and not any(lk["url"] == p["url"] for lk in draft["links"]):
            link_ideas.append({"url": p["url"], "title": p.get("title"), "reason": f"Entwurf erwähnt „{' '.join(content_tokens(label)[:4])}“"})
    link_ideas = link_ideas[:10]

    total = sum(c["weight"] for c in checks)
    earned = sum(c["weight"] * (1.0 if c["status"] == "pass" else 0.5 if c["status"] == "warn" else 0.0) for c in checks)
    return {
        "score": round(100 * earned / total) if total else 0,
        "keyword": keyword, "intent": intent, "word_count": n_words, "target_word_count": target_words,
        "keyword_occurrences": occurrences, "keyword_density": density, "readability": read,
        "headings": headings[:100], "checks": checks, "semantic_terms": semantic, "topic_coverage": coverage,
        "faq_suggestions": faq, "schema_recommendations": schema, "internal_link_suggestions": link_ideas,
        "format": draft["format"], "competitors_used": len(comp),
        "notes": ["Die Scores sind Heuristiken nach Onpage-Regeln und sagen keine Rankings voraus."]
                 + ([] if comp else ["Keine Wettbewerberseiten angegeben: Begriffs- und Themenvorschläge brauchen SERP-Daten oder eingefügte Wettbewerber-URLs."]),
    }
