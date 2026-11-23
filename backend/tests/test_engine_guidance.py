"""Search-engine evidence must not imply undocumented requirements."""
from app.audit.rules import RULES, rule_dict
from app.audit.engine_guidance import engine_guidance, ENGINE_STATES


def test_all_rules_have_engine_specific_entries():
    assert len(RULES) == 117
    for rule_id in RULES:
        evidence = rule_dict(rule_id)["search_engines"]
        assert set(evidence) == {"bing", "brave"}
        for row in evidence.values():
            assert row["status"] in ENGINE_STATES
            if row["status"] == "not_evaluated":
                assert row["documentation"] is None


def test_brave_has_no_invented_llms_or_indexnow_rules():
    for rule_id in ("geo_llms_missing", "title_too_long", "schema_none"):
        assert engine_guidance(rule_id)["brave"]["status"] == "not_evaluated"


def test_documented_robots_behavior_is_not_mistaken_for_noindex():
    assert engine_guidance("robots_blocks_site")["brave"]["status"] == "related_guidance"
    assert engine_guidance("noindex")["brave"]["status"] == "related_guidance"
