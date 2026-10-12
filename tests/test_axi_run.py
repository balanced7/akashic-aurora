"""Pins for `run` after the AXI conversion: the framing around the steps' own output.

The toolbelt is pointed at a temporary directory and the step subprocess is faked, so nothing
touches data/verb-registry/ and no verb really runs.

Run: uv run pytest tests/test_axi_run.py -q
"""

import argparse
import subprocess

import pytest

import agent_cli


@pytest.fixture
def belt(monkeypatch, tmp_path):
    from core.toolbelt import registry

    monkeypatch.setattr(registry, "default_root", lambda: str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    tb = registry.Toolbelt("trun")
    tb.mint("ok", [["locks"], ["status"]])
    tb.mint("bad", [["locks"], ["defer", "trun", "--done", "nope"], ["status"]])
    tb.mint("hist", [["alias", "trun", "history", "$1"]])

    def fake_run(argv, **kw):
        rc = 2 if "defer" in argv else 0
        return subprocess.CompletedProcess(argv, rc, stdout=f"<output of {argv[2]}>\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return tb


def _run(capsys, name, *rest, dry=False):
    ns = argparse.Namespace(agent_id="trun", name=name, args=list(rest), dry=dry)
    code = agent_cli.cmd_run(ns)
    return code, capsys.readouterr().out


def test_steps_are_framed_and_the_close_is_a_summary(belt, capsys):
    code, text = _run(capsys, "ok")
    assert code == 0
    assert "step 1/2: locks\n<output of locks>\nstep 2/2: status\n<output of status>" in text
    assert text.rstrip().endswith("alias: ok\nstatus: done\nsteps: 2\nran: 2")


def test_a_failing_step_is_named_with_what_never_ran(belt, capsys):
    code, text = _run(capsys, "bad")
    assert code == 2  # the step's exit code, as before
    assert "status: stopped" in text
    assert "failed_step: 2" in text
    assert "failed: defer trun --done nope" in text
    assert "exit: 2" in text
    assert "skipped: 1" in text
    assert "step 3/3" not in text


def test_dry_run_lists_resolved_steps(belt, capsys):
    code, text = _run(capsys, "hist", "land", dry=True)
    assert code == 0
    assert "steps[1]: alias trun history land" in text
    assert "run trun hist land" in text


def test_unknown_alias_and_missing_macro_args_are_structured(belt, capsys):
    code, text = _run(capsys, "ghost")
    assert code == 1
    assert "code: NOT_FOUND" in text
    code, text = _run(capsys, "hist")
    assert code == 1
    assert "expects 1 arg(s)" in text


def test_human_view_closes_with_a_verdict(belt, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "bad")
    assert "▸ step 2/3  defer trun --done nope" in text
    assert "✗ bad stopped at step 2/3 (defer trun --done nope, exit 2)" in text
    assert "1 step(s) not run" in text
