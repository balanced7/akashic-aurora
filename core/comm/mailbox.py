"""mailbox -- T095 M0: shadow mailbox state index over the append-only lanes.

Read-only follower: derives per-message per-agent state from what the streams
already contain.  Evidence ladder (docs/comms-mailbox-design-2026-07.md sec 2,
counter-folded 2026-07-18):

    acked > replied/auto_acked > consumed > unhandled

- ``acked``      -- a durable msg_ack references one of the message's stream ids
- ``replied``    -- some envelope carries ``meta.answers == <one of its ids>``
- ``auto_acked`` -- same signal on a handoff (T026: an answering reply = handled)
- ``consumed``   -- the target agent's committed cursor has advanced past the
                    message (the cursor IS the consumption record; zero new writes)
- ``unhandled``  -- none of the above

M0 is OBSERVATIONAL ONLY.  The index writes nothing outside ``{ns}:mailbox:*``:
no cursors, no acks, no sends, no wake state.  Toward the transport it is
fail-silent; toward the operator it is fail-LOUD (``available: False`` with a
fall-back-to-peek reason).  Kill switch: ``AKASHIC_MAILBOX=0``.

Retention is tiered by kind (deepseek counter sec 3): handoff/request/question/
blocker entries outlive chat-tier entries, and cap eviction drops non-long kinds
first so a chatty session can never evict an unhandled handoff.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.comm import packet_spec

# ------------------------------------------------------------------ constants

LONG_KINDS = frozenset({"handoff", "request", "question", "blocker"})
LONG_RETENTION_S = 30 * 86400
SHORT_RETENTION_S = 7 * 86400
DEFAULT_CAP = 5000
DEFAULT_BUDGET = 2000
_LAG_PROBE = 64
_ANSWERED_KEY_CAP = 20000

TIER_RANK = {"unhandled": 0, "consumed": 1, "auto_acked": 2, "replied": 2, "acked": 3}

# source name -> (stream key template, cursor hash kind, cursor field)
#   cursor hash kind: "lane" -> {ns}:cursor:lane:{agent} ; "legacy" -> {ns}:cursor:{agent}
_SOURCES: Tuple[Tuple[str, str, str, str], ...] = (
    ("work_inbox",   "{ns}:work:inbox:{agent}", "lane",   "inbox"),
    ("sig_inbox",    "{ns}:sig:inbox:{agent}",  "lane",   "sig_inbox"),
    ("legacy_inbox", "{ns}:inbox:{agent}",      "legacy", "inbox"),
    ("work_bc",      "{ns}:work:broadcast",     "lane",   "bc"),
    ("sig_bc",       "{ns}:sig:broadcast",      "lane",   "sig_bc"),
    ("legacy_bc",    "{ns}:broadcast",          "legacy", "bc"),
)


def enabled() -> bool:
    return os.getenv("AKASHIC_MAILBOX", "1") not in ("0", "false", "False")


def _connect():
    from core.comm.bus import _connect as bus_connect
    return bus_connect()


# ------------------------------------------------------------------ helpers

def _sid_tuple(sid: str) -> Tuple[int, int]:
    ms, _, seq = str(sid).partition("-")
    try:
        return (int(ms or 0), int(seq or 0))
    except ValueError:
        return (0, 0)


def _sid_lte(a: str, b: str) -> bool:
    return _sid_tuple(a) <= _sid_tuple(b)


def _fallback_sha(fields: Dict[str, str]) -> str:
    basis = "|".join(str(fields.get(k, "")) for k in ("frm", "to", "kind", "content", "ts"))
    return "fb" + hashlib.sha256(basis.encode("utf-8", "replace")).hexdigest()[:40]


def _entry_ts_s(fields: Dict[str, str], sid: str) -> float:
    ts = str(fields.get("ts", ""))
    try:
        return float(ts)
    except ValueError:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        ms, _, _seq = str(sid).partition("-")
        try:
            return int(ms) / 1000.0
        except ValueError:
            return 0.0


def _is_mailbox_kind(kind: str, meta: Dict[str, Any]) -> bool:
    if packet_spec.lane_for(kind) == "trace":
        return False
    try:
        if packet_spec.is_trace_kind(kind):
            return False
    except Exception:
        pass
    if isinstance(meta, dict) and meta.get("display_only"):
        return False
    return True


def _keys(ns: str, agent: str) -> Dict[str, str]:
    return {
        "pos": f"{ns}:mailbox:pos:{agent}",
        "z": f"{ns}:mailbox:z:{agent}",
        "msg": f"{ns}:mailbox:msg:{agent}:",          # + sha
        "evicted": f"{ns}:mailbox:evicted:{agent}",
        "answered": f"{ns}:mailbox:answered",          # global answers map
    }


def _unavailable(reason: str) -> Dict[str, Any]:
    return {"available": False,
            "reason": f"{reason} -- fall back to bifrost-sync peek",
            "entries": [], "counts": {}, "index_lag": -1, "evicted": 0}


# ------------------------------------------------------------------ ingest

def _ingest_one(client, ns: str, agent: str, source: str, sid: str,
                fields: Dict[str, str]) -> Optional[str]:
    kind = str(fields.get("kind", "_unknown") or "_unknown")
    try:
        meta = json.loads(fields.get("meta") or "{}")
    except (ValueError, TypeError):
        meta = {}
    # feed the global answers map from ANY envelope, even non-mailbox kinds
    answers = meta.get("answers") if isinstance(meta, dict) else None
    if answers:
        k = _keys(ns, agent)
        try:
            if len(client.hgetall(k["answered"])) < _ANSWERED_KEY_CAP:
                client.hset(k["answered"], str(answers), json.dumps(
                    {"by": fields.get("frm", "?"), "ts": fields.get("ts", ""), "sid": sid}))
        except Exception:
            raise
    if not _is_mailbox_kind(kind, meta):
        return None
    sha = str(fields.get("sha") or "") or _fallback_sha(fields)
    k = _keys(ns, agent)
    mkey = k["msg"] + sha
    existing = client.hgetall(mkey) or {}
    try:
        ids = json.loads(existing.get("ids") or "{}")
    except (ValueError, TypeError):
        ids = {}
    ids[source] = sid
    mapping = {
        "sha": sha, "kind": kind, "frm": str(fields.get("frm", "?")),
        "ts": str(fields.get("ts", "")), "ids": json.dumps(ids),
        "ts_s": str(existing.get("ts_s") or _entry_ts_s(fields, sid)),
    }
    client.hset(mkey, mapping=mapping)
    client.zadd(k["z"], {sha: float(mapping["ts_s"]) if float(mapping["ts_s"]) > 0
                         else float(_sid_tuple(sid)[0])})
    return sha


def catch_up(ns: str, agent: str, *, client=None,
             budget: Optional[int] = DEFAULT_BUDGET) -> Dict[str, Any]:
    """Incremental follower: ingest new entries beyond the per-source index position.
    ``budget=0`` counts lag without ingesting (pin 7). Only ``{ns}:mailbox:*`` is
    written."""
    client = client if client is not None else _connect()
    k = _keys(ns, agent)
    pos = client.hgetall(k["pos"]) or {}
    ingested = 0
    lag = 0
    for source, tmpl, _chash, _cfield in _SOURCES:
        stream = tmpl.format(ns=ns, agent=agent)
        last = str(pos.get(source, "0-0"))
        probe_n = _LAG_PROBE if not budget else int(budget) + 1
        entries = client.xrange(stream, "(" + last, "+", count=probe_n) or []
        take = 0 if budget == 0 else (len(entries) if budget is None else min(len(entries), int(budget)))
        for sid, fields in entries[:take]:
            _ingest_one(client, ns, agent, source, str(sid), dict(fields))
            ingested += 1
            last = str(sid)
        if take:
            client.hset(k["pos"], source, last)
        lag += len(entries) - take
    return {"ingested": ingested, "lag": lag}


# ------------------------------------------------------------------ eviction

def _evict(client, ns: str, agent: str, cap: int) -> int:
    k = _keys(ns, agent)
    now = time.time()
    total_evicted = 0
    members = client.zrange(k["z"], 0, -1, withscores=True) or []
    # age sweep, tiered by kind
    for sha, score in members:
        m = client.hgetall(k["msg"] + str(sha)) or {}
        ts_s = float(m.get("ts_s") or score or 0)
        if ts_s <= 0:
            continue
        limit = LONG_RETENTION_S if m.get("kind") in LONG_KINDS else SHORT_RETENTION_S
        if now - ts_s > limit:
            client.zrem(k["z"], str(sha))
            client.delete(k["msg"] + str(sha))
            client.hincrby(k["evicted"], m.get("kind", "_unknown"), 1)
            total_evicted += 1
    # cap eviction: oldest non-long kinds first, then oldest of anything
    while client.zcard(k["z"]) > cap:
        victims = client.zrange(k["z"], 0, -1) or []
        victim = None
        for sha in victims:
            m = client.hgetall(k["msg"] + str(sha)) or {}
            if m.get("kind") not in LONG_KINDS:
                victim = (sha, m.get("kind", "_unknown"))
                break
        if victim is None and victims:
            sha = victims[0]
            m = client.hgetall(k["msg"] + str(sha)) or {}
            victim = (sha, m.get("kind", "_unknown"))
        if victim is None:
            break
        client.zrem(k["z"], str(victim[0]))
        client.delete(k["msg"] + str(victim[0]))
        client.hincrby(k["evicted"], victim[1], 1)
        total_evicted += 1
    return total_evicted


def _evicted_total(client, ns: str, agent: str) -> int:
    h = client.hgetall(_keys(ns, agent)["evicted"]) or {}
    try:
        return sum(int(v) for v in h.values())
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------ resolve

def _default_acks(ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    try:
        from core.comm.promoter import acks_for
        return acks_for(ids)
    except Exception:
        return {}


def _resolve(client, ns: str, agent: str,
             acks_lookup: Optional[Callable[[List[str]], Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Tier every live entry. Cursor hashes are read EXACTLY ONCE (snapshot
    semantics, pin 12); acks use the exact per-id lookup; answers ride the global
    map fed at ingest time."""
    k = _keys(ns, agent)
    lane_cursor = client.hgetall(f"{ns}:cursor:lane:{agent}") or {}
    legacy_cursor = client.hgetall(f"{ns}:cursor:{agent}") or {}
    cursors = {"lane": lane_cursor, "legacy": legacy_cursor}
    answered = client.hgetall(k["answered"]) or {}
    members = client.zrange(k["z"], 0, -1, withscores=True) or []
    all_ids: List[str] = []
    raw: List[Dict[str, Any]] = []
    for sha, score in members:
        m = client.hgetall(k["msg"] + str(sha)) or {}
        if not m:
            continue
        try:
            ids = json.loads(m.get("ids") or "{}")
        except (ValueError, TypeError):
            ids = {}
        all_ids.extend(ids.values())
        raw.append({"sha": str(sha), "kind": m.get("kind", "_unknown"),
                    "frm": m.get("frm", "?"), "ts": m.get("ts", ""),
                    "ts_s": float(m.get("ts_s") or 0), "score": float(score),
                    "ids": ids})
    acks = (acks_lookup or _default_acks)(all_ids) if all_ids else {}
    out: List[Dict[str, Any]] = []
    for e in raw:
        tier = "unhandled"
        if any(acks.get(str(sid)) for sid in e["ids"].values()):
            tier = "acked"
        elif any(str(sid) in answered for sid in e["ids"].values()):
            tier = "auto_acked" if e["kind"] == "handoff" else "replied"
        else:
            for source, sid in e["ids"].items():
                spec = next((s for s in _SOURCES if s[0] == source), None)
                if spec is None:
                    continue
                cursor_val = cursors[spec[2]].get(spec[3], "")
                if cursor_val and _sid_lte(str(sid), str(cursor_val)):
                    tier = "consumed"
                    break
        e2 = {key: e[key] for key in ("sha", "kind", "frm", "ts", "ids")}
        e2["tier"] = tier
        out.append(e2)
    out.sort(key=lambda e: (min(_sid_tuple(s) for s in e["ids"].values())
                            if e["ids"] else (0, 0), e["sha"]))
    return out


# ------------------------------------------------------------------ public

def query(ns: str, agent: str, *, client=None,
          acks_lookup: Optional[Callable[[List[str]], Dict[str, Any]]] = None,
          cap: int = DEFAULT_CAP, catch_up_budget: Optional[int] = DEFAULT_BUDGET,
          min_evidence: Optional[str] = None) -> Dict[str, Any]:
    """The free question: what is addressed to `agent`, in what state, and why."""
    if not enabled():
        return _unavailable("mailbox disabled (AKASHIC_MAILBOX=0)")
    try:
        client = client if client is not None else _connect()
        cu = catch_up(ns, agent, client=client, budget=catch_up_budget)
        _evict(client, ns, agent, cap)
        entries = _resolve(client, ns, agent, acks_lookup)
        if min_evidence is not None:
            floor = TIER_RANK.get(str(min_evidence), 0)
            entries = [e for e in entries if TIER_RANK.get(e["tier"], 0) <= floor]
        counts: Dict[str, int] = {"unhandled": 0}
        for e in entries:
            counts[e["tier"]] = counts.get(e["tier"], 0) + 1
        return {"available": True, "agent": agent, "entries": entries,
                "counts": counts, "index_lag": int(cu["lag"]),
                "evicted": _evicted_total(client, ns, agent)}
    except Exception as exc:                                  # loud to operator,
        return _unavailable(f"index unavailable ({exc})")      # silent to transport


def rebuild(ns: str, agent: str, *, client=None,
            acks_lookup: Optional[Callable[[List[str]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Drop the agent's index and rebuild from the log; report divergence vs the
    incremental state (pin 3: must be 0 -- the determinism receipt)."""
    if not enabled():
        return _unavailable("mailbox disabled (AKASHIC_MAILBOX=0)")
    try:
        client = client if client is not None else _connect()
        k = _keys(ns, agent)
        old = {e["sha"]: e["tier"] for e in _resolve(client, ns, agent, acks_lookup)}
        for sha in client.zrange(k["z"], 0, -1) or []:
            client.delete(k["msg"] + str(sha))
        client.delete(k["z"])
        client.delete(k["pos"])
        while True:
            cu = catch_up(ns, agent, client=client, budget=DEFAULT_BUDGET)
            if cu["ingested"] == 0:
                break
        new_entries = _resolve(client, ns, agent, acks_lookup)
        new = {e["sha"]: e["tier"] for e in new_entries}
        divergence = sum(1 for sha in set(old) | set(new) if old.get(sha) != new.get(sha))
        return {"available": True, "divergence": divergence, "entries": len(new_entries)}
    except Exception as exc:
        return _unavailable(f"rebuild failed ({exc})")


def explain(ns: str, agent: str, ref: str, *, client=None,
            acks_lookup: Optional[Callable[[List[str]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Evidence chain for one message: which sources carry it, every cursor
    comparison, ack records, answers linkage, and the tier verdict."""
    if not enabled():
        return _unavailable("mailbox disabled (AKASHIC_MAILBOX=0)")
    try:
        client = client if client is not None else _connect()
        entries = _resolve(client, ns, agent, acks_lookup)
        ref = str(ref)
        hit = next((e for e in entries if e["sha"].startswith(ref)
                    or ref in e["ids"].values()), None)
        if hit is None:
            return {"available": True, "found": False, "ref": ref}
        lane_cursor = client.hgetall(f"{ns}:cursor:lane:{agent}") or {}
        legacy_cursor = client.hgetall(f"{ns}:cursor:{agent}") or {}
        answered = client.hgetall(_keys(ns, agent)["answered"]) or {}
        comparisons = []
        for source, sid in hit["ids"].items():
            spec = next((s for s in _SOURCES if s[0] == source), None)
            if spec is None:
                continue
            cursor_val = (lane_cursor if spec[2] == "lane" else legacy_cursor).get(spec[3], "")
            comparisons.append({"source": source, "stream_id": sid,
                                "cursor": cursor_val or None,
                                "consumed": bool(cursor_val and _sid_lte(sid, cursor_val))})
        acks = (acks_lookup or _default_acks)(list(hit["ids"].values()))
        return {"available": True, "found": True, "sha": hit["sha"], "kind": hit["kind"],
                "frm": hit["frm"], "ts": hit["ts"], "tier": hit["tier"],
                "cursor_comparisons": comparisons,
                "acks": {sid: acks.get(str(sid), []) for sid in hit["ids"].values()},
                "answered_by": {sid: json.loads(answered[sid]) for sid in hit["ids"].values()
                                if sid in answered}}
    except Exception as exc:
        return _unavailable(f"explain failed ({exc})")
