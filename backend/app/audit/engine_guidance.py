"""Search-engine-specific evidence mappings.

This is a *documented overlap*, not a claim of complete crawler parity.
Unknown rules are intentionally marked unverified, never inferred from Google.
"""
from __future__ import annotations

ENGINE_DOCUMENTATION = {
    "google": "https://developers.google.com/search/docs/essentials",
    "bing": "https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a",
    "brave": "https://search.brave.com/help/brave-search-crawler",
}

# Specific documented behavior, only where the engine publicly describes it.
BING_DOCUMENTED = frozenset({
    "http_5xx", "http_4xx", "fetch_error", "robots_blocks_site",
    "robots_unreachable", "noindex", "blocked_by_robots",
    "canonical_invalid", "canonical_broken", "duplicate_content",
    "title_missing", "broken_internal_link", "sitemap_invalid",
    "sitemap_non_indexable",
})
BRAVE_DOCUMENTED = frozenset({
    "noindex", "robots_blocks_site", "blocked_by_robots",
})
# Not supported as a claim of documented engine-specific ranking criteria.
ENGINE_STATES = ("related_guidance", "not_evaluated")


def engine_guidance(rule_id: str) -> dict:
    """Return per-engine evidence, without transferring Google claims to Bing/Brave."""
    # This module is only invoked for IDs from the registered audit catalogue.
    return {
        engine: {
            "status": ("related_guidance" if rule_id in ids else "not_evaluated"),
            "documentation": ENGINE_DOCUMENTATION[engine]
                if rule_id in ids else None,
        }
        for engine, ids in (
            ("bing", BING_DOCUMENTED),
            ("brave", BRAVE_DOCUMENTED),
        )
    }
