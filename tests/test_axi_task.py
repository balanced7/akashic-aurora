"""Pins for `task` (core/coord/conductor.py main) after the AXI conversion.

Offline: the ledger is a tmp file through the AKASHIC_TASKS_PATH door, the Redis mirror is
switched off and the bus announcements are muted, so these never touch a store.

Run: uv run pytest tests/test_axi_task.py -q
"""

import pytest

from core.coord import conductor
from core.coord import task_ledger as TL


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("AKASHIC_TASKS_PATH", str(tmp_path / "tasks.json"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(TL, "_bus_client", lambda: None)
    monkeypatch.setattr(conductor, "_broadcast", lambda *a, **k: None)
    return tmp_path


def _run(capsys, *argv):
    code = conductor.main(list(argv))
    return code, capsys.readouterr().out


def test_empty_ledger_is_a_definite_zero(ledger, capsys):
    code, text = _run(capsys, "list")
    assert code == 0
    assert text.startswith("total: 0\n")
    assert "task propose" in text


def test_propose_names_the_id_and_the_next_verb(ledger, capsys):
    code, text = _run(capsys, "propose", "Fix the redirect", "--by", "bench")
    assert code == 0
    assert text.startswith("task: T001\nstatus: proposed\ntitle: Fix the redirect\n")
    assert "task approve T001" in text


def test_list_counts_and_rows(ledger, capsys):
    for argv in (
        ("propose", "A", "--by", "b"),
        ("propose", "B", "--by", "b"),
        ("approve", "T001"),
        ("claim", "T001", "--by", "alice"),
        ("approve", "T002"),
    ):
        assert conductor.main(list(argv)) == 0
    capsys.readouterr()
    code, text = _run(capsys, "list")
    assert code == 0
    assert "total: 2\n" in text
    assert "active: 1\n" in text
    assert "active_tasks[1]{id,title,status,owner}:\n  T001,A,claimed,alice" in text
    assert "next_claimable: when the active task closes or parks" in text  # W15: one slot policy


def test_next_none_while_a_task_is_active(ledger, capsys):
    conductor.main(["propose", "A", "--by", "b"])
    conductor.main(["approve", "T001"])
    capsys.readouterr()
    code, text = _run(capsys, "next")
    assert code == 0
    assert "next: T001" in text
    assert "task claim T001 --by <agent_id>" in text
    conductor.main(["claim", "T001", "--by", "alice"])
    capsys.readouterr()
    _, text = _run(capsys, "next")
    assert text.startswith("next: none\n")


def test_a_ledger_refusal_is_a_structured_error_exit_1(ledger, capsys):
    conductor.main(["propose", "A", "--by", "b"])
    capsys.readouterr()
    code, text = _run(capsys, "claim", "T001", "--by", "alice")  # proposed -> claimed is illegal
    assert code == 1
    assert "illegal transition" in text
    assert "code: REFUSED" in text


def test_unknown_flag_is_reported_by_the_subcommand(ledger, capsys):
    with pytest.raises(SystemExit) as e:
        conductor.main(["list", "--nope"])
    assert e.value.code == 2
    text = capsys.readouterr().out
    assert "command: " in text
    assert "task list" in text
    assert "--limit" in text


def test_human_list(ledger, monkeypatch, capsys):
    conductor.main(["propose", "A", "--by", "b"])
    capsys.readouterr()
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "list")
    assert "1 task · 0 done" in text
    assert "DONE is closed" in text
