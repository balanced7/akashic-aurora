"""Replay the memory system itself (meta-harness task 08).

Pinned here, with a fake agent that reads its run's private memory the way recall hands it
lessons (default: fixes half the bugs; a USE-PLUS lesson: all; a USE-MINUS-WRONG lesson: none):
  * a planted good lesson makes the after arm beat the before arm significantly, and a planted
    wrong lesson makes it worse;
  * the proven effect is stamped on the lesson (visible to `recall --full`) and moves the ranker;
  * each arm sees exactly one memory state, in a private store -- not the live one, not another
    arm's;
  * snapshots round-trip, ablation removes the lesson and its index memberships, and a lesson
    change queues itself with its previous record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metaharness_fixtures import build_world, fake_candidate  # noqa: E402

from core.foundation.store import FileStore  # noqa: E402
from core.metaharness import memreplay, replay, stats  # noqa: E402

PYTEST = [sys.executable, "-m", "pytest"]


def _lesson(store: FileStore, name: str, rec: str) -> None:
    store.hset(
        f"learn:experiment:{name}",
        mapping={
            "experiment_name": name,
            "recommendation": rec,
            "what_tried": "fix f",
            "timestamp": "2026-10-01T00:00:00",
            "files_affected": "[]",
        },
    )
    store.lpush("learn:experiments:all", name)
    store.zadd("learn:experiments:success", {name: 1.0})


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=6)
    fake_candidate("base", agent, "memory")
    store = FileStore(str(tmp_path / "memory.json"))
    _lesson(store, "unrelated_note", "keep commits small")
    return repo, ids, store


def test_snapshots_round_trip_and_ablation_removes_the_lesson(world, tmp_path):
    _, _, store = world
    _lesson(store, "plus_rule", "USE-PLUS when f subtracts")
    full = memreplay.capture(store=store, label="full")
    ablated = memreplay.capture(store=store, exclude=("plus_rule",), label="abl")
    target = tmp_path / "run_state"
    assert memreplay.load(full, target) >= 4
    fs = FileStore(str(target / "session_logs" / "store_state.json"))
    assert fs.hgetall("learn:experiment:plus_rule")["recommendation"] == "USE-PLUS when f subtracts"
    assert set(fs.lrange("learn:experiments:all", 0, -1)) == {"plus_rule", "unrelated_note"}
    snap = json.loads(ablated.read_text())
    assert "learn:experiment:plus_rule" not in snap["data"]
    assert "plus_rule" not in snap["data"]["learn:experiments:all"]["value"]
    assert all(m != "plus_rule" for m, _ in snap["data"]["learn:experiments:success"]["value"])


def test_a_planted_good_lesson_beats_its_absence(world):
    repo, ids, store = world
    _lesson(store, "plus_rule", "USE-PLUS when f subtracts")
    out = memreplay.experiment(
        "plus_rule",
        "base",
        scenarios=ids,
        previous=None,
        known_previous=True,
        trials=1,
        repo=repo,
        runner=PYTEST,
        store=store,
    )
    assert out["comparisons"]["after_vs_before"]["functional"] == stats.BETTER
    assert out["comparisons"]["after_vs_ablate"]["functional"] == stats.BETTER
    pe = out["proven_effect"]
    assert pe["effect"] == pytest.approx(0.5)
    assert pe["ci"][0] > 0
    assert pe["surfaced"]["after"] == len(ids)
    assert pe["surfaced"]["before"] == 0
    stamped = json.loads(store.hgetall("learn:experiment:plus_rule")["proven_effect"])
    assert stamped["verdict"] == stats.BETTER
    assert memreplay.ranker_factor(stamped) == memreplay.BOOST


def test_a_planted_wrong_lesson_does_worse(world):
    repo, ids, store = world
    _lesson(store, "minus_rule", "USE-MINUS-WRONG: keep the subtraction")
    out = memreplay.experiment(
        "minus_rule",
        "base",
        scenarios=ids,
        previous=None,
        known_previous=True,
        trials=1,
        repo=repo,
        runner=PYTEST,
        store=store,
    )
    assert out["comparisons"]["after_vs_before"]["functional"] == stats.WORSE
    assert memreplay.ranker_factor(out["proven_effect"]) == memreplay.DAMP


def test_an_edit_replays_against_the_previous_text(world):
    repo, ids, store = world
    _lesson(store, "rule", "USE-PLUS when f subtracts")
    previous = store.hgetall("learn:experiment:rule")
    _lesson(store, "rule", "USE-MINUS-WRONG: keep the subtraction")  # the edit made it wrong
    out = memreplay.experiment(
        "rule",
        "base",
        scenarios=ids,
        previous=previous,
        known_previous=True,
        trials=1,
        repo=repo,
        runner=PYTEST,
        store=store,
    )
    assert out["comparisons"]["after_vs_before"]["functional"] == stats.WORSE, "the edit is what is measured"


def test_each_arm_runs_on_its_own_private_store(world):
    repo, ids, store = world
    _lesson(store, "plus_rule", "USE-PLUS when f subtracts")
    names = memreplay.arm_candidates("base", "plus_rule", previous=None, known_previous=True, store=store)
    r = replay.run(names["after"], ids[0], trials=1, repo=repo)[0]
    env = json.loads(Path(r["run_dir"], "run.json").read_text())
    assert env["redis_db"] == 15
    card = replay.candidate(names["after"])
    sandbox_env = replay.sandbox_env(Path(r["run_dir"]), session_id="s", card=card, fixtures=None, redis_db=15)
    assert sandbox_env["REDIS_PORT"] == replay.CLOSED_REDIS_PORT, "an arm with a snapshot never reaches a shared Redis"
    assert sandbox_env["AKASHIC_RECALL_STATE_DIR"].startswith(r["run_dir"]), "nor the shared recall cache"
    private = FileStore(str(Path(r["run_dir"]) / "state" / "session_logs" / "store_state.json"))
    assert private.hgetall("learn:experiment:plus_rule")
    none = replay.run(names["none"], ids[0], trials=1, repo=repo)[0]
    empty = Path(none["run_dir"]) / "state" / "session_logs" / "store_state.json"
    assert not empty.exists() or not FileStore(str(empty)).hgetall("learn:experiment:plus_rule")


def test_a_lesson_change_queues_itself_with_its_previous_record(world, monkeypatch):
    from core.learning.learning_store import LearningStore

    _, _, store = world
    ls = LearningStore(store=store)
    _lesson(store, "q_rule", "USE-PLUS")
    before = store.hgetall("learn:experiment:q_rule")
    ls.mark_benched("q_rule", reason="never credited")
    q = {r["lesson"]: r for r in memreplay.queued()}
    assert q["q_rule"]["why"] == "bench"
    assert q["q_rule"]["previous"] == before
    monkeypatch.setenv("AKASHIC_MEMREPLAY_TRIGGERS", "0")
    ls.mark_graduated("unrelated_note", enforced_by="a hook")
    assert "unrelated_note" not in {r["lesson"] for r in memreplay.queued()}


def test_related_scenarios_use_files_and_trigger_words(world):
    _, ids, _ = world
    got = memreplay.related_scenarios(
        {"recommendation": "fix m3 before anything", "files_affected": json.dumps(["m3.py"])}
    )
    assert got[0] == ids[3]
