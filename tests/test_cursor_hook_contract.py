"""Contract tests for the Cursor hook adapters (agent/harness/hooks/cursor_*.py).

Two layers, honest about what is and is not pinned (Integration Tiers H2):

1. ADAPTER contracts that hold regardless of Cursor's exact payload shape -- event
   routing (argv beats payload), field fallbacks, output envelopes, fail-open on
   garbage, the credit sequence. These run ALWAYS.
2. PAYLOAD-pinned tests driven by tests/fixtures/cursor_payloads/*.json -- SKIPPED with
   a teaching reason until composer pins live captures there (the adapters auto-capture
   to %TEMP%/akashic_recall/payloads_cursor/; see the fixtures README). Assumed shapes
   sank the first Claude credit design (2026-07-01) -- these stay skipped, not faked.
"""
import glob
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness.hooks import (cursor_beforeshell, cursor_posttooluse, cursor_pretooluse,
                           cursor_sessionstart)

_FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "cursor_payloads")
_FIXTURES = sorted(glob.glob(os.path.join(_FIX, "*.json")))


def _run(module, payload, capsys, argv=None, raw=None):
    real_argv = sys.argv
    sys.argv = argv or [getattr(module, "__file__", "hook")]
    try:
        sys.stdin = io.StringIO(raw if raw is not None else json.dumps(payload))
        rc = module.main()
    finally:
        sys.argv = real_argv
        sys.stdin = sys.__stdin__
    return rc, capsys.readouterr().out.strip()


# --- 1. adapter contracts (shape-independent) ------------------------------------------------------

def test_event_routing_argv_beats_payload():
    real = sys.argv
    try:
        sys.argv = ["hook", "--event", "postToolUseFailure"]
        assert cursor_posttooluse._event({"hook_event_name": "postToolUse"}) == "postToolUseFailure"
        sys.argv = ["hook"]
        assert cursor_posttooluse._event({"hook_event_name": "postToolUseFailure"}) == "postToolUseFailure"
        assert cursor_posttooluse._event({}) == "postToolUse", "default is the success event"
    finally:
        sys.argv = real


@pytest.mark.parametrize("payload,want", [
    ({"command": "a"}, ("a", "")),
    ({"tool_input": {"command": "b"}}, ("b", "")),
    ({"file_path": "p1"}, ("", "p1")),
    ({"tool_input": {"file_path": "p2"}}, ("", "p2")),
    ({"path": "p3"}, ("", "p3")),
    ({"command": "a", "tool_input": {"file_path": "p"}}, ("a", "p")),
    ({}, ("", "")),
])
def test_field_fallbacks(payload, want):
    assert cursor_pretooluse._fields(payload) == want
    assert cursor_posttooluse._fields(payload) == want


def test_sessionstart_ships_identity_even_when_whisper_silent(monkeypatch, capsys):
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    monkeypatch.setenv("AKASHIC_AUTOBOOT", "0")   # silence the whisper -> identity must still ship
    rc, out = _run(cursor_sessionstart, {}, capsys)
    assert rc == 0
    assert json.loads(out)["env"]["AKASHIC_AGENT_ID"] == "composer"


def test_sessionstart_explicit_id_wins(monkeypatch, capsys):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "someone")
    monkeypatch.setenv("AKASHIC_AUTOBOOT", "0")
    rc, out = _run(cursor_sessionstart, {}, capsys)
    assert json.loads(out)["env"]["AKASHIC_AGENT_ID"] == "someone"


def test_beforeshell_and_pretooluse_fail_open_on_garbage(capsys):
    for mod in (cursor_beforeshell, cursor_pretooluse):
        rc, out = _run(mod, None, capsys, raw="not json")
        assert rc == 0 and json.loads(out)["permission"] == "allow"


def test_pretooluse_out_of_repo_path_is_allowed(capsys):
    elsewhere = "C:\\Somewhere\\Else\\f.py" if os.name == "nt" else "/somewhere/else/f.py"
    rc, out = _run(cursor_pretooluse, {"file_path": elsewhere}, capsys)
    assert json.loads(out)["permission"] == "allow", "the lock guard only speaks for this repo"


def _wire_credit(monkeypatch, calls):
    import core.recall.at_action as aa
    monkeypatch.setattr(aa, "resolve_action_outcome",
                        lambda sid, tgt, ok, **kw: (calls.append((sid, tgt, ok)) or
                                                    {"flipped": False, "credited": 0, "sources": []}))
    monkeypatch.setattr(aa, "recall_at",
                        lambda **kw: {"lessons": [], "locks": [], "counter": None, "shown": 0,
                                      "total": 0, "faithful": True, "confidence": 1.0})


def test_posttooluse_failure_then_success_credit_sequence(monkeypatch, capsys):
    from core.recall.at_action import normalize_target
    from agent.harness.scope import repo_root
    calls = []
    _wire_credit(monkeypatch, calls)
    cmd, sid = "py probe_contract.py", "conv-1"
    tgt = normalize_target(None, cmd)
    rc, _ = _run(cursor_posttooluse, {"conversation_id": sid, "command": cmd, "cwd": repo_root()},
                 capsys, argv=["hook", "--event", "postToolUseFailure"])
    rc2, _ = _run(cursor_posttooluse, {"conversation_id": sid, "command": cmd, "cwd": repo_root()},
                  capsys)
    assert rc == 0 and rc2 == 0
    assert calls == [(sid, tgt, False), (sid, tgt, True)], \
        "the failure event is the DIRECT fail half; the next success completes the flip pair"


def test_posttooluse_out_of_scope_and_kill_switch_are_silent(monkeypatch, capsys):
    calls = []
    _wire_credit(monkeypatch, calls)
    elsewhere = "C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else"
    rc, out = _run(cursor_posttooluse, {"conversation_id": "c", "command": "echo hi",
                                        "cwd": elsewhere}, capsys)
    assert rc == 0 and out == "" and calls == []
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "0")
    from agent.harness.scope import repo_root
    rc, out = _run(cursor_posttooluse, {"conversation_id": "c", "command": "py agent_cli.py list",
                                        "cwd": repo_root()}, capsys)
    assert rc == 0 and out == "" and calls == []


# --- 2. payload-pinned contracts (composer's captures are the ground truth) ------------------------

_ROUTE = {"sessionstart": cursor_sessionstart, "beforeshell": cursor_beforeshell,
          "pretooluse": cursor_pretooluse, "posttooluse": cursor_posttooluse,
          "posttoolusefailure": cursor_posttooluse, "sessionend": None}


@pytest.mark.skipif(not _FIXTURES, reason=(
    "no pinned Cursor payloads yet -- composer: run a hooked Cursor session, then copy "
    "captures from %TEMP%/akashic_recall/payloads_cursor/ into tests/fixtures/cursor_payloads/ "
    "(see that README) and extend these pins with exact field assertions"))
@pytest.mark.parametrize("path", _FIXTURES, ids=[os.path.basename(p) for p in _FIXTURES])
def test_pinned_payload_round_trips_the_adapter(path, capsys):
    """Every pinned capture must route to its adapter and produce exit 0 + JSON-or-silence.
    Extend per-fixture with exact shape pins as they land (claude twin: test_claude_hook_contract)."""
    name = os.path.basename(path).lower()
    module = next((m for k, m in _ROUTE.items() if name.startswith(k) and m), None)
    if module is None:
        pytest.skip(f"no adapter route for fixture {name} (sessionend writes the real draft; "
                    f"cover it via its own tmp-path test when pinning)")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    argv = ["hook", "--event", "postToolUseFailure"] if name.startswith("posttoolusefailure") else None
    rc, out = _run(module, payload, capsys, argv=argv)
    assert rc == 0
    if out:
        json.loads(out)   # anything emitted must be a valid JSON envelope
