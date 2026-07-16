"""Session bookends -- the live EPISODE layer over the narrative Chapter (Slice S1).

Semantic Relationship: an Episode IS a Chapter with an open span + intent (`why`)

An episode is a confined, titled stretch of a session carrying WHAT (title + description) and WHY
(intent). Per the DeepSeek design review (2026-07-07, research/reviewed/), an episode is NOT a new
record type -- it is a narrative `Chapter` with a mandatory `why`, plus one piece of live state the
retrospective Chronicler never needed: a pointer to the currently-OPEN episode (span_end still None),
mirroring `narr:session:open`. This module owns that lifecycle: open -> accrue beats -> close+draft
-> accept. Drafting is deterministic over the closed span's beats, with an injectable `writer` seam
for an optional LLM paraphrase (the Distiller pattern) -- core stays no-LLM by default.

Best-effort + fail-soft throughout: a bookend hiccup must never break boot, a CLI command, or a session.
"""
import json
import random
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.foundation.store import Store, create_store
from core.foundation.timeutil import to_epoch as _epoch
from core.narrative.beat_log import BeatLog, ROUTER_ACTIVE
from core.narrative.chapter_lifecycle import load_chapter_from_store, persist_chapter_in_place
from core.narrative.schema import Chapter
from core.narrative.track_router import RouteHint

EPISODE_OPEN_KEY = "narr:episode:open"   # JSON {chapter_id, start, track} -- the one open episode
_DEFAULT_TRACK = "ai-setup"


def _now(now: Optional[str]) -> str:
    return now or datetime.utcnow().isoformat()


def _dur(start_iso: str, end_iso: str) -> int:
    try:
        return max(0, int(_epoch(end_iso) - _epoch(start_iso)))
    except Exception:
        return 0


def _load_open(store: Store) -> Optional[Dict[str, Any]]:
    try:
        raw = store.get(EPISODE_OPEN_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def open_episode(store: Optional[Store] = None, *, now: Optional[str] = None,
                 track: Optional[str] = None) -> Optional[Chapter]:
    """Open a fresh episode: a new Chapter with an OPEN span (span_end=None) that beats accrue to.
    Sets the `narr:episode:open` pointer. Returns the Chapter (or None on failure). Never raises."""
    try:
        store = store if store is not None else create_store()
        now_iso = _now(now)
        track = track or store.get(ROUTER_ACTIVE) or _DEFAULT_TRACK
        cid = f"ch_{int(_epoch(now_iso))}_{random.randint(1000, 9999)}"
        ch = Chapter(id=cid, track=track, title="", span_start=now_iso)
        persist_chapter_in_place(store, ch, now=now_iso)
        store.set(EPISODE_OPEN_KEY, json.dumps({"chapter_id": cid, "start": now_iso, "track": track}))
        return ch
    except Exception:
        return None


def _current_chapter(store: Store, *, now: str, auto_open: bool) -> Optional[Chapter]:
    rec = _load_open(store)
    ch = load_chapter_from_store(store, rec["chapter_id"]) if rec else None
    if ch is None and auto_open:                     # no pointer, or it dangles -> open one (migration-safe)
        ch = open_episode(store, now=now)
    return ch


def current_episode(store: Optional[Store] = None, *, now: Optional[str] = None,
                    auto_open: bool = True) -> Dict[str, Any]:
    """The live current episode as the UI contract (`episode current --json`). Auto-opens one if none
    exists (so the panel always has a current). `suggestion` stays None HERE: the door (agent_cli
    `episode current`) composes it from episode_suggester.suggest() -- suggester imports this module
    for draft_fields, so the dependency must stay one-way."""
    store = store if store is not None else create_store()
    now_iso = _now(now)
    ch = _current_chapter(store, now=now_iso, auto_open=auto_open)
    if ch is None:
        return {"current_chapter": None}
    beats = content_beats(BeatLog(store).in_window(ch.span_start, now_iso))
    return {"current_chapter": {
        "id": ch.id, "title": ch.title, "description": ch.summary, "why": ch.why,
        "started": ch.span_start, "duration_seconds": _dur(ch.span_start, now_iso),
        "beats_count": len(beats), "suggestion": None}}


# ---- drafting {title, description, why} over a closed span (deterministic + optional writer seam) ----

def _draft_title(beats: List[Any]) -> str:
    if not beats:
        return "Untitled episode"
    top = max(beats, key=lambda b: (getattr(b, "weight", 1) or 1))
    return (top.summary or "Untitled episode")[:120]


def _draft_description(beats: List[Any]) -> str:
    """The few most-salient non-session beats, joined -- a deterministic one-liner of WHAT happened."""
    sal = sorted([b for b in beats if getattr(b, "kind", "") != "session"],
                 key=lambda b: (getattr(b, "weight", 1) or 1), reverse=True)[:3]
    return " · ".join(b.summary for b in sal if b.summary)[:400]


def _draft_why(beats: List[Any], *, writer: Optional[Callable] = None) -> str:
    """WHY = the episode's intent. Primary source (DeepSeek review): the LATEST decision/mark beat in
    the span (the "we're doing this because..." moment), task title secondary. An optional injected
    `writer(basis, beats)->str` LLM seam may paraphrase; default stays deterministic + fail-soft."""
    intent = [b for b in beats if getattr(b, "kind", "") in ("decision", "mark")]
    basis = (intent[-1].summary if intent else (beats[0].summary if beats else "")) or ""
    if writer:
        try:
            w = writer(basis, beats)
            if w:
                return str(w)[:300]
        except Exception:
            pass
    return basis[:300]


_BOUNDARY_SOURCE_PREFIX = "episode:close:"


def content_beats(beats: List[Any]) -> List[Any]:
    """Drop episode-BOUNDARY marker beats (the `mark` each close emits). The close-mark lands on the
    exact timestamp the next episode opens, so it falls inside the NEXT span's window -- and being
    kind=mark it would otherwise become that episode's drafted `why` ("Episode closed: ...") and a
    phantom input to the S3 triggers. Boundary beats stay in Chapter.beats (provenance); they are
    just not CONTENT. Found by the S3 noise tests, 2026-07-08."""
    return [b for b in beats if not str(getattr(b, "source", "")).startswith(_BOUNDARY_SOURCE_PREFIX)]


def draft_fields(beats: List[Any], *, writer: Optional[Callable] = None) -> Dict[str, str]:
    """The {title, description, why} draft over a span's CONTENT beats -- the ONE drafting source,
    used by close_episode and by the S3 suggester (contract #6: a suggestion matches the draft)."""
    beats = content_beats(beats)
    return {"title": _draft_title(beats), "description": _draft_description(beats),
            "why": _draft_why(beats, writer=writer)}


def close_episode(store: Optional[Store] = None, *, now: Optional[str] = None,
                  title: Optional[str] = None, description: Optional[str] = None,
                  why: Optional[str] = None, finalize: bool = False,
                  writer: Optional[Callable] = None, open_next: bool = True) -> Dict[str, Any]:
    """Close the current episode: draft {title, description, why} over its span's beats (user-supplied
    fields win over the draft), stamp span_end, emit a `mark` boundary beat, and open the next episode.
    Returns {draft, new_current_chapter} (the UI contract). `finalize=True` = the one-shot agent path
    that accepts the draft immediately. `open_next=False` (session-end force-close) leaves NO open
    episode instead of starting a fresh one. Never raises."""
    try:
        store = store if store is not None else create_store()
        now_iso = _now(now)
        ch = _current_chapter(store, now=now_iso, auto_open=True)
        if ch is None:
            return {"draft": None, "new_current_chapter": None}
        beats = BeatLog(store).in_window(ch.span_start, now_iso)
        drafted = draft_fields(beats, writer=writer)
        ch.title = title if title is not None else drafted["title"]
        ch.summary = description if description is not None else drafted["description"]
        ch.why = why if why is not None else drafted["why"]
        ch.span_end = now_iso
        ch.beats = [b.id for b in beats]
        ch.final = bool(finalize)
        persist_chapter_in_place(store, ch, now=now_iso)
        BeatLog(store).emit("mark", f"Episode closed: {ch.title}"[:120], f"episode:close:{ch.id}",
                            at=now_iso, hint=RouteHint(category="meta", task="episode"))
        if open_next:
            new_ch = open_episode(store, now=now_iso, track=ch.track)
        else:
            try:
                store.delete(EPISODE_OPEN_KEY)   # session-end: no dangling open episode
            except Exception:
                pass
            new_ch = None
        return {
            "draft": {"chapter_id": ch.id, "title": ch.title,
                      "description": ch.summary, "why": ch.why},
            "new_current_chapter": ({"id": new_ch.id, "started": new_ch.span_start,
                                     "duration_seconds": 0, "suggestion": None}
                                    if new_ch else None),
        }
    except Exception:
        return {"draft": None, "new_current_chapter": None}


def close_open_episode_for_session_end(store: Optional[Store] = None, *, now: Optional[str] = None,
                                       writer: Optional[Callable] = None) -> Dict[str, Any]:
    """T081-W8: resolve the open episode at SESSION END so it never dangles across sessions -- the
    '189h Untitled episode' bug, where sessions came and went while one episode stayed open. Prior
    art: OpenTelemetry spans auto-close when their context exits; an episode's context IS the
    session, so the session ending is its natural close.

      - has CONTENT beats  -> close+draft (open_next=False: leave NO fresh open episode; the next
        session's first current_episode() auto-opens one).
      - EMPTY (no content)  -> just clear the open pointer, creating NO phantom 'Untitled' chapter
        (closing an empty span with a draft is what MINTED the 189h Untitled episode).
      - dangling pointer    -> clear it.

    Returns a short status dict. Never raises -- a bookend hiccup must never block a session ending."""
    try:
        store = store if store is not None else create_store()
        rec = _load_open(store)
        if not rec:
            return {"action": "none"}
        now_iso = _now(now)
        ch = load_chapter_from_store(store, rec.get("chapter_id"))
        if ch is None:                                   # pointer dangles -> clear, nothing to draft
            _clear_open(store)
            return {"action": "cleared_dangling"}
        beats = content_beats(BeatLog(store).in_window(ch.span_start, now_iso))
        if not beats:                                    # empty -> clear, no phantom Untitled chapter
            _clear_open(store)
            return {"action": "cleared_empty", "chapter_id": ch.id}
        res = close_episode(store, now=now_iso, finalize=False, open_next=False, writer=writer)
        return {"action": "closed", "chapter_id": ch.id,
                "title": (res.get("draft") or {}).get("title")}
    except Exception:
        return {"action": "error"}


def _clear_open(store: Store) -> None:
    try:
        store.delete(EPISODE_OPEN_KEY)
    except Exception:
        pass


def accept_episode(store: Optional[Store], chapter_id: str, *, title: Optional[str] = None,
                   description: Optional[str] = None, why: Optional[str] = None,
                   now: Optional[str] = None) -> Dict[str, Any]:
    """Finalize a closed episode: apply any per-field edits and mark it immutable (`final=True`).
    Idempotent -- re-accepting overwrites the same fields. Returns {chapter} or {error}. Never raises."""
    try:
        store = store if store is not None else create_store()
        ch = load_chapter_from_store(store, chapter_id)
        if ch is None:
            return {"error": "unknown_chapter", "chapter_id": chapter_id}
        if title is not None:
            ch.title = title
        if description is not None:
            ch.summary = description
        if why is not None:
            ch.why = why
        ch.final = True
        persist_chapter_in_place(store, ch, now=_now(now))
        return {"chapter": {"id": ch.id, "title": ch.title, "description": ch.summary,
                            "why": ch.why, "final": True}}
    except Exception:
        return {"error": "accept_failed", "chapter_id": chapter_id}
