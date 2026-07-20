# DRAFT ARTIFACT (T097-S1 fence input) -- NOT WIRED, moved out of core/ pending fence verdict.
# Original target: core/comm/progress.py. See t097-s1-fence-brief-2026-07-20.md.
"""core.comm.progress -- RB-27 turn-progress stamps (T097-S1, the revival mesh's floor).

The C1-8 incident in one line: a runner sat in a 25-40 minute silent window while every
gauge (daemon heartbeat, presence, process-alive) read healthy, because liveness was
measured at the process layer and nothing measured TURN progress. The fleet's unanimous
revival-mesh law (docs/revival-mesh-reconciliation-2026-07-19.md C2): detection precedes
action, and detection means a per-hop progress stamp peers can read as an AGE.

This module is the K0-genus shared seam: every runner (deepseek, kimi, sol) stamps through
the same two functions; doctor and future revive machinery read through the same one.

Contract:
- stamp() is EMIT-ONLY and FAIL-SOFT: it must never raise into a turn, never block the hot
  path (single Redis SET, no retries), and its absence degrades reads to "no stamp", never
  an error. A broken stamp layer must not be able to hurt the machinery it observes
  (safety_net_detector_must_not_share_failure_mode).
- Ages are computed from the stamp's OWN ts at read time -- never from file mtimes and
  never from message arrival times (C1-8 fossil rule, C6-4 stale-stream rule).
- A stamp is a claim of PROGRESS, not of health: phase transitions moving = alive;
  a frozen young stamp means nothing yet; a frozen OLD stamp is exactly the RB-27 signal.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

_KEY_PREFIX = "progress:"
_TTL_S = 2 * 60 * 60   # stamps expire; a vanished key reads as "no stamp", never stale truth


def _client():
    from core.comm.bus import Bus   # lazy: import-cheap for non-runner callers
    return Bus()._client


def stamp(agent: str, phase: str, detail: Optional[Dict[str, Any]] = None) -> None:
    """Record that <agent>'s turn machinery reached <phase> NOW. Fail-soft, emit-only."""
    try:
        payload = {"ts": time.time(), "phase": str(phase)[:64]}
        if detail:
            payload["detail"] = {str(k)[:32]: str(v)[:120] for k, v in list(detail.items())[:6]}
        _client().set(_KEY_PREFIX + agent, json.dumps(payload), ex=_TTL_S)
    except Exception:
        pass


def read(agent: str) -> Optional[Dict[str, Any]]:
    """The raw last stamp for <agent>, or None. Adds computed age_s. Fail-soft."""
    try:
        raw = _client().get(_KEY_PREFIX + agent)
        if not raw:
            return None
        rec = json.loads(raw)
        rec["age_s"] = max(0.0, time.time() - float(rec.get("ts", 0)))
        return rec
    except Exception:
        return None


def render_line(agent: str) -> str:
    """One doctor-ready line: last-progress age + phase, or an honest no-stamp."""
    rec = read(agent)
    if rec is None:
        return f"progress {agent}: no stamp (runner predates S1 or stamps expired)"
    age = rec["age_s"]
    age_txt = f"{int(age)}s" if age < 120 else f"{int(age // 60)}m{int(age % 60)}s"
    return f"progress {agent}: {age_txt} ago ({rec.get('phase', '?')})"
