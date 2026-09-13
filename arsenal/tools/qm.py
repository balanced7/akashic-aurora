"""Quartermaster (qm): Vandor's small helper for the arsenal lane's repeated chores.

    py arsenal/tools/qm.py mail                                  consume claude's work lane, one line per message
    py arsenal/tools/qm.py lock [--clear-stale]                  the git index lock and live git processes
    py arsenal/tools/qm.py commit --as SEAT --msg FILE PATH...   lock-aware commit, authored as the seat
    py arsenal/tools/qm.py receipts [first-light] [play]         run the Chrome receipts one at a time

Daniel, 2026-09-13: "feel free to set up helpers for yourself and naming them for long horizon work
and reducing your cognative load." Re-arming the Bifrost standby stays a harness-tracked background
command; this helper never starts long-lived listeners.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / ".git" / "index.lock"
RECEIPTS = {"first-light": "arsenal/lanes/chrome_verify.mjs", "play": "arsenal/lanes/play_verify.mjs"}
STALE_LOCK_S = 300

_HEADER = re.compile(r"^\s*\[([a-z_ -]+)\] from (\S+?):\s?(.*)$")
_FETCH = re.compile(r"bifrost-fetch --get (\S+?)\]")


# --------------------------------------------------------------------------- git lock
def git_process_count() -> int:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq git.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return sum(1 for line in out.splitlines() if line.lower().startswith('"git.exe"'))


def lock_state() -> dict:
    if not LOCK.exists():
        return {"present": False}
    st = LOCK.stat()
    return {"present": True, "bytes": st.st_size, "age_s": int(time.time() - st.st_mtime),
            "git_processes": git_process_count()}


def is_stale(state: dict) -> bool:
    # Only a lock nobody can still be writing: empty, old, and no git process alive right now.
    return state.get("present") and state["bytes"] == 0 and state["age_s"] > STALE_LOCK_S \
        and state["git_processes"] == 0


def clear_stale_lock() -> str:
    state = lock_state()
    if not state["present"]:
        return "no lock"
    if is_stale(state):
        LOCK.unlink()
        return f"removed a stale lock ({state['age_s']} s old, 0 bytes, no git process)"
    return f"kept the lock: {state}"


def wait_for_lock(max_wait_s: int = 90) -> bool:
    deadline = time.time() + max_wait_s
    while LOCK.exists() and time.time() < deadline:
        if is_stale(lock_state()):
            print(clear_stale_lock())
            break
        time.sleep(1)
    return not LOCK.exists()


# --------------------------------------------------------------------------- commands
def cmd_mail(args) -> int:
    env = dict(os.environ, BIFROST_CONSUME_LANE="work")
    done = subprocess.run([sys.executable, "agent_cli.py", "bifrost-sync", args.agent, "--consume", "--limit", "60"],
                          cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    messages, current = [], None
    for line in done.stdout.splitlines():
        header = _HEADER.match(line)
        if header:
            current = {"kind": header.group(1), "from": header.group(2), "first": header.group(3), "fetch": None}
            messages.append(current)
        if current:
            found = _FETCH.search(line)
            if found:
                current["fetch"] = found.group(1)
    if not messages:
        print((done.stdout.strip().splitlines() or ["(no output)"])[0])
        return done.returncode
    for msg in messages:
        tail = f"  [full: bifrost-fetch --get {msg['fetch']}]" if msg["fetch"] else ""
        print(f"[{msg['kind']}] {msg['from']}: {msg['first'][:args.width]}{tail}")
    print(f"({len(messages)} consumed; re-arm the standby as a harness-tracked background command)")
    return 0


def cmd_commit(args) -> int:
    msg = Path(args.msg)
    if not msg.is_file():
        print(f"no message file at {msg}")
        return 2
    if not wait_for_lock():
        print(f"the git lock is still held after waiting: {lock_state()}")
        return 3
    env = dict(os.environ, AKASHIC_AGENT_ID=args.seat, GIT_AUTHOR_NAME=args.seat,
               GIT_AUTHOR_EMAIL=f"{args.seat}@akashic-aurora.local")
    for argv in (["git", "add", "--", *args.paths], ["git", "commit", "-F", str(msg), "--", *args.paths]):
        done = subprocess.run(argv, cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        if done.returncode != 0:
            lines = [l for l in (done.stdout + done.stderr).splitlines() if "LF will be replaced" not in l]
            print("\n".join(lines[-15:]))
            return done.returncode
    head = subprocess.run(["git", "log", "-1", "--format=%h %an | %s"], cwd=REPO, capture_output=True, text=True)
    print(head.stdout.strip())
    return 0


def cmd_receipts(args) -> int:
    worst = 0
    for name in args.names or list(RECEIPTS):
        script = RECEIPTS.get(name)
        if not script:
            print(f"unknown receipt {name!r}; choose from {', '.join(RECEIPTS)}")
            worst = 2
            continue
        started = time.time()
        proc = subprocess.Popen(["node", script], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        try:
            out, _ = proc.communicate(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            # /T takes the test Chrome down with node, so no orphan keeps the debug port.
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
            out, _ = proc.communicate()
            tail = [l for l in out.splitlines() if l.strip()][-6:]
            print(f"{name}: TIMED OUT after {args.timeout} s, process tree killed")
            print("  last output: " + " | ".join(t[:160] for t in tail))
            worst = max(worst, 1)
            continue
        print(f"{name}: exit {proc.returncode} in {time.time() - started:.0f} s")
        for line in out.splitlines():
            if line.startswith(("verdict:", "receipt:", "decoder:", "clip frames:", "broken presets:", "ERROR", "EXC")):
                print("  " + line[:400])
        worst = max(worst, 0 if proc.returncode == 0 else 1)
    return worst


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")  # agent mail can carry characters a cp1252 console lacks
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(prog="qm", description="Quartermaster: Vandor's chores for the arsenal lane")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mail = sub.add_parser("mail", help="consume the work lane, one line per message")
    mail.add_argument("--agent", default="claude")
    mail.add_argument("--width", type=int, default=220)
    lock = sub.add_parser("lock", help="report the git index lock")
    lock.add_argument("--clear-stale", action="store_true",
                      help="remove it only if it is empty, over 5 minutes old, and no git process is running")
    commit = sub.add_parser("commit", help="lock-aware commit authored as a seat")
    commit.add_argument("--as", dest="seat", required=True)
    commit.add_argument("--msg", required=True, help="a commit message file")
    commit.add_argument("paths", nargs="+")
    receipts = sub.add_parser("receipts", help="run Chrome receipts one at a time")
    receipts.add_argument("names", nargs="*", help=f"any of: {', '.join(RECEIPTS)} (default: all)")
    receipts.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)

    if args.cmd == "mail":
        return cmd_mail(args)
    if args.cmd == "lock":
        print(clear_stale_lock() if args.clear_stale else lock_state())
        return 0
    if args.cmd == "commit":
        return cmd_commit(args)
    return cmd_receipts(args)


if __name__ == "__main__":
    sys.exit(main())
