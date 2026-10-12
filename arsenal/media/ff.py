"""arsenal.media.ff -- find and run ffmpeg/ffprobe, say what the build can do, escape Windows paths for filters.

Every ffmpeg or ffprobe call in arsenal.media goes through run() or popen(), so the binary, `-hide_banner -nostdin`,
stderr capture and the exact argv for the receipt live in one place. Agents hunted for ffmpeg 113 times in 53
transcripts and typed its path by hand 203 times before this existed.

Search order, first hit wins:
  1. ARSENAL_FFMPEG: a path to ffmpeg(.exe), or to the folder that holds it (ffprobe is taken from beside it);
  2. the location `py -m arsenal.media doctor --save` cached in <state>/config.json;
  3. ffmpeg on PATH;
  4. imageio-ffmpeg's bundled copy, with a loud warning (no AMF, no whisper, no libass, no ffprobe).
The cached choice sits above PATH on purpose: it is written only by an explicit `doctor --save`, which picks the
most capable build on the machine, while PATH can hold whatever an installer dropped there.

<state> is ARSENAL_MEDIA_STATE when set (tests point it at a temp folder), else state/arsenal/media in the repo.
"""
from __future__ import annotations

import glob
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Sequence

FFMPEG_ENV = "ARSENAL_FFMPEG"
STATE_ENV = "ARSENAL_MEDIA_STATE"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXE = ".exe" if os.name == "nt" else ""
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW: no console flash per call

NO_FFMPEG = (f"no ffmpeg found: set {FFMPEG_ENV} to ffmpeg.exe (or its folder), or run "
             f"`py -m arsenal.media doctor --save` to find and remember the best build on this machine")
BUNDLED_WARNING = ("using imageio-ffmpeg's bundled ffmpeg: it ships no ffprobe, and builds vary (the 7.1 one here "
                   "has AMF and libass but no whisper); run `py -m arsenal.media doctor --save` to pick the house build")

#: Encoders and filters the primitives care about; caps() reports each as true/false.
WATCH_ENCODERS = ("h264_amf", "hevc_amf", "av1_amf", "libx264", "libx265", "libsvtav1", "libvpx-vp9",
                  "prores_ks", "dnxhd", "libopus", "aac", "flac", "pcm_s16le")
WATCH_FILTERS = ("scdet", "scale", "crop", "ebur128", "loudnorm", "silencedetect", "blackdetect", "freezedetect",
                 "whisper", "ass", "subtitles", "libplacebo", "showwavespic", "amix", "pan", "volume", "xfade")

#: Measured failures on this machine. A primitive that would take one of these paths says so instead.
KNOWN_BAD = {
    "vulkan_hevc_decode": "Vulkan HEVC decode fails on this driver (error -1145393733, measured 2026-10-12)",
    "whisper_filter_gpu": "the whisper filter's GPU path rejects gfx1201 and falls back to CPU at 0.62x realtime",
    "d3d11va_bit_exact": "d3d11va output differs from software decode by up to 7 luma levels on the same frame; "
                         "decode in software (hw=None) for pixel-exact comparisons",
}

#: Optional Python packages the primitives use when present. Each has a fallback.
OPTIONAL_PACKAGES = {
    "av": "PyAV: probe fallback, house analysis",
    "numpy": "frames as arrays",
    "PIL": "contact sheets, alpha WebP export",
    "cv2": "template matching (League clock fallback)",
    "soundfile": "audio blocks",
    "librosa": "onsets for avsync",
    "scipy": "cross-correlation for avsync",
    "faster_whisper": "speech to text (words)",
    "scenedetect": "shots: ContentDetector (fallback: ffmpeg scdet + spike rule)",
    "rapidocr": "League clock OCR (fallback: digit templates on cv2)",
    "pymediainfo": "probe: encoder application, CFR/VBR (fallback: ffprobe tags only)",
    "imageio_ffmpeg": "last-resort ffmpeg",
}


class MediaError(RuntimeError):
    """A primitive refusing, with a one-line reason; argv and stderr when ffmpeg/ffprobe was the one that failed."""

    def __init__(self, message: str, *, argv: Optional[Sequence[str]] = None, stderr: str = ""):
        super().__init__(message)
        self.argv = list(argv) if argv else None
        self.stderr = stderr


# =================================================================================================
# state
# =================================================================================================

def state_dir() -> Path:
    """Where arsenal.media keeps its config, caps cache, catalog, sidecars and receipts (gitignored)."""
    return Path(os.environ.get(STATE_ENV) or _default_state_dir())


def config_path() -> Path:
    return state_dir() / "config.json"


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


# =================================================================================================
# locate
# =================================================================================================

def _sibling(ffmpeg_path: str, name: str) -> Optional[str]:
    p = Path(ffmpeg_path).with_name(name + _EXE)
    return str(p) if p.is_file() else None


def _from_env() -> Optional[str]:
    raw = os.environ.get(FFMPEG_ENV, "").strip().strip('"')
    if not raw:
        return None
    p = Path(raw)
    if p.is_dir():
        p = p / ("ffmpeg" + _EXE)
    if p.is_file():
        return str(p)
    found = shutil.which(raw)
    if found:
        return found
    raise MediaError(f"{FFMPEG_ENV} is set to {raw!r}, but there is no ffmpeg there; fix the path or clear "
                     f"{FFMPEG_ENV}")


def _default_state_dir() -> Path:
    return _REPO_ROOT / "state" / "arsenal" / "media"


def _from_config() -> Optional[str]:
    """The saved choice in <state>, then in the repo's default state: a test that relocates state for isolation
    still finds the house build."""
    for cfg in dict.fromkeys([config_path(), _default_state_dir() / "config.json"]):
        p = (_read_json(cfg) or {}).get("ffmpeg")
        if p and os.path.isfile(p):
            return p
    return None


def _bundled() -> Optional[str]:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


_located: Dict[tuple, dict] = {}


def locate(refresh: bool = False) -> dict:
    """{"ffmpeg", "ffprobe", "source", "warning"}: which binaries the house uses, and why."""
    cfg = config_path()
    key = (os.environ.get(FFMPEG_ENV, ""), str(cfg), cfg.stat().st_mtime_ns if cfg.is_file() else 0)
    if not refresh and key in _located:
        return dict(_located[key])
    found = None
    for source, finder in (("env", _from_env), ("config", _from_config), ("path", lambda: shutil.which("ffmpeg"))):
        ff = finder()
        if ff:
            probe = _sibling(ff, "ffprobe") or (shutil.which("ffprobe") if source == "path" else None)
            found = {"ffmpeg": ff, "ffprobe": probe, "source": source, "warning": None}
            break
    if found is None:
        bundled = _bundled()
        if not bundled:
            raise MediaError(NO_FFMPEG)
        found = {"ffmpeg": bundled, "ffprobe": None, "source": "imageio-ffmpeg", "warning": BUNDLED_WARNING}
        warnings.warn(BUNDLED_WARNING, stacklevel=2)
    _located.clear()
    _located[key] = found
    return dict(found)


def ffmpeg() -> str:
    return locate()["ffmpeg"]


def ffprobe() -> str:
    loc = locate()
    if not loc["ffprobe"]:
        raise MediaError(f"no ffprobe beside {loc['ffmpeg']} (source: {loc['source']}); point {FFMPEG_ENV} at a "
                         f"build that ships both, or run `py -m arsenal.media doctor --save`")
    return loc["ffprobe"]


# =================================================================================================
# run
# =================================================================================================

_gpu_lock_warned = False


def _gpu_wrap(argv: List[str], label: str) -> List[str]:
    """Run argv under the house GPU lock (arsenal/GPU-LOCK.md: one locking story for every lane)."""
    global _gpu_lock_warned
    node = shutil.which("node")
    helper = _REPO_ROOT / "arsenal" / "lanes" / "gpu_lock.mjs"
    if not node or not helper.is_file():
        if not _gpu_lock_warned:           # once per process: a stream of spawns must not bury real warnings
            _gpu_lock_warned = True
            warnings.warn(f"GPU lock unavailable (node={bool(node)}, helper={helper.is_file()}); running GPU "
                          f"work such as {label!r} without it", stacklevel=3)
        return argv
    return [node, str(helper), "run", "--label", f"arsenal.media {label}", "--"] + argv


def argv_for(args: Sequence[str], *, tool: str = "ffmpeg") -> List[str]:
    """The full argv run() would execute (binary + house flags + args), for plans and receipts."""
    if tool == "ffmpeg":
        return [ffmpeg(), "-hide_banner", "-nostdin"] + [str(a) for a in args]
    if tool == "ffprobe":
        return [ffprobe(), "-hide_banner"] + [str(a) for a in args]
    raise MediaError(f"unknown tool {tool!r}: ffmpeg or ffprobe")


def _tail(text: str, n: int = 6) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return " | ".join(lines[-n:])


def run(args: Sequence[str], *, tool: str = "ffmpeg", timeout: Optional[float] = None, check: bool = True,
        binary: bool = False, input: Optional[bytes] = None, gpu: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run ffmpeg/ffprobe with the house flags. stdout is bytes when binary=True, else text; stderr is always text.

    gpu: a short label; when given, the call holds the house GPU lock for its duration (AMF encodes over ~30 s,
    model inference, proxy batches). Short d3d11va reads don't need it.
    """
    argv = argv_for(args, tool=tool)
    full = _gpu_wrap(argv, gpu) if gpu else argv
    try:
        proc = subprocess.run(full, input=input, capture_output=True, timeout=timeout, creationflags=_NO_WINDOW)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"{tool} timed out after {timeout} s", argv=argv) from exc
    except OSError as exc:
        raise MediaError(f"could not start {tool}: {exc}", argv=argv) from exc
    stderr = proc.stderr.decode("utf-8", errors="replace")
    stdout = proc.stdout if binary else proc.stdout.decode("utf-8", errors="replace")
    done = subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)
    if check and proc.returncode != 0:
        raise MediaError(f"{tool} exited {proc.returncode}: {_tail(stderr) or '(no stderr)'}", argv=argv,
                         stderr=stderr)
    return done


def popen(args: Sequence[str], *, tool: str = "ffmpeg", gpu: Optional[str] = None,
          stdin=None) -> subprocess.Popen:
    """Start ffmpeg/ffprobe with stdout piped (for streaming frames or audio). stderr goes to a temp file, never a
    pipe, so a chatty decoder cannot deadlock the reader; read it afterwards with stderr_text(proc)."""
    argv = argv_for(args, tool=tool)
    full = _gpu_wrap(argv, gpu) if gpu else argv
    err = tempfile.TemporaryFile()
    try:
        proc = subprocess.Popen(full, stdin=stdin if stdin is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=err, creationflags=_NO_WINDOW)
    except OSError as exc:
        err.close()
        raise MediaError(f"could not start {tool}: {exc}", argv=argv) from exc
    proc.arsenal_argv = argv          # type: ignore[attr-defined]
    proc.arsenal_errfile = err        # type: ignore[attr-defined]
    return proc


def stderr_text(proc: subprocess.Popen) -> str:
    err = getattr(proc, "arsenal_errfile", None)
    if err is None or err.closed:
        return ""
    err.seek(0)
    return err.read().decode("utf-8", errors="replace")


def finish(proc: subprocess.Popen, *, check: bool = True, timeout: Optional[float] = 30.0) -> int:
    """Wait for a popen() process, close its pipes, and raise MediaError on a non-zero exit when check=True."""
    try:
        if proc.stdout:
            proc.stdout.close()
        rc = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = proc.wait()
    text = stderr_text(proc)
    err = getattr(proc, "arsenal_errfile", None)
    if err is not None:
        err.close()
    if check and rc != 0:
        raise MediaError(f"ffmpeg exited {rc}: {_tail(text) or '(no stderr)'}",
                         argv=getattr(proc, "arsenal_argv", None), stderr=text)
    return rc


def probe_json(path, *, entries: Sequence[str] = ("-show_format", "-show_streams", "-show_chapters"),
               extra: Sequence[str] = ()) -> dict:
    """ffprobe -of json on one file: the shared parse every primitive uses (it was hand-parsed 44 times)."""
    res = run(["-v", "error", "-of", "json", *entries, *extra, str(path)], tool="ffprobe")
    try:
        return json.loads(res.stdout or "{}")
    except ValueError as exc:
        raise MediaError(f"ffprobe gave non-JSON output for {path}", argv=res.args) from exc


# =================================================================================================
# caps
# =================================================================================================

_ENCODER_RE = re.compile(r"^\s*[VAS][F.][S.][X.][B.][D.]\s+(\S+)")
_FILTER_RE = re.compile(r"^\s*[TSC.|]{2,3}\s+(\S+)\s+\S*->\S*")


def _parse_names(text: str, rx: re.Pattern) -> List[str]:
    out = []
    for line in text.splitlines():
        m = rx.match(line)
        if m and m.group(1) != "=":
            out.append(m.group(1))
    return out


def _probe_caps(binary: str) -> dict:
    def call(flag: str) -> str:
        try:
            proc = subprocess.run([binary, "-hide_banner", flag], capture_output=True, timeout=30,
                                  creationflags=_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return proc.stdout.decode("utf-8", errors="replace")

    version_text = call("-version")
    first = version_text.splitlines()[0] if version_text else ""
    m = re.match(r"ffmpeg version (\S+)", first)
    encoders = _parse_names(call("-encoders"), _ENCODER_RE)
    filters = _parse_names(call("-filters"), _FILTER_RE)
    hw = call("-hwaccels").splitlines()
    hwaccels = [ln.strip() for ln in hw[1:] if ln.strip()] if hw and "Hardware" in hw[0] else []
    conf = re.search(r"configuration:(.*)", version_text)
    return {"version": m.group(1) if m else (first or None), "configuration": conf.group(1).strip() if conf else "",
            "encoders_all": sorted(set(encoders)), "filters_all": sorted(set(filters)), "hwaccels": hwaccels}


def _caps_view(binary: str, raw: dict) -> dict:
    enc, fil = set(raw.get("encoders_all", [])), set(raw.get("filters_all", []))
    return {"path": binary, "version": raw.get("version"),
            "encoders": {e: e in enc for e in WATCH_ENCODERS},
            "filters": {f: f in fil for f in WATCH_FILTERS},
            "hwaccels": list(raw.get("hwaccels", [])),
            "n_encoders": len(enc), "n_filters": len(fil),
            "known_bad": dict(KNOWN_BAD)}


def _caps_entry(binary: str, refresh: bool = False) -> dict:
    """The cached raw probe of one binary, refreshed when its (path, size, mtime) stamp changes. The first call on a
    cold cache costs three ffmpeg runs (-encoders, -filters, -hwaccels): about a second, not a hot path."""
    st = os.stat(binary)
    stamp = {"path": binary, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    cache_file = state_dir() / "caps.json"
    cache = _read_json(cache_file) or {}
    entry = cache.get(binary)
    if refresh or not entry or entry.get("stamp") != stamp:
        entry = {"stamp": stamp, "raw": _probe_caps(binary)}
        cache[binary] = entry
        try:
            _write_json(cache_file, cache)
        except OSError:
            pass
    return entry


def caps(refresh: bool = False, *, binary: Optional[str] = None) -> dict:
    """What the ffmpeg build can do, cached on disk per (path, size, mtime). `encoders`/`filters` report the
    WATCH_* names the primitives care about; has_encoder()/has_filter() answer for any name."""
    binary = binary or ffmpeg()
    return _caps_view(binary, _caps_entry(binary, refresh)["raw"])


def has_encoder(name: str) -> bool:
    """True when the chosen build has this encoder (any name, not only the watched ones: the build is the truth)."""
    return name in set(_caps_entry(ffmpeg())["raw"].get("encoders_all", []))


def has_filter(name: str) -> bool:
    """True when the chosen build has this filter (any name, not only the watched ones: the build is the truth)."""
    return name in set(_caps_entry(ffmpeg())["raw"].get("filters_all", []))


def version_short() -> str:
    try:
        return str(caps().get("version") or "unknown")
    except MediaError:
        return "none"


# =================================================================================================
# filter paths
# =================================================================================================

def filter_path(p, *, quote: bool = True) -> str:
    """A file path as a filtergraph option value: forward slashes, the drive colon escaped (C\\:/...), and by default
    wrapped in single quotes so spaces survive: subtitles=filename='C\\:/a b/x.ass'.

    Without this, `subtitles=C:/a b/x.ass` fails with 'Unable to parse "original_size"' (measured): the colon ends the
    option. A path holding an apostrophe is refused; copy it somewhere plainer.
    """
    s = str(Path(p).resolve()).replace("\\", "/")
    if "'" in s:
        raise MediaError(f"filter paths cannot hold an apostrophe ({s!r}); copy the file to a plainer path")
    s = s.replace(":", "\\:")
    return f"'{s}'" if quote else s


# =================================================================================================
# doctor
# =================================================================================================

def _candidates() -> List[str]:
    seen, out = set(), []

    def add(p: Optional[str]) -> None:
        if p and os.path.isfile(p):
            key = os.path.normcase(os.path.abspath(p))
            if key not in seen:
                seen.add(key)
                out.append(os.path.abspath(p))

    try:
        add(_from_env())
    except MediaError:
        pass
    add(_from_config())
    add(shutil.which("ffmpeg"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        for p in sorted(glob.glob(os.path.join(local, "*", "ffmpeg", "bin", "ffmpeg" + _EXE))):
            add(p)
    return out


def _score(view: dict, has_probe: bool) -> int:
    """doctor --save keeps the HIGHEST score, not the last build it saw: each AMF encoder 4 (GPU encode is the
    budget path), libass 3 and an ffprobe beside it 3 (captions and probing are daily needs), whisper, scdet,
    ebur128 and libx264 2 each. A stronger build found later replaces the saved one on the next --save."""
    enc, fil = view["encoders"], view["filters"]
    return (4 * sum(enc.get(e, False) for e in ("h264_amf", "hevc_amf", "av1_amf"))
            + 3 * bool(fil.get("ass")) + 2 * bool(fil.get("whisper")) + 2 * bool(fil.get("scdet"))
            + 2 * bool(fil.get("ebur128")) + 2 * bool(enc.get("libx264")) + 3 * has_probe)


def _package(name: str) -> dict:
    if importlib.util.find_spec(name) is None:
        return {"present": False}
    dist = {"PIL": "pillow", "cv2": "opencv-python", "av": "av", "faster_whisper": "faster-whisper",
            "imageio_ffmpeg": "imageio-ffmpeg"}.get(name, name)
    try:
        version = importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        version = None
    return {"present": True, "version": version}


def doctor(save: bool = False) -> dict:
    """Binaries, their caps, Python, optional packages and the two env settings; with save=True, remember the most
    capable ffmpeg on this machine in <state>/config.json so every later call finds it."""
    from . import api
    problems: List[str] = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")      # the warning is reported once, below, as a problem
            current = locate(refresh=True)
    except MediaError as exc:
        current = {"ffmpeg": None, "ffprobe": None, "source": None, "warning": str(exc)}
    found = []
    for path in _candidates():
        try:
            view = caps(binary=path)
        except OSError:
            continue
        probe = _sibling(path, "ffprobe")
        found.append({"ffmpeg": path, "ffprobe": probe, "version": view["version"],
                      "score": _score(view, bool(probe)), "encoders": view["encoders"], "filters": view["filters"]})
    found.sort(key=lambda c: -c["score"])
    best = found[0] if found else None
    saved = None
    if save and best:
        _write_json(config_path(), {"ffmpeg": best["ffmpeg"], "ffprobe": best["ffprobe"], "score": best["score"],
                                    "version": best["version"], "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        saved = best["ffmpeg"]
        current = locate(refresh=True)
    if current.get("warning"):
        problems.append(current["warning"])
    if best and current.get("ffmpeg") and os.path.normcase(best["ffmpeg"]) != os.path.normcase(current["ffmpeg"]):
        problems.append(f"a more capable ffmpeg exists ({best['ffmpeg']}); `doctor --save` remembers it")
    if current.get("ffmpeg") and not current.get("ffprobe"):
        problems.append("no ffprobe beside the chosen ffmpeg")
    if not sys.flags.utf8_mode and os.environ.get("PYTHONUTF8") != "1":
        problems.append("PYTHONUTF8 is not 1: printing non-cp1252 text can crash (it hit 17 agents); "
                        "set it as a user environment variable")
    packages = {name: dict(_package(name), use=use) for name, use in OPTIONAL_PACKAGES.items()}
    chosen_caps = None
    if current.get("ffmpeg"):
        try:
            chosen_caps = caps(binary=current["ffmpeg"])
        except OSError:
            chosen_caps = None
    return {"api": api("doctor"), "chosen": current, "caps": chosen_caps, "candidates": found, "saved": saved,
            "python": {"version": sys.version.split()[0], "executable": sys.executable,
                       "utf8_mode": bool(sys.flags.utf8_mode)},
            "env": {FFMPEG_ENV: os.environ.get(FFMPEG_ENV), "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
                    STATE_ENV: os.environ.get(STATE_ENV)},
            "packages": packages, "problems": problems, "state_dir": str(state_dir())}


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media doctor",
                                 description="where ffmpeg and ffprobe live, what the build can do, optional packages")
    ap.add_argument("--save", action="store_true", help="remember the most capable ffmpeg on this machine")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = doctor(save=args.save)
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    ch = rep["chosen"]
    print(f"ffmpeg   {ch.get('ffmpeg')}  (source: {ch.get('source')})")
    print(f"ffprobe  {ch.get('ffprobe')}")
    if rep["caps"]:
        c = rep["caps"]
        on = [k for k, v in {**c["encoders"], **c["filters"]}.items() if v]
        off = [k for k, v in {**c["encoders"], **c["filters"]}.items() if not v]
        print(f"version  {c['version']}   hwaccels: {', '.join(c['hwaccels']) or 'none'}")
        print(f"has      {', '.join(on)}")
        print(f"lacks    {', '.join(off) or '-'}")
    if rep["candidates"]:
        print("builds found on this machine (best first):")
        for cand in rep["candidates"]:
            print(f"  score {cand['score']:2d}  {cand['version']}  {cand['ffmpeg']}")
    if rep["saved"]:
        print(f"saved    {rep['saved']} -> {config_path()}")
    pk = rep["packages"]
    print("packages " + "  ".join(f"{n}{'' if v['present'] else ' (missing)'}" for n, v in pk.items()))
    for p in rep["problems"]:
        print(f"! {p}")
    return 0
