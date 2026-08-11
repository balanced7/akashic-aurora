"""THE EYE S6 -- position: the inhabitant loop.

S0-S5 gave the sensorium its senses. Senses without a standpoint are a search engine, not
a world: you can ask anything and you are nowhere. This module is the standpoint -- where a
seat IS, how it moves, what it sees from here, and what changed while it slept.

    eye go <addr>     move (the trail remembers where you came from)
    eye back          pop the trail
    eye look          the standpoint rendered: this node, its neighbours as silhouettes,
                      its exits, and heat as NUMBERS
    eye since         the ambient delta -- what arrived while I was away

THE KEY IS THE INCARNATION, NEVER THE AGENT (design atom the-eye-design-v2_208b26, fence
r1 C4). `claude` is not a standpoint; `claude#6ebe8686` is. Two live sessions of one agent
sharing a position clobber each other on every move, and worse, they poison `since=`: each
would report the other's travel as its own elapsed interval, which is precisely the reading
`since=` exists to give. This house has already paid for the general form of this law at
the consumer seat, the runner lock and the lane cursor; here it is applied before the bill
rather than after.

SUCCESSION IS AN ACT. A fresh incarnation reads None until it explicitly inherits, and the
inheritance is recorded on the row. A standpoint adopted silently is indistinguishable from
one you walked to yourself -- and then `since=` is measuring an interval that was never
yours.

Position lives in the same projection as the rest of the eye (state/eye/eye.db). It is the
one table here that is genuinely disposable: losing a bookmark costs a `go`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.eye.index import _connect, get_event
from core.eye.connectome import _steps, _group


def whoami(agent: str = "claude") -> str:
    """This seat's incarnation key: agent#sid8, the same derivation the bus uses so one
    incarnation means one thing fleet-wide. A seat with no session id in its environment
    gets '#local' -- named, so it can never be mistaken for a real incarnation."""
    sid = (os.environ.get("BIFROST_INCARNATION")
           or os.environ.get("CLAUDE_CODE_SESSION_ID") or "")
    return f"{agent}#{str(sid)[:8]}" if sid else f"{agent}#local"


def _ensure_schema(con) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS position(
        seat TEXT PRIMARY KEY, addr TEXT NOT NULL, trail TEXT NOT NULL,
        marked_at REAL NOT NULL, moved_at REAL NOT NULL, inherited_from TEXT)""")


def _row(con, seat: str) -> Optional[Dict[str, Any]]:
    r = con.execute("SELECT seat, addr, trail, marked_at, moved_at, inherited_from "
                    "FROM position WHERE seat=?", (seat,)).fetchone()
    if not r:
        return None
    return {"seat": r[0], "addr": r[1], "trail": json.loads(r[2]), "marked_at": r[3],
            "moved_at": r[4], "inherited_from": r[5]}


def where(seat: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """This seat's standpoint, or None. None means NO POSITION -- never a default root:
    a fabricated standpoint would make `since=` report an interval the seat never lived."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        return _row(con, seat)
    finally:
        con.close()


def go(seat: str, addr: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Move. The previous standpoint is pushed onto the trail so `back` can undo it.

    A move to an address that does not resolve REFUSES with the expected shape (the
    grammar's 422 rule) and leaves the seat exactly where it was -- a half-move is a
    position that lies about where you have been."""
    ev = get_event(addr, db_path=db_path)
    if ev is None:
        raise ValueError(
            f"cannot go to {addr!r} -- an address on this plane is session:line "
            f"(e.g. 2b1b8946-...:1955); get one from `eye find`. The seat has NOT moved.")
    con = _connect(db_path)
    _ensure_schema(con)
    now = time.time()
    try:
        cur = _row(con, seat)
        trail = (cur["trail"] + [cur["addr"]]) if cur else []
        con.execute(
            "INSERT INTO position(seat, addr, trail, marked_at, moved_at, inherited_from) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(seat) DO UPDATE SET addr=excluded.addr, "
            "trail=excluded.trail, moved_at=excluded.moved_at",
            (seat, addr, json.dumps(trail[-32:]), now, now,
             cur["inherited_from"] if cur else None))
        con.commit()
        return _row(con, seat)
    finally:
        con.close()


def back(seat: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Pop the trail. At the origin this is a no-op that SAYS it is one, rather than
    silently staying put and letting the caller believe it moved."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        cur = _row(con, seat)
        if cur is None:
            raise ValueError(
                f"{seat} has no position to go back from -- `eye go <addr>` first")
        if not cur["trail"]:
            return {**cur, "at_trail_origin": True}
        trail = list(cur["trail"])
        prev = trail.pop()
        con.execute("UPDATE position SET addr=?, trail=?, moved_at=? WHERE seat=?",
                    (prev, json.dumps(trail), time.time(), seat))
        con.commit()
        return {**_row(con, seat), "at_trail_origin": False}
    finally:
        con.close()


def inherit(seat: str, from_seat: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Succession, explicitly. The predecessor is left untouched -- being inherited FROM is
    not a move -- and the inheritor's row records where the standpoint came from, so a
    later `since=` can be read for what it is: an interval that began at the handover."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        src = _row(con, from_seat)
        if src is None:
            raise ValueError(
                f"{from_seat} has no position to inherit -- nothing to succeed to "
                f"(a virgin seat reads None by design, never a default root)")
        now = time.time()
        con.execute(
            "INSERT INTO position(seat, addr, trail, marked_at, moved_at, inherited_from) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(seat) DO UPDATE SET addr=excluded.addr, "
            "trail=excluded.trail, marked_at=excluded.marked_at, "
            "moved_at=excluded.moved_at, inherited_from=excluded.inherited_from",
            (seat, src["addr"], json.dumps(src["trail"]), now, now, from_seat))
        con.commit()
        return _row(con, seat)
    finally:
        con.close()


def look(seat: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """The standpoint rendered -- THE default verb, so it must stay cheap.

    Neighbours are SILHOUETTES (one clipped line each), never full bodies: the whole point
    of a level-of-detail world is that looking around costs a fraction of reading. Heat is
    NUMERIC (fence r1 C1) -- glow is something a UI may do with these numbers, never the
    channel the agent reads. And a gauge this plane cannot populate reads None, not 0: a
    zero is a measurement, and we have not made one."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        cur = _row(con, seat)
        if cur is None:
            raise ValueError(
                f"{seat} has no position -- `eye go <addr>` to take one "
                f"(a standpoint is never assumed for you)")
        node = get_event(cur["addr"], db_path=db_path)
        if node is None:
            raise ValueError(
                f"{seat} stands at {cur['addr']!r}, which no longer resolves -- the index "
                f"may have been rebuilt; `eye go` somewhere current")
        ups = _steps(con, cur["addr"], up=True)
        downs = _steps(con, cur["addr"], up=False)
        exits = [{"edge_kind": e["edge_kind"], "evidence": e["evidence"],
                  "to": e["event_id"], "direction": d}
                 for d, group in (("upstream", ups), ("downstream", downs))
                 for e in group]
        neighbors = []
        for e in (ups + downs)[:6]:
            ev = get_event(e["event_id"], db_path=db_path)
            if ev is None:
                continue
            neighbors.append({"event_id": e["event_id"], "voice": ev["voice"],
                              "edge_kind": e["edge_kind"], "evidence": e["evidence"],
                              "snippet": " ".join(ev["text"].split())[:160]})
        after = con.execute(
            "SELECT COUNT(*) FROM events WHERE session=? AND line > ?",
            (node["session"], node["line"])).fetchone()[0]
        group = _group(con, cur["addr"])
    finally:
        con.close()

    body = " ".join(node["text"].split())[:400]
    view = {
        "seat": seat, "addr": cur["addr"],
        "node": {"event_id": node["event_id"], "voice": node["voice"],
                 "type": node["type"], "session": node["session"],
                 "line": node["line"], "ts": node["ts"], "text": body},
        "same_utterance": group,
        "neighbors": neighbors, "exits": exits,
        "heat": {
            "staleness_s": (time.time() - node["ts"]) if node["ts"] else None,
            "session_events_after": int(after),
            # This plane has no funnel credit -- lessons do, transcript events do not.
            # UNKNOWN is the honest value; 0 would be a measurement we never made.
            "credit": None,
        },
        "inherited_from": cur["inherited_from"],
    }
    view["tokens"] = max(1, len(json.dumps(view)) // 4)
    return view


def since(seat: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """The ambient delta: what arrived while this seat was away.

    Anchored on THIS seat's mark, which is why the key is the incarnation. The mark moves
    only when the seat moves -- reading the delta does not consume it, so asking twice
    gives the same answer rather than silently zeroing what you have not acted on."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        cur = _row(con, seat)
        if cur is None:
            raise ValueError(
                f"{seat} has no position, so there is no interval to measure -- "
                f"`eye go <addr>` first")
        mark = cur["marked_at"]
        # KNOWN_AT, not world time (grammar sec 1). "What changed while I was away" asks what
        # became KNOWABLE in the interval -- a transcript written last week and ingested this
        # morning is new to every reader this morning. Measuring by the event's own timestamp
        # instead reports zero for exactly the arrivals a returning seat most needs to see.
        # NULL indexed_at is not a guess: it means the row predates the column, so it is
        # necessarily older than any mark takeable from now on, and is correctly excluded.
        added = con.execute("SELECT COUNT(*) FROM events WHERE indexed_at > ?",
                            (mark,)).fetchone()[0]
        sessions = con.execute("SELECT COUNT(DISTINCT session) FROM events "
                               "WHERE indexed_at > ?", (mark,)).fetchone()[0]
        operator = con.execute(
            "SELECT COUNT(*) FROM events WHERE indexed_at > ? AND voice='operator'",
            (mark,)).fetchone()[0]
        edges = con.execute(
            "SELECT COUNT(*) FROM edges WHERE formed_at > ?", (mark,)).fetchone()[0]
        # Events with no parseable ts cannot be placed in the interval AT ALL -- the same
        # unevaluable class `find` reports under as_of. Counted, and declared.
        fogged = con.execute("SELECT COUNT(*) FROM events WHERE ts IS NULL").fetchone()[0]
    finally:
        con.close()
    return {"seat": seat, "addr": cur["addr"], "since_ts": mark,
            "events_added": int(added), "sessions_touched": int(sessions),
            "operator_events": int(operator), "edges_formed": int(edges),
            "degraded": bool(fogged),
            "degraded_reason": (f"{fogged} event(s) carry no parseable timestamp and "
                                f"cannot be placed in or out of this interval"
                                if fogged else None)}
