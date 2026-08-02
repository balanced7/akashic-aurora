"""PRE-REGISTERED ACCEPTANCE -- live reasoning must reach the bus (Daniil's ask).

Committed RED before implementation (M3 pre-registration).

DANIIL, verbatim 2026-08-02: "I can see that deepseek is thinking but I don't see its
reasoning and our very beta version of the bifrost bus had this ability, I want it back
and for kimi as well."

MEASURED before writing these pins -- last 400 bus broadcasts:
    deepseek:tool   219
    kimi:tool        33
    kimi:think        2      <- kimi DOES stream reasoning
    deepseek:think    0      <- deepseek streams NONE

THE CAUSE, scripts/deepseek_chat.py:301: ``if r and self.think:`` gates CAPTURE on the
same flag as DISPLAY. The runner launches without --think, so self.think is False, the
reasoning chunks the API sends anyway (proved by the 2026-08-02 probe battery: thinking
is on server-side by default) are dropped on the floor, ``reasoning_buf`` stays empty,
and the ``_trace("thinking", ...)`` at line 325 never fires. The operator watches an
agent work for hours and never sees it think.

THE CONTRACT: capture is not display. self.think may govern whether we PRINT reasoning
to the console; it must never govern whether reasoning that ALREADY ARRIVED is observable.
A signal the provider hands us for free must not be discarded by a display flag.

Run::

    py -m pytest tests/test_reasoning_trace_reaches_the_bus.py -q
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.deepseek_chat as dc  # noqa: E402


def _chunk(*, content=None, reasoning=None):
    """One SSE chunk in the shape the openai SDK hands us (verified against the raw wire
    capture 2026-08-02: reasoning_content is a delta field, model_extra is always {})."""
    delta = SimpleNamespace(content=content, reasoning_content=reasoning,
                            tool_calls=None, model_extra={})
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)],
                           usage=None)


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


class _FakeClient:
    """Returns a canned stream; records nothing else."""

    def __init__(self, chunks):
        inner = SimpleNamespace(create=lambda **kw: _FakeStream(chunks))
        self.chat = SimpleNamespace(completions=inner)


def _agent(chunks, *, think):
    traces = []
    a = dc.Agent(_FakeClient(chunks), toolbox=None, model="deepseek-v4-pro", system="s",
                 think=think, tools_enabled=False,
                 on_trace=lambda kind, text: traces.append((kind, text)))
    a.messages = [{"role": "user", "content": "hi"}]
    return a, traces


REASONING_CHUNKS = [
    _chunk(reasoning="Let me "),
    _chunk(reasoning="check the ACL "),
    _chunk(reasoning="before answering."),
    _chunk(content="Done."),
]


# ---------------------------------------------------------------- pin 1
def test_reasoning_is_traced_even_when_think_is_off():
    """THE DEFECT. The runner launches WITHOUT --think, the API sends reasoning anyway,
    and it must still reach the trace callback. RED before the fix."""
    agent, traces = _agent(REASONING_CHUNKS, think=False)

    agent._stream_turn()

    thinking = [t for k, t in traces if k == "thinking"]
    assert thinking, (
        "no thinking trace emitted with think=False -- reasoning the provider already "
        "sent was discarded by a DISPLAY flag, so the operator never sees the agent think")
    assert "check the ACL" in thinking[0], f"reasoning text lost: {thinking[0]!r}"


# ---------------------------------------------------------------- pin 2
def test_reasoning_is_still_traced_when_think_is_on():
    """NO REGRESSION. The --think path must keep working exactly as before."""
    agent, traces = _agent(REASONING_CHUNKS, think=True)

    agent._stream_turn()

    thinking = [t for k, t in traces if k == "thinking"]
    assert thinking and "check the ACL" in thinking[0]


# ---------------------------------------------------------------- pin 3
def test_answer_content_is_unaffected_by_the_capture_change():
    """NO REGRESSION, and the one that matters most: reasoning must never leak into the
    ANSWER. The runner_reasoning_eats_final_answer lesson is the receipt for what happens
    when these two streams get crossed."""
    agent, _ = _agent(REASONING_CHUNKS, think=False)

    content, tool_calls = agent._stream_turn()

    assert content == "Done.", f"reasoning leaked into the answer: {content!r}"
    assert tool_calls == []


# ---------------------------------------------------------------- pin 4
def test_no_reasoning_means_no_thinking_trace():
    """A turn with no reasoning must emit no thinking trace -- an empty 💭 on the bus is
    noise, and the console renders every trace it receives."""
    agent, traces = _agent([_chunk(content="Plain answer.")], think=False)

    agent._stream_turn()

    assert [t for k, t in traces if k == "thinking"] == []


# ---------------------------------------------------------------- pin 5
def test_thinking_trace_is_bounded():
    """The trace is a live glance, not a transcript. It must stay bounded so one long
    reasoning turn cannot flood the bus or the console feed."""
    agent, traces = _agent([_chunk(reasoning="x" * 5000), _chunk(content="ok")], think=False)

    agent._stream_turn()

    thinking = [t for k, t in traces if k == "thinking"]
    assert thinking and len(thinking[0]) <= 600, (
        f"unbounded thinking trace ({len(thinking[0]) if thinking else 0} chars) -- "
        "the bus is not a transcript")
