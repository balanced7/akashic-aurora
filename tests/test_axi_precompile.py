"""Pins for `precompile` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_precompile.py -q
"""

import argparse

import pytest

from core.metaharness import cli, precompile


class _LS:
    store = None

    def load_all_learnings_from_store(self):
        return [{"experiment_name": "a"}, {"experiment_name": "b"}]


def _gate(ok, **held):
    g = {"proven": True, "stable": True, "premise": True, **held}
    return {**g, "pass": ok, "proven_by": "credit"}


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    import core.learning.learning_store as ls_mod

    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(ls_mod, "get_learning_store_instance", lambda: _LS())


def _run(capsys, action, **kw):
    ns = argparse.Namespace(action=action, lesson=None, base="baseline", harness=None, force=False, root="", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.precompile_main(ns)
    return code, capsys.readouterr().out


def test_plan_names_the_gates_each_lesson_fails(capsys, monkeypatch):
    rows = [
        {"lesson": "a", "kind": "guard", "harnesses": ["claude-code"], "gates": _gate(True)},
        {"lesson": "b", "kind": "instruction", "harnesses": ["claude-code", "cursor"],
         "gates": _gate(False, proven=False, stable=False)},
    ]  # fmt: skip
    monkeypatch.setattr(precompile, "plan", lambda lessons, store=None: rows)
    code, text = _run(capsys, "plan")
    assert code == 0
    assert "total: 2\npassing: 1" in text
    assert "lessons[2]{lesson,kind,status,failing_gates,harnesses}:" in text
    assert 'b,instruction,held,"proven, stable","claude-code, cursor"' in text
    assert "precompile build" in text


def test_empty_plan_says_zero(capsys, monkeypatch):
    monkeypatch.setattr(precompile, "plan", lambda lessons, store=None: [])
    _, text = _run(capsys, "plan")
    assert "total: 0\npassing: 0\nlessons: []" in text


def test_build_with_nothing_passing_is_an_error_with_exit_1(capsys, monkeypatch):
    monkeypatch.setattr(precompile, "build", lambda *a, **k: {"built": False, "why": "no lesson passed the gates"})
    code, text = _run(capsys, "build")
    assert code == 1
    assert "code: NOTHING_TO_BUILD" in text
    assert "precompile build --force" in text


def test_check_reports_drift_as_data_with_exit_1(capsys, monkeypatch):
    monkeypatch.setattr(precompile, "check_drift", lambda root: ["CLAUDE.md: the generated block was edited"])
    code, text = _run(capsys, "check", root="/tmp/x")
    assert code == 1
    assert "drift: 1" in text
    monkeypatch.setattr(precompile, "check_drift", lambda root: [])
    code, text = _run(capsys, "check", root="/tmp/x")
    assert code == 0
    assert "drift: 0" in text


def test_human_plan_is_a_table(capsys, monkeypatch):
    rows = [{"lesson": "a", "kind": "guard", "harnesses": ["claude-code"], "gates": _gate(True)}]
    monkeypatch.setattr(precompile, "plan", lambda lessons, store=None: rows)
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "plan")
    assert "Precompile plan" in text
    assert "guard" in text
