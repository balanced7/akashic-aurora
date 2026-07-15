"""flow_trace (R3 / T054) -- the OTel-style waterfall over lanes: what HAPPENED, in causal
order, across which lanes -- the packet substrate's face.

`lookback` answers "why", `knowledge_map` answers "what is near" -- `flow_trace` answers
"what happened": which ask produced which answer, on which lane, how long the gap was,
and whether one logical message arrived MORE than once (the T066 double-delivery class,
live receipts 2026-07-14: event:events:raw:1784082287759-0 and 1784003725351-0).

No stamped flow id exists on the wire yet (T040 spec'd it, T046 lands it), so v1 DERIVES
flows from what envelopes already carry:
  - meta.answers  -> the causal edge (reply UNDER its ask; flow id = root message id,
                     OTel trace_id-shaped). When the wire gains a real `flow` field the
                     loader reads it first and this derivation becomes the fallback.
  - sha           -> duplicate collapse: the same logical message observed under two
                     stream ids / lanes renders as ONE node with copies=N -- the tracer
                     exposes double-delivery instead of amplifying it.
  - stream key    -> the lane label (work / sig / trace / legacy / broadcast).

Read-only: nothing here sends, consumes, or advances a cursor. Fail-soft per stream --
a broken stream drops out; the trace never bricks. Pure walk (`build_flows`) split from
the live loader (`flow_trace`), the knowledge_map precedent.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_WINDOW_MS = 6 * 60 * 60 * 1000     # 6h of traffic is a session's story
PER_STREAM_LIMIT = 400                     # bounded read per stream; the window trims harder
SNIPPET_CHARS = 72


def lane_of(stream_key: str) -> str:
    """Lane label from the stream key shape, tolerant of any '<namespace>:' prefix
    (drill namespaces like test-rb25:* keep their lane)."""
    rest = str(stream_key).split(":")[1:]
    head = rest[0] if rest else ""
    return {"work": "work", "sig": "sig", "trace": "trace",
            "inbox": "legacy", "broadcast": "broadcast"}.get(head, "unknown")


def _ms(eid: Any) -> int:
    try:
        return int(str(eid).split("-", 1)[0])
    except Exception:
        return 0


def _norm(e: Dict[str, Any]) -> Dict[str, Any]:
    """Defensive normalization -- malformed entries degrade, never crash (pin F5)."""
    meta = e.get("meta")
    if isinstance(meta, (bytes, str)):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    try:
        length = int(e.get("len") or 0)
    except Exception:
        length = 0
    return {"id": str(e.get("id", "")), "ms": _ms(e.get("id")),
            "lane": lane_of(e.get("stream", "")), "frm": str(e.get("frm", "?")),
            "to": str(e.get("to", "?")), "kind": str(e.get("kind", "?")),
            "meta": meta, "len": length, "sha": (str(e.get("sha")) if e.get("sha") else None),
            "snippet": str(e.get("content", "") or "")[:SNIPPET_CHARS]}


# ---------------------------------------------------------------- the walk (pure, testable)
def build_flows(entries: List[Dict[str, Any]], *,
                window_ms: int = DEFAULT_WINDOW_MS) -> Dict[str, Any]:
    """Group raw stream entries into causal flows.

    Returns {flows: [{flow, root, span_ms, nodes}], counts{}}. Each node:
    {id, ms, frm, to, kind, lanes[], copies, len, offset_ms, snippet, children[]}
    (+ answers_missing when the causal parent fell outside the window). Flow id =
    the root message id; roots newest-first; children by time; offsets vs the root."""
    norm = [_norm(e) for e in (entries or []) if e and e.get("id")]
    if not norm:
        return {"flows": [], "counts": {"flows": 0, "nodes": 0, "copies": 0,
                                        "dropped_by_window": 0}}
    newest = max(n["ms"] for n in norm)
    cutoff = newest - max(0, int(window_ms))
    kept = [n for n in norm if n["ms"] >= cutoff]
    dropped = len(norm) - len(kept)

    # Duplicate collapse: same content hash + same (frm,to,kind) = one logical message
    # observed N times. sha-less entries NEVER collapse (pin F5) -- no hash, no identity.
    nodes: List[Dict[str, Any]] = []
    by_key: Dict[Any, Dict[str, Any]] = {}
    id_map: Dict[str, Dict[str, Any]] = {}
    for n in sorted(kept, key=lambda x: x["ms"]):
        key = (n["sha"], n["frm"], n["to"], n["kind"]) if n["sha"] else object()
        node = by_key.get(key)
        if node is None:
            node = {"id": n["id"], "ms": n["ms"], "frm": n["frm"], "to": n["to"],
                    "kind": n["kind"], "lanes": [n["lane"]], "copies": 1, "len": n["len"],
                    "snippet": n["snippet"], "meta": n["meta"], "children": []}
            by_key[key] = node
            nodes.append(node)
        else:
            node["copies"] += 1
            if n["lane"] not in node["lanes"]:
                node["lanes"].append(n["lane"])
        id_map[n["id"]] = node          # ANY observed id resolves to the logical node

    # Causal linking via meta.answers. Guards: no self-link, parent must precede the
    # child in time (a later "parent" would cycle the tree -- treat as missing).
    roots: List[Dict[str, Any]] = []
    for node in nodes:
        ans = str(node["meta"].get("answers") or "")
        parent = id_map.get(ans) if ans else None
        if parent is not None and parent is not node and parent["ms"] <= node["ms"]:
            parent["children"].append(node)
        else:
            if ans and parent is None:
                node["answers_missing"] = ans
            roots.append(node)

    def _finish(node: Dict[str, Any], root_ms: int) -> int:
        node["offset_ms"] = node["ms"] - root_ms
        node["lanes"] = sorted(node["lanes"])
        node.pop("meta", None)
        node["children"].sort(key=lambda c: c["ms"])
        last = node["ms"]
        for c in node["children"]:
            last = max(last, _finish(c, root_ms))
        return last

    flows = []
    for r in sorted(roots, key=lambda x: x["ms"], reverse=True):
        span_end = _finish(r, r["ms"])
        count = _tree_size(r)
        flows.append({"flow": r["id"], "root": r, "span_ms": span_end - r["ms"],
                      "nodes": count})
    return {"flows": flows,
            "counts": {"flows": len(flows), "nodes": len(nodes),
                       "copies": len(kept), "dropped_by_window": dropped}}


def _tree_size(node: Dict[str, Any]) -> int:
    return 1 + sum(_tree_size(c) for c in node["children"])


# ---------------------------------------------------------------- the loader (live streams)
def flow_trace(agent: Optional[str] = None, *, window_ms: int = DEFAULT_WINDOW_MS,
               per_stream: int = PER_STREAM_LIMIT, namespace: Optional[str] = None,
               client: Any = None, skip_kinds: Optional[set] = None) -> Dict[str, Any]:
    """Scan the live lane streams (work + legacy inboxes, both broadcasts) and build
    flows. `agent` filters to flows touching that agent. `skip_kinds` (default: trace)
    drops narration chatter BEFORE the walk -- pre-lane trace copies in legacy inboxes
    would otherwise flood the render with singleton flows. Read-only; fail-soft per
    stream. Accrues a funnel count (the lookback pattern)."""
    from core.comm.bus import _connect, NS
    ns = namespace or os.environ.get("BIFROST_NAMESPACE", NS)
    r = client if client is not None else _connect()
    if r is None:
        return {"flows": [], "counts": {"flows": 0, "nodes": 0, "copies": 0,
                                        "dropped_by_window": 0}, "offline": True}
    dec = (lambda x: x.decode() if isinstance(x, bytes) else x)

    streams: List[str] = [f"{ns}:broadcast", f"{ns}:work:broadcast"]
    try:
        for pat in (f"{ns}:work:inbox:*", f"{ns}:inbox:*"):
            for k in r.scan_iter(match=pat, count=200):
                streams.append(dec(k))
    except Exception:
        pass

    skip = {"trace"} if skip_kinds is None else set(skip_kinds)
    entries: List[Dict[str, Any]] = []
    for s in dict.fromkeys(streams):            # order-preserving dedupe
        try:
            for eid, fields in r.xrevrange(s, count=per_stream):
                f = {dec(k): dec(v) for k, v in fields.items()}
                if str(f.get("kind", "")) in skip:
                    continue
                f["id"] = dec(eid)
                f["stream"] = s
                entries.append(f)
        except Exception:
            continue                             # a broken stream drops out, never bricks

    out = build_flows(entries, window_ms=window_ms)
    if agent:
        def _touches(node):
            return node["frm"] == agent or node["to"] == agent or \
                   any(_touches(c) for c in node["children"])
        out["flows"] = [f for f in out["flows"] if _touches(f["root"])]
        out["counts"]["flows"] = len(out["flows"])
    _count(out)
    return out


def _count(out: Dict[str, Any]) -> None:
    """Best-effort funnel: queries + flows rendered. Kill switch AKASHIC_FLOW_NO_COUNT=1."""
    if os.environ.get("AKASHIC_FLOW_NO_COUNT") == "1":
        return
    try:
        from core.foundation.store import create_store
        st = create_store(prefer_redis=True)

        def bump(key, by):
            try:
                st.set(key, str(int(st.get(key) or 0) + by))
            except Exception:
                pass
        bump("flow_trace:queries", 1)
        if out.get("counts", {}).get("flows"):
            bump("flow_trace:flows", out["counts"]["flows"])
    except Exception:
        pass
