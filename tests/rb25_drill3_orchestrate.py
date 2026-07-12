"""
RB-25 Drill 3 -- STORM orchestrator (execution harness; claude's executor for deepseek's frozen burst).

Runbook split (docs/rb25-exam-runbook-2026-07-11.md): deepseek AUTHORS the burst
(tests/rb25_drill3_burst.py, frozen), claude EXECUTES it against a live fleet. This harness
runs the whole storm deterministically in ONE process so the interactive-by-design drill
(mid-burst TASKKILL on operator signal) is reproducible and non-interactive:

  1. launch 2 echo runners (different ids) + 2 twin watchers (same id, 2 sessions), isolated ns
  2. capture pre-kill state (runner-lock generation + read-cursor for runner B)
  3. drive tests/rb25_drill3_burst.py UNMODIFIED via programmatic stdin -- feeds the --pause-at
     resume that a human would press Enter for (the frozen script is never edited)
  4. at the pause:  S4 probe (spawn a duplicate-id runner -> capture the RB-21 single-consumer
     refusal) ; hard-kill runner B (taskkill /F, no clean shutdown) ; clear_if_pid the corpse
     lock (the "cursor passes the corpse" operator move, per drill 1)
  5. resume the burst -> messages 21-50 land with runner B dead
  6. start the successor (same id as the corpse) -> it must claim + drain B's directed backlog
  7. capture the full evidence bundle -> research/reviewed/rb25-drill3-evidence-<storm>.json

Bars (frozen in the burst docstring; graded from the evidence by the verifier, deepseek):
  S1 no unacked loss   S2 no phantom wake   S3 cursor passes the corpse
  S4 single consumer holds   S5 duplicate discipline

The harness prints a PRELIMINARY execution-side self-read of each bar, but the GATE is
deepseek's independent verify (fence doctrine). ISOLATION: everything in namespace
'rb25drill3', throwaway uuid ids, AKASHIC_DRILL_ECHO=1 -- never the live 'bifrost' fleet.

Usage:  py tests/rb25_drill3_orchestrate.py [--pause-at 20]
"""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

NS = "rb25drill3"
# Our OWN reads (Bus, runner_lock) must target the drill namespace -- set BEFORE importing them.
os.environ["BIFROST_NAMESPACE"] = NS
os.environ["AKASHIC_DRILL_ECHO"] = "1"

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.comm.bus import Bus                # noqa: E402
from core.comm import runner_lock            # noqa: E402

PY = sys.executable
TAG_RE = re.compile(r"(storm-[0-9a-f]+-(?:request|handoff|steer|trace|chat)-\d{3})")


def child_env():
    e = dict(os.environ)
    e["AKASHIC_DRILL_ECHO"] = "1"
    e["BIFROST_NAMESPACE"] = NS
    # Force UTF-8 on every child: the frozen burst prints a check-mark status char, which a
    # piped child otherwise encodes as cp1252 on Windows and dies on. Environmental fix only --
    # the burst script itself is never edited.
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    return e


def spawn(argv, log_path, **kw):
    """Launch a child python process, stdout+stderr -> log_path. Returns Popen."""
    f = open(log_path, "w", encoding="utf-8")
    p = subprocess.Popen([PY] + argv, cwd=str(REPO), env=child_env(),
                         stdout=f, stderr=subprocess.STDOUT, text=True, **kw)
    p._logf = f
    return p


def log_tail(path, n=4000):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[-n:]
    except Exception:
        return ""


def tag_of(content):
    m = TAG_RE.search(str(content))
    return m.group(1) if m else None


def unconsumed(agent):
    """Non-destructive read of an agent's pending inbox (advance=False -> cursor untouched)."""
    b = Bus(agent)
    out = []
    for x in b.inbox(limit=3000, advance=False):
        out.append({"frm": x.frm, "kind": str(x.kind), "tag": tag_of(x.content)})
    return out


def main():
    ap = argparse.ArgumentParser(description="RB-25 drill 3 storm orchestrator")
    ap.add_argument("--pause-at", type=int, default=20, help="messages before the mid-burst kill")
    ap.add_argument("--drain-timeout", type=int, default=25, help="seconds to wait for the successor to drain")
    args = ap.parse_args()

    storm = uuid.uuid4().hex[:8]
    ids = {"a": f"d3a-{storm}", "b": f"d3b-{storm}", "w": f"d3w-{storm}"}
    reviewed = REPO / "research" / "reviewed"
    logdir = reviewed / f"rb25-drill3-logs-{storm}"
    logdir.mkdir(parents=True, exist_ok=True)
    ledger_path = reviewed / f"rb25-drill3-ledger-{storm}.json"
    evidence_path = reviewed / f"rb25-drill3-evidence-{storm}.json"

    ev = {"storm": storm, "ns": NS, "ids": ids, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    children = []

    def note(msg):
        print(f"[orch {storm}] {msg}", flush=True)

    try:
        # -- 1. runners + twin watchers -------------------------------------------------
        note(f"launching runners a={ids['a']} b={ids['b']} + twin watchers w={ids['w']}")
        rA = spawn(["scripts/bifrost_runner_deepseek.py", "--agent", ids["a"]], logdir / "runnerA.log")
        rB = spawn(["scripts/bifrost_runner_deepseek.py", "--agent", ids["b"]], logdir / "runnerB.log")
        children += [rA, rB]
        w1 = spawn(["scripts/bifrost_wake.py", "--agent", ids["w"], "--session", f"{storm}-s1"], logdir / "watcher1.log")
        w2 = spawn(["scripts/bifrost_wake.py", "--agent", ids["w"], "--session", f"{storm}-s2"], logdir / "watcher2.log")
        children += [w1, w2]
        time.sleep(5)  # registration + seat claim

        ev["boot"] = {
            "runnerA_alive": rA.poll() is None, "runnerB_alive": rB.poll() is None,
            "watcher1_alive": w1.poll() is None, "watcher2_alive": w2.poll() is None,
            "presence": Bus("orch-probe").presence(),
        }
        note(f"boot: runners alive={ev['boot']['runnerA_alive']}/{ev['boot']['runnerB_alive']} "
             f"watchers alive={ev['boot']['watcher1_alive']}/{ev['boot']['watcher2_alive']}")

        # -- 2. pre-kill state for runner B (the corpse-to-be) --------------------------
        hb = runner_lock.holder(ids["b"]) or {}
        ev["pre_kill"] = {
            "runnerB_pid": rB.pid,
            "lock_holder_b": hb,
            "gen_b": runner_lock.generation_of(hb.get("token", "")) if hb.get("token") else None,
            "cursor_b": Bus(ids["b"]).cursor(),
        }

        # -- 3. drive the frozen burst; read stdout until the pause ---------------------
        note("starting burst (pause-at=%d)" % args.pause_at)
        burst = subprocess.Popen(
            [PY, "tests/rb25_drill3_burst.py", "--runner", ids["a"], "--target", ids["b"],
             "--watcher", ids["w"], "--namespace", NS, "--pause-at", str(args.pause_at),
             "--ledger", str(ledger_path)],
            cwd=str(REPO), env=child_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1, encoding="utf-8", errors="replace")
        children.append(burst)

        q = queue.Queue()

        def reader(pipe, qq):
            for line in iter(pipe.readline, ''):
                qq.put(line)
            qq.put(None)

        threading.Thread(target=reader, args=(burst.stdout, q), daemon=True).start()

        burst_lines = []
        paused = False
        deadline = time.time() + 45
        while time.time() < deadline:
            try:
                line = q.get(timeout=1)
            except queue.Empty:
                if burst.poll() is not None:
                    break
                continue
            if line is None:
                break
            burst_lines.append(line.rstrip("\n"))
            if line.startswith("OPERATOR:") or "TASKKILL the runner" in line:
                paused = True
                break
        ev["burst_paused"] = paused
        note(f"burst paused={paused} after {len(burst_lines)} stdout lines")

        if not paused:
            # The burst did not reach the pause -- almost always an early crash. Capture + abort
            # cleanly (finally tears everything down) rather than proceeding to kill nothing.
            try:
                burst.wait(timeout=5)
            except Exception:
                pass
            (logdir / "burst.log").write_text("\n".join(burst_lines), encoding="utf-8")
            note("BURST DID NOT PAUSE -- likely early exit. Aborting. Tail:")
            print("\n".join(burst_lines[-15:]))
            ev["aborted"] = "burst_did_not_pause"
            evidence_path.write_text(json.dumps(ev, indent=2, default=str), encoding="utf-8")
            return

        # -- 4. at the pause: S4 probe, hard kill B, clear the corpse lock -------------
        # S4: a second runner with A's id must be refused (single-consumer seat).
        note("S4 probe: spawning duplicate runner for id a")
        dupe = spawn(["scripts/bifrost_runner_deepseek.py", "--agent", ids["a"], "--once"], logdir / "dupeA.log")
        try:
            dupe.wait(timeout=10)
        except subprocess.TimeoutExpired:
            dupe.kill()
        s4_out = log_tail(logdir / "dupeA.log")
        s4_refused = ("Refusing to start" in s4_out) or ("already live" in s4_out) or ("holds the consumer seat" in s4_out)
        ev["s4"] = {
            "dupe_exit": dupe.returncode,
            "refused": s4_refused,
            "pass": s4_refused,
            "dupe_out": s4_out[-600:],
        }
        note(f"S4 dupe refused={ev['s4']['refused']} exit={ev['s4']['dupe_exit']}")

        # corpse snapshot just before the kill
        corpse_cursor = Bus(ids["b"]).cursor()
        pid_b = rB.pid
        note(f"HARD KILL runner B pid={pid_b}")
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_b)], capture_output=True, text=True)
        time.sleep(1)
        cleared = runner_lock.clear_if_pid(ids["b"], pid_b)
        ev["kill"] = {
            "corpse_pid": pid_b,
            "corpse_cursor": corpse_cursor,
            "taskkill_done": rB.poll() is not None,
            "lock_cleared_by_pid": cleared,
        }
        note(f"corpse cleared_by_pid={cleared} exited={ev['kill']['taskkill_done']}")

        # -- 5. resume the burst (feed the newline the human would press) --------------
        try:
            burst.stdin.write("\n")
            burst.stdin.flush()
        except Exception as e:
            note(f"resume write failed: {e}")
        # drain the rest of the burst stdout
        while True:
            try:
                line = q.get(timeout=1)
            except queue.Empty:
                if burst.poll() is not None:
                    break
                continue
            if line is None:
                break
            burst_lines.append(line.rstrip("\n"))
        try:
            burst.wait(timeout=30)
        except subprocess.TimeoutExpired:
            burst.kill()
        (logdir / "burst.log").write_text("\n".join(burst_lines), encoding="utf-8")
        note(f"burst finished, {len(burst_lines)} total stdout lines")

        # -- 6. start the successor (same id as the corpse) ----------------------------
        note("starting successor runner for id b")
        rB2 = spawn(["scripts/bifrost_runner_deepseek.py", "--agent", ids["b"]], logdir / "runnerB_successor.log")
        children.append(rB2)
        time.sleep(4)
        succ_out = log_tail(logdir / "runnerB_successor.log")
        succ_hb = runner_lock.holder(ids["b"]) or {}
        ev["successor"] = {
            "pid": rB2.pid,
            "alive": rB2.poll() is None,
            "online": "online" in succ_out and "Refusing to start" not in succ_out,
            "refused": "Refusing to start" in succ_out,
            "lock_holder": succ_hb,
            "gen_b_after": runner_lock.generation_of(succ_hb.get("token", "")) if succ_hb.get("token") else None,
            "out": succ_out[-600:],
        }
        note(f"successor online={ev['successor']['online']} refused={ev['successor']['refused']}")

        # -- 7. wait for drain, then capture the evidence bundle -----------------------
        note("waiting for drain")
        t0 = time.time()
        while time.time() - t0 < args.drain_timeout:
            pa, pb = Bus(ids["a"]).pending(), Bus(ids["b"]).pending()
            if pa == 0 and pb == 0:
                break
            time.sleep(2)
        time.sleep(2)

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        driver_id = ledger["driver_id"]
        replies = Bus(driver_id).inbox(limit=5000, advance=False)
        reply_tags = {}
        for m in replies:
            t = tag_of(m.content)
            reply_tags[t] = reply_tags.get(t, 0) + 1

        unc_a, unc_b = unconsumed(ids["a"]), unconsumed(ids["b"])
        unc_tags = set(x["tag"] for x in (unc_a + unc_b) if x["tag"])
        answered = set(t for t in reply_tags if t)

        # S1 accounting over directed requests (the bar's subject)
        req_entries = [e for e in ledger["messages"] if e["kind"] == "request"]
        lost = [e["content_tag"] for e in req_entries
                if e["content_tag"] not in answered and e["content_tag"] not in unc_tags]
        ev["s1"] = {
            "requests_sent": len(req_entries),
            "send_side_lost": ledger.get("lost_count", 0),
            "answered": len([e for e in req_entries if e["content_tag"] in answered]),
            "unconsumed_at_end": len([e for e in req_entries if e["content_tag"] in unc_tags]),
            "unaccounted": lost,
            "pass": len(lost) == 0 and ledger.get("lost_count", 0) == 0,
        }

        # S2 phantom wake: did either watcher DETECT (exit on the trace/steer flood)?
        w1_out, w2_out = log_tail(logdir / "watcher1.log"), log_tail(logdir / "watcher2.log")
        ev["s2"] = {
            "watcher1_alive": w1.poll() is None, "watcher2_alive": w2.poll() is None,
            "watcher1_detected": "DETECTED" in w1_out, "watcher2_detected": "DETECTED" in w2_out,
            "pass": ("DETECTED" not in w1_out) and ("DETECTED" not in w2_out),
            "watcher1_out": w1_out[-400:], "watcher2_out": w2_out[-400:],
        }

        # S3 cursor passes the corpse -- report the SEAT handoff (mechanical) separately from
        # BACKLOG drain (the corpse's work actually getting consumed). Conflating them hides the
        # 2026-07-12 finding: the seat hands off cleanly but a non-virgin successor may not drain.
        b_pending = Bus(ids["b"]).pending()
        seat_handoff = (ev["successor"]["online"]
                        and ev["successor"]["lock_holder"].get("pid") != ev["kill"]["corpse_pid"]
                        and ev["kill"]["lock_cleared_by_pid"])
        ev["s3"] = {
            "corpse_cursor": ev["kill"]["corpse_cursor"],
            "successor_cursor": Bus(ids["b"]).cursor(),
            "lock_cleared": ev["kill"]["lock_cleared_by_pid"],
            "successor_online": ev["successor"]["online"],
            "successor_pid_differs": ev["successor"]["lock_holder"].get("pid") != ev["kill"]["corpse_pid"],
            "seat_handoff_ok": seat_handoff,
            "backlog_drained": b_pending == 0,
            "b_pending_final": b_pending,
            "pass": seat_handoff and b_pending == 0,
        }

        # S5 duplicate discipline: handoff answered at most once
        handoff_tags = [e["content_tag"] for e in ledger["messages"] if e["kind"] == "handoff"]
        ev["s5"] = {
            "handoff_reply_counts": {t: reply_tags.get(t, 0) for t in handoff_tags},
            "pass": all(reply_tags.get(t, 0) <= 1 for t in handoff_tags),
        }

        ev["reply_tags_total"] = sum(reply_tags.values())
        ev["unconsumed_a"], ev["unconsumed_b"] = unc_a, unc_b
        ev["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        evidence_path.write_text(json.dumps(ev, indent=2, default=str), encoding="utf-8")

        # -- preliminary execution-side self-read (NOT the gate) -----------------------
        print("\n" + "=" * 60)
        print(f"RB-25 DRILL 3 STORM -- execution self-read (storm {storm})")
        print("=" * 60)
        for bar in ("s1", "s2", "s3", "s4"):
            p = ev.get(bar, {}).get("pass")
            print(f"  {bar.upper()}: {'PASS' if p else 'CHECK'}  {json.dumps({k:v for k,v in ev[bar].items() if k not in ('watcher1_out','watcher2_out','dupe_out','out')})[:180]}")
        print(f"  S5: {'PASS' if ev['s5']['pass'] else 'CHECK'}  {ev['s5']['handoff_reply_counts']}")
        print(f"\nevidence -> {evidence_path}")
        print(f"ledger   -> {ledger_path}")
        print(f"logs     -> {logdir}")
        print("GATE: deepseek independent verify pending (fence doctrine).")

    finally:
        note("teardown: stopping all drill children")
        for p in children:
            try:
                if p.poll() is None:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            except Exception:
                pass
        # free the throwaway locks so a re-run is clean
        for k in ("a", "b"):
            try:
                h = runner_lock.holder(ids[k]) or {}
                if h.get("pid"):
                    runner_lock.clear_if_pid(ids[k], h["pid"])
            except Exception:
                pass


if __name__ == "__main__":
    main()
