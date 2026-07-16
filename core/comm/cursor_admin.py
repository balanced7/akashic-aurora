"""cursor_admin -- T076a: SANCTIONED skip-to-now for an agent's consume cursors.

The 2026-07-15 562-echo mountain (and today's deepseek echo-grind) took super-admin hand
surgery on the cursor keys (note cursor-skip-2026-07-15). This is that operation as a
guarded, audited door: advance ALL of an agent's consume cursors (shared legacy hash +
lane hash) to their stream tails, so a resuming consumer starts at NOW and the straggler
peek starts at NOW, with a durable `cursor_skip_to_now` event carrying before/after.

Safety:
  - REASON required (audited admin op; refuse-loud without one).
  - Fleet must be PAUSED (control.is_paused): skipping under a live consumer races its
    drain. Pause-state probe errors REFUSE (fail-closed -- an unsanctioned skip is worse
    than a delayed one; the inverse of the liveness fail-open direction, deliberately).
  - Writes ride the SAME guarded Lua as every cursor advance (advance_to /
    advance_cursor_fields): backwards ids refused at the resource, generations passed
    through unchanged (equal-gen accepted; we never mint -- a skip is not a claim).
  - Never touches fencing generations, seats, or locks.

Cites: T076 task text + research/reviewed/t086-seat-reconciliation-2026-07-16.md
(lease/fencing doctrine); refines T014 (live asks re-send via L4 redrives; echo skips).
"""
from __future__ import annotations

from typing import Any, Dict


def skip_to_now(agent: str, by: str, reason: str) -> Dict[str, Any]:
    """Advance every consume cursor for `agent` to its stream tail. Returns a report dict:
    {"ok": bool, "refused": str, "before": {...}, "after": {...}}. Never raises."""
    out: Dict[str, Any] = {"ok": False, "agent": str(agent), "by": str(by),
                           "reason": str(reason or ""), "before": {}, "after": {},
                           "refused": ""}
    if not str(reason or "").strip():
        out["refused"] = "reason required (this is an audited admin operation)"
        return out
    try:
        from core.comm import control
        if not control.is_paused():
            out["refused"] = ("fleet not paused -- a skip under a live consumer races its "
                              "drain; run bifrost-pause first")
            return out
    except Exception:
        out["refused"] = "pause state unprobeable -- refusing (fail-closed for admin ops)"
        return out
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent))
        if not b.online:
            out["refused"] = "bus offline"
            return out
        c = b._client
        out["before"] = {"shared": b.cursor(), "lane": b.read_lane_cursor()}
        tails = b.tail()                              # legacy inbox/bc concrete tails
        lane_fields: Dict[str, str] = {}
        for lane, (fi, fb) in (("work", ("inbox", "bc")), ("sig", ("sig_inbox", "sig_bc"))):
            keys = b._lane_keys(lane)
            for logical, field in (("inbox", fi), ("bc", fb)):
                try:
                    last = c.xrevrange(keys[logical], count=1)
                    lane_fields[field] = str(last[0][0]) if last else "0"
                except Exception:
                    lane_fields[field] = "0"
        # The legacy SHADOW positions continue the straggler-peek story from NOW.
        lane_fields["shadow_inbox"] = tails.get("inbox", "0")
        lane_fields["shadow_bc"] = tails.get("bc", "0")

        def _gen(key: str) -> int:
            try:
                return int(c.hget(key, "gen") or 0)
            except Exception:
                return 0

        res_shared = b.advance_to(
            inbox=(tails.get("inbox") if tails.get("inbox", "0") != "0" else None),
            bc=(tails.get("bc") if tails.get("bc", "0") != "0" else None),
            generation=_gen(b._cursor_key()))
        fields = {f: v for f, v in lane_fields.items() if v != "0"}
        res_lane = (b.advance_cursor_fields(b.lane_cursor_key(), fields,
                                            generation=_gen(b.lane_cursor_key()))
                    if fields else "OK_NOOP")
        out["after"] = {"shared": b.cursor(), "lane": b.read_lane_cursor(),
                        "advance": {"shared": res_shared, "lane": res_lane}}
        bad = ("STALE_GENERATION", "ERROR", "OFFLINE")
        out["ok"] = res_shared not in bad and res_lane not in bad
        try:   # durable audit -- a skipped backlog must never look like silent loss
            from core.events.event_log import capture_event
            capture_event("cursor_skip_to_now",
                          f"consume cursors for '{agent}' skipped to stream tails by {by}: {reason}",
                          agent_id=str(agent),
                          detail={"by": str(by), "reason": str(reason),
                                  "before": out["before"], "after": out["after"]})
        except Exception:
            pass
        return out
    except Exception as e:
        out["refused"] = f"error ({type(e).__name__})"
        return out
