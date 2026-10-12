"""Pins for `corpus` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_corpus.py -q
"""

import argparse
import json

import pytest

from core.metaharness import cli, corpus


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _scenario(sid, status="candidate", title="Fix the adder", prompt="Make add() add."):
    corpus.save_labels(
        sid, {"id": sid, "title": title, "status": status, "split": "dev", "oracle": "tests", "priority": 3}
    )
    (corpus.scenario_dir(sid) / "prompt.md").write_text(prompt, encoding="utf-8")


def _run(capsys, action, id_="", **kw):
    ns = argparse.Namespace(
        action=action, id=id_, limit=None, status="", reason="", by="", cap_mb=None, fields=None, json=False
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.corpus_main(ns)
    return code, capsys.readouterr().out


def test_empty_list_and_status_say_zero_and_how_to_fill(capsys):
    code, text = _run(capsys, "list")
    assert code == 0
    assert "total: 0\nscenarios: []" in text
    assert "corpus mine" in text
    _, text = _run(capsys, "status")
    assert "total: 0" in text


def test_list_is_a_table_with_the_default_schema(capsys):
    _scenario("T1-aaaa")
    _scenario("T2-bbbb", status="accepted")
    _, text = _run(capsys, "list")
    assert "total: 2" in text
    assert "scenarios[2]{id,status,split,oracle,title}:" in text
    assert "T2-bbbb,accepted,dev,tests,Fix the adder" in text
    _, text = _run(capsys, "list", fields="priority")
    assert "{id,status,split,oracle,title,priority}" in text
    code, text = _run(capsys, "list", fields="bogus")
    assert code == 2
    assert "code: USAGE" in text


def test_show_cuts_a_long_prompt_and_points_at_the_file(capsys):
    _scenario("T1-aaaa", prompt="word " * 400)
    _, text = _run(capsys, "show", "T1-aaaa")
    assert "(truncated, 1999 chars total)" in text
    assert "prompt_file:" in text
    assert "corpus show T1-aaaa --json" in text


def test_missing_scenario_and_missing_id_are_structured_errors(capsys):
    code, text = _run(capsys, "show", "nope")
    assert code == 1
    assert "code: NOT_FOUND" in text
    code, text = _run(capsys, "accept")
    assert code == 2
    assert "code: USAGE" in text


def test_json_is_unchanged(capsys):
    _scenario("T1-aaaa")
    _, text = _run(capsys, "list", json=True)
    assert text == json.dumps([corpus.labels("T1-aaaa")], indent=1, default=str) + "\n"


def test_accept_confirms_and_human_list_is_a_table(capsys, monkeypatch):
    _scenario("T1-aaaa")
    code, text = _run(capsys, "accept", "T1-aaaa", reason="good test")
    assert code == 0
    assert "status: accepted" in text
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "list")
    assert "T1-aaaa" in text
    assert "accepted" in text
