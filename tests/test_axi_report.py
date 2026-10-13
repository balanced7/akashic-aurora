"""Pins for `report` after the AXI conversion: the receipt for a written scaffold, the crib as
rows, a missing title, and the scaffold on stdout left untouched.

Run: uv run pytest tests/test_axi_report.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(**kw):
    ns = argparse.Namespace(title="", eyebrow="Akashic Aurora", out="", crib=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    return agent_cli.cmd_report(ns)


def test_a_written_scaffold_gets_a_receipt(tmp_path, capsys):
    target = tmp_path / "r.html"
    assert _run(title="Retro", out=str(target)) == 0
    out = capsys.readouterr().out
    assert f"wrote: {target}" in out
    assert f"chars: {len(target.read_text(encoding='utf-8'))}" in out
    assert "report --crib" in out


def test_the_crib_is_rows(capsys):
    assert _run(crib=True) == 0
    out = capsys.readouterr().out
    assert "primitives[" in out
    assert "{primitive,use}:" in out
    assert "hr.rule" in out


def test_no_title_is_a_usage_error(capsys):
    assert _run() == 2
    out = capsys.readouterr().out
    assert "code: USAGE" in out
    assert "--title" in out


def test_the_scaffold_itself_prints_raw(capsys):
    assert _run(title="Raw") == 0
    out = capsys.readouterr().out
    assert out.startswith("<title>Raw</title>")
