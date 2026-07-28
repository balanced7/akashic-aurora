"""roster -- S2: the lobby. Per-seat liveness the whole fleet can read.

Design: build-queue synthesis S2 (Daniel-gated 2026-07-28) + kimi's fence P1 (a heartbeat is
PROVABLY live -- freshness-windowed, never replayed) + W84 (render confesses checked /
NOT-checked) + T5 (the directory carries reachability and inventory pointers, NEVER payload).

WHY THIS EXISTS: the reaper (S4) triggers on heartbeat expiry, and until tonight NO claude
seat published a heartbeat at all -- deepseek and kimi runners beat bifrost:worklive:<agent>,
but seats had nothing per-incarnation. The roster is the reaper's only sensor, the router's
input for bare-role mail (priority: actively-working > idle-alive > stale), and the UI's
honesty about who is actually reachable (Sol rendered "sleeping" for exactly this gap).

Keys (T5: no payload):
    {ns}:worklive:{agent}#{sid8}   JSON {phase, beat_ts, since_ts, seq}, TTL WORKLIVE_TTL_S.

STATE LADDER (kimi P1 -- key-exists is NOT alive):
    LIVE   beat within FRESH_S           STALE  key exists, beat older than FRESH_S
    DEAD   no key (TTL reaped it)        -- absence is the only DEAD; never LIVE by default.
Monotonic beats: heartbeat() refuses to write a beat_ts older than the stored one, so a
replayed/duplicated beat can never resurrect a stale seat or mask a death.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

WORKLIVE_TTL_S = int(os.environ.get("AKASHIC_WORKLIVE_TTL_S", "180") or 180)
FRESH_S = float(os.environ.get("AKASHIC_WORKLIVE_FRESH_S", "45") or 45)


def _connect():
    from core.comm.bus import _connect as bus_connect
    return bus_connect()


def _key(ns: str, agent: str, sid8: str) -> str:
    return f"{ns}:worklive:{agent}#{sid8}"


def heartbeat(ns: str, agent: str, sid8: str, *, phase: str = "idle",
              client=None, _beat_ts: Optional[float] = None) -> bool:
    """Beat this seat's liveness. Monotonic (P5): an older beat_ts never overwrites a
    fresher one. `_beat_ts` is injectable for pins only. Never raises."""
    try:
        client = client or _connect()
        k = _key(ns, agent, str(sid8)[:8])
        now = float(_beat_ts if _beat_ts is not None else time.time())
        prev: Dict[str, Any] = {}
        try:
            prev = json.loads(client.get(k) or "{}")
        except (ValueError, TypeError):
            prev = {}
        prev_beat = float(prev.get("beat_ts") or 0)
        if now < prev_beat:
            # P5: replay refused -- refresh the TTL (the seat IS being touched) but keep
            # the fresher stored beat; a replayed heartbeat cannot rewind liveness.
            client.expire(k, WORKLIVE_TTL_S)
            return False
        doc = {"phase": str(phase), "beat_ts": now,
               "since_ts": float(prev.get("since_ts") or now),
               "seq": int(prev.get("seq") or 0) + 1}
        client.set(k, json.dumps(doc), ex=WORKLIVE_TTL_S)
        return True
    except Exception:
        return False


def _have_summary(client, ns: str, agent: str, sid8: str) -> Dict[str, Any]:
    """T3 (torrent bitfield): the seat's consumed-through positions -- inventory POINTERS,
    never payload (T5). A successor diffs these instead of guessing what a dead seat saw."""
    have: Dict[str, Any] = {}
    try:
        have["legacy_inbox"] = str((client.hgetall(f"{ns}:cursor:{agent}") or {}).get("inbox", "0"))
    except Exception:
        pass
    try:
        have["seat_inbox"] = str(client.hget(f"{ns}:cursor:seat:{agent}#{sid8}", "seat") or "0")
    except Exception:
        pass
    try:
        have["lane_inbox"] = str((client.hgetall(f"{ns}:cursor:lane:{agent}") or {}).get("inbox", "0"))
    except Exception:
        pass
    return have


def roster(ns: str, *, client=None, now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Every known seat in `ns`, with its PROVEN state. Read-only; derives everything from
    worklive keys + cursor hashes (a projection -- rebuild-safe by construction)."""
    client = client or _connect()
    now = float(now if now is not None else time.time())
    rows: List[Dict[str, Any]] = []
    try:
        keys = sorted(client.keys(f"{ns}:worklive:*"))
    except Exception:
        return rows
    for k in keys:
        tail = str(k).rsplit(":worklive:", 1)[-1]
        if "#" not in tail:
            continue                       # agent-level runner worklive (legacy shape) -- skip
        agent, _, sid8 = tail.partition("#")
        try:
            doc = json.loads(client.get(k) or "{}")
        except (ValueError, TypeError):
            doc = {}
        beat = float(doc.get("beat_ts") or 0)
        age = now - beat if beat else None
        state = "LIVE" if (age is not None and age <= FRESH_S) else "STALE"
        rows.append({
            "seat": tail, "agent": agent, "sid8": sid8,
            "phase": str(doc.get("phase") or "?"),
            "beat_ts": beat, "beat_age_s": (round(age, 1) if age is not None else None),
            "seq": int(doc.get("seq") or 0),
            "state": state,
            "have": _have_summary(client, ns, agent, sid8),
        })
    rows.sort(key=lambda r: (r["agent"], -(r["beat_ts"] or 0)))
    return rows


def render_roster(ns: str, *, client=None) -> List[str]:
    """Human render with the W84 contract: what this roster CHECKED, and what it did NOT."""
    rows = roster(ns, client=client)
    out = [f"# seat roster ({ns}) -- {len(rows)} seat(s)"]
    for r in rows:
        age = f"{r['beat_age_s']}s" if r["beat_age_s"] is not None else "?"
        have = ",".join(f"{k}@{str(v)[-9:]}" for k, v in (r.get("have") or {}).items())
        out.append(f"  [{r['state']:5}] {r['seat']:24} phase={r['phase']:10} beat={age:>7} "
                   f"seq={r['seq']:<5} have: {have}")
    if not rows:
        out.append("  (no per-seat worklive keys -- no seat has ever heartbeat in this ns)")
    # W84: the confession line. A roster that cannot name its blind spots is unwedge again.
    out.append(f"  checked:     {ns}:worklive:<agent>#<sid8> keys (TTL {WORKLIVE_TTL_S}s, "
               f"fresh<= {FRESH_S:g}s) + cursor positions (have-summary)")
    out.append("  NOT checked: process liveness (a beating loop can host a wedged model) | "
               "wake watcher armed | runner locks | role-queue claims -- doctor covers those")
    return out
