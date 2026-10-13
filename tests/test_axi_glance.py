"""Pins for `glance program` after the AXI conversion: what an agent and a person see.

Every run names a temp ledger with --ledger-path, so nothing here reads the checkout's
state/coord/tasks.json.

Run: uv run pytest tests/test_axi_glance.py -q
"""

import json

import pytest

import agent_cli

TASKS = [
    {"id": "T901", "title": "Fence the migration path", "status": "in_progress", "owner": "kimi", "arc": "A3"},
    {"id": "T902", "title": "Retire the old bridge", "status": "blocked", "owner": "claude", "deps": ["T901"]},
    {"id": "T903", "title": "Write the release notes", "status": "proposed", "owner": ""},
]


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    p = tmp_path / "tasks.json"
    p.write_text(json.dumps({"seq": 3, "tasks": TASKS}), encoding="utf-8")
    return p


def _run(capsys, *argv):
    args = agent_cli.build_parser().parse_args(["glance", "program", *argv])
    code = args.fn(args)
    return code, capsys.readouterr().out


def test_agent_view_lists_tasks_and_names_what_it_cannot_check(ledger, capsys):
    code, text = _run(capsys, "--ledger-path", str(ledger))
    assert code == 0
    assert "ledger: read" in text
    assert "total: 3" in text
    assert "needs_attention[1]: T902" in text
    assert "tasks[3]{id,attention,status,owner,arc,title}:" in text
    assert "T902,ATTENTION,blocked,claude" in text
    assert "runtime_attention" in text.split("uncheckable[", 1)[1]
    assert "glance program --json" in text


def test_a_cut_says_how_many_it_shows(ledger, capsys):
    _, text = _run(capsys, "--ledger-path", str(ledger), "--max-items", "1")
    assert "total: 3\nshown: 1" in text
    assert "glance program --max-items 3" in text


def test_the_brief_states_it_has_no_identity_authority(ledger, capsys):
    _, text = _run(capsys, "--ledger-path", str(ledger), "--brief")
    assert "projection: brief" in text
    assert "identity_authority: none" in text


def test_an_empty_ledger_is_said_outright(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"seq": 0, "tasks": []}), encoding="utf-8")
    code, text = _run(capsys, "--ledger-path", str(p))
    assert code == 0
    assert "total: 0" in text
    assert "tasks: no task in the ledger" in text


def test_an_unreadable_ledger_says_why(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    _, text = _run(capsys, "--ledger-path", str(tmp_path / "nope.json"))
    assert 'ledger: "UNREADABLE: FileNotFoundError' in text
    assert 'tasks: "none: the ledger was not read"' in text


def test_json_and_compact_keep_the_versioned_contract(ledger, capsys):
    _, text = _run(capsys, "--ledger-path", str(ledger), "--json")
    assert json.loads(text)["schema_version"] == "world-snapshot/v1"
    assert text.startswith("{\n  ")
    _, text = _run(capsys, "--ledger-path", str(ledger), "--compact")
    assert json.loads(text)["bounds"]["total_items"] == 3
    assert "\n" not in text.strip()


def test_human_view(ledger, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "--ledger-path", str(ledger), "--max-items", "2")
    assert "1 need attention" in text
    assert "T902" in text
    assert "2 of 3 shown" in text
    assert "uncheckable:" in text
