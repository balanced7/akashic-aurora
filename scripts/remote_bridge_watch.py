"""Watch the remote-bridge inbox and exit the moment a NEW peer message parks.

    py scripts/remote_bridge_watch.py [--timeout-min 45] [--agent claude]

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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout-min", type=float, default=45.0)
    ap.add_argument("--poll-sec", type=float, default=3.0)
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
            return 0
    print(f"\nno new peer mail in {a.timeout_min:.0f} min — watch expired, nothing lost",
          flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
