"""T061 PRE-REGISTERED ACCEPTANCE -- an ANSWERED directed ask must never redrive.

Root cause (note t061-root-cause, confirmed on evidence 2026-07-14): answers arriving as
kind=HANDOFF (pointer+verdict per packet law) never settle a reply-anchored expectation --
the settle predicate counted only kind=reply. Six armed expectations for ANSWERED handoffs
redrove ~4 times; deepseek deduped from ledger state, then correctly escalated.

Fix under pin: expectations settle on ANY directed ANSWER-shaped message from the target
after the anchor -- ANSWER_KINDS = {reply, handoff, completion}. "note" is deliberately
EXCLUDED: RB-29 timeout/error notes must keep the expectation armed so the redrive fires
(a timeout reply never acks a handoff -- T026 doctrine).

Redis-backed, throwaway namespace per test (BIFROST_NAMESPACE is read per-call by both
the expectations module and Bus). Run: py -m pytest tests/test_t061_settle_linkage.py -q
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import expectations
from core.comm.bus import Bus


def _redis_up():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    return connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                           timeout_seconds=3, decode_responses=True) is not None


def _ns(monkeypatch):
    if not _redis_up():
        pytest.skip("redis not available")
    ns = f"bifrost_t061_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def test_b1_linked_handoff_settles_exactly(monkeypatch):
    """The incident class: a directed HANDOFF carrying meta.answers=<oid> IS the answer --
    it must settle that exact expectation."""
    _ns(monkeypatch)
    assert expectations.arm("claude", "100-0", "deepseek", "handoff", "review this", 3600)
    Bus("deepseek").send("claude", "handoff", "verdict filed: GREEN",
                         meta={"answers": "100-0"})
    out = expectations.sweep("claude")
    assert "100-0" in out["cleared"], f"linked handoff must settle its ask, got {out}"


def test_b2_unlinked_handoff_fifo_clears_oldest(monkeypatch):
    """The 2026-07-14 shape verbatim: 'R7 design filed' handoffs carried NO answers meta.
    An unlinked directed handoff from the target clears the OLDEST expectation on that
    target (one per message); newer ones stay armed."""
    _ns(monkeypatch)
    assert expectations.arm("claude", "200-0", "deepseek", "handoff", "ask one", 3600)
    assert expectations.arm("claude", "201-0", "deepseek", "handoff", "ask two", 3600)
    Bus("deepseek").send("claude", "handoff", "design filed: research/reviewed/x.md")
    out = expectations.sweep("claude")
    assert out["cleared"] == ["200-0"], f"exactly the OLDEST must clear, got {out['cleared']}"
    c = expectations._client()
    assert c.hget(f"{expectations._key('claude')}", "201-0"), "the newer ask stays armed"


def test_b3_note_never_settles(monkeypatch):
    """RB-29 doctrine preserved: a timeout/error NOTE keeps the expectation armed so the
    redrive fires. Notes must not settle, linked or not."""
    _ns(monkeypatch)
    assert expectations.arm("claude", "300-0", "deepseek", "request", "answer me", 3600)
    Bus("deepseek").send("claude", "note", "(runner timed out -- abandoned)")
    out = expectations.sweep("claude")
    assert out["cleared"] == [], f"a note must never settle an expectation, got {out}"
    c = expectations._client()
    assert c.hget(f"{expectations._key('claude')}", "300-0"), "expectation stays armed"


def test_b4_completion_settles_and_wrong_agent_immune(monkeypatch):
    """A completion from the target settles (FIFO); an unlinked handoff from a DIFFERENT
    agent never touches expectations armed on the target."""
    _ns(monkeypatch)
    assert expectations.arm("claude", "400-0", "deepseek", "request", "do the thing", 3600)
    Bus("cursor").send("claude", "handoff", "unrelated ask from cursor")
    out1 = expectations.sweep("claude")
    assert out1["cleared"] == [], "another agent's handoff must not clear deepseek's slot"
    Bus("deepseek").send("claude", "completion", "done: the thing")
    out2 = expectations.sweep("claude")
    assert out2["cleared"] == ["400-0"], f"completion settles the ask, got {out2}"


def test_b5_broadcast_answer_kinds_never_settle(monkeypatch):
    """Broadcast handoffs/replies are room chatter, never answers (bc stays pinned at
    tail) -- extending the settle kinds must not widen the broadcast hole."""
    _ns(monkeypatch)
    assert expectations.arm("claude", "500-0", "deepseek", "request", "answer me", 3600)
    Bus("deepseek").broadcast("handoff", "to the room: something shipped")
    Bus("deepseek").broadcast("reply", "room chatter reply")
    out = expectations.sweep("claude")
    assert out["cleared"] == [], f"broadcasts must never settle, got {out}"


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t061_settle_linkage.py -q")
