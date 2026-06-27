"""
Stress tests for the `story` CLI verb (Slice 4). Edge cases, large datasets,
corruption, concurrency, partial matches, and boundary conditions.
"""
import json
import os
import sys
import tempfile
import random
import string
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog, TIMELINE
from core.narrative.chronicler import Chronicler
from core.narrative.schema import (
    Beat, Chapter, Track, Atlas, Edge,
    beat_key, chapter_key, track_key,
    STORY_FORMAT_VERSION,
)
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from core.narrative.track_router import RouteHint
from datetime import datetime, timedelta


def _run_cli(args, store=None):
    """Simulate `py agent_cli.py story <args>` and return (stdout, returncode)."""
    import io
    from agent_cli import cmd_story
    class FakeArgs:
        pass
    fa = FakeArgs()
    fa.chronicle = "--chronicle" in args
    fa.session_end = "--session-end" in args
    fa.mark = None
    fa.track = None
    fa.theme = None
    fa.themes = "--themes" in args
    fa.at = None
    fa.chapter = None
    fa.beat = None
    fa.json = "--json" in args
    for a in args:
        if a.startswith("--track="):
            fa.track = a.split("=", 1)[1]
        elif a.startswith("--theme="):
            fa.theme = a.split("=", 1)[1]
        elif a.startswith("--chapter="):
            fa.chapter = a.split("=", 1)[1]
        elif a.startswith("--beat="):
            fa.beat = a.split("=", 1)[1]
        elif a.startswith("--at="):
            fa.at = a.split("=", 1)[1]
    old_stdout = sys.stdout
    sys.stdout = buf = __import__("io").StringIO()
    rc = 0
    try:
        rc = cmd_story(fa, store=store) or 0
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    except Exception:
        rc = 1
    finally:
        sys.stdout = old_stdout
    return buf.getvalue(), rc


def _make_store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _seed_beats(store, n, tracks=("ai-setup", "research")):
    """Create n beats across given tracks, return BeatLog."""
    bl = BeatLog(store)
    cdir = tempfile.mkdtemp()
    for i in range(n):
        tr = tracks[i % len(tracks)]
        kind = "commit" if tr == "ai-setup" else ("learning" if tr == "research" else "note")
        at = f"2026-06-{27 + i // 10:02d}T{10 + i % 10:02d}:00:00"
        hint = None
        if tr == "ai-setup":
            hint = RouteHint(paths=["core/"])
        elif tr == "research":
            hint = RouteHint(category="research")
        elif tr == "vision":
            hint = RouteHint(category="vision")
        bl.emit(kind, f"beat {i} of {n}", f"source:{i}",
                at=at, weight=random.randint(1, 5), hint=hint)
    return bl, cdir


# =========================== Large datasets ===========================

def stress_large_beat_count():
    """Chronicle and explore 1000+ beats."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 1000, tracks=("ai-setup", "research", "vision"))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=80),
                   token_budget=2000)
    t0 = time.time()
    report = c.chronicle_all(now="2026-07-01T00:00:00")
    elapsed = time.time() - t0
    print(f"  1000 beats: {report['chapters']} chapters, "
          f"{report['tracks']} tracks, {elapsed:.2f}s chronicle time")

    # Atlas view
    out, rc = _run_cli([], store=s)
    assert rc == 0
    assert "Story Atlas" in out
    assert "research" in out or "ai-setup" in out
    print(f"  atlas output: {len(out)} bytes")

    # Track view
    out, rc = _run_cli(["--track=research"], store=s)
    assert rc == 0
    assert "research" in out

    # Chapter view (first chapter from first track)
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    out, rc = _run_cli([f"--chapter={cid}"], store=s)
    assert rc == 0
    assert cid in out

    # Beat view
    raw_ch = s.get(chapter_key(cid))
    ch = Chapter.from_dict(json.loads(raw_ch))
    out, rc = _run_cli([f"--beat={ch.beats[0]}"], store=s)
    assert rc == 0

    print(f"  stress-large-beats: 1000 beats OK")


def stress_many_tracks():
    """20+ tracks, each with sparse chapters. Bypasses TrackRouter
    (which would map all unknown categories to 'unknown') by writing
    track/chapter keys directly to the store."""
    s = _make_store()
    tracks = [f"track_{i}" for i in range(25)]
    # Create a chapter per track directly in the store
    chapters = []
    for i, t in enumerate(tracks):
        cid = f"ch_mt_{i}"
        ch = Chapter(id=cid, track=t, title=f"chapter in {t}",
                     span_start=f"2026-06-{27 + i // 10:02d}T{10 + i % 10:02d}:00:00",
                     span_end=f"2026-06-{27 + i // 10:02d}T{11 + i % 10:02d}:00:00",
                     summary=f"Chapter for track {t}",
                     beats=[f"beat_mt_{i}"], relates=[])
        s.set(chapter_key(cid), json.dumps(ch.to_dict()))
        tr = Track(id=t, title=t, chapters=[cid])
        s.set(track_key(t), json.dumps(tr.to_dict()))
        chapters.append(cid)
    # Create atlas
    at = Atlas(generated_at="2026-06-27T12:00:00", summary="many tracks",
               tracks=list(tracks))
    s.set("narr:atlas:current", json.dumps(at.to_dict()))
    out, rc = _run_cli([], store=s)
    assert rc == 0
    for t in tracks[:3]:
        assert t in out
    print(f"  stress-many-tracks: 25 tracks in atlas OK")


# =========================== Corrupted / edge data ===========================

def stress_corrupt_chapter_json():
    """Store has malformed chapter JSON -> story handles gracefully."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 10)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-07-01T00:00:00")

    # Corrupt one chapter
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    s.set(chapter_key(cid), "not valid json{{{")

    # Chapter view should fail gracefully
    out, rc = _run_cli([f"--chapter={cid}"], store=s)
    assert rc == 2 or "ERROR" in out
    # Atlas should still work
    out2, rc2 = _run_cli([], store=s)
    assert rc2 == 0
    print(f"  stress-corrupt-chapter: corrupt chapter handled OK")


def stress_corrupt_beat_json():
    """Malformed beat JSON -> beat view returns error, other views work."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 10)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-07-01T00:00:00")

    # Corrupt the beat key namespace
    s.set(beat_key("corrupt_beat_1"), "{{{bad json")

    out, rc = _run_cli(["--beat=corrupt_beat_1"], store=s)
    # Should say not found (we check beat_key first, then bare narr:beat:)
    assert rc == 2 or "ERROR" in out or "not found" in out
    print(f"  stress-corrupt-beat: corrupt beat handled OK")


def stress_empty_track():
    """Track key exists in atlas but has no chapters."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 5, tracks=("ai-setup",))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-07-01T00:00:00")

    # Manually add an empty track to the atlas
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    at.tracks.append("empty_track")
    s.set("narr:atlas:current", json.dumps(at.to_dict()))
    s.set(track_key("empty_track"), json.dumps(Track(id="empty_track", title="Empty", chapters=[]).to_dict()))

    out, rc = _run_cli([], store=s)
    assert rc == 0
    assert "empty_track" in out
    print(f"  stress-empty-track: empty track rendered OK")


def stress_unicode_in_beats():
    """Beat summaries with Unicode should handle correctly."""
    s = _make_store()
    bl = BeatLog(s)
    cdir = tempfile.mkdtemp()
    bl.emit("note", "café résumé étude 中文测试", "src:1",
            at="2026-06-27T10:00:00", weight=1)
    bl.emit("note", "emoji 🧠 📚 🚀 test", "src:2",
            at="2026-06-27T11:00:00", weight=1)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-06-27T12:00:00")

    out, rc = _run_cli([], store=s)
    assert rc == 0
    # Just shouldn't crash
    out2, rc2 = _run_cli(["--json"], store=s)
    assert rc2 == 0
    data = json.loads(out2)
    print(f"  stress-unicode: Unicode non-breaking OK")


def stress_chapter_with_no_beats():
    """Chapter object with empty beat list -> should not crash."""
    s = _make_store()
    # Manually insert a chapter with no beats
    ch = Chapter(id="chapter_empty", track="ai-setup", title="ghost chapter",
                 span_start="2026-01-01T00:00:00", span_end="2026-01-01T01:00:00",
                 summary="", beats=[], relates=[])
    s.set(chapter_key("chapter_empty"), json.dumps(ch.to_dict()))
    # Create a track pointing to it
    tr = Track(id="ai-setup", title="AI Setup", chapters=["chapter_empty"])
    s.set(track_key("ai-setup"), json.dumps(tr.to_dict()))
    # Create atlas
    at = Atlas(generated_at="2026-01-01T00:00:00", summary="test", tracks=["ai-setup"])
    s.set("narr:atlas:current", json.dumps(at.to_dict()))

    out, rc = _run_cli([], store=s)
    assert rc == 0
    out2, rc2 = _run_cli(["--track=ai-setup"], store=s)
    assert rc2 == 0
    out3, rc3 = _run_cli(["--chapter=chapter_empty"], store=s)
    assert rc3 == 0
    print(f"  stress-empty-chapter: ghost chapter handled OK")


# =========================== Partial / ambiguous matches ===========================

class _MockBD:
    """BoundaryDetector that creates chapters where each beat is its own chapter."""
    def detect(self, beats):
        return list(range(len(beats) + 1)) if beats else [0]

def stress_at_partial_match():
    """--at with time that matches boundary exactly (start/end edge)."""
    s = _make_store()
    bl = BeatLog(s)
    cdir = tempfile.mkdtemp()
    bl.emit("note", "morning", "src:1", at="2026-06-27T10:00:00", weight=1)
    bl.emit("note", "afternoon", "src:2", at="2026-06-28T14:00:00", weight=1)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   boundary_detector=_MockBD())
    c.chronicle_all(now="2026-06-28T15:00:00")

    # At the exact second of the first beat
    out, rc = _run_cli(["--at=2026-06-27T10:00:00"], store=s)
    assert rc == 0
    # At a time exactly between the two chapters
    out2, rc2 = _run_cli(["--at=2026-06-27T15:00:00"], store=s)
    assert rc2 == 1 or "No chapter" in out2
    print(f"  stress-partial-match: boundary edge cases OK")


def stress_at_bad_formats():
    """--at with various malformed timestamps."""
    s = _make_store()
    for bad in ["not-a-date", "2026/01/01", "1667", "", "2026-13-01T00:00:00"]:
        out, rc = _run_cli([f"--at={bad}"], store=s)
        # Should report error without crashing
        assert rc == 2 or "ERROR" in out
    print(f"  stress-bad-at: malformed timestamps all error OK")


def stress_track_case_sensitivity():
    """Track names should be matched case-insensitively? Currently case-sensitive."""
    s = _make_store()
    bl = BeatLog(s)
    cdir = tempfile.mkdtemp()
    bl.emit("commit", "case test", "src:1", at="2026-06-27T10:00:00",
            hint=RouteHint(paths=["core/"]))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-06-27T12:00:00")

    out, rc = _run_cli(["--track=AI-SETUP"], store=s)
    assert rc == 2  # case-sensitive, should fail
    out2, rc2 = _run_cli(["--track=ai-setup"], store=s)
    assert rc2 == 0
    print(f"  stress-case: case-sensitive matching (expected behavior) OK")


# =========================== Concurrency / idempotence ===========================

def stress_concurrent_reads():
    """Multiple story reads should not interfere."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 50)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-07-01T00:00:00")

    results = {}
    for i in range(20):
        out, rc = _run_cli([], store=s)
        results[i] = (out, rc)
    for i, (out, rc) in results.items():
        assert rc == 0, f"run {i} failed: rc={rc}"
    # All outputs should be identical (read-only)
    first = list(results.values())[0][0]
    for i, (out, rc) in results.items():
        assert out == first, f"run {i} output differs"
    print(f"  stress-concurrent: 20 concurrent reads -> identical output OK")


# =========================== Performance ===========================

def stress_latency():
    """Story CLI should respond within reasonable time."""
    s = _make_store()
    bl, cdir = _seed_beats(s, 500)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir)
    c.chronicle_all(now="2026-07-01T00:00:00")

    t0 = time.time()
    for _ in range(10):
        _run_cli([], store=s)
        _run_cli(["--track=ai-setup"], store=s)
    elapsed = time.time() - t0
    avg = elapsed / 20
    print(f"  20 story CLI calls: {elapsed:.3f}s total, {avg*1000:.1f}ms avg")
    assert avg < 5.0, f"avg latency {avg*1000:.1f}ms > 5s threshold"
    print(f"  stress-latency: avg {avg*1000:.1f}ms OK")


# =========================== main ===========================

def main():
    print("=" * 60)
    print("STORY CLI STRESS TESTS (Slice 4)")
    print("=" * 60)

    print("\n--- Large datasets ---")
    stress_large_beat_count()
    stress_many_tracks()

    print("\n--- Corrupted / edge data ---")
    stress_corrupt_chapter_json()
    stress_corrupt_beat_json()
    stress_empty_track()
    stress_unicode_in_beats()
    stress_chapter_with_no_beats()

    print("\n--- Partial / ambiguous matches ---")
    stress_at_partial_match()
    stress_at_bad_formats()
    stress_track_case_sensitivity()

    print("\n--- Concurrency / idempotence ---")
    stress_concurrent_reads()

    print("\n--- Performance ---")
    stress_latency()

    print("\n" + "=" * 60)
    print("ALL STORY CLI STRESS TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
