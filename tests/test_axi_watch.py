"""Pins for `watch` after the AXI conversion: declare, status in each state, and the refusals.

The expectation file is pointed at a temporary path (AKASHIC_RUN_EXPECTATION), so nothing touches
state/expect/ and no watcher is involved.

Run: uv run pytest tests/test_axi_watch.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def expect(monkeypatch, tmp_path):
    path = tmp_path / "run-active.json"
    monkeypatch.setenv("AKASHIC_RUN_EXPECTATION", str(path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return path


def _watch(capsys, **kw):
    ns = argparse.Namespace(agent_id="twatch", declare=None, grace=1800.0, checkpoint=False, stand_down=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_watch(ns)
    return code, capsys.readouterr().out


def test_no_expectation_is_an_explicit_none(expect, capsys):
    code, text = _watch(capsys)
    assert code == 0
    assert text.startswith("expectation: none\nrun_declared: no\nalarm: no")
    assert 'watch twatch --declare "<what is running>"' in text


def test_declare_then_status_open(expect, capsys):
    code, text = _watch(capsys, declare="nightly reindex", grace=600.0)
    assert code == 0
    assert "expectation: open\nrun: nightly reindex\nby: twatch\ngrace_s: 600" in text
    assert "watch twatch --checkpoint" in text
    _, text = _watch(capsys)
    assert "expectation: open\nalarm: no\nrun: nightly reindex" in text
    assert "grace_s: 600" in text


def test_grace_zero_reads_as_an_alarm(expect, capsys):
    import json
    import time

    _watch(capsys, declare="migration", grace=0.0)
    doc = json.loads(expect.read_text(encoding="utf-8"))
    doc["checkpoint_at"] = time.time() - 5  # five quiet seconds, past a zero grace
    expect.write_text(json.dumps(doc), encoding="utf-8")
    _, text = _watch(capsys)
    assert "expectation: alarm\nalarm: yes" in text
    assert "finding: " in text


def test_stand_down_and_nothing_open(expect, capsys):
    code, text = _watch(capsys, stand_down=True)
    assert code == 1
    assert "code: NOTHING_OPEN" in text
    code, text = _watch(capsys, checkpoint=True)
    assert code == 1
    _watch(capsys, declare="x")
    code, text = _watch(capsys, stand_down=True)
    assert code == 0
    assert "expectation: stood down" in text
    _, text = _watch(capsys)
    assert "expectation: stood down\nalarm: no\nlast_run: x" in text


def test_human_view_leads_with_the_state(expect, capsys, monkeypatch):
    _watch(capsys, declare="nightly reindex", grace=600.0)
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _watch(capsys)
    assert "open  nightly reindex" in text
    assert "of 10m grace" in text
