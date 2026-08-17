"""T323 s1 -- the route record: the string through the forest, as a thing you can hold.

Daniil's charter, verbatim (eye ed728d23:2173): "a string through a forest you can walk with
by hand so you dont need to re-discover relationships between different things... a mechanical
through line for work we did and become an easy to parse and easy to trace map." And the
policy sentence this module enforces at every broken leg (adopted by the fence as literal
mechanics): "A unclear route is still a route, and we can update them as we go."

Lineage, exact: his idea -> the twin's synthesis (ed728d23:2461, a route IS a chain of
reified provenance) -> the fan-5 record schema (atom .._troubleshooting-re-fan_3ddf5a) ->
deepseek's physics pass (atom .._t323-fence-deepseek_9f8fb4) -> this build.

THE SUBSTRATE SPLIT (the one amendment to the fence counter, made loudly): deepseek said
"put routes in the Eye's own SQLite" -- right spirit (routes are provenance over addresses;
they belong beside the addresses), one flaw: eye.db is gitignored and rebuildable-by-design,
and a route is an AUTHORED object. A rebuild would erase every string anyone ever tied. So
Pillar 0's own split applies:

    state/coord/routes.jsonl   append-only, TRACKED  -- the authored truth (the Ledger half)
    eye.db routes/route_steps  queryable projection  -- rebuildable from the journal (Store)

Saves append the journal first, then upsert the projection. rebuild() replays the journal,
so wiping the projection loses nothing authored (pin P5). deepseek's idempotency survives at
both layers: the route id is a content hash, so a crash-redelivered or double-pasted save is
the SAME line and the SAME row (pin P2), and the projection insert is INSERT OR IGNORE.

T335 -- WALKS ARE RECORDS TOO, and until 2026-08-17 they were the exception to the sentence
above. A walk only incremented walk_count in the PROJECTION; rebuild() replayed nothing but
route_saved, and _project() inserts walk_count=0. So "wiping the projection loses nothing
authored" was true of every field except the one this organ produces by being USED -- the
route survived a wipe and the evidence anyone had walked it did not. Walks now journal as
kind="route_walked" and replay like saves, so the law holds as written.

The same record closes the ambiguity Daniil named ("I don't want our forest thread to lie to
us"): walk_count could not tell a glance from a traversal. Each walk now carries a DEPTH
derived from the executed path -- listed / resolved / drilled, with legs_drilled counting
BODIES OBTAINED rather than legs attempted. Walks taken before this existed resolve UNKNOWN
in walks(); they are never backfilled, because inventing a depth for them would be the exact
defect the field was added to remove.

STEP VOCABULARY (fan-5, trimmed to s1): observation | discriminating-test | decision |
dead-end | anchor | handoff. Dead ends are first-class and carry the refuted hypothesis in
`is_not` plus the receipt that killed it -- half a route's value is the pruned branch the
next walker skips. Unknown types are refused at save: a vocabulary that accepts anything
means nothing (the kind-resolution lesson, one plane over).

s1 deliberately does NOT include: the recall-at trigger join (s2, holds for kimi's
precision counter), assertions/competing-route ranking (s3), retraction (s4), prefetch (s5).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Module-level so tests (and a future config pass) can repoint both planes together.
JOURNAL_PATH = _REPO_ROOT / "state" / "coord" / "routes.jsonl"
DB_PATH = _REPO_ROOT / "state" / "eye" / "eye.db"

SCHEMA_VERSION = 1

STEP_TYPES = ("observation", "discriminating-test", "decision", "dead-end", "anchor",
              "handoff")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canon_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize author-supplied steps: only known keys, only known types, receipts required.

    A step without a receipt is an unfalsifiable claim about the past -- refused at the
    door rather than discovered at walk time."""
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(steps):
        typ = str(s.get("type", ""))
        if typ not in STEP_TYPES:
            raise ValueError(f"step {i}: unknown type {typ!r} (vocabulary: {STEP_TYPES})")
        receipt = str(s.get("receipt") or s.get("target") or "")
        if not receipt:
            raise ValueError(f"step {i}: no receipt -- a claim about the past must be "
                             "checkable")
        out.append({
            "id": f"s{i + 1}",
            "type": typ,
            "target": str(s.get("target") or receipt),
            "receipt": receipt,
            "note": " ".join(str(s.get("note", "")).split()),
            "is_not": [str(x) for x in (s.get("is_not") or [])],
            "outcome": dict(s.get("outcome") or {}),
            "superseded_by": s.get("superseded_by"),
        })
    return out


def _route_id(name: str, steps: List[Dict[str, Any]]) -> str:
    """Content-hash id (deepseek's physics answer): the same authored content is the same
    route, however many times a crash or a double-paste replays the save."""
    blob = json.dumps({"name": name, "steps": steps}, sort_keys=True, ensure_ascii=False)
    return "r_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _connect() -> sqlite3.Connection:
    p = Path(DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS routes(
        route_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
        walk_count INTEGER NOT NULL DEFAULT 0, by TEXT, at TEXT,
        schema_version INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS route_steps(
        route_id TEXT NOT NULL, seq INTEGER NOT NULL, id TEXT, type TEXT NOT NULL,
        target TEXT, receipt TEXT, note TEXT, is_not TEXT, outcome TEXT,
        superseded_by TEXT, PRIMARY KEY(route_id, seq))""")
    # T335: the typed walk record. walk_count above survives as the TOTAL (it is the only
    # thing carrying the walks taken before this table existed); this table carries the ones
    # whose depth is actually known. The difference between them is the UNKNOWN population,
    # and it is computed, never backfilled.
    con.execute("""CREATE TABLE IF NOT EXISTS route_walks(
        walk_id TEXT PRIMARY KEY, route_id TEXT NOT NULL, at TEXT, by TEXT,
        depth TEXT NOT NULL, legs_shown INTEGER, legs_drilled INTEGER)""")
    return con


def _project_walk(con: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    """T335: one route_walked journal record -> one route_walks row, and the total moves
    ONLY when a row was really inserted. INSERT OR IGNORE plus rowcount is what makes a
    replayed journal idempotent here -- an unconditional `walk_count + 1` would inflate the
    total on every rebuild, which is the same class of lie this slice exists to remove."""
    cur = con.execute(
        "INSERT OR IGNORE INTO route_walks(walk_id, route_id, at, by, depth, legs_shown, "
        "legs_drilled) VALUES(?,?,?,?,?,?,?)",
        (rec["walk_id"], rec["route_id"], rec.get("at", ""), rec.get("by", ""),
         rec["depth"], rec.get("legs_shown"), rec.get("legs_drilled")))
    if cur.rowcount:
        con.execute("UPDATE routes SET walk_count = walk_count + 1 WHERE route_id=?",
                    (rec["route_id"],))


def _project(con: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    """One journal record -> projection rows. INSERT OR IGNORE keeps replays idempotent."""
    con.execute(
        "INSERT OR IGNORE INTO routes(route_id, name, status, walk_count, by, at, "
        "schema_version) VALUES(?,?,?,?,?,?,?)",
        (rec["route_id"], rec["name"], rec.get("status", "active"), 0,
         rec.get("by", ""), rec.get("at", ""), rec.get("schema_version", SCHEMA_VERSION)))
    for seq, s in enumerate(rec["steps"]):
        con.execute(
            "INSERT OR IGNORE INTO route_steps(route_id, seq, id, type, target, receipt, "
            "note, is_not, outcome, superseded_by) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (rec["route_id"], seq, s["id"], s["type"], s["target"], s["receipt"],
             s["note"], json.dumps(s["is_not"]), json.dumps(s["outcome"]),
             s.get("superseded_by")))


def save(name: str, steps: List[Dict[str, Any]], *, by: str) -> str:
    """Tie a string: journal first (the durable truth), projection second (the queryable
    copy). Returns the content-hash route id either way -- saving the same content twice
    is one route (P2)."""
    name = " ".join(str(name).split())
    if not name:
        raise ValueError("a route needs a name -- it is the handle the next walker grabs")
    canon = _canon_steps(steps)
    rid = _route_id(name, canon)
    rec = {"v": 1, "kind": "route_saved", "route_id": rid, "schema_version": SCHEMA_VERSION,
           "name": name, "by": str(by), "at": _now_iso(), "status": "active",
           "steps": canon}

    jp = Path(JOURNAL_PATH)
    jp.parent.mkdir(parents=True, exist_ok=True)
    already = False
    if jp.exists():
        for line in jp.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("route_id") == rid:
                    already = True
                    break
            except Exception:
                continue
    if not already:
        with open(jp, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    con = _connect()
    try:
        _project(con, rec)
        con.commit()
    finally:
        con.close()
    return rid


def rebuild() -> int:
    """Replay the journal into the projection. The pin-P5 law: wiping eye.db loses nothing
    authored, because the journal is the truth and this is just re-derivation."""
    jp = Path(JOURNAL_PATH)
    if not jp.exists():
        return 0
    n = 0
    con = _connect()
    try:
        for line in jp.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("kind") == "route_saved":
                _project(con, rec)
                n += 1
            elif rec.get("kind") == "route_walked":
                # T335: walks replay too, or the docstring above is false for the one record
                # the organ produces by being used.
                _project_walk(con, rec)
                n += 1
        con.commit()
    finally:
        con.close()
    return n


def _resolve(step: Dict[str, Any]) -> str:
    """'current' when the target address resolves in the Eye's events table; 'dangling'
    otherwise -- WITH the last-known address preserved. Degradation is named, never
    silent, and never fatal (his sentence is the policy)."""
    target = str(step.get("target", ""))
    if ":" not in target:
        return "dangling"
    sess, _, line = target.rpartition(":")
    try:
        con = sqlite3.connect(str(DB_PATH))
        try:
            row = con.execute(
                "SELECT 1 FROM events WHERE session LIKE ? AND line=?",
                (sess + "%", int(line))).fetchone()
        finally:
            con.close()
        return "current" if row else "dangling"
    except Exception:
        return "dangling"


def _drill(step: Dict[str, Any]) -> Optional[str]:
    """T335: fetch a leg's BODY, which is what distinguishes reading a route from reading
    its table of contents. Returns the text, or None when the address does not resolve --
    and the None is the point: legs_drilled counts bodies obtained, never legs attempted."""
    target = str(step.get("target", ""))
    if ":" not in target:
        return None
    sess, _, line = target.rpartition(":")
    try:
        con = sqlite3.connect(str(DB_PATH))
        try:
            row = con.execute(
                "SELECT text FROM events WHERE session LIKE ? AND line=?",
                (sess + "%", int(line))).fetchone()
        finally:
            con.close()
        return row[0] if row else None
    except Exception:
        return None


def walk(name_or_id: str, *, resolve: bool = False, drill: bool = False,
         by: str = "") -> Dict[str, Any]:
    """Re-walk a saved string: steps in authored order, receipts attached, and (with
    resolve=True) each leg's resolution named. With drill=True each leg's BODY is read.

    T335 -- THE WALK IS NOW A RECORD, AND THE RECORD NAMES ITS DEPTH. Daniil's ruling: "I
    don't want our forest thread to lie to us and make traversal records be ambiguous." A
    bare walk_count could not tell a glance from a traversal, and the walk was never written
    to the journal at all, so the module's own lossless-rebuild law had a hole exactly the
    shape of its usage history.

    DEPTH IS DERIVED FROM THE EXECUTED PATH, NEVER PASSED IN. There is deliberately no
    `depth` parameter: a self-declared fidelity field is exactly as trustworthy as the
    number it replaced, and the whole point is that the record reports what actually ran.
        listed    the index was printed -- real, useful, and not a traversal
        resolved  every leg's ADDRESS was checked (current/dangling)
        drilled   every leg's BODY was read; legs_drilled counts the ones obtained
    """
    con = _connect()
    try:
        row = con.execute(
            "SELECT route_id, name, status, walk_count FROM routes "
            "WHERE name=? OR route_id=? ORDER BY at DESC LIMIT 1",
            (name_or_id, name_or_id)).fetchone()
        if not row:
            raise KeyError(f"no route named {name_or_id!r} -- `eye route ls` shows what "
                           "strings exist; `eye route save` ties a new one")
        rid, name, status, walk_count = row
        steps = []
        for (seq, sid, typ, target, receipt, note, is_not, outcome, sup) in con.execute(
                "SELECT seq, id, type, target, receipt, note, is_not, outcome, "
                "superseded_by FROM route_steps WHERE route_id=? ORDER BY seq", (rid,)):
            s = {"id": sid, "type": typ, "target": target, "receipt": receipt,
                 "note": note, "is_not": json.loads(is_not or "[]"),
                 "outcome": json.loads(outcome or "{}"), "superseded_by": sup}
            if resolve:
                s["resolution"] = _resolve(s)
            steps.append(s)
    finally:
        con.close()

    # The depth is whatever this call ACTUALLY did, computed after doing it.
    legs_drilled = 0
    if drill:
        for s in steps:
            body = _drill(s)
            if body is not None:
                s["body"] = body
                legs_drilled += 1
    depth = "drilled" if drill else ("resolved" if resolve else "listed")

    rec = {"v": 1, "kind": "route_walked", "walk_id": uuid.uuid4().hex[:16],
           "route_id": rid, "name": name, "at": _now_iso(), "by": str(by),
           "depth": depth, "legs_shown": len(steps), "legs_drilled": legs_drilled}

    # Journal FIRST, projection second -- the same ordering save() uses, and the reason a
    # wiped eye.db now loses no walk history either.
    jp = Path(JOURNAL_PATH)
    jp.parent.mkdir(parents=True, exist_ok=True)
    with open(jp, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    con = _connect()
    try:
        _project_walk(con, rec)
        con.commit()
    finally:
        con.close()

    # The walk reports its own honest tally. `walk_count` alone is the bare total this slice
    # exists to stop trusting, so it never travels without the breakdown beside it -- a count
    # without its scope is not a coverage claim, one organ over. This is also what makes
    # walks() reachable from the door every walk already comes through, rather than only from
    # a render that has not been written yet.
    return {"route_id": rid, "name": name, "status": status,
            "walk_count": walk_count + 1, "depth": depth,
            "legs_shown": len(steps), "legs_drilled": legs_drilled,
            "tally": walks(rid), "steps": steps}


def walks(name_or_id: str) -> Dict[str, Any]:
    """T335: the honest read side. Never a bare total -- a count without its scope is not a
    coverage claim, which is the frame this house already enforces on every other number.

    `unknown` is the walks the projection counted before walks were journaled. They had a
    real depth and nobody recorded it, so the only true answer is UNKNOWN. Backfilling them
    as 'listed' would be a guess wearing a measurement's clothes -- the T176 defect committed
    by the fix that closes it."""
    con = _connect()
    try:
        row = con.execute(
            "SELECT route_id, walk_count FROM routes WHERE name=? OR route_id=? "
            "ORDER BY at DESC LIMIT 1", (name_or_id, name_or_id)).fetchone()
        if not row:
            raise KeyError(f"no route named {name_or_id!r} -- `eye route ls` shows what "
                           "strings exist")
        rid, total = row
        records = [
            {"walk_id": w, "at": at, "by": by, "depth": d,
             "legs_shown": ls, "legs_drilled": ld}
            for (w, at, by, d, ls, ld) in con.execute(
                "SELECT walk_id, at, by, depth, legs_shown, legs_drilled FROM route_walks "
                "WHERE route_id=? ORDER BY at", (rid,))]
    finally:
        con.close()
    by_depth: Dict[str, int] = {}
    for r in records:
        by_depth[r["depth"]] = by_depth.get(r["depth"], 0) + 1
    return {"route_id": rid, "total": total, "by_depth": by_depth,
            "unknown": max(0, total - len(records)), "records": records}


def list_routes() -> List[Dict[str, Any]]:
    """The register: name, status, walks, step count -- the strings that exist."""
    con = _connect()
    try:
        rows = con.execute(
            "SELECT r.route_id, r.name, r.status, r.walk_count, r.by, r.at, "
            "COUNT(s.seq) FROM routes r LEFT JOIN route_steps s "
            "ON s.route_id = r.route_id GROUP BY r.route_id ORDER BY r.at").fetchall()
    finally:
        con.close()
    return [{"route_id": rid, "name": name, "status": status, "walk_count": wc,
             "by": by, "at": at, "steps": n}
            for rid, name, status, wc, by, at, n in rows]
