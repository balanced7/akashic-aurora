"""THE EYE S4 -- the connectome: edges that remember their own formation.

The stance (atom idea-connectome-stance_fa0131): ideas spread through this system as
RECEIPTED EDGES, not opaque weight updates. "Every synapse remembers its own formation,
and the connectome is scrubbable through time." The mechanical delta that stance costs is
three fields on the edge contract -- `formed_by`, `formed_at`, `formed_via` (query grammar
sec 5) -- and this module is where they first become real.

WHAT THE TRANSCRIPT PLANE ACTUALLY OFFERS, measured before this was written (8 live
sessions, 2026-08-11):

    record type    uuid/parentUuid
    assistant      3629 / 3629
    user           1913 / 1913
    attachment     1299 / 1299
    system          144 / 144
    queue-operation    0 / 398      <-- where the operator's queued voice lives

The harness records a causal chain for every voice EXCEPT the one this organ was built to
protect. So the chain alone cannot carry his speech, and three edge kinds are needed --
each with a different EVIDENCE GRADE, which is the honesty this module turns on:

  follows        parent -> child, from parentUuid          evidence: RECORDED
  same_utterance records of ONE utterance, by text identity evidence: DERIVED
  adjacent       an orphan pinned to the nearest chained    evidence: INFERRED
                 event by position

`recorded` is the harness's own bookkeeping. `derived` is computed from record CONTENT and
is exact (identical text in one session is the same utterance -- the enqueue/dequeue pair
plus the delivered twin). `inferred` is a GUESS from position, and it is the only handhold
the 21.4% of his queued utterances that never became a `user` record will ever have.
A walk that crosses an inferred edge sets `degraded` and names it. An inference laundered
as a record is precisely the class THE EYE exists to refuse.

THE UTTERANCE SET is the reusable payload. An utterance is not a row -- it is the SET of
records carrying it. S2's pyramid learned that inline for its digests; `eye freq` had not,
and counted records as if they were utterances, inflating its verdicts across its own
threshold. Both now read the set from here, so the law lives in one place
(convergent_fixes_describe_meaning_not_location_or_membership).

The edge table is part of the same rebuildable projection as the index (state/eye/eye.db):
never committed, reconstructible from source at any time.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.eye.index import _connect, get_event

# The grammar's vocabulary (sec 5) is `fence | recall-firing | fan | supersession | manual`
# -- minted for edges formed by MINDS reasoning. The transcript plane forms edges by three
# other routes, and naming them beats leaving them blank: absence must keep meaning exactly
# one thing (pre-contract). Filed as a divergence for ratification at the next gate, per the
# anti-fossil license -- the forms are a floor, and an unnamed edge would be a fossil.
FORMED_VIA: Tuple[str, ...] = (
    # grammar sec 5, verbatim
    "fence", "recall-firing", "fan", "supersession", "manual",
    # this plane's additions -- each states the EVIDENCE it rests on
    "transcript",     # the harness wrote the link down       -> recorded
    "text-identity",  # computed from record content, exact   -> derived
    "adjacency",      # guessed from position                 -> inferred
)

_EVIDENCE_OF: Dict[str, str] = {
    "transcript": "recorded",
    "text-identity": "derived",
    "adjacency": "inferred",
    "fence": "recorded", "recall-firing": "recorded", "fan": "recorded",
    "supersession": "recorded", "manual": "recorded",
}

_INDEXER = "eye-indexer"   # this module, when IT computes an edge
_HARNESS = "harness"       # the recorder, when the link was already in the data


def _ensure_schema(con) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS edges(
        src TEXT NOT NULL, dst TEXT NOT NULL, edge_kind TEXT NOT NULL,
        formed_by TEXT, formed_at REAL, formed_via TEXT, evidence TEXT,
        hops INTEGER,
        PRIMARY KEY(src, dst, edge_kind))""")
    con.execute("CREATE INDEX IF NOT EXISTS edges_src ON edges(src)")
    con.execute("CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst)")


def _norm(text: str) -> str:
    return " ".join((text or "").split())


# ---------------------------------------------------------------- build
def build(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """(Re)build the edge table from the indexed events. Idempotent by construction: the
    table is dropped and rewritten, and the primary key would collapse a duplicate anyway.

    Cheap enough to be wholesale at this corpus scale; the incremental refinement rides a
    later slice -- stated, not silent."""
    con = _connect(db_path)
    _ensure_schema(con)
    now = time.time()
    try:
        con.execute("DELETE FROM edges")
        sessions = [r[0] for r in con.execute(
            "SELECT DISTINCT session FROM events").fetchall()]
        for s in sessions:
            rows = con.execute(
                "SELECT event_id, line, uuid, parent_uuid, voice, type, text, ts "
                "FROM events WHERE session=? ORDER BY line", (s,)).fetchall()
            evs = [{"event_id": r[0], "line": r[1], "uuid": r[2], "parent": r[3],
                    "voice": r[4], "type": r[5], "text": r[6], "ts": r[7]} for r in rows]

            # (1) follows -- the recorded chain. The harness formed this link, not us.
            #
            # Resolved TRANSITIVELY through the raw chain. A record's parent is usually a
            # tool call or tool result: a real link the harness wrote down, carrying no
            # text and so holding no event of its own. Stopping at the first unindexed
            # parent left 93.8% of links dangling (14,983 parents, 927 resolving) and made
            # the walk dead-end one hop from wherever it started. So we climb the raw
            # chain until we reach a record that DID become an event, and record how many
            # silent records we passed -- every hop is the harness's own bookkeeping, so
            # the edge stays RECORDED; `hops` is what makes the compression visible.
            by_uuid = {e["uuid"]: e for e in evs if e["uuid"]}
            raw = dict(con.execute(
                "SELECT uuid, parent_uuid FROM chain WHERE session=?", (s,)).fetchall())
            chained: Set[str] = set()
            for e in evs:
                cur_uuid, hops = e["parent"], 1
                seen_uuids: Set[str] = set()
                while cur_uuid and cur_uuid not in by_uuid and cur_uuid not in seen_uuids:
                    seen_uuids.add(cur_uuid)
                    cur_uuid = raw.get(cur_uuid)
                    hops += 1
                par = by_uuid.get(cur_uuid or "")
                if par is None or par["event_id"] == e["event_id"]:
                    continue
                con.execute(
                    "INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?,?)",
                    (e["event_id"], par["event_id"], "follows",
                     _HARNESS, e["ts"] if e["ts"] is not None else now,
                     "transcript", "recorded", hops))
                chained.add(e["event_id"])
                chained.add(par["event_id"])

            # (2) same_utterance -- one utterance, N records, joined by exact text.
            # Scoped to a session: identical text in two sessions is two utterances (that
            # is exactly what `freq` measures across sessions, and conflating them would
            # destroy the axis).
            groups: Dict[str, List[Dict[str, Any]]] = {}
            for e in evs:
                if e["voice"] != "operator":
                    continue          # the duplicate-recording law is an operator-lane fact
                groups.setdefault(_norm(e["text"]), []).append(e)
            for members in groups.values():
                if len(members) < 2:
                    continue
                anchor = members[0]
                for m in members[1:]:
                    con.execute(
                        "INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?,?)",
                        (m["event_id"], anchor["event_id"], "same_utterance",
                         _INDEXER, m["ts"] if m["ts"] is not None else now,
                         "text-identity", "derived", 1))

            # (3) adjacent -- the orphan's only handhold. An operator utterance with no
            # uuid AND no twin in the chain would otherwise be unreachable from any walk:
            # the founding wound, reproduced inside the organ built to close it. So it is
            # pinned to the nearest PRECEDING chained event and marked INFERRED, forever.
            reachable = set(chained)
            for members in groups.values():
                if any(m["event_id"] in chained for m in members):
                    reachable.update(m["event_id"] for m in members)
            for members in groups.values():
                # ONE utterance gets ONE handhold, on its earliest record: the rest of the
                # set is already joined by same_utterance, so a guess per duplicate record
                # would multiply the same guess and inflate every inferred-edge count that
                # reads it.
                anchor = members[0]
                if anchor["event_id"] in reachable:
                    continue
                prior = [x for x in evs
                         if x["line"] < anchor["line"] and x["event_id"] in chained]
                if not prior:
                    continue          # nothing to pin to -- an edge would be invention
                con.execute(
                    "INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?,?)",
                    (anchor["event_id"], prior[-1]["event_id"], "adjacent",
                     _INDEXER, anchor["ts"] if anchor["ts"] is not None else now,
                     "adjacency", "inferred", 1))
        con.commit()
        by_kind = dict(con.execute(
            "SELECT edge_kind, COUNT(*) FROM edges GROUP BY edge_kind").fetchall())
        by_evidence = dict(con.execute(
            "SELECT evidence, COUNT(*) FROM edges GROUP BY evidence").fetchall())
        total = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    finally:
        con.close()
    return {"edges_total": int(total),
            "by_kind": {k: int(v) for k, v in by_kind.items()},
            "by_evidence": {k: int(v) for k, v in by_evidence.items()},
            "built_at": round(now, 2)}


def edges(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        rows = con.execute("SELECT src, dst, edge_kind, formed_by, formed_at, formed_via, "
                           "evidence, hops FROM edges ORDER BY src, edge_kind").fetchall()
    finally:
        con.close()
    return [{"src": r[0], "dst": r[1], "edge_kind": r[2], "formed_by": r[3],
             "formed_at": r[4], "formed_via": r[5], "evidence": r[6], "hops": r[7]}
            for r in rows]


def _insert_pre_contract_edge(src: str, dst: str, edge_kind: str,
                              db_path: Optional[Path] = None) -> None:
    """Test seam ONLY: an edge as it would exist from before the formation contract --
    no formed_by, no formed_at, no formed_via. Production never writes one of these; the
    exclusion trap (grammar sec 5 / fence r1 C4) exists precisely because history does."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        con.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,NULL,NULL,NULL,NULL,NULL)",
                    (src, dst, edge_kind))
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------- the utterance set
def utterance_group(event_id: str, db_path: Optional[Path] = None) -> List[str]:
    """Every record carrying the same utterance as this one, including itself.

    THE reusable primitive of this slice. A lone record returns a singleton -- never an
    empty list, because "this utterance has no records" is never true of a record."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        return _group(con, event_id)
    finally:
        con.close()


def _group(con, event_id: str) -> List[str]:
    """Connected component over same_utterance edges (undirected). Small by nature -- an
    utterance is recorded a handful of times, never thousands."""
    seen = {event_id}
    frontier = [event_id]
    while frontier:
        nxt = []
        for nid in frontier:
            for (other,) in con.execute(
                    "SELECT dst FROM edges WHERE src=? AND edge_kind='same_utterance' "
                    "UNION SELECT src FROM edges WHERE dst=? AND "
                    "edge_kind='same_utterance'", (nid, nid)).fetchall():
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
    return sorted(seen, key=lambda e: (e.rsplit(":", 1)[0], int(e.rsplit(":", 1)[1])
                                       if e.rsplit(":", 1)[-1].isdigit() else 0))


# ---------------------------------------------------------------- the walk
def _steps(con, node: str, up: bool) -> List[Dict[str, Any]]:
    """EVERY edge out of this node in the given direction. `follows` points child ->
    parent, so upstream reads src=node and downstream reads dst=node; `adjacent` rides the
    same direction carrying its inferred grade.

    Returns a LIST, not one row. A parent has many children, and a node can carry more
    than one edge of a kind (a pre-contract edge alongside a contracted one is exactly the
    case the exclusion trap is about). An earlier draft took fetchone() here and the
    fixture's linear chain hid it -- a single-parent shape cannot show you that you dropped
    the siblings (a green pin is evidence about the pin)."""
    q = ("SELECT dst, edge_kind, formed_by, formed_at, formed_via, evidence, hops "
         "FROM edges WHERE src=? AND edge_kind IN ('follows','adjacent') "
         "ORDER BY edge_kind, dst") if up else (
        "SELECT src, edge_kind, formed_by, formed_at, formed_via, evidence, hops "
        "FROM edges WHERE dst=? AND edge_kind IN ('follows','adjacent') "
        "ORDER BY edge_kind, src")
    return [{"event_id": r[0], "edge_kind": r[1], "formed_by": r[2], "formed_at": r[3],
             "formed_via": r[4], "evidence": r[5], "hops": r[6]}
            for r in con.execute(q, (node,))]


def trace(event_id: str, db_path: Optional[Path] = None, depth: int = 20,
          formed_via: Optional[str] = None) -> Dict[str, Any]:
    """The connectome walk: where did this come from, and what came after it.

    Upstream is the formation chain (nearest ancestor first); downstream is the
    descendants. A queue-op record with no uuid is walked through its utterance set --
    the twin is IN the chain, so his queued voice reaches the same ancestry his delivered
    voice does, by derivation rather than by guess. The bridge is named in the envelope
    (`bridged_via`) instead of being slipped into the ancestor list as if it were a hop.

    `formed_via=` filters the walk to edges formed that way. THE EXCLUSION TRAP (grammar
    sec 5, fence r1 C4): pre-contract edges -- those carrying no formation metadata --
    cannot be evaluated against such a filter, so they are counted and declared, never
    silently dropped and never backfilled with a sentinel."""
    con = _connect(db_path)
    _ensure_schema(con)
    try:
        node = get_event(event_id, db_path=db_path)
        if node is None:
            raise ValueError(
                f"no event at {event_id!r} -- the address is session:line; get one from "
                f"`eye find` (got 0 rows is NOT the answer to a bad address)")

        group = _group(con, event_id)

        # Walk from whichever record of THIS utterance is actually in the chain. A
        # queue-op record has no uuid of its own, so his queued voice reaches the chain
        # through its twin -- derivation, not inference. The hop is reported as
        # `bridged_via` rather than pushed into the ancestor list, because it is not a
        # step through time: it is the same moment, recorded again.
        start, bridged_via = event_id, None
        if not _steps(con, event_id, up=True):
            for other in group:
                if other != event_id and _steps(con, other, up=True):
                    start, bridged_via = other, other
                    break

        unevaluable: Set[Tuple[str, str, str]] = set()
        inferred = 0

        def walk(up: bool) -> List[Dict[str, Any]]:
            """Breadth-first, so nearest kin come first and a branching parent keeps all
            of its children. Bounded by `depth` NODES -- the corpus has long chains and an
            unbounded walk is a context bomb, not a sensorium."""
            nonlocal inferred
            out: List[Dict[str, Any]] = []
            guard, frontier = {start}, [start]
            while frontier and len(out) < max(1, int(depth)):
                nxt: List[str] = []
                for cur in frontier:
                    for step in _steps(con, cur, up=up):
                        if step["event_id"] in guard:
                            continue
                        if formed_via is not None and step["formed_via"] is None:
                            # Unevaluable against the filter -- counted and declared, never
                            # silently dropped, never backfilled with a sentinel.
                            unevaluable.add((cur, step["event_id"], step["edge_kind"]))
                            continue
                        guard.add(step["event_id"])
                        nxt.append(step["event_id"])
                        if formed_via is not None and step["formed_via"] != formed_via:
                            continue
                        if step["evidence"] == "inferred":
                            inferred += 1
                        ev = get_event(step["event_id"], db_path=db_path)
                        out.append({**step, "voice": ev["voice"] if ev else None,
                                    "line": ev["line"] if ev else None,
                                    "ts": ev["ts"] if ev else None,
                                    "snippet": (ev["text"][:160] if ev else "")})
                        if len(out) >= max(1, int(depth)):
                            break
                    if len(out) >= max(1, int(depth)):
                        break
                frontier = nxt
            return out

        upstream = walk(up=True)
        downstream = walk(up=False)
        pre_contract = len(unevaluable)
    finally:
        con.close()

    reasons = []
    if inferred:
        reasons.append(f"{inferred} inferred edge(s) crossed (adjacency, not a recorded "
                       f"link) -- this ancestry is a positional guess")
    if pre_contract:
        reasons.append(f"{pre_contract} pre-contract edge(s) carry no formation metadata "
                       f"and were unevaluable under formed_via={formed_via!r}")
    return {"node": node, "upstream": upstream, "downstream": downstream,
            "same_utterance": group, "bridged_via": bridged_via,
            "edges_inferred": inferred, "pre_contract_edges": pre_contract,
            "degraded": bool(reasons),
            "degraded_reason": ("; ".join(reasons) if reasons else None)}
