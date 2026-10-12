"""Pins for `memreplay` after the AXI conversion: what an agent and a person see.

Nothing here replays anything: run and drain are exercised on their refusals only.

Run: uv run pytest tests/test_axi_memreplay.py -q
"""

import argparse

import pytest

from core.metaharness import cli, memreplay


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, action, **kw):
    ns = argparse.Namespace(
        action=action, lesson="", base="", scenario=None, trials=3, daily_usd=None, label="", exclude=None, json=False
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.memreplay_main(ns)
    return code, capsys.readouterr().out


def test_empty_queue_says_zero_and_what_fills_it(capsys):
    code, text = _run(capsys, "queue")
    assert code == 0
    assert "queued: 0\nlessons: []\nfills: " in text


def test_queue_rows_and_capped_hints(capsys):
    memreplay.enqueue("port_clash", "graduate", {"experiment_name": "port_clash"})
    memreplay.enqueue("port_clash", "bench", None)  # the first record is the "before"
    _, text = _run(capsys, "queue")
    assert "queued: 1" in text
    assert "lessons[1]{lesson,why,at}:" in text
    assert "port_clash,graduate," in text
    assert "memreplay run --lesson port_clash --base baseline --daily-usd 5" in text


def test_run_and_drain_refuse_without_their_flags(capsys, monkeypatch):
    monkeypatch.setattr(memreplay, "experiment", lambda *a, **k: pytest.fail("replayed without --base"))
    monkeypatch.setattr(memreplay, "drain", lambda *a, **k: pytest.fail("drained without a budget"))
    code, text = _run(capsys, "run", lesson="x")
    assert code == 2
    assert "code: USAGE" in text
    code, text = _run(capsys, "drain", base="baseline")
    assert code == 2
    assert "--daily-usd 5" in text


def test_human_empty_queue(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "queue")
    assert "Memory replay queue" in text
    assert "queued" in text
