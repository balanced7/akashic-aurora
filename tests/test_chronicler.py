"""
Tests for the Chronicler (Slice 3). Shape + robustness + acceptance bar
(faithfulness = 100%, coverage >= 95%, idempotent, chronological integrity).

Run: py tests/test_chronicler.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog, TIMELINE
from core.narrative.chronicler import Chronicler, BoundaryDetector
from core.narrative.schema import (
    Beat, Chapter, Track, Atlas, Edge,
    beat_key, chapter_key, track_key,
    validate_beat, STORY_FORMAT_VERSION,
)
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller


def _log():
    return BeatLog(FileStore(os.path.join(tempfile.mkdtemp(), "s.json")))


def _chronicler(log=None, store=None):
    s = store or FileStore(os.path.join(tempfile.mkdtemp(), "c.json"))
    return Chronicler(
        beat_log=log or BeatLog(s),
        store=s,
        ranker=Ranker(),
        distiller=Distiller(max_chars_per_entry=170),
        token_budget=4000,
        chronicle_dir=tempfile.mkdtemp(),
    )


# =========================== BoundaryDetector ===========================


def _beat(at: str, weight: int = 1, kind: str = "note",
          summary: str = "x", source: str = "ledger:1") -> Beat:
    return Beat(id=f"b_{at}", at=at, kind=kind, summary=summary,
                source=source, weight=weight)


def test_detect_no_boundaries():
    """No gap, no milestone → one chapter for the whole sequence."""
    d = BoundaryDetector(min_gap_hours=4, salience_weight=5)
    beats = [
        _beat("2026-06-27T10:00:00"),
        _beat("2026-06-27T10:30:00"),
        _beat("2026-06-27T11:00:00"),
    ]
    cuts = d.detect(beats)
    assert cuts == [0], f"expected [0], got {cuts}"
    print("  no-boundary: one chapter for the whole sequence OK")


def test_detect_time_gap():
    """Gap > min_gap_hours → boundary at that beat."""
    d = BoundaryDetector(min_gap_hours=4, salience_weight=5)
    beats = [
        _beat("2026-06-27T10:00:00"),
        _beat("2026-06-27T10:30:00"),
        _beat("2026-06-28T06:00:00"),   # >19h gap
        _beat("2026-06-28T07:00:00"),
    ]
    cuts = d.detect(beats)
    assert 2 in cuts, f"expected cut at 2, got {cuts}"
    print("  time-gap: boundary detected after gap OK")


def test_detect_milestone():
    """Weight >= salience_weight → boundary at that beat."""
    d = BoundaryDetector(min_gap_hours=4, salience_weight=5)
    beats = [
        _beat("2026-06-27T10:00:00", weight=2),
        _beat("2026-06-27T10:30:00", weight=2),
        _beat("2026-06-27T11:00:00", weight=5, kind="milestone"),
        _beat("2026-06-27T11:30:00", weight=2),
    ]
    cuts = d.detect(beats)
    assert 2 in cuts, f"expected cut at 2 (milestone), got {cuts}"
    print("  milestone: boundary at milestone beat OK")


def test_detect_empty():
    """Empty sequence → [0] (one empty chapter)."""
    d = BoundaryDetector()
    assert d.detect([]) == [0]
    print("  empty: [] -> [0] OK")


def test_detect_deterministic():
    """Same input → same cuts every time."""
    d = BoundaryDetector(min_gap_hours=4, salience_weight=5)
    beats = [
        _beat("2026-06-27T10:00:00", weight=2),
        _beat("2026-06-27T11:00:00", weight=5, kind="milestone"),
        _beat("2026-06-27T12:00:00", weight=2),
        _beat("2026-06-28T10:00:00", weight=2),  # 22h gap
    ]
    a = d.detect(beats)
    b = d.detect(beats)
    assert a == b, f"determinism violated: {a} != {b}"
    print("  deterministic: same input -> same cuts OK")


# =========================== Chronicler ===========================


def test_chronicler_empty():
    """No beats → empty report, no crash."""
    c = _chronicler()
    report = c.chronicle_all()
    assert report["chapters"] == 0
    assert report["total_beats"] == 0
    assert report["faithful"] is True
    print("  empty: no beats -> empty report OK")


def test_chronicler_single_beat():
    """Single beat → one chapter with that beat."""
    c = _chronicler()
    b = c.beat_log.emit("note", "single beat", "ledger:1",
                        at="2026-06-27T10:00:00")
    report = c.chronicle_all()
    assert report["chapters"] == 1
    assert report["total_beats"] == 1
    ch_key = chapter_key(f"chapter_{hashlib_mock(b.track, 0, '2026-06-27T10:00:00')}")
    # Actually let's use the real key: the md5 of f"{track}_{seg_index}_{span_start}"
    import hashlib
    expected_id = f"chapter_{hashlib.md5(f'{b.track}_0_2026-06-27T10:00:00'.encode()).hexdigest()[:12]}"
    raw = c.store.get(chapter_key(expected_id))
    assert raw is not None, "chapter should be persisted"
    ch = Chapter.from_dict(json.loads(raw))
    assert ch.track == b.track
    assert ch.beats == [b.id]
    print("  single-beat: one chapter with that beat OK")


def hashlib_mock(track, seg_idx, span):
    import hashlib
    return hashlib.md5(f"{track}_{seg_idx}_{span}".encode()).hexdigest()[:12]


def test_chronicler_shape():
    """Emit a multi-track sequence → verify chapter shape + beat grouping."""
    from core.narrative.track_router import RouteHint
    c = _chronicler()
    beats = [
        c.beat_log.emit("commit", "add store", "git:1",
                        at="2026-06-27T10:00:00",
                        hint=RouteHint(paths=["core/foundation/store.py"])),
        c.beat_log.emit("commit", "add ledgers", "git:2",
                        at="2026-06-27T10:30:00",
                        hint=RouteHint(paths=["core/foundation/ledger.py"])),
        c.beat_log.emit("learning", "prior art RAPTOR", "learn:exp:1",
                        at="2026-06-27T12:00:00",
                        hint=RouteHint(category="research")),
    ]

    report = c.chronicle_all()
    assert report["chapters"] >= 1
    assert report["total_beats"] == 3
    assert report["faithful"] is True

    # Atlas should list all tracks
    raw_atlas = c.store.get("narr:atlas:current")
    assert raw_atlas is not None
    atlas = Atlas.from_dict(json.loads(raw_atlas))
    assert "ai-setup" in atlas.tracks
    assert "research" in atlas.tracks
    print(f"  shape: {report['chapters']} chapters, {report['tracks']} tracks OK")


def test_chronicler_uses_route_hint():
    """Use RouteHint for track routing during emit."""
    from core.narrative.track_router import RouteHint
    c = _chronicler()
    b = c.beat_log.emit("commit", "core fix", "git:3",
                        at="2026-06-27T10:00:00",
                        hint=RouteHint(paths=["core/foundation/store.py"]))
    assert b.track == "ai-setup"
    report = c.chronicle_all()
    assert report["total_beats"] == 1
    assert report["chapters"] == 1
    print("  route-hint: beat routed by path hint during chronicle OK")


def test_chronicler_idempotent():
    """Running chronicle_all twice on the same data → same output."""
    import json as _json
    cdir = tempfile.mkdtemp()
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))

    FIXED_NOW = "2026-06-27T15:00:00"

    # First run
    c1 = Chronicler(beat_log=BeatLog(s), store=s, chronicle_dir=cdir)
    for i in range(5):
        c1.beat_log.emit("note", f"beat {i}", f"ledger:{i}",
                         at=f"2026-06-27T{10 + i}:00:00")
    r1 = c1.chronicle_all(now=FIXED_NOW)

    # Snapshot chapter contents from store after r1
    chapters_after_r1 = {}
    raw_atlas = s.get("narr:atlas:current")
    if raw_atlas:
        at = Atlas.from_dict(_json.loads(raw_atlas))
        for t in at.tracks:
            raw_t = s.get(track_key(t))
            if raw_t:
                tr = Track.from_dict(_json.loads(raw_t))
                for cid in tr.chapters:
                    raw_ch = s.get(chapter_key(cid))
                    if raw_ch:
                        chapters_after_r1[cid] = raw_ch

    # Second run on same store
    c2 = Chronicler(beat_log=BeatLog(s), store=s, chronicle_dir=cdir)
    r2 = c2.chronicle_all(now=FIXED_NOW)

    assert r1["chapters"] == r2["chapters"], "chapter count must match"
    assert r1["total_beats"] == r2["total_beats"], "beat count must match"
    assert r1["coverage"] == r2["coverage"], "coverage must match"

    # Chapter data should be byte-identical after second run
    chapters_after_r2 = {}
    raw_atlas2 = s.get("narr:atlas:current")
    if raw_atlas2:
        at2 = Atlas.from_dict(_json.loads(raw_atlas2))
        for t in at2.tracks:
            raw_t = s.get(track_key(t))
            if raw_t:
                tr = Track.from_dict(_json.loads(raw_t))
                for cid in tr.chapters:
                    raw_ch = s.get(chapter_key(cid))
                    if raw_ch:
                        chapters_after_r2[cid] = raw_ch

    for cid, content in chapters_after_r1.items():
        assert content == chapters_after_r2.get(cid), \
            f"chapter {cid} content differs between runs"
    print(f"  idempotent: chapters={r1['chapters']} identical on re-run OK")


def test_chronicler_chronological_integrity():
    """Beats in chapters appear in chronological order."""
    c = _chronicler()
    c.beat_log.emit("note", "first", "ledger:1",
                    at="2026-06-27T10:00:00")
    c.beat_log.emit("milestone", "second", "ledger:2",
                    at="2026-06-27T11:00:00", weight=5)
    c.beat_log.emit("note", "third", "ledger:3",
                    at="2026-06-27T12:00:00")

    report = c.chronicle_all()
    raw_atlas = c.store.get("narr:atlas:current")
    assert raw_atlas is not None
    atlas = Atlas.from_dict(json.loads(raw_atlas))

    for ch_dict in json.loads(c.store.get("narr:atlas:current")):
        pass  # atlas doesn't contain chapters directly

    # Load all chapters and verify their beats are sorted
    for track in atlas.tracks:
        raw = c.store.get(track_key(track))
        if not raw:
            continue
        from core.narrative.schema import Track as Tr
        t = Tr.from_dict(json.loads(raw))
        for cid in t.chapters:
            raw_ch = c.store.get(chapter_key(cid))
            if raw_ch:
                ch = Chapter.from_dict(json.loads(raw_ch))
                times = []
                for bid in ch.beats:
                    raw_b = c.store.get(beat_key(bid))
                    if raw_b:
                        b = Beat.from_dict(json.loads(raw_b))
                        times.append(b.at)
                assert times == sorted(times), f"beats in {cid} not chronological"
    print("  chronological: beats in chapters are time-ordered OK")


def test_chronicler_faithfulness():
    """Every chapter's source entries must resolve to a real Beat.

    Faithfulness bar = 100% (the Distiller's lossless-pointer invariant).
    """
    from core.narrative.track_router import RouteHint
    c = _chronicler()
    for i in range(3):
        c.beat_log.emit("learning", f"lesson {i}", f"learn:exp:{i}",
                        at=f"2026-06-27T{10 + i}:00:00",
                        hint=RouteHint(category="research"))

    report = c.chronicle_all()
    assert report["faithful"] is True, "all chapters must have resolvable beat sources"
    print(f"  faithfulness: {report['faithful']} OK")


def test_chronicler_coverage():
    """At least 95% of weight->=4 Beats appear in a chapter."""
    c = _chronicler()
    # Emit two high-weight and one low-weight beat
    c.beat_log.emit("milestone", "major milestone", "git:m1",
                    at="2026-06-27T10:00:00", weight=5)
    c.beat_log.emit("decision", "key decision", "ledger:d1",
                    at="2026-06-27T11:00:00", weight=4)
    c.beat_log.emit("note", "low-weight note", "ledger:n1",
                    at="2026-06-27T12:00:00", weight=1)

    report = c.chronicle_all()
    assert report["coverage"] >= 95.0, \
        f"coverage {report['coverage']} < 95%"
    print(f"  coverage: {report['coverage']}% (bar >= 95%) OK")


def test_chronicler_md_and_json_rendered():
    """Verify story.md and story.index.json are written to disk."""
    cdir = tempfile.mkdtemp()
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    c = Chronicler(
        beat_log=BeatLog(s),
        store=s,
        chronicle_dir=cdir,
        token_budget=4000,
    )
    c.beat_log.emit("note", "test beat", "ledger:1",
                    at="2026-06-27T10:00:00")
    report = c.chronicle_all()

    assert os.path.exists(report["story_md"]), "story.md must exist"
    assert os.path.exists(report["story_json"]), "story.index.json must exist"

    md = open(report["story_md"], encoding="utf-8").read()
    assert "Story" in md
    assert "Atlas" in md

    idx = json.loads(open(report["story_json"], encoding="utf-8").read())
    assert idx["version"] == STORY_FORMAT_VERSION
    assert "atlas" in idx
    assert "chapters" in idx
    assert len(idx["chapters"]) == 1
    print("  render: story.md + story.index.json written correctly OK")


def test_chronicler_multi_chapter_by_gap():
    """Beats with >4h gap produce separate chapters."""
    c = _chronicler()
    # Beat 1-2: same session
    c.beat_log.emit("note", "morning work", "ledger:1",
                    at="2026-06-27T10:00:00")
    c.beat_log.emit("note", "more morning", "ledger:2",
                    at="2026-06-27T11:00:00")
    # Beat 3-4: next day (big gap)
    c.beat_log.emit("note", "next day work", "ledger:3",
                    at="2026-06-28T10:00:00")
    c.beat_log.emit("note", "more next day", "ledger:4",
                    at="2026-06-28T11:00:00")

    report = c.chronicle_all()
    assert report["chapters"] >= 2, \
        f"expected >=2 chapters from a day gap, got {report['chapters']}"
    print(f"  multi-chapter: {report['chapters']} chapters from time gap OK")


def test_chronicler_skip_corrupt_beat():
    """A corrupt/invalid beat in the store is skipped, not fatal."""
    c = _chronicler()
    # Emit one valid beat
    b = c.beat_log.emit("note", "valid", "ledger:1",
                        at="2026-06-27T10:00:00")
    # Manually inject a corrupt beat
    c.store.set("narr:beat:corrupt_beat", "not valid json{{{")
    c.store.zadd(TIMELINE, {"corrupt_beat": _epoch("2026-06-27T09:00:00")})

    report = c.chronicle_all()
    assert report["chapters"] >= 1
    assert report["faithful"] is True
    print("  corrupt-beat-skip: corrupt beat skipped, no crash OK")


def _epoch(iso: str) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0


# =========================== main ===========================


def main():
    print("=" * 60)
    print("BOUNDARY DETECTOR TESTS")
    print("=" * 60)
    test_detect_no_boundaries()
    test_detect_time_gap()
    test_detect_milestone()
    test_detect_empty()
    test_detect_deterministic()

    print("\n" + "=" * 60)
    print("CHRONICLER TESTS (Slice 3)")
    print("=" * 60)
    test_chronicler_empty()
    test_chronicler_single_beat()
    test_chronicler_shape()
    test_chronicler_uses_route_hint()
    test_chronicler_idempotent()
    test_chronicler_chronological_integrity()
    test_chronicler_faithfulness()
    test_chronicler_coverage()
    test_chronicler_md_and_json_rendered()
    test_chronicler_multi_chapter_by_gap()
    test_chronicler_skip_corrupt_beat()

    print("\n" + "=" * 60)
    print("ALL CHRONICLER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
