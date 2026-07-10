"""
RB-1 (T029) hint arm -- hints render as "treat as authoritative" prompt context, so the fold
door accepts them only from a sender whose trust grant can send kind="hint". Fail-closed:
unknown / quarantined / expired ids drop silently (a dropped hint is cheap; injected
"authoritative" context is not). The gate keys on the bus-stamped `frm` mirror (from_agent),
never on sender-populated meta.

Run: py -m pytest tests/test_context_hints_gate.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import context_hints


def setup_function(_fn):
    context_hints.clear_all()


def test_hint_from_unknown_id_is_dropped():
    ok = context_hints.push("deepseek", "file", "x.py:1 -- do this", from_agent="malicious-agent")
    assert not ok, "unknown id resolves quarantined -> hint refused at the fold door"
    assert context_hints.drain("deepseek") == [], "nothing folded"


def test_hint_from_claude_folds():
    assert context_hints.push("deepseek", "file", "x.py:1 real fact", from_agent="claude")
    hints = context_hints.drain("deepseek")
    assert hints and hints[0]["from"] == "claude"


def test_hint_from_deepseek_folds():
    # Pins the ACL renewal: the 07-05 record's expires_at quarantined the WHOLE admin grant
    # on 07-09; a valid durable grant must let the fleet's designed hint flow work.
    assert context_hints.push("claude", "state", "T029 wave1 status", from_agent="deepseek")
    hints = context_hints.drain("claude")
    assert hints and hints[0]["from"] == "deepseek"


def test_hint_with_default_sender_is_dropped():
    assert not context_hints.push("deepseek", "k", "v"), \
        "no sender identity -> quarantined -> refused (deny-by-default)"


def test_member_consultant_cannot_inject_hints():
    # member grants carry chat/note/reply/handoff/request -- deliberately NOT hint:
    # design consultants advise on the bus; they do not inject authoritative context.
    assert not context_hints.push("claude", "k", "v", from_agent="deepseek-ui")


# ---- R8 (T029 tier-2): ring-overflow loss under fold pressure -----------------
# The context_hints ring has maxlen=8. When ledger_update folds and hints arrive in
# the same turn batch, hints can be evicted by the ring before the agent drains them.
# Kill: a pinned hint evicted by a flood, or unbounded growth.
# Fix design (battery Class 2 Wave 2): dedup-by-key dict (latest-per-key, lossless
# within the key namespace) or surface "N hints dropped" on overflow.
# Authored by deepseek (tier-2 fenced handoff, bus reply 1783688456583-0);
# materialized + reviewed by claude.

def test_ring_evicts_oldest_under_flood():
    """HINT_MAX_PER_AGENT=8: the 9th hint evicts the oldest. Pin the bound IS 8."""
    for i in range(10):
        context_hints.push("flood", f"key{i}", f"val{i}", from_agent="claude")
    hints = context_hints.drain("flood")
    assert len(hints) == 8, "ring cap = 8; oldest 2 evicted"
    assert hints[0]["key"] == "key2", "oldest entries (key0, key1) evicted"
    assert hints[-1]["key"] == "key9", "newest entry preserved"


def test_ring_eviction_is_silent():
    """The ring drops oldest silently -- no 'dropped' signal to the caller.
    This IS the R8 defect: the agent has no way to know it lost hints.
    Post-fix expectation: drain returns a dropped count or the ring becomes a
    dedup-by-key dict -- update this pin to the new contract when the fix lands."""
    for i in range(16):
        context_hints.push("silent", f"k{i}", f"v{i}", from_agent="claude")
    hints = context_hints.drain("silent")
    assert len(hints) == 8
    assert all(int(h["key"][1:]) >= 8 for h in hints), \
        "first 8 hints silently evicted -- R8 ring-overflow loss"


def test_ring_overflow_does_not_grow_unbounded():
    """The ring is a deque with maxlen -- memory is bounded. Verify it stays
    bounded under sustained pressure (no unbounded growth)."""
    for i in range(1000):
        context_hints.push("sustained", f"k{i % 20}", f"v{i}", from_agent="claude")
    assert context_hints.pending_count("sustained") <= 8, \
        "ring stays bounded even under 1000 pushes"


def test_hint_sender_trust_gate_still_works_under_flood():
    """RB-1 gate must still reject untrusted hints even during a flood."""
    ok = context_hints.push("flood2", "good_k", "good_v", from_agent="claude")
    assert ok
    not_ok = context_hints.push("flood2", "bad_k", "bad_v", from_agent="evil")
    assert not not_ok, "RB-1 gate: untrusted hint rejected regardless of ring state"
    hints = context_hints.drain("flood2")
    assert len(hints) == 1 and hints[0]["key"] == "good_k"
