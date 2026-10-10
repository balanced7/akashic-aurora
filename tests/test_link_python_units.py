"""Fleet links (RFC #70): the Python half of core/link, pinned without aurora-linkd or aurora_rs.

The daemon is faked at the JSON-RPC boundary, so the real `Client` (framing, contract checks,
errors) carries every call:

- `FakeDaemon` is an in-process reader/writer pair answering each request line from a table;
- `fake_linkd_script()` writes a tiny Python "aurora-linkd" that answers on stdio, so the one-shot
  child of `connect()` and the ManagedChild wiring of `aurora link serve` run for real.

Quarantine and promotion go to fakeredis and a stub bus; every file lands under tmp_path (AI_SETUP).
The CLI verbs are pinned in tests/test_link_cli_units.py, on the same fakes.
"""

from __future__ import annotations

import copy
import io
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, ClassVar

import fakeredis
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.link import client as lc  # noqa: E402  # sys.path bootstrap
from core.link import export, health, panel, promote, quarantine, serve  # noqa: E402  # sys.path bootstrap

LINK = "a" * 64
OTHER_LINK = "b" * 64
OUR_ROOT = "r00t" + "0" * 60
THEIR_ROOT = "f1ee7" + "1" * 59
REC = "c" * 64
ORIG = "d" * 64


# ------------------------------------------------------------------------------------ the fakes


class Refuse(Exception):
    """Raised by a FakeDaemon handler to answer with a JSON-RPC error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class FakeDaemon:
    """A reader/writer pair for `Client`: each written request line is answered from `handlers`
    (a value, or a callable taking the params), and the answer is what the next readline returns."""

    def __init__(self, handlers: dict[str, Any] | None = None):
        self.handlers: dict[str, Any] = dict(handlers or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.lines: list[dict[str, Any]] = []
        self._out: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> int:
        req = json.loads(data.decode("utf-8"))
        self.lines.append(req)
        method, params = req["method"], req["params"]
        self.calls.append((method, params))
        resp: dict[str, Any] = {"jsonrpc": "2.0", "id": req["id"]}
        h = self.handlers.get(method)
        if h is None:
            resp["error"] = {"code": -32601, "message": f"fake has no {method}"}
        else:
            try:
                resp["result"] = h(params) if callable(h) else copy.deepcopy(h)
            except Refuse as e:
                resp["error"] = {"code": e.code, "message": e.message}
        self._out.append((json.dumps(resp) + "\n").encode("utf-8"))
        return len(data)

    def flush(self) -> None:
        pass

    def readline(self) -> bytes:
        return self._out.pop(0) if self._out else b""

    def close(self) -> None:
        self.closed = True

    def client(self) -> lc.Client:
        return lc.Client(self, self, desc="fake")

    def methods(self) -> list[str]:
        return [m for m, _ in self.calls]


def member(label: str, root: str, *, us: bool = False, **kw: Any) -> dict[str, Any]:
    """One member row of link.status, with one device."""
    m: dict[str, Any] = {
        "label": label,
        "root": root,
        "us": us,
        "removed": False,
        "pending": False,
        "verified": True,
        "role": "owner" if us else "writer",
        "devices": [
            {
                "label": f"{label}-pc",
                "device": "e" * 64,
                "head": 3,
                "last_contact": 1_700_000_000,
                "removed": False,
                "frozen": False,
                "cert_expired": False,
            }
        ],
    }
    m.update(kw)
    return m


def status(link: str = LINK, name: str = "ops", members: list[dict[str, Any]] | None = None, **kw: Any):
    """A link.status answer: us (`home`) and one peer fleet (`serge`)."""
    s: dict[str, Any] = {
        "link": link,
        "name": name,
        "epoch": 2,
        "my_role": "owner",
        "acl_entries": 5,
        "rotation_due": False,
        "members": members if members is not None else [member("home", OUR_ROOT, us=True), member("serge", THEIR_ROOT)],
        "pending_joins": [],
        "live_sessions": [],
        "quarantine_unpromoted": 0,
        "sent": [],
        "alarms": [],
        "dropped_acl_entries": [],
    }
    s.update(kw)
    return s


def event(cursor: int, *, link: str = LINK, rid: str | None = None, **body: Any) -> dict[str, Any]:
    """One admitted record as events.wait returns it."""
    b: dict[str, Any] = {"kind": "chat", "seat": "chronos", "to": "@home/claude", "content": f"msg {cursor}"}
    b.update(body)
    return {
        "record_id": rid or f"{cursor:064x}",
        "link": link,
        "link_name": "ops",
        "fleet": "serge",
        "fleet_root": THEIR_ROOT,
        "device": "e" * 64,
        "body": b,
        "received_at": 1_700_000_100,
        "cursor": cursor,
    }


class StubBus:
    """Records what promotion puts on the bus; answers with `mid`."""

    def __init__(self, mid: str | None = "17-0"):
        self.mid = mid
        self.sent: list[tuple[str, str, str, dict[str, Any] | None]] = []

    def send(self, to: str, kind: str, text: str, meta: dict[str, Any] | None = None) -> str | None:
        self.sent.append((to, kind, text, meta))
        return self.mid


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """A throwaway data root: state/link lives under tmp_path."""
    monkeypatch.setenv("AI_SETUP", str(tmp_path))
    monkeypatch.setenv("BIFROST_NAMESPACE", "bifrost")
    return tmp_path


@pytest.fixture
def r() -> Any:
    return fakeredis.FakeRedis(decode_responses=True)


FAKE_LINKD = r"""
import json, os, sys
plan = json.load(open(os.environ["FAKE_LINKD_PLAN"], encoding="utf-8"))
log = open(os.environ["FAKE_LINKD_LOG"], "a", encoding="utf-8")
log.write(json.dumps({"argv": sys.argv[1:]}) + "\n"); log.flush()
for line in sys.stdin:
    req = json.loads(line)
    m = req["method"]
    log.write(json.dumps({"method": m, "params": req["params"]}) + "\n"); log.flush()
    resp = {"jsonrpc": "2.0", "id": req["id"]}
    queue = plan.get(m)
    if queue is None:
        resp["error"] = {"code": -32601, "message": "no " + m}
    else:
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, dict) and "__error__" in item:
            resp["error"] = item["__error__"]
        else:
            resp["result"] = item
    sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()
    if m == "daemon.shutdown":
        sys.exit(0)
"""


def fake_linkd_script(tmp_path: Path, monkeypatch, plan: dict[str, list[Any]]) -> tuple[Path, Path]:
    """An executable stand-in for aurora-linkd answering `plan` (method -> answers, the last one
    repeating) on stdio. Returns (binary, log of argv and calls)."""
    binary = tmp_path / "bin" / "aurora-linkd"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(f"#!{sys.executable}\n{FAKE_LINKD}", encoding="utf-8")
    binary.chmod(0o755)
    plan_file, log = tmp_path / "plan.json", tmp_path / "linkd-calls.jsonl"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setenv("FAKE_LINKD_PLAN", str(plan_file))
    monkeypatch.setenv("FAKE_LINKD_LOG", str(log))
    monkeypatch.setenv("AURORA_LINKD", str(binary))
    return binary, log


def logged(log: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]


# ------------------------------------------------------------------------------------ client.py


def test_client_frames_one_json_request_per_line_and_drops_none_params():
    """A call is one JSON-RPC 2.0 line with a fresh id; None params never leave."""
    d = FakeDaemon({"link.status": {"link": LINK}, "sync.now": {"dialed": 2}})
    c = d.client()
    assert c.call("link.status", link="ops") == {"link": LINK}
    assert c.call("sync.now", link=None) == {"dialed": 2}
    first, second = d.lines[0], d.lines[1]
    assert first["jsonrpc"] == "2.0"
    assert first["method"] == "link.status"
    assert first["params"] == {"link": "ops"}
    assert second["params"] == {}, "a None param is dropped, not sent as null"
    assert second["id"] > first["id"]


def test_client_maps_remote_error_and_closed_channel_to_link_rpc_error():
    """An error answer keeps its code; an empty read is -32003 naming the method."""
    d = FakeDaemon({"identity.status": lambda _p: (_ for _ in ()).throw(Refuse(-32001, "refused: nope"))})
    c = d.client()
    with pytest.raises(lc.LinkRpcError) as e:
        c.call("identity.status")
    assert (e.value.code, e.value.message) == (-32001, "refused: nope")

    class Silent(FakeDaemon):
        def readline(self) -> bytes:
            return b""

    with pytest.raises(lc.LinkRpcError) as e2:
        Silent().client().call("link.list")
    assert e2.value.code == -32003
    assert "link.list" in e2.value.message


def test_client_refuses_off_contract_calls_before_writing_anything():
    """Unknown methods and unknown/missing params fail locally with JSON-RPC codes."""
    d = FakeDaemon()
    c = d.client()
    with pytest.raises(lc.LinkRpcError) as e:
        c.call("link.nuke")
    assert e.value.code == -32601
    with pytest.raises(lc.LinkRpcError) as e2:
        c.call("link.accept", link="ops", joinn="x")
    assert e2.value.code == -32602
    assert "join" in e2.value.message
    assert "joinn" in e2.value.message
    assert d.calls == [], "nothing reached the daemon"


def test_client_close_closes_both_streams_and_runs_the_hook_once_per_close():
    """close() (and the context manager) closes the streams and calls the close hook."""
    hooks: list[int] = []
    d = FakeDaemon()
    with lc.Client(d, d, close_hook=lambda: hooks.append(1), desc="x") as c:
        assert c.desc == "x"
    assert d.closed
    assert hooks == [1]


def test_find_linkd_override_wins_and_a_missing_override_is_none(tmp_path, monkeypatch):
    """$AURORA_LINKD names the binary; pointing it at nothing means links are unavailable."""
    exe = tmp_path / "linkd"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("AURORA_LINKD", str(exe))
    assert lc.find_linkd() == str(exe)
    monkeypatch.setenv("AURORA_LINKD", str(tmp_path / "absent"))
    assert lc.find_linkd() is None


def test_find_linkd_search_order_path_then_beside_python_then_newest_dev_build(tmp_path, monkeypatch):
    """Without an override: PATH, then next to sys.executable, then the newer aurora-rs build."""
    monkeypatch.delenv("AURORA_LINKD", raising=False)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    pybin = tmp_path / "py" / "bin"
    pybin.mkdir(parents=True)
    monkeypatch.setattr(lc.sys, "executable", str(pybin / "python"))
    repo = tmp_path / "repo"
    monkeypatch.setattr(lc, "repo_root", lambda: repo)
    assert lc.find_linkd() is None, "nothing anywhere"

    release = repo / "aurora-rs" / "target" / "release" / "aurora-linkd"
    debug = repo / "aurora-rs" / "target" / "debug" / "aurora-linkd"
    for p in (release, debug):
        p.parent.mkdir(parents=True)
        p.write_text("", encoding="utf-8")
    os.utime(release, (1, 1))
    os.utime(debug, (2, 2))
    assert lc.find_linkd() == str(debug), "the newer dev build wins"

    beside = pybin / "aurora-linkd"
    beside.write_text("", encoding="utf-8")
    assert lc.find_linkd() == str(beside), "the wheel's copy beats a dev build"

    on_path = empty / "aurora-linkd"
    on_path.write_text("", encoding="utf-8")
    on_path.chmod(0o755)
    assert lc.find_linkd() == str(on_path), "PATH beats the wheel's copy"


def test_spawn_args_build_the_daemon_command_line(tmp_path):
    """--home/--secrets precede `serve`; stdio, socket and offline map to their flags."""
    args = lc.spawn_args("linkd", tmp_path, stdio=True, socket_=False, offline=True, secrets=tmp_path / "s")
    assert args == [
        "linkd",
        "--home",
        str(tmp_path),
        "--secrets",
        str(tmp_path / "s"),
        "serve",
        "--stdio",
        "--no-socket",
        "--offline",
    ]
    args2 = lc.spawn_args(
        "linkd", tmp_path, stdio=False, socket_=True, offline=False, extra=["--mailbox"], secrets=tmp_path
    )
    assert args2[-2:] == ["serve", "--mailbox"]


def test_state_dir_follows_the_data_root(home):
    """state/link lives under AI_SETUP unless a home is given."""
    assert lc.state_dir() == home / "state" / "link"
    assert lc.state_dir(home / "x") == home / "x" / "state" / "link"


def test_connect_without_a_daemon_or_binary_raises_linkd_missing(home, monkeypatch):
    """No running socket and no binary: LinkdMissing carrying the install remedy."""
    monkeypatch.setattr(lc, "find_linkd", lambda: None)
    (lc.state_dir(home)).mkdir(parents=True)
    (lc.state_dir(home) / "linkd.addr").write_text(str(home / "no.sock"), encoding="utf-8")
    with pytest.raises(lc.LinkdMissing) as e:
        lc.connect(home=home)
    assert "akashic-aurora-linkd" in str(e.value)
    assert lc.running_addr(home) is None, "a stale address file is not a running daemon"
    assert lc.running_addr(home / "nowhere") is None


def test_connect_spawns_an_offline_one_shot_child_and_reaps_it(home, monkeypatch):
    """Without a running daemon, connect() runs `serve --stdio --no-socket --offline` for the call."""
    _binary, log = fake_linkd_script(home, monkeypatch, {"link.list": [[{"link": LINK}]]})
    with lc.connect(home=home, secrets=home / "sec") as c:
        assert c.desc.startswith("one-shot pid ")
        assert c.call("link.list") == [{"link": LINK}]
    rows = logged(log)
    argv = rows[0]["argv"]
    assert argv[:2] == ["--home", str(home)]
    assert argv[3] == str(home / "sec")
    assert argv[-4:] == ["serve", "--stdio", "--no-socket", "--offline"]
    assert rows[1] == {"method": "link.list", "params": {}}


def test_connect_uses_a_running_daemons_unix_socket(home):
    """When linkd.addr names a live socket, calls go there and no child is spawned."""
    short = Path(tempfile.mkdtemp(prefix="lk"))
    sock_path = str(short / "s")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(4)
    seen: list[str] = []

    def answer() -> None:
        for _ in range(2):  # running_addr's probe, then the real connection
            conn, _a = srv.accept()
            with conn, conn.makefile("rwb", buffering=0) as f:
                line = f.readline()
                if not line:
                    continue
                req = json.loads(line)
                seen.append(req["method"])
                f.write((json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {"up": True}}) + "\n").encode())

    t = threading.Thread(target=answer, daemon=True)
    t.start()
    try:
        lc.state_dir(home).mkdir(parents=True)
        (lc.state_dir(home) / "linkd.addr").write_text(sock_path + "\n", encoding="utf-8")
        assert lc.running_addr(home) == sock_path
        with lc.connect(home=home) as c:
            assert c.desc == f"socket {sock_path}"
            assert c.call("daemon.status") == {"up": True}
        t.join(5)
        assert seen == ["daemon.status"]
    finally:
        srv.close()
        Path(sock_path).unlink(missing_ok=True)
        short.rmdir()


def test_module_call_goes_networked_only_for_network_methods_and_online_joins(monkeypatch):
    """call() asks for a networked child for sync/net methods and a join without a bundle."""
    seen: list[bool] = []
    d = FakeDaemon({"sync.now": {}, "link.join": {"ok": 1}, "link.list": []})

    def fake_connect(*, network: bool = False, home: Path | None = None) -> lc.Client:
        seen.append(network)
        return d.client()

    monkeypatch.setattr(lc, "connect", fake_connect)
    lc.call("sync.now")
    lc.call("link.join", code="aurora-invite1:x")
    lc.call("link.join", code="aurora-invite1:x", acl=[1])
    assert lc.call("link.list") == []
    assert seen == [True, True, False, False]


# -------------------------------------------------------------------------------- quarantine.py


def test_quarantine_fields_take_provenance_from_the_acl_and_carry_no_authority():
    """Stream fields: fleet from the daemon, seat only a claim, blobs as JSON, authority none."""
    e = event(4, reply_to=ORIG, blobs=[{"name": "a.txt", "bytes": 3}])
    f = quarantine.fields(e)
    assert f["fleet"] == "serge"
    assert f["seat_claim"] == "chronos"
    assert f["authority"] == "none"
    assert f["reply_to"] == ORIG
    assert json.loads(f["blobs"]) == [{"name": "a.txt", "bytes": 3}]
    assert f["cursor"] == "4"
    assert f["to"] == "@home/claude"
    bare = quarantine.fields({"link": LINK})
    assert bare["reply_to"] == ""
    assert bare["blobs"] == "[]"
    assert bare["kind"] == ""
    assert all(isinstance(v, str) for v in bare.values())


def test_quarantine_stream_key_follows_the_bus_namespace(monkeypatch):
    """bifrost:remote:<link>, under BIFROST_NAMESPACE or an explicit namespace."""
    monkeypatch.setenv("BIFROST_NAMESPACE", "test")
    assert quarantine.stream_key(LINK) == f"test:remote:{LINK}"
    assert quarantine.stream_key(LINK, "x") == f"x:remote:{LINK}"


def test_admit_queues_on_the_remote_stream_only(home, r):
    """Admitted records land on bifrost:remote:<link>, never on an inbox or broadcast."""
    assert quarantine.admit([event(1), event(2), event(1, link=OTHER_LINK)], r) == 3
    assert r.xlen(quarantine.stream_key(LINK)) == 2
    assert set(r.keys("*")) == {quarantine.stream_key(LINK), quarantine.stream_key(OTHER_LINK)}
    assert quarantine.admit([], r) == 0


def test_admit_with_the_bus_offline_queues_nothing(monkeypatch):
    """No Redis: admit returns 0 (the daemon's store still holds every record)."""
    monkeypatch.setattr(quarantine, "redis_client", lambda: None)
    assert quarantine.admit([event(1)]) == 0


def test_redis_client_fails_soft_to_none(monkeypatch):
    """A Redis that cannot be reached is None, not an exception."""
    import core.foundation.redis_connection as rc

    def boom(**_kw: Any) -> Any:
        raise ConnectionError("down")

    monkeypatch.setattr(rc, "connect_to_redis_with_fail_fast", boom)
    assert quarantine.redis_client() is None


def test_cursors_round_trip_and_a_corrupt_file_reads_as_empty(home):
    """cursors.json survives a restart; garbage in it means start from zero, not a crash."""
    assert quarantine.load_cursors() == {}
    quarantine.save_cursors({LINK: 7})
    assert quarantine.load_cursors() == {LINK: 7}
    assert not quarantine.cursors_path().with_suffix(".tmp").exists(), "written atomically"
    quarantine.cursors_path().write_text("[1, 2]", encoding="utf-8")
    assert quarantine.load_cursors() == {}


def test_pump_once_queues_then_advances_each_links_cursor(home, r):
    """Records past our cursors are queued, then the cursor moves to the highest seen."""
    quarantine.save_cursors({LINK: 1})
    waits: list[dict[str, Any]] = []
    batches = [{"events": [event(2), event(5), event(3, link=OTHER_LINK)]}, {"events": []}]

    def wait(p: dict[str, Any]) -> Any:
        waits.append(p)
        return batches.pop(0)

    c = FakeDaemon({"events.wait": wait}).client()
    got = quarantine.pump_once(c, timeout_ms=10, r=r)
    assert [e["cursor"] for e in got] == [2, 5, 3]
    assert waits[0] == {"cursors": {LINK: 1}, "timeout_ms": 10}
    assert quarantine.load_cursors() == {LINK: 5, OTHER_LINK: 3}
    assert r.xlen(quarantine.stream_key(LINK)) == 2
    assert quarantine.pump_once(c, timeout_ms=10, r=r) == []
    assert quarantine.load_cursors() == {LINK: 5, OTHER_LINK: 3}, "nothing new, nothing moved"


def test_pump_once_with_the_bus_offline_neither_asks_nor_advances(home, monkeypatch):
    """Bus offline: no events.wait call, no cursor change."""
    monkeypatch.setattr(quarantine, "redis_client", lambda: None)
    d = FakeDaemon()
    assert quarantine.pump_once(d.client()) == []
    assert d.calls == []
    assert quarantine.load_cursors() == {}


def test_inbox_reads_the_stream_newest_first(home, r):
    """With the bus up, inbox is the stream, newest first, with stream ids."""
    quarantine.admit([event(1), event(2), event(3)], r)
    c = FakeDaemon({"link.status": status()}).client()
    rows = quarantine.inbox(c, "ops", limit=2, r=r)
    assert [x["cursor"] for x in rows] == ["3", "2"]
    assert all("stream_id" in x for x in rows)


def test_inbox_falls_back_to_the_store_when_the_stream_is_empty(home, r):
    """Empty stream: the store's records of that link only, newest first, limited."""
    evs = {"events": [event(1), event(2, link=OTHER_LINK), event(3), event(4)]}
    d = FakeDaemon({"link.status": status(), "events.wait": evs})
    rows = quarantine.inbox(d.client(), "ops", limit=2, r=r)
    assert [x["cursor"] for x in rows] == ["4", "3"]
    assert d.calls[-1] == ("events.wait", {"cursors": {LINK: 0}, "limit": 1000})


def test_rebuild_replays_the_store_in_batches_and_saves_the_cursor(home, r):
    """rebuild() drops the stream, replays every batch for that link, and stores the cursor."""
    r.xadd(quarantine.stream_key(LINK), {"stale": "1"})
    batches = {0: [event(1), event(2), event(9, link=OTHER_LINK)], 2: [event(3)], 3: []}
    d = FakeDaemon({"link.status": status(), "events.wait": lambda p: {"events": batches[p["cursors"][LINK]]}})
    assert quarantine.rebuild(d.client(), "ops", r) == 3
    rows = r.xrange(quarantine.stream_key(LINK))
    assert [f["cursor"] for _sid, f in rows] == ["1", "2", "3"], "the stale entry is gone"
    assert quarantine.load_cursors()[LINK] == 3


def test_rebuild_refuses_with_the_bus_offline(monkeypatch):
    """No bus: rebuild says so instead of silently doing nothing."""
    monkeypatch.setattr(quarantine, "redis_client", lambda: None)
    with pytest.raises(RuntimeError, match="offline"):
        quarantine.rebuild(FakeDaemon().client(), "ops")


# ----------------------------------------------------------------------------------- promote.py


def write_promote_toml(home: Path, text: str, link: str = LINK) -> None:
    p = promote.policy_dir(link) / "promote.toml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_promote_policy_defaults_to_manual(home):
    """No promote.toml: manual, no rules. The written default is manual too and never overwritten."""
    assert promote.load_policy(LINK) == {"mode": "manual", "rules": []}
    path = promote.write_default_policy(LINK)
    assert promote.load_policy(LINK) == {"mode": "manual", "rules": []}
    path.write_text('mode = "rules"\n', encoding="utf-8")
    promote.write_default_policy(LINK)
    assert path.read_text(encoding="utf-8") == 'mode = "rules"\n', "an existing policy is kept"


def test_promote_policy_malformed_is_manual_and_says_why(home):
    """A broken promote.toml means manual, with the error named."""
    write_promote_toml(home, "mode = [")
    pol = promote.load_policy(LINK)
    assert pol["mode"] == "manual"
    assert pol["rules"] == []
    assert "promote.toml" in pol["error"]


def test_promote_policy_drops_handoff_rules_and_unknown_modes(home):
    """A rule may never promote handoff; an unknown mode reads as manual."""
    write_promote_toml(
        home, 'mode = "rules"\n[[rules]]\nkind = "handoff"\nto = "x"\n[[rules]]\nkind = "reply"\nto = "claude"\n'
    )
    assert promote.load_policy(LINK) == {"mode": "rules", "rules": [{"kind": "reply", "to": "claude"}]}
    write_promote_toml(home, 'mode = "yolo"\n')
    assert promote.load_policy(LINK)["mode"] == "manual"


def test_render_names_the_fleet_seat_and_attachments():
    """Bus text is `[remote fleet/seat] content` plus a blob hint per attachment."""
    rec = event(1, content="hello", blobs=[{"name": "a.log", "bytes": 12}])
    text = promote.render(rec)
    assert text.startswith("[remote serge/chronos] hello")
    assert "a.log (12 bytes)" in text
    assert f"aurora link blob {rec['record_id'][:12]}" in text
    assert "\n" not in promote.render(event(1))


def promotable(rec_status: str = "admitted", promoted: Any = None, first: bool = True, **body: Any) -> FakeDaemon:
    rec = event(1, rid=REC, **body)
    rec.update(status=rec_status, promoted=promoted)
    return FakeDaemon({"link.status": status(), "record.get": rec, "promotion.record": {"first": first}})


def test_promote_puts_one_record_on_the_bus_with_provenance_and_no_authority():
    """An admitted record to @home/<seat> reaches that seat once, data-only, with ACL provenance."""
    d, bus = promotable(), StubBus()
    out = promote.promote(d.client(), "ops", REC, by="person:t", bus=bus)
    assert out == {"promoted": True, "record_id": REC, "seat": "claude", "bus_id": "17-0"}
    to, kind, text, meta = bus.sent[0]
    assert (to, kind) == ("claude", "chat")
    assert text.startswith("[remote serge/chronos]")
    assert meta is not None
    assert meta["authority"] == "none"
    assert meta["verified"] is True
    assert meta["fleet"] == "serge"
    assert meta["idempotency_key"] == f"link:{REC}"
    assert meta["seat_claim"] == "chronos"
    assert ("promotion.record", {"link": LINK, "record_id": REC, "seat": "claude", "by": "person:t"}) in d.calls


def test_promote_refuses_records_that_are_not_admitted():
    """Own or refused records are never promoted."""
    with pytest.raises(promote.PromotionRefused, match="record is own"):
        promote.promote(promotable("own").client(), "ops", REC, by="p", bus=StubBus())


def test_promote_is_idempotent_unless_again():
    """An already-promoted record is not resent; the daemon's `first=false` also stops a resend."""
    bus = StubBus()
    out = promote.promote(promotable(promoted={"seat": "x"}).client(), "ops", REC, by="p", bus=bus)
    assert out == {"promoted": False, "already": {"seat": "x"}, "record_id": REC}
    out2 = promote.promote(promotable(first=False).client(), "ops", REC, by="p", bus=bus)
    assert out2["promoted"] is False
    assert out2["already"] is True
    assert bus.sent == []
    out3 = promote.promote(
        promotable(promoted={"seat": "x"}, first=False).client(), "ops", REC, by="p", again=True, bus=bus
    )
    assert out3["promoted"] is True
    assert len(bus.sent) == 1


def test_promote_needs_a_seat_for_mail_to_the_whole_fleet_or_another_fleet():
    """`@home` or `@other/x` names none of our seats: --to is required."""
    for to in ("@home", "@other/claude", ""):
        with pytest.raises(promote.PromotionRefused, match="say which seat"):
            promote.promote(promotable(to=to).client(), "ops", REC, by="p", bus=StubBus())
    out = promote.promote(promotable(to="@home").client(), "ops", REC, by="p", to="sol", bus=StubBus())
    assert out["seat"] == "sol"


def test_promote_with_the_bus_down_says_rerun_with_again():
    """Recorded but not delivered: the refusal names --again."""
    with pytest.raises(promote.PromotionRefused, match="--again"):
        promote.promote(promotable().client(), "ops", REC, by="p", bus=StubBus(mid=None))


def rules_daemon(orig: dict[str, Any] | None) -> FakeDaemon:
    """A daemon for apply_rules: the incoming record REC, and an original ORIG (or none)."""
    incoming = event(1, rid=REC, kind="reply", reply_to=ORIG, to="@home")
    incoming["status"] = "admitted"

    def get(p: dict[str, Any]) -> Any:
        if p["record_id"] == REC:
            return copy.deepcopy(incoming)
        if orig is None:
            raise Refuse(-32001, "no such record")
        return copy.deepcopy(orig)

    return FakeDaemon({"link.status": status(), "record.get": get, "promotion.record": {"first": True}})


def test_apply_rules_does_nothing_under_the_manual_default(home):
    """No promote.toml: every record waits in quarantine."""
    d, bus = rules_daemon(None), StubBus()
    assert promote.apply_rules(d.client(), [event(1, rid=REC)], bus=bus) == []
    assert bus.sent == []
    assert d.calls == []


def test_apply_rules_promotes_a_matching_kind_to_the_named_seat(home):
    """A `kind = chat, to = claude` rule promotes chat, by rule:chat, and nothing else."""
    write_promote_toml(home, 'mode = "rules"\n[[rules]]\nkind = "chat"\nto = "claude"\n')
    rec = event(1, rid=REC, to="@home")
    rec["status"] = "admitted"
    d = FakeDaemon({"link.status": status(), "record.get": rec, "promotion.record": {"first": True}})
    bus = StubBus()
    done = promote.apply_rules(d.client(), [event(1, rid=REC), event(2, kind="question")], bus=bus)
    assert [x["seat"] for x in done] == ["claude"]
    assert bus.sent[0][3] is not None
    assert bus.sent[0][3]["promoted_by"] == "rule:chat"


REPLY_RULE = 'mode = "rules"\n[[rules]]\nkind = "reply"\nreplies_to_ours = true\nto = "original_sender"\n'


def test_apply_rules_routes_a_reply_to_ours_back_to_the_original_sender(home):
    """A reply to a record our fleet wrote goes to the seat that wrote it."""
    write_promote_toml(home, REPLY_RULE)
    orig = {"status": "own", "fleet_root": OUR_ROOT, "body": {"kind": "question", "seat": "sol"}}
    bus = StubBus()
    incoming = event(1, rid=REC, kind="reply", reply_to=ORIG)
    done = promote.apply_rules(rules_daemon(orig).client(), [incoming], bus=bus)
    assert [x["seat"] for x in done] == ["sol"]
    assert bus.sent[0][0] == "sol"


@pytest.mark.parametrize(
    "orig",
    [
        None,  # the original is unknown to the store
        {"status": "admitted", "fleet_root": THEIR_ROOT, "body": {"kind": "question", "seat": "sol"}},
        {"status": "own", "fleet_root": OUR_ROOT, "body": {"kind": "ack", "seat": "sol"}},
        {"status": "own", "fleet_root": THEIR_ROOT, "body": {"kind": "question", "seat": "sol"}},
    ],
)
def test_apply_rules_never_routes_replies_to_mail_that_is_not_ours(home, orig):
    """Unknown originals, other fleets' mail and acks never satisfy replies_to_ours."""
    write_promote_toml(home, REPLY_RULE)
    bus = StubBus()
    incoming = event(1, rid=REC, kind="reply", reply_to=ORIG)
    assert promote.apply_rules(rules_daemon(orig).client(), [incoming], bus=bus) == []
    assert bus.sent == []


def test_apply_rules_skips_a_reply_rule_without_reply_to_and_swallows_refusals(home):
    """No reply_to: the reply rule does not match; a refused promotion is left in quarantine."""
    write_promote_toml(home, REPLY_RULE + '[[rules]]\nkind = "chat"\nto = "claude"\n')
    bus = StubBus()
    assert promote.apply_rules(rules_daemon(None).client(), [event(1, rid=REC, kind="reply")], bus=bus) == []
    own = event(1, rid=REC)
    own["status"] = "own"
    d = FakeDaemon({"link.status": status(), "record.get": own})
    assert promote.apply_rules(d.client(), [event(1, rid=REC)], bus=bus) == []
    assert bus.sent == []


def test_apply_rules_needs_a_seat_from_the_rule(home):
    """A rule with no `to` (and not original_sender) promotes nothing."""
    write_promote_toml(home, 'mode = "rules"\n[[rules]]\nkind = "chat"\n')
    assert promote.apply_rules(rules_daemon(None).client(), [event(1, rid=REC)], bus=StubBus()) == []


# ------------------------------------------------------------------------------------ export.py


def link_list_daemon(*statuses: dict[str, Any], sent: list[dict[str, Any]] | None = None) -> FakeDaemon:
    rows = [{"link": s["link"], "name": s["name"]} for s in statuses]
    by_id = {s["link"]: s for s in statuses}

    def send(p: dict[str, Any]) -> Any:
        if sent is not None:
            att = p.get("attachments") or []
            sent.append({**p, "attachment_text": [Path(a["path"]).read_text(encoding="utf-8") for a in att]})
        return {"record_id": REC}

    return FakeDaemon({"link.list": rows, "link.status": lambda p: by_id[p["link"]], "link.send": send})


def test_parse_address_accepts_fleet_and_fleet_seat_only():
    """@fleet and @fleet/seat parse; anything else is refused."""
    assert export.parse_address("@serge/chronos") == ("serge", "chronos")
    assert export.parse_address(" @serge ") == ("serge", None)
    assert export.is_remote_address("@serge")
    assert not export.is_remote_address(5)
    with pytest.raises(export.ExportRefused):
        export.parse_address("claude")


def test_export_policy_defaults_filters_and_refuses_a_broken_file(home):
    """Default: every bridge kind, every seat, 8000 chars; unknown kinds drop; a broken file blocks."""
    pol = export.load_policy(LINK)
    assert set(pol["kinds"]) == {"chat", "question", "handoff", "reply", "completion", "blocker", "note"}
    assert pol["seats"] == ["*"]
    assert pol["max_chars"] == 8000
    path = export.write_default_policy(LINK)
    written = export.load_policy(LINK)
    assert set(written["kinds"]) == set(pol["kinds"]), "the written default agrees"
    assert written["seats"] == ["*"]
    path.write_text('kinds = ["chat", "halt"]\nseats = ["claude"]\nmax_chars = 300\n', encoding="utf-8")
    assert export.load_policy(LINK) == {"kinds": ["chat"], "seats": ["claude"], "max_chars": 300}
    export.write_default_policy(LINK)
    assert "halt" in path.read_text(encoding="utf-8"), "an existing policy is never overwritten"
    path.write_text("kinds = [", encoding="utf-8")
    with pytest.raises(export.ExportRefused, match="unreadable"):
        export.load_policy(LINK)


def test_resolve_link_matches_label_or_root_and_skips_us_removed_and_pending():
    """A fleet is found by label, root, or a root prefix of 8+; us/removed/pending never match."""
    members = [
        member("home", OUR_ROOT, us=True),
        member("serge", THEIR_ROOT),
        member("gone", "9" * 64, removed=True),
        member("waiting", "8" * 64, pending=True),
    ]
    d = link_list_daemon(status(members=members))
    assert export.resolve_link(d.client(), "serge") == (LINK, "serge")
    assert export.resolve_link(d.client(), THEIR_ROOT[:8]) == (LINK, "serge")
    for nope in ("home", "gone", "waiting", THEIR_ROOT[:4]):
        with pytest.raises(export.ExportRefused, match="no link here"):
            export.resolve_link(d.client(), nope)


def test_resolve_link_needs_the_link_named_when_a_fleet_shares_two():
    """Two links with the same fleet: ambiguous until the link is named (by name, id or prefix)."""
    d = link_list_daemon(status(), status(link=OTHER_LINK, name="dev"))
    with pytest.raises(export.ExportRefused, match="more than one link"):
        export.resolve_link(d.client(), "serge")
    assert export.resolve_link(d.client(), "serge", "dev") == (OTHER_LINK, "serge")
    assert export.resolve_link(d.client(), "serge", LINK[:6]) == (LINK, "serge")


def test_send_remote_writes_a_redacted_record_addressed_by_the_members_label(home):
    """Content is redacted, addressed `@label/seat`, and reply_to/source come from meta."""
    sent: list[dict[str, Any]] = []
    d = link_list_daemon(status(), sent=sent)
    secret = "sk-" + "A1b2C3d4E5f6G7h8J9k0"
    rid = export.send_remote(
        "claude",
        f"@{THEIR_ROOT[:10]}/chronos",
        "question",
        f"key {secret}",
        {"answers": ORIG, "source_id": "99-0"},
        client=d.client(),
    )
    assert rid == REC
    p = sent[0]
    assert p["link"] == LINK
    assert p["source"] == "99-0"
    assert "attachments" not in p
    body = p["body"]
    assert body["to"] == "@serge/chronos"
    assert body["seat"] == "claude"
    assert body["kind"] == "question"
    assert body["reply_to"] == ORIG
    assert secret not in body["content"]
    assert body["content"].startswith("key ")
    assert not d.closed, "a caller's client is left open"


def test_send_remote_spills_long_text_to_an_attachment_and_cleans_it_up(home):
    """Past max_chars, the full text travels as message.md and the temp file is removed after."""
    path = export.write_default_policy(LINK)
    path.write_text("max_chars = 500\n", encoding="utf-8")
    sent: list[dict[str, Any]] = []
    long = "x" * 1200
    export.send_remote(
        "claude",
        "@serge",
        "chat",
        long,
        {"answers": "not-a-hash"},
        client=link_list_daemon(status(), sent=sent).client(),
    )
    p = sent[0]
    assert p["body"]["to"] == "@serge"
    assert "reply_to" not in p["body"]
    assert "source" not in p
    assert len(p["body"]["content"]) < 500
    assert "1200 chars in all" in p["body"]["content"]
    assert p["attachments"][0]["name"] == "message.md"
    assert p["attachment_text"] == [long]
    assert not Path(p["attachments"][0]["path"]).exists()


def test_send_remote_enforces_export_kinds_and_seats(home):
    """export.toml kinds and seats gate what leaves; nothing is written when refused."""
    export.write_default_policy(LINK).write_text('kinds = ["chat"]\nseats = ["sol"]\n', encoding="utf-8")
    sent: list[dict[str, Any]] = []
    d = link_list_daemon(status(), sent=sent)
    with pytest.raises(export.ExportRefused, match="kind 'handoff'"):
        export.send_remote("sol", "@serge/x", "handoff", "h", client=d.client())
    with pytest.raises(export.ExportRefused, match="seat 'claude'"):
        export.send_remote("claude", "@serge/x", "chat", "h", client=d.client())
    assert sent == []
    export.send_remote("sol", "@serge/x", "chat", None, client=d.client())
    assert sent[0]["body"]["content"] == ""


def test_send_remote_opens_and_closes_its_own_channel(home, monkeypatch):
    """Without a client, send_remote connects itself and closes the channel even on refusal."""
    d = link_list_daemon(status())
    monkeypatch.setattr(export, "connect", d.client)
    assert export.send_remote("claude", "@serge/x", "chat", "hi") == REC
    assert d.closed
    d.closed = False
    with pytest.raises(export.ExportRefused):
        export.send_remote("claude", "@nobody/x", "chat", "hi")
    assert d.closed


# ------------------------------------------------------------------------------------ health.py


def health_daemon(st: dict[str, Any], ident: dict[str, Any] | None = None) -> FakeDaemon:
    return FakeDaemon(
        {
            "identity.status": ident
            or {
                "device": "dev",
                "label": "home",
                "fingerprint": "fp",
                "cert_expires": 1_900_000_000,
                "needs_renewal": False,
            },
            "link.list": [{"link": st["link"], "name": st["name"]}],
            "link.status": st,
        }
    )


def use_links(home: Path) -> None:
    lc.state_dir().mkdir(parents=True, exist_ok=True)
    (lc.state_dir() / f"{LINK}.db").write_bytes(b"")


def test_health_is_quiet_when_links_are_not_in_use(home, monkeypatch):
    """No binary and no store: nothing in use, no problems, and render() prints nothing."""
    monkeypatch.setattr(health, "find_linkd", lambda: None)
    h = health.health()
    assert h == {"in_use": False, "available": False, "running": False, "links": [], "problems": []}
    assert health.render(h) == []
    monkeypatch.setattr(health, "find_linkd", lambda: "/bin/linkd")
    monkeypatch.setattr(health, "running_addr", lambda: "/s")
    h2 = health.health()
    assert h2["available"]
    assert h2["running"]
    assert not h2["in_use"]
    assert h2["problems"] == []


def test_health_with_stores_but_no_binary_names_the_install(home, monkeypatch):
    """Links on disk but no daemon: the one problem is the install remedy."""
    use_links(home)
    monkeypatch.setattr(health, "find_linkd", lambda: None)
    h = health.health()
    assert h["in_use"]
    assert h["problems"] == [lc.MISSING]
    lines = health.render(h)
    assert lines[0].startswith("## LINKS")
    assert "(not installed)" in lines[1]
    assert lines[-1] == f"  ! {lc.MISSING}"


def test_health_reports_every_problem_with_its_remedy(home, monkeypatch):
    """Renewal, alarms, unverified members, rotation, pending approvals and no serve are named."""
    use_links(home)
    st = status(
        rotation_due=True,
        quarantine_unpromoted=4,
        alarms=[{"kind": "fork", "author": "f" * 64, "detail": "two heads"}],
        pending_joins=[
            {"join": "1" * 64, "label": "newbie", "needs_approval": True},
            {"join": "2" * 64, "label": "x", "needs_approval": False},
        ],
        members=[
            member("home", OUR_ROOT, us=True, verified=False),
            member("serge", THEIR_ROOT, verified=False),
            member("old", "7" * 64, removed=True, verified=False),
        ],
    )
    ident = {"device": "d", "label": "home", "fingerprint": "fp", "cert_expires": 1_900_000_000, "needs_renewal": True}
    d = health_daemon(st, ident)
    monkeypatch.setattr(health, "find_linkd", lambda: "/bin/linkd")
    monkeypatch.setattr(health, "running_addr", lambda: None)
    monkeypatch.setattr(health, "connect", d.client)
    h = health.health()
    assert h["identity"]["needs_renewal"] is True
    assert h["links"] == [
        {
            "name": "ops",
            "link": LINK,
            "role": "owner",
            "members": 2,
            "alarms": 1,
            "unverified": ["serge"],
            "quarantine": 4,
            "rotation_due": True,
        }
    ]
    text = "\n".join(h["problems"])
    assert "aurora link renew --phrase-stdin" in text
    assert "ops: ALARM fork from ffffffffffffffff: two heads" in text
    assert "aurora link verify ops" in text
    assert "serge" in text
    assert "key rotation is due" in text
    assert f"aurora link accept ops {'1' * 12}" in text
    assert "2" * 12 not in text
    assert "start `aurora link serve`" in text
    lines = health.render(h)
    assert "  ops: 2 members, role owner, 4 in quarantine, 1 ALARM(S)" in lines
    assert "daemon: not running" in lines[1]


def test_health_survives_a_daemon_that_does_not_answer(home, monkeypatch):
    """A failing daemon becomes a problem line, never an exception."""
    use_links(home)
    d = FakeDaemon({"identity.status": lambda _p: (_ for _ in ()).throw(Refuse(-32003, "store locked"))})
    monkeypatch.setattr(health, "find_linkd", lambda: "/bin/linkd")
    monkeypatch.setattr(health, "running_addr", lambda: "/s")
    monkeypatch.setattr(health, "connect", d.client)
    h = health.health()
    assert h["problems"] == ["aurora-linkd did not answer: store locked"]


def test_health_clean_link_while_running_has_no_problems(home, monkeypatch):
    """A verified, quiet link with serve running reports nothing to fix."""
    use_links(home)
    monkeypatch.setattr(health, "find_linkd", lambda: "/bin/linkd")
    monkeypatch.setattr(health, "running_addr", lambda: "/s")
    monkeypatch.setattr(health, "connect", health_daemon(status()).client)
    h = health.health()
    assert h["problems"] == []
    assert h["links"][0]["unverified"] == []
    assert health.render(h)[2] == "  ops: 2 members, role owner, 0 in quarantine"


# ------------------------------------------------------------------------------------- panel.py


def test_panel_snapshot_is_just_health_when_links_are_unavailable(monkeypatch):
    """Not in use or not installed: no daemon call, links empty."""
    monkeypatch.setattr(panel, "health", lambda: {"in_use": True, "available": False})

    def no_connect() -> lc.Client:
        raise AssertionError("must not connect")

    monkeypatch.setattr(panel, "connect", no_connect)
    assert panel.snapshot() == {"health": {"in_use": True, "available": False}, "links": []}


def test_panel_snapshot_lists_each_links_status_and_quarantine(home, monkeypatch, r):
    """Each link shows its status and its quarantine inbox from the stream."""
    quarantine.admit([event(1), event(2)], r)
    monkeypatch.setattr(quarantine, "redis_client", lambda: r)
    monkeypatch.setattr(panel, "health", lambda: {"in_use": True, "available": True})
    d = FakeDaemon({"link.list": [{"link": LINK, "name": "ops"}], "link.status": status()})
    monkeypatch.setattr(panel, "connect", d.client)
    snap = panel.snapshot(inbox_limit=1)
    assert len(snap["links"]) == 1
    assert snap["links"][0]["status"]["name"] == "ops"
    assert [x["cursor"] for x in snap["links"][0]["inbox"]] == ["2"]


def test_panel_snapshot_reports_a_failing_daemon_as_state(monkeypatch):
    """A daemon error lands in `error`, not as an exception."""
    monkeypatch.setattr(panel, "health", lambda: {"in_use": True, "available": True})

    def missing() -> lc.Client:
        raise lc.LinkdMissing("gone")

    monkeypatch.setattr(panel, "connect", missing)
    assert panel.snapshot()["error"] == "gone"


def test_panel_act_needs_explicit_confirm_and_a_known_action(monkeypatch):
    """Without confirm nothing runs; an unknown action is refused after connecting."""
    d = FakeDaemon()
    monkeypatch.setattr(panel, "connect", d.client)
    assert panel.act("promote", {"link": "ops"}, confirm=False) == {
        "ok": False,
        "why": "confirm must be sent explicitly",
    }
    assert d.calls == []
    assert panel.act("delete", {}, confirm=True) == {"ok": False, "why": "unknown action 'delete'"}


def test_panel_act_promotes_accepts_declines_and_verifies(monkeypatch):
    """Each console action reaches the daemon with the console as the promoter."""
    rec = event(1, rid=REC)
    rec["status"] = "admitted"
    d = FakeDaemon(
        {
            "link.status": status(),
            "record.get": rec,
            "promotion.record": {"first": True},
            "link.accept": {"entry": "e1"},
            "link.decline": {"entry": "e2"},
            "link.verify": [{"label": "serge", "verified": True}],
        }
    )
    monkeypatch.setattr(panel, "connect", d.client)
    import core.comm.bus as bus_mod

    bus = StubBus()
    monkeypatch.setattr(bus_mod, "Bus", lambda _name: bus)
    out = panel.act("promote", {"link": "ops", "record": REC, "by": "dan"}, confirm=True)
    assert out["ok"]
    assert out["seat"] == "claude"
    assert bus.sent[0][3] is not None
    assert bus.sent[0][3]["promoted_by"] == "console:dan"
    assert panel.act("accept", {"link": "ops", "join": "j"}, confirm=True) == {"ok": True, "entry": "e1"}
    assert panel.act("decline", {"link": "ops", "join": "j"}, confirm=True) == {"ok": True, "entry": "e2"}
    assert panel.act("verify", {"link": "ops"}, confirm=True)["verified"][0]["label"] == "serge"
    assert ("link.verify", {"link": "ops", "mark": True}) in d.calls


def test_panel_act_turns_refusals_into_why(monkeypatch):
    """A refused promotion is {ok: False, why}, not an exception."""
    rec = event(1, rid=REC)
    rec["status"] = "own"
    monkeypatch.setattr(panel, "connect", FakeDaemon({"link.status": status(), "record.get": rec}).client)
    out = panel.act("promote", {"link": "ops", "record": REC}, confirm=True)
    assert out["ok"] is False
    assert "record is own" in out["why"]


# ------------------------------------------------------------------------------------- serve.py


def test_daemon_flags_map_every_serve_option():
    """`aurora link serve` options become the daemon's serve flags, in order."""
    assert serve.daemon_flags() == []
    assert serve.daemon_flags(
        mailbox=True,
        relays=["https://r1", "https://r2"],
        no_relay=True,
        no_n0=True,
        no_mdns=True,
        bind="127.0.0.1:0",
        relay_only=True,
        trace_rpc=True,
    ) == [
        "--mailbox",
        "--relay",
        "https://r1",
        "--relay",
        "https://r2",
        "--no-relay",
        "--no-n0",
        "--no-mdns",
        "--bind",
        "127.0.0.1:0",
        "--relay-only",
        "--trace-rpc",
    ]


def test_serve_without_the_binary_prints_the_remedy_and_exits_2(monkeypatch):
    """No aurora-linkd: exit code 2 and the install line, nothing spawned."""
    monkeypatch.setattr(serve, "find_linkd", lambda: None)
    out = io.StringIO()
    assert serve.run(out=out) == 2
    assert out.getvalue() == f"[link serve] {lc.MISSING}\n"


@pytest.fixture
def no_signals(monkeypatch) -> dict[int, Any]:
    """serve.run installs SIGINT/SIGTERM handlers: record them instead of installing them."""
    handlers: dict[int, Any] = {}
    monkeypatch.setattr(serve.signal, "signal", lambda sig, h: handlers.__setitem__(sig, h))
    return handlers


def test_serve_once_pumps_quarantine_applies_rules_and_shuts_the_daemon_down(home, monkeypatch, r, no_signals):
    """One tick under a real ManagedChild: records are quarantined, rules promote, then shutdown."""
    write_promote_toml(home, 'mode = "rules"\n[[rules]]\nkind = "chat"\nto = "claude"\n')
    rec = event(1, rid=REC)
    rec["status"] = "admitted"
    _binary, log = fake_linkd_script(
        home,
        monkeypatch,
        {
            "events.wait": [{"events": [event(1, rid=REC)]}],
            "link.status": [status()],
            "record.get": [rec],
            "promotion.record": [{"first": True}],
            "daemon.shutdown": [{}],
        },
    )
    monkeypatch.setattr(quarantine, "redis_client", lambda: r)
    import core.comm.bus as bus_mod

    bus = StubBus()
    monkeypatch.setattr(bus_mod, "Bus", lambda _name: bus)
    out = io.StringIO()
    assert serve.run(flags=["--no-mdns"], once=True, out=out) == 0
    text = out.getvalue()
    assert "aurora-linkd pid" in text
    assert "1 record(s) quarantined" in text
    assert f"rule promoted {REC[:12]} -> claude" in text
    assert r.xlen(quarantine.stream_key(LINK)) == 1
    assert bus.sent[0][0] == "claude"
    assert quarantine.load_cursors() == {LINK: 1}
    rows = logged(log)
    assert rows[0]["argv"][-3:] == ["serve", "--stdio", "--no-mdns"], "socket on, network on, flags passed"
    assert [x.get("method") for x in rows[1:]][-1] == "daemon.shutdown"
    assert set(no_signals) >= {serve.signal.SIGINT}


def test_serve_survives_a_channel_error_and_reports_it(home, monkeypatch, r, no_signals):
    """An RPC error from the pump is printed and the loop waits for the daemon instead of dying."""
    fake_linkd_script(
        home,
        monkeypatch,
        {"events.wait": [{"__error__": {"code": -32003, "message": "store busy"}}], "daemon.shutdown": [{}]},
    )
    monkeypatch.setattr(quarantine, "redis_client", lambda: r)
    monkeypatch.setattr(serve.time, "sleep", lambda _s: None)
    out = io.StringIO()
    assert serve.run(once=True, out=out) == 0
    assert "channel error (LinkRpcError: store busy); waiting for the daemon" in out.getvalue()


class FakeChild:
    """A ManagedChild stand-in: scripted poll() results and optional rpc pipes."""

    instances: ClassVar[list[FakeChild]] = []
    script: Any = None  # a test sets this to drive poll()

    def __init__(self, args: list[str], stdio_rpc: bool = False):
        self.args = args
        self.stdio_rpc = stdio_rpc
        self.on_exit: Any = None
        self.pid = 4242
        self.rpc_pipes: Any = None
        self.ticks = 0
        self.terminated = False
        FakeChild.instances.append(self)

    def spawn(self) -> None:
        pass

    def poll(self) -> None:
        self.ticks += 1
        if self.script:
            self.script(self)

    def terminate(self) -> None:
        self.terminated = True


def test_serve_logs_a_daemon_exit_and_stops_on_a_signal(home, monkeypatch, no_signals):
    """A daemon exit appends its tail to state/logs/linkd.log; SIGINT ends the loop cleanly."""
    import scripts.bifrost_child as bc

    FakeChild.instances.clear()
    monkeypatch.setattr(bc, "ManagedChild", FakeChild)
    monkeypatch.setattr(serve, "find_linkd", lambda: "/opt/aurora-linkd")
    monkeypatch.setattr(serve.time, "sleep", lambda _s: None)

    def script(child: FakeChild) -> None:
        if child.ticks == 1:
            child.on_exit(101, "thread 'main' panicked")
        else:
            no_signals[serve.signal.SIGINT]()

    monkeypatch.setattr(FakeChild, "script", staticmethod(script))
    out = io.StringIO()
    assert serve.run(out=out) == 0
    child = FakeChild.instances[0]
    assert child.terminated
    assert child.stdio_rpc
    assert child.ticks == 2
    assert child.args[0] == "/opt/aurora-linkd"
    assert "--no-socket" not in child.args
    log = serve.log_path().read_text(encoding="utf-8")
    assert "aurora-linkd exited 101" in log
    assert "panicked" in log
    assert serve.log_path() == home / "state" / "logs" / "linkd.log"
    assert "aurora-linkd exited 101; tail in" in out.getvalue()


def test_serve_mailbox_opens_no_quarantine(home, monkeypatch, no_signals):
    """A mailbox daemon is never pumped: no events.wait, only the shutdown at the end."""
    import scripts.bifrost_child as bc

    FakeChild.instances.clear()
    monkeypatch.setattr(bc, "ManagedChild", FakeChild)
    monkeypatch.setattr(serve, "find_linkd", lambda: "/opt/aurora-linkd")
    d = FakeDaemon({"daemon.shutdown": {}})

    class Raw(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, b: Any) -> int:
            line = d.readline()
            b[: len(line)] = line
            return len(line)

    def script(child: FakeChild) -> None:
        child.rpc_pipes = (Raw(), d)
        if child.ticks >= 3:
            no_signals[serve.signal.SIGINT]()

    monkeypatch.setattr(FakeChild, "script", staticmethod(script))
    monkeypatch.setattr(serve.time, "sleep", lambda _s: None)
    assert serve.run(mailbox=True, out=io.StringIO()) == 0
    assert d.methods() == ["daemon.shutdown"]


def test_serve_mailbox_once_returns_without_a_signal(home, monkeypatch, no_signals):
    """`aurora link mailbox --once` stops after its first pass, like serve --once."""
    import scripts.bifrost_child as bc

    FakeChild.instances.clear()
    monkeypatch.setattr(bc, "ManagedChild", FakeChild)
    monkeypatch.setattr(serve, "find_linkd", lambda: "/opt/aurora-linkd")
    d = FakeDaemon({"daemon.shutdown": {}})

    class Raw(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, b: Any) -> int:
            line = d.readline()
            b[: len(line)] = line
            return len(line)

    def script(child: FakeChild) -> None:
        child.rpc_pipes = (Raw(), d)
        assert child.ticks < 5, "mailbox --once kept looping"

    monkeypatch.setattr(FakeChild, "script", staticmethod(script))
    monkeypatch.setattr(serve.time, "sleep", lambda _s: None)
    assert serve.run(mailbox=True, once=True, out=io.StringIO()) == 0
    assert d.methods() == ["daemon.shutdown"]
