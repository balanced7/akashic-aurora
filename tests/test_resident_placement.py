"""T267 RED -- the designation has four fields and we populate two.

Daniil 2026-08-10: "Can you build it out with placeholder names and we can change them later
if we don't like them."

STATE THAT OPENED THIS: three residents are ratified -- Anthropic|Vandor, Kimi|Navi,
Deepseek|Heimdall -- and every one renders as VENDOR|CALLSIGN only, because family, team and
number were never set. The schema exists and the plane is empty, so `@Onyx` and `@Red`
address nothing and the family half of T108 routing has nothing to route to.

WHY PLACEMENT IS ITS OWN VERB, and not a re-nomination. Naming and posting are DIFFERENT
ACTS. Ceremony rule 1 forbids naming yourself; it says nothing about where you are posted,
and posting is an org decision. Forcing placement through nominate+ratify would also mean
re-ratifying an identical callsign purely to set a field -- filling the naming history with
records that decide nothing, and inviting a spurious `formerly:` entry for a name that never
changed.

APPEND-ONLY STILL. A re-posting appends; the prior posting survives, because "who was in
Onyx during exercise 7" is a question about the past, and an update-in-place would erase the
only record that can answer it. Same physics as the callsign log and the role stream.

Run: py -m pytest tests/test_resident_placement.py -q
"""
import os
import subprocess
import sys

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _seed(agent, exp):
    rc, out = run("learn", agent, "--experiment", exp, "--tried", "placement seed",
                  "--result", "placement seed")
    assert rc == 0, out
    return exp


@pytest.fixture(scope="module")
def posted():
    """A ratified resident, ready to be posted somewhere."""
    from core.fleet import residents as R
    exp = _seed("kimi", "pin_placement_receipt_kimi")
    R.nominate(nominee="kimi", callsign="Navi", receipts=[exp], by="daniil_pin")
    R.ratify(nominee="kimi", callsign="Navi", by="daniil_pin")
    return "kimi"


# ---------------------------------------------------------------- P1: the full designation

def test_p1_placement_completes_the_four_field_designation(posted):
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, vendor="Kimi",
            by="daniil_pin")
    d = R.designation("kimi")
    for part in ("Kimi", "Jade", "Red", "Navi"):
        assert part in d, f"'{part}' missing from the full designation: {d!r}"
    assert "1 - Navi" in d, f"the number must render with the callsign: {d!r}"


def test_p1b_an_unplaced_resident_still_renders_the_short_form(posted):
    """Most seats are posted nowhere. Absence of a posting is not an error and must not
    render as an empty field or a placeholder dash."""
    from core.fleet import residents as R
    exp = _seed("cursor", "pin_placement_receipt_cursor")
    R.nominate(nominee="cursor", callsign="Compass", receipts=[exp], by="daniil_pin")
    R.ratify(nominee="cursor", callsign="Compass", by="daniil_pin")
    d = R.designation("cursor")
    assert "Compass" in d
    # No pipe is CORRECT here: with no vendor and no posting there is only a callsign. The
    # first draft of this pin demanded a "|" and was asserting a FORMAT rather than the
    # property that matters -- that absent fields render as absent, never as empty segments.
    assert "None" not in d and "|  |" not in d and not d.strip().startswith("|"),         f"absent fields must render as ABSENT, not as empty segments: {d!r}"


# ---------------------------------------------------------------- P2: append-only

def test_p2_a_reposting_appends_and_the_prior_posting_survives(posted):
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, by="daniil_pin")
    R.place(agent="kimi", family="Onyx", team="Blue", number=4, by="daniil_pin")
    assert "Onyx" in R.designation("kimi") and "Blue" in R.designation("kimi")
    hist = R.placement_history("kimi")
    fams = [h.get("family") for h in hist]
    # Assert the TAIL, not the whole list. The fixture is module-scoped, so earlier tests have
    # already posted this resident; demanding the full history asserted a test isolation that
    # shared state never provided. The pin's bug, not the code's -- and the ordering claim this
    # pin actually makes is about the last two postings.
    assert fams[-2:] == ["Jade", "Onyx"], \
        f"both postings must survive in order -- an update path would erase the timeline: {fams}"
    assert len(fams) >= 2, "history must accumulate, never overwrite"


def test_p3_placement_never_touches_the_callsign_or_mints_a_formerly(posted):
    """The bug this verb exists to avoid: setting a field must not look like a re-naming."""
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, by="daniil_pin")
    rec = R.get("kimi")
    assert rec["callsign"] == "Navi", "placement must not change the name"
    assert not rec.get("formerly"), \
        f"placement must not mint a formerly: entry -- no name was superseded: {rec.get('formerly')}"


# ---------------------------------------------------------------- P4: the refusals

def test_p4_placing_a_non_resident_refuses_and_points_at_the_ceremony(posted):
    from core.fleet import residents as R
    with pytest.raises(ValueError) as e:
        R.place(agent="nobody_here", family="Onyx", team="Blue", number=9, by="daniil_pin")
    msg = str(e.value).lower()
    assert "resident" in msg and "nominate" in msg, \
        f"the refusal must say why AND name the fix: {e.value}"


def test_p4b_placement_needs_an_actor(posted):
    from core.fleet import residents as R
    with pytest.raises(ValueError):
        R.place(agent="kimi", family="Onyx", team="Blue", number=2, by="")


# ---------------------------------------------------------------- P5: the door

def test_p5_the_cli_places_and_show_renders_it(posted):
    rc, out = run("resident", "place", "kimi", "--family", "Jade", "--team", "Red",
                  "--number", "1", "--by", "daniil_pin")
    assert rc == 0, out
    rc, shown = run("resident", "show", "kimi")
    assert rc == 0
    for part in ("Jade", "Red", "Navi"):
        assert part in shown, f"'{part}' must render in show: {shown[:300]}"


def test_p6_roster_lists_a_family(posted):
    """The point of a family is that you can ask who is in it -- otherwise it is decoration
    and the family half of T108 routing has nothing to address."""
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, by="daniil_pin")
    members = R.family_members("Jade")
    assert "kimi" in members, f"Jade must contain kimi, got {members}"
    assert R.family_members("NoSuchFamily") == [], "an empty family is empty, never everyone"


def test_p7_team_membership_is_queryable_too(posted):
    """Heimdall's T267 review gap: team_members() existed with ZERO pin coverage while being
    structurally identical to family_members and equally load-bearing for the TEAM half of
    T108 routing. Same shape as the vendor gap this slice already hit -- a function exists,
    the code is right, and nothing verifies it before the routing slice depends on it."""
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, by="daniil_pin")
    assert "kimi" in R.team_members("Red"), "Red must contain kimi"
    assert R.team_members("NoSuchTeam") == [], "an empty team is empty, never everyone"
    assert R.team_members("") == [], "a blank team must not match every unposted resident"


def test_p8_a_re_placement_changes_the_vendor_and_the_latest_wins(posted):
    """The substrate-change path the design atom promises: a model upgrade must render as a
    flagged change, never as an orphaned archive. Untested until the review named it."""
    from core.fleet import residents as R
    R.place(agent="kimi", family="Jade", team="Red", number=1, vendor="Kimi", by="daniil_pin")
    R.place(agent="kimi", family="Jade", team="Red", number=1, vendor="Kimi-K3", by="daniil_pin")
    d = R.designation("kimi")
    assert "Kimi-K3" in d, f"the latest vendor must win: {d!r}"
    assert R.get("kimi")["callsign"] == "Navi", "and re-homing must NOT rename the resident"
