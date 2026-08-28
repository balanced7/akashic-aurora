"""RED pins -- make Sunshine (sol) reachable from Discord via `!spawn`.

PRE-REGISTRATION, committed before the implementation, per M3.
Every pin here must fail solely because `sunshine`/`sol` is not yet in the seat registry.

WHY: Sunshine is the only seat with no lever. `revive.py` cannot target him
(DAEMON_AGENTS is deepseek/kimi; --target is app/redis/daemon/gateway), and
`!spawn sunshine` currently resolves to None, which means the gateway treats the word as a
TASK STRING and launches a claude session whose job is to go investigate him -- the exact
2026-08-24 defect this module was written to kill, reproduced for a different name.

He has a runner script at scripts/bifrost_runner_sol.py, so the `runner` kind fits without
new launcher machinery. This is a registry entry, not a mechanism.

THE HOUSE RULE THAT GOVERNS THE LAST PIN: a recovery path without an executed drill and a
dated receipt is PRESUMED BROKEN. `drilled` must stay empty until a drill actually runs, and
launch_note must SAY SO -- an undrilled lever must not read like a drilled one.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fleet import seat_launchers as SL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Pin 1 -- both spellings resolve. He says "Sunshine"; the ledger says "sol".
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word", ["sunshine", "Sunshine", "SUNSHINE", "sol", "  sol  ", "`sol`"])
def test_p1_both_spellings_resolve_to_one_seat(word):
    rec = SL.resolve_seat(word)
    assert rec is not None, f"{word!r} must resolve -- unresolved means the gateway treats it as a task"
    assert rec["seat"] == "sol", rec
    assert rec["callsign"] == "Sunshine", rec


# ---------------------------------------------------------------------------
# Pin 2 -- a SENTENCE is still a task, never a launch. The strictness is the fix.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phrase", [
    "sunshine and check the ui",
    "ask sunshine about the contract",
    "sol, are you there",
])
def test_p2_a_sentence_is_a_task_not_a_launch(phrase):
    assert SL.resolve_seat(phrase) is None, (
        f"{phrase!r} must stay a task -- loosening resolution reintroduces the 2026-08-24 defect "
        "from the other direction")


# ---------------------------------------------------------------------------
# Pin 3 -- he launches with HIS OWN runner script, never the deepseek one.
# ---------------------------------------------------------------------------

def test_p3_launches_the_sol_runner_not_the_shared_deepseek_script():
    rec = SL.resolve_seat("sunshine")
    argv, env, cwd = SL.launch_argv(rec, root=ROOT)

    joined = " ".join(argv)
    assert "bifrost_runner_sol.py" in joined, argv
    assert "bifrost_runner_deepseek.py" not in joined, (
        "the daemon hardcodes the deepseek runner for --spawn-runner; handing sol that script is "
        "the daemon_spawn_runner_hardcodes_deepseek_script lesson repeating")
    assert "--agent" in argv and "sol" in argv, argv
    assert cwd == ROOT, cwd


# ---------------------------------------------------------------------------
# Pin 4 -- identity is STATED, never inherited. The module's own law.
# ---------------------------------------------------------------------------

def test_p4_env_states_its_own_identity():
    rec = SL.resolve_seat("sol")
    _, env, _ = SL.launch_argv(rec, root=ROOT)
    assert env.get("AKASHIC_AGENT_ID") == "sol", (
        f"every seat states its own identity; inheriting it is how a seat wakes up as someone "
        f"else: {env}")
    assert env.get("BIFROST_CONSUME_LANE") == "work", env


# ---------------------------------------------------------------------------
# Pin 5 -- the runner script must actually exist, and the lever must refuse if not.
# ---------------------------------------------------------------------------

def test_p5_refuses_loudly_when_the_script_is_absent():
    rec = SL.resolve_seat("sunshine")
    assert os.path.isfile(os.path.join(ROOT, "scripts", "bifrost_runner_sol.py")), (
        "precondition: sol has a runner script")

    with pytest.raises(RuntimeError, match="no runner script"):
        SL.launch_argv(rec, root=os.path.join(ROOT, "does-not-exist"))


# ---------------------------------------------------------------------------
# Pin 6 -- an UNDRILLED lever must not read like a drilled one.
# ---------------------------------------------------------------------------

def test_p6_launch_note_confesses_when_the_lever_is_not_drilled():
    rec = SL.resolve_seat("sunshine")
    note = SL.launch_note(rec)
    assert "Sunshine" in note and "sol" in note, note

    if rec.get("drilled"):
        assert rec["drilled"] in note, "a drilled lever must show its dated receipt"
        assert "NOT yet drilled" not in note, note
    else:
        assert "NOT yet drilled" in note, (
            f"a wired-but-unproven lever must say so; a recovery path without an executed drill "
            f"and a dated receipt is presumed broken: {note}")


# ---------------------------------------------------------------------------
# Pin 7 -- adding Sunshine must not disturb the seats already registered.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word,seat", [
    ("rill", "dsh_agent"), ("dsh_agent", "dsh_agent"),
    ("heimdall", "deepseek"), ("deepseek", "deepseek"),
    ("navi", "kimi"), ("kimi", "kimi"),
])
def test_p7_existing_seats_are_untouched(word, seat):
    rec = SL.resolve_seat(word)
    assert rec is not None and rec["seat"] == seat, (word, rec)
