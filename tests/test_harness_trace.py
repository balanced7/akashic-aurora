"""PIN: agent/harness/trace.py -- display-only trace lines pushed onto the Bifrost bus.

Contract: emit() broadcasts one kind=trace envelope and is fail-open (False, never raises);
AKASHIC_TRACE=0 silences everything; narrate() is gated by the shared narration level;
summarize() turns a tool call into one short line without file bodies. The bus and the control
store are faked, so no Redis is touched.
"""

import os
import sys
from typing import Any, ClassVar

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.comm.bus
import core.comm.control
from agent.harness import trace


class FakeBus:
    sent: ClassVar[list[tuple[str, str, Any, Any]]] = []
    result: ClassVar[str | None] = "mid-1"

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def broadcast(self, kind, content=None, *, meta=None):
        FakeBus.sent.append((self.agent_id, kind, content, meta))
        return FakeBus.result


@pytest.fixture
def bus(monkeypatch):
    FakeBus.sent = []
    FakeBus.result = "mid-1"
    monkeypatch.setattr(core.comm.bus, "Bus", FakeBus)
    monkeypatch.delenv("AKASHIC_TRACE", raising=False)
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    return FakeBus


def test_emit_broadcasts_display_only_trace(bus):
    """emit() sends a kind=trace line with the kind's prefix and display-only meta from the agent id."""
    assert trace.emit("tool", "  Bash · ls  ", agent_id="seat") is True
    assert bus.sent == [
        (
            "seat",
            "trace",
            "\U0001f527 Bash · ls",
            {"via": "seat-hook", "hops": 0, "trace": "tool", "display_only": True},
        )
    ]


def test_emit_agent_id_from_env_then_default(bus, monkeypatch):
    """Without an explicit id, emit() uses AKASHIC_AGENT_ID, else 'claude'; unknown kinds get a dot prefix."""
    trace.emit("other", "x")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "envseat")
    trace.emit("think", "y")
    assert [(a, c) for a, _, c, _ in bus.sent] == [("claude", "· x"), ("envseat", "\U0001f4ad y")]


def test_emit_noops_on_kill_switch_blank_text_offline_or_error(bus, monkeypatch):
    """emit() returns False when disabled, blank, the bus is offline (None) or raising -- and never raises."""
    assert trace.emit("tool", "   ") is False
    bus.result = None
    assert trace.emit("tool", "x") is False

    class Broken:
        def __init__(self, *_):
            raise ConnectionError("down")

    monkeypatch.setattr(core.comm.bus, "Bus", Broken)
    assert trace.emit("tool", "x") is False
    monkeypatch.setenv("AKASHIC_TRACE", "0")
    monkeypatch.setattr(core.comm.bus, "Bus", FakeBus)
    assert trace.emit("tool", "x") is False
    assert len(bus.sent) == 1  # only the offline attempt reached broadcast


@pytest.mark.parametrize(
    ("current", "level", "shown"),
    [
        ("off", "key", False),
        ("key", "key", True),
        ("key", "full", False),
        ("full", "full", True),
        ("full", "key", True),
    ],
)
def test_narrate_is_gated_by_shared_level(bus, monkeypatch, current, level, shown):
    """narrate() shows a line only when the shared level is at least the line's level, and never at off."""
    monkeypatch.setattr(core.comm.control, "get_narration_level", lambda: current)
    assert trace.narrate("why", level=level, agent_id="seat") is shown
    assert len(bus.sent) == int(shown)
    if shown:
        assert bus.sent[0][2] == "\U0001f4ad why"


def test_narrate_fails_open_to_key_and_respects_kill_switch(bus, monkeypatch):
    """A broken level lookup counts as 'key'; AKASHIC_TRACE=0 silences narrate entirely."""

    def boom():
        raise RuntimeError("no redis")

    monkeypatch.setattr(core.comm.control, "get_narration_level", boom)
    assert trace.narrate("a", level="key") is True
    assert trace.narrate("b", level="full") is False
    monkeypatch.setenv("AKASHIC_TRACE", "0")
    assert trace.narrate("c", level="key") is False
    assert len(bus.sent) == 1


@pytest.mark.parametrize(
    ("tool", "ti", "expected"),
    [
        ("Edit", {"file_path": "/a/b/c.py", "new_string": "BODY"}, "Edit · c.py"),
        ("Read", {}, "Read · ?"),
        ("Bash", {"command": "ls -la\nsecond line", "description": "List"}, "Bash · List — ls -la"),
        ("PowerShell", {"command": "dir"}, "PowerShell · dir"),
        ("Bash", {}, "Bash · "),
        ("Glob", {"pattern": "**/*.py"}, "Glob · **/*.py"),
        ("Grep", {"pattern": "def  x"}, "Grep · def x"),
        ("Task", {"subagent_type": "Explore"}, "Task · Explore"),
        ("WebSearch", {"query": "q"}, "WebSearch · q"),
        ("WebFetch", {"url": "https://x"}, "WebFetch · https://x"),
        ("Mystery", None, "Mystery"),
    ],
)
def test_summarize_one_line_per_tool(tool, ti, expected):
    """summarize() renders '<Tool> · <what>' from the relevant input field, never the payload body."""
    assert trace.summarize(tool, ti) == expected


def test_summarize_clips_long_text():
    """Long descriptions are clipped to 120 characters ending in an ellipsis."""
    out = trace.summarize("Task", {"description": "w " * 200})
    assert out.startswith("Task · ")
    assert len(out) - len("Task · ") == 120
    assert out.endswith("…")
