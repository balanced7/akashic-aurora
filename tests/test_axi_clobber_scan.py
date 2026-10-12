"""Pins for `clobber-scan` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_clobber_scan.py -q
"""

import argparse
import json

import pytest

import agent_cli

_CEREMONY = """def pause_fleet(c):
    c.set(_pause_key(), "1")


def guarded(c):
    if was_paused():
        control.resume()


def reset_lane(c, lane):
    c.delete(_cursor_key(lane))
"""


@pytest.fixture(autouse=True)
def agent_mode(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, path, **kw):
    code = agent_cli.cmd_clobber_scan(argparse.Namespace(path=str(path), json=kw.get("json", False)))
    return code, capsys.readouterr().out


def test_findings_are_rows_with_counts_and_exit_1(tmp_path, capsys):
    f = tmp_path / "ceremony.py"
    f.write_text(_CEREMONY, encoding="utf-8")
    code, text = _run(capsys, f)
    assert code == 1  # a finding still exits 1: the verb's contract, unchanged
    assert "findings: 2" in text
    assert "writes[2]{line,family,snippet}:" in text
    assert "2,pause," in text
    assert "11,cursor," in text
    assert "resume" not in text.split("writes[")[1].split("review:")[0]  # the guarded write is not a row
    assert text.count("review:") == 1  # the review instruction, once, not once per row
    assert "help[" not in text  # the next step is reading those lines, not a command


def test_a_clean_file_says_zero(tmp_path, capsys):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n", encoding="utf-8")
    code, text = _run(capsys, f)
    assert code == 0
    assert "findings: 0" in text
    assert "writes" not in text


def test_unreadable_file_is_a_structured_error(tmp_path, capsys):
    code, text = _run(capsys, tmp_path / "missing.py")
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_json_is_the_finding_list(tmp_path, capsys):
    f = tmp_path / "ceremony.py"
    f.write_text(_CEREMONY, encoding="utf-8")
    _, text = _run(capsys, f, json=True)
    assert [x["line_no"] for x in json.loads(text)] == [2, 11]


def test_human_view(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    f = tmp_path / "ceremony.py"
    f.write_text(_CEREMONY, encoding="utf-8")
    _, text = _run(capsys, f)
    assert "2 unguarded control-key writes" in text
    assert "c.delete(_cursor_key(lane))" in text
