"""arsenal.media.probe -- a file's facts: what it is, every stream, where its keyframes are; remembered as a sidecar.

Why it exists: ffprobe JSON was parsed by hand 44 times by 20 agents and probe.py was written by 4 of them, and
nothing remembered the answers, so every agent re-read 2.4 GB recordings. probe() reads a file once and writes its
facts to <state>/sidecars/<id>.json (never beside the original; the original is opened read-only). The sidecar is
the truth the media catalog (catalog.py) indexes; the catalog can be rebuilt from the sidecars alone.

keyframes() is the packet-flag scan: it reads the container index, decodes nothing, and takes 0.8 s on a 33-minute
recording (the `-skip_frame nokey` decode path took 11.8 s and is not used).

Every time in a sidecar is a file time (README, "The house clock"): seconds from the file's start, container pts
minus the format start_time. The one exception is the top-level start_s, which IS that format start_time: where file
time 0 sits on the container's own clock (1.4 s on an MPEG-TS, 0 on OBS MP4). video.start_s is where the first frame
sits in the file (0.021 s on an MPEG-TS whose sound is muxed ahead of the picture). A sidecar written before the
ruling (no "clock" key) kept container pts; read_sidecar() moves it onto the file clock and probe() rewrites it.

Measured 2026-10-12 on `2026-10-11 17-51-11.mp4` (33 min, 2.4 GB, HEVC 1080p60, OBS 32.2.2): ffprobe 47-58 ms,
quick_id 1-2 ms warm, the keyframe interval from the first 20 s of packets 55 ms, the full keyframe index 1.0 s
(487 keyframes, 4.17 s apart). A cold probe took 0.69 s, 0.42 s of it the League kind check (3 keyframes through the
league lane's HUD reader: replay, replay, replay); the same probe from its sidecar took 2.8 ms.

    sc = probe(path)                    # -> sidecar dict (+ the house result keys: api, source, params, blind)
    sc["audio"][0]["house_name"]        # "Mix": a stream's own title, else the house track map (OBS track N+1)
    sc["video"]["keyint_s"]             # 4.166667: how early a copy-cut can start
"""
from __future__ import annotations

import importlib.util
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from . import ff, parse
from .receipt import quick_id  # noqa: F401  (re-exported: probe.quick_id is the documented name)

SIDECAR_SCHEMA = "arsenal.media.sidecar/v0"

#: ffmpeg's a:N is OBS track N+1 (studio Part 3.3). The map's home is arsenal.media.audio; track_name() uses audio's
#: rule and this copy is only its fallback.
HOUSE_TRACKS = {0: "Mix", 1: "Voice", 2: "Game", 3: "Comms", 4: "Music", 5: "Piano"}

#: Packets read from the start of the file to measure the keyframe interval without a full scan.
KEYINT_HEAD_S = 20.0

#: Keys a probe result carries on top of the sidecar: never written into the sidecar file.
RESULT_KEYS = ("api", "source", "params", "computed_with", "blind", "receipt", "cached", "sidecar_path")

#: Sidecar keys that belong to the catalog's history of the file, kept when the facts are re-read.
_KEPT_ON_REFRESH = ("kind", "kind_from", "kind_votes", "links", "spans", "artifacts", "tags", "cataloged")

#: Windows refuses a file for a moment while another process replaces it, and refuses the replace while a reader
#: holds the old file open (both a PermissionError). Unretried, the review saw 1 of 428 reads and 1 of 868 writes
#: fail that way with two processes on one sidecar for 15 s. Each is now retried this long before it counts.
SHARE_RETRY_S = 2.0

BLIND = [
    "vfr is ffprobe's average-vs-base frame rate comparison unless pymediainfo is installed (it reads the "
    "container's own frame-rate mode)",
    "keyint_s without keyframes=True is measured on the first 20 s of packets only; keyframes_n needs keyframes=True",
    "recorded_at from an OBS file name is LOCAL wall time with 1 s resolution; from tags it is the container's "
    "creation_time, which some tools reset on remux",
    "kind is league_* only when arsenal.media.league.hud can look at 3 keyframes; otherwise screen (an OBS "
    "recording) or unknown",
]


def keyframes(path, *, stream: int = 0) -> List[float]:
    """File times (s from the file's start: container pts minus the format start_time) of every keyframe of video
    stream `stream`, ascending. One ffprobe pass reads the packet flags and the format start together."""
    res = ff.run(["-v", "error", "-select_streams", f"v:{stream}", "-show_entries",
                  "packet=pts_time,flags:format=start_time", "-of", "csv", str(path)], tool="ffprobe")
    pts: List[float] = []
    f0 = 0.0
    for line in res.stdout.splitlines():
        section, _, rest = line.partition(",")
        if section == "packet":
            t, _, flags = rest.partition(",")
            if "K" in flags and t not in ("", "N/A"):
                pts.append(float(t))
        elif section == "format" and rest.strip(",") not in ("", "N/A"):
            f0 = float(rest.strip(","))
    return sorted(round(t - f0, 6) for t in pts)


_scan_keyframes = keyframes        # probe()'s `keyframes` flag shadows the function name inside probe()


# =================================================================================================
# sidecars: <state>/sidecars/<id>.json, the truth the catalog indexes
# =================================================================================================

def sidecar_dir() -> Path:
    return ff.state_dir() / "sidecars"


def sidecar_path(media_id: str) -> Path:
    return sidecar_dir() / f"{media_id}.json"


def retry_shared(fn, *, wait_s: Optional[float] = None):
    """fn(), retried while Windows answers PermissionError (a sharing violation, or a name still being replaced or
    deleted) for up to wait_s (default SHARE_RETRY_S); the last PermissionError is raised."""
    deadline = time.monotonic() + (SHARE_RETRY_S if wait_s is None else wait_s)
    delay = 0.002
    while True:
        try:
            return fn()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.05)


def read_sidecar(media_id: str) -> Optional[dict]:
    """The sidecar on the file clock, or None when there is none (or it is not JSON: probe() then reads the file
    again). One held open by another process for longer than SHARE_RETRY_S refuses, never reads as missing."""
    raw = _read_raw(media_id)
    return None if raw is None else on_file_clock(raw)


def on_file_clock(sc: dict) -> dict:
    """A sidecar with every time on the file clock. One written before the house clock ruling (no "clock" key) kept
    container pts in keyframes, chapters and video.start_s: each is moved by the format start it recorded (start_s)."""
    if sc.get("clock") == "file":
        return sc
    sc = dict(sc)
    f0 = float(sc.get("start_s") or 0.0)
    if f0:
        if sc.get("keyframes") is not None:
            sc["keyframes"] = [round(k - f0, 6) for k in sc["keyframes"]]
        if isinstance(sc.get("video"), dict) and sc["video"].get("start_s") is not None:
            sc["video"] = dict(sc["video"], start_s=round(sc["video"]["start_s"] - f0, 6))
        sc["chapters"] = [dict(c, **{k: round(c[k] - f0, 6) for k in ("t0", "t1") if c.get(k) is not None})
                          for c in sc.get("chapters") or []]
    sc["clock"] = "file"
    return sc


def _read_raw(media_id: str) -> Optional[dict]:
    """The sidecar file exactly as written."""
    path = sidecar_path(media_id)
    try:
        text = retry_shared(lambda: path.read_text(encoding="utf-8"))
    except PermissionError as exc:
        raise ff.MediaError(f"sidecar {media_id} stayed locked by another process for {SHARE_RETRY_S:g} s "
                            f"({path})") from exc
    except OSError:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def pure(sidecar: dict) -> dict:
    """The sidecar part of a probe result (the house result keys removed)."""
    return {k: v for k, v in sidecar.items() if k not in RESULT_KEYS}


@contextmanager
def sidecar_lock(media_id: str, wait_s: float = 10.0, stale_s: float = 60.0) -> Iterator[None]:
    """One writer per sidecar across processes (the editor's server and an agent's import can meet): an O_EXCL
    lock file beside it, taken over when older than stale_s."""
    lock = sidecar_path(media_id).with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            os.close(os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):  # PermissionError: Windows, the last holder's lock still deleting
            pass
        try:
            if time.time() - lock.stat().st_mtime > stale_s:
                lock.unlink()
                continue
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise ff.MediaError(f"sidecar {media_id} is locked by another writer ({lock})")
        time.sleep(0.02)
    try:
        yield
    finally:
        try:
            retry_shared(lock.unlink)       # a lock left behind would stall every writer until it goes stale
        except OSError:
            pass


def write_sidecar(sidecar: dict) -> Path:
    """Write atomically (temp file + replace), UTF-8, LF; returns the path. Callers hold sidecar_lock()."""
    sc = pure(sidecar)
    path = sidecar_path(sc["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}-{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(sc, fh, indent=1, sort_keys=True)
            fh.write("\n")
        try:
            retry_shared(lambda: os.replace(tmp, path))     # a reader holding the old file open refuses the replace
        except PermissionError as exc:
            raise ff.MediaError(f"sidecar {sc['id']} stayed open in another process for {SHARE_RETRY_S:g} s; "
                                f"not written ({path})") from exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return path


# =================================================================================================
# facts
# =================================================================================================

def _ratio(text) -> Optional[float]:
    num, _, den = str(text or "").partition("/")
    try:
        n, d = float(num), float(den or 1)
    except ValueError:
        return None
    return n / d if d else None


def _num(value, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def track_name(audio_index: int, tags: Optional[dict]) -> Tuple[Optional[str], str]:
    """(title, house_name): arsenal.media.audio's rule, so the catalog and the audio lanes name tracks alike (a
    stream's own title unless an encoder wrote a generic one like "simple_opus_recording0", else the house map).
    The fallback below is only for a moment when audio.py cannot be imported."""
    try:
        from .audio import track_name as audio_track_name
    except Exception:
        title = (tags or {}).get("title") or None
        return title, title or HOUSE_TRACKS.get(audio_index, f"Track {audio_index + 1}")
    title, house, _source = audio_track_name(audio_index, tags)
    return title, house


def _minus(value, f0: float) -> Optional[float]:
    """A container time as a file time."""
    v = _num(value)
    return None if v is None else round(v - f0, 6)


def _video(s: dict, f0: float) -> dict:
    tags = s.get("tags") or {}
    avg, base = _ratio(s.get("avg_frame_rate")), _ratio(s.get("r_frame_rate"))
    fps = avg or base
    return {"index": s.get("index"), "codec": s.get("codec_name"), "profile": s.get("profile"),
            "w": s.get("width"), "h": s.get("height"), "fps": round(fps, 6) if fps else None,
            "fps_rational": s.get("avg_frame_rate") if avg else s.get("r_frame_rate"),
            "vfr": bool(avg and base and abs(avg - base) > 0.01 * base), "vfr_from": "ffprobe-rates",
            "has_b_frames": _num(s.get("has_b_frames"), int), "pix_fmt": s.get("pix_fmt"),
            "color": {"range": s.get("color_range"), "space": s.get("color_space"),
                      "transfer": s.get("color_transfer"), "primaries": s.get("color_primaries")},
            "time_base": s.get("time_base"), "start_s": _minus(s.get("start_time"), f0),
            "duration_s": _num(s.get("duration")), "frames": _num(s.get("nb_frames"), int),
            "encoder": tags.get("encoder"), "title": tags.get("title"),
            "keyint_s": None, "keyint_frames": None, "keyint_from": None, "keyframes_n": None}


def _audio(streams: List[dict]) -> List[dict]:
    out = []
    for n, s in enumerate(x for x in streams if x.get("codec_type") == "audio"):
        tags = s.get("tags") or {}
        title, house = track_name(n, tags)
        out.append({"index": n, "stream": s.get("index"), "codec": s.get("codec_name"),
                    "channels": s.get("channels"), "layout": s.get("channel_layout"),
                    "sample_rate": _num(s.get("sample_rate"), int), "title": title,
                    "house_name": house, "language": tags.get("language"),
                    "duration_s": _num(s.get("duration")), "bit_rate": _num(s.get("bit_rate"), int)})
    return out


def _subtitles(streams: List[dict]) -> List[dict]:
    return [{"index": n, "stream": s.get("index"), "codec": s.get("codec_name"),
             "title": (s.get("tags") or {}).get("title"), "language": (s.get("tags") or {}).get("language")}
            for n, s in enumerate(x for x in streams if x.get("codec_type") == "subtitle")]


def _chapters(raw: List[dict], f0: float) -> List[dict]:
    return [{"t0": _minus(c.get("start_time"), f0), "t1": _minus(c.get("end_time"), f0),
             "title": (c.get("tags") or {}).get("title")} for c in raw or []]


def _creation_epoch(tags: dict) -> Optional[float]:
    raw = tags.get("creation_time")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp() if dt.year >= 2000 else None     # mp4 writers put 1904/1970 in for "unknown"


def _recorded(path: Path, tags: dict, mtime_ns: int, duration: Optional[float]) -> Tuple[str, float, str]:
    """(local ISO wall time, epoch, where it came from): the OBS name, else the container's creation_time, else the
    file's mtime minus its duration (the moment a recorder that closes on stop started)."""
    dt = parse.obs_time(path.name)
    if dt is not None:
        return dt.isoformat(), parse.local_epoch(dt), "filename"
    epoch = _creation_epoch(tags)
    source = "tags"
    if epoch is None:
        epoch, source = mtime_ns / 1e9 - (duration or 0.0), "mtime-duration"
    local = datetime.fromtimestamp(round(epoch))
    return local.isoformat(), float(epoch), source


def _keyint_head(path, seconds: float = KEYINT_HEAD_S) -> Optional[float]:
    """Median gap between keyframes in the first `seconds` of packets: the keyframe interval without a full scan."""
    res = ff.run(["-v", "error", "-select_streams", "v:0", "-read_intervals", f"%+{seconds:g}",
                  "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(path)], tool="ffprobe", check=False)
    kf = sorted(float(p) for p, _, f in (ln.partition(",") for ln in res.stdout.splitlines())
                if "K" in f and p not in ("", "N/A"))
    return _median_gap(kf)


def _median_gap(kf: List[float]) -> Optional[float]:
    gaps = sorted(b - a for a, b in zip(kf, kf[1:]) if b > a)
    return round(gaps[len(gaps) // 2], 6) if gaps else None


def _set_keyint(video: dict, keyint: Optional[float], source: str, n: Optional[int] = None) -> None:
    video["keyint_s"] = keyint
    video["keyint_frames"] = int(round(keyint * video["fps"])) if keyint and video.get("fps") else None
    video["keyint_from"] = source if keyint else None
    if n is not None:
        video["keyframes_n"] = n


def _mediainfo(path) -> Optional[dict]:
    """pymediainfo, when installed: the writing application and the container's own frame-rate mode (31 ms)."""
    if importlib.util.find_spec("pymediainfo") is None:
        return None
    try:
        from pymediainfo import MediaInfo
        info = MediaInfo.parse(str(path))
    except Exception as exc:          # a mediainfo failure must not cost the probe
        return {"error": str(exc)[:200]}
    general = next((t for t in info.tracks if t.track_type == "General"), None)
    video = next((t for t in info.tracks if t.track_type == "Video"), None)
    return {"writing_application": getattr(general, "writing_application", None),
            "encoded_application": getattr(general, "encoded_application", None),
            "frame_rate_mode": getattr(video, "frame_rate_mode", None) if video else None}


def _facts(path: Path, st: os.stat_result, media_id: str, mediainfo: bool) -> dict:
    j = ff.probe_json(path)
    fmt = j.get("format") or {}
    tags = fmt.get("tags") or {}
    streams = j.get("streams") or []
    vstreams = [s for s in streams if s.get("codec_type") == "video"
                and not (s.get("disposition") or {}).get("attached_pic")]
    duration = _num(fmt.get("duration"))
    f0 = _num(fmt.get("start_time")) or 0.0
    video = _video(vstreams[0], f0) if vstreams else None
    mi = _mediainfo(path) if mediainfo else None
    if video is not None:
        _set_keyint(video, _keyint_head(path), f"head:{KEYINT_HEAD_S:g}s")
        mode = (mi or {}).get("frame_rate_mode")
        if mode in ("CFR", "VFR"):
            video["vfr"], video["vfr_from"] = mode == "VFR", "mediainfo"
    recorded_at, recorded_epoch, recorded_from = _recorded(path, tags, st.st_mtime_ns, duration)
    encoder = tags.get("encoder") or (mi or {}).get("writing_application")
    return {"schema": SIDECAR_SCHEMA, "id": media_id, "path": str(path), "name": path.name, "size": st.st_size,
            "mtime_ns": st.st_mtime_ns, "container": fmt.get("format_name"), "duration_s": duration,
            "clock": "file", "start_s": _num(fmt.get("start_time")), "bit_rate": _num(fmt.get("bit_rate"), int),
            "recorded_at": recorded_at, "recorded_epoch": recorded_epoch, "recorded_from": recorded_from,
            "encoder": encoder, "format_tags": tags, "video": video, "audio": _audio(streams),
            "subtitles": _subtitles(streams), "chapters": _chapters(j.get("chapters"), f0), "mediainfo": mi,
            "kind": _cheap_kind(video, encoder), "kind_from": "rules", "links": {}, "spans": [], "artifacts": [],
            "tags": [], "probed_at": datetime.now().isoformat(timespec="seconds"),
            "probed_with": {"ffprobe": ff.version_short(), "pymediainfo": mi is not None}}


def _cheap_kind(video: Optional[dict], encoder: Optional[str]) -> str:
    if video is None:
        return "audio"
    return "screen" if str(encoder or "").startswith("OBS") else "unknown"


# =================================================================================================
# kind: League footage, by the league lane's HUD layout detector on 3 keyframes
# =================================================================================================

def _hud():
    """arsenal.media.league.hud when the league lane has built it, else None (kind then stays screen/unknown)."""
    try:
        if importlib.util.find_spec("arsenal.media.league.hud") is None:
            return None
        from .league import hud
    except Exception:
        return None
    return hud if hasattr(hud, "detect_layout") else None


def _keyframe_at(path, t: float, w: int, h: int):
    """The first keyframe at or after t, decoded alone (-skip_frame nokey): one HEVC frame, not a GOP."""
    import numpy as np
    res = ff.run(["-v", "error", "-skip_frame", "nokey", "-ss", f"{t:.3f}", "-i", str(path), "-map", "0:v:0",
                  "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], binary=True, check=False)
    if len(res.stdout) < w * h * 3:
        return None
    return np.frombuffer(res.stdout[:w * h * 3], np.uint8).reshape((h, w, 3))


def detect_kind(path, sidecar: dict) -> Tuple[str, str, Optional[list]]:
    """(kind, kind_from, votes): league_replay / league_live when the HUD detector sees that layout on at least 2 of
    3 keyframes (25/50/75% of the file); otherwise the sidecar's rule-based kind is kept. votes is None when the
    league lane's HUD module is not there to ask (ingest asks again once it is)."""
    hud = _hud()
    video = sidecar.get("video")
    if hud is None:
        return sidecar.get("kind", "unknown"), sidecar.get("kind_from", "rules"), None
    if not video or not sidecar.get("duration_s"):
        return sidecar.get("kind", "unknown"), sidecar.get("kind_from", "rules"), []
    votes = []
    for frac in (0.25, 0.5, 0.75):
        img = _keyframe_at(path, sidecar["duration_s"] * frac, video["w"], video["h"])
        if img is None:
            continue
        try:
            votes.append(str(hud.detect_layout(img)))
        except Exception as exc:
            votes.append(f"error: {str(exc)[:80]}")
    for layout in ("replay", "live"):
        if votes.count(layout) >= 2:
            return f"league_{layout}", "hud", votes
    return sidecar.get("kind", "unknown"), sidecar.get("kind_from", "rules"), votes


# =================================================================================================
# probe
# =================================================================================================

def _params(keyframes: bool, mediainfo: bool, refresh: bool) -> dict:
    return {"keyframes": keyframes, "mediainfo": mediainfo, "refresh": refresh, "keyint_head_s": KEYINT_HEAD_S}


def probe(path, *, keyframes: bool = False, mediainfo: bool = True, refresh: bool = False) -> dict:
    """The file's facts as an "arsenal.media.sidecar/v0" dict, read once and remembered under <state>/sidecars/.

    keyframes=True also stores the full keyframe list (packet-flag scan, ~1 s per 33 min) and sets keyframes_n.
    mediainfo=True uses pymediainfo when it is installed (writing application, CFR/VFR). refresh=True re-reads the
    facts even when the sidecar is current; what the catalog learned since (spans, artifacts, tags, links, kind)
    is kept. The result is the sidecar plus the house result keys (api, source, params, computed_with, blind).

    A sidecar is written for every file probed; only files imported into the catalog (catalog.upsert / ingest)
    become catalog rows, and probe() keeps those rows current when it re-reads one."""
    from . import receipt
    p = Path(path).resolve()
    if not p.is_file():
        raise ff.MediaError(f"no such file: {p}")
    st = p.stat()
    media_id = quick_id(p)
    raw = _read_raw(media_id)
    old = None if raw is None else on_file_clock(raw)
    current = old is not None and old.get("size") == st.st_size and old.get("mtime_ns") == st.st_mtime_ns
    computed = refresh or not current
    if computed:
        sc = _facts(p, st, media_id, mediainfo)
        if old:
            sc.update({k: old[k] for k in _KEPT_ON_REFRESH if k in old})
            if current and old.get("keyframes") is not None:
                sc["keyframes"] = old["keyframes"]
                _set_keyint(sc["video"], old["video"].get("keyint_s"), old["video"].get("keyint_from"),
                            len(old["keyframes"]))
        if sc.get("kind_from") == "rules":
            sc["kind"], sc["kind_from"], votes = detect_kind(p, sc)
            if votes is not None:
                sc["kind_votes"] = votes
    else:
        sc = dict(old)
        if sc.get("path") != str(p):                # the same bytes, seen at a new path (moved or copied)
            sc["path"], sc["name"], computed = str(p), p.name, True
        if raw.get("clock") != "file":              # written on the container clock: rewritten on the file clock
            computed = True
    if keyframes and sc.get("video") and sc.get("keyframes") is None:
        kf = _scan_keyframes(p)
        sc["keyframes"] = kf
        _set_keyint(sc["video"], _median_gap(kf), "full", len(kf))
        computed = True
    if computed:
        with sidecar_lock(media_id):
            fresh = read_sidecar(media_id)
            if fresh is not None and fresh != old:    # the catalog wrote while we read the file: keep its news
                sc.update({k: fresh[k] for k in _KEPT_ON_REFRESH if k in fresh})
            write_sidecar(sc)
            if sc.get("cataloged"):               # under the lock: rows land in the order sidecars were written
                from . import catalog
                catalog.reindex(sc)
    src = {"path": sc["path"], "size": sc["size"], "mtime_ns": sc["mtime_ns"], "id": media_id}
    res = receipt.result("probe", src, _params(keyframes, mediainfo, refresh), sc, BLIND, write_receipt=computed)
    res.setdefault("receipt", None)             # an answer from the sidecar computed nothing new to write down
    res["cached"] = not computed
    res["sidecar_path"] = str(sidecar_path(media_id))
    return res


# =================================================================================================
# CLI: py -m arsenal.media probe <video> [--keyframes] [--refresh] [--json]
# =================================================================================================

def _summary(sc: dict) -> List[str]:
    lines = [f"{sc['name']}  id {sc['id']}  {sc['size'] / 1e9:.2f} GB  {sc['duration_s'] or 0:.2f} s  "
             f"{sc.get('container')}  kind {sc.get('kind')}"]
    lines.append(f"recorded {sc.get('recorded_at')} ({sc.get('recorded_from')})   encoder {sc.get('encoder')}")
    v = sc.get("video")
    if v:
        lines.append(f"video  {v['codec']} {v['w']}x{v['h']} {v['fps']} fps{' VFR' if v['vfr'] else ''}  "
                     f"b-frames {v['has_b_frames']}  {v['pix_fmt']}  keyframe every {v['keyint_s']} s "
                     f"({v['keyint_frames']} frames, {v['keyint_from']})"
                     + (f", {v['keyframes_n']} keyframes" if v.get("keyframes_n") else ""))
    for a in sc.get("audio", []):
        lines.append(f"audio  a:{a['index']} {a['codec']} {a['channels']} ch {a['sample_rate']} Hz  "
                     f"\"{a['house_name']}\"" + ("" if a["title"] else " (house map: no title in the file)"))
    for c in sc.get("chapters", []):
        lines.append(f"chapter {c['t0']:.3f}-{c['t1']:.3f}  {c['title']}")
    return lines


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media probe",
                                 description="ffprobe a video once and remember it: duration, codec, fps, every "
                                             "audio track and its name, keyframe interval, OBS encoder, recorded time")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--keyframes", action="store_true", help="also index every keyframe (~1 s per 33 min)")
    ap.add_argument("--refresh", action="store_true", help="re-read the file even if its sidecar is current")
    ap.add_argument("--no-mediainfo", action="store_true", help="skip pymediainfo even when it is installed")
    ap.add_argument("--json", action="store_true", help="print the whole sidecar")
    a = ap.parse_args(argv)
    for path in a.paths:
        t0 = time.perf_counter()
        sc = probe(path, keyframes=a.keyframes, mediainfo=not a.no_mediainfo, refresh=a.refresh)
        if a.json:
            print(json.dumps({k: v for k, v in sc.items() if k != "keyframes"}, indent=1, default=str))
            continue
        print("\n".join(_summary(sc)))
        print(f"({'sidecar' if sc['cached'] else 'probed'} in {(time.perf_counter() - t0) * 1000:.0f} ms: "
              f"{sc['sidecar_path']})")
    return 0
