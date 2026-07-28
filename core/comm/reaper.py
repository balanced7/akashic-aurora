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

LAW C: this module is THE one re-homing writer. A short NX claim serializes live reapers;
the durable done marker is written only AFTER a successful send. Delivery is deliberately
at-least-once: a crash after send but before the marker may replay, while a failed send can
never poison the message into a permanent strand. ``original_mid`` makes such a replay
recognizable. LOUD: every re-home emits a durable event + stderr line; a quiet reaper would
be the confident-zero in the organ built against stranding.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

REHOME_MARK_TTL_S = 7 * 86400
REHOME_CLAIM_TTL_S = 30


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


def _release_claim(client, key: str, token: str) -> None:
    """Release only this reaper's transient claim; never delete a successor's claim."""
    try:
        client.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1, key, token)
    except Exception:
        try:
            if str(client.get(key) or "") == token:
                client.delete(key)
        except Exception:
            pass


def _stream_id_tuple(value: Any) -> tuple:
    try:
        ms, seq = str(value).split("-", 1)
        return int(ms), int(seq)
    except (ValueError, TypeError):
        return 0, 0


def _later_stream_id(left: Any, right: Any) -> str:
    """The later of two Redis stream ids, tolerating the legacy ``0`` sentinel."""
    return str(left if _stream_id_tuple(left) >= _stream_id_tuple(right) else right)


def _provably_dead(row: Dict[str, Any], *, client=None, ns: Optional[str] = None) -> bool:
    """DEAD by the roster's witness, or tombstoned by record. STALE is NOT dead --
    a wedged-but-beating loop resumes (S3); reaping it would rob a live seat (the
    exact failure kimi's slice-1 cut deferred the reaper to avoid)."""
    if row.get("state") == "DEAD":
        return True
    try:
        from core.comm import wake_seat
        full_sid = str(row.get("full_sid") or "")
        return bool(full_sid and wake_seat.is_tombstoned(
            full_sid, c=client, namespace=ns))
    except Exception:
        return False


ORPHAN_MIN_AGE_S = 240.0     # worklive TTL (180) + grace: a stream this old with NO witness
                             # was never a live seat's -- crash-at-birth (kimi's seam,
                             # narrowed). A younger orphan is a JUST-BORN seat whose mail
                             # arrived before its first boot-beat: NEVER robbed.


def _orphan_rows(client, ns: str, known: set, min_age_s: float) -> List[Dict[str, Any]]:
    """kimi's S4 seam: seats that died BEFORE their first-ever heartbeat leave no worklive,
    no seatseen witness, no roster row -- invisible to a roster-only reaper, and they are
    exactly the seats most likely to strand. Detect them by their SEAT STREAMS: a stream
    whose newest entry is older than the age floor, with no witness of life, is an orphan."""
    rows: List[Dict[str, Any]] = []
    try:
        streams = [str(k) for k in client.keys(f"{ns}:inbox:*")]
    except Exception:
        return rows
    now = time.time()
    for skey in streams:
        tail = skey.rsplit(":inbox:", 1)[-1]
        if "#" not in tail or tail in known:
            continue
        agent, _, sid8 = tail.partition("#")
        try:
            newest = client.xrevrange(skey, count=1) or []
        except Exception:
            continue
        if not newest:
            continue
        ms = str(newest[0][0]).partition("-")[0]
        try:
            age = now - (int(ms) / 1000.0)
        except ValueError:
            continue
        if age < min_age_s:
            continue                       # just-born protection: never rob a fresh seat
        rows.append({"agent": agent, "sid8": sid8, "full_sid": "",
                     "seat": tail, "state": "DEAD",
                     "have": {"seat_inbox": "0"}, "_orphan": True})
    return rows


def reap(ns: str, *, client=None, limit_per_seat: int = 50,
         _orphan_min_age_s: Optional[float] = None) -> List[Dict[str, Any]]:
    """Re-home every provably-dead seat's unread directed mail. Returns re-home records.
    Idempotent; loud; never raises. The one re-homing writer (Law C).
    Covers BOTH death shapes: witnessed deaths (roster DEAD / tombstone) AND never-beaten
    orphan streams (kimi's seam -- crash-before-first-beat), age-discriminated so a
    just-born seat is never robbed."""
    client = client or _connect()
    out: List[Dict[str, Any]] = []
    try:
        from core.comm import roster as _roster
        from core.comm.bus import Bus
        rows = _roster.roster(ns, client=client)
    except Exception:
        return out
    known = {str(r.get("seat")) for r in rows}
    rows = rows + _orphan_rows(client, ns, known,
                               ORPHAN_MIN_AGE_S if _orphan_min_age_s is None else _orphan_min_age_s)
    per_seat_limit = max(0, int(limit_per_seat))
    if per_seat_limit == 0:
        return out
    for row in rows:
        if not (row.get("_orphan") or _provably_dead(row, client=client, ns=ns)):
            continue
        agent, sid8 = str(row.get("agent")), str(row.get("sid8"))
        seat_stream = f"{ns}:inbox:{agent}#{sid8}"
        try:
            seat_bus = Bus(agent, namespace=(None if ns == "bifrost" else ns))
            seat_cursor_key = seat_bus._seat_cursor_key(sid8)
        except Exception:
            continue
        have = row.get("have") or {}
        consumed_to = str(have.get("seat_inbox") or "0")
        try:
            reaped_to = str(client.hget(seat_cursor_key, "reaper") or "0")
        except Exception:
            reaped_to = str(have.get("reaper") or "0")
        safe_cursor = _later_stream_id(consumed_to, reaped_to)
        scan_from = "(" + safe_cursor if safe_cursor not in ("0", "0-0") else "-"
        delivered = 0
        cursor_blocked = False
        page_size = max(1, min(per_seat_limit, 100))
        while delivered < per_seat_limit:
            try:
                stranded = client.xrange(
                    seat_stream, min=scan_from, max="+", count=page_size) or []
            except Exception:
                break
            if not stranded:
                break
            scan_from = "(" + str(stranded[-1][0])
            for mid, fields in stranded:
                if delivered >= per_seat_limit:
                    break
                mid = str(mid)
                mark = f"{ns}:rehomed:{agent}#{sid8}:{mid}"
                claim = mark + ":claim"
                token = uuid.uuid4().hex
                try:
                    if client.exists(mark):
                        if not cursor_blocked:
                            safe_cursor = mid
                        continue
                    held = client.set(
                        claim, token, nx=True, ex=REHOME_CLAIM_TTL_S)
                except Exception:
                    held = None
                if not held:
                    cursor_blocked = True
                    continue
                try:
                    if client.exists(mark):
                        _release_claim(client, claim, token)
                        if not cursor_blocked:
                            safe_cursor = mid
                        continue
                except Exception:
                    _release_claim(client, claim, token)
                    cursor_blocked = True
                    continue

                f = dict(fields or {})
                try:
                    meta = json.loads(f.get("meta") or "{}")
                except (ValueError, TypeError):
                    meta = {}
                meta.pop("to_incarnation", None)   # the dead seat's address dies with it
                meta["rehomed_from"] = f"{agent}#{sid8}"
                meta["original_mid"] = mid
                meta["original_ts"] = f.get("ts", "")
                try:
                    content = json.loads(f.get("content") or "null")
                except (ValueError, TypeError):
                    content = f.get("content")
                sender = str(f.get("frm") or "unknown")
                try:
                    b = Bus(sender, namespace=(None if ns == "bifrost" else ns))
                    new_mid = b.send(
                        agent, str(f.get("kind") or "note"), content, meta=meta)
                except Exception:
                    new_mid = None
                if not new_mid:
                    _release_claim(client, claim, token)
                    cursor_blocked = True
                    _loud(f"[reaper] FAILED to re-home {str(f.get('kind') or 'note')} "
                          f"{mid} from dead seat {agent}#{sid8}; retry remains eligible")
                    continue

                marked = False
                try:
                    marked = bool(client.set(
                        mark, str(new_mid), ex=REHOME_MARK_TTL_S))
                except Exception:
                    pass
                _release_claim(client, claim, token)
                rec = {"agent": agent, "seat": f"{agent}#{sid8}",
                       "original_mid": mid, "rehomed_mid": new_mid,
                       "kind": str(f.get("kind") or "note")}
                out.append(rec)
                delivered += 1
                if marked and not cursor_blocked:
                    safe_cursor = mid
                elif not marked:
                    cursor_blocked = True
                suffix = "" if marked else " (DONE MARK FAILED; at-least-once replay possible)"
                _loud(f"[reaper] re-homed {rec['kind']} {mid} from dead seat "
                      f"{rec['seat']} -> role '{agent}' as {new_mid} "
                      f"(original clock preserved){suffix}")
                try:
                    from core.events.event_log import capture_event
                    capture_event("seat_rehome", rec)
                except Exception:
                    pass
        if safe_cursor != reaped_to:
            try:
                client.hset(seat_cursor_key, "reaper", safe_cursor)
            except Exception:
                pass
    return out
