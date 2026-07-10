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

# Kinds that keep the watcher waiting: display-only firehose (trace), fold-into-current-task
# facts (steer -- when idle there is no current task; it surfaces at the next natural turn),
# and ledger control-plane markers (resolved / ledger_update, P3/T023: the wake report prints
# the full read-state-first ledger anyway, so a transition marker adds NOTHING wake-worthy --
# it insta-woke armed watchers three times on 2026-07-09 before this line existed; runners
# fold these hint-style instead).
# P0 (T017): 'reply' is deliberately WAKE-WORTHY -- a directed reply arriving while the agent
# idles is usually the answer to something it asked (T016: the eaten reply was a requested
# fenced report). The watcher only DETECTS; nothing here is consumed (see wake_block).
SKIP_KINDS = {"trace", "steer", "resolved", "ledger_update"}

STAND_DOWN_RC = 4   # a newer watcher owns the heartbeat -> this one exits without reporting


def _hb_path(agent):
    return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{agent}.pid")


def _hb_holder(path):
    """The pid recorded in the heartbeat file, or None (unreadable/missing = fail-open)."""
    try:
        return int(open(path).read().strip())
    except Exception:
        return None


def watch(agent: str, total_deadline_s: int, inner_block_ms: int, *,
          api: BifrostAPI = None, hb_path: str = None, my_pid: int = None) -> int:
    api = api if api is not None else BifrostAPI(agent)
    if not api.online_now:
        print("BIFROST_WAKE: bus OFFLINE (Redis unreachable)")
        return 2
    api.online()
    hb = hb_path if hb_path is not None else _hb_path(agent)
    me = my_pid if my_pid is not None else os.getpid()
    out, seen = [], []
    steers = 0            # skipped steers are counted so the quiet exit says "check at next boot"
    deadline = time.time() + total_deadline_s
    while time.time() < deadline and not out:
        # Singleton (newest-wins): a later watcher overwrites the heartbeat; the older one must
        # stand down instead of double-reading the bus. Detect-only makes a brief overlap
        # harmless, but two live watchers = two wakes for one message = confusing re-invokes.
        holder = _hb_holder(hb)
        if holder is not None and holder != me:
            print(f"BIFROST_WAKE: standing down for {agent} (heartbeat now owned by pid {holder})")
            return STAND_DOWN_RC
        try:
            msgs = api.wake_block(timeout_ms=inner_block_ms)
        except Exception as e:
            print("WAKE_ERROR: " + str(e)); return 1
        for m in msgs:
            frm = str(getattr(m, "frm", "?"))
            kind = str(getattr(m, "kind", "?"))
            to = str(getattr(m, "to", "?"))
            seen.append(f"{frm}:{kind}")
            if kind == "steer":
                steers += 1
            if frm == agent or kind in SKIP_KINDS:
                continue
            if kind == "reply" and to == "*":
                continue   # a BROADCAST reply is room chatter, not "someone answered you"
                           # (deepseek red-team F5: only DIRECTED replies wake an idle agent)
            out.append({"frm": frm, "kind": kind, "text": str(getattr(m, "content", "") or "")[:2000]})
    # Read-state-first (Slice C): the governed task ledger prints BEFORE the messages, so a waking
    # agent obeys DONE/NEXT and never acts on a stale backlog message. Fail-open.
    try:
        from core.coord.task_ledger import format_state
        print(format_state(agent=agent, now=time.time()))   # P5: stale proposals labeled at wake
    except Exception:
        pass
    if out:
        print(f"BIFROST WAKE -- messages for {agent} (DETECTED, not consumed -- read them via "
              f"bifrost-sync/inbox):")
        print(json.dumps(out, indent=1))          # ensure_ascii=True -> cp1252-safe stdout on Windows
    else:
        queued = f"; {steers} steer(s) queued for next boot" if steers else ""
        print(f"BIFROST_WAKE: quiet for {agent} (saw: " + ", ".join(seen[-12:]) + queued + ")")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Block until a Bifrost message wakes this agent.")
    ap.add_argument("--agent", default="claude", help="the agent whose inbox to watch")
    ap.add_argument("--deadline", type=int, default=1800, help="seconds before an idle re-arm (default 30 min)")
    ap.add_argument("--block", type=int, default=120_000, help="ms per inner blocking read")
    a = ap.parse_args()
    hb = _hb_path(a.agent)
    me = os.getpid()
    try:
        with open(hb, "w") as f:
            f.write(str(me))
    except Exception:
        pass
    try:
        return watch(a.agent, a.deadline, a.block, hb_path=hb, my_pid=me)
    finally:
        # Remove the heartbeat only if it is still OURS -- a newer watcher may have taken the
        # seat (newest-wins singleton); deleting its heartbeat would un-arm a live listener.
        try:
            if _hb_holder(hb) == me:
                os.remove(hb)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
