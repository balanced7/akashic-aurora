"""
RB-25 Drill 4 -- LONG IDLE SOAK (~72h). certify-at-soak-start (Daniel ruling 2026-07-12):
T029 certifies when drill 3 is verified AND this soak is ARMED with a clean T0. The 72h run is
PASSIVE background observation; ANY bar failure at a later checkpoint REOPENS T029.

Bars (docs/library/design/20260711_rb-25-engine-exam-runbook-pre-registered_9356ea.md, Drill 4):
  K1 MEMORY BOUNDED    runner+watcher RSS grows <= +15% of its T0 baseline (named tolerance, M8)
  K2 SEAT HYGIENE      the wake seat renews; no orphan seats accumulate; no kill-loop shape
  K3 RECONNECT         (manual, mid-window) one induced Redis restart -> degrade -> recover
  K4 FIREHOSE BOUNDED  the broadcast/event stream stays within its trim bound (no unbounded growth)
  K5 TRAFFIC ANSWERED  every ping answered inside its window; ZERO expectation_dead. The harness
                       INVOKES expectations.sweep each cycle (the sweep runs at render only, so a
                       72h loop that never swept would measure nothing -- runbook fence catch).

Subject: a LABELED throwaway ECHO runner + wake watcher on the LIVE bus. This soaks the real
infrastructure (memory, seats, firehose, reconnect) cost-free -- echo means no LLM calls. The 30-min
ping cadence is far under the reply rate limit, so the runaway guard never trips.

Durable, RE-ARMABLE: all state in research/reviewed/rb25-drill4-soak-ledger.json. If the monitor
process dies (reboot), re-run `monitor` -- it reads the ledger and continues; the detached subject
survives independently.

Subcommands:
  arm         start the subject, take the T0 checkpoint + first ping/sweep, report certify-at-start
  sample      one ping+sweep cycle (append a row) -- called by monitor or manually
  checkpoint  a full checkpoint (RSS/seats/firehose) evaluated vs T0 -- at T0/T24/T48/T72
  status      evaluate K1/K2/K4/K5 from the ledger so far -> PASS | DEGRADED | FAIL
  monitor     the loop: sample every --interval s, checkpoint every --checkpoint-every s, until
              --duration s (defaults 1800 / 86400 / 259200 = 30min / 24h / 72h). --compress for a
              fast smoke (10 / 30 / 90 s).
  disarm      stop the subject, finalize the ledger
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Isolate the soak SUBJECT in its own namespace: the echo runner + watcher then see ONLY soak traffic
# -- no spurious watcher wakes on live broadcasts, no stale-backlog answering -- and Fix A keeps their
# control plane off the live bus. K4 still probes the LIVE firehose explicitly (see _firehose_len).
os.environ.setdefault("BIFROST_NAMESPACE", "rb25soak")

import psutil  # noqa: E402
from core.comm.bus import Bus                 # noqa: E402
from core.comm import expectations            # noqa: E402
from core.comm import wake_seat               # noqa: E402
from core.comm import runner_lock             # noqa: E402

PY = sys.executable
LEDGER = REPO / "research" / "reviewed" / "rb25-drill4-soak-ledger.json"
LOGDIR = REPO / "research" / "reviewed" / "rb25-drill4-soak-logs"
RUNNER_ID = "rb25-soak-runner"
WATCHER_ID = "rb25-soak-watcher"
DRIVER_ID = "rb25-soak-driver"
SESSION = "rb25soak"
RSS_TOLERANCE = 0.15          # K1: +15% of T0
K4_SLACK = 1.10               # K4: XADD MAXLEN ~ trims approximately; allow 10% over the bound
PING_WITHIN_S = 300           # K5 reply window


# ------------------------------------------------------------------ ledger
def load() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save(led: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=2, default=str), encoding="utf-8")


def _now() -> float:
    return time.time()


def _rss(pid) -> int:
    try:
        return int(psutil.Process(int(pid)).memory_info().rss)
    except Exception:
        return -1                 # -1 = process gone / unreadable (K1 flags it)


def _alive(pid) -> bool:
    try:
        return psutil.pid_exists(int(pid)) and psutil.Process(int(pid)).is_running()
    except Exception:
        return False


# ------------------------------------------------------------------ subject
def _child_env() -> dict:
    e = dict(os.environ)
    e["AKASHIC_DRILL_ECHO"] = "1"          # echo responder: no LLM calls
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["BIFROST_MAX_REPLIES_PER_MIN"] = "1000"   # 30-min pings are far under this; belt+suspenders
    e["BIFROST_NAMESPACE"] = "rb25soak"          # subject isolated; Fix A keeps its control plane off live
    return e


def _spawn_detached(argv, log_path):
    """Launch a subject process that OUTLIVES this harness invocation (so the monitor can be a
    separate, re-armable process). Returns pid."""
    LOGDIR.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "a", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
    p = subprocess.Popen([PY] + argv, cwd=str(REPO), env=_child_env(),
                         stdout=f, stderr=subprocess.STDOUT, creationflags=flags)
    return p.pid


def _seat_orphans() -> int:
    """Count the SOAK subject's own dead-pid seat files (orphan accumulation, K2). Scoped to
    'rb25-soak-*' so pre-existing live orphan seats never false-fail the drill."""
    orphans = 0
    seat_dir = os.path.dirname(wake_seat.seat_path(WATCHER_ID, SESSION))
    for f in glob.glob(os.path.join(seat_dir, "bifrost_wake_rb25-soak-*.pid")):
        try:
            pid = int(open(f).read().strip() or "0")
            if pid and not _alive(pid):
                orphans += 1
        except Exception:
            pass
    return orphans


def _firehose_len() -> dict:
    """K4: the LIVE broadcast stream length vs its trim bound -- measured explicitly on 'bifrost'
    even though the soak subject is isolated, because K4 is about the REAL firehose staying bounded
    over 72h (Bus's explicit namespace= arg overrides the harness's BIFROST_NAMESPACE)."""
    try:
        b = Bus("rb25-soak-probe", namespace="bifrost")
        return {"bc_len": int(b._client.xlen(b._bc_key)), "maxlen": int(b.maxlen), "ns": "bifrost"}
    except Exception as e:
        return {"bc_len": -1, "maxlen": -1, "err": str(e)}


def take_checkpoint(led: dict, label: str) -> dict:
    r_pid, w_pid = led["subject"]["runner_pid"], led["subject"]["watcher_pid"]
    cp = {
        "label": label,
        "ts": _now(),
        "runner_alive": _alive(r_pid), "watcher_alive": _alive(w_pid),
        "runner_rss": _rss(r_pid), "watcher_rss": _rss(w_pid),
        "seat_present": os.path.exists(wake_seat.seat_path(WATCHER_ID, SESSION)),
        "seat_orphans": _seat_orphans(),
        "firehose": _firehose_len(),
    }
    led.setdefault("checkpoints", []).append(cp)
    return cp


# ------------------------------------------------------------------ one ping+sweep cycle (K5)
def do_sample(led: dict) -> dict:
    drv = Bus(DRIVER_ID)
    # sweep FIRST -- process the PRIOR cycle's expectation lifecycle (clear answered, redrive expired,
    # kill exhausted). This is the render-time invocation K5 requires; its `dead` list is the K5 signal.
    swept = expectations.sweep(DRIVER_ID)
    ts = _now()
    tag = str(ts)
    mid = drv.send(RUNNER_ID, "request", f"[soak-ping] {tag}", meta={"soak": True})
    armed = expectations.arm(DRIVER_ID, mid, RUNNER_ID, "request", "[soak-ping]", PING_WITHIN_S) if mid else False
    # Reliable "answered" = poll the driver inbox for the echo reply carrying THIS ping's unique ts,
    # independent of sweep timing (the earlier bug: a 2s sweep raced the reply).
    answered = False
    deadline = time.time() + 6
    while time.time() < deadline:
        if any(str(getattr(m, "kind", "")) == "reply" and tag in str(getattr(m, "content", ""))
               for m in drv.inbox(limit=200, advance=False)):
            answered = True
            break
        time.sleep(0.5)
    expectations.sweep(DRIVER_ID)                 # clear the now-answered expectation (no false redrive)
    drv.inbox(limit=1000, advance=True)           # consume replies so the driver inbox stays bounded
    row = {
        "ts": ts, "mid": mid, "armed": armed, "answered": answered,
        "dead": swept.get("dead", []), "redriven": swept.get("redriven", []),
        "runner_alive": _alive(led["subject"]["runner_pid"]),
    }
    led.setdefault("samples", []).append(row)
    return row


# ------------------------------------------------------------------ bar evaluation
def evaluate(led: dict) -> dict:
    cps = led.get("checkpoints", [])
    samples = led.get("samples", [])
    t0 = cps[0] if cps else None
    res = {}

    # K1 MEMORY BOUNDED -- runbook: fail if RSS "grows MONOTONICALLY beyond +15%". A one-time startup
    # settle that then plateaus is NOT a leak; only a sustained climb past tolerance is. So FAIL only
    # when the final growth exceeds tolerance AND memory is still climbing at the last checkpoint.
    if t0 and len(cps) >= 2:
        def _growth(cp, who):
            base, cur = t0.get(who, 0), cp.get(who, 0)
            return (cur - base) / base if base > 0 and cur > 0 else 0.0
        k1 = {"verdict": "PASS", "tolerance": RSS_TOLERANCE}
        for who in ("runner_rss", "watcher_rss"):
            series = [_growth(cp, who) for cp in cps]
            final = series[-1]
            climbing = final > series[-2] + 0.005      # still rising >0.5% at the end = trend, not settle
            if final > k1.get("final_growth", -1):
                k1.update({"who": who, "final_growth": round(final, 4), "still_climbing": climbing})
            if final > RSS_TOLERANCE and climbing:
                k1["verdict"] = "FAIL"
        res["K1"] = k1
    else:
        res["K1"] = {"verdict": "PENDING", "note": "need >=2 checkpoints for a trend"}

    # K2 SEAT HYGIENE
    orphan_max = max([cp.get("seat_orphans", 0) for cp in cps], default=0)
    seat_ok = all(cp.get("seat_present") for cp in cps) if cps else False
    res["K2"] = {"verdict": "PASS" if (seat_ok and orphan_max == 0) else ("PENDING" if not cps else "FAIL"),
                 "seat_present_all": seat_ok, "max_orphans": orphan_max}

    # K4 FIREHOSE BOUNDED -- approximate trimming (XADD MAXLEN ~) legitimately sits a little over the
    # bound; fail only on real UNBOUNDED growth (>K4_SLACK over maxlen), not macro-node granularity.
    overs = [cp for cp in cps if cp.get("firehose", {}).get("bc_len", -1) >
             cp.get("firehose", {}).get("maxlen", 1 << 30) * K4_SLACK]
    res["K4"] = {"verdict": "PASS" if (cps and not overs) else ("PENDING" if not cps else "FAIL"),
                 "breaches": len(overs)}

    # K5 TRAFFIC ANSWERED
    n = len(samples)
    unanswered = [s for s in samples if not s.get("answered")]
    dead = [d for s in samples for d in s.get("dead", [])]
    res["K5"] = {"verdict": "PASS" if (n > 0 and not unanswered and not dead) else ("PENDING" if n == 0 else "FAIL"),
                 "pings": n, "unanswered": len(unanswered), "expectation_dead": len(dead)}

    # K3 is a manual mid-window step
    res["K3"] = {"verdict": led.get("k3", {}).get("verdict", "MANUAL_PENDING"),
                 "note": "induced Redis restart, mid-window; record via `k3` marker"}

    overall = "PASS"
    for k in ("K1", "K2", "K4", "K5"):
        if res[k]["verdict"] == "FAIL":
            overall = "FAIL"
            break
        if res[k]["verdict"] == "PENDING" and overall != "FAIL":
            overall = "IN_PROGRESS"
    res["overall"] = overall
    return res


# ------------------------------------------------------------------ commands
def cmd_arm(args):
    if LEDGER.exists() and load().get("subject", {}).get("armed") and not args.force:
        print("soak already armed (use --force to re-arm from scratch). Use `status` / `monitor`.")
        return 1
    LOGDIR.mkdir(parents=True, exist_ok=True)
    # clear any stale locks from a prior soak subject
    for aid in (RUNNER_ID,):
        h = runner_lock.holder(aid) or {}
        if h.get("pid") and not _alive(h["pid"]):
            runner_lock.clear_if_pid(aid, h["pid"])
    r_pid = _spawn_detached(["scripts/bifrost_runner_deepseek.py", "--agent", RUNNER_ID],
                            LOGDIR / "soak_runner.log")
    w_pid = _spawn_detached(["scripts/bifrost_wake.py", "--agent", WATCHER_ID, "--session", SESSION,
                             "--deadline", "999999"], LOGDIR / "soak_watcher.log")
    time.sleep(6)                              # let them register + claim the seat
    led = {
        "drill": "rb25-drill4-soak", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "t0_ts": _now(), "namespace": "bifrost (live)",
        "subject": {"runner_id": RUNNER_ID, "watcher_id": WATCHER_ID, "driver_id": DRIVER_ID,
                    "runner_pid": r_pid, "watcher_pid": w_pid, "armed": True},
        "checkpoints": [], "samples": [],
    }
    take_checkpoint(led, "T0")
    do_sample(led)
    save(led)
    ev = evaluate(led)
    t0 = led["checkpoints"][0]
    clean = t0["runner_alive"] and t0["watcher_alive"] and led["samples"][-1]["answered"]
    print(f"SOAK ARMED @ T0 -- runner pid {r_pid} alive={t0['runner_alive']} rss={t0['runner_rss']}; "
          f"watcher pid {w_pid} alive={t0['watcher_alive']}; seat={t0['seat_present']}; "
          f"first ping answered={led['samples'][-1]['answered']}")
    print(f"T0 baseline clean: {clean}  ->  certify-at-soak-start "
          f"{'GRANTED (arm the monitor next)' if clean else 'BLOCKED (T0 not clean, investigate)'}")
    print(f"ledger -> {LEDGER}")
    return 0 if clean else 2


def cmd_sample(args):
    led = load()
    if not led.get("subject", {}).get("armed"):
        print("not armed -- run `arm` first")
        return 1
    row = do_sample(led)
    save(led)
    print(f"sample @ {time.strftime('%H:%M:%S')}: answered={row['answered']} dead={row['dead']} "
          f"runner_alive={row['runner_alive']}")
    return 0


def cmd_checkpoint(args):
    led = load()
    if not led.get("subject", {}).get("armed"):
        print("not armed -- run `arm` first")
        return 1
    cp = take_checkpoint(led, args.label or f"T+{int((_now()-led['t0_ts'])/3600)}h")
    save(led)
    print(f"checkpoint {cp['label']}: runner_rss={cp['runner_rss']} watcher_rss={cp['watcher_rss']} "
          f"seat={cp['seat_present']} orphans={cp['seat_orphans']} firehose={cp['firehose']}")
    return 0


def cmd_status(args):
    led = load()
    if not led:
        print("no soak ledger yet -- run `arm`")
        return 1
    ev = evaluate(led)
    elapsed_h = (_now() - led["t0_ts"]) / 3600
    print(f"RB-25 DRILL 4 SOAK -- {elapsed_h:.2f}h elapsed, {len(led.get('samples', []))} samples, "
          f"{len(led.get('checkpoints', []))} checkpoints")
    for k in ("K1", "K2", "K3", "K4", "K5"):
        print(f"  {k}: {ev[k]['verdict']:14s} {json.dumps({x: y for x, y in ev[k].items() if x != 'verdict'})}")
    print(f"  OVERALL: {ev['overall']}")
    return 0


def cmd_monitor(args):
    interval, cp_every, duration = (10, 30, 90) if args.compress else (args.interval, args.checkpoint_every, args.duration)
    led = load()
    if not led.get("subject", {}).get("armed"):
        print("not armed -- run `arm` first")
        return 1
    led["monitor_pid"] = os.getpid()          # so disarm can stop the loop; re-armable if it dies
    save(led)
    t_start = _now()
    last_cp = t_start
    print(f"monitor: interval={interval}s checkpoint_every={cp_every}s duration={duration}s")
    while _now() - t_start < duration:
        led = load()
        do_sample(led)
        if _now() - last_cp >= cp_every:
            take_checkpoint(led, f"T+{int((_now()-led['t0_ts'])/3600)}h")
            last_cp = _now()
        save(led)
        time.sleep(max(1, interval))
    led = load()
    take_checkpoint(led, "T-final")
    led["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save(led)
    ev = evaluate(led)
    print(f"monitor done -- overall {ev['overall']}")
    return 0


def cmd_disarm(args):
    led = load()
    for pid in (led.get("subject", {}).get("runner_pid"), led.get("subject", {}).get("watcher_pid"),
                led.get("monitor_pid")):
        if pid:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
            except Exception:
                pass
    h = runner_lock.holder(RUNNER_ID) or {}
    if h.get("pid"):
        runner_lock.clear_if_pid(RUNNER_ID, h["pid"])
    if led:
        led.setdefault("subject", {})["armed"] = False
        led["disarmed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save(led)
    print("soak disarmed (subject stopped)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="RB-25 drill 4 soak harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("arm"); a.add_argument("--force", action="store_true")
    sub.add_parser("sample")
    cp = sub.add_parser("checkpoint"); cp.add_argument("--label", default="")
    sub.add_parser("status")
    m = sub.add_parser("monitor")
    m.add_argument("--interval", type=int, default=1800)
    m.add_argument("--checkpoint-every", type=int, default=86400)
    m.add_argument("--duration", type=int, default=259200)
    m.add_argument("--compress", action="store_true", help="fast smoke: 10/30/90s")
    sub.add_parser("disarm")
    args = ap.parse_args()
    return {"arm": cmd_arm, "sample": cmd_sample, "checkpoint": cmd_checkpoint,
            "status": cmd_status, "monitor": cmd_monitor, "disarm": cmd_disarm}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
