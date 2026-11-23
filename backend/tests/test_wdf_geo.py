"""Unit tests for the WDF*IDF and GEO modules (no network)."""
from __future__ import annotations

import math
from datetime import UTC, datetime

from app.audit.geo import analyse_geo, robots_report
from app.content.wdf_idf import analyse_wdf_idf, idf, thirds, wdf
from app.crawler.parser import parse_html


# ------------------------------------------------------------------ WDF*IDF
def test_wdf_and_idf_formulas():
    assert wdf(0, 100) == 0.0
    assert math.isclose(wdf(3, 255), math.log2(4) / math.log2(256))
    assert math.isclose(idf(4, 2), math.log10(3))
    assert idf(4, 0) == 0.0


def _doc(url, text, headings=None):
    return {"url": url, "text": text, "headings": headings or []}


def test_wdf_idf_statuses_and_german_stopwords():
    comp = [
        _doc("https://a.example/", "Die Arbeitsplatte aus Keramik ist hitzebeständig. Keramik Arbeitsplatte pflegen und reinigen."),
        _doc("https://b.example/", "Eine Arbeitsplatte aus Keramik braucht eine stabile Unterkonstruktion. Keramik bleibt kratzfest."),
        _doc("https://c.example/", "Keramik als Arbeitsplatte: kratzfest, hitzebeständig und pflegeleicht."),
    ]
    own = _doc("Eigener Text", "Holz Holz Holz Holz Holz Holz Holz Holz Arbeitsplatte aus Holz für die Küche.")
    r = analyse_wdf_idf(own, comp, keyword="Keramik Arbeitsplatte", lang="de")
    terms = {t["term"]: t for t in r["terms"]}
    assert "die" not in terms and "und" not in terms and "eine" not in terms
    assert terms["keramik"]["status"] == "fehlt"
    assert terms["keramik"]["is_keyword"] is True
    assert terms["arbeitsplatte"]["competitors_using"] == 3
    assert "holz" not in terms  # used by no competitor
    assert r["documents"][0]["is_own"] is True
    assert r["summary"]["missing"]
    assert set(r["distribution"]) <= {t["term"] for t in r["terms"]}


def test_wdf_idf_over_maximum_and_bigrams():
    comp = [_doc(f"https://{c}.example/", "Spüle aus Edelstahl reinigen. Edelstahl Spüle pflegen mit weichem Tuch. Kalk entfernen.")
            for c in "abc"]
    own = _doc("x", " ".join(["Edelstahl"] * 30) + " Spüle reinigen Kalk entfernen weichem Tuch pflegen")
    r = analyse_wdf_idf(own, comp, keyword="edelstahl", ngram=2)
    terms = {t["term"]: t for t in r["terms"]}
    assert terms["edelstahl"]["status"] == "über Maximum"
    assert "kalk entfernen" in terms


def test_wdf_idf_without_own_page_and_without_competitors():
    r = analyse_wdf_idf(None, [_doc("https://a.example/", "Kochfeld Dunstabzug Kochfeld Abluft")], keyword="")
    assert r["summary"] is None and r["distribution"] is None and r["terms"]
    assert analyse_wdf_idf(None, [])["terms"] == []


def test_thirds_distribution():
    d = thirds("alpha beta gamma delta alpha epsilon zeta alpha", ["alpha"], set())
    assert sum(d["alpha"]) == 3


# ------------------------------------------------------------------ GEO
HTML = b"""<!doctype html><html lang="de"><head><title>Keramik-Arbeitsplatte</title>
<meta name="description" content="Was eine Keramik-Arbeitsplatte kann.">
<meta name="author" content="Max Muster">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"HomeAndConstructionBusiness","name":"Muster K\\u00fcchen","sameAs":["https://www.instagram.com/x","https://www.linkedin.com/company/1"]},
 {"@type":"Article","headline":"Keramik","dateModified":"2026-11-01T00:00:00+01:00","author":{"@type":"Person","name":"Max Muster"}},
 {"@type":"FAQPage","mainEntity":[]}]}</script></head>
<body><nav><a href="/">Start</a></nav><main><h1>Keramik-Arbeitsplatte</h1>
<p>Eine Keramik-Arbeitsplatte ist 12 mm stark, hitzebest\xc3\xa4ndig bis 300 Grad und kratzfest. Sie eignet sich f\xc3\xbcr
Familien, die viel kochen und eine pflegeleichte Fl\xc3\xa4che suchen, kostet aber mehr als Schichtstoff.</p>
<h2>Wie pflegt man Keramik?</h2><p>Mit warmem Wasser und einem weichen Tuch reinigen, bei Kalk etwas Essigreiniger nutzen, danach trocken wischen.</p>
<h2>Was kostet eine Keramik-Arbeitsplatte?</h2><ul><li>Material</li><li>Ausschnitte</li></ul>
<p>Laut <a href="https://www.hersteller.example/pflege">Hersteller</a> und <a href="https://norm.example/">Norm</a> sind 20 % Aufpreis und 6 Wochen Lieferzeit realistisch.</p>
</main><footer>Impressum</footer></body></html>"""


def test_geo_good_page_and_robots():
    parsed = parse_html(HTML, "https://kueche.example/ratgeber/keramik/", "text/html; charset=utf-8")
    robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    r = analyse_geo("https://kueche.example/ratgeber/keramik/", HTML, parsed, robots_text=robots, robots_status=200,
                    llms_status=200, llms_text="# Kueche\n> Ratgeber\n\n## Ratgeber\n- [Keramik](https://kueche.example/ratgeber/keramik/): Pflege", ai_txt_status=404,
                    now=datetime(2026, 11, 22, tzinfo=UTC))
    c = {x["id"]: x for x in r["checks"]}
    assert c["ai_search_bots"]["status"] == "pass"
    assert c["ai_training_bots"]["status"] == "warn" and "GPTBot" in c["ai_training_bots"]["detail"]
    assert c["llms_txt"]["status"] == "pass"
    assert c["entity"]["status"] == "pass" and c["same_as"]["status"] == "pass"
    assert c["author"]["status"] == "pass"
    assert c["freshness"]["status"] == "pass"
    assert c["question_headings"]["status"] == "pass"
    assert c["lists_tables"]["status"] == "pass"
    assert c["sources"]["status"] == "pass"
    assert c["faq_schema"]["status"] == "pass"
    assert c["answer_first"]["status"] == "pass"
    assert 0 < r["score"] <= 100


def test_geo_blocked_search_bot_and_noindex():
    parsed = parse_html(b"<html><head><meta name='robots' content='noindex'></head><body><p>kurz</p></body></html>",
                        "https://x.example/", "text/html")
    r = analyse_geo("https://x.example/", b"<html><body><p>kurz</p></body></html>", parsed,
                    robots_text="User-agent: OAI-SearchBot\nDisallow: /\n", robots_status=200, llms_status=404)
    c = {x["id"]: x for x in r["checks"]}
    assert c["ai_search_bots"]["status"] == "fail" and "OAI-SearchBot" in c["ai_search_bots"]["detail"]
    assert c["indexable"]["status"] == "fail"
    assert c["server_text"]["status"] == "fail"
    assert c["entity"]["status"] == "fail"


def test_robots_report_5xx_blocks_everything():
    rows = robots_report("", 503, "https://x.example/")
    assert all(not r["allowed"] for r in rows)


# ------------------------------------------------------------------ API (against the local fixture website)
def test_api_wdf_idf_and_geo(client, auth, fixture_site):
    base = fixture_site.url
    r = client.post("/api/content/wdf-idf", headers=auth, json={
        "keyword": "page", "my_url": base + "/about",
        "competitor_urls": [base + "/near-a", base + "/near-b", base + "/dup-a"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["documents"][0]["is_own"] is True and len(body["documents"]) == 4
    assert body["terms"] and "status" in body["terms"][0]

    r = client.post("/api/content/wdf-idf", headers=auth, json={"keyword": "x", "competitor_urls": []})
    assert r.status_code == 400

    r = client.post("/api/geo/check", headers=auth, json={"url": base + "/good-schema"})
    assert r.status_code == 200, r.text
    g = r.json()
    assert 0 <= g["score"] <= 100 and {c["group"] for c in g["checks"]} >= {"Zugang", "Struktur"}
    assert any(b["agent"] == "OAI-SearchBot" for b in g["crawlers"])

    assert client.post("/api/geo/check", json={"url": base + "/"}).status_code == 401


def test_content_analyze_includes_wdf_idf(client, auth, fixture_site):
    base = fixture_site.url
    r = client.post("/api/content/analyze", headers=auth, json={
        "content": "# Testseite\n\nDiese Seite erklärt das Thema ausführlich und nennt Beispiele für die Planung.",
        "keyword": "page", "competitor_urls": [base + "/near-a", base + "/near-b", base + "/about"]})
    assert r.status_code == 200, r.text
    w = r.json()["wdf_idf"]
    assert w["documents"][0]["is_own"] is True and w["terms"] and "status" in w["terms"][0]
    assert all(t["term"] not in ("der", "und", "die") for t in w["terms"])


# ------------------------------------------------------------------ GEO inside the regular crawl
def test_geo_page_findings_thresholds():
    from app.audit.geo import page_findings
    short = parse_html(b"<html><body><main><h1>X</h1><p>Kurzer Text ohne viel Inhalt hier.</p></main></body></html>", "https://x.example/a", "text/html")
    assert page_findings("https://x.example/a", b"<html><body><main><h1>X</h1><p>Kurzer Text</p></main></body></html>", short) == []
    long_text = " ".join(["Wort"] * 140)
    html = (f"<html><head><script type='application/ld+json'>{{\"@type\":\"Article\",\"headline\":\"A\"}}</script></head>"
            f"<body><main><h1>A</h1><p>{long_text}</p>" + "".join(f"<h2>Abschnitt {i}</h2><p>{long_text}</p>" for i in range(5))
            + "</main></body></html>").encode()
    p = parse_html(html, "https://x.example/b", "text/html")
    ids = {f[0] for f in page_findings("https://x.example/b", html, p, is_start=True)}
    assert {"geo_no_answer_first", "geo_no_question_headings", "geo_no_lists_tables", "geo_no_sources",
            "geo_long_paragraphs", "geo_no_date", "geo_no_author", "geo_entity_missing"} <= ids


def test_geo_site_findings():
    from app.audit.geo import site_findings
    from app.crawler.robots import RobotsRules
    rules = RobotsRules("User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: ChatGPT-User\nDisallow: /\n", 200)
    s = site_findings(rules, "https://x.example/", 404, "")
    assert s["blocked_search"] == ["OAI-SearchBot"] and s["blocked_user"] == ["ChatGPT-User"] and s["llms_ok"] is False
    assert site_findings(None, "https://x.example/", 200, "# Titel\n")["llms_ok"] is True


def test_crawl_reports_geo_rules(client, auth, crawled):
    summary = client.get(f"/api/crawls/{crawled['crawl_id']}/issues", headers=auth).json()
    rules = {g.get("rule_id") or g.get("id") for g in summary.get("groups", summary.get("items", []))}
    assert "geo_llms_missing" in rules  # the fixture site has no /llms.txt


def test_geo_ignores_referenced_articles_on_hub_pages():
    from app.audit.geo import page_findings
    text = " ".join(["Wort"] * 60)
    html = ("<html><head><script type='application/ld+json'>{\"@type\":\"CollectionPage\",\"hasPart\":["
            "{\"@type\":\"Article\",\"headline\":\"A\",\"url\":\"https://x.example/ratgeber/a/\"}]}</script></head>"
            f"<body><main><h1>Hub</h1><p>{text}</p><p>{text}</p></main></body></html>").encode()
    p = parse_html(html, "https://x.example/hub/", "text/html")
    ids = {f[0] for f in page_findings("https://x.example/hub/", html, p)}
    assert "geo_no_date" not in ids and "geo_no_author" not in ids


# ------------------------------------------------------------------ template pages and GSC target check
def test_template_pairs_flags_swapped_name_pages_only():
    from app.audit.analysis import template_pairs
    body = "Wir planen deine Küche in ORT mit Beratung vor Ort, Aufmaß und Montage aus einer Hand. " * 8
    other = "Ein ganz anderer Text über Bäder, Fliesen und Armaturen im Badezimmer. " * 10
    pairs = template_pairs([(1, body.replace("ORT", "Alpha")), (2, body.replace("ORT", "Beta")), (3, other)])
    assert 2 in pairs[1] and pairs[1][2] >= 0.5 and 3 not in pairs


def test_template_pairs_ignores_site_wide_blocks():
    from app.audit.analysis import template_pairs
    cta = "Jetzt Termin vereinbaren und unverbindlich beraten lassen, wir freuen uns auf dich. "
    items = [(i, cta * 3 + f"Eigener Inhalt Nummer {i} " + " ".join(f"wort{i}x{j}" for j in range(60))) for i in range(60)]
    assert template_pairs(items) == {}


def test_keyword_mapping_compares_with_search_console(client, auth, crawled):
    site_id = crawled["site"]["id"]
    base = crawled["base"]
    client.post(f"/api/sites/{site_id}/keywords", headers=auth, json={"keywords": ["about page"]})
    csv_text = f"Suchanfrage,Seite,Klicks,Impressionen,Position\nabout page,{base}/dup-a,2,40,\"6,5\"\n"
    r = client.post(f"/api/sites/{site_id}/gsc/import", headers=auth,
                    files={"file": ("Daten.csv", csv_text.encode("utf-8"), "text/csv")})
    assert r.status_code in (200, 201), r.text
    m = client.get(f"/api/sites/{site_id}/keywords/mapping", headers=auth).json()
    item = next(i for i in m["items"] if i["keyword"] == "about page")
    assert m["gsc_available"] is True and "target mismatch" in m["summary"]
    assert item["gsc"]["top"]["url"] == f"{base}/dup-a" and item["gsc"]["top"]["impressions"] == 40
    assert isinstance(item["target_mismatch"], bool)
