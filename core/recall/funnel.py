"""
Recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are
earned lessons being CAPTURED?

Semantic Relationship: FunnelSnapshot derived_from ExistingRecords (read-only)

Instrument by READING what the loop already records -- never by adding write paths
(t3_stats_funnel_first_slice). Sources, and what each can answer:

  recall:use:* counters (Store)   all-time surfaced / useful / noise / helped per lesson
  per-session flip logs (tempdir) flips in a RECENT window (pruned weekly -- no trends)
  flip EVENTS (durable firehose)  flips per day over WEEKS -> the trend/pace view
  lesson timestamps (LearningStore) lessons recorded per day

Slice 2 (2026-07-02): this module extracts the computation from the CLI so boot / the
SessionStart hook / stats all read ONE funnel; adds the durable per-day trend + the
30-day pace against the Wave-A gate (30+ lessons / 30d); and fixes slice 1's window
bug -- store timestamps are datetime.utcnow().isoformat(), so windows/buckets here are
computed against utcnow too (comparing against local now() shifted the window by the
host's UTC offset).

Everything is fail-soft and injectable: a missing backend yields zeros, never a raise.
"""
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# The Wave-A gate from docs/leapfrog-plan.md: "corpus growth rate measurably up
# (target 30+ lessons in 30 days)". One place, so every renderer quotes the same bar.
TARGET_LESSONS_30D = 30

# Durable-trend scan bound (newest events). If a scan RETURNS exactly this many, older
# events may have been dropped -- snapshot marks it so renderers can say so (no silent caps).
EVENT_SCAN_LIMIT = 5000


def _parse_ts(s: Any) -> Optional[datetime]:
    """Naive-UTC datetime from a stored ISO string (both stores stamp utcnow().isoformat())."""
    try:
        return datetime.fromisoformat(str(s)[:19])
    except Exception:
        return None


def snapshot(hours: float = 24.0, *, store: Any = None, learning_store: Any = None,
             flips: Optional[List[Dict[str, Any]]] = None,
             injections: Optional[List[Dict[str, Any]]] = None,
             now: Optional[datetime] = None) -> Dict[str, Any]:
    """All-time funnel counters + one recent window. The dict `stats` prints verbatim."""
    if store is None:
        try:
            from core.foundation.store import create_store
            store = create_store()
        except Exception:
            store = None
    use: Dict[str, Dict[str, Any]] = {}
    if store is not None:
        try:
            for k in store.keys("recall:use:*"):
                try:
                    use[k[len("recall:use:"):]] = json.loads(store.get(k) or "{}")
                except Exception:
                    pass
        except Exception:
            pass
    surfaced = sum(int(u.get("surfaced", 0)) for u in use.values())
    helped = sum(int(u.get("helped", 0)) for u in use.values())
    useful = sum(int(u.get("useful", 0)) for u in use.values())
    noise = sum(int(u.get("noise", 0)) for u in use.values())
    with_track = sum(1 for u in use.values() if int(u.get("helped", 0)) or int(u.get("useful", 0)))

    recs: List[Dict[str, Any]] = []
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        recs = learning_store.load_all_learnings_from_store()
    except Exception:
        recs = []
    now = now or datetime.utcnow()
    cutoff = now - timedelta(hours=hours)
    new_lessons = [r for r in recs if (_parse_ts(r.get("timestamp")) or datetime.min) >= cutoff]

    if flips is None:
        try:
            from core.recall.at_action import recent_flips
            flips = recent_flips(hours)
        except Exception:
            flips = []
    credited = sum(1 for f in flips if f.get("credited"))
    if injections is None:
        try:
            from core.recall.at_action import recent_injections
            injections = recent_injections(hours)
        except Exception:
            injections = []
    # 'lessons_per_flip' not 'capture rate': recorded lessons are NOT all flip-caused, so a
    # ratio over 1.0 is legitimate -- the name must not lie.
    window = {"flips": len(flips), "flips_credited": credited,
              "flips_corpus_gap": len(flips) - credited,
              "lessons_recorded": len(new_lessons),
              "lessons_per_flip": (round(len(new_lessons) / len(flips), 2) if flips else None),
              # what the push side COSTS (the Ronacher dissent: measure it): count + ~tokens
              "injections": len(injections),
              "injected_tokens_approx": sum(int(i.get("chars", 0)) for i in injections) // 4}
    # Value rate = (useful + helped) / surfaced: of everything recall pushed, how much earned
    # credit. The one steering ratio (Greptile managed its whole noise war by the analogous
    # address rate, 19%->55%). OBSERVABILITY ONLY -- never feed it back into ranking as an
    # optimizer input (epistemic-risk register F2: a proxy under optimization pressure Goodharts).
    value_rate = round((useful + helped) / surfaced, 4) if surfaced else None
    return {"corpus_lessons": len(recs), "tracked_sources": len(use),
            "surfaced_impressions": surfaced, "votes": {"useful": useful, "noise": noise},
            "helped_credits": helped, "lessons_with_track_record": with_track,
            "value_rate": value_rate,
            "window_hours": hours, "window": window}


def triage(min_surfaced: int = 5, *, store: Any = None, learning_store: Any = None,
           injections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Sharpening-loop S1: rank every tracked lesson by measured value so a REVIEWER can
    decide what to merge, graduate, or retire. READ-ONLY and OBSERVABILITY-ONLY by design:
    this function proposes nothing and prunes nothing -- feeding its output back into
    ranking or automated deletion is the F2 Goodhart trap (epistemic-risk register).

    Buckets (adjudication vocabulary, field-grounded 2026-07: utility-scored eviction
    beats accumulation, but the SELECTION stays human/frontier judgment):
      protect        earned credit (helped or useful > 0) -- the corpus's proven core
      cost_no_return surfaced >= min_surfaced with zero credit -- top merge/retire/
                     graduate candidates, ranked by cost (surfaced desc)
      noise_voted    explicitly voted noise -- review the trigger phrasing or retire
      watch          surfaced 1..min_surfaced-1, no credit yet -- too early to judge
      dormant_count  in corpus, never surfaced -- costs nothing until shown
      ghosts         learn:experiment:* counters naming NO live lesson (bookkeeping
                     debt from retired lessons, not knowledge) -- kept out of the
                     adjudication buckets; fold with `recall-counters --fold`
    """
    if store is None:
        try:
            from core.foundation.store import create_store
            store = create_store()
        except Exception:
            store = None
    use: Dict[str, Dict[str, Any]] = {}
    if store is not None:
        try:
            for k in store.keys("recall:use:*"):
                try:
                    use[k[len("recall:use:"):]] = json.loads(store.get(k) or "{}")
                except Exception:
                    pass
        except Exception:
            pass
    n_corpus = 0
    corpus_names: set = set()
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        recs = learning_store.load_all_learnings_from_store()
        n_corpus = len(recs)
        corpus_names = {r.get("experiment_name") for r in recs}
    except Exception:
        pass
    # window-scoped push cost per source (injection ledger is tempdir-lifetime: a cost
    # SAMPLE, not all-time truth -- renderers must label it as such)
    if injections is None:
        try:
            from core.recall.at_action import recent_injections
            injections = recent_injections(24 * 7)
        except Exception:
            injections = []
    win_chars: Dict[str, int] = {}
    for inj in injections or []:
        srcs = [s for s in (inj.get("s") or []) if s]
        if srcs:
            per = int(inj.get("chars", 0)) // len(srcs)
            for s in srcs:
                win_chars[s] = win_chars.get(s, 0) + per

    # A ghost is a lesson-shaped counter whose lesson is gone (retired/renamed): bookkeeping
    # debt, not adjudicable knowledge -- bucketing it as cost would propose retiring a phantom.
    # Classified only when the corpus read yielded names (a broken read must not ghost everything).
    _LESSON = "learn:experiment:"
    rows, ghosts, live_lessons = [], [], 0
    for src, u in use.items():
        row = {"source": src,
               "surfaced": int(u.get("surfaced", 0)),
               "useful": int(u.get("useful", 0)),
               "noise": int(u.get("noise", 0)),
               "helped": int(u.get("helped", 0)),
               "window_tokens_approx": win_chars.get(src, 0) // 4}
        if src.startswith(_LESSON):
            if corpus_names and src[len(_LESSON):] not in corpus_names:
                ghosts.append(row)
                continue
            live_lessons += 1
        rows.append(row)
    ghosts.sort(key=lambda r: r["surfaced"], reverse=True)
    protect = sorted((r for r in rows if r["helped"] or r["useful"]),
                     key=lambda r: (r["helped"], r["useful"]), reverse=True)
    noise_voted = [r for r in rows if r["noise"] and not (r["helped"] or r["useful"])]
    rest = [r for r in rows if not (r["helped"] or r["useful"]) and not r["noise"]]
    cost_no_return = sorted((r for r in rest if r["surfaced"] >= min_surfaced),
                            key=lambda r: r["surfaced"], reverse=True)
    watch = [r for r in rest if 0 < r["surfaced"] < min_surfaced]
    return {"corpus_lessons": n_corpus, "tracked": len(rows) + len(ghosts),
            "tracked_lessons": live_lessons, "ghosts": ghosts,
            "dormant_count": max(0, n_corpus - live_lessons),
            "min_surfaced": min_surfaced,
            "protect": protect, "cost_no_return": cost_no_return,
            "noise_voted": noise_voted, "watch_count": len(watch),
            "window_injected_tokens_approx": sum(r["window_tokens_approx"] for r in rows + ghosts)}


def summary_line(snap: Dict[str, Any]) -> str:
    """The one-line funnel pulse for boot / SessionStart. ASCII, small-when-not-silent."""
    w = snap.get("window") or {}
    v = snap.get("votes") or {}
    hrs = float(snap.get("window_hours", 24))
    span = f"{hrs / 24:g}d" if hrs >= 48 else f"{hrs:g}h"
    rate = snap.get("value_rate")
    return (f"{snap.get('corpus_lessons', 0)} lessons | surfaced {snap.get('surfaced_impressions', 0)}"
            f" | votes useful={v.get('useful', 0)} noise={v.get('noise', 0)}"
            f" | helped {snap.get('helped_credits', 0)}"
            + (f" | value {rate * 100:.1f}%" if rate is not None else "")
            + f" | last {span}: +{w.get('lessons_recorded', 0)} lesson(s), {w.get('flips', 0)} flip(s)")


def trend(days: int = 7, *, learning_store: Any = None, event_log: Any = None,
          now: Optional[datetime] = None) -> Dict[str, Any]:
    """Per-day lessons/flips over `days`, from DURABLE records only.

    The tempdir flip logs prune weekly, so the trend reads the flip EVENTS the PostToolUse
    hook captures on the firehose (kind="flip", detail.credited) plus lesson timestamps.
    Returns oldest-first buckets, the 30d lesson count vs TARGET_LESSONS_30D, and
    `events_capped` (True when the scan hit EVENT_SCAN_LIMIT -- older flips may be missing;
    renderers must say so rather than under-report silently).
    """
    now = now or datetime.utcnow()
    days = max(1, int(days))
    day_keys = [(now - timedelta(days=i)).date().isoformat() for i in range(days - 1, -1, -1)]
    buckets = {d: {"date": d, "lessons": 0, "flips": 0, "credited": 0} for d in day_keys}

    recs: List[Dict[str, Any]] = []
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        recs = learning_store.load_all_learnings_from_store()
    except Exception:
        recs = []
    lessons_30d = 0
    cutoff_30d = now - timedelta(days=30)
    for r in recs:
        ts = _parse_ts(r.get("timestamp"))
        if ts is None:
            continue
        if ts >= cutoff_30d:
            lessons_30d += 1
        d = ts.date().isoformat()
        if d in buckets:
            buckets[d]["lessons"] += 1

    events: List[Dict[str, Any]] = []
    try:
        if event_log is None:
            from core.events.event_log import get_event_log
            event_log = get_event_log()
        events = event_log.scan(limit=EVENT_SCAN_LIMIT)
    except Exception:
        events = []
    for ev in events:
        if ev.get("kind") != "flip":
            continue
        ts = _parse_ts(ev.get("at"))
        if ts is None:
            continue
        d = ts.date().isoformat()
        if d in buckets:
            buckets[d]["flips"] += 1
            try:
                if int((ev.get("detail") or {}).get("credited", 0)) > 0:
                    buckets[d]["credited"] += 1
            except Exception:
                pass

    return {"days": days,
            "per_day": [buckets[d] for d in day_keys],
            "lessons_30d": lessons_30d,
            "target_30d": TARGET_LESSONS_30D,
            "events_capped": len(events) >= EVENT_SCAN_LIMIT}
