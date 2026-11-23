"""Regression tests for audit rule provenance and transparent classification."""
from app.audit.rules import (
    RULE_CLASSIFICATIONS,
    RULES,
    classify_rule,
    rule_dict,
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
