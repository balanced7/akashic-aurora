"""
bifrost_wake -- event-driven wake for a turn-based agent.

Run this in the BACKGROUND. It does a blocking read on the agent's Bifrost inbox + broadcast and
costs ~nothing while waiting; the instant a message arrives it prints it and EXITS. A harness that
re-invokes an agent when its background task finishes (e.g. Claude Code) thus wakes the agent
exactly when there's mail -- no polling, no OS notification, no API key. The agent then reads its
inbox normally and re-arms a fresh watcher.

It DETECTS without consuming (advance=False), so the message is still there for the agent's inbox().

  py scripts/bifrost_wake.py --agent claude                 # block until a message (forever)
  py scripts/bifrost_wake.py --agent claude --timeout 1800000   # 30-min safety re-arm
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus


def main() -> int:
    ap = argparse.ArgumentParser(description="Block until a Bifrost message wakes this agent.")
    ap.add_argument("--agent", default="claude", help="the agent whose inbox to watch")
    ap.add_argument("--timeout", type=int, default=0, help="ms to block; 0 = block forever")
    a = ap.parse_args()

    bus = Bus(a.agent)
    if not bus.online:
        print("BIFROST_WAKE: bus OFFLINE (Redis unreachable)")
        return 2
    bus.register()
    msgs = bus.wait(a.timeout, advance=False)        # detect-only; the agent consumes via inbox()
    if not msgs:
        print(f"BIFROST_WAKE: timed out, no new messages for {a.agent}")
        return 0
    print(f"BIFROST_WAKE: {len(msgs)} new message(s) for {a.agent} -- read your inbox + respond:")
    for m in msgs:
        print(f"  <- {m.frm} [{m.kind}]: {str(m.content)[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
