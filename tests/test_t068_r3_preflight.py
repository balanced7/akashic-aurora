"""T068-R3 PRE-REGISTERED ACCEPTANCE -- the pre-flight assertion runner.

Design half: docs/library/report/20260715_deepseek-t068-r3-design-pre-flight-asser_5eb933.md (deepseek M10 --
"the seat this gate protects"). Claude builds; deepseek live-drills (fabricated cite ->
HOLD fires). The gate verifies a directed answer's FACTUAL claims before it leaves the
runner: A1 file:line cites resolve, A2 evidence events exist, A3 closure language names
a pin/task/commit (warning only). Two-cycle fail-open: losing a reply is the worse bug.

Pins P1-P9 per the design Part (e). Unit pins hit core/comm/assertions.py directly;
integration pins drive the runner's _process_one with a fake bus (the msg_ack pattern).

Run: py -m pytest tests/test_t068_r3_preflight.py -q
"""
import os
import sys
from types import SimpleNamespace

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import assertions


def _gate_on(monkeypatch):
    monkeypatch.setenv("BIFROST_PREFLIGHT_ASSERT", "1")


# ------------------------------------------------------------------ unit: the assertions
def test_p1_valid_citations_pass(monkeypatch):
    _gate_on(monkeypatch)
    held, feedback, warnings = assertions.run_preflight(
        "The fix is at core/comm/assertions.py:1 and pins P1-P9 are green (T068).")
    assert not held, f"valid cites must pass, got feedback: {feedback}"


def test_p2_p3_fabricated_file_and_oob_line_hold(monkeypatch):
    _gate_on(monkeypatch)
    held, feedback, _ = assertions.run_preflight(
        "Root cause at docs/this-file-does-not-exist-9x7.md:42.")
    assert held and "does not exist" in feedback, f"fabricated file must HOLD, got {feedback!r}"
    held2, feedback2, _ = assertions.run_preflight(
        "See core/comm/assertions.py:999999 for the fix.")
    assert held2 and "out of bounds" in feedback2, f"OOB line must HOLD, got {feedback2!r}"


def test_p4_fake_event_held(monkeypatch):
    _gate_on(monkeypatch)
    held, feedback, _ = assertions.run_preflight(
        "Evidence: event:events:raw:999999999999999-0 shows the dual delivery.")
    assert held and "event" in feedback.lower(), f"fabricated event must HOLD, got {feedback!r}"


def test_p8_closure_without_pin_warns_but_does_not_hold(monkeypatch):
    _gate_on(monkeypatch)
    held, _, warnings = assertions.run_preflight("The bug is fixed and shipped.")
    assert not held, "A3 is WARNING-level, never a hold"
    assert warnings, "closure language without pin/task/commit must warn"
    held2, _, warnings2 = assertions.run_preflight("Fixed -- pins P1-P3 green, T068 @ 20003c7.")
    assert not held2 and not warnings2, "closure WITH references is clean"


def test_p7_kill_switch_disables(monkeypatch):
    monkeypatch.setenv("BIFROST_PREFLIGHT_ASSERT", "0")
    held, feedback, warnings = assertions.run_preflight(
        "Cites docs/this-file-does-not-exist-9x7.md:42 and event:events:raw:9-9.")
    assert not held and not warnings, "kill switch must disable ALL assertions (fail-open)"


# ------------------------------------------------------- integration: the runner gate
def _run(monkeypatch, reply_text, second_reply=None, kind_to="claude", broadcast=False):
    """Drive _process_one with a fake bus; returns (sent_replies, sent_notes, respond_calls)."""
    import scripts.bifrost_runner_deepseek as runner
    from core.comm import promoter
    monkeypatch.setattr(promoter, "ack", lambda *a, **k: True)
    sent_replies, sent_other, bcasts = [], [], []
    bus = SimpleNamespace(
        send=lambda to, kind, content, **k: sent_other.append((to, kind, content)),
        send_reply=lambda to, content, **k: sent_replies.append((to, content)),
        broadcast=lambda kind, content, **k: bcasts.append((kind, content)))
    args = SimpleNamespace(agent="deepseek", agentic=False, model="m")
    rate = SimpleNamespace(allow=lambda: True)
    calls = []

    def respond(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return reply_text
        return second_reply if second_reply is not None else reply_text
    msg = SimpleNamespace(kind="handoff", frm="claude", to=("*" if broadcast else "deepseek"),
                          id="424242-0", content="do the thing", meta={})
    runner._process_one(msg, bus, args, respond, rate)
    return sent_replies, sent_other, bcasts, calls


def test_p2_integration_fabricated_cite_held_then_fixed(monkeypatch):
    _gate_on(monkeypatch)
    good = "Done -- see core/comm/assertions.py:1, pins P1 green (T068)."
    bad = "Done -- see docs/this-file-does-not-exist-9x7.md:42."
    replies, _, _, calls = _run(monkeypatch, bad, second_reply=good)
    assert len(calls) == 2, "the agent must get ONE fix round on a HOLD"
    assert len(replies) == 1 and "assertions.py" in replies[0][1], \
        "the FIXED reply is what ships"


def test_p9_double_fail_sends_anyway_loud(monkeypatch, capsys):
    _gate_on(monkeypatch)
    bad = "Root cause at docs/this-file-does-not-exist-9x7.md:42."
    replies, _, _, calls = _run(monkeypatch, bad, second_reply=bad)
    assert len(calls) == 2 and len(replies) == 1, "after two failed cycles the reply STILL ships"
    err = capsys.readouterr().err
    assert "PRE-FLIGHT" in err and "sending anyway" in err, "the fail-open must be LOUD"


def test_p5_note_skips_assertions(monkeypatch):
    _gate_on(monkeypatch)
    import scripts.bifrost_runner_deepseek as runner
    from core.comm import promoter
    monkeypatch.setattr(promoter, "ack", lambda *a, **k: True)
    sent = []
    bus = SimpleNamespace(send=lambda to, kind, content, **k: sent.append((kind, content)),
                          send_reply=lambda *a, **k: pytest.fail("notes never ride send_reply"),
                          broadcast=lambda *a, **k: None)
    args = SimpleNamespace(agent="deepseek", agentic=False, model="m")
    boom = lambda prompt: (_ for _ in ()).throw(RuntimeError("api down"))
    msg = SimpleNamespace(kind="handoff", frm="claude", to="deepseek", id="424243-0",
                          content="cites docs/this-file-does-not-exist-9x7.md:42", meta={})
    runner._process_one(msg, bus, args, boom, SimpleNamespace(allow=lambda: True))
    assert sent and sent[0][0] == "note", "error notes go out FAST, no assertion involvement"


def test_p6_broadcast_skips_assertions(monkeypatch):
    _gate_on(monkeypatch)
    bad = "Cites docs/this-file-does-not-exist-9x7.md:42."
    replies, _, bcasts, calls = _run(monkeypatch, bad, broadcast=True)
    assert len(calls) == 1 and bcasts and not replies, \
        "broadcast replies skip the gate entirely (room chatter)"


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t068_r3_preflight.py -q")
