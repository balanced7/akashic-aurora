"""T335 s1 RED: a traversal record must not lie about how deep the traversal went.

DANIIL'S RULING, verbatim 2026-08-17: "Lets add that fidelity, I don't want our forest thread
to lie to us and make traversal records be ambiguous."

HOW IT WAS FOUND, because the provenance matters here. He asked whether walking route #1 had
actually helped. The honest answer was that I read the INDEX -- seven one-line labels and their
transcript coordinates -- and never once drilled a leg with `eye get`. The organ recorded that
identically to a full traversal. `walked=3` was a health number nobody had measured, which is
the same class as this morning's M3 pre-registration finding (pins landing WITH their
implementation, so git holds no evidence the acceptance came first) and the same fix shape as
T324's q_usage receipts.

TWO DEFECTS, ONE CAUSE: walk history lives ONLY in the eye.db projection, as a bare integer.

  (1) AMBIGUITY -- walk_count cannot distinguish a glance from a traversal.

  (2) DURABILITY, and this one is worse and was NOT in the original observation. Walks are
      never journaled at all. rebuild() replays only kind="route_saved", and _project()
      hardcodes walk_count=0 on insert, so wiping eye.db destroys every traversal ever
      recorded. routes.py's own module docstring states the opposite as a law -- "rebuild()
      replays the journal, so wiping the projection loses nothing authored (pin P5)" -- and
      P5 is true for every field except the one the organ produces by being USED. The route
      record is durable; the evidence that anyone walked it is not.

THE SHAPE OF THE FIX is the house's, twice over. Walks become journal records (the Pillar 0
split the module already declares: authored truth in state/coord/routes.jsonl, projection in
eye.db). Depth is RECORDED FROM THE EXECUTED PATH, never declared by the caller -- T322's
ingress law, capture origin at the source rather than infer it at the projection. And legacy
walk_count with no journal record behind it resolves UNKNOWN rather than being backfilled as
"listed", which is T176's law: absence must never be dressed as a decision. Guessing here
would be the exact defect this slice exists to close, committed by the fix itself.

SCOPE OF s1: the record layer (core/eye/routes.py). The `ls`/`walk` RENDER lives in
agent_cli.py, which is claimed by T275 (verifying since 2026-08-11) -- not taken, so the
surface is s2. walks() below is the read side the render will consume.

Run: py -m pytest tests/test_t335_s1_walk_fidelity.py -q
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.eye import routes as R  # noqa: E402


STEPS = [
    {"type": "anchor", "target": "sess:1", "note": "the charter"},
    {"type": "dead-end", "target": "sess:2", "note": "the paraphrase trap",
     "is_not": ["the-phrase-is-the-key"]},
    {"type": "decision", "target": "sess:3", "note": "filed"},
]


def _seed_events(db_path, targets):
    """A drill reads leg BODIES out of the Eye's events table, so the fixture has to have
    one. Seeding it is what makes P6 test the mechanism instead of testing `len(STEPS)`."""
    import sqlite3
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
    """Both planes repointed together -- the module says they are repointable for exactly
    this reason, and a walk-fidelity pin that wrote to the live journal would be recording
    fake traversals into the record it is trying to make trustworthy."""
    monkeypatch.setattr(R, "JOURNAL_PATH", tmp_path / "routes.jsonl")
    monkeypatch.setattr(R, "DB_PATH", tmp_path / "eye.db")
    rid = R.save("test-string", STEPS, by="claude")
    _seed_events(tmp_path / "eye.db", [s["target"] for s in STEPS])
    return rid


def _journal_kinds(monkeypatched_path) -> list:
    if not monkeypatched_path.exists():
        return []
    out = []
    for line in monkeypatched_path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


# ============================================================ durability: the worse defect

def test_p1_a_walk_is_journaled_not_only_counted(tied, tmp_path):
    """A walk must land on the DURABLE plane, beside the save. Today it exists only as an
    incremented integer in a projection the module calls rebuildable."""
    R.walk("test-string")
    recs = _journal_kinds(tmp_path / "routes.jsonl")
    walked = [r for r in recs if r.get("kind") == "route_walked"]
    assert len(walked) == 1, (
        "a walk that leaves nothing on the journal is a traversal the truth plane cannot "
        "attest to -- and the projection holding it is wiped by design")
    assert walked[0].get("route_id") == tied


def test_p2_wiping_the_projection_loses_no_walk_history(tied, tmp_path):
    """THE LAW THE MODULE ALREADY CLAIMS, made true. routes.py's docstring: 'rebuild()
    replays the journal, so wiping the projection loses nothing authored (pin P5).' Every
    walk ever taken is currently the exception to that sentence."""
    R.walk("test-string")
    R.walk("test-string")
    (tmp_path / "eye.db").unlink()          # the wipe the module says is safe
    R.rebuild()
    w = R.walks("test-string")
    assert w["total"] == 2, (
        "walk history did not survive the rebuild the module advertises as lossless")
    assert w["by_depth"].get("listed") == 2


def test_p3_a_walk_is_an_event_so_two_walks_are_two_records(tied, tmp_path):
    """Append-only, like every other record in this house. A walk is something that
    HAPPENED; collapsing two into one state would re-create the ambiguity one layer down."""
    R.walk("test-string")
    R.walk("test-string")
    walked = [r for r in _journal_kinds(tmp_path / "routes.jsonl")
              if r.get("kind") == "route_walked"]
    assert len(walked) == 2
    assert walked[0].get("at") is not None and walked[1].get("at") is not None


# ============================================================ ambiguity: depth is recorded

def test_p4_a_plain_walk_records_that_it_only_listed(tied):
    """The pin that encodes what I actually did to route #1. Printing the index is a real
    and useful act; it is simply not a traversal, and the record must say which."""
    R.walk("test-string")
    w = R.walks("test-string")
    assert w["by_depth"].get("listed") == 1
    assert not w["by_depth"].get("drilled"), (
        "a plain walk must never be able to record itself as drilled")


def test_p5_resolve_is_a_deeper_walk_and_says_so(tied):
    """--resolve genuinely touches every leg's address to classify it current/dangling. That
    is more than listing and less than reading the bodies, and it gets its own name rather
    than being rounded to either neighbour."""
    R.walk("test-string", resolve=True)
    w = R.walks("test-string")
    assert w["by_depth"].get("resolved") == 1
    assert not w["by_depth"].get("listed")


def test_p6_drilling_records_the_depth_and_the_count(tied):
    """The real traversal: every leg's body actually read. legs_drilled ships WITH it,
    because a depth label without a count is the same unfalsifiable claim one level up."""
    R.walk("test-string", drill=True)
    w = R.walks("test-string")
    assert w["by_depth"].get("drilled") == 1
    rec = w["records"][-1]
    assert rec["legs_drilled"] == len(STEPS), "a drilled walk must count the legs it read"
    assert rec["legs_shown"] == len(STEPS)


def test_p6b_a_drill_over_a_dangling_leg_counts_what_it_actually_read(tmp_path, monkeypatch):
    """THE PIN THAT STOPS legs_drilled FROM BEING len(steps) IN DISGUISE. Half a route's
    legs can dangle -- that is why _resolve() exists and why 'an unclear route is still a
    route'. A drill that reports 3-of-3 while two bodies were unreachable would be the same
    lie in a new field, and it is the lie this slice is most at risk of shipping."""
    monkeypatch.setattr(R, "JOURNAL_PATH", tmp_path / "routes.jsonl")
    monkeypatch.setattr(R, "DB_PATH", tmp_path / "eye.db")
    R.save("partial", STEPS, by="claude")
    _seed_events(tmp_path / "eye.db", [STEPS[0]["target"]])     # only leg 1 is reachable

    R.walk("partial", drill=True)
    rec = R.walks("partial")["records"][-1]
    assert rec["legs_shown"] == 3
    assert rec["legs_drilled"] == 1, (
        "two legs dangle -- a drill must report the bodies it got, not the legs it wanted")


def test_p7_depth_is_derived_from_the_executed_path_not_declared(tied):
    """T322's ingress law applied here: the record must not accept a caller's word for what
    the caller did. A depth argument would make the fidelity field exactly as trustworthy as
    the number it replaced -- and would let a glance file itself as a traversal."""
    with pytest.raises(TypeError):
        R.walk("test-string", depth="drilled")   # type: ignore[call-arg]


# ============================================================ the legacy population

def test_p8_unbacked_walk_count_resolves_UNKNOWN_never_backfilled(tied, tmp_path):
    """THE PIN THAT KEEPS THE FIX HONEST ABOUT ITSELF. Route #1 already carries walk_count=3
    from before walks were journaled. Those three had a real depth and nobody recorded it,
    so the only true answer is UNKNOWN. Backfilling them as 'listed' would be a guess wearing
    a measurement's clothes -- the T176 defect, committed by the commit that closes it."""
    import sqlite3
    con = sqlite3.connect(str(tmp_path / "eye.db"))
    con.execute("UPDATE routes SET walk_count = 3 WHERE route_id=?", (tied,))
    con.commit()
    con.close()

    w = R.walks("test-string")
    assert w["unknown"] == 3, (
        "three counted walks with no journal record behind them are UNKNOWN, not listed")
    assert w["total"] == 3
    assert not w["by_depth"], "no depth may be attributed to a walk nobody recorded"

    R.walk("test-string")
    w2 = R.walks("test-string")
    assert w2["unknown"] == 3, "a new walk must not retroactively explain the old ones"
    assert w2["by_depth"].get("listed") == 1
    assert w2["total"] == 4


def test_p9_the_read_side_never_offers_a_bare_total_without_its_breakdown(tied):
    """A count without its scope is not a coverage claim -- the frame this house already
    enforces on every other number. `walked=3` was that violation in miniature."""
    R.walk("test-string")
    w = R.walks("test-string")
    for field in ("total", "by_depth", "unknown", "records"):
        assert field in w, f"walks() must ship {field} -- the total alone is what lied"
