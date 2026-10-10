"""The precompiler (meta-harness task 09): lessons into harness primitives.

Pinned here:
  * routing puts each kind of lesson in its primitive, and a narrow lesson stays interpretive;
  * the gates hold a lesson that is unproven, fresh, or whose premise names a missing file;
  * ten lessons compile into at least three primitive types for each harness, as an archive
    candidate whose contract cites them -- never as a direct write to the live tree;
  * generated files rebuild exactly from the lessons, and a hand edit is caught;
  * the generated guard really blocks the command its lesson forbids;
  * a lesson's scope decides which harnesses get it, and apply stamps where it now lives.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.foundation.store import FileStore  # noqa: E402
from core.metaharness import precompile, replay, review  # noqa: E402

OLD = (datetime.now(UTC) - timedelta(days=60)).replace(tzinfo=None).isoformat()
PROVEN = json.dumps({"effect": 0.4, "ci": [0.1, 0.7], "verdict": "better"})


def L(name: str, rec: str, **kw) -> dict:
    return {
        "experiment_name": name,
        "recommendation": rec,
        "what_tried": kw.pop("tried", ""),
        "success": "yes",
        "timestamp": OLD,
        "proven_effect": PROVEN,
        **kw,
    }


LESSONS = [
    L("no_force_push", "Never run `git push --force` on master; open a PR instead."),
    L("no_verify_hooks", "Don't use `--no-verify` when committing: fix the hook failure."),
    L("redis_db_15", "Always pass `REDIS_DB=15` to `pytest` so tests never touch db 0."),
    L(
        "ship_release",
        "Use when cutting a release: 1. run the gate, 2. bump the version, then 3. tag and push the tag.",
    ),
    L("lock_then_edit", "Use when two agents edit one file: 1. claim the lock, then 2. edit, then 3. unlock."),
    L(
        "review_pass",
        "Use when a large PR needs a second look: delegate a review pass that reads only the diff and the tests.",
    ),
    L(
        "migration_pass",
        "Use when moving a module: run a migration subagent that updates every import and re-runs the suite.",
    ),
    L("uv_only", "Use uv for every Python command; never call pip directly."),
    L("docs_checker", "Docs pages must pass apps/docs/scripts/check-docs.mjs before a commit."),
    L("no_tool_for_ports", "There is no command for listing which world owns a port; a missing tool -- build one."),
    L("narrow_flake", "Sometimes the wake test flakes under load; rerun it alone before blaming the change."),
]


def test_routing_puts_each_lesson_in_its_primitive():
    kinds = {x["experiment_name"]: precompile.route(x) for x in LESSONS}
    assert kinds["no_force_push"] == kinds["no_verify_hooks"] == kinds["redis_db_15"] == "guard"
    assert kinds["ship_release"] == kinds["lock_then_edit"] == "skill"
    assert kinds["review_pass"] == kinds["migration_pass"] == "subagent"
    assert kinds["uv_only"] == "instruction"
    assert kinds["no_tool_for_ports"] == "tool"
    assert kinds["narrow_flake"] == "interpretive", "a hedged, narrow lesson stays with recall at action"


def test_the_gates_hold_unproven_fresh_and_broken_premise_lessons():
    assert precompile.gates(LESSONS[0])["pass"] is True
    assert precompile.gates({**LESSONS[0], "proven_effect": ""})["pass"] is False
    assert precompile.gates({**LESSONS[0], "proven_effect": ""}, use={"useful": 3})["proven_by"] == "credit"
    fresh = {**LESSONS[0], "timestamp": datetime.now(UTC).replace(tzinfo=None).isoformat()}
    assert precompile.gates(fresh)["stable"] is False
    broken = {**LESSONS[0], "recommendation": "Never run `git push --force`; see `core/does_not_exist.py`."}
    g = precompile.gates(broken)
    assert g["premise"] is False
    assert "MISSING" in g["premise_banner"]


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    live = tmp_path / "live"
    (live / ".claude").mkdir(parents=True)
    (live / "CLAUDE.md").write_text("# CLAUDE.md\n\nHand-written notes stay.\n", encoding="utf-8")
    (live / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")
    (live / ".claude" / "settings.json").write_text(
        json.dumps({"env": {"A": "1"}, "hooks": {"Stop": []}}), encoding="utf-8"
    )
    replay.create_candidate("baseline")
    return live


def test_ten_lessons_compile_into_three_or_more_primitives_as_a_candidate(state):
    res = precompile.build(LESSONS, live_root=state)
    assert res["built"] is True
    assert len(res["lessons"]) == 10, "every routable lesson that passes the gates; the flaky one stays interpretive"
    kinds = set(res["kinds"].values())
    assert {"guard", "skill", "subagent", "instruction", "tool"} <= kinds
    ov = Path(replay.candidate(res["candidate"])["overlay"])
    skill = (ov / ".agents/skills/ship-release/SKILL.md").read_text()
    assert skill.startswith("---\nname: ship-release\ndescription: Use when cutting a release.\n---\n"), (
        "frontmatter first"
    )
    assert (ov / ".claude/agents/review-pass.md").exists()
    assert (ov / ".cursor/rules/precompiled-facts.mdc").exists()
    assert (ov / ".aurora/precompiled/runner_prompt.md").exists()
    claude = (ov / "CLAUDE.md").read_text()
    assert "Hand-written notes stay." in claude
    assert "learn:experiment:uv_only" in claude
    settings = json.loads((ov / ".claude/settings.json").read_text())
    assert settings["env"] == {"A": "1"}, "the hand-written settings survive"
    assert any("precompiled_guard.py" in json.dumps(e) for e in settings["hooks"]["PreToolUse"])
    contract = json.loads((ov.parent / "contract.json").read_text())
    assert contract["lessons"] == res["lessons"]
    assert contract["mode"] == "precompiled"
    assert (state / "CLAUDE.md").read_text() == "# CLAUDE.md\n\nHand-written notes stay.\n", (
        "the live tree is untouched"
    )


def test_generated_files_rebuild_exactly_and_hand_edits_are_caught(state):
    a = precompile.build(LESSONS, live_root=state, name="pc-a")
    b = precompile.build(list(reversed(LESSONS)), live_root=state, name="pc-b")
    oa, ob = (Path(replay.candidate(n)["overlay"]) for n in (a["candidate"], b["candidate"]))
    files_a = {str(p.relative_to(oa)): p.read_bytes() for p in oa.rglob("*") if p.is_file()}
    files_b = {str(p.relative_to(ob)): p.read_bytes() for p in ob.rglob("*") if p.is_file()}
    assert files_a == files_b, "same lessons, any order -> the same bytes"
    assert precompile.check_drift(oa) == []
    claude = oa / "CLAUDE.md"
    claude.write_text(claude.read_text().replace("Use uv for every", "Use pip for every"), encoding="utf-8")
    skill = oa / ".agents/skills/ship-release/SKILL.md"
    skill.write_text(skill.read_text() + "extra\n", encoding="utf-8")
    drift = precompile.check_drift(oa)
    assert any("CLAUDE.md: the generated block was edited by hand" in d for d in drift)
    assert any("SKILL.md: the generated file was edited by hand" in d for d in drift)
    (oa / "CLAUDE.md").write_text(
        precompile.put_block("# hand edit OUTSIDE the block\n", [precompile._instruction_line(LESSONS[7])]),
        encoding="utf-8",
    )
    assert not any("CLAUDE.md" in d for d in precompile.check_drift(oa)), "text outside the markers is free"


def test_the_generated_guard_blocks_what_its_lesson_forbids(state, tmp_path):
    res = precompile.build(LESSONS, live_root=state)
    ov = Path(replay.candidate(res["candidate"])["overlay"])

    def call(cmd: str) -> dict:
        r = subprocess.run(
            [sys.executable, str(ov / precompile.GUARD)],
            input=json.dumps({"tool_input": {"command": cmd}}),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return json.loads(r.stdout) if r.stdout.strip() else {}

    deny = call("git push --force origin master")["hookSpecificOutput"]
    assert deny["permissionDecision"] == "deny"
    assert "learn:experiment:no_force_push" in deny["permissionDecisionReason"]
    assert "additionalContext" in call("pytest -q tests")["hookSpecificOutput"], "a missing required flag warns"
    assert call("REDIS_DB=15 pytest -q") == {}
    assert call("ls -la") == {}


def test_scope_decides_the_harnesses(state):
    codex_only = L(
        "codex_flag", "Never run `codex --dangerously-bypass`; it skips the sandbox.", scope="harness:codex-cli"
    )
    assert precompile.harnesses_for(codex_only) == ["codex-cli"]
    res = precompile.build([codex_only], live_root=state)
    assert res["harnesses"] == ["codex-cli"]
    ov = Path(replay.candidate(res["candidate"])["overlay"])
    assert (ov / ".codex/hooks.json").exists()
    assert not (ov / ".claude/settings.json").exists()


def test_apply_stamps_where_each_lesson_now_lives(state, tmp_path, monkeypatch):
    store = FileStore(str(tmp_path / "mem.json"))
    for x in LESSONS:
        store.hset(f"learn:experiment:{x['experiment_name']}", mapping={k: str(v) for k, v in x.items()})
    res = precompile.build(LESSONS, live_root=state)
    n = precompile.stamp_compiled(Path(replay.candidate(res["candidate"])["overlay"]), res["candidate"], store=store)
    assert n == 10
    where = json.loads(store.hgetall("learn:experiment:ship_release")["compiled_into"])
    assert where["candidate"] == res["candidate"]
    assert ".agents/skills/ship-release/SKILL.md" in where["harnesses"]["claude-code"]
    assert "compiled_into" not in store.hgetall("learn:experiment:narrow_flake")
    assert review.HIGH_RISK, "a compiled guard touches settings, so review needs two reviewers"


def test_unused_pieces_are_demotion_candidates(state):
    res = precompile.build(LESSONS, live_root=state)
    ov = Path(replay.candidate(res["candidate"])["overlay"])
    unused = precompile.demote_unused(ov, {".agents/skills/ship-release/SKILL.md": 4})
    assert ".agents/skills/ship-release/SKILL.md" not in unused
    assert ".agents/skills/lock-then-edit/SKILL.md" in unused
