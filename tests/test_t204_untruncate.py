"""
T204 -- un-truncate: two causes of a cut answer, two recoveries. RED first.

MEASURED, twice in one session (2026-08-06):
  * a 2200-token fence answer came back cut mid-sentence -- real content, just not
    finished
  * a --with ask carrying 8662 prompt tokens came back as TWENTY CHARACTERS, and another
    returned "" outright: reasoning consumed the entire completion budget before a single
    visible token was emitted

Both report finish_reason == "length". They are NOT the same failure and the right move
differs, which is exactly the T202 lesson one layer down -- a blind retry is what you do
when you have not named the cause.

  CUT      partial answer exists  -> CONTINUE it. The model has said something; asking it
                                     to resume costs one more completion, not the whole
                                     prompt again (which with --with is 8662 tokens).
  STARVED  answer is empty        -> continuation has NOTHING to continue. Only a larger
                                     budget helps, so say that precisely and do not spend
                                     a call proving it.

DIAGNOSIS BEFORE RECOVERY: `completion_tokens_details.reasoning_tokens` is on the response
and we have never read it -- the T156 wire work listed it among seven zero-cost fields we
discard, and named it "the diagnosis for content-empty-because-thinking-ate-the-budget".
Reading it turns "the answer was cut" into "reasoning used 1180 of your 1200 tokens".

STITCHING IS WHERE THIS GETS DISHONEST IF DONE CASUALLY. A continuation can repeat the
tail, drift, or silently run forever. So: a bounded number of continuations, the result
says how many happened, and running out of continuations is still PARTIALLY -- never a
clean `done` that hides a stitched-and-still-incomplete answer.

Run: py -m pytest tests/test_t204_untruncate.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import ask as ask_mod  # noqa: E402


class _Usage:
    def __init__(self, pt=10, ct=20, reasoning=None):
        self.prompt_tokens, self.completion_tokens = pt, ct
        if reasoning is not None:
            self.completion_tokens_details = type(
                "D", (), {"reasoning_tokens": reasoning})()


def _resp(content, finish, usage=None):
    msg = type("M", (), {"content": content})()
    choice = type("C", (), {"message": msg, "finish_reason": finish})()
    return type("R", (), {"choices": [choice], "usage": usage or _Usage()})()


class ScriptedClient:
    """Returns queued responses in order and records every request it received."""

    def __init__(self, *responses):
        self._queue = list(responses)
        self.calls = []
        outer = self

        class _Completions:
            @staticmethod
            def create(**kw):
                outer.calls.append(kw)
                return outer._queue.pop(0) if outer._queue else _resp("", "stop")

        self.chat = type("chat", (), {"completions": _Completions})()


# --------------------------------------------------------------------------------------
# CUT: there is an answer, it just stopped. Continue it.
# --------------------------------------------------------------------------------------

def test_a_cut_answer_is_continued_and_stitched():
    c = ScriptedClient(_resp("The first half", "length"),
                       _resp(" and the second half.", "stop"))
    o = ask_mod.ask("q", client=c, continue_on_cut=True)
    assert o.ok and not o.partial, "a fully continued answer is DONE"
    assert o.detail["answer"] == "The first half and the second half."
    assert o.detail["continuations"] == 1
    assert len(c.calls) == 2


def test_the_continuation_carries_the_partial_as_context():
    """A continuation that does not show the model what it already said will restart or
    repeat. The partial must ride as an assistant turn."""
    c = ScriptedClient(_resp("half one", "length"), _resp(" half two", "stop"))
    ask_mod.ask("q", client=c, continue_on_cut=True)
    roles = [m["role"] for m in c.calls[1]["messages"]]
    assert "assistant" in roles
    assert any("half one" in str(m.get("content")) for m in c.calls[1]["messages"])


def test_continuations_are_bounded_and_still_partial_when_exhausted():
    """Running out of continuations must NOT render as a clean done -- that would hide a
    stitched-but-still-incomplete answer behind a success."""
    c = ScriptedClient(*[_resp("x", "length") for _ in range(10)])
    o = ask_mod.ask("q", client=c, continue_on_cut=True, max_continuations=2)
    assert o.partial, "exhausted continuations stay PARTIALLY"
    assert o.detail["continuations"] == 2
    assert len(c.calls) == 3, "1 original + 2 continuations, never unbounded"


def test_continuation_is_opt_in():
    """Default behaviour is unchanged: a cut answer comes back PARTIALLY, as T169
    established. Spending extra calls must be asked for."""
    c = ScriptedClient(_resp("cut here", "length"))
    o = ask_mod.ask("q", client=c)
    assert o.partial and len(c.calls) == 1


# --------------------------------------------------------------------------------------
# STARVED: reasoning ate the budget. Continuation cannot help.
# --------------------------------------------------------------------------------------

def test_an_empty_length_answer_is_starved_not_cut():
    """THE CASE MEASURED TODAY. Nothing was emitted, so there is nothing to continue --
    spending a continuation call here buys a second empty answer."""
    c = ScriptedClient(_resp("", "length", _Usage(pt=8662, ct=1200, reasoning=1200)))
    o = ask_mod.ask("q", client=c, continue_on_cut=True, max_tokens=1200)
    assert not o.ok, "no answer at all is a failure, not a partial"
    assert o.detail.get("truncation") == "STARVED"
    assert len(c.calls) == 1, "must NOT spend a continuation on an empty answer"


def test_starved_says_how_much_reasoning_ate():
    """'The answer was cut' is not actionable. 'Reasoning used 1200 of 1200' tells you to
    raise the budget, and by roughly how much."""
    c = ScriptedClient(_resp("", "length", _Usage(pt=8662, ct=1200, reasoning=1200)))
    o = ask_mod.ask("q", client=c, continue_on_cut=True, max_tokens=1200)
    assert o.detail.get("reasoning_tokens") == 1200
    assert "1200" in o.why and "reasoning" in o.why.lower()


def test_reasoning_tokens_are_recorded_even_on_success():
    """A zero-cost field we have always discarded. Recording it on every call makes the
    starvation threshold learnable instead of guessed."""
    c = ScriptedClient(_resp("fine", "stop", _Usage(pt=10, ct=50, reasoning=30)))
    o = ask_mod.ask("q", client=c)
    assert o.ok and o.detail.get("reasoning_tokens") == 30


def test_absent_reasoning_field_is_none_never_zero():
    """A provider that does not report reasoning must not read as 'reasoned zero' -- that
    is the fabricated-measurement lie this repo refuses everywhere else."""
    c = ScriptedClient(_resp("fine", "stop", _Usage(pt=10, ct=50)))
    o = ask_mod.ask("q", client=c)
    assert o.detail.get("reasoning_tokens") is None


def test_truncation_field_names_the_cause_on_every_outcome():
    c = ScriptedClient(_resp("done", "stop"))
    assert ask_mod.ask("q", client=c).detail.get("truncation") is None
    c2 = ScriptedClient(_resp("cut", "length"))
    assert ask_mod.ask("q", client=c2).detail.get("truncation") == "CUT"
