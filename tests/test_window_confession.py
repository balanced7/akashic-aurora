"""
RB-5 (T029 Wave 2) -- "window truncated" confession everywhere a bound must remain.

Bar (docs/resilience-battery-slices-2026-07.md): no surface shows "unhandled/none" when
the true state is "beyond the window"; boot and the CLI agree on the unhandled threshold;
a bounded read says what it dropped (funnel `events_capped` precedent,
core/recall/funnel.py:292). The ack lookup itself goes EXACT in RB-4 (by-ref index,
gated on deepseek design-review); until it lands, the beyond-window ack read is pinned
here as a strict xfail so the gap stays a visible confession, not a silent one.

Covers: R17 coherence, boot-vs-CLI threshold mismatch, hint-ring overflow (RB-6 overlap).
Run: py -m pytest tests/test_window_confession.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import context_hints, promoter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeQuery:
    """Models the real read bound: newest-first order, honors top_k (eq.search contract),
    and (for RB-4) the exact by-ref lookup the index will provide."""

    def __init__(self, events):
        self.events = events            # newest first, like the empty-query Ranker order

    def search(self, q, kind=None, since=None, until=None, top_k=50):
        return [e for e in self.events if e.get("kind") == kind][:top_k]

    def events_for_ref(self, ref):
        return [e for e in self.events if ref in (e.get("refs") or [])]


def _promoted_rec(mid, to="claude"):
    return {"kind": "bifrost_msg", "at": "t0", "refs": [f"bifrost:{mid}"],
            "detail": {"frm": "alice", "to": to, "kind": "handoff",
                       "content": "please do X", "ts": "t0"}}


# ------------------------------------------------------------- promoted() page confession

def test_promoted_page_confesses_older_records():
    evs = [_promoted_rec(f"{i}-0") for i in range(7)]
    page, more = promoter.promoted_page(limit=5, event_query=FakeQuery(evs))
    assert len(page) == 5 and more is True, \
        "a full page must say older records exist, not under-report silently"
    page, more = promoter.promoted_page(limit=10, event_query=FakeQuery(evs))
    assert len(page) == 7 and more is False, \
        "a page with room left is the whole truth -- no false confession"


# ------------------------------------------------------------- one threshold seam

def test_unhandled_threshold_reads_env_through_one_seam(monkeypatch):
    monkeypatch.setenv("AKASHIC_ACK_UNHANDLED_HOURS", "3")
    assert promoter.unhandled_threshold_hours() == 3
    monkeypatch.setenv("AKASHIC_ACK_UNHANDLED_HOURS", "garbage")
    assert promoter.unhandled_threshold_hours() == promoter.UNHANDLED_HOURS
    monkeypatch.delenv("AKASHIC_ACK_UNHANDLED_HOURS")
    assert promoter.unhandled_threshold_hours() == promoter.UNHANDLED_HOURS


def test_boot_and_cli_share_the_threshold_and_page_seams():
    """Structural guard (comprehensibility-immune-system style): agent_cli must not read
    the threshold env itself (boot silently used the default while the CLI read the env
    -- the RB-5 mismatch), and both renderers must page through promoted_page."""
    src = open(os.path.join(REPO, "agent_cli.py"), encoding="utf-8").read()
    assert "AKASHIC_ACK_UNHANDLED_HOURS" not in src, \
        "threshold env is read ONLY via promoter.unhandled_threshold_hours()"
    assert src.count("promoted_page(") >= 2, \
        "both the promoted CLI verb and the boot digest page with the confession bit"


# ------------------------------------------------------------- hint-ring overflow confession

def setup_function(_fn):
    context_hints.clear_all()


def test_hint_ring_overflow_is_confessed():
    for i in range(12):
        context_hints.push("deepseek", f"h{i}", f"v{i}", from_agent="claude")
    dropped = context_hints.take_dropped("deepseek")
    assert dropped == 4, "12 pushes into a ring of 8 -> 4 evictions counted"
    hints = context_hints.drain("deepseek")
    block = context_hints.format_for_prompt(hints, dropped=dropped)
    assert "4" in block and "dropped" in block, \
        "the drained block confesses the loss instead of silently narrowing"
    assert context_hints.take_dropped("deepseek") == 0, "one confession per drain"


def test_no_overflow_means_no_confession():
    for i in range(3):
        context_hints.push("deepseek", f"h{i}", f"v{i}", from_agent="claude")
    assert context_hints.take_dropped("deepseek") == 0
    block = context_hints.format_for_prompt(context_hints.drain("deepseek"), dropped=0)
    assert "dropped" not in block, "no false confession when nothing was lost"


def test_confession_renders_even_with_no_live_hints():
    block = context_hints.format_for_prompt([], dropped=2)
    assert block and "2" in block and "dropped" in block, \
        "losses are reported even when every surviving hint also expired"
    assert context_hints.format_for_prompt([], dropped=0) == "", \
        "empty ring, no losses -> no block at all (unchanged contract)"


def test_clear_all_resets_the_drop_ledger():
    for i in range(12):
        context_hints.push("deepseek", f"h{i}", f"v{i}", from_agent="claude")
    context_hints.clear_all()
    assert context_hints.take_dropped("deepseek") == 0


# ------------------------------------------------------------- RB-4 (pending) exact ack lookup

@pytest.mark.xfail(strict=True,
                   reason="RB-4 by-ref exact ack lookup -- build gated on deepseek "
                          "design-review (T029 Wave 2); flips green when acks_for "
                          "switches to events_for_ref")
def test_ack_beyond_the_500_window_still_reads_handled():
    """S2/R17 root: acks_for pulls the newest-500 msg_ack records then filters, so once
    >500 acks exist the FIRST-acked message reads as never-handled (false UNHANDLED
    re-flag). RB-4's acceptance: it still reads handled."""
    first_ack = {"kind": "msg_ack", "at": "t0", "refs": ["bifrost:m0"],
                 "detail": {"by": "claude", "msg_id": "m0", "note": "handled long ago"}}
    newer = [{"kind": "msg_ack", "at": f"t{i+1}", "refs": [f"bifrost:m{i+1}"],
              "detail": {"by": "claude", "msg_id": f"m{i+1}", "note": ""}}
             for i in range(520)]
    q = FakeQuery(list(reversed(newer)) + [first_ack])   # newest first; m0's ack oldest
    acks = promoter.acks_for(["m0"], event_query=q)
    assert acks["m0"], "the oldest settled message must still read as handled (exact lookup)"
