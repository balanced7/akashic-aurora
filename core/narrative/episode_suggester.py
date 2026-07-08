"""Episode auto-suggester (bookends Slice S3) -- ADVISORY phase-boundary suggestions, never a forced close.

Semantic Relationship: a Suggestion PROPOSES closing the open Episode (human/agent accepts)

Watches the four already-existing phase signals the design locked (docs/session-bookends-design-2026-07.md
D4/D5 + review Q5c) and, when one fires, emits ONE advisory suggestion whose shape matches the close
draft (contract #6: {title, description, why} + {reason, confidence}) so the UI reuses one edit panel:

  * impl-complete     (0.88) -- a task-ledger task went DONE inside this episode's span
  * subsystem-switch  (0.75) -- the last >=2 ROUTED beats (Beat.track, the TrackRouter's verdict)
                                unanimously land on a different track than the episode's
  * new-objective     (0.70) -- a task was claimed/started inside the span (a new WHY began)
  * idle              (0.60) -- no beat for ~15 min (episode-level threshold, DISTINCT from the
                                4h session gap in chronicler.BoundaryDetector)

Poll-evaluated, not daemonized: `suggest()` is called at read time (the `episode current` door; the
UI panel polls it), so there is no loop to supervise. Deterministic + NO-LLM throughout.

NOISE GATES (the slice's acceptance bar: fire on a real switch, NOT on noise): a young episode
(<5 min) or a thin one (<2 beats) never suggests; each distinct trigger fingerprint fires AT MOST
ONCE per episode; replacements respect a 10-min cooldown and must BEAT the standing suggestion's
confidence; an idle suggestion self-clears the moment activity resumes. The standing suggestion is
returned unchanged on every poll (stable for the panel); the durable event fires only on transitions.

SHARED EVENT BUS (review Q5d -- RENEW dedup): each NEW suggestion is also captured as one durable
`episode_suggestion` event on the raw firehose (core/events), the same stream RENEW's future refresh
policy reads -- one phase-boundary detector serves both features, so they can never double-nudge.

Lateral read, by design: new-objective/impl-complete come from the SIBLING coordination layer's read
API (core/coord/task_ledger.read_ledger) -- the locked design names it as the trigger source. The
import is function-local + fail-soft: without coord, those two triggers silently degrade and the
switch/idle triggers still work. Best-effort everywhere; a suggester hiccup must never break a door.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.store import Store, create_store
from core.foundation.timeutil import to_epoch as _epoch
from core.narrative.beat_log import BeatLog
from core.narrative.chapter_lifecycle import load_chapter_from_store
from core.narrative.episode import EPISODE_OPEN_KEY, content_beats, draft_fields

SUGGEST_STATE_KEY = "narr:episode:suggestion:state"   # {chapter_id, fingerprints, last_at, active}

CONFIDENCE = {          # deterministic per-trigger confidence (contract example: impl-complete 0.88)
    "impl-complete": 0.88,
    "subsystem-switch": 0.75,
    "new-objective": 0.70,
    "idle": 0.60,
}
IDLE_S = 900            # episode-level idle (review Q5c) -- NOT the 4h session gap
MIN_SPAN_S = 300        # a just-opened episode never suggests (anti rapid-fire after each close)
MIN_BEATS = 2           # a thin episode has nothing worth bookending
COOLDOWN_S = 600        # min gap between DIFFERENT suggestions for the same episode
_SWITCH_WINDOW = 3      # switch looks at the last N routed beats...
_SWITCH_MIN_BEATS = 2   # ...and needs >=2 of them, unanimous, on a non-episode track


def _now(now: Optional[str]) -> str:
    return now or datetime.utcnow().isoformat()


# ---- pure trigger evaluation (unit-testable without a store) ---------------------------------------

def evaluate(*, chapter_track: str, span_start: str, beats: List[Any],
             task_events: List[Tuple[str, str, float]],
             now: str) -> Optional[Dict[str, Any]]:
    """All four triggers over already-loaded state -> the single strongest candidate
    {reason, confidence, fingerprint}, or None. `task_events` = (kind, task_id, at_epoch) with
    kind in {"new-objective", "impl-complete"}. Pure + deterministic; noise gates first.

    Subsystem-switch reads the ROUTED BEATS (Beat.track, set by the TrackRouter), not the live
    router key: emitting any beat moves `narr:router:active` as a side effect, so the raw key
    fires on router drift (found by this slice's own noise test). The honest signal is the last
    >=2 routed beats UNANIMOUSLY landing on a different track than the episode's -- one stray
    beat is noise and stays silent."""
    try:
        now_ep = _epoch(now)
        start_ep = _epoch(span_start)
    except Exception:
        return None
    if now_ep - start_ep < MIN_SPAN_S or len(beats) < MIN_BEATS:
        return None

    candidates: List[Dict[str, Any]] = []

    for kind, tid, at_ep in task_events:
        if kind in CONFIDENCE and start_ep <= at_ep <= now_ep:
            candidates.append({"reason": kind, "confidence": CONFIDENCE[kind],
                               "fingerprint": f"{kind}:{tid}"})

    recent = [getattr(b, "track", None) for b in beats[-_SWITCH_WINDOW:]]
    recent = [t for t in recent if t]
    if (chapter_track and len(recent) >= _SWITCH_MIN_BEATS
            and len(set(recent)) == 1 and recent[0] != chapter_track):
        candidates.append({"reason": "subsystem-switch", "confidence": CONFIDENCE["subsystem-switch"],
                           "fingerprint": f"subsystem-switch:{recent[0]}"})

    newest = beats[-1] if beats else None
    if newest is not None:
        try:
            if now_ep - _epoch(getattr(newest, "at", "") or "") >= IDLE_S:
                candidates.append({"reason": "idle", "confidence": CONFIDENCE["idle"],
                                   "fingerprint": f"idle:{getattr(newest, 'id', '?')}"})
        except Exception:
            pass

    if not candidates:
        return None
    return max(candidates, key=lambda c: c["confidence"])   # ties: first wins (dict order above)


def _task_events(ledger_path: Optional[str]) -> List[Tuple[str, str, float]]:
    """Task-ledger history -> trigger events. Lateral coord read (see module docstring); fail-soft
    to [] so a missing/broken ledger only degrades these two triggers."""
    try:
        from core.coord.task_ledger import read_ledger, LEDGER_PATH
        led = read_ledger(ledger_path or LEDGER_PATH, client=None)   # git file = truth; no Redis dep
        out: List[Tuple[str, str, float]] = []
        for t in led.get("tasks", []):
            for h in t.get("history", []):
                to, at = h.get("to"), h.get("at")
                if not at:
                    continue
                try:
                    at_ep = _epoch(at)
                except Exception:
                    continue
                if to in ("claimed", "in_progress"):
                    out.append(("new-objective", t.get("id", "?"), at_ep))
                elif to == "done":
                    out.append(("impl-complete", t.get("id", "?"), at_ep))
        return out
    except Exception:
        return []


# ---- stateful shell: dedup + cooldown + standing suggestion + bus emission -------------------------

def _load_state(store: Store) -> Dict[str, Any]:
    try:
        raw = store.get(SUGGEST_STATE_KEY)
        st = json.loads(raw) if raw else {}
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


def _save_state(store: Store, st: Dict[str, Any]) -> None:
    try:
        store.set(SUGGEST_STATE_KEY, json.dumps(st))
    except Exception:
        pass


def suggest(store: Optional[Store] = None, *, now: Optional[str] = None,
            ledger_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The advisory suggestion for the OPEN episode, or None. Idempotent at read time: the standing
    suggestion is returned on every poll until it is replaced (stronger trigger, post-cooldown),
    invalidated (idle broken by new activity), or the episode closes (chapter id changes). Emits one
    durable `episode_suggestion` event per NEW suggestion (the RENEW-shared bus). Never raises."""
    try:
        store = store if store is not None else create_store()
        now_iso = _now(now)
        rec = store.get(EPISODE_OPEN_KEY)
        rec = json.loads(rec) if rec else None
        ch = load_chapter_from_store(store, rec["chapter_id"]) if rec else None
        if ch is None:
            return None
        # CONTENT beats only: the previous episode's close-mark shares this span's start timestamp
        # and must not count toward thin-gates, idle recency, switch unanimity, or the draft.
        beats = content_beats(BeatLog(store).in_window(ch.span_start, now_iso))
        st = _load_state(store)
        if st.get("chapter_id") != ch.id:                      # fresh episode -> fresh slate
            st = {"chapter_id": ch.id, "fingerprints": [], "last_at": None, "active": None}

        active = st.get("active")
        newest_id = getattr(beats[-1], "id", None) if beats else None
        if active and str(active.get("fingerprint", "")).startswith("idle:") \
                and f"idle:{newest_id}" != active.get("fingerprint"):
            active = None                                      # activity resumed -> idle self-clears
            st["active"] = None
            _save_state(store, st)

        cand = evaluate(chapter_track=ch.track or "", span_start=ch.span_start, beats=beats,
                        task_events=_task_events(ledger_path), now=now_iso)

        if cand is None or cand["fingerprint"] in st.get("fingerprints", []):
            return _public(active)                             # nothing new -> the standing view
        if active is not None and cand["confidence"] <= active.get("confidence", 0.0):
            return _public(active)                             # only a STRONGER trigger replaces
        last_at = st.get("last_at")
        if last_at:
            try:
                if _epoch(now_iso) - _epoch(last_at) < COOLDOWN_S:
                    return _public(active)                     # too soon after the previous one
            except Exception:
                pass

        suggestion = {**draft_fields(beats), "reason": cand["reason"],
                      "confidence": cand["confidence"], "fingerprint": cand["fingerprint"]}
        st["fingerprints"] = list(st.get("fingerprints", [])) + [cand["fingerprint"]]
        st["last_at"] = now_iso
        st["active"] = suggestion
        _save_state(store, st)
        try:                                                   # the RENEW-shared durable bus
            from core.events.event_log import capture_event
            capture_event("episode_suggestion",
                          f"SUGGEST episode close: {cand['reason']} ({cand['confidence']:.2f}) "
                          f"-- {suggestion['title']}"[:200],
                          agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
                          detail={"chapter_id": ch.id, **suggestion})
        except Exception:
            pass
        return _public(suggestion)
    except Exception:
        return None


def _public(suggestion: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The contract view (#6): draft fields + reason/confidence; the fingerprint stays internal."""
    if not suggestion:
        return None
    return {k: v for k, v in suggestion.items() if k != "fingerprint"}
