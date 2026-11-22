"""Strict editorial context detection for existing link opportunities."""
from app.services.link_context import link_context


def test_link_context_finds_quoteable_passage():
    d = link_context("Eine Keramik Arbeitsplatte ist pflegeleicht. Die Küche kann geräumig sein.", ["keramik", "arbeitsplatte"])
    assert d is not None
    assert "Keramik Arbeitsplatte" in d["context_snippet"]
    assert d["anchor_candidate"] == "Keramik Arbeitsplatte"


def test_link_context_rejects_scattered_matches():
    text = "Keramik wird in der Küche eingesetzt. Eine Arbeitsplatte aus Holz gibt es auch."
    assert link_context(text, ["keramik", "arbeitsplatte"]) is None


def test_link_context_does_not_invent_anchor():
    assert link_context("", ["keramik", "arbeitsplatte"]) is None
    assert link_context("Keramik Arbeitsplatte", ["keramik", "arbeitsplatte"]) is None
    assert link_context("Eine Keramik Arbeitsplatte ist pflegeleicht.", ["keramik"]) is None
