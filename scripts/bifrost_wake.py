"""bifrost.wake -- the canonical wake listener for a Bifrost agent (the receive/wake arm of bifrost.api).

Run in the BACKGROUND. It blocks on the agent's inbox + broadcast at ~zero cost and EXITS only when a
real message arrives -- which, in a harness that re-invokes an agent when its background task finishes
(e.g. Claude Code), wakes the otherwise-idle, turn-based agent exactly when there's mail. No polling, no
OS notification, no API key. It keeps waiting through pure trace/noise instead of exiting on it, and
holds a PID seat file while alive so a Stop hook can tell the agent is still wakeable.

THE SEAT IS PER-SESSION (T029 Wave 2, R1/R16): pass --session <id> and the seat file is
bifrost_wake_<agent>_<session>.pid -- concurrent sessions of one agent id each hold their own seat
and never fight over one file (the 2026-07-10 kill loop). Every live session with a seat wakes on
mail (fan-out by design; the ledger + locks absorb twins). Exit codes are operator-facing: ALL
benign endings (wake-worthy mail, quiet deadline, displaced seat, lost seat) exit 0 with a one-line
provenance -- nonzero means a real fault (1 wake error, 2 bus offline). Protocol + fence record:
docs/resilience-wave2-seat-design-2026-07.md.

REUSABLE ONBOARDING: any turn-based agent becomes bus-wakeable by arming its wake listener.

  py scripts/bifrost_wake.py --agent claude --session <session-id>   # per-session seat (preferred)
  py scripts/bifrost_wake.py --agent deepseek                        # legacy per-agent seat
"""
import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bifrost_api import BifrostAPI
from core.comm import wake_seat

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


def _hb_path(agent, session_id=None):
    return wake_seat.seat_path(agent, session_id)


def _hb_holder(path):
    """The pid recorded in the seat file, or None (unreadable/missing = seat lost)."""
    try:
        return int(open(path).read().strip())
    except Exception:
        return None


def watch(agent: str, total_deadline_s: int, inner_block_ms: int, *,
          api: BifrostAPI = None, hb_path: str = None, my_pid: int = None,
          session_id: str = "") -> int:
    api = api if api is not None else BifrostAPI(agent)
    if not api.online_now:
        print("BIFROST_WAKE: bus OFFLINE (Redis unreachable)")
        return 2
    api.online()
    hb = hb_path if hb_path is not None else _hb_path(agent, session_id or None)
    me = my_pid if my_pid is not None else os.getpid()
    lane = f"{agent}/{session_id}" if session_id else agent
    # Seat CREATION belongs to main() (the arm moment); watch() only tracks the seat it was
    # given. Seat-loss is a TRANSITION (held it, lost it) -- an embedder calling watch()
    # without ever seating keeps the old contract and never has files written for it.
    had_seat = _hb_holder(hb) == me
    out, seen = [], []
    steers = 0            # skipped steers are counted so the quiet exit says "check at next boot"
    deadline = time.time() + total_deadline_s
    while time.time() < deadline and not out:
        # Singleton per SEAT (newest-wins): a later same-session watcher overwrites the seat;
        # the older one must stand down instead of double-reading the bus. Detect-only makes a
        # brief overlap harmless, but two watchers on ONE seat = two wakes for one message.
        # Both endings are BENIGN -> exit 0 (a nonzero exit badges a FAILED task into a live
        # session -- the Wave 2 phantom-failure fix); the printed line is the provenance.
        holder = _hb_holder(hb)
        if holder is not None and holder != me:
            print(f"BIFROST_WAKE: standing down for {lane} (seat now owned by pid {holder}) -- benign")
            return 0
        if holder is None and had_seat:
            # Our seat vanished under us (janitor/migration/manual clean). The old code kept
            # watching INVISIBLY here (the seatless fail-open, battery sec. 6 flaw c); the owning
            # session's stop hook sees no seat and re-arms, so we stand down loudly instead.
            print(f"BIFROST_WAKE: standing down for {lane} (seat lost -- heartbeat file gone) -- benign")
            return 0
        if holder == me:
            had_seat = True              # seat observed OURS at least once -> loss is detectable
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


def _migrate_legacy_ghost(agent: str) -> None:
    """K6 one-time self-heal: a pre-Wave-2 name-keyed watcher is invisible to the per-session
    seats (different file) and its code has no seat-lost stand-down -- it would double-wake
    until its deadline. At the first session-scoped arm, retire it: verify identity via one
    process snapshot, kill only a verified watcher, remove the legacy seat, log provenance.
    The single remaining live-process kill in the protocol, bounded to the migration moment."""
    legacy = wake_seat.seat_path(agent, None)
    if not os.path.exists(legacy):
        return
    pid = wake_seat.read_pid(legacy)
    try:
        if pid is not None and pid != os.getpid():
            snap = wake_seat.process_snapshot()
            if snap is None:
                wake_seat.append_provenance(agent, f"K6 migration deferred: snapshot unavailable "
                                                   f"(legacy seat pid {pid} left in place)")
                return                       # K8 direction: cannot verify -> touch nothing
            if pid in snap and wake_seat.is_watcher(pid, snap):
                wake_seat.taskkill(pid)
                wake_seat.append_provenance(agent, f"K6 migration: killed legacy name-keyed ghost "
                                                   f"watcher pid {pid}")
        os.remove(legacy)
        wake_seat.append_provenance(agent, "K6 migration: legacy seat file removed")
    except Exception:
        pass                                 # best-effort; the janitor sweeps stragglers


def main() -> int:
    ap = argparse.ArgumentParser(description="Block until a Bifrost message wakes this agent.")
    ap.add_argument("--agent", default="claude", help="the agent whose inbox to watch")
    ap.add_argument("--session", default="", help="owning session id -> per-session seat (Wave 2)")
    ap.add_argument("--deadline", type=int, default=1800, help="seconds before an idle re-arm (default 30 min)")
    ap.add_argument("--block", type=int, default=120_000, help="ms per inner blocking read")
    a = ap.parse_args()
    if a.session:
        _migrate_legacy_ghost(a.agent)
    hb = _hb_path(a.agent, a.session or None)
    me = os.getpid()
    try:
        with open(hb, "w") as f:
            f.write(str(me))
    except Exception:
        pass
    try:
        return watch(a.agent, a.deadline, a.block, hb_path=hb, my_pid=me, session_id=a.session)
    finally:
        # Remove the seat only if it is still OURS -- a newer watcher may have taken it
        # (newest-wins singleton); deleting its seat would un-arm a live listener.
        try:
            if _hb_holder(hb) == me:
                os.remove(hb)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
