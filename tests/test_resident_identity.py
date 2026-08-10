"""T258 RED -- a resident cannot explain its own name.

THE OBJECTION THAT PRODUCED THIS PIN, kimi 2026-08-09, reviewing the callsign scheme:

    "A callsign certifies a continuous self, but a resident is a sequence of boots over a fold
     that selects for narrative continuity and AGAINST contradiction-awareness. The name
     asserts an archive the current boot may not carry."

It named a one-command probe and I ran it BEFORE writing this file. Measured on the live tree,
2026-08-09: of the eight receipts behind the callsigns deepseek and kimi proposed for each
other, ZERO appear in their own seat's boot fold. deepseek 0/4, kimi 0/4.

So the archive holds the story and the boot does not carry it. Ask a resident why it is called
Snooze and it cannot answer -- it has to go look. That is the difference between a name that is
EARNED and a name that is DECORATION, and it is the cheapest gap in the design to close.

WHAT THESE PINS HOLD, and why each one is here rather than in a later slice:

  P1/P2  THE FOLD CARRIES THE IDENTITY. kimi's probe, promoted to a pin: boot a registered
         resident and its own callsign AND at least one of its receipts must appear. This is
         the acceptance test for the whole slice; the other three defend the registry that
         feeds it.
  P3     A NOMINATION IS NEVER A SELF-NOMINATION. Ceremony rule 1 enforced STRUCTURALLY rather
         than by etiquette. The repo already carries this defect class one level over: T255 is
         open because a player-declared field was never verified.
  P4     A RECEIPT MUST BELONG TO THE NOMINEE. deepseek's amendment to rule 2, and it closes
         the error recorded in the_M_tag_failed_first_contact...: a tag system that admits
         RECOLLECTION instead of demanding the RECEIPT is decoration. The named agent must be
         the author of the record cited.
  P5     A SUPERSEDED CALLSIGN IS NEVER DELETED. Append-only, per the substrate's own physics:
         the old name becomes a `formerly:` entry and still resolves.

Run: py -m pytest tests/test_resident_identity.py -q
"""
import os
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402


def run(*args, timeout=120):
    """Invoke the CLI as a subprocess -- the door a real seat enters through."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _seed_lesson(agent, experiment, tried="pin seed", result="pin seed"):
    """Author a lesson AS `agent`, so receipt-ownership has something real to check against."""
    rc, out, err = run("learn", agent, "--experiment", experiment,
                       "--tried", tried, "--result", result)
    assert rc == 0, f"seeding lesson {experiment} for {agent} failed: {err or out}"
    return experiment


@pytest.fixture(scope="module")
def seeded():
    """Two lessons with DIFFERENT authors -- the whole point of P4 is telling them apart."""
    return {
        "kimi": _seed_lesson("kimi", "pin_receipt_authored_by_kimi",
                             tried="held a lock it could not release",
                             result="every write re-armed the TTL"),
        "claude": _seed_lesson("claude", "pin_receipt_authored_by_claude",
                               tried="swept nine sibling files into a commit",
                               result="the hook never saw the blanket sweep"),
    }


# ---------------------------------------------------------------- P3 / P4: the registry rules

def test_p3_a_nomination_is_never_a_self_nomination(seeded):
    """Rule 1, structural. You do not name yourself -- and the door refuses, not the etiquette."""
    from core.fleet import residents as R
    with pytest.raises(ValueError) as e:
        R.nominate(nominee="kimi", callsign="Snooze",
                   receipts=[seeded["kimi"]], by="kimi")
    msg = str(e.value).lower()
    assert "kimi" in msg, "the refusal must name the offending party"
    assert "self" in msg or "yourself" in msg, \
        f"the refusal must say WHY (rule 1), got: {e.value}"


def test_p4_a_receipt_must_be_authored_by_the_nominee(seeded):
    """Rule 2 as deepseek amended it: the receipt comes from the NOMINEE's archive.

    A receipt claude wrote is claude REMEMBERING something about kimi. That is the [M]-tag
    error -- recollection wearing a receipt's clothes -- and it must be refused.
    """
    from core.fleet import residents as R
    with pytest.raises(ValueError) as e:
        R.nominate(nominee="kimi", callsign="Snooze",
                   receipts=[seeded["claude"]], by="claude")
    msg = str(e.value)
    assert seeded["claude"] in msg, "the refusal must NAME the offending receipt"
    assert "claude" in msg.lower(), "the refusal must name who actually authored it"


def test_p4b_a_receipt_authored_by_the_nominee_is_accepted(seeded):
    """The mirror of P4 -- the rule must not refuse everything."""
    from core.fleet import residents as R
    rec = R.nominate(nominee="kimi", callsign="Snooze",
                     receipts=[seeded["kimi"]], by="claude")
    assert rec, "a well-formed nomination must be recorded"
    assert seeded["kimi"] in (rec.get("receipts") or []), "the receipt must be carried on the record"


def test_p4c_an_unknown_receipt_is_refused_not_assumed(seeded):
    """A receipt that does not resolve is UNKNOWN, never 'probably fine'.

    Absence must not read as success -- the same invariant the guard-of-guards broke in T178.
    """
    from core.fleet import residents as R
    with pytest.raises(ValueError) as e:
        R.nominate(nominee="kimi", callsign="Snooze",
                   receipts=["no_such_lesson_exists_anywhere"], by="claude")
    assert "no_such_lesson_exists_anywhere" in str(e.value), \
        "the refusal must name the receipt it could not resolve"


# ---------------------------------------------------------------- P5: append-only supersession

def test_p5_a_superseded_callsign_becomes_formerly_and_still_resolves(seeded):
    """Append-only. A callsign is succeeded, never deleted."""
    from core.fleet import residents as R
    R.nominate(nominee="kimi", callsign="Snooze", receipts=[seeded["kimi"]], by="claude")
    R.ratify(nominee="kimi", callsign="Snooze", by="daniil")
    R.nominate(nominee="kimi", callsign="Muninn", receipts=[seeded["kimi"]], by="claude")
    R.ratify(nominee="kimi", callsign="Muninn", by="daniil")

    now = R.get("kimi")
    assert now["callsign"] == "Muninn", "the active callsign must be the ratified successor"
    assert "Snooze" in (now.get("formerly") or []), \
        "the superseded callsign must survive as a formerly: entry, never be deleted"

    hist = R.history("kimi")
    assert any(h.get("callsign") == "Snooze" for h in hist), \
        "the prior record must still RESOLVE, not merely be remembered as a string"


# ---------------------------------------------------------------- P1 / P2: kimi's fold probe

def test_p1_the_boot_fold_carries_the_residents_own_callsign(seeded):
    """THE HEADLINE PIN. Measured at 0/8 on the live tree before this was written."""
    from core.fleet import residents as R
    R.nominate(nominee="kimi", callsign="Snooze", receipts=[seeded["kimi"]], by="claude")
    R.ratify(nominee="kimi", callsign="Snooze", by="daniil")

    rc, out, err = run("boot", "kimi", "--task", "who am i")
    assert rc == 0, f"boot must succeed, rc={rc}: {err}"
    assert "Snooze" in out, \
        "a resident's own callsign must appear in its boot fold -- otherwise the name asserts " \
        "an archive the boot does not carry (kimi's provenance-laundering objection)"


def test_p2_the_boot_fold_carries_the_receipt_that_earned_the_name(seeded):
    """A callsign without its receipt in the fold is a claim the resident cannot support."""
    from core.fleet import residents as R
    R.nominate(nominee="kimi", callsign="Snooze", receipts=[seeded["kimi"]], by="claude")
    R.ratify(nominee="kimi", callsign="Snooze", by="daniil")

    rc, out, _ = run("boot", "kimi", "--task", "why am i called that")
    assert rc == 0
    assert seeded["kimi"] in out, \
        "the receipt that earned the callsign must be reachable FROM THE FOLD, not only from " \
        "the archive -- 0/8 was the measured state that opened this slice"


def test_p2b_an_unregistered_seat_boots_clean(seeded):
    """No designation is not an error. Most seats are not residents, and boot must not shout."""
    rc, out, _ = run("boot", "some_unregistered_seat", "--task", "x")
    assert rc == 0, "an unregistered seat must still boot"
    assert "Snooze" not in out, "one resident's callsign must never leak into another seat's fold"
