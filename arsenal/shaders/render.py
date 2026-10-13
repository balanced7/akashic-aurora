"""py -m arsenal shader render | check | filmstrip | serve -- the shader harness: our runtime's pages, rendered headless
on the CPU, with a receipt for every picture.

    render <id|path.json|path.frag> [--t 0,2,4] [--size 480x270] [--fps 60] [--out DIR [--allow-tracked]]
        PNGs plus receipt.json, by default in state/arsenal/shaders/renders/<id>/
    check [<id> ...] [--set loved|love_top] [--all] [--limit N]
        compile and render one frame per shader: ok or fail, the first error, the media we stood in for, ms per frame;
        the census lands in state/arsenal/shaders/check/<timestamp>.json (each frame beside it, in <timestamp>/)
    filmstrip <id> [--frames 8] [--to 8] [--out DIR [--allow-tracked]]
        one contact-sheet PNG of the shader over time, state/arsenal/shaders/renders/<id>/filmstrip.png
    serve [--port 8797]
        the lab server alone (arsenal/shaders/serve.py), for the headless driver; do not open in a browser

TIME. A still at t is reached in fixed steps of 1/fps from a reset, 60 fps by default: Shadertoy runs at about 60, and
shaders that count iFrame (a glitch timed in frames, spheres placed by frame number) or integrate iTimeDelta draw
Shadertoy's picture only at Shadertoy's rate. toy-runtime.js's DEFAULT_FPS is the same 60 (a test holds them equal).

HOW A PICTURE IS MADE. This module starts the lab server if none is running (a private one, on an ephemeral loopback
port, for the life of this process), writes a plan, and hands it to arsenal/shaders/headless.mjs. The driver takes the
house GPU lock, launches a private headless Chrome forced onto SwiftShader, refuses to render unless the renderer says
SwiftShader, loads /lab/render.html once per job (render.html advances the runtime from a reset to each t, so even a
feedback shader's still is reproducible; a shader with no history jumps straight to the frame that walk ends on), and
writes PNGs and its own result. Work longer than one burst (GPU-LOCK.md:
under three minutes, release between bursts) is split: the driver returns the jobs it had no time for as "deferred", and
this module runs them in the next burst, after a pause long enough for a waiting lane to take the lock first.

WHY THE CHECKS ARE DOUBLED. The renderer string is judged twice: by the driver before any job page loads, and here,
on each page's own report, before a frame counts. judge_renderer below and judgeRenderer in headless.mjs are twins;
tests/test_shader_harness.py runs both over the same strings, so the rule cannot drift in one language only.

THE LICENCE LINE. Renders of corpus shaders are pictures of other people's work. They stay under state/ (gitignored),
and every receipt and contact sheet names the shader, its author and its licence. --out is refused outside <repo>/state/
for a corpus subject whatever else is given (an id, a file under the corpus, or a shader JSON with a Shadertoy id), and
for any other subject unless --allow-tracked says so; the driver checks every job's out_dir again (headless.mjs).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

from . import cli
from . import corpus as C
from . import serve as S

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE_ROOT = ROOT / "state"      # gitignored; headless.mjs STATE_ROOT. Pictures of a corpus shader never leave it
STATE = STATE_ROOT / "arsenal" / "shaders"
RENDERS = STATE / "renders"
CHECKS = STATE / "check"
RUNS = STATE / "runs"            # each run's plans and the driver's own results, kept as evidence
HEADLESS = HERE / "headless.mjs"

RENDER_API = "arsenal.shader-render/v1"
CHECK_API = "arsenal.shader-check/v1"
FILMSTRIP_API = "arsenal.shader-filmstrip/v1"
PLAN_API = "arsenal.shader-headless-plan/v1"     # headless.mjs PLAN_API
RESULT_API = "arsenal.shader-headless/v1"        # headless.mjs RESULT_API

DEFAULT_PAGE = "render.html"
DEFAULT_T = [0.0, 2.0, 4.0]
DEFAULT_SIZE = (480, 270)
DEFAULT_FPS = 60                 # Shadertoy's rate, and toy-runtime.js DEFAULT_FPS (see TIME above)
CHECK_T = [0.0]                  # one frame: frame 0 is the cheapest true test of compile, link and draw
CHECK_SIZE = (320, 180)
FILMSTRIP_SIZE = (320, 180)
FILMSTRIP_COLS = 4
MAX_TIMES = 64
MAX_SIDE = 2048
MAX_FPS = 120
RENDER_TIMEOUT_S = 120           # one job's deadline in the driver; the page's own watchdog fires 5 s before it
CHECK_TIMEOUT_S = 30
FILMSTRIP_TIMEOUT_S = 150
# A job's deadline never exceeds what a burst leaves it: headless.mjs BURST_MS (170 s) less SHUTDOWN_MARGIN_MS (15 s),
# less a few seconds of Chrome start. A longer ask would only be cut short by the driver's budget.
BURST_CAP_S = 150
BURST_GAP_S = 12                 # between bursts: longer than a waiter's 10 s (+20% jitter) poll, so it gets its turn
# The driver's last-resort kill (driver_limit_s): past the lock wait asked for, a waiter can still be in one jam-lane
# poll (60 s) and one jam scan (up to 30 s); then a whole burst (170 s) and the slowest shutdown (about 30 s).
DRIVER_SLACK_S = 150
EXIT_REFUSED, EXIT_LOCK = 3, 4   # headless.mjs EXIT codes
STATUSES = ("done", "timeout", "error", "deferred", "refused")
FLAT_SPREAD = 3                  # a frame whose luma spans fewer levels than this is one flat colour (often black)
PAGE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,80}\.html")

# A renderer string names SwiftShader and no hardware: the twin of judgeRenderer in headless.mjs (same pattern, same order).
# The Direct3D names take a version suffix ("Direct3D11", "D3D12"); a bare \bdirect3d\b would miss "Direct3D11".
HARDWARE_HINT = re.compile(r"\b(amd|radeon|ati|nvidia|geforce|quadro|rtx|intel|iris|uhd graphics|adreno|mali|apple m\d|"
                           r"direct3d\d*|d3d\d+)\b", re.I)


class NotSoftwareRenderer(RuntimeError):
    """The browser would draw on hardware. Nothing renders, by house rule (AMD TDR history)."""


def judge_renderer(renderer) -> Tuple[bool, Optional[str]]:
    if not isinstance(renderer, str) or not renderer.strip():
        return False, "no renderer string (no WebGL2 context, or WEBGL_debug_renderer_info is unavailable)"
    if not re.search(r"swiftshader", renderer, re.I):
        return False, f"the renderer is not SwiftShader: {renderer}"
    hw = HARDWARE_HINT.search(renderer)
    if hw:
        return False, f"the renderer names hardware ({hw.group(0)}): {renderer}"
    return True, None


def assert_software_renderer(renderer) -> str:
    ok, reason = judge_renderer(renderer)
    if not ok:
        raise NotSoftwareRenderer(reason)
    return renderer


# --------------------------------------------------------------------------------------------- argument parsing
def parse_times(text: str) -> List[float]:
    """'0,1.5,4' -> [0.0, 1.5, 4.0]. Each t is a finite number >= 0; at most MAX_TIMES of them."""
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    if not parts:
        raise ValueError("give at least one time, e.g. 0,2,4")
    if len(parts) > MAX_TIMES:
        raise ValueError(f"at most {MAX_TIMES} times per render")
    out = []
    for p in parts:
        try:
            t = float(p)
        except ValueError:
            raise ValueError(f"not a time in seconds: {p!r}") from None
        if t != t or t in (float("inf"), float("-inf")) or t < 0:
            raise ValueError(f"a time must be a finite number of seconds >= 0, not {p!r}")
        out.append(t)
    return out


def parse_size(text: str) -> Tuple[int, int]:
    """'480x270' -> (480, 270). Each side 1..MAX_SIDE."""
    m = re.fullmatch(r"\s*(\d+)\s*[xX*]\s*(\d+)\s*", str(text))
    if not m:
        raise ValueError(f"a size is WIDTHxHEIGHT, e.g. 480x270, not {text!r}")
    w, h = int(m.group(1)), int(m.group(2))
    if not (1 <= w <= MAX_SIDE and 1 <= h <= MAX_SIDE):
        raise ValueError(f"each side must be 1..{MAX_SIDE} pixels")
    return w, h


def _arg(fn):
    def wrapped(text):
        try:
            return fn(text)
        except (ValueError, S.BindRefused) as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None
    wrapped.__name__ = fn.__name__
    return wrapped


def parse_port(text: str) -> int:
    try:
        port = int(text)
    except ValueError:
        raise ValueError(f"not a port: {text!r}") from None
    S.validate_bind(S.HOST, port)   # refuses 8793 (Daniel's server) and anything outside 0..65535
    return port


def parse_fps(text: str) -> int:
    fps = int(text)
    if not 1 <= fps <= MAX_FPS:
        raise ValueError(f"fps must be 1..{MAX_FPS}")
    return fps


def parse_page(text: str) -> str:
    if not PAGE_NAME.fullmatch(text):
        raise ValueError(f"a lab page is a plain file name ending .html, not {text!r}")
    return text


def filmstrip_times(frames: int, to: float) -> List[float]:
    """frames evenly spaced from 0 to `to`, both ends included."""
    if frames < 1 or frames > MAX_TIMES:
        raise ValueError(f"frames must be 1..{MAX_TIMES}")
    if to < 0:
        raise ValueError("--to must be >= 0")
    if frames == 1:
        return [round(float(to), 4)]
    return [round(to * i / (frames - 1), 4) for i in range(frames)]


# ------------------------------------------------------------------------------------------------------ sources
SHADERTOY_ID = re.compile(r"[A-Za-z0-9]{6}")


@dataclass
class Source:
    key: str                     # a corpus id, or local-<stem> for a file
    kind: str                    # corpus | json | frag
    path: Path
    src: str                     # the URL path the page fetches the shader JSON from
    meta: dict = field(default_factory=dict)
    corpus_copy: bool = False    # a file that is someone's published shader (see is_corpus_file)

    @property
    def corpus_subject(self) -> bool:
        """Other people's work: its pictures stay under state/ whatever flag is given."""
        return self.kind == "corpus" or self.corpus_copy


def is_corpus_file(path: Path, shader: dict, corpus: Path) -> bool:
    """A shader file that is a corpus subject: it lies under the corpus, or its info.id is Shadertoy-shaped (six letters
    and digits), which makes it someone's published shader whether or not we saved it. Our own files carry no such id
    (wrap_frag names its shader "local")."""
    try:
        if path.resolve().is_relative_to(Path(corpus).resolve()):
            return True
    except OSError:
        return True  # cannot tell: assume the stricter rule
    sid = (shader.get("info") or {}).get("id")
    return isinstance(sid, str) and bool(SHADERTOY_ID.fullmatch(sid))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-")[:48] or "shader"


def wrap_frag(code: str, name: str) -> dict:
    """A Shadertoy-style fragment (mainImage) as the one-pass shader JSON the runtime reads."""
    if not re.search(r"\bvoid\s+mainImage\s*\(", code):
        raise ValueError("a .frag here must define mainImage(out vec4 fragColor, in vec2 fragCoord), Shadertoy style; "
                         "house sketches (u_res, u_time) render through scripts/vfx_render.py")
    return {"ver": "0.1", "info": {"id": "local", "name": name, "username": "local", "description": "", "tags": []},
            "renderpass": [{"name": "Image", "type": "image", "code": code, "inputs": [],
                            "outputs": [{"id": "4dfGRr", "channel": 0}], "description": ""}]}


def unwrap_json(obj) -> dict:
    """A shader JSON as saved in the corpus, or as Shadertoy's API wraps it ({"Shader": {...}} or a list of one)."""
    if isinstance(obj, list) and len(obj) == 1:
        obj = obj[0]
    if isinstance(obj, dict) and isinstance(obj.get("Shader"), dict):
        obj = obj["Shader"]
    if not isinstance(obj, dict) or not isinstance(obj.get("renderpass"), list) or not obj["renderpass"]:
        raise ValueError("not a shader JSON: it needs a non-empty renderpass list")
    return obj


def stage_job(shader: dict, key: str, jobs_dir: Optional[Path] = None) -> str:
    """Write a loose shader where the lab server's /jobs/ route serves it; returns that URL path.
    jobs_dir defaults to serve.JOBS read at CALL time, so a test can point it elsewhere."""
    jobs_dir = Path(jobs_dir) if jobs_dir is not None else S.JOBS
    body = json.dumps(shader, ensure_ascii=False).encode("utf-8")
    name = f"{key}-{hashlib.sha256(body).hexdigest()[:10]}.json"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / name).write_bytes(body)
    return f"/jobs/{name}"


def resolve_source(arg: str, corpus: Optional[Path] = None) -> Source:
    """A corpus id (or a name that matches exactly one shader), a .json shader, or a .frag with mainImage."""
    corpus = Path(corpus) if corpus is not None else C.CORPUS  # read at call time, like corpus.py does
    p = Path(arg)
    if p.suffix.lower() in (".json", ".frag", ".glsl") and p.is_file():
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".json":
            shader, kind = unwrap_json(json.loads(text)), "json"
        else:
            shader, kind = wrap_frag(text, p.stem), "frag"
        key = "local-" + _slug(p.stem)
        copy = is_corpus_file(p, shader, corpus)
        meta = C.meta_for(shader)
        meta["id"] = key
        if not meta["license"]["explicit"] and not copy:  # Shadertoy's default licence applies to Shadertoy's work only
            meta["license"] = {"license": "not stated (local file)", "explicit": False, "line": ""}
        return Source(key=key, kind=kind, path=p.resolve(), src=stage_job(shader, key), meta=meta, corpus_copy=copy)
    hits = C.resolve(arg, corpus)
    if len(hits) != 1:
        more = f": {', '.join(hits[:8])}" if hits else ""
        raise LookupError(f"{arg!r} names {len(hits)} corpus shaders{more}; give an id, a .json or a .frag")
    sid = hits[0]
    return Source(key=sid, kind="corpus", path=corpus / "shaders" / sid / "shader.json",
                  src=f"/corpus/{sid}/shader.json", meta=C.load_meta(sid, corpus))


class OutDirRefused(ValueError):
    """An output directory a picture may not go to (see THE LICENCE LINE)."""


def out_dir_refusal(out: Path, source: Source, allow_tracked: bool = False) -> Optional[str]:
    """None when `out` may hold this source's pictures, else why not. Anything at or under <repo>/state/ is fine.
    Elsewhere: never for a corpus subject (other people's work), and for our own shader only with --allow-tracked.
    STATE_ROOT is read at call time, so a test can stand a temp state/ in for the real one."""
    target = Path(out).resolve()
    root = Path(STATE_ROOT).resolve()
    if target.is_relative_to(root):
        return None
    if source.corpus_subject:
        return (f"refused: {target} is outside {root}. Pictures of a corpus shader ({source.key}, someone else's work) "
                "stay under state/, which git ignores; --allow-tracked does not apply to them")
    if not allow_tracked:
        return (f"refused: {target} is outside {root}; pass --allow-tracked to write pictures of your own shader "
                "there (never a corpus shader's)")
    return None


def out_dir_for(ns, source: Source, default: Path) -> Path:
    """The verb's output directory, resolved and checked; raises OutDirRefused."""
    out = Path(ns.out).resolve() if getattr(ns, "out", None) else Path(default).resolve()
    why = out_dir_refusal(out, source, bool(getattr(ns, "allow_tracked", False)))
    if why:
        raise OutDirRefused(why)
    return out


def leaves_state(out: Path) -> bool:
    """True when a checked out_dir lies outside state/: the driver is told so (allow_tracked), and checks it again."""
    return not Path(out).resolve().is_relative_to(Path(STATE_ROOT).resolve())


def page_url(base: str, page: str, src: str, times: Sequence[float], size: Tuple[int, int], fps: int,
             budget_ms: int, parity: bool = True) -> str:
    """The render page's query, as the contract names it (src, t, w, h, fps, media) plus the page watchdog's budget,
    and parity=0 only when asked (render.js then compiles without the runtime's GPU-parity shims)."""
    params = {"src": base + src, "t": ",".join(f"{t:g}" for t in times), "w": size[0], "h": size[1], "fps": fps,
              "media": f"{base}/corpus/media/", "budget": budget_ms}
    if not parity:
        params["parity"] = 0
    return f"{base}/lab/{page}?" + urlencode(params, safe="/:,")


# ------------------------------------------------------------------------------------------------------- driver
@dataclass
class Job:
    key: str
    url: str
    out_dir: Path
    prefix: str
    timeout_ms: int
    size: Tuple[int, int]
    screenshot: bool = False
    allow_tracked: bool = False  # out_dir lies outside state/, as --allow-tracked allowed for a non-corpus subject

    def plan_row(self) -> dict:
        return {"key": self.key, "url": self.url, "out_dir": str(self.out_dir), "prefix": self.prefix,
                "timeout_ms": self.timeout_ms, "w": self.size[0], "h": self.size[1], "screenshot": self.screenshot,
                "allow_tracked": bool(self.allow_tracked)}


def build_plan(label: str, jobs: Sequence[Job], lock_wait_ms: int) -> dict:
    return {"api": PLAN_API, "label": label, "lock_wait_ms": int(lock_wait_ms), "jobs": [j.plan_row() for j in jobs]}


def _kill_tree(pid: int) -> None:
    """taskkill /T on the driver we started: node and the Chrome it launched, and nothing else."""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30)


def driver_limit_s(lock_wait_ms: int) -> float:
    """Seconds after which a driver that has not exited is killed (taskkill /T on it): a wedged driver, never a burst
    that keeps its rules (see DRIVER_SLACK_S)."""
    return lock_wait_ms / 1000 + BURST_CAP_S + DRIVER_SLACK_S


def _run_burst(plan: dict, run_dir: Path, n: int, lock_wait_ms: int, quiet: bool) -> Tuple[int, dict]:
    plan_path, result_path = run_dir / f"plan-{n}.json", run_dir / f"result-{n}.json"
    plan_path.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    proc = subprocess.Popen(["node", str(HEADLESS), "--plan", str(plan_path), "--result", str(result_path)],
                            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    limit_s = driver_limit_s(lock_wait_ms)
    timer = threading.Timer(limit_s, _kill_tree, args=(proc.pid,))
    timer.daemon = True
    timer.start()
    try:
        for line in proc.stdout:  # the driver's progress goes to stderr, so --json on stdout stays clean
            if not quiet:
                sys.stderr.write(line)
                sys.stderr.flush()
        code = proc.wait()
    finally:
        timer.cancel()
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result = {"api": RESULT_API, "jobs": [], "error": f"the driver wrote no result (exit {code}, limit {limit_s:.0f} s)"}
    result["_path"] = str(result_path)
    return code, result


def run_jobs(jobs: Sequence[Job], label: str, lock_wait_min: float = 10, quiet: bool = False) -> dict:
    """Run jobs through the driver in as many bursts as they need. Returns {software, chrome, rows: {key: row}, bursts}."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS / f"{stamp}-{os.getpid()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    lock_wait_ms = int(lock_wait_min * 60_000)
    merged = {"run_dir": str(run_dir), "software": None, "chrome": None, "rows": {}, "bursts": [], "refused": None,
              "error": None}
    pending = list(jobs)
    n = 0
    while pending:
        n += 1
        if n > 1:
            time.sleep(BURST_GAP_S)
        code, result = _run_burst(build_plan(label, pending, lock_wait_ms), run_dir, n, lock_wait_ms, quiet)
        merged["bursts"].append({"n": n, "exit": code, "result": result.get("_path"), "lock": result.get("lock"),
                                 "timings": result.get("timings"), "jobs": len(pending),
                                 "chrome_launches": (result.get("chrome") or {}).get("launches")})
        merged["software"] = merged["software"] or result.get("software")
        merged["chrome"] = merged["chrome"] or (result.get("chrome") or {}).get("version")
        rows = {r.get("key"): r for r in result.get("jobs") or []}
        deferred = []
        for job in pending:
            row = rows.get(job.key) or {"key": job.key, "url": job.url, "status": "error",
                                        "error": result.get("error") or f"the driver returned no row (exit {code})"}
            if row.get("status") == "deferred" and code not in (EXIT_REFUSED, EXIT_LOCK):
                deferred.append(job)
            merged["rows"][job.key] = row
        if code == EXIT_REFUSED:
            merged["refused"] = result.get("refused") or "the driver refused to render"
            break
        if code == EXIT_LOCK:
            merged["error"] = result.get("error") or "GPU lock not taken"
            break
        if result.get("error") and not deferred:
            merged["error"] = result["error"]
        if len(deferred) == len(pending):  # no progress at all: never loop on a burst that does nothing
            merged["error"] = merged["error"] or "a burst completed no job"
            break
        pending = deferred
    return merged


# -------------------------------------------------------------------------------------------------- frame facts
def frame_facts(path: Optional[str]) -> dict:
    """{mean_luma, flat} for a PNG we wrote: a decodable image, and whether it is one flat colour (a black frame, say)."""
    if not path:
        return {"mean_luma": None, "flat": None}
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            lum = im.convert("L")
            lo, hi = lum.getextrema()
            return {"mean_luma": round(ImageStat.Stat(lum).mean[0], 2), "flat": (hi - lo) < FLAT_SPREAD}
    except Exception as exc:  # a PNG that does not decode is a fact worth recording, not a crash
        return {"mean_luma": None, "flat": None, "decode_error": f"{type(exc).__name__}: {exc}"}


def pass_error(p: dict) -> str:
    """One failed pass's first error: render.js's own summary (firstError), else the first line of its mapped log."""
    if p.get("firstError"):
        return str(p["firstError"]).strip()
    log = str(p.get("mappedLog") or p.get("log") or "")
    return next((ln.strip() for ln in log.splitlines() if ln.strip()), "did not compile")


def frame_walk(f: dict) -> dict:
    """How the page reached a still (render.js): the iFrame it shows, how many frames it drew to get there, whether
    that walk began from a reset, and whether it jumped (a shader without history draws only the walk's last frame).
    Absent keys stay absent (the probe page draws each t directly)."""
    names = {"frame": "frame", "frames": "frames_walked", "reset": "reset", "jumped": "jumped"}
    return {ours: f[theirs] for theirs, ours in names.items() if theirs in f}


def first_error(row: dict) -> Optional[str]:
    """The first thing that went wrong for one job: a pass's first log line, the page's first error, the driver's."""
    render = row.get("render") or {}
    for p in (render.get("compile") or {}).get("passes") or []:
        if not p.get("ok"):
            return f"{p.get('name')}: {pass_error(p)}"[:300]
    for e in render.get("errors") or []:
        return str(e)[:300]
    if row.get("error"):
        return str(row["error"])[:300]
    for c in row.get("console") or []:
        if c.get("type") in ("exception", "error"):
            return f"{c.get('type')}: {c.get('text')}"[:300]
    return None


# ----------------------------------------------------------------------------------------------------- receipts
RECEIPT_FIELDS = {
    "api": str, "id": str, "name": (str, type(None)), "author": (str, type(None)), "license": (str, type(None)),
    "source": dict, "request": dict, "ok": bool, "status": str, "renderer": (str, type(None)),
    "software_renderer": bool, "chrome": (str, type(None)), "compile": (dict, type(None)), "frames": list,
    "substituted": list, "unsupported": list, "errors": list, "timings": dict, "started_at": str, "finished_at": str,
    "driver": dict,
}
FRAME_FIELDS = {"t": (int, float), "png": (str, type(None)), "ms": (int, float, type(None)), "bytes": int}


def validate_receipt(receipt: dict) -> List[str]:
    """Problems with a render receipt's shape ([] when it is sound)."""
    problems = []
    if not isinstance(receipt, dict):
        return ["a receipt is a JSON object"]
    for key, kind in RECEIPT_FIELDS.items():
        if key not in receipt:
            problems.append(f"missing {key}")
        elif not isinstance(receipt[key], kind) or (kind is int and isinstance(receipt[key], bool)):
            problems.append(f"{key} has the wrong type ({type(receipt[key]).__name__})")
    if receipt.get("api") not in (RENDER_API, FILMSTRIP_API):
        problems.append(f"api is {receipt.get('api')!r}")
    if receipt.get("status") not in STATUSES:
        problems.append(f"status {receipt.get('status')!r} is not one of {STATUSES}")
    for i, f in enumerate(receipt.get("frames") or []):
        for key, kind in FRAME_FIELDS.items():
            if key not in f or not isinstance(f[key], kind) or isinstance(f[key], bool):
                problems.append(f"frames[{i}].{key} missing or the wrong type")
    if receipt.get("ok") is True:
        if not receipt.get("software_renderer"):
            problems.append("ok without a software renderer")
        if not receipt.get("frames") or any(not f.get("png") for f in receipt["frames"]):
            problems.append("ok without every frame written")
        if receipt.get("status") != "done":
            problems.append("ok but the status is not done")
    return problems


def build_receipt(source: Source, request: dict, row: dict, merged: dict, started_at: str,
                  api: str = RENDER_API) -> dict:
    """One shader's receipt from the driver's row. The renderer is judged again here; a frame counts only if it holds."""
    render = row.get("render") or {}
    renderer = render.get("renderer") or ((merged.get("software") or {}).get("webgl") or {}).get("renderer")
    software, why = judge_renderer(renderer)
    status = row.get("status") or "error"
    if status not in STATUSES:
        status = "error"
    errors = [str(e) for e in render.get("errors") or []]
    if row.get("error"):
        errors.append(str(row["error"]))
    frames = []
    if status == "done" and not software:
        status = "refused"
        errors.append(f"frames not counted: {why}")
    elif status == "done":
        for f in row.get("frames") or []:
            frames.append({"t": float(f.get("t") or 0), "png": f.get("file"), "ms": f.get("ms"),
                           "bytes": int(f.get("bytes") or 0), **frame_walk(f), **frame_facts(f.get("file"))})
    wanted = len(request.get("t") or [])
    ok = (status == "done" and software and render.get("ok") is True and len(frames) == wanted
          and all(f["png"] for f in frames))
    lic = source.meta.get("license") or {}
    return {
        "api": api, "id": source.key, "name": source.meta.get("name"), "author": source.meta.get("author"),
        "license": lic.get("license") if isinstance(lic, dict) else lic, "url": source.meta.get("url"),
        "source": {"kind": source.kind, "path": str(source.path), "src": source.src},
        "request": request, "ok": bool(ok), "status": status,
        "renderer": renderer, "software_renderer": bool(software), "chrome": merged.get("chrome"),
        "compile": render.get("compile"), "frames": frames,
        "substituted": list(render.get("substituted") or []), "unsupported": list(render.get("unsupported") or []),
        "errors": errors, "first_error": None if ok else first_error(row),
        "console": (row.get("console") or [])[:20], "screenshot": row.get("screenshot"),
        "history": render.get("history"),
        "timings": {"page_wall_ms": row.get("wall_ms"),
                    "frame_ms": [f["ms"] for f in frames],
                    "warm_ms": render.get("warmMs"),
                    "lock_wait_ms": [((b.get("lock") or {}).get("wait_ms")) for b in merged.get("bursts") or []],
                    "chrome_start_ms": [l.get("start_ms") for b in merged.get("bursts") or []
                                        for l in (b.get("chrome_launches") or [])]},
        "started_at": started_at, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "driver": {"run_dir": merged.get("run_dir"), "bursts": len(merged.get("bursts") or []),
                   "refused": merged.get("refused"), "error": merged.get("error"),
                   "gpu_feature_status": (merged.get("software") or {}).get("feature_status")},
        "note": "a picture of the named author's shader under its licence; it stays under state/" if source.corpus_subject
                else "a local file",
    }


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------------------------------------- verbs
def _timeout_ms(ns, default_s: float) -> int:
    seconds = ns.timeout if getattr(ns, "timeout", None) else default_s
    return int(min(max(5.0, seconds), BURST_CAP_S) * 1000)


def _page_ready(page: str) -> Optional[str]:
    if not (S.LAB / page).is_file():
        return f"{S.LAB / page} does not exist"
    return None


class _Lab:
    """The lab server for one verb: an existing one on --port, else a private ephemeral one closed on exit."""
    def __init__(self, port: int):
        self.server, self.base = S.base_for(port)

    def __enter__(self):
        return self.base

    def __exit__(self, *exc):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


def cmd_render(ns) -> int:
    missing = _page_ready(ns.page)
    if missing:
        print(missing, file=sys.stderr)
        return 2
    try:
        source = resolve_source(ns.source)
        out_dir = out_dir_for(ns, source, RENDERS / source.key)
    except (LookupError, ValueError, OSError) as exc:  # OutDirRefused is a ValueError: refused before any work
        print(str(exc), file=sys.stderr)
        return 2
    timeout_ms = _timeout_ms(ns, RENDER_TIMEOUT_S)
    request = {"t": ns.t, "w": ns.size[0], "h": ns.size[1], "fps": ns.fps, "page": ns.page, "timeout_ms": timeout_ms,
               "parity": ns.parity}
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.monotonic()
    with _Lab(ns.port) as base:
        url = page_url(base, ns.page, source.src, ns.t, ns.size, ns.fps, max(5000, timeout_ms - 5000), ns.parity)
        job = Job(source.key, url, out_dir, "", timeout_ms, ns.size, ns.screenshot, allow_tracked=leaves_state(out_dir))
        merged = run_jobs([job], f"shader render {source.key}", ns.lock_wait_min, quiet=ns.json)
    receipt = build_receipt(source, request, merged["rows"][source.key], merged, started)
    receipt["request"]["base"] = base
    receipt["timings"]["wall_ms"] = round((time.monotonic() - t0) * 1000)
    _write_json(out_dir / "receipt.json", receipt)
    receipt["receipt"] = str(out_dir / "receipt.json")

    def human(r):
        head = (f"{'rendered' if r['ok'] else r['status'].upper()}: {r['id']} \"{r['name']}\" by {r['author']} "
                f"({r['license']}) in {r['timings']['wall_ms'] / 1000:.1f} s")
        lines = [head, f"  renderer: {r['renderer']}"]
        lines += [f"  t={f['t']:<6g} {f['ms'] if f['ms'] is not None else '?':>8} ms  {f['png']}"
                  + ("  (one flat colour)" if f.get("flat") else "") for f in r["frames"]]
        if r["substituted"]:
            lines.append(f"  stood in for: {json.dumps(r['substituted'])[:300]}")
        if r["unsupported"]:
            lines.append(f"  unsupported: {json.dumps(r['unsupported'])[:300]}")
        if r["first_error"]:
            lines.append(f"  first error: {r['first_error']}")
        if r["driver"]["refused"]:
            lines.append(f"  REFUSED: {r['driver']['refused']}")
        lines.append(f"  receipt: {r['receipt']}")
        return "\n".join(lines)
    cli._print(receipt, ns.json, human)
    if merged.get("refused"):
        return EXIT_REFUSED
    return 0 if receipt["ok"] else 1


def check_ids(ns, corpus: Optional[Path] = None) -> Tuple[List[str], List[str]]:
    """(ids to check, ids named but not saved). Explicit ids first, then --set, or --all."""
    corpus = Path(corpus) if corpus is not None else C.CORPUS
    have = set(C.all_ids(corpus))
    wanted: List[str] = []
    if ns.all:
        wanted = C.all_ids(corpus)
    else:
        wanted = list(ns.ids or [])
        if ns.set:
            sets = C.load_sets(corpus)
            if ns.set not in sets:
                raise LookupError(f"no set {ns.set!r}; sets: {', '.join(k for k in sets if not k.startswith('_'))}")
            wanted += [i for i in sets[ns.set] if i not in wanted]
    if not wanted:
        raise LookupError("give shader ids, --set NAME, or --all")
    ids = [i for i in wanted if i in have]
    missing = [i for i in wanted if i not in have]
    if ns.limit:
        ids = ids[: ns.limit]
    return ids, missing


def census_row(meta: dict, row: dict, merged: dict) -> dict:
    render = row.get("render") or {}
    renderer = render.get("renderer") or ((merged.get("software") or {}).get("webgl") or {}).get("renderer")
    software, _ = judge_renderer(renderer)
    status = row.get("status") or "error"
    frames = [f for f in row.get("frames") or [] if f.get("file")] if status == "done" and software else []
    facts = frame_facts(frames[0]["file"]) if frames else {"mean_luma": None, "flat": None}
    ms = [f.get("ms") for f in frames if isinstance(f.get("ms"), (int, float))]
    # A still's ms covers its whole walk (render.js draws every frame from a reset up to t), so the cost of ONE frame is
    # the ms over the frames walked when the page says how many; the probe page draws each t once.
    walked = [f.get("frames") for f in frames if isinstance(f.get("frames"), int) and f.get("frames") > 0]
    per_frame = (sum(ms) / sum(walked) if ms and len(walked) == len(ms)
                 else sum(ms) / len(ms) if ms else None)
    ok = status == "done" and software and render.get("ok") is True and bool(frames)
    passes = (render.get("compile") or {}).get("passes") or []
    lic = meta.get("license") or {}
    return {
        "id": meta.get("id"), "name": meta.get("name"), "author": meta.get("author"),
        "license": lic.get("license") if isinstance(lic, dict) else lic,
        "ok": bool(ok), "status": status if (software or status != "done") else "refused",
        "first_error": None if ok else first_error(row),
        "pass_errors": [{"pass": p.get("name"), "error": pass_error(p)[:300]} for p in passes if not p.get("ok")],
        "substituted": list(render.get("substituted") or []), "unsupported": list(render.get("unsupported") or []),
        "ms_per_frame": round(per_frame, 1) if per_frame is not None else None,
        "ms_per_still": round(sum(ms) / len(ms), 1) if ms else None,
        # One frame drawn after the stills, timed to completion: the per-frame cost without the first draw's compile.
        "warm_ms": render.get("warmMs") if isinstance(render.get("warmMs"), (int, float)) else None,
        "history": render.get("history"),
        "frames_walked": sum(walked) if walked else None,
        "flat": facts.get("flat"), "mean_luma": facts.get("mean_luma"),
        "png": frames[0]["file"] if frames else None, "wall_ms": row.get("wall_ms"),
    }


def cmd_check(ns) -> int:
    missing_page = _page_ready(ns.page)
    if missing_page:
        print(missing_page, file=sys.stderr)
        return 2
    try:
        ids, not_saved = check_ids(ns)
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    stamp = time.strftime("%Y%m%d-%H%M%S")
    frames_dir = CHECKS / stamp
    timeout_ms = _timeout_ms(ns, CHECK_TIMEOUT_S)
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.monotonic()
    metas = {sid: C.load_meta(sid) for sid in ids}
    with _Lab(ns.port) as base:
        jobs = [Job(sid, page_url(base, ns.page, f"/corpus/{sid}/shader.json", ns.t, ns.size, ns.fps,
                                  max(5000, timeout_ms - 5000), ns.parity),
                    frames_dir, f"{sid}_", timeout_ms, ns.size) for sid in ids]
        merged = run_jobs(jobs, f"shader check ({len(ids)})", ns.lock_wait_min, quiet=ns.json)
    rows = [census_row(metas[sid], merged["rows"].get(sid) or {"status": "error", "error": "no row"}, merged)
            for sid in ids]
    count = lambda pred: sum(1 for r in rows if pred(r))  # noqa: E731
    census = {
        "api": CHECK_API, "started_at": started, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "wall_ms": round((time.monotonic() - t0) * 1000), "set": ns.set, "all": bool(ns.all),
        "request": {"t": ns.t, "w": ns.size[0], "h": ns.size[1], "fps": ns.fps, "page": ns.page, "timeout_ms": timeout_ms,
                    "parity": ns.parity},
        "renderer": ((merged.get("software") or {}).get("webgl") or {}).get("renderer"), "chrome": merged.get("chrome"),
        "refused": merged.get("refused"), "error": merged.get("error"), "not_saved": not_saved,
        "probe_page": ns.page != DEFAULT_PAGE,  # a stand-in page draws its own picture: it proves the harness only
        "summary": {"checked": len(rows), "ok": count(lambda r: r["ok"]), "fail": count(lambda r: not r["ok"]),
                    "timeout": count(lambda r: r["status"] == "timeout"),
                    "deferred": count(lambda r: r["status"] == "deferred"),
                    "flat": count(lambda r: r["flat"] is True),
                    "with_stand_ins": count(lambda r: bool(r["substituted"]))},
        "bursts": merged.get("bursts"), "frames_dir": str(frames_dir), "shaders": rows,
    }
    out = CHECKS / f"{stamp}.json"
    _write_json(out, census)
    census["census"] = str(out)

    def human(c):
        s = c["summary"]
        lines = [f"checked {s['checked']} shaders in {c['wall_ms'] / 1000:.0f} s on {c['renderer']}"
                 + (f"  (page {c['request']['page']}: a harness proof, not a verdict on these shaders)"
                    if c["probe_page"] else ""),
                 f"  ok {s['ok']}  fail {s['fail']}  (timeout {s['timeout']}, deferred {s['deferred']})  "
                 f"flat frame {s['flat']}  with stand-in media {s['with_stand_ins']}"]
        if c["refused"]:
            lines.append(f"  REFUSED: {c['refused']}")
        if c["error"]:
            lines.append(f"  driver: {c['error'][:300]}")
        for r in c["shaders"]:
            mark = "ok  " if r["ok"] else "FAIL"
            ms = f"{r['ms_per_frame']:>7} ms" if r["ms_per_frame"] is not None else "      - ms"
            warm = f"warm {r['warm_ms']:>7} ms" if r.get("warm_ms") is not None else "warm       - ms"
            tail = r["first_error"] or ("flat frame" if r["flat"] else "")
            lines.append(f"  {mark} {r['id']}  {(r['name'] or '')[:28]:<28} {ms}  {warm}  {tail[:100]}")
        if c["not_saved"]:
            lines.append(f"  not in the corpus yet: {' '.join(c['not_saved'])}")
        lines.append(f"  census: {c['census']}")
        return "\n".join(lines)
    cli._print(census, ns.json, human)
    if merged.get("refused"):
        return EXIT_REFUSED
    return 0


def contact_sheet(frames: Sequence[dict], header: str, out: Path, cols: int = FILMSTRIP_COLS,
                  cell: Tuple[int, int] = FILMSTRIP_SIZE) -> Path:
    """Frames ({t, png}) in a grid under a one-line header naming the shader, its author and its licence."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:  # Pillow older than 10.1
        font = ImageFont.load_default()
    cols = max(1, min(cols, len(frames) or 1))
    rows = max(1, -(-len(frames) // cols))
    pad, head_h = 6, 26
    w, h = cell
    sheet = Image.new("RGB", (pad + cols * (w + pad), head_h + pad + rows * (h + pad)), (11, 13, 18))
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 6), header, fill=(216, 221, 230), font=font)
    for i, f in enumerate(frames):
        x, y = pad + (i % cols) * (w + pad), head_h + pad + (i // cols) * (h + pad)
        if f.get("png") and Path(f["png"]).is_file():
            with Image.open(f["png"]) as im:
                sheet.paste(im.convert("RGB").resize((w, h)), (x, y))
        else:
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=(30, 22, 26))
            draw.text((x + 8, y + h // 2 - 7), "no frame", fill=(220, 120, 120), font=font)
        label = f"t={f.get('t', 0):g}s"
        box = draw.textbbox((0, 0), label, font=font)
        draw.rectangle([x, y + h - (box[3] - box[1]) - 8, x + (box[2] - box[0]) + 8, y + h], fill=(0, 0, 0))
        draw.text((x + 4, y + h - (box[3] - box[1]) - 6), label, fill=(230, 230, 230), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def cmd_filmstrip(ns) -> int:
    missing = _page_ready(ns.page)
    if missing:
        print(missing, file=sys.stderr)
        return 2
    try:
        source = resolve_source(ns.source)
        times = filmstrip_times(ns.frames, ns.to)
        base_dir = out_dir_for(ns, source, RENDERS / source.key)
    except (LookupError, ValueError, OSError) as exc:  # OutDirRefused is a ValueError: refused before any work
        print(str(exc), file=sys.stderr)
        return 2
    frames_dir = base_dir / "filmstrip"
    timeout_ms = _timeout_ms(ns, FILMSTRIP_TIMEOUT_S)
    request = {"t": times, "w": ns.size[0], "h": ns.size[1], "fps": ns.fps, "page": ns.page, "timeout_ms": timeout_ms,
               "frames": ns.frames, "to": ns.to}
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.monotonic()
    with _Lab(ns.port) as base:
        url = page_url(base, ns.page, source.src, times, ns.size, ns.fps, max(5000, timeout_ms - 5000), ns.parity)
        merged = run_jobs([Job(source.key, url, frames_dir, "", timeout_ms, ns.size,
                               allow_tracked=leaves_state(frames_dir))],
                          f"shader filmstrip {source.key}", ns.lock_wait_min, quiet=ns.json)
    receipt = build_receipt(source, request, merged["rows"][source.key], merged, started, api=FILMSTRIP_API)
    receipt["timings"]["wall_ms"] = round((time.monotonic() - t0) * 1000)
    sheet = None
    if receipt["frames"]:
        header = (f"{receipt['name']} by {receipt['author']}  |  {receipt['license']}  |  {source.key}  |  "
                  f"0..{ns.to:g} s, {ns.frames} frames, {ns.fps} fps steps from a reset  |  SwiftShader")[:160]
        sheet = contact_sheet([{"t": f["t"], "png": f["png"]} for f in receipt["frames"]], header,
                              base_dir / "filmstrip.png", cols=ns.cols, cell=ns.size)
    receipt["sheet"] = str(sheet) if sheet else None
    _write_json(base_dir / "filmstrip.json", receipt)
    receipt["receipt"] = str(base_dir / "filmstrip.json")
    cli._print(receipt, ns.json, lambda r: (
        f"{'filmstrip' if r['sheet'] else r['status'].upper()}: {r['id']} \"{r['name']}\" by {r['author']}, "
        f"{len(r['frames'])}/{ns.frames} frames in {r['timings']['wall_ms'] / 1000:.1f} s\n"
        + (f"  sheet: {r['sheet']}\n" if r["sheet"] else "")
        + (f"  first error: {r['first_error']}\n" if r["first_error"] else "")
        + f"  receipt: {r['receipt']}"))
    if merged.get("refused"):
        return EXIT_REFUSED
    return 0 if sheet else 1


def cmd_serve(ns) -> int:
    return S.serve(ns.port, verbose=ns.verbose)


# ---------------------------------------------------------------------------------------------------- registration
def _out(p: argparse.ArgumentParser, default: str) -> None:
    p.add_argument("--out", help=f"directory (default {default}); outside state/ only with --allow-tracked, never for "
                                 "a corpus shader")
    p.add_argument("--allow-tracked", action="store_true",
                   help="let --out lie outside state/ for a shader of your own (.frag or .json, not from the corpus)")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--fps", type=_arg(parse_fps), default=DEFAULT_FPS,
                   help=f"the fixed step used to advance to each t (default {DEFAULT_FPS}, Shadertoy's rate)")
    p.add_argument("--page", type=_arg(parse_page), default=DEFAULT_PAGE,
                   help="the lab page to load (render.html; _harness_probe.html proves the harness alone)")
    p.add_argument("--port", type=_arg(parse_port), default=S.DEFAULT_PORT,
                   help="reuse a lab server on this port if one runs there (else a private one starts)")
    p.add_argument("--timeout", type=float, default=None, help=f"seconds one job may take (at most {BURST_CAP_S})")
    p.add_argument("--lock-wait-min", type=float, default=10, help="minutes to wait for the GPU lock")
    p.add_argument("--no-parity", dest="parity", action="store_false",
                   help="compile without the runtime's GPU-parity shims (tanh, min/max NaN rules): SwiftShader as is")


def register_render(sub) -> None:
    p = sub.add_parser("render", help="render a shader to PNGs on SwiftShader, with a receipt")
    p.add_argument("source", help="a corpus id (or a name matching one shader), a shader .json, or a .frag with mainImage")
    p.add_argument("--t", type=_arg(parse_times), default=list(DEFAULT_T), help="times in seconds, e.g. 0,1.5,4")
    p.add_argument("--size", type=_arg(parse_size), default=DEFAULT_SIZE, help="WIDTHxHEIGHT, default 480x270")
    _out(p, "state/arsenal/shaders/renders/<id>, for the PNGs and receipt.json")
    p.add_argument("--screenshot", action="store_true", help="also save a screenshot of the whole page")
    _common(p)
    p.set_defaults(fn=cmd_render)


def register_check(sub) -> None:
    p = sub.add_parser("check", help="compile and render one frame per shader; a census of what works")
    p.add_argument("ids", nargs="*", help="corpus ids")
    p.add_argument("--set", help="a named set from sets.json (loved, love_top)")
    p.add_argument("--all", action="store_true", help="every shader in the corpus")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--t", type=_arg(parse_times), default=list(CHECK_T), help="times (default 0: frame zero)")
    p.add_argument("--size", type=_arg(parse_size), default=CHECK_SIZE, help="WIDTHxHEIGHT, default 320x180")
    _common(p)
    p.set_defaults(fn=cmd_check)


def register_filmstrip(sub) -> None:
    p = sub.add_parser("filmstrip", help="one contact-sheet PNG of a shader over time")
    p.add_argument("source", help="a corpus id (or a unique name), a shader .json, or a .frag with mainImage")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--to", type=float, default=8.0, help="last time in seconds (frames are spaced from 0 to this)")
    p.add_argument("--size", type=_arg(parse_size), default=FILMSTRIP_SIZE, help="one cell, WIDTHxHEIGHT")
    p.add_argument("--cols", type=int, default=FILMSTRIP_COLS)
    _out(p, "state/arsenal/shaders/renders/<id>")
    _common(p)
    p.set_defaults(fn=cmd_filmstrip)


def register_serve(sub) -> None:
    p = sub.add_parser("serve", help=f"the lab server on {S.HOST} (default port {S.DEFAULT_PORT}; 8793 is refused), "
                                     f"{S.HEADLESS_ONLY}")
    p.add_argument("--port", type=_arg(parse_port), default=S.DEFAULT_PORT)
    p.add_argument("--verbose", action="store_true", help="log every request, not only failures")
    p.set_defaults(fn=cmd_serve)


cli.VERBS["render"] = register_render
cli.VERBS["check"] = register_check
cli.VERBS["filmstrip"] = register_filmstrip
cli.VERBS["serve"] = register_serve
