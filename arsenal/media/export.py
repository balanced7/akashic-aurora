"""arsenal.media.export -- one call makes the YouTube, Shorts, edit-proxy, archive or transparent version, checked.

Promoted from the studio's production-pipeline studio_export.py + export_presets.json (now presets.json beside this
file), with the studio's own fix: alpha_webp_anim is encoded with Pillow, because ffmpeg's animated WebP piles up
opacity on soft edges (alpha error 111 by frame 30, measured by the studio).

How a render runs:
  1. audio first, on its own: the chosen tracks (audio="0", "1,2", [1, 2] or {1: 0.0, 2: -6.0} for gains) are mixed
     over the same range and, when the preset has a loudness target, normalized by the measured two-pass loudnorm in
     audio.normalize_render, read back after the final codec and re-rendered once if it missed (AAC overshoots true
     peak by a few tenths of a dB). Proxies and mezzanines keep every track untouched instead, names and all.
  2. video once, with the finished audio stream-copied in: a miss never re-encodes the picture.
  3. qc on the output: stream inventory, exact frame count, duration to one frame, I within 0.5 LU of the target and
     true peak at or under it, and alpha present for the alpha presets. Problems are lines in the result, and the
     CLI exits 1.
Two inputs change the plan and say so in notes: audio that is digital silence is rendered without normalization
(and qc does not hold it to the target I), and a source narrower than a crop preset's window (a 540x1170 phone
recording into Shorts' 9:16) is padded instead of cropped. An unknown loudness key or an audio= that picks no track
is refused, as is alpha_webp_anim without Pillow (alpha_webm needs no Pillow).

Measured 2026-10-12 (presets.json keeps one `measured` row per preset): on a 10 s synthetic excerpt (1280x720p60
H.264 with a pink-noise mix at -54.9 LUFS, or 640x360p30 with a moving soft alpha) every preset met its loudness
target (-14.0 LUFS / -1.7 dBTP against -14 / -1.5), its exact frame count and its stream inventory; renders took
0.5 s (ProRes 4444) to 9.5 s (4K AMF) and 23.2 s for the 300-frame Pillow WebP (libwebp method 4). Pillow's WebP
kept alpha exact on all 300 frames where ffmpeg's libwebp was off by 249 at frame 30. On a real 10 s League clip
(-41.2 LUFS) shorts_1080x1920 landed at -14.1 / -1.6 dBTP after its first AAC render overshot to -1.4.
AMF encodes take the house GPU lock when the range is longer than 30 s (4K AMF ran at about 1x realtime).
"""
from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from . import audio as audio_mod
from . import ff, receipt

PRESETS_FILE = Path(__file__).with_name("presets.json")
GPU_LOCK_OVER_S = 30.0          # AMF encodes of longer ranges hold the house GPU lock
WEBP_FRAME_CAP_BYTES = 1 << 30  # the materialized fallback refuses more raw RGBA than this

_cache: Dict[str, object] = {}

AudioSpec = Union[str, int, Sequence[int], Dict[int, float]]


def presets() -> dict:
    """The preset file: {"loudness_targets": {...}, "presets": {name: {...}}, "_sources": {...}}."""
    stamp = PRESETS_FILE.stat().st_mtime_ns
    if _cache.get("stamp") != stamp:
        _cache["data"] = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        _cache["stamp"] = stamp
    return _cache["data"]          # type: ignore[return-value]


# =================================================================================================
# source facts and filters
# =================================================================================================

def _source(src) -> dict:
    j = ff.probe_json(src, entries=("-show_format", "-show_streams"))
    v = next((s for s in j.get("streams") or [] if s.get("codec_type") == "video"), None)
    if v is None:
        raise ff.MediaError(f"{Path(str(src)).name} has no video stream")
    tags = {k.lower(): val for k, val in (v.get("tags") or {}).items()}
    pix = str(v.get("pix_fmt") or "")
    vp9_alpha = v.get("codec_name") == "vp9" and str(tags.get("alpha_mode")) == "1"
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": audio_mod._fps(v), "codec": v.get("codec_name"),
            "pix_fmt": pix, "alpha": vp9_alpha or pix.startswith(_ALPHA_PIX),
            "decoder": ["-c:v", "libvpx-vp9"] if vp9_alpha else [],       # ffmpeg's own vp9 decoder drops alpha
            "duration": float((j.get("format") or {}).get("duration") or 0.0),
            "n_audio": sum(1 for s in j.get("streams") or [] if s.get("codec_type") == "audio")}


def _even(x: float) -> int:
    return max(2, int(round(x / 2.0)) * 2)


def _crop_fits(p: dict, info: dict) -> bool:
    """Does the preset's w:h window of the full source height fit inside the source's width?"""
    return int(info["h"] * int(p["width"]) / int(p["height"]) / 2) * 2 <= info["w"]


def out_geometry(p: dict, info: dict, crop_x: float = 0.5) -> dict:
    """{w, h, fps, vf, fit}: the output picture a preset makes from this source. A crop preset fed a source narrower
    than its window (a 9:19.5 phone recording into Shorts' 9:16) pads instead: the crop would ask for more width
    than the picture has, and ffmpeg fails the whole encode."""
    fit, fps = p["fit"], p["fps"]
    if fit == "crop" and not _crop_fits(p, info):
        fit = "pad"
    chain = []
    if fit == "pad":
        w, h = int(p["width"]), int(p["height"])
        chain += [f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos",
                  f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"]
    elif fit == "crop":
        w, h = int(p["width"]), int(p["height"])
        cw = f"trunc(ih*{w}/{h}/2)*2"      # widest w:h window of the full source height, placed by crop_x
        chain += [f"crop={cw}:ih:(iw-{cw})*{min(max(crop_x, 0.0), 1.0):.4f}:0", f"scale={w}:{h}:flags=lanczos"]
    elif fit == "scale":
        w = int(p["width"])
        h = _even(info["h"] * w / info["w"])
        chain.append(f"scale={w}:{h}:flags=lanczos")
    else:
        w, h = info["w"], info["h"]
    out_fps = float(fps) if isinstance(fps, (int, float)) else info["fps"]
    if isinstance(fps, (int, float)):
        chain.append(f"fps={fps}")
    if chain:
        chain.append("setsar=1")
    return {"w": w, "h": h, "fps": out_fps, "vf": ",".join(chain) or None, "fit": fit}


def _audio_pick(spec: AudioSpec, trs: List[dict], src) -> Dict[int, float]:
    """audio= as {a_index: gain_db}, refusing a spec that picks no track (it would render no audio bus)."""
    gains = (audio_mod._gain_map(spec, trs, src) if isinstance(spec, dict)
             else {i: 0.0 for i in audio_mod.pick(spec, trs, src)})
    if not gains:
        raise ff.MediaError(f"audio={spec!r} picks no track of {Path(str(src)).name} "
                            f"(it has {audio_mod._describe(trs)})")
    return gains


def _need_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise ff.MediaError("alpha_webp_anim needs Pillow (pip install pillow), which this Python lacks; "
                            "alpha_webm carries the same alpha without it") from None


def _trim(start: Optional[float], dur: float) -> List[str]:
    return (["-ss", f"{start:.6f}"] if start else []) + ["-t", f"{dur:.6f}"]


# =================================================================================================
# animated WebP via Pillow
# =================================================================================================

class _LazyFrame:
    """One frame of a running decode, pulled when Pillow's WebP writer seeks to it, so memory holds one frame at a
    time. Pillow's writer only asks a frame for n_frames, seek(), mode and getim() (11.x; `im` for older ones)."""

    n_frames = 1
    mode = "RGBA"

    def __init__(self, pull):
        self._pull = pull
        self._img = None

    def seek(self, idx: int) -> None:
        self._img = self._pull(self)

    def tell(self) -> int:
        return 0

    def load(self):
        return None

    def getim(self):
        return self._img.getim()

    @property
    def im(self):
        return self._img.im

    @property
    def size(self):
        return self._img.size


def _webp_args(src, info: dict, geo: dict, start: Optional[float], dur: float, n: int) -> List[str]:
    vf = f"{geo['vf']},tpad=stop_mode=clone:stop_duration=1"      # exactly n frames even if the range ends early
    return ["-v", "error", *info["decoder"], *_trim(start, dur), "-i", str(src), "-map", "0:v:0", "-vf", vf,
            "-frames:v", str(n), "-pix_fmt", "rgba", "-f", "rawvideo", "-"]


def webp_frames(src, info: dict, geo: dict, start: Optional[float], dur: float):
    """Yield the RGBA frames (PIL images) an alpha_webp_anim export encodes: the same decode the test compares."""
    from PIL import Image
    n = max(1, int(round(dur * geo["fps"])))
    proc = ff.popen(_webp_args(src, info, geo, start, dur, n))
    size = geo["w"] * geo["h"] * 4
    try:
        for _ in range(n):
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield Image.frombuffer("RGBA", (geo["w"], geo["h"]), buf, "raw", "RGBA", 0, 1)
    finally:
        ff.finish(proc, check=False)


def _encode_webp(src, out: Path, p: dict, info: dict, geo: dict, start: Optional[float], dur: float) -> dict:
    from PIL import Image  # noqa: F401  (Pillow is the encoder here)
    opts = dict(p.get("pillow") or {})
    n = max(1, int(round(dur * geo["fps"])))
    frame_ms = 1000.0 / geo["fps"]           # Pillow rounds the running sum, so n frames last exactly n/fps
    save_kw = {"save_all": True, "duration": frame_ms, "loop": int(opts.get("loop", 0)),
               "lossless": bool(opts.get("lossless", False)), "quality": int(opts.get("quality", 80)),
               "alpha_quality": int(opts.get("alpha_quality", 100)), "method": int(opts.get("method", 4)),
               "minimize_size": bool(opts.get("minimize_size", False))}
    for k in ("kmin", "kmax", "allow_mixed"):
        if k in opts:
            save_kw[k] = opts[k]
    gen = webp_frames(src, info, geo, start, dur)
    first = next(gen, None)
    if first is None:
        raise ff.MediaError(f"no frames decoded from {Path(str(src)).name} for the WebP export")
    state = {"last": None, "got": 1}

    def pull(frame: _LazyFrame):
        if state["last"] is not None:
            state["last"]._img = None          # drop the frame Pillow has already encoded
        img = next(gen, None)
        if img is None:
            raise ff.MediaError("the WebP decode ended before its frame count")
        state["last"], state["got"] = frame, state["got"] + 1
        return img

    t0 = time.perf_counter()
    mode = "lazy"
    try:
        first.save(out, format="WEBP", append_images=[_LazyFrame(pull) for _ in range(n - 1)], **save_kw)
        gen.close()                            # ends the decode process now, not at garbage collection
    except (AttributeError, TypeError):
        gen.close()                            # a Pillow whose writer wants more than the lazy frame offers
        if n * geo["w"] * geo["h"] * 4 > WEBP_FRAME_CAP_BYTES:
            raise ff.MediaError(f"animated WebP of {n} frames at {geo['w']}x{geo['h']} needs more than "
                                f"{WEBP_FRAME_CAP_BYTES >> 20} MB of frames on this Pillow; trim the range or use "
                                f"alpha_webm")
        frames = [im.copy() for im in webp_frames(src, info, geo, start, dur)]
        frames[0].save(out, format="WEBP", append_images=frames[1:], **save_kw)
        mode = "materialized"
    return {"frames": n, "frame_ms": frame_ms, "pillow": save_kw, "frame_source": mode,
            "encode_s": round(time.perf_counter() - t0, 3), "argv": ff.argv_for(_webp_args(src, info, geo, start,
                                                                                       dur, n))}


def _qc_webp(out: Path, geo: dict, dur: float, expect_alpha: bool) -> dict:
    from PIL import Image
    problems = []
    with Image.open(out) as im:
        n = getattr(im, "n_frames", 1)
        total_ms, alpha_min = 0, 255
        for k in range(n):
            im.seek(k)
            im.load()                          # Pillow fills info["duration"] on load, not on seek
            total_ms += int(im.info.get("duration", 0))
            if k in (0, n // 2, n - 1):
                alpha_min = min(alpha_min, im.convert("RGBA").getchannel("A").getextrema()[0])
        size, mode, loop = im.size, im.mode, im.info.get("loop")
    want_n = max(1, int(round(dur * geo["fps"])))
    if n != want_n:
        problems.append(f"WebP has {n} frames, expected {want_n}")
    if abs(total_ms / 1000.0 - dur) > 1.0 / geo["fps"] + 1e-6:
        problems.append(f"WebP lasts {total_ms / 1000.0:.3f} s, expected {dur:.3f} s within one frame")
    if size != (geo["w"], geo["h"]):
        problems.append(f"WebP is {size[0]}x{size[1]}, expected {geo['w']}x{geo['h']}")
    if expect_alpha and alpha_min == 255:
        problems.append("WebP came out fully opaque from a source with alpha")
    return {"ok": not problems, "problems": problems, "frames": n, "duration_s": total_ms / 1000.0,
            "size": list(size), "mode": mode, "loop": loop, "alpha_min_sampled": alpha_min}


# =================================================================================================
# export
# =================================================================================================

_ALPHA_PIX = ("yuva", "rgba", "argb", "bgra", "abgr", "gbrap", "ya8", "ya16")


def _alpha_problems(inv: dict, preset: str, src_alpha: bool) -> List[str]:
    """An alpha preset fed an alpha source must come out with alpha (ffprobe shows VP9 alpha only as a tag)."""
    if not (preset.startswith("alpha_") and src_alpha):
        return []
    v = next((s for s in inv["streams"] if s["type"] == "video"), None)
    if v is None:
        return ["no video stream to carry alpha"]
    if v["codec"] == "vp9":
        return [] if str(v.get("alpha_mode")) == "1" else ["VP9 output carries no alpha (alpha_mode tag missing)"]
    return [] if str(v.get("pix_fmt") or "").startswith(_ALPHA_PIX) else [f"{v['pix_fmt']} has no alpha plane"]


def export(src, preset: str, out, *, start: Optional[float] = None, end: Optional[float] = None,
           audio: AudioSpec = "0", crop_x: float = 0.5, loudness: Optional[str] = None, dry_run: bool = False,
           check: bool = True) -> dict:
    """Render src (or [start, end) of it) to a named preset with measured loudness and a QC receipt.

    audio: the a:N tracks to mix ("0", "1,2", [1, 2], track names, or {index: gain_db}); ignored by presets that keep
    every track (proxy_edit, mezzanine_dnxhr) or carry none (alpha_*). loudness overrides the preset's target key
    (youtube, shorts, vo_stem, none; anything else is refused). dry_run returns the plan (argv per step) without
    running anything. notes lists what changed the plan (silent audio not normalized, a narrow source padded)."""
    cfg = presets()
    if preset not in cfg["presets"]:
        raise ff.MediaError(f"unknown preset {preset!r}; have: {', '.join(cfg['presets'])}")
    p = dict(cfg["presets"][preset], name=preset)
    out = Path(out)
    info = _source(src)
    t0 = float(start or 0.0)
    t1 = float(end) if end is not None else info["duration"]
    if t0 < 0 or t1 <= t0 or t1 > info["duration"] + 1e-3:
        raise ff.MediaError(f"bad range [{start}, {end}) for a {info['duration']:.3f} s source: need "
                            f"0 <= start < end <= duration")
    dur = t1 - t0
    geo = out_geometry(p, info, crop_x)
    loud_key = loudness or p.get("loudness", "none")
    if loud_key not in cfg["loudness_targets"]:
        raise ff.MediaError(f"unknown loudness target {loud_key!r}; have: {', '.join(cfg['loudness_targets'])}")
    wants_audio = p.get("acodec") != ["-an"] and info["n_audio"] > 0
    target = cfg["loudness_targets"].get(loud_key) if wants_audio else None
    amf = any(str(a).endswith("_amf") for a in p.get("vcodec", []))
    gpu = f"export {preset}" if amf and dur > GPU_LOCK_OVER_S else None
    params = {"preset": preset, "start": start, "end": end, "audio": audio if not isinstance(audio, dict) else
              {str(k): v for k, v in audio.items()}, "crop_x": crop_x, "loudness": loud_key, "dry_run": dry_run,
              "check": check}
    blind = ["the QC reads the output back with ebur128; YouTube's own loudness reading can differ by a few tenths",
             "alpha presets need an alpha source (qtrle, ProRes 4444, PNG, VP9 alpha); a plain source exports opaque",
             "an AMF encode's quality depends on the driver; the receipt names the encoder, not the driver"]
    notes: List[str] = []
    if geo["fit"] != p["fit"]:
        notes.append(f"the source ({info['w']}x{info['h']}) is narrower than {geo['w']}:{geo['h']}: padded, not "
                     f"cropped")
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    if p.get("encoder") == "pillow":
        if dry_run:
            return receipt.result("export", src, params, {"plan": [ff.argv_for(_webp_args(
                src, info, geo, start, dur, max(1, int(round(dur * geo["fps"])))))], "out": str(out)}, blind=blind)
        _need_pillow()
        enc = _encode_webp(src, out, p, info, geo, start, dur)
        q = _qc_webp(out, geo, dur, info["alpha"]) if check else None
        payload = {"out": str(out), "geometry": geo, "webp": enc, "qc": q, "ok": (q or {"ok": True})["ok"],
                   "problems": (q or {}).get("problems", []), "notes": notes,
                   "seconds": round(time.perf_counter() - started, 3), "bytes": out.stat().st_size}
        return receipt.result("export", src, params, payload, blind=blind, engine={"pillow": _pillow_version()})

    trs = audio_mod.tracks(src) if wants_audio else []
    steps: List[dict] = []
    tmp_audio: Optional[Path] = None          # the mixed, normalized audio, stream-copied into the video pass
    a_inputs: List[str] = []
    a_graph = ""
    inputs = [*info["decoder"], *_trim(start, dur), "-i", str(src)]
    maps: List[str] = []
    graph = f"[0:v:0]{geo['vf']}[vout]" if geo["vf"] else None
    maps += ["-map", "[vout]"] if graph else ["-map", "0:v:0"]
    a_args: List[str] = []
    n_audio_out = 0
    titles: List[str] = []
    if wants_audio and p.get("keep_all_audio"):
        maps += ["-map", "0:a?"]
        a_args = list(p["acodec"])
        for t in trs:
            a_args += [f"-metadata:s:a:{t['index']}", f"title={t['house_name']}"]   # MP4 drops names otherwise
        n_audio_out = len(trs)
        titles = [t["house_name"] for t in trs]
    elif wants_audio:
        gains = _audio_pick(audio, trs, src)
        plan = [{"src": str(src), "start": t0, "end": t1, "dur": dur, "at": 0.0, "tracks": list(gains),
                 "muted": [], "gains_db": gains, "fade_in_s": 0.0, "fade_out_s": 0.0}]
        a_inputs, a_graph = audio_mod.mix_graph(plan)
        ext = ".m4a" if "aac" in p["acodec"] else ".mka"
        tmp_dir = ff.state_dir() / "export" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_audio = tmp_dir / f"{out.stem}.{os.getpid()}.{uuid.uuid4().hex[:12]}{ext}"   # unique per call, any thread
        inputs += ["-i", str(tmp_audio)]
        maps += ["-map", "1:a:0"]
        a_args = ["-c:a", "copy"]
        n_audio_out = 1
    vargs = ["-y", "-nostats", *inputs, *(["-filter_complex", graph] if graph else []), *maps, *p["vcodec"],
             *(a_args or ["-an"])]
    if p.get("faststart"):
        vargs += ["-movflags", "+faststart"]
    vargs.append(str(out))
    if dry_run:
        if tmp_audio is not None:
            steps.append({"step": "audio", "argv": ff.argv_for(["-y", *a_inputs, "-filter_complex", a_graph, "-map",
                                                                "[mix]", *p["acodec"], str(tmp_audio)]),
                          "note": "with a loudness target this runs as loudnorm pass 1 + pass 2 + read-back"})
        steps.append({"step": "video", "argv": ff.argv_for(vargs), "gpu_lock": gpu})
        return receipt.result("export", src, params, {"plan": steps, "out": str(out), "geometry": geo, "notes": notes},
                              blind=blind)
    normalized = bool(target)
    try:
        if tmp_audio is not None:
            done = audio_mod.normalize_render(a_inputs, a_graph, "mix", tmp_audio, list(p["acodec"]), target=target)
            steps.append({"step": "audio", "argv": done["argv"], "loudnorm": done["pass1"],
                          "attempts": done["attempts"], "normalized": done["normalized"], "notes": done["notes"]})
            normalized = done["normalized"]
            notes += done["notes"]
        tv = time.perf_counter()
        res = ff.run(vargs, gpu=gpu)
        steps.append({"step": "video", "argv": res.args, "gpu_lock": gpu,
                      "seconds": round(time.perf_counter() - tv, 3)})
    finally:
        if tmp_audio is not None:
            with contextlib.suppress(OSError):       # never mask the render's own error with a cleanup one
                tmp_audio.unlink()
    q, problems = None, []
    if check:
        expect = {"video_streams": 1, "audio_streams": n_audio_out, "duration_s": dur,
                  "frames": int(round(dur * geo["fps"])), "w": geo["w"], "h": geo["h"]}
        if target:
            expect["TP_max"] = target["TP"]
            if normalized:                            # digital silence stays at -70 LUFS: no I to hold it to
                expect.update(I=target["I"], I_tol=0.5)
        if titles:
            expect["titles"] = titles
        q = audio_mod.qc(out, expect=expect, video=False)
        problems = list(q["problems"]) + _alpha_problems({"streams": q["streams"]}, preset, info["alpha"])
    payload = {"out": str(out), "geometry": geo, "steps": steps, "target": target,
               "normalized": normalized if target else None,
               "qc": {k: q[k] for k in ("ok", "problems", "I", "TP", "LRA", "duration_s", "streams", "receipt")}
               if q else None, "ok": not problems, "problems": problems, "notes": notes,
               "seconds": round(time.perf_counter() - started, 3), "bytes": out.stat().st_size}
    return receipt.result("export", src, params, payload, blind=blind)


def _pillow_version() -> str:
    try:
        import PIL
        return PIL.__version__
    except ImportError:
        return "missing"


# =================================================================================================
# CLI: py -m arsenal.media export <preset> <src> <out> [--start --end --audio 0,1 --crop-x --loudness --dry-run]
# =================================================================================================

def cli(verb: str, argv: List[str]) -> int:
    import argparse
    from .frames import parse_time
    names = ", ".join(presets()["presets"])
    ap = argparse.ArgumentParser(prog="py -m arsenal.media export",
                                 description=f"export with platform presets and a loudness QC receipt ({names})")
    ap.add_argument("preset", nargs="?")
    ap.add_argument("src", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--list", action="store_true", help="list the presets and loudness targets")
    ap.add_argument("--start", help="s or m:ss")
    ap.add_argument("--end", help="s or m:ss")
    ap.add_argument("--audio", default="0", help="a:N tracks to mix, e.g. 0 or 1,2 or Voice,Game; gains as 1:0,2:-6")
    ap.add_argument("--crop-x", type=float, default=0.5, help="Shorts crop position 0 (left) .. 1 (right)")
    ap.add_argument("--loudness", help="override the preset's target: youtube, shorts, vo_stem, none")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.list or not (a.preset and a.src and a.out):
        cfg = presets()
        for name, p in cfg["presets"].items():
            print(f"{name:20s} {p.get('width')}x{p.get('height')} @ {p.get('fps')}  loudness={p.get('loudness')}  "
                  f"{p.get('container')}")
        print("targets: " + json.dumps(cfg["loudness_targets"]))
        return 0 if a.list else 2
    audio_spec: AudioSpec = a.audio
    if ":" in a.audio:
        audio_spec = {k: float(v) for k, v in (part.split(":") for part in a.audio.split(","))}
    res = export(a.src, a.preset, a.out, start=parse_time(a.start) if a.start else None,
                 end=parse_time(a.end) if a.end else None, audio=audio_spec, crop_x=a.crop_x, loudness=a.loudness,
                 dry_run=a.dry_run)
    keys = ("plan", "out") if a.dry_run else ("out", "ok", "problems", "qc", "seconds", "bytes", "receipt")
    print(json.dumps({k: res.get(k) for k in keys}, indent=2, default=str))
    return 0 if a.dry_run or res.get("ok") else 1
