"""
T097-S1 · P-S1-5 (kimi fence verdict O1b) -- 'call-issued' phase before the blocking create().
Slice 0 of the T098 build-our-own plan, second pin.

THE GAP: the progress pulse bumps at tool rounds (on_trace), but a hang INSIDE the streamed
create() fires no tool round -- so a stalled model call (C1-8: 25-40 min, never a first token)
was indistinguishable from an idle gap 'between rounds'. Fix: mark a distinct 'calling-model'
phase the instant BEFORE create(), and flip to 'thinking' on the first streamed token. A hang
in the API call then self-renders as 'calling-model' aged (P-S1-0 surfaces it at 150s), legibly
'hung in the API' -- no doctor change needed.

Hermetic: a fake client captures the worklive phase (via on_activity) at create()-time. No network.
Run: py -m pytest tests/test_t097_s1_call_issued_phase.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


class _EmptyStream:
    def __iter__(self):
        return iter(())          # create() returns, but yields NO tokens (the pure API-hang shape)


def test_calling_model_phase_is_set_before_create():
    """P-S1-5: at the instant create() is entered, the worklive phase must be the DISTINCT
    'calling-model' (so a hang there is legible as an API stall), not the ambiguous 'thinking'."""
    import deepseek_chat as dc
    captured = {"phase": None, "at_create": None}

    def on_activity(state, detail=""):
        captured["phase"] = state

    class _Completions:
        def create(self, **kw):
            captured["at_create"] = captured["phase"]     # the phase set immediately before create()
            return _EmptyStream()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    ag = dc.Agent(_Client(), None, model="deepseek-test", system="s", think=False,
                  tools_enabled=False, on_activity=on_activity)
    ag.send("hello")
    assert captured["at_create"] == "calling-model", (
        f"expected 'calling-model' phase at the blocking create(), got {captured['at_create']!r}")


def test_phase_flips_to_thinking_once_the_stream_yields():
    """Guard: the pre-call phase must NOT persist -- once the stream yields a token the phase
    flips to 'thinking', so a normal (non-hung) call doesn't linger as 'calling-model'."""
    import deepseek_chat as dc
    seq = []

    def on_activity(state, detail=""):
        seq.append(state)

    class _Delta:
        content = "hi"
        tool_calls = None
        reasoning_content = None
        model_extra = None

    class _Choice:
        delta = _Delta()

    class _Chunk:
        choices = [_Choice()]
        usage = None

    class _OneStream:
        def __iter__(self):
            return iter([_Chunk()])

    class _Completions:
        def create(self, **kw):
            return _OneStream()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    ag = dc.Agent(_Client(), None, model="deepseek-test", system="s", think=False,
                  tools_enabled=False, on_activity=on_activity)
    ag.send("hello")
    assert "calling-model" in seq, "the call-issued phase must be marked before create()"
    assert "thinking" in seq, "the phase must flip to 'thinking' once the stream yields"
    assert seq.index("calling-model") < seq.index("thinking"), \
        "calling-model precedes thinking (the flip happens on the first streamed token)"
