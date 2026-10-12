"""Pins for `suite-baseline` after the AXI conversion: what an agent and a person see.

The baseline file is redirected to a temporary path, so nothing here touches the repo's receipt.

Run: uv run pytest tests/test_axi_suite_baseline.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.coord import suite_baseline as sb

_OUT = "FAILED tests/test_a.py::test_old - E\nFAILED tests/test_b.py::test_new - E\n"


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(sb, "BASELINE_PATH", str(tmp_path / "suite_baseline.json"))
    monkeypatch.setattr(sb, "_ledger_claims", lambda: {"T1": "done"})
    monkeypatch.setattr(sb, "_task_files", dict)
    return tmp_path


def _write_baseline(tmp_path, nodes, lane=""):
    rec = {"v": 1, "sha": "abc1234f", "seat": "kimi", "at": "2026-10-01T00:00:00+00:00"}
    rec["failures"] = [{"node": n, "lane": lane} for n in nodes]
    (tmp_path / "suite_baseline.json").write_text(json.dumps(rec), encoding="utf-8")


def _run(capsys, **kw):
    ns = argparse.Namespace(agent_id="bench", from_file=None, sha="", check=False, show=False, whose=None, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_suite_baseline(ns)
    return code, capsys.readouterr().out


def test_show_is_provenance_and_counts(baseline, capsys):
    _write_baseline(baseline, ["tests/test_a.py::test_old"], lane="T1")
    code, text = _run(capsys, show=True)
    assert code == 0
    assert "sha: abc1234\nseat: kimi" in text
    assert "failures: 1\nclosed_lanes" in text
    assert "closed_lanes[1]: T1" in text  # the lane closed since: classification rotted
    assert "suite-baseline bench --check --from-file" in text


def test_show_with_no_baseline_says_so(baseline, capsys):
    code, text = _run(capsys, show=True)
    assert code == 0
    assert "baseline: none recorded\nfailures: 0" in text


def test_check_counts_and_names_the_new_failure(baseline, capsys, tmp_path):
    _write_baseline(baseline, ["tests/test_a.py::test_old", "tests/test_c.py::test_gone"])
    f = tmp_path / "pytest.txt"
    f.write_text(_OUT, encoding="utf-8")
    code, text = _run(capsys, check=True, from_file=str(f))
    assert code == 1  # a new failure still exits 1
    assert "new: 1\nfixed: 1\ninherited: 1" in text
    assert "tests/test_b.py::test_new" in text
    assert '--whose "tests/test_b.py::test_new"' in text


def test_missing_and_unreadable_file_are_structured_errors(baseline, capsys, tmp_path):
    code, text = _run(capsys)
    assert code == 2
    assert "code: USAGE" in text
    code, text = _run(capsys, from_file=str(tmp_path / "nope.txt"))
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_record_confirms_what_was_stored(baseline, capsys, tmp_path):
    f = tmp_path / "pytest.txt"
    f.write_text(_OUT, encoding="utf-8")
    code, text = _run(capsys, from_file=str(f), sha="deadbeef")
    assert code == 0
    assert "recorded: 2\nsha: deadbee" in text
    rec = sb.read()
    assert rec is not None
    assert rec["seat"] == "bench"


def test_boot_line_unchanged(baseline):
    _write_baseline(baseline, ["tests/test_a.py::test_old"], lane="T1")
    line = sb.render_boot_line()
    assert line.startswith("# suite baseline @abc1234 (")
    assert "by kimi): 1 known failure(s)" in line
    assert "1 classified lane(s) since closed (T1)" in line


def test_human_check(baseline, capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _write_baseline(baseline, ["tests/test_a.py::test_old"])
    f = tmp_path / "pytest.txt"
    f.write_text(_OUT, encoding="utf-8")
    _, text = _run(capsys, check=True, from_file=str(f))
    assert "1 new  0 fixed  1 inherited" in text
    assert "NEW tests/test_b.py::test_new" in text
