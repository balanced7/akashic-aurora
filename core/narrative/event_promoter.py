"""
EventPromoter (Slice 5) -- promote salient raw events into narrative Beats.

Semantic Relationship: SalientRawEvent promoted_to Beat (reflection / consolidation)

PRIOR ART (this is the well-studied reflection / episodic->semantic consolidation layer):
  - Generative Agents (Park et al. 2023): every observation gets an importance/poignancy
    score; *reflection* fires when accumulated importance crosses a THRESHOLD (not on a
    fixed schedule) and is written back into the stream. -> our salience() + threshold-gated
    promotion; the threshold + per-run cap ARE the rate-limiter (no Beat flood).
  - GAM / SEEM (ACL 2026): a write-isolation episodic buffer is consolidated only on
    boundaries, with a provenance pointer preserved. -> raw stays sacred (append-only); the
    promoted Beat points AT the raw atom (source = event:<stream>:<id>).
  - "What Deserves Memory" / Nemori (ACL 2026): predefined importance heuristics encode
    *designer intuition*, not data. -> ours is an honest Tier-0 baseline; an embedding/LLM
    scorer is a documented future seam that must BEAT this on a fixture (same ablation gate
    as TrackRouter Tier-1), or it doesn't ship.

WHY it's needed: the auto-hooks (Slice 2) already beat the things that flow through a verb
(commits, learnings). This catches SALIENT raw activity that did NOT -- e.g. an external
runtime's tool_call / file_edit / error -- so the curated narrative stays in sync with the
full-fidelity substrate. Events that already have a Beat (a git: or learn:experiment: ref)
are skipped, so we never double-promote.

Layering: System 4. Imports the domain EventQuery (lower) + the narrative BeatLog (same
layer). A pure-domain module must not depend upward on the narrative, so promotion lives
HERE, not in core/events.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.store import Store, create_store
from core.events.event_query import EventQuery, get_event_query

PROMOTED_SET = "narr:promoted:refs"        # dedup: refs already promoted to a Beat
DEFAULT_THRESHOLD = 3                       # salience >= this is worth a Beat
DEFAULT_MAX_PROMOTE = 10                    # per-run cap (rate-limit; no Beat flood)
DEFAULT_SCAN = 500                          # how many recent raw events to consider

# raw kind -> Beat kind (unknown -> note; the `weight` carries the salience either way)
_KIND_TO_BEAT = {"learning": "learning", "blocker": "blocker",
                 "decision": "decision", "milestone": "milestone"}

# base salience per raw kind (the Tier-0 importance prior)
_BASE_SALIENCE = {"milestone": 5, "decision": 4, "learning": 4, "blocker": 3,
                  "command": 3, "file_edit": 2, "tool_call": 1, "observation": 1,
                  "message": 1, "note": 1, "boot": 1, "session": 1}

# content boosts (each group adds at most once; final score is clamped to 0..5)
_BOOST: List[Tuple[Tuple[str, ...], int]] = [
    (("error", "fail", "failed", "broke", "broken", "bug", "crash", "traceback", "exception"), 1),
    (("fix", "fixed", "resolved", "repair", "patch"), 1),
    (("decide", "decision", "decided", "chose", "chosen", "adopt"), 1),
    (("milestone", "shipped", "breakthrough", "release", "complete", "completed"), 1),
]

# refs that mean "this already has a Beat from an auto-hook" -> don't double-promote.
# `beat:<id>` is stamped by hooks that emit a Beat themselves (e.g. `log`); `git:` /
# `learn:experiment:` are the commit / learning atoms the mirror & learn hooks already beat.
_ALREADY_BEAT_PREFIXES = ("beat:", "git:", "learn:experiment:")


def salience(event: Dict[str, Any]) -> int:
    """Tier-0 importance score (0..5) for a raw event -- kind prior + content boosts.

    Deliberately simple and deterministic (the honest baseline the Nemori critique warns
    about). The seam for an embedding/LLM poignancy scorer is a drop-in replacement here.
    """
    kind = str(event.get("kind", "note"))
    score = _BASE_SALIENCE.get(kind, 1)
    text = (str(event.get("summary", "")) + " " +
            json.dumps(event.get("detail", {}), default=str)).lower()
    for words, bump in _BOOST:
        if any(w in text for w in words):
            score += bump
    return max(0, min(5, score))


def _already_beat(event: Dict[str, Any]) -> bool:
    for r in event.get("refs", []) or []:
        if str(r).startswith(_ALREADY_BEAT_PREFIXES):
            return True
    return False


def promote_salient(store: Optional[Store] = None, event_query: Optional[EventQuery] = None,
                    *, threshold: int = DEFAULT_THRESHOLD, max_promote: int = DEFAULT_MAX_PROMOTE,
                    scan: int = DEFAULT_SCAN, agent: Optional[str] = None) -> Dict[str, int]:
    """Scan recent raw events; promote the salient, not-yet-promoted ones into Beats.

    Rate-limited three ways (Generative-Agents-style): a salience THRESHOLD, a per-run CAP
    (highest salience first), and a persistent DEDUP set so a re-run never re-promotes.
    Best-effort: never raises. Returns counts {scanned, eligible, promoted, skipped_dup,
    skipped_beat}.
    """
    report = {"scanned": 0, "eligible": 0, "promoted": 0, "skipped_dup": 0, "skipped_beat": 0}
    try:
        store = store if store is not None else create_store()
        eq = event_query if event_query is not None else get_event_query()
        from core.narrative.beat_log import BeatLog
        bl = BeatLog(store)

        candidates = eq.log.scan(agent=agent, limit=scan)
        report["scanned"] = len(candidates)

        scored: List[Tuple[int, Dict[str, Any]]] = []
        for e in candidates:
            ref = e.get("_ref")
            if not ref:
                continue
            if _already_beat(e):
                report["skipped_beat"] += 1
                continue
            if salience(e) < threshold:
                continue
            if store.sismember(PROMOTED_SET, ref):
                report["skipped_dup"] += 1
                continue
            scored.append((salience(e), e))

        report["eligible"] = len(scored)
        from core.narrative.track_router import RouteHint
        # highest salience first (ties -> most recent), then apply the per-run cap
        scored.sort(key=lambda x: (x[0], x[1].get("at", "")), reverse=True)
        for s, e in scored[:max(0, max_promote)]:
            # Route via a hint (like the commit/learn hooks) so the Track is registered --
            # passing an explicit `track` to emit() skips _route and leaves the track
            # un-indexed. The raw event's `track` becomes the routing task signal.
            hint = RouteHint(task=str(e.get("summary", "") or e.get("track", "")),
                             category=str(e.get("kind", "")))
            beat = bl.emit(_KIND_TO_BEAT.get(e.get("kind", ""), "note"),
                           summary=e.get("summary", ""), source=e["_ref"],
                           weight=s, at=e.get("at"), hint=hint)
            if beat is not None:
                store.sadd(PROMOTED_SET, e["_ref"])
                report["promoted"] += 1
        return report
    except Exception:
        return report
