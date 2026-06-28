"""
Session lifecycle (Slice 1 auto-capture) -- the spine fills itself.

Semantic Relationship: SessionStart/SessionEnd Beats bound a default Chapter

The narrative spine should accrete WITHOUT an agent remembering to log. The only
durable lifecycle signals we control in-process are:

  - boot (bootstrap.py)  -> a session begins
  - session-end (CLI)    -> a session is explicitly closed

Because external agents shell out one short-lived process per command, there is no
long-lived process to hang an `atexit` on. So auto-capture is anchored on boot:
``start_session`` first CLOSES any still-open prior session (emitting its session-end
Beat and re-chronicling), then opens a new one. Net effect: every boot finalises the
previous session's story, so the chronicle and boot-feed stay fresh on their own.

A single marker key tracks the open session:
    narr:session:open -> ISO timestamp of the open session's start

Best-effort throughout: a hiccup here must never block boot or any CLI command.
"""
from datetime import datetime
from typing import Optional

from core.foundation.store import Store, create_store
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint

SESSION_OPEN_KEY = "narr:session:open"


def _capture_session(summary: str, ref: str, *, at: str, detail: Optional[dict] = None) -> None:
    """Auto-logger (Slice 2): mirror a session boundary into the RAW event firehose, so the
    full-fidelity timeline shows session spans too. Best-effort -- never blocks the session."""
    try:
        from core.events.event_log import capture_event
        capture_event("session", summary, agent_id="system", at=at, refs=[ref], detail=detail)
    except Exception:
        pass


def _chronicle(store: Store, bl: BeatLog, now: str) -> None:
    """Re-distill the spine (best-effort). Imported lazily to avoid a heavy import
    on the hot boot path when chronicling is disabled."""
    from core.narrative.health import bump
    try:
        from core.narrative.chronicler import Chronicler
        Chronicler(beat_log=bl, store=store).chronicle_all(now=now)
        bump(store, "chronicle:run")
    except Exception:
        bump(store, "chronicle:error")     # the story stopped refreshing -- make it visible


def start_session(store: Optional[Store] = None, *, now: Optional[str] = None,
                  chronicle: bool = True) -> dict:
    """Open a session, auto-closing any prior open one first.

    Returns a small report: ``{"closed_prior": bool, "start": iso}``. Never raises.
    """
    report = {"closed_prior": False, "start": None}
    try:
        store = store if store is not None else create_store()
        bl = BeatLog(store)
        now_iso = now or datetime.utcnow().isoformat()

        prior = store.get(SESSION_OPEN_KEY)
        if prior:
            bl.emit("session", "Session ended", "session:end", at=now_iso,
                    hint=RouteHint(category="meta", task="session"))
            _capture_session("Session ended (auto-closed on boot)", "session:end", at=now_iso,
                             detail={"start": prior, "end": now_iso})
            store.delete(SESSION_OPEN_KEY)
            report["closed_prior"] = True
            if chronicle:
                _chronicle(store, bl, now_iso)

        bl.emit("session", "Session started", "session:start", at=now_iso,
                hint=RouteHint(category="meta", task="session"))
        _capture_session("Session started", "session:start", at=now_iso)
        store.set(SESSION_OPEN_KEY, now_iso)
        report["start"] = now_iso
    except Exception:
        pass
    return report


def end_session(store: Optional[Store] = None, *, now: Optional[str] = None,
                chronicle: bool = True) -> dict:
    """Explicitly close the current session and re-chronicle.

    Idempotent: emits the session-end Beat only when a session is actually open, so
    repeated calls don't litter the timeline with orphan ends -- but always
    re-chronicles so a manual ``story --session-end`` still refreshes the story.
    Returns ``{"closed": bool}``. Never raises.
    """
    report = {"closed": False}
    try:
        store = store if store is not None else create_store()
        bl = BeatLog(store)
        now_iso = now or datetime.utcnow().isoformat()

        if store.get(SESSION_OPEN_KEY):
            bl.emit("session", "Session ended", "session:end", at=now_iso,
                    hint=RouteHint(category="meta", task="session"))
            _capture_session("Session ended", "session:end", at=now_iso)
            store.delete(SESSION_OPEN_KEY)
            report["closed"] = True
        if chronicle:
            _chronicle(store, bl, now_iso)
    except Exception:
        pass
    return report
