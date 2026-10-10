"""PIN: the claude_pretooluse LIVE twin routes recall through the strangler door.

Defer: suite:test_seat_identity_resolver (r7 red at clean HEAD).

THE MECHANISM. Commit 873db5de (t383, rule of three) replaced the inline recall_at/render/
mark_seen/mark_impression/log_injection sequence in agent/harness/hooks/claude_pretooluse.py::
_recall_context with one delegation -- agent.harness.actions.recall_block -- and did NOT port
it to the twin at scripts/hooks/claude_pretooluse.py. The twins are TWO REAL FILES that differ
only by sys.path depth, and a home-rooted session runs the scripts/ copy (check_wiring.py
declares that copy 'not walked'). So the strangler's identity thread (agent_id explicit beats
env, `_agent(None)` -> AKASHIC_AGENT_ID) and every future policy change to recall_block land on
the copy that is NOT running, while the live copy keeps its own private fork of the sequence.

test_seat_identity_resolver::r7 catches the SYMPTOM (identity lines differ across twins). This
pin catches the MECHANISM: both twins must reach recall_block with the same arguments for the
same payload. The door is replaced with a recorder and the engine underneath is made inert, so
an un-ported twin fails on the assertion and never on the environment (no Redis, no state).
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# scripts/hooks/claude_pretooluse.py is now a runpy shim onto this file (check_wiring enforces
# the shape), so there is ONE body to pin.
COPIES = {
    "agent_harness": os.path.join(ROOT, "agent", "harness", "hooks", "claude_pretooluse.py"),
}

# SYNTHETIC session id -- never a real seat's (the r1/r2 lesson in test_seat_identity_resolver).
SID = "testsid0-0000-0000-0000-000000000000"
SENTINEL = "SENTINEL-RECALL-BLOCK"


def _load(which: str):
    """Load a hook copy under a unique module name: the file's only import-time side effect is
    its own sys.path insert, and unique names keep the two twins (and test_k0's top-level
    `claude_pretooluse`) from aliasing each other in sys.modules."""
    spec = importlib.util.spec_from_file_location(f"_twin_{which}_pretooluse", COPIES[which])
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def door_calls(monkeypatch, tmp_path):
    """Recorder on the strangler door + an inert engine beneath it."""
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    monkeypatch.setenv("AKASHIC_RECALL_STATE_DIR", str(tmp_path))
    import agent.harness.actions as actions

    calls: list = []

    def fake_recall_block(session_key, seen_key, path, command, agent_id=None):
        calls.append((session_key, seen_key, path, command, agent_id))
        return SENTINEL

    monkeypatch.setattr(actions, "recall_block", fake_recall_block)

    # A twin that bypasses the door reaches the engine directly; make that path inert so the
    # pin fails on the ASSERTION (door never called), not on Redis/state in a fresh worktree.
    import core.recall.at_action as at_action

    def bypassed(*_a, **_k):
        raise RuntimeError("engine reached directly -- the strangler door was bypassed")

    monkeypatch.setattr(at_action, "recall_at", bypassed)
    return calls


def test_canonical_hook_routes_recall_through_the_strangler_door(door_calls):
    """The defect, named. The copy a home-rooted session actually runs must delegate to
    agent.harness.actions.recall_block with the session uuid as BOTH keys (byte-for-byte the
    pre-t383 behavior, per actions.py's TWO KEYS note) and no explicit agent_id (the door's
    _agent(None) resolves env -- the identity thread lives in ONE place)."""
    hook = _load("agent_harness")
    out = hook._recall_context(
        {"session_id": SID, "tool_name": "Bash", "tool_input": {"command": "py agent_cli.py status"}}
    )
    assert door_calls == [(SID, SID, None, "py agent_cli.py status", None)], (
        "agent/harness/hooks/claude_pretooluse.py::_recall_context did not go through "
        f"agent.harness.actions.recall_block -- it still carries the pre-t383 inline fork; "
        f"door calls seen: {door_calls!r}"
    )
    assert out == SENTINEL, f"door's rendering was not returned verbatim: {out!r}"
