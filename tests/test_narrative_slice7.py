"""
Slice 7 tests — bi-temporal supersession, learning back-links, boot narrative feed.

Run: py tests/test_narrative_slice7.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog, reset_beat_log_singleton
from core.narrative.chapter_lifecycle import (
    correct_chapter,
    is_active_chapter,
    load_chapter_from_store,
    persist_chapter_in_place,
    rebuild_track_chapter_list,
    write_learning_chapter_backlinks,
)
from core.narrative.chronicler import Chronicler
from core.narrative.schema import Chapter, Track, ATLAS_KEY, chapter_key, track_key
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from core.context.narrative_loader import load_recent_narrative_for_boot
from core.context.aggregator import assemble_context


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def test_regenerate_in_place_keeps_stable_id():
    """Re-writing the same logical chapter with changed content keeps the id
    (regenerate-from-atoms) and preserves valid_from while refreshing recorded_at."""
    s = _store()
    ch1 = Chapter(id="chapter_abc123", track="ai-setup", title="v1",
                  span_start="2026-06-27T10:00:00", summary="- old summary",
                  beats=["b1"], learnings=[], commits=[])
    persist_chapter_in_place(s, ch1, now="2026-06-27T12:00:00")
    ch2 = Chapter(id="chapter_abc123", track="ai-setup", title="v1",
                  span_start="2026-06-27T10:00:00", summary="- corrected, with new facts",
                  beats=["b1", "b2"], learnings=[], commits=[])
    out = persist_chapter_in_place(s, ch2, now="2026-06-27T13:00:00")
    assert out.id == "chapter_abc123", "regenerate keeps the deterministic id"
    assert out.valid_from == "2026-06-27T10:00:00", "valid_from is never moved"
    assert out.recorded_at == "2026-06-27T13:00:00", "recorded_at refreshes"
    assert is_active_chapter(out)
    print("  in-place: regenerate keeps stable id + bi-temporal anchors OK")


def test_explicit_correction_supersedes_with_edges():
    """A genuine correction (different id) retires the old chapter and links both
    with real 66-type edges; only the new one is active."""
    s = _store()
    old = Chapter(id="chapter_old", track="ai-setup", title="old",
                  span_start="2026-06-27T10:00:00", summary="- old", beats=["b1"])
    persist_chapter_in_place(s, old, now="2026-06-27T12:00:00")
    new = Chapter(id="chapter_new", track="ai-setup", title="corrected",
                  span_start="2026-06-27T10:00:00", summary="- corrected", beats=["b1", "b2"])
    out = correct_chapter(s, "chapter_old", new, now="2026-06-27T13:00:00")
    closed = load_chapter_from_store(s, "chapter_old")
    assert closed.valid_to == "2026-06-27T13:00:00", "old chapter validity closed"
    assert any(e.type == "replaces" and e.target == "chapter_new" for e in closed.relates)
    assert any(e.type == "is_version_of" and e.target == "chapter_old" for e in out.relates)
    assert is_active_chapter(out) and not is_active_chapter(closed)
    print("  correction: explicit supersession closes old + links versions OK")


def test_track_list_drops_superseded():
    """rebuild_track_chapter_list never keeps a superseded/missing chapter id
    (the double-count bug guard)."""
    s = _store()
    a = Chapter(id="chapter_a", track="ai-setup", title="a",
                span_start="2026-06-27T10:00:00", summary="- a", beats=["b1"])
    b = Chapter(id="chapter_b", track="ai-setup", title="b",
                span_start="2026-06-27T11:00:00", summary="- b", beats=["b2"])
    persist_chapter_in_place(s, a)
    persist_chapter_in_place(s, b)
    rebuild_track_chapter_list(s, "ai-setup", ["chapter_a", "chapter_b"])
    # supersede a with a new chapter
    c = Chapter(id="chapter_c", track="ai-setup", title="c",
                span_start="2026-06-27T10:00:00", summary="- c", beats=["b1"])
    correct_chapter(s, "chapter_a", c)
    tr = rebuild_track_chapter_list(s, "ai-setup", ["chapter_c", "chapter_b"])
    assert "chapter_a" not in tr.chapters, "superseded chapter must be pruned"
    assert set(tr.chapters) == {"chapter_b", "chapter_c"}
    assert len(tr.chapters) == len(set(tr.chapters)), "no duplicates"
    print("  track-hygiene: superseded ids pruned, no double-count OK")


def test_learning_chapter_backlink():
    s = _store()
    # learn:experiment:{id} is a Redis HASH in production -- store it as one here so the
    # test exercises the same type path as canonical Redis (a string would mask WRONGTYPE).
    s.hset("learn:experiment:demo_exp", mapping={
        "experiment_name": "demo_exp",
        "recommendation": "try this",
    })
    ch = Chapter(
        id="chapter_link1",
        track="research",
        title="Research stretch",
        span_start="2026-06-27T10:00:00",
        summary="- did research",
        beats=["b1"],
        learnings=["learn:experiment:demo_exp"],
        commits=[],
    )
    persist_chapter_in_place(s, ch)
    n = write_learning_chapter_backlinks(s, ch)
    assert n == 1
    rec = s.hgetall("learn:experiment:demo_exp")
    assert rec.get("narrative_chapter") == "chapter_link1"
    assert rec.get("narrative_track") == "research"
    assert rec.get("experiment_name") == "demo_exp"   # original fields preserved
    print("  backlink: learning record stamped with chapter OK")


def test_boot_includes_narrative():
    s = _store()
    bl = BeatLog(s)
    cdir = tempfile.mkdtemp()
    from core.narrative.track_router import RouteHint
    bl.emit("learning", "Slice 7 narrative boot test", "learn:experiment:slice7_boot",
            at="2026-06-27T10:00:00", weight=4,
            hint=RouteHint(category="testing", task="slice7"))
    c = Chronicler(
        beat_log=bl, store=s, chronicle_dir=cdir,
        ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
    )
    c.chronicle_all(now="2026-06-27T12:00:00")
    nav = load_recent_narrative_for_boot(store=s)
    assert nav is not None and nav.get("chapters"), "narrative loader should return chapters"

    class _LS:
        @staticmethod
        def load_all_learnings_from_store():
            return []

        @staticmethod
        def search_learnings_by_keyword(q):
            return []

    class _CM:
        @staticmethod
        def derive_full_context_for_agent_repriming():
            return {
                "big_picture": {"progress_percentage": 0,
                                "milestones": {"total": 0, "completed": 0}},
                "mid_picture": {"current_work": None},
            }

        @staticmethod
        def load_blockers_filtered_by_status(status="active"):
            return []

    ctx = assemble_context(
        "what has been done lately",
        token_budget=9000,
        learning_store=_LS(),
        context_manager=_CM(),
        store=s,
    )
    assert ctx.get("sections", {}).get("narrative"), "boot context must include narrative section"
    assert "narrative" in (ctx.get("skeleton") or "").lower() or ctx["sections"]["narrative"]
    print("  boot-feed: aggregator includes narrative section OK")


def test_beat_log_isolated_under_test_env():
    # SAVE and RESTORE, never pop blind. Under the old opt-in regime this flag was usually
    # unset, so popping it was harmless. Since T070 made backend isolation universal
    # (2026-07-25) the flag is set for the whole suite, and an unconditional pop stripped
    # isolation from every test that ran after this one in the same process -- caught by
    # test_t070_universal_isolation failing in CI while passing when run alone.
    _prior = os.environ.get("_AISETUP_TEST_ISOLATED")
    os.environ["_AISETUP_TEST_ISOLATED"] = "1"
    reset_beat_log_singleton()
    try:
        from core.narrative.beat_log import get_beat_log
        a = get_beat_log()
        b = get_beat_log()
        assert a is not b, "isolated mode must not cache singleton"
    finally:
        if _prior is None:
            os.environ.pop("_AISETUP_TEST_ISOLATED", None)
        else:
            os.environ["_AISETUP_TEST_ISOLATED"] = _prior
        reset_beat_log_singleton()
    print("  isolation: BeatLog skips singleton under test env OK")


def test_theme_assigner_wired_into_emit():
    """Regression: emit() must INFER themes when none are passed (Slice 5 was dead
    code — the assigner existed but nothing called it in the production path)."""
    s = _store()
    bl = BeatLog(s)
    from core.narrative.track_router import RouteHint
    b = bl.emit("learning", "TrackRouter routing benchmark fixture", "learn:experiment:x",
                at="2026-06-27T10:00:00",
                hint=RouteHint(category="research", task="routing"))
    assert "routing" in b.themes, f"themes should be inferred, got {b.themes}"
    assert "evaluation" in b.themes, "multi-label inference expected"
    # explicit themes (incl. []) are honored verbatim, not overwritten
    b2 = bl.emit("note", "routing words here", "src:2",
                 at="2026-06-27T11:00:00", themes=[])
    assert b2.themes == [], "explicit empty themes must be respected"
    print("  theme-wiring: emit infers themes; explicit list honored OK")


def test_theme_index_accumulates_all_member_beats():
    """Regression: every beat sharing a theme must land in that theme's beat index
    (the old theme_seen guard recorded only the first)."""
    s = _store()
    bl = BeatLog(s)
    from core.narrative.track_router import RouteHint
    bl.emit("note", "routing fix one", "src:1", at="2026-06-27T10:00:00",
            themes=["routing"], hint=RouteHint(paths=["core/"]))
    bl.emit("note", "routing fix two", "src:2", at="2026-06-27T11:00:00",
            themes=["routing"], hint=RouteHint(category="research"))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=tempfile.mkdtemp(),
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170))
    c.chronicle_all(now="2026-06-27T12:00:00")
    from core.narrative.schema import Theme, theme_key
    t = Theme.from_dict(json.loads(s.get(theme_key("routing"))))
    assert len(t.beats) == 2, f"theme should index both beats, got {t.beats}"
    print("  theme-index: all member beats recorded OK")


def test_coverage_drops_when_high_weight_beat_omitted():
    """Regression: coverage must actually fall when the Distiller drops a high-weight
    beat (the old metric compared a set to itself and was pinned at 100%)."""
    s = _store()
    bl = BeatLog(s)
    from core.narrative.track_router import RouteHint
    # three high-weight beats in one chapter, but a tiny budget so not all fit
    for i in range(3):
        bl.emit("decision", f"high weight decision number {i} with enough text to cost budget",
                f"ledger:d{i}", at=f"2026-06-27T1{i}:00:00", weight=5,
                hint=RouteHint(category="research", task="x"))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=tempfile.mkdtemp(),
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
                   token_budget=15)  # deliberately too small for all three
    report = c.chronicle_all(now="2026-06-27T20:00:00")
    assert report["coverage"] < 100.0, \
        f"coverage must drop when beats are omitted, got {report['coverage']}"
    assert report["faithful"] is True, "what IS summarized must still resolve"
    print(f"  coverage-real: dropped beat lowers coverage to {report['coverage']}% OK")


def main():
    print("=" * 60)
    print("NARRATIVE SLICE 7 + REVIEW-FIX TESTS")
    print("=" * 60)
    test_regenerate_in_place_keeps_stable_id()
    test_explicit_correction_supersedes_with_edges()
    test_track_list_drops_superseded()
    test_learning_chapter_backlink()
    test_boot_includes_narrative()
    test_beat_log_isolated_under_test_env()
    test_theme_assigner_wired_into_emit()
    test_theme_index_accumulates_all_member_beats()
    test_coverage_drops_when_high_weight_beat_omitted()
    print("\n" + "=" * 60)
    print("ALL SLICE 7 + REVIEW-FIX TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
