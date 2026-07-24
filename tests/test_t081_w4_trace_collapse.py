"""T081-W4 PRE-REGISTERED ACCEPTANCE — bifrost_inbox trace collapse.

Committed BEFORE implementation (method-baseline pre-registration; T031 rule practiced).
Cites docs/library/report/20260715_boot-onboarding-ergonomics-reconciliatio_94a21c.md (W4 spec) +
night-build-brief-2026-07-16.md (per-slice method: prior-art pass → design → pins → build →
validate → cross-verify → commit).

Prior art synthesized:
  rsyslog pmlastmsg: consecutive-dedup, first always shown, "last message repeated N times"
  Grafana Loki: collapse at query/render time, not ingest
  OTel tail-sampling: decide per snapshot, don't carry state across observations

Pins:
  W4-P1  Consecutive same-kind traces collapse (5 trace → 1 shown + 4 more)
  W4-P2  Mixed trace kinds each get their own run (thinking + tool interleaved)
  W4-P3  Singleton trace: no collapse
  W4-P4  Work message breaks trace run (trace-work-trace = two separate trace groups)
  W4-P5  Traces only (no mail): trace summary only, no blank header
  W4-P6  Empty inbox: unchanged message
  W4-P7  Work+traces: work shown first and verbatim, traces after separator
  W4-P8  Bus offline: error unchanged

Run: py -m pytest tests/test_t081_w4_trace_collapse.py -q
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Minimal Message dataclass matching the bus.Message shape. The shared render_collapsed
# in agent/bifrost_pull accepts both dict and object messages (_mget tolerant).
@dataclass
class _M:
    kind: str
    frm: str
    content: str = "sample trace content"
    id: str = "0-0"
    to: str = "deepseek"
    ts: str = "2026-07-16T00:00:00"
    meta: Dict[str, Any] = None

    def __post_init__(self):
        if self.meta is None:
            self.meta = {}


def _make_toolbox(agent_id="deepseek", allow_write=False):
    """Lightweight ToolBox for render tests — no confirm, no exec, no trust."""
    from scripts.deepseek_chat import ToolBox
    return ToolBox(ROOT, allow_exec=False, trust=False, allow_secrets=False,
                   confirm=lambda _p: False, agent_id=agent_id,
                   allow_write=allow_write, boot_text="test", boot_sources=[])


def _render(msgs: List[_M]) -> str:
    """Call the shared render_collapsed + join, same as bifrost_inbox does post-refactor."""
    from agent.bifrost_pull import render_collapsed
    lines = render_collapsed(msgs)
    return "\n".join(lines) if lines else "(inbox empty -- no unread messages)"


# ------------------------------------------------------------------ W4-P1: consecutive collapse
def test_w4_p1_consecutive_same_kind_traces_collapse():
    """5 consecutive [trace] from deepseek → one shown, then '4 more trace(s)'."""
    msgs = [_M(kind="trace", frm="deepseek", content=f"trace line {i}")
            for i in range(5)]
    out = _render(msgs)
    assert "[trace] from deepseek: trace line 0" in out, "first trace must be shown"
    assert "4 more trace(s) from deepseek" in out, "must collapse remaining 4"
    assert "trace line 1" not in out, "collapsed traces must not show content"
    assert "trace line 4" not in out, "collapsed traces must not show content"
    assert "--traces to expand" in out, "must hint the expansion flag"


# ------------------------------------------------------------------ W4-P2: mixed trace kinds
def test_w4_p2_mixed_trace_kinds_separate_runs():
    """3 [thinking] + 2 [tool] from claude → each kind gets its own collapse run."""
    msgs = [
        _M(kind="thinking", frm="claude", content="think 1"),
        _M(kind="thinking", frm="claude", content="think 2"),
        _M(kind="thinking", frm="claude", content="think 3"),
        _M(kind="tool", frm="claude", content="tool 1"),
        _M(kind="tool", frm="claude", content="tool 2"),
    ]
    out = _render(msgs)
    assert "think 1" in out, "first thinking must be shown"
    assert "2 more thinking(s) from claude" in out, "thinking collapse"
    assert "tool 1" in out, "first tool must be shown"
    assert "1 more tool(s) from claude" in out, "tool collapse"
    assert "think 2" not in out, "collapsed think content must not appear"
    assert "tool 2" not in out, "collapsed tool content must not appear"


# ------------------------------------------------------------------ W4-P3: singleton no collapse
def test_w4_p3_singleton_trace_no_collapse():
    """Single [trace] from deepseek → shown normally, no 'more' line."""
    msgs = [_M(kind="trace", frm="deepseek", content="lone trace")]
    out = _render(msgs)
    assert "lone trace" in out, "singleton must be shown"
    assert "more" not in out, "no collapse on singleton"
    assert "more trace" not in out, "no collapse on singleton (alt phrasing)"


# ------------------------------------------------------------------ W4-P4: work message breaks trace run
def test_w4_p4_work_message_breaks_trace_run():
    """3 traces, 1 handoff from claude, 2 traces → two separate trace groups."""
    msgs = [
        _M(kind="trace", frm="deepseek", content="a1"),
        _M(kind="trace", frm="deepseek", content="a2"),
        _M(kind="trace", frm="deepseek", content="a3"),
        _M(kind="handoff", frm="claude", content="a handoff"),
        _M(kind="trace", frm="deepseek", content="b1"),
        _M(kind="trace", frm="deepseek", content="b2"),
    ]
    out = _render(msgs)
    # Work line must appear verbatim
    assert "[handoff] from claude: a handoff" in out, "work message must be verbatim"
    # First trace group: a1 shown, 2 more
    assert "a1" in out, "first trace of first group must be shown"
    assert "2 more trace(s) from deepseek" in out, "first group collapse"
    # Second trace group: b1 shown, 1 more
    assert "b1" in out, "first trace of second group must be shown"
    assert "1 more trace(s) from deepseek" in out, "second group collapse"
    # a2 and a3 must NOT appear (collapsed)
    assert "a2" not in out, "collapsed a2 must not appear"
    assert "a3" not in out, "collapsed a3 must not appear"


# ------------------------------------------------------------------ W4-P5: traces only
def test_w4_p5_traces_only_no_blank_header():
    """20 traces, 0 mail → trace summary only, no mail section or blank header."""
    msgs = [_M(kind="trace", frm="deepseek", content=f"t{i}") for i in range(20)]
    out = _render(msgs)
    assert "19 more trace(s)" in out, "must collapse 19"
    assert "t0" in out, "first trace must be shown"
    # No blank line at the top (no mail section)
    lines = out.split("\n")
    assert lines[0].startswith("[trace]"), f"first line must be trace, got: {lines[0]!r}"


# ------------------------------------------------------------------ W4-P6: empty inbox
def test_w4_p6_empty_inbox_unchanged():
    """Empty inbox → unchanged message."""
    out = _render([])
    assert out == "(inbox empty -- no unread messages)", f"empty got: {out!r}"


# ------------------------------------------------------------------ W4-P7: work first
def test_w4_p7_work_shown_first_and_verbatim():
    """Mix of work+traces → work entries shown verbatim and FIRST, traces after separator."""
    msgs = [
        _M(kind="trace", frm="deepseek", content="t1"),
        _M(kind="trace", frm="deepseek", content="t2"),
        _M(kind="chat", frm="claude", content="hello"),
        _M(kind="handoff", frm="claude", content="review this"),
        _M(kind="trace", frm="deepseek", content="t3"),
    ]
    out = _render(msgs)
    lines = out.split("\n")
    # Work messages must appear before traces
    chat_idx = next(i for i, l in enumerate(lines) if "chat" in l)
    handoff_idx = next(i for i, l in enumerate(lines) if "handoff" in l)
    trace_idx = next(i for i, l in enumerate(lines) if "trace" in l)
    assert chat_idx < trace_idx, "chat must appear before traces"
    assert handoff_idx < trace_idx, "handoff must appear before traces"
    # Both work lines must be verbatim
    assert "[chat] from claude: hello" in out
    assert "[handoff] from claude: review this" in out
    # Trace group: t1+t2 collapsed (2 more), t3 is singleton
    assert "1 more trace(s) from deepseek" in out, "first trace group collapse"
    assert "t3" in out, "singleton trace after work must be shown"
    # blank separator between work and traces
    assert "" in lines, "must have blank separator between work and traces"


# ------------------------------------------------------------------ W4-P8: offline
def test_w4_p8_offline_error_unchanged():
    """Bus offline → error message unchanged (tested via direct ToolBox path)."""
    tb = _make_toolbox(agent_id=None)
    out = tb.bifrost_inbox()
    # When agent_id is None, _bus() returns None → the NOT ON BUS error
    assert "ERROR" in out and "Bifrost bus" in out, f"offline got: {out!r}"


# ------------------------------------------------------------------ integration: real bus round-trip
def test_w4_integration_real_bus_traces_collapse():
    """End-to-end: send real trace messages, then peek through bifrost_inbox. Redis-backed;
    skip if Redis is down. Uses a throwaway namespace."""
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        import pytest as _p
        _p.skip("redis not available")

    import uuid
    ns = f"bifrost_w4_int_{uuid.uuid4().hex[:8]}"
    aid = f"deepseek-test-{uuid.uuid4().hex[:4]}"
    os.environ["BIFROST_NAMESPACE"] = ns
    try:
        from core.comm.bus import Bus
        # Register aid
        b_me = Bus(aid)
        b_me.register(ttl=60)
        # Send traces FROM another agent TO aid — own-broadcasts are filtered, so
        # we need a different sender to land in aid's inbox
        b_other = Bus(f"other-{uuid.uuid4().hex[:4]}")
        for i in range(4):
            b_other.send(aid, "trace", f"integration trace {i}",
                         meta={"display_only": True})
        b_other.send(aid, "chat", "real mail message",
                     meta={"via": "test"})
        # Now peek through ToolBox as aid
        tb = _make_toolbox(agent_id=aid)
        out = tb.bifrost_inbox()
        # The chat must appear verbatim
        assert "[chat] from" in out, f"chat must appear: {out}"
        assert "real mail message" in out, f"chat content must appear: {out}"
        # Traces must be collapsed
        assert "3 more trace(s)" in out, f"must collapse 3 traces: {out}"
        assert "integration trace 0" in out, "first trace must be shown"
        # Trace 1-3 must NOT appear
        assert "integration trace 3" not in out, "collapsed traces must not appear"
        # Cleanup
        for key in c.keys(f"{ns}:*"):
            c.delete(key)
    finally:
        del os.environ["BIFROST_NAMESPACE"]


if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
