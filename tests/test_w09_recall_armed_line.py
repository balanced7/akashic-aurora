"""W09 pins — a boot line proving recall-at is armed (calibrated silence vs missing wiring).

Wish W09 (kimi F2): kimi mis-diagnosed recall-at hook ABSENCE during their walk because
downstream silence is indistinguishable from a dead hook. A boot line saying "recall-at:
armed, N lessons warm" makes later silence CALIBRATED (the surface is live, nothing was
relevant) rather than suspect. Pure render over warm_cache's count.

  P1  armed line names the warm lesson count
  P2  a zero-count corpus still confirms ARMED (empty != broken)
  P3  a warm failure (count None) renders the honest "could not warm" variant
  P4  a warm cache with NO registered hook is not armed, and says how to install it (#55)
  P5  the hook check reads the installer's status (registered / not / unreadable)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def test_p1_armed_line_names_count():
    line = agent_cli._recall_armed_line(34)
    assert "recall-at" in line
    assert "armed" in line
    assert "34" in line
    assert "silence" in line.lower(), "the line teaches that later silence is calibrated"


def test_p2_zero_corpus_still_armed():
    line = agent_cli._recall_armed_line(0)
    assert "armed" in line, "an empty corpus is armed, not broken"
    assert "0" in line, "an empty corpus is armed, not broken"


def test_p3_warm_failure_is_honest():
    line = agent_cli._recall_armed_line(None)
    assert "could not warm" in line.lower() or "unavailable" in line.lower()
    assert "armed" not in line, "a failed warm must not claim armed"


def test_p4_no_hook_is_not_armed():
    line = agent_cli._recall_armed_line(34, hooked=False)
    assert "armed" not in line, "a warm cache with no hook must not claim armed (#55)"
    assert "NOT installed" in line
    assert "hooks install" in line, "the line names the command that turns it on"
    assert "armed" in agent_cli._recall_armed_line(34, hooked=True)


def _rows(installed=(), error=""):
    return [{"harness": "claude", "installed": list(installed), "stale": [], "error": error}]


def test_p5_hook_check_reads_installer_status(monkeypatch):
    from agent.harness import install

    monkeypatch.setattr(install, "status", lambda: _rows(["PreToolUse:claude_pretooluse.py"]))
    assert agent_cli._recall_hook_registered() is True
    monkeypatch.setattr(install, "status", lambda: _rows(["PreToolUse:claude_trace.py"]))
    assert agent_cli._recall_hook_registered() is False, "the trace hook recalls nothing"
    monkeypatch.setattr(install, "status", lambda: _rows(error="JSONDecodeError"))
    assert agent_cli._recall_hook_registered() is None, "unreadable settings are unknown, not off"
