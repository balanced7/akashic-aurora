"""remote_bridge_relay — drain parked peer mail onto the LOCAL bus, safely, forever.

    py scripts/remote_bridge_relay.py --once          # drain what is parked, then stop
    py scripts/remote_bridge_relay.py --loop          # stand up as a service

This is the last mile of bifrost-to-bifrost. accept() admits a remote message and PARKS it;
remote_bridge_watch.py notices it; this puts it where your seats actually look. Run on both
sides, two fleets share a conversation instead of two mailboxes.

READ THIS BEFORE RUNNING IT — IT CHANGES YOUR THREAT MODEL ON PURPOSE.

accept() parks rather than busses because "a remote sentence must never be a thing that
HAPPENED TO an agent." That property is the main defence, and this relay spends it: it puts
another fleet's words on your live bus, where your seats read them. That is the whole point
and it is also a prompt-injection surface into a fleet holding a shell, a repo and an API
budget. It is therefore OPT-IN, never a default, and never something a peer can switch on.

WHAT MAKES IT SURVIVABLE is not trust — it is that the relayed message carries no power. The
posture is copied verbatim from the Discord guest tier (R2/R3), which solved this exact
problem for human visitors:

  - ATTRIBUTED IN THE BODY. Every line arrives as "[remote <route>] ..." so no reader can
    mistake a peer's sentence for a colleague's.
  - authority: none IN THE META. The house's own rule, applied to a fleet instead of a guest.
  - PROVENANCE FROM THE ROUTE. `frm` is the verified route; the peer's claim rides as
    `claimed_frm` and decides nothing. A signature authenticates the channel, never the claim.
  - NO CONTROL KINDS, EVER. accept() already refuses them at the gate; this refuses them
    again here, because a relay that trusts its upstream is one upstream bug from being a
    remote control. Two locks on one door is the correct number when the door opens inward.
  - IDEMPOTENT. Each message carries `bridge:<id>`; a redelivery re-posts nothing.

WHAT IT WILL NOT DO: it will not consume, delete or modify the parked record (that stays the
audit trail), will not relay anything accept() did not already admit, and will not act on a
single word it carries. It moves mail. It never obeys it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.comm import remote_relay as RR  # noqa: E402

#: Kinds this relay will put on a live bus. NARROWER than BRIDGE_KINDS on purpose: the gate
#: decides what may CROSS a fleet boundary, this decides what may be SPOKEN to your seats,
#: and those are different questions -- the same lesson FORWARD_KINDS taught the bridge.
RELAY_KINDS = frozenset({"chat", "question", "reply", "note", "completion", "blocker"})

#: Which parked ids have been relayed. Durable, because a restart that re-relays the backlog
#: would spam every seat with yesterday's conversation.
CURSOR = ROOT / "state" / "coord" / "remote_bridge_relayed.json"


def relayed_ids() -> set:
    try:
        return set(json.loads(CURSOR.read_text(encoding="utf-8")).get("ids") or [])
    except (OSError, ValueError):
        return set()


def remember(ids: set) -> None:
    try:
        CURSOR.parent.mkdir(parents=True, exist_ok=True)
        CURSOR.write_text(json.dumps({"ids": sorted(ids)}, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"  WARNING: cursor not persisted ({e}) — a restart may re-relay", flush=True)


def drain_once(bus_agent: str = "bridge-relay", dry: bool = False) -> int:
    RR._reset_cache()
    done = relayed_ids()
    rows = [r for r in RR._read_jsonl(RR.inbox_path())
            if str(r.get("frm", "")).startswith("remote:")]
    fresh = [r for r in rows if str(r.get("id")) not in done]
    if not fresh:
        return 0

    try:
        from core.comm.bus import Bus
        bus = Bus(bus_agent)
    except Exception as e:                                        # noqa: BLE001
        print(f"  bus unavailable ({type(e).__name__}: {e}) — nothing relayed, nothing lost",
              flush=True)
        return 0

    sent = 0
    for r in fresh:
        kind = str(r.get("kind") or "")
        mid = str(r.get("id"))
        if kind not in RELAY_KINDS:
            print(f"  REFUSED {mid}: kind {kind!r} may cross the bridge but may not be "
                  f"spoken to a seat", flush=True)
            done.add(mid)                     # refused is decided, not pending
            continue
        body = f"[remote {r.get('frm')}] {r.get('content')}"
        meta = {"source": "remote-bridge", "remote": True, "authority": "none",
                "route": r.get("frm"), "claimed_frm": r.get("claimed_frm"),
                "bridge_id": mid, "idempotency_key": f"bridge:{mid}"}
        if dry:
            print(f"  WOULD relay {mid} ({kind}): {body[:70]}", flush=True)
        else:
            bid = bus.broadcast("chat", body, meta=meta)
            print(f"  relayed {mid} ({kind}) -> bus {bid}", flush=True)
        done.add(mid)
        sent += 1
    if not dry:
        remember(done)
    return sent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Relay parked peer mail onto the local bus")
    ap.add_argument("--loop", action="store_true", help="stay up as a service")
    ap.add_argument("--once", action="store_true", help="drain what is parked, then stop")
    ap.add_argument("--dry-run", action="store_true", help="show what would be relayed")
    ap.add_argument("--poll-sec", type=float, default=4.0)
    ap.add_argument("--agent", default="bridge-relay", help="bus identity to post under")
    a = ap.parse_args(argv)

    if not (a.loop or a.once or a.dry_run):
        ap.error("say --once, --loop or --dry-run out loud. This relay puts another fleet's "
                 "words on your live bus; it does not start by accident.")

    print(f"bridge relay — inbox {RR.inbox_path()}", flush=True)
    print(f"  relay kinds: {sorted(RELAY_KINDS)}   posture: authority=none, no levers",
          flush=True)
    n = drain_once(a.agent, dry=a.dry_run)
    print(f"  {n} relayed", flush=True)
    if not a.loop:
        return 0
    while True:
        time.sleep(a.poll_sec)
        try:
            drain_once(a.agent)
        except Exception as e:                                    # noqa: BLE001
            print(f"  tick error ({type(e).__name__}: {e}) — relay continues", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
