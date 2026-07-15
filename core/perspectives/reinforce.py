"""
ReinforcedGraph (Slice P1) -- an association graph whose edges STRENGTHEN with co-use
and DECAY without it. Turns the static typed graph into a living, experience-shaped map.

Semantic Relationship: Association strengthened_by CoActivation (decayed by Time)

Math (grounded -- ACT-R / Hebbian):
  * bounded saturating Hebbian update:  s <- s + LR * w * (MAX - s)
    -> approaches MAX asymptotically, NEVER exceeds it (no runaway -- the classic
       unbounded-Hebbian failure mode).
  * half-life decay (lazy, on read):    s_now = s_stored * 0.5 ** (elapsed / HALF_LIFE)
    -> what isn't reinforced fades. This is the ANTI-OSSIFICATION mechanism (a map that
       only ever strengthens becomes a rich-get-richer echo chamber).

Read-only on the substrate (Ledger/beats untouched). The only write-back is bounded,
decayed reinforcement (lens-law safe: a view can never corrupt the source).

Storage (on the Store, canonical or injected):
  persp:assoc:<a>|<b>      -> json {strength, count, last_used}   (undirected, a<b)
  persp:assoc:node:<id>    -> set of neighbour ids
"""
import json
from typing import List, Optional, Tuple

from core.foundation.store import Store, create_store

MAX_STRENGTH = 1.0
LEARNING_RATE = 0.34
HALF_LIFE_SECONDS = 30 * 24 * 3600   # 30 days


from core.foundation.timeutil import to_epoch as _epoch   # unified tz-safe epoch (S5)


class ReinforcedGraph:
    def __init__(self, store: Optional[Store] = None,
                 learning_rate: float = LEARNING_RATE,
                 half_life_seconds: float = HALF_LIFE_SECONDS):
        self.store = store if store is not None else create_store()
        self.lr = learning_rate
        self.half_life = half_life_seconds

    @staticmethod
    def _key(a: str, b: str) -> str:
        a, b = sorted((a, b))
        return f"persp:assoc:{a}|{b}"

    def _load(self, a: str, b: str) -> dict:
        raw = self.store.get(self._key(a, b))
        if not raw:
            return {"strength": 0.0, "count": 0, "last_used": None}
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {"strength": 0.0, "count": 0, "last_used": None}

    def _decayed(self, rec: dict, now) -> float:
        s = rec.get("strength", 0.0)
        last = rec.get("last_used")
        if last is None or s <= 0:
            return s
        elapsed = max(0.0, _epoch(now) - _epoch(last))
        return s * (0.5 ** (elapsed / self.half_life))

    def reinforce(self, a: str, b: str, *, now, weight: float = 1.0) -> float:
        """Strengthen the a-b association (bounded). Returns the new strength."""
        if a == b or not a or not b:
            return 0.0
        rec = self._load(a, b)
        s = self._decayed(rec, now)                       # fade to 'now' first
        s = s + self.lr * weight * (MAX_STRENGTH - s)     # bounded saturating bump
        s = min(MAX_STRENGTH, max(0.0, s))
        self.store.set(self._key(a, b), json.dumps(
            {"strength": s, "count": rec.get("count", 0) + 1, "last_used": now}))
        self.store.sadd(f"persp:assoc:node:{a}", b)
        self.store.sadd(f"persp:assoc:node:{b}", a)
        return s

    def reinforce_cooccurrence(self, node_ids, *, now, weight: float = 1.0) -> int:
        """Co-activation: every pair in the set strengthens (e.g. beats in one chapter)."""
        ids = [n for n in dict.fromkeys(node_ids) if n]   # de-dup, keep order
        pairs = 0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                self.reinforce(ids[i], ids[j], now=now, weight=weight)
                pairs += 1
        return pairs

    def strength(self, a: str, b: str, *, now) -> float:
        return self._decayed(self._load(a, b), now)

    def neighbors(self, a: str, *, now, top_k: int = 10) -> List[Tuple[str, float]]:
        """Strongest current associations of `a`, decayed-to-now, strongest first."""
        nbrs = self.store.smembers(f"persp:assoc:node:{a}")
        scored = [(n, self.strength(a, n, now=now)) for n in nbrs]
        scored = [(n, s) for n, s in scored if s > 0]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


_INSTANCE: Optional[ReinforcedGraph] = None


def get_reinforced_graph(store: Optional[Store] = None) -> ReinforcedGraph:
    # T069 reconciled spec: injection -> fresh; _AISETUP_TEST_ISOLATED -> fresh per
    # call, cache untouched (stateless wrapper); canonical -> lazy singleton.
    import os
    global _INSTANCE
    if store is not None:
        return ReinforcedGraph(store)
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return ReinforcedGraph()
    if _INSTANCE is None:
        _INSTANCE = ReinforcedGraph()
    return _INSTANCE
