"""Pins for `log` after the AXI conversion: the confirmation, the missing-summary warning, the
store failure.

Run: uv run pytest tests/test_axi_log.py -q
"""

from types import SimpleNamespace

import pytest

import agent_cli


@pytest.fixture
def log(monkeypatch, capsys):
    import core.narrative.beat_log as bl

    holder = {"beat": SimpleNamespace(id="beat_42")}
    monkeypatch.setattr(bl, "get_beat_log", lambda: SimpleNamespace(emit=lambda *a, **k: holder["beat"]))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(beat=..., **kw):
        if beat is not ...:
            holder["beat"] = beat
        ns = SimpleNamespace(
            **{"kind": "note", "summary": "", "source": "", "category": "", "task": "", "json": False, **kw}
        )
        code = agent_cli.cmd_log(ns)
        return code, capsys.readouterr().out

    return run


def test_confirmation(log):
    code, text = log(summary="shipped the ledger migration")
    assert code == 0
    assert text.startswith("recorded: true\nkind: note\nbeat_id: beat_42\nsummary: shipped the ledger migration")
    assert "warning" not in text
    assert "help[" not in text


def test_missing_summary_warns(log):
    _, text = log()
    assert "warning: " in text
    assert "no --summary" in text


def test_store_failure_is_an_error(log):
    code, text = log(beat=None, summary="x")
    assert code == 1
    assert "code: WRITE_FAILED" in text
