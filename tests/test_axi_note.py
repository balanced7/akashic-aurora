"""Pins for `note` after the AXI conversion: the write confirmation, --get, and the misses.

Run: uv run pytest tests/test_axi_note.py -q
"""

import os
import tempfile
from types import SimpleNamespace as Ns

import pytest

import agent_cli
from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory


def _args(**kw):
    base = {
        "agent_id": "alice",
        "title": "where-we-are",
        "note": "Wave 3 done; next: the ledger table.",
        "context": "",
        "category": "",
        "supersedes": None,
        "retire": None,
        "get": None,
        "session": "",
        "json": False,
    }
    base.update(kw)
    return Ns(**base)


@pytest.fixture
def note(monkeypatch, capsys):
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    monkeypatch.setattr(agent_cli, "project_notes", lambda: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(**kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        code = agent_cli.cmd_note(_args(**kw), mem=mem)
        return code, capsys.readouterr().out

    return run


def test_write_then_rewrite_names_the_superseded_prior(note):
    code, text = note()
    assert code == 0
    assert text.startswith("noted: where-we-are\nid: ")
    assert "superseded: none (first note with this title)" in text
    first_id = text.split("id: ")[1].split("\n")[0]
    _, text = note(note="Wave 4")
    assert f"superseded: {first_id}" in text


def test_get_is_a_detail_view_with_the_whole_body(note):
    note(context="decided Monday")
    code, text = note(get="where-we-are")
    assert code == 0
    assert "status: active" in text
    assert "Wave 3 done; next: the ledger table." in text
    assert "context: decided Monday" in text
    assert "help[" not in text


def test_a_miss_is_not_found_with_the_listing_hint(note):
    code, text = note(get="never-existed")
    assert code == 1
    assert "code: NOT_FOUND" in text
    assert "agent_cli.py notes" in text or "aurora notes" in text


def test_missing_body_is_a_usage_error(note):
    code, text = note(note="")
    assert code == 2
    assert "code: USAGE" in text


def test_human_get_prints_the_body_as_written(note):
    note(note="line one\nline two")
    _, text = note(get="where-we-are", env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Note · where-we-are")
    assert "line one\nline two" in text
