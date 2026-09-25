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

THE COMMIT GAUGE (2026-09-24). The machine froze again (1 fps cursor, hard
power cut) and this recorder named nothing, for two reasons:
  1. It was not running. Launched by hand, it wrote its last sample at
     2026-09-07 17:37, the minute of a reboot, and nothing started it again.
     It now runs from the AkashicAurora-MemWatch scheduled task (logon, plus
     a 15-minute self-heal trigger that is ignored while an instance lives).
  2. It watched the wrong gauge. Its own trail covers two Resource-Exhaustion
     hits (09-04 01:53, 09-06 02:33); at both, 21.2 GB and 14.0 GB of RAM were
     still AVAILABLE. Windows' detector fires on COMMIT -- memory charged
     against RAM + pagefile (~124 GB here) -- and commit that is charged but
     not resident is invisible to RSS. So each sample now also carries system
     commit, kernel paged/nonpaged pool, handle and thread totals, the top
     kernel pool tags (the 09-11 outage WAS the pool, and a tag is the only
     handle on which driver holds it), and per-process private bytes and
     handles. Under pressure it samples faster and writes a full snapshot of
     every process with its command line, so the next post-mortem has a name.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import psutil
except ImportError:  # pragma: no cover - environment guard
    print("mem_watch: psutil is required (py -m pip install psutil)", file=sys.stderr)
    raise SystemExit(2)

DEFAULT_LOG = r"E:\AI-Setup\state\mem-watch\mem_watch.jsonl"

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
MB = 1024 * 1024
IS_WINDOWS = sys.platform == "win32"


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


def _win_perf() -> dict:
    """System commit, kernel pools and handle totals from GetPerformanceInfo.

    Returns {} off Windows or if the call fails: the recorder must never die for
    want of one gauge.
    """
    if not IS_WINDOWS:
        return {}
    try:
        import ctypes
        from ctypes import wintypes

        class PERFORMANCE_INFORMATION(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("CommitTotal", ctypes.c_size_t), ("CommitLimit", ctypes.c_size_t),
                        ("CommitPeak", ctypes.c_size_t), ("PhysicalTotal", ctypes.c_size_t),
                        ("PhysicalAvailable", ctypes.c_size_t), ("SystemCache", ctypes.c_size_t),
                        ("KernelTotal", ctypes.c_size_t), ("KernelPaged", ctypes.c_size_t),
                        ("KernelNonpaged", ctypes.c_size_t), ("PageSize", ctypes.c_size_t),
                        ("HandleCount", wintypes.DWORD), ("ProcessCount", wintypes.DWORD),
                        ("ThreadCount", wintypes.DWORD)]

        pi = PERFORMANCE_INFORMATION()
        pi.cb = ctypes.sizeof(pi)
        if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(pi), pi.cb):
            return {}

        def mb(pages: int) -> int:
            return round(pages * pi.PageSize / MB)

        commit, limit = mb(pi.CommitTotal), mb(pi.CommitLimit)
        return {
            "commit_mb": commit,
            "commit_limit_mb": limit,
            "commit_peak_mb": mb(pi.CommitPeak),
            "commit_pct": round(100.0 * commit / limit, 1) if limit else 0.0,
            "kernel_paged_mb": mb(pi.KernelPaged),
            "kernel_nonpaged_mb": mb(pi.KernelNonpaged),
            "system_cache_mb": mb(pi.SystemCache),
            "handles": int(pi.HandleCount),
            "threads": int(pi.ThreadCount),
        }
    except Exception:
        return {}


def _pool_tags(top: int | None = 8, min_mb: float = 0.0) -> list[dict]:
    """Kernel pool usage by tag (SystemPoolTagInformation), biggest first.

    top=N keeps the N biggest nonpaged plus the N biggest paged tags; top=None keeps
    every tag of at least min_mb. Returns [] off 64-bit Windows or on any failure.
    """
    if not IS_WINDOWS:
        return []
    try:
        import ctypes
        if ctypes.sizeof(ctypes.c_void_p) != 8:  # the record layout below is x64's
            return []
        size, status, raw = 1 << 20, None, b""
        for _ in range(6):
            buf = ctypes.create_string_buffer(size)
            ret = ctypes.c_ulong(0)
            status = ctypes.windll.ntdll.NtQuerySystemInformation(
                22, buf, size, ctypes.byref(ret)) & 0xFFFFFFFF
            if status == 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH: grow and retry
                size = max(size * 2, ret.value + 4096)
                continue
            raw = buf.raw[:ret.value or size]
            break
        if status != 0 or len(raw) < 8:
            return []
        count = int.from_bytes(raw[0:4], "little")
        rows = []
        for i in range(count):
            rec = raw[8 + i * 40: 8 + (i + 1) * 40]
            if len(rec) < 40:
                break
            rows.append({
                "tag": rec[0:4].decode("ascii", "replace").replace("\x00", " "),
                "nonpaged_mb": round(int.from_bytes(rec[32:40], "little") / MB, 1),
                "paged_mb": round(int.from_bytes(rec[16:24], "little") / MB, 1),
            })
        if top is None:
            keep = [r for r in rows if r["nonpaged_mb"] + r["paged_mb"] >= min_mb]
        else:
            by_np = sorted(rows, key=lambda r: r["nonpaged_mb"], reverse=True)[:top]
            by_pg = sorted(rows, key=lambda r: r["paged_mb"], reverse=True)[:top]
            keep = list({r["tag"]: r for r in by_np + by_pg}.values())
        return sorted(keep, key=lambda r: r["nonpaged_mb"] + r["paged_mb"], reverse=True)
    except Exception:
        return []


def sample(top_n: int, track_substrings: list[str]) -> dict:
    vm = psutil.virtual_memory()
    procs = []
    tracked = []
    attrs = ["pid", "name", "memory_info", "create_time", "cmdline"]
    if IS_WINDOWS:
        attrs.append("num_handles")
    for p in psutil.process_iter(attrs):
        try:
            info = p.info
            mi = info.get("memory_info")
            if not mi:
                continue
            rss_mb = round(mi.rss / MB, 1)
            # Private bytes = this process's COMMIT charge (Windows pmem.private; vms is
            # the same pagefile figure). RSS alone misses commit that is not resident.
            private = getattr(mi, "private", None)
            if private is None:
                private = getattr(mi, "vms", 0)
            row = {
                "pid": info["pid"],
                "name": info.get("name") or "?",
                "rss_mb": rss_mb,
                "private_mb": round(private / MB, 1),
                "handles": info.get("num_handles") or 0,
            }
            cmd = " ".join(info.get("cmdline") or [])
            procs.append({**row, "cmd": cmd[:300]})
            # Anything that looks like ours gets recorded regardless of rank,
            # so a slow leak in a small process is still visible in the trail.
            low = cmd.lower()
            if any(s in low for s in track_substrings):
                tracked.append({
                    **row,
                    "age_s": int(time.time() - (info.get("create_time") or time.time())),
                    "cmd": cmd[:200],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # The top list is the union of the biggest by RSS and the biggest by COMMIT:
    # a process whose pages were trimmed or never touched still holds commit.
    by_rss = sorted(procs, key=lambda r: r["rss_mb"], reverse=True)[:top_n]
    by_private = sorted(procs, key=lambda r: r["private_mb"], reverse=True)[:top_n]
    top = list({r["pid"]: {k: v for k, v in r.items() if k != "cmd"}
                for r in by_rss + by_private}.values())
    top.sort(key=lambda r: r["rss_mb"], reverse=True)
    swap = psutil.swap_memory()
    host = {
        "total_mb": round(vm.total / MB),
        "available_mb": round(vm.available / MB),
        "percent_used": vm.percent,
        "swap_used_mb": round(swap.used / MB),
        "uptime_h": round((time.time() - psutil.boot_time()) / 3600, 1),
    }
    host.update(_win_perf())
    return {
        "at": _utc(),
        "host": host,
        "top": top,
        "top_handles": [{"pid": r["pid"], "name": r["name"], "handles": r["handles"]}
                        for r in sorted(procs, key=lambda r: r["handles"], reverse=True)[:5]],
        "pools": _pool_tags(8),
        "tracked": sorted(tracked, key=lambda r: r["rss_mb"], reverse=True),
        "proc_count": len(procs),
        "_all": procs,  # for the pressure snapshot only; main() never writes it to the trail
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


def host_commit_alert(*, commit_mb, limit_mb, warn_pct, alert_pct, top_private):
    """The commit-side host decision, pure so it can be pinned. Alert line, or None.

    Commit is the gauge Windows' Resource-Exhaustion detector actually reads, and at
    both of its hits this recorder's trail holds (09-04, 09-06) the RSS gauge still
    showed 14-21 GB available. The line names the biggest private-bytes holders,
    because an alert that reports only a total repeats the 08-26 blindness.
    """
    if not limit_mb:
        return None
    pct = 100.0 * commit_mb / limit_mb
    if pct < warn_pct:
        return None
    level = "ALERT" if pct >= alert_pct else "WARN"
    who = ", ".join(f"{r['name']}:{r['private_mb']:.0f}MB" for r in top_private[:5])
    return f"{level} host commit {pct:.1f}% ({commit_mb}/{limit_mb} MB) -- top private: {who}"


def should_snapshot(*, now, last_snapshot_at, commit_pct, available_mb,
                    pct_threshold, min_available_mb, min_gap_s):
    """Whether to write a full pressure snapshot now. Pure, so it can be pinned.

    Pressure is high commit OR little available RAM (either one froze this machine).
    Snapshots are throttled so a long squeeze leaves a record, not a flood.
    """
    if commit_pct < pct_threshold and available_mb >= min_available_mb:
        return False
    return last_snapshot_at is None or now - last_snapshot_at > min_gap_s


def prune_snapshots(directory: str, keep: int) -> int:
    """Keep only the newest `keep` snapshots. Returns how many were removed."""
    files = sorted(glob.glob(os.path.join(directory, "snap-*.json")), key=os.path.getmtime)
    doomed = files[:-keep] if keep > 0 else files
    removed = 0
    for f in doomed:
        try:
            os.remove(f)
            removed += 1
        except OSError:
            pass
    return removed


def write_snapshot(directory: str, snap: dict, keep: int) -> str:
    """Every process (with its command line) plus every pool tag >= 8 MB, one file."""
    os.makedirs(directory, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(directory, f"snap-{stamp}.json")
    body = {
        "at": snap["at"],
        "host": snap["host"],
        "pools": _pool_tags(None, min_mb=8.0),
        "procs": sorted(snap.get("_all", []), key=lambda r: r["private_mb"], reverse=True),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    prune_snapshots(directory, keep)
    return path


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
    ap.add_argument("--commit-warn-pct", type=float, default=80.0,
                    help="system commit %% of the commit limit that emits WARN")
    ap.add_argument("--commit-alert-pct", type=float, default=90.0,
                    help="system commit %% of the commit limit that emits ALERT")
    ap.add_argument("--pressure-pct", type=float, default=85.0,
                    help="commit %% at which sampling switches to --pressure-interval")
    ap.add_argument("--pressure-interval", type=int, default=30,
                    help="seconds between samples while under pressure")
    ap.add_argument("--snapshot-pct", type=float, default=88.0,
                    help="commit %% that triggers a full pressure snapshot")
    ap.add_argument("--snapshot-min-avail-mb", type=float, default=2048.0,
                    help="available RAM below which a snapshot is taken regardless of commit")
    ap.add_argument("--snapshot-gap", type=int, default=600,
                    help="minimum seconds between pressure snapshots")
    ap.add_argument("--snapshot-keep", type=int, default=40, help="snapshots to retain")
    ap.add_argument("--force-snapshot", action="store_true",
                    help="write one snapshot now regardless of pressure (for drills)")
    ap.add_argument("--once", action="store_true", help="take one sample and exit")
    args = ap.parse_args()

    track = [s.strip().lower() for s in args.track.split(",") if s.strip()]
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    snap_dir = os.path.join(os.path.dirname(args.log), "snapshots")

    # Per-process high-water marks let us name a GROWING process, not just a big
    # one. A process that is merely large was probably always large; a process
    # whose RSS only ever climbs is the leak.
    highwater: dict[int, float] = {}
    first_seen: dict[int, float] = {}
    alerted_at: dict[int, float] = {}   # RSS at each pid's last ALERT -- the re-arm floor
    last_snapshot_at: float | None = None

    while True:
        commit_pct = 0.0
        try:
            snap = sample(args.top, track)
            host = snap["host"]
            pct = host["percent_used"]
            commit_pct = host.get("commit_pct", 0.0)

            alerts = []
            if pct >= args.alert_pct:
                alerts.append(
                    f"ALERT host memory {pct:.1f}% used, "
                    f"{host['available_mb']}MB free -- top: "
                    + ", ".join(f"{r['name']}:{r['rss_mb']}MB" for r in snap["top"][:5])
                )
            elif pct >= args.warn_pct:
                alerts.append(f"WARN host memory {pct:.1f}% used, {host['available_mb']}MB free")

            top_private = sorted(snap["_all"], key=lambda r: r["private_mb"], reverse=True)
            line = host_commit_alert(
                commit_mb=host.get("commit_mb", 0), limit_mb=host.get("commit_limit_mb", 0),
                warn_pct=args.commit_warn_pct, alert_pct=args.commit_alert_pct,
                top_private=top_private)
            if line:
                alerts.append(line)

            for row in snap["top"] + snap["tracked"]:
                pid, rss = row["pid"], row["rss_mb"]
                prev = highwater.get(pid, 0.0)
                if rss > prev:
                    highwater[pid] = rss
                first_seen.setdefault(pid, rss)
                line = process_alert(
                    name=row["name"], pid=pid, rss=rss, first_seen=first_seen[pid],
                    last_alert=alerted_at.get(pid), peak=highwater.get(pid, rss),
                    proc_alert_mb=args.proc_alert_mb, growth_alert_mb=args.growth_alert_mb)
                if line:
                    alerted_at[pid] = rss
                    alerts.append(line)

            now = time.time()
            if args.force_snapshot or should_snapshot(
                    now=now, last_snapshot_at=last_snapshot_at, commit_pct=commit_pct,
                    available_mb=host["available_mb"], pct_threshold=args.snapshot_pct,
                    min_available_mb=args.snapshot_min_avail_mb, min_gap_s=args.snapshot_gap):
                snap["snapshot"] = write_snapshot(snap_dir, snap, args.snapshot_keep)
                last_snapshot_at = now

            all_procs = snap.pop("_all")
            snap["alerts"] = alerts
            _rotate(args.log)
            with open(args.log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(snap) + "\n")

            for line in alerts:
                print(f"[{snap['at']}] {line}", flush=True)

            # Reap high-water entries for dead pids so this watcher does not become
            # the leak it was written to catch.
            live = {r["pid"] for r in all_procs}
            for dead in [p for p in highwater if p not in live]:
                highwater.pop(dead, None)
                first_seen.pop(dead, None)
                alerted_at.pop(dead, None)

            if args.once:
                print(json.dumps(snap["host"]), flush=True)
                return 0
        except Exception as exc:  # a recorder that dies on one bad sample records nothing
            if args.once:
                raise
            try:
                with open(args.log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"at": _utc(), "error": repr(exc)[:500]}) + "\n")
            except OSError:
                pass
        time.sleep(args.pressure_interval if commit_pct >= args.pressure_pct else args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
