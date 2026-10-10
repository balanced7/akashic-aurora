"""Fleet links end to end (RFC #70, Phases 1-5): real aurora-linkd processes on loopback.

Each fleet is its own data root and secrets folder; daemons bind 127.0.0.1 with no n0 DNS, no
relays and no mDNS, so nothing leaves the machine. The quarantine goes to fakeredis and promotion
to a stub bus, so the live bus is never touched.

Skipped when no aurora-linkd binary is built (`cargo build -p aurora-linkd`); CI's rust job builds
it and runs this file.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.link import client as lc  # noqa: E402  # sys.path bootstrap
from core.link import promote, quarantine  # noqa: E402  # sys.path bootstrap

BINARY = lc.find_linkd()
pytestmark = pytest.mark.skipif(BINARY is None, reason="aurora-linkd is not built")

NET_FLAGS = ["--no-n0", "--no-relay", "--no-mdns", "--bind", "127.0.0.1:0"]


class Fleet:
    """One fleet: a data root, a secrets folder, and (while up) a daemon."""

    def __init__(self, base: Path, name: str):
        self.name = name
        self.home = base / name
        self.secrets = base / name / ".secrets"
        self.home.mkdir(parents=True)
        self.proc: subprocess.Popen | None = None

    def up(self, *, mailbox: bool = False) -> "Fleet":
        extra = NET_FLAGS + (["--mailbox"] if mailbox else [])
        args = lc.spawn_args(
            str(BINARY), self.home, stdio=False, socket_=True, offline=False, extra=extra, secrets=self.secrets
        )
        env = {**os.environ, "AURORA_LINKD_BLOB_POLL_S": "1"}
        log = open(self.home / "linkd.log", "ab")  # noqa: SIM115  # kept for the daemon's lifetime
        self.proc = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=log)
        deadline = time.time() + 20
        while time.time() < deadline:
            if lc.running_addr(self.home):
                return self
            time.sleep(0.1)
        raise AssertionError(f"{self.name}'s daemon did not come up")

    def down(self) -> None:
        if self.proc:
            self.proc.terminate()
            self.proc.wait(10)
            self.proc = None

    def call(self, method: str, **params):
        with lc.connect(
            home=self.home, secrets=self.secrets, network=method == "link.join" and "acl" not in params
        ) as c:
            return c.call(method, **params)

    def wait_net(self) -> None:
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                self.call("net.status")
                return
            except lc.LinkRpcError:
                time.sleep(0.2)
        raise AssertionError(f"{self.name}'s network did not start")

    def events(self) -> list:
        return self.call("events.wait", cursors={}, limit=1000)["events"]

    def record_ids(self, link: str) -> set:
        return {r["ct_hash"] for r in self.call("bundle.export", link=link)["records"]}


@pytest.fixture
def fleets(tmp_path):
    made: list[Fleet] = []

    def make(name: str) -> Fleet:
        f = Fleet(tmp_path, name)
        made.append(f)
        return f

    yield make
    for f in made:
        f.down()


def introduce(*fs: Fleet) -> None:
    """Exchange loopback dial hints (n0 DNS and mDNS are off in these tests), then dial now."""
    for f in fs:
        f.wait_net()
    for f in fs:
        st = f.call("net.status")
        addrs = [x for x in st["addrs"] if x.startswith("127.0.0.1:")]
        for g in fs:
            if g is not f:
                g.call("peers.add", device=st["endpoint"], addrs=addrs)
    for f in fs:
        f.call("sync.now")


def wait_for(pred, timeout=30.0, what="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for {what}")


def link_two(a: Fleet, b: Fleet, *, role: str = "writer") -> str:
    """A creates `partners`, B joins it over the network. Both must be up."""
    a.call("identity.init", label=a.name)
    b.call("identity.init", label=b.name)
    a.wait_net()
    b.wait_net()
    link = a.call("link.create", name="partners")["link"]
    code = a.call("link.invite", link="partners", role=role)["code"]
    joined = b.call("link.join", code=code, label=b.name)
    assert joined["fingerprint_matches_code"]
    assert joined["has_key"]
    return link


def offline_join(a: Fleet, b: Fleet, link: str, *, role: str) -> None:
    """B joins A's link through files only: the two daemons never run at the same time."""
    inv = a.call("link.invite", link=link, role=role)
    out = b.call("link.join", code=inv["code"], label=b.name, acl=inv["acl"])
    a.call("bundle.import", bundle=out["bundle"])  # A admits it (and wraps the key: no approval)
    b.call("bundle.import", bundle=a.call("bundle.export", link=link, records=False))


# ---------------------------------------------------------------------------------------- phase 1


def test_identity_create_invite_join_verify_and_status(fleets):
    a, b = fleets("fleet-a").up(), fleets("fleet-b").up()
    link = link_two(a, b)
    sa = a.call("link.verify", link=link)
    sb = b.call("link.verify", link=link)
    assert sa[0]["safety_number"] == sb[0]["safety_number"], "both sides compute the same safety number"
    a.call("link.verify", link=link, mark=True)
    status = a.call("link.status", link=link)
    them = next(m for m in status["members"] if not m["us"])
    assert them["label"] == "fleet-b"
    assert them["role"] == "writer"
    assert them["verified"]
    c = fleets("fleet-c").up()
    c.call("identity.init", label="fleet-c")
    sc = c.call("link.create", name="other")
    assert sc["fingerprint"] != status["members"][0]["fingerprint"]


def test_the_recovery_phrase_re_derives_the_same_root(fleets):
    a = fleets("a").up()
    first = a.call("identity.init", label="a")
    a.down()
    second_home = fleets("a-again").up()
    again = second_home.call("identity.init", label="a-laptop", phrase=first["phrase"])
    assert again["root"] == first["root"]
    assert again["device"] != first["device"]
    assert again["phrase"] is None, "a phrase that was given is never echoed back"


def test_removing_a_member_rotates_the_key(fleets):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    out = a.call("link.remove_member", link=link, member="b")
    assert out["epoch"] == 1
    a.call("link.send", link=link, body={"kind": "note", "seat": "claude", "to": "@b", "content": "after removal"})
    time.sleep(2)
    assert all(e["body"].get("content") != "after removal" for e in b.events())


# ------------------------------------------------------------------------------------ phases 2, 3


def test_mail_is_quarantined_then_promoted_once(fleets):
    import fakeredis

    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    b.call(
        "link.send", link=link, body={"kind": "question", "seat": "codex", "to": "@a/claude", "content": "playbook?"}
    )
    wait_for(lambda: a.events(), what="A to admit B's record")
    r = fakeredis.FakeRedis(decode_responses=True)
    with lc.connect(home=a.home, secrets=a.secrets) as c:
        events = quarantine.pump_once(c, timeout_ms=100, r=r, home=a.home)
        assert [e["body"]["content"] for e in events] == ["playbook?"]
        keys = set(r.keys("*"))
        assert keys == {quarantine.stream_key(link)}, f"quarantine only, never an inbox or broadcast: {keys}"
        sent = []

        class StubBus:
            def send(self, to, kind, text, meta=None):
                sent.append((to, kind, text, meta))
                return "1-0"

        rid = events[0]["record_id"]
        first = promote.promote(c, link, rid, by="person:test", bus=StubBus())
        again = promote.promote(c, link, rid, by="person:test", bus=StubBus())
    assert first["promoted"]
    assert first["seat"] == "claude"
    assert not again["promoted"], "promotion is idempotent by record id"
    assert len(sent) == 1
    to, kind, text, meta = sent[0]
    assert (to, kind, text) == ("claude", "question", "[remote b/codex] playbook?")
    assert meta["authority"] == "none"
    assert meta["fleet"] == "b"
    assert meta["record_id"] == rid


def test_control_kinds_are_refused_at_write(fleets):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    for kind in ("halt", "nudge", "steer", "ack"):
        with pytest.raises(lc.LinkRpcError):
            a.call("link.send", link=link, body={"kind": kind, "seat": "claude", "to": "@b", "content": "x"})


def test_partitioned_fleets_converge(fleets):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    b.down()
    for i in range(3):
        a.call("link.send", link=link, body={"kind": "chat", "seat": "claude", "to": "@b", "content": f"a{i}"})
        b.call(
            "link.send", link=link, body={"kind": "chat", "seat": "codex", "to": "@a", "content": f"b{i}"}
        )  # offline one-shot
    b.up()
    wait_for(lambda: a.record_ids(link) == b.record_ids(link) and len(a.record_ids(link)) >= 6, what="convergence")
    got_b = sorted(e["body"]["content"] for e in b.events())
    assert got_b == ["a0", "a1", "a2"], "no duplicates, no loss"


def test_attachments_travel_as_verified_blobs(fleets, tmp_path):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    f = tmp_path / "playbook.md"
    f.write_text("# steps\n1. breathe\n", encoding="utf-8")
    a.call(
        "link.send",
        link=link,
        body={"kind": "handoff", "seat": "claude", "to": "@b/codex", "content": "see attached"},
        attachments=[{"path": str(f), "name": "playbook.md"}],
    )
    wait_for(lambda: b.events(), what="the record")
    rid = b.events()[0]["record_id"]
    out = tmp_path / "got.md"
    wait_for(lambda: _try_blob(b, link, rid, out), what="the blob")
    assert out.read_text(encoding="utf-8") == "# steps\n1. breathe\n"


def _try_blob(f: Fleet, link: str, rid: str, out: Path, name: str = "playbook.md") -> bool:
    try:
        f.call("blob.get", link=link, record_id=rid, blob=name, out=str(out))
        return True
    except lc.LinkRpcError:
        return False


def test_a_used_invite_is_refused_and_logged(fleets):
    a, b, c = fleets("a").up(), fleets("b").up(), fleets("c").up()
    a.call("identity.init", label="a")
    b.call("identity.init", label="b")
    c.call("identity.init", label="c")
    for f in (a, b, c):
        f.wait_net()
    a.call("link.create", name="p")
    code = a.call("link.invite", link="p", role="writer")["code"]
    b.call("link.join", code=code, label="b")
    with pytest.raises(lc.LinkRpcError) as e:
        c.call("link.join", code=code, label="c")
    assert "refused" in e.value.message
    log = (a.home / "state" / "logs" / "linkd-refusals.log").read_text(encoding="utf-8")
    assert "join" in log, "the real reason is logged locally; the wire only got the uniform close"


# ---------------------------------------------------------------------------------------- phase 5


def test_a_mailbox_carries_mail_and_blobs_between_fleets_never_online_together(fleets, tmp_path):
    a, m = fleets("a").up(), fleets("mailbox").up(mailbox=True)
    a.call("identity.init", label="a")
    m.call("identity.init", label="mailbox")
    a.wait_net()
    m.wait_net()
    link = a.call("link.create", name="p")["link"]
    code = a.call("link.invite", link="p", role="mailbox")["code"]
    m.call("link.join", code=code, label="mailbox")
    b = fleets("b")  # B is offline throughout A's sessions
    b.call("identity.init", label="b")
    offline_join(a, b, link, role="writer")
    note = tmp_path / "note.txt"
    note.write_text("for b only", encoding="utf-8")
    a.call(
        "link.send",
        link=link,
        body={"kind": "note", "seat": "claude", "to": "@b/codex", "content": "via the mailbox"},
        attachments=[{"path": str(note), "name": "note.txt"}],
    )
    wait_for(lambda: len(m.record_ids(link)) >= 1, what="the mailbox to hold A's record")
    time.sleep(3)  # let the mailbox fetch the blob too
    a.down()
    b.up()
    introduce(b, m)
    wait_for(lambda: b.events(), what="B to receive through the mailbox")
    ev = b.events()[0]
    assert ev["body"]["content"] == "via the mailbox"
    assert ev["fleet"] == "a"
    out = tmp_path / "got.txt"
    wait_for(lambda: _try_blob(b, link, ev["record_id"], out, "note.txt"), what="the blob via the mailbox")
    assert out.read_text(encoding="utf-8") == "for b only"
    b.call("link.send", link=link, body={"kind": "reply", "seat": "codex", "to": "@a/claude", "content": "got it"})
    wait_for(lambda: len(m.record_ids(link)) >= 2, what="the mailbox to hold B's reply")
    b.down()
    a.up()
    introduce(a, m)
    wait_for(lambda: any(e["body"].get("content") == "got it" for e in a.events()), what="A to get the reply")
    status = m.call("link.status", link=link)
    assert status["my_role"] == "mailbox"
    assert m.events() == [], "a mailbox admits nothing it could read: it holds no key"


def test_a_third_fleet_relays_between_two_that_never_meet(fleets):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    c = fleets("c")
    c.call("identity.init", label="c")
    offline_join(a, c, link, role="writer")
    b.call("bundle.import", bundle=a.call("bundle.export", link=link, records=False))
    a.call("link.send", link=link, body={"kind": "note", "seat": "claude", "to": "@c", "content": "a to c"})
    wait_for(lambda: any(e["body"].get("content") == "a to c" for e in b.events()), what="B to hold A's mail")
    a.down()
    c.up()
    introduce(b, c)
    wait_for(lambda: any(e["body"].get("content") == "a to c" for e in c.events()), what="C to receive A's mail via B")
    assert next(e for e in c.events() if e["body"]["content"] == "a to c")["fleet"] == "a"


def test_retention_keeps_headers(fleets):
    a, b = fleets("a").up(), fleets("b").up()
    link = link_two(a, b)
    a.call("link.send", link=link, body={"kind": "chat", "seat": "claude", "to": "@b", "content": "x"})
    wait_for(lambda: b.events(), what="delivery")
    out = b.call("housekeeping")
    assert out["retired"] == 0, "nothing is past a 90-day retention yet"


# --------------------------------------------------------------------------------- supervision


def test_the_daemon_restarts_under_managed_child(tmp_path):
    from scripts.bifrost_child import ManagedChild

    home, secrets = tmp_path / "h", tmp_path / "h" / ".secrets"
    home.mkdir()
    args = lc.spawn_args(str(BINARY), home, stdio=True, socket_=True, offline=True, secrets=secrets)
    child = ManagedChild(args, stdio_rpc=True, breaker_window_s=60, breaker_max=5)
    child.spawn()
    try:
        first = child.pid
        assert first is not None
        wait_for(lambda: lc.running_addr(home) is not None, what="the first daemon")
        os.kill(first, 9)
        wait_for(lambda: child.poll() is not None or not child.alive, timeout=10, what="the crash to be seen")
        wait_for(lambda: child.poll() is None and child.alive and child.pid != first, timeout=20, what="a restart")
        pipes = child.rpc_pipes
        assert pipes is not None
        reader, writer = pipes
        import io

        c = lc.Client(io.BufferedReader(reader), writer)
        assert c.call("daemon.status")["pid"] == child.pid
    finally:
        child.terminate()


def test_the_cli_reports_a_missing_daemon_package(monkeypatch, capsys):
    from types import SimpleNamespace

    from core.link import cli

    monkeypatch.setattr(lc, "find_linkd", lambda: None)
    monkeypatch.setattr(lc, "running_addr", lambda home=None: None)
    rc = cli.main(SimpleNamespace(action="list", args=[], json=False))
    assert rc == 2
    assert "akashic-aurora-linkd" in capsys.readouterr().out


def test_bundle_round_trip_is_verified(fleets, tmp_path):
    a = fleets("a").up()
    a.call("identity.init", label="a")
    link = a.call("link.create", name="p")["link"]
    a.call("link.send", link=link, body={"kind": "chat", "seat": "claude", "to": "@x", "content": "hi"})
    bundle = a.call("bundle.export", link=link)
    bundle["records"][0]["seq"] = 7  # tampered in transit
    out = a.call("bundle.import", bundle=json.loads(json.dumps(bundle)))
    assert out["records_stored"] == 0
