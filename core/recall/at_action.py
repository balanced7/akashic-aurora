"""Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action.

Semantic Relationship: Recall surfaces ActiveKnowledge for a PointOfAction (path | command)

The pain this closes: storage is passive — lessons are written far more than they are read when
they matter. Given the file path or shell command an agent is about to act on, return the FEW
highest-signal ACTIVE items (relevant lessons + a lock/peer-activity warning) with `source`
pointers. The one reusable engine consumed by BOTH the `recall-at` CLI verb AND the PreToolUse
hook's `additionalContext` (so it is wired by construction, never built-but-not-wired).

Design — deterministic, no-LLM, fail-soft (SOTA-informed; see docs/agent-experience-plan.md):
- **keyword/path-first relevance** via the shared Ranker (no embedding on the hot path).
- **SHOW NOTHING unless it clears a relevance floor** — a weak, off-topic hint at action-time is
  worse than silence (context-rot). We gate on the Ranker's RELEVANCE component specifically, not
  the blended score, so a merely-important-but-irrelevant lesson never fires.
- **cap at a few entries** (default 3) — skeleton-first, lossy summary + lossless `source` pointer.
- **FAITH-1 gate** — recalled text runs through `faithfulness_report`; nothing unfaithful (a
  fabricated/unresolvable pointer) ever reaches the agent.
- **fully degrades to empty** on any error — a recall path must never brick the action.

LATENCY: lesson items are served from a TTL disk cache (a fresh hook process can't hold an in-memory
one), so after warm-up a call is a ~1ms file read + rank, not a store round-trip. On a cold/down store
the cache returns last-known-good (stale fallback) instead of empty — this kills the cold-start empty.
The PreToolUse hook is also non-blocking + fail-open, so even a cold first call delays a hint, never the
action. Anti-repeat (don't re-surface a lesson already shown this session) is handled by the hook via
`exclude_sources`. Tunables: AKASHIC_RECALL_CACHE_TTL (sec), AKASHIC_RECALL_AT_ACTION=0 (off).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
# generic tokens that carry no recall signal (tooling/noise) — never used as query terms.
_STOP = {"core", "self", "true", "false", "none", "null", "test", "tests", "json",
         "http", "https", "www", "com", "the", "and", "for", "with", "this", "that",
         "py", "python", "git", "main", "init", "args", "data", "path", "file"}

# --- warm disk cache: a fresh hook process can't keep an in-memory cache, so cache the projected
# lesson items to a small JSON file (read ~1ms) instead of cold-connecting the store every call.
# Fresh (within TTL) -> read it; expired -> refresh from the store; store fails (cold/down) -> fall
# back to the STALE cache (last-known-good) -- this is what kills the cold-start empty. Env-tunable.
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "akashic_recall")
_CACHE_FILE = os.path.join(_CACHE_DIR, "lesson_items.json")
_CACHE_TTL = float(os.getenv("AKASHIC_RECALL_CACHE_TTL", "120"))


def _project_items(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for rec in recs:
        summary = rec.get("recommendation") or rec.get("actual") or rec.get("what_tried") or ""
        if not summary:
            continue
        items.append({
            "text": summary,
            "source": f"learn:experiment:{rec.get('experiment_name')}",
            "importance": 4 if str(rec.get("success", "")).lower() in ("yes", "true") else 3,
            "timestamp": rec.get("timestamp"), "kind": "lesson",
        })
    return items


def _cached_items(learning_store: Optional[Any]) -> List[Dict[str, Any]]:
    """Projected lesson items via a TTL disk cache with stale-fallback. An INJECTED store (tests)
    bypasses the cache for determinism; only the production singleton path is cached."""
    if learning_store is not None:
        return _project_items(learning_store.load_all_learnings_from_store())
    try:
        if (time.time() - os.stat(_CACHE_FILE).st_mtime) < _CACHE_TTL:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)          # fresh cache hit (~1ms, no store round-trip)
    except Exception:
        pass
    try:
        from core.learning.learning_store import get_learning_store
        items = _with_usefulness(_project_items(get_learning_store().load_all_learnings_from_store()))
        if items:
            try:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(items, f)
            except Exception:
                pass
        return items
    except Exception:
        try:                                  # store cold/down -> last-known-good (kills cold empties)
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


# Per-session anti-repeat files live here (the hook writes them; this module prunes them). Keep this
# path in sync with claude_pretooluse.py:_SEEN_DIR.
_SEEN_DIR = os.path.join(_CACHE_DIR, "seen")


def warm_cache(learning_store: Optional[Any] = None) -> int:
    """Force-refresh the lesson-item disk cache from the store (ignores TTL). Best-effort; returns the
    item count (0 on failure). Call at session start (SessionStart hook / boot) so the FIRST recall is
    already warm -- the last cold-start corner."""
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        items = _with_usefulness(_project_items(learning_store.load_all_learnings_from_store()))
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f)
        return len(items)
    except Exception:
        return 0


def prune_state(max_age_days: float = 7.0) -> int:
    """Best-effort sweep of stale per-session anti-repeat files (one accrues per session). Returns the
    count removed. The cache itself is a single self-refreshing file, so it needs no pruning."""
    removed = 0
    try:
        cutoff = time.time() - max_age_days * 86400.0
        for name in os.listdir(_SEEN_DIR):
            p = os.path.join(_SEEN_DIR, name)
            try:
                if os.path.isfile(p) and os.stat(p).st_mtime < cutoff:
                    os.remove(p)
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed


# --- usefulness feedback loop: recall learns what's LOAD-BEARING. Each lesson accrues counters in the
# Store (recall:use:<source>): `surfaced` (auto, each time it's shown) + explicit `useful`/`noise` votes
# (via `agent_cli.py recall-feedback`). A smoothed factor then boosts proven-useful lessons and decays
# ones surfaced often yet never useful -- self-improving relevance, deterministic, no LLM. Counters are
# baked into the warm cache at build time, so the hot path stays a pure file read.
_USE_PREFIX = "recall:use:"


def _store():
    from core.foundation.store import create_store
    return create_store()


def _load_use(store, source: str) -> Dict[str, int]:
    try:
        raw = store.get(_USE_PREFIX + str(source))
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _with_usefulness(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach each lesson's usefulness counters (read once at cache-build time -> off the hot path)."""
    try:
        store = _store()
        for it in items:
            it["_use"] = _load_use(store, it.get("source"))
    except Exception:
        pass
    return items


def usefulness_factor(use: Optional[Dict[str, int]]) -> float:
    """Smoothed ranking multiplier in [0.5, 1.5]. Neutral (1.0) for unseen; ->1.5 for proven-useful;
    ->0.5 for noise-voted or surfaced-often-yet-never-useful (the automatic noise decay)."""
    use = use or {}
    useful = int(use.get("useful", 0))
    noise = int(use.get("noise", 0))
    surfaced = int(use.get("surfaced", 0))
    eff = useful - noise
    denom = max(surfaced, useful + noise) + 2.0
    rate = max(0.0, min(1.0, (eff + 1.0) / denom))   # ~0.5 neutral; ->1 useful; ->0 stale/noise
    return 0.5 + rate


def record_feedback(source: str, kind: str = "useful", *, store=None) -> bool:
    """Record an explicit usefulness vote for a recalled lesson (kind: 'useful' | 'noise'). Shapes
    future recall ranking. Best-effort; safe to call repeatedly."""
    if not source or kind not in ("useful", "noise"):
        return False
    try:
        store = store or _store()
        use = _load_use(store, source)
        use[kind] = int(use.get(kind, 0)) + 1
        store.set(_USE_PREFIX + str(source), json.dumps(use))
        return True
    except Exception:
        return False


def bump_surfaced(sources, *, store=None) -> None:
    """Increment the `surfaced` (impression) counter for shown lessons -- best-effort, fire-and-forget."""
    try:
        store = store or _store()
        for s in sources:
            use = _load_use(store, s)
            use["surfaced"] = int(use.get("surfaced", 0)) + 1
            store.set(_USE_PREFIX + str(s), json.dumps(use))
    except Exception:
        pass


def _query_from(path: Optional[str], command: Optional[str]) -> str:
    """Build a keyword query from a path (dir/stem tokens) and/or command. Keeps tokens len>3
    (the Ranker's keyword_relevance ignores shorter ones) minus generic noise; order-stable, deduped."""
    parts: List[str] = []
    if path:
        parts += _TOKEN_RE.findall(path.replace("\\", "/"))
    if command:
        parts += _TOKEN_RE.findall(command)[:16]
    out: List[str] = []
    for t in parts:
        t = t.lower()
        if len(t) > 3 and t not in _STOP and t not in out:
            out.append(t)
    return " ".join(out)


def _lessons(query: str, now: Optional[float], limit: int, min_relevance: float,
             learning_store: Optional[Any] = None,
             exclude_sources: Optional[set] = None) -> List[Dict[str, Any]]:
    """Rank ACTIVE lessons by relevance; keep those above the show-nothing floor, minus any already
    surfaced this session (`exclude_sources` -> anti-repeat) and intra-call source dups."""
    from core.primitives.ranker import Ranker
    items = _cached_items(learning_store)
    excl = exclude_sources or set()
    cands: List = []
    seen = set()
    for s in Ranker().rank(items, query=query, now=now):   # Ranker excludes superseded (is_active)
        if s.components.get("relevance", 0.0) <= min_relevance:
            continue   # SHOW-NOTHING floor (T_min): must actually match this path/command; never pad to `limit`
        src = s.item.get("source")
        if src in seen or src in excl:
            continue   # intra-call dedup + cross-action anti-repeat (each item adds NEW info)
        seen.add(src)
        # usefulness re-rank: proven-useful lessons rise; surfaced-often-yet-never-useful decay
        cands.append((s.score * usefulness_factor(s.item.get("_use")), s.item))
    cands.sort(key=lambda t: t[0], reverse=True)
    return [it for _, it in cands[:limit]]


def _locks(path: Optional[str], agent_id: Optional[str]) -> List[Dict[str, Any]]:
    """A peer holding an advisory lock on this exact path = the single most actionable hint."""
    if not path:
        return []
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, agent_id or "(unidentified)")
    except Exception:
        return []
    if c.get("conflict"):
        return [{"held_by": c.get("held_by"), "reason": c.get("reason", "")}]
    return []


def recall_at(*, path: Optional[str] = None, command: Optional[str] = None,
              agent_id: Optional[str] = None, limit: int = 3,
              min_relevance: float = 0.0, now: Optional[float] = None,
              learning_store: Optional[Any] = None,
              exclude_sources: Optional[set] = None,
              count_surface: bool = False) -> Dict[str, Any]:
    """Given a point of action (path and/or command), return the few highest-signal active items.
    `exclude_sources` (lesson sources already shown this session) enables hook anti-repeat.
    Deterministic, no-LLM, FAITH-gated, fail-soft (returns an empty result on any error)."""
    try:
        query = _query_from(path, command)
        lessons = _lessons(query, now, limit, min_relevance, learning_store, exclude_sources) if query else []
        locks = _locks(path, agent_id)
        faithful, conf = True, 1.0
        if lessons:
            from core.primitives.faithfulness import faithfulness_report
            skeleton = "\n".join(f"- {l['text']}  (source: {l['source']})" for l in lessons)
            rep = faithfulness_report(lessons, skeleton)
            faithful, conf = rep["faithful"], rep["confidence"]
            if not faithful:
                lessons = []   # never surface unfaithful recall — silence beats a fabricated hint
        if count_surface and lessons:
            bump_surfaced([l.get("source") for l in lessons])   # impression count (best-effort, feeds noise-decay)
        return {"path": path, "command": command, "query": query, "lessons": lessons,
                "locks": locks, "shown": len(lessons) + len(locks),
                "faithful": faithful, "confidence": conf}
    except Exception as e:
        return {"path": path, "command": command, "query": "", "lessons": [], "locks": [],
                "shown": 0, "faithful": True, "confidence": 1.0, "error": type(e).__name__}


def render(result: Dict[str, Any], *, max_chars: int = 110) -> str:
    """Compact, agent-readable rendering for the hook's additionalContext. Empty result -> ''."""
    lines: List[str] = []
    for lk in result.get("locks", []):
        lines.append(f"[lock] {lk.get('held_by')} holds an advisory lock on this path — coordinate before editing")
    for l in result.get("lessons", []):
        s = l.get("text", "")
        if len(s) > max_chars:
            s = s[:max_chars].rsplit(" ", 1)[0] + "..."
        lines.append(f"[lesson] {s} (source: {l.get('source')})")
    if not lines:
        return ""
    # Factual framing (not imperative — imperative trips prompt-injection defenses). Hard total cap
    # well under Claude Code's 10k-char additionalContext limit.
    body = "Recall-at-action (Akashic) - facts relevant to what you're about to do:\n" + "\n".join(lines)
    return body[:900]
