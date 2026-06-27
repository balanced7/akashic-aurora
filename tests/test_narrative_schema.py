"""
Tests for the narrative schema (Slice 0). Pure data shapes — no behavior yet.

Run: py tests/test_narrative_schema.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrative.schema import (
    Beat, Chapter, Track, Theme, Atlas, Edge,
    BEAT_KINDS, DEFAULT_WEIGHT, clamp_weight, valid_relationship,
    validate_beat, validate_edge,
    beat_key, chapter_key, track_key, theme_key, ATLAS_KEY,
)


def test_keys():
    assert beat_key("b1") == "narr:beat:b1"
    assert chapter_key("c1") == "narr:chapter:c1"
    assert track_key("ai-setup") == "narr:track:ai-setup"
    assert theme_key("local-first") == "narr:theme:local-first"
    assert ATLAS_KEY == "narr:atlas:current"
    print("  key helpers OK")


def test_edges_validate_against_real_vocabulary():
    # real short-names from the 66-type framework
    for real in ("part_of", "precedes", "causes", "member_of", "influences", "replaces"):
        assert valid_relationship(real), f"{real} should be a real relationship"
        assert Edge(real, "x").is_valid()
    # invented names must be rejected (names-must-not-lie enforced)
    for fake in ("led_to", "inspired_by", "is_about", "supersedes", "not_a_rel"):
        assert not valid_relationship(fake), f"{fake} should NOT validate"
        assert validate_edge(Edge(fake, "x")), "invalid edge must report a problem"
    print("  edges validate against the real relationship vocabulary OK")


def test_weight_and_kinds():
    assert clamp_weight(9) == 5 and clamp_weight(-3) == 0 and clamp_weight("nope") == 1
    assert DEFAULT_WEIGHT["milestone"] == 5 and DEFAULT_WEIGHT["note"] == 1
    assert set(BEAT_KINDS) == set(DEFAULT_WEIGHT.keys())
    print("  narrative weight + kinds OK")


def test_beat_roundtrip_and_validation():
    b = Beat(
        id="beat_1", at="2026-06-27T15:00:00", kind="learning",
        summary="recorded the narrative prior-art", source="learn:experiment:narrative_memory_prior_art",
        weight=4, track="research", themes=["local-first"],
        relates=[Edge("member_of", "narr:theme:local-first"), Edge("part_of", "narr:chapter:c1")],
        chapter="narr:chapter:c1",
    )
    assert validate_beat(b) == [], "a well-formed beat has no problems"
    again = Beat.from_dict(b.to_dict())
    assert again == b, "beat must round-trip through dict"
    assert isinstance(again.relates[0], Edge)
    # a source-less beat with a bad kind + invalid edge is caught
    bad = Beat(id="x", at="t", kind="bogus", summary="", source="", weight=99,
               relates=[Edge("led_to", "y")])
    probs = validate_beat(bad)
    assert any("kind" in p for p in probs) and any("source" in p for p in probs) \
        and any("weight" in p for p in probs) and any("led_to" in p for p in probs)
    print("  beat round-trip + validation OK")


def test_other_nodes_roundtrip():
    c = Chapter(id="c1", track="research", title="Narrative prior-art",
                span_start="2026-06-27T14:00:00", beats=["beat_1"],
                relates=[Edge("precedes", "narr:chapter:c2")], recorded_at="2026-06-27T16:00:00")
    assert Chapter.from_dict(c.to_dict()) == c
    t = Track(id="research", title="Research", domain="research", chapters=["c1"])
    assert Track.from_dict(t.to_dict()) == t
    th = Theme(id="local-first", title="Local-first / no-cloud", beats=["beat_1"])
    assert Theme.from_dict(th.to_dict()) == th
    a = Atlas(generated_at="2026-06-27T16:00:00", summary="the journey", tracks=["research", "ai-setup"])
    assert Atlas.from_dict(a.to_dict()) == a
    print("  Chapter/Track/Theme/Atlas round-trip OK")


def main():
    print("=" * 60)
    print("NARRATIVE SCHEMA TESTS (Slice 0)")
    print("=" * 60)
    test_keys()
    test_edges_validate_against_real_vocabulary()
    test_weight_and_kinds()
    test_beat_roundtrip_and_validation()
    test_other_nodes_roundtrip()
    print("\n" + "=" * 60)
    print("ALL NARRATIVE SCHEMA TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
