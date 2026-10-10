"""Three fleets on three network stacks: the host (A), and two containers (B, mailbox M), each behind
its own Docker NAT on its own bridge network, which Docker isolates from the other.

A and B are never online together after B joins: mail and a file go A -> M -> B and back through
the mailbox, which runs in its own container and holds no read key. Nothing is forced: the
daemons use their defaults (n0 address lookup, n0 relays, direct paths where NAT allows).

    python3 three_networks_docker.py <path to a release aurora-linkd> [scratch dir]

Needs Docker and internet access (n0's relays and DNS). The binary must run on debian:latest.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))
from rpc import call  # noqa: E402  # sibling helper

from core.link.client import Client  # noqa: E402  # the repo's own RPC client

BIN = os.path.abspath(sys.argv[1])
ROOT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/lk3"
IMAGE = "aurora-linkd-test:local"
procs: dict[str, subprocess.Popen] = {}
clients: dict[str, Client] = {}


def sh(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def build_image() -> None:
    with tempfile.TemporaryDirectory() as ctx:
        shutil.copy(BIN, Path(ctx, "aurora-linkd"))
        Path(ctx, "Dockerfile").write_text(
            "FROM debian:latest\nCOPY aurora-linkd /usr/local/bin/aurora-linkd\n", encoding="utf-8"
        )
        sh("docker", "build", "-q", "-t", IMAGE, ctx)


class Host:
    """A daemon on this machine, reached over its socket."""

    def __init__(self, name: str):
        self.name = name

    def up(self) -> "Host":
        home = Path(ROOT, self.name)
        home.mkdir(parents=True, exist_ok=True)
        (home / "state" / "link" / "linkd.addr").unlink(missing_ok=True)
        log = Path(ROOT, f"{self.name}.log").open("a")  # noqa: SIM115  # held for the daemon's lifetime
        procs[self.name] = subprocess.Popen([BIN, "--home", str(home), "serve", "--no-mdns"], stdout=log, stderr=log)
        path = home / "state" / "link" / "linkd.addr"
        while not path.exists():
            time.sleep(0.1)
        time.sleep(0.3)
        self.addr = path.read_text(encoding="utf-8").strip()
        return self

    def call(self, method: str, **params):
        return call(self.addr, method, **params)

    def down(self) -> None:
        procs[self.name].terminate()
        procs[self.name].wait(10)


class Container:
    """A daemon in its own container, on its own Docker network, reached over stdio."""

    def __init__(self, name: str, mailbox: bool = False):
        self.name, self.mailbox = name, mailbox
        subprocess.run(["docker", "network", "create", f"lk-net-{name}"], capture_output=True, check=False)

    def up(self) -> "Container":
        args = [
            "docker",
            "run",
            "-i",
            "--rm",
            "--name",
            f"lk-{self.name}",
            "--network",
            f"lk-net-{self.name}",
            "-v",
            f"lk-{self.name}-data:/data",
            IMAGE,
            "aurora-linkd",
            "--home",
            "/data",
            "serve",
            "--stdio",
            "--no-socket",
            "--no-mdns",
        ]
        if self.mailbox:
            args.append("--mailbox")
        log = Path(ROOT, f"{self.name}.log").open("a")  # noqa: SIM115  # held for the daemon's lifetime
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
        procs[self.name] = p
        self.client = Client(p.stdout, p.stdin)
        return self

    def call(self, method: str, **params):
        return self.client.call(method, **params)

    def down(self) -> None:
        subprocess.run(["docker", "stop", "-t", "3", f"lk-{self.name}"], capture_output=True, check=False)
        procs[self.name].wait(15)


def wait_net(d) -> dict:
    for _ in range(300):
        try:
            return d.call("net.status")
        except Exception:  # noqa: BLE001  # not up yet
            time.sleep(0.2)
    raise SystemExit(f"{d.name}: network did not start")


def events(d) -> list:
    return d.call("events.wait", timeout_ms=1000)["events"]


def step(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def wait_until(pred, what: str, t: float = 180) -> float:
    step(f"waiting: {what}")
    start = time.time()
    while time.time() - start < t:
        if pred():
            return round(time.time() - start, 2)
        time.sleep(0.5)
    raise SystemExit(f"timed out: {what}")


out: dict = {}
shutil.rmtree(ROOT, ignore_errors=True)
Path(ROOT).mkdir(parents=True)
for n in ("b", "m"):
    subprocess.run(["docker", "volume", "rm", "-f", f"lk-{n}-data"], capture_output=True, check=False)
step("building the image")
build_image()
step("starting a (host), b and m (containers)")
a, b, m = Host("a"), Container("b"), Container("m", mailbox=True)
try:
    a.up(), b.up(), m.up()
    for d, label in ((a, "fleet-a"), (b, "fleet-b"), (m, "mailbox")):
        step(f"identity.init on {d.name}")
        d.call("identity.init", label=label)
    out["b_network"] = sh("docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", "lk-b")
    out["m_network"] = sh("docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", "lk-m")
    for d in (a, b, m):
        step(f"waiting for {d.name}'s network")
        out[f"{d.name}_addrs"] = wait_net(d)["addrs"]
    link = a.call("link.create", name="partners")["link"]
    t = time.time()
    m.call("link.join", code=a.call("link.invite", link="partners", role="mailbox")["code"], label="mailbox")
    out["mailbox_join_s"] = round(time.time() - t, 2)
    t = time.time()
    b.call("link.join", code=a.call("link.invite", link="partners", role="writer")["code"], label="fleet-b")
    out["b_join_s"] = round(time.time() - t, 2)
    wait_until(
        lambda: m.call("link.status", link=link)["acl_entries"] == a.call("link.status", link=link)["acl_entries"],
        "mailbox ACL",
    )

    # B goes offline. A writes, with a file, then leaves: only the mailbox can carry it.
    b.down()
    Path(ROOT, "note.bin").write_bytes(os.urandom(256 * 1024))
    a.call(
        "link.send",
        link=link,
        body={"kind": "handoff", "seat": "claude", "to": "@fleet-b/codex", "content": "via the mailbox, across NATs"},
        attachments=[{"path": f"{ROOT}/note.bin", "name": "note.bin"}],
    )
    out["a_to_mailbox_s"] = wait_until(
        lambda: len(m.call("bundle.export", link=link)["records"]) >= 1, "mailbox to hold A's record"
    )
    time.sleep(20)  # the mailbox's blob fetcher polls every 15 s
    a.down()

    b.up()
    wait_net(b)
    out["mailbox_to_b_s"] = wait_until(
        lambda: any(e["body"].get("content", "").startswith("via the mailbox") for e in events(b)), "B to get A's mail"
    )
    ev = next(e for e in events(b) if e["body"].get("content", "").startswith("via the mailbox"))
    got = None
    for _ in range(90):
        try:
            b.call("blob.get", link=link, record_id=ev["record_id"], blob="note.bin", out="/data/got.bin")
            got = sh("docker", "exec", "lk-b", "sha256sum", "/data/got.bin").split()[0]
            break
        except Exception:  # noqa: BLE001  # still fetching
            time.sleep(1)
    out["file_intact_at_b"] = got == sh("sha256sum", f"{ROOT}/note.bin").split()[0]
    out["provenance_at_b"] = {"fleet": ev["fleet"], "seat_claim": ev["seat_claim"]}
    b.call(
        "link.send",
        link=link,
        body={
            "kind": "reply",
            "seat": "codex",
            "to": "@fleet-a/claude",
            "content": "got it, thanks",
            "reply_to": ev["record_id"],
        },
    )
    out["b_to_mailbox_s"] = wait_until(
        lambda: len(m.call("bundle.export", link=link)["records"]) >= 2, "mailbox to hold B's reply"
    )
    b.down()

    a.up()
    wait_net(a)
    out["mailbox_to_a_s"] = wait_until(
        lambda: any(e["body"].get("content") == "got it, thanks" for e in events(a)), "A to get B's reply"
    )
    out["mailbox_admitted_nothing"] = events(m) == []
    out["mailbox_role"] = m.call("link.status", link=link)["my_role"]
    print(json.dumps(out, indent=1))
finally:
    for d in (b, m):
        d.down() if d.name in procs and procs[d.name].poll() is None else None
        subprocess.run(["docker", "network", "rm", f"lk-net-{d.name}"], capture_output=True, check=False)
    for p in procs.values():
        if p.poll() is None:
            p.terminate()
