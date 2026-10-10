"""The replayable task corpus (meta-harness task 03).

Pinned here:
  * archived transcripts and scenario files never hold a secret: every write is redacted and
    then checked, and a check hit refuses the write;
  * the miner proposes one scenario per done task with a real commit, never for a symbolic
    commit like HEAD, and never twice;
  * a test-oracle scenario validates only if its oracle fails on the start state and passes on
    the reference solution;
  * the holdout split is deterministic and near 30%; discrimination and retirement follow the
    recorded outcomes.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metaharness import corpus, redact, transcripts  # noqa: E402

FAKE_KEY = "sk-ant-api03-" + "A1b2C3d4E5f6G7h8I9j0" * 2


@pytest.fixture(autouse=True)
def _own_state(tmp_path, monkeypatch):
    """Each test gets its own metaharness state (state_root follows AI_SETUP)."""
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))


# --------------------------------------------------------------------------- redaction
def test_redaction_rewrites_visibly_and_the_check_then_passes():
    text = f'key={FAKE_KEY} and "api_key": "abcdef123456" and Bearer abcdefghijklmnopqrstuvwxyz'
    out = redact.redact(text)
    assert FAKE_KEY not in out
    assert "[REDACTED-KEY]" in out
    assert "abcdef123456" not in out
    assert redact.find_secrets(out) == []


def test_the_check_catches_what_the_rewrite_cannot():
    assert redact.find_secrets("-----BEGIN RSA PRIVATE KEY-----\nMIIE") == ["private key block"]


# --------------------------------------------------------------------------- transcripts
def test_archive_redacts_skips_unchanged_and_refuses_a_leak(tmp_path):
    src = tmp_path / "sess-a.jsonl"
    src.write_text(json.dumps({"message": {"content": f"use {FAKE_KEY}"}}) + "\n", encoding="utf-8")
    leak = tmp_path / "sess-b.jsonl"
    leak.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n", encoding="utf-8")
    r = transcripts.archive([("claude-code", src), ("claude-code", leak)], cap_mb=10)
    assert r["archived"] == 1
    assert len(r["refused"]) == 1
    assert "sess-b" in r["refused"][0]
    meta = transcripts.sessions()["sess-a"]
    assert meta["prov"] == "prov:session:sess-a"
    with gzip.open(transcripts._root() / meta["path"], "rt") as f:
        body = f.read()
    assert FAKE_KEY not in body
    assert "[REDACTED-KEY]" in body
    assert transcripts.read("sess-a")[0]["message"]["content"].startswith("use [REDACTED")
    again = transcripts.archive([("claude-code", src)], cap_mb=10)
    assert again["unchanged"] == 1
    assert again["archived"] == 0


def test_archive_stops_at_the_cap_without_evicting(tmp_path):
    big = tmp_path / "big.jsonl"
    big.write_text("x" * (2 * 1024 * 1024), encoding="utf-8")
    r = transcripts.archive([("codex-cli", big)], cap_mb=1)
    assert r["capped"] is True
    assert r["archived"] == 0


# --------------------------------------------------------------------------- mining
def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "init")
    (r / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (r / "tests").mkdir()
    (r / "tests" / "test_calc.py").write_text(
        "import sys, os\nsys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
        "from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n",
        encoding="utf-8",
    )
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "fix add")
    fix = _git(r, "rev-parse", "HEAD")
    (r / "README.md").write_text("# calc\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "docs")
    docs = _git(r, "rev-parse", "HEAD")
    hist = [{"to": "claimed", "at": "2026-10-01T00:00:00+00:00"}, {"to": "done", "at": "2026-10-01T01:00:00+00:00"}]
    ledger = {
        "seq": 3,
        "tasks": [
            {
                "id": "T1",
                "title": "add must add",
                "status": "done",
                "commit": fix[:8],
                "owner": "claude",
                "history": hist,
                "acceptance": f"tests pass; token {FAKE_KEY}",
            },
            {
                "id": "T2",
                "title": "write a readme",
                "status": "done",
                "commit": docs,
                "owner": "claude",
                "history": hist,
            },
            {"id": "T3", "title": "symbolic", "status": "done", "commit": "HEAD", "owner": "claude", "history": hist},
            {"id": "T4", "title": "not done", "status": "approved", "commit": fix, "owner": "claude"},
        ],
    }
    lp = tmp_path / "tasks.json"
    lp.write_text(json.dumps(ledger), encoding="utf-8")
    return r, lp, fix, docs


def test_the_miner_writes_one_scenario_per_real_done_task(repo):
    r, lp, fix, docs = repo
    events = [
        {"kind": "fail", "agent_id": "claude", "at": "2026-10-01T00:30:00+00:00"},
        {"kind": "flip", "agent_id": "claude", "at": "2026-10-01T00:31:00+00:00"},
    ]
    new = corpus.mine(ledger_path=str(lp), repo=r, events=events)
    ids = sorted(n["id"] for n in new)
    assert ids == [f"T1-{fix[:8]}", f"T2-{docs[:8]}"], "HEAD and not-done tasks must not be mined"
    t1 = corpus.labels(f"T1-{fix[:8]}")
    assert t1["oracle"] == "tests"
    assert t1["signals"] == {"fails": 1, "flips": 1, "lessons": 0}
    assert t1["priority"] == 3
    d = corpus.scenario_dir(t1["id"])
    assert (d / "start.sha").read_text().strip() == _git(r, "rev-parse", f"{fix}^")
    assert (d / "oracle" / "tests.txt").read_text().split() == ["tests/test_calc.py"]
    assert "calc.py" in (d / "reference" / "solution.patch").read_text()
    assert "test_calc" not in (d / "reference" / "solution.patch").read_text()
    assert FAKE_KEY not in (d / "prompt.md").read_text(), "the prompt is redacted"
    assert corpus.labels(f"T2-{docs[:8]}")["oracle"] == "rubric"
    assert (corpus.scenario_dir(f"T2-{docs[:8]}") / "oracle" / "rubric.md").exists()
    assert corpus.mine(ledger_path=str(lp), repo=r, events=events) == [], "mining is idempotent"


def test_validation_needs_fail_on_start_and_pass_on_reference(repo):
    r, lp, fix, _ = repo
    corpus.mine(ledger_path=str(lp), repo=r, events=[])
    res = corpus.validate(f"T1-{fix[:8]}", repo=r, runner=[sys.executable, "-m", "pytest"])
    assert res == {"id": f"T1-{fix[:8]}", "ok": True, "fails_on_start": True, "passes_on_reference": True}
    assert _git(r, "worktree", "list").count("\n") == 0, "the throwaway worktree is removed"
    assert corpus.labels(f"T1-{fix[:8]}")["validated"]["ok"] is True


# --------------------------------------------------------------------------- curation
def test_the_holdout_split_is_deterministic_and_near_thirty_percent():
    ids = [f"T{i}-abcdef12" for i in range(2000)]
    share = sum(corpus.split_for(i) == "holdout" for i in ids) / len(ids)
    assert 0.26 < share < 0.34
    assert corpus.split_for("T7-abcdef12") == corpus.split_for("T7-abcdef12")


def test_discrimination_select_and_retire(repo):
    r, lp, fix, docs = repo
    corpus.mine(ledger_path=str(lp), repo=r, events=[])
    a, b = f"T1-{fix[:8]}", f"T2-{docs[:8]}"
    for sid in (a, b):
        corpus.set_status(sid, "accepted", by="tester")
        corpus.save_labels(sid, {**corpus.labels(sid), "split": "dev"})
    for cand, ok in (("c1", True), ("c2", False), ("c3", True)):
        corpus.record_outcome(a, cand, ok)
        corpus.record_outcome(b, cand, True)
    assert corpus.labels(a)["discrimination"] == pytest.approx(0.333)
    assert corpus.labels(b)["discrimination"] == 0.0
    assert corpus.select(split="dev")[0] == a, "high disagreement is spent on first"
    assert corpus.retire_saturated() == [b]
    st = corpus.status()
    assert st["by_status"] == {"accepted": 1, "retired": 1}


def test_a_status_outside_the_lifecycle_is_refused(repo):
    r, lp, fix, _ = repo
    corpus.mine(ledger_path=str(lp), repo=r, events=[])
    with pytest.raises(ValueError, match="status must be one of"):
        corpus.set_status(f"T1-{fix[:8]}", "maybe")


def test_state_lives_under_the_isolated_state_root():
    assert str(corpus.corpus_dir()).startswith(os.environ["AI_SETUP"])
    assert os.environ.get("_AISETUP_TEST_ISOLATED")
