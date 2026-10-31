"""The two corpus walkers: the neighborhood map, and the rationale lookback.

Different questions over the same store, kept together so the contrast stays visible:
`knowledge-map` WALKS the edges the system already grows (surface hits, then the one-hop
neighborhood, then the retired archive), while `lookback` returns the layered WHY with a drill
pointer per hit. Flat relevance finds neither on its own.
"""
from __future__ import annotations

import json

from verbs.registry import verb


@verb(local=False, door_notes="CLI + ToolBox + MCP twin; core.recall.knowledge_map.")
def cmd_knowledge_map(args):
    """R8 (T059): WALK the knowledge neighborhood of a topic instead of querying it blind.
    lookback returns a flat ranked list; this returns a graph -- surface hits (L1), the
    one-hop neighborhood reached by WALKING the related_to edges the system already grows
    (L2, both directions), and the on-topic archive of retired/superseded records (L3).
    Each node carries a drill pointer; neighborhood nodes name the edge that reached them."""
    from core.recall.knowledge_map import knowledge_map
    topic = " ".join(args.query or []) if isinstance(args.query, list) else (args.query or "")
    topic = topic.strip()
    m = knowledge_map(topic, per_layer=args.per_layer or 6)
    if args.json:
        print(json.dumps(m, indent=2, default=str)); return 0
    if not topic:
        print("# knowledge-map: give a topic to walk (e.g. 'lanes', 'wedge', 'supersession')")
        return 0
    c = m["counts"]
    print(f"# KNOWLEDGE MAP: {topic}   "
          f"({c['surface']} surface | {c['neighborhood']} neighborhood | {c['archive']} archive)")
    if not (m["surface"] or m["neighborhood"] or m["archive"]):
        print("  (nothing above the relevance floor -- try different terms)")
        return 0

    def _row(n, indent="  "):
        edge = f" +{n['edge_count']} edges" if n.get("edge_count") else ""
        rel = f" (rel {n['score']})" if n.get("score") is not None else ""
        print(f"{indent}[{n['kind']}:{n['status']}] {n['title']}{rel}{edge}")
        if n.get("via"):
            v = n["via"]
            arrow = "<--" if v["direction"] == "in" else "-->"
            matched = f" [{','.join(v['matched'])}]" if v.get("matched") else ""
            print(f"{indent}    via {v['from']} {arrow}{matched}")
        print(f"{indent}    {n['excerpt']}")
        print(f"{indent}    drill: {n['drill']}")

    if m["surface"]:
        print("\n## L1 surface -- direct topic hits")
        for n in m["surface"]:
            _row(n)
    if m["neighborhood"]:
        print("\n## L2 neighborhood -- one hop along the edges (relevance alone can't reach these)")
        for n in m["neighborhood"]:
            _row(n)
    if m["archive"]:
        print("\n## L3 archive -- on topic but retired/superseded (reachable, not live)")
        for n in m["archive"]:
            _row(n)
    return 0


@verb(local=False, door_notes="CLI; core.recall.lookback. Named in core/coord/capability_search as a pointer target.")
def cmd_lookback(args):
    """P7 (T027): one question over the rationale corpus -- the strategic WHY, layered and
    drillable. Temporal drill (story/events) answers what happened; this answers why it is
    the way it is: docs (currency-labeled) -> research/reviewed -> notes (incl. retired) ->
    promoted bus -> chapters -> git bodies, each hit with its drill pointer."""
    from core.recall.lookback import lookback
    question = " ".join(args.question or [])
    layers = [s.strip() for s in (args.layers or "").split(",") if s.strip()] or None
    hits = lookback(question, per_layer=args.per_layer or 3, layers=layers)
    if args.json:
        print(json.dumps(hits, indent=2, default=str)); return 0
    if not hits:
        print(f"# lookback: nothing above the relevance floor for: {question!r}\n"
              "  (try different terms; layers: docs,research,notes,promoted,chapters,git)")
        return 0
    print(f"# lookback: {question}")
    current_layer = None
    for h in hits:
        if h["layer"] != current_layer:
            current_layer = h["layer"]
            print(f"\n## {current_layer}")
        # Headline number = the SORT KEY, so position and figure agree; relevance beside it, named,
        # because it is the one that says why the row matched. Printing only the component used to
        # make a correctly-ordered list look unsorted (measured 0.382, 0.215, 0.248 in one layer).
        _rel = h.get("relevance")
        _why = f", rel {_rel}" if _rel is not None and _rel != h.get("score") else ""
        print(f"  [{h['status']}] {h['source']}  (rank {h['score']}{_why})")
        print(f"      {h['excerpt']}")
        print(f"      drill: {h['drill']}")
    return 0
