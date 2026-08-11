"""THE EYE S2 -- the pyramid: LOD as regenerable projection, fidelity by construction.

The fence's hardest ruling (design atom the-eye-design-v2_208b26, r1 C2/C5): a stale
summary is honest fog; a LYING summary is invisible poison. This module's answer is
structural -- summaries are EXTRACTIVE-ONLY:

  - L1 (exchange) text = the opening operator sentence + the first agent sentence,
    verbatim, drawn from events the node's refs anchor. NO LLM in the path.
  - L2 (session digest) text = the session's operator opening sentences, verbatim.
  - refs are the event_ids themselves; descent is citation-following, never re-search.
  - reads carry is_stale (events newer than built_at) -- fog, never silence.

An exchange = one operator turn + everything until the next operator turn (the grouping
law: every exchange opens with the operator's voice). Levels above L2 (arc/era) ride the
narrative spine and land in a later slice.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.eye.index import _connect, get_event


def _first_sentence(text: str, cap: int = 220) -> str:
    t = " ".join(text.split())
    if len(t) <= cap:
        return t
    head = t[:cap]
    m = max(head.rfind(". "), head.rfind("? "), head.rfind("! "))
    if m > cap * 0.35:
        return head[:m + 1]
    return head[:head.rfind(" ")] + " …"


def _ensure_schema(con) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS pyramid(
        node_id TEXT PRIMARY KEY, level TEXT NOT NULL, session TEXT NOT NULL,
        seq INTEGER NOT NULL, text TEXT NOT NULL, refs TEXT NOT NULL,
        built_at REAL NOT NULL, tokens INTEGER NOT NULL)""")


def build(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """(Re)build L1+L2 for every session. Extractive, deterministic, cheap enough to be
    wholesale at this corpus scale (the incremental refinement rides a later slice --
    stated, not silent)."""
    con = _connect(db_path)
    _ensure_schema(con)
    now = time.time()
    built_l1 = built_l2 = 0
    try:
        sessions = [r[0] for r in con.execute(
            "SELECT DISTINCT session FROM events").fetchall()]
        con.execute("DELETE FROM pyramid")
        for s in sessions:
            evs = [{"event_id": r[0], "voice": r[1], "text": r[2], "tokens": r[3]}
                   for r in con.execute(
                       "SELECT event_id, voice, text, tokens FROM events "
                       "WHERE session=? ORDER BY line", (s,)).fetchall()]
            # Group into exchanges. An exchange = a run of operator turn(s) + the replies
            # until the NEXT operator run. A new exchange opens on an operator event ONLY
            # after an agent has replied -- because the harness records one operator turn
            # TWICE (the queue-operation enqueue + the user record, identical text), and
            # consecutive operator events are one moment, not two exchanges. Caught live on
            # this very session, 2026-08-11; the fixture below pins the duplicate pattern.
            exchanges: List[List[Dict[str, Any]]] = []
            cur: List[Dict[str, Any]] = []
            seen_agent = False
            for e in evs:
                if e["voice"] == "operator":
                    if cur and seen_agent:
                        exchanges.append(cur)
                        cur, seen_agent = [], False
                    cur.append(e)
                else:
                    if cur:
                        cur.append(e)
                        if e["voice"] == "agent":
                            seen_agent = True
                    # leading non-operator events before the first operator turn are
                    # ambient -- they ride the digest via counts, not an exchange
            if cur and any(x["voice"] == "operator" for x in cur):
                exchanges.append(cur)

            child_ids = []
            for i, ex in enumerate(exchanges, start=1):
                op = next(e for e in ex if e["voice"] == "operator")
                agent = next((e for e in ex if e["voice"] == "agent"), None)
                text = _first_sentence(op["text"])
                if agent:
                    text += " -> " + _first_sentence(agent["text"], cap=140)
                refs = [e["event_id"] for e in ex]
                nid = f"{s}/L1:{i:03d}"
                con.execute(
                    "INSERT INTO pyramid(node_id, level, session, seq, text, refs, "
                    "built_at, tokens) VALUES(?,?,?,?,?,?,?,?)",
                    (nid, "L1", s, i, text, json.dumps(refs), now,
                     max(1, len(text) // 4)))
                child_ids.append(nid)
                built_l1 += 1

            # One opener per exchange, deduped -- the same utterance recorded as queue-op
            # AND user must not appear twice in the digest.
            op_openers, _last = [], None
            for ex in exchanges:
                op = next(e for e in ex if e["voice"] == "operator")
                line = _first_sentence(op["text"], cap=160)
                norm = " ".join(line.lower().split())[:80]
                if norm != _last:
                    op_openers.append(line)
                    _last = norm
            op_openers = op_openers[:8]
            digest = " · ".join(op_openers) if op_openers else "(no operator turns)"
            all_refs = [e["event_id"] for e in evs]
            con.execute(
                "INSERT INTO pyramid(node_id, level, session, seq, text, refs, built_at, "
                "tokens) VALUES(?,?,?,?,?,?,?,?)",
                (f"{s}/L2", "L2", s, 0, digest,
                 json.dumps(all_refs[:50]), now, max(1, len(digest) // 4)))
            built_l2 += 1
        con.commit()
    finally:
        con.close()
    return {"sessions": len(sessions), "l1_nodes": built_l1, "l2_nodes": built_l2,
            "built_at": round(now, 2)}


def nodes(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        rows = con.execute("SELECT node_id, level, session, seq, text, refs, built_at, "
                           "tokens FROM pyramid ORDER BY session, level, seq").fetchall()
    finally:
        con.close()
    return [{"node_id": r[0], "level": r[1], "session": r[2], "seq": r[3], "text": r[4],
             "refs": json.loads(r[5]), "built_at": r[6], "tokens": r[7]} for r in rows]


def zoom(addr: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """LOD navigation: a session name -> its L2 digest (+ child L1 ids); an L1 node id ->
    the exchange (+ event refs). Every read carries is_stale -- fog, never silence."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        node_id = addr if "/L" in addr else f"{addr}/L2"
        r = con.execute("SELECT node_id, level, session, seq, text, refs, built_at, "
                        "tokens FROM pyramid WHERE node_id=?", (node_id,)).fetchone()
        if not r:
            raise ValueError(
                f"no pyramid node at {addr!r} -- zoom takes a session name or an L1 id "
                f"(<session>/L1:NNN); build with the eye door first if the pyramid is empty")
        # staleness: any event in this session the build never saw (fog, never silence)
        stale_row = con.execute(
            "SELECT COUNT(*) FROM events WHERE session=? AND (ts IS NULL OR ts > ?) "
            "AND event_id NOT IN (SELECT value FROM json_each(?))",
            (r[2], r[6], r[5])).fetchone()
        children = []
        if r[1] == "L2":
            children = [x[0] for x in con.execute(
                "SELECT node_id FROM pyramid WHERE session=? AND level='L1' "
                "ORDER BY node_id", (r[2],)).fetchall()]
    finally:
        con.close()
    return {"node_id": r[0], "level": r[1], "session": r[2], "text": r[4],
            "refs": json.loads(r[5]), "built_at": r[6], "tokens": r[7],
            "children": children, "is_stale": bool(stale_row and stale_row[0])}
