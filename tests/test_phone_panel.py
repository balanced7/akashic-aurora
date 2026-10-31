"""Pins for the phone control panel (arsenal/panel) -- the GATE for the 2026-10-31 build.

Daniel's ask, verbatim: "can we build a management app for our connections and services on my phone?
This way we can spin daemons up and down, restore connection, set up video feed etc."

The panel can start and stop processes on his desktop, so this file is not a smoke test: it is the
refusal surface. Pre-registered acceptance (written before the first line of the panel ran):

  1. THE ALLOWLIST REFUSES ANYTHING ELSE -- an unknown service, an unknown verb, a verb a service does
     not declare, and a body carrying a field the API does not take, all refuse and all touch nothing.
  2. NO SHELL, NO ARG INJECTION -- `shell=True`, `os.system` and `os.popen` appear nowhere in the
     package (asserted by reading its own source), the argv handed to a spawn is EXACTLY the declared
     list, and a request can never contribute an argument.
  3. LOOPBACK-ONLY BIND -- a non-loopback host is refused by the constructor, and the live socket is on
     127.0.0.1.
  4. HOST / ORIGIN -- a foreign Host is 421 (DNS rebinding), a foreign Origin is 403.
  5. THE STATUS SCHEMA -- one document, tri-state, colours mapped, watched-never-touched separated,
     video block present, and the phase-3 reachability JSON carried verbatim.
  6. THE CONFIRM TOKEN -- stop/restart need one; it is single-use, bound to one service+verb, and
     expires.
  7. THE AUDIT LINE -- every decision (acted, refused, throttled) appends one JSON line, and the file is
     append-only.
  8. RATE LIMIT -- the destructive window answers 429 with Retry-After.

THE FAKE-SERVICE HARNESS IS THE POINT: every I/O seam (spawn, external query, process list, terminate,
prober, reachability) is a fake in this file, so NO REAL DAEMON, scheduled task or port is touched by
the suite. The ONE live drill (a preview server on a TEST port) is run by hand and receipted in
docs/PHONE-PANEL.md, never from here.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from arsenal.panel import spec as spec_mod
from arsenal.panel.actions import ActionRefused, ActionRunner
from arsenal.panel.audit import AuditLog
from arsenal.panel.limit import RateLimiter
from arsenal.panel.probe import DOWN, UNKNOWN, UP, Prober
from arsenal.panel.server import API_VERSION, Panel, PanelServer
from arsenal.panel.status import ReachabilityCache, build as build_status
from arsenal.panel.tokens import ConfirmTokens

REPO = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- the fake harness
class FakeProc:
    """A process row: pid + argv, matching what actions._real_processes yields."""

    def __init__(self, pid: int, argv):
        self.pid = pid
        self.argv = [str(a) for a in argv]

    def __iter__(self):
        return iter(self.argv)


class FakeWorld:
    """One object holding every seam the panel uses. Nothing here touches the real machine."""

    def __init__(self, *, running=None, ports=None, port_up=None, tasks=None, services=None,
                 spawn_binds=True):
        self.spawned = []
        self.terminated = []
        self.queries = []
        self.spawn_binds = spawn_binds
        self.processes = [FakeProc(i + 100, argv) for i, argv in enumerate(running or [])]
        self.ports = dict(ports or port_up or {})
        self.tasks = dict(tasks or {})
        self.services = dict(services or {})

    # seams
    def popen(self, argv, cwd=None, detached=True):
        self.spawned.append({"argv": list(argv), "cwd": cwd, "detached": detached})
        if self.spawn_binds:
            for token in argv:                  # a spawned server binds its port: simulate it
                if str(token).isdigit():
                    self.ports[int(token)] = True

        class _Handle:
            pid = 4242

        return _Handle()

    def run(self, argv):
        self.queries.append(list(argv))
        lower = [str(a).lower() for a in argv]
        exe = lower[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if len(argv) >= 2 and exe == "schtasks" and lower[1] == "/query":
            name = argv[lower.index("/tn") + 1]
            status = self.tasks.get(name)
            if status is None:
                return 1, "ERROR: The system cannot find the file specified."
            return 0, f"TaskName:      \\{name}\r\nStatus:        {status}\r\n"
        if len(argv) >= 2 and exe == "schtasks" and lower[1] in ("/end", "/run"):
            name = argv[lower.index("/tn") + 1]
            self.tasks[name] = "Ready" if lower[1] == "/end" else "Running"
            return 0, "SUCCESS"
        if len(argv) >= 2 and exe == "sc" and lower[1] == "query":
            return 0, "STATE : 4  RUNNING"
        return 0, ""

    def terminate(self, pid):
        self.terminated.append(pid)
        for proc in self.processes:
            if getattr(proc, "pid", None) == pid:
                for token in getattr(proc, "argv", []):   # the port closes with its server
                    if str(token).isdigit():
                        self.ports[int(token)] = False
        self.processes = [p for p in self.processes if getattr(p, "pid", None) != pid]

    def connect(self, host, port, timeout):
        return bool(self.ports.get(int(port)))

    def prober(self):
        return Prober(connect=self.connect, processes=lambda: self.processes, run=self.run,
                      service_status=lambda name: self.services.get(name), timeout=0.01)


def make_runner(world, *, prober=None, wait_s=0.05):
    return ActionRunner(popen=world.popen, run=world.run, processes=lambda: world.processes,
                        terminate=world.terminate, prober=prober or world.prober(),
                        clock=time.monotonic, sleep=lambda s: None, start_wait_s=wait_s)


BASE_SPEC = {
    "services": [
        {"id": "preview-8901", "label": "Preview 8901", "group": "stage",
         "probe": {"kind": "port", "host": "127.0.0.1", "port": 8901},
         "start": ["py", "-m", "http.server", "8901", "--bind", "127.0.0.1"],
         "stop": {"type": "kill_argv", "match": ["http.server", "8901"]}},
        {"id": "a-task", "label": "A task", "group": "log",
         "probe": {"kind": "task", "name": "Fake-Task"},
         "start": ["schtasks", "/Run", "/TN", "Fake-Task"],
         "stop": {"type": "task_end", "name": "Fake-Task"}},
        {"id": "watched", "label": "Watched only", "group": "services", "status_only": True,
         "why_no_actions": "the house rule says nobody touches this from a phone",
         "probe": {"kind": "argv", "match": ["some_watcher.py"]}},
        {"id": "no-stop", "label": "No stop", "group": "link",
         "probe": {"kind": "argv", "match": ["revive.py"]},
         "start": ["py", "scripts/revive.py", "--target", "gateway"],
         "stop": {"type": "none", "why": "never hand-killed; the revive ladder is the only lever"}},
    ]
}


def write_spec(tmp_path, doc) -> str:
    p = tmp_path / "phone-panel.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def load(doc, tmp_path, root=None):
    return spec_mod.load_specs(write_spec(tmp_path, doc), root=root or str(REPO))


# =========================================================================== 1. the allowlist
def test_a_valid_allowlist_loads_and_derives_its_verbs(tmp_path):
    specs = load(BASE_SPEC, tmp_path)
    assert set(specs) == {"preview-8901", "a-task", "watched", "no-stop"}
    assert specs["preview-8901"].allowed_verbs() == ("start", "stop", "restart")
    assert specs["watched"].allowed_verbs() == ()          # status-only: no verbs, ever
    assert specs["no-stop"].allowed_verbs() == ("start", "restart")   # stop: none is not a stop
    assert specs["watched"].needs_confirm("stop") is False
    assert specs["preview-8901"].needs_confirm("stop") is True


def test_an_unknown_service_is_refused_and_nothing_is_touched(tmp_path):
    world = FakeWorld(ports={8901: False})
    panel = _panel(tmp_path, world)
    code, payload = panel.act({"service": "../../etc/passwd", "verb": "start"})
    assert code == 404 and "no service" in payload["error"]
    assert world.spawned == [] and world.terminated == []


def test_an_unknown_verb_is_refused(tmp_path):
    world = FakeWorld(ports={8901: False})
    panel = _panel(tmp_path, world)
    for verb in ("kill", "exec", "START", "restart; rm -rf /", ""):
        code, payload = panel.act({"service": "preview-8901", "verb": verb})
        assert code in (400, 403), (verb, code)
        assert world.spawned == [] and world.terminated == []


def test_a_verb_the_service_does_not_declare_is_refused_with_its_reason(tmp_path):
    world = FakeWorld()
    panel = _panel(tmp_path, world)
    code, payload = panel.act({"service": "watched", "verb": "start"})
    assert code == 403
    assert "does not accept" in payload["error"]
    assert "house rule" in payload["why"]
    code, payload = panel.act({"service": "no-stop", "verb": "stop", "token": "x"})
    assert code == 403 and "does not accept" in payload["error"]
    assert world.spawned == [] and world.terminated == []


def test_a_body_carrying_another_field_is_refused_not_ignored(tmp_path):
    """The injection defence is a SCHEMA. A client that thinks it is passing `args` is told it is not."""
    world = FakeWorld(ports={8901: False})
    panel = _panel(tmp_path, world)
    for extra in ({"args": ["--evil"]}, {"cmd": "calc.exe"}, {"shell": True},
                  {"path": "/etc/passwd"}, {"argv": ["whoami"]}):
        body = {"service": "preview-8901", "verb": "start"}
        body.update(extra)
        code, payload = panel.act(body)
        assert code == 400
        assert "unknown field" in payload["error"]
    assert world.spawned == [], "a refused body must not reach a spawn"


def test_spec_validation_refuses_each_unsafe_shape(tmp_path):
    # a string argv would invite shell=True later
    with pytest.raises(spec_mod.SpecError, match="must be a LIST"):
        load({"services": [{"id": "x", "probe": {"kind": "absent", "why": "n/a"},
                            "start": "py -m http.server"}]}, tmp_path)
    # a duplicate id makes one row unreachable
    with pytest.raises(spec_mod.SpecError, match="declared twice"):
        load({"services": [{"id": "x", "probe": {"kind": "absent", "why": "n/a"}},
                           {"id": "x", "probe": {"kind": "absent", "why": "n/a"}}]}, tmp_path)
    # a probe that leaves loopback is a different question than "is it up on this PC"
    with pytest.raises(spec_mod.SpecError, match="only probes loopback"):
        load({"services": [{"id": "x", "probe": {"kind": "port", "host": "0.0.0.0", "port": 80}}]},
             tmp_path)
    # a relative cwd resolves against wherever the panel was launched from
    with pytest.raises(spec_mod.SpecError, match="absolute path"):
        load({"services": [{"id": "x", "probe": {"kind": "absent", "why": "n/a"},
                            "start": ["py", "-V"], "start_cwd": "scripts"}]}, tmp_path)
    # status_only must not declare a start
    with pytest.raises(spec_mod.SpecError, match="status_only"):
        load({"services": [{"id": "x", "status_only": True, "why_no_actions": "no",
                            "probe": {"kind": "absent", "why": "n/a"}, "start": ["py", "-V"]}]},
             tmp_path)
    # a non-id id (a URL field) is refused
    with pytest.raises(spec_mod.SpecError, match="must match"):
        load({"services": [{"id": "Not An Id!", "probe": {"kind": "absent", "why": "n/a"}}]},
             tmp_path)
    # an empty allowlist is refused rather than started
    with pytest.raises(spec_mod.SpecError, match="non-empty"):
        load({"services": []}, tmp_path)
    # a missing file is refused, with the reason an empty list would hide
    with pytest.raises(spec_mod.SpecError, match="no allowlist"):
        spec_mod.load_specs(str(tmp_path / "absent.json"))


# =============================================================== 2. no shell, no arg injection
def test_no_shell_primitive_exists_in_the_package():
    """Read the package's own CODE (AST, not prose): `shell=True`, os.system and os.popen cannot appear.

    A substring hunt over the source would fail on this package's own docstrings -- which NAME the
    forbidden primitives in order to forbid them, exactly the way the purity ratchet once went red on
    Rill's own prose. So this parses the code and inspects calls, which is the thing that actually
    matters: a future edit that adds `shell=True` fails HERE, not in production."""
    import ast

    for path in sorted((REPO / "arsenal" / "panel").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords or ():
                    assert not (kw.arg == "shell" and getattr(kw.value, "value", None) is True), \
                        f"{path.name}:{node.lineno} calls with shell=True"
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert not (node.value.id == "os" and node.attr in ("system", "popen")), \
                    f"{path.name}:{node.lineno} calls os.{node.attr}"
            if isinstance(node, ast.Name):
                assert node.id not in ("eval", "exec"), \
                    f"{path.name}:{getattr(node, 'lineno', '?')} uses {node.id}()"
        # the one place a shell could sneak in as a literal string
        assert "shell=True" not in _code_only(path), f"{path.name} mentions shell=True in code"


def _code_only(path) -> str:
    """The file's source with docstrings and comments stripped, so prose cannot trip a code check."""
    import ast
    import io
    import tokenize

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add((body[0].lineno, body[0].col_offset))
    keep = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        keep.append(tok.string)
    return " ".join(keep)


def test_the_argv_handed_to_a_spawn_is_exactly_the_declared_list(tmp_path):
    world = FakeWorld(ports={8901: False})       # down now; the fake spawn is what brings it up
    specs = load(BASE_SPEC, tmp_path)
    runner = make_runner(world)
    result = runner.perform(specs["preview-8901"], "start")
    assert result.ok is True, result.detail
    assert len(world.spawned) == 1
    argv = world.spawned[0]["argv"]
    assert isinstance(argv, list) and argv == list(specs["preview-8901"].start)
    assert all(isinstance(a, str) for a in argv)
    assert world.spawned[0]["detached"] is True
    assert world.spawned[0]["cwd"] == specs["preview-8901"].start_cwd


def test_a_request_string_never_reaches_a_command(tmp_path):
    """The request names an id and a verb. Even a hostile id produces no spawn and no query."""
    world = FakeWorld(ports={8901: False})
    panel = _panel(tmp_path, world)
    for hostile in ("preview-8901 --evil", "preview-8901;calc", "$(whoami)",
                    "preview-8901\nrm -rf /", "PREVIEW-8901"):
        panel.act({"service": hostile, "verb": "start"})
    assert world.spawned == [] and world.queries == []


# ============================================================================ 3. loopback bind
def test_a_non_loopback_host_is_refused_by_the_constructor(tmp_path):
    world = FakeWorld()
    panel = _panel_from(BASE_SPEC, world, port=0, tmp_path=tmp_path)
    for host in ("0.0.0.0", "192.168.0.10", "100.116.105.68", "::", "localhost.evil.com"):
        with pytest.raises(ValueError, match="loopback only"):
            PanelServer(panel, host=host, port=0)


def test_the_live_socket_is_on_loopback(tmp_path):
    world = FakeWorld(ports={8901: False})
    panel = _panel(tmp_path, world)
    srv = PanelServer(panel, port=0).start()
    try:
        assert srv.httpd.server_address[0] == "127.0.0.1"
        assert srv.port > 0
    finally:
        srv.stop()


# ========================================================================= 4. Host and Origin
class _Served:
    """A panel on an ephemeral loopback port, with HTTP helpers."""

    def __init__(self, panel):
        self.srv = PanelServer(panel, port=0).start()
        self.base = f"http://127.0.0.1:{self.srv.port}"

    def get(self, path, headers=None):
        req = urllib.request.Request(self.base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read(), dict(res.headers)
        except urllib.error.HTTPError as err:
            return err.code, err.read(), dict(err.headers)

    def post(self, path, body, headers=None):
        hdrs = {"Content-Type": "application/json"}
        hdrs.update(headers or {})
        req = urllib.request.Request(self.base + path, method="POST",
                                     data=json.dumps(body).encode("utf-8"), headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.loads(res.read() or b"{}"), dict(res.headers)
        except urllib.error.HTTPError as err:
            raw = err.read()
            try:
                payload = json.loads(raw or b"{}")
            except ValueError:
                payload = {"raw": raw.decode("utf-8", "replace")}
            return err.code, payload, dict(err.headers)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.srv.stop()


def test_a_foreign_host_header_is_421_dns_rebinding(tmp_path):
    world = FakeWorld(ports={8901: False})
    with _Served(_panel(tmp_path, world)) as s:
        code, payload, _ = (lambda r: (r[0], json.loads(r[1] or b"{}"), r[2]))(
            s.get("/api/status", headers={"Host": "evil.example.com"}))
        assert code == 421 and "loopback" in payload["error"]
        # and the correct loopback Host is fine
        code, payload, _ = (lambda r: (r[0], json.loads(r[1] or b"{}"), r[2]))(s.get("/api/status"))
        assert code == 200 and payload["version"] == API_VERSION


def test_a_foreign_origin_is_403_on_post(tmp_path):
    world = FakeWorld(ports={8901: False})
    with _Served(_panel(tmp_path, world)) as s:
        code, payload, _ = s.post("/api/action", {"service": "preview-8901", "verb": "start"},
                                  headers={"Origin": "https://evil.example.com"})
        assert code == 403 and "origin" in payload["error"]
        assert world.spawned == []


def test_a_loopback_origin_is_accepted_and_a_missing_origin_too(tmp_path):
    world = FakeWorld(ports={8901: True})     # already up -> start is a no-op that still answers 200
    with _Served(_panel(tmp_path, world)) as s:
        origin = {"Origin": s.base}
        code, payload, _ = s.post("/api/action", {"service": "preview-8901", "verb": "start"},
                                  headers=origin)
        assert code == 200, payload
        code, payload, _ = s.post("/api/action", {"service": "preview-8901", "verb": "start"})
        assert code == 200, payload


def test_a_non_json_post_is_415(tmp_path):
    world = FakeWorld(ports={8901: False})
    with _Served(_panel(tmp_path, world)) as s:
        req = urllib.request.Request(s.base + "/api/action", method="POST",
                                     data=b"service=preview&verb=start",
                                     headers={"Content-Type": "text/plain"})
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "a text/plain POST must not be accepted"
        except urllib.error.HTTPError as err:
            assert err.code == 415


# =========================================================================== 5. the status schema
def test_the_status_document_has_the_pinned_schema(tmp_path):
    world = FakeWorld(ports={8901: True}, tasks={"Fake-Task": "Running"},
                      running=[["py", "some_watcher.py"]])
    panel = _panel(tmp_path, world, reach=_stub_reach(UP))
    doc = panel.status_document()
    for key in ("generated", "epoch", "version", "panel", "link", "reachability", "services",
                "status_only", "video", "groups", "audit_tail", "rate"):
        assert key in doc, key
    assert doc["version"] == API_VERSION
    rows = {r["id"]: r for r in doc["services"]}
    assert set(rows) == {"preview-8901", "a-task", "no-stop"}
    assert {r["id"] for r in doc["status_only"]} == {"watched"}
    assert rows["preview-8901"]["state"] == UP and rows["preview-8901"]["colour"] == "green"
    assert rows["a-task"]["state"] == UP and rows["a-task"]["colour"] == "green"
    assert rows["no-stop"]["state"] == DOWN and rows["no-stop"]["colour"] == "red"
    assert rows["preview-8901"]["actions"] == ["start", "stop", "restart"]
    assert rows["preview-8901"]["confirm"] == ["stop", "restart"]
    assert rows["a-task"]["confirm"] == ["stop", "restart"]
    assert "link" in doc["video"] and "artemis" in doc["video"] and "apollo" in doc["video"]


def test_unknown_is_amber_and_never_collapses_into_red(tmp_path):
    """A probe that could not look is UNKNOWN (amber). DOWN (red) is a claim, and it needs an answer."""
    world = FakeWorld(ports={8901: False}, tasks={})     # Fake-Task: schtasks cannot answer

    def broken():
        raise RuntimeError("process list unavailable")

    prober = Prober(connect=world.connect, processes=broken, run=world.run, timeout=0.01)
    panel = _panel(tmp_path, world, prober=prober)
    doc = panel.status_document()
    rows = {r["id"]: r for r in doc["services"]}
    assert rows["a-task"]["state"] == UNKNOWN and rows["a-task"]["colour"] == "amber"
    assert "not DOWN" in rows["a-task"]["why"] or "UNKNOWN" in rows["a-task"]["why"]
    assert rows["no-stop"]["state"] == UNKNOWN and rows["no-stop"]["colour"] == "amber"
    assert rows["preview-8901"]["state"] == DOWN and rows["preview-8901"]["colour"] == "red"


def test_the_reachability_json_travels_verbatim_and_a_failure_is_labelled_stale(tmp_path):
    rep = _stub_reach(UP)("dsh_agent", "")
    doc = build_status(load(BASE_SPEC, tmp_path), FakeWorld().prober(), port=1,
                       reach=ReachabilityCache("dsh_agent", fetch=_stub_reach(UP)))
    assert doc["reachability"]["rungs"]["gateway"]["state"] == UP
    assert doc["link"]["verdict"].startswith("reachable by")

    def broken(agent, session):
        raise RuntimeError("redis is down")

    cache = ReachabilityCache("dsh_agent", fetch=broken)
    doc2 = build_status(load(BASE_SPEC, tmp_path), FakeWorld().prober(), port=1, reach=cache)
    assert doc2["reachability"].get("_stale") is True
    assert doc2["link"]["stale"] is True
    assert "redis is down" in doc2["link"]["why"]


def test_the_page_assets_are_served_from_a_fixed_route_table(tmp_path):
    world = FakeWorld(ports={8901: False})
    with _Served(_panel(tmp_path, world)) as s:
        for route, ctype in (("/", "text/html"), ("/app.js", "text/javascript"),
                             ("/app.css", "text/css"), ("/manifest.webmanifest", "manifest+json"),
                             ("/sw.js", "text/javascript"), ("/icon.svg", "image/svg")):
            code, body, headers = s.get(route)
            assert code == 200, route
            assert ctype in headers.get("Content-Type", ""), (route, headers.get("Content-Type"))
            assert body, route
        code, body, headers = s.get("/../local/phone-panel.json")
        assert code == 404                       # no request path is ever a filesystem path
        code, _, headers = s.get("/")
        assert "Content-Security-Policy" in headers
        assert "unsafe-inline" not in headers["Content-Security-Policy"]


# ============================================================================ 6. confirm token
def _mint(panel, service, verb):
    code, payload = panel.confirm({"service": service, "verb": verb})
    assert code == 200, payload
    return payload["token"]


def test_stop_without_a_confirm_token_is_403_and_stops_nothing(tmp_path):
    world = FakeWorld(ports={8901: True}, running=[["py", "http.server", "8901"]])
    panel = _panel(tmp_path, world)
    code, payload = panel.act({"service": "preview-8901", "verb": "stop"})
    assert code == 403 and "confirm token" in payload["error"]
    assert world.terminated == []


def test_a_confirm_token_is_single_use(tmp_path):
    world = FakeWorld(ports={8901: True}, running=[["py", "http.server", "8901"]])
    panel = _panel(tmp_path, world)
    token = _mint(panel, "preview-8901", "stop")
    world.ports[8901] = False                 # the stop will look like it worked
    code, payload = panel.act({"service": "preview-8901", "verb": "stop", "token": token})
    assert code == 200, payload
    # replay: the token is gone, and the replay must not stop anything
    world.processes = [FakeProc(101, ["py", "http.server", "8901"])]
    world.ports[8901] = True
    code, payload = panel.act({"service": "preview-8901", "verb": "stop", "token": token})
    assert code == 403
    assert world.terminated == [100]          # only the first, legitimate kill


def test_a_confirm_token_is_bound_to_one_service_and_verb(tmp_path):
    world = FakeWorld(ports={8901: True}, tasks={"Fake-Task": "Running"})
    panel = _panel(tmp_path, world)
    token = _mint(panel, "preview-8901", "stop")
    code, _ = panel.act({"service": "a-task", "verb": "stop", "token": token})
    assert code == 403
    code, _ = panel.act({"service": "preview-8901", "verb": "restart", "token": token})
    assert code == 403
    assert world.terminated == [] and world.queries == []


def test_a_confirm_token_expires():
    now = [1000.0]
    tokens = ConfirmTokens(ttl_s=30.0, clock=lambda: now[0], mint=lambda: "tok")
    token, ttl = tokens.issue("a", "stop")
    assert ttl == 30.0
    assert tokens.consume(token, "a", "stop") is True      # live, consumed
    token2, _ = tokens.issue("a", "stop")
    now[0] += 31.0
    assert tokens.consume(token2, "a", "stop") is False     # expired


def test_confirming_a_verb_that_needs_no_token_is_refused(tmp_path):
    world = FakeWorld()
    panel = _panel(tmp_path, world)
    code, payload = panel.confirm({"service": "preview-8901", "verb": "start"})
    assert code == 400 and "does not need a confirm token" in payload["error"]


def test_the_token_cap_is_enforced():
    counter = iter(range(100))
    tokens = ConfirmTokens(ttl_s=60.0, clock=lambda: 1.0, mint=lambda: f"tok{next(counter)}",
                           max_outstanding=2)
    tokens.issue("a", "stop")
    tokens.issue("b", "stop")
    with pytest.raises(OverflowError):
        tokens.issue("c", "stop")


# =============================================================================== 7. audit line
def test_every_decision_appends_one_audit_line_and_nothing_rewrites_the_file(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    world = FakeWorld(ports={8901: False}, running=[["py", "http.server", "8901"]])
    panel = _panel(tmp_path, world, audit_path=str(audit_path))

    world.ports[8901] = True
    code, _ = panel.act({"service": "preview-8901", "verb": "start"})       # acted
    assert code == 200
    code, _ = panel.act({"service": "nope", "verb": "start"})               # refused
    assert code == 404
    code, _ = panel.act({"service": "preview-8901", "verb": "stop"})        # refused (no token)
    assert code == 403

    lines = [json.loads(ln) for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 3
    first = lines[0]
    for key in ("ts", "epoch", "decision", "service", "verb", "ok", "remote"):
        assert key in first, key
    assert first["decision"] == "acted" and first["service"] == "preview-8901"
    assert lines[1]["decision"] == "refused" and lines[1]["service"] == "nope"
    assert lines[2]["decision"] == "refused" and "confirm token" in lines[2]["reason"]
    assert all(rec["remote"] == "127.0.0.1" for rec in lines)
    # append-only: the first line is byte-identical after the later writes
    assert audit_path.read_text(encoding="utf-8").splitlines()[0] == json.dumps(
        first, ensure_ascii=False, sort_keys=True)
    # and the document carries the tail
    assert len(panel.status_document()["audit_tail"]) == 3


def test_an_unwritable_audit_path_is_reported_not_swallowed(tmp_path):
    log = AuditLog(str(tmp_path / "no-such-dir" / "audit.jsonl"))
    assert log.write({"decision": "acted"}) == ""          # makedirs creates it
    log2 = AuditLog(str(tmp_path))
    assert "could not be written" in log2.write({"decision": "acted"})


# ============================================================================== 8. rate limit
def test_the_destructive_window_answers_429_with_retry_after(tmp_path):
    now = [500.0]
    limiter = RateLimiter(destructive=2, actions=50, attempts=50, window_s=60.0,
                          clock=lambda: now[0])
    world = FakeWorld(ports={8901: True}, running=[["py", "http.server", "8901"]])
    panel = _panel(tmp_path, world, limiter=limiter)
    # mint the budget's worth of tokens up front, so the ACTION gate can be exercised on its own
    tokens = [_mint(panel, "preview-8901", "stop") for _ in range(3)]

    accepted = 0
    for token in tokens[:2]:
        world.processes = [FakeProc(100, ["py", "http.server", "8901"])]   # the server comes back
        world.ports[8901] = True
        code, _ = panel.act({"service": "preview-8901", "verb": "stop", "token": token})
        accepted += 1 if code == 200 else 0
    assert accepted == 2

    # (a) the ACTION gate: a valid token, refused because the window is spent
    world.processes = [FakeProc(100, ["py", "http.server", "8901"])]
    world.ports[8901] = True
    code, payload = panel.act({"service": "preview-8901", "verb": "stop", "token": tokens[2]})
    assert code == 429 and "too many requests" in payload["error"]
    assert payload["retry_after_s"] > 0
    assert world.processes, "a throttled verb must not have stopped anything"

    # (b) the MINT gate: no token is handed out for a verb that could not be honoured
    code, payload = panel.confirm({"service": "preview-8901", "verb": "stop"})
    assert code == 429

    now[0] += 61.0
    token = _mint(panel, "preview-8901", "stop")
    code, _ = panel.act({"service": "preview-8901", "verb": "stop", "token": token})
    assert code == 200, "the window must roll"


def test_the_attempt_bound_counts_refusals_too():
    now = [0.0]
    limiter = RateLimiter(attempts=3, actions=99, destructive=99, clock=lambda: now[0])
    for _ in range(3):
        assert limiter.check()[0] is True
        limiter.note(acted=False)
    ok, retry, why = limiter.check()
    assert ok is False and retry > 0 and "requests in" in why


# ================================================================= 9. actions: verify, not assume
def test_a_start_reports_what_the_probe_saw_not_what_was_spawned(tmp_path):
    world = FakeWorld(ports={8901: False}, spawn_binds=False)   # the spawn does NOT bind
    specs = load(BASE_SPEC, tmp_path)
    runner = make_runner(world)
    result = runner.perform(specs["preview-8901"], "start")
    assert world.spawned, "the spawn happened"
    assert result.ok is False, "but the probe never read UP, so the verb did not verify"
    assert result.state == DOWN
    assert "still reads" in result.detail


def test_a_stop_kills_only_a_process_whose_argv_still_matches(tmp_path):
    """Invariant 3: re-read the pid's argv immediately before terminating, or fail safe.

    Two cases, and the second is the one that matters: a world where the process list CHANGES between
    the target list being built and the kill being issued -- exactly the shape of the confounder this
    house has been bitten by (a process that exited and had its pid reused, a predicate that matched
    the shell running the check). A broken predicate must leave the process ALONE."""
    specs = load(BASE_SPEC, tmp_path)

    # (a) honest path: one match, argv still matches, killed, probe agrees it went
    world = FakeWorld(running=[["py", "http.server", "8901"]])
    world.ports[8901] = True
    runner = make_runner(world)
    result = runner.perform(specs["preview-8901"], "stop")
    assert world.terminated == [100]
    world.ports[8901] = False            # the port closes because the process is gone
    shifty = FakeWorld(running=[])

    # (b) fail-safe path: the argv shifts before the kill, so nothing is terminated
    class Shifting:
        """Yields one argv on the first pass (the target list) and another afterwards."""

        def __init__(self, first, later):
            self.first, self.later, self.passes = first, later, 0

        def __iter__(self):
            self.passes += 1
            return iter(self.first if self.passes == 1 else self.later)

    shifty = FakeWorld(running=[])
    shifty.processes = Shifting([FakeProc(200, ["py", "http.server", "8901"])],
                                [FakeProc(200, ["py", "different.py"])])
    shifty.ports[8901] = True
    runner2 = make_runner(shifty)
    result2 = runner2.perform(specs["preview-8901"], "stop")
    assert shifty.terminated == [], "a pid whose argv changed must be left alone"
    assert result2.ok is False
    assert "no longer matches" in result2.detail


def test_a_target_that_vanished_is_not_a_problem_but_a_changed_one_is(tmp_path):
    """VANISHED != CHANGED, and the live drill of 2026-10-31 is why this pin exists.

    `py -m http.server 8901` is a LAUNCHER SHIM: it exits while its python child keeps the port, so a
    target is routinely gone between the list and the kill. That must not read as a refusal (it made a
    correct stop look broken in the drill); a pid whose argv CHANGED is still left alone and still
    counts as a problem."""
    specs = load(BASE_SPEC, tmp_path)

    class VanishingAfterListing:
        def __init__(self):
            self.passes = 0

        def __iter__(self):
            self.passes += 1
            if self.passes == 1:
                return iter([FakeProc(300, ["py", "http.server", "8901"]),
                             FakeProc(301, ["py", "http.server", "8901"])])
            return iter([FakeProc(301, ["py", "http.server", "8901"])])   # 300 has gone

    world = FakeWorld(running=[])
    world.processes = VanishingAfterListing()
    world.ports[8901] = True
    runner = make_runner(world)
    result = runner.perform(specs["preview-8901"], "stop")
    assert world.terminated == [301], "the survivor is killed, the vanished one is simply not a target"
    assert result.ok is True
    assert "already gone: [300]" in result.detail
    assert "no longer matches" not in result.detail


def test_a_restart_stops_first_and_never_starts_on_a_failed_stop(tmp_path):
    world = FakeWorld(running=[["py", "http.server", "8901"]])
    world.ports[8901] = True

    def no_terminate(pid):
        raise PermissionError("denied")

    specs = load(BASE_SPEC, tmp_path)
    runner = ActionRunner(popen=world.popen, run=world.run, processes=lambda: world.processes,
                          terminate=no_terminate, prober=world.prober(), sleep=lambda s: None,
                          start_wait_s=0.02)
    result = runner.perform(specs["preview-8901"], "restart")
    assert result.ok is False
    assert world.spawned == [], "a restart whose stop failed must NOT start a second copy"
    assert "did NOT run" in result.detail


def test_a_task_backed_service_stops_and_starts_through_the_task(tmp_path):
    world = FakeWorld(tasks={"Fake-Task": "Running"})
    specs = load(BASE_SPEC, tmp_path)
    runner = make_runner(world)
    result = runner.perform(specs["a-task"], "stop")
    assert result.ok is True and result.state == DOWN
    assert ["schtasks", "/End", "/TN", "Fake-Task"] in world.queries
    result = runner.perform(specs["a-task"], "start")
    assert result.ok is True
    assert ["schtasks", "/Run", "/TN", "Fake-Task"] in world.queries


def test_an_unreadable_task_is_unknown_not_down(tmp_path):
    world = FakeWorld(tasks={})
    specs = load(BASE_SPEC, tmp_path)
    state = world.prober().probe(specs["a-task"])
    assert state["state"] == UNKNOWN
    assert "not DOWN" in state["why"]


def test_a_status_only_service_cannot_be_performed_even_by_the_runner(tmp_path):
    specs = load(BASE_SPEC, tmp_path)
    runner = make_runner(FakeWorld())
    with pytest.raises(ActionRefused, match="does not accept"):
        runner.perform(specs["watched"], "start")


# ================================================================== 10. the real allowlist holds
def test_the_house_allowlist_validates_and_keeps_the_fences():
    """The committed local/phone-panel.json, checked for the rules the brief named explicitly."""
    specs, meta = spec_mod.load_document(str(REPO / "local" / "phone-panel.json"))
    # the three that are watched and never touched
    for sid in ("rill-dsh", "claude-wake-listener", "phonelink-watcher"):
        assert specs[sid].status_only is True
        assert specs[sid].allowed_verbs() == ()
        assert specs[sid].why_no_actions
    # the gateway goes only through the revive ladder and is never hand-killed
    gw = specs["gateway"]
    assert gw.start is not None and "revive.py" in " ".join(gw.start)
    assert gw.stop["type"] == "none"
    assert "stop" not in gw.allowed_verbs()
    # the runners are never hand-killed either (the runner lock and daemon own the seat)
    for sid in ("runner-deepseek", "runner-kimi"):
        assert specs[sid].stop["type"] == "none"
        assert "revive.py" in " ".join(specs[sid].start)
    # every declared start is a list of strings; a Python launch also names an ABSOLUTE cwd (a
    # scheduled-task launch does not need one, because the task carries its own working directory)
    for spec in specs.values():
        if spec.start:
            assert isinstance(spec.start, tuple)
            assert all(isinstance(a, str) and a for a in spec.start)
            if spec.start[0] in ("py", "python"):
                assert spec.start_cwd and Path(spec.start_cwd).is_absolute(), spec.id
    # apollo is declared ABSENT rather than optimistically green
    assert specs["apollo"].probe["kind"] == "absent"
    assert specs["apollo"].allowed_verbs() == ()
    assert "video" in meta and "artemis" in meta["video"]


# ------------------------------------------------------------------------------ helpers
def _stub_reach(state=UP):
    def fetch(agent, session):
        return {"agent": agent, "session": session, "generated": "2026-10-31T00:00:00",
                "rungs": {"gateway": {"state": state},
                          "wake_listener": {"state": state, "seats": [{"pid": 1}]},
                          "consumer_seat": {"state": state},
                          "runner": {"state": state},
                          "operator_mail": {"state": state},
                          "phone_tunnel": {"state": state, "phone_answers": True,
                                           "tailnet_host": "100.0.0.1", "tailnet_port": 8022}},
                "verdict": {"line": "reachable by: gateway, wake listener, phone (tailnet)"}}
    return fetch


def _panel(tmp_path, world, *, prober=None, reach=None, limiter=None, audit_path=None,
           port=8789):
    return _panel_from(BASE_SPEC, world, prober=prober, reach=reach, limiter=limiter,
                       audit_path=audit_path or str(tmp_path / "audit.jsonl"), port=port,
                       tmp_path=tmp_path)


def _panel_from(doc, world, *, prober=None, reach=None, limiter=None, audit_path=None,
                port=8789, tmp_path=None):
    specs = spec_mod.load_specs(write_spec(tmp_path, doc), root=str(REPO))
    pr = prober or world.prober()
    return Panel(specs, port=port, prober=pr, runner=make_runner(world, prober=pr),
                 limiter=limiter, audit_path=audit_path or str(tmp_path / "audit.jsonl"),
                 reach=ReachabilityCache("dsh_agent", fetch=reach or _stub_reach(UP)),
                 video_meta={"artemis": {"label": "Artemis", "deep_link": "intent://x"}})
