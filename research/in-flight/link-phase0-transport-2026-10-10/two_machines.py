"""Two fleets on two physical machines, on two networks: this machine (`host`) and a GitHub Actions
runner (`far`, .github/workflows/link-two-machines.yml). They meet the way two people's fleets do:
the far side joins by invite code over the internet, through whatever path iroh finds (n0 address
lookup, n0 relays, a direct path where both NATs allow it). Nothing is forced.

    host:  python3 two_machines.py host <aurora-linkd> <scratch dir>
           prints the invite code, then waits for the far fleet.
    far:   python3 two_machines.py far <aurora-linkd> <scratch dir> <invite code>

The code is single-use and expires in 30 minutes. The host sends a question with a 256 KiB file
whose sha256 it names in the message; the far side checks the file, replies with its own file and
its own network facts, and waits for the host's acknowledgement. Each side prints a JSON report.
"""

import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc import call  # sibling helper, imported after the path is set

ROLE, BIN, ROOT = sys.argv[1], os.path.abspath(sys.argv[2]), Path(sys.argv[3]).resolve()
LINK = "two-machines"


def step(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def start(name: str) -> tuple[subprocess.Popen, str]:
    home = ROOT / name
    home.mkdir(parents=True, exist_ok=True)
    log = (ROOT / f"{name}.log").open("a")  # noqa: SIM115  # held for the daemon's lifetime
    p = subprocess.Popen([BIN, "--home", str(home), "serve", "--no-mdns"], stdout=log, stderr=log)
    addr = home / "state" / "link" / "linkd.addr"
    while not addr.exists():
        time.sleep(0.1)
    time.sleep(0.3)
    return p, addr.read_text(encoding="utf-8").strip()


def wait_net(s: str) -> dict:
    for _ in range(600):
        try:
            st = call(s, "net.status")
            if st.get("relay") or st.get("addrs"):
                return st
        except RuntimeError:
            pass
        time.sleep(0.2)
    raise SystemExit("the daemon's network did not come up")


def wait_event(s: str, pred, what: str, t: float = 1800) -> dict:
    step(f"waiting: {what}")
    end = time.time() + t
    while time.time() < end:
        for e in call(s, "events.wait", timeout_ms=2000)["events"]:
            if pred(e):
                return e
    raise SystemExit(f"timed out: {what}")


def fetch(s: str, rid: str, name: str, out: Path) -> str:
    for _ in range(180):
        try:
            call(s, "blob.get", link=LINK, record_id=rid, blob=name, out=str(out))
            return hashlib.sha256(out.read_bytes()).hexdigest()
        except RuntimeError:
            time.sleep(1)
    raise SystemExit(f"blob {name} never arrived")


def where() -> dict:
    return {"hostname": socket.gethostname(), "platform": platform.platform(), "machine": platform.machine()}


def host() -> dict:
    p, s = start("host")
    try:
        call(s, "identity.init", label="fleet-home")
        net = wait_net(s)
        call(s, "link.create", name=LINK)
        code = call(s, "link.invite", link=LINK, role="writer", ttl_s=1800, single_use=True)["code"]
        print(code, flush=True)  # stdout carries only the code; the report goes to the report file
        att = ROOT / "from-host.bin"
        att.write_bytes(os.urandom(256 * 1024))
        sha = hashlib.sha256(att.read_bytes()).hexdigest()
        call(
            s,
            "link.send",
            link=LINK,
            body={"kind": "question", "seat": "claude", "to": "@fleet-far/codex", "content": f"sha256 {sha}"},
            attachments=[{"path": str(att), "name": "from-host.bin"}],
        )
        t0 = time.time()
        reply = wait_event(s, lambda e: e["body"].get("kind") == "reply", "the far fleet's reply")
        far = json.loads(reply["body"]["content"])
        got = fetch(s, reply["record_id"], "from-far.bin", ROOT / "got-from-far.bin")
        call(s, "link.send", link=LINK, body={"kind": "note", "seat": "claude", "to": "@fleet-far", "content": "ack"})
        time.sleep(15)  # let the ack reach the far side before this daemon stops
        return {
            "host": where(),
            "host_net": {"relay": net.get("relay"), "addrs": net.get("addrs")},
            "far": far,
            "far_fleet": reply["fleet"],
            "far_file_intact": got == far["sha256_sent"],
            "host_file_intact_at_far": far["host_file_intact"],
            "reply_after_s": round(time.time() - t0, 1),
            "status": call(s, "link.status", link=LINK),
            "sessions": call(s, "net.status").get("sessions"),
        }
    finally:
        p.terminate()


def far(code: str) -> dict:
    p, s = start("far")
    try:
        call(s, "identity.init", label="fleet-far")
        net = wait_net(s)
        t0 = time.time()
        j = call(s, "link.join", code=code, label="fleet-far")
        join_s = round(time.time() - t0, 2)
        q = wait_event(s, lambda e: e["body"].get("kind") == "question", "the host's question")
        want = q["body"]["content"].split()[-1]
        got = fetch(s, q["record_id"], "from-host.bin", ROOT / "got-from-host.bin")
        att = ROOT / "from-far.bin"
        att.write_bytes(os.urandom(256 * 1024))
        sha = hashlib.sha256(att.read_bytes()).hexdigest()
        report = {
            "where": where(),
            "relay": net.get("relay"),
            "addrs": net.get("addrs"),
            "join_s": join_s,
            "fingerprint_matches_code": j.get("fingerprint_matches_code"),
            "host_fleet": q["fleet"],
            "host_file_intact": got == want,
            "sha256_sent": sha,
        }
        call(
            s,
            "link.send",
            link=LINK,
            body={"kind": "reply", "seat": "codex", "to": "@fleet-home/claude", "content": json.dumps(report)},
            attachments=[{"path": str(att), "name": "from-far.bin"}],
        )
        ack = wait_event(s, lambda e: e["body"].get("content") == "ack", "the host's ack")
        report["ack_from"] = ack["fleet"]
        report["sessions"] = call(s, "net.status").get("sessions")
        return report
    finally:
        p.terminate()


if __name__ == "__main__":
    shutil.rmtree(ROOT, ignore_errors=True)
    ROOT.mkdir(parents=True)
    out = host() if ROLE == "host" else far(sys.argv[4])
    (ROOT / "report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1), file=sys.stderr)
    ok = out.get("far_file_intact") and out.get("host_file_intact_at_far") if ROLE == "host" else out.get("ack_from")
    sys.exit(0 if ok else 1)
