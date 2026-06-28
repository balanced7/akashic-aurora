"""
Narrative health counters (Slice W-c) -- give the silent best-effort paths a voice.

The spine logs best-effort: `_route`, theme assignment, and chronicling all swallow exceptions
so capturing the story can never break the host command. That is correct -- but it means a rule
that silently no-ops (routing fails -> every beat lands in `unknown`; chronicling errors -> the
story stops refreshing) looks IDENTICAL to healthy. These counters surface that silence: a small
Store hash the `status` command reads, so degradation is observable instead of invisible.

Counters are best-effort and approximate (read-modify-write, not atomic) -- observability, not
accounting. A counter hiccup must never raise into the path it observes (that would defeat the
whole point of the best-effort wrapping).

Layering: this is narrative (System 4). It is bumped only from narrative-layer code -- the lower
event/domain primitives must not depend upward on it, so their own failures stay in their logs.
"""
from typing import Any, Dict, Optional

HEALTH_KEY = "narr:health"


def bump(store: Any, metric: str, n: int = 1) -> None:
    """Increment a health counter. Never raises (observability must not break the host path)."""
    if store is None or not metric:
        return
    try:
        cur = store.hget(HEALTH_KEY, metric)
        store.hset(HEALTH_KEY, metric, str(int(cur or 0) + n))
    except Exception:
        pass


def snapshot(store: Any) -> Dict[str, Any]:
    """All health counters as a dict (ints where parseable). Never raises -> {} on any hiccup."""
    out: Dict[str, Any] = {}
    if store is None:
        return out
    try:
        for k, v in (store.hgetall(HEALTH_KEY) or {}).items():
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = v
    except Exception:
        pass
    return out


def reset(store: Any) -> None:
    """Clear all counters (tests / a fresh measurement window). Never raises."""
    try:
        store.delete(HEALTH_KEY)
    except Exception:
        pass
