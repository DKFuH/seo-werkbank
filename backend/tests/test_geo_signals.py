"""robots.txt AI signals (Cloudflare managed block, Content-Signal), AI meta tags and llms.txt structure."""
from __future__ import annotations

from app.audit.geo import ai_meta, ai_meta_problems, analyse_geo, llms_validate, page_findings, robots_ai_signals
from app.crawler.parser import parse_html
from app.crawler.robots import RobotsRules

CF_ROBOTS = """# As a condition of accessing this website, you agree to abide by the following content signals:
User-agent: *
Content-Signal: search=yes, ai-train=no
Allow: /

# BEGIN Cloudflare Managed content
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Bytespider
Disallow: /
# END Cloudflare Managed Content
"""


def test_content_signal_is_no_syntax_error_and_cloudflare_block_is_found():
    rules = RobotsRules(CF_ROBOTS, 200)
    assert rules.errors == []  # Content-Signal must not be reported as unknown directive
    assert rules.content_signals == [(["*"], {"search": "yes", "ai-train": "no"})]
    signals = robots_ai_signals(rules)
    assert signals["cloudflare_managed"] and signals["cloudflare_blocks"] == ["claudebot", "gptbot"]
    assert signals["restrictive"] == []  # ai-train=no is a legitimate choice


def test_restrictive_content_signal():
    rules = RobotsRules("User-agent: *\nContent-Signal: search=no, ai-input=no\nAllow: /\n", 200)
    restrictive = robots_ai_signals(rules)["restrictive"]
    assert len(restrictive) == 2 and restrictive[0].startswith("search=no")
    assert robots_ai_signals(RobotsRules("User-agent: *\nAllow: /\n", 200))["cloudflare_blocks"] is None


def test_ai_meta_tags_and_header():
    from app.audit.geo import _doc
    doc = _doc(b'<html><head><meta name="GPTBot" content="noindex, nofollow"><meta name="robots" content="index, noai"></head></html>')
    meta = ai_meta(doc, "PerplexityBot: noindex", "index, noai")
    assert meta["blocked_search"] == ["PerplexityBot"]  # GPTBot is a training crawler, not a search crawler
    assert meta["per_agent"]["GPTBot"] == "noindex, nofollow" and meta["noai"] and not meta["noimageai"]
    problems = ai_meta_problems(meta)
    assert any("PerplexityBot" in p for p in problems) and "noai gesetzt" in problems
    clean = ai_meta(_doc(b"<html><head><meta name='robots' content='index'></head></html>"), "", "index")
    assert ai_meta_problems(clean) == []


def test_llms_validate():
    full = "# Muster\n\n> Tischlerei in Musterstadt\n\n## Leistungen\n- [Küchen](https://muster.de/kuechen): Planung\n"
    assert llms_validate(full)["issues"] == []
    bad = llms_validate("Muster Tischlerei\nhttps://muster.de")
    assert len(bad["issues"]) == 4


def test_geo_check_reports_signals_and_crawl_rule():
    html = b'<html><head><meta name="ClaudeBot" content="noindex"></head><body><main><h1>X</h1><p>Text</p></main></body></html>'
    parsed = parse_html(html, "https://x.example/", "text/html")
    r = analyse_geo("https://x.example/", html, parsed, robots_text=CF_ROBOTS, robots_status=200,
                    llms_status=200, llms_text="# X", llms_full_status=404)
    c = {x["id"]: x for x in r["checks"]}
    assert c["robots_signals"]["status"] == "warn" and "Cloudflare" in c["robots_signals"]["detail"]
    assert c["llms_txt"]["status"] == "warn" and "llms-full.txt nicht vorhanden" in c["llms_txt"]["detail"]
    assert c["ai_meta"]["status"] == "pass"  # ClaudeBot is a training crawler, not a search crawler
    ids = {f[0] for f in page_findings("https://x.example/", html, parsed)}
    assert "geo_ai_meta_restricted" not in ids


def test_crawl_reports_site_level_signal_rules():
    from app.audit.geo import site_findings
    facts = site_findings(RobotsRules(CF_ROBOTS, 200), "https://x.example/", 200, "# X")
    assert facts["cloudflare_blocks"] == ["claudebot", "gptbot"] and facts["llms_issues"]


def test_build_llms_txt_groups_sorts_and_skips():
    from app.api.geo_access import build_llms_txt
    pages = [
        {"url": "https://m.de/", "title": "Start", "meta_description": "Tischlerei", "pagerank": 9},
        {"url": "https://m.de/kontakt", "title": "Kontakt", "meta_description": "", "pagerank": 5},
        {"url": "https://m.de/ratgeber/keramik", "title": "Keramik [Pflege]", "meta_description": "Wie man Keramik reinigt", "pagerank": 3},
        {"url": "https://m.de/ratgeber/holz", "title": "Holz", "meta_description": None, "pagerank": 4},
        {"url": "https://m.de/tag/kueche", "title": "Tag", "meta_description": "", "pagerank": 8},
        {"url": "https://m.de/ratgeber/?page=2", "title": "Seite 2", "meta_description": "", "pagerank": 7},
        {"url": "https://m.de/impressum", "title": "Impressum", "meta_description": "", "pagerank": 1},
        {"url": "https://m.de/ohne-titel", "title": "", "meta_description": "", "pagerank": 6},
    ]
    r = build_llms_txt("Muster", "Tischlerei in Musterstadt", pages)
    text = r["text"]
    assert text.startswith("# Muster\n\n> Tischlerei in Musterstadt\n")
    assert r["sections"] == ["Wichtige Seiten", "Ratgeber", "Rechtliches"] and r["pages"] == 4
    assert text.index("[Holz]") < text.index("[Keramik (Pflege)]")  # better linked first, brackets escaped
    assert "Tag" not in text and "Seite 2" not in text and "ohne-titel" not in text
    from app.audit.geo import llms_validate
    assert llms_validate(text)["issues"] == []


def test_llms_txt_draft_endpoint(client, auth, crawled):
    site_id = crawled["site"]["id"]
    r = client.get(f"/api/sites/{site_id}/geo/llms-txt-draft", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["text"].startswith("# ") and data["pages"] > 0 and data["crawl_id"]
    dl = client.get(f"/api/sites/{site_id}/geo/llms-txt-draft", headers=auth, params={"download": True})
    assert dl.status_code == 200 and "llms.txt" in dl.headers.get("content-disposition", "")
    other = client.post("/api/auth/register", json={"email": "llms-other@example.com", "password": "correct horse battery"}).json()
    assert client.get(f"/api/sites/{site_id}/geo/llms-txt-draft",
                      headers={"Authorization": "Bearer " + other["access_token"]}).status_code == 404
