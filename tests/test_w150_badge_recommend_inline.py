"""W150 pins: the badge's earned-by lessons carry their content, not just their names.

The wish (docs/WISHLIST.md W150): boot said the badge was earned by
wake_drain_the_lane_you_ARMED_not_the_one_docs_name -- the exact lesson about the exact
thing that broke that session -- and its content only reached the seat later via
recall-at. The badge block is the one place boot already knows which lessons define
THIS seat; ~15 tokens each buys the payload at the moment of identity.

Reconciled contract (claude half + deepseek fence half, 2026-08-13):
  B1 each receipt renders slug + a clipped clause of its lesson's recommendation;
  B2 a missing/unreachable lesson renders the slug ALONE -- no exception, and one bad
     slug cannot break the other receipts or the boot (deepseek: wrap per-receipt);
  B3 long recommendations clip to a bounded line; the drill line stays;
  B4 non-residents render "" unchanged;
  layering: core/fleet must NOT import agent_cli for _clip (cycle) -- local clip.
"""
import pytest

from core.fleet import residents


RECEIPTS = ["wake_drain_the_lane_you_ARMED_not_the_one_docs_name",
            "operator_speech_hides_in_queue_operation_records"]

REC1 = ("Use when a wake watcher insta-fires on a stable pending count: drain the lane "
        "you ARMED, not the one the docs name. BIFROST_WAKE_LANE=X implies "
        "BIFROST_CONSUME_LANE=X; peeking the shared cursor lies to you about the lane.")


@pytest.fixture
def resident(monkeypatch):
    monkeypatch.setattr(residents, "get",
                        lambda agent_id: {"receipts": list(RECEIPTS)})
    monkeypatch.setattr(residents, "designation",
                        lambda agent_id: "Anthropic | Amber | Blue | 1 - Vandor")
    monkeypatch.setattr(residents, "current_role", lambda agent_id: None)
    return monkeypatch


def test_b1_receipts_carry_their_recommendation(resident):
    lookup = {RECEIPTS[0]: {"recommendation": REC1},
              RECEIPTS[1]: {"recommendation": "Queue operation records hide operator speech."}}
    block = residents.boot_block("claude", lesson_lookup=lambda slug: lookup[slug])
    assert RECEIPTS[0] in block
    assert "drain the lane" in block           # the payload, inline
    assert "hide operator speech" in block.lower() or "operator speech" in block


def test_b2_missing_lesson_degrades_to_slug_alone(resident):
    """One unreachable lesson: its slug still renders, the OTHER receipt still gets
    its payload, boot completes. Both the empty-record and the raising-store shape."""
    lookup = {RECEIPTS[0]: {},                       # recorded but empty
              RECEIPTS[1]: {"recommendation": "Queue records."}}
    block = residents.boot_block("claude", lesson_lookup=lambda slug: lookup[slug])
    assert RECEIPTS[0] in block
    assert "Queue records." in block

    def explode(slug):
        raise ConnectionError("store down")
    block2 = residents.boot_block("claude", lesson_lookup=explode)
    assert RECEIPTS[0] in block2 and RECEIPTS[1] in block2
    assert "YOU ARE" in block2


def test_b3_long_recommendation_clips_and_drill_stays(resident):
    lookup = {s: {"recommendation": "x" * 2000} for s in RECEIPTS}
    block = residents.boot_block("claude", lesson_lookup=lambda slug: lookup[slug])
    for line in block.splitlines():
        assert len(line) <= 220, f"unbounded badge line: {len(line)} chars"
    assert "recall --full learn:experiment:" in block   # the drill survives (B3)


def test_b4_non_resident_unchanged(monkeypatch):
    monkeypatch.setattr(residents, "get", lambda agent_id: None)
    assert residents.boot_block("nobody") == ""


def test_b5_default_lookup_fails_open(resident, monkeypatch):
    """No injected lookup + no reachable store: the block still renders with bare
    slugs -- the badge NEVER costs a boot."""
    import core.learning.learning_store as ls
    def explode(*a, **kw):
        raise ConnectionError("redis down")
    monkeypatch.setattr(ls, "get_learning_store_instance", explode)
    block = residents.boot_block("claude")
    assert "YOU ARE" in block
    assert RECEIPTS[0] in block
