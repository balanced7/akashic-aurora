"""Pins for `boot` after the AXI conversion: the agent document, the empty store, the human sheet.

The context itself (ranking, budgets, the orientation head) is pinned by the boot suites; these
pin only how it is presented.

Run: uv run pytest tests/test_axi_boot.py -q
"""

import argparse

import pytest

import agent_cli


def _ctx(entries):
    skeleton = "\n".join(f"- {e['summary']}  (source: {e['source']})" for e in entries)
    return {
        "status": "success",
        "context": {
            "skeleton": skeleton,
            "skeleton_entries": [{**e, "relates": None, "kind": ""} for e in entries],
            "sections": {"learnings": [{"source": e["source"]} for e in entries], "blockers": []},
        },
    }


@pytest.fixture
def boot(monkeypatch, capsys):
    import agent.initializer as init

    holder = {"res": _ctx([])}
    monkeypatch.setattr(init, "derive_agent_context_from_startup_sources", lambda *a, **k: holder["res"])
    monkeypatch.setattr(agent_cli, "_orientation_header", lambda *a, **k: "# Map: docs/ARCHITECTURE.md\n#   nested")
    monkeypatch.setattr(agent_cli, "_primer_aware", lambda: False)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "alice")

    def run(entries=(), **env):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        holder["res"] = _ctx(list(entries))
        code = agent_cli.cmd_boot(argparse.Namespace(agent_id="alice", task="tests hang", json=False))
        return code, capsys.readouterr().out

    return run


def test_agent_document_leads_with_who_and_counts(boot):
    code, text = boot([{"summary": "check port 16379", "source": "port_clash"}])
    assert code == 0
    lines = text.splitlines()
    assert lines[:4] == ["agent: alice", "task: tests hang", "lessons: 1", "blockers: 0"]
    assert "orientation[2]{line}:" in text
    assert '"Map: docs/ARCHITECTURE.md"' in text
    assert "> nested" in text, "an indented head line keeps its nesting"
    assert "context[1]{summary,source}:" in text
    assert "check port 16379,port_clash" in text
    assert "learn alice --experiment NAME" in text, "the contribute hint carries the agent id"
    assert "bifrost-sync alice" in text


def test_empty_store_says_so(boot):
    code, text = boot([])
    assert code == 0
    assert "context: none yet -- you are the first agent to contribute" in text
    assert "lessons: 0" in text


def test_human_view_is_a_titled_sheet(boot):
    _, text = boot([{"summary": "check port 16379", "source": "port_clash"}], AURORA_OUTPUT="human", NO_COLOR="1")
    assert text.startswith("Boot · alice")
    assert "1 lesson(s), 0 blocker(s) -- tests hang" in text
    assert "Lessons and context (most relevant first)" in text
    assert "• check port 16379 (port_clash)" in text
    assert "agent: alice" not in text
