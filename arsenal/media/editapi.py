"""arsenal.media.editapi -- the editor's HTTP routes (/api/edit/...), answered inside `py -m arsenal serve`.

serve.py hands every /api/edit/ request here through one dispatch line; the rules about the timeline itself live in
arsenal/media/edit.py, which the CLI and a future MCP door share, so this module is routing, the background job
runner, and byte serving with HTTP Range (serve.py's own sender, so seeking behaves as /api/media does).

The job runner is ONE worker thread over a priority queue: one heavy job at a time, so a render, a demux and a shots
proxy never fight over the GPU or the RAM (the machine froze at 82-92 h of uptime under parallel load). Cheap jobs
jump ahead of queued renders and shots: demux 0, peaks 1, render 2, shots 3. Nothing running is pre-empted.

A drop arrives as the browser knows it, {name, size, lastModified}: catalog.resolve_dropped finds the real path
(the catalog, then the library roots), with serve's Library.resolve(name, size) behind it. Nothing is copied. On a
33-minute OBS recording (measured 2026-10-12) the import answers in 0.84 s and, with the worker free, the demuxed
track follows 0.26 s later and its waveform about 4 s after that.
Routes whose primitive is not built yet answer 503 {"error": "arsenal.media.<module> not built yet"}; work still in
the queue answers 202 {"state": ...}.
"""
from __future__ import annotations

import itertools
import math
import os
import queue
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from . import edit, ff

PREFIX = "/api/edit/"
VIDEO_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
               ".mkv": "video/x-matroska"}
AUDIO_TYPES = {".ogg": "audio/ogg", ".opus": "audio/ogg", ".oga": "audio/ogg", ".m4a": "audio/mp4",
               ".mp4": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".wav": "audio/wav",
               ".mp3": "audio/mpeg", ".mka": "audio/x-matroska", ".webm": "audio/webm"}
MEDIA_JOBS = ("demux", "peaks", "shots")
PRIORITY = {"demux": 0, "peaks": 1, "render": 2, "lossless": 2, "shots": 3}
NEEDS = {"demux": ("audio", "demux"), "peaks": ("peaks", "peaks"), "shots": ("shots", "shots")}
DERIVED = {"demux": "audio", "peaks": "peaks", "shots": "shots"}       # job kind -> its key in rec["derived"]
BUILDERS: Dict[str, Callable] = {"demux": edit.build_demux, "peaks": edit.build_peaks, "shots": edit.build_shots}
KEEP_JOBS = 500
_JID = r"j\d+-[0-9a-f]{6}"


def _reason(exc: BaseException) -> str:
    text = str(exc).strip().splitlines()
    return f"{type(exc).__name__}: {text[0] if text else ''}"[:400]


class Jobs:
    """Background work, one job at a time, in priority order; a job is a callable taking progress(fraction)."""

    def __init__(self):
        self._q: "queue.PriorityQueue" = queue.PriorityQueue()
        self._jobs: Dict[str, dict] = {}
        self._by_key: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._seq = itertools.count(1)
        self._worker: Optional[threading.Thread] = None

    def submit(self, kind: str, fn: Callable[[Callable[[float], None]], object], *, key: Optional[str] = None,
               **meta) -> dict:
        """Queue fn; with a key, a job of that key already queued or running is returned instead (no twins)."""
        with self._lock:
            if key and key in self._by_key:
                job = self._jobs.get(self._by_key[key])
                if job and job["state"] in ("queued", "running"):
                    return self._view(job)
            n = next(self._seq)
            job = {"id": f"j{n}-{secrets.token_hex(3)}", "kind": kind, "key": key, "state": "queued",
                   "progress": 0.0, "result": None, "error": None, "created_at": time.time(), "started_at": None,
                   "finished_at": None, **meta}
            self._jobs[job["id"]] = job
            if key:
                self._by_key[key] = job["id"]
            self._q.put((PRIORITY.get(kind, 5), n, job["id"], fn))
            self._prune()
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, daemon=True, name="edit-jobs")
                self._worker.start()
            return self._view(job)

    def get(self, jid: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(jid)
            return self._view(job) if job else None

    def for_key(self, key: str) -> Optional[dict]:
        with self._lock:
            jid = self._by_key.get(key)
            return self._view(self._jobs[jid]) if jid in self._jobs else None

    def forget(self, key: str) -> None:
        """Let a finished (done or failed) job of this key be submitted again."""
        with self._lock:
            jid = self._by_key.get(key)
            if jid and self._jobs.get(jid, {}).get("state") in ("done", "error"):
                del self._by_key[key]

    def wait_idle(self, timeout: float = 60.0) -> bool:
        """True once nothing is queued or running (tests, and a server shutting down politely)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if all(j["state"] in ("done", "error") for j in self._jobs.values()):
                    return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _view(job: dict) -> dict:
        return {k: v for k, v in job.items() if k != "key"}

    def _prune(self) -> None:
        done = [j for j in self._jobs.values() if j["state"] in ("done", "error")]
        for j in sorted(done, key=lambda j: j["finished_at"] or 0)[:max(0, len(self._jobs) - KEEP_JOBS)]:
            self._jobs.pop(j["id"], None)
            if j.get("key") and self._by_key.get(j["key"]) == j["id"]:
                del self._by_key[j["key"]]

    def _run(self) -> None:
        while True:
            _prio, _n, jid, fn = self._q.get()
            job = self._jobs.get(jid)
            if job is None:
                continue
            job.update(state="running", started_at=time.time())

            def progress(fraction: float, job=job) -> None:
                job["progress"] = round(max(0.0, min(1.0, float(fraction))), 4)

            try:
                job["result"] = fn(progress)
                job.update(state="done", progress=1.0)
            except Exception as exc:  # a failed job is reported on its own record; the worker carries on
                job.update(state="error", error=_reason(exc))
            finally:
                job["finished_at"] = time.time()


class EditService:
    """The editor's per-server state: its job runner, where renders land, a cache of peaks bodies."""

    def __init__(self, app):
        self.app = app
        self.jobs = Jobs()
        roots = list(getattr(getattr(app, "library", None), "roots", []) or [])
        self.out_root = (Path(roots[0]) / edit.OUT_FOLDER) if roots else ff.state_dir() / "edit-renders"
        self._bodies: Dict[str, Tuple[int, bytes]] = {}

    # ----------------------------------------------------------------- media jobs
    def media_jobs(self, rec: dict, *, retry: bool = False) -> Dict[str, str]:
        """{demux, peaks, shots: "queued"|"running"|"done"|"error: ..."}; queues what is missing."""
        states = {}
        for kind in MEDIA_JOBS:
            if edit.derived_ready(rec, DERIVED[kind]):
                states[kind] = "done"
                continue
            mod, attr = NEEDS[kind]
            if not edit.is_built(mod, attr):
                states[kind] = f"error: arsenal.media.{mod} not built yet"
                continue
            key = f"{kind}:{rec['id']}"
            job = self.jobs.for_key(key)
            if job and (job["state"] == "done" or (retry and job["state"] == "error")):
                self.jobs.forget(key)     # done but its files are gone, or a retry was asked for
                job = None
            if job is None:
                job = self.jobs.submit(kind, lambda progress, k=kind, mid=rec["id"]: BUILDERS[k](mid, progress),
                                       key=key, media_id=rec["id"])
            states[kind] = f"error: {job['error']}" if job["state"] == "error" else job["state"]
        return states

    def body_for(self, path: Path) -> bytes:
        """A derived JSON file's bytes, cached while its mtime holds (peaks bodies run to a few MB)."""
        mtime = path.stat().st_mtime_ns
        hit = self._bodies.get(str(path))
        if hit and hit[0] == mtime:
            return hit[1]
        body = path.read_bytes()
        if len(self._bodies) > 64:
            self._bodies.clear()
        self._bodies[str(path)] = (mtime, body)
        return body


_service_lock = threading.Lock()


def service(app) -> EditService:
    svc = getattr(app, "edit_service", None)
    if svc is None:
        with _service_lock:
            svc = getattr(app, "edit_service", None)
            if svc is None:
                svc = EditService(app)
                app.edit_service = svc
    return svc


def media_view(rec: dict) -> dict:
    """What the page gets for one imported file: the facts the bin and the inspector show, and its URLs."""
    mid = rec["id"]
    keys = ("id", "name", "path", "size", "mtime_ns", "duration_s", "container", "kind", "recorded_at", "encoder",
            "video", "audio", "n_audio", "chapters", "links", "tags", "facts_from", "facts_notes", "imported_at")
    out = {k: rec.get(k) for k in keys}
    # every time above is a file time; Chrome's <video>.currentTime counts on the container's own clock (measured,
    # Chrome 154: a source whose container clock starts at 1.4 s opens at currentTime 1.4), so the page converts by it
    out["container_start_s"] = float(rec.get("start_s") or 0.0)
    n = len(rec.get("audio") or [])
    base = f"{PREFIX}media/{mid}"
    out["tracks"] = n
    out["urls"] = {"video": f"{base}/video", "audio": [f"{base}/audio/{i}" for i in range(n)],
                   "peaks": [f"{base}/peaks/{i}" for i in range(n)], "shots": f"{base}/shots",
                   "keyframes": f"{base}/keyframes", "cutplan": f"{base}/cutplan"}
    return out


# =================================================================================================
# routes
# =================================================================================================

Reply = Optional[Tuple[int, object]]


def _import(svc: EditService, handler, query, body) -> Reply:
    roots = [str(r) for r in handler.app.library.roots]
    if body.get("path"):
        path = str(body["path"])
    else:
        name, size = body.get("name"), body.get("size")
        if not isinstance(name, str) or not name or not isinstance(size, int) or isinstance(size, bool):
            return 400, {"error": "import needs {name, size, lastModified} (a dropped File) or {path}"}
        try:
            last_ms = int(body.get("lastModified") or 0)
        except (TypeError, ValueError):
            last_ms = 0
        path = None
        try:
            path = edit.module("catalog", "resolve_dropped").resolve_dropped(name, size, last_ms, roots=roots)
        except edit.NotBuilt:
            pass
        if not path:
            clip = handler.app.library.resolve(name, size)
            path = clip["path"] if clip else None
        if not path:
            return 404, {"error": f"{name} ({size} bytes) is not under the library roots",
                         "hint": "a browser drop carries a name and size, never a path: move the file under a library "
                                 "root, start the server with --root <its folder>, or import it by path "
                                 "(py -m arsenal.media edit add <project> <file>)",
                         "roots": roots}
    rec = edit.import_media(path)
    return 200, {"media": media_view(rec), "jobs": svc.media_jobs(rec, retry=True)}


def _media_list(svc, handler, query, body) -> Reply:
    return 200, {"media": [media_view(r) for r in edit.list_media()]}


def _media_get(svc, handler, query, body, mid) -> Reply:
    rec = edit.get_media(mid)
    return 200, {"media": media_view(rec), "jobs": svc.media_jobs(rec)}


def _send_file(handler, path: Path, content_type: str) -> Reply:
    sender = getattr(handler, "_send_file", None)
    if sender is None:
        return 503, {"error": "this server has no Range sender (arsenal/serve.py Handler._send_file)"}
    sender(path, content_type)
    return None


def _video(svc, handler, query, body, mid) -> Reply:
    rec = edit.get_media(mid)
    path = edit.source_path(rec)
    if path is None:
        return 404, {"error": f"the source is gone from {rec['path']}"}
    return _send_file(handler, path, VIDEO_TYPES.get(path.suffix.lower(), "application/octet-stream"))


def _not_ready(svc: EditService, rec: dict, kind: str) -> Reply:
    state = svc.media_jobs(rec).get(kind, "")
    if "not built yet" in state:
        return 503, {"error": state.split("error: ", 1)[-1], "state": state}
    if state.startswith("error"):
        return 500, {"error": state.split("error: ", 1)[-1], "state": state}
    return 202, {"state": state}


def _track(rec: dict, n: str) -> int:
    i = int(n)
    if i >= len(rec.get("audio") or []):
        raise edit.EditError(f"{rec.get('name')} has {len(rec.get('audio') or [])} audio track(s), no track {i}",
                             status=404)
    return i


def _audio(svc, handler, query, body, mid, n) -> Reply:
    rec = edit.get_media(mid)
    i = _track(rec, n)
    path = edit.derived_path(rec, "audio", i)
    if path is None:
        return _not_ready(svc, rec, "demux")
    return _send_file(handler, path, AUDIO_TYPES.get(path.suffix.lower(), "application/octet-stream"))


def _peaks(svc, handler, query, body, mid, n) -> Reply:
    rec = edit.get_media(mid)
    i = _track(rec, n)
    path = edit.derived_path(rec, "peaks", i)
    if path is None:
        return _not_ready(svc, rec, "peaks")
    handler._send(200, svc.body_for(path), "application/json")
    return None


def _shots(svc, handler, query, body, mid) -> Reply:
    rec = edit.get_media(mid)
    path = edit.derived_path(rec, "shots")
    if path is None:
        return _not_ready(svc, rec, "shots")
    return 200, edit.read_json(path)


def _keyframes(svc, handler, query, body, mid) -> Reply:
    return 200, {"keyframes": edit.keyframes(mid)}


def _float_arg(query, name: str) -> float:
    raw = (query.get(name) or [""])[0]
    try:
        v = float(raw)
    except ValueError:
        v = math.nan
    if not math.isfinite(v):                # float() takes 'nan' and 'inf'; neither is a time
        raise edit.EditError(f"{name} must be a number of seconds, not {raw!r}")
    return v


def _cutplan(svc, handler, query, body, mid) -> Reply:
    rec = edit.get_media(mid)
    cut = edit.module("cut", "plan")
    return 200, cut.plan(rec["path"], _float_arg(query, "start"), _float_arg(query, "end"))


def _presets(svc, handler, query, body) -> Reply:
    rows = []
    for pid, p in edit.presets().items():
        if pid in edit.ALPHA_PRESETS:
            continue                       # timeline renders carry no alpha; the clip exporter serves those
        rows.append({"id": pid, "label": p.get("label") or pid.replace("_", " "), "width": p.get("width"),
                     "height": p.get("height"), "fps": p.get("fps"), "container": p.get("container"),
                     "loudness": p.get("loudness"), "why": p.get("why")})
    return 200, {"presets": rows}


def _projects(svc, handler, query, body) -> Reply:
    return 200, {"projects": edit.list_projects()}


def _project_new(svc, handler, query, body) -> Reply:
    settings = body.get("settings") if isinstance(body.get("settings"), dict) else None
    return 201, {"project": edit.new_project(body.get("name") or "", settings=settings)}


def _project_get(svc, handler, query, body, pid) -> Reply:
    return 200, {"project": edit.load(pid)}


def _project_put(svc, handler, query, body, pid) -> Reply:
    doc = body.get("project") if isinstance(body.get("project"), dict) else body
    if doc.get("id") != pid:
        return 400, {"error": f"the document's id {doc.get('id')!r} is not {pid}"}
    return 200, {"project": edit.save(doc)}


def _render_summary(res: dict) -> dict:
    keep = ("path", "duration_s", "duration_expected_s", "duration_ok", "render_s", "realtime_x", "qc", "receipt")
    return {k: res.get(k) for k in keep}


def _render(svc: EditService, handler, query, body, pid) -> Reply:
    doc = edit.load(pid)
    if not any(c.get("lane") == "V1" for c in doc.get("clips") or []):
        return 400, {"error": "the timeline has no clips on V1"}
    preset = body.get("preset") or "youtube_4k60_fast"
    p = edit.resolve_preset(preset)          # 400 unknown, 503 when the export lane is not built
    out = body.get("out")
    if out is not None:
        if not isinstance(out, str) or not os.path.isabs(out):
            return 400, {"error": "out must be an absolute file path"}
        if Path(out).suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"):
            return 400, {"error": "out must end in .mp4, .mov, .mkv or .webm"}
        if Path(out).exists():
            return 409, {"error": f"{out} exists; renders never overwrite a file"}
    problems = edit.validate(doc, media_lookup=edit._registry_lookup)
    if problems:
        return 400, {"error": "; ".join(problems[:5]), "problems": problems}
    job = svc.jobs.submit("render", lambda progress: _render_summary(
        edit.render(doc, p, out=out, out_root=svc.out_root, progress=progress)),
        project_id=pid, rev=doc.get("rev"), preset=p["id"])
    return 202, {"job": job}


def _job(svc, handler, query, body, jid) -> Reply:
    job = svc.jobs.get(jid)
    if job is None:
        return 404, {"error": f"no job {jid} (jobs live as long as the server)"}
    return 200, job


_M, _P = edit.MID_PATTERN, edit.PID_PATTERN
ROUTES: List[Tuple[str, "re.Pattern", Callable]] = [(m, re.compile(rx), fn) for m, rx, fn in (
    ("GET", r"/api/edit/media", _media_list),
    ("GET", rf"/api/edit/media/({_M})", _media_get),
    ("GET", rf"/api/edit/media/({_M})/video", _video),
    ("GET", rf"/api/edit/media/({_M})/audio/(\d{{1,2}})", _audio),
    ("GET", rf"/api/edit/media/({_M})/peaks/(\d{{1,2}})", _peaks),
    ("GET", rf"/api/edit/media/({_M})/shots", _shots),
    ("GET", rf"/api/edit/media/({_M})/keyframes", _keyframes),
    ("GET", rf"/api/edit/media/({_M})/cutplan", _cutplan),
    ("GET", r"/api/edit/projects", _projects),
    ("GET", rf"/api/edit/projects/({_P})", _project_get),
    ("GET", rf"/api/edit/jobs/({_JID})", _job),
    ("GET", r"/api/edit/presets", _presets),
    ("POST", r"/api/edit/import", _import),
    ("POST", r"/api/edit/projects", _project_new),
    ("POST", rf"/api/edit/projects/({_P})/render", _render),
    ("PUT", rf"/api/edit/projects/({_P})", _project_put),
)]


def _same_machine(handler) -> bool:
    origin = handler.headers.get("Origin")
    return origin is None or urlsplit(origin).hostname in ("127.0.0.1", "localhost")


def handle(handler, method: str, path: str, query: dict, body_reader: Callable[[], object]) -> None:
    """Answer one /api/edit/ request on serve.py's handler (its _json, _send and _send_file)."""
    svc = service(handler.app)
    body: object = None
    if method in ("POST", "PUT"):
        try:
            body = body_reader()        # read first: a refused request leaves the keep-alive connection usable
        except ValueError as exc:
            return handler._json(400, {"error": f"the body is not JSON: {exc}"})
        if not _same_machine(handler):
            return handler._json(403, {"error": f"editor writes are accepted from this machine's pages only, not "
                                                f"{handler.headers.get('Origin')}"})
        body = {} if body is None else body
        if not isinstance(body, dict):
            return handler._json(400, {"error": "the body must be a JSON object"})
    for verb, rx, fn in ROUTES:
        m = rx.fullmatch(path) if verb == method else None
        if m:
            break
    else:
        return handler._json(404, {"error": f"no route for {method} {path}"})
    try:
        reply = fn(svc, handler, query, body, *m.groups())
    except edit.Conflict as exc:
        reply = 409, {"error": str(exc), "project": exc.current}
    except edit.EditError as exc:
        reply = exc.status, {"error": str(exc), "problems": exc.problems}
    except edit.NotBuilt as exc:
        reply = 503, {"error": str(exc)}
    except ff.MediaError as exc:
        reply = 422, {"error": str(exc)}
    if reply is not None:
        status, payload = reply
        handler._json(status, payload)
