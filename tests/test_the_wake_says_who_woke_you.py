"""RED pins: a wake tells you THAT you woke, never WHO called.

PRE-REGISTRATION (M3). RED at this commit; the implementation follows separately.

DANIEL'S ASK, 2026-10-05, verbatim: "Instead of checking what fired it, how do you get
notified what woke you? so you know exactly what came and from whom"

THE FRICTION, as it actually runs today. The wake listener exits when mail arrives, which
re-invokes the harness. What the seat receives is:

    Background command "Re-arm the wake listener" completed (exit code 0)

That is the whole notification. It names the TASK and says nothing about the MESSAGE. The
listener knew perfectly well -- at `scripts/bifrost_wake.py:644` it prints
`BIFROST WAKE -- messages for {agent}` followed by `json.dumps(out)`, where `out` holds the
sender, the kind and the body of every message that woke it. That print goes to the task's
output file, which nobody reads unless the seat spends a tool call on `tail`.

Measured on this session, 2026-10-05: FOURTEEN wakes, and fourteen `tail` calls to answer
"who called". Every one of them was a round trip whose entire purpose was to recover
information the waking process already had in hand and threw at a log.

THE SHAPE OF THE FIX, and it is small because both halves already exist. The listener writes
a one-shot note at the moment it fires; the UserPromptSubmit hook -- which ALREADY injects
`[akashic] mail: N unread bus msg(s)` on every turn (scripts/hooks/claude_userpromptsubmit.py:85)
-- renders it at the top of the very next turn and clears it. No new transport, no new poll:
one file in the same tempdir that already holds `.arming`, `.origin`, `.pid`, `.seen` and the
re-arm trigger, and one more line on a hook that is already speaking.

WHY FIRE-ONCE IS LOAD-BEARING AND NOT A DETAIL. A note that is not cleared re-announces a
stale wake on every subsequent turn, and a seat that is told "daniil woke you" three turns
running will either act twice on one message or learn to ignore the line. Both are worse than
silence. The note is consumed by the first turn that reads it -- the same discipline as the
re-arm trigger, which `clear_rearm_trigger()` removes at arm time precisely so a cycle cannot
be mistaken for a death.

AND IT MUST NAME THE SENDER, NOT THE COUNT. "1 new message" is the defect wearing a smaller
hat: it tells a seat to go look, which is the tool call this exists to remove. The line has to
carry WHO and WHAT, which is exactly what Daniel asked for.

Run::

    py -m pytest tests/test_the_wake_says_who_woke_you.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BW = _load("scripts/bifrost_wake.py", "_bw_under_test")

#: The shape `out` actually carries at the wake exit (bifrost_wake.py:644 json.dumps(out)).
WOKE_BY = [
    {"frm": "daniil", "kind": "chat", "id": "1791245759419-0",
     "content": "Instead of checking what fired it, how do you get notified what woke you?"},
]


# ------------------------------------------------------------------ the writer, at the listener
def test_the_listener_can_persist_what_woke_it(tmp_path, monkeypatch):
    """THE SEAM. The listener holds `out` at exit and currently only prints it."""
    monkeypatch.setattr(BW.tempfile, "gettempdir", lambda: str(tmp_path))
    assert hasattr(BW, "write_wake_note"), (
        "scripts/bifrost_wake.py has no `write_wake_note` -- the listener knows who woke it "
        "(it prints `out` at :644) and throws that away into a task log the seat must `tail`. "
        "Fourteen wakes on 2026-10-05 cost fourteen tail calls to recover it.")

    BW.write_wake_note("claude", "sess1234", WOKE_BY, tmp=str(tmp_path))
    note = BW.read_wake_note("claude", "sess1234", tmp=str(tmp_path))
    assert note, "the note did not survive the write"
    blob = repr(note)
    assert "daniil" in blob, "the note does not name WHO woke the seat: %s" % blob
    assert "chat" in blob, "the note does not carry the KIND: %s" % blob


def test_the_note_is_consumed_by_the_first_reader(tmp_path, monkeypatch):
    """FIRE-ONCE. A note that lingers re-announces a stale wake every turn, and a seat told
    the same thing three turns running either double-acts or stops reading the line."""
    monkeypatch.setattr(BW.tempfile, "gettempdir", lambda: str(tmp_path))
    BW.write_wake_note("claude", "sess1234", WOKE_BY, tmp=str(tmp_path))
    assert BW.read_wake_note("claude", "sess1234", tmp=str(tmp_path)), "first read empty"
    assert not BW.read_wake_note("claude", "sess1234", tmp=str(tmp_path)), (
        "the wake note survived its first read -- the next turn would be told again about a "
        "message already handled")


def test_a_missing_note_is_silent_and_never_raises(tmp_path, monkeypatch):
    """Fail-open, like every other organ on this path: no wake note is the NORMAL case for a
    turn the operator typed into directly, and it must cost nothing."""
    monkeypatch.setattr(BW.tempfile, "gettempdir", lambda: str(tmp_path))
    assert BW.read_wake_note("claude", "nosuch", tmp=str(tmp_path)) in (None, [], {}, "")


# ------------------------------------------------------------------ the reader, at the hook
@pytest.mark.parametrize("rel", ["scripts/hooks/claude_userpromptsubmit.py",
                                 "agent/harness/hooks/claude_userpromptsubmit.py"])
def test_the_turn_start_hook_announces_who_woke_you(rel, tmp_path, monkeypatch):
    """THE PAYOFF, pinned on BOTH TWINS -- the house has a standing hazard that the
    scripts/hooks and agent/harness/hooks copies drift apart, and a fix that lands in one is a
    fix the live seat may not be running."""
    hook = _load(rel, "_hook_" + rel.replace("/", "_").replace(".", "_"))
    assert hasattr(hook, "build_wake_line"), (
        "%s has no `build_wake_line` -- it already injects the unread COUNT every turn "
        "(build_bus_line), which tells the seat to go look. Daniel asked for who and what, "
        "which removes the looking." % rel)

    monkeypatch.setattr(BW.tempfile, "gettempdir", lambda: str(tmp_path))
    BW.write_wake_note("claude", "sess1234", WOKE_BY, tmp=str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))

    line = hook.build_wake_line("claude", "sess1234")
    assert line, "no line rendered for a session that was just woken by mail"
    assert "daniil" in line, "the line does not name the sender: %r" % line
    assert "Instead of checking" in line or "woke" in line.lower(), (
        "the line carries neither the message nor the fact of the wake: %r" % line)


@pytest.mark.parametrize("rel", ["scripts/hooks/claude_userpromptsubmit.py",
                                 "agent/harness/hooks/claude_userpromptsubmit.py"])
def test_the_hook_is_silent_when_the_turn_was_not_a_wake(rel, tmp_path, monkeypatch):
    """Most turns are the operator typing. Silence then, or the line becomes wallpaper."""
    hook = _load(rel, "_hookq_" + rel.replace("/", "_").replace(".", "_"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    assert hook.build_wake_line("claude", "no-such-session") == ""
