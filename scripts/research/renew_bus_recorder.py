"""
renew_bus_recorder -- durably capture live Bifrost traffic for the RENEW context-lifecycle research.

Bird #2 of the "two birds" exercise (2026-07-07): the bus is ephemeral (Redis Streams, maxlen-capped)
and only *salient* kinds are promoted to the Ledger, so ordinary tool-call traces are lost. This tails
the shared broadcast stream (every agent's tool traces + messages) and appends each message as one JSONL
line under research/in-flight/, so the "agents in flight" telemetry is parseable AFTER the fact.

That captured stream is also the substrate for RENEW research item A -- the deterministic context-health
signals (file-reread rate, tool-call repetition, turns-since-boot, per-agent churn). See
docs/agent-membrane-design-2026-07.md ("Renew") and the `renew-membrane-temporal-job` note.

Standalone + reversible: touches no hook and no hot path. Registers as its own bus agent so it only
READS; it never broadcasts (so it never pollutes the very stream it measures).

  py scripts/research/renew_bus_recorder.py            # tail forever, append to today's JSONL
  py scripts/research/renew_bus_recorder.py --once     # drain the current backlog and exit (smoke test)
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

from core.comm.bus import Bus

OUT_DIR = os.path.join(REPO, "research", "in-flight")
AGENT_ID = "renew-recorder"


def _outfile() -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return os.path.join(OUT_DIR, f"bus-{day}.jsonl")


def _record(fh, m) -> None:
    """One bus Message -> one flat JSONL row keyed for later item-A parsing."""
    row = {
        "id": m.id,            # ms-based stream id -> time-orderable
        "ts": m.ts,            # emitter wall-clock
        "frm": m.frm,          # which agent (multi-agent-in-flight dimension)
        "to": m.to,
        "kind": m.kind,        # "tool", "say", "think", ... (trace.emit uses "tool")
        "content": m.content,  # the tool summary string (parse Read/Edit targets from here)
        "meta": m.meta,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    fh.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="drain the current backlog once and exit (smoke test), don't block")
    args = ap.parse_args()

    bus = Bus(AGENT_ID)
    if not bus.online:
        print("[renew-recorder] bus offline (Redis unreachable); nothing to record", file=sys.stderr)
        return 1
    bus.register(card={"role": "research recorder",
                       "note": "read-only; captures in-flight telemetry for RENEW research"})

    path = _outfile()
    n = 0
    with open(path, "a", encoding="utf-8") as fh:
        if args.once:
            for m in bus.wait(timeout_ms=1500, advance=True, limit=500):
                _record(fh, m)
                n += 1
            fh.flush()
            print(f"[renew-recorder] --once drained {n} message(s) -> {path}")
            return 0
        print(f"[renew-recorder] tailing Bifrost -> {path} (Ctrl-C to stop)")
        while True:
            msgs = bus.wait(timeout_ms=0, advance=True, limit=200)   # block forever, ~0 cost
            if not msgs:
                continue
            for m in msgs:
                _record(fh, m)
                n += 1
            fh.flush()


if __name__ == "__main__":
    raise SystemExit(main())
