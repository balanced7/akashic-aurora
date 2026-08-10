"""T259 RED -- the identity/role split: a resident's JOB is an event, never a field.

DANIIL'S SENTENCE, 2026-08-09, which this file implements verbatim:

    "we could see that Deepseek Onyx Blue 3 'Rook' was operating as Jester on the Red team
     side of the exercise on this timestamp. This way agents can change roles and still
     generate useful information into the general All Jesters on Red team of exercise."

Three claims live in that sentence, one pin group each:

  IDENTITY IS PERMANENT, THE JOB IS SITUATIONAL. Rook stays Rook; Jester is what Rook was
  DOING, on a side, in an exercise, at a timestamp. So an assignment is an append-only EVENT
  (agent, role, side, exercise, at, by) and the current role is a projection, never a field
  someone edits. (P4 holds append-only; P5 renders the split.)

  "ALL JESTERS ON RED" IS A QUERY. Because assignments are events, the cross-resident
  projection costs nothing to build and cannot drift from the log it projects. (P2.)

  A DECLARED TITLE IS NOT A VERIFIED ONE. Daniil's phrase was "declarable job title", so
  self-declaration is LEGAL -- but T255 is open on this exact defect one plane down
  (claim_class, player-declared, never verified), so a self-assignment must RENDER as
  SELF-DECLARED and be filterable, or the projection silently rebuilds T255. (P3.)

WHY THE SPLIT EARNS ITS KEEP (atom sec.4): two archives accumulate from one work stream. A
role producing the same finding class regardless of who wears it is a property of the SEAT;
a resident producing across roles is a property of the AGENT. Today those render identically.

Run: py -m pytest tests/test_resident_roles.py -q
"""
import os
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _seed_lesson(agent, experiment):
    rc, out, err = run("learn", agent, "--experiment", experiment,
                       "--tried", "role-pin seed", "--result", "role-pin seed")
    assert rc == 0, f"seeding {experiment} failed: {err or out}"
    return experiment


@pytest.fixture(scope="module")
def residents():
    """Two RATIFIED residents -- roles attach to the identity sheet, so the sheet must exist."""
    from core.fleet import residents as R
    out = {}
    for agent, callsign in (("kimi", "Navi"), ("deepseek", "Heimdall")):
        exp = _seed_lesson(agent, f"pin_role_receipt_{agent}")
        R.nominate(nominee=agent, callsign=callsign, receipts=[exp], by="daniil_pin")
        R.ratify(nominee=agent, callsign=callsign, by="daniil_pin")
        out[agent] = callsign
    return out


# ------------------------------------------------------------------ P1: the refusals

def test_p1_assign_refuses_a_missing_role_and_a_missing_assigner(residents):
    from core.fleet import residents as R
    with pytest.raises(ValueError):
        R.assign(agent="kimi", role="", by="claude")
    with pytest.raises(ValueError):
        R.assign(agent="kimi", role="Jester", by="")


def test_p1b_assign_refuses_a_non_resident(residents):
    """Roles live on the identity sheet; a seat with no sheet has nowhere to wear one.

    The refusal must point at the ceremony, not just say no -- errors that teach (ACI law).
    """
    from core.fleet import residents as R
    with pytest.raises(ValueError) as e:
        R.assign(agent="unregistered_seat", role="Jester", by="claude")
    assert "resident" in str(e.value).lower(), "the refusal must say WHY: not a resident"
    assert "nominate" in str(e.value).lower(), "and point at the ceremony that fixes it"


# ------------------------------------------------------------------ P2: the projection

def test_p2_all_jesters_on_red_returns_exactly_the_planted_assignments(residents):
    """Daniil's query, literally: All Jesters on Red team of exercise."""
    from core.fleet import residents as R
    R.assign(agent="kimi", role="Jester", side="Red", exercise="E7", by="claude")
    R.assign(agent="deepseek", role="Jester", side="Red", exercise="E7", by="claude")
    R.assign(agent="deepseek", role="Bard", side="Blue", exercise="E7", by="claude")     # decoy
    R.assign(agent="kimi", role="Jester", side="Red", exercise="E8", by="claude")        # decoy

    hits = R.roles(role="Jester", side="Red", exercise="E7")
    who = sorted(h["agent_id"] for h in hits)
    assert who == ["deepseek", "kimi"], f"expected exactly the two E7 Red Jesters, got {who}"
    assert all(h.get("role") == "Jester" and h.get("side") == "Red" for h in hits)


def test_p2b_an_empty_projection_is_empty_not_everything(residents):
    """A filter nothing matches returns [], never the unfiltered log -- the fallback that is
    wider than the thing it replaces is the audited defect class."""
    from core.fleet import residents as R
    assert R.roles(role="NoSuchRole") == []


# ------------------------------------------------------------------ P3: declared vs assigned

def test_p3_a_self_assignment_renders_self_declared_and_is_filterable(residents):
    """'Declarable job title' -- legal, LABELLED, filterable. Otherwise T255 rebuilt."""
    from core.fleet import residents as R
    R.assign(agent="kimi", role="Scout", side="Blue", exercise="E9", by="kimi")
    R.assign(agent="deepseek", role="Scout", side="Blue", exercise="E9", by="claude")

    scouts = R.roles(role="Scout", exercise="E9")
    by_agent = {h["agent_id"]: h for h in scouts}
    assert by_agent["kimi"]["provenance"] == "self-declared"
    assert by_agent["deepseek"]["provenance"] == "assigned"

    verified_only = R.roles(role="Scout", exercise="E9", provenance="assigned")
    assert [h["agent_id"] for h in verified_only] == ["deepseek"], \
        "a query must be able to exclude self-declared titles, or the projection is T255"


# ------------------------------------------------------------------ P4: append-only

def test_p4_reassignment_appends_and_the_history_survives(residents):
    """Rook can change jobs; the record that Rook WAS Jester at that timestamp survives."""
    from core.fleet import residents as R
    R.assign(agent="kimi", role="Jester", side="Red", exercise="E10", by="claude")
    R.assign(agent="kimi", role="Oracle", side="Red", exercise="E10", by="claude")

    hist = R.role_history("kimi")
    e10 = [h for h in hist if h.get("exercise") == "E10"]
    assert [h["role"] for h in e10] == ["Jester", "Oracle"], \
        "both assignments must survive in order -- an update path would erase the timeline"
    assert R.current_role("kimi")["role"] == "Oracle", "current = the LATEST event, projected"


# ------------------------------------------------------------------ P5: the rendered split

def test_p5_show_renders_identity_and_current_role_as_separate_planes(residents):
    from core.fleet import residents as R
    R.assign(agent="deepseek", role="Jester", side="Red", exercise="E11", by="claude")
    rc, out, _ = run("resident", "show", "deepseek")
    assert rc == 0
    assert "Heimdall" in out, "the permanent identity must render"
    assert "Jester" in out, "the situational role must render beside it"
    assert "Red" in out, "with its side"


def test_p5b_boot_carries_the_current_job_beside_the_name(residents):
    """The full identity sheet at boot: who I am, what earned it, what I am doing now."""
    from core.fleet import residents as R
    R.assign(agent="kimi", role="Premise-Check", side="Red", exercise="E12", by="claude")
    rc, out, _ = run("boot", "kimi", "--task", "what is my job")
    assert rc == 0
    assert "Navi" in out
    assert "Premise-Check" in out, "a resident boots knowing its CURRENT assignment too"


def test_p5c_a_resident_with_no_role_renders_clean(residents):
    """No assignment is the ordinary state, not a warning. (Fresh resident, zero roles.)"""
    from core.fleet import residents as R
    exp = _seed_lesson("cursor", "pin_role_receipt_cursor")
    R.nominate(nominee="cursor", callsign="Compass", receipts=[exp], by="daniil_pin")
    R.ratify(nominee="cursor", callsign="Compass", by="daniil_pin")
    rc, out, _ = run("resident", "show", "cursor")
    assert rc == 0
    assert "Compass" in out
    assert "operating as" not in out.lower(), "no role -> no role line, never a nag"
