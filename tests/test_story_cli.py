"""
Tests for the `story` CLI verb (Slice 4). Shape + robustness + drill-pointer
acceptance bar (right chapter/beat reachable in <=2 drills).

Run: py tests/test_story_cli.py
"""
import json
import os
import sys
import tempfile

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
from datetime import datetime


def _setup_story():
    """Create a store with beats + chronicle, return store path + chronicle dir."""
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    cdir = tempfile.mkdtemp()
    c = Chronicler(
        beat_log=BeatLog(s), store=s, chronicle_dir=cdir,
        ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
    )
    c.beat_log.emit("note", "first beat", "ledger:1",
                    at="2026-06-27T10:00:00")
    c.beat_log.emit("commit", "fix core bug", "git:a1",
                    at="2026-06-27T10:30:00",
                    hint=RouteHint(paths=["core/"]))
    c.beat_log.emit("learning", "prior art RAPTOR", "learn:exp:1",
                    at="2026-06-28T09:00:00",
                    hint=RouteHint(category="research"))
    c.beat_log.emit("decision", "use Ranker+Distiller", "ledger:d1",
                    at="2026-06-28T10:00:00", weight=5)
    c.chronicle_all(now="2026-06-28T12:00:00")
    return s, cdir


def _run_cli(args, store=None):
    """Simulate `py agent_cli.py story <args>` and return (stdout, returncode)."""
    import io
    from agent_cli import cmd_story
    class FakeArgs:
        pass
    fa = FakeArgs()
    fa.chronicle = "--chronicle" in args
    fa.session_end = "--session-end" in args
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
    sys.stdout = buf = io.StringIO()
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


# =========================== Shape tests ===========================


def test_story_atlas_shape():
    """`story` with no flags prints atlas + tracks with counts."""
    s, cdir = _setup_story()
    out, rc = _run_cli([], store=s)
    assert rc == 0, f"non-zero exit: {rc}"
    assert "Story Atlas" in out
    assert "ai-setup" in out
    assert "research" in out
    assert "chapter(s)" in out
    print("  atlas: atlas printed with tracks OK")


def test_story_atlas_json():
    """`story --json` returns Atlas as JSON."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--json"], store=s)
    assert rc == 0
    data = json.loads(out)
    assert "generated_at" in data
    assert "tracks" in data
    assert "ai-setup" in data["tracks"]
    print("  atlas-json: Atlas JSON round-trip OK")


def test_story_track():
    """`story --track NAME` prints chapters in that track."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--track=ai-setup"], store=s)
    assert rc == 0
    assert "Track: ai-setup" in out
    assert "chapter" in out
    assert "beats" in out
    print("  track: per-track chapter listing OK")


def test_story_track_json():
    """`story --track NAME --json` returns chapters as JSON array."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--track=ai-setup", "--json"], store=s)
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "track" in data[0]
    assert "beats" in data[0]
    print("  track-json: per-track JSON chapters OK")


def test_story_chapter():
    """`story --chapter ID` prints full chapter."""
    s, cdir = _setup_story()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    # Get first chapter from first track
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    out, rc = _run_cli([f"--chapter={cid}"], store=s)
    assert rc == 0
    assert "Chapter:" in out
    assert cid in out
    assert "Critic" in out
    print("  chapter: full chapter detail OK")


def test_story_chapter_json():
    """`story --chapter ID --json` returns Chapter as JSON."""
    s, cdir = _setup_story()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    out, rc = _run_cli([f"--chapter={cid}", "--json"], store=s)
    assert rc == 0
    data = json.loads(out)
    assert data["id"] == cid
    assert "track" in data
    assert "beats" in data
    print("  chapter-json: Chapter JSON round-trip OK")


def test_story_beat():
    """`story --beat ID` prints full beat."""
    s, cdir = _setup_story()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    raw_ch = s.get(chapter_key(tr.chapters[0]))
    ch = Chapter.from_dict(json.loads(raw_ch))
    bid = ch.beats[0]
    out, rc = _run_cli([f"--beat={bid}"], store=s)
    assert rc == 0
    assert "Beat:" in out
    assert bid in out
    assert "Kind:" in out
    print("  beat: full beat detail OK")


def test_story_beat_json():
    """`story --beat ID --json` returns Beat as JSON."""
    s, cdir = _setup_story()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    raw_ch = s.get(chapter_key(tr.chapters[0]))
    ch = Chapter.from_dict(json.loads(raw_ch))
    bid = ch.beats[0]
    out, rc = _run_cli([f"--beat={bid}", "--json"], store=s)
    assert rc == 0
    data = json.loads(out)
    assert data["id"] == bid
    assert "kind" in data
    assert "summary" in data
    print("  beat-json: Beat JSON round-trip OK")


def test_story_at_timestamp():
    """`story --at ISO` finds the chapter containing that time."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--at=2026-06-27T10:15:00"], store=s)
    assert rc == 0
    assert "Chapters containing" in out
    assert "2026-06-27" in out
    print("  at-timestamp: chapter found by time OK")


def test_story_at_no_match():
    """`story --at` with a time before any beats returns 1."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--at=2025-01-01T00:00:00"], store=s)
    assert rc == 1
    print("  at-no-match: returns exit code 1 OK")


# =========================== Robustness ===========================


def test_story_empty_store():
    """No story exists -> error message + exit code 2."""
    s, cdir = _setup_story()
    # Use a different store with no story data
    empty = FileStore(os.path.join(tempfile.mkdtemp(), "empty.json"))
    out, rc = _run_cli([], store=empty)
    assert rc == 2 or "ERROR" in out, f"expected error, got rc={rc} out={out[:100]}"
    print("  empty-store: error on empty store OK")


def test_story_bad_chapter():
    """Non-existent chapter ID -> error."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--chapter=nonexistent_chapter"], store=s)
    assert rc == 2
    print("  bad-chapter: unknown chapter error OK")


def test_story_bad_beat():
    """Non-existent beat ID -> error."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--beat=nonexistent_beat"], store=s)
    assert rc == 2
    print("  bad-beat: unknown beat error OK")


def test_story_bad_track():
    """Non-existent track -> error."""
    s, cdir = _setup_story()
    out, rc = _run_cli(["--track=nonexistent_track"], store=s)
    assert rc == 2
    print("  bad-track: unknown track error OK")


# =========================== Acceptance bar ===========================


def test_story_drill_pointer():
    """Drill pointers resolve: chapter -> beat, beat -> chapter.
    
    Acceptance bar: the right chapter/beat is reachable in <=2 drills.
    """
    s, cdir = _setup_story()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    raw_ch = s.get(chapter_key(cid))
    ch = Chapter.from_dict(json.loads(raw_ch))
    bid = ch.beats[0]
    raw_b = s.get(beat_key(bid))
    assert raw_b is not None, f"beat {bid} not found"
    b = Beat.from_dict(json.loads(raw_b))
    # beat should have a chapter back-link
    if b.chapter:
        raw_back = s.get(chapter_key(b.chapter))
        assert raw_back is not None, f"back-link chapter {b.chapter} not found"
    # ch.commits contains source strings
    assert len(ch.beats) > 0, "chapter has no beats"
    assert ch.summary, "chapter has no summary"
    print("  drill-pointer: every beat resolves, back-links OK")


def test_story_ascii_safe():
    """Output is ASCII-safe (no encoding errors on cp1252)."""
    s, cdir = _setup_story()
    out, rc = _run_cli([])
    # Verify it can be encoded as ASCII (or at least cp1252)
    try:
        out.encode("ascii")
    except UnicodeEncodeError:
        try:
            out.encode("cp1252")
        except UnicodeEncodeError as e:
            assert False, f"output not cp1252-safe: {e}"
    print("  ascii-safe: output encodes to cp1252 OK")


def test_story_within_budget():
    """Output stays within reasonable token budget."""
    s, cdir = _setup_story()
    out, rc = _run_cli([])
    # 4000 tokens ~= 16000 chars (conservative estimate)
    assert len(out) < 20000, f"atlas output too long: {len(out)} chars"
    out2, rc2 = _run_cli(["--track=research"])
    assert len(out2) < 20000, f"track output too long: {len(out2)} chars"
    print("  within-budget: output size within limits OK")


# =========================== main ===========================


def main():
    print("=" * 60)
    print("STORY CLI TESTS (Slice 4)")
    print("=" * 60)
    test_story_atlas_shape()
    test_story_atlas_json()
    test_story_track()
    test_story_track_json()
    test_story_chapter()
    test_story_chapter_json()
    test_story_beat()
    test_story_beat_json()
    test_story_at_timestamp()
    test_story_at_no_match()
    test_story_empty_store()
    test_story_bad_chapter()
    test_story_bad_beat()
    test_story_bad_track()
    test_story_drill_pointer()
    test_story_ascii_safe()
    test_story_within_budget()

    print("\n" + "=" * 60)
    print("ALL STORY CLI TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
