"""knowledge_map (R8 / T059) -- WALK the knowledge, don't query it blind.

`lookback` answers "what is the best flat hit for this question" -- a ranked list across
the rationale corpora. `knowledge_map` answers a different question: "what is the
NEIGHBORHOOD around this topic", rendered as a walkable graph, so an agent or Daniel can
follow the edges the system ALREADY grows instead of re-querying at every step.

The self-organizing layer exists; it just had no face:
  - lessons grow `related_to` edges at capture time (learning_store.mark_related), stored
    one-directional new->existing on the new record as JSON;
  - notes supersede (agent_memory: superseded flag);
  - docs declare currency (Status: current | superseded | historical).

Three layers, the cache hierarchy from claude's B5 sketch (L1 surface / L2 neighborhood /
L3 archive):
  surface       -- the direct topic hits, current only (you-are-here);
  neighborhood  -- lessons reached by WALKING the related_to edges from the surface, BOTH
                   directions (the edge is one-way on disk, so traversal must go both ways
                   or half the neighborhood is invisible). This is the payoff relevance
                   alone cannot produce: an edge-only lesson has zero topic relevance yet
                   is one hop from the answer;
  archive       -- retired notes / superseded|historical docs / benched|graduated lessons
                   still on topic (dead law stays REACHABLE but never reads as live).

Zero new storage: every edge is read from where it already lives. Deterministic, no LLM,
fail-soft per corpus (a broken corpus drops out; the map never bricks). Corpus adapters
for notes and docs are reused verbatim from lookback -- one projection, two faces.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from core.recall.lookback import (
    MIN_RELEVANCE, _build_idf_relevance, _stem_relevance, _match_excerpt,
    _docs_items, _note_items,
)

# statuses that mean "on topic but not live": routed to the archive layer, off the surface
ARCHIVE_STATUS = {"retired", "superseded", "historical", "benched", "graduated"}
PER_LAYER = 6


def _safe(fn: Callable[[], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    try:
        return fn() or []
    except Exception:
        return []


# ---------------------------------------------------------------- corpus adapter (lessons)
def _lesson_status(rec: Dict[str, Any]) -> str:
    """current | benched | graduated. The store's predicates own the field contract --
    benched/graduated hold ISO timestamps when set, so only is_benched/is_graduated may
    read them (a truthy-string compare reads every timestamp as false)."""
    from core.learning.learning_store import is_benched, is_graduated
    if is_benched(rec):
        return "benched"
    if is_graduated(rec):
        return "graduated"
    return "current"


def _lesson_items() -> List[Dict[str, Any]]:
    """Every lesson as a graph node carrying its related_to edges. Notes and docs come from
    lookback's adapters unchanged; lessons need the edge projection, which is ours."""
    from core.learning.learning_store import get_learning_store
    out: List[Dict[str, Any]] = []
    for rec in get_learning_store().load_all_learnings_from_store():
        name = str(rec.get("experiment_name") or "").strip()
        if not name:
            continue
        try:
            raw = json.loads(rec.get("related_to") or "[]")
        except Exception:
            raw = []
        edges = [{"to": e.get("experiment_name"), "type": "related_to", "matched": e.get("matched")}
                 for e in raw if isinstance(e, dict) and e.get("experiment_name")]
        status = _lesson_status(rec)
        text = "\n".join(str(rec.get(k, "")) for k in
                         ("experiment_name", "recommendation", "actual", "root_cause",
                          "what_tried", "category") if rec.get(k))
        out.append({"kind": "lesson", "id": name, "text": text,
                    "source": rec.get("source") or f"learn:experiment:{name}",
                    "timestamp": rec.get("timestamp", ""),
                    "importance": 1 if status != "current" else 3,
                    "status": status,
                    "drill": f"recall --full learn:experiment:{name}",
                    "edges": edges})
    return out


# ---------------------------------------------------------------- node projection
def _node(item: Dict[str, Any], kind: str, score: Optional[float], q: str) -> Dict[str, Any]:
    text = str(item.get("text", ""))
    title = (item.get("id") or (text.split("\n", 1)[0] if text else "") or
             item.get("source", "")).strip()[:80]
    return {"kind": kind,
            "id": item.get("id") or item.get("source", ""),
            "title": title,
            "source": item.get("source", ""),
            "status": item.get("status", "current"),
            "score": score,
            "excerpt": _match_excerpt(text, q) if (q and text) else text[:180],
            "drill": item.get("drill") or item.get("source", ""),
            "edge_count": len(item.get("edges") or [])}


# ---------------------------------------------------------------- the walk (pure, testable)
def build_map(topic: str, lessons: List[Dict[str, Any]], notes: List[Dict[str, Any]],
              docs: List[Dict[str, Any]], *, per_layer: int = PER_LAYER,
              min_relevance: float = MIN_RELEVANCE,
              relevance_fn: Optional[Callable[[str, str], float]] = None,
              now: Optional[float] = None) -> Dict[str, Any]:
    """Walk the neighborhood of `topic` over already-loaded corpus item lists.

    Returns {topic, surface[], neighborhood[], archive[], counts{}}. Each node:
    {kind, id, title, source, status, score, excerpt, drill, edge_count}; neighborhood
    nodes add `via` = {from, type, direction(in|out), matched}. Pure: the loader
    (`knowledge_map`) supplies the lists, so the graph logic is unit-testable in isolation."""
    q = (topic or "").strip()
    empty = {"topic": q, "surface": [], "neighborhood": [], "archive": [],
             "counts": {"surface": 0, "neighborhood": 0, "archive": 0}}
    if not q:
        return empty

    lessons = lessons or []
    notes = notes or []
    docs = docs or []
    lesson_by_id = {l.get("id"): l for l in lessons if l.get("id")}

    from core.primitives.ranker import Ranker
    if relevance_fn is None:
        try:
            relevance_fn = _build_idf_relevance(
                [str(i.get("text", "")) for i in (lessons + notes + docs)])
        except Exception:
            relevance_fn = _stem_relevance
    ranker = Ranker(relevance_fn=relevance_fn)

    # L1 surface (current) + L3 archive (on-topic but retired), split by currency.
    surface: List[Dict[str, Any]] = []
    archive: List[Dict[str, Any]] = []
    for items, kind in ((lessons, "lesson"), (notes, "note"), (docs, "doc")):
        kept = 0
        arch_kept = 0
        for sc in ranker.rank(items, query=q, now=now):
            relv = sc.components.get("relevance", 0.0)
            if relv < min_relevance:
                continue
            node = _node(sc.item, kind, round(relv, 3), q)
            if node["status"] in ARCHIVE_STATUS:
                if arch_kept < per_layer:
                    archive.append(node)
                    arch_kept += 1
                continue
            if kept < per_layer:
                surface.append(node)
                kept += 1
    surface_ids = {n["id"] for n in surface}
    # rank order, never set order: which neighbors survive the cap below must be a
    # function of the graph, not of per-process string hashing
    surface_lesson_order = [n["id"] for n in surface if n["kind"] == "lesson"]
    surface_lesson_ids = set(surface_lesson_order)
    surface_rank = {sid: i for i, sid in enumerate(surface_lesson_order)}

    # L2 neighborhood: WALK the related_to edges from the surface lessons, both directions.
    neighborhood: List[Dict[str, Any]] = []
    seen = set(surface_ids)

    def _add(rec: Dict[str, Any], frm: str, edge: Dict[str, Any], direction: str) -> None:
        node = _node(rec, "lesson", None, q)
        node["via"] = {"from": frm, "type": edge.get("type", "related_to"),
                       "direction": direction, "matched": edge.get("matched")}
        neighborhood.append(node)
        seen.add(node["id"])

    for sid in surface_lesson_order:                           # forward: surface -> edge -> B
        for e in (lesson_by_id.get(sid, {}).get("edges") or []):
            bid = e.get("to")
            if bid and bid not in seen and bid in lesson_by_id:
                _add(lesson_by_id[bid], sid, e, "out")
    rev = []                                                   # reverse: A -> edge -> surface
    for rec in lessons:
        aid = rec.get("id")
        if not aid or aid in seen:
            continue
        for e in (rec.get("edges") or []):
            if e.get("to") in surface_lesson_ids:
                rev.append((surface_rank[e.get("to")], str(aid), rec, e))
                break
    # reverse arrivals ordered by their surface target's rank, then id -- input list
    # order must never decide who survives the truncation two lines down
    for _, _, rec, e in sorted(rev, key=lambda t: (t[0], t[1])):
        _add(rec, e.get("to"), e, "in")
    neighborhood = neighborhood[:per_layer * 2]

    return {"topic": q, "surface": surface, "neighborhood": neighborhood, "archive": archive,
            "counts": {"surface": len(surface), "neighborhood": len(neighborhood),
                       "archive": len(archive)}}


# ---------------------------------------------------------------- the loader (live corpora)
def knowledge_map(topic: str, *, per_layer: int = PER_LAYER,
                  min_relevance: float = MIN_RELEVANCE,
                  now: Optional[float] = None) -> Dict[str, Any]:
    """Walk the LIVE knowledge neighborhood of `topic`. Loads lessons (with edges), notes,
    and docs fail-soft, then delegates to `build_map`. Accrues a per-topic funnel count so
    the next audit of this surface has numbers, not anecdotes (the lookback pattern)."""
    lessons = _safe(_lesson_items)
    notes = _safe(_note_items)
    docs = _safe(_docs_items)
    m = build_map(topic, lessons, notes, docs, per_layer=per_layer,
                  min_relevance=min_relevance, now=now)
    _count(m)
    return m


def _count(m: Dict[str, Any]) -> None:
    """Best-effort funnel: queries + total nodes walked. Kill switch AKASHIC_KMAP_NO_COUNT=1."""
    if os.environ.get("AKASHIC_KMAP_NO_COUNT") == "1":
        return
    try:
        from core.foundation.store import create_store
        st = create_store(prefer_redis=True)
        c = m.get("counts", {})
        nodes = c.get("surface", 0) + c.get("neighborhood", 0) + c.get("archive", 0)

        def bump(key, by):
            try:
                st.set(key, str(int(st.get(key) or 0) + by))
            except Exception:
                pass
        bump("knowledge_map:queries", 1)
        if nodes:
            bump("knowledge_map:nodes", nodes)
    except Exception:
        pass
