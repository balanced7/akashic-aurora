"""Remote bridge listener — the HTTP door in front of the inbound gate (v1).

Design: docs/library/design/remote-bifrost-bridge-design.md §3.3. Pins:
tests/test_remote_bridge_listener_pins.py (all offline — the handler is a pure function and
the socket server is a thin shell over it).

THIS IS THE DANGEROUS HALF, and the design says so in its own §5: "the entire danger
concentrates at v1. A remote peer that can speak `chat` into our bus can try to talk an agent
into running commands." Everything below is written to keep that sentence false.

THE DIVISION OF LABOUR. core/comm/remote_relay.accept() decides ADMISSION — is this envelope
authentic, fresh, and of a kind we accept. This module decides EXPOSURE — who can reach the
door at all, how much they may make us allocate, and what they learn when refused. Two
questions, and conflating them is how a correct gate ends up behind an open door.

THE ASYMMETRY, because it reads as a violation of house style until you see who the reader is.
This repo's error doctrine is errors-that-teach, and accept() honours it with long, specific
refusals. Those go to the LOG. The WIRE gets one flat refusal, identical for a forged
signature, a stale replay, a control kind and a malformed body — because a distinct message
per failure makes an unauthenticated endpoint an ORACLE. Probe it and you learn whether the
key is wrong, whether it is merely stale, whether the kind you tried exists. Errors-that-teach
is a rule about the reader; across a fleet boundary the reader is not necessarily a friend.

WHAT THIS DOOR DELIBERATELY CANNOT DO:
  - it cannot be reached from outside the machine unless someone TYPED --allow-public
  - it has one verb on one path; everything else is 404/405 with no hint
  - it never puts anything on the live bus (accept() parks; an agent drains deliberately)
  - it never raises, so a malformed byte is not a denial of service
  - it is inert until keyed: started without the inbound key, it refuses everything

Run:
  py scripts/remote_bridge_listener.py                    # 127.0.0.1:8791, the safe default
  py scripts/remote_bridge_listener.py --port 9000
  py scripts/remote_bridge_listener.py --host 0.0.0.0 --allow-public   # deliberate, logged
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402

#: Loopback. THE DEFAULT IS THE POLICY — nobody reads flag docs before the first run, and this
#: machine runs with Defender disabled and Windows Update blocked by choice, so an
#: all-interfaces default is one absent-minded launch from an open door on an unpatched box.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8791

#: A bridge envelope is a few KB. The cap is checked against the DECLARED Content-Length before
#: any read, so a claimed 4GB body costs one comparison instead of 4GB of allocation.
MAX_BODY_BYTES = 256 * 1024

#: The ONE refusal the wire ever sees. Names no policy, no peer, no mechanism — see the module
#: docstring on why this is not a violation of errors-that-teach but an application of it.
FLAT_REFUSAL: Dict[str, str] = {"status": "refused"}

_ACCEPTED = {"status": "accepted"}


def bind_allowed(host: str, *, allow_public: bool) -> Tuple[bool, str]:
    """May we bind here? Non-loopback is REFUSED unless opted into by name.

    A flag that merely warns is a flag that gets ignored, and the dangerous case must not be
    reachable by a typo or a copy-pasted command line. Loopback is always fine — that is the
    tunnel-terminated shape (ssh -L / Tailscale / cloudflared), which is also how the peer
    should reach us in production: let a real tunnel own the transport security and keep this
    door facing an interface only the machine itself can speak to.
    """
    local = host in ("127.0.0.1", "localhost", "::1")
    if local or allow_public:
        return True, ""
    return False, (
        f"refusing to bind {host!r}: that is a PUBLIC interface and this is the inbound half "
        f"of a fleet bridge. Re-run with --allow-public if you meant it, or (better) bind "
        f"loopback and put a tunnel in front so the transport security is owned by something "
        f"built for it.")


def length_allowed(declared: int) -> bool:
    """Cap by DECLARED length, before reading. Refusing after the read is not a refusal."""
    try:
        return 0 <= int(declared) <= MAX_BODY_BYTES
    except (TypeError, ValueError):
        return False


def handle_request(method: str, path: str, body: bytes, *,
                   secret: Optional[bytes] = None, peer: str = "",
                   ) -> Tuple[int, Dict[str, Any], str]:
    """The whole door as a PURE FUNCTION: (status, wire_body, log_line). NEVER RAISES.

    Pure so the pins run with no port, no thread and no network. A listener whose tests need a
    live socket is a listener whose tests get skipped and rot — the discord_bridge precedent.
    """
    try:
        if str(path).split("?")[0].rstrip("/") not in ("/xfer",):
            return 404, FLAT_REFUSAL, f"404 no such path {path!r}"
        if str(method).upper() != "POST":
            return 405, FLAT_REFUSAL, f"405 method {method!r} on /xfer (POST only)"
        if not length_allowed(len(body or b"")):
            return 413, FLAT_REFUSAL, (
                f"413 body {len(body or b'')}B over the {MAX_BODY_BYTES}B cap")

        try:
            envelope = json.loads((body or b"").decode("utf-8"))
        except Exception as e:                                    # noqa: BLE001
            return 400, FLAT_REFUSAL, f"400 unreadable envelope ({type(e).__name__}: {e})"

        out = RR.accept(envelope, secret=secret, peer=peer)
        if not out.ok:
            # The teaching reason goes HERE and only here.
            return 400, FLAT_REFUSAL, f"400 refused by the gate: {out.why}"
        return 202, _ACCEPTED, f"202 admitted {out.ref} from remote:{peer or 'peer'}"
    except Exception as e:                                        # noqa: BLE001
        # A listener that raises is a denial of service with a one-line exploit, and this one
        # is reachable by anyone who can route to the port. There is no input that gets a
        # traceback out of this function.
        return 400, FLAT_REFUSAL, f"400 handler caught {type(e).__name__}: {e}"


class _Handler(BaseHTTPRequestHandler):
    server_version = "akashic-bridge/1.0"
    peer_name = ""

    def _respond(self, status: int, payload: Dict[str, Any], log: str) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except OSError:
            pass
        print(f"[{time.strftime('%H:%M:%S')}] {self.client_address[0]} {log}", flush=True)

    def do_POST(self) -> None:                                    # noqa: N802
        declared = self.headers.get("Content-Length") or 0
        if not length_allowed(declared):
            self._respond(413, FLAT_REFUSAL, f"413 declared length {declared} refused unread")
            return
        try:
            body = self.rfile.read(int(declared))
        except (OSError, ValueError) as e:
            self._respond(400, FLAT_REFUSAL, f"400 body read failed ({type(e).__name__}: {e})")
            return
        self._respond(*handle_request("POST", self.path, body, peer=self.peer_name))

    def do_GET(self) -> None:                                     # noqa: N802
        self._respond(*handle_request("GET", self.path, b"", peer=self.peer_name))

    def log_message(self, fmt, *args):
        """Silence the stdlib's own line — _respond already prints one we control."""


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *,
          allow_public: bool = False, peer: str = "") -> int:
    ok, why = bind_allowed(host, allow_public=allow_public)
    if not ok:
        print(why, file=sys.stderr)
        return 2

    peer = peer or str((RR._config().get("peer") or {}).get("name") or "")
    if not RR._secret(RR.INBOUND_KEY_FILE):
        # Started, and honestly useless. Loud, because a listener that looks up but refuses
        # everything is the exact shape of "green receipt over a broken path" this house spent
        # a 2h44m outage learning to hate.
        print("WARNING: no inbound secret found — this listener is INERT and will refuse "
              "every message. Drop remote_bridge_inbound.key into .secrets/ (py agent_cli.py "
              "secret) and restart.", file=sys.stderr)

    _Handler.peer_name = peer
    httpd = ThreadingHTTPServer((host, port), _Handler)
    print(f"akashic remote-bridge listener on http://{host}:{port}/xfer  peer={peer or '?'}"
          f"{'  [PUBLIC]' if host not in ('127.0.0.1', 'localhost', '::1') else ''}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nlistener stopped", flush=True)
    finally:
        httpd.server_close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Akashic remote-bridge inbound listener (v1)")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--peer", default="", help="route name for provenance (default: config)")
    ap.add_argument("--allow-public", action="store_true",
                    help="permit a non-loopback bind — say it out loud or it is refused")
    a = ap.parse_args(argv)
    return serve(a.host, a.port, allow_public=a.allow_public, peer=a.peer)


if __name__ == "__main__":
    raise SystemExit(main())
