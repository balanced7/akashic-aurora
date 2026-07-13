"""Advisory path-locks (Concurrency design C2).

Two peers coordinate on WHO is editing WHAT without a central authority: an agent
claims an advisory lock on a path before editing it, and the claim is visible to the
other agent (surfaced at boot + presence). The lock is ADVISORY -- it coordinates
cooperating peers we own; it is not OS-enforced.

Two safety properties, the lessons every distributed-lock source agrees on:
  * **Fencing token** -- each acquisition gets a monotonic token, so a stale/paused
    holder (whose lock expired and was reclaimed) can be detected and rejected at the
    commit gate. validate_token() is that check.
  * **TTL** -- a crashed holder's lock auto-expires and is reclaimable; no deadlock.

Redis-backed via the canonical connector; fail-soft -- when Redis is down there is no
locking (advisory degrades to "no coordination", surfaced as online=False), never a
crash. Keys:
    bifrost:lock:<norm_path>  -> JSON {agent, token, path, ts, ttl}
    bifrost:lock:_seq         -> INCR fencing-token sequence
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ns-isolation GLOBAL (2026-07-12, deliberate -- do NOT scope to BIFROST_NAMESPACE): advisory PATH
# LOCKS protect the SHARED FILESYSTEM, which is one resource across ALL namespaces. Scoping would let
# a drill agent and a live agent edit the SAME file each believing it holds the lock -- reintroducing
# exactly the edit race these locks exist to prevent. In the GLOBAL_MODULES allowlist (see
# tests/test_coordination_namespace_isolation.py).
NS = "bifrost"
SEQ_KEY = f"{NS}:lock:_seq"
DEFAULT_TTL = 900   # 15 min -- long enough for a slice, short enough to self-heal a crash
_ROOT = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    try:
        from core.comm.bus import _connect as bus_connect
        return bus_connect()
    except Exception:
        return None


def normalize_path(path: Any) -> str:
    """Canonical key form: repo-relative, forward slashes, case-folded (Windows is
    case-insensitive, so two spellings of one file must collide to one lock)."""
    p = str(path or "").strip().replace("\\", "/")
    try:
        ap = Path(p)
        if ap.is_absolute():
            p = ap.resolve().relative_to(_ROOT).as_posix()
    except Exception:
        pass
    while p.startswith("./"):
        p = p[2:]
    return p.strip("/").lower()


def _lock_key(path: str) -> str:
    return f"{NS}:lock:{normalize_path(path)}"


class LockManager:
    """An agent's handle on the advisory path-locks. One per agent identity."""

    def __init__(self, agent_id: str, client: Optional[Any] = None):
        self.agent_id = str(agent_id or "unknown")
        self._client = client if client is not None else _connect()

    @property
    def online(self) -> bool:
        return self._client is not None

    def _next_token(self) -> int:
        return int(self._client.incr(SEQ_KEY))

    def acquire(self, path: str, ttl: int = DEFAULT_TTL) -> Dict[str, Any]:
        """Claim `path`. Returns {ok, online, mine, token, held_by, path}. Re-claiming a
        lock you already hold refreshes its TTL (re-entrant) and keeps your token."""
        norm = normalize_path(path)
        if not self.online:
            return {"ok": False, "online": False, "mine": False, "token": None,
                    "held_by": None, "path": norm}
        key = _lock_key(norm)
        try:
            existing = self._client.get(key)
            if existing:
                cur = json.loads(existing)
                if cur.get("agent") == self.agent_id:
                    cur["ts"] = _now(); cur["ttl"] = ttl
                    self._client.set(key, json.dumps(cur), ex=ttl)   # extend (re-entrant)
                    return {"ok": True, "online": True, "mine": True,
                            "token": cur.get("token"), "held_by": self.agent_id, "path": norm}
                return {"ok": False, "online": True, "mine": False,
                        "token": cur.get("token"), "held_by": cur.get("agent"), "path": norm}
            token = self._next_token()
            value = json.dumps({"agent": self.agent_id, "token": token, "path": norm,
                                "ts": _now(), "ttl": ttl})
            if self._client.set(key, value, nx=True, ex=ttl):
                return {"ok": True, "online": True, "mine": True, "token": token,
                        "held_by": self.agent_id, "path": norm}
            # lost the race -- report the winner
            cur = json.loads(self._client.get(key) or "{}")
            return {"ok": False, "online": True, "mine": False,
                    "token": cur.get("token"), "held_by": cur.get("agent"), "path": norm}
        except Exception:
            return {"ok": False, "online": False, "mine": False, "token": None,
                    "held_by": None, "path": norm}

    def release(self, path: str) -> bool:
        """Release `path` -- only if YOU hold it (advisory: don't steal a peer's lock)."""
        if not self.online:
            return False
        key = _lock_key(path)
        try:
            cur = self._client.get(key)
            if cur and json.loads(cur).get("agent") == self.agent_id:
                self._client.delete(key)
                return True
        except Exception:
            pass
        return False

    def holder(self, path: str) -> Optional[Dict[str, Any]]:
        if not self.online:
            return None
        try:
            cur = self._client.get(_lock_key(path))
            return json.loads(cur) if cur else None
        except Exception:
            return None

    def validate_token(self, path: str, token: Any, agent: Optional[str] = None) -> bool:
        """The fencing check for a commit gate: True iff `path` is CURRENTLY held by
        `agent` (default: me) with exactly `token`. A stale token (lock expired and
        reclaimed by a peer) returns False."""
        h = self.holder(path)
        who = agent or self.agent_id
        return bool(h and h.get("agent") == who and h.get("token") == token)

    def list_locks(self) -> List[Dict[str, Any]]:
        if not self.online:
            return []
        out: List[Dict[str, Any]] = []
        try:
            for key in self._client.scan_iter(f"{NS}:lock:*"):
                if key.endswith(":_seq"):
                    continue
                v = self._client.get(key)
                if v:
                    out.append(json.loads(v))
        except Exception:
            return []
        return sorted(out, key=lambda d: d.get("path", ""))


def path_conflict(path: str, agent: str, client: Optional[Any] = None) -> Dict[str, Any]:
    """Would `agent` editing `path` collide with a peer's advisory lock?
    Returns {conflict: bool, held_by, reason}. Fail-open: no Redis / no lock -> no conflict."""
    lm = LockManager(agent, client=client)
    h = lm.holder(path)
    if h and h.get("agent") and h.get("agent") != lm.agent_id:
        who = h.get("agent")
        return {"conflict": True, "held_by": who, "reason": (
            f"'{normalize_path(path)}' is locked by {who} (token {h.get('token')}). "
            f"Edit a file you hold, request a handoff via the bus, or wait for release "
            f"(advisory lock, see docs/concurrency-design.md C2).")}
    return {"conflict": False, "held_by": None, "reason": ""}


def guard_write(path: str, agent: str, ttl: int = DEFAULT_TTL, client: Optional[Any] = None) -> Dict[str, Any]:
    """The ONE environmental write-gate an agent calls BEFORE editing `path` (A0.1).

    Turns coordination from social (negotiate: 'stand down please') into environmental (read shared
    state, react): it PROACTIVELY claims the advisory lock so peers are auto-blocked, or YIELDS if a
    peer already holds it. The claim is re-entrant, so calling it on every edit REFRESHES the TTL --
    a lock never lapses mid-task while its holder keeps working (the gap that reopened today's
    collision window). The lock holder IS the influence map: `locks` / holder(path) shows who's in a
    file before anyone types. Fail-open: no Redis -> ok (never wedge a local edit).

    Returns {ok, held_by, claimed, reason}. When ok is False the caller should YIELD (not retry) and
    surface `reason` on the bus so the yield is visible, not silent."""
    lm = LockManager(agent, client=client)
    res = lm.acquire(path, ttl=ttl)                     # re-entrant: extends the TTL if already mine
    if res.get("ok"):
        return {"ok": True, "held_by": agent, "claimed": True, "reason": ""}
    if res.get("online"):                               # a peer holds it -> yield, don't clobber
        h = lm.holder(path) or {}
        who = h.get("agent") or res.get("held_by")
        return {"ok": False, "held_by": who, "claimed": False, "reason": (
            f"'{normalize_path(path)}' is being edited by {who} (advisory lock). Yielding -- "
            f"coordinate on the bus or wait for release (C2, docs/concurrency-design.md).")}
    return {"ok": True, "held_by": agent, "claimed": False, "reason": ""}   # offline -> fail-open
