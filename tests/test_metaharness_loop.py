"""The candidate archive and the proposer loop (meta-harness task 07).

Pinned here, with a scripted proposer and an overlay-aware fake agent:
  * the loop runs unattended within its budget and produces ranked candidates with verdicts; a
    candidate that beats its parent on the held-out scenarios goes to the human review queue,
    and the live harness is never touched;
  * every candidate traces back to its parent and its hypothesis;
  * contracts are enforced: no predictions, unlisted files or too many edits are refused;
  * predictions are checked, and a proposer whose predictions fail earns less budget;
  * the daily budget stops the loop; GEPA keeps per-scenario specialists; the flag optimiser
    finds the best config of a noisy objective under a constraint.
"""

from __future__ import annotations

import json
import random
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metaharness_fixtures import build_world, fake_candidate  # noqa: E402

from core.metaharness import archive, corpus, flags, loop, proposer, replay, review  # noqa: E402

PYTEST = [sys.executable, "-m", "pytest"]

FAKE_PROPOSER = textwrap.dedent(
    """
    import json, os, sys
    mode = sys.argv[1]
    os.makedirs("out/overlay", exist_ok=True)
    edits = [{"kind": "instruction", "path": "CLAUDE.md", "why": "tell the agent to fix the bug"}]
    if mode == "good":
        open("out/overlay/CLAUDE.md", "w").write("FIX-EVERYTHING\\n")
        preds = [{"metric": "pass_rate", "expect": "+50%"}]
    elif mode == "wrong":
        open("out/overlay/CLAUDE.md", "w").write("be careful\\n")
        preds = [{"metric": "pass_rate", "expect": "+50%"}]
    elif mode == "sprawl":
        for i in range(5):
            open(f"out/overlay/F{i}.md", "w").write("x")
            edits.append({"kind": "instruction", "path": f"F{i}.md", "why": "x"})
        preds = [{"metric": "tokens", "expect": "-10%"}]
    else:
        open("out/overlay/CLAUDE.md", "w").write("x")
        preds = []
    json.dump({"hypothesis": mode, "edits": edits, "predictions": preds}, open("out/contract.json", "w"))
    print(json.dumps({"type": "result", "total_cost_usd": 0.02, "usage": {}}))
    """
)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=6)
    for i, s in enumerate(ids):  # a fixed split: 4 dev, 2 holdout
        lab = corpus.labels(s)
        lab["split"] = "holdout" if i >= 4 else "dev"
        corpus.save_labels(s, lab)
    fake_candidate("baseline", agent, "aware", hypothesis="the live harness")
    prop = tmp_path / "fake_proposer.py"
    prop.write_text(FAKE_PROPOSER, encoding="utf-8")
    return repo, ids, prop


def _card(prop: Path, mode: str) -> dict:
    return {"model": f"fake-{mode}", "command": [sys.executable, str(prop), mode]}


def test_the_loop_finds_a_better_candidate_and_queues_it_for_review(world):
    repo, _ids, prop = world
    log = loop.iterate(
        "baseline",
        proposals=1,
        ladder=(2, 4),
        trials=1,
        holdout_n=2,
        daily_usd=10.0,
        repo=repo,
        proposer_card=_card(prop, "good"),
        runner=PYTEST,
    )
    assert len(log["proposed"]) == 1
    cand = log["proposed"][0]
    assert log["survivors"] == [cand]
    assert len(log["queued_for_review"]) == 1, log
    it = review.item(log["queued_for_review"][0])
    assert it["candidate"] == cand
    assert it["against"] == "baseline"
    assert it["status"] == "pending", "the loop queues; only a person's accept applies"
    assert archive.scores(cand)["pass_rate"] == 1.0
    assert archive.scores("baseline")["pass_rate"] == 0.0
    assert cand in log["front"]
    assert archive.lineage(cand) == [cand, "baseline"]
    assert replay.candidate(cand)["hypothesis"] == "good"
    assert "+FIX-EVERYTHING" in (archive.cdir(cand) / "parent.diff").read_text()
    pred = json.loads((archive.cdir(cand) / "prediction.json").read_text())
    assert (pred["hits"], pred["checked"]) == (1, 1)
    assert loop.spent_today() > 0


def test_a_candidate_that_does_not_beat_its_parent_is_not_queued(world):
    repo, _ids, prop = world
    log = loop.iterate(
        "baseline",
        proposals=1,
        ladder=(2,),
        trials=1,
        holdout_n=2,
        daily_usd=10.0,
        repo=repo,
        proposer_card=_card(prop, "wrong"),
        runner=PYTEST,
    )
    assert log["queued_for_review"] == []
    assert proposer.budget_weight("fake-wrong") < 0.5, "a failed prediction lowers the proposer's share"


def test_contracts_and_the_bundle_limit_are_enforced(world):
    _repo, ids, prop = world
    for mode, why in (("sprawl", "bundle limit"), ("nopred", "makes no predictions")):
        pack = proposer.build_pack("baseline", scenarios=ids[:2])
        proposer.run_proposer(pack, _card(prop, mode))
        res = proposer.accept(pack, proposer_id=mode)
        assert res["accepted"] is False
        assert any(why in e for e in res["errors"]), res["errors"]
    pack = proposer.build_pack("baseline", scenarios=ids[:2])
    (pack / "out" / "overlay" / "X.md").write_text("x", encoding="utf-8")
    (pack / "out" / "contract.json").write_text(
        json.dumps(
            {
                "hypothesis": "h",
                "edits": [{"kind": "skill", "path": "Y.md"}],
                "predictions": [{"metric": "tokens", "expect": "-5%"}],
            }
        ),
        encoding="utf-8",
    )
    assert any("not in the contract" in e for e in proposer.accept(pack)["errors"])


def test_the_pack_carries_raw_traces_and_rejections(world):
    repo, ids, _prop = world
    loop.evaluate("baseline", ids[:2], trials=1, daily_usd=10.0, repo=repo, runner=PYTEST)
    with (archive.cdir("baseline") / "reviews.jsonl").open("a") as f:
        f.write(json.dumps({"status": "rejected", "reason": "too clever"}) + "\n")
    pack = proposer.build_pack("baseline", scenarios=ids[:2])
    assert (pack / "traces" / ids[0] / "t1" / "transcript.jsonl").exists()
    assert (pack / "traces" / ids[0] / "t1" / "grade.json").exists()
    brief = (pack / "brief.md").read_text()
    assert "too clever" in brief
    assert "Prefer STRUCTURAL edits" in brief


def test_the_daily_budget_stops_the_loop(world):
    repo, _ids, prop = world
    logs = loop.run(
        "baseline",
        iterations=3,
        daily_usd=0.0001,
        proposals=1,
        ladder=(2,),
        trials=1,
        holdout_n=2,
        repo=repo,
        proposer_card=_card(prop, "good"),
        runner=PYTEST,
    )
    assert "daily budget" in logs[-1]["stopped"]


def test_gepa_keeps_per_scenario_specialists():
    rows = [
        {"name": "a", "scores": {"per_scenario_pass": {"s1": 1.0, "s2": 0.0}}},
        {"name": "b", "scores": {"per_scenario_pass": {"s1": 0.0, "s2": 1.0}}},
        {"name": "c", "scores": {"per_scenario_pass": {"s1": 0.5, "s2": 0.5}}},
    ]
    assert proposer.gepa_parents(rows) == ["a", "b"], "the average-but-never-best candidate is not a parent"


def test_the_flag_optimiser_finds_the_constrained_optimum():
    space = {
        "hook": {"type": "bool"},
        "floor": {"type": "float", "min": 0.0, "max": 1.0},
        "turns": {"type": "int", "min": 5, "max": 50},
    }
    rng = random.Random(1)

    def objective(c):  # best at hook on, floor near 0.3, more turns -- but turns cost money
        score = (0.4 if c["hook"] else 0.0) + 0.4 * (1 - abs(c["floor"] - 0.3)) + 0.2 * c["turns"] / 50
        return score + rng.gauss(0, 0.02), 0.02 * c["turns"]

    hist = []
    for i in range(24):
        for c in flags.suggest(space, hist, seed=i, constraint=("cost", 0.6)):
            s, cost = objective(c)
            hist.append({"config": c, "score": s, "cost": cost})
    feasible = [h for h in hist if h["cost"] <= 0.6]
    best = max(feasible, key=lambda h: h["score"])["config"]
    assert best["hook"] is True
    assert abs(best["floor"] - 0.3) < 0.2
    assert best["turns"] <= 30


def test_flags_render_into_an_overlay(tmp_path):
    p = flags.render({"AKASHIC_RECALL_AT_ACTION": True, "AKASHIC_RECALL_FLOOR": 0.25}, tmp_path)
    doc = json.loads(p.read_text())
    assert doc["env"] == {"AKASHIC_RECALL_AT_ACTION": "1", "AKASHIC_RECALL_FLOOR": "0.25"}
