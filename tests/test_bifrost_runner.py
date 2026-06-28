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
    assert r.CARD_API["runtime_class"] == "api" and r.CARD_API["wake_mode"] == "runner"
    assert r.CARD_WEB["runtime_class"] == "web"


def test_web_failed_detects_errors():
    assert r.web_failed("LOGIN_REQUIRED: sign in") is True
    assert r.web_failed("GEMINI_WEB_ERROR: timeout") is True
    assert r.web_failed("WEB_OK") is False


def test_card_for_provider():
    assert r.card_for("api")["runtime_class"] == "api"
    assert r.card_for("web")["runtime_class"] == "web"
    assert r.card_for("auto")["runtime_class"] == "web"


def test_module_smoke():
    assert callable(r.main) and callable(r.provider_reply) and callable(r.provider_reply_web)


if __name__ == "__main__":
    for fn in [
        test_should_answer_routing,
        test_card_is_api_runner,
        test_web_failed_detects_errors,
        test_card_for_provider,
        test_module_smoke,
    ]:
        fn()
    print("RUNNER ROUTING TESTS PASSED")
