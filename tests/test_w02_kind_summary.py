"""W02 pins — per-kind unread summary in the bifrost-sync collapsed view.

Wish W02 (kimi F9): the collapsed view showed a fold but not a per-kind census, so triage
needed a SECOND call with --traces to learn whether an ASK was buried under trace spam.
A one-line summary at the header answers "is there anything I must ANSWER?" in one read.

Buckets (by what the seat must DO): asks (request/question/handoff/blocker -- need a reply),
fyi (inform/note/reply/completion/decision/hint -- read, no reply), traces (trace/steer/
nudge/ledger_update -- telemetry/control). Unknown kinds bucket to fyi (fail toward showing).

  P1  counts by bucket, ordered asks-first (the thing that matters leads)
  P2  the render line names only NON-ZERO buckets, asks always shown when > 0
  P3  empty -> "" (no line); the section already handles the zero case
  P4  an ask buried under 9 traces is VISIBLE in the summary (the W02 trigger)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.bifrost_pull import kind_summary, render_kind_summary


def _m(kind, frm="x"):
    return {"kind": kind, "frm": frm, "content": "..."}


def test_p1_counts_by_bucket():
    msgs = [_m("question"), _m("handoff"), _m("inform"), _m("trace"), _m("trace")]
    s = kind_summary(msgs)
    assert s == {"asks": 2, "fyi": 1, "traces": 2}


def test_p2_render_nonzero_only_asks_first():
    line = render_kind_summary([_m("handoff"), _m("inform"), _m("trace")])
    assert line == "1 ask / 1 fyi / 1 trace"
    # pluralization + zero-bucket omission
    line2 = render_kind_summary([_m("question"), _m("question"), _m("trace")])
    assert line2 == "2 asks / 1 trace" and "fyi" not in line2


def test_p3_empty_is_silent():
    assert render_kind_summary([]) == ""
    assert kind_summary([]) == {"asks": 0, "fyi": 0, "traces": 0}


def test_p4_buried_ask_is_visible():
    msgs = [_m("trace")] * 9 + [_m("request")]
    line = render_kind_summary(msgs)
    assert line.startswith("1 ask"), "a single ask under 9 traces leads the summary"
    assert "9 traces" in line


def test_p5_unknown_kind_is_fyi():
    assert kind_summary([_m("weird_new_kind")]) == {"asks": 0, "fyi": 1, "traces": 0}
