"""
B-runner -- the Gemini (API agent) runner: routing logic + smoke.

The runner loop itself blocks on the bus (a human/dogfood exercises it); here we test the pure
routing decision (answer others' questions, never our own echoes, never 'reply' -- the loop guard).

Run: py -m pytest tests/test_bifrost_runner.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import bifrost_runner as r


def test_should_answer_routing():
    assert r.should_answer("chat", "cursor", "gemini") is True
    assert r.should_answer("request", "claude", "gemini") is True
    assert r.should_answer("handoff", "claude", "gemini") is True
    assert r.should_answer("chat", "gemini", "gemini") is False     # our own echo
    assert r.should_answer("note", "cursor", "gemini") is False     # not a question
    assert r.should_answer("reply", "cursor", "gemini") is False    # never answer a reply (no loops)


def test_card_is_api_runner():
    assert r.CARD["runtime_class"] == "api" and r.CARD["wake_mode"] == "runner" and r.CARD["door"] == "runner"


def test_module_smoke():
    assert callable(r.main) and callable(r.provider_reply)


if __name__ == "__main__":
    for fn in [test_should_answer_routing, test_card_is_api_runner, test_module_smoke]:
        fn()
    print("RUNNER ROUTING TESTS PASSED")
