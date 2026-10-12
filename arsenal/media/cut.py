"""arsenal.media.cut -- trim to the exact frame, re-encoding only the head; every audio track and its name come along.

OBS puts a keyframe every 4.17 s (250 frames at 60 fps) and a plain `-c copy` trim can only start on one, so a
"lossless trim" starts up to 4.17 s early (ffmpeg hides about 1.5 s of that pre-roll behind an MP4 edit list that
not every player honours). Three modes:

  copy   snap to the keyframe at or before start, copy every packet, report the real start. Lossless.
  smart  re-encode only the head [start, next keyframe) on the GPU (hevc_amf / h264_amf, CQP 18), stream-copy the
         rest bit for bit, join both as one Annex-B stream (parameter sets in band, so the encoder change mid-stream
         is legal) and mux it with the audio packets copied. Falls back to exact, and says so, for B-frames, a
         variable frame rate or a codec without a smart path.
  exact  re-encode the whole range (same codec, CQP 18; holds the house GPU lock when estimated over 30 s).

The first frame is the one frames.at_times(start) shows (the first whose time >= start - 1 ms). Every time here is a
file time (README, "The house clock"): seconds from the file's start, what ffmpeg's `-ss` means and what
probe.keyframes reports; facts() converts ffprobe's container times at the edge by subtracting the format start_time
(1.4 s on an MPEG-TS; 0 on the OBS MP4/MKV files), and frame k of the source sits at the video's first file time +
k / fps. The one place a container time comes back is verify's -copyts decode, whose trim bounds add the format start
back. `-seek_timestamp 1` is not a shortcut: on the house build it moves the demuxer seek but the accurate-seek trim
still adds the format start (measured 2026-10-12: `-ss 2.5` on a TS gave the frame at 3.905 s).
Every audio track is kept with its title written explicitly (`-metadata:s:a:N title=`: a
copy-remux into MP4 drops track names otherwise); audio packets keep their source timing, so only a partial first
packet (up to 20 ms Opus, 21 ms AAC) is left out. Only the video travels as raw Annex-B, pumped through pipes into
the muxer: no intermediate file is written and memory stays at one 1 MiB chunk.

plan() is what the editor's trim handles call to show the cost; keyframes and stream facts are cached per
(path, size, mtime) under <state>/cut/facts/.

Promoted from the outside-tools smartcut.py with its two bugs kept fixed: no -shortest (raw Annex-B has no timestamps
and -shortest silently ended the audio at 0), and frame indices count from the video's start_time (a non-zero
start_time shifted every frame).

Measured 2026-10-12 on "2026-10-11 17-51-11.mp4" (33 min, 1080p60 HEVC, keyframes every 4.17 s), two runs, the
second with other builders loading the machine:
  601.5-612.0 s smart: 630 frames, 0 decode errors, head PSNR 50.8 dB (lowest of the 160 head frames 49.9),
    470/470 copied frames bit-identical, 1.07-1.23 s (verify 2.0-2.9 s); two more smart cuts: head PSNR 50.9, 52.3 dB
  600.0-605.0 s (on a keyframe): copy, 300 frames bit-identical, 0.10-0.12 s; a 120 s copy 0.39-0.43 s, its verify
    2.9 s (it decoded the whole output, 12.0 s, before verify sampled long outputs)
  exact: 224 frames/s (software decode + AMF encode; 20 s of 1080p60 in 5.35 s)
  plan(): median 0.5 ms over 50 calls with the facts in memory, 0.6 ms from the disk cache; the first look at a
    file (ffprobe + keyframe scan) 0.9-1.4 s
  audio: within 1 ms of the source in every mode and container (cross-correlated noise tracks, synthetic files;
    an MPEG-TS with a 1.4 s format start included: -0.7/+0.3 ms, where the seeks before the fix put it 1.4 s off)

verify picks the frames it compares by their own pts, so it does not share a seek error with the cut it checks:
on that TS the unfixed cut started 2.000 s late in every mode and the frame-counting verify still said ok.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from . import ff, probe, receipt

MODES = ("copy", "smart", "exact")
CONTAINERS = (".mp4", ".mkv", ".mov", ".m4v")
#: codec -> (encoders, best first; Annex-B bitstream filter; raw muxer/demuxer name)
CODECS = {"hevc": (("hevc_amf", "libx265"), "hevc_mp4toannexb", "hevc"),
          "h264": (("h264_amf", "libx264"), "h264_mp4toannexb", "h264")}
HEAD_QP = 18
COMPARE_MAX = 1800              # verify compares every frame up to this many, then head + tail samples
SAMPLE = 300                    # frames per sample when the output is longer than COMPARE_MAX
GPU_LOCK_AFTER_S = 30.0         # an encode estimated longer than this holds the house GPU lock
PSNR_FLOOR_DB = 30.0            # a re-encoded frame below this is not the frame it replaces (CQP 18 measures 48-52)
_CHUNK = 1 << 20
_FACTS_VERSION = 3              # 2: format_start; 3: every time on the file clock

#: The wall-time model behind est_s, fitted 2026-10-12 on the 33-min 1080p60 HEVC OBS recording (per-frame terms
#: scale with pixels relative to 1080p): copy 120 s = 0.43 s; smart 10.5 s (160-frame head) = 1.07 s, smart 119 s =
#: 1.60 s; exact 20 s = 5.35 s (224 fps: software decode + AMF encode). verify_est_s: 326 / 630 frames (every frame
#: decoded three times) 1.71 / 2.04 s; 7200 frames (sampled: 600-760 frames decoded for errors, 600 compared) 2.94 s
#: copy, 3.58 s smart.
COST = {"copy_base_s": 0.08, "smart_base_s": 0.75, "exact_base_s": 0.30, "head_fps": 450.0, "exact_fps": 224.0,
        "copy_bytes_per_s": 350e6, "verify_base_s": 1.3, "verify_decode_fps": 2700.0, "verify_s_per_frame": 1.3e-4}


# =================================================================================================
# facts: video stream, audio tracks, keyframes -- cached per (path, size, mtime)
# =================================================================================================

_memo: Dict[tuple, dict] = {}


def _tag(tags: dict, *names: str) -> Optional[str]:
    low = {k.lower(): v for k, v in (tags or {}).items()}
    for n in names:
        if low.get(n):
            return str(low[n])
    return None


def _fraction(text) -> Fraction:
    num, _, den = str(text or "0/1").partition("/")
    try:
        return Fraction(int(num), int(den or 1)) if int(den or 1) else Fraction(0)
    except ValueError:
        return Fraction(float(text)).limit_denominator(1001)


def _duration(stream: dict) -> float:
    """A stream's duration; MKV keeps it only as a DURATION tag (00:00:03.761000000)."""
    if stream.get("duration") not in (None, "N/A"):
        return float(stream["duration"])
    tag = _tag(stream.get("tags"), "duration")
    if tag and re.match(r"^\d+:\d+:\d+(\.\d+)?$", tag):
        h, m, sec = tag.split(":")
        return int(h) * 3600 + int(m) * 60 + float(sec)
    return 0.0


def _read_facts(path: Path) -> dict:
    j = ff.probe_json(path, entries=("-show_format", "-show_streams"))
    streams = j.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not (s.get("disposition") or {}).get("attached_pic")), None)
    if v is None:
        raise ff.MediaError(f"no video stream in {path}: cut trims video files (audio-only cuts are not built)")
    avg = _fraction(v.get("avg_frame_rate"))
    rfps = _fraction(v.get("r_frame_rate"))
    # r_frame_rate is exact for a constant-rate file (60/1); avg drifts with a remux's rounding (480000/7999)
    vfr = bool(rfps and avg and abs(float(rfps) - float(avg)) > 0.01 * float(rfps))
    fps = avg if (vfr or not rfps) else rfps
    fmt = j.get("format") or {}
    f0 = float(fmt.get("start_time") or 0.0)           # the container's own start: file time 0
    v_start = float(v.get("start_time") or f0) - f0
    v_dur = _duration(v) or float(fmt.get("duration") or 0.0)
    audio = []
    for s in streams:
        if s.get("codec_type") != "audio":
            continue
        audio.append({"a_index": len(audio), "index": s["index"], "codec": s.get("codec_name"),
                      "channels": s.get("channels"), "sample_rate": int(s.get("sample_rate") or 0),
                      "title": _tag(s.get("tags"), "title", "name"),
                      "start": float(s.get("start_time") or f0) - f0, "duration": _duration(s)})
    video = {"index": v["index"], "codec": v.get("codec_name"), "w": int(v.get("width") or 0),
             "h": int(v.get("height") or 0), "fps": f"{fps.numerator}/{fps.denominator}",
             "vfr": vfr,
             "has_b_frames": int(v.get("has_b_frames") or 0), "pix_fmt": v.get("pix_fmt"),
             "profile": v.get("profile"), "start": v_start, "duration": v_dur,
             "color": {k: v.get(k) for k in ("color_range", "color_space", "color_transfer", "color_primaries")},
             "bit_rate": int(v.get("bit_rate") or fmt.get("bit_rate") or 0)}
    return {"video": video, "audio": audio, "container": fmt.get("format_name"),
            "format_start": f0, "duration": float(fmt.get("duration") or v_dur)}


def _facts_file(key: tuple) -> Path:
    h = hashlib.sha1(repr(key).encode("utf-8")).hexdigest()[:20]
    return ff.state_dir() / "cut" / "facts" / f"{h}.json"


def facts(src, *, refresh: bool = False, cache: bool = True) -> dict:
    """{source, video, audio, keyframes, ...} of one file: one ffprobe + the packet-flag keyframe scan, remembered in
    memory and on disk per (path, size, mtime) so the editor's trim handles never wait on a 2.4 GB file twice. Every
    time is a file time; format_start says where file time 0 sits on the container's clock.
    cache=False reads fresh and remembers nothing (verify and concat use it for the outputs they check)."""
    p = Path(src).resolve()
    try:
        st = p.stat()
    except OSError as exc:
        raise ff.MediaError(f"cannot read {src}: {exc.strerror or exc}") from exc
    key = (str(p), st.st_size, st.st_mtime_ns, _FACTS_VERSION)
    if cache and not refresh and key in _memo:
        return _memo[key]
    cache_file = _facts_file(key)
    got = None
    if cache and not refresh:
        try:
            got = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            got = None
        if got and got.get("key") != list(key):
            got = None
    if got is None:
        got = _read_facts(p)
        got["keyframes"] = probe.keyframes(p, stream=0)
        got["source"] = receipt.source(p)
        got["key"] = list(key)
        if cache:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_file.with_name(f"{cache_file.name}.{os.getpid()}.tmp")
                with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(got, fh)
                os.replace(tmp, cache_file)
            except OSError:
                pass
    if not got["keyframes"]:
        raise ff.MediaError(f"no keyframes found in {src}: the container index is unreadable")
    if cache:
        if len(_memo) > 64:
            _memo.clear()
        _memo[key] = got
    return got


# =================================================================================================
# frame arithmetic: frame k of the source sits at the video's first file time + k / fps
# =================================================================================================

def _fps(f: dict) -> Fraction:
    return _fraction(f["video"]["fps"])


def _index(t: float, f: dict) -> int:
    """The index of the frame whose pts is t (a keyframe, a real start)."""
    return int(round((t - f["video"]["start"]) * _fps(f)))


def _first_at(t: float, f: dict) -> int:
    """The first frame whose pts >= t - 1 ms: frames.at_times' convention (ffmpeg's `-ss t -frames:v 1`), so a cut
    starts on exactly the frame a grab or a sheet cell at t shows. The 1 ms also absorbs MKV's ms-rounded pts."""
    return int(math.ceil((t - f["video"]["start"] - 1e-3) * _fps(f) - 1e-9))


def _time(k: int, f: dict) -> float:
    return f["video"]["start"] + k / float(_fps(f))


def _n_frames(f: dict) -> int:
    return int(round(f["video"]["duration"] * _fps(f)))


def _keyframe_at_or_before(f: dict, t: float) -> float:
    half = 0.5 / float(_fps(f))
    kfs = f["keyframes"]
    cands = [k for k in kfs if k <= t + half]
    return cands[-1] if cands else kfs[0]


def _keyframe_after(f: dict, t: float) -> Optional[float]:
    half = 0.5 / float(_fps(f))
    return next((k for k in f["keyframes"] if k > t + half), None)


def _ss(f: dict, t: float) -> str:
    """A file time as ffmpeg's input `-ss` takes it: the same number (-ss counts from the format start_time)."""
    return f"{max(0.0, t):.6f}"


def _seek(f: dict, keyframe: float) -> List[str]:
    """Input-seek args that land exactly on `keyframe` (with -noaccurate_seek): a quarter frame past it, so ffprobe's
    6-decimal rounding of the keyframe's time can never make the demuxer pick the keyframe before. Nothing when it is
    the first one."""
    if keyframe <= f["keyframes"][0] + 1e-6:
        return []
    return ["-ss", _ss(f, keyframe + 0.25 / float(_fps(f)))]


# =================================================================================================
# plan
# =================================================================================================

_has_encoder: Dict[tuple, bool] = {}


def _encoder(codec: str) -> Optional[str]:
    """The best encoder this ffmpeg has for codec (AMF first), remembered per binary: plan() runs on every drag."""
    binary = ff.ffmpeg()
    for name in CODECS.get(codec, ((), None, None))[0]:
        key = (binary, name)
        if key not in _has_encoder:
            _has_encoder[key] = ff.has_encoder(name)
        if _has_encoder[key]:
            return name
    return None


def _raw_ok(f: dict) -> bool:
    """Can the video travel as a raw Annex-B stream with rebuilt timestamps (no B-frames, constant rate)?"""
    v = f["video"]
    return v["codec"] in CODECS and not v["has_b_frames"] and not v["vfr"]


def _smart_blocker(f: dict, encoder: Optional[str]) -> Optional[str]:
    v = f["video"]
    if v["codec"] not in CODECS:
        return f"codec {v['codec']} has no smart path (hevc and h264 do)"
    if v["has_b_frames"]:
        return f"the source has B-frames (has_b_frames={v['has_b_frames']}): a head cannot be spliced in front"
    if v["vfr"]:
        return "the source has a variable frame rate: smart and copy rebuild timestamps at a constant rate"
    if v["pix_fmt"] not in ("yuv420p", "nv12", "yuvj420p", "p010le", "yuv420p10le"):
        return f"pixel format {v['pix_fmt']} is not one the head encoder writes"
    if encoder is None:
        return f"no encoder for {v['codec']} in this ffmpeg build"
    return None


def _range(f: dict, start: float, end: float) -> tuple:
    """(fs, fe): the output holds source frames [fs, fe). Refuses a range outside the video."""
    if not (end > start):
        raise ff.MediaError(f"bad range: end {end} must be after start {start}")
    v = f["video"]
    n = _n_frames(f)
    fs, fe = max(0, _first_at(start, f)), _first_at(end, f)
    if start < -1e-3 or fs >= n:
        raise ff.MediaError(f"bad range: start {start} s lies outside the video ({v['start']:.3f}-"
                            f"{_time(n, f):.3f} s)")
    if fe > n + 1:
        raise ff.MediaError(f"bad range: end {end} s is past the end of the video ({_time(n, f):.3f} s)")
    fe = min(fe, n)
    if fe <= fs:
        raise ff.MediaError(f"bad range: {start}-{end} s holds no whole frame at {float(_fps(f)):g} fps")
    return fs, fe


def _est(f: dict, mode: str, *, encode: int = 0, copy_frames: int = 0) -> float:
    v = f["video"]
    px = max(0.05, v["w"] * v["h"] / (1920 * 1080))
    copy_s = v["bit_rate"] / 8.0 * copy_frames / (float(_fps(f)) or 30.0) / COST["copy_bytes_per_s"]
    if mode == "copy":
        return round(COST["copy_base_s"] + copy_s, 2)
    if mode == "smart":
        return round(COST["smart_base_s"] + encode * px / COST["head_fps"] + copy_s, 2)
    return round(COST["exact_base_s"] + encode * px / COST["exact_fps"], 2)


def _verify_est(f: dict, frames: int, copied_from: Optional[int]) -> float:
    """verify()'s wall time: the decode-error pass over its windows plus the PSNR pass (output and source)."""
    v = f["video"]
    px = max(0.05, v["w"] * v["h"] / (1920 * 1080))
    decoded = sum(c for _, c in _windows(frames, copied_from, COMPARE_MAX))
    decoded += 2 * (frames if frames <= COMPARE_MAX else 2 * SAMPLE)
    return round(COST["verify_base_s"] + decoded * px / COST["verify_decode_fps"]
                 + frames * COST["verify_s_per_frame"], 2)


def _plan(f: dict, start: float, end: float) -> dict:
    fps = _fps(f)
    fs, fe = _range(f, start, end)
    t_first = _time(fs, f)
    k0 = _keyframe_at_or_before(f, t_first)
    k0f = _index(k0, f)
    k1 = _keyframe_after(f, t_first)
    k1f = _index(k1, f) if k1 is not None else None
    on_key = k0f == fs
    encoder = _encoder(f["video"]["codec"]) or _encoder("h264")
    blocker = _smart_blocker(f, _encoder(f["video"]["codec"]))
    reasons: List[str] = []
    copy_frames = fe - k0f
    modes = {
        "copy": {"start_real": round(k0, 6), "early_s": round(t_first - k0, 6), "frames": copy_frames,
                 "lossless": True, "est_s": _est(f, "copy", copy_frames=copy_frames)},
        "exact": {"start_real": round(t_first, 6), "frames": fe - fs, "lossless": False,
                  "head_frames": fe - fs, "est_s": _est(f, "exact", encode=fe - fs)},
    }
    if on_key:
        head = 0
    elif k1f is None or k1f >= fe:
        head = fe - fs
    else:
        head = k1f - fs
    if not blocker:
        modes["smart"] = {"start_real": round(t_first, 6), "frames": fe - fs, "lossless": head == 0,
                          "head_frames": head, "copied_frames": fe - fs - head,
                          "est_s": _est(f, "smart", encode=head, copy_frames=fe - fs - head)}
    if on_key:
        suggested = "copy"
        reasons.append("start lies on a keyframe: a copy is frame-exact and lossless")
    elif blocker:
        suggested = "exact"
        reasons.append(f"smart is not possible: {blocker}")
    elif head == fe - fs:
        suggested = "exact"
        reasons.append("no keyframe inside the range: the whole range is the head, so it is re-encoded")
    else:
        suggested = "smart"
        reasons.append(f"start is {t_first - k0:.3f} s after the keyframe at {k0:.3f} s: re-encode "
                       f"{head} frames ({head / float(fps):.3f} s) up to the keyframe at {k1:.3f} s, copy the rest")
    head_s = {"copy": 0.0, "exact": (fe - fs) / float(fps), "smart": head / float(fps)}[suggested]
    est = modes[suggested]["est_s"]
    verify_est = _verify_est(f, modes[suggested]["frames"], {"copy": 0, "smart": head, "exact": None}[suggested])
    gpu = suggested == "exact" and est > GPU_LOCK_AFTER_S
    if gpu:
        reasons.append(f"the encode is estimated over {GPU_LOCK_AFTER_S:.0f} s: it will hold the house GPU lock")
    return {"mode_suggested": suggested, "start": start, "end": end, "first_frame": fs, "end_frame": fe,
            "frames": fe - fs, "start_real": modes[suggested]["start_real"], "start_keyframe": round(k0, 6),
            "next_keyframe": None if k1 is None else round(k1, 6), "on_keyframe": on_key,
            "head_reencode_s": round(head_s, 6), "est_s": est, "verify_est_s": verify_est,
            "encoder": encoder if suggested != "copy" else None,
            "gpu_lock": gpu, "smart_blocker": blocker, "modes": modes, "reasons": reasons,
            "fps": f["video"]["fps"], "keyint_s": _keyint(f)}


def _keyint(f: dict) -> Optional[float]:
    k = f["keyframes"]
    if len(k) < 2:
        return None
    gaps = sorted(b - a for a, b in zip(k, k[1:]))
    return round(gaps[len(gaps) // 2], 6)


_PLAN_BLIND = ["est_s (the cut) and verify_est_s (verify=True adds it) are a model calibrated on one machine "
               "(cut.COST), not a measurement of this call",
               "a variable-frame-rate file is detected by r_frame_rate != avg_frame_rate only"]


def plan(src, start: float, end: float) -> dict:
    """What a trim of [start, end) (file seconds) will cost, without cutting: the suggested mode, the keyframe at or
    before start, how much head is re-encoded, an estimated wall time for the cut and for its verify, and the
    reasons. Fast on a cached file."""
    f = facts(src)
    p = _plan(f, float(start), float(end))
    # no receipt: the editor asks on every trim-handle rest, and a plan changes nothing on disk
    return receipt.result("cut", f["source"], {"start": float(start), "end": float(end), "plan": True}, p,
                          _PLAN_BLIND, write_receipt=False)


# =================================================================================================
# cut
# =================================================================================================

def _tracks(f: dict, tracks) -> List[dict]:
    audio = f["audio"]
    if tracks in (None, "all"):
        return list(audio)
    if tracks in ("none", ()):
        return []
    want = [int(t) for t in (tracks.split(",") if isinstance(tracks, str) else tracks)]
    names = ", ".join(f"{a['a_index']} {a['title'] or '(untitled)'!r}" for a in audio) or "none"
    for t in want:
        if not 0 <= t < len(audio):
            raise ff.MediaError(f"missing audio track {t}: the source has {len(audio)} ({names})")
    return [audio[t] for t in want]


def _audio_args(sel: List[dict], input_no: int) -> List[str]:
    args: List[str] = []
    for a in sel:
        args += ["-map", f"{input_no}:a:{a['a_index']}"]
    if sel:
        args += ["-c:a", "copy", "-copypriorss:a", "0"]
    for i, a in enumerate(sel):
        args += [f"-metadata:s:a:{i}", f"title={a['title'] or ''}"]
    return args


def _encode_args(f: dict, encoder: str) -> List[str]:
    v = f["video"]
    if encoder.endswith("_amf"):
        args = ["-c:v", encoder, "-quality", "quality", "-rc", "cqp", "-qp_i", str(HEAD_QP), "-qp_p", str(HEAD_QP)]
    elif encoder == "libx265":
        args = ["-c:v", encoder, "-crf", str(HEAD_QP - 2), "-preset", "fast", "-x265-params", "bframes=0:log-level=1"]
    else:
        args = ["-c:v", encoder, "-crf", str(HEAD_QP - 2), "-preset", "fast"]
    args += ["-bf", "0", "-g", "9999"]
    pix = v["pix_fmt"] if v["pix_fmt"] in ("yuv420p", "p010le", "yuv420p10le") else "yuv420p"
    args += ["-pix_fmt", pix]
    c = v["color"]
    for opt, key in (("-color_range", "color_range"), ("-colorspace", "color_space"),
                     ("-color_trc", "color_transfer"), ("-color_primaries", "color_primaries")):
        if c.get(key) and c[key] not in ("unknown", "reserved"):
            args += [opt, c[key]]
    return args


def _video_tag(codec: str, container: str) -> List[str]:
    """hev1: parameter sets may sit in band, which the spliced head needs (hvc1 promises they never change)."""
    if container in (".mp4", ".mov", ".m4v") and codec == "hevc":
        return ["-tag:v", "hev1"]
    return []


def _default_out(src: Path, start: float, end: float, mode: str) -> Path:
    ext = src.suffix.lower() if src.suffix.lower() in CONTAINERS else ".mkv"
    return ff.state_dir() / "cut" / f"{src.stem}_{start:09.3f}-{end:09.3f}_{mode}{ext}"


def _check_out(src: Path, out: Path) -> str:
    container = out.suffix.lower()
    if container not in CONTAINERS:
        raise ff.MediaError(f"cut writes {', '.join(CONTAINERS)}; got {out.name!r}")
    if out.resolve() == src.resolve():
        raise ff.MediaError("out is the source file: originals are never touched")
    out.parent.mkdir(parents=True, exist_ok=True)
    return container


def _pump(producers: Sequence[tuple], consumer: List[str]) -> List[List[str]]:
    """Run each (args, gpu label or None) producer in turn, one heavy process at a time, and stream its stdout into
    the consumer's stdin."""
    argvs: List[List[str]] = []
    cons = ff.popen(consumer, stdin=subprocess.PIPE)
    argvs.append(cons.arsenal_argv)          # type: ignore[attr-defined]
    broken = False
    try:
        for args, gpu in producers:
            prod = ff.popen(args, gpu=gpu)
            argvs.append(prod.arsenal_argv)  # type: ignore[attr-defined]
            try:
                for chunk in iter(lambda: prod.stdout.read(_CHUNK), b""):
                    if broken:
                        continue
                    try:
                        cons.stdin.write(chunk)
                    except (BrokenPipeError, OSError):
                        broken = True        # the muxer stopped reading (it reached -t): drain and finish
            finally:
                ff.finish(prod, check=not broken, timeout=None)
        try:
            cons.stdin.close()
        except OSError:
            pass
    except BaseException:
        if cons.poll() is None:
            cons.kill()
        ff.finish(cons, check=False)
        raise
    ff.finish(cons, timeout=None)
    return argvs


def _run_spliced(f: dict, src: Path, out: Path, container: str, fs: int, fe: int, head: int, encoder: Optional[str],
                 sel: List[dict], start_from: int) -> List[List[str]]:
    """copy (head == 0, start_from = keyframe frame) and smart: raw Annex-B video through a pipe, audio from src."""
    v = f["video"]
    codec = v["codec"]
    _encoders, bsf, raw = CODECS[codec]
    fps = v["fps"]
    producers = []
    first = start_from
    if head:
        k0 = _keyframe_at_or_before(f, _time(fs, f))
        k0f = _index(k0, f)
        # a head is at most one keyframe interval (OBS: 250 frames, ~0.5 s of AMF): the lock only for a huge GOP
        gpu = "cut smart head" if _est(f, "exact", encode=head) > GPU_LOCK_AFTER_S else None
        producers.append((["-v", "error", "-noaccurate_seek", *_seek(f, k0), "-i", str(src), "-map", "0:v:0",
                           "-vf", f"trim=start_frame={fs - k0f}:end_frame={fs + head - k0f},setpts=PTS-STARTPTS",
                           *_encode_args(f, encoder), "-bsf:v", bsf, "-f", raw, "pipe:1"], gpu))
        first = fs + head
    if fe > first:
        producers.append((["-v", "error", *_seek(f, _time(first, f)), "-i", str(src), "-map", "0:v:0",
                           "-frames:v", str(fe - first), "-c:v", "copy", "-bsf:v", bsf, "-f", raw, "pipe:1"], None))
    t_a = _time(start_from if not head else fs, f)
    n = fe - (start_from if not head else fs)
    dur = n / float(_fraction(fps))
    consumer = ["-v", "error", "-y", "-fflags", "+genpts", "-r", fps, "-f", raw, "-i", "pipe:0"]
    if sel:
        consumer += ["-ss", _ss(f, t_a), "-t", f"{dur + 0.1:.6f}", "-i", str(src)]
    consumer += ["-map", "0:v:0", "-c:v", "copy", *_video_tag(codec, container)]
    consumer += _audio_args(sel, 1)
    consumer += ["-map_metadata", "1" if sel else "-1", "-map_chapters", "-1", "-t", f"{dur:.6f}", str(out)]
    return _pump(producers, consumer)


def _run_exact(f: dict, src: Path, out: Path, container: str, fs: int, fe: int, encoder: str,
               sel: List[dict]) -> List[List[str]]:
    v = f["video"]
    k0 = _keyframe_at_or_before(f, _time(fs, f))
    k0f = _index(k0, f)
    dur = (fe - fs) / float(_fps(f))
    args = ["-v", "error", "-y", "-noaccurate_seek", *_seek(f, k0), "-i", str(src)]
    if sel:
        args += ["-ss", _ss(f, _time(fs, f)), "-t", f"{dur + 0.1:.6f}", "-i", str(src)]
    args += ["-map", "0:v:0", "-vf", f"trim=start_frame={fs - k0f}:end_frame={fe - k0f},setpts=PTS-STARTPTS",
             *_encode_args(f, encoder)]
    args += _audio_args(sel, 1)
    args += ["-map_metadata", "1" if sel else "-1", "-map_chapters", "-1", "-t", f"{dur:.6f}", str(out)]
    long = _est(f, "exact", encode=fe - fs) > GPU_LOCK_AFTER_S
    ff.run(args, gpu="cut exact" if long else None)
    return [ff.argv_for(args)]


def _run_copy_remux(f: dict, src: Path, out: Path, container: str, k0: float, fe: int,
                    sel: List[dict]) -> List[List[str]]:
    """copy for sources the raw path cannot carry (B-frames, other codecs): a container-level copy from the keyframe."""
    dur = _time(fe, f) - k0
    args = ["-v", "error", "-y", *_seek(f, k0), "-i", str(src), "-map", "0:v:0", "-c:v", "copy"]
    args += _audio_args(sel, 0)
    args += ["-t", f"{dur:.6f}", "-avoid_negative_ts", "make_zero", "-map_chapters", "-1", str(out)]
    ff.run(args)
    return [ff.argv_for(args)]


_CUT_BLIND = [
    "audio is copied packet by packet: it is accurate to one packet (20 ms Opus, 21 ms AAC), never resampled",
    "no fades at the cut points: the 30 ms join fades belong to the EDL renderer",
    "chapters and subtitle/data streams are not carried",
    "the re-encoded head (smart) or range (exact) is CQP 18: visually lossless, not bit-identical",
]


def cut(src, start: float, end: float, out=None, *, mode: str = "smart", tracks: Union[str, Sequence[int]] = "all",
        verify: bool = True, preset: Optional[str] = None) -> dict:
    """Trim [start, end) (file seconds) into out (.mp4, .mkv or .mov). Returns the house result: the mode that ran,
    the real start, frame counts, the audio tracks kept, the argv of every process and, with verify=True, verify()."""
    if mode not in MODES:
        raise ff.MediaError(f"unknown mode {mode!r}: {', '.join(MODES)}")
    if preset is not None:
        raise ff.MediaError("preset: export presets are not wired into cut yet; leave preset=None (the house "
                            "intermediate: same codec, CQP 18)")
    t0 = time.perf_counter()
    srcp = Path(src)
    f = facts(srcp)
    p = _plan(f, float(start), float(end))
    fs, fe = p["first_frame"], p["end_frame"]
    sel = _tracks(f, tracks)
    outp = Path(out) if out else _default_out(srcp, float(start), float(end), mode)
    container = _check_out(srcp, outp)
    reasons: List[str] = []
    ran = mode
    if mode == "smart":
        if p["on_keyframe"]:
            ran = "copy"
            reasons.append("start lies on a keyframe: copied (frame-exact and lossless)")
        elif p["smart_blocker"] or p["mode_suggested"] == "exact":
            ran = "exact"
            reasons.append("smart fell back to exact: " + (p["smart_blocker"] or "no keyframe inside the range"))
    encoder = _encoder(f["video"]["codec"]) or _encoder("h264")
    head = 0
    tolerance = 0
    start_real = _time(fs, f)
    if ran == "copy":
        k0 = p["start_keyframe"]
        start_real = k0
        if not _raw_ok(f):
            tolerance = f["video"]["has_b_frames"] + 1
            argvs = _run_copy_remux(f, srcp, outp, container, k0, fe, sel)
            reasons.append("copied at container level (B-frames or a codec without a raw path): the end is "
                           "accurate to the packet, not guaranteed to the frame")
        else:
            argvs = _run_spliced(f, srcp, outp, container, fs, fe, 0, None, sel, _index(k0, f))
        if k0 < _time(fs, f) - 1e-6:
            reasons.append(f"copy starts on the keyframe at {k0:.3f} s, {_time(fs, f) - k0:.3f} s before the "
                           f"requested start")
    elif ran == "smart":
        head = p["modes"]["smart"]["head_frames"]
        argvs = _run_spliced(f, srcp, outp, container, fs, fe, head, encoder, sel, fs)
    else:
        if encoder is None:
            raise ff.MediaError("exact: this ffmpeg build has no h264/hevc encoder")
        head = fe - fs
        argvs = _run_exact(f, srcp, outp, container, fs, fe, encoder, sel)
    wall = round(time.perf_counter() - t0, 3)
    first = _index(start_real, f)
    payload = {"out": str(outp), "mode": ran, "mode_requested": mode, "start_real": round(start_real, 6),
               "end_real": round(_time(fe, f), 6), "frames": fe - first, "head_frames": head,
               "copied_frames": (fe - first - head) if ran != "exact" else 0,
               "encoder": encoder if ran != "copy" else None,
               "audio": [{"a_index": a["a_index"], "title": a["title"], "codec": a["codec"]} for a in sel],
               "reasons": reasons, "wall_s": wall, "plan": p, "argv": argvs}
    if verify:
        copied_from = {"copy": 0, "smart": head, "exact": None}[ran]
        v = _verify(srcp, start_real, _time(fe, f), outp, tracks=tracks, copied_from=copied_from,
                    frames_tolerance=tolerance, write_receipt=False)
        payload["verify"] = {k: v[k] for k in v if k not in ("api", "source", "params", "computed_with", "blind",
                                                             "receipt")}
        payload["verify_wall_s"] = v["wall_s"]
    params = {"start": float(start), "end": float(end), "out": str(outp), "mode": mode,
              "tracks": tracks if isinstance(tracks, str) else list(tracks), "verify": verify, "preset": preset,
              "head_qp": HEAD_QP}
    return receipt.result("cut", f["source"], params, payload, _CUT_BLIND)


# =================================================================================================
# verify
# =================================================================================================

_PSNR_LINE = re.compile(r"n:(\d+).*?mse_avg:([0-9.]+|inf).*?psnr_avg:([0-9.]+|inf)")


def _window(f: dict, k_first: int, count: int) -> tuple:
    """(seek args, trim filter) that decode frames [k_first, k_first + count) of a file. The frames are picked by
    their own pts (the command runs with -copyts), never by counting from where the seek landed: a cut that started
    on the wrong frame is then compared against the right one, not against the same wrong one. -copyts hands the
    filters container pts, so the file times get the format start added back (-start_at_zero is no substitute: it
    subtracts the start of the streams read, measured 1.421 s against the format's 1.4 on an MPEG-TS)."""
    kf = _keyframe_at_or_before(f, _time(k_first, f))
    fps = _fps(f)
    f0 = f.get("format_start", 0.0)
    # a quarter frame early: trim rounds its bounds to the stream's ticks, and on a 1/fps timebase a half-frame
    # margin is a rounding tie (1234.558333 s * 60 = 74073.49998 kept the frame before; measured on the recording)
    q = 0.25 / float(fps)
    # pts = frame index on a 1/fps timebase: ms-rounded (MKV) and exact (MP4) timestamps then pair frame for frame
    return (["-noaccurate_seek", *_seek(f, kf)],
            f"trim=start={_time(k_first, f) - q + f0:.6f}:end={_time(k_first + count, f) - q + f0:.6f},"
            f"settb={fps.denominator}/{fps.numerator},setpts=N")


def _psnr_frames(src: Path, fsrc: dict, src_first: int, out: Path, fout: dict, out_first: int,
                 count: int) -> List[tuple]:
    """Per-frame (out index, mse, psnr dB) of out frames [out_first, +count) against source frames
    [src_first, +count), both decoded in software."""
    o_seek, o_trim = _window(fout, out_first, count)
    s_seek, s_trim = _window(fsrc, src_first, count)
    graph = f"[0:v]{o_trim}[a];[1:v]{s_trim}[b];[a][b]psnr=stats_file=-"
    res = ff.run(["-v", "error", "-copyts", *o_seek, "-i", str(out), *s_seek, "-i", str(src), "-lavfi", graph,
                  "-f", "null", "-"])
    rows = []
    for line in res.stdout.splitlines():
        m = _PSNR_LINE.search(line)
        if m:
            mse = float(m.group(2))
            rows.append((out_first + int(m.group(1)) - 1, mse, float("inf") if m.group(3) == "inf"
                         else float(m.group(3))))
    return rows


def _count_frames(path: Path) -> int:
    res = ff.run(["-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                  "stream=nb_read_packets", "-of", "csv=p=0", str(path)], tool="ffprobe")
    try:
        return int(res.stdout.strip().split(",")[0])
    except ValueError:
        return 0


def _db(x: float) -> Optional[float]:
    return None if x is None else ("inf" if x == float("inf") else round(x, 2))


def _windows(n: int, copied_from: Optional[int], compare_max: int) -> List[tuple]:
    """(first, count) output windows that verify decodes: all n frames up to compare_max; past that the head
    through SAMPLE frames after the splice, and the last SAMPLE frames (the middle is the source's own packets)."""
    if n <= compare_max:
        return [(0, n)] if n > 0 else []
    head_end = min(n, (copied_from or 0) + SAMPLE)
    tail = max(head_end, n - SAMPLE)
    return [(0, head_end)] + ([(tail, n - tail)] if n > tail else [])


def _decode_errors(path: Path, f: dict, windows: Sequence[tuple], n_total: int) -> List[str]:
    """ffmpeg's error lines from decoding the video and every audio track over each (first frame, count) window."""
    errors: List[str] = []
    for first, count in windows:
        span: List[str] = []
        if (first, count) != (0, n_total):
            kf = _keyframe_at_or_before(f, _time(first, f))
            dur = (first + count - _index(kf, f) + 1) / float(_fps(f))
            span = ["-noaccurate_seek", *_seek(f, kf), "-t", f"{dur:.6f}"]
        res = ff.run(["-v", "error", *span, "-i", str(path), "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"],
                     check=False)
        errors += [ln for ln in res.stderr.splitlines() if ln.strip()]
    return errors


def verify(src, start: float, end: float, out, *, tracks: Union[str, Sequence[int]] = "all",
           copied_from: Union[int, str, None] = "auto", compare_max: int = COMPARE_MAX,
           frames_tolerance: int = 0, psnr_floor_db: float = PSNR_FLOOR_DB) -> dict:
    """Check a cut against its source: frame count, decode errors, per-frame PSNR of the first and last frames,
    whether the copied frames are bit-identical (mse 0 in software decode), and every audio track and its title.
    Written as a receipt.

    start is the source time of the output's first frame (the real start a copy cut reports). copied_from is the
    output frame index from which frames should be bit copies: "auto" infers it from the keyframes (0 on a
    keyframe, else the next keyframe), None means nothing was copied (exact). frames_tolerance is how many frames
    the count may miss by and still be ok (a container-level copy of a B-frame source ends on a packet). A
    re-encoded frame under psnr_floor_db is a different frame, not a lossy copy of the right one."""
    return _verify(src, start, end, out, tracks=tracks, copied_from=copied_from, compare_max=compare_max,
                   frames_tolerance=frames_tolerance, psnr_floor_db=psnr_floor_db, write_receipt=True)


def _verify(src, start: float, end: float, out, *, tracks, copied_from, compare_max: int = COMPARE_MAX,
            frames_tolerance: int = 0, psnr_floor_db: float = PSNR_FLOOR_DB, write_receipt: bool) -> dict:
    """verify(); cut() embeds the result in its own receipt (and its `verify` flag shadows the public name)."""
    t0 = time.perf_counter()
    srcp, outp = Path(src), Path(out)
    fsrc = facts(srcp)
    fout = facts(outp, cache=False)
    fs, fe = _range(fsrc, float(start), float(end))
    expected = fe - fs
    n_out = _count_frames(outp)
    if copied_from == "auto":
        k1 = _keyframe_after(fsrc, _time(fs, fsrc))
        copied_from = 0 if _index(_keyframe_at_or_before(fsrc, _time(fs, fsrc)), fsrc) == fs else (
            None if k1 is None or _index(k1, fsrc) >= fe else _index(k1, fsrc) - fs)
    n = min(n_out, expected)
    windows = _windows(n_out, copied_from, compare_max)
    errors = _decode_errors(outp, fout, windows, n_out)
    rows: List[tuple] = []
    want_compared = 0
    if n > 0:
        if n <= compare_max:
            rows = _psnr_frames(srcp, fsrc, fs, outp, fout, 0, n)
            want_compared = n
        else:
            rows = _psnr_frames(srcp, fsrc, fs, outp, fout, 0, SAMPLE)
            rows += _psnr_frames(srcp, fsrc, fs + n - SAMPLE, outp, fout, n - SAMPLE, SAMPLE)
            want_compared = len(set(range(SAMPLE)) | set(range(n - SAMPLE, n)))
    by_index = {i: (mse, db) for i, mse, db in rows if 0 <= i < n}
    copied = [i for i in by_index if copied_from is not None and i >= copied_from]
    identical = [i for i in copied if by_index[i][0] == 0.0]
    head = [by_index[i][1] for i in by_index if copied_from is None or i < copied_from]
    sel = _tracks(fsrc, tracks)
    out_audio = fout["audio"]
    want_titles = [a["title"] for a in sel]
    got_titles = [a["title"] for a in out_audio]
    v_start = fout["video"]["start"]
    payload = {
        "frames_expected": expected, "frames_out": n_out, "frames_compared": len(by_index),
        "frames_compared_expected": want_compared,
        "decode_errors": len(errors), "decode_error_lines": errors[:5],
        "decode_checked": [list(w) for w in windows], "decode_checked_frames": sum(c for _, c in windows),
        "head_psnr_db": _db(by_index[0][1]) if 0 in by_index else None,
        "tail_psnr_db": _db(by_index[n - 1][1]) if (n - 1) in by_index else None,
        "head_min_psnr_db": _db(min(head)) if head else None,
        "copied_from": copied_from, "copied_compared": len(copied), "copied_identical": len(identical),
        "copied_identical_sample": (len(identical) == len(copied)) if copied else None,
        "audio_streams_in": len(sel), "audio_streams_out": len(out_audio),
        "titles_in": want_titles, "titles_out": got_titles, "titles_kept": want_titles == got_titles,
        "audio_start_offset_ms": [round((a["start"] - v_start) * 1000, 1) for a in out_audio],
        "audio_duration_s": [round(a["duration"], 3) for a in out_audio],
        "video_duration_s": round(fout["video"]["duration"], 3),
        "ok": (abs(n_out - expected) <= frames_tolerance and not errors and want_titles == got_titles
               and len(out_audio) == len(sel) and len(by_index) == want_compared
               and (not head or min(head) >= psnr_floor_db)
               and (not copied or len(identical) == len(copied))),
        "wall_s": round(time.perf_counter() - t0, 3),
    }
    blind = ["PSNR and identity are measured on software-decoded frames; a player's hardware decode may differ by a "
             "few luma levels",
             f"outputs longer than {compare_max} frames are compared, and decoded for errors, on the first and last "
             f"{SAMPLE} frames (plus the re-encoded head) only",
             f"a re-encoded frame is only checked against the {psnr_floor_db:g} dB floor: on a still scene the frame "
             f"next to the right one can score above it"]
    params = {"start": float(start), "end": float(end), "out": str(outp),
              "tracks": tracks if isinstance(tracks, str) else list(tracks), "copied_from": copied_from,
              "compare_max": compare_max, "frames_tolerance": frames_tolerance, "psnr_floor_db": psnr_floor_db}
    return receipt.result("cut", fsrc["source"], params, payload, blind, write_receipt=write_receipt)


# =================================================================================================
# concat
# =================================================================================================

def _signature(f: dict) -> dict:
    v = f["video"]
    return {"video": [v["codec"], v["w"], v["h"], v["pix_fmt"], v["fps"]],
            "audio": [[a["codec"], a["sample_rate"], a["channels"]] for a in f["audio"]]}


def _concat_line(p: Path) -> str:
    return "file '" + str(p.resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n"


def concat(parts: Sequence, out=None, *, verify_decode: bool = True) -> dict:
    """Join cuts end to end without re-encoding (the concat demuxer). Refuses parts whose codec, size, pixel format,
    frame rate or audio layout differ, naming the first mismatch."""
    if len(parts) < 2:
        raise ff.MediaError("concat needs at least two parts")
    t0 = time.perf_counter()
    paths = [Path(p) for p in parts]
    infos = [facts(p) for p in paths]
    sig0 = _signature(infos[0])
    for p, info in zip(paths[1:], infos[1:]):
        sig = _signature(info)
        for key in ("video", "audio"):
            if sig[key] != sig0[key]:
                raise ff.MediaError(f"concat refuses {p.name}: its {key} {sig[key]} differs from {paths[0].name}'s "
                                    f"{sig0[key]}; re-encode it with cut(mode='exact') first")
    outp = Path(out) if out else ff.state_dir() / "cut" / f"{paths[0].stem}_concat{len(paths)}{paths[0].suffix}"
    container = outp.suffix.lower()
    if container not in CONTAINERS:
        raise ff.MediaError(f"concat writes {', '.join(CONTAINERS)}; got {outp.name!r}")
    if any(outp.resolve() == p.resolve() for p in paths):
        raise ff.MediaError("out is one of the parts: parts are never overwritten")
    outp.parent.mkdir(parents=True, exist_ok=True)
    titles = [a["title"] for a in infos[0]["audio"]]
    with tempfile.TemporaryDirectory(prefix="arsenal-concat-") as td:
        lst = Path(td) / "parts.ffconcat"
        with open(lst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("ffconcat version 1.0\n")
            for p in paths:
                fh.write(_concat_line(p))
        args = ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-map", "0:v:0", "-map", "0:a?",
                "-c", "copy", *_video_tag(infos[0]["video"]["codec"], container)]
        for i, t in enumerate(titles):
            args += [f"-metadata:s:a:{i}", f"title={t or ''}"]
        args += [str(outp)]
        ff.run(args)
    expected = sum(_count_frames(p) for p in paths)
    n_out = _count_frames(outp)
    errors: List[str] = []
    if verify_decode:
        dec = ff.run(["-v", "error", "-i", str(outp), "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"],
                     check=False)
        errors = [ln for ln in dec.stderr.splitlines() if ln.strip()]
    fout = facts(outp, cache=False)
    payload = {"out": str(outp), "parts": [str(p) for p in paths], "frames_expected": expected, "frames_out": n_out,
               "decode_errors": len(errors) if verify_decode else None, "decode_error_lines": errors[:5],
               "titles_out": [a["title"] for a in fout["audio"]], "titles_kept": [a["title"] for a in
                                                                                  fout["audio"]] == titles,
               "duration_s": round(fout["duration"], 3), "wall_s": round(time.perf_counter() - t0, 3),
               "argv": [ff.argv_for(args)]}
    blind = ["no fades or crossfades at the joins (the EDL renderer owns those)",
             "parts with different parameter sets need them in band (hev1, as cut writes); an hvc1 part from "
             "another encoder can fail to decode after the join"]
    return receipt.result("cut", [str(p) for p in paths], {"parts": [str(p) for p in paths], "out": str(outp),
                                                           "verify_decode": verify_decode, "op": "concat"},
                          payload, blind)


# =================================================================================================
# CLI: py -m arsenal.media cut <src> <start> <end> [<out>] [--mode smart] [--plan] [--tracks 0,2] [--no-verify]
#      py -m arsenal.media cut --concat <part> <part> ... --out <out>
# =================================================================================================

def cli(verb: str, argv: List[str]) -> int:
    import argparse
    from .frames import parse_time
    ap = argparse.ArgumentParser(prog="py -m arsenal.media cut",
                                 description="trim/cut a video to the exact frame: copy (lossless, from the keyframe), "
                                             "smart (re-encode only the head, copy the rest) or exact; keeps every "
                                             "audio track and its name; --plan shows the cost without cutting")
    ap.add_argument("src", nargs="?")
    ap.add_argument("start", nargs="?", help="seconds or m:ss(.fff) from the file's start")
    ap.add_argument("end", nargs="?", help="seconds or m:ss(.fff) from the file's start")
    ap.add_argument("out", nargs="?", help=".mp4/.mkv/.mov (default <state>/cut/...)")
    ap.add_argument("--mode", default="smart", choices=MODES)
    ap.add_argument("--plan", action="store_true", help="show the cost and the suggested mode, cut nothing")
    ap.add_argument("--tracks", default="all", help="audio tracks to keep: all, none, or 0,2 (a:N indices)")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--concat", nargs="+", metavar="PART", help="join these parts without re-encoding")
    ap.add_argument("--out", dest="out_opt", help="output path (for --concat)")
    ap.add_argument("--json", action="store_true", help="print the whole result")
    a = ap.parse_args(argv)
    if a.concat:
        res = concat(a.concat, a.out_opt)
    else:
        if not (a.src and a.start and a.end):
            ap.error("give <src> <start> <end> [<out>], or --concat")
        start, end = parse_time(a.start), parse_time(a.end)
        if a.plan:
            res = plan(a.src, start, end)
        else:
            res = cut(a.src, start, end, a.out or a.out_opt, mode=a.mode, tracks=a.tracks, verify=not a.no_verify)
    if a.json:
        print(json.dumps(res, indent=2, default=str))
        return 0
    keep = ("mode_suggested", "start_real", "start_keyframe", "next_keyframe", "head_reencode_s", "est_s",
            "verify_est_s", "reasons",
            "out", "mode", "frames", "head_frames", "copied_frames", "audio", "wall_s", "frames_expected",
            "frames_out", "decode_errors", "titles_kept", "receipt")
    view = {k: res[k] for k in keep if k in res}
    if "verify" in res:
        view["verify"] = {k: res["verify"][k] for k in ("ok", "frames_expected", "frames_out", "decode_errors",
                                                         "head_psnr_db", "copied_identical_sample", "titles_kept")}
    print(json.dumps(view, indent=2, default=str))
    return 0 if res.get("verify", {}).get("ok", True) else 1
