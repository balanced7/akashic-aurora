#!/usr/bin/env python
"""mem_watch -- a black box recorder for host memory.

Born 2026-08-26, the morning after the machine ran out of 62GB and the
forensics found NOTHING: the ramdisk logs died with the reboot, Windows
logged no Resource-Exhaustion event, and no process-level history existed
anywhere. We could not name the culprit because nobody was writing it down.

This is the writing-down. It samples host + per-process memory on an
interval and appends one JSON line per sample to a log that SURVIVES A
REBOOT (E:\\, deliberately not the X:\\ ramdisk -- a forensic log on a
ramdisk is a log that deletes itself exactly when you need it).

Two outputs:
  - the JSONL trail (durable, for post-mortems)
  - stdout ALERT/WARN lines (for a live Monitor to notify on)

Deliberately dependency-free and cheap: one psutil sweep per interval,
a bounded top-N, and size-capped rotation so it cannot become the thing
that eats the disk.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover - environment guard
    print("mem_watch: psutil is required (py -m pip install psutil)", file=sys.stderr)
    raise SystemExit(2)

DEFAULT_LOG = str(Path(__file__).resolve().parents[2] / "state" / "mem-watch" / "mem_watch.jsonl")

# Processes whose RSS is OS memory ACCOUNTING, not consumption. MemCompression's
# working set IS other processes' compressed pages: it grows when Windows is SAVING
# memory, so a growth alert on it says the opposite of what it appears to say. Real
# pressure is still caught -- by the host warn-pct/alert-pct rule, which is the right
# instrument for it. Observed 2026-08-27: MemCompression at 4.4GB while the host sat
# at 46.7% used with 32.9GB free and swap at 0.4%.
SYSTEM_MEM_PROCS = {"memcompression", "system", "system idle process"}
# Rotate well before the log itself becomes a disk problem.
MAX_BYTES = 32 * 1024 * 1024
KEEP_ROTATIONS = 3


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rotate(path: str) -> None:
    """Size-capped rotation. A forensic log that fills the disk is a new incident."""
    try:
        if os.path.getsize(path) < MAX_BYTES:
            return
    except OSError:
        return
    oldest = f"{path}.{KEEP_ROTATIONS}"
    if os.path.exists(oldest):
        os.remove(oldest)
    for i in range(KEEP_ROTATIONS - 1, 0, -1):
        src, dst = f"{path}.{i}", f"{path}.{i + 1}"
        if os.path.exists(src):
            os.replace(src, dst)
    os.replace(path, f"{path}.1")


def sample(top_n: int, track_substrings: list[str]) -> dict:
    vm = psutil.virtual_memory()
    procs = []
    tracked = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "create_time", "cmdline"]):
        try:
            info = p.info
            mi = info.get("memory_info")
            if not mi:
                continue
            rss_mb = round(mi.rss / (1024 * 1024), 1)
            row = {
                "pid": info["pid"],
                "name": info.get("name") or "?",
                "rss_mb": rss_mb,
            }
            procs.append(row)
            # Anything that looks like ours gets recorded regardless of rank,
            # so a slow leak in a small process is still visible in the trail.
            cmd = " ".join(info.get("cmdline") or [])
            low = cmd.lower()
            if any(s in low for s in track_substrings):
                tracked.append({
                    **row,
                    "age_s": int(time.time() - (info.get("create_time") or time.time())),
                    "cmd": cmd[:200],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda r: r["rss_mb"], reverse=True)
    swap = psutil.swap_memory()
    return {
        "at": _utc(),
        "host": {
            "total_mb": round(vm.total / (1024 * 1024)),
            "available_mb": round(vm.available / (1024 * 1024)),
            "percent_used": vm.percent,
            "swap_used_mb": round(swap.used / (1024 * 1024)),
        },
        "top": procs[:top_n],
        "tracked": sorted(tracked, key=lambda r: r["rss_mb"], reverse=True),
        "proc_count": len(procs),
    }



def process_alert(*, name, pid, rss, first_seen, last_alert, peak,
                  proc_alert_mb, growth_alert_mb):
    """The per-process leak decision, pure so it can be pinned. Alert line, or None.

    A process that is merely BIG was probably always big (WSL's VM sits at gigabytes
    by design). A process that is big AND STILL CLIMBING is the leak. Requiring both
    keeps the lane quiet enough to trust.

    RE-ARM RATCHET (2026-08-27, found in production the first time this organ ever
    fired for real). The old rule compared against first_seen on EVERY sample, so a
    process that climbed once and then went flat re-alerted every interval forever --
    observed firing six times in three minutes on a process that was actively
    SHRINKING, while the host sat at 46.7% used with 32.9GB free. A leak detector
    must report ACCELERATION, not a standing state. After a trip, a process must
    climb another full growth_alert_mb above the level it last alerted at before it
    speaks again. Same cry-wolf class as the operator-inbox warning filed the same
    day ([f63e1186c6]): an alarm that is wrong in the common case trains everyone to
    ignore it in the uncommon one, which is the only case that ever mattered.

    The morning's drill proved this organ FIRES. It could not prove it ever STOPS --
    it ran a deliberate 90-second ramp and was watched only while the ramp climbed.
    """
    if str(name).lower() in SYSTEM_MEM_PROCS:
        return None
    if rss < proc_alert_mb:
        return None
    growth = rss - first_seen
    if last_alert is None:
        if growth < growth_alert_mb:
            return None
        since = "since first seen"
    elif rss - last_alert < growth_alert_mb:
        return None
    else:
        since = f"since the {last_alert:.0f}MB alert"
    return (f"ALERT process {name} pid={pid} rss={rss}MB peak={peak:.0f}MB "
            f"(grew {growth:+.1f}MB {since})")


def main() -> int:
    ap = argparse.ArgumentParser(description="host + per-process memory black box")
    ap.add_argument("--interval", type=int, default=30, help="seconds between samples")
    ap.add_argument("--log", default=DEFAULT_LOG, help="durable JSONL path (must survive reboot)")
    ap.add_argument("--top", type=int, default=12, help="how many processes to record per sample")
    ap.add_argument("--warn-pct", type=float, default=80.0, help="host used%% that emits WARN")
    ap.add_argument("--alert-pct", type=float, default=90.0, help="host used%% that emits ALERT")
    ap.add_argument("--proc-alert-mb", type=float, default=4096.0,
                    help="single-process RSS floor before growth is worth alerting on")
    ap.add_argument("--growth-alert-mb", type=float, default=512.0,
                    help="RSS growth since first sighting that emits ALERT")
    ap.add_argument("--track", default="ai-setup,akashic,bifrost,bridge,discord,ollama,vmmem",
                    help="comma-separated substrings marking processes we always record")
    ap.add_argument("--once", action="store_true", help="take one sample and exit")
    args = ap.parse_args()

    track = [s.strip().lower() for s in args.track.split(",") if s.strip()]
    os.makedirs(os.path.dirname(args.log), exist_ok=True)

    # Per-process high-water marks let us name a GROWING process, not just a big
    # one. A process that is merely large was probably always large; a process
    # whose RSS only ever climbs is the leak.
    highwater: dict[int, float] = {}
    first_seen: dict[int, float] = {}
    alerted_at: dict[int, float] = {}   # RSS at each pid's last ALERT -- the re-arm floor

    while True:
        snap = sample(args.top, track)
        pct = snap["host"]["percent_used"]

        alerts = []
        if pct >= args.alert_pct:
            alerts.append(
                f"ALERT host memory {pct:.1f}% used, "
                f"{snap['host']['available_mb']}MB free -- top: "
                + ", ".join(f"{r['name']}:{r['rss_mb']}MB" for r in snap["top"][:5])
            )
        elif pct >= args.warn_pct:
            alerts.append(f"WARN host memory {pct:.1f}% used, {snap['host']['available_mb']}MB free")

        for row in snap["top"] + snap["tracked"]:
            pid, rss = row["pid"], row["rss_mb"]
            prev = highwater.get(pid, 0.0)
            if rss > prev:
                highwater[pid] = rss
            first_seen.setdefault(pid, rss)
            growth = rss - first_seen[pid]
            line = process_alert(
                name=row["name"], pid=pid, rss=rss, first_seen=first_seen[pid],
                last_alert=alerted_at.get(pid), peak=highwater.get(pid, rss),
                proc_alert_mb=args.proc_alert_mb, growth_alert_mb=args.growth_alert_mb)
            if line:
                alerted_at[pid] = rss
                alerts.append(line)

        snap["alerts"] = alerts
        _rotate(args.log)
        with open(args.log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(snap) + "\n")

        for line in alerts:
            print(f"[{snap['at']}] {line}", flush=True)

        # Reap high-water entries for dead pids so this watcher does not become
        # the leak it was written to catch.
        live = {r["pid"] for r in snap["top"]} | {r["pid"] for r in snap["tracked"]}
        for dead in [p for p in highwater if p not in live]:
            highwater.pop(dead, None)
            first_seen.pop(dead, None)
            alerted_at.pop(dead, None)

        if args.once:
            print(json.dumps(snap["host"]), flush=True)
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
