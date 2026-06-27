"""
Tests for the TrackRouter (Slice 2). Shape + robustness + the ACCEPTANCE BAR
(ARI >= 0.70, WindowDiff <= 0.30 on the gold fixture) + emit integration.

Run: py tests/test_track_router.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrative.track_router import TrackRouter, RouteHint
from core.narrative.schema import Beat
from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from narrative_metrics import ari, nmi, purity, accuracy, boundaries, windowdiff, boundary_f1
from fixtures.narrative_fixture import gold_rows

ARI_BAR = 0.70
WINDOWDIFF_BAR = 0.30


def _beat(row):
    return Beat(id="b", at=row["at"], kind=row["kind"], summary=row["summary"], source=row["source"])


def test_metrics_sanity():
    assert ari([1, 1, 2, 2], [1, 1, 2, 2]) == 1.0
    assert ari("aabb", "abab") < 0.5
    assert windowdiff(boundaries("aabb"), boundaries("aabb")) == 0.0
    assert boundary_f1([0, 1, 0], [0, 1, 0]) == 1.0
    print("  metric helpers sanity OK")


def test_shape():
    r = TrackRouter()
    # a commit touching core/ -> ai-setup (by path)
    res = r.route_one(_beat({"at": "t", "kind": "commit", "summary": "x", "source": "git:1"}),
                      RouteHint(paths=["core/foundation/store.py"]))
    assert res.track == "ai-setup" and res.basis == "path"
    # a research learning -> research (by category)
    res = r.route_one(_beat({"at": "t", "kind": "learning", "summary": "x", "source": "learn:e"}),
                      RouteHint(category="research"), active="ai-setup")
    assert res.track == "research" and res.switched is True
    # strong domain keyword beats a misleading category
    res = r.route_one(_beat({"at": "t", "kind": "learning", "summary": "ZLUDA on PATH", "source": "l"}),
                      RouteHint(category="infrastructure", task="stemroller"))
    assert res.track == "stemroller" and res.basis == "strong"
    print("  shape: path / category / strong-keyword routing OK")


def test_robustness():
    r = TrackRouter()
    # no signal -> persist the active track (a switch needs a reason)
    res = r.route_one(_beat({"at": "t", "kind": "note", "summary": "back to it", "source": "l"}),
                      RouteHint(), active="vision")
    assert res.track == "vision" and res.switched is False and res.basis == "persist"
    # no signal AND no active -> unknown, no crash
    res = r.route_one(_beat({"at": "t", "kind": "note", "summary": "", "source": "l"}), RouteHint())
    assert res.track == "unknown"
    # idempotent: routing the same sequence twice gives identical results
    items = [(_beat(row), RouteHint(paths=row["paths"], category=row["category"], task=row["task"]))
             for row in gold_rows()]
    a = [x.track for x in r.route_sequence(items)]
    b = [x.track for x in r.route_sequence(items)]
    assert a == b, "routing must be deterministic"
    print("  robustness: persist / unknown / determinism OK")


def test_meets_acceptance_bar():
    rows = gold_rows()
    gold = [row["gold"] for row in rows]
    items = [(_beat(row), RouteHint(paths=row["paths"], category=row["category"], task=row["task"]))
             for row in rows]
    results = TrackRouter().route_sequence(items)
    pred = [r.track for r in results]

    score_ari = ari(gold, pred)
    score_wd = windowdiff(boundaries(gold), boundaries(pred))
    misses = [(rows[i]["summary"][:45], gold[i], pred[i]) for i in range(len(gold)) if gold[i] != pred[i]]
    print(f"\n  --- TrackRouter on the gold fixture ({len(gold)} beats) ---")
    print(f"    ARI         = {score_ari:.3f}   (bar >= {ARI_BAR})")
    print(f"    accuracy    = {accuracy(gold, pred):.3f}")
    print(f"    NMI         = {nmi(gold, pred):.3f}   purity = {purity(gold, pred):.3f}")
    print(f"    WindowDiff  = {score_wd:.3f}   (bar <= {WINDOWDIFF_BAR})")
    print(f"    boundary-F1 = {boundary_f1(boundaries(gold), boundaries(pred)):.3f}")
    print(f"    misses ({len(misses)}): " + "; ".join(f"[{g}->{p}] {s}" for s, g, p in misses))
    assert score_ari >= ARI_BAR, f"ARI {score_ari:.3f} below bar {ARI_BAR}"
    assert score_wd <= WINDOWDIFF_BAR, f"WindowDiff {score_wd:.3f} above bar {WINDOWDIFF_BAR}"
    print("  ACCEPTANCE BAR MET")


def test_emit_integration():
    log = BeatLog(FileStore(os.path.join(tempfile.mkdtemp(), "s.json")))
    b1 = log.emit("commit", "Slice 0 schema", "git:abc", at="2026-06-27T10:00:00",
                  hint=RouteHint(paths=["core/narrative/schema.py"]))
    assert b1.track == "ai-setup", "emit routes via the hint"
    b2 = log.emit("learning", "RAPTOR analogue", "learn:e", at="2026-06-27T11:00:00",
                  hint=RouteHint(category="research"))
    assert b2.track == "research"
    # per-track index populated; active track persisted
    assert log.store.zcard("narr:track:ai-setup:beats") == 1
    assert log.store.zcard("narr:track:research:beats") == 1
    assert log.store.get("narr:router:active") == "research"
    print("  emit integration: beats routed + per-track index + active persisted OK")


def main():
    print("=" * 60)
    print("TRACK ROUTER TESTS (Slice 2)")
    print("=" * 60)
    test_metrics_sanity()
    test_shape()
    test_robustness()
    test_meets_acceptance_bar()
    test_emit_integration()
    print("\n" + "=" * 60)
    print("ALL TRACK ROUTER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
