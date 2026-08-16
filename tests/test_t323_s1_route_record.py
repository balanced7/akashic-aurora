"""T323 s1 RED pins: the route record -- the string through the forest becomes a thing.

Daniil's charter, verbatim (eye ed728d23:2173): "a string through a forest you can walk with
by hand so you dont need to re-discover relationships between different things... a mechanical
through line for work we did"; and: "routing savepoints... A unclear route is still a route,
and we can update them as we go." Approved 2026-08-16 ("I approve all of it").

Design lineage: his idea -> the twin's synthesis (ed728d23:2461, routes = chains of reified
provenance) -> fan branch 5's record schema (atom art_20260816_troubleshooting-re-fan_3ddf5a)
-> deepseek's physics pass (atom art_20260816_t323-fence-deepseek_9f8fb4).

THE SUBSTRATE DECISION, pinned here because it AMENDS the fence counter: deepseek said "put
routes in the Eye's own SQLite" because eye.db is the addressable never-drops organ. Right
spirit, one flaw: eye.db is gitignored and rebuildable-by-design, and a route is an AUTHORED
object -- rebuild the db from transcripts and every route would vanish. So s1 follows the
house's own Pillar-0 split: an append-only TRACKED journal (state/coord/routes.jsonl) is the
source of truth; the eye.db `routes` table is the queryable projection beside the addresses,
rebuildable from the journal at any time. P5 is the pin that makes this law: wipe the
projection, rebuild, nothing authored is lost. deepseek's INSERT OR IGNORE idempotency
applies at the projection; journal appends are the durable write.

Run: py -m pytest tests/test_t323_s1_route_record.py -q
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import routes as RT  # noqa: E402


STEPS = [
    {"type": "anchor", "target": "sess-a:100", "receipt": "sess-a:100",
     "note": "the handoff that opened the day"},
    {"type": "observation", "target": "sess-a:210", "receipt": "sess-a:210",
     "note": "watcher top hits are subagent briefs"},
    {"type": "discriminating-test", "target": "sess-a:340", "receipt": "sess-a:340",
     "note": "voice audit: 419/523 operator-voice sessions are briefs",
     "outcome": {"contaminated": "s4", "clean": "END"}},
    {"type": "dead-end", "target": "sess-a:400", "receipt": "sess-a:400",
     "note": "inverse link pairs do NOT fix the type confusion",
     "is_not": ["inverse-pairs-fix-types"]},
    {"type": "decision", "target": "sess-a:520", "receipt": "sess-a:520",
     "note": "filter at the data layer, not per-consumer"},
]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated journal + projection db."""
    journal = tmp_path / "routes.jsonl"
    db = tmp_path / "eye.db"
    monkeypatch.setattr(RT, "JOURNAL_PATH", journal, raising=False)
    monkeypatch.setattr(RT, "DB_PATH", db, raising=False)
    return journal, db


# ------------------------------------------------- P1: a saved route EXISTS twice
def test_p1_save_writes_journal_and_projection(env):
    """The journal line is the durable truth; the projection row is the queryable copy.
    Both must exist after one save -- a route that exists in only one plane is either
    unqueryable or mortal."""
    journal, db = env
    rid = RT.save("first-string", STEPS, by="claude")
    assert rid and rid.startswith("r_")

    lines = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines()]
    assert any(l.get("route_id") == rid for l in lines), "journal holds the authored truth"

    con = sqlite3.connect(str(db))
    row = con.execute("SELECT name, status, walk_count FROM routes WHERE route_id=?",
                      (rid,)).fetchone()
    con.close()
    assert row == ("first-string", "active", 0)


# ------------------------------------------------- P2: idempotent by content
def test_p2_same_content_saves_once(env):
    """deepseek's physics answer, preserved at the projection: the id is a content hash and
    a duplicate save (crash-redelivery, double-paste) is ONE route, not two."""
    journal, db = env
    r1 = RT.save("first-string", STEPS, by="claude")
    r2 = RT.save("first-string", STEPS, by="claude")
    assert r1 == r2
    con = sqlite3.connect(str(db))
    n = con.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    con.close()
    assert n == 1


# ------------------------------------------------- P3: the walk returns the string
def test_p3_walk_returns_steps_in_order_with_receipts(env):
    journal, db = env
    RT.save("first-string", STEPS, by="claude")
    walk = RT.walk("first-string")
    assert walk["name"] == "first-string"
    assert [s["type"] for s in walk["steps"]] == [s["type"] for s in STEPS]
    assert all(s.get("receipt") for s in walk["steps"]), \
        "a step without a receipt is an unfalsifiable claim about the past"


# ------------------------------------------------- P4: dead ends are first-class
def test_p4_dead_end_carries_the_refuted_hypothesis(env):
    """Half the value of a route is the pruned branch (Kepner-Tregoe IS-NOT; the fan's
    branch-5 finding #2). A dead end must carry WHAT was refuted and the receipt that
    refuted it -- otherwise the next walker re-explores."""
    journal, db = env
    RT.save("first-string", STEPS, by="claude")
    walk = RT.walk("first-string")
    dead = [s for s in walk["steps"] if s["type"] == "dead-end"]
    assert dead, "the fixture's dead end vanished"
    assert dead[0]["is_not"] == ["inverse-pairs-fix-types"]
    assert dead[0]["receipt"]


# ------------------------------------------------- P5: THE SUBSTRATE LAW
def test_p5_projection_wipe_loses_nothing_authored(env):
    """The pin that amends the fence counter. eye.db is rebuildable-by-design; routes are
    authored. Wipe the projection entirely -- rebuild() restores every route from the
    tracked journal. If this pin ever breaks, routes have become mortal."""
    journal, db = env
    rid = RT.save("first-string", STEPS, by="claude")
    con = sqlite3.connect(str(db))
    con.execute("DELETE FROM routes")
    con.execute("DELETE FROM route_steps")
    con.commit(); con.close()

    RT.rebuild()
    walk = RT.walk("first-string")
    assert walk["route_id"] == rid
    assert len(walk["steps"]) == len(STEPS)


# ------------------------------------------------- P6: an unclear route is still a route
def test_p6_unresolvable_step_is_dangling_named_and_walkable_past(env):
    """His words are the policy (deepseek's fence answer adopted them verbatim): a step
    whose target cannot be resolved is marked dangling WITH its last-known address, and the
    walk continues -- degraded, named, never aborted."""
    journal, db = env
    steps = STEPS + [{"type": "anchor", "target": "gone-session:999",
                      "receipt": "gone-session:999", "note": "rotated away"}]
    RT.save("degraded-string", steps, by="claude")
    walk = RT.walk("degraded-string", resolve=True)
    last = walk["steps"][-1]
    assert last["resolution"] == "dangling", "an unresolvable step must confess, not abort"
    assert last["target"] == "gone-session:999", "the last-known address is preserved"
    assert len(walk["steps"]) == len(steps), "the walk survived the broken leg"


# ------------------------------------------------- P7: the register is listable
def test_p7_list_shows_name_status_walkcount_steps(env):
    journal, db = env
    RT.save("first-string", STEPS, by="claude")
    rows = RT.list_routes()
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "first-string" and r["status"] == "active"
    assert r["steps"] == len(STEPS) and r["walk_count"] == 0
