"""Pins for `compress` after the AXI conversion: what an agent and a person see.

`compress run` is exercised on its refusal only: nothing replays.

Run: uv run pytest tests/test_axi_compress.py -q
"""

import argparse

import pytest

from core.metaharness import cli, compress


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _tree(root):
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# T\n\n## Start here\n\nboot\n\n## Learn\n\nlearn\n", encoding="utf-8")
    sk = root / ".agents" / "skills" / "one"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text("---\nname: one\n---\nbody\n", encoding="utf-8")
    return root


def _run(capsys, action, **kw):
    ns = argparse.Namespace(action=action, candidate="", scenario=None, root="", max_runs=0, trials=1, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.compress_main(ns)
    return code, capsys.readouterr().out


def test_pieces_counts_by_kind(capsys, tmp_path):
    root = _tree(tmp_path / "tree")
    n = len(compress.pieces(root))
    code, text = _run(capsys, "pieces", root=str(root))
    assert code == 0
    assert f"total: {n}" in text
    assert "by_kind:" in text
    assert f"pieces[{n}]{{id,kind}}:" in text


def test_empty_tree_says_zero(capsys, tmp_path):
    (tmp_path / "empty").mkdir()
    _, text = _run(capsys, "pieces", root=str(tmp_path / "empty"))
    assert "total: 0\npieces: []" in text


def test_telemetry_with_no_runs_says_so_and_how_to_get_runs(capsys, tmp_path):
    root = _tree(tmp_path / "tree")
    _, text = _run(capsys, "telemetry", candidate="baseline", scenario=["T1"], root=str(root))
    assert "runs_read: 0" in text
    assert "replay run --candidate baseline --scenario T1 --budget-usd 2" in text


def test_run_without_a_cap_is_refused_before_anything_runs(capsys, monkeypatch):
    monkeypatch.setattr(compress, "run_compression", lambda *a, **k: pytest.fail("ran without --max-runs"))
    code, text = _run(capsys, "run", candidate="baseline", scenario=["T1"])
    assert code == 2
    assert "code: USAGE" in text
    assert "--max-runs 20" in text


def test_human_pieces_is_a_table(capsys, monkeypatch, tmp_path):
    root = _tree(tmp_path / "tree")
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "pieces", root=str(root))
    assert "Harness pieces" in text
    assert "section" in text
