"""arsenal.panel.server -- the control API on 127.0.0.1, and the PWA it serves.

WHAT DANIEL GETS (his words, 2026-10-31): "can we build a management app for our connections and
services on my phone? This way we can spin daemons up and down, restore connection, set up video feed
etc." This is the PC half. The phone half is `scripts/phone/`.

REACHED FROM THE PHONE THROUGH THE EXISTING TUNNEL, and that is the whole networking design. The
PhoneLink watcher already runs `ssh -R 8787:127.0.0.1:8787 -R 8798:127.0.0.1:8798` to the phone, so the
phone's own loopback gets those PC ports. This API adds ONE more `-R` for its own port (see
`phonelink.ps1 watch` and `docs/PHONE-PANEL.md`). CONSEQUENCE, stated plainly because it is the point:
**nothing here is ever published to the tailnet** -- there is no tailnet-facing socket, no `0.0.0.0`
bind, and no relay. The phone talks to 127.0.0.1 on its own device, and ssh carries it.

THE GATES ON EVERY REQUEST, in the order they run (and each one is pinned):

  * BIND -- `127.0.0.1` only; the constructor REFUSES any other host, and the socket is bound
    exclusively (SO_EXCLUSIVEADDRUSE on Windows) so a second server fails instead of sharing the port.
  * HOST (421) -- the request must name this server by a loopback name. This is the DNS-rebinding fix,
    taken from `arsenal/rgb/desk/server.py`: a page on another site that rebinds its own name to
    127.0.0.1 still sends ITS OWN name in `Host`, so it can neither read this state nor drive it.
  * ORIGIN (403, POST only) -- when a browser names an Origin it must be one of this server's own
    loopback origins. A cross-site form POST carries a foreign Origin and is refused.
  * CONTENT-TYPE (415) / LENGTH (413, 400) / JSON OBJECT (400) -- POSTs are JSON, bounded, and must be
    an object. Values are CHECKED, never coerced.
  * THE ALLOWLIST (404 / 403) -- `service` must be an id in the allowlist, `verb` must be one of the
    three. There is no field through which a command, a path or an argument could travel.
  * CONFIRM TOKEN (403) -- stop and restart need a token minted by a separate `POST /api/confirm`.
  * RATE LIMIT (429) -- three sliding windows, see limit.py.
  * AUDIT -- every decision, taken or refused, appended to `state/phone-panel-audit.jsonl`.

THE PAGE IS SERVED BY THIS SAME SERVER, from files next to this module, through a fixed route table --
no path from a request ever becomes a filesystem path. A CSP with no `inline` allowances means the
page's JS and CSS are real files, which is also why `unsafe-inline` does not appear.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import status as status_mod
from .actions import ActionRefused, ActionRunner
from .audit import AuditLog
from .limit import RateLimiter
from .probe import Prober
from .spec import CONFIRM_VERBS, VERBS

WEB_DIR = Path(__file__).resolve().parent / "web"

#: The port. Registered in config.PORT_REGISTRY (PROD band, 878x); docs/PORTS.md is generated from
#: that, so this literal and the registry cannot disagree for long -- check_ports.py fails the commit.
DEFAULT_PORT = 8789

#: The API version the page and the schema agree on.
API_VERSION = "1"

#: A POST body is a service id, a verb and a token. 2 KB is generous; anything larger is not this API.
MAX_BODY = 2048

#: The page's own files, by route. FIXED: a request path is looked up in this table and never joined
#: to a filesystem path, so there is no traversal surface at all.
ASSETS: Dict[str, Tuple[str, str]] = {
    "/": ("page.html", "text/html; charset=utf-8"),
    "/index.html": ("page.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
}

#: Sent on every answer. `nosniff` stops a browser reinterpreting an API body as a document.
BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

#: Strict enough to mean something, loose enough to run offline: everything from this origin, no
#: inline script and no inline style (there are none), no framing, no form targets.
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; "
       "form-action 'none'; frame-ancestors 'none'")


class Panel:
    """The decision surface: what the handler calls. No HTTP types here, so it can be unit-tested."""

    def __init__(self, specs: Dict[str, Any],
                 *,
                 port: int,
                 host: str = "127.0.0.1",
                 prober: Optional[Prober] = None,
                 runner: Optional[ActionRunner] = None,
                 tokens=None,
                 limiter: Optional[RateLimiter] = None,
                 audit: Optional[AuditLog] = None,
                 audit_path: str = "",
                 agent: str = "",
                 session: str = "",
                 confirm_ttl_s: float = 60.0,
                 reach: Optional[status_mod.ReachabilityCache] = None,
                 video_meta: Optional[Dict[str, Any]] = None) -> None:
        from .tokens import DEFAULT_TTL_S, ConfirmTokens
        self.specs = dict(specs)
        self.port = int(port)
        self.host = host
        self.prober = prober or Prober()
        self.runner = runner or ActionRunner(prober=self.prober)
        self.tokens = tokens or ConfirmTokens(ttl_s=confirm_ttl_s)
        self.limiter = limiter or RateLimiter()
        self.audit = audit or AuditLog(audit_path or os.path.join(os.getcwd(), "state",
                                                                  "phone-panel-audit.jsonl"))
        self.audit_path = self.audit.path
        self.agent = agent
        self.session = session
        self.confirm_ttl_s = float(getattr(self.tokens, "ttl_s", DEFAULT_TTL_S))
        self.reach = reach
        self.video_meta = video_meta or {}
        self.started = time.time()

    # ------------------------------------------------------------------------------- status
    def status_document(self) -> Dict[str, Any]:
        return status_mod.build(self.specs, self.prober, port=self.port, host=self.host,
                                agent=self.agent, session=self.session, version=API_VERSION,
                                confirm_ttl_s=self.confirm_ttl_s,
                                audit_tail=self.audit.tail(8), audit_path=self.audit_path,
                                reach=self.reach, video_meta=self.video_meta,
                                extra={"rate": self.limiter.snapshot()})

    # ------------------------------------------------------------------------------- confirm
    def confirm(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Mint a confirm token for one (service, verb). Refuses for a non-destructive verb."""
        ok, why = _parse_action(body, self.specs, require_token=False)
        if not ok:
            return (why or (400, {"error": "bad request"}))
        code, spec, verb = why
        if not spec.needs_confirm(verb):
            return 400, {"error": f"{verb!r} on {spec.id!r} does not need a confirm token "
                                  f"(only {', '.join(CONFIRM_VERBS)} do)"}
        allowed, retry, reason = self.limiter.check(spec.id, verb)
        if not allowed:
            return 429, {"error": f"too many requests: {reason}", "retry_after_s": retry}
        try:
            token, expires = self.tokens.issue(spec.id, verb)
        except OverflowError as exc:
            return 429, {"error": str(exc)}
        return 200, {"ok": True, "token": token, "expires_in_s": expires,
                     "service": spec.id, "verb": verb}

    # ------------------------------------------------------------------------------- action
    def act(self, body: Dict[str, Any], *, remote: str = "127.0.0.1") -> Tuple[int, Dict[str, Any]]:
        """Perform one allowlisted verb. Every path through here leaves an audit line."""
        parsed = _parse_action(body, self.specs, require_token=True)
        if parsed[0] is False:
            code, payload = parsed[1]
            self._audit({"decision": "refused", "service": body.get("service"),
                         "verb": body.get("verb"), "ok": False,
                         "reason": payload.get("error", ""), "remote": remote})
            return code, payload
        _, spec, verb = parsed[1]

        allowed, retry, reason = self.limiter.check(spec.id, verb)
        if not allowed:
            self.limiter.note(spec.id, verb, acted=False)
            self._audit({"decision": "throttled", "service": spec.id, "verb": verb, "ok": False,
                         "reason": reason, "remote": remote})
            return 429, {"error": f"too many requests: {reason}", "retry_after_s": retry}

        if spec.needs_confirm(verb):
            token = body.get("token")
            if not isinstance(token, str) or not self.tokens.consume(token, spec.id, verb):
                self.limiter.note(spec.id, verb, acted=False)
                self._audit({"decision": "refused", "service": spec.id, "verb": verb, "ok": False,
                             "reason": "confirm token missing, used, expired or minted for another "
                                       f"service/verb (stop and restart need POST /api/confirm)",
                             "remote": remote})
                return 403, {"error": "a confirm token minted for THIS service and verb is required",
                             "confirm": f"POST /api/confirm {json.dumps({'service': spec.id, 'verb': verb})}"}
        try:
            result = self.runner.perform(spec, verb)
        except ActionRefused as exc:
            self.limiter.note(spec.id, verb, acted=False)
            self._audit({"decision": "refused", "service": spec.id, "verb": verb, "ok": False,
                         "reason": str(exc), "remote": remote})
            return 403, {"error": str(exc)}
        except Exception as exc:
            self.limiter.note(spec.id, verb, acted=True)
            self._audit({"decision": "error", "service": spec.id, "verb": verb, "ok": False,
                         "reason": f"{type(exc).__name__}: {exc}", "remote": remote})
            return 500, {"error": f"the action raised: {type(exc).__name__}: {exc}"}
        self.limiter.note(spec.id, verb, acted=True)
        audit_error = self._audit({"decision": "acted", "service": spec.id, "verb": verb,
                                   "ok": result.ok, "state": result.state,
                                   "detail": result.detail, "pids": result.pids,
                                   "elapsed_ms": result.elapsed_ms, "remote": remote})
        payload = {"ok": result.ok, **result.as_dict()}
        if audit_error:
            payload["audit"] = audit_error
        return (200 if result.ok else 502), payload

    # ------------------------------------------------------------------------------- internals
    def _audit(self, record: Dict[str, Any]) -> str:
        return self.audit.write(record)


def _parse_action(body: Any, specs: Dict[str, Any], *, require_token: bool):
    """Validate the request grammar. Returns (True, (code, spec, verb)) or (False, (code, payload)).

    THE WHOLE INJECTION DEFENCE IS HERE, and it is a schema rather than a filter: `service` is looked
    up as a KEY in the allowlist (so an unknown string has no effect at all), `verb` is checked against
    three literals, `token` is an opaque string, and ANY OTHER KEY is refused. A request that carries
    `args`, `cmd`, `path` or `shell` is refused for carrying it -- not silently ignored, because a
    client that thinks it is passing an argument should be told it is not."""
    if not isinstance(body, dict):
        return False, (400, {"error": "the body must be a JSON object"})
    unknown = sorted(set(body) - {"service", "verb", "token"})
    if unknown:
        return False, (400, {"error": f"unknown field(s) {unknown}: this API takes only service, verb"
                                      + (", token" if require_token else "")})
    service, verb = body.get("service"), body.get("verb")
    if not isinstance(service, str) or not isinstance(verb, str):
        return False, (400, {"error": "'service' and 'verb' must be strings"})
    spec = specs.get(service)
    if spec is None:
        return False, (404, {"error": f"no service {service!r} in the allowlist",
                             "known": sorted(specs)})
    if verb not in VERBS:
        return False, (403, {"error": f"{verb!r} is not a verb; this API takes "
                                      f"{', '.join(VERBS)}"})
    if verb not in spec.allowed_verbs():
        return False, (403, {"error": f"{spec.id!r} does not accept {verb!r}",
                             "allowed": list(spec.allowed_verbs()),
                             "why": spec.why_no_actions})
    return True, (200, spec, verb)


class _PanelHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False                     # a port in use fails at once, never shared
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class _PanelHandler(BaseHTTPRequestHandler):
    server_version = "AkashicPanel/" + API_VERSION
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------------------ plumbing
    def log_message(self, fmt, *args):                # quiet: the audit file is the record
        pass

    @property
    def panel(self) -> Panel:
        return self.server.panel                      # type: ignore[attr-defined]

    def _loopback_names(self) -> set:
        port = self.server.server_port
        return {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}

    def _origins(self) -> set:
        return {f"http://{n}" for n in self._loopback_names()}

    def _send(self, code: int, body: bytes, ctype: str, extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in BASE_HEADERS.items():
            self.send_header(key, value)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, code: int, obj: Any, extra: Optional[Dict[str, str]] = None) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8", extra)

    def _host_ok(self) -> bool:
        """DNS-rebinding gate (the desk-themes server's fix, adopted): 421 for a non-loopback Host."""
        if (self.headers.get("Host") or "").strip().lower() in self._loopback_names():
            return True
        self._json(421, {"error": "this panel answers only to a loopback name (127.0.0.1, localhost)"})
        return False

    # ------------------------------------------------------------------------------ GET
    def do_GET(self):
        if not self._host_ok():
            return
        path, _, query = self.path.partition("?")
        route = path.rstrip("/") or "/"
        if route in ASSETS:
            name, ctype = ASSETS[route]
            try:
                body = (WEB_DIR / name).read_bytes()
            except FileNotFoundError:
                return self._json(500, {"error": f"the page asset {name!r} is missing from {WEB_DIR}"})
            extra = {"Content-Security-Policy": CSP} if ctype.startswith("text/html") else None
            return self._send(200, body, ctype, extra)
        if route == "/api/status":
            try:
                return self._json(200, self.panel.status_document())
            except Exception as exc:                  # never drop the connection without an answer
                return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
        if route == "/api/audit":
            tail = _int_param(query, "tail", default=20, low=1, high=50)
            return self._json(200, {"tail": self.panel.audit.tail(tail),
                                    "path": self.panel.audit_path})
        if route == "/api/health":
            return self._json(200, {"ok": True, "version": API_VERSION, "port": self.panel.port,
                                    "uptime_s": round(time.time() - self.panel.started, 1),
                                    "services": len(self.panel.specs)})
        return self._json(404, {"error": f"no route {route}"})

    # ------------------------------------------------------------------------------ POST
    def do_POST(self):
        # read the body FIRST, bounded: answering a refusal while the client is still sending makes
        # Windows reset the connection and the client sees ConnectionAborted instead of the answer.
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        raw = self.rfile.read(n) if 0 < n <= MAX_BODY else b""
        if not self._host_ok():
            return
        route = (self.path.partition("?")[0]).rstrip("/")
        origin = (self.headers.get("Origin") or "").strip().lower()
        if origin and origin not in self._origins():
            return self._json(403, {"error": "another origin may not drive this PC"})
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._json(415, {"error": "send JSON (Content-Type: application/json)"})
        if n < 0:
            return self._json(400, {"error": "bad Content-Length"})
        if n > MAX_BODY:
            return self._json(413, {"error": "body too large"})
        try:
            body = json.loads(raw.decode("utf-8") or "{}") if n else {}
        except ValueError:
            return self._json(400, {"error": "body is not valid JSON"})
        remote = self.client_address[0] if self.client_address else "?"
        if route == "/api/confirm":
            code, payload = self.panel.confirm(body)
            return self._json(code, payload)
        if route == "/api/action":
            code, payload = self.panel.act(body, remote=remote)
            extra = ({"Retry-After": str(int(payload["retry_after_s"]))}
                     if code == 429 and "retry_after_s" in payload else None)
            return self._json(code, payload, extra)
        return self._json(404, {"error": f"no route {route}"})


def _int_param(query: str, key: str, *, default: int, low: int, high: int) -> int:
    for pair in (query or "").split("&"):
        k, _, v = pair.partition("=")
        if k == key:
            try:
                return max(low, min(high, int(v)))
            except ValueError:
                return default
    return default


class PanelServer:
    """Bind, serve, stop. The bind is loopback-only and REFUSES to be anything else."""

    def __init__(self, panel: Panel, *, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(
                f"the panel serves loopback only; refusing to bind {host!r}. This API starts and "
                f"stops processes -- publishing it to a tailnet address is a different decision than "
                f"the one that was made, and it is not made here.")
        self.httpd = _PanelHTTPServer((host, port), _PanelHandler)
        self.httpd.panel = panel                      # type: ignore[attr-defined]
        panel.port = self.httpd.server_port
        self.port = self.httpd.server_port
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "PanelServer":
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="phone-panel",
                                        daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._thread is not None:
            self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(2.0)
