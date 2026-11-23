"""Regression tests for audit rule provenance and transparent classification."""
from types import SimpleNamespace

from app.audit.analysis import calculate_profile_scores
from app.audit.rules import (
    PROFILE_RULE_IDS,
    RULE_CLASSIFICATIONS,
    RULES,
    classify_rule,
    rule_dict,
    rule_profiles,
    rule_provenance,
)


def test_every_rule_has_valid_provenance():
    assert len(RULES) >= 95
    assert all(classify_rule(rule_id) in RULE_CLASSIFICATIONS for rule_id in RULES)


def test_provenance_is_in_serialized_rule():
    for rule_id in RULES:
        data = rule_dict(rule_id)
        assert data["classification"] == classify_rule(rule_id)
        assert data["classification_label"]
        assert "google_documentation" in data
        assert "google_requirement" in data
        assert data["profiles"] == list(rule_profiles(rule_id))


def test_profiles_only_include_explicit_engine_guidance():
    assert rule_profiles("thin_content") == ()
    assert rule_profiles("noindex") == ("google", "bing", "brave")
    assert rule_profiles("geo_llms_missing") == ("geo",)
    assert "robots_blocks_site" in PROFILE_RULE_IDS["bing"]
    assert "robots_blocks_site" in PROFILE_RULE_IDS["brave"]
    assert "title_missing" in PROFILE_RULE_IDS["google"]
    assert "title_missing" in PROFILE_RULE_IDS["bing"]
    assert "title_missing" not in PROFILE_RULE_IDS["brave"]
    assert "thin_content" not in PROFILE_RULE_IDS["google"]


def test_profile_scores_only_penalize_rules_in_the_selected_profile():
    pages = [
        SimpleNamespace(id=1, is_html=True, status_code=200, blocked_by_robots=False),
        SimpleNamespace(id=2, is_html=True, status_code=200, blocked_by_robots=False),
    ]
    scores = calculate_profile_scores(pages, [
        (1, "title_missing", "high"),
        (1, "noindex", "low"),
        (None, "robots_blocks_site", "critical"),
        (None, "geo_llms_missing", "low"),
    ])

    assert scores["google"]["score"] == 84.5
    assert scores["bing"]["score"] == 84.5
    assert scores["brave"]["score"] == 89.5
    assert scores["geo"]["score"] == 99.5


def test_non_google_thresholds_are_not_claimed_as_google_rules():
    for rule_id in ("thin_content", "title_too_long", "description_too_long",
                    "h1_multiple", "canonical_missing", "robots_missing",
                    "schema_none"):
        assert classify_rule(rule_id) == "seo_heuristic"
        assert rule_provenance(rule_id)["google_requirement"] is False


def test_geo_hypotheses_are_not_google_ranking_factors():
    for rule_id in RULES:
        if rule_id.startswith("geo_"):
            assert classify_rule(rule_id) == "geo_experiment"
            assert rule_provenance(rule_id)["google_documentation"] is None


def test_unknown_rules_fail_closed():
    import pytest
    with pytest.raises(KeyError):
        classify_rule("not_a_registered_rule")
