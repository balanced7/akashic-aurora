"""
T018 -- a promise is not a deliverable: the runner's one-bounce reprompt.

Bar: a promise-shaped FINAL reply ("Let me fold this into my review closure") triggers exactly
one deliver-now resend and ships the resend's result; outcome-shaped replies pass untouched;
a second promise ships as-is (one bounce is a nudge, two is a wedge); resend failures fail open.

Seen live 2026-07-09: the T017 seat-2 diff review arrived only after a manual deliver-now
reprompt -- the runner's first reply promised the review instead of delivering it.
Run: py -m pytest tests/test_runner_promise_bounce.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from scripts.bifrost_runner_deepseek import bounce_promise


class FakeSend:
    def __init__(self, reply=None, boom=False):
        self.calls = []
        self.reply = reply
        self.boom = boom

    def __call__(self, prompt):
        self.calls.append(prompt)
        if self.boom:
            raise RuntimeError("api down")
        return self.reply


def test_promise_ending_bounces_once_and_ships_the_deliverable():
    resend = FakeSend(reply="1. FINDING: the actual review content.")
    out = bounce_promise("Good context.\n\nLet me fold this into my T017 review closure.", resend)
    assert out == "1. FINDING: the actual review content."
    assert len(resend.calls) == 1
    assert "deliver the promised work now" in resend.calls[0].lower()


def test_outcome_ending_passes_untouched():
    resend = FakeSend(reply="should never be used")
    answer = "Review complete: zero critical findings. No holds."
    assert bounce_promise(answer, resend) == answer
    assert resend.calls == [], "no bounce on an outcome-shaped ending"


def test_second_promise_ships_as_is_no_loop():
    resend = FakeSend(reply="I'll get to the review shortly.")
    out = bounce_promise("I'll write the review next.", resend)
    assert out == "I'll get to the review shortly.", "one bounce only -- the second promise ships"
    assert len(resend.calls) == 1


def test_stop_verb_ending_is_not_bounced():
    resend = FakeSend(reply="unused")
    answer = "Analysis done.\n\nI'll wait for your review."
    assert bounce_promise(answer, resend) == answer, "an announced stop is an ending, not a promise"
    assert resend.calls == []


def test_resend_failure_fails_open_to_original():
    resend = FakeSend(boom=True)
    answer = "Let me now compile the full report."
    assert bounce_promise(answer, resend) == answer
    assert len(resend.calls) == 1


def test_empty_resend_falls_back_to_original():
    resend = FakeSend(reply="")
    answer = "I'm going to draft the findings now."
    assert bounce_promise(answer, resend) == answer


def test_empty_and_none_answers_pass_through():
    resend = FakeSend(reply="unused")
    assert bounce_promise("", resend) == ""
    assert bounce_promise(None, resend) is None
    assert resend.calls == []


def test_let_me_know_is_a_handoff_not_a_promise():
    resend = FakeSend(reply="unused")
    answer = "Findings attached above.\n\nLet me know if you need the raw diffs."
    assert bounce_promise(answer, resend) == answer
    assert resend.calls == [], "user-conditional 'let me know' must never bounce"
