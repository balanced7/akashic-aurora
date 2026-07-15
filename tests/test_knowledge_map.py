"""knowledge_map (R8 / T059) -- the WALK property, pre-registered.

lookback answers "best flat hit for this question". knowledge_map answers "what is the
NEIGHBORHOOD around this topic" by WALKING the edges the system already grows -- lesson
`related_to` lesson (learning_store.mark_related), note supersession, doc currency. The
kill condition, and the whole reason the feature is not lookback-rebranded, is this:

  a lesson reachable ONLY by an edge (zero topic relevance of its own) must still appear
  in the neighborhood.

If that fails, we shipped a second keyword search. The tests below pin it: the forward
walk, the reverse walk (edges persist one-directional new->existing, so the traversal
must go both ways to see the whole neighborhood), currency honesty (retired/superseded
records land in archive, never surface), and empty/robust inputs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.ranker import keyword_relevance
from core.recall.knowledge_map import build_map


def _lesson(name, text, edges=None, status="current"):
    return {"kind": "lesson", "id": name, "text": text,
            "source": f"learn:experiment:{name}", "timestamp": "2026-07-14T00:00:00",
            "importance": 1 if status == "benched" else 3, "status": status,
            "drill": f"recall --full learn:experiment:{name}",
            "edges": [{"to": t, "type": "related_to", "matched": ["problem", "root_cause"]}
                      for t in (edges or [])]}


def _note(nid, title, body, status="current"):
    return {"text": f"{title}\n{body}", "source": f"mem:decision:{nid}",
            "timestamp": "2026-07-14T00:00:00", "importance": 3 if status == "current" else 1,
            "layer": "notes", "status": status, "drill": f"notes --all (id {nid})"}


def _ids(nodes):
    return {n["id"] for n in nodes}


def test_forward_walk_reaches_edge_only_lesson():
    """A matches the topic; B is reachable ONLY via A's related_to edge (no 'wedge' in B).
    B must surface in the neighborhood with the edge annotated -- lookback could never do this."""
    a = _lesson("cursor_wedge_detect", "wedge detection for a stuck agent worker",
                edges=["launcher_singleton_lock"])
    b = _lesson("launcher_singleton_lock", "singleton lock TTL token per runner")
    m = build_map("wedge", [a, b], [], [], relevance_fn=keyword_relevance, min_relevance=0.01)

    assert "cursor_wedge_detect" in _ids(m["surface"]), "the topic hit must be on the surface"
    assert "launcher_singleton_lock" not in _ids(m["surface"]), \
        "B has zero topic relevance -- it must NOT reach the surface by ranking"
    nb = {n["id"]: n for n in m["neighborhood"]}
    assert "launcher_singleton_lock" in nb, "B must be WALKED to via the edge (the whole point)"
    via = nb["launcher_singleton_lock"]["via"]
    assert via["from"] == "cursor_wedge_detect" and via["type"] == "related_to" \
        and via["direction"] == "out", f"edge must be annotated out from A, got {via}"
    print("--- forward walk ---\n  edge-only lesson reached + annotated OK")


def test_reverse_walk_traverses_the_one_directional_edge():
    """Edges persist one-directional (new record -> existing). B matches the topic; A points
    AT B. Seeing A requires traversing the edge BACKWARD -- else half the neighborhood is invisible."""
    a = _lesson("cursor_wedge_detect", "wedge detection for a stuck agent worker",
                edges=["launcher_singleton_lock"])
    b = _lesson("launcher_singleton_lock", "singleton lock TTL token per runner")
    m = build_map("singleton", [a, b], [], [], relevance_fn=keyword_relevance, min_relevance=0.01)

    assert "launcher_singleton_lock" in _ids(m["surface"])
    nb = {n["id"]: n for n in m["neighborhood"]}
    assert "cursor_wedge_detect" in nb, "reverse edge must be traversed (new->existing is one-way on disk)"
    assert nb["cursor_wedge_detect"]["via"]["direction"] == "in", "reverse edge marked inbound"
    print("--- reverse walk ---\n  one-directional edge traversed backward OK")


def test_currency_honesty_retired_goes_to_archive():
    """Dead law must not read as live: a retired note on-topic lands in archive, never surface."""
    live = _note("n1", "bus lanes design", "lane roster work sig trace retention", status="current")
    dead = _note("n0", "bus lanes old plan", "lane roster work sig trace superseded", status="retired")
    m = build_map("lanes", [], [live, dead], [], relevance_fn=keyword_relevance, min_relevance=0.01)

    assert "mem:decision:n1" in _ids(m["surface"]), "the live note belongs on the surface"
    assert "mem:decision:n0" not in _ids(m["surface"]), "the retired note must NOT be on the surface"
    assert "mem:decision:n0" in _ids(m["archive"]), "the retired note belongs in the archive layer"
    print("--- currency honesty ---\n  retired note routed to archive, off the surface OK")


def test_adapter_status_contract_timestamps_not_booleans():
    """The store stamps benched/graduated with ISO TIMESTAMPS (mark_benched/mark_graduated),
    never booleans. The adapter must read them through the store's canonical predicates --
    a truthy-string compare read all four live benched lessons as current (2026-07-14)."""
    from core.recall.knowledge_map import _lesson_status, ARCHIVE_STATUS
    assert _lesson_status({"benched": "2026-07-08T05:38:53.822519"}) == "benched"
    assert _lesson_status({"graduated": "2026-07-12T10:00:00"}) == "graduated"
    assert _lesson_status({"benched": "", "graduated": ""}) == "current"
    assert {"benched", "graduated"} <= ARCHIVE_STATUS, \
        "both retirement flavors must route to the archive layer"
    print("--- adapter status contract ---\n  timestamp flags -> benched/graduated OK")


def test_benched_and_graduated_lessons_land_in_archive():
    """Graduation's contract (learning_store.is_graduated): out of recall SURFACES, in
    full-corpus queries. The map is a surface -- both flavors belong in L3, never L1."""
    live = _lesson("live_wedge", "wedge live guidance")
    ben = _lesson("old_wedge_bench", "wedge advice benched long ago", status="benched")
    grad = _lesson("wedge_rule_enforced", "wedge rule now enforced by a hook", status="graduated")
    m = build_map("wedge", [live, ben, grad], [], [], relevance_fn=keyword_relevance,
                  min_relevance=0.01)
    assert "live_wedge" in _ids(m["surface"])
    assert "old_wedge_bench" not in _ids(m["surface"]), "benched must not read as live"
    assert "wedge_rule_enforced" not in _ids(m["surface"]), "graduated must not read as live"
    assert {"old_wedge_bench", "wedge_rule_enforced"} <= _ids(m["archive"])
    print("--- retirement flavors ---\n  benched + graduated routed to archive OK")


def test_walk_is_input_order_invariant():
    """Which neighbors survive the cap must be a function of the GRAPH, not of set-iteration
    or input list order (PYTHONHASHSEED flipped the survivors across processes, 2026-07-14).
    Hub relevances are strictly distinct (1/3, 2/3, 3/3 query words -- keyword_relevance is
    fraction-of-query-words) so ranker TIE-break order is not what's tested here."""
    topic = "wedge lock runner"
    coverage = ["wedge only", "wedge lock pair", "wedge lock runner full"]
    lessons = []
    for s in range(3):
        targets = [f"leaf_{s}_{i}" for i in range(8)]
        lessons.append(_lesson(f"hub_{s}", coverage[s] + f" pattern {s}", edges=targets))
        lessons += [_lesson(t, f"unrelated payload {t}") for t in targets]
    a = build_map(topic, lessons, [], [], relevance_fn=keyword_relevance, min_relevance=0.01)
    b = build_map(topic, list(reversed(lessons)), [], [], relevance_fn=keyword_relevance,
                  min_relevance=0.01)
    assert [n["id"] for n in a["neighborhood"]] == [n["id"] for n in b["neighborhood"]], \
        "the cap's survivors flipped with input order"
    assert a["counts"]["neighborhood"] == 12, "cap itself must still bind (3x8 candidates)"
    print("--- walk determinism ---\n  survivors invariant to input order OK")


def test_empty_and_robust():
    """Empty topic -> empty map, no crash; malformed items must not brick the walk."""
    assert build_map("", [_lesson("x", "y")], [], [])["surface"] == []
    junk = [{"kind": "lesson", "id": "j", "text": "wedge", "edges": [{"to": None}], "status": "current"}]
    m = build_map("wedge", junk, [{}], [{"status": "current"}], relevance_fn=keyword_relevance,
                  min_relevance=0.01)
    assert "j" in _ids(m["surface"]), "a valid hit survives alongside malformed neighbors"
    print("--- empty + robust ---\n  empty topic empty map; malformed items tolerated OK")


if __name__ == "__main__":
    print("=" * 60)
    print("KNOWLEDGE_MAP -- the WALK property (T059 / R8)")
    print("=" * 60)
    test_forward_walk_reaches_edge_only_lesson()
    test_reverse_walk_traverses_the_one_directional_edge()
    test_currency_honesty_retired_goes_to_archive()
    test_adapter_status_contract_timestamps_not_booleans()
    test_benched_and_graduated_lessons_land_in_archive()
    test_walk_is_input_order_invariant()
    test_empty_and_robust()
    print("\nALL KNOWLEDGE_MAP TESTS PASSED")
