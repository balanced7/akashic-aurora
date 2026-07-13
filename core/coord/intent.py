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
import os
import re
import time
from typing import Any, Dict, List, Optional


def _ns() -> str:
    # ns-isolation (2026-07-12 core/coord follow-up, deepseek-reviewed): intent coordination is
    # per-namespace (a drill agent's intents must not collide with live). Default "bifrost"; per-call.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _intent_prefix() -> str:
    return f"{_ns()}:intent:"
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
    return f"{_intent_prefix()}{agent}:{slug(intent)}"


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
        pattern = f"{_intent_prefix()}{agent}:*" if agent else f"{_intent_prefix()}*"
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


# --- negotiation round: brief window after user input where agents declare plans ---

PROPOSAL_TIMEOUT = 8.0          # seconds agents have to respond before the round auto-closes
def _proposal_ns() -> str:
    return f"{_ns()}:proposal"
PROPOSAL_TTL = 60               # proposal records auto-expire after a minute


def propose(agent: str, plan: Dict[str, Any], client: Any = None) -> Dict[str, Any]:
    """Submit a proposal for the current negotiation round. The plan MUST include:
      - what: short description of the task
      - scope: list of files/dirs/topics
      - estimate: rough time/effort (e.g. '~5 min', '1 slice')
    Returns the full round state: every agent's proposal + conflict verdicts.
    Fail-open: no Redis -> admitted but no peer visibility."""
    c = client or _client()
    if c is None:
        return {"ok": True, "offline": True, "round": {}}
    key = f"{_proposal_ns()}:{_round_id()}:{agent}"
    payload = {
        "agent": agent, "what": str(plan.get("what", "")), "intent": slug(plan.get("intent") or plan.get("what", "")),
        "scope": _norm_scope(plan.get("scope")),
        "estimate": str(plan.get("estimate", "")), "ts": _now(),
    }
    try:
        c.set(key, json.dumps(payload), ex=PROPOSAL_TTL)
    except Exception:
        pass
    return {"ok": True, "round": _round_state(c)}


def round_state(client: Any = None) -> Dict[str, Any]:
    """Current state of the negotiation round: every proposal + conflict map."""
    return _round_state(client or _client())


def _round_id() -> str:
    """Stable round id: minute-granularity so proposals within the same brief window group together."""
    return time.strftime("%Y%m%d%H%M")


def _round_state(c) -> Dict[str, Any]:
    if c is None:
        return {"proposals": [], "conflicts": [], "verdict": "offline", "agents": []}
    rid = _round_id()
    proposals: List[Dict[str, Any]] = []
    try:
        for k in (c.keys(f"{_proposal_ns()}:{rid}:*") or []):
            raw = c.get(k)
            if raw:
                try:
                    proposals.append(json.loads(raw))
                except Exception:
                    pass
    except Exception:
        pass
    agents = sorted({p["agent"] for p in proposals})
    # conflicts: two agents claiming the same scope file
    conflicts = _scope_conflicts(proposals)
    # verdict: green (no conflicts), amber (same file different intents — fine but flag),
    #          red (same file same intent — coordinate)
    conflict_files = {c["file"] for c in conflicts}
    same_intent = [c for c in conflicts if c.get("same_intent")]
    if same_intent:
        verdict = "red"
        reason = "duplicate intent on: " + ", ".join(c["file"] for c in same_intent)
    elif conflict_files:
        verdict = "amber"
        reason = "shared files with different intents: " + ", ".join(sorted(conflict_files))
    else:
        verdict = "green"
        reason = "no scope conflicts"
    return {
        "proposals": proposals, "conflicts": conflicts, "verdict": verdict,
        "reason": reason, "agents": agents, "round": rid,
    }


def _scope_conflicts(proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find files claimed by more than one agent. Returns list of {file, agents, same_intent}.

    Intent matching v1 (honest): uses the explicit 'intent' TAG field if present, falling back to
    slug('what') only for backward compat. The TAG is the coordination key; 'what' is human-readable
    description. This avoids the fuzzy-intent trap (slug('restyle header') != slug('restyle the header'))
    by requiring agents to use the same tag for the same work. Fuzzy semantic overlap is deferred."""
    file_agents: Dict[str, List[Dict[str, Any]]] = {}
    for p in proposals:
        for f in p.get("scope", []):
            file_agents.setdefault(f, []).append(p)
    out = []
    for f, claimers in file_agents.items():
        if len(claimers) > 1:
            agents = [c["agent"] for c in claimers]
            # Prefer explicit intent tag, fall back to slug(what) for backward compat
            intent_tags = [slug(c.get("intent", "") or c.get("what", "")) for c in claimers]
            out.append({
                "file": f, "agents": agents,
                "same_intent": len(set(intent_tags)) < len(intent_tags),  # any duplicate tags?
            })
    return out


def clear_round(client: Any = None) -> int:
    """Remove all proposals for the current round. Returns count deleted."""
    c = client or _client()
    if c is None:
        return 0
    rid = _round_id()
    count = 0
    try:
        for k in (c.keys(f"{_proposal_ns()}:{rid}:*") or []):
            c.delete(k)
            count += 1
    except Exception:
        pass
    return count


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
