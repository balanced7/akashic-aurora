"""Clickable, local practice excerpts. Reuses pianocue's MIDI reconstruction; never broadcasts cues.

py -m arsenal.replay serve                       # read-only player on localhost:8796
py -m arsenal.pianocue replay-link latest 3:43 --seconds 12 --label "The A bass"
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from .performance import PerformanceError, PerformanceStore
from .pianocue import build_replay_cue, clock_text, parse_clock, validate_cue, _utf8_streams
from .replay_harmony import harmony, theory_module

DEFAULT_PORT = 8796
WEB = Path(__file__).resolve().parent / "web"
ASSETS = {
    "/": ("replay.html", "text/html; charset=utf-8"),
    "/web/replay.html": ("replay.html", "text/html; charset=utf-8"),
    "/web/piano/replay.js": ("piano/replay.js", "text/javascript; charset=utf-8"),
    "/web/piano/replay.css": ("piano/replay.css", "text/css; charset=utf-8"),
    "/web/piano/cues.js": ("piano/cues.js", "text/javascript; charset=utf-8"),
    "/web/conversation.html": ("conversation.html", "text/html; charset=utf-8"),
    "/web/piano/conversation.js": ("piano/conversation.js", "text/javascript; charset=utf-8"),
    "/web/piano/conversation.css": ("piano/conversation.css", "text/css; charset=utf-8"),
}


def excerpt(store, session, at, seconds=8.0, speed=1.0):
    """Read a bounded excerpt. Resolve 'latest' now so a saved link cannot drift to another take."""
    if not math.isfinite(seconds) or not 0.1 <= seconds <= 60:
        raise ValueError("seconds must be between 0.1 and 60")
    if not math.isfinite(speed) or not 0.25 <= speed <= 2:
        raise ValueError("speed must be between 0.25 and 2")
    start = parse_clock(at)
    session = store.latest() if session == "latest" else session
    if not session:
        raise ValueError("no practice session found")
    events = store.events(session)
    end = start + round(seconds * 1000)
    recorded_end = max((event["t_ms"] for event in events), default=0)
    if end > recorded_end:
        raise ValueError(f"excerpt ends beyond the logged take ({clock_text(recorded_end)}); shorten --seconds")
    cue = validate_cue(build_replay_cue(events, start, seconds, speed, at_text=at, session=session))
    return {"session": session, "start_ms": start, "end_ms": end, "seconds": seconds, "speed": speed,
            "cue": cue, "sound": "MIDI reconstruction with the built-in keys voice; not recorded piano audio"}


def link(session, at, seconds=8.0, speed=1.0, label=None, port=DEFAULT_PORT, root=None):
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    data = excerpt(PerformanceStore(root), session, at, seconds, speed)
    label = (label or "Replay this passage").strip()
    if not label or len(label) > 160 or any(ord(c) < 32 for c in label):
        raise ValueError("label must be 1-160 characters on one line")
    query = urlencode({"session": data["session"], "at": at, "seconds": f"{seconds:g}",
                       "speed": f"{speed:g}", "label": label})
    url = f"http://127.0.0.1:{port}/web/replay.html?{query}"
    title = f"{label} · {clock_text(data['start_ms'])}–{clock_text(data['end_ms'])}"
    escaped = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return {"url": url, "markdown": f"[{escaped}]({url})", "session": data["session"],
            "start_ms": data["start_ms"], "end_ms": data["end_ms"], "speed": speed,
            "steps": len(data["cue"]["steps"])}


def add_verb(subparsers):
    p = subparsers.add_parser("replay-link", help="make a clickable excerpt link; plays only when clicked")
    p.add_argument("session", help="a session id, or latest (resolved to a fixed take)")
    p.add_argument("at", help="start time, m:ss")
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--label", help="what to listen for")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="replay server port (default 8796)")
    p.add_argument("--root", help="practice sessions directory")
    p.add_argument("--json", action="store_true")


def run_link(args, out):
    try:
        result = link(args.session, args.at, args.seconds, args.speed, args.label, args.port, args.root)
    except (ValueError, PerformanceError, OSError) as exc:
        print(f"cannot make replay link: {exc}", file=out)
        return 2
    print(json.dumps(result, ensure_ascii=False) if args.json else result["markdown"], file=out)
    return 0


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, data, content_type="application/json"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/api/health":
            return self._send(200, {"ok": True, "api": "arsenal.replay/v1", "conversation": 1, "chords": 1})
        if url.path == "/web/piano/replay-theory.js":
            return self._send(200, theory_module(WEB / "piano.js"), "text/javascript; charset=utf-8")
        if url.path in ASSETS:
            file, content_type = ASSETS[url.path]
            return self._send(200, (WEB / file).read_bytes(), content_type)
        if url.path == "/api/conversation":
            return self._send(200, {**self.server.conversation.cards(), "responses": self.server.conversation.responses()})
        if url.path.startswith("/api/conversation/replay/"):
            try:
                data = self.server.conversation.response(url.path.rsplit("/", 1)[-1])["replay"]
                return self._send(200, {**data, "chords": harmony(data["cue"], data.get("speed", 1))})
            except (ValueError, OSError) as exc:
                return self._send(404, {"error": str(exc)})
        if url.path == "/api/piano/replay":
            q = parse_qs(url.query)
            get = lambda key, default="": q.get(key, [default])[0]
            try:
                result = excerpt(self.server.performance, get("session"), get("at"),
                                 float(get("seconds", "8")), float(get("speed", "1")))
                return self._send(200, {**result, "chords": harmony(result["cue"], result["speed"])})
            except PerformanceError as exc:
                return self._send(getattr(exc, "status", 404), {"error": str(exc)})
            except (ValueError, OSError) as exc:
                return self._send(400, {"error": str(exc)})
        self._send(404, {"error": "no such replay resource"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/conversation/responses":
            return self._send(404, {"error": "no such conversation action"})
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_address[1]}":
            return self._send(403, {"error": "save answers from this player"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("response body must be 1-16384 bytes")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("response must be application/json")
            body = json.loads(self.rfile.read(length))
            data = self.server.conversation.save_response(body)
            return self._send(200, {k: v for k, v in data.items() if k != "replay"})
        except (ValueError, PerformanceError, OSError) as exc:
            return self._send(400, {"error": str(exc)})

    def log_message(self, fmt, *args):
        # No query strings/session identifiers in service access logs.
        sys.stderr.write(f"[replay] {self.command} {urlsplit(self.path).path}\n")


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, port=DEFAULT_PORT, root=None, conversation_root=None):
        self.performance = PerformanceStore(root)
        from .conversation import ConversationStore
        self.conversation = ConversationStore(conversation_root, self.performance)
        super().__init__(("127.0.0.1", port), Handler)


def main(argv=None):
    _utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    p = sub.add_parser("serve", help="serve the read-only replay player")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--root", help="practice sessions directory")
    p.add_argument("--conversation-root", help="private conversation card and response directory")
    for name in ("cards", "responses"):
        p = sub.add_parser(name, help="read question cards or saved musical answers")
        p.add_argument("--root", help="practice sessions directory")
        p.add_argument("--conversation-root", help="private conversation directory")
        p.add_argument("--json", action="store_true")
        if name == "cards":
            p.add_argument("--from-json", help="publish a validated private card collection")
    add_verb(sub)
    args = ap.parse_args(argv)
    if args.verb == "replay-link":
        return run_link(args, sys.stdout)
    if args.verb in ("cards", "responses"):
        from .conversation import ConversationStore
        store = ConversationStore(args.conversation_root, PerformanceStore(args.root))
        try:
            if args.verb == "cards":
                data = store.publish(json.loads(Path(args.from_json).read_text(encoding="utf-8"))) if args.from_json else store.cards()
            else:
                data = {"responses": store.responses()}
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        except (ValueError, OSError, PerformanceError) as exc:
            print(f"conversation: {exc}", file=sys.stderr)
            return 2
    with Server(args.port, args.root, args.conversation_root) as server:
        print(f"Replay player: http://127.0.0.1:{server.server_address[1]}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
