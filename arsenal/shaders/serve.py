"""py -m arsenal shader serve [--port 8797] -- the shader lab's own small web server: loopback only, read-only, and
for the headless driver; do not open in a browser (its pages render on SwiftShader only, and refuse any other renderer).

WHY A SERVER OF ITS OWN. Daniel's arsenal server (arsenal/serve.py) owns port 8793 and carries his live piano and editor
sessions. The shader lab never shares that port or that process: a hung SwiftShader burst or a crash here must not take
the piano down with it. So this is a separate, standard-library server that serves exactly these, and nothing else:

    /lab/<file>                 arsenal/web/shaderlab/          our runtime (toy-runtime.js), render.html, the lab pages
    /lib/<file>, /glsl/<file>   arsenal/web/glsl/               the house module library (our own GLSL, modlib.js and
                                                                its index.json); /glsl/ is the path modlib's usage note
                                                                fetches, /lib/ the older name, both one root
    /corpus/<id>/shader.json    state/.../corpus/shaders/<id>/  one corpus shader, exactly as saved
    /corpus/media/<file>        state/.../corpus/media/         the textures, cubemap faces and volumes shaders sample
    /jobs/<name>.json           state/arsenal/shaders/jobs/     shader JSON `render` wrote for a .frag or loose .json path
    /atlas.json                 arsenal/shaders/atlas.json      the primitive atlas as data (our own words)
    /shelf/index.json           state/.../shaders/shelf/        the Shelf: the Loved shaders' cards (shelf.py; private)
    /renders/<id>/<file>.png    state/.../shaders/renders/      SwiftShader stills and filmstrip sheets (private)
    /study/<id>.md              state/.../shaders/study/        the study notes (private)
    /cards/<name>/<file>.png    state/.../shaders/cards/        module test cards (`py -m arsenal shader card`)
    /webl/<file>                arsenal/web/lib/                params.js, params-ui.js, workbench/*: the page parts
    /health                     who this is, so `render` can tell this server from anything else on the port

The Shelf's routes are shaped like a datasheet drawer: one fixed file (/atlas.json, /shelf/index.json), or one level of
named files in one folder (/renders/<id>/<file>.png, /cards/<name>/<file>.png), each name checked against a pattern
before it touches the disk. Pictures only where pictures are meant: a receipt or a filmstrip's frame folder is not
served. A STUDY-ONLY shader (its own header withholds permission, or the atlas rules it so) is shown by its study note
and never by its pictures, and never run: /renders/ and /corpus/<id>/shader.json (the source the Workbench's Stage runs)
refuse its id with a 403 whatever sits on disk, reading at request time the same sources the Workbench reads: the
Shelf's index, the atlas's `loved` list and every atlas group's `study_only` list (any one is enough; the atlas alone
holds when no Shelf has been built). /jobs/ is the second door, since `render` stages a loose .json there: a job whose
id is study only, or one of whose passes is a study-only corpus shader's pass by its text, is refused the same way.

LOOPBACK ONLY IS A RULE, NOT A DEFAULT. The corpus is other people's work, mostly CC BY-NC-SA; serving it beyond this
machine would be redistributing it. So there is no host option at all: the bind address is the constant 127.0.0.1, and a
request whose Host header names anything but a loopback name is refused (otherwise a DNS-rebinding page open in Daniel's
own browser could read the corpus through this port). Port 8793 is refused outright: it is Daniel's server.

READ-ONLY. GET and HEAD only. A path is served only after it has been percent-decoded once, checked segment by segment
(no "..", no backslash, no drive colon, no NUL) and resolved to a real file that still lies under its root, so neither
an encoded traversal nor a symlink pointing out of a root can reach another file.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

from . import corpus as C

HOST = "127.0.0.1"
DEFAULT_PORT = 8797
FORBIDDEN_PORTS = {8793: "Daniel's arsenal server (arsenal/serve.py)"}  # headless.mjs FORBIDDEN_PORTS is the twin
SERVE_API = "arsenal.shader-serve/v1"
HEADLESS_ONLY = "for the headless driver; do not open in a browser"

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "arsenal" / "web" / "shaderlab"
LIB = ROOT / "arsenal" / "web" / "glsl"   # the house library's home (build spec 2026-10-13, ruling 1)
JOBS = ROOT / "state" / "arsenal" / "shaders" / "jobs"
LIB_ROUTES = ("/lib/", "/glsl/")
STATE = ROOT / "state" / "arsenal" / "shaders"
ATLAS = ROOT / "arsenal" / "shaders" / "atlas.json"     # a file, not a folder
SHELF = STATE / "shelf"                                 # shelf.py writes index.json here
RENDERS = STATE / "renders"                             # render.py's default out dir: renders/<id>/
STUDY = STATE / "study"
CARDS = STATE / "cards"                                 # the card verb: cards/<module name>/
WEBL = ROOT / "arsenal" / "web" / "lib"

LOOPBACK_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}
SHADER_ID = re.compile(r"[A-Za-z0-9]{6}")                   # a Shadertoy id, as corpus.save_shader requires
MEDIA_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,200}")  # media are saved by basename (Shadertoy names them by hash)
JOB_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,96}\.json")
RENDER_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")  # a corpus id, local-<stem> (render.py), or a group's name
CARD_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,96}")  # a module name (modules.NAME_RE), as a folder name
PNG_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.png")
CHUNK = 1024 * 1024

TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".json": "application/json", ".glsl": "text/plain; charset=utf-8", ".frag": "text/plain; charset=utf-8",
    ".vert": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bin": "application/octet-stream",
    ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav",
    ".webm": "video/webm", ".ogv": "video/ogg", ".mp4": "video/mp4",
}


class BindRefused(ValueError):
    """The server was asked to listen somewhere it must not: off loopback, or on a port that belongs to someone else."""


def validate_bind(host: str, port: int) -> None:
    """Refuse any bind but 127.0.0.1, and the ports in FORBIDDEN_PORTS. Port 0 (an ephemeral port) is allowed."""
    if host != HOST:
        raise BindRefused(f"the shader server listens on {HOST} only, not {host!r}: the corpus must not leave this machine")
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise BindRefused(f"not a TCP port: {port!r}")
    if port in FORBIDDEN_PORTS:
        raise BindRefused(f"port {port} is refused: it is {FORBIDDEN_PORTS[port]}")


def host_is_loopback(host_header: Optional[str]) -> bool:
    """True for a Host header naming 127.0.0.1, localhost or [::1] (any port), or for no Host header at all."""
    if not host_header:
        return True  # HTTP/1.0 clients send none; a browser always does, so this is no rebinding door
    value = host_header.strip().lower()
    if value.startswith("["):
        name = value[1:value.find("]")] if "]" in value else value
    else:
        name = value.rsplit(":", 1)[0] if value.count(":") == 1 else value
    return name in LOOPBACK_HOSTNAMES


def safe_file(root: Path, rel: str) -> Optional[Path]:
    """The file `rel` names under `root`, or None if it is not a plain relative path to a file inside root.

    `rel` arrives percent-decoded once. It is refused if any segment is "." or "..", or it holds a backslash, a colon
    (a Windows drive or stream), or a NUL; the resolved path (symlinks followed) must still lie under the resolved root."""
    if not rel or "\\" in rel or ":" in rel or "\x00" in rel or rel.startswith("/"):
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    try:
        base = root.resolve()
        target = (base / rel).resolve()
    except (OSError, RuntimeError):
        return None
    if not target.is_relative_to(base) or not target.is_file():
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "arsenal-shaderlab/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # quiet on success: a render burst fetches the runtime, the shader and its media for every frame set. Quiet too
        # on a medium the corpus lacks: the runtime stands in for it and every receipt lists the stand-in, so a 404 line
        # per missing texture per shader would only bury the lines that matter.
        if not self.server.verbose and len(args) >= 2:
            status = str(args[1])
            if status[:1] in ("2", "3") or (status == "404" and urlsplit(self.path).path.startswith("/corpus/media/")):
                return
        sys.stderr.write(f"[shaderlab] {fmt % args}\n")

    # ------------------------------------------------------------------ responses
    def _send(self, status: int, body: bytes, content_type: str, headers: Optional[dict] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj, indent=1).encode("utf-8"), "application/json")

    def _not_found(self) -> None:
        self._json(404, {"error": "not found", "routes": ROUTES})

    def _file(self, path: Path) -> None:
        """A file's bytes, with single-range support so a <video> or <audio> input can seek."""
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
                end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
            if start >= size or start > end:
                return self._unsatisfiable(size)
            status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        self._send(416, b"", "text/plain", {"Content-Range": f"bytes */{size}"})

    # -------------------------------------------------------------------- routing
    def do_GET(self):
        self._route()

    def do_HEAD(self):
        self._route()

    def _refuse_method(self):
        self._send(405, b'{"error": "read-only: GET and HEAD only"}', "application/json", {"Allow": "GET, HEAD"})

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse_method

    def _route(self) -> None:
        if not host_is_loopback(self.headers.get("Host")):
            return self._json(403, {"error": "this server answers loopback names only (127.0.0.1, localhost)"})
        raw = urlsplit(self.path).path
        path = unquote(raw)
        roots: Dict[str, Path] = self.server.roots
        try:
            if path in ("/", "/health"):
                return self._json(200, self.server.health())
            if path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")  # every page load asks; no answer is the quiet answer
            if path in ("/lab", "/lab/"):
                index = safe_file(roots["lab"], "index.html")
                return self._file(index) if index else self._not_found()
            if path.startswith("/lab/"):
                target = safe_file(roots["lab"], path[len("/lab/"):])
                return self._file(target) if target else self._not_found()
            for prefix in LIB_ROUTES:
                if path.startswith(prefix):
                    target = safe_file(roots["lib"], path[len(prefix):])
                    return self._file(target) if target else self._not_found()
            if path.startswith("/corpus/media/"):
                name = path[len("/corpus/media/"):]
                target = safe_file(roots["corpus"] / "media", name) if MEDIA_NAME.fullmatch(name) else None
                return self._file(target) if target else self._not_found()
            m = re.fullmatch(r"/corpus/([^/]+)/shader\.json", path)
            if m:
                sid = m.group(1)
                if not SHADER_ID.fullmatch(sid):
                    return self._not_found()
                if sid.lower() in self.server.study_only_ids():
                    # the Workbench's Stage runs a loved shader from this route; a study-only one is never run
                    return self._json(403, {"error": f"{sid} is study only: it is shown by its study note "
                                                     f"(/study/{sid}.md), never run and never pictured"})
                target = safe_file(roots["corpus"] / "shaders", f"{sid}/shader.json")
                return self._file(target) if target else self._not_found()
            if path.startswith("/jobs/"):
                name = path[len("/jobs/"):]
                target = safe_file(roots["jobs"], name) if JOB_NAME.fullmatch(name) else None
                if not target:
                    return self._not_found()
                held = self.server.job_holds_study_only(target)
                if held:
                    # the second door: `render` stages a loose .json here, and a copy of a study-only shader is that
                    # shader whatever its file is called
                    return self._json(403, {"error": f"this job holds {held}, which is study only: it is shown by its "
                                                     "study note, never run and never pictured"})
                return self._file(target)
            if path == "/atlas.json":
                atlas = Path(roots["atlas"])
                target = safe_file(atlas.parent, atlas.name)
                return self._file(target) if target else self._not_found()
            if path == "/shelf/index.json":
                target = safe_file(roots["shelf"], "index.json")
                return self._file(target) if target else self._not_found()
            m = re.fullmatch(r"/renders/([^/]+)/([^/]+)", path)
            if m:
                key, name = m.groups()
                if not (RENDER_KEY.fullmatch(key) and PNG_NAME.fullmatch(name)):
                    return self._not_found()
                if key.lower() in self.server.study_only_ids():
                    return self._json(403, {"error": f"{key} is study only: it is shown by its study note "
                                                     f"(/study/{key}.md), never by its pictures"})
                target = safe_file(roots["renders"], f"{key}/{name}")
                return self._file(target) if target else self._not_found()
            m = re.fullmatch(r"/study/([^/]+)\.md", path)
            if m:
                target = safe_file(roots["study"], f"{m.group(1)}.md") if SHADER_ID.fullmatch(m.group(1)) else None
                return self._file(target) if target else self._not_found()
            m = re.fullmatch(r"/cards/([^/]+)/([^/]+)", path)
            if m:
                ok = CARD_NAME.fullmatch(m.group(1)) and PNG_NAME.fullmatch(m.group(2))
                target = safe_file(roots["cards"], f"{m.group(1)}/{m.group(2)}") if ok else None
                return self._file(target) if target else self._not_found()
            if path.startswith("/webl/"):
                target = safe_file(roots["webl"], path[len("/webl/"):])
                return self._file(target) if target else self._not_found()
            return self._not_found()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return  # the page went away mid-file (a render job timed out and its tab was closed)


ROUTES = ["/health", "/lab/<file>", "/lib/<file>", "/glsl/<file>", "/corpus/<id>/shader.json", "/corpus/media/<file>",
          "/jobs/<name>.json", "/atlas.json", "/shelf/index.json", "/renders/<id>/<file>.png", "/study/<id>.md",
          "/cards/<name>/<file>.png", "/webl/<file>"]


def _json_any(path: Path):
    """A JSON file's value, or None when it cannot be read or parsed."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _json_or_none(path: Path) -> Optional[dict]:
    data = _json_any(path)
    return data if isinstance(data, dict) else None


def study_only_from(shelf_index: Optional[dict], atlas: Optional[dict]) -> frozenset:
    """Lower-cased ids that are never pictured, run or served: study only in the Shelf's index (either spelling), in the
    atlas's loved list, or in any atlas group's study_only list. These are the sources the Workbench's isStudyOnly
    (arsenal/web/lib/workbench/shelf.js) ORs, so the server refuses at least what a page would; a true in any one wins.
    Lower case because Windows folds case in paths, so /renders/abcde2/ would reach abcDE2's folder."""
    ids = set()
    for row in (shelf_index or {}).get("shaders") or []:
        if isinstance(row, dict) and (row.get("study_only") or row.get("studyOnly")) and isinstance(row.get("id"), str):
            ids.add(row["id"].lower())
    for row in (atlas or {}).get("loved") or []:
        if isinstance(row, dict) and row.get("study_only") and isinstance(row.get("id"), str):
            ids.add(row["id"].lower())
    for group in (atlas or {}).get("groups") or []:
        listed = group.get("study_only") if isinstance(group, dict) else None
        if isinstance(listed, list):
            ids.update(x.lower() for x in listed if isinstance(x, str))
    return frozenset(ids)


# A pass shorter than this is not used to recognise a shader by its text: a one-line stub is common to many shaders.
PASS_KEY_MIN = 64


def pass_key(code) -> Optional[str]:
    """A pass's text as compared between a staged job and the corpus: line endings unified and trailing blanks dropped,
    so a copy saved by another editor is still the same pass; None for a pass too short to tell shaders apart."""
    if not isinstance(code, str):
        return None
    text = "\n".join(line.rstrip() for line in code.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
    return text if len(text) >= PASS_KEY_MIN else None


def shader_of(data) -> Optional[dict]:
    """The shader in a job file: as saved, or as Shadertoy's API wraps it ({"Shader": {...}}, or a list of one)."""
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if isinstance(data, dict) and isinstance(data.get("Shader"), dict):
        data = data["Shader"]
    return data if isinstance(data, dict) else None


class ShaderServer(ThreadingHTTPServer):
    """The lab server. It has no host parameter on purpose: see the module docstring."""
    daemon_threads = True
    allow_reuse_address = False  # on Windows, reuse would let two servers share a port

    def __init__(self, port: int = DEFAULT_PORT, *, lab: Path = LAB, lib: Path = LIB,
                 corpus: Path = C.CORPUS, jobs: Path = JOBS, atlas: Path = ATLAS, shelf: Path = SHELF,
                 renders: Path = RENDERS, study: Path = STUDY, cards: Path = CARDS, webl: Path = WEBL,
                 verbose: bool = False):
        validate_bind(HOST, port)
        super().__init__((HOST, port), Handler)
        try:
            validate_bind(self.server_address[0], self.server_address[1])  # an ephemeral port: say so if it ever lands on one
        except BindRefused:
            self.server_close()
            raise
        # "atlas" is the one root that is a file; every other root is a folder a route serves from.
        self.roots = {"lab": Path(lab), "lib": Path(lib), "corpus": Path(corpus), "jobs": Path(jobs),
                      "atlas": Path(atlas), "shelf": Path(shelf), "renders": Path(renders), "study": Path(study),
                      "cards": Path(cards), "webl": Path(webl)}
        self.verbose = verbose
        self._study_only_cache: Tuple[tuple, frozenset] = ((), frozenset())
        self._study_passes_cache: Tuple[tuple, Dict[str, str]] = ((), {})
        self._study_only_lock = threading.Lock()

    def study_only_ids(self) -> frozenset:
        """The ids /renders/ refuses, re-read whenever the Shelf's index or the atlas changes on disk."""
        sources = (Path(self.roots["shelf"]) / "index.json", Path(self.roots["atlas"]))
        stamp = []
        for p in sources:
            try:
                st = p.stat()
                stamp.append((st.st_mtime_ns, st.st_size))
            except OSError:
                stamp.append(None)
        stamp = tuple(stamp)
        with self._study_only_lock:
            if self._study_only_cache[0] != stamp:
                self._study_only_cache = (stamp, study_only_from(_json_or_none(sources[0]), _json_or_none(sources[1])))
            return self._study_only_cache[1]

    def study_only_passes(self) -> Dict[str, str]:
        """{pass_key: id} for every pass of every study-only shader saved in the corpus, re-read when the study-only set
        or one of those files changes. A corpus folder is found whatever its case (the set is lower-cased)."""
        ids = self.study_only_ids()
        shaders = Path(self.roots["corpus"]) / "shaders"
        files = []
        if ids:
            try:
                names = sorted(p.name for p in shaders.iterdir() if p.is_dir())
            except OSError:
                names = []
            for name in names:
                if name.lower() in ids:
                    f = shaders / name / "shader.json"
                    try:
                        st = f.stat()
                    except OSError:
                        continue
                    files.append((name, f, st.st_mtime_ns, st.st_size))
        stamp = (ids, tuple((n, m, s) for n, _, m, s in files))
        with self._study_only_lock:
            if self._study_passes_cache[0] == stamp:
                return self._study_passes_cache[1]
        keys: Dict[str, str] = {}
        for name, f, _, _ in files:
            shader = shader_of(_json_any(f))
            for p in (shader or {}).get("renderpass") or []:
                key = pass_key(p.get("code")) if isinstance(p, dict) else None
                if key:
                    keys.setdefault(key, name)
        with self._study_only_lock:
            self._study_passes_cache = (stamp, keys)
        return keys

    def job_holds_study_only(self, path: Path) -> Optional[str]:
        """The study-only shader a staged job holds, or None: its info.id is study only (case-folded), or one of its
        passes is a study-only corpus shader's pass, by text. A job that is not a readable shader holds none."""
        ids = self.study_only_ids()
        if not ids:
            return None
        shader = shader_of(_json_any(path))
        if shader is None:
            return None
        info = shader.get("info") if isinstance(shader.get("info"), dict) else {}
        sid = info.get("id")
        if isinstance(sid, str) and sid.lower() in ids:
            return sid
        passes = self.study_only_passes()
        for p in shader.get("renderpass") or []:
            key = pass_key(p.get("code")) if isinstance(p, dict) else None
            if key and key in passes:
                return passes[key]
        return None

    @property
    def base_url(self) -> str:
        return f"http://{HOST}:{self.server_address[1]}"

    def health(self) -> dict:
        lab = self.roots["lab"]
        return {"api": SERVE_API, "pid": os.getpid(), "base": self.base_url,
                "roots": {k: str(v) for k, v in self.roots.items()},
                "lab_pages": sorted(p.name for p in lab.glob("*.html")) if lab.is_dir() else [],
                "routes": ROUTES}

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return  # a headless tab closed mid-response
        super().handle_error(request, client_address)


def start_in_thread(port: int = 0, **roots) -> ShaderServer:
    """A server on a daemon thread (port 0 = an ephemeral loopback port). The caller shuts it down."""
    server = ShaderServer(port, **roots)
    threading.Thread(target=server.serve_forever, daemon=True, name="shaderlab-serve").start()
    return server


def probe(port: int, timeout: float = 1.5) -> Optional[dict]:
    """The /health answer of a shader server on this port, or None if nothing (or something else) answers there."""
    validate_bind(HOST, port)
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/health", timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("api") == SERVE_API else None


def banner(server: ShaderServer) -> List[str]:
    """What the `serve` verb prints: where things are, and who the pages are for. They render on SwiftShader only and
    refuse any other renderer; opened in an ordinary browser on this host they would meet its AMD GPU, so the banner
    says so plainly instead of advertising them to a person."""
    base = server.base_url
    return [f"[shaderlab] serving on {base} (loopback only, read-only), {HEADLESS_ONLY}",
            f"[shaderlab]   lab     {base}/lab/   <- {server.roots['lab']}  (pages for headless.mjs on SwiftShader)",
            f"[shaderlab]   library {base}/glsl/ and {base}/lib/   <- {server.roots['lib']}",
            f"[shaderlab]   corpus  {base}/corpus/<id>/shader.json, {base}/corpus/media/<file>",
            f"[shaderlab]   shelf   {base}/atlas.json, {base}/shelf/index.json, {base}/renders/<id>/<file>.png, "
            f"{base}/study/<id>.md, {base}/cards/<name>/<file>.png",
            f"[shaderlab]   parts   {base}/webl/   <- {server.roots['webl']}",
            "[shaderlab]   render a picture with `py -m arsenal shader render <id>`, not by opening a page"]


def serve(port: int = DEFAULT_PORT, verbose: bool = False) -> int:
    """The `serve` verb: run in the foreground until Ctrl+C."""
    try:
        server = ShaderServer(port, verbose=verbose)
    except BindRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"could not listen on {HOST}:{port}: {exc}"
              + ("  (a shader server is already running there)" if probe(port) else ""), file=sys.stderr)
        return 1
    for line in banner(server):
        print(line, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def base_for(port: int) -> Tuple[Optional[ShaderServer], str]:
    """(server we started or None, base URL): reuse a shader server already on `port`, else start a private one on an
    ephemeral port for the life of this process, so a render never occupies the lab's port or waits on someone's server."""
    found = probe(port)
    ours = {"lab": str(LAB), "lib": str(LIB), "corpus": str(C.CORPUS), "jobs": str(JOBS)}
    if found and all((found.get("roots") or {}).get(k) == v for k, v in ours.items()):
        return None, f"http://{HOST}:{port}"
    server = start_in_thread(0)  # nothing there, something else there, or a lab server over other roots (a test's)
    return server, server.base_url
