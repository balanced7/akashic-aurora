"""arsenal.media.frames -- pictures out of a video in ONE ffmpeg pass: a span, only the keyframes, or exact moments.

Before this, 21 scripts spawned one ffmpeg per timestamp (0.6 s a frame against 0.03 s in one pass) and 13 agents
rewrote a frame-grab helper. Measured on the 1080p60 HEVC OBS recordings: d3d11va decode 1345 fps, CPU 620 fps,
keyframe-only 325x realtime.

    for t, img in frames(v, start=600, dur=120, fps=2, crop=(930, 84, 90, 26)): ...
    for t, img in keyframes(v, crop=(0.48, 0.04, 0.05, 0.02)): ...     # fractions of the frame work too
    for t_req, t_pts, img in at_times(v, [601.5, 640.0]): ...

crop = (x, y, w, h) in source pixels, or all four <= 1.0 as fractions of the frame; applied before scaling, so a HUD
crop never pulls a full-size array into Python. size = (w, h), or (w, None) to keep the aspect (rounded to even).
pix_fmt: 'rgb24' (default), 'bgr24' (OpenCV), 'gray'. hw: 'd3d11va' or None; pixel-exact comparisons decode in
software (hw=None) because d3d11va differs by up to 7 luma levels (ff.KNOWN_BAD). Never 'vulkan' for HEVC here.
"""
from __future__ import annotations

import os
import re
import threading
import queue
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from . import ff

_CHANNELS = {"bgr24": 3, "rgb24": 3, "gray": 1}
_PTS = re.compile(rb"pts_time:\s*([-0-9.]+)")


#: Containers whose index makes an accurate input seek land exactly (measured bit-identical on OBS MP4). Anything
#: else (MPEG-TS, program streams, raw elementary streams) seeks to the first keyframe AT OR AFTER the target:
#: measured 2026-10-12 on a TS with keyframes every 2 s, -ss 3.0 landed at 4.0 and -ss 1.9 at 2.0.
_INDEXED = ("mov", "mp4", "m4a", "3gp", "3g2", "mj2", "matroska", "webm", "avi")


def video_info(path) -> dict:
    """{w, h, fps, start, duration, format, format_start} of the first video stream (one ffprobe call). `start` is
    the stream's start_time; `format_start` the container's, which the file clock counts from."""
    j = ff.probe_json(path, entries=("-select_streams", "v:0", "-show_entries",
                                     "stream=width,height,avg_frame_rate,start_time"
                                     ":format=duration,start_time,format_name"))
    if not j.get("streams"):
        raise ff.MediaError(f"no video stream in {path}")
    s = j["streams"][0]
    fmt = j.get("format") or {}
    num, _, den = str(s.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": fps, "start": float(s.get("start_time") or 0.0),
            "duration": float(fmt.get("duration") or 0.0), "format": str(fmt.get("format_name") or ""),
            "format_start": float(fmt.get("start_time") or 0.0)}


def _indexed(info: dict) -> bool:
    return any(name in _INDEXED for name in info["format"].split(","))


_kf_cache: dict = {}


def _keyframe_at_or_before(path, t: float) -> float:
    """The last keyframe at or before file time t (probe.keyframes speaks the file clock)."""
    from . import probe
    st = os.stat(path)
    key = (str(Path(path).resolve()), st.st_size, st.st_mtime_ns)
    if key not in _kf_cache:
        _kf_cache.clear()
        _kf_cache[key] = probe.keyframes(path)
    before = [k for k in _kf_cache[key] if k <= t + 1e-6]
    return before[-1] if before else 0.0


def _origin(info: dict, point: float) -> float:
    """The file time of ffmpeg's output t=0 when it reads v:0 alone, input-seeked to `point` (0: no seek).

    -ss counts from the format start_time, and so does the output clock, until the streams ffmpeg reads all start
    later than the seek point: then it corrects the output clock to the first of them ("Correcting start time"). A
    picture muxed after its sound therefore comes out with its first frame at t=0 (measured 2026-10-12, ffmpeg
    N-124319, on MPEG-TS: a first frame 0.021 s into the file with the sound muxed ahead, 0.521 s with the picture
    delayed 0.5 s, both labelled 0.000 before this correction)."""
    return max(point, info["start"] - info["format_start"])


def _seek(path, info: dict, start: float) -> Tuple[List[str], float, float]:
    """Input-seek args, the seek point (output t=0 is _origin(info, point)), and the first time to keep.

    Indexed containers: an accurate -ss (ffmpeg decodes from the keyframe and discards up to start). Others: seek to
    just before the keyframe at or before start with -noaccurate_seek, so the landing is that keyframe, and drop the
    frames before start by their pts here."""
    if not start:
        return [], 0.0, 0.0
    if _indexed(info):
        return ["-ss", f"{start:.6f}"], start, start
    point = max(0.0, _keyframe_at_or_before(path, start) - 0.0005)
    return (["-noaccurate_seek", "-ss", f"{point:.6f}"] if point > 0 else []), point, start


def resolve_crop(crop, w: int, h: int) -> Optional[Tuple[int, int, int, int]]:
    """Pixels stay pixels; four values all <= 1.0 are fractions of (w, h). Clamped to the frame, sizes made even."""
    if not crop:
        return None
    x, y, cw, ch = (float(v) for v in crop)
    if max(x, y, cw, ch) <= 1.0:
        x, y, cw, ch = x * w, y * h, cw * w, ch * h
    x, y = int(round(x)), int(round(y))
    cw, ch = int(round(cw)), int(round(ch))
    if cw <= 0 or ch <= 0 or x < 0 or y < 0 or x + cw > w or y + ch > h:
        raise ff.MediaError(f"crop {crop} falls outside the {w}x{h} frame")
    return x, y, cw, ch


def _out_size(info: dict, crop, size) -> Tuple[int, int]:
    base_w, base_h = (crop[2], crop[3]) if crop else (info["w"], info["h"])
    if not size:
        return base_w, base_h
    sw, sh = size
    if sw and not sh:
        sh = max(2, int(round(base_h * sw / base_w / 2)) * 2)
    elif sh and not sw:
        sw = max(2, int(round(base_w * sh / base_h / 2)) * 2)
    return int(sw), int(sh)


def _vf(crop, size, fps) -> str:
    chain = []
    if crop:
        x, y, w, h = crop
        chain.append(f"crop={w}:{h}:{x}:{y}")
    if size:
        chain.append(f"scale={size[0]}:{size[1]}:flags=area")
    if fps:
        chain.append(f"fps={fps}")
    chain.append("showinfo")            # per-frame pts_time on stderr -> exact timestamps
    return ",".join(chain)


#: Longest wait for a frame's showinfo line once its pixels have arrived. Generous: a line is normally microseconds
#: behind its frame; a missing one means the pixel and timestamp streams disagree, which must fail, never hang.
_PTS_WAIT_S = 60.0


def _stream(args: List[str], w: int, h: int, ch: int, t_offset: float) -> Iterator[Tuple[float, "np.ndarray"]]:
    import subprocess
    import numpy as np
    argv = ff.argv_for(args)
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=ff._NO_WINDOW)
    times: "queue.Queue[Optional[float]]" = queue.Queue()
    tail: List[bytes] = []

    def read_stderr() -> None:     # showinfo lines carry the pts; the rest is kept for the error message
        for line in iter(proc.stderr.readline, b""):
            m = _PTS.search(line)
            if m:
                times.put(float(m.group(1)))
            else:
                tail.append(line)
                del tail[:-20]
        times.put(None)

    reader = threading.Thread(target=read_stderr, daemon=True)
    reader.start()
    n = w * h * ch
    got = 0
    try:
        while True:
            buf = proc.stdout.read(n)
            if len(buf) < n:
                break
            try:
                t = times.get(timeout=_PTS_WAIT_S)
            except queue.Empty:
                raise ff.MediaError(f"frame {got} arrived with no timestamp after {_PTS_WAIT_S:.0f} s: ffmpeg wrote "
                                    f"more frames than its filter saw (duplicated output frames)", argv=argv)
            got += 1
            if t is None:              # showinfo printed no pts for it: a decoder hiccup, never a frame with t=None
                continue
            img = np.frombuffer(buf, np.uint8).reshape((h, w, ch) if ch > 1 else (h, w))
            yield round(t + t_offset, 6), img
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
        rc = proc.wait()
        reader.join(timeout=5)
    if got == 0 and rc not in (0, None):
        msg = b" | ".join(x.strip() for x in tail[-4:]).decode("utf-8", errors="replace")
        raise ff.MediaError(f"ffmpeg gave no frames (exit {rc}): {msg}", argv=argv)


def _hw(hw: Optional[str]) -> List[str]:
    if hw == "vulkan":
        raise ff.MediaError(ff.KNOWN_BAD["vulkan_hevc_decode"])
    return ["-hwaccel", hw] if hw else []


def frames(path, start: float = 0.0, dur: Optional[float] = None, fps: Optional[float] = None, crop=None,
           size=None, pix_fmt: str = "rgb24", hw: Optional[str] = "d3d11va") -> Iterator[Tuple[float, "np.ndarray"]]:
    """Every frame of [start, start+dur) (or resampled to fps), as (seconds on the file clock, array).

    The file clock counts from the file's start (what a player shows, what ffmpeg's -ss means); on a container whose
    start_time is not 0 (MPEG-TS) that is the container pts minus the format start."""
    info = video_info(path)
    c = resolve_crop(crop, info["w"], info["h"])
    w, h = _out_size(info, c, size)
    seek, point, keep_from = _seek(path, info, start)
    args = ["-nostats", "-loglevel", "info", *_hw(hw), *seek, "-i", str(path)]
    if dur:
        args += ["-t", f"{(start - point) + dur:.6f}"]
    # passthrough: one output frame per filtered frame, so every frame has exactly one showinfo line (a duplicating
    # output once paired frames with the wrong timestamps, and could stall the reader)
    args += ["-map", "0:v:0", "-fps_mode", "passthrough", "-vf", _vf(c, (w, h) if size else None, fps),
             "-pix_fmt", pix_fmt, "-f", "rawvideo", "-"]
    end = start + dur if dur else None
    for t, img in _stream(args, w, h, _CHANNELS[pix_fmt], _origin(info, point)):
        if t < keep_from - 1e-3:
            continue
        if end is not None and t >= end - 1e-6:
            break
        yield t, img


def keyframes(path, crop=None, size=None, pix_fmt: str = "rgb24",
              hw: Optional[str] = "d3d11va") -> Iterator[Tuple[float, "np.ndarray"]]:
    """Only the keyframes (no inter-frame decode at all): the cheapest whole-file sampler (~325x realtime)."""
    info = video_info(path)
    c = resolve_crop(crop, info["w"], info["h"])
    w, h = _out_size(info, c, size)
    args = ["-nostats", "-loglevel", "info", "-skip_frame", "nokey", *_hw(hw), "-i", str(path), "-map", "0:v:0",
            "-fps_mode", "passthrough", "-vf", _vf(c, (w, h) if size else None, None), "-pix_fmt", pix_fmt,
            "-f", "rawvideo", "-"]
    yield from _stream(args, w, h, _CHANNELS[pix_fmt], _origin(info, 0.0))


def at_times(path, times: Sequence[float], crop=None, size=None, pix_fmt: str = "rgb24", hw: Optional[str] = None,
             max_gap: float = 8.0, past_end: str = "error") -> Iterator[Tuple[float, float, "np.ndarray"]]:
    """The frame showing each requested time, as (t_requested, t_pts, array), in time order.

    Times closer than max_gap share one decode window (one process, input-seek to the window start). The frame for t
    is the first whose pts >= t - 1 ms: ffmpeg's own `-ss t -frames:v 1` convention, so a grab here is bit-identical
    to the single-frame grabs every earlier script made (measured). Software decode by default: these are the frames
    people compare pixel by pixel.

    A time after the last frame's display interval (1/average-fps long: exact for the house's CFR OBS recordings, an
    approximation on a variable-frame-rate file) has no frame. past_end decides: "error" (default) refuses with
    the file's end time, "skip" leaves it out, "last" yields the final frame with its OWN pts, so t_pts < t_req
    shows it was not decoded at t_req (an invented frame must never look like a decoded one)."""
    if past_end not in ("error", "skip", "last"):
        raise ff.MediaError(f"past_end={past_end!r}: error, skip or last")
    ts = sorted(float(t) for t in times)
    if not ts:
        return
    info = video_info(path)
    frame_s = 1.0 / info["fps"] if info["fps"] else 1.0 / 30
    clusters, cur = [], [ts[0]]
    for t in ts[1:]:
        if t - cur[-1] <= max_gap:
            cur.append(t)
        else:
            clusters.append(cur)
            cur = [t]
    clusters.append(cur)
    for c in clusters:
        a, b = c[0], c[-1]
        want = list(c)
        last = None
        for t, img in frames(path, start=max(0.0, a - frame_s), dur=(b - a) + 2.5 * frame_s, crop=crop, size=size,
                             pix_fmt=pix_fmt, hw=hw):
            if t is None:
                continue
            while want and t + 1e-3 >= want[0]:
                yield want.pop(0), t, img
            last = (t, img)
            if not want:
                break
        if want and last is None:              # the whole window lies past the end: read the file's final frames
            for t, img in frames(path, start=max(0.0, info["duration"] - 4 * frame_s), crop=crop, size=size,
                                 pix_fmt=pix_fmt, hw=hw):
                last = (t, img)
        for t_req in want:
            if last is not None and t_req <= last[0] + frame_s + 1e-3:
                yield t_req, last[0], last[1]  # inside the last frame's display interval: it IS the frame shown
            elif past_end == "error":
                end = f"{last[0] + frame_s:.3f} s" if last is not None else "its start"
                raise ff.MediaError(f"t={t_req:.3f} s is past the end of {Path(path).name} (frames end at {end}); "
                                    f"pass past_end='last' or 'skip' to accept that")
            elif past_end == "last" and last is not None:
                yield t_req, last[0], last[1]


def save(path, times: Sequence[float], out_dir, *, fmt: str = "png", crop=None, size=None,
         hw: Optional[str] = None, past_end: str = "error") -> dict:
    """Write the frame at each time to out_dir; returns the house result with a manifest
    [{t_requested, t_pts, crop, file}]."""
    from PIL import Image
    from . import receipt
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    stem = Path(path).stem
    for t_req, t_pts, img in at_times(path, times, crop=crop, size=size, pix_fmt="rgb24", hw=hw, past_end=past_end):
        name = out / f"{stem}_{t_req:010.3f}.{fmt}"
        Image.fromarray(img).save(name)
        rows.append({"t_requested": t_req, "t_pts": t_pts, "crop": list(crop) if crop else None, "file": str(name)})
    params = {"times": list(times), "fmt": fmt, "crop": crop, "size": size, "hw": hw, "past_end": past_end}
    return receipt.result("grab", path, params, {"frames": rows, "out_dir": str(out)},
                          blind=["with past_end='last', a time past the end gets the final frame; its t_pts says so"])


# =================================================================================================
# CLI: py -m arsenal.media grab <video> --at 12.5,30 | --span 10:20 [--fps 2] [--crop x,y,w,h] [--size 640x]
# =================================================================================================

def parse_time(s: str) -> float:
    """'75', '75.5', '1:15', '1:15.5', '0:01:15' -> seconds."""
    parts = [float(p) for p in str(s).strip().split(":")]
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def _parse_size(s: Optional[str]):
    if not s:
        return None
    w, _, h = s.lower().partition("x")
    return (int(w) if w else None, int(h) if h else None)


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="py -m arsenal.media grab",
                                 description="grab frames at times or over a span, in one ffmpeg pass")
    ap.add_argument("video")
    ap.add_argument("--at", help="comma-separated times (s or m:ss)")
    ap.add_argument("--span", help="start:end as m:ss-m:ss or s-s, e.g. 10:00-10:20")
    ap.add_argument("--fps", type=float, default=1.0, help="frames per second over --span (default 1)")
    ap.add_argument("--crop", help="x,y,w,h in pixels, or fractions <= 1.0")
    ap.add_argument("--size", help="WxH, Wx (keep aspect) or xH")
    ap.add_argument("--out", help="folder (default: <state>/grab/<video stem>)")
    ap.add_argument("--sheet", action="store_true", help="also put the frames on one labelled contact sheet")
    ap.add_argument("--hw", default=None, help="d3d11va for speed; default software (pixel-exact)")
    a = ap.parse_args(argv)
    crop = tuple(float(v) for v in a.crop.split(",")) if a.crop else None
    if a.at:
        times = [parse_time(t) for t in a.at.split(",") if t.strip()]
    elif a.span:
        lo, _, hi = a.span.partition("-")
        t0, t1 = parse_time(lo), parse_time(hi)
        n = max(1, int((t1 - t0) * a.fps))
        times = [t0 + i / a.fps for i in range(n)]
    else:
        ap.error("give --at or --span")
    out = Path(a.out) if a.out else ff.state_dir() / "grab" / Path(a.video).stem
    res = save(a.video, times, out, crop=crop, size=_parse_size(a.size), hw=a.hw)
    if a.sheet:
        try:
            from . import sheet as sheet_mod
        except ImportError:
            print("(--sheet: arsenal.media.sheet is not built yet)")
        else:
            sh = sheet_mod.sheet([r["file"] for r in res["frames"]], out=str(out / "sheet.png"))
            res["sheet"] = sh.get("png")
    print(json.dumps({"out_dir": res["out_dir"], "frames": len(res["frames"]), "sheet": res.get("sheet"),
                      "receipt": res.get("receipt")}, indent=2))
    return 0
