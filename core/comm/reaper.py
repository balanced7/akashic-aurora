"""reaper -- S4: a dead seat's unread directed mail re-homes, loudly. Never stranded.

Design: build-queue S4 (Daniel-gated) + the T108 fence Q3 synthesis (re-homed asks are
CLAIMABLE items carrying their ORIGINAL clocks -- deepseek's no-false-obligation +
kimi's no-reset-clock, both cores) + Discord's bounded-window precedent (netcode doc:
sessions expire server-side; then events re-route -- never infinite retention, never
silent loss).

PRECONDITIONS, all shipped tonight, in order:
    S2 roster    the DEATH SENSOR -- a seat is reapable only when PROVABLY dead:
                 tombstoned (ended by record, T086) OR worklive expired with a seatseen
                 witness (DEAD state). kimi's F3 law holds: a slow-but-alive seat renders
                 LIVE/STALE by its own cadence and is NEVER reaped (S3's resume path is
                 how it comes back).
    S1 role q    the claimable home's semantics (exactly-once, generation-fenced).
    S3           resume-vs-invalid discrimination -- reaping only ends INVALID seats.

MECHANISM (smallest provable cut): for each provably-dead seat, read its seat stream
BEYOND its own consumed cursor (the have-summary's seat_inbox position) and re-SEND each
stranded message to the AGENT ROLE (bare bus.send -- deliverable to any live seat today,
claimable-by-consumption; the XREADGROUP role-queue home upgrades when the runner
call-site migrations land -- a NAMED delta, not a silent one). Provenance meta carries
{rehomed_from, original_ts, original_mid}: the ORIGINAL clock rides along (fence Q3), so
freshness/expectation logic judges by the real age, never a reset one.

LAW C: this module is THE one re-homing writer. Idempotent by NX marker per original
message id -- a reaper racing another reaper re-homes once. LOUD: every re-home emits a
durable event + stderr line; a quiet reaper would be the confident-zero in the organ
built against stranding.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

REHOME_MARK_TTL_S = 7 * 86400


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


def _provably_dead(row: Dict[str, Any]) -> bool:
    """DEAD by the roster's witness, or tombstoned by record. STALE is NOT dead --
    a wedged-but-beating loop resumes (S3); reaping it would rob a live seat (the
    exact failure kimi's slice-1 cut deferred the reaper to avoid)."""
    if row.get("state") == "DEAD":
        return True
    try:
        from core.comm import wake_seat
        return bool(wake_seat.is_tombstoned(str(row.get("sid8") or "")))
    except Exception:
        return False


def reap(ns: str, *, client=None, limit_per_seat: int = 50) -> List[Dict[str, Any]]:
    """Re-home every provably-dead seat's unread directed mail. Returns re-home records.
    Idempotent; loud; never raises. The one re-homing writer (Law C)."""
    client = client or _connect()
    out: List[Dict[str, Any]] = []
    try:
        from core.comm import roster as _roster
        from core.comm.bus import Bus
        rows = _roster.roster(ns, client=client)
    except Exception:
        return out
    for row in rows:
        if not _provably_dead(row):
            continue
        agent, sid8 = str(row.get("agent")), str(row.get("sid8"))
        seat_stream = f"{ns}:inbox:{agent}#{sid8}"
        consumed_to = str((row.get("have") or {}).get("seat_inbox") or "0")
        lo = "(" + consumed_to if consumed_to not in ("0", "0-0") else "-"
        try:
            stranded = client.xrange(seat_stream, min=lo, max="+", count=limit_per_seat) or []
        except Exception:
            continue
        if not stranded:
            continue
        try:
            b = Bus(agent, namespace=(None if ns == "bifrost" else ns))
        except Exception:
            continue
        for mid, fields in stranded:
            mid = str(mid)
            mark = f"{ns}:rehomed:{agent}#{sid8}:{mid}"
            try:
                fresh = client.set(mark, "1", nx=True, ex=REHOME_MARK_TTL_S)
            except Exception:
                fresh = None
            if not fresh:
                continue                        # another reaper pass already re-homed it
            f = dict(fields or {})
            try:
                meta = json.loads(f.get("meta") or "{}")
            except (ValueError, TypeError):
                meta = {}
            meta.pop("to_incarnation", None)     # the dead seat's address dies with it
            meta["rehomed_from"] = f"{agent}#{sid8}"
            meta["original_mid"] = mid
            meta["original_ts"] = f.get("ts", "")  # fence Q3: the ORIGINAL clock rides
            try:
                content = json.loads(f.get("content") or "null")
            except (ValueError, TypeError):
                content = f.get("content")
            new_mid = b.send(agent, str(f.get("kind") or "note"), content, meta=meta)
            rec = {"agent": agent, "seat": f"{agent}#{sid8}", "original_mid": mid,
                   "rehomed_mid": new_mid, "kind": str(f.get("kind") or "note")}
            out.append(rec)
            _loud(f"[reaper] re-homed {rec['kind']} {mid} from dead seat {rec['seat']} -> "
                  f"role '{agent}' as {new_mid} (original clock preserved)")
            try:
                from core.events.event_log import capture_event
                capture_event("seat_rehome", rec)
            except Exception:
                pass
    return out
