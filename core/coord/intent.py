"""
Intent declaration -- Policy 0 of the coordination layer.

The environment coordinates by INTENT, not by file. An agent declares "I intend to X, scope = these
paths/topics"; the environment ADMITS it unless a PEER already holds the same intent (duplicate waste).
Two agents working the same file with DIFFERENT intents both proceed -- the parallel-useful case a
file lock wrongly blocks. That advantage is measured, not asserted: core/coord/experiment.py shows
intent_gate beating lock_gate on parallel-useful and mixed workloads.

Locks are the ENFORCEMENT backstop UNDER this (core/comm/locks.guard_write), not the default: intent
coordinates; the lock only stops a genuine same-resource collision that slips past intent.

Conflict rule (v1, honest): two intents conflict iff the same normalized intent TAG. Scope tags
(files/dirs/topics) are the influence map + what the enforcement backstop reads to know which files an
intent covers. Fuzzy scope-overlap matching is a deliberate LATER refinement, not faked here.

Fail-open on any Redis error (never wedge a local agent). Redis-backed and TTL'd -- a crashed agent's
intent auto-expires, exactly like presence and locks.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

NS = "bifrost"
INTENT_PREFIX = f"{NS}:intent:"
DEFAULT_TTL = 900          # 15 min -- long enough for a slice, self-heals a crash (mirrors locks)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _client():
    """Shared bus Redis client via the sanctioned connector. None when unreachable -> fail open."""
    try:
        from core.comm.bus import get_bus
        return get_bus("intent")._client
    except Exception:
        return None


def slug(intent: str) -> str:
    """Normalize an intent tag: lowercase, trim, non-alnum -> single hyphen. The conflict key."""
    return re.sub(r"[^a-z0-9]+", "-", str(intent).strip().lower()).strip("-") or "unnamed"


def _key(agent: str, intent: str) -> str:
    return f"{INTENT_PREFIX}{agent}:{slug(intent)}"


def _norm_scope(scope) -> List[str]:
    if scope is None:
        return []
    if isinstance(scope, str):
        scope = [scope]
    return [str(s).strip() for s in scope if str(s).strip()]


def active(agent: Optional[str] = None, client: Any = None) -> List[Dict[str, Any]]:
    """Every live intent (the intent influence map), or just one agent's. Expired ones are already
    gone (Redis TTL). Fail-open: no Redis -> []."""
    c = client or _client()
    if c is None:
        return []
    out: List[Dict[str, Any]] = []
    try:
        pattern = f"{INTENT_PREFIX}{agent}:*" if agent else f"{INTENT_PREFIX}*"
        for k in (c.keys(pattern) or []):
            raw = c.get(k)
            if raw:
                try:
                    out.append(json.loads(raw))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def conflicts(agent: str, intent: str, client: Any = None) -> List[Dict[str, Any]]:
    """Active intents that collide with (agent, intent): the SAME normalized tag held by a PEER.
    Same agent re-declaring is NOT a conflict (re-entrant refresh)."""
    tag = slug(intent)
    return [i for i in active(client=client)
            if slug(i.get("intent", "")) == tag and i.get("agent") != agent]


def declare(agent: str, intent: str, scope=None, ttl: int = DEFAULT_TTL, client: Any = None) -> Dict[str, Any]:
    """Declare an intent. ADMITS (registers it, peers now see it on the map) unless a peer already holds
    the same intent -> then YIELDS (does not register; the agent should coordinate or defer). Re-entrant:
    the same agent re-declaring its own intent just refreshes the TTL. Fail-open: no Redis -> admitted."""
    c = client or _client()
    if c is None:
        return {"ok": True, "conflicts": [], "reason": "", "offline": True}
    peers = conflicts(agent, intent, client=c)
    if peers:
        who = ", ".join(sorted({p.get("agent", "?") for p in peers}))
        return {"ok": False, "conflicts": peers, "reason": (
            f"intent '{slug(intent)}' is already declared by {who} -- coordinate or defer "
            f"(duplicate work). Different intents on the same files are fine; this is the SAME intent.")}
    try:
        c.set(_key(agent, intent),
              json.dumps({"agent": agent, "intent": str(intent), "scope": _norm_scope(scope), "ts": _now(), "ttl": ttl}),
              ex=ttl)
    except Exception:
        pass                                     # advisory: never block a local agent on a Redis error
    return {"ok": True, "conflicts": [], "reason": ""}


def release(agent: str, intent: str, client: Any = None) -> bool:
    """Withdraw an intent (work done/abandoned). Idempotent. Fail-open."""
    c = client or _client()
    if c is None:
        return False
    try:
        c.delete(_key(agent, intent))
        return True
    except Exception:
        return False


def covers(agent: str, path: str, client: Any = None) -> bool:
    """True iff `agent` holds an active intent whose scope covers `path` (prefix match). The enforcement
    backstop asks this: an agent writing a file it declared no intent for is acting outside its plan."""
    p = str(path).replace("\\", "/")
    for i in active(agent=agent, client=client):
        for s in (i.get("scope") or []):
            s = str(s).replace("\\", "/")
            if p == s or p.startswith(s.rstrip("/") + "/") or s in p:
                return True
    return False
