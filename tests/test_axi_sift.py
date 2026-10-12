"""Pins for `sift` after the AXI conversion: the dry run, a refused run and the --json path.

Evidence comes from a hand-built corpus and the fan is faked, so nothing here calls a model.

Run: uv run pytest tests/test_axi_sift.py -q
"""

import pytest

import agent_cli
from core.comm import ask as ask_mod
from core.coord import sift as S
from core.outcome import BoundaryOutcome

CORPUS = {
    "core/a.py": "x = wakeable(1)\n# wakeable means a seat can be woken\n",
    "core/b.py": "if wakeable:\n    pass\n",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    real = S.evidence_pack
    monkeypatch.setattr(S, "evidence_pack", lambda term, **kw: real(term, corpus=CORPUS, **kw))


def _sift(*argv):
    return agent_cli.cmd_sift(agent_cli.build_parser().parse_args(["sift", *argv]))


def test_dry_run_counts_the_evidence_and_spends_nothing(capsys):
    assert _sift("wakeable", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "dry_run: true" in out
    assert "spent_usd: 0" in out
    assert "packs[1]{term,occurrences,files,sha,capped}:" in out
    assert "  wakeable,3,2," in out
    assert '"core/a.py:1"' in out
    assert "6 tier-1 branches (1 terms x 6 hats)" in out
    assert "sift wakeable --out sift.json" in out


def test_unknown_hat_is_a_usage_error_naming_the_known_ones(capsys):
    assert _sift("wakeable", "--hats", "nosuchhat", "--dry-run") == 2
    out = capsys.readouterr().out
    assert "code: USAGE" in out
    assert "known_hats[6]:" in out


def test_a_run_with_no_dossiers_is_refused_outright(monkeypatch, capsys):
    o = BoundaryOutcome.partially("nothing landed")
    o.detail.update(n=1, n_ok=0, branches=[{"ok": False, "answer": "", "why": "timeout"}])
    monkeypatch.setattr(ask_mod, "ask_many", lambda *a, **k: o)
    assert _sift("wakeable", "--hats", "outsider") == 0
    cap = capsys.readouterr()
    assert "refused: no curator dossiers landed" in cap.out
    assert "landed: 0" in cap.out
    assert "# tier 1: fanning" in cap.err  # progress of a paid run goes to stderr


def test_json_dry_run_keeps_its_old_text(capsys):
    assert _sift("wakeable", "--dry-run", "--json") == 0
    out = capsys.readouterr().out
    assert out.startswith("# sift: 1 term(s) x 6 hat(s), planes=['source'], evidence=breadth\n  wakeable     occ=3")
    assert "# DRY RUN -- nothing spent." in out


def test_human_dry_run_says_nothing_was_spent(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "160")
    assert _sift("wakeable", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "nothing spent" in out
    assert "evidence packs" in out
