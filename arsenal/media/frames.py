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

import re
import threading
import queue
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from . import ff

_CHANNELS = {"bgr24": 3, "rgb24": 3, "gray": 1}
_PTS = re.compile(rb"pts_time:\s*([-0-9.]+)")


def video_info(path) -> dict:
    """{w, h, fps, start, duration} of the first video stream (one ffprobe call)."""
    j = ff.probe_json(path, entries=("-select_streams", "v:0", "-show_entries",
                                     "stream=width,height,avg_frame_rate,start_time:format=duration"))
    if not j.get("streams"):
        raise ff.MediaError(f"no video stream in {path}")
    s = j["streams"][0]
    num, _, den = str(s.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": fps, "start": float(s.get("start_time") or 0.0),
            "duration": float((j.get("format") or {}).get("duration") or 0.0)}


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
            t = times.get()
            img = np.frombuffer(buf, np.uint8).reshape((h, w, ch) if ch > 1 else (h, w))
            got += 1
            yield (round(t + t_offset, 6) if t is not None else None), img
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
    """Every frame of [start, start+dur) (or resampled to fps), as (pts seconds on the source clock, array)."""
    info = video_info(path)
    c = resolve_crop(crop, info["w"], info["h"])
    w, h = _out_size(info, c, size)
    args = ["-nostats", "-loglevel", "info", *_hw(hw)]
    args += (["-ss", f"{start:.6f}"] if start else []) + ["-i", str(path)]
    args += (["-t", f"{dur:.6f}"] if dur else [])
    args += ["-map", "0:v:0", "-vf", _vf(c, (w, h) if size else None, fps), "-pix_fmt", pix_fmt,
             "-f", "rawvideo", "-"]
    yield from _stream(args, w, h, _CHANNELS[pix_fmt], start)


def keyframes(path, crop=None, size=None, pix_fmt: str = "rgb24",
              hw: Optional[str] = "d3d11va") -> Iterator[Tuple[float, "np.ndarray"]]:
    """Only the keyframes (no inter-frame decode at all): the cheapest whole-file sampler (~325x realtime)."""
    info = video_info(path)
    c = resolve_crop(crop, info["w"], info["h"])
    w, h = _out_size(info, c, size)
    args = ["-nostats", "-loglevel", "info", "-skip_frame", "nokey", *_hw(hw), "-i", str(path), "-map", "0:v:0",
            "-fps_mode", "passthrough", "-vf", _vf(c, (w, h) if size else None, None), "-pix_fmt", pix_fmt,
            "-f", "rawvideo", "-"]
    yield from _stream(args, w, h, _CHANNELS[pix_fmt], 0.0)


def at_times(path, times: Sequence[float], crop=None, size=None, pix_fmt: str = "rgb24", hw: Optional[str] = None,
             max_gap: float = 8.0) -> Iterator[Tuple[float, float, "np.ndarray"]]:
    """The frame showing each requested time, as (t_requested, t_pts, array), in time order.

    Times closer than max_gap share one decode window (one process, input-seek to the window start). The frame for t
    is the first whose pts >= t - 1 ms: ffmpeg's own `-ss t -frames:v 1` convention, so a grab here is bit-identical
    to the single-frame grabs every earlier script made (measured). Software decode by default: these are the frames
    people compare pixel by pixel."""
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
                if t is not None:
                    last = (t, img)
        for t_req in want:                     # past the end of the file: the last decoded frame
            if last is not None:
                yield t_req, last[0], last[1]


def save(path, times: Sequence[float], out_dir, *, fmt: str = "png", crop=None, size=None,
         hw: Optional[str] = None) -> dict:
    """Write the frame at each time to out_dir; returns the house result with a manifest
    [{t_requested, t_pts, crop, file}]."""
    from PIL import Image
    from . import receipt
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    stem = Path(path).stem
    for t_req, t_pts, img in at_times(path, times, crop=crop, size=size, pix_fmt="rgb24", hw=hw):
        name = out / f"{stem}_{t_req:010.3f}.{fmt}"
        Image.fromarray(img).save(name)
        rows.append({"t_requested": t_req, "t_pts": t_pts, "crop": list(crop) if crop else None, "file": str(name)})
    params = {"times": list(times), "fmt": fmt, "crop": crop, "size": size, "hw": hw}
    return receipt.result("grab", path, params, {"frames": rows, "out_dir": str(out)},
                          blind=["times past the end of the file return the last frame"])


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
