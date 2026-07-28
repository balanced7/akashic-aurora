"""role_queue -- T108 S1: load-balanced role-addressed work with claim semantics.

Design settled by the T108 fence (research/reviewed/t108-fence-halves-2026-07-28.md), the
build-queue synthesis AS AMENDED by the codex/Sol outside review, and Daniel's gate
2026-07-28 ~04:00 ("Lets get to work, we can iterate more later if there is need").

WHAT THIS IS: ONE work queue per agent ROLE. Any free seat claims the next item, exactly
once. This is the single place serialization survives in the N-seat architecture -- role
work must not be double-executed -- and it uses the primitive built for it:

  * NATIVE CONSUMER GROUPS (XREADGROUP): exactly-once claim per group; the PEL is the claim
    ledger; XAUTOCLAIM recovers from dead AND stalled claimants (P1, P2).
  * SIDE-EFFECT FENCE (P3, kimi's fence): a per-message fence key names the CURRENT
    claimant; commit() is an atomic compare-and-delete only the current claimant passes.
    A reclaimed (stale) writer's commit is REFUSED -- its side effect never crosses the hop.
    Fenced ONLY at commit, not blanket: pure/read-only role work pays nothing extra.
  * FRESHNESS (P4): publish() stamps fresh_until; delivery past it is DROPPED-AS-STALE
    (acked + loud), never handed to a consumer -- the resent packet that arrived too late
    (netcode doc sec 5; games drop it, never replay it).
  * PROJECTION (P5, the Sol amendment): claim_state() derives from the stream PEL + fence
    records ONLY. Nothing here owns state a rebuild could not rederive; the mailbox may
    RENDER this, it never stores it.

Six invariants (the slice-2 spec header, replacing law-citation-per-line): one durable
message identity | one current claim generation | one directory of live seats (S2) |
per-seat replicated views (slice 1) | lease expiry without message loss | typed channel
semantics.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _connect():
    from core.comm.bus import _connect as bus_connect
    return bus_connect()


def _loud(msg: str) -> None:
    try:
        from core.comm.bus import _loud as bus_loud
        bus_loud(msg)
    except Exception:
        import sys
        print(msg, file=sys.stderr)


def _stream_key(ns: str, agent: str) -> str:
    return f"{ns}:role:{agent}"


def _group(agent: str) -> str:
    return f"{agent}-workers"


def _fence_key(ns: str, agent: str, msg_id: str) -> str:
    return f"{ns}:rolefence:{agent}:{msg_id}"


# Atomic compare-and-delete: commit passes ONLY while the fence still names this claimant.
_COMMIT_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  redis.call('del', KEYS[1])
  return 1
end
return 0
"""


def _ensure_group(client, stream: str, group: str) -> None:
    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception as e:                       # BUSYGROUP = already exists (idempotent)
        if "BUSYGROUP" not in str(e):
            raise


@dataclass
class Claim:
    ns: str
    agent: str
    msg_id: str
    consumer: str
    fields: Dict[str, Any] = field(default_factory=dict)


def publish(ns: str, agent: str, kind: str, content: Any = None, *,
            meta: Optional[Dict[str, Any]] = None,
            freshness_s: Optional[float] = None, client=None) -> Optional[str]:
    """Add one role-work item. Returns the message id (the durable message identity)."""
    client = client or _connect()
    stream = _stream_key(ns, agent)
    env = {"kind": str(kind), "content": json.dumps(content, default=str),
           "ts": str(time.time()), "meta": json.dumps(meta or {}, default=str),
           "fresh_until": str(time.time() + freshness_s) if freshness_s else ""}
    _ensure_group(client, stream, _group(agent))
    return str(client.xadd(stream, env))


def _is_stale(fields: Dict[str, Any], now: Optional[float] = None) -> bool:
    fu = str(fields.get("fresh_until") or "")
    if not fu:
        return False
    try:
        return (now or time.time()) > float(fu)
    except ValueError:
        return False


def _drop_stale(client, ns: str, agent: str, msg_id: str, fields: Dict[str, Any]) -> None:
    """P4: ack + clear fence + LOUD. Dropped-as-stale is a decision, never a silence."""
    stream, group = _stream_key(ns, agent), _group(agent)
    try:
        client.xack(stream, group, msg_id)
        client.delete(_fence_key(ns, agent, msg_id))
    except Exception:
        pass
    _loud(f"[role-queue] DROPPED-AS-STALE {msg_id} (kind={fields.get('kind')}) -- past its "
          f"freshness window; a task redelivered too late is not re-executed")
    try:
        from core.events.event_log import capture_event
        capture_event("role_stale_drop", {"agent": agent, "msg_id": msg_id,
                                          "kind": str(fields.get("kind", ""))})
    except Exception:
        pass


def claim_next(ns: str, agent: str, consumer: str, *, block_ms: int = 0,
               client=None) -> Optional[Claim]:
    """Claim the next role-work item for `consumer`. Exactly-once per group (P1); stale
    items are dropped, never delivered (P4); the fence names the claimant (P3)."""
    client = client or _connect()
    stream, group = _stream_key(ns, agent), _group(agent)
    _ensure_group(client, stream, group)
    for _ in range(64):                            # drain stales without recursing forever
        try:
            res = client.xreadgroup(group, consumer, {stream: ">"}, count=1,
                                    block=(block_ms or None))
        except Exception:
            return None
        entries = [(sid, f) for _s, rows in (res or []) for sid, f in rows]
        if not entries:
            return None
        msg_id, fields = str(entries[0][0]), dict(entries[0][1])
        if _is_stale(fields):
            _drop_stale(client, ns, agent, msg_id, fields)
            continue
        client.set(_fence_key(ns, agent, msg_id), consumer)
        return Claim(ns=ns, agent=agent, msg_id=msg_id, consumer=consumer, fields=fields)
    return None


def reclaim_stalled(ns: str, agent: str, consumer: str, *, min_idle_s: float,
                    client=None) -> List[Claim]:
    """P2: take over claims idle past `min_idle_s` (stalled OR dead claimants -- XAUTOCLAIM
    moves PEL ownership; the fence transfers with it, which is what fences the old writer)."""
    client = client or _connect()
    stream, group = _stream_key(ns, agent), _group(agent)
    _ensure_group(client, stream, group)
    try:
        res = client.xautoclaim(stream, group, consumer,
                                min_idle_time=int(min_idle_s * 1000), start_id="0-0")
    except Exception:
        return []
    # redis-py returns (next_start, entries) or (next_start, entries, deleted) per version.
    entries = res[1] if isinstance(res, (list, tuple)) and len(res) >= 2 else []
    out: List[Claim] = []
    for sid, fields in entries or []:
        msg_id, fields = str(sid), dict(fields or {})
        if _is_stale(fields):
            _drop_stale(client, ns, agent, msg_id, fields)
            continue
        client.set(_fence_key(ns, agent, msg_id), consumer)   # authority transfer (P3)
        out.append(Claim(ns=ns, agent=agent, msg_id=msg_id, consumer=consumer, fields=fields))
    return out


def commit(claim: Claim, *, client=None) -> bool:
    """The side-effect gate (P3). Atomic compare-and-delete on the fence: passes ONLY while
    the fence still names this claimant. A reclaimed writer gets False -- its work product
    must not land. On pass: XACK (the claim leaves the PEL; the item is done)."""
    if claim is None:
        return False
    client = client or _connect()
    try:
        ok = bool(client.eval(_COMMIT_LUA, 1,
                              _fence_key(claim.ns, claim.agent, claim.msg_id),
                              claim.consumer))
    except Exception:
        return False
    if not ok:
        _loud(f"[role-queue] FENCED: stale claimant '{claim.consumer}' refused commit on "
              f"{claim.msg_id} -- the claim was reclaimed; this side effect does not land")
        return False
    try:
        client.xack(_stream_key(claim.ns, claim.agent), _group(claim.agent), claim.msg_id)
    except Exception:
        pass
    return True


def claim_state(ns: str, agent: str, msg_id: str, *, client=None) -> Dict[str, Any]:
    """P5: the projection. Derived from PEL + fence ONLY -- any fresh reader computes the
    same answer; nothing here is a cache that could diverge from the durable layer."""
    client = client or _connect()
    stream, group = _stream_key(ns, agent), _group(agent)
    holder = None
    try:
        holder = client.get(_fence_key(ns, agent, msg_id))
    except Exception:
        pass
    pel = []
    try:
        pel = client.xpending_range(stream, group, min=msg_id, max=msg_id, count=1) or []
    except Exception:
        pel = []
    if not pel and not holder:
        return {"claimed_by": None, "pending": False}
    row = pel[0] if pel else {}
    return {"claimed_by": holder or (row.get("consumer") if isinstance(row, dict) else None),
            "pending": bool(pel),
            "idle_ms": (row.get("time_since_delivered") if isinstance(row, dict) else None),
            "deliveries": (row.get("times_delivered") if isinstance(row, dict) else None)}
