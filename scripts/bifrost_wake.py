"""bifrost.wake -- the canonical wake listener for a Bifrost agent (the receive/wake arm of bifrost.api).

Run in the BACKGROUND. It blocks on the agent's inbox + broadcast at ~zero cost and EXITS only when a
real message arrives -- which, in a harness that re-invokes an agent when its background task finishes
(e.g. Claude Code), wakes the otherwise-idle, turn-based agent exactly when there's mail. No polling, no
OS notification, no API key. It keeps waiting through pure trace/noise instead of exiting on it, and
writes a PID heartbeat while alive so a Stop hook can tell the agent is still wakeable.

REUSABLE ONBOARDING: any turn-based agent becomes bus-wakeable by arming its wake listener.

  py scripts/bifrost_wake.py --agent claude        # watch for claude
  py scripts/bifrost_wake.py --agent deepseek      # the template for any agent
"""
import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bifrost_api import BifrostAPI

SKIP_KINDS = {"trace", "reply", "steer"}   # noise / non-reply kinds -> keep waiting


def _hb_path(agent):
    return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{agent}.pid")


def watch(agent: str, total_deadline_s: int, inner_block_ms: int) -> int:
    api = BifrostAPI(agent)
    if not api.online_now:
        print("BIFROST_WAKE: bus OFFLINE (Redis unreachable)")
        return 2
    api.online()
    out, seen = [], []
    deadline = time.time() + total_deadline_s
    while time.time() < deadline and not out:
        try:
            msgs = api.wake_block(timeout_ms=inner_block_ms)
        except Exception as e:
            print("WAKE_ERROR: " + str(e)); return 1
        for m in msgs:
            frm = str(getattr(m, "frm", "?"))
            kind = str(getattr(m, "kind", "?"))
            seen.append(f"{frm}:{kind}")
            if frm == agent or kind in SKIP_KINDS:
                continue
            out.append({"frm": frm, "kind": kind, "text": str(getattr(m, "content", "") or "")[:2000]})
    if out:
        print(f"BIFROST WAKE -- messages for {agent}:")
        print(json.dumps(out, indent=1))          # ensure_ascii=True -> cp1252-safe stdout on Windows
    else:
        print(f"BIFROST_WAKE: quiet for {agent} (saw: " + ", ".join(seen[-12:]) + ")")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Block until a Bifrost message wakes this agent.")
    ap.add_argument("--agent", default="claude", help="the agent whose inbox to watch")
    ap.add_argument("--deadline", type=int, default=1800, help="seconds before an idle re-arm (default 30 min)")
    ap.add_argument("--block", type=int, default=120_000, help="ms per inner blocking read")
    a = ap.parse_args()
    hb = _hb_path(a.agent)
    try:
        with open(hb, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    try:
        return watch(a.agent, a.deadline, a.block)
    finally:
        try:
            os.remove(hb)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
