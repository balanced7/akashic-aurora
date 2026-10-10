"""Lesson scope (meta-harness task 02): a lesson applies where its scope says, and nowhere else.

Acceptance pinned here:
  * a lesson recorded in Codex with model X is not pushed to a Claude Code session with model Y,
    unless it is scoped wider;
  * widening is proposed only with evidence from more than one harness or model;
  * a lesson with no scope (every lesson written before this) behaves exactly as before.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from typing import Any

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.foundation.store import FileStore  # noqa: E402  # sys.path bootstrap
from core.learning import scope  # noqa: E402  # sys.path bootstrap
from core.learning.learning_store import LearningStore  # noqa: E402  # sys.path bootstrap

CODEX_X = {"harness": "codex-cli", "model": "gpt-5.3-codex"}
CLAUDE_Y = {"harness": "claude-code", "model": "claude-opus-5-5"}


def _ls() -> LearningStore:
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(prefix="scope_"), "l.json")))


def _lesson(ls: LearningStore, name: str, text: str, scope_str: str = "") -> None:
    sig = {
        "experiment_name": name,
        "what_tried": text,
        "actual_outcome": "",
        "success": "yes",
        "recommendation": text,
    }
    if scope_str:
        sig["scope"] = scope_str
    assert ls.persist_learning_derived_from_experiment(sig) is True


# --------------------------------------------------------------------------- the rule
def test_terms_parse_and_a_typo_is_refused():
    assert scope.parse("harness:codex-cli, model:gpt") == ["harness:codex-cli", "model:gpt"]
    assert scope.parse("universal harness:x") == ["universal"]
    with pytest.raises(ValueError, match="bad scope term"):
        scope.parse("harnes:codex")


def test_no_scope_means_universal():
    assert scope.of({}) == ["universal"]
    assert scope.lesson_applies({}, CLAUDE_Y)


def test_model_family_and_id_match_differently():
    assert scope.model_family("claude-opus-5-5") == "claude-opus"
    assert scope.applies(["model:claude-opus"], {"model": "claude-opus-4-1"})
    assert not scope.applies(["model:claude-opus-5-5"], {"model": "claude-opus-4-1"})
    assert scope.applies(["model:claude-opus-5-5"], {"model": "claude-opus-5-5"})


def test_same_kind_is_or_and_different_kinds_are_and():
    terms = ["harness:codex-cli", "harness:cursor", "model:gpt"]
    assert scope.applies(terms, {"harness": "cursor", "model": "gpt-5"})
    assert not scope.applies(terms, {"harness": "claude-code", "model": "gpt-5"})
    assert not scope.applies(terms, {"harness": "cursor", "model": "claude-opus-5-5"})


def test_an_unknown_context_never_excludes():
    assert scope.applies(["harness:codex-cli", "model:gpt"], {})
    assert scope.applies(["model:gpt"], {"harness": "claude-code"})


def test_the_default_is_harness_and_model_family():
    prov = {"harness": "codex-cli", "model": "gpt-5.3-codex", "effort": "high"}
    assert scope.propose(prov) == ["harness:codex-cli", "model:gpt"]
    assert scope.propose({"harness": "shell", "model": "unknown"}) == ["universal"]


# --------------------------------------------------------------------------- acceptance 1
def test_a_codex_model_x_lesson_is_not_pushed_to_claude_model_y():
    from core.recall.at_action import recall_at

    ls = _ls()
    _lesson(ls, "codex_only_sandbox_flag", "pytest tempdir sandbox flag codex", "harness:codex-cli model:gpt")
    _lesson(ls, "universal_sandbox_flag", "pytest tempdir sandbox flag universal")
    common: dict[str, Any] = {
        "command": "pytest tempdir sandbox flag",
        "learning_store": ls,
        "limit": 5,
        "min_relevance": 0.0,
    }
    claude = [i["source"] for i in recall_at(applies_in=CLAUDE_Y, **common).get("lessons", [])]
    codex = [i["source"] for i in recall_at(applies_in=CODEX_X, **common).get("lessons", [])]
    assert "learn:experiment:codex_only_sandbox_flag" not in claude
    assert "learn:experiment:universal_sandbox_flag" in claude
    assert "learn:experiment:codex_only_sandbox_flag" in codex


def test_scoped_wider_it_is_pushed():
    from core.recall.at_action import recall_at

    ls = _ls()
    _lesson(ls, "codex_and_claude", "pytest tempdir sandbox flag both", "harness:codex-cli harness:claude-code")
    got = recall_at(
        command="pytest tempdir sandbox flag", learning_store=ls, limit=5, min_relevance=0.0, applies_in=CLAUDE_Y
    )
    assert "learn:experiment:codex_and_claude" in [i["source"] for i in got.get("lessons", [])]


def test_boot_drops_out_of_scope_lessons_from_its_budget():
    lessons = [
        {"experiment_name": "a", "scope": "harness:codex-cli"},
        {"experiment_name": "b"},
        {"experiment_name": "c", "scope": "model:claude-opus"},
    ]
    kept = [x["experiment_name"] for x in scope.filter_applicable(lessons, CLAUDE_Y)]
    assert kept == ["b", "c"]


def test_the_filter_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("AKASHIC_SCOPE_FILTER", "0")
    assert len(scope.filter_applicable([{"scope": "harness:codex-cli"}], CLAUDE_Y)) == 1


# --------------------------------------------------------------------------- acceptance 2
def _flip(source: str, sid: str) -> dict:
    return {"kind": "flip", "detail": {"sources": [source], "prov": f"prov:session:{sid}"}}


def test_widening_needs_evidence_from_two_harnesses():
    provs = {"s1": {"harness": "codex-cli", "model": "gpt-5"}, "s2": {"harness": "claude-code", "model": "gpt-5"}}
    lesson = {"experiment_name": "L", "scope": "harness:codex-cli model:gpt"}
    one = scope.evidence([_flip("learn:experiment:L", "s1")] * 3, [], provs.get)
    assert scope.widening_proposals([lesson], one) == [], "three credits in ONE harness is not breadth"
    two = scope.evidence([_flip("learn:experiment:L", "s1"), _flip("learn:experiment:L", "s2")], [], provs.get)
    props = scope.widening_proposals([lesson], two)
    assert len(props) == 1
    assert props[0]["proposed"] == "model:gpt"
    assert props[0]["evidence"] == {"harness": ["claude-code", "codex-cli"]}


def test_repeats_count_as_evidence_and_unprovenanced_events_do_not():
    provs = {"s1": {"harness": "codex-cli"}, "s2": {"harness": "cursor"}}
    lesson = {"experiment_name": "R", "scope": "harness:codex-cli"}
    ev = scope.evidence(
        [{"kind": "flip", "detail": {"sources": ["learn:experiment:R"]}}],  # no prov: pre-task-01
        [{"of": "R", "prov": "prov:session:s1"}, {"of": "R", "prov": "prov:session:s2"}],
        provs.get,
    )
    assert scope.widening_proposals([lesson], ev)[0]["proposed"] == "universal"


def test_universal_lessons_are_never_proposed():
    provs = {"a": {"harness": "x"}, "b": {"harness": "y"}}
    ev = scope.evidence([_flip("learn:experiment:U", "a"), _flip("learn:experiment:U", "b")], [], provs.get)
    assert scope.widening_proposals([{"experiment_name": "U"}], ev) == []


# --------------------------------------------------------------------------- hierarchy
def test_the_tree_groups_by_level_broadest_first():
    t = scope.tree(
        [
            {"experiment_name": "u"},
            {"experiment_name": "h", "scope": "harness:cursor"},
            {"experiment_name": "m", "scope": "harness:cursor model:claude-opus-5-5"},
            {"experiment_name": "f", "scope": "model:claude-opus"},
        ]
    )
    assert list(t) == ["universal", "harness", "model:family", "model:id"]
    assert t["model:id"] == {"harness:cursor model:claude-opus-5-5": ["m"]}


# --------------------------------------------------------------------------- the CLI door
def _cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "agent_cli.py", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180
    )


def _env(**extra: str) -> dict[str, str]:
    base = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            ("CLAUDE", "CODEX_", "CURSOR_", "AKASHIC_SESSION", "AKASHIC_HARNESS", "AKASHIC_MODEL", "AI_AGENT")
        )
    }
    assert base.get("_AISETUP_TEST_ISOLATED"), "a CLI child without isolation would write the live store"
    return {**base, **extra}


def test_learn_proposes_a_scope_and_set_and_show_round_trip():
    env = _env(
        AKASHIC_SESSION_ID=f"s-{uuid.uuid4().hex[:8]}", AKASHIC_HARNESS="codex-cli", AKASHIC_MODEL="gpt-5.3-codex"
    )
    name = f"scope_cli_{uuid.uuid4().hex[:6]}"
    r = _cli("learn", "scopetest", "--experiment", name, "--tried", "t", "--result", "r", env=env)
    assert r.returncode == 0, r.stderr[-400:]
    assert "[scope] harness:codex-cli model:gpt" in r.stdout
    shown = json.loads(_cli("scope", "show", "--experiment", name, "--json", env=env).stdout)
    assert shown["scope"] == "harness:codex-cli model:gpt"
    assert _cli("scope", "set", "--experiment", name, "--scope", "universal", env=env).returncode == 0
    shown = json.loads(_cli("scope", "show", "--experiment", name, "--json", env=env).stdout)
    assert shown["scope"] == "universal"
    full = json.loads(_cli("recall", "--full", f"learn:experiment:{name}", "--json", env=env).stdout)
    assert full["what_tried"] == "t", "set must touch only the scope field"


def test_learn_refuses_a_bad_scope():
    env = _env()
    r = _cli("learn", "scopetest", "--experiment", "x_bad_scope", "--tried", "t", "--scope", "model", env=env)
    assert r.returncode == 2
    assert "bad scope term" in r.stdout


def test_plain_recall_still_lists_an_out_of_scope_lesson_with_a_tag():
    name = f"scope_tag_{uuid.uuid4().hex[:6]}"
    env = _env(AKASHIC_SESSION_ID=f"s-{uuid.uuid4().hex[:8]}", AKASHIC_HARNESS="codex-cli", AKASHIC_MODEL="gpt-5")
    assert _cli("learn", "scopetest", "--experiment", name, "--tried", "zqxj tagged probe", env=env).returncode == 0
    other = _env(
        AKASHIC_SESSION_ID=f"s-{uuid.uuid4().hex[:8]}", AKASHIC_HARNESS="claude-code", AKASHIC_MODEL="claude-opus-5-5"
    )
    out = _cli("recall", name, env=other).stdout
    assert name in out
    assert "[scope: harness:codex-cli model:gpt -- not this agent]" in out
