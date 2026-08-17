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
def test_p6_no_TOOLBOX_eye_verb_can_write_the_corpus():
    """The corpus is the record of what was said. A door onto it that could write would let a
    seat edit the evidence it is reasoning from.

    SCOPE TIGHTENED (Heimdall, independent verification 2026-08-17). The earlier name claimed
    "no Eye verb can write THE CORPUS", which is FALSE at the CLI: `agent_cli.py` exposes
    `eye ingest`, routed at cmd_eye and backed by core/eye/index.py:ingest -- a corpus-writing
    Eye door. What is true, and what this pin actually checks, is narrower: the TOOLBOX door
    T336 shipped is read-only, because each verb hard-codes its subcommand and can never reach
    `ingest`. He marked it CLOSE because every pin passes for the reason it claims and the
    shipped surface is genuinely read-only -- but the pin's NAME overreached its evidence, and
    a name that claims more than it tests is the defect this suite exists to catch. His exact
    residual risk, recorded: if a later refactor routes a ToolBox Eye verb through a
    subcommand computed from caller input, this pin would still pass while the door gained a
    write path.

    AMENDED (T338): the first version of this pin banned the tokens 'write' and 'open(' from
    each method's own source. That was the right INTENT expressed as the wrong TEST, twice
    over. (a) It is too broad: it forbade an audit write to a different file, which the
    disclosure design now REQUIRES. (b) It is too narrow: inspect.getsource(eye_freq) cannot
    see what eye_freq CALLS, so moving a write one frame down defeated it silently -- exactly
    the instrument-blindness class this suite exists to catch, committed by this suite. The
    pin now names the thing it actually protects: the CORPUS."""
    import inspect
    src = "".join(inspect.getsource(getattr(TB.ToolBox, n)) for n in EYE_TOOLS)
    src += inspect.getsource(TB.ToolBox._eye_disclose)   # follow the call, do not stop at it
    for forbidden in ("ingest", "--persist", "eye.db", "DB_PATH"):
        assert forbidden not in src, (
            f"an Eye door (or its helper) references {forbidden!r} -- these surfaces read the "
            f"corpus and must never write it")


def test_p7_every_corpus_read_discloses_itself():
    """T338, Daniil's ruling: disclosure instead of a permission gate, because a gate priced on
    every new seat forever protects against a rare event he personally controls, while
    disclosure costs nothing at invocation and answers the better question -- not 'may this
    seat read?' but 'what did it actually read?'

    The corpus holds his transcripts. A read of them must not be able to happen quietly, and
    that has to be structural: an agent that must REMEMBER to disclose will not."""
    import inspect
    for name in EYE_TOOLS:
        src = inspect.getsource(getattr(TB.ToolBox, name))
        assert "_eye_disclose" in src, (
            f"{name} can read the operator's transcripts without leaving a trace")


def test_p8_a_failed_disclosure_confesses_and_never_blocks_the_read():
    """Two properties in tension, and both matter. The read must not fail because the audit
    failed -- making the honest path the expensive one is the exact failure mode this design
    was chosen to avoid. But a silent audit failure would be worse than no audit at all,
    because it would look identical to a disclosed read."""
    import inspect
    src = inspect.getsource(TB.ToolBox._eye_disclose)
    assert "except Exception" in src, "the audit must never break the read"
    assert "DISCLOSURE FAILED" in src, (
        "a failed audit must say so in the returned text -- silence here is indistinguishable "
        "from a disclosed read, which is the T176 defect wearing an audit's coat")
