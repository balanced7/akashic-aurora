"""Harness compression (meta-harness task 11).

Pinned here:
  * the screening designs: Hadamard matrices from Sylvester and both Paley constructions,
    Plackett-Burman designs that are orthogonal and balanced, and a foldover;
  * main effects with intervals recover planted effects; the Lasso finds a sparse signal;
    noisy ddmin removes a redundant pair only one member at a time;
  * THE PLANTED TEST from the task: a harness with 5 useful, 2 redundant-pair and 20 useless
    pieces -- the method keeps every useful piece and one of the pair, drops every useless
    piece, stays non-inferior, and does it within the stated budget;
  * the piece registry and masks: sections cut, skills and subagents deleted through the
    overlay deletion list, hook entries removed; telemetry finds never-used pieces.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metaharness import compress  # noqa: E402  # sys.path bootstrap


def test_hadamard_and_pb_designs():
    for n in (4, 8, 12, 20, 24, 28, 36, 44):
        h = compress.hadamard(n)
        assert compress._is_hadamard(h), n
    for k in (5, 11, 16, 27):
        d = compress.pb_design(k)
        assert d.shape[0] % 4 == 0
        assert d.shape[0] > k
        assert np.array_equal(d.T @ d, d.shape[0] * np.eye(k)), "orthogonal columns"
        assert not d.sum(0).any(), "each factor kept in exactly half the runs"
    f = compress.foldover(compress.pb_design(7))
    assert f.shape == (16, 7)
    assert not f.sum(0).any()


def test_main_effects_recover_planted_effects():
    d = compress.foldover(compress.pb_design(11))
    rng = random.Random(3)
    truth = [0.3, 0.0, -0.2] + [0.0] * 8
    y = [0.5 + sum(t * x / 2 for t, x in zip(truth, row, strict=True)) + rng.gauss(0, 0.01) for row in d]
    eff = compress.main_effects(d, y)
    assert eff[0]["effect"] == pytest.approx(0.3, abs=0.02)
    assert eff[2]["effect"] == pytest.approx(-0.2, abs=0.02)
    assert eff[1]["lo"] < 0 < eff[1]["hi"]


def test_lasso_finds_a_sparse_signal():
    rng = np.random.default_rng(0)
    x = (rng.random((120, 10)) < 0.8).astype(float)
    y = list(0.4 * x[:, 2] + 0.3 * x[:, 7] + rng.normal(0, 0.01, 120))
    w = compress.lasso(x, y, 0.01)
    assert {i for i, v in enumerate(w) if abs(v) > 1e-6} == {2, 7}


def test_ddmin_never_removes_both_halves_of_a_redundant_pair():
    def ok(removed: set[str]) -> bool:
        return not {"a", "b"} <= removed and "u" not in removed

    removed = compress.noisy_ddmin(["a", "b", "x", "y", "u", "z"], ok)
    assert {"x", "y", "z"} <= removed
    assert "u" not in removed
    assert len({"a", "b"} & removed) == 1


def test_non_inferiority():
    assert compress.non_inferior([0.0, 0.01, -0.01, 0.0, 0.02, -0.005] * 5, 0.03)
    assert not compress.non_inferior([-0.1, -0.08, -0.12, -0.09] * 5, 0.03)


# --------------------------------------------------------------------------- the planted test
def _planted():
    useful = [{"id": f"useful{i}", "group": f"g-useful{i}", "kind": "section"} for i in range(5)]
    pair = [{"id": "pairA", "group": "g-pair", "kind": "skill"}, {"id": "pairB", "group": "g-pair", "kind": "skill"}]
    useless = [{"id": f"useless{i}", "group": f"g-useless{i // 2}", "kind": "section"} for i in range(20)]
    return useful + pair + useless


def _evaluate(mask: dict[str, bool], scenario: str) -> float:
    score = 0.3 + 0.1 * sum(mask[f"useful{i}"] for i in range(5)) + (0.1 if mask["pairA"] or mask["pairB"] else 0.0)
    seed = int(
        hashlib.sha256(json.dumps([sorted(k for k, v in mask.items() if not v), scenario]).encode()).hexdigest()[:8], 16
    )
    return score + random.Random(seed).gauss(0, 0.02)


def test_the_planted_harness_is_compressed_correctly_within_budget():
    items = _planted()
    scenarios = [f"s{i}" for i in range(40)]
    res = compress.compress(items, _evaluate, scenarios, screen_scenarios=20, margin=0.03)
    kept, dropped = set(res["kept"]), set(res["dropped"])
    assert {f"useful{i}" for i in range(5)} <= kept, res["group_effects"]
    assert {f"useless{i}" for i in range(20)} <= dropped
    assert len({"pairA", "pairB"} & kept) == 1, "one of the redundant pair stays"
    assert res["non_inferior"] is True
    assert set(res["hot_groups"]) == {f"g-useful{i}" for i in range(5)} | {"g-pair"}
    # the plan's budget: about 1.5k-3.5k task-runs; leave-one-out at equal precision is 10-25x more
    assert res["task_runs"] <= 3500, res["task_runs"]


# --------------------------------------------------------------------------- registry and masks
@pytest.fixture
def tree(tmp_path):
    r = tmp_path / "live"
    (r / ".agents" / "skills" / "ship").mkdir(parents=True)
    (r / ".agents" / "skills" / "ship" / "SKILL.md").write_text("---\nname: ship\n---\n", encoding="utf-8")
    (r / ".claude" / "agents").mkdir(parents=True)
    (r / ".claude" / "agents" / "reviewer.md").write_text("---\nname: reviewer\n---\n", encoding="utf-8")
    (r / "AGENTS.md").write_text(
        "# AGENTS\n\nintro\n\n## Boot first\nrun boot\n\n## Locks\nclaim locks\n", encoding="utf-8"
    )
    hooks = {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 a/claude_trace.py"}]},
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 a/claude_pretooluse.py"}]},
        ]
    }
    (r / ".claude" / "settings.json").write_text(json.dumps({"env": {"X": "1"}, "hooks": hooks}), encoding="utf-8")
    return r


def test_the_registry_finds_every_kind_of_piece(tree):
    ids = {p["id"] for p in compress.pieces(tree)}
    assert ids == {
        "section:AGENTS.md#boot-first",
        "section:AGENTS.md#locks",
        "skill:ship",
        "subagent:reviewer",
        "hook:PreToolUse:claude_trace.py",
        "hook:PreToolUse:claude_pretooluse.py",
    }


def test_a_mask_cuts_sections_deletes_files_and_removes_hooks(tree, tmp_path):
    from core.metaharness.replay import OVERLAY_DELETE

    items = compress.pieces(tree)
    keep = {p["id"]: True for p in items}
    keep.update({"section:AGENTS.md#locks": False, "skill:ship": False, "hook:PreToolUse:claude_trace.py": False})
    out = compress.apply_mask(tree, items, keep, tmp_path / "ov")
    agents = (out / "AGENTS.md").read_text()
    assert "## Boot first" in agents
    assert "## Locks" not in agents
    assert "intro" in agents
    assert (out / OVERLAY_DELETE).read_text().split() == [".agents/skills/ship"]
    settings = json.loads((out / ".claude" / "settings.json").read_text())
    assert settings["env"] == {"X": "1"}
    assert "claude_trace.py" not in json.dumps(settings)
    assert "claude_pretooluse.py" in json.dumps(settings)


def test_the_replay_sandbox_honours_the_deletion_list(tmp_path):
    import subprocess

    from core.metaharness import replay

    repo = tmp_path / "repo"
    (repo / "keep").mkdir(parents=True)
    (repo / "keep" / "a.txt").write_text("a", encoding="utf-8")
    (repo / "gone").mkdir()
    (repo / "gone" / "b.txt").write_text("b", encoding="utf-8")
    for cmd in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "."],
        ["commit", "-qm", "x"],
    ):
        subprocess.run(["git", *cmd], cwd=repo, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    ov = tmp_path / "ov"
    (ov / ".aurora").mkdir(parents=True)
    (ov / replay.OVERLAY_DELETE).write_text("gone\n../escape\n", encoding="utf-8")
    wd = tmp_path / "wd"
    replay.prepare_sandbox(sha, wd, ov, repo=repo)
    assert (wd / "keep" / "a.txt").exists()
    assert not (wd / "gone").exists()
    assert not (wd / replay.OVERLAY_DELETE).exists(), "the list never reaches the agent"


def test_telemetry_counts_uses_and_names_never_used_pieces(tree, tmp_path):
    items = compress.pieces(tree)
    rd = tmp_path / "run"
    rd.mkdir()
    lines = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ship"}}]},
        },
        {"type": "system", "subtype": "hook", "text": "PreToolUse hook claude_pretooluse.py ran"},
    ]
    (rd / "transcript.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    uses = compress.telemetry([rd], items)
    assert uses["skill:ship"] == 1
    assert uses["hook:PreToolUse:claude_pretooluse.py"] == 1
    assert compress.drop_candidates(uses, min_runs=1, n_runs=1) == sorted(
        [
            "section:AGENTS.md#boot-first",
            "section:AGENTS.md#locks",
            "subagent:reviewer",
            "hook:PreToolUse:claude_trace.py",
        ]
    )
    assert compress.drop_candidates(uses, min_runs=20, n_runs=1) == [], "one run cannot prove never"


def test_a_real_candidate_is_compressed_through_replay_and_queued(tmp_path, monkeypatch):
    from metaharness_fixtures import build_world, fake_candidate

    from core.metaharness import replay, review

    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=3)
    fake_candidate("full", agent, "aware")
    ov = Path(replay.candidate("full")["overlay"])
    (ov / "CLAUDE.md").write_text(
        "# Harness\n\n## Fix\nFIX-EVERYTHING\n\n## Fluff\nbe nice to the code\n", encoding="utf-8"
    )
    res = compress.run_compression(
        "full",
        ids,
        repo=repo,
        max_runs=400,
        runner=[sys.executable, "-m", "pytest"],
        screen_scenarios=3,
        item_masks=6,
        margin=0.05,
    )
    assert res["built"] is True, res
    assert res["dropped"] == ["section:CLAUDE.md#fluff"]
    assert "section:CLAUDE.md#fix" in res["kept"]
    assert res["non_inferior"] is True
    out = (Path(replay.candidate(res["candidate"])["overlay"]) / "CLAUDE.md").read_text()
    assert "FIX-EVERYTHING" in out
    assert "be nice" not in out
    contract = json.loads((Path(replay.candidate(res["candidate"])["overlay"]).parent / "contract.json").read_text())
    assert set(contract["piece_effects"]["groups"]) == {"CLAUDE.md#fix", "CLAUDE.md#fluff"}
    assert review.item(res["queued_for_review"])["status"] == "pending"


def test_the_run_cap_stops_a_real_compression(tmp_path, monkeypatch):
    from metaharness_fixtures import build_world, fake_candidate

    from core.metaharness import replay

    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=2)
    fake_candidate("full", agent, "aware")
    (Path(replay.candidate("full")["overlay"]) / "CLAUDE.md").write_text(
        "# H\n\n## A\nx\n\n## B\ny\n", encoding="utf-8"
    )
    res = compress.run_compression(
        "full", ids, repo=repo, max_runs=3, runner=[sys.executable, "-m", "pytest"], screen_scenarios=2, item_masks=4
    )
    assert res["built"] is False
    assert "cap of 3" in res["why"]
