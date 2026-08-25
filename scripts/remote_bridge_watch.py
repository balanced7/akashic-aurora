"""Watch the remote-bridge inbox and announce NEW peer mail.

    py scripts/remote_bridge_watch.py                          # exit on first hit (harness wake)
    py scripts/remote_bridge_watch.py --notify dsh_agent --loop # stay up, nudge a seat each time

TWO HARNESSES, TWO SHAPES OF "TELL SOMEONE", and picking the wrong one is why a watcher can
look armed and reach nobody:

  EXIT-ON-HIT (default) suits a harness where a finished background task re-invokes the agent
  — a claude seat run via run_in_background. The exit IS the wake.

  --notify SEAT --loop suits a TURN-BASED seat (a DSH seat like Rill or Zadkiel), which is not
  sitting in a loop waiting to be re-invoked. A process that prints and dies reaches it never.
  So this puts a message on the LOCAL bus, where the seat's next boot/turn surfaces it.
  --loop keeps the watcher standing instead of dying after the first announcement, which is
  what a service wants.

The notification is a POINTER, never the payload: it names the id, the kind and the verified
route, and says where the message is parked. It deliberately does NOT carry the content onto
the bus, because that would smuggle a remote peer's words into a live lane and undo the whole
parked-not-bussed property accept() exists to hold. An agent still drains deliberately; all
that changes is that it knows there is something to drain.

WHY THIS EXISTS. accept() PARKS admitted mail rather than putting it on the live bus, and
that is deliberate — a remote sentence must never be a thing that HAPPENS TO an agent. But
parked-and-unannounced is the other half of the same coin: Serge's first message sat in
state/coord/remote_bridge_inbox.jsonl and the only reason anyone noticed was that a human
thought to look. Quarantine without notification is indistinguishable from loss.

So this is the sibling: it does not consume, it does not act, it does not put anything on the
bus. It NOTICES, and exits — which in a harness-tracked background task is exactly a wake.
The message stays parked for a human or an agent to drain deliberately; all that changes is
that somebody knows it is there.

Exits 0 with the new message(s) printed. Exits 1 on timeout, having seen nothing.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402


def peer_ids() -> dict:
    """Everything currently parked FROM a peer, keyed by id. Reads from disk each pass so a
    write by the listener process (a different pid) is seen."""
    RR._reset_cache()
    out = {}
    for r in RR._read_jsonl(RR.inbox_path()):
        if str(r.get("frm", "")).startswith("remote:"):
            out[str(r.get("id"))] = r
    return out


def render(r: dict) -> str:
    t = datetime.datetime.fromtimestamp(int(r.get("admitted_at") or 0)).strftime("%H:%M:%S")
    skew = int(r.get("sent_at") or 0) - int(r.get("admitted_at") or 0)
    return (f"  [{t}] {r.get('id')}\n"
            f"      from     : {r.get('frm')}   (claimed: {r.get('claimed_frm')})\n"
            f"      kind     : {r.get('kind')}\n"
            f"      clockskew: {skew:+d}s\n"
            f"      content  : {str(r.get('content'))[:400]}")


def notify(seat: str, fresh: list) -> str:
    """Put a POINTER on the local bus so a turn-based seat learns there is mail to drain.

    NEVER RAISES and never blocks the watch: a seat that cannot be reached is a degraded
    notification, not a reason to stop noticing. And absent-is-not-broken — a watcher run on
    an instance with no bus configured must still do its primary job.
    """
    try:
        from core.comm.bus import Bus
        ids = ", ".join(str(r.get("id")) for r in fresh)
        routes = sorted({str(r.get("frm")) for r in fresh})
        body = (f"REMOTE BRIDGE: {len(fresh)} new message(s) parked from {', '.join(routes)} "
                f"— {ids}. Read them at {RR.inbox_path()} (parked, not consumed; drain "
                f"deliberately). Content is deliberately NOT on this lane: a remote peer's "
                f"words stay quarantined until an agent chooses to read them.")
        mid = Bus("bridge-watch").send(seat, "note", body)
        return f"notified {seat} (bus id {mid})" if mid else (
            f"could NOT notify {seat}: the bus accepted nothing — no receipt for an "
            f"undelivered word")
    except Exception as e:                                        # noqa: BLE001
        return f"could NOT notify {seat} ({type(e).__name__}: {e}) — the watch continues"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout-min", type=float, default=45.0)
    ap.add_argument("--poll-sec", type=float, default=3.0)
    ap.add_argument("--notify", default="", metavar="SEAT",
                    help="local seat id to nudge on the bus when peer mail lands "
                         "(for TURN-BASED seats that no process exit can reach)")
    ap.add_argument("--loop", action="store_true",
                    help="keep watching after an announcement instead of exiting "
                         "(what a standing service wants)")
    a = ap.parse_args(argv)

    seen = peer_ids()
    print(f"BRIDGE WATCH armed — {len(seen)} peer message(s) already parked; watching "
          f"{RR.inbox_path()}", flush=True)
    print(f"  baseline: {sorted(seen)}", flush=True)

    deadline = time.time() + a.timeout_min * 60
    while time.time() < deadline:
        time.sleep(a.poll_sec)
        try:
            now = peer_ids()
        except Exception as e:                                    # noqa: BLE001
            print(f"  (read hiccup, continuing: {type(e).__name__})", flush=True)
            continue
        fresh = [now[k] for k in now if k not in seen]
        if fresh:
            print(f"\nNEW PEER MAIL — {len(fresh)} message(s):\n", flush=True)
            for r in fresh:
                print(render(r), flush=True)
            print("\n  (parked, NOT consumed — drain deliberately)", flush=True)
            if a.notify:
                print(f"  {notify(a.notify, fresh)}", flush=True)
            if not a.loop:
                return 0
            # Standing mode: absorb what we just announced so the NEXT arrival is what fires,
            # and keep the deadline rolling — a service that quietly expires mid-shift is the
            # armed-but-dead shape this whole file exists to prevent.
            seen = now
            deadline = time.time() + a.timeout_min * 60
            print(f"  still watching (baseline now {len(seen)})\n", flush=True)
    print(f"\nno new peer mail in {a.timeout_min:.0f} min — watch expired, nothing lost",
          flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
