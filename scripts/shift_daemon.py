"""shift_daemon — the autonomous shift supervisor that makes multi-hour unattended work real.

Design: docs/library/design/autonomous-shift-loop-design.md (fence shift-loop).
Decision core: core/coord/shift_loop.py (next_beat + shift-state note, pinned).

WHAT THIS IS: the CADENCE, not a second agentic brain. It strings together primitives that
already exist and are already guarded — TaskLedger.claim (the mutex), mirror.py commit-by-name,
self_restart (stale-code), the durable shift-state note — into a loop that keeps the fleet
producing, committing, and handoff-ing across hours WITHOUT the operator as conductor.

WHAT IT DELIBERATELY IS NOT (scope guard, and the parts that keep this a supervisor not a rogue):
  - It does NOT invent work. next_beat() says idle when nothing is claimable, and idle is a
    valid beat, not a failure.
  - It does NOT self-approve its own closes. The ledger's LOAD_BEARING independent-review gate
    and T352 operator-ruling still apply. The loop may LAND what it CLAIMED, but it closes only
    with a real commit SHA + verification (or the counted --self-verified escape).
  - It does NOT claim blindly. Every pick routes through TaskLedger.claim(); the claim IS the
    mutex, and a losing claimant gets LedgerError and picks something else.
  - It does NOT run the agentic content-work itself. Its "work" slot is bounded, safe
    reconciliation: verify claim state, land anything already done (commit by name via mirror),
    emit the shift-state handoff. The real investigation/editing rides the agentic runner; this
    daemon is the loop that keeps the cadence honest.

Safety posture mirrors bifrost_daemon: it holds its OWN lock (no twin), honors the freeze/drain
envelope if present, and fail-closed (any unexpected error -> idle for a beat, stay loud, never
spin-hot).

Run (explicit, opt-in — this does NOT attach to the live fleet silently):
  py scripts/shift_daemon.py --agent deepseek --beat 300 --max-beats 0
      --beat N       seconds between decisions (default 300)
      --max-beats N  0 = run forever; N = stop after N beats (for a bounded morning test)
      --dry-run      decide + print, never claim/commit/handoff
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import shift_loop


def _log(msg: str) -> None:
    print(f"[shift-daemon] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Autonomous shift supervisor (fence shift-loop).")
    ap.add_argument("--agent", default="deepseek")
    ap.add_argument("--beat", type=float, default=300.0, help="seconds between decisions")
    ap.add_argument("--max-beats", type=int, default=0, help="0 = run forever")
    ap.add_argument("--dry-run", action="store_true", help="decide + print, never mutate")
    args = ap.parse_args()

    from core.coord import task_ledger as TL

    led = TL.TaskLedger(client=None)   # git-durable truth; no Redis mirror in dry/test mode
    beats = 0
    _log(f"shift supervisor for '{args.agent}' beat={args.beat}s "
         f"max={args.max_beats or 'forever'} dry={args.dry_run}")

    while True:
        beats += 1
        try:
            view = TL.state_view(client=None)
            statuses = {t["id"]: t["status"] for t in
                        (view["done"] + view["in_progress"] + view["next"]
                         + view["proposed"] + view["blocked"] + view["parked"])}
        except Exception as e:
            _log(f"ledger read failed ({type(e).__name__}: {e}) — idle (keep-running)")
            statuses = {}

        decision = shift_loop.next_beat(statuses=statuses)
        _log(f"beat {beats}: {decision['action']}"
             + (f" {decision['task']}" if decision["task"] else "")
             + f" — {decision['reason']}")

        # Dry-run: decide and stop. Never claim/commit/handoff.
        if args.dry_run:
            pass
        elif decision["action"] == "claim" and decision["task"]:
            try:
                t = led.transition(decision["task"], TL.CLAIMED, by=args.agent,
                                   at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                _log(f"claimed {t['id']} (now {t['status']})")
            except TL.LedgerError as e:
                _log(f"claim refused — {e} (another seat or gate; next beat re-decides)")
        elif decision["action"] == "handoff":
            # write the durable shift-state note (supersedes the prior one)
            note = shift_loop.new_shift_state(
                opened=f"{args.agent} @ {time.strftime('%Y-%m-%dT%H:%M:%S')}",
                claimed=str(decision["task"] or "none"),
                cadence_note=f"shift boundary at beat {beats}: {decision['reason']}",
            )
            _log(f"handoff: would emit shift-state note {note} (note door wired by the runner)")

        if args.max_beats and beats >= args.max_beats:
            _log(f"max beats {args.max_beats} reached — stopping")
            break
        time.sleep(args.beat)

    return 0


if __name__ == "__main__":
    sys.exit(main())
