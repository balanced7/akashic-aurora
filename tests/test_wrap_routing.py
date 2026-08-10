"""T268 RED -- wrap does not ask for tomorrow's routing, so the night shift cannot pre-chew.

MEASURED PRECONDITION, and the way it was found matters. Running the first manual sleep shift
(2026-08-10) showed its highest-value job could not run at all: pre-chewing a resident's
catch-up pack needs to know WHICH tasks that resident will face, and tomorrow was not routed
-- 24 NEXT items and 61 proposals with no assignment. Reading the literature had produced the
OPPOSITE conclusion, that our control over scheduling made the precompute caveat moot. It does
not: routing is a PRECONDITION of precompute, and the scheduler is us.

wrap --focus already records free-text INTENT. What no organ records is TARGETS -- which
ledger items, taken by which resident -- which is precisely what a pre-chew consumes.

THE PIN THAT MATTERS MOST IS P5, the nudge. A rule that lives only in a document requires
someone to remember it, which is the failure this whole slice exists to fix; a wrap that
silently accepts no routing would rebuild that failure inside the fix.

AND THE SUGGESTION MUST STAY A SUGGESTION (P3/P4). Matching a target to a resident by its own
archive is evidence, not authority -- routing is Daniil's act. A suggestion rendered as a
decision is the self-declared-identity class one plane over, and an unreceipted suggestion is
a vibe, so each one names the lessons that produced it.

Run: py -m pytest tests/test_wrap_routing.py -q
"""
import os
import subprocess
import sys

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402


def run(*args, timeout=180):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


@pytest.fixture(scope="module")
def a_real_task():
    """A routable target, proposed through the real door so the id is one the ledger issued."""
    rc, out = run("task", "propose",
                  "T268 pin target: a routable ledger item about bus lane cursors and wake",
                  "--by", "claude")
    assert rc == 0, out
    import re
    m = re.search(r"proposed (T\d+)", out)
    assert m, f"could not read the minted id: {out[:200]}"
    return m.group(1)


# ---------------------------------------------------------------- P1/P2: routing is recorded

def test_p1_route_records_targets_that_survive_to_the_next_boot(a_real_task):
    rc, out = run("wrap", "--route", a_real_task, "--commit")
    assert rc == 0, f"wrap --route must succeed: {out[-500:]}"
    rc, boot = run("boot", "claude", "--task", "what is routed")
    assert a_real_task in boot, \
        "a routed target must reach the next boot -- an organ the night shift cannot read " \
        "is an organ that does not exist"


def test_p2_an_unroutable_id_refuses_loudly(a_real_task):
    """Recording a target nobody can work is worse than recording nothing: the shift would
    pre-chew for a task that does not exist and report success."""
    rc, out = run("wrap", "--route", "T99999", "--commit")
    assert "T99999" in out, "the refusal must NAME the id it could not route"
    low = out.lower()
    assert any(w in low for w in ("no such", "not found", "unknown", "refus")), \
        f"and say why, got: {out[-300:]}"


# ---------------------------------------------------------------- P3/P4: suggestions, receipted

def test_p3_each_routed_target_suggests_a_resident(a_real_task):
    """Evidence-based: matched against each resident's OWN archive (T260 scope)."""
    rc, out = run("wrap", "--route", a_real_task)
    assert rc == 0
    low = out.lower()
    assert any(cs in out for cs in ("Vandor", "Navi", "Heimdall")) or "no resident" in low, \
        f"a routed target must name a suggested resident, or say plainly that none matched: {out[-400:]}"


def test_p4_a_suggestion_carries_its_receipts_and_is_labelled_a_suggestion(a_real_task):
    """An unreceipted suggestion is a vibe, and a suggestion rendered as a decision is the
    class T255 is open about."""
    rc, out = run("wrap", "--route", a_real_task)
    low = out.lower()
    assert "suggest" in low, "the render must label it a SUGGESTION, never an assignment"
    assert ("because" in low or "matched" in low or "learn:" in low or "lesson" in low), \
        f"and must show what evidence produced it: {out[-400:]}"


# ---------------------------------------------------------------- P5: the nudge

def test_p5_a_wrap_with_no_routing_nudges_and_still_succeeds(a_real_task):
    """THE LOAD-BEARING PIN. The nudge is the whole point -- and it must never block a wrap,
    because a hygiene prompt that can fail a wrap is a prompt people learn to route around."""
    rc, out = run("wrap")
    assert rc == 0, "a wrap without routing must still succeed"
    low = out.lower()
    assert "route" in low, "an unrouted wrap must mention routing"
    assert "pre-chew" in low or "prechew" in low or "night" in low, \
        "and must name the CONSEQUENCE, not just the omission -- an instruction without a " \
        "reason is the checklist-fatigue shape"


def test_p6_focus_behaviour_is_unchanged(a_real_task):
    """--focus is a different organ (free-text intent). This slice must not disturb it."""
    rc, out = run("wrap", "--focus", "a test focus line for T268", "--commit")
    assert rc == 0
    assert "next-focus" in out or "directive" in out.lower(), \
        f"--focus must still set the directive note: {out[-300:]}"
