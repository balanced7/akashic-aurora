"""
Slice 8 — the narrative evaluation harness (the keystone).

Runs the WHOLE acceptance battery against the gold fixture, prints a metrics table,
and asserts every per-slice bar from docs/narrative-test-plan.md. This is the gate the
test plan demands: "a slice ships only when its acceptance bar is met on the fixture."
It is regression-guarded (pytest) and human-readable (`py tests/test_narrative.py`).

Bars enforced
  Routing (Slice 2)     : ARI >= 0.70, WindowDiff <= 0.30, boundary-F1 >= 0.60
  Themes (Slice 5)      : multi-label micro-F1 >= 0.60   (the previously-unmeasured bar)
  Chronicler (Slice 3)  : faithfulness == 100%, coverage >= 95%, chronological == 100%
  Navigation (Slice 4)  : every QA pair reachable in <= 2 drills, beat resolves

Theme metric note: the plan named "NMI >= 0.60", but NMI assumes a single-label
partition while themes are MULTI-label. Micro-F1 over (beat, theme) pairs is the
methodologically correct bar; single-label NMI on the primary theme is reported too,
for continuity.
"""
import os
import sys
import tempfile

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.chronicler import Chronicler
from core.narrative.schema import Atlas, Beat, Chapter, beat_key, chapter_key, track_key
from core.narrative.track_router import TrackRouter, RouteHint
from core.narrative.theme_assigner import ThemeAssigner
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from narrative_metrics import (
    ari, nmi, purity, accuracy, boundaries, windowdiff, boundary_f1,
    multilabel_prf, jaccard_multilabel,
)
from fixtures.narrative_fixture import gold_rows, gold_qa, GOLD_TRACKS, GOLD_THEME_VOCAB

# ---- acceptance bars (docs/narrative-test-plan.md) ----
ARI_BAR = 0.70
WINDOWDIFF_BAR = 0.30
BOUNDARY_F1_BAR = 0.60
THEME_F1_BAR = 0.60
FAITHFUL_BAR = 100.0
COVERAGE_BAR = 95.0
CHRONO_BAR = 100.0
NAV_BAR = 100.0


# ===================== measurement =====================

def _measure_routing():
    rows = gold_rows()
    gold = [r["gold"] for r in rows]
    items = [
        (Beat(id=f"b{i}", at=r["at"], kind=r["kind"], summary=r["summary"], source=r["source"]),
         RouteHint(paths=r["paths"], category=r["category"], task=r["task"]))
        for i, r in enumerate(rows)
    ]
    pred = [res.track for res in TrackRouter().route_sequence(items)]
    gb, pb = boundaries(gold), boundaries(pred)
    return {
        "ARI": ari(gold, pred),
        "NMI": nmi(gold, pred),
        "purity": purity(gold, pred),
        "accuracy": accuracy(gold, pred),
        "WindowDiff": windowdiff(gb, pb),
        "boundary_F1": boundary_f1(gb, pb),
    }


def _measure_themes():
    rows = gold_rows()
    ta = ThemeAssigner()
    gold_sets = [r["gold_themes"] for r in rows]
    pred_sets = []
    for r in rows:
        beat = Beat(id="b", at=r["at"], kind=r["kind"], summary=r["summary"], source=r["source"])
        hint = RouteHint(paths=r["paths"], category=r["category"], task=r["task"])
        pred_sets.append(ta.assign(beat, hint))
    prec, rec, f1 = multilabel_prf(gold_sets, pred_sets)
    # single-label NMI on the primary (first) theme, for continuity with the plan
    g_primary = [g[0] if g else "_none_" for g in gold_sets]
    p_primary = [p[0] if p else "_none_" for p in pred_sets]
    return {
        "precision": prec,
        "recall": rec,
        "micro_F1": f1,
        "jaccard": jaccard_multilabel(gold_sets, pred_sets),
        "primary_NMI": nmi(g_primary, p_primary),
    }


def _build_store():
    """Emit every fixture beat through the REAL pipeline (router + theme inference),
    then chronicle. Returns (store, chronicle_report)."""
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    bl = BeatLog(s)
    rows = gold_rows()
    for r in rows:
        bl.emit(r["kind"], r["summary"], r["source"], at=r["at"],
                hint=RouteHint(paths=r["paths"], category=r["category"], task=r["task"]))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=tempfile.mkdtemp(),
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170))
    report = c.chronicle_all(now="2026-06-30T00:00:00")
    return s, report


def _measure_chronicler(store, report):
    # chronological integrity: every chapter's beats are time-ordered
    chrono_ok = True
    raw_atlas = store.get("narr:atlas:current")
    if raw_atlas:
        import json
        atlas = Atlas.from_dict(json.loads(raw_atlas))
        for t in atlas.tracks:
            raw_t = store.get(track_key(t))
            if not raw_t:
                continue
            from core.narrative.schema import Track
            tr = Track.from_dict(json.loads(raw_t))
            for cid in tr.chapters:
                ch = _load_chapter(store, cid)
                if not ch:
                    continue
                times = [b.at for b in (_load_beat(store, bid) for bid in ch.beats) if b]
                if times != sorted(times):
                    chrono_ok = False
    return {
        "faithfulness": 100.0 if report["faithful"] else 0.0,
        "coverage": report["coverage"],
        "chronological": 100.0 if chrono_ok else 0.0,
        "chapters": report["chapters"],
        "tracks": report["tracks"],
    }


def _measure_navigation(store):
    """For each QA pair: Atlas -> (--at) chapter [drill 1] -> (--beat) beat [drill 2].
    Success = expected track's chapter is reached and a beat resolves, in <= 2 drills."""
    import json
    from datetime import datetime
    raw_atlas = store.get("narr:atlas:current")
    if not raw_atlas:
        return {"success_rate": 0.0, "max_drills": 0, "n": 0}
    atlas = Atlas.from_dict(json.loads(raw_atlas))
    from core.narrative.schema import Track

    def chapters_at(ts_iso):
        target = datetime.fromisoformat(ts_iso).timestamp()
        hits = []
        for t in atlas.tracks:
            raw_t = store.get(track_key(t))
            if not raw_t:
                continue
            for cid in Track.from_dict(json.loads(raw_t)).chapters:
                ch = _load_chapter(store, cid)
                if not ch:
                    continue
                try:
                    start = datetime.fromisoformat(ch.span_start).timestamp()
                    end = (datetime.fromisoformat(ch.span_end).timestamp()
                           if ch.span_end else float("inf"))
                except (ValueError, TypeError):
                    continue
                if start <= target <= end:
                    hits.append(ch)
        return hits

    ok, max_drills = 0, 0
    qa = gold_qa()
    for pair in qa:
        drills = 1                          # Atlas -> chapter via --at
        found = [ch for ch in chapters_at(pair["at"]) if ch.track == pair["expect_track"]]
        if not found:
            continue
        ch = found[0]
        beat_ok = False
        if ch.beats:
            drills = 2                       # chapter -> beat via --beat
            b = _load_beat(store, ch.beats[0])
            beat_ok = b is not None and bool(b.source)
        if beat_ok and drills <= 2:
            ok += 1
            max_drills = max(max_drills, drills)
    return {"success_rate": (ok / len(qa) * 100) if qa else 100.0,
            "max_drills": max_drills, "n": len(qa)}


def _load_chapter(store, cid):
    import json
    raw = store.get(chapter_key(cid))
    if not raw:
        return None
    try:
        return Chapter.from_dict(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _load_beat(store, bid):
    import json
    raw = store.get(beat_key(bid))
    if not raw:
        return None
    try:
        return Beat.from_dict(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


# ===================== report table =====================

def _row(name, value, op, bar, fmt="{:.3f}"):
    if op == ">=":
        ok = value >= bar
    elif op == "<=":
        ok = value <= bar
    else:
        ok = value == bar
    val = fmt.format(value)
    return (f"  {'PASS' if ok else 'FAIL'}  {name:<28} {val:>8}  (bar {op} {bar})", ok)


def render_report():
    rt = _measure_routing()
    th = _measure_themes()
    store, report = _build_store()
    ch = _measure_chronicler(store, report)
    nav = _measure_navigation(store)

    lines, oks = [], []
    lines.append("=" * 64)
    lines.append("NARRATIVE EVALUATION HARNESS (Slice 8) -- fixture: %d beats, %d tracks"
                 % (len(gold_rows()), len(GOLD_TRACKS)))
    lines.append("=" * 64)

    lines.append("\n[Routing -- Slice 2]")
    for r, ok in (
        _row("ARI", rt["ARI"], ">=", ARI_BAR),
        _row("WindowDiff", rt["WindowDiff"], "<=", WINDOWDIFF_BAR),
        _row("boundary_F1", rt["boundary_F1"], ">=", BOUNDARY_F1_BAR),
    ):
        lines.append(r); oks.append(ok)
    lines.append("        (NMI %.3f | purity %.3f | accuracy %.3f)"
                 % (rt["NMI"], rt["purity"], rt["accuracy"]))

    lines.append("\n[Themes -- Slice 5]")
    for r, ok in (_row("theme micro-F1", th["micro_F1"], ">=", THEME_F1_BAR),):
        lines.append(r); oks.append(ok)
    lines.append("        (precision %.3f | recall %.3f | jaccard %.3f | primary-NMI %.3f)"
                 % (th["precision"], th["recall"], th["jaccard"], th["primary_NMI"]))

    lines.append("\n[Chronicler -- Slice 3]")
    for r, ok in (
        _row("faithfulness %", ch["faithfulness"], "==", FAITHFUL_BAR, "{:.1f}"),
        _row("coverage %", ch["coverage"], ">=", COVERAGE_BAR, "{:.1f}"),
        _row("chronological %", ch["chronological"], "==", CHRONO_BAR, "{:.1f}"),
    ):
        lines.append(r); oks.append(ok)
    lines.append("        (%d chapters across %d tracks)" % (ch["chapters"], ch["tracks"]))

    lines.append("\n[Navigation -- Slice 4]")
    for r, ok in (_row("QA reachable %", nav["success_rate"], "==", NAV_BAR, "{:.1f}"),):
        lines.append(r); oks.append(ok)
    lines.append("        (%d QA pairs, max %d drills)" % (nav["n"], nav["max_drills"]))

    lines.append("\n" + "=" * 64)
    lines.append("RESULT: %d/%d bars met" % (sum(oks), len(oks)))
    lines.append("=" * 64)
    return "\n".join(lines), all(oks)


# ===================== pytest entry points =====================

def test_routing_bars():
    rt = _measure_routing()
    assert rt["ARI"] >= ARI_BAR, rt
    assert rt["WindowDiff"] <= WINDOWDIFF_BAR, rt
    assert rt["boundary_F1"] >= BOUNDARY_F1_BAR, rt


def test_theme_bar():
    th = _measure_themes()
    assert th["micro_F1"] >= THEME_F1_BAR, th


def test_chronicler_bars():
    store, report = _build_store()
    ch = _measure_chronicler(store, report)
    assert ch["faithfulness"] == FAITHFUL_BAR, ch
    assert ch["coverage"] >= COVERAGE_BAR, ch
    assert ch["chronological"] == CHRONO_BAR, ch


def test_navigation_bar():
    store, _ = _build_store()
    nav = _measure_navigation(store)
    assert nav["success_rate"] == NAV_BAR, nav
    assert nav["max_drills"] <= 2, nav


def test_all_bars_met():
    _, all_ok = render_report()
    assert all_ok, "one or more narrative acceptance bars not met (run `py tests/test_narrative.py`)"


if __name__ == "__main__":
    report, all_ok = render_report()
    print(report)
    sys.exit(0 if all_ok else 1)
