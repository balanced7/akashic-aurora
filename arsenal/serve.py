"""Local HTTP server for First Light. Binds 127.0.0.1 only and uses only the standard library.

The routes are listed in arsenal/FIRST-LIGHT-SPEC.md. Media is served only for clips found under
the configured library roots, addressed by id, with HTTP Range support so the browser can seek.
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import select
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .graph import GraphError, load_graph
from .performance import SESSION_PATTERN, PerformanceError, PerformanceStore
from .jam.runs import JamApi
from .pianocue import MAX_CUE_BODY, CueError, CueHub, validate_cue
from .plan import make_plan, render_plan
from .presets import list_presets
from .registry import load_registry
from .take import TakeLedger
from .timebase import StaleEpoch

HOST = "127.0.0.1"
PACKAGE = Path(__file__).resolve().parent
WEB = PACKAGE / "web"
GRAPHS = PACKAGE / "graphs"
DEFAULT_ROOTS = [r"E:\Video Output E"]
MEDIA_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime",
               ".webm": "video/webm", ".mkv": "video/x-matroska"}
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".json": "application/json", ".frag": "text/plain; charset=utf-8",
                ".vert": "text/plain; charset=utf-8", ".glsl": "text/plain; charset=utf-8",
                ".svg": "image/svg+xml", ".png": "image/png"}
MAX_CLIPS = 500
MAX_BODY = 16 * 1024 * 1024
CHUNK = 1024 * 1024
RECORDINGS_DIR = "arsenal-renders"
RECORDING_TYPES = {"video/webm": ".webm", "video/mp4": ".mp4", "video/x-matroska": ".mkv"}
MAX_RECORDING = 4 * 1024 ** 3
_ID = r"[0-9a-f]{16}"
_TAKE = r"\d{8}-\d{6}-[0-9a-f]{8}"


def _is_jam_path(path: str) -> bool:
    return path == "/api/piano/replay" or path == "/api/piano/deck" or path.startswith("/api/piano/deck/") or \
        path == "/api/piano/jam" or path.startswith("/api/piano/jam/")


def clip_id_for(path) -> str:
    return hashlib.sha1(str(Path(path).resolve()).lower().encode("utf-8")).hexdigest()[:16]


class Library:
    """Media files under the library roots, rescanned at most every ten seconds."""

    def __init__(self, roots: List[str]):
        self.roots = [Path(r).resolve() for r in roots]
        self._clips: Dict[str, dict] = {}
        self._scanned = 0.0
        self._lock = threading.Lock()

    def _scan(self, force: bool = False) -> None:
        with self._lock:
            if not force and self._clips and time.monotonic() - self._scanned < 10:
                return
            found = []
            for root in self.roots:
                if not root.is_dir():
                    continue
                for dirpath, _dirs, files in os.walk(root):
                    for name in files:
                        path = Path(dirpath) / name
                        if path.suffix.lower() not in MEDIA_TYPES:
                            continue
                        try:
                            st = path.stat()
                        except OSError:
                            continue
                        found.append({"id": clip_id_for(path), "name": name, "path": str(path),
                                      "size": st.st_size, "mtime": int(st.st_mtime),
                                      "ext": path.suffix.lower().lstrip(".")})
            found.sort(key=lambda c: c["mtime"], reverse=True)
            self._clips = {c["id"]: c for c in found[:MAX_CLIPS]}
            self._scanned = time.monotonic()

    def clips(self) -> List[dict]:
        self._scan()
        return sorted(self._clips.values(), key=lambda c: c["mtime"], reverse=True)

    def get(self, clip_id: str) -> Optional[dict]:
        self._scan()
        if clip_id not in self._clips:
            self._scan(force=True)
        return self._clips.get(clip_id)

    def resolve(self, name: str, size: int) -> Optional[dict]:
        for attempt in (False, True):
            self._scan(force=attempt)
            for clip in self._clips.values():
                if clip["name"] == name and clip["size"] == size:
                    return clip
        return None


class Jobs:
    """Background feature analysis per clip: 202 while computing, 200 when ready, 500 once on error."""

    def __init__(self):
        self._jobs: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def features(self, clip: dict) -> Tuple[int, dict]:
        with self._lock:
            job = self._jobs.get(clip["id"])
            if job is None:
                job = {"status": "computing", "progress": 0.0}
                self._jobs[clip["id"]] = job
                threading.Thread(target=self._run, args=(clip, job), daemon=True,
                                 name=f"features-{clip['id']}").start()
            if job["status"] == "ready":
                return 200, {"status": "ready", "features": job["features"]}
            if job["status"] == "error":
                del self._jobs[clip["id"]]  # the next request retries
                return 500, {"status": "error", "error": job["error"]}
            return 202, {"status": "computing", "progress": round(job["progress"], 3)}

    @staticmethod
    def _run(clip: dict, job: dict) -> None:
        try:
            from . import analysis  # imported lazily: PyAV is heavy, and the page works without it

            def progress(value):
                job["progress"] = max(0.0, min(1.0, float(value)))

            job["features"] = analysis.audio_features(clip["path"], progress=progress)
            job["status"] = "ready"
        except Exception as exc:  # the page declares the degradation
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["status"] = "error"


class App:
    def __init__(self, roots: List[str], takes_root=None, presets_dir=None, performance_root=None,
                 performance_log: bool = True, jam_root=None):
        self.presets_dir = presets_dir
        self.registry = load_registry()
        self.library = Library(roots)
        self.ledger = TakeLedger(takes_root)
        # None switches the practice-log routes off: they answer 404 "no route", like a server from before them.
        self.performance = PerformanceStore(performance_root) if performance_log else None
        self.jobs = Jobs()
        self.probes: Dict[str, dict] = {}
        self.cues = CueHub()  # Claude's hand on the piano page (arsenal/pianocue.py)
        # The jam space: deck, runs and their routes (arsenal/jam). Its files sit beside the practice log's
        # (state/arsenal/jam by default; <performance root>/../jam for a server given --performance-root). Nothing is
        # read or written until a jam route is used; serve() closes runs a previous server left open.
        if jam_root is None and performance_root is not None:
            jam_root = Path(performance_root).resolve().parent / "jam"
        self.jam = JamApi(root=jam_root, performance=self.performance, hub=lambda: self.cues)


class Handler(BaseHTTPRequestHandler):
    server_version = f"arsenal/{__version__}"
    protocol_version = "HTTP/1.1"

    @property
    def app(self) -> App:
        return self.server.app

    def log_message(self, fmt, *args):
        if "/api/media/" in self.path or "/api/analysis/" in self.path:
            return  # seeks and polls are chatty
        if self.path.startswith("/api/performance/") and self.path.endswith("/events") and args[1:2] == ("200",):
            return  # the practice log flushes every second while Daniel plays
        sys.stderr.write(f"[arsenal] {fmt % args}\n")

    # ----------------------------------------------------------------- responses
    def _send(self, status: int, body: bytes, content_type: str, headers: Optional[dict] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj, default=str).encode("utf-8"), "application/json")

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw.decode("utf-8") or "null")

    # -------------------------------------------------------------------- routing
    def do_HEAD(self):
        self._route("GET")

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def _route(self, method: str) -> None:
        url = urlsplit(self.path)
        path, query = url.path, parse_qs(url.query)
        try:
            if method == "GET":
                if path == "/":
                    self.send_response(302)
                    self.send_header("Location", "/first-light")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if path == "/favicon.ico":
                    return self._send(204, b"", "image/x-icon")
                if path == "/first-light":
                    return self._static(WEB / "first-light.html")
                if path == "/play":
                    return self._static(WEB / "play.html")
                if path == "/piano":
                    return self._static(WEB / "piano.html")
                if path.startswith("/web/"):
                    return self._static_under(unquote(path[len("/web/"):]))
                if path == "/api/health":
                    return self._json(200, {"ok": True, "api": "arsenal.serve/v0", "version": __version__})
                if path == "/api/library":
                    return self._json(200, {"roots": [str(r) for r in self.app.library.roots],
                                            "clips": self.app.library.clips()})
                if path == "/api/resolve":
                    return self._resolve(query)
                if path == "/api/takes":
                    return self._json(200, {"takes": self.app.ledger.list()})
                if path == "/api/presets":
                    return self._json(200, {"presets": list_presets(self.app.presets_dir)})
                if path == "/api/piano/cues":
                    return self._cue_stream(query)
                if path == "/api/piano/cues/status":
                    return self._json(200, self.app.cues.status())
                if _is_jam_path(path):
                    return self._jam_route("GET", path, query)
                logging = self.app.performance is not None
                if path == "/api/performance" and logging:
                    return self._json(200, {"sessions": self.app.performance.list()})
                routes = [(rf"/api/media/({_ID})", self._media),
                          (rf"/api/probe/({_ID})", lambda cid: self._probe(cid, query)),
                          (rf"/api/analysis/({_ID})", self._analysis),
                          (r"/api/graph/([A-Za-z0-9_-]+)", self._graph),
                          (rf"/api/take/({_TAKE})", self._take_get)]
                if logging:
                    routes.append((rf"/api/performance/({SESSION_PATTERN})", self._performance_get))
                for pattern, handler in routes:
                    m = re.fullmatch(pattern, path)
                    if m:
                        return handler(m.group(1))
            elif method == "POST":
                if path == "/api/plan":
                    return self._plan()
                if path == "/api/recordings":
                    return self._recording(query)
                if path == "/api/take/open":
                    return self._take_open()
                if path == "/api/piano/cue":
                    return self._cue_post()
                if _is_jam_path(path):
                    return self._jam_route("POST", path, query)
                m = re.fullmatch(rf"/api/take/({_TAKE})/(events|close)", path)
                if m:
                    return self._take_post(m.group(1), m.group(2))
                if self.app.performance is not None:
                    if path == "/api/performance/open":
                        return self._performance_post(None, "open")
                    m = re.fullmatch(rf"/api/performance/({SESSION_PATTERN})/(events|close)", path)
                    if m:
                        return self._performance_post(m.group(1), m.group(2))
            return self._json(404, {"error": f"no route for {method} {path}"})
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return  # the browser cancelled, usually a seek
        except Exception as exc:
            try:
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            except OSError:
                pass

    # --------------------------------------------------------------------- static
    def _static(self, file: Path) -> None:
        if not file.is_file():
            if file.parent == WEB and file.suffix == ".html":
                return self._json(503, {"error": f"the {file.stem} page is not built yet"})
            return self._json(404, {"error": "not found"})
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_TYPES.get(file.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _static_under(self, rel: str) -> None:
        target = (WEB / rel).resolve()
        if not target.is_relative_to(WEB):
            return self._json(404, {"error": "not found"})
        return self._static(target)

    # ---------------------------------------------------------------------- media
    def _media(self, clip_id: str) -> None:
        clip = self.app.library.get(clip_id)
        if not clip:
            return self._json(404, {"error": "no such clip in the library roots"})
        path = Path(clip["path"])
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        header = self.headers.get("Range")
        if header:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
            if not m or (m.group(1) == "" and m.group(2) == ""):
                return self._unsatisfiable(size)
            if m.group(1) == "":
                start = max(0, size - int(m.group(2)))
            else:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            end = min(end, size - 1)
            if start >= size or start > end:
                return self._unsatisfiable(size)
            status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(CHUNK, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _unsatisfiable(self, size: int) -> None:
        self.send_response(416)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _resolve(self, query) -> None:
        name = (query.get("name") or [""])[0]
        size = (query.get("size") or [""])[0]
        if not name or not size.isdigit():
            return self._json(400, {"error": "resolve needs name and size"})
        clip = self.app.library.resolve(name, int(size))
        if not clip:
            return self._json(404, {"error": "not in library roots",
                                    "roots": [str(r) for r in self.app.library.roots]})
        return self._json(200, {"clip": clip})

    def _probe(self, clip_id: str, query) -> None:
        clip = self.app.library.get(clip_id)
        if not clip:
            return self._json(404, {"error": "no such clip in the library roots"})
        from . import analysis
        want_hw = (query.get("hw") or ["0"])[0] == "1"
        key = f"{clip_id}:{clip['size']}:{clip['mtime']}:{int(want_hw)}"
        if key not in self.app.probes:
            result = analysis.probe(clip["path"])
            if want_hw:
                result["hwdecode"] = analysis.hw_decode_evidence(clip["path"])
            result["clip_id"] = clip_id
            self.app.probes[key] = result
        return self._json(200, self.app.probes[key])

    def _analysis(self, clip_id: str) -> None:
        clip = self.app.library.get(clip_id)
        if not clip:
            return self._json(404, {"error": "no such clip in the library roots"})
        status, body = self.app.jobs.features(clip)
        return self._json(status, body)

    # ------------------------------------------------------------ graphs, plans
    def _graph(self, name: str) -> None:
        file = GRAPHS / f"{name}.json"
        if not file.is_file():
            return self._json(404, {"error": f"no graph {name!r}"})
        return self._json(200, json.loads(file.read_text(encoding="utf-8")))

    def _plan(self) -> None:
        try:
            obj = self._read_json()
        except ValueError as exc:
            return self._json(400, {"problems": [f"the body is not JSON: {exc}"]})
        if isinstance(obj, dict) and "api" not in obj and isinstance(obj.get("graph"), dict):
            obj = obj["graph"]  # the {"graph": ...} envelope that /api/take/open also uses
        try:
            plan = make_plan(load_graph(obj), self.app.registry)
        except GraphError as exc:
            return self._json(400, {"problems": exc.problems})
        return self._json(200, {"plan": plan, "text": render_plan(plan)})

    # ----------------------------------------------------------------------- takes
    def _take_open(self) -> None:
        try:
            body = self._read_json() or {}
            graph = load_graph(body.get("graph"))
            plan = make_plan(graph, self.app.registry)
        except GraphError as exc:
            return self._json(400, {"problems": exc.problems})
        except ValueError as exc:
            return self._json(400, {"problems": [str(exc)]})
        meta = dict(body.get("meta") or {})
        clip_id = body.get("clip_id")
        clip = self.app.library.get(clip_id) if isinstance(clip_id, str) and re.fullmatch(_ID, clip_id) else None
        if clip:
            meta.update(clip_id=clip["id"], clip_name=clip["name"], clip_path=clip["path"],
                        clip_size=clip["size"], clip_mtime=clip["mtime"])
        elif clip_id:
            meta.update(clip_id=clip_id, clip_outside_library=True)
        return self._json(200, {"take_id": self.app.ledger.open(graph.to_json(), plan, meta)})

    def _take_post(self, take_id: str, action: str) -> None:
        try:
            body = self._read_json() or {}
        except ValueError as exc:
            return self._json(400, {"error": f"the body is not JSON: {exc}"})
        try:
            if action == "events":
                return self._json(200, {"accepted": self.app.ledger.append(take_id, body.get("events") or [])})
            self.app.ledger.close(take_id, body.get("summary") or {})
            return self._json(200, {"ok": True})
        except StaleEpoch as exc:
            return self._json(409, {"error": str(exc)})
        except KeyError as exc:
            if exc.args and exc.args[0] == take_id:
                return self._json(404, {"error": f"no take {take_id}"})
            return self._json(400, {"error": f"an event is missing {exc}"})
        except (ValueError, TypeError) as exc:
            return self._json(409 if "closed" in str(exc) else 400, {"error": str(exc)})

    def _take_get(self, take_id: str) -> None:
        try:
            return self._json(200, self.app.ledger.load(take_id))
        except KeyError:
            return self._json(404, {"error": f"no take {take_id}"})

    # ------------------------------------------------------------ practice log
    def _performance_post(self, session: Optional[str], action: str) -> None:
        """open, events and close (PIANO-V2-SPEC section 4): 400 malformed, 404 unknown, 409 closed.

        Optional for uploads that must not double up (the browser's offline buffer): open takes client_id and
        answers {session, resumed, closed, last_seq}; events and close take seq, and events answers
        {accepted, duplicate, last_seq}. A 409 carries last_seq.
        """
        try:
            body = self._read_json()
        except ValueError as exc:
            return self._json(400, {"error": f"the body is not JSON: {exc}"})
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return self._json(400, {"error": "the body must be a JSON object"})
        store = self.app.performance
        try:
            if action == "open":
                return self._json(200, store.open_session(body.get("meta"), body.get("client_id")))
            if action == "events":
                if "events" not in body:
                    return self._json(400, {"error": "the body needs events, a list"})
                return self._json(200, store.append_batch(session, body["events"], body.get("seq")))
            # close may carry the last events: the pagehide beacon sends both in one request
            return self._json(200, {"summary": store.close(session, body.get("events"), body.get("seq"))})
        except PerformanceError as exc:
            return self._json(exc.status, {"error": str(exc), **exc.extra})

    def _performance_get(self, session: str) -> None:
        try:
            return self._json(200, self.app.performance.get(session))
        except PerformanceError as exc:
            return self._json(exc.status, {"error": str(exc)})

    # --------------------------------------------------------------- piano cues
    def _cue_post(self) -> None:
        """POST /api/piano/cue {"cue": CUE}: 200 {id, listeners}, 400 malformed, 403 from another site.

        The body is always read first, so a refused request leaves the keep-alive connection usable.
        """
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = True
            return self._json(400, {"error": "Content-Length is not a number"})
        if length > MAX_CUE_BODY:
            self.close_connection = True  # the body stays unread, so this connection cannot be reused
            return self._json(413, {"error": f"a cue body is at most {MAX_CUE_BODY} bytes"})
        raw = self.rfile.read(length) if length > 0 else b""
        origin = self.headers.get("Origin")
        if origin is not None and urlsplit(origin).hostname not in ("127.0.0.1", "localhost"):
            return self._json(403, {"error": f"cues are accepted from this machine's pages only, not {origin}"})
        try:
            body = json.loads(raw.decode("utf-8") or "null")
        except ValueError as exc:
            return self._json(400, {"error": f"the body is not JSON: {exc}"})
        if not isinstance(body, dict) or "cue" not in body:
            return self._json(400, {"error": 'the body must be {"cue": {...}}'})
        try:
            cue = validate_cue(body["cue"])
        except CueError as exc:
            return self._json(400, {"error": str(exc)})
        return self._json(200, self.app.cues.publish(cue))

    def _cue_stream(self, query: Optional[dict] = None) -> None:
        """GET /api/piano/cues: an event stream held open on this connection's own thread until the page goes away.

        The Last-Event-ID header wins; ?lastEventId=N is the fallback for a page that had to open a fresh EventSource
        (which cannot set the header)."""
        hub = self.app.cues
        last_event_id = None
        header = (self.headers.get("Last-Event-ID") or "").strip()
        if not header and query:
            header = ((query.get("lastEventId") or [""])[0]).strip()
        if re.fullmatch(r"\d{1,18}", header):
            last_event_id = int(header)
        # a jam page announces itself: ?caps=jam1,deck1&page=<page id> (the hub keeps only well-formed values)
        caps = tuple(c for c in ((query or {}).get("caps") or [""])[0].split(",") if c)[:8]
        page_id = ((query or {}).get("page") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.close_connection = True  # no Content-Length: the stream ends when the connection does
        if self.command == "HEAD":
            return
        token, inbox, preamble = hub.open_stream(last_event_id, caps, page_id)
        try:
            self.wfile.write(preamble)  # "retry: 1000", an id: cursor, then any replayed cues
            last_write = time.monotonic()
            while True:
                try:
                    frame = inbox.get(timeout=0.25)
                except queue.Empty:
                    frame = b""
                if frame is None:
                    return  # the hub closed
                if frame:
                    self.wfile.write(frame)
                    last_write = time.monotonic()
                elif time.monotonic() - last_write >= hub.heartbeat_s:
                    self.wfile.write(b": hb\n\n")
                    last_write = time.monotonic()
                if self._peer_gone():
                    return
        except (OSError, ValueError):
            return  # the page went away mid-write
        finally:
            hub.unsubscribe(token)

    def _jam_route(self, method: str, path: str, query) -> None:
        """The deck, jam and replay routes (jam-spec 5), answered by arsenal/jam/runs.py JamApi. A POST is read and
        checked as a cue post is: the 2 MB cap, the same-machine origin check, a JSON object."""
        body = None
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self.close_connection = True
                return self._json(400, {"error": "Content-Length is not a number"})
            if length > MAX_CUE_BODY:
                self.close_connection = True
                return self._json(413, {"error": f"a jam body is at most {MAX_CUE_BODY} bytes"})
            raw = self.rfile.read(length) if length > 0 else b""
            origin = self.headers.get("Origin")
            if origin is not None and urlsplit(origin).hostname not in ("127.0.0.1", "localhost"):
                return self._json(403, {"error": f"jam requests are accepted from this machine's pages only, not "
                                                 f"{origin}"})
            try:
                body = json.loads(raw.decode("utf-8") or "null")
            except ValueError as exc:
                return self._json(400, {"error": f"the body is not JSON: {exc}"})
            if body is None:
                body = {}
        status, reply = self.app.jam.handle(method, path, query, body)
        return self._json(status, reply)

    def _peer_gone(self) -> bool:
        """An EventSource never sends after its request, so a readable socket means the peer closed (or reset)."""
        sock = self.connection
        try:
            readable, _, _ = select.select([sock], [], [], 0)
            if not readable:
                return False
            return sock.recv(1, socket.MSG_PEEK) == b""
        except (OSError, ValueError):
            return True

    # ----------------------------------------------------------------- recordings
    def _recording(self, query) -> None:
        """Save an uploaded recording under the first library root, so it shows up in the library."""
        kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        ext = RECORDING_TYPES.get(kind)
        if not ext:
            return self._json(415, {"error": f"a recording must be video/webm, video/mp4 or video/x-matroska, "
                                             f"not {kind or 'untyped'}"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_RECORDING:
            return self._json(413 if length else 411, {"error": "a recording needs a Content-Length of at most 4 GB"})
        if not self.app.library.roots:
            return self._json(503, {"error": "there is no library root to save into"})
        label = re.sub(r"[^A-Za-z0-9_-]+", "-", (query.get("name") or ["recording"])[0]).strip("-")[:40] or "recording"
        folder = self.app.library.roots[0] / RECORDINGS_DIR
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{time.strftime('%Y-%m-%d %H-%M-%S')} {label}"
        target, n = folder / f"{stem}{ext}", 1
        while target.exists():
            n += 1
            target = folder / f"{stem} ({n}){ext}"
        partial = folder / f"{target.name}.part"
        remaining = length
        with open(partial, "wb") as fh:
            while remaining > 0:
                chunk = self.rfile.read(min(CHUNK, remaining))
                if not chunk:
                    break
                fh.write(chunk)
                remaining -= len(chunk)
        if remaining:
            partial.unlink(missing_ok=True)
            return self._json(400, {"error": "the upload ended before Content-Length bytes arrived"})
        partial.replace(target)
        return self._json(200, {"path": str(target), "clip_id": clip_id_for(target), "bytes": length})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # on Windows, reuse would let two servers share a port

    def __init__(self, port: int, app: App):
        super().__init__((HOST, port), Handler)
        self.app = app


def serve(port: int = 8793, roots: Optional[List[str]] = None, takes_root=None, performance_root=None,
          performance_log: bool = True) -> None:
    app = App(roots or DEFAULT_ROOTS, takes_root, performance_root=performance_root, performance_log=performance_log)
    server = Server(port, app)
    roots_text = ", ".join(str(r) for r in app.library.roots)
    base = f"http://{HOST}:{server.server_address[1]}"
    print(f"[arsenal] First Light at {base}/first-light, Play at {base}/play  (library: {roots_text})", flush=True)
    log_text = f"sessions in {app.performance.root}" if app.performance else "off (the routes answer 404)"
    print(f"[arsenal] practice log: {log_text}", flush=True)
    closed = app.jam.runs.close_unclosed()  # a run left open by an earlier server ends with server-restart
    print(f"[arsenal] jam: deck and runs in {app.jam.root}"
          + (f"; closed {len(closed)} run(s) an earlier server left open" if closed else ""), flush=True)
    ticking = threading.Event()

    def tick() -> None:  # passes that end by themselves, pending runs nobody launched
        while not ticking.wait(0.5):
            try:
                app.jam.tick()
            except Exception as exc:  # the ticker never takes the server down
                sys.stderr.write(f"[arsenal] jam tick: {type(exc).__name__}: {exc}\n")

    threading.Thread(target=tick, daemon=True, name="jam-tick").start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ticking.set()
        app.cues.close()  # ends every open cue stream
        server.server_close()
