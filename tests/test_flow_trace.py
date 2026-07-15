"""flow_trace (R3 / T054) -- the WATERFALL property, pre-registered.

lookback answers "why", knowledge_map answers "what's near" -- flow_trace answers
"what HAPPENED, in causal order, across which lanes". The packet substrate has no
stamped flow id on the wire yet (T040 spec'd it; T046 lands it), so v1 DERIVES flows
from what envelopes already carry: meta.answers reply-links (causal edges) + sha
(duplicate detection). The kill conditions, pre-registered before the module exists:

  1. a reply carrying meta.answers must land UNDER its ask in the same flow
     (flow id = root message id, OTel trace_id-shaped);
  2. the same logical message observed on two lanes (dual-write / the T066
     double-delivery class) must render as ONE node with copies=2, never two flows.

If (1) fails we shipped a message list, not a tracer; if (2) fails the tracer
amplifies the very duplication bug it exists to expose (live receipts 2026-07-14:
event:events:raw:1784082287759-0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.flow_trace import build_flows, lane_of


def _e(eid, stream, frm, to, kind, *, meta=None, sha=None, length=100):
    return {"id": eid, "stream": stream, "frm": frm, "to": to, "kind": kind,
            "ts": "", "meta": meta or {}, "len": length, "sha": sha}


def _flow_ids(out):
    return [f["flow"] for f in out["flows"]]


def test_f1_answers_chain_builds_the_waterfall():
    """An ask and its meta.answers reply are ONE flow: reply nested under the ask,
    positive offset, flow id = the root (ask) id."""
    ask = _e("1000-0", "bifrost:inbox:deepseek", "claude", "deepseek", "request", sha="a1")
    rep = _e("5000-0", "bifrost:work:inbox:claude", "deepseek", "claude", "reply",
             meta={"answers": "1000-0"}, sha="b2")
    out = build_flows([ask, rep])
    assert len(out["flows"]) == 1, "ask + its answer must be ONE flow, not two"
    fl = out["flows"][0]
    assert fl["flow"] == "1000-0", "flow id is the root message id"
    root = fl["root"]
    assert root["kind"] == "request" and len(root["children"]) == 1
    child = root["children"][0]
    assert child["kind"] == "reply" and child["offset_ms"] == 4000, \
        f"reply offset must be child_ms - root_ms, got {child.get('offset_ms')}"
    print("--- F1 answers chain ---\n  reply nested under ask, offset 4000ms OK")


def test_f2_duplicate_delivery_collapses_to_one_node():
    """The T066 signature: one logical reply observed on legacy AND work lanes
    (different stream ids, same sha + frm/to/kind) = ONE node, copies=2, both lanes."""
    ask = _e("1000-0", "bifrost:inbox:deepseek", "claude", "deepseek", "request", sha="a1")
    legacy = _e("5000-0", "bifrost:inbox:claude", "deepseek", "claude", "reply",
                meta={"answers": "1000-0"}, sha="dupsha")
    workcp = _e("5200-0", "bifrost:work:inbox:claude", "deepseek", "claude", "reply",
                meta={"answers": "1000-0"}, sha="dupsha")
    out = build_flows([ask, legacy, workcp])
    assert len(out["flows"]) == 1
    kids = out["flows"][0]["root"]["children"]
    assert len(kids) == 1, "same-sha copies must collapse to ONE logical node"
    node = kids[0]
    assert node["copies"] == 2, f"copy count must expose the double-delivery, got {node['copies']}"
    assert set(node["lanes"]) == {"legacy", "work"}, f"both lanes observed, got {node['lanes']}"
    print("--- F2 duplicate delivery ---\n  one node, copies=2, lanes legacy+work OK")


def test_f3_lane_parse_from_stream_keys():
    """Lane labels come from the stream key shape, namespace-prefix tolerant."""
    assert lane_of("bifrost:work:inbox:claude") == "work"
    assert lane_of("bifrost:work:broadcast") == "work"
    assert lane_of("bifrost:inbox:claude") == "legacy"
    assert lane_of("bifrost:broadcast") == "broadcast"
    assert lane_of("bifrost:sig:inbox:claude") == "sig"
    assert lane_of("bifrost:trace:feed") == "trace"
    assert lane_of("test-rb25:work:inbox:x") == "work", "drill namespaces keep their lane"
    print("--- F3 lane parse ---\n  all six key shapes labeled OK")


def test_f4_singletons_window_and_order():
    """Unlinked messages are their own flows, newest-first; the window excludes
    entries older than window_ms relative to the newest entry."""
    old = _e("1000-0", "bifrost:inbox:claude", "a", "claude", "note", sha="s1")
    mid = _e("600000-0", "bifrost:inbox:claude", "b", "claude", "handoff", sha="s2")
    new = _e("900000-0", "bifrost:work:inbox:claude", "c", "claude", "request", sha="s3")
    out = build_flows([old, mid, new], window_ms=500_000)
    ids = _flow_ids(out)
    assert "1000-0" not in ids, "outside the window -- must be excluded"
    assert ids == ["900000-0", "600000-0"], f"newest flow first, got {ids}"
    assert out["counts"]["flows"] == 2 and out["counts"]["dropped_by_window"] == 1
    print("--- F4 window + order ---\n  singleton flows, newest-first, window drop counted OK")


def test_f5_robust_inputs_never_brick():
    """Malformed meta / missing sha / unknown parents degrade, never crash; a reply
    whose parent is outside the window roots its own flow with the dangling link kept."""
    orphan = _e("7000-0", "bifrost:work:inbox:claude", "deepseek", "claude", "reply",
                meta={"answers": "1-0"}, sha=None)
    junk = {"id": "8000-0", "stream": "bifrost:inbox:claude", "frm": "x", "to": "claude",
            "kind": "chat", "meta": "NOT A DICT", "len": "NaN", "sha": None}
    out = build_flows([orphan, junk])
    ids = _flow_ids(out)
    assert "7000-0" in ids, "orphaned reply must still appear as its own flow root"
    orph = next(f for f in out["flows"] if f["flow"] == "7000-0")
    assert orph["root"].get("answers_missing") == "1-0", "the dangling causal link stays visible"
    assert "8000-0" in ids, "malformed entry tolerated, not dropped silently"
    # no-sha entries must NOT dedupe against each other
    a = _e("9000-0", "bifrost:inbox:claude", "y", "claude", "chat", sha=None)
    b = _e("9100-0", "bifrost:work:inbox:claude", "y", "claude", "chat", sha=None)
    out2 = build_flows([a, b])
    assert out2["counts"]["flows"] == 2, "sha-less entries never collapse"
    print("--- F5 robustness ---\n  orphans rooted, junk tolerated, sha-less never dedupes OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FLOW_TRACE -- the WATERFALL property (T054 / R3)")
    print("=" * 60)
    test_f1_answers_chain_builds_the_waterfall()
    test_f2_duplicate_delivery_collapses_to_one_node()
    test_f3_lane_parse_from_stream_keys()
    test_f4_singletons_window_and_order()
    test_f5_robust_inputs_never_brick()
    print("\nALL FLOW_TRACE TESTS PASSED")
