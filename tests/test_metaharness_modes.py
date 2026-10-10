"""Two execution modes for memory (meta-harness task 10).

Pinned here:
  * the switch: unset is interpretive and changes nothing; precompiled pushes nothing; hybrid
    skips exactly the lessons compiled into the ACTIVE harness;
  * in hybrid mode no lesson is both compiled into a harness and pushed at action time there;
  * the four-arm report gives each arm's scores with intervals and picks the default mode:
    the best pass rate, then the cheapest;
  * placement promotes, demotes and recompiles on evidence, and a compiled lesson that changes
    queues a recompile.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metaharness_fixtures import build_world, fake_candidate  # noqa: E402  # sys.path bootstrap

from core.foundation.store import FileStore  # noqa: E402  # sys.path bootstrap
from core.learning.learning_store import LearningStore  # noqa: E402  # sys.path bootstrap
from core.metaharness import modes, precompile, replay  # noqa: E402  # sys.path bootstrap

PYTEST = [sys.executable, "-m", "pytest"]
OLD = (datetime.now(UTC) - timedelta(days=60)).replace(tzinfo=None).isoformat()
CLAUDE_ONLY = json.dumps(
    {"candidate": "c", "harnesses": {"claude-code": ["CLAUDE.md"]}, "at": "2026-10-01T00:00:00+00:00"}
)


def _items() -> list[dict]:
    return [{"source": "learn:experiment:a", "compiled_into": CLAUDE_ONLY}, {"source": "learn:experiment:b"}]


def test_unset_is_interpretive_and_changes_nothing():
    assert modes.mode({}) == "interpretive"
    assert modes.mode({"AKASHIC_MEMORY_MODE": "nonsense"}) == "interpretive"
    assert modes.filter_for_mode(_items(), env={}) == _items()


def test_precompiled_pushes_nothing_and_hybrid_skips_only_the_active_harness():
    assert modes.filter_for_mode(_items(), env={"AKASHIC_MEMORY_MODE": "precompiled"}) == []
    hybrid = {"AKASHIC_MEMORY_MODE": "hybrid"}
    assert [i["source"] for i in modes.filter_for_mode(_items(), env=hybrid, harness="claude-code")] == [
        "learn:experiment:b"
    ]
    assert len(modes.filter_for_mode(_items(), env=hybrid, harness="codex-cli")) == 2, (
        "not compiled into codex: still pushed there"
    )


def test_in_hybrid_no_lesson_is_both_compiled_and_pushed(monkeypatch):
    from core.recall.at_action import recall_at

    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(prefix="modes_"), "l.json")))
    for name, compiled in (("tmp_flag_compiled", CLAUDE_ONLY), ("tmp_flag_plain", "")):
        sig = {
            "experiment_name": name,
            "what_tried": "pytest tempdir sandbox flag",
            "success": "yes",
            "recommendation": f"pytest tempdir sandbox flag {name}",
        }
        assert ls.persist_learning_derived_from_experiment(sig)
        if compiled:
            ls.store.hset(f"learn:experiment:{name}", mapping={"compiled_into": compiled})
    monkeypatch.setenv("AKASHIC_HARNESS", "claude-code")
    args: dict[str, Any] = {
        "command": "pytest tempdir sandbox flag",
        "learning_store": ls,
        "limit": 5,
        "min_relevance": 0.0,
        "applies_in": {},
    }
    monkeypatch.setenv("AKASHIC_MEMORY_MODE", "interpretive")
    assert {i["source"] for i in recall_at(**args)["lessons"]} == {
        "learn:experiment:tmp_flag_compiled",
        "learn:experiment:tmp_flag_plain",
    }
    monkeypatch.setenv("AKASHIC_MEMORY_MODE", "hybrid")
    pushed = {i["source"] for i in recall_at(**args)["lessons"]}
    assert pushed == {"learn:experiment:tmp_flag_plain"}
    monkeypatch.setenv("AKASHIC_MEMORY_MODE", "precompiled")
    assert recall_at(**args)["lessons"] == []


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    repo, ids, agent = build_world(tmp_path, n=6)
    fake_candidate("base", agent, "modes")
    store = FileStore(str(tmp_path / "memory.json"))
    lesson = {
        "experiment_name": "plus_everywhere",
        "recommendation": "USE-PLUS in every f: return a + b.",
        "success": "yes",
        "timestamp": OLD,
    }
    store.hset("learn:experiment:plus_everywhere", mapping=lesson)
    store.lpush("learn:experiments:all", "plus_everywhere")
    res = precompile.build(
        [lesson], base="base", name="base-compiled", harnesses=("claude-code",), live_root=repo, force=True
    )
    assert res["built"]
    store.hset(
        "learn:experiment:plus_everywhere",
        mapping={
            "compiled_into": json.dumps(
                {"candidate": "base-compiled", "harnesses": {"claude-code": ["CLAUDE.md"]}, "at": OLD}
            )
        },
    )
    return repo, ids, store


def test_the_four_arms_report_and_choose_a_default(world):
    repo, ids, store = world
    rep = modes.compare("base", "base-compiled", ids, trials=1, repo=repo, runner=PYTEST, store=store)
    s = rep["scores"]
    assert s["bare"]["pass_rate"] == 0.5
    assert s["interpretive"]["pass_rate"] == s["precompiled"]["pass_rate"] == s["hybrid"]["pass_rate"] == 1.0
    assert s["interpretive"]["tokens"] > s["precompiled"]["tokens"], "a pushed lesson costs context"
    assert s["hybrid"]["tokens"] == s["precompiled"]["tokens"], "hybrid does not push what is compiled"
    assert rep["default_mode"] == "precompiled"
    assert rep["vs_interpretive"]["bare"]["functional"]["verdict"] == "worse"
    assert set(rep["vs_interpretive"]["precompiled"]["tokens"]) == {"effect", "ci", "verdict"}
    assert (Path(os.environ["AI_SETUP"]) / "metaharness" / "modes" / "report-claude-code-fake.json").exists()
    hybrid = replay.candidate(rep["arms"]["hybrid"])
    assert hybrid["env"]["AKASHIC_MEMORY_MODE"] == "hybrid"
    assert "claude_pretooluse.py" in (Path(hybrid["overlay"]) / ".claude" / "settings.json").read_text(), (
        "the recall hook is switched on for interpretive arms"
    )


def test_placement_and_staleness():
    fresh_compiled = {
        "experiment_name": "edited",
        "compiled_into": json.dumps({"harnesses": {"claude-code": ["CLAUDE.md"]}, "at": "2026-01-01T00:00:00+00:00"}),
        "timestamp": "2026-09-01T00:00:00",
    }
    unused = {
        "experiment_name": "unused",
        "compiled_into": json.dumps(
            {"harnesses": {"claude-code": [".agents/skills/x/SKILL.md"]}, "at": "2026-12-01T00:00:00+00:00"}
        ),
        "timestamp": "2026-01-01T00:00:00",
    }
    used = {**unused, "experiment_name": "used"}
    proven = {
        "experiment_name": "proven",
        "recommendation": "Use uv for every Python command.",
        "success": "yes",
        "timestamp": OLD,
        "proven_effect": json.dumps({"ci": [0.1, 0.5]}),
    }
    narrow = {"experiment_name": "narrow", "recommendation": "Sometimes it flakes; rerun it alone.", "timestamp": OLD}
    rows = {
        r["lesson"]: r["move"]
        for r in modes.placement([fresh_compiled, unused, used, proven, narrow], used={".agents/skills/x/SKILL.md": 0})
    }
    assert rows == {"edited": "recompile", "unused": "demote", "used": "demote", "proven": "compile", "narrow": "keep"}
    rows = {r["lesson"]: r["move"] for r in modes.placement([used], used={".agents/skills/x/SKILL.md": 3})}
    assert rows == {"used": "keep"}


def test_a_compiled_lesson_that_changes_queues_a_recompile(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    store = FileStore(str(tmp_path / "m.json"))
    store.hset("learn:experiment:c1", mapping={"experiment_name": "c1", "compiled_into": CLAUDE_ONLY})
    store.hset("learn:experiment:p1", mapping={"experiment_name": "p1"})
    ls = LearningStore(store=store)
    ls.mark_benched("c1", reason="never credited")
    ls.mark_benched("p1", reason="never credited")
    q = modes.recompile_queue()
    assert [r["lesson"] for r in q] == ["c1"], "only a COMPILED lesson needs a recompile"
    assert q[0]["why"] == "bench"
