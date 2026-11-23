"""Section-referenced Bing/Brave evidence and the engine-specific checks derived from the guidelines."""
from __future__ import annotations

from app.api.bing import _candidates
from app.audit.engine_guidance import BING_GUIDANCE, BRAVE_GUIDANCE, engine_guidance
from app.audit.page_checks import bing_legacy_directives
from app.audit.rules import PROFILE_RULE_IDS, RULES, classify_rule, rule_profiles
from app.crawler.robots import RobotsRules
from app.db import session_scope
from app.models import Crawl, Page, Site


def test_every_mapping_names_its_basis():
    for table in (BING_GUIDANCE, BRAVE_GUIDANCE):
        assert set(table) <= set(RULES)
        for rule_id, entry in table.items():
            assert entry["section"], rule_id
            if entry["evidence"] == "quoted":
                assert entry["quote"] and len(entry["quote"]) > 20, rule_id
            else:
                assert entry["evidence"] == "topic" and entry["quote"] is None, rule_id


def test_serialised_evidence_carries_section_quote_and_source_state():
    row = engine_guidance("redirect_temporary")["bing"]
    assert row["status"] == "related_guidance" and row["evidence"] == "quoted"
    assert "less than 2 days" in row["quote"] and row["section"].startswith("7.")
    assert "2026-11-23" in row["source_status"]
    assert engine_guidance("redirect_temporary")["brave"]["status"] == "not_evaluated"


def test_claims_without_a_source_stay_unmapped():
    # Not stated in the Bing guidelines or on Brave's crawler page; keep them out of the engine scores.
    for rule_id in ("redirect_chain", "title_too_long", "description_too_long", "viewport_missing", "slow_response",
                    "html_too_large", "hreflang_invalid", "thin_content"):
        assert engine_guidance(rule_id)["bing"]["status"] == "not_evaluated", rule_id
        assert engine_guidance(rule_id)["brave"]["status"] == "not_evaluated", rule_id


def test_brave_mappings_follow_the_googlebot_dependency_only_where_stated():
    assert engine_guidance("robots_googlebot_blocked")["brave"]["evidence"] == "quoted"
    # Our crawler's own user agent is evaluated for these, not Googlebot: topic only.
    assert engine_guidance("blocked_by_robots")["brave"]["evidence"] == "topic"
    assert PROFILE_RULE_IDS["brave"] == {"noindex", "robots_googlebot_blocked", "robots_blocks_site", "blocked_by_robots"}


def test_new_rules_are_classified_and_profiled():
    for rule_id, profile in (("robots_googlebot_blocked", "brave"), ("robots_bingbot_blocked", "bing"),
                             ("robots_bingbot_group_incomplete", "bing"), ("sitemap_lastmod_missing", "bing"),
                             ("bing_legacy_ai_directives", "bing")):
        assert classify_rule(rule_id) == "seo_heuristic"
        assert rule_profiles(rule_id) == (profile,)
    assert len(RULES) == 122


def test_robots_agent_specific_blocks_and_bingbot_group():
    text = """User-agent: *
Disallow: /intern/
Disallow: /tmp/

User-agent: bingbot
Disallow: /tmp/

User-agent: Googlebot
Disallow: /
"""
    rules = RobotsRules(text)
    assert rules.allowed("https://x.de/", "SEO-Werkbank") is True
    assert rules.allowed("https://x.de/", "Googlebot") is False
    assert rules.allowed("https://x.de/", "Mozilla/5.0 (compatible; bingbot/2.0)") is True
    assert rules.missing_generic_disallows("bingbot") == ["/intern/"]
    assert RobotsRules("User-agent: *\nDisallow: /a/\n").missing_generic_disallows("bingbot") == []


def test_bingbot_group_complete_reports_nothing():
    text = "User-agent: *\nDisallow: /a/\n\nUser-agent: bingbot\nDisallow: /a/\nCrawl-delay: 1\n"
    assert RobotsRules(text).missing_generic_disallows("bingbot") == []


def test_legacy_directives_only_when_they_apply_to_bing():
    assert bing_legacy_directives(["noindex, noarchive"], None) == ["noarchive"]
    assert bing_legacy_directives([], "bingbot: nocache") == ["nocache"]
    assert bing_legacy_directives([], "googlebot: noarchive") == []
    assert bing_legacy_directives(["index, follow"], "ai-grounding:disallow") == []
    assert bing_legacy_directives(["noarchive"], "nocache") == ["noarchive", "nocache"]


def test_indexnow_candidates_include_removed_urls(client, auth, fixture_site):
    r = client.post("/api/sites", headers=auth, json={"name": "IndexNow removed", "url": fixture_site.url + "/removed-test/"})
    assert r.status_code in (200, 201), r.text
    site_id = r.json()["id"]
    base = fixture_site.url + "/removed-test"
    with session_scope() as db:
        site = db.get(Site, site_id)
        old = Crawl(site_id=site.id, status="completed", start_url=site.url)
        new = Crawl(site_id=site.id, status="completed", start_url=site.url)
        db.add_all([old, new])
        db.flush()

        def page(crawl, name, status=200, h="a"):
            db.add(Page(crawl_id=crawl.id, url=f"{base}/{name}", status_code=status, is_html=True,
                        indexable=status == 200, content_hash=h))

        for name in ("same", "changed", "deleted", "redirected"):
            page(old, name)
        page(new, "same")
        page(new, "changed", h="b")
        page(new, "deleted", status=404)
        page(new, "fresh")
        page(new, "redirected", status=301)
        db.flush()
        found = _candidates(db, site.id)
    assert found["new"] == [f"{base}/fresh"]
    assert found["changed"] == [f"{base}/changed"]
    assert found["removed"] == [f"{base}/deleted"]  # 301 is a move, not a removal
