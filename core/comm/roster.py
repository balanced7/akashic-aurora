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

STATE LADDER (kimi P1 + fence findings F1/F3 -- key-exists is NOT alive, and absence is
not silence):
    LIVE   beat within the seat's OWN cadence window (2x EMA of inter-beat intervals,
           floor 10s; FRESH_S=45s only for seats with no rhythm yet) -- F3: the false-LIVE
           window is bounded by the seat's real recovery time, never a fleet-wide dial.
    STALE  worklive key exists, beat outside the window.
    DEAD   worklive TTL'd away but the seatseen witness (24h) remembers -- F1: a seat that
           EVER beat renders DEAD with its last beat age; silent absence is reserved for
           seats that never existed. The reaper keys on worklive absence; the RENDER
           confesses the death.
Monotonic beats: heartbeat() refuses to write a beat_ts older than the stored one, so a
replayed/duplicated beat can never resurrect a stale seat or mask a death. Have-summaries
derive their keys through the Bus door (F2) with shared cursors LABELED as shared.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

WORKLIVE_TTL_S = int(os.environ.get("AKASHIC_WORKLIVE_TTL_S", "180") or 180)
RESUME_GAP_S = float(os.environ.get("AKASHIC_RESUME_GAP_S", "600") or 600)   # S3: away-time that counts as a RESUME
FRESH_S = float(os.environ.get("AKASHIC_WORKLIVE_FRESH_S", "45") or 45)


def _connect():
    from core.comm.bus import _connect as bus_connect
    return bus_connect()


def _key(ns: str, agent: str, sid8: str) -> str:
    return f"{ns}:worklive:{agent}#{sid8}"


SEATSEEN_TTL_S = 86400          # kimi F1: death must outlive the worklive TTL to be RENDERABLE


def _seen_key(ns: str, agent: str, sid8: str) -> str:
    return f"{ns}:seatseen:{agent}#{sid8}"


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
        # S3 (Discord's Resumed marker): a beat after a long absence IS a resume -- report
        # it so the sync render can separate replayed backlog from live mail.
        resumed_after = (now - prev_beat) if (prev_beat > 0 and now - prev_beat > RESUME_GAP_S) else None
        if now < prev_beat:
            # P5: replay refused -- refresh the TTL (the seat IS being touched) but keep
            # the fresher stored beat; a replayed heartbeat cannot rewind liveness.
            client.expire(k, WORKLIVE_TTL_S)
            return {"ok": False, "resumed_after_s": None}
        # kimi F3: learn the seat's OWN cadence so LIVE's window derives from rhythm,
        # not an unjustified fleet-wide dial. EMA of inter-beat intervals.
        ema = float(prev.get("ema_interval") or 0)
        if prev_beat > 0:
            interval = max(0.0, now - prev_beat)
            ema = (0.3 * interval + 0.7 * ema) if ema > 0 else interval
        doc = {"phase": str(phase), "beat_ts": now,
               "since_ts": float(prev.get("since_ts") or now),
               "seq": int(prev.get("seq") or 0) + 1,
               "ema_interval": round(ema, 3)}
        client.set(k, json.dumps(doc), ex=WORKLIVE_TTL_S)
        # kimi F1: the long-lived death witness -- when worklive TTLs away, this record
        # lets the roster render DEAD-with-last-beat instead of silent absence.
        try:
            client.set(_seen_key(ns, agent, str(sid8)[:8]),
                       json.dumps({"beat_ts": now, "phase": str(phase)}), ex=SEATSEEN_TTL_S)
        except Exception:
            pass
        return {"ok": True,
                "resumed_after_s": (round(resumed_after, 1) if resumed_after else None)}
    except Exception:
        return {"ok": False, "resumed_after_s": None}


def _have_summary(client, ns: str, agent: str, sid8: str) -> Dict[str, Any]:
    """T3 (torrent bitfield): the seat's consumed-through positions -- inventory POINTERS,
    never payload (T5). kimi F2: keys are DERIVED THROUGH THE BUS DOOR (the organ that owns
    the formats), never a parallel hardcoded f-string; the shared legacy cursor is labeled
    so a successor knows which pointer a twin could have advanced (advisory, not proof)."""
    have: Dict[str, Any] = {}
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent), namespace=(None if ns == "bifrost" else ns))
        try:
            have["legacy_inbox_shared"] = str(b._read_cursor().get("inbox", "0"))
        except Exception:
            pass
        try:
            have["seat_inbox"] = str(client.hget(b._seat_cursor_key(str(sid8)[:8]), "seat") or "0")
        except Exception:
            pass
        try:
            have["lane_inbox_shared"] = str((client.hgetall(b.lane_cursor_key(str(agent))) or {}).get("inbox", "0"))
        except Exception:
            pass
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
        live_keys = {str(k) for k in client.keys(f"{ns}:worklive:*")}
        seen_keys = {str(k) for k in client.keys(f"{ns}:seatseen:*")}
    except Exception:
        return rows
    live_tails = {k.rsplit(":worklive:", 1)[-1] for k in live_keys if "#" in k.rsplit(":worklive:", 1)[-1]}
    seen_tails = {k.rsplit(":seatseen:", 1)[-1] for k in seen_keys if "#" in k.rsplit(":seatseen:", 1)[-1]}
    for tail in sorted(live_tails | seen_tails):
        agent, _, sid8 = tail.partition("#")
        doc: Dict[str, Any] = {}
        dead = tail not in live_tails
        try:
            raw = client.get(_seen_key(ns, agent, sid8) if dead else _key(ns, agent, sid8))
            doc = json.loads(raw or "{}")
        except (ValueError, TypeError):
            doc = {}
        beat = float(doc.get("beat_ts") or 0)
        age = now - beat if beat else None
        if dead:
            # kimi F1: a seat that EVER beat renders DEAD with its last beat age -- never
            # silent absence; the reaper keys on absence, the RENDER confesses the death.
            state = "DEAD"
        else:
            # kimi F3: LIVE's window derives from the seat's OWN cadence (2x EMA, floored),
            # falling back to FRESH_S only for seats with no rhythm yet. A wedged loop's
            # false-LIVE window is bounded by the seat's real recovery time, not a dial.
            ema = float(doc.get("ema_interval") or 0)
            window = max(2.0 * ema, 10.0) if ema > 0 else FRESH_S
            state = "LIVE" if (age is not None and age <= window) else "STALE"
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
