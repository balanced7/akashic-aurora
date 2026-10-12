"""Pins for `wrap` after the AXI conversion: the draft document, the commit confirmation, the
curated-head refusal and the human view.

Run: uv run pytest tests/test_axi_wrap.py -q
"""

import argparse
import os
import tempfile

import pytest

import agent_cli
from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory


@pytest.fixture
def wrap(monkeypatch, capsys):
    import subprocess

    import core.learning.agent_memory as am

    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    monkeypatch.setattr(agent_cli, "_recent_commits", lambda hours: [])
    monkeypatch.setattr(agent_cli, "_recent_lessons", lambda n: [])
    monkeypatch.setattr(agent_cli, "build_session_draft", lambda *a, **k: "Shipped:\n  - the ledger migration")
    monkeypatch.setattr(agent_cli, "project_notes", lambda: None)
    # the digest refresh and the scorecard are subprocesses: keep them out of a unit pin
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: argparse.Namespace(stdout="", returncode=0))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(**kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        ns = argparse.Namespace(
            **{"hours": 12, "grounding": None, "commit": False, "title": None, "force": False, "focus": None,
               "route": None, **kw}
        )  # fmt: skip
        code = agent_cli.cmd_wrap(ns)
        return code, capsys.readouterr().out

    return run, mem


def test_preview_is_a_draft_with_the_commit_hint(wrap):
    run, _ = wrap
    code, text = run()
    assert code == 0
    assert "state: draft -- not recorded" in text
    assert "record_with: " in text
    assert "draft[2]{line}:" in text
    assert "wrap --commit" in text
    assert "routing,no routing set" in text


def test_commit_confirms_the_note(wrap):
    run, _ = wrap
    code, text = run(commit=True)
    assert code == 0
    assert "wrapped: where-we-are" in text
    assert "superseded: none (first note with this title)" in text


def test_a_curated_head_is_refused_with_both_escapes(wrap):
    run, mem = wrap
    mem.decide_with_retry("where-we-are", "hand-written", curated=True)
    code, text = run(commit=True)
    assert code == 1
    assert "code: CURATED_HEAD" in text
    assert "wrap --commit --force" in text
    assert "--title" in text


def test_human_view(wrap):
    run, _ = wrap
    _, text = run(env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Wrap · draft where-we-are")
    assert "draft, not recorded" in text
    assert "  - the ledger migration" in text
