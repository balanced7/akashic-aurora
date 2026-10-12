"""arsenal.media.edit -- the editor's timeline document, the operations on it, and the render to one file.

One project is one JSON file (arsenal.media.timeline/v0) at <state>/edits/<pid>.json. The First Light page, the CLI
(`py -m arsenal.media edit ...`) and a future MCP tool all edit it through these functions, so the rules live here
once:

  * one writer at a time, by revision: save() takes the revision the caller loaded; a stale one raises Conflict with
    the current document (HTTP 409). The write is rev+1, atomic (temp file + os.replace) under a per-project lock file;
  * operations are pure (doc in, new doc out) and validate: src_in < src_out inside the media's duration, no overlap
    on V1 in v0, every lane a clip names exists, gains inside the mixer's -60..+12 dB;
  * originals are never touched or copied. Media facts and the editor's derived files (demuxed tracks, peaks, shots)
    live under <state>/edits/media/<mid>/; renders go to a NEW folder, <library root>/aurora-edits/<project>/, or to
    an explicit out, and never over an existing file.

render() is one ffmpeg run: every clip is its own input, seeked on the input side (-ss/-t) so a clip at 30:00 of a
33-minute recording does not decode the first 30 minutes. Every stream of a clip is anchored on src_in (video
fps start_time=0, audio aresample first_pts=0), not on its own first timestamp, so a track that starts late in the
source stays where the source puts it; the timeline's boundaries are rounded to frames once and each clip is trimmed
to that exact frame count (video) and sample count (audio, 48 kHz), so clips neither drift nor pile up rounding.
Per-track volume comes from the clip's and the lane's gain, mute and solo; the clip's tracks are amixed (normalize=0,
unity gain); gaps on V1 become black and silence; everything is concatenated and encoded with an export preset (its
two-pass loudnorm when the preset names a target), then audio.qc holds it to the timeline's duration, frame count and
loudness target. AMF presets run under the house GPU lock.

A/V sync, flash and beep both at 2.0 s in the source (2026-10-12): audio minus video 0.0 to 1.0 ms on a track that
starts 0.5 s late (clips from 0 and from 1 s), a video stream that starts 0.1 s late (MKV and MP4), and mid-file clips
from MKV (PCM and Opus); anchoring each stream on its own first timestamp had given -500 and -12, -70.6 and +20, -24
and -20 ms on those. On an OBS-shaped MP4 whose video
starts 25 ms after its audio the render keeps those 25 ms (the flash lands on the next 30 fps frame: -33.3 ms); the
old graph showed 0.0 there only because it slid the picture 25 ms early.

Measured 2026-10-12 on this machine (house ffmpeg N-124319, software decode), 2 clips x 10 s:
  * synthetic 320x240 project (2 x ~1 s): 0.11-0.14 s, duration exact;
  * 3-track 1080p60 HEVC oracle, libx264 veryfast 1080p60: 3.1-3.4 s (6.4x realtime), 20.000 s / 1200 frames out,
    qc clean;
  * 33-min OBS recording, decode + filters only: 2.0-2.8 s (7-10x); proxy_edit (h264_amf 1080p): 10.5 s of encode (1.9x),
    plus whatever the GPU lock makes it wait; youtube_4k60_fast with its -14 LUFS two-pass: 17.5 s including a lock
    wait (input -40.7 LUFS, output -14.0 LUFS / -1.4 dBTP). The encoder is the bottleneck, not the seek or the graph.
On the same recording (33.8 min, 2.4 GB): import 0.84 s (0.03 s again), keyframes 0.92 s, demux 0.26 s, peaks of one
track 3.7-4.3 s (3.4 MB of JSON for the page); at 16-bit, 3.0 s of decode and 3.1 MB of JSON (integrator, 2026-10-12).

Primitives built by the other lanes (catalog, probe.probe, audio, peaks, shots, cut, export) are imported lazily; when
one is not there yet a call raises NotBuilt ("arsenal.media.<module> not built yet", HTTP 503) instead of the editor
growing a second copy of it. The one fallback is a media's basic facts: without the catalog and probe.probe, import
reads duration and streams from ff.probe_json, the shared ffprobe parse, and says so in facts_from.
"""
from __future__ import annotations

import contextlib
import copy
import importlib
import json
import math
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from . import ff, receipt

API = "arsenal.media.timeline/v0"
#: What this document is a projection of (Heimdall's fence, 2026-10-12). v0 timelines are their own master; when the
#: studio board becomes the master, documents saying "timeline-v0" are the ones a migration converts, detectably.
MASTER = "timeline-v0"
DEFAULT_SETTINGS = {"fps": 60, "width": 1920, "height": 1080}
PID_PATTERN = r"\d{8}-\d{6}-[0-9a-f]{6}"
MID_PATTERN = r"[0-9a-f]{16}"
VIDEO_SUFFIXES = (".mp4", ".m4v", ".mov", ".webm", ".mkv")
GAIN_RANGE_DB = (-60.0, 12.0)
OUT_FOLDER = "aurora-edits"
AUDIO_RATE = 48000
EPS = 1e-4                    # 0.1 ms: float noise between at + length and the next clip's at
MIN_CLIP_S = 1e-3
CONTAINER_SUFFIX = {"mp4": ".mp4", "mov": ".mov", "webm": ".webm", "mkv": ".mkv", "matroska": ".mkv",
                    "webp": ".webp"}
MUXER = {".mp4": "mp4", ".mov": "mov", ".mkv": "matroska", ".webm": "webm", ".webp": "webp"}
#: The render pipeline writes yuv420p; these presets carry alpha the timeline never has.
ALPHA_PRESETS = ("alpha_webm", "alpha_prores4444", "alpha_webp_anim")


class EditError(ValueError):
    """A refused edit, with the problems found and the HTTP status the editor's routes answer with."""

    def __init__(self, message: str, *, problems: Optional[List[str]] = None, status: int = 400):
        super().__init__(message)
        self.problems = list(problems or [message])
        self.status = status


class Conflict(EditError):
    """save() was given a revision that is no longer the current one; .current is the document on disk."""

    def __init__(self, current: dict, sent_rev):
        super().__init__(f"project {current.get('id')} is at rev {current.get('rev')}, the edit was made on rev "
                         f"{sent_rev}: changed elsewhere", status=409)
        self.current = current


class NotBuilt(RuntimeError):
    """A primitive another lane builds is not in the package yet (HTTP 503)."""


def module(name: str, attr: Optional[str] = None):
    """arsenal.media.<name> (and its attr), or NotBuilt with the one-line reason the editor shows."""
    full = f"arsenal.media.{name}"
    try:
        mod = importlib.import_module(full)
    except ModuleNotFoundError as exc:
        if exc.name in (full, f"arsenal.media.{name.split('.')[0]}"):
            raise NotBuilt(f"{full} not built yet") from exc
        raise
    if attr and not hasattr(mod, attr):
        raise NotBuilt(f"{full}.{attr} not built yet")
    return mod


def is_built(name: str, attr: Optional[str] = None) -> bool:
    try:
        module(name, attr)
        return True
    except NotBuilt:
        return False


# =================================================================================================
# files: atomic JSON under a lock file
# =================================================================================================

def edits_dir() -> Path:
    return ff.state_dir() / "edits"


def project_file(pid: str) -> Path:
    if not re.fullmatch(PID_PATTERN, str(pid)):
        raise EditError(f"{pid!r} is not a project id", status=404)
    return edits_dir() / f"{pid}.json"


def media_file(mid: str) -> Path:
    if not re.fullmatch(MID_PATTERN, str(mid)):
        raise EditError(f"{mid!r} is not a media id", status=404)
    return edits_dir() / "media" / f"{mid}.json"


def media_dir(mid: str) -> Path:
    """Where the editor keeps one media's derived files (demuxed tracks, peaks, shots, keyframes)."""
    return media_file(mid).with_suffix("")


_thread_locks: Dict[str, threading.Lock] = {}
_thread_locks_guard = threading.Lock()


@contextlib.contextmanager
def locked(target: Path, *, timeout: float = 10.0, stale_s: float = 30.0) -> Iterator[None]:
    """Hold <target>.lock: a lock FILE, so the server, the CLI and an MCP door exclude each other across processes.
    A lock older than stale_s is a dead writer's and is broken; the window it guards is milliseconds."""
    with _thread_locks_guard:
        tlock = _thread_locks.setdefault(str(target), threading.Lock())
    with tlock:
        lock = target.with_name(target.name + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    age = time.time() - lock.stat().st_mtime
                except OSError:
                    continue
                if age > stale_s:
                    with contextlib.suppress(OSError):
                        lock.unlink()
                    continue
                if time.monotonic() > deadline:
                    raise EditError(f"{target.name} is being written by another process (lock {lock})", status=503)
                time.sleep(0.01)
                continue
            os.write(fd, f"{os.getpid()} {time.time():.3f}\n".encode("ascii"))
            os.close(fd)
            break
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                lock.unlink()


def _retry(fn: Callable, attempts: int = 25):
    """Windows refuses os.replace (and some opens) while another handle is open on the file; it clears in ms."""
    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.02)


def read_json(path: Path) -> Optional[dict]:
    def read():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None
    return _retry(read)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, default=str)
        fh.write("\n")
    _retry(lambda: os.replace(tmp, path))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# =================================================================================================
# media: what the editor knows about one imported file
# =================================================================================================

def _fps(rate: Optional[str]) -> Optional[float]:
    num, _, den = str(rate or "0/1").partition("/")
    try:
        n, d = float(num), float(den or 1)
    except ValueError:
        return None
    return round(n / d, 6) if n and d else None


def _ffprobe_facts(path: Path) -> dict:
    """Duration and streams from the shared ffprobe parse: the editor's minimum when catalog/probe are not built."""
    j = ff.probe_json(path)
    fmt = j.get("format") or {}
    streams = j.get("streams") or []
    vs = next((s for s in streams if s.get("codec_type") == "video"
               and not (s.get("disposition") or {}).get("attached_pic")), None)
    f0 = float(fmt.get("start_time") or 0.0)
    video = None
    if vs:
        video = {"codec": vs.get("codec_name"), "w": vs.get("width"), "h": vs.get("height"),
                 "fps": _fps(vs.get("avg_frame_rate")) or _fps(vs.get("r_frame_rate")),
                 "has_b_frames": vs.get("has_b_frames"), "pix_fmt": vs.get("pix_fmt"),
                 "start_s": round(float(vs.get("start_time") or f0) - f0, 6)}
    audio = []
    for s in (s for s in streams if s.get("codec_type") == "audio"):
        tags = s.get("tags") or {}
        audio.append({"index": s.get("index"), "codec": s.get("codec_name"), "channels": s.get("channels"),
                      "sample_rate": int(s.get("sample_rate") or 0) or None, "title": tags.get("title"),
                      "house_name": None})
    tags = fmt.get("tags") or {}
    return {"duration_s": float(fmt.get("duration") or 0.0), "container": fmt.get("format_name"),
            "encoder": tags.get("encoder"), "recorded_at": None, "video": video, "audio": audio,
            "chapters": [], "kind": "unknown", "links": {}, "clock": "file", "start_s": f0}


#: Keys of a sidecar the editor does not carry in its media record (the house result keys, the full keyframe list).
_SIDECAR_SKIP = ("api", "source", "params", "computed_with", "blind", "receipt", "cached", "sidecar_path", "keyframes")


def _sidecar(side) -> Optional[dict]:
    if isinstance(side, dict) and ("audio" in side or "video" in side):
        return {k: v for k, v in side.items() if k not in _SIDECAR_SKIP}
    return None


def _facts(path: Path) -> Tuple[dict, str, List[str]]:
    """(facts, facts_from, notes): the catalog's quick ingest (probe + sidecar + catalog row + time links), else
    probe.probe, else the shared ffprobe parse."""
    notes: List[str] = []
    try:
        catalog = module("catalog", "ingest")
        probe = module("probe", "read_sidecar")
        rows = catalog.ingest(str(path), proxy=False, shots=False, peaks=False, clock="off")
        row = rows[0] if isinstance(rows, list) and rows else {}
        side = _sidecar(probe.read_sidecar(row["id"])) if row.get("id") else None
        if side:
            return side, "catalog", notes
        notes.append(f"catalog.ingest gave no sidecar ({row.get('error') or 'no id'})")
    except NotBuilt as exc:
        notes.append(str(exc))
    except Exception as exc:  # the editor still opens the file; the note says why the facts are thinner
        notes.append(f"catalog.ingest failed: {type(exc).__name__}: {exc}")
    try:
        side = _sidecar(module("probe", "probe").probe(str(path)))
        if side:
            return side, "probe", notes
    except NotBuilt as exc:
        notes.append(str(exc))
    except Exception as exc:
        notes.append(f"probe.probe failed: {type(exc).__name__}: {exc}")
    return _ffprobe_facts(path), "ffprobe", notes


def track_label(media: dict, n: int) -> str:
    tracks = media.get("audio") or []
    t = tracks[n] if n < len(tracks) else {}
    return str(t.get("title") or t.get("house_name") or f"Track {n + 1}")


def _unchanged(rec: dict) -> bool:
    """The record's own file is still there with the size and mtime it was imported at."""
    try:
        st = Path(rec["path"]).stat()
    except (KeyError, TypeError, OSError):
        return False
    return st.st_size == rec.get("size") and st.st_mtime_ns == rec.get("mtime_ns")


def source_path(rec: dict) -> Optional[Path]:
    """The media's file: its recorded path, else another place the same bytes were imported from (same size)."""
    for cand in [rec.get("path"), *(rec.get("paths") or [])]:
        try:
            if cand and Path(cand).stat().st_size == rec.get("size"):
                return Path(cand)
        except OSError:
            continue
    return None


def import_media(path) -> dict:
    """Learn one file's facts (cheap: no proxy, no peaks, no shots) and remember it as editor media. Read-only on the
    file; importing the same file again refreshes the facts and keeps the derived files while size and mtime hold.
    The media id is a content hash, so a byte-identical copy imported from another folder is the SAME media: the
    record keeps the file it already knows while that file is unchanged, and lists the copy in paths (a fallback when
    the first goes), so dropping a backup copy never re-points the clips of every project to it."""
    p = Path(path).resolve()
    if not p.is_file():
        raise EditError(f"no file at {p}", status=404)
    if p.suffix.lower() not in VIDEO_SUFFIXES:
        raise EditError(f"{p.name}: the editor imports videos ({', '.join(VIDEO_SUFFIXES)})", status=415)
    facts, facts_from, notes = _facts(p)
    mid = facts.get("id") if re.fullmatch(MID_PATTERN, str(facts.get("id") or "")) else receipt.quick_id(p)
    if not facts.get("video"):
        raise EditError(f"{p.name} has no video stream; v0 timelines hold video clips", status=415)
    rec = dict(facts)
    audio = []
    for n, t in enumerate(rec.get("audio") or []):
        t = dict(t)
        t["track"] = n
        audio.append(t)
    rec.update(id=mid, audio=audio, n_audio=len(audio), facts_from=facts_from, facts_notes=notes, imported_at=_now())
    rec["duration_s"] = float(rec.get("duration_s") or 0.0)
    for t in rec["audio"]:
        t["label"] = track_label(rec, t["track"])
    target = media_file(mid)
    with locked(target):
        old = read_json(target) or {}
        home = p
        if old.get("path") and os.path.normcase(str(old["path"])) != os.path.normcase(str(p)) and _unchanged(old):
            home = Path(old["path"])
        st = home.stat()
        known = [str(home), *(old.get("paths") or [old.get("path")]), str(p)]
        rec.update(name=home.name, path=str(home), size=st.st_size, mtime_ns=st.st_mtime_ns,
                   paths=list(dict.fromkeys(x for x in known if x))[:8])
        same = old.get("size") == st.st_size and old.get("mtime_ns") == st.st_mtime_ns
        rec["derived"] = old.get("derived", {}) if same else {}
        if same and isinstance((old.get("video") or {}).get("keyint_s"), (int, float)) and rec.get("video") \
                and not rec["video"].get("keyint_s"):
            rec["video"].update({k: old["video"][k] for k in ("keyint_s", "keyframes_n") if k in old["video"]})
        _apply_track_starts(rec)
        write_json(target, rec)
    return rec


def get_media(mid: str) -> dict:
    rec = read_json(media_file(mid))
    if not rec:
        raise EditError(f"no imported media {mid}", status=404)
    return rec


def list_media() -> List[dict]:
    folder = edits_dir() / "media"
    out = []
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        rec = read_json(f)
        if rec and re.fullmatch(MID_PATTERN, f.stem):
            out.append(rec)
    out.sort(key=lambda r: r.get("imported_at") or "", reverse=True)
    return out


def update_media(mid: str, change: Callable[[dict], None]) -> dict:
    """Read-modify-write one media record under its lock (the job worker, the keyframe cache and import share it)."""
    target = media_file(mid)
    with locked(target):
        rec = read_json(target)
        if not rec:
            raise EditError(f"no imported media {mid}", status=404)
        change(rec)
        write_json(target, rec)
    return rec


def set_derived(mid: str, kind: str, value) -> dict:
    """Record one derived file (or map of them) under rec["derived"][kind]."""
    def change(rec: dict) -> None:
        rec.setdefault("derived", {})[kind] = value
        _apply_track_starts(rec)
    return update_media(mid, change)


def _apply_track_starts(rec: dict) -> None:
    """Copy each demuxed track's start_s onto rec["audio"]: a track that starts late in the source plays from 0 in its
    own file, so the page offsets it by start_s."""
    rows = (rec.get("derived") or {}).get("audio") or {}
    for t in rec.get("audio") or []:
        row = rows.get(str(t.get("track")))
        if isinstance(row, dict) and row.get("start_s") is not None:
            t["start_s"] = row["start_s"]


def track_starts(rec: dict) -> List[float]:
    """Where each audio track starts in the source file (a file time): the demux rows' start_s (already on
    rec["audio"]), else ffprobe's stream start_time minus the format start_time, as audio.tracks reports it."""
    have = [t.get("start_s") for t in rec.get("audio") or []]
    if all(_num(v) for v in have):
        return [float(v) for v in have]
    j = ff.probe_json(rec["path"], entries=("-show_streams", "-show_format"), extra=("-select_streams", "a"))
    f0 = float((j.get("format") or {}).get("start_time") or 0.0)
    probed = [round(float(s["start_time"]) - f0, 6) if s.get("start_time") not in (None, "N/A") else 0.0
              for s in j.get("streams") or []]
    return [float(v) if _num(v) else (probed[n] if n < len(probed) else 0.0) for n, v in enumerate(have)]


def derived_ready(rec: dict, kind: str) -> bool:
    got = (rec.get("derived") or {}).get(kind)
    if kind in ("audio", "peaks"):
        n = len(rec.get("audio") or [])
        if not isinstance(got, dict) or len(got) < n:
            return False
        return all(Path(v["path"] if isinstance(v, dict) else v).is_file() for v in got.values())
    return bool(got) and Path(got).is_file()


def derived_path(rec: dict, kind: str, track: Optional[int] = None) -> Optional[Path]:
    got = (rec.get("derived") or {}).get(kind)
    if track is not None:
        got = (got or {}).get(str(track)) if isinstance(got, dict) else None
    if isinstance(got, dict):
        got = got.get("path")
    return Path(got) if got and Path(got).is_file() else None


def build_demux(mid: str, progress: Optional[Callable[[float], None]] = None) -> dict:
    """Every audio track to its own file (audio.demux, stream copy where Chromium can play it) so the page plays the
    tracks side by side: Chromium here has no HTMLMediaElement.audioTracks."""
    audio = module("audio", "demux")
    rec = get_media(mid)
    rows = {}
    if rec.get("audio"):
        res = audio.demux(rec["path"], str(media_dir(mid) / "audio"), tracks="all", codec="copy")
        for row in res.get("tracks") or []:
            rows[str(row["index"])] = {"path": row["path"], "start_s": row.get("start_s"), "codec": row.get("codec"),
                                       "how": row.get("how")}
    return set_derived(mid, "audio", rows)["derived"]["audio"]


def build_peaks(mid: str, progress: Optional[Callable[[float], None]] = None, *, spp: int = 512) -> dict:
    """Waveform peaks per track (peaks.peaks, 16-bit mono), kept as {sample_rate, spp, data} normalised to -1..1.
    16-bit, not peaks.js's 8: the lanes draw on a dB scale down to -54 dBFS and OBS game audio sits near -40 LUFS,
    under 8-bit's first step (-42 dBFS). Measured 2026-10-12: 8-bit left 88% of the columns of 2026-10-11 16-48-25
    and 48.5% of 17-51-11 at zero (a flat lane); 16-bit none, for the same 3.0 s and 3.1 MB of JSON instead of 2.6."""
    peaks = module("peaks", "peaks")
    rec = get_media(mid)
    n_tracks = len(rec.get("audio") or [])
    starts = track_starts(rec)
    out_dir = media_dir(mid) / "peaks"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for n in range(n_tracks):
        res = peaks.peaks(rec["path"], track=n, spp=spp, bits=16, channels="mono", out_prefix=str(out_dir / f"a{n}"),
                          formats=("json",))
        payload = peaks_payload(res, spp=spp)
        # pixel 0 is the track's first sample, so the lane draws it from where the track starts on the source clock
        # (peaks.peaks' own start_s is its span's start: 0.0 without a span)
        payload["start_s"] = starts[n]
        target = out_dir / f"a{n}.editor.json"
        write_json(target, payload)
        files[str(n)] = str(target)
        if progress:
            progress((n + 1) / n_tracks)
    return set_derived(mid, "peaks", files)["derived"]["peaks"]


def peaks_payload(res, *, spp: int = 512) -> dict:
    """{sample_rate, spp, length, data: [min, max, ...]} in -1..1, from the waveform itself or from the result of
    peaks.peaks, which names its audiowaveform-v2 .json file (the data stays in the files)."""
    wave = None
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, (list, tuple)) or hasattr(data, "tolist"):
        wave = res
    else:
        files = res.get("files") if isinstance(res, dict) else None
        path = (files or {}).get("json") if isinstance(files, dict) else None
        loaded = read_json(Path(path)) if path else None
        if loaded and "data" in loaded:
            wave = loaded
    if wave is None:
        raise ff.MediaError("peaks gave no waveform data (no 'data' and no 'files.json' in its result)")
    data = wave["data"]
    data = data.tolist() if hasattr(data, "tolist") else list(data)
    scale = {8: 128.0, 16: 32768.0}.get(int(wave.get("bits") or 0), 1.0)
    channels = int(wave.get("channels") or 1)
    if channels > 1:            # keep channel 0's min/max pairs: the lane draws one wave
        step = 2 * channels
        data = [v for i in range(0, len(data) - step + 1, step) for v in data[i:i + 2]]
    # 8-bit: 3 decimals lose nothing; 16-bit: 4 decimals keep 1e-4 (-80 dBFS), under the lanes' -54 dB floor
    places = 4 if int(wave.get("bits") or 0) == 16 else 3
    norm = [round(max(-1.0, min(1.0, float(v) / scale)), places) for v in data]
    return {"sample_rate": int(wave.get("sample_rate") or AUDIO_RATE),
            "spp": int(wave.get("samples_per_pixel") or wave.get("spp") or spp),
            "length": len(norm) // 2, "data": norm}


def build_shots(mid: str, progress: Optional[Callable[[float], None]] = None) -> str:
    """The cuts in the video (shots.shots with its default detector), kept as {cuts, shots, detector_ran, blind}."""
    shots = module("shots", "shots")
    rec = get_media(mid)
    res = shots.shots(rec["path"])
    keep = {"cuts": list(res.get("cuts") or []), "shots": res.get("shots"), "detector_ran": res.get("detector_ran"),
            "blind": res.get("blind"), "receipt": res.get("receipt")}
    target = media_dir(mid) / "shots.json"
    write_json(target, keep)
    set_derived(mid, "shots", str(target))
    return str(target)


def keyframes(mid: str) -> List[float]:
    """Keyframe file times of the media (probe.keyframes, a packet-flag scan: 0.8 s on 33 minutes), cached beside
    it. A cache without "clock": "file" was written on the container clock and is read again."""
    from . import probe
    rec = get_media(mid)
    cache = media_dir(mid) / "keyframes.json"
    got = read_json(cache)
    if got and got.get("size") == rec.get("size") and got.get("mtime_ns") == rec.get("mtime_ns") \
            and got.get("clock") == "file":
        return got["keyframes"]
    kfs = probe.keyframes(rec["path"])
    write_json(cache, {"size": rec.get("size"), "mtime_ns": rec.get("mtime_ns"), "clock": "file", "keyframes": kfs})

    def change(cur: dict) -> None:          # the inspector's keyframe interval, when the probe did not give one
        cur.setdefault("derived", {})["keyframes"] = str(cache)
        video = cur.get("video") or {}
        if len(kfs) > 1 and not video.get("keyint_s"):
            gaps = sorted(b - a for a, b in zip(kfs, kfs[1:]))
            video.update(keyint_s=round(gaps[len(gaps) // 2], 4), keyframes_n=len(kfs))
        cur["video"] = video
    update_media(mid, change)
    return kfs


# =================================================================================================
# projects
# =================================================================================================

def new_project(name: str, *, settings: Optional[dict] = None) -> dict:
    name = str(name or "").strip()
    if not name:
        raise EditError("a project needs a name")
    pid = f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
    now = _now()
    doc = {"api": API, "master": MASTER, "id": pid, "name": name[:120], "rev": 1, "created_at": now,
           "updated_at": now,
           "settings": dict(DEFAULT_SETTINGS, **(settings or {})),
           "lanes": {"video": [{"id": "V1"}],
                     "audio": [{"id": "A1", "label": "Mix", "gain_db": 0.0, "mute": False, "solo": False}]},
           "clips": [], "markers": [], "board": None}
    problems = validate(doc, media_lookup=None)
    if problems:
        raise EditError("; ".join(problems), problems=problems)
    target = project_file(pid)
    with locked(target):
        write_json(target, doc)
    return doc


def load(pid: str) -> dict:
    doc = read_json(project_file(pid))
    if not doc:
        raise EditError(f"no project {pid}", status=404)
    return doc


def list_projects() -> List[dict]:
    folder = edits_dir()
    out = []
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if not re.fullmatch(PID_PATTERN, f.stem):
            continue
        doc = read_json(f)
        if doc:
            out.append({"id": doc.get("id"), "name": doc.get("name"), "rev": doc.get("rev"),
                        "updated_at": doc.get("updated_at"), "clips": len(doc.get("clips") or [])})
    out.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    return out


def save(doc: dict, *, media_lookup: Optional[Callable[[str], Optional[dict]]] = "registry") -> dict:
    """Write doc as the next revision. doc["rev"] must be the revision the caller loaded; otherwise Conflict carries the
    current document. Returns the stored document (rev + 1, updated_at now)."""
    if not isinstance(doc, dict):
        raise EditError("a project must be a JSON object")
    pid = doc.get("id")
    target = project_file(pid)
    lookup = _registry_lookup if media_lookup == "registry" else media_lookup
    with locked(target):
        current = read_json(target)
        if not current:
            raise EditError(f"no project {pid}", status=404)
        if doc.get("rev") != current.get("rev"):
            raise Conflict(current, doc.get("rev"))
        nxt = copy.deepcopy(doc)
        nxt.update(api=API, id=pid, rev=int(current["rev"]) + 1, created_at=current.get("created_at"),
                   updated_at=_now(), master=current.get("master") or MASTER)
        problems = validate(nxt, media_lookup=lookup)
        if problems:
            raise EditError("; ".join(problems[:5]), problems=problems)
        write_json(target, nxt)
    return nxt


def _registry_lookup(mid: str) -> Optional[dict]:
    try:
        return get_media(mid)
    except EditError:
        return None


# =================================================================================================
# validation
# =================================================================================================

def clip_len(clip: dict) -> float:
    return float(clip["src_out"]) - float(clip["src_in"])


def clip_end(clip: dict) -> float:
    return float(clip["at"]) + clip_len(clip)


def duration(doc: dict) -> float:
    return max((clip_end(c) for c in doc.get("clips") or []), default=0.0)


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _gain_ok(v) -> bool:
    return _num(v) and GAIN_RANGE_DB[0] <= v <= GAIN_RANGE_DB[1]


def _obj(v, where: str, p: List[str]) -> dict:
    """v when it is an object; else {} and one problem (a PUT body is the page's word, not a promise of types)."""
    if v is None or isinstance(v, dict):
        return v or {}
    p.append(f"{where} must be an object, not {type(v).__name__}")
    return {}


def _arr(v, where: str, p: List[str]) -> list:
    if v is None or isinstance(v, list):
        return v or []
    p.append(f"{where} must be a list, not {type(v).__name__}")
    return []


def validate(doc: dict, *, media_lookup: Optional[Callable[[str], Optional[dict]]] = None) -> List[str]:
    """Problems with a timeline document, [] when it is sound. With media_lookup, clip ranges and tracks are checked
    against the media's duration and audio tracks too. Any JSON gives a list of problems, never an exception."""
    p: List[str] = []
    if not isinstance(doc, dict):
        return [f"a project must be a JSON object, not {type(doc).__name__}"]
    if doc.get("api") != API:
        p.append(f"api must be {API}")
    if not isinstance(doc.get("name"), str) or not doc["name"].strip():
        p.append("name must be a non-empty string")
    s = _obj(doc.get("settings"), "settings", p)
    if not (_num(s.get("fps")) and 1 <= s["fps"] <= 240):
        p.append("settings.fps must be 1..240")
    for k in ("width", "height"):
        v = s.get(k)
        if not (isinstance(v, int) and not isinstance(v, bool) and 16 <= v <= 8192 and v % 2 == 0):
            p.append(f"settings.{k} must be an even integer 16..8192")
    lanes = _obj(doc.get("lanes"), "lanes", p)
    vids = [ln.get("id") for ln in _arr(lanes.get("video"), "lanes.video", p) if isinstance(ln, dict)]
    if "V1" not in vids:
        p.append("lanes.video must hold V1")
    aids = []
    for ln in _arr(lanes.get("audio"), "lanes.audio", p):
        if not isinstance(ln, dict) or not re.fullmatch(r"A\d{1,2}", str(ln.get("id"))):
            p.append(f"audio lane {ln!r} needs an id A1..A99")
            continue
        if ln["id"] in aids:
            p.append(f"audio lane {ln['id']} appears twice")
        aids.append(ln["id"])
        if not _gain_ok(ln.get("gain_db", 0.0)):
            p.append(f"lane {ln['id']}: gain_db must be {GAIN_RANGE_DB[0]:g}..{GAIN_RANGE_DB[1]:g}")
        for flag in ("mute", "solo"):
            if not isinstance(ln.get(flag, False), bool):
                p.append(f"lane {ln['id']}: {flag} must be true or false")
    ids = set()
    clips = _arr(doc.get("clips"), "clips", p)
    for c in clips:
        if not isinstance(c, dict):
            p.append(f"clip {c!r} is not an object")
            continue
        cid = c.get("id")
        tag = f"clip {cid}"
        if not isinstance(cid, str) or not cid:
            p.append("a clip needs an id")
        elif cid in ids:
            p.append(f"{tag} appears twice")
        else:
            ids.add(cid)
        if c.get("lane") not in vids:
            p.append(f"{tag}: lane {c.get('lane')!r} does not exist")
        if not all(_num(c.get(k)) for k in ("src_in", "src_out", "at")):
            p.append(f"{tag}: src_in, src_out and at must be numbers (seconds)")
            continue
        if c["src_in"] < 0 or c["at"] < 0:
            p.append(f"{tag}: src_in and at must be >= 0")
        if c["src_out"] - c["src_in"] < MIN_CLIP_S:
            p.append(f"{tag}: src_in {c['src_in']:.3f} must be before src_out {c['src_out']:.3f}")
        media = media_lookup(c.get("media_id")) if media_lookup else None
        if media_lookup and media is None:
            p.append(f"{tag}: media {c.get('media_id')!r} is not imported")
        if media and c["src_out"] > float(media.get("duration_s") or 0.0) + 1e-3:
            p.append(f"{tag}: src_out {c['src_out']:.3f} is past the media's end "
                     f"({float(media.get('duration_s') or 0):.3f} s)")
        n_tracks = len(media.get("audio") or []) if media else None
        for a in _arr(c.get("audio"), f"{tag}: audio", p):
            if not isinstance(a, dict) or not isinstance(a.get("src_track"), int) or a["src_track"] < 0:
                p.append(f"{tag}: audio entry {a!r} needs src_track >= 0")
                continue
            if n_tracks is not None and a["src_track"] >= n_tracks:
                p.append(f"{tag}: the media has {n_tracks} audio track(s), no track {a['src_track']}")
            if a.get("lane") not in aids:
                p.append(f"{tag}: audio lane {a.get('lane')!r} does not exist")
            if not _gain_ok(a.get("gain_db", 0.0)):
                p.append(f"{tag} track {a['src_track']}: gain_db must be {GAIN_RANGE_DB[0]:g}..{GAIN_RANGE_DB[1]:g}")
            if not isinstance(a.get("mute", False), bool):
                p.append(f"{tag} track {a['src_track']}: mute must be true or false")
    v1 = sorted((c for c in clips if isinstance(c, dict) and c.get("lane") == "V1"
                 and all(_num(c.get(k)) for k in ("src_in", "src_out", "at"))), key=lambda c: c["at"])
    for a, b in zip(v1, v1[1:]):
        if clip_end(a) > b["at"] + EPS:
            p.append(f"clips {a.get('id')} and {b.get('id')} overlap on V1 ({clip_end(a):.3f} > {b['at']:.3f})")
    for m in _arr(doc.get("markers"), "markers", p):
        if not isinstance(m, dict) or not _num(m.get("t")) or m["t"] < 0:
            p.append(f"marker {m!r} needs t >= 0")
    return p


def _check(doc: dict, media_lookup) -> dict:
    problems = validate(doc, media_lookup=media_lookup)
    if problems:
        raise EditError("; ".join(problems[:5]), problems=problems)
    return doc


def _clip(doc: dict, clip_id: str) -> dict:
    for c in doc.get("clips") or []:
        if c.get("id") == clip_id:
            return c
    raise EditError(f"no clip {clip_id} in project {doc.get('id')}", status=404)


def _new_clip_id(doc: dict) -> str:
    taken = {c.get("id") for c in doc.get("clips") or []}
    while True:
        cid = f"c{secrets.token_hex(3)}"
        if cid not in taken:
            return cid


def _t(v: float) -> float:
    return round(float(v), 6)


def _lookup_for(media: Optional[dict]):
    def lookup(mid):
        if media and mid == media.get("id"):
            return media
        return _registry_lookup(mid)
    return lookup


# =================================================================================================
# operations (pure: doc in, new doc out; save() writes)
# =================================================================================================

def add_clip(doc: dict, media: dict, *, src_in: float = 0.0, src_out: Optional[float] = None,
             at: Optional[float] = None, lane: str = "V1") -> Tuple[dict, dict]:
    """Append (at=None) or place a clip of media; its audio tracks land on A1..An (created, labelled from the track
    names, when missing; a project's first clip names the lanes)."""
    doc = copy.deepcopy(doc)
    dur = float(media.get("duration_s") or 0.0)
    src_out = dur if src_out is None else float(src_out)
    if at is None:
        at = max((clip_end(c) for c in doc["clips"] if c.get("lane") == lane), default=0.0)
    lanes = doc["lanes"].setdefault("audio", [])
    first = not doc["clips"]
    by_id = {ln["id"]: ln for ln in lanes}
    audio = []
    for n, _t_ in enumerate(media.get("audio") or []):
        lid = f"A{n + 1}"
        label = track_label(media, n)
        if lid not in by_id:
            by_id[lid] = {"id": lid, "label": label, "gain_db": 0.0, "mute": False, "solo": False}
            lanes.append(by_id[lid])
        elif first:
            by_id[lid]["label"] = label
        audio.append({"src_track": n, "lane": lid, "gain_db": 0.0, "mute": False})
    lanes.sort(key=lambda ln: int(ln["id"][1:]))
    clip = {"id": _new_clip_id(doc), "media_id": media["id"], "lane": lane, "src_in": _t(src_in),
            "src_out": _t(src_out), "at": _t(at), "audio": audio}
    doc["clips"].append(clip)
    doc["clips"].sort(key=lambda c: (c.get("lane"), c.get("at")))
    return _check(doc, _lookup_for(media)), clip


def move(doc: dict, clip_id: str, at: float, *, media_lookup="registry") -> dict:
    doc = copy.deepcopy(doc)
    _clip(doc, clip_id)["at"] = _t(at)
    doc["clips"].sort(key=lambda c: (c.get("lane"), c.get("at")))
    return _check(doc, _registry_lookup if media_lookup == "registry" else media_lookup)


def trim(doc: dict, clip_id: str, *, src_in: Optional[float] = None, src_out: Optional[float] = None,
         media_lookup="registry") -> dict:
    """Move a clip's edges in source time. The left edge keeps the picture where it was on the timeline: at moves by
    the same amount src_in does (dragging a clip's head, not slipping it)."""
    doc = copy.deepcopy(doc)
    c = _clip(doc, clip_id)
    if src_in is not None:
        c["at"] = _t(c["at"] + (float(src_in) - c["src_in"]))
        c["src_in"] = _t(src_in)
    if src_out is not None:
        c["src_out"] = _t(src_out)
    return _check(doc, _registry_lookup if media_lookup == "registry" else media_lookup)


def split(doc: dict, clip_id: str, t: float, *, media_lookup="registry") -> Tuple[dict, dict]:
    """Cut a clip in two at timeline time t; the right half gets a new id and the same track settings."""
    doc = copy.deepcopy(doc)
    c = _clip(doc, clip_id)
    t = float(t)
    if not (c["at"] + MIN_CLIP_S < t < clip_end(c) - MIN_CLIP_S):
        raise EditError(f"split at {t:.3f} s is not inside clip {clip_id} ({c['at']:.3f}..{clip_end(c):.3f})")
    cut = _t(c["src_in"] + (t - c["at"]))
    right = copy.deepcopy(c)
    right.update(id=_new_clip_id(doc), src_in=cut, at=_t(t))
    c["src_out"] = cut
    doc["clips"].append(right)
    doc["clips"].sort(key=lambda x: (x.get("lane"), x.get("at")))
    return _check(doc, _registry_lookup if media_lookup == "registry" else media_lookup), right


def remove(doc: dict, clip_id: str) -> dict:
    doc = copy.deepcopy(doc)
    _clip(doc, clip_id)
    doc["clips"] = [c for c in doc["clips"] if c.get("id") != clip_id]
    return doc


def set_lane_gain(doc: dict, lane: str, *, gain_db: Optional[float] = None, mute: Optional[bool] = None,
                  solo: Optional[bool] = None, label: Optional[str] = None) -> dict:
    doc = copy.deepcopy(doc)
    ln = next((x for x in doc["lanes"].get("audio") or [] if x.get("id") == lane), None)
    if ln is None:
        raise EditError(f"no audio lane {lane}", status=404)
    for key, val in (("gain_db", gain_db), ("mute", mute), ("solo", solo), ("label", label)):
        if val is not None:
            ln[key] = float(val) if key == "gain_db" else val
    return _check(doc, None)


def set_clip_track_gain(doc: dict, clip_id: str, src_track: int, *, gain_db: Optional[float] = None,
                        mute: Optional[bool] = None) -> dict:
    doc = copy.deepcopy(doc)
    c = _clip(doc, clip_id)
    entry = next((a for a in c.get("audio") or [] if a.get("src_track") == src_track), None)
    if entry is None:
        raise EditError(f"clip {clip_id} carries no track {src_track}", status=404)
    if gain_db is not None:
        entry["gain_db"] = float(gain_db)
    if mute is not None:
        entry["mute"] = bool(mute)
    return _check(doc, None)


# =================================================================================================
# render
# =================================================================================================

def presets() -> Dict[str, dict]:
    """The export lane's presets, id -> preset (NotBuilt until arsenal.media.export lands)."""
    export = module("export", "presets")
    got = export.presets()
    if isinstance(got, dict) and isinstance(got.get("presets"), dict):
        got = got["presets"]
    if isinstance(got, list):
        got = {p.get("id"): p for p in got if isinstance(p, dict)}
    return {k: v for k, v in (got or {}).items() if not str(k).startswith("_") and isinstance(v, dict)}


def _loudness_target(preset: dict) -> Optional[dict]:
    want = preset.get("loudness")
    if isinstance(want, dict):
        return want if all(k in want for k in ("I", "TP")) else None
    if not want or want == "none":
        return None
    try:
        export = module("export")
    except NotBuilt:
        return None
    for attr in ("LOUDNESS_TARGETS", "loudness_targets"):
        table = getattr(export, attr, None)
        table = table() if callable(table) else table
        if isinstance(table, dict) and isinstance(table.get(want), dict):
            return table[want]
    got = export.presets() if hasattr(export, "presets") else None
    if isinstance(got, dict) and isinstance((got.get("loudness_targets") or {}).get(want), dict):
        return got["loudness_targets"][want]
    return None


def resolve_preset(preset) -> dict:
    if isinstance(preset, dict):
        out = dict(preset)
        out.setdefault("id", "custom")
        return out
    table = presets()
    if preset not in table:
        raise EditError(f"no export preset {preset!r}; have: {', '.join(sorted(table))}", status=400)
    out = dict(table[preset])
    out["id"] = preset
    return out


def _canvas(doc: dict, preset: dict) -> Tuple[int, int, float]:
    """(w, h, fps) of the render: the preset's numbers, "source"/"auto" falling back to the project's settings."""
    s = doc["settings"]
    pw, ph = preset.get("width"), preset.get("height")
    if isinstance(pw, int) and isinstance(ph, int):
        w, h = pw, ph
    elif isinstance(pw, int):                       # "auto" height keeps the project's aspect
        w, h = pw, max(2, int(round(pw * s["height"] / s["width"] / 2)) * 2)
    else:
        w, h = s["width"], s["height"]
    fps = preset.get("fps") if _num(preset.get("fps")) else s["fps"]
    return int(w), int(h), float(fps)


def _fit_chain(w: int, h: int, fit: str, crop_x: float) -> str:
    if fit == "crop":
        cw = f"trunc(ih*{w}/{h}/2)*2"
        return f"crop={cw}:ih:(iw-{cw})*{crop_x:.4f}:0,scale={w}:{h}:flags=lanczos"
    return (f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black")


def _effective_tracks(doc: dict, clip: dict) -> List[Tuple[int, float]]:
    """(src_track, gain_db) for each track this clip contributes: lane and clip mute, solo, and summed gains."""
    lanes = {ln["id"]: ln for ln in doc["lanes"].get("audio") or []}
    soloing = any(ln.get("solo") for ln in lanes.values())
    out = []
    for a in clip.get("audio") or []:
        ln = lanes.get(a.get("lane")) or {}
        if a.get("mute") or ln.get("mute") or (soloing and not ln.get("solo")):
            continue
        out.append((int(a["src_track"]), float(ln.get("gain_db", 0.0)) + float(a.get("gain_db", 0.0))))
    return out


def _segments(doc: dict, fps: float) -> List[dict]:
    """V1 in timeline order as segments {"gap": True | "clip": c, "start": frame, "frames": n}. Every timeline
    boundary is rounded to a frame once (n = round(end * fps) - round(start * fps)), so each clip starts on the frame
    its `at` names: rounding each clip's LENGTH instead let ten contiguous 0.1167 s clips at 30 fps render 5 frames
    long (1.333 s for a 1.167 s timeline)."""
    clips = sorted((c for c in doc.get("clips") or [] if c.get("lane") == "V1"), key=lambda c: c["at"])
    segs, frame, prev_end = [], 0, 0.0
    for c in clips:
        # a clip that butts onto the previous one (float noise within EPS) starts on its last frame, never a gap
        start = frame if c["at"] <= prev_end + EPS else max(frame, int(round(c["at"] * fps)))
        if start > frame:
            segs.append({"gap": True, "start": frame, "frames": start - frame})
        end = max(start + 1, int(round(clip_end(c) * fps)))
        segs.append({"clip": c, "start": start, "frames": end - start})
        frame, prev_end = end, clip_end(c)
    return segs


def _samples(start_frame: int, frames: int, fps: float) -> int:
    """Audio samples of a segment, from its rounded boundaries: the audio never drifts from the frames."""
    return int(round((start_frame + frames) / fps * AUDIO_RATE)) - int(round(start_frame / fps * AUDIO_RATE))


def build_graph(doc: dict, preset: dict, media: Dict[str, dict], *, crop_x: float = 0.5,
                with_video: bool = True, with_audio: bool = True) -> Tuple[List[str], str, List[str], float]:
    """(input args, filter graph, output labels, total seconds) for the timeline: the render's whole plan."""
    w, h, fps = _canvas(doc, preset)
    fit = preset.get("fit") or "pad"
    inputs: List[str] = []
    parts: List[str] = []
    labels: List[str] = []
    k = 0
    total_frames = 0
    for i, seg in enumerate(_segments(doc, fps)):
        n = seg["frames"]
        samples = _samples(seg["start"], n, fps)
        total_frames += n
        if seg.get("gap"):
            if with_video:
                parts.append(f"color=c=black:s={w}x{h}:r={fps:g},format=yuv420p,setsar=1,"
                             f"trim=end_frame={n},setpts=PTS-STARTPTS[v{i}]")
            if with_audio:
                parts.append(f"anullsrc=r={AUDIO_RATE}:cl=stereo,atrim=end_sample={samples},"
                             f"asetpts=PTS-STARTPTS[a{i}]")
        else:
            c = seg["clip"]
            m = media[c["media_id"]]
            dur = n / fps
            # input-side seek: fast (no decode of what comes before) and frame-accurate when transcoding. After it,
            # t=0 on every stream of this input IS src_in, so each stream is anchored there (fps start_time=0,
            # aresample first_pts=0: pad or trim to it), never on its own first timestamp: PTS-STARTPTS slid a
            # track that starts 0.5 s late 0.5 s early, and mid-file MKV clips 12-24 ms early.
            inputs += ["-ss", f"{c['src_in']:.6f}", "-t", f"{dur + 0.5:.6f}", "-i", m["path"]]
            if with_video:
                parts.append(f"[{k}:v:0]fps={fps:g}:start_time=0,{_fit_chain(w, h, fit, crop_x)},setsar=1,"
                             f"format=yuv420p,tpad=stop=-1:stop_mode=clone,trim=end_frame={n},"
                             f"setpts=PTS-STARTPTS[v{i}]")
            if with_audio:
                tracks = _effective_tracks(doc, c)
                n_src = len(m.get("audio") or [])
                tracks = [(t, g) for t, g in tracks if t < n_src]
                if not tracks:
                    parts.append(f"anullsrc=r={AUDIO_RATE}:cl=stereo,atrim=end_sample={samples},"
                                 f"asetpts=PTS-STARTPTS[a{i}]")
                else:
                    names = []
                    for t, g in tracks:
                        name = f"a{i}t{t}"
                        # async=1 turns on swr's compensation; with first_pts=0 the first frame is padded or
                        # trimmed to src_in (to 1 ms), later jumps over 0.1 s are filled; nothing is stretched
                        parts.append(f"[{k}:a:{t}]aresample={AUDIO_RATE}:async=1:first_pts=0,"
                                     f"aformat=sample_fmts=fltp:channel_layouts=stereo,volume={g:.3f}dB[{name}]")
                        names.append(f"[{name}]")
                    mix = ("".join(names) + f"amix=inputs={len(names)}:normalize=0:dropout_transition=0,"
                           if len(names) > 1 else names[0])
                    parts.append(f"{mix}apad=whole_len={samples},atrim=end_sample={samples},"
                                 f"asetpts=PTS-STARTPTS[a{i}]")
            k += 1
        labels.append(i)
    n_seg = len(labels)
    if n_seg == 0:
        raise EditError("the timeline has no clips on V1")
    streams = "".join((f"[v{i}]" if with_video else "") + (f"[a{i}]" if with_audio else "") for i in labels)
    outs = []
    if with_video:
        outs.append("[vout]")
    if with_audio:
        outs.append("[aout]")
    parts.append(f"{streams}concat=n={n_seg}:v={int(with_video)}:a={int(with_audio)}{''.join(outs)}")
    return inputs, ";\n".join(parts), outs, total_frames / fps


def _media_for(doc: dict) -> Dict[str, dict]:
    out = {}
    for c in doc.get("clips") or []:
        mid = c.get("media_id")
        if mid not in out:
            rec = get_media(mid)
            found = source_path(rec)
            if found is None:
                raise EditError(f"media {mid} is gone from {rec['path']}", status=404)
            out[mid] = dict(rec, path=str(found))
    return out


def safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", str(name)).strip(" .-")[:80] or "untitled"


def default_out_root() -> Path:
    """<first library root of `py -m arsenal serve`>/aurora-edits: a new folder beside nothing."""
    from ..serve import DEFAULT_ROOTS
    return Path(DEFAULT_ROOTS[0]) / OUT_FOLDER


def _part(path: Path) -> Path:
    """The file a render writes before it is published (not a media suffix: the library scan never lists it)."""
    return path.with_name(f"{path.name}.part")


def _fresh(path: Path) -> Path:
    """path, or "name (2).ext", "name (3).ext"...: the first name neither on disk nor claimed by a running render."""
    n, cand = 1, path
    while cand.exists() or _part(cand).exists():
        n += 1
        cand = path.with_name(f"{path.stem} ({n}){path.suffix}")
    return cand


def _claim(target: Path, *, numbered: bool) -> Tuple[Path, Path]:
    """(target, work): create <target>.part with O_EXCL, so two renders at once (the server, the CLI, an MCP door)
    never write one file. A numbered default name moves on to the next free one; an explicit out answers 409.
    A .part a killed render left behind keeps its name taken until someone deletes it."""
    base = target
    while True:
        work = _part(target)
        if not target.exists():
            try:
                os.close(os.open(str(work), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return target, work
            except FileExistsError:
                pass
        if not numbered:
            raise EditError(f"{target} exists or is being rendered ({work.name}); renders never overwrite a file",
                            status=409)
        target = _fresh(base)


def _publish(work: Path, target: Path) -> None:
    """Move a finished render into place WITHOUT replacing anything (os.replace would): Windows' rename refuses an
    existing destination, and elsewhere a hard link does. FileExistsError when target appeared meanwhile."""
    if os.name == "nt":
        _retry(lambda: os.rename(work, target))
    else:
        os.link(work, target)
        os.unlink(work)


def _out_path(doc: dict, preset: dict, out, out_root, media: Dict[str, dict], suffix: str) -> Path:
    sources = {os.path.normcase(str(Path(m["path"]).resolve())) for m in media.values()}
    if out:
        target = Path(out).resolve()
        if target.exists():
            raise EditError(f"{target} exists; renders never overwrite a file (pick another --out)", status=409)
    else:
        root = Path(out_root) if out_root else default_out_root()
        folder = root / safe_name(doc.get("name") or doc["id"])
        target = _fresh(folder / f"{safe_name(doc.get('name'))} r{doc.get('rev')} {preset['id']}{suffix}")
    if os.path.normcase(str(target)) in sources:
        raise EditError("refusing to write over an original", status=409)
    return target


def _run_progress(args: List[str], total_s: float, progress, gpu: Optional[str]) -> None:
    """ffmpeg with -progress on stdout: out_time_us / total is the job's progress. stderr goes to ff's temp file and
    comes back in the MediaError when the run fails."""
    proc = ff.popen(["-progress", "pipe:1", "-nostats", *args], gpu=gpu)
    try:
        for raw in proc.stdout:
            line = raw.decode("ascii", errors="replace").strip()
            if line.startswith("out_time_us=") and progress and total_s > 0:
                with contextlib.suppress(ValueError):
                    progress(min(0.99, max(0.0, int(line.split("=", 1)[1]) / 1e6 / total_s)))
    except BaseException:
        proc.kill()
        ff.finish(proc, check=False)
        raise
    ff.finish(proc, check=True, timeout=None)


def _measure_loudness(inputs: List[str], graph_file: Path, target: dict) -> dict:
    res = ff.run(["-nostats", *inputs, "-/filter_complex", str(graph_file), "-map", "[aln]", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    if not m:
        raise ff.MediaError("loudnorm pass 1 printed no measurement", argv=res.args, stderr=res.stderr)
    return json.loads(m.group(0))


def render(doc, preset="youtube_4k60_fast", *, out=None, out_root=None, crop_x: float = 0.5,
           loudness: str = "preset", qc: bool = True, progress: Optional[Callable[[float], None]] = None) -> dict:
    """Render the timeline to one file with an export preset; returns the house result (receipt under
    <state>/receipts/edit/) with path, duration, the argv, and audio.qc when that lane is built."""
    if isinstance(doc, str):
        doc = load(doc)
    problems = validate(doc, media_lookup=_registry_lookup)
    if problems:
        raise EditError("; ".join(problems[:5]), problems=problems)
    p = resolve_preset(preset)
    if p["id"] in ALPHA_PRESETS:
        raise EditError(f"{p['id']} carries alpha; timeline renders have none (export the clip instead)")
    media = _media_for(doc)
    acodec = list(p.get("acodec") or ["-c:a", "aac", "-b:a", "320k", "-ar", str(AUDIO_RATE), "-ac", "2"])
    with_audio = acodec != ["-an"]
    vcodec = list(p.get("vcodec") or ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"])
    suffix = CONTAINER_SUFFIX.get(str(p.get("container") or "mp4"), ".mp4")
    target = _out_path(doc, p, out, out_root, media, suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    inputs, graph, outs, total_s = build_graph(doc, p, media, crop_x=crop_x, with_audio=with_audio)
    w, h, fps = _canvas(doc, p)
    timeline_s = max((clip_end(c) for c in doc["clips"] if c.get("lane") == "V1"), default=0.0)
    total_frames = int(round(total_s * fps))
    graph_file = edits_dir() / "render-tmp" / f"{doc['id']}-{os.getpid()}-{threading.get_ident()}.graph.txt"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    blind = ["clips are hard cuts: no transitions or join fades in v0",
             "only V1 and the clips' own audio tracks are rendered; markers and board are not",
             f"every clip is one ffmpeg input: {len(inputs) // 6} decoders open at once (peak memory grows about "
             f"19 MiB per 1080p60 HEVC clip: 169 MiB for 1 clip, 861 MiB for 32, measured 2026-10-12)"]
    measured = None
    target_ln = _loudness_target(p) if (loudness == "preset" and with_audio) else None
    if loudness == "preset" and with_audio and p.get("loudness") not in (None, "none") and target_ln is None:
        blind.append(f"preset loudness {p.get('loudness')!r} could not be resolved; no normalisation applied")
    t0 = time.perf_counter()
    base = target
    target, work = _claim(target, numbered=not out)
    try:
        if target_ln:
            with open(graph_file, "w", encoding="utf-8", newline="\n") as fh:
                _, agraph, _, _ = build_graph(doc, p, media, crop_x=crop_x, with_video=False, with_audio=True)
                fh.write(agraph.replace("[aout]", "[amix0]") + f";\n[amix0]loudnorm=I={target_ln['I']}:"
                         f"TP={target_ln['TP']}:LRA={target_ln.get('LRA', 11)}:print_format=json[aln]")
            measured = _measure_loudness(inputs, graph_file, target_ln)
            # digital silence measures input_i -inf, which pass 2 rejects outright: render it plainly and say so
            unmeasurable = module("audio", "loudnorm_unmeasurable").loudnorm_unmeasurable(measured)
            if unmeasurable:
                blind.append(unmeasurable)
                target_ln = None
            else:
                graph = graph.replace("[aout]", "[amix0]", 1)
                graph += (f";\n[amix0]loudnorm=I={target_ln['I']}:TP={target_ln['TP']}:"
                          f"LRA={target_ln.get('LRA', 11)}:measured_I={measured['input_i']}:"
                          f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
                          f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:"
                          f"linear=true,aresample={AUDIO_RATE}[aout]")
        with open(graph_file, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(graph)
        args = ["-y", *inputs, "-/filter_complex", str(graph_file)]
        for label in outs:
            args += ["-map", label]
        args += vcodec + (acodec if with_audio else ["-an"])
        if p.get("faststart"):
            args += ["-movflags", "+faststart"]
        args += ["-f", MUXER.get(target.suffix.lower(), "mp4"), str(work)]
        gpu = "edit render" if any("_amf" in str(a) for a in vcodec) else None
        _run_progress(args, total_s, progress, gpu)
        while True:
            try:
                _publish(work, target)
                break
            except FileExistsError:
                if out:
                    raise EditError(f"{target} appeared while this render ran; renders never overwrite a file",
                                    status=409) from None
                target = _fresh(base)
    finally:
        with contextlib.suppress(OSError):
            work.unlink()
        with contextlib.suppress(OSError):
            graph_file.unlink()
    seconds = time.perf_counter() - t0
    got = ff.probe_json(target, entries=("-show_format", "-show_streams"))
    vstream = next((s for s in got.get("streams") or [] if s.get("codec_type") == "video"), {})
    out_dur = float(vstream.get("duration") or (got.get("format") or {}).get("duration") or 0.0)
    qc_res = None
    if qc and with_audio:
        expect = {"video_streams": 1, "audio_streams": 1, "duration_s": round(timeline_s, 6), "frames": total_frames,
                  "w": w, "h": h, "fps": fps}
        if target_ln:                       # as export does: hold the result to the target it was normalised to
            expect["TP_max"] = target_ln["TP"]
            if measured and float(measured.get("input_i") or -99) > -70:   # digital silence stays at -70 LUFS
                expect.update(I=target_ln["I"], I_tol=0.5)
        try:
            qc_res = module("audio", "qc").qc(str(target), expect=expect)
        except NotBuilt as exc:
            qc_res = {"skipped": str(exc)}
        except Exception as exc:  # the render is done; a failing check is reported, not fatal
            qc_res = {"error": f"{type(exc).__name__}: {exc}"}
    if progress:
        progress(1.0)
    params = {"project": doc["id"], "rev": doc.get("rev"), "preset": p["id"], "out": str(out) if out else None,
              "out_root": str(out_root) if out_root else None, "crop_x": crop_x, "loudness": loudness, "qc": qc,
              "canvas": {"w": w, "h": h, "fps": fps}}
    # duration_ok holds the file to the TIMELINE (the document's last clip end), not to the frame total it was built
    # from, so a rounding slip in the plan shows up here instead of agreeing with itself
    payload = {"path": str(target), "duration_s": round(out_dur, 6), "duration_expected_s": round(timeline_s, 6),
               "frames": total_frames, "duration_ok": abs(out_dur - timeline_s) <= 1.0 / fps + 1e-6,
               "render_s": round(seconds, 3),
               "realtime_x": round(total_s / seconds, 2) if seconds > 0 else None,
               "clips": len([c for c in doc["clips"] if c.get("lane") == "V1"]),
               "loudness_pass1": measured, "qc": qc_res, "argv": ff.argv_for(args), "graph": graph}
    sources = sorted({m["path"] for m in media.values()})
    return receipt.result("edit", sources, params, payload, blind,
                          engine={"timeline": API, "vcodec": vcodec[:2]})


def trim_lossless(doc, clip_id: str, *, out=None, out_root=None, mode: str = "smart") -> dict:
    """One clip out of its source without re-encoding past the first GOP: cut.cut(mode="smart") keeping every audio
    track separate and titled. Lands in the project's render folder unless out says otherwise."""
    if isinstance(doc, str):
        doc = load(doc)
    c = _clip(doc, clip_id)
    cut = module("cut", "cut")
    m = get_media(c["media_id"])
    suffix = Path(m["path"]).suffix or ".mkv"
    target = _out_path(doc, {"id": f"{clip_id} {mode}"}, out, out_root, {m["id"]: m}, suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    return cut.cut(m["path"], float(c["src_in"]), float(c["src_out"]), str(target),
                   mode=mode, tracks="all", verify=True)


# =================================================================================================
# CLI: py -m arsenal.media edit new|list|show|add|trim|split|move|rm|gain|render|lossless
# =================================================================================================

def _edit_and_save(pid: str, op: Callable[[dict], dict]) -> dict:
    doc = load(pid)
    return save(op(doc))


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    from .frames import parse_time as _parse

    def parse_time(text: str) -> float:
        try:
            v = _parse(text)
        except ValueError:
            v = float("nan")
        if not math.isfinite(v):
            raise EditError(f"{text!r} is not a time (seconds, m:ss or h:mm:ss)")
        return v

    ap = argparse.ArgumentParser(prog="py -m arsenal.media edit",
                                 description="the editor's timeline document (arsenal.media.timeline/v0): create, "
                                             "add clips, trim, split, mix, render to a file with an export preset")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new", help="create a project")
    s.add_argument("name")
    s.add_argument("--fps", type=float, default=DEFAULT_SETTINGS["fps"])
    s.add_argument("--width", type=int, default=DEFAULT_SETTINGS["width"])
    s.add_argument("--height", type=int, default=DEFAULT_SETTINGS["height"])
    sub.add_parser("list", help="projects, newest first")
    s = sub.add_parser("show", help="print a project's document")
    s.add_argument("pid")
    s = sub.add_parser("add", help="import a video (read-only) and append it to V1 (or place it with --at)")
    s.add_argument("pid")
    s.add_argument("video")
    s.add_argument("--in", dest="src_in", default="0", help="source in (s or m:ss)")
    s.add_argument("--out", dest="src_out", help="source out (default: the end)")
    s.add_argument("--at", help="timeline position (default: after the last clip)")
    s = sub.add_parser("trim", help="move a clip's in and/or out point (source seconds)")
    s.add_argument("pid")
    s.add_argument("clip")
    s.add_argument("--in", dest="src_in")
    s.add_argument("--out", dest="src_out")
    s = sub.add_parser("split", help="split a clip at a timeline time")
    s.add_argument("pid")
    s.add_argument("clip")
    s.add_argument("t")
    s = sub.add_parser("move", help="place a clip at a timeline time")
    s.add_argument("pid")
    s.add_argument("clip")
    s.add_argument("at")
    s = sub.add_parser("rm", help="remove a clip")
    s.add_argument("pid")
    s.add_argument("clip")
    s = sub.add_parser("gain", help="an audio lane's gain (dB), mute and solo")
    s.add_argument("pid")
    s.add_argument("lane", help="A1, A2, ...")
    s.add_argument("--db", type=float)
    s.add_argument("--mute", choices=("on", "off"))
    s.add_argument("--solo", choices=("on", "off"))
    s = sub.add_parser("render", help="render the timeline to one file with an export preset")
    s.add_argument("pid")
    s.add_argument("--preset", default="youtube_4k60_fast")
    s.add_argument("--out", help="output file (default: <library root>/aurora-edits/<project>/)")
    s = sub.add_parser("lossless", help="one clip out of its source, smart-cut, every audio track kept and titled")
    s.add_argument("pid")
    s.add_argument("clip")
    s.add_argument("--out")
    a = ap.parse_args(argv)

    def show(obj) -> int:
        print(json.dumps(obj, indent=2, default=str))
        return 0

    def onoff(v):
        return None if v is None else v == "on"

    try:
        if a.cmd == "new":
            return show(new_project(a.name, settings={"fps": a.fps, "width": a.width, "height": a.height}))
        if a.cmd == "list":
            for row in list_projects():
                print(f"{row['id']}  rev {row['rev']:<4} {row['clips']:>3} clips  {row['updated_at']}  {row['name']}")
            return 0
        if a.cmd == "show":
            return show(load(a.pid))
        if a.cmd == "add":
            media = import_media(a.video)
            doc = load(a.pid)
            nxt, clip = add_clip(doc, media, src_in=parse_time(a.src_in),
                                 src_out=parse_time(a.src_out) if a.src_out else None,
                                 at=parse_time(a.at) if a.at else None)
            saved = save(nxt)
            return show({"clip": clip, "rev": saved["rev"], "media": {k: media.get(k) for k in
                                                                       ("id", "name", "duration_s", "n_audio")}})
        if a.cmd == "trim":
            saved = _edit_and_save(a.pid, lambda d: trim(d, a.clip,
                                                          src_in=parse_time(a.src_in) if a.src_in else None,
                                                          src_out=parse_time(a.src_out) if a.src_out else None))
            return show(_clip(saved, a.clip))
        if a.cmd == "split":
            saved = _edit_and_save(a.pid, lambda d: split(d, a.clip, parse_time(a.t))[0])
            return show([c for c in saved["clips"] if c["lane"] == "V1"])
        if a.cmd == "move":
            return show(_clip(_edit_and_save(a.pid, lambda d: move(d, a.clip, parse_time(a.at))), a.clip))
        if a.cmd == "rm":
            return show({"rev": _edit_and_save(a.pid, lambda d: remove(d, a.clip))["rev"]})
        if a.cmd == "gain":
            saved = _edit_and_save(a.pid, lambda d: set_lane_gain(d, a.lane, gain_db=a.db, mute=onoff(a.mute),
                                                                   solo=onoff(a.solo)))
            return show(saved["lanes"]["audio"])
        if a.cmd == "render":
            res = render(a.pid, a.preset, out=a.out,
                         progress=lambda f: print(f"\r{f * 100:5.1f}%", end="", flush=True))
            print()
            return show({k: res.get(k) for k in ("path", "duration_s", "duration_ok", "render_s", "realtime_x",
                                                 "qc", "receipt")})
        if a.cmd == "lossless":
            res = trim_lossless(a.pid, a.clip, out=a.out)
            return show({k: res.get(k) for k in ("out", "mode", "audio", "verify", "receipt") if k in res})
    except NotBuilt as exc:
        print(f"edit: {exc}", file=__import__("sys").stderr)
        return 3
    except EditError as exc:
        print(f"edit: {exc}", file=__import__("sys").stderr)
        return 1
    return 2
