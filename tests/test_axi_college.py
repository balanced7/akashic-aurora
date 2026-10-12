"""Pins for `college` after the AXI conversion: what an agent and a person see.

Courses live under a temporary AURORA_COLLEGE_ROOT, never the repo's artifacts/college.

Run: uv run pytest tests/test_axi_college.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.library.college import run_college


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_COLLEGE_ROOT", str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    run_college("start", "c1", {"title": "T", "topic": "x", "lecturer": "claude", "auditor": "kimi"}, actor="claude")
    return tmp_path


def _run(capsys, action, course="c1", **kw):
    ns = argparse.Namespace(college_action=action, course=course, actor="", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_college(ns)
    return code, capsys.readouterr().out


def test_show_is_stage_counts_and_gaps(root, capsys):
    code, text = _run(capsys, "show")
    assert code == 0
    assert "course: c1\ntitle: T\nlecturer: claude\nauditor: kimi" in text
    assert "sources: 0\nverified_primary: 0\nlecture: unsealed" in text
    assert "gaps[4]:" in text
    assert "no verified primary source" in text
    # the first gap's fix, with the seat the record names as the one who must act
    assert "college source c1 --id <id>" in text
    assert "--actor kimi" in text


def test_refusal_is_a_structured_error(root, capsys):
    code, text = _run(capsys, "start", title="T", topic="x", lecturer="a", auditor="b", actor="a")
    assert code == 2
    assert "code: REFUSED" in text
    assert "already exists" in text


def test_unknown_course(root, capsys):
    code, text = _run(capsys, "show", course="nope")
    assert code == 2
    assert "unknown college course" in text


def test_json_is_the_record(root, capsys):
    _, text = _run(capsys, "show", json=True)
    assert json.loads(text)["course"]["auditor"] == "kimi"


def test_human_view(root, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "show")
    assert "lecturer claude · auditor kimi" in text
    assert "gap: lecture is not sealed" in text
