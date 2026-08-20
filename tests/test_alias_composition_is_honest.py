"""RED: the composition plane runs steps blind, and that is why nobody fills it.

Daniil, 2026-08-20: "see what verbs need to be added or combined / refined. Perhaps verb families
or arguments so that it becomes easier to use and see them." The registry ALREADY has a `family`
field and only three entries. I assumed neglect. Measured instead, and the plane is unsound --
which is the actual reason it is empty. Nobody populates a composition layer whose macros
silently do nothing.

THREE DEFECTS, each verified by invocation (ask the door, do not read the door):

1. `run` SWALLOWS STEP OUTPUT. `flightdeck` alone prints a fleet table. Through
   `run claude cycle-open` it printed only "-> flightdeck". So a step that FAILED and a step that
   worked are indistinguishable from the caller -- a receipt about invocation, not about outcome.
   The exact family this house spent 2026-08-19 removing: the spawn syscall returning while the
   child died, send() returning while the word never arrived.

2. `$SELF$` IS NOT SUBSTITUTED. `run --dry` renders `defer $SELF$ --list` literally. The shipped
   recovery-kit uses `$SELF$` in its own steps, so either kit substitutes at install time or the
   kit's ceremonies carry the same hole.

3. THE FALSE NEGATIVE THAT MAKES IT DANGEROUS RATHER THAN MERELY BROKEN: `defer '$SELF$' --list`
   EXITS 0 and prints "queue empty -- nothing awaits a capable seat". So does
   `defer totally-not-an-agent-xyz --list`. An unsubstituted token therefore queries a
   nonexistent seat's queue and reports EMPTY -- cheerfully, forever, while the real queue fills.
   Locally true (that queue is empty), false about the world (mine is not).

Composed, those three mean a rhythm built on aliases would report a clean cycle while doing
nothing at all. That is worse than no rhythm, because it produces receipts.

Run:  py -m pytest tests/test_alias_composition_is_honest.py -v
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CLI = [sys.executable, str(REPO / "agent_cli.py")]


def _run(*args, timeout=180):
    return subprocess.run(CLI + list(args), cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


# --------------------------------------------------------------- 1. output surfacing
def test_run_surfaces_what_its_steps_actually_printed():
    """A macro that hides its steps' output is a receipt about invocation. flightdeck prints a
    fleet table; through `run` that table must still reach the caller."""
    direct = _run("flightdeck")
    assert "FLIGHTDECK" in direct.stdout, "precondition: flightdeck prints a banner"
    viarun = _run("run", "claude", "cycle-open")
    assert "FLIGHTDECK" in viarun.stdout, (
        "run swallowed the step's output -- a failing step and a working step look identical")


def test_run_reports_a_failing_step_as_a_failure():
    """The floor: if a step exits nonzero, the macro must not report done."""
    _run("alias", "claude", "mint", "probe-doomed-step",
         "--step", "definitely-not-a-verb", "--family", "PROBE",
         "--why", "RED pin probe: a nonzero step must not read as done")
    try:
        out = _run("run", "claude", "probe-doomed-step")
        assert out.returncode != 0 or "fail" in (out.stdout + out.stderr).lower(), (
            "a macro whose step could not even resolve still reported success")
    finally:
        _run("alias", "claude", "retire", "probe-doomed-step", "--reason", "RED pin cleanup")


# --------------------------------------------------------------- 2. token substitution
def test_self_token_resolves_to_the_running_seat():
    """The shipped recovery-kit writes $SELF$ into its steps. If run does not substitute it, every
    kit ceremony that uses it addresses a seat that does not exist."""
    out = _run("run", "claude", "cycle-open", "--dry")
    assert "$SELF$" not in out.stdout, "$SELF$ reached the step unsubstituted"
    assert "claude" in out.stdout, "the token should have resolved to the running seat"


# --------------------------------------------------------------- 3. the false negative
def test_defer_refuses_an_unknown_seat_instead_of_reporting_empty():
    """THE DANGEROUS ONE. `defer <nonexistent> --list` prints 'queue empty' and exits 0, so an
    unsubstituted token silently reads a phantom queue and reports nothing waiting. A door that
    answers a malformed address with a cheerful negative manufactures false confidence -- the
    eye_get_says_no_event_when_it_means_bad_address lesson, on a different door."""
    roster = _run("doctor", "--json")
    if "discord" not in roster.stdout and "claude" not in roster.stdout:
        pytest.skip("no live fleet roster in this environment -- the roster HINT is untestable "
                    "here; the roster-free invariant is covered by the sibling pin below")
    out = _run("defer", "totally-not-an-agent-xyz", "--list")
    combined = (out.stdout + out.stderr).lower()
    assert out.returncode != 0 or "unknown" in combined or "no such" in combined, (
        "an unknown seat's queue reported EMPTY rather than UNKNOWN -- absence and "
        "nonexistence must not render identically")


def test_defer_empty_and_defer_unknown_do_not_render_identically():
    """Even if both are permitted, they must be distinguishable, or a typo reads as good news."""
    real = _run("defer", "claude", "--list")
    fake = _run("defer", "totally-not-an-agent-xyz", "--list")
    assert real.stdout.strip() != fake.stdout.strip(), (
        "a real empty queue and a phantom seat produce byte-identical output")
