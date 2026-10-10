"""The human review queue (meta-harness task 06).

Pinned here:
  * no harness change reaches the live config without a recorded human accept;
  * every decision is stored with its reasons, linked to the runs, and its per-criterion calls
    land beside the grader's calls (model criteria also feed the judge calibration);
  * a high-risk surface (hooks, guards, settings) needs two distinct reviewers;
  * rollback restores the previous config exactly, including files apply created;
  * the provisional watch rolls back on worse live signals and keeps a change that holds;
  * a rejected item is written back to the candidate's folder for the proposer.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metaharness_fixtures import build_world, fake_candidate  # noqa: E402

from core.metaharness import graders, replay, review  # noqa: E402

PYTEST = [sys.executable, "-m", "pytest"]


@pytest.fixture
def queued(tmp_path, monkeypatch):
    """A graded good-vs-bad comparison queued for review, with a live root to apply to."""
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=3)
    fake_candidate("bad", agent, "bad")
    fake_candidate("good", agent, "good")
    ov = replay.candidates_dir() / "good" / "overlay"
    (ov / "AGENTS.md").write_text("new contract\n", encoding="utf-8")
    (ov / "docs").mkdir()
    (ov / "docs" / "NEW.md").write_text("created by apply\n", encoding="utf-8")
    for name in ("bad", "good"):
        for s in ids:
            for r in replay.run(name, s, trials=1, repo=repo):
                graders.grade_run(Path(r["run_dir"]), s, repo=repo, runner=PYTEST)
    live = tmp_path / "live"
    live.mkdir()
    (live / "AGENTS.md").write_text("old contract\n", encoding="utf-8")
    v = graders.compare("bad", "good", ids)
    it = review.enqueue("good", v, live_root=live, predicted="every scenario passes")
    return it, live, ids


def test_an_item_carries_verdict_diff_runs_and_prediction(queued):
    it, _live, ids = queued
    assert it["status"] == "pending"
    assert it["predicted"] == "every scenario passes"
    assert set(it["show_scenarios"]) <= set(ids)
    assert len(it["show_scenarios"]) == 3
    diff = (review.queue_dir() / it["id"] / "config.diff").read_text()
    assert "-old contract" in diff
    assert "+new contract" in diff
    page = review.render(it["id"]).read_text()
    assert "Config diff" in page
    assert "review decide" in page
    assert [x["id"] for x in review.pending()] == [it["id"]]


def test_no_change_lands_without_a_recorded_accept(queued):
    it, live, _ = queued
    with pytest.raises(PermissionError, match="no harness change lands without a recorded accept"):
        review.apply(it["id"], live_root=live)
    assert (live / "AGENTS.md").read_text() == "old contract\n"


def test_decisions_are_recorded_with_reasons_and_labels(queued):
    it, _live, _ = queued
    with pytest.raises(ValueError, match="reviewer and a reason"):
        review.decide(it["id"], "ana", "accept", {}, "  ")
    with pytest.raises(ValueError, match="per-criterion calls"):
        review.decide(it["id"], "ana", "accept", {"functional": "great"}, "x")
    it = review.decide(it["id"], "ana", "accept", {"functional": "better", "quality": "same"}, "passes everything")
    assert it["status"] == "accepted"
    assert it["decisions"][0]["reason"] == "passes everything"
    labels = [json.loads(x) for x in (review.queue_dir() / "labels.jsonl").read_text().splitlines()]
    assert {"criterion": "functional", "person": "better", "grader": "better"}.items() <= labels[0].items()
    assert graders.agreement("quality")["n"] == 1, "a model criterion feeds the judge calibration"
    assert review.disagreements() == [], "functional agreed; quality had no grader call (same == same)"


def test_apply_then_rollback_restores_exactly(queued):
    it, live, _ = queued
    review.decide(it["id"], "ana", "accept", {"functional": "better"}, "ok")
    applied = review.apply(
        it["id"], live_root=live, signals={"fails": 0, "flips": 0, "repeats": 0, "churn": 0, "sessions": 0, "days": 14}
    )
    assert applied["status"] == "applied"
    assert (live / "AGENTS.md").read_text() == "new contract\n"
    assert (live / "docs" / "NEW.md").exists()
    review.rollback(it["id"], reason="test")
    assert (live / "AGENTS.md").read_text() == "old contract\n"
    assert not (live / "docs" / "NEW.md").exists(), "a file apply created is removed again"
    back = (replay.candidates_dir() / "good" / "reviews.jsonl").read_text()
    assert "rolled back: test" in back


def test_high_risk_surfaces_need_two_reviewers(tmp_path, monkeypatch, queued):
    it, live, _ = queued
    ov = replay.candidates_dir() / "good" / "overlay"
    (ov / ".claude").mkdir()
    (ov / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    risky = review.enqueue("good", it["verdict"], live_root=live)
    assert risky["reviewers_needed"] == 2
    assert review.decide(risky["id"], "ana", "accept", {}, "fine")["status"] == "pending"
    assert review.decide(risky["id"], "ana", "accept", {}, "still fine")["status"] == "pending", (
        "the same reviewer twice is one reviewer"
    )
    assert review.decide(risky["id"], "bo", "accept", {}, "agree")["status"] == "accepted"


def test_reject_writes_back_for_the_proposer(queued):
    it, _, _ = queued
    review.decide(it["id"], "ana", "reject", {"quality": "worse"}, "edits the contract without need")
    rec = json.loads((replay.candidates_dir() / "good" / "reviews.jsonl").read_text().splitlines()[-1])
    assert rec["status"] == "rejected"
    assert rec["reason"] == "edits the contract without need"
    assert review.pending() == []


def test_items_expire(queued):
    it, _, _ = queued
    stale = review.item(it["id"])
    stale["expires"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat(timespec="seconds")
    review._save(stale)
    assert review.pending() == []
    assert review.item(it["id"])["status"] == "expired"


def _events(start: datetime, kind: str, n: int) -> list[dict]:
    return [{"kind": kind, "at": (start + timedelta(minutes=i)).isoformat(timespec="seconds")} for i in range(n)]


def test_the_watch_rolls_back_on_worse_signals_and_keeps_what_holds(queued):
    it, live, _ = queued
    review.decide(it["id"], "ana", "accept", {}, "ok")
    t0 = datetime.now(UTC)
    before = review.live_signals(t0 - timedelta(days=14), t0, _events(t0 - timedelta(days=10), "fail", 6), [])
    review.apply(it["id"], live_root=live, signals=before)
    calm = review.watch(now=t0 + timedelta(days=1), events=_events(t0 + timedelta(hours=1), "fail", 1), repeats=[])
    assert calm[0]["status"] == "applied", "too few events to call it worse"
    bad = review.watch(now=t0 + timedelta(days=2), events=_events(t0 + timedelta(hours=1), "fail", 30), repeats=[])
    assert bad[0]["status"] == "rolled_back"
    assert (live / "AGENTS.md").read_text() == "old contract\n"


def test_a_change_that_holds_for_the_window_is_kept(queued):
    it, live, _ = queued
    review.decide(it["id"], "ana", "accept", {}, "ok")
    t0 = datetime.now(UTC)
    review.apply(
        it["id"], live_root=live, signals={"fails": 6, "flips": 0, "repeats": 0, "churn": 0, "sessions": 0, "days": 14}
    )
    out = review.watch(now=t0 + timedelta(days=review.WATCH_DAYS, minutes=1), events=_events(t0, "fail", 2), repeats=[])
    assert out[0]["status"] == "kept"
    assert (live / "AGENTS.md").read_text() == "new contract\n"
