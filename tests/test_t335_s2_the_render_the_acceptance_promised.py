"""T335 s2 RED: the two acceptance clauses that shipped as prose instead of as doors.

HOW THIS WAS FOUND, and the provenance is the point. Heimdall bounced T335 on independent
review (2026-08-17, report art_20260817_frontier-heimdall-t340-t339-close_d9f203). He did NOT
bounce the pin he was asked to attack -- he traced `depth` end to end and confirmed it is
genuinely unreachable from any caller, which is the row's load-bearing invariant. He bounced
something better:

    "the record does not lie, but the acceptance overreaches the shipped surface by two
     clauses."

  CLAUSE 4 -- "--drill records drilled with a legs_drilled count." The parser defines
  route_action, --resolve, --json. There is no --drill. The `drill` parameter exists only as
  a Python kwarg, reachable by `import core.eye.routes` and by nothing a seat would ever type.

  CLAUSE 7 -- "ls and walk show the depth breakdown and never a bare total." `ls` renders
  walked={walk_count}; `walk` renders walk #{walk_count}. Both are exactly the bare total the
  row exists to stop trusting. walks() / by_depth / unknown are never called from agent_cli.py.

WHY THIS IS A ROW-COMPLETION AND NOT A NEW ROW. s1's own scope note deferred the render
because agent_cli.py was claimed by T275 ("verifying since 2026-08-11 -- not taken, so the
surface is s2"). T275 closed 2026-08-17 (5ce065d8, verified independently). The reason the
surface was deferred no longer exists, so the deferral expires rather than graduating into a
permanent limitation.

THE FORK HEIMDALL REFUSED TO PICK, and why this half of it: he offered (1) wire the doors, or
(2) amend clauses 4 and 7 down to describe the record layer. Option 2 writes a known
limitation into the contract a receipt signs, and Daniil's standing rule is that an order-note
around a reproducible defect is the TRIGGER to fix it properly, not the fix. So: wire it.

THE SHAPE OF THE FIX IS SMALL BECAUSE s1 ALREADY DID THE WORK. walk() already returns depth,
legs_drilled and a full `tally` from walks(). The render simply never read them. This is the
house's signature defect in its smallest form -- built, not wired -- one plane above the one
s1 closed.

PIN DISCIPLINE, carried from the same night's fourth pin-lying instance: every assertion below
is POSITIVE (the content expected), never absence-of-an-error. Fixture values are chosen so
they cannot appear as substrings of the constants in scope -- the route is named with a token
no source file contains, and the leg count is 7 so a match on "7 legs" cannot be satisfied by
a stray 3 from STEPS or a 1 from a version field.

Run: py -m pytest tests/test_t335_s2_the_render_the_acceptance_promised.py -q
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.eye import routes as R  # noqa: E402
import agent_cli  # noqa: E402

# A name no source file in this repo contains, so a render assertion can never pass by
# matching some other route's output that happened to be printed.
ROUTE = "zqx-forest-thread-probe"

STEPS = [
    {"type": "anchor", "target": "sessQ:11", "note": "the charter"},
    {"type": "observation", "target": "sessQ:12", "note": "the first sighting"},
    {"type": "discriminating-test", "target": "sessQ:13", "note": "the control"},
    {"type": "dead-end", "target": "sessQ:14", "note": "the paraphrase trap",
     "is_not": ["the-phrase-is-the-key"]},
    {"type": "decision", "target": "sessQ:15", "note": "filed"},
    {"type": "handoff", "target": "sessQ:16", "note": "passed on"},
    {"type": "anchor", "target": "sessQ:17", "note": "the closing tie"},
]
LEGS = len(STEPS)          # 7 -- see the pin-discipline note above


def _seed_events(db_path, targets):
    """A drill reads leg BODIES out of the Eye's events table, so the fixture must have one.
    Seeding it is what makes the drill pins test the mechanism instead of testing len(STEPS)."""
    con = sqlite3.connect(str(db_path))
    con.execute("""CREATE TABLE IF NOT EXISTS events(
        event_id TEXT PRIMARY KEY, session TEXT NOT NULL, line INTEGER NOT NULL,
        ts REAL, voice TEXT NOT NULL, type TEXT NOT NULL, text TEXT NOT NULL,
        cwd TEXT, branch TEXT, tokens INTEGER, uuid TEXT, parent_uuid TEXT,
        indexed_at REAL)""")
    for t in targets:
        sess, _, line = t.rpartition(":")
        con.execute("INSERT OR IGNORE INTO events(event_id, session, line, voice, type, "
                    "text) VALUES(?,?,?,?,?,?)",
                    (t, sess, int(line), "operator", "message", f"body of {t}"))
    con.commit()
    con.close()


@pytest.fixture()
def tied(tmp_path, monkeypatch):
    """Both planes repointed together. A render pin that walked the LIVE route would write
    fake traversals into the very record this row exists to make trustworthy -- the walk is a
    mutation, so an un-isolated pin here is self-falsifying."""
    monkeypatch.setattr(R, "JOURNAL_PATH", tmp_path / "routes.jsonl")
    monkeypatch.setattr(R, "DB_PATH", tmp_path / "eye.db")
    R.save(ROUTE, STEPS, by="claude")
    _seed_events(tmp_path / "eye.db", [s["target"] for s in STEPS])
    return tmp_path


def _run(argv):
    """Drive the REAL door: the real parser, the real dispatch. A pin that called routes.walk()
    directly would prove nothing about clause 4, whose entire content is that a seat can TYPE
    this."""
    p = agent_cli.build_parser()
    args = p.parse_args(argv)
    return args.fn(args)


def _walk_records(tmp_path):
    jp = tmp_path / "routes.jsonl"
    if not jp.exists():
        return []
    out = []
    for line in jp.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("kind") == "route_walked":
            out.append(rec)
    return out


# ---------------------------------------------------------------- clause 4: the flag

def test_p1_the_drill_flag_exists_at_the_door():
    """CLAUSE 4, at its narrowest. The acceptance names a flag; either it parses or the
    clause is prose. Asserts the parsed VALUE, not the help text -- a --drill mentioned only
    in a help string would satisfy a grep and still not run."""
    p = agent_cli.build_parser()
    args = p.parse_args(["eye", "route", "walk", ROUTE, "--drill"])
    assert getattr(args, "drill", None) is True, (
        "eye route walk has no --drill flag; T335 clause 4 names one. The drill= kwarg on "
        "routes.walk() is reachable only by importing the module, which is not a door")


def test_p2_walking_with_drill_records_drilled_depth(tied):
    """THE MECHANISM PIN, and the reason P1 alone is not enough. A flag that parses but is
    never threaded into walk() would leave the journal recording 'listed' while the operator
    typed --drill -- a traversal record lying about its depth, which is the exact defect the
    whole row exists to kill, reintroduced one layer above where s1 killed it."""
    _run(["eye", "route", "walk", ROUTE, "--drill"])
    recs = _walk_records(tied)
    assert len(recs) == 1, f"expected exactly one walk record, got {len(recs)}"
    assert recs[0]["depth"] == "drilled", (
        f"typed --drill, journal recorded depth={recs[0]['depth']!r}")
    assert recs[0]["legs_drilled"] == LEGS, (
        f"clause 4 names a legs_drilled count; expected {LEGS}, got "
        f"{recs[0]['legs_drilled']}")


def test_p3_a_plain_walk_still_records_listed(tied):
    """The other half of the same mechanism, and a guard against the cheapest way to make P2
    pass: hardcoding drilled. s1's invariant is that depth reports what ACTUALLY ran."""
    _run(["eye", "route", "walk", ROUTE])
    recs = _walk_records(tied)
    assert recs[0]["depth"] == "listed", (
        f"a plain walk must record listed, got {recs[0]['depth']!r}")
    assert recs[0]["legs_drilled"] == 0


# ---------------------------------------------------------------- clause 7: the render

def test_p4_the_walk_render_carries_the_breakdown_not_a_bare_total(tied, capsys):
    """CLAUSE 7, on the walk surface. Positive assertion: the breakdown's own labels must be
    PRESENT. Written this way deliberately -- 'assert "walk #" not in out' would pass against
    a render that printed nothing at all, which is absence-of-a-lie standing in for
    presence-of-the-truth, the shape that hid three real defects behind green pins last night."""
    _run(["eye", "route", "walk", ROUTE, "--drill"])
    out = capsys.readouterr().out
    assert "drilled" in out, (
        "the walk render never names the depth it just recorded; walk() already returns "
        "depth and tally and the render reads neither")
    assert f"{LEGS}" in out, "the render must carry the legs count it drilled"


def test_p4b_unknown_walks_are_named_in_the_render_not_folded_away(tied, capsys):
    """The UNKNOWN half of clause 7, and this pin was WRONG on its first draft -- it asserted
    UNKNOWN appears unconditionally, on a fixture whose walks are all journaled. The honest
    render names UNKNOWN only when unknown walks exist; satisfying the first draft would have
    meant printing UNKNOWN=0 on every route, making the surface worse to make a pin green.
    Recorded here rather than quietly amended: the pin was red for the wrong reason, which is
    the same class as a pin green for the wrong reason and is caught by the same question --
    would this pass/fail for a reason unrelated to the mechanism?

    So the pin now MANUFACTURES the condition it is about: phantom walks the projection
    counted before walks were journaled, which must surface as UNKNOWN rather than being
    folded into listed."""
    con = sqlite3.connect(str(tied / "eye.db"))
    con.execute("UPDATE routes SET walk_count = walk_count + 4 WHERE name = ?", (ROUTE,))
    con.commit()
    con.close()
    _run(["eye", "route", "walk", ROUTE])
    out = capsys.readouterr().out
    assert "UNKNOWN=4" in out, (
        "four walks with no journal record behind them must render as UNKNOWN=4; folding "
        "them into a depth bucket is the guess T176 forbids, committed at the render side "
        f"after s1 refused it at the read side. got: {out!r}")


def test_p5_the_ls_render_carries_the_breakdown_not_a_bare_total(tied, capsys):
    """CLAUSE 7, on the ls surface. A bare walked=N is the number Daniil's ruling called
    ambiguous, printed at the moment someone decides whether a route is worth walking.

    HONEST SCOPE, narrowed after Heimdall's flag: this pin is green BY SELF-SEEDING. It drills
    first, so the drilled=1 it asserts exists only because this same test just wrote that
    record -- _route_tally renders only non-zero buckets, so a COLD route prints no `drilled`
    at all. The pin is true, and it is weaker than its first docstring implied ("the surface a
    seat reads FIRST" described a route nobody had just drilled). Recorded rather than quietly
    reworded: a pin whose docstring claims more than its fixture arranges is the same
    claim-wider-than-premise shape this row was bounced for. test_p5b covers the cold case."""
    _run(["eye", "route", "walk", ROUTE, "--drill"])
    capsys.readouterr()
    _run(["eye", "route", "ls"])
    out = capsys.readouterr().out
    assert ROUTE in out, "fixture route missing from ls -- the pin is not reading the render"
    assert "drilled" in out, (
        "ls renders a bare walked=N; clause 7 requires the depth breakdown beside it")


def test_p5b_a_cold_route_renders_honestly_rather_than_blank(tied, capsys):
    """The case p5 does NOT cover, added because Heimdall named the gap. A route nobody has
    walked must say so in words rather than rendering an empty parenthesis, because a blank
    beside a zero reads as a broken render and a reader cannot tell it from a missing one."""
    _run(["eye", "route", "ls"])
    out = capsys.readouterr().out
    assert "never walked" in out, (
        f"a cold route must name its own emptiness, not render blank. got: {out!r}")


def test_p5c_a_depth_the_vocabulary_does_not_know_is_shown_not_dropped(tied, capsys):
    """HEIMDALL'S SECOND FLAG, closed. The renderer used to order by a hardcoded tuple, so any
    depth outside it was journalled correctly and then silently vanished from every surface --
    the record right, nothing reading it, which is this house's signature defect one turn down.
    Ordering may be a closed choice; MEMBERSHIP may not. An unrecognised depth is precisely the
    case a reader most needs to see."""
    con = sqlite3.connect(str(tied / "eye.db"))
    con.execute("UPDATE routes SET walk_count = walk_count + 1 WHERE name = ?", (ROUTE,))
    con.execute("INSERT INTO route_walks(walk_id, route_id, at, by, depth, legs_shown, "
                "legs_drilled) SELECT 'w-probe', route_id, 1, 'claude', 'spelunked', 7, 7 "
                "FROM routes WHERE name = ?", (ROUTE,))
    con.commit()
    con.close()
    _run(["eye", "route", "ls"])
    out = capsys.readouterr().out
    assert "spelunked=1" in out, (
        f"a depth outside DEPTHS must still render; dropping it makes the journal's truth "
        f"invisible at the surface. got: {out!r}")


# ---------------------------------------------------------------- the s1 invariant, guarded

def test_p6_wiring_the_flag_did_not_make_depth_caller_declarable(tied):
    """THE REGRESSION GUARD ON THE LOAD-BEARING INVARIANT. Heimdall confirmed depth is
    unreachable from any caller; this row adds a caller. The one way s2 could damage s1 is by
    threading a depth string through the new flag instead of a boolean, so the pin that
    mattered most in s1 is re-asserted here against the surface that could break it."""
    with pytest.raises(TypeError):
        R.walk(ROUTE, depth="drilled")


def test_p7_legacy_walks_without_journal_backing_still_render_unknown(tied):
    """T176's law, which the render must not quietly undo. A projection counted walks before
    walks were journaled; those had a real depth nobody recorded. Backfilling them as
    'listed' at RENDER time would be the same guess s1 refused to make at READ time."""
    con = sqlite3.connect(str(tied / "eye.db"))
    con.execute("UPDATE routes SET walk_count = walk_count + 5 WHERE name = ?", (ROUTE,))
    con.commit()
    con.close()
    tally = R.walks(ROUTE)
    assert tally["unknown"] == 5, (
        f"five phantom walks with no journal record must resolve UNKNOWN, got "
        f"{tally['unknown']}")
