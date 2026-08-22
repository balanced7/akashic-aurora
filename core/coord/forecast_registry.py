"""T375 -- the engineering forecast registry (append-only, fold-not-table).

At every gate, the approved slice REGISTERS expected outcomes; at review the
outcomes are SCORED against what was observed. The registry is the cross-
cutting registry primitive in its cheapest instance -- T369's golden bank and
the trader's forecast registry inherit its two disciplines through this door:

  KNOWABLE-TS: an outcome's timestamp is DERIVED by resolving the cited
  evidence artifact (a stream id self-stamps; a commit has a commit time) --
  the door structurally cannot accept a scorer-supplied timestamp, because a
  self-stamped knowable-ts is a forged attribution in waiting (Heimdall's
  counter, bus 1787420737264-0, transposing a_boundary_declaration_is_a_claim).
  The hindsight guard is STRICT: resolved ts must be > registered_at; the ==
  boundary refuses, because a millisecond-wide seam is exactly where hindsight
  would live.

  ECHO-BAN: credit only from OUTCOME joins. Evidence pointing at the register
  plane (forecast:...) is agreement, and agreement is not evidence. The sole
  carve-out is verdict=voided -- a void is a statement about the BET, not a
  claim about the world, so it is the only path that needs no outcome
  artifact. It must stay the only one, or voided becomes the hindsight
  escape hatch.

NOT the same organ as scripts/checkers/check_preregistration.py: that gate
enforces COMMIT ordering (pins born before their implementation); this one
enforces FORECAST ordering (bets registered before their outcomes were
knowable). The trader counter that demanded this organ names the distinction;
both are preserved on purpose.

Storage: one append-only JSONL event log (register | score events). State is
a PURE fold over events -- no in-place mutation exists, which is what makes
the append-only property auditable from the file alone and lets a future
index sit behind the same fold without a rewrite. Single-writer assumption
v1: gate-time writes are low-contention; the cross-process lock class is
tracked separately (deferred CAS-on-TaskLedger work, same family).

Verdicts: hit | miss | partial | voided | residual. The engineering instance
uses the first four; `residual` (directionally right, benchmark-subtracted
edge indistinguishable from zero) is the documented trader-inheritance member
-- the enum is the primitive, this organ uses a subset. Conflating residual
with partial would make a trader calibration read near-perfect while carrying
zero alpha, which is why the bucket exists from day one.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional

VERDICTS = ("hit", "miss", "partial", "voided", "residual")

_REGISTER_PLANE = object()      # resolver sentinel: the ref points at a forecast


class RegistryRefusal(Exception):
    """A refused write, loudly -- the registry never guesses."""


def fold(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Registry state as a pure function of the event log. Never mutates its
    input; later a cache or index sits BEHIND this seam, not instead of it."""
    state: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        kind = ev.get("kind")
        if kind == "register":
            row = {k: ev[k] for k in ev if k != "kind"}
            state[str(ev.get("id"))] = row
        elif kind == "score":
            fid = str(ev.get("forecast_id"))
            if fid in state:
                merged = dict(state[fid])
                for k in ("scored_by", "scored_at", "observed", "evidence_ref",
                          "outcome_knowable_ts", "verdict"):
                    merged[k] = ev.get(k)
                state[fid] = merged
    return state


def _resolve_default(ref: str) -> Optional[Any]:
    """evidence_ref -> the artifact's OWN timestamp (seconds), _REGISTER_PLANE
    for forecast refs, or None for anything this v1 cannot resolve.

    Schemes: event:<stream>:<ms>-<seq> (stream ids self-stamp in ms);
    commit:<sha> (git commit time); forecast:<id> (register plane)."""
    ref = str(ref or "").strip()
    if not ref:
        return None
    if ref.startswith("forecast:"):
        return _REGISTER_PLANE
    if ref.startswith("event:"):
        try:
            sid = ref.rsplit(":", 1)[1]
            return int(sid.split("-", 1)[0]) / 1000.0
        except Exception:
            return None
    if ref.startswith("commit:"):
        sha = ref.split(":", 1)[1].strip()
        if not sha:
            return None
        try:
            out = subprocess.run(["git", "show", "-s", "--format=%ct", sha],
                                 capture_output=True, text=True, timeout=10,
                                 cwd=os.path.dirname(os.path.dirname(
                                     os.path.dirname(os.path.abspath(__file__)))))
            return float(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 else None
        except Exception:
            return None
    return None


class ForecastRegistry:
    def __init__(self, path: str, *, now_fn: Callable[[], float] = time.time,
                 resolver: Callable[[str], Optional[Any]] = _resolve_default):
        self.path = path
        self._now = now_fn
        self._resolve = resolver

    # ------------------------------------------------------------- plumbing
    def _events(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue        # a torn tail line never poisons the fold
        return out

    def _append(self, event: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def state(self) -> Dict[str, Dict[str, Any]]:
        return fold(self._events())

    # ------------------------------------------------------------- register
    def register(self, *, id: str, task_ref: str, registered_by: str,
                 expectation: Dict[str, Any], horizon_ts: float,
                 mechanism: str, dies_when: str) -> Dict[str, Any]:
        """Register a bet BEFORE its outcome is knowable. registered_at is
        stamped by the door's clock -- backdating is not a parameter."""
        fid = str(id).strip()
        if not fid:
            raise RegistryRefusal("a forecast needs an id")
        if fid in self.state():
            raise RegistryRefusal(
                f"forecast {fid!r} already registered -- the log is append-only; "
                f"supersede with a new id + void the old, never edit")
        if not str(dies_when or "").strip():
            raise RegistryRefusal(
                f"forecast {fid!r} has no dies_when -- a bet that cannot die "
                f"is not a bet (the hope-riff field is mandatory)")
        event = {"kind": "register", "id": fid, "task_ref": str(task_ref),
                 "registered_by": str(registered_by),
                 "registered_at": float(self._now()),
                 "expectation": expectation, "horizon_ts": float(horizon_ts),
                 "mechanism": str(mechanism), "dies_when": str(dies_when)}
        self._append(event)
        return event

    # ------------------------------------------------------------- score
    def score(self, forecast_id: str, *, scored_by: str, observed: str,
              evidence_ref: str, verdict: str) -> Dict[str, Any]:
        """Score a bet against an OUTCOME artifact. There is deliberately no
        timestamp parameter: outcome_knowable_ts is derived by resolving
        evidence_ref, or the score refuses."""
        fid = str(forecast_id).strip()
        row = self.state().get(fid)
        if row is None:
            raise RegistryRefusal(f"no forecast {fid!r} registered")
        if row.get("verdict"):
            raise RegistryRefusal(
                f"forecast {fid!r} already scored ({row['verdict']}) -- "
                f"append-only: a rescore is a new forecast, not an edit")
        if verdict not in VERDICTS:
            raise RegistryRefusal(f"verdict {verdict!r} not in {VERDICTS}")

        knowable_ts: Optional[float]
        if verdict == "voided":
            # the sole no-artifact path: a void is about the bet, not the world
            knowable_ts = None
        else:
            resolved = self._resolve(evidence_ref)
            if resolved is _REGISTER_PLANE:
                raise RegistryRefusal(
                    f"evidence {evidence_ref!r} points at the register plane -- "
                    f"agreement is not evidence (echo-ban): credit joins only "
                    f"to outcomes")
            if resolved is None:
                raise RegistryRefusal(
                    f"evidence {evidence_ref!r} missing or unresolvable -- the "
                    f"door derives outcome_knowable_ts from the artifact; no "
                    f"artifact, no score")
            knowable_ts = float(resolved)
            if knowable_ts <= float(row["registered_at"]):
                raise RegistryRefusal(
                    f"hindsight bet: evidence timestamp {knowable_ts} is not "
                    f"strictly after registration {row['registered_at']} -- "
                    f"named, not scored")

        event = {"kind": "score", "forecast_id": fid, "scored_by": str(scored_by),
                 "scored_at": float(self._now()), "observed": str(observed),
                 "evidence_ref": str(evidence_ref),
                 "outcome_knowable_ts": knowable_ts, "verdict": verdict}
        self._append(event)
        return event

    # ------------------------------------------------------------- render
    def calibration(self) -> Dict[str, Any]:
        """The fleet's engineering-bet hit rate, plus the nag: overdue bets.
        rate = hit / all scored non-void verdicts (partial and residual count
        against, exactly so near-misses cannot inflate the number)."""
        state = self.state()
        by_author: Dict[str, Dict[str, Any]] = {}
        overdue: List[Dict[str, Any]] = []
        now = float(self._now())
        for fid in sorted(state):
            row = state[fid]
            v = row.get("verdict")
            if v:
                a = by_author.setdefault(row.get("registered_by", "?"),
                                         {k: 0 for k in VERDICTS})
                a[v] += 1
            elif float(row.get("horizon_ts", 0)) < now:
                overdue.append(row)
        for a in by_author.values():
            scored = sum(a[k] for k in VERDICTS if k != "voided")
            a["rate"] = (a["hit"] / scored) if scored else None
        overdue.sort(key=lambda r: r.get("horizon_ts", 0))
        return {"by_author": by_author, "overdue": overdue}
