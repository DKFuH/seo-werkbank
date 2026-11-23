"""Search-engine-specific evidence mappings with section references.

This is a *documented overlap*, not a claim of complete crawler parity.
Unknown rules are intentionally marked unverified, never inferred from Google.

Every mapped rule carries an ``evidence`` level:

* ``quoted``: a sentence in the engine's own guideline describes exactly this check; ``section`` and ``quote`` name it.
* ``topic``: the guideline covers the subject area, but contains no sentence that states this specific check.

Quotes are kept in the language of the source; bullet lists are joined with commas. Do not add a mapping without a verifiable passage or an explicit
``topic`` entry, and do not copy Google statements to Bing or Brave.
"""
from __future__ import annotations

ENGINE_DOCUMENTATION = {
    "google": "https://developers.google.com/search/docs/essentials",
    "bing": "https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a",
    "brave": "https://search.brave.com/help/brave-search-crawler",
}
# State of the source text the quotes were taken from.
SOURCE_STATUS = {
    "bing": "Bing Webmaster Guidelines, lokale Kopie, geprüft am 2026-11-23 (AI-Preferences-Hinweis vom 2026-10-30)",
    "brave": "Brave Search crawler help page, abgerufen am 2026-11-23",
}

_TOPIC = "topic"
_QUOTED = "quoted"


def _q(section: str, quote: str) -> dict:
    return {"evidence": _QUOTED, "section": section, "quote": quote}


def _t(section: str) -> dict:
    return {"evidence": _TOPIC, "section": section, "quote": None}


_BING_TITLE_DESC = _q(
    "13. Structure Content Clearly Using HTML",
    "Missing, duplicate, or overly short title tags and meta descriptions may reduce indexing reliability, ranking, "
    "and eligibility for grounding results and citations.")
_BING_BLOCK = _q("8. Allow Efficient Crawling and Rendering", "Blocking Bingbot in your robots.txt file")
_BING_NOARCHIVE = _q(
    "10. Use robots.txt and Meta Directives Correctly",
    "NOARCHIVE prevents content from being used in Copilot responses and grounding results.")

# Specific documented behaviour, only where Bing publicly describes it.
BING_GUIDANCE: dict[str, dict] = {
    # crawling and robots.txt
    "robots_blocks_site": _BING_BLOCK,
    "blocked_by_robots": _q("8. Allow Efficient Crawling and Rendering", "Blocking important URLs unnecessarily"),
    "robots_bingbot_blocked": _BING_BLOCK,
    "robots_bingbot_group_incomplete": _q(
        "How to create a robots.txt file",
        "On finding a specific set of instructions for itself, Bingbot will ignore the directives listed in the "
        "generic section, so you need to repeat all the general directives in addition to the specific directives "
        "you created for it in specific section of the file."),
    "robots_unreachable": _t("8. Allow Efficient Crawling and Rendering"),
    "http_5xx": _t("8. Allow Efficient Crawling and Rendering"),
    "fetch_error": _t("8. Allow Efficient Crawling and Rendering"),
    "http_4xx": _t("9. Remove URLs Cleanly When Content is Deleted"),
    # indexing and canonicalisation
    "noindex": _q("10. Use robots.txt and Meta Directives Correctly",
                  "Use NOINDEX when a URL should NOT appear in Bing search, Copilot experiences, or grounding API results."),
    "duplicate_content": _q("6. Consolidate Duplicate URLs", "Avoid serving the same content across multiple URLs."),
    "canonical_missing": _q("6. Consolidate Duplicate URLs",
                            "Use canonical URLs, parameter controls, and consistent URL structures to consolidate signals "
                            "and improve grounding visibility."),
    "canonical_invalid": _t("6. Consolidate Duplicate URLs"),
    "canonical_broken": _t("6. Consolidate Duplicate URLs"),
    "canonical_multiple": _t("6. Consolidate Duplicate URLs"),
    "url_many_params": _q("8. Allow Efficient Crawling and Rendering",
                          "Outputting excessive or low-value URLs, such as duplicate content or URLs with numerous parameters"),
    "redirect_temporary": _q("7. Handle URL Moves with Proper Redirects",
                             "Use 302 redirects only for very short-term changes (less than 2 days)"),
    # sitemaps and discovery
    "sitemap_missing": _q("3. Use Sitemaps to Signal Importance and Freshness",
                          "Use XML sitemaps to indicate which URLs matter and when content changes."),
    "sitemap_non_indexable": _q("3. Use Sitemaps to Signal Importance and Freshness",
                                "List only canonical URLs; Remove deleted or redirected URLs promptly"),
    "sitemap_lastmod_missing": _q("3. Use Sitemaps to Signal Importance and Freshness",
                                  "Include freshness signals (such as lastmod) where applicable"),
    "sitemap_invalid": _t("3. Use Sitemaps to Signal Importance and Freshness"),
    "not_in_sitemap": _t("3. Use Sitemaps to Signal Importance and Freshness"),
    "broken_internal_link": _t("5. Use Links to Establish Structure and Authority"),
    "empty_anchor": _q("5. Use Links to Establish Structure and Authority",
                       "Include relevant anchor text or image alt attributes"),
    # content structure
    "title_missing": _BING_TITLE_DESC,
    "title_duplicate": _BING_TITLE_DESC,
    "title_too_short": _BING_TITLE_DESC,
    "description_missing": _BING_TITLE_DESC,
    "description_duplicate": _BING_TITLE_DESC,
    "description_too_short": _BING_TITLE_DESC,
    "heading_skipped": _q("13. Structure Content Clearly Using HTML", "Logical <H1> – <H6> heading hierarchy"),
    "h1_missing": _t("13. Structure Content Clearly Using HTML"),
    "img_alt_missing": _q("12. Optimize Images and Video for Understanding",
                          "To support understanding (rather than replace text), provide: Descriptive file names, Alt text, "
                          "Captions, transcripts, or structured data"),
    # structured data
    "schema_invalid_json": _q("Marking up your site: Schema and Data Validation Failure",
                              "Please carefully verify your annotations before publishing them on your site."),
    "schema_missing_required": _q("Marking up your site: Schema and Data Validation Failure",
                                  "An event without a date, or a person without a name, will also be ignored."),
    # Copilot, grounding and AI preferences
    "bing_legacy_ai_directives": _q(
        "FAQ - New AI Preferences, Q20",
        "AI Training and AI Grounding replace NoArchive and NoCache for training and grounding."),
    "geo_ai_meta_restricted": _BING_NOARCHIVE,
    "geo_snippet_limited": _q("10. Use robots.txt and Meta Directives Correctly",
                              "DATA-NOSNIPPET and NOSNIPPET prevent Bing from displaying captions and may limit Copilot "
                              "citation quality."),
    "geo_schema_not_visible": _q("14. Use Structured Data Accurately", "Markup must accurately reflect visible content."),
    "geo_hidden_instructions": _q(
        "Abuse: Prompt Injection and AI Manipulation",
        "Attempts to add content designed to manipulate or interfere with language models used by Bing or Copilot may "
        "result in reduced visibility or removal from search experiences."),
    "geo_brand_inconsistent": _q("16. Define Entities Clearly and Consistently",
                                 "Use clear and consistent naming for people, organizations, products, and locations."),
    "geo_entity_missing": _t("16. Define Entities Clearly and Consistently"),
    "geo_no_answer_first": _q("18. Surface Key information early", "Place essential information near the top of the URL"),
    "geo_stale": _q("19. Keep Content Accurate and Up to Date", "Update content when facts or guidance change."),
}

BRAVE_GUIDANCE: dict[str, dict] = {
    "noindex": _q("Brave Search crawler",
                  "A site owner can delist a page by using [the robots noindex directive]."),
    "robots_googlebot_blocked": _q(
        "Brave Search crawler",
        "if a domain or page is not crawlable by Googlebot, then Brave Search's bot will not crawl it either."),
    # Our crawler's own user agent is evaluated here, not Googlebot: topic only.
    "robots_blocks_site": _t("Brave Search crawler"),
    "blocked_by_robots": _t("Brave Search crawler"),
}

# Backwards-compatible views.
BING_DOCUMENTED = frozenset(BING_GUIDANCE)
BRAVE_DOCUMENTED = frozenset(BRAVE_GUIDANCE)
# Not supported as a claim of documented engine-specific ranking criteria.
ENGINE_STATES = ("related_guidance", "not_evaluated")


def engine_guidance(rule_id: str) -> dict:
    """Return per-engine evidence, without transferring Google claims to Bing/Brave."""
    # This module is only invoked for IDs from the registered audit catalogue.
    out: dict[str, dict] = {}
    for engine, table in (("bing", BING_GUIDANCE), ("brave", BRAVE_GUIDANCE)):
        entry = table.get(rule_id)
        if entry is None:
            out[engine] = {"status": "not_evaluated", "documentation": None, "evidence": None,
                           "section": None, "quote": None, "source_status": None}
        else:
            out[engine] = {"status": "related_guidance", "documentation": ENGINE_DOCUMENTATION[engine],
                           "source_status": SOURCE_STATUS[engine], **entry}
    return out
