"""
Chronicler (Slice 3) — distill narrative Beats into Chapters + Storyline + Atlas.

Semantic Relationship: Chapters chronicled_from Beats (distilled, time-windowed)

Generalizes core/learning/consolidation.py (rule of three — the third user after
LearningStore and AgentMemory). Pipeline:

1. collect: read Beats from BeatLog within a time window
2. group: partition by Track (each Track gets its own chapter sequence)
3. segment: BoundaryDetector finds chapter boundaries within each Track
4. build: for each segment, Ranker + Distiller → Chapter summary + beat list
5. rollup: Storyline per Track + Atlas across Tracks
6. persist: write Chapters/Track chapter lists/Atlas to Store
7. render: chronicles/story.md + chronicles/story.index.json

Store namespace (written):
  narr:chapter:<id>        -> Chapter as JSON
  narr:track:<track>       -> Track with chapters list updated
  narr:atlas:current       -> Atlas as JSON
  narr:beat:<id>.chapter   -> back-link (bidirectional provenance)

Read-only on beat raw data. Best-effort: failures never raise into caller.
"""
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.foundation.store import Store, create_store
from core.foundation.timeutil import to_epoch, hours_between
from core.narrative.beat_log import BeatLog, get_beat_log
from core.narrative.schema import (
    Beat, Chapter, Track, Theme, Atlas, Edge,
    beat_key, chapter_key, track_key, theme_key, ATLAS_KEY,
    validate_beat, STORY_FORMAT_VERSION, BOUNDARY_KINDS,
)
from core.narrative.chapter_lifecycle import (
    persist_chapter_in_place,
    rebuild_track_chapter_list,
    write_learning_chapter_backlinks,
)
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller

TIMELINE = "narr:beats:timeline"
ROUTER_ACTIVE = "narr:router:active"


# Timezone-safe comparison (D4): naive == UTC, so mixed naive/tz-aware beats sort and
# gap-measure consistently instead of mis-ordering / silently collapsing to a 0.0 gap.
_epoch = to_epoch
_hour_gap = hours_between


class BoundaryDetector:
    """Find chapter boundaries within a per-Track Beat sequence.

    Heuristic triggers (ES-Mem/HingeMem boundary research, reduced to cheap signals):
    - explicit: a beat whose kind is in BOUNDARY_KINDS (an agent-declared `mark`) —
      always cuts, regardless of weight/time. This is the human-in-the-loop signal.
    - time_gap: >min_gap_hours since the previous beat (session boundary)
    - milestone: a weight >= salience_weight beat (salience spike)

    Tunable; over-segmentation is mergeable later.
    Deterministic: same input → same cuts.
    """

    def __init__(self, min_gap_hours: float = 4.0, salience_weight: int = 5):
        self.min_gap_hours = min_gap_hours
        self.salience_weight = salience_weight

    def detect(self, beats: List[Beat]) -> List[int]:
        """Return cut indices marking chapter start positions.

        Each index i means: a new chapter starts at beat i.
        [0, 3, 7] -> chapters: beats[0:3], beats[3:7], beats[7:]

        Always includes 0. Consecutive identical cuts are merged.
        Empty input -> [0] (one empty chapter).
        """
        if not beats:
            return [0]
        cuts = {0}
        for i in range(1, len(beats)):
            if self._is_boundary(beats, i):
                cuts.add(i)
        out = sorted(cuts)
        return out

    def _is_boundary(self, beats: List[Beat], i: int) -> bool:
        """Would beat[i] start a new chapter given beat[i-1]?"""
        prev = beats[i - 1]
        curr = beats[i]
        if curr.kind in BOUNDARY_KINDS:          # explicit mark_chapter — always cuts
            return True
        if _hour_gap(prev.at, curr.at) >= self.min_gap_hours:
            return True
        if curr.weight >= self.salience_weight:
            return True
        return False


class Chronicler:
    """Windowed distillation of narrative Beats into Chapters + Storyline + Atlas.

    Main entry points:
      chronicle_window(start_iso, end_iso)  — process a specific time range
      chronicle_all()                       — full rebuild from all stored beats

    Injects dependency seams for testability and future upgrades:
    ranker, distiller, boundary_detector, token_budget.
    Read-only on beat data; never mutates raw beats.
    Best-effort: never raises.
    """

    TOKEN_BUDGET = 4000
    MAX_CHARS_PER_ENTRY = 170

    def __init__(
        self,
        beat_log: Optional[BeatLog] = None,
        store: Optional[Store] = None,
        ranker: Optional[Ranker] = None,
        distiller: Optional[Distiller] = None,
        boundary_detector: Optional[BoundaryDetector] = None,
        token_budget: int = TOKEN_BUDGET,
        chronicle_dir: Optional[str] = None,
    ):
        self.beat_log = beat_log or get_beat_log()
        self.store = store or create_store()
        self.ranker = ranker or Ranker()
        self.distiller = distiller or Distiller(
            max_chars_per_entry=self.MAX_CHARS_PER_ENTRY
        )
        self.boundary_detector = boundary_detector or BoundaryDetector()
        self.token_budget = token_budget
        base = (
            Path(chronicle_dir)
            if chronicle_dir
            else Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "chronicles"
        )
        self.chronicle_dir = base

    # ---- public API ----

    def chronicle_window(
        self, start_iso: str, end_iso: str, now: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chronicle all Beats in [start_iso, end_iso). Returns report dict."""
        beats = self.beat_log.in_window(start_iso, end_iso)
        return self._chronicle(beats, start_iso, end_iso, now=now)

    def chronicle_all(self, now: Optional[str] = None) -> Dict[str, Any]:
        """Full rebuild from all stored beats. Idempotent (same data → same output)."""
        raw = self.store.zrange(TIMELINE, 0, -1)
        beats: List[Beat] = []
        for bid in raw:
            b = self._load_beat(bid)
            if b is not None:
                beats.append(b)
        if not beats:
            return self._empty_report()
        beats.sort(key=lambda b: to_epoch(b.at))
        return self._chronicle(beats, beats[0].at, beats[-1].at, now=now)

    # ---- core pipeline ----

    def _chronicle(
        self, beats: List[Beat], start_iso: str, end_iso: str,
        now: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not beats:
            return self._empty_report()

        now_iso = now or datetime.utcnow().isoformat()

        by_track: Dict[str, List[Beat]] = defaultdict(list)
        for b in beats:
            by_track[b.track or "unknown"].append(b)

        chapters: List[Chapter] = []
        for track, track_beats in sorted(by_track.items()):
            track_beats.sort(key=lambda x: to_epoch(x.at))
            cuts = self.boundary_detector.detect(track_beats)
            for seg_i in range(len(cuts) - 1):
                seg = track_beats[cuts[seg_i]:cuts[seg_i + 1]]
                if seg:
                    chapters.append(self._build_chapter(track, seg, seg_i, now=now_iso))
            if cuts:
                seg = track_beats[cuts[-1]:]
                if seg:
                    chapters.append(
                        self._build_chapter(track, seg, len(cuts) - 1, now=now_iso)
                    )

        chapters.sort(key=lambda c: to_epoch(c.span_start))

        storyline = self._build_storyline(chapters)
        atlas = self._build_atlas(chapters, start_iso, end_iso, now=now_iso)

        self._persist(chapters, atlas)

        result = self._render(atlas, chapters, storyline, now=now_iso)

        return {
            "chapters": len(chapters),
            "tracks": len(by_track),
            "total_beats": len(beats),
            "beats_by_track": {t: len(v) for t, v in sorted(by_track.items())},
            "story_md": str(result["story_md"]),
            "story_json": str(result["story_json"]),
            "faithful": result["faithful"],
            "coverage": result["coverage"],
        }

    def _build_chapter(
        self, track: str, beats: List[Beat], seg_index: int,
        now: Optional[str] = None,
    ) -> Chapter:
        """Distill a segment of Beats into a Chapter (mid view).

        Uses Ranker + Distiller to produce a budgeted summary with lossless
        source pointers. Every entry in the summary resolves to a real Beat source.
        """
        items = []
        for b in beats:
            items.append(
                {
                    "text": b.summary,
                    "importance": b.weight,
                    "timestamp": b.at,
                    "source": b.source,
                    "relationship_type": b.relates[0].type if b.relates else None,
                }
            )

        now_ts = _epoch(now) if now else None
        ranked = [s.item for s in self.ranker.rank(items, query="", now=now_ts)]
        distillation = self.distiller.distill(
            ranked,
            token_budget=self.token_budget,
            instruction=f"chapter summary for {track}",
            kind="beat",
        )

        span_start = beats[0].at
        span_end = beats[-1].at

        raw = f"{track}_{seg_index}_{span_start}"
        ch_id = f"chapter_{hashlib.md5(raw.encode()).hexdigest()[:12]}"

        # An explicit `mark` names its own chapter; otherwise the most salient beat
        # (highest weight, then latest) supplies the title.
        marks = [b for b in beats if b.kind in BOUNDARY_KINDS]
        best = marks[0] if marks else max(beats, key=lambda b: (b.weight, b.at))
        title = (best.summary[:77] + "...") if len(best.summary) > 80 else best.summary

        beat_ids = [b.id for b in beats]
        commits_list = [b.source for b in beats if b.source.startswith("git:")]
        learnings_list = [b.source for b in beats if b.source.startswith("learn:")]

        chapter = Chapter(
            id=ch_id,
            track=track,
            title=title,
            span_start=span_start,
            span_end=span_end,
            summary=distillation.skeleton or "(no salient events)",
            beats=beat_ids,
            learnings=learnings_list,
            commits=commits_list,
            relates=[
                Edge("part_of", f"narr:track:{track}"),
            ],
            recorded_at=now or datetime.utcnow().isoformat(),
            valid_from=span_start,
            critic_ok=distillation.critic_ok,
        )
        return chapter

    def _build_storyline(self, chapters: List[Chapter]) -> Dict[str, List[str]]:
        """Group chapter IDs by track, in temporal order."""
        by_track: Dict[str, List[str]] = defaultdict(list)
        for ch in chapters:
            by_track[ch.track].append(ch.id)
        return dict(by_track)

    def _build_atlas(
        self, chapters: List[Chapter], start_iso: str, end_iso: str,
        now: Optional[str] = None,
    ) -> Atlas:
        """The broad view across all Tracks over the window."""
        tracks = sorted({ch.track for ch in chapters})
        summary_parts = []
        for t in tracks:
            count = sum(1 for ch in chapters if ch.track == t)
            summary_parts.append(f"{t}: {count} chapter(s)")
        summary = "; ".join(summary_parts)
        return Atlas(
            generated_at=now or datetime.utcnow().isoformat(),
            summary=summary,
            tracks=tracks,
        )

    # ---- persistence ----

    def _persist(self, chapters: List[Chapter], atlas: Atlas) -> None:
        """Write chapters, back-links, track refs, and atlas to the Store.

        Chapters keep their deterministic ids (regenerate-in-place); track lists are
        rebuilt to active, resolvable chapters only (no stale/superseded accumulation).
        """
        for ch in chapters:
            # Per-chapter best-effort: one bad chapter must not abort the whole
            # chronicle (the Atlas is written last; losing it would blank the story).
            try:
                persist_chapter_in_place(self.store, ch)
                write_learning_chapter_backlinks(self.store, ch)
                for bid in ch.beats:
                    raw = self.store.get(beat_key(bid))
                    if raw:
                        try:
                            b = Beat.from_dict(json.loads(raw))
                            b.chapter = ch.id          # bidirectional back-link
                            self.store.set(beat_key(b.id), json.dumps(b.to_dict()))
                        except Exception:
                            pass
            except Exception:
                continue

        by_track: Dict[str, List[str]] = defaultdict(list)
        for ch in chapters:
            by_track[ch.track].append(ch.id)
        for track_id, cids in by_track.items():
            try:
                rebuild_track_chapter_list(self.store, track_id, cids)
            except Exception:
                continue

        # Theme index: accumulate EVERY member beat (a theme is multi-beat AND
        # cross-track), loading each Theme once per run then writing it back.
        theme_cache: Dict[str, Theme] = {}
        for ch in chapters:
            for bid in ch.beats:
                raw = self.store.get(beat_key(bid))
                if not raw:
                    continue
                try:
                    b = Beat.from_dict(json.loads(raw))
                    beat_dirty = False
                    for th in b.themes:
                        if th not in theme_cache:
                            existing = self.store.get(theme_key(th))
                            theme_cache[th] = (
                                Theme.from_dict(json.loads(existing)) if existing
                                else Theme(id=th, title=th, beats=[])
                            )
                        t = theme_cache[th]
                        if bid not in t.beats:
                            t.beats.append(bid)
                        edge_target = f"narr:theme:{th}"
                        if not any(e.target == edge_target for e in b.relates):
                            b.relates.append(Edge("member_of", edge_target))
                            beat_dirty = True
                    if beat_dirty:
                        b.chapter = ch.id
                        self.store.set(beat_key(bid), json.dumps(b.to_dict()))
                except Exception:
                    pass
        for th, t in theme_cache.items():
            self.store.set(theme_key(th), json.dumps(t.to_dict()))
        self.store.set(ATLAS_KEY, json.dumps(atlas.to_dict()))

    # ---- rendering ----

    def _render(
        self, atlas: Atlas, chapters: List[Chapter],
        storyline: Dict[str, List[str]], now: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write chronicles/story.md + chronicles/story.index.json.

        Returns dict with paths + faithfulness + coverage metrics.
        """
        self.chronicle_dir.mkdir(parents=True, exist_ok=True)
        now_iso = now or datetime.utcnow().isoformat()

        chapters.sort(key=lambda c: to_epoch(c.span_start))

        md_lines = [
            f"# Story — generated {now_iso}",
            "",
            f"Version: {STORY_FORMAT_VERSION}",
            "",
            "## Atlas",
        ]
        for t in atlas.tracks:
            count = sum(1 for ch in chapters if ch.track == t)
            md_lines.append(f"- **{t}**: {count} chapter(s)")
        md_lines.extend(
            [
                "",
                f"Summary: {atlas.summary}",
                "",
            ]
        )

        for ch in chapters:
            md_lines.extend(
                [
                    f"## {ch.title} ({ch.track})",
                    f"Span: {ch.span_start} \u2192 {ch.span_end or 'present'}",
                    f"Beats: {len(ch.beats)}  \u00b7 Critic: {ch.critic_ok}",
                    "",
                    ch.summary,
                    "",
                ]
            )

        md_path = self.chronicle_dir / "story.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        index = {
            "version": STORY_FORMAT_VERSION,
            "generated_at": now_iso,
            "atlas": atlas.to_dict(),
            "storyline": storyline,
            "chapters": [ch.to_dict() for ch in chapters],
        }
        json_path = self.chronicle_dir / "story.index.json"
        json_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

        faithful, coverage = self._compute_metrics(chapters)
        return {
            "story_md": md_path,
            "story_json": json_path,
            "faithful": faithful,
            "coverage": coverage,
        }

    _SOURCE_RE = re.compile(r"\(source:\s*([^)]+?)\s*\)")

    def _compute_metrics(
        self, chapters: List[Chapter]
    ) -> tuple:
        """Compute faithfulness and coverage -- the two real acceptance bars.

        Faithfulness (bar = 100%): EVERY `(source: X)` claim in a chapter summary
        must resolve to the source of a Beat actually belonging to that chapter. A
        claim pointing at a beat that isn't in the chapter is a fabricated pointer.

        Coverage (bar >= 95%): of all weight->=4 Beats, the fraction whose source
        actually appears in their chapter's distilled summary. This DROPS when the
        Distiller has to omit a high-weight Beat to fit the budget -- the whole point
        of measuring it (the old check compared a set against itself and was pinned
        at 100%).
        """
        faithful = True
        for ch in chapters:
            if not ch.beats:
                faithful = False
                break
            chapter_sources = set()
            for bid in ch.beats:
                b = self._load_beat(bid)
                if b is not None and b.source:
                    chapter_sources.add(b.source)
            for claimed in self._SOURCE_RE.findall(ch.summary or ""):
                if claimed not in chapter_sources:
                    faithful = False
                    break
            if not faithful:
                break

        high_weight = 0
        covered = 0
        for ch in chapters:
            summary = ch.summary or ""
            for bid in ch.beats:
                b = self._load_beat(bid)
                if b is None or b.weight < 4:
                    continue
                high_weight += 1
                if b.source and b.source in summary:
                    covered += 1

        coverage_pct = (covered / high_weight * 100) if high_weight > 0 else 100.0
        return faithful, round(coverage_pct, 1)

    def _load_beat(self, beat_id: str) -> Optional[Beat]:
        raw = self.store.get(beat_key(beat_id))
        if not raw:
            return None
        try:
            return Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            return None

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "chapters": 0,
            "tracks": 0,
            "total_beats": 0,
            "beats_by_track": {},
            "story_md": "",
            "story_json": "",
            "faithful": True,
            "coverage": 100.0,
        }
