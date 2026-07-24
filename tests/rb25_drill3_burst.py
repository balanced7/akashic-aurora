"""
RB-25 Drill 3 -- CONCURRENCY STORM: burst script (authored by deepseek, executed by claude).

Per the runbook execution split (docs/library/design/20260711_rb-25-engine-exam-runbook-pre-registered_9356ea.md drill 2 section):
deepseek AUTHORS the burst script, claude EXECUTES it against the live fleet.

FROZEN BARS (pass/fail each, verifiable from the ledger + transcripts):
  S1 NO UNACKED LOSS: every directed request in the burst is accounted for -- answered
     by a live runner, redelivered to the successor, or visible-unconsumed at storm end.
     This script PRE-SEEDS the ledger (each id recorded at send, never reconstructed).
  S2 NO PHANTOM WAKE: the trace/steer flood alone never produces a watcher exit-0 with
     DETECTED block (SKIP_KINDS discipline under load).
  S3 CURSOR PASSES THE CORPSE: after the mid-burst kill, the successor claims and its
     commits succeed.
  S4 SINGLE CONSUMER HOLDS: twin watcher sessions -- exactly one advances the shared
     cursor; loser gets RB-21 teaching shape.
  S5 DUPLICATE DISCIPLINE: redelivered handoffs are answered at most once within the
     reply-sent sentinel's TTL window.

ISOLATION (CRITICAL — the F2 pins taught us shared-stream pollution wakes the real fleet):
  The burst script writes to namespace "rb25drill3" (NOT the live "bifrost" namespace).
  All runner/watcher subprocesses launched by Claude MUST also use this namespace by
  setting BIFROST_NAMESPACE=rb25drill3 in their environment. Throwaway UUID ids for
  all drill agents. AKASHIC_DRILL_ECHO=1 on runners (throwaway ids are quarantined +
  we need them to NOT seed-at-tail since we plant mail first).

CLAUDE EXECUTION CHECKLIST:
  1. Set env: BIFROST_NAMESPACE=rb25drill3 + AKASHIC_DRILL_ECHO=1 for ALL drill subprocesses
  2. Use throwaway UUID agent ids for runners + watchers (never reuse live ids)
  3. Start 2 watchers (twin sessions, SAME watcher id) + 2 runners (different ids)
  4. Run the burst script (it connects to the same rb25drill3 namespace)
  5. Mid-burst: TASKKILL the SECOND runner, then resume the burst
  6. Start the successor runner (same id as the killed one)
  7. Wait for drain, then verify S1-S5 against the pre-seeded ledger

Usage:
  py tests/rb25_drill3_burst.py \
      --runner DEEPSEEK_ID --target SECOND_ID --watcher WATCHER_ID \
      [--namespace rb25drill3] [--pause-at 20] [--ledger research/reviewed/rb25-drill3-ledger.json]

The --pause-at flag makes the script PAUSE after sending that many messages, printing a
clear signal so the operator (claude) can TASKKILL the target runner mid-burst. Press
Enter to resume.
"""
import argparse
import json
import os
import sys
import time
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from core.comm.bus import Bus

STORM_KINDS = [
    # (kind, count, to_target, description)
    # S1 material: directed requests that MUST be answered (runner targets)
    ("request", 12, "runner", "directed request to deepseek runner"),
    ("request", 8,  "target", "directed request to second runner"),
    # S2 material: trace/steer flood that must NOT wake the watcher
    ("trace",   8,  "broadcast", "display-only trace broadcast"),
    ("steer",   5,  "runner", "soft steer to deepseek runner"),
    ("trace",   3,  "broadcast", "more trace noise"),
    # S5 material: handoffs exercise the reply-sent sentinel / duplicate discipline
    ("handoff", 2,  "runner", "handoff to deepseek runner"),
    # S1 remainder: more directed requests to both runners
    ("request", 4,  "runner", "more directed requests to deepseek runner"),
    ("request", 3,  "target", "more directed requests to second runner"),
    # chat noise (tolerated duplicates per S5)
    ("chat",    2,  "runner", "casual chat to deepseek runner"),
    ("chat",    1,  "target", "casual chat to second runner"),
    # S2: one more steer for good measure
    ("steer",   1,  "runner", "final steer"),
    # S1: final directed request to both
    ("request", 1,  "runner", "final request to deepseek runner"),
    ("request", 1,  "target", "final request to second runner"),
]

# Total: 12+8+8+5+3+2+4+3+2+1+1+1+1 = 51 messages (>= 40 ✓)


def _resolve_target(kind_spec: str, runner_id: str, target_id: str) -> str:
    """Map the logical target in STORM_KINDS to an actual agent id."""
    if kind_spec == "runner":
        return runner_id
    elif kind_spec == "target":
        return target_id
    elif kind_spec == "broadcast":
        return "*"
    raise ValueError(f"unknown target spec: {kind_spec}")


def main():
    parser = argparse.ArgumentParser(description="RB-25 Drill 3 concurrency storm burst")
    parser.add_argument("--runner", required=True, help="DeepSeek runner agent id")
    parser.add_argument("--target", required=True, help="Second runner agent id")
    parser.add_argument("--watcher", required=True, help="Watcher agent id (for the ledger)")
    parser.add_argument("--namespace", default="rb25drill3",
                        help="Redis namespace for the drill (default: rb25drill3 — isolated from live bifrost)")
    parser.add_argument("--count", type=int, default=None,
                        help="Override total message count (default: use the frozen STORM_KINDS total)")
    parser.add_argument("--pause-at", type=int, default=None,
                        help="Pause after N messages for the mid-burst TASKKILL (press Enter to resume)")
    parser.add_argument("--ledger", default=None,
                        help="Path for the send-time ledger JSON (default: research/reviewed/rb25-drill3-ledger.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the message plan without sending anything")
    args = parser.parse_args()

    runner_id = args.runner
    target_id = args.target
    watcher_id = args.watcher
    storm_id = uuid.uuid4().hex[:12]

    # --- Build the message plan ---
    plan = []
    for kind, count, to_spec, desc in STORM_KINDS:
        to_agent = _resolve_target(to_spec, runner_id, target_id)
        for i in range(count):
            seq = len(plan)
            content_tag = f"storm-{storm_id}-{kind}-{seq:03d}"
            if kind == "request":
                content = f"[drill-3 request] {content_tag}: {desc}"
            elif kind == "handoff":
                content = f"[drill-3 handoff] {content_tag}: {desc}"
            elif kind == "steer":
                content = f"[drill-3 steer] {content_tag}: fold this into your current round: {desc}"
            elif kind == "trace":
                content = f"[drill-3 trace] {content_tag}: {desc} (display-only, never wakes)"
            elif kind == "chat":
                content = f"[drill-3 chat] {content_tag}: hello from the storm"
            else:
                content = f"[drill-3] {content_tag}: {desc}"
            plan.append({
                "seq": seq,
                "kind": kind,
                "to": to_agent,
                "content_tag": content_tag,
                "content": content,
                "desc": desc,
            })

    total = len(plan)
    if args.count is not None:
        plan = plan[:args.count]
        total = len(plan)
    if total < 40:
        print(f"ERROR: burst count {total} < 40 minimum. Increase --count or fix STORM_KINDS.",
              file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        print(f"DRY RUN: {total} messages planned (storm {storm_id})")
        for m in plan:
            print(f"  [{m['seq']:03d}] {m['kind']:8s} -> {m['to']:30s}  {m['content_tag']}")
        print(f"  pause-at: {args.pause_at}")
        return

    # --- Connect to the bus (ISOLATED namespace — never the live bifrost) ---
    driver_id = f"rb25-storm-driver-{storm_id}"
    bus = Bus(driver_id, namespace=args.namespace)
    if not bus.online:
        print("ERROR: bus is offline -- is Redis running?", file=sys.stderr)
        sys.exit(3)

    # --- PRE-SEED the ledger ---
    ledger_path = args.ledger or os.path.join(
        REPO, "research", "reviewed", "rb25-drill3-ledger.json")
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)

    ledger = {
        "storm_id": storm_id,
        "namespace": args.namespace,
        "driver_id": driver_id,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "targets": {
            "runner_deepseek": runner_id,
            "runner_second": target_id,
            "watcher": watcher_id,
        },
        "pause_at": args.pause_at,
        "planned_count": total,
        "messages": [],
    }

    # --- Execute the burst ---
    print(f"STORM {storm_id}: {total} messages in namespace '{args.namespace}' "
          f"(runner={runner_id}, target={target_id}, watcher={watcher_id})")
    if args.pause_at:
        print(f"  WILL PAUSE after message {args.pause_at} for TASKKILL")
    print(f"  ledger: {ledger_path}")
    print("---")

    sent_count = 0
    pause_at = args.pause_at

    for m in plan:
        # Send
        meta = {"storm_id": storm_id, "seq": m["seq"], "content_tag": m["content_tag"]}
        if m["to"] == "*":
            mid = bus.broadcast(m["kind"], m["content"], meta=meta)
        else:
            mid = bus.send(m["to"], m["kind"], m["content"], meta=meta)

        # Record in ledger (pre-seeded: recorded at send time, not reconstructed)
        entry = {
            "seq": m["seq"],
            "mid": mid,
            "kind": m["kind"],
            "to": m["to"],
            "content_tag": m["content_tag"],
            "sent_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ack": mid is not None,
        }
        ledger["messages"].append(entry)

        status = "✓" if mid else "✗ LOST (bus returned None)"
        print(f"  [{m['seq']:03d}/{total-1}] {m['kind']:8s} -> {m['to']:25s}  {status}  {mid or 'NO_MID'}")

        sent_count += 1

        # Flush ledger incrementally so a crash doesn't lose the whole record
        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=2)

        # --- Pause for mid-burst kill ---
        if pause_at is not None and sent_count == pause_at:
            print("===")
            print(f"PAUSE: {sent_count}/{total} messages sent.")
            print(f"OPERATOR: TASKKILL the runner ({target_id}) NOW, then press Enter to resume.")
            print("===")
            try:
                input()
            except EOFError:
                pass
            print("RESUMING burst...")

        # Small inter-send delay so the bus isn't overwhelmed and the operator has
        # time to observe / kill. 50ms = 20 msgs/sec; the full burst takes ~2.5s.
        time.sleep(0.05)

    # --- Finalize ---
    ledger["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ledger["sent_count"] = sent_count
    ledger["lost_count"] = sum(1 for m in ledger["messages"] if not m["ack"])

    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)

    print("---")
    print(f"STORM COMPLETE: {sent_count} sent, {ledger['lost_count']} lost, "
          f"ledger -> {ledger_path}")
    print("Post-storm verification (operator):")
    print(f"  S1: check every request mid in the ledger has a reply or is unconsumed")
    print(f"  S2: check watcher stdout -- trace/steer flood must NOT produce DETECTED exit")
    print(f"  S3: check successor cursor > corpse's last committed cursor")
    print(f"  S4: check twin watcher transcripts for RB-21 teaching shape on loser")
    print(f"  S5: check no duplicate replies for handoff mids within sentinel TTL")


if __name__ == "__main__":
    main()
