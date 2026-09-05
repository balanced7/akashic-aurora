"""The sender-shape gate — prose failed twice, so this is the machinery.

2026-09-04: three operator replies were sent as
  bifrost-send --to daniil --kind chat "<a 1000-char message>" claude
Text BEFORE the sender, so argparse bound the MESSAGE to agent_id and the word "claude" to
text. Discord rejected every one with HTTP 400 (a webhook username cannot be a thousand
characters); the operator saw silence and said "stuck again?" while an hour went into
diagnosing a pump defect that did not exist.

TWO lessons already covered this (bifrost_send_variadic_text_requires_options_before_sender,
30 days old; bifrost_send_always_text_file, 48 days old). Recall SURFACED both at me and I
violated them anyway -- a reading failure, not a targeting one. The repeat verb's own words:
"a short gap means prose is the wrong instrument and a gate is the right one." So: an agent
id is a SLUG, and anything that is obviously prose is refused at the door with the fix
spelled out. Structural, not disciplinary -- per the operator's own principle, the answer to
a boulder is not more hammers.

Run: py -m pytest tests/test_bifrost_send_sender_guard.py -q
"""
import pytest

from core.comm import sender_guard as SG


def test_a_normal_seat_id_passes():
    for ok in ("claude", "deepseek", "kimi", "sol", "dsh_agent", "codex_root",
               "opus-engineer", "gpt-new"):
        assert SG.check_sender(ok) is None, f"{ok!r} is a real seat id and must pass"


def test_a_sentence_as_sender_is_refused_and_names_the_fix():
    msg = SG.check_sender("Found it, and it was MY bug -- every reply I sent you was "
                          "malformed because the ordering bit me")
    assert msg, "prose as a sender id must refuse, not send"
    assert "--text-file" in msg, "the refusal must name the rule that prevents it"
    assert "sender" in msg.lower()


def test_the_exact_shape_that_cost_the_hour():
    # The real payload: options, then a long body, then the seat name. argparse binds the
    # body to agent_id. This is the case the gate exists for.
    body = ("WHERE WE ARE (and this message is itself the receipt -- it went out the "
            "normal bus path, no hand-pumping): your 20 agents broke NOTHING. " * 6)
    assert SG.check_sender(body), "the 1000-char sender must never reach the webhook"


def test_whitespace_is_the_tell_even_when_short():
    # "claude two" is short enough to pass a length check but is still not an id.
    assert SG.check_sender("claude two")
    assert SG.check_sender("send this")


def test_an_empty_or_missing_sender_refuses_too():
    for bad in ("", "   ", None):
        assert SG.check_sender(bad)


def test_a_long_but_id_shaped_sender_still_passes():
    # The gate must not become a length police for legitimately long ids (self-registered
    # seats look like codex_frontier_019f6e7e). No whitespace, no sentence punctuation.
    assert SG.check_sender("codex_frontier_019f6e7e") is None
    assert SG.check_sender("a" * 63) is None


def test_refusal_is_data_not_an_exception():
    # Callers are CLI doors that must print and exit non-zero, never traceback at him.
    out = SG.check_sender("this is prose")
    assert isinstance(out, str)
