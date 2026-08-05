"""PRE-REGISTERED ACCEPTANCE (T169) -- a seat that runs out of budget must still answer.

MEASURED in the T166 fire drill, 2026-08-04. Four seats received their brief (`FIRE DRILL` appears
in all four logs) and ZERO issued a send. `deepseek-red` hit the stop TWICE:

    [stopped: hit 30 tool rounds]

`scripts/deepseek_chat.py` ends that loop with `return ""`. The empty string IS the loss. Red had
produced 109KB of correct wedge analysis -- including a right trace of how a runner reaches
"running with a dead pulse" -- and none of it left the log.

THE INCENTIVE IS BACKWARDS AND THAT IS WHY THIS IS A BLOCKER. The more a seat investigates, the
more rounds it spends; the more rounds it spends, the likelier it returns nothing. For a research
fleet, the seats doing the best work are the most likely to deliver silence. Season 1 cannot score
what it never receives.

THE FIX IS NOT A BIGGER BUDGET. A bigger budget moves the cliff; it does not remove it. On
exhaustion the agent makes ONE more model call with TOOLS DISABLED and an explicit instruction to
answer now from what it already has. Total loss becomes a partial answer, and partial answers are
scoreable.

F5 exists because the obvious fix has an obvious trap: if the forced call itself fails, returning
"" again would reinstate the silent loss one layer up. Something must always come back.

  F1  on exhaustion, send() returns a NON-EMPTY answer
  F2  the forced final call runs with tools DISABLED         (no 31st tool round)
  F3  the answer is MARKED as budget-truncated               (a reader must know it is partial)
  F4  a normal turn is unchanged                             (no regression on the common path)
  F5  if the forced call itself fails, something still comes back, never ""

Run: py -m pytest tests/test_t169_budget_exhaustion_still_answers.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import deepseek_chat as DC  # noqa: E402


class _Box:
    """Minimal ToolBox stand-in: every tool call succeeds and returns a short string."""
    _clarify_count = 0

    def execute(self, name, args):
        return "ok"


def _agent(turns, tools_enabled=True):
    """An Agent whose _stream_turn is scripted. `turns` is a list of (content, tool_calls)."""
    a = DC.Agent.__new__(DC.Agent)
    a.messages = []
    a.model = "fake"
    a.think = False
    a.tools_enabled = tools_enabled
    a.toolbox = _Box()
    a.interrupt = None
    a.inject = None
    a._seen = []
    seq = list(turns)

    def _stream_turn():
        a._seen.append(dict(tools_enabled=a.tools_enabled))
        return seq.pop(0) if seq else ("", [])

    a._stream_turn = _stream_turn
    a._mark_context = lambda *_a, **_k: None
    return a


def _toolcall(i):
    return ("", [{"id": f"c{i}", "name": "read_file", "arguments": "{}"}])


def test_f1_exhaustion_still_returns_an_answer():
    """The bug: 30 tool rounds then `return ""`, and 109KB of analysis is gone."""
    a = _agent([_toolcall(i) for i in range(DC.MAX_TOOL_ROUNDS)] + [("PARTIAL ANSWER", [])])
    out = a.send("investigate deeply")
    assert out, "a seat that spent its whole budget returned NOTHING -- the T166 failure"
    assert "PARTIAL ANSWER" in out


def test_f2_the_forced_call_has_tools_disabled():
    """Otherwise the forced hop just spends a 31st round and returns empty again."""
    a = _agent([_toolcall(i) for i in range(DC.MAX_TOOL_ROUNDS)] + [("done", [])])
    a.send("investigate deeply")
    assert a._seen, "no model calls recorded"
    assert a._seen[-1]["tools_enabled"] is False, (
        "the forced final call still had tools enabled -- it can spend another round and "
        "return nothing")


def test_f3_the_answer_is_marked_budget_truncated():
    a = _agent([_toolcall(i) for i in range(DC.MAX_TOOL_ROUNDS)] + [("PARTIAL", [])])
    out = a.send("investigate deeply")
    assert "truncat" in out.lower() or "budget" in out.lower(), (
        f"a partial answer that does not say it is partial will be read as complete: {out!r}")


def test_f4_a_normal_turn_is_unchanged():
    a = _agent([("straight answer", [])])
    assert a.send("hi") == "straight answer"
    assert len(a._seen) == 1, "the common path must not gain an extra model call"


def test_f5_a_failing_forced_call_still_returns_something():
    """The trap in the obvious fix: replacing one silent "" with another."""
    a = _agent([_toolcall(i) for i in range(DC.MAX_TOOL_ROUNDS)])

    def _boom():
        raise RuntimeError("model down")

    calls = {"n": 0}
    orig = a._stream_turn

    def _stream_turn():
        calls["n"] += 1
        if calls["n"] > DC.MAX_TOOL_ROUNDS:
            _boom()
        return orig()

    a._stream_turn = _stream_turn
    out = a.send("investigate deeply")
    assert out, "the forced call failed and the seat went silent again"
    assert "budget" in out.lower() or "truncat" in out.lower()
