"""
RB-1 (T029) hint arm -- hints render as "treat as authoritative" prompt context, so the fold
door accepts them only from a sender whose trust grant can send kind="hint". Fail-closed:
unknown / quarantined / expired ids drop silently (a dropped hint is cheap; injected
"authoritative" context is not). The gate keys on the bus-stamped `frm` mirror (from_agent),
never on sender-populated meta.

Run: py -m pytest tests/test_context_hints_gate.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import context_hints


def setup_function(_fn):
    context_hints.clear_all()


def test_hint_from_unknown_id_is_dropped():
    ok = context_hints.push("deepseek", "file", "x.py:1 -- do this", from_agent="malicious-agent")
    assert not ok, "unknown id resolves quarantined -> hint refused at the fold door"
    assert context_hints.drain("deepseek") == [], "nothing folded"


def test_hint_from_claude_folds():
    assert context_hints.push("deepseek", "file", "x.py:1 real fact", from_agent="claude")
    hints = context_hints.drain("deepseek")
    assert hints and hints[0]["from"] == "claude"


def test_hint_from_deepseek_folds():
    # Pins the ACL renewal: the 07-05 record's expires_at quarantined the WHOLE admin grant
    # on 07-09; a valid durable grant must let the fleet's designed hint flow work.
    assert context_hints.push("claude", "state", "T029 wave1 status", from_agent="deepseek")
    hints = context_hints.drain("claude")
    assert hints and hints[0]["from"] == "deepseek"


def test_hint_with_default_sender_is_dropped():
    assert not context_hints.push("deepseek", "k", "v"), \
        "no sender identity -> quarantined -> refused (deny-by-default)"


def test_member_consultant_cannot_inject_hints():
    # member grants carry chat/note/reply/handoff/request -- deliberately NOT hint:
    # design consultants advise on the bus; they do not inject authoritative context.
    assert not context_hints.push("claude", "k", "v", from_agent="deepseek-ui")
