"""T336 RED: the Eye at the peer door -- corpus access for seats that never had it.

DANIIL, 2026-08-17: "We need to give deepseek and kimi eye access, I am most curious where they
will go, since they didn't get to use it this time around."

THE DEFECT, and I caused it an hour before filing this. I sent Heimdall and Navi a curiosity brief
whose mechanics section listed `py agent_cli.py eye freq ...`, `eye find`, `eye zoom`, `eye get`.
Their runners have exec=off. Every one of those commands is unrunnable at their door, so both seats
ran a corpus curiosity pass through read_file and search_files -- grep over a corpus that has a
grammar, a frequency verdict and an address resolver sitting one layer away, unreachable.

core/comm/toolbox.py TOOLS exposes read_file, list_directory, find_files, search_files, git_log,
git_diff, git_show, git_status, knowledge_recall, recall_at, knowledge_full, memory_note,
memory_recall, knowledge_boot, knowledge_map, delta, knowledge_learn, knowledge_note,
bifrost_send, bifrost_inbox, bifrost_fetch -- and not one Eye verb.

WHY eye_freq IS THE LOAD-BEARING ONE. It is the only door in this house that returns a verdict on
the OPERATOR'S OWN AXIS -- unheard / mentioned-once / recurring / standing-directive. Tonight it
showed that "tag|tagging|metadata|emit|emission" is a STANDING-DIRECTIVE across 211 sessions while
the operator was apologising for not having articulated it. No amount of grep produces that; it is
a measurement, not a search.

DISPATCH IS getattr(self, name) (toolbox.py:1247), so a method per tool IS the wiring. The TOOLS
entries carry each name as a STRING LITERAL, which is what keeps check_wiring's ast.Constant match
able to see them -- deepseek-red's A5 dispatch-bypass lesson warns that a registry pattern goes
invisible to that checker, and it does not bite here for exactly that reason. P5 pins it so a later
refactor to computed names cannot silently blind the guard.

Run: py -m pytest tests/test_t336_eye_at_the_peer_door.py -q
"""
from __future__ import annotations

import ast
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import toolbox as TB  # noqa: E402

EYE_TOOLS = ("eye_find", "eye_freq", "eye_get", "eye_zoom")


def _declared_names():
    return {t.get("function", t).get("name") for t in TB.TOOLS}


# ------------------------------------------------------------------ the door exists
@pytest.mark.parametrize("name", EYE_TOOLS)
def test_p1_each_eye_verb_is_declared_at_the_door(name):
    """A tool a peer cannot see is a tool a peer does not have. This is the whole slice."""
    assert name in _declared_names(), (
        f"{name} is not in TOOLS -- the seat cannot call what the door never offered")


@pytest.mark.parametrize("name", EYE_TOOLS)
def test_p2_each_eye_verb_dispatches(name):
    """Dispatch is getattr(self, name) at toolbox.py:1247, so a declared name with no method is a
    tool that answers 'ERROR: unknown tool' -- worse than absent, because it advertises."""
    assert callable(getattr(TB.ToolBox, name, None)), (
        f"{name} is declared in TOOLS but has no method -- getattr dispatch will refuse it")


# ------------------------------------------------------------------ the contract of the answers
def test_p3_freq_is_described_as_a_verdict_not_a_search():
    """The reason this verb matters is that it MEASURES rather than retrieves. A description that
    reads like search will be used like search, and the standing-directive verdict -- the only
    thing here that no other door can produce -- will never be asked for."""
    d = {t.get("function", t)["name"]: t.get("function", t)["description"] for t in TB.TOOLS}
    text = d["eye_freq"].lower()
    assert "verdict" in text, "eye_freq must advertise that it returns a verdict"
    for word in ("standing", "operator"):
        assert word in text, f"eye_freq's description must name '{word}' -- it is the axis"


def test_p4_get_advertises_the_address_shape():
    """An address resolver whose description omits the address shape sends every caller through a
    guess. The corpus addresses as session:line and nothing else."""
    d = {t.get("function", t)["name"]: t.get("function", t)["description"] for t in TB.TOOLS}
    assert "session" in d["eye_get"].lower() and "line" in d["eye_get"].lower()


# ------------------------------------------------------------------ the guard that must keep seeing
def test_p5_the_names_stay_string_literals_so_check_wiring_can_see_them():
    """deepseek-red's A5 lesson: check_wiring matches ast.Constant string values, so any dispatch
    that COMPUTES a tool name ('eye_' + verb) goes invisible and the reachability guard silently
    stops covering this surface. Pinned at the source rather than trusted."""
    src = open(os.path.join(ROOT, "core", "comm", "toolbox.py"), encoding="utf-8").read()
    literals = {n.value for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    for name in EYE_TOOLS:
        assert name in literals, (
            f"{name} is not a bare string literal in toolbox.py -- if the name is computed, "
            f"check_wiring cannot see the method and this door leaves the guard's view")


# ------------------------------------------------------------------ read-only, by construction
def test_p6_no_eye_verb_can_write():
    """The corpus is a record of what was said. A door onto it that could write would let a seat
    edit the evidence it is being asked to reason from."""
    import inspect
    for name in EYE_TOOLS:
        src = inspect.getsource(getattr(TB.ToolBox, name))
        for forbidden in ("ingest", "--persist", "open(", "write"):
            assert forbidden not in src, (
                f"{name} references {forbidden!r} -- Eye doors at the peer surface are read-only")
