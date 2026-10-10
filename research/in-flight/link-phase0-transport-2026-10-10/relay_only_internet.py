"""Two daemons with no IP transports: they can meet only through n0's public relays (internet)."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call

BIN, ROOT = sys.argv[1], sys.argv[2]
shutil.rmtree(ROOT, ignore_errors=True)
procs = {}


def start(name):
    home = f"{ROOT}/{name}"
    os.makedirs(home, exist_ok=True)
    log = open(f"{ROOT}/{name}.log", "a")  # noqa: SIM115  # held for the daemon's lifetime
    procs[name] = subprocess.Popen([BIN, "--home", home, "serve", "--relay-only", "--no-mdns"], stdout=log, stderr=log)
    addr = f"{home}/state/link/linkd.addr"
    while not os.path.exists(addr):
        time.sleep(0.1)
    time.sleep(0.3)
    return open(addr).read().strip()


def wait_net(s):
    for _ in range(300):
        try:
            st = call(s, "net.status")
            if st["relay"]:
                return st
        except RuntimeError:
            pass
        time.sleep(0.2)
    raise SystemExit("no relay connection")


def wait_events(s, n, t=120):
    end = time.time() + t
    while time.time() < end:
        ev = call(s, "events.wait", timeout_ms=2000)["events"]
        if len(ev) >= n:
            return ev
    raise SystemExit("timed out waiting for events")


out = {}
try:
    A = start("a")
    B = start("b")
    call(A, "identity.init", label="fleet-a")
    call(B, "identity.init", label="fleet-b")
    sa, sb = wait_net(A), wait_net(B)
    out["a_net"] = {"relay": sa["relay"], "ip_addrs": sa["addrs"]}
    out["b_net"] = {"relay": sb["relay"], "ip_addrs": sb["addrs"]}
    call(A, "link.create", name="partners")
    code = call(A, "link.invite", link="partners")["code"]
    t = time.time()
    j = call(B, "link.join", code=code, label="fleet-b")
    out["join_s"] = round(time.time() - t, 2)
    out["fingerprint_matches_code"] = j["fingerprint_matches_code"]
    t = time.time()
    call(
        A,
        "link.send",
        link="partners",
        body={"kind": "question", "seat": "claude", "to": "@fleet-b/codex", "content": "over the internet relay?"},
    )
    ev = wait_events(B, 1)
    out["a_to_b_s"] = round(time.time() - t, 2)
    out["b_got"] = ev[0]["body"]["content"]
    Path(f"{ROOT}/att.bin").write_bytes(os.urandom(1 << 20))
    t = time.time()
    r = call(
        B,
        "link.send",
        link="partners",
        body={"kind": "reply", "seat": "codex", "to": "@fleet-a/claude", "content": "yes, with 1 MiB attached"},
        attachments=[{"path": f"{ROOT}/att.bin", "name": "att.bin"}],
    )
    ev = wait_events(A, 1)
    out["b_to_a_s"] = round(time.time() - t, 2)
    t = time.time()
    for _ in range(60):
        try:
            call(A, "blob.get", link="partners", record_id=ev[0]["record_id"], blob="att.bin", out=f"{ROOT}/got.bin")
            break
        except RuntimeError:
            time.sleep(1)
    out["blob_1MiB_s"] = round(time.time() - t, 2)
    out["blob_intact"] = Path(f"{ROOT}/got.bin").read_bytes() == Path(f"{ROOT}/att.bin").read_bytes()
    # Partition: B goes down, A writes, B comes back and catches up through the relay.
    procs["b"].terminate()
    procs["b"].wait(10)
    call(
        A,
        "link.send",
        link="partners",
        body={"kind": "note", "seat": "claude", "to": "@fleet-b", "content": "while you were away"},
    )
    B = start("b")
    wait_net(B)
    t = time.time()
    ev = wait_events(B, 2)
    out["catch_up_after_restart_s"] = round(time.time() - t, 2)
    out["b_now_has"] = [e["body"]["content"] for e in ev]
    out["sessions_a"] = call(A, "net.status")["sessions"]
    print(json.dumps(out, indent=1))
finally:
    for p in procs.values():
        p.terminate()
