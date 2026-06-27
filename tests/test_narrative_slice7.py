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
    is_active_chapter,
    load_chapter_from_store,
    persist_chapter_with_supersession,
    write_learning_chapter_backlinks,
)
from core.narrative.chronicler import Chronicler
from core.narrative.schema import Chapter, ATLAS_KEY, chapter_key
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from context.narrative_loader import load_recent_narrative_for_boot
from context.aggregator import assemble_context


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def test_supersession_on_content_change():
    s = _store()
    ch1 = Chapter(
        id="chapter_abc123",
        track="ai-setup",
        title="First version",
        span_start="2026-06-27T10:00:00",
        summary="- old summary",
        beats=["b1"],
        learnings=[],
        commits=[],
    )
    persist_chapter_with_supersession(s, ch1, now="2026-06-27T12:00:00")
    ch2 = Chapter(
        id="chapter_abc123",
        track="ai-setup",
        title="First version",
        span_start="2026-06-27T10:00:00",
        summary="- corrected summary with new facts",
        beats=["b1", "b2"],
        learnings=[],
        commits=[],
    )
    out = persist_chapter_with_supersession(s, ch2, now="2026-06-27T13:00:00")
    old = load_chapter_from_store(s, "chapter_abc123")
    assert old is not None and old.valid_to, "old chapter must be closed"
    assert out.id != "chapter_abc123", "new chapter gets a new id"
    assert is_active_chapter(out)
    print("  supersession: content change closes old chapter OK")


def test_learning_chapter_backlink():
    s = _store()
    s.set("learn:experiment:demo_exp", json.dumps({
        "experiment_name": "demo_exp",
        "recommendation": "try this",
    }))
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
    persist_chapter_with_supersession(s, ch)
    write_learning_chapter_backlinks(s, ch)
    rec = json.loads(s.get("learn:experiment:demo_exp"))
    assert rec.get("narrative_chapter") == "chapter_link1"
    assert rec.get("narrative_track") == "research"
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
    os.environ["_AISETUP_TEST_ISOLATED"] = "1"
    reset_beat_log_singleton()
    try:
        from core.narrative.beat_log import get_beat_log
        a = get_beat_log()
        b = get_beat_log()
        assert a is not b, "isolated mode must not cache singleton"
    finally:
        os.environ.pop("_AISETUP_TEST_ISOLATED", None)
        reset_beat_log_singleton()
    print("  isolation: BeatLog skips singleton under test env OK")


def main():
    print("=" * 60)
    print("NARRATIVE SLICE 7 TESTS")
    print("=" * 60)
    test_supersession_on_content_change()
    test_learning_chapter_backlink()
    test_boot_includes_narrative()
    test_beat_log_isolated_under_test_env()
    print("\n" + "=" * 60)
    print("ALL SLICE 7 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
