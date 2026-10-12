"""arsenal.media.shots -- easy scene detection: the cuts in a video, found on a small proxy copy.

Why it exists: arsenal.storyboard divides footage into still stretches and motion (right for pacing and piano takes)
but is not a cut detector, and a fixed ffmpeg `scene > 0.3` threshold finds a third of the cuts (F1 0.50). This makes
a 360p30 proxy once (cached as a catalog artifact), then scans it:

  detector "content"  PySceneDetect ContentDetector, threshold 27 (the default when scenedetect is installed)
  detector "spike"    ffmpeg's per-frame scene score + the house spike rule from analyze_video.py: a frame is a cut
                      when its score >= 0.30, or >= 0.12 AND >= 8x the median of the surrounding 2 s (a camera pan
                      lifts the whole neighbourhood, a hard cut is a one-frame spike); shots at least 0.25 s apart.
                      The fallback when scenedetect is absent; it needs nothing but ffmpeg and numpy.
  "auto"              content if scenedetect imports, else spike; the result names which one ran and why.
  clockmap=...        League footage: jumps in game time (studio.clockmap.v1 passes) are added as cuts with
                      source "clock"; pixel methods see a same-game jump as camera movement.

Measured 2026-10-12 on media-oracles/clips/synthetic2.mp4 (186 s, 8 OBS recordings, 40 hard cuts, 7 dissolves,
7 same-game cuts), scored with the research bench's matching (hard cuts +-0.25 s, dissolve centres +-0.8 s):
  spike on the 360p proxy   F1 0.844 (P 0.884, R 0.809; 2 of 7 dissolves, 3 of 7 same-game cuts); ~300x realtime
  content on the proxy      F1 0.851 (P 0.925, R 0.787) in the research venv that has scenedetect; 2.5 s
  arsenal storyboard        F1 0.711 as a cut detector (transition starts; 3.9 s): it is not one
  ffmpeg scdet's own score  is on another scale (max 0.19 here vs 0.49): the 0.30/0.12 rule assumes the scene score
On 1080p60 HEVC: the proxy took 6.7 s for 2 min and 95.8 s for the 33-min 17-51-11 (438 MB at CRF 23); the spike
scan of that proxy took 5.2 s warm, 8.3 s from a cold disk (390x / 245x realtime, 142 cuts: the replay's rewinds and
camera jumps), the same 5.2 s as the earlier log-file scan it replaced.
The truth file's hard-cut times drift from the frames by up to 5.6 frames (it sums the requested segment lengths,
not the frames the montage kept), so +-1 frame cannot be scored against it; frame accuracy is tested on a lavfi
montage built at test time, where every cut lands within one proxy frame.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import api, ff
from . import probe as probe_mod

PROXY_HEIGHT = 360
PROXY_FPS = 30
PROXY_GOP_S = 1.0
PROXY_CRF = 23               # at 26 ContentDetector lost a cut on synthetic2 (F1 0.837); 23 keeps 0.851
PROXY_S_PER_SOURCE_S = 0.05   # proxy cost per second of 1080p60 source: 6.7 s / 120 s and 95.8 s / 2028 s measured
PROXY_GPU_LOCK_S = 30.0       # a proxy expected to take longer than this holds the house GPU lock (d3d11va decode)

CONTENT_THRESHOLD = 27.0
SPIKE_THRESHOLD = 0.30
SPIKE_FLOOR = 0.12
SPIKE_RATIO = 8.0
SPIKE_HALF_WINDOW_S = 1.0
SPIKE_BASE_FLOOR = 0.004      # a frozen neighbourhood (median 0) must not make every speck a "spike"
SCORE_WIDTH = 320             # the spike rule's thresholds were tuned on scene scores at 320 px wide

CLOCK_JUMP_S = 1.0            # a pass boundary is a cut when game time jumps by more than this
CLOCK_MERGE_S = 0.5           # ... unless a pixel cut already sits this close
SHEET_MAX = 48                # one representative frame per shot, at most this many on the sheet

BLIND = [
    "a jump within the same League game looks like camera movement to pixel methods (they found 0-3 of 7); pass a "
    "clockmap to add those cuts",
    "dissolves: the spike rule and ContentDetector each find about 2 of 7 (TransNetV2 is v1)",
    "cut times come from the 30 fps proxy: within one proxy frame (33 ms) of the source's cut frame",
    "a one-frame flash (an ability, a muzzle flash) can read as a cut under the spike rule",
    "times are file times (seconds from the file's start, what ffmpeg's -ss means, the sidecar's keyframe clock); "
    "the scan itself counts from the first frame, which sits video_start_s into the file (0.021 s on an MPEG-TS "
    "whose sound is muxed ahead of the picture), and every pixel cut is moved by that much",
]


def _has_scenedetect() -> bool:
    import importlib.util
    return importlib.util.find_spec("scenedetect") is not None


# =================================================================================================
# proxy
# =================================================================================================

def _proxy_cost_s(sc: dict) -> float:
    """Expected proxy time: duration scaled by pixels and frame rate against 1080p60 (a 360p montage costs ~1 s and
    never waits for the GPU lock; a 33-minute 1080p60 recording costs ~100 s and takes it)."""
    v = sc.get("video") or {}
    scale = ((v.get("w") or 1920) * (v.get("h") or 1080)) / (1920 * 1080) * (v.get("fps") or 60) / 60
    return float(sc.get("duration_s") or 0.0) * scale * PROXY_S_PER_SOURCE_S


def proxy_path(media_id: str, height: int = PROXY_HEIGHT, fps: float = PROXY_FPS, gop_s: float = PROXY_GOP_S) -> Path:
    return ff.state_dir() / "proxy" / f"{media_id}-{height}p{fps:g}-g{gop_s:g}.mp4"


_target_locks: Dict[str, threading.Lock] = {}
_target_locks_guard = threading.Lock()


def _target_lock(target: Path) -> threading.Lock:
    """One encoder per proxy file in this process: the editor's threaded server or an MCP door asking twice for
    the same uncached proxy waits for the first encode instead of racing it (and holding a second heavy encode)."""
    key = os.path.normcase(str(target.resolve()))
    with _target_locks_guard:
        return _target_locks.setdefault(key, threading.Lock())


def _encode_proxy(src: Path, sc: dict, target: Path, height: int, fps: float, gop_s: float,
                  hw: Optional[str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{os.getpid()}-{threading.get_ident()}.tmp{target.suffix}")
    gop = max(1, int(round(gop_s * fps)))
    tail = ["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn",
            "-vf", f"scale=-2:{height}:flags=bilinear,fps={fps:g}", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", str(PROXY_CRF), "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", str(tmp)]
    gpu = "proxy" if hw and _proxy_cost_s(sc) > PROXY_GPU_LOCK_S else None
    try:
        try:
            ff.run((["-hwaccel", hw] if hw else []) + tail, gpu=gpu)
        except ff.MediaError:
            if not hw:
                raise
            ff.run(tail)                              # a codec the GPU decoder refuses: decode in software
        if not (target.is_file() and target.stat().st_size > 0):   # another process may have finished first
            probe_mod.retry_shared(lambda: os.replace(tmp, target))
    finally:
        if tmp.exists():
            tmp.unlink()


def proxy(src, *, height: int = PROXY_HEIGHT, fps: float = PROXY_FPS, gop_s: float = PROXY_GOP_S,
          hw: Optional[str] = "d3d11va", out=None) -> str:
    """A small analysis copy (video only, x264 ultrafast, a keyframe every gop_s), made once and cached: the next
    call returns the same file. 2 min of 1080p60 HEVC take ~6 s. Registered as a "proxy" artifact when the source is
    in the catalog. The editor's scrub proxy is a different thing (export preset proxy_edit)."""
    src = Path(src).resolve()
    sc = probe_mod.probe(src)
    if not sc.get("video"):
        raise ff.MediaError(f"{src.name} has no video stream to make a proxy of")
    if hw == "vulkan":
        raise ff.MediaError(ff.KNOWN_BAD["vulkan_hevc_decode"])
    target = Path(out) if out else proxy_path(sc["id"], height, fps, gop_s)
    params = {"height": height, "fps": fps, "gop_s": gop_s, "crf": PROXY_CRF, "codec": "libx264 ultrafast",
              "audio": False}
    with _target_lock(target):
        if not (target.is_file() and target.stat().st_size > 0):
            _encode_proxy(src, sc, target, height, fps, gop_s, hw)
    from . import catalog
    if catalog.is_cataloged(sc["id"]) and catalog.artifact(sc["id"], "proxy", params=params) is None:
        catalog.add_artifact(sc["id"], "proxy", target, params=params, api=api("shots"))
    return str(target)


# =================================================================================================
# detectors
# =================================================================================================

_PTS = re.compile(r"pts_time:([-0-9.]+)")
_SCORE = re.compile(r"lavfi\.scene_score=([0-9.]+)")


def scene_scores(video, *, width: int = SCORE_WIDTH) -> Tuple[List[float], List[float]]:
    """ffmpeg's scene-change score (0..1) of every frame, in one decode pass at `width` px. The metadata filter
    prints to ffmpeg's stdout (file=-), read line by line as it comes: a 33-minute scan never holds its log in
    memory, and no path enters the filtergraph (a state folder holding an apostrophe broke the earlier log file)."""
    vf = f"scale={width}:-2,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=-"
    times: List[float] = []
    scores: List[float] = []
    proc = ff.popen(["-nostats", "-v", "error", "-i", str(video), "-map", "0:v:0", "-an", "-vf", vf,
                     "-f", "null", "-"])
    try:
        t = None
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace")
            m = _PTS.search(line)
            if m:
                t = float(m.group(1))
                continue
            m = _SCORE.search(line)
            if m and t is not None:
                times.append(t)
                scores.append(float(m.group(1)))
    except BaseException:
        proc.kill()
        ff.finish(proc, check=False)
        raise
    ff.finish(proc)
    return times, scores


def spike_cuts(times: Sequence[float], scores: Sequence[float], *, threshold: float = SPIKE_THRESHOLD,
               floor: float = SPIKE_FLOOR, ratio: float = SPIKE_RATIO, half_window_s: float = SPIKE_HALF_WINDOW_S,
               min_shot_s: float = 0.25) -> List[dict]:
    """The house spike rule (analyze_video.detect_cuts, promoted): [{t, score, ratio}] in time order. Of two
    candidates closer than min_shot_s the stronger is kept (a flash, a 2-frame dissolve)."""
    import numpy as np
    t_arr, s_arr = np.asarray(times, float), np.asarray(scores, float)
    if len(s_arr) < 3:
        return []
    fps = 1.0 / max(float(np.median(np.diff(t_arr))), 1e-6)
    w = max(2, int(round(half_window_s * fps)))
    cuts: List[dict] = []
    for i in np.where(s_arr >= min(floor, threshold))[0]:
        if t_arr[i] <= t_arr[0]:
            continue
        lo, hi = max(0, i - w), min(len(s_arr), i + w + 1)
        nb = np.concatenate([s_arr[lo:max(lo, i - 1)], s_arr[min(hi, i + 2):hi]])   # the frame and its 2 neighbours out
        base = max(float(np.median(nb)) if len(nb) else 0.0, SPIKE_BASE_FLOOR)
        s = float(s_arr[i])
        if not (s >= threshold or s >= ratio * base):
            continue
        cut = {"t": round(float(t_arr[i]), 6), "score": round(s, 6), "ratio": round(s / base, 2)}
        if cuts and cut["t"] - cuts[-1]["t"] < min_shot_s:
            if s > cuts[-1]["score"]:
                cuts[-1] = cut
            continue
        cuts.append(cut)
    return cuts


def content_cuts(video, *, threshold: float = CONTENT_THRESHOLD, min_shot_s: float = 0.25,
                 fps: float = PROXY_FPS) -> List[dict]:
    """PySceneDetect ContentDetector (needs `scenedetect`): [{t, score: None}] at each new scene's first frame. The
    per-cut score would need a StatsManager, which made detection 2.6x slower (6.3 s against 2.5 s on synthetic2)."""
    from scenedetect import ContentDetector, SceneManager, open_video
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold, min_scene_len=max(1, int(round(min_shot_s * fps)))))
    sm.detect_scenes(open_video(str(video), backend="opencv"))

    def seconds(tc) -> float:              # 0.7 has the property; 0.6 only get_seconds()
        try:
            return float(tc.seconds)
        except AttributeError:
            return float(tc.get_seconds())
    return [{"t": round(seconds(start), 6), "score": None} for start, _end in sm.get_scene_list()[1:]]


def clock_cuts(clockmap) -> List[dict]:
    """Game-time jumps between consecutive passes of a studio.clockmap.v1 map (a dict or a path): each is a cut at
    the later pass's first file time. A speed change with continuous game time is not a cut."""
    cmap = json.loads(Path(clockmap).read_text(encoding="utf-8")) if isinstance(clockmap, (str, Path)) else clockmap
    passes = sorted((p for p in (cmap or {}).get("passes") or [] if p.get("file")), key=lambda p: p["file"][0])
    out = []
    for a, b in zip(passes, passes[1:]):
        t = float(b["file"][0])
        game_a = float(a.get("speed", 1.0)) * t + float(a.get("offset", 0.0))
        game_b = float(b.get("speed", 1.0)) * t + float(b.get("offset", 0.0))
        if abs(game_a - game_b) > CLOCK_JUMP_S:
            out.append({"t": round(t, 6), "score": None, "source": "clock", "pass": b.get("id"),
                        "jump_game_s": round(game_b - game_a, 3), "gap_s": round(t - float(a["file"][1]), 3)})
    return out


# =================================================================================================
# shots
# =================================================================================================

def _detector(detector: str) -> Tuple[str, Optional[str]]:
    if detector == "auto":
        if _has_scenedetect():
            return "content", None
        return "spike", "scenedetect is not installed: ran the spike rule (ffmpeg scene score) instead"
    if detector == "content" and not _has_scenedetect():
        raise ff.MediaError("detector 'content' needs the scenedetect package (Daniel's install); "
                            "use detector='spike' or 'auto'")
    if detector == "transnet":
        raise ff.MediaError("detector 'transnet' (TransNetV2) is v1 and not built yet; use 'auto' or 'spike'")
    if detector not in ("content", "spike"):
        raise ff.MediaError(f"unknown detector {detector!r}: auto, content or spike")
    return detector, None


def shots(src, *, detector: str = "auto", threshold: Optional[float] = None, min_shot_s: float = 0.25,
          use_proxy: bool = True, clockmap=None) -> dict:
    """The cuts and shots of a video: {"cuts": [{t, score, source}], "shots": [[t0, t1], ...], "detector_ran", ...}
    plus the house result keys. Times are file times (README, "The house clock"): seconds from the file's start,
    what ffmpeg's -ss means. start_s is where file time 0 sits on the container's own clock (1.4 s on an MPEG-TS, 0
    on OBS mp4) and video_start_s where the first frame sits in the file. A clock-map pass that starts outside the
    file makes no cut: it is listed in clock_cuts_dropped. When the file is in the catalog its shots are stored as
    "shot" spans (a re-run replaces them)."""
    from . import catalog, receipt
    src = Path(src).resolve()
    sc = probe_mod.probe(src)
    if not sc.get("video"):
        raise ff.MediaError(f"{src.name} has no video stream: nothing to cut")
    ran, why = _detector(detector)
    thr = threshold if threshold is not None else (CONTENT_THRESHOLD if ran == "content" else SPIKE_THRESHOLD)
    t0 = time.perf_counter()
    video = Path(proxy(src)) if use_proxy else src
    proxy_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    n_frames = None
    if ran == "content":
        fps = PROXY_FPS if use_proxy else (sc["video"].get("fps") or PROXY_FPS)
        cuts = [dict(c, source="content") for c in content_cuts(video, threshold=thr, min_shot_s=min_shot_s, fps=fps)]
    else:
        times, scores = scene_scores(video)
        n_frames = len(times)
        cuts = [dict(c, source="spike") for c in spike_cuts(times, scores, threshold=thr, min_shot_s=min_shot_s)]
    detect_s = time.perf_counter() - t1
    # Both scans count from the first frame: ffmpeg, reading v:0 alone, starts its output clock there when the
    # picture starts after the file does (the proxy is encoded that way too), and a scene list counts frames.
    origin = float((sc.get("video") or {}).get("start_s") or 0.0)
    if origin:
        cuts = [dict(c, t=round(c["t"] + origin, 6)) for c in cuts]
    duration = float(sc.get("duration_s") or 0.0)
    dropped: List[dict] = []
    if clockmap is not None:
        for c in clock_cuts(clockmap):
            if not 0.0 < c["t"] < duration:          # a pass outside the file: never an impossible cut
                dropped.append(c)
                continue
            near = [p for p in cuts if p["source"] != "clock" and abs(p["t"] - c["t"]) <= CLOCK_MERGE_S]
            if near:
                near[0]["clock"] = c.get("pass")
            else:
                cuts.append(c)
        cuts.sort(key=lambda c: c["t"])
    edges = [0.0] + [c["t"] for c in cuts if 0.0 < c["t"] < duration] + [duration]
    shot_list = [[round(a, 6), round(b, 6)] for a, b in zip(edges, edges[1:]) if b > a]
    params = {"detector": detector, "threshold": thr, "min_shot_s": min_shot_s, "use_proxy": use_proxy,
              "clockmap": None if clockmap is None else (str(clockmap) if isinstance(clockmap, (str, Path))
                                                          else "dict"),
              "proxy": {"height": PROXY_HEIGHT, "fps": PROXY_FPS, "gop_s": PROXY_GOP_S, "crf": PROXY_CRF},
              "spike": {"threshold": SPIKE_THRESHOLD, "floor": SPIKE_FLOOR, "ratio": SPIKE_RATIO,
                        "half_window_s": SPIKE_HALF_WINDOW_S, "score_width": SCORE_WIDTH},
              "content": {"threshold": CONTENT_THRESHOLD}}
    payload = {"cuts": cuts, "shots": shot_list, "detector_ran": ran, "fallback_reason": why,
               "proxy": str(video) if use_proxy else None, "frames_scored": n_frames, "duration_s": duration,
               "clock_cuts_dropped": dropped, "start_s": sc.get("start_s"),
               "video_start_s": (sc.get("video") or {}).get("start_s"),
               "timings": {"proxy_s": round(proxy_s, 3), "detect_s": round(detect_s, 3),
                           "realtime_x": round(duration / detect_s, 1) if detect_s > 0 else None}}
    if catalog.is_cataloged(sc["id"]):
        starts = {c["t"]: c for c in cuts}
        catalog.add_spans(sc["id"], "shot", [(a, b, None, {"cut": (starts.get(a) or {}).get("source"),
                                                           "score": (starts.get(a) or {}).get("score")})
                                             for a, b in shot_list], source=ran)
    src_dict = {"path": sc["path"], "size": sc["size"], "mtime_ns": sc["mtime_ns"], "id": sc["id"]}
    return receipt.result("shots", src_dict, params, payload, BLIND)


def sheet(res: dict, *, out=None, clock=None) -> Optional[str]:
    """One representative frame per shot (its middle, read from the proxy) on one labelled contact sheet via
    arsenal.media.sheet; None when that module is not built yet. clock: a clockmap, for game time in the labels."""
    try:
        from . import sheet as sheet_mod
    except ImportError:
        return None
    shots_ = res["shots"]
    if len(shots_) > SHEET_MAX:                     # sample evenly: one sheet stays one image read
        step = len(shots_) / SHEET_MAX
        shots_ = [shots_[int(i * step)] for i in range(SHEET_MAX)]
    video = res.get("proxy") or res["source"]["path"]
    items = [{"src": video, "t": (a + b) / 2, "label": f"shot {res['shots'].index([a, b]) + 1}  "
                                                      f"{int(a // 60)}:{a % 60:04.1f}"} for a, b in shots_]
    target = Path(out) if out else ff.state_dir() / "shots" / f"{res['source']['id']}-shots.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    made = sheet_mod.sheet(items, title=f"{Path(res['source']['path']).name}: {len(res['shots'])} shots "
                                        f"({res['detector_ran']})", out=str(target), clock=clock)
    return made.get("png") if isinstance(made, dict) else str(target)


# =================================================================================================
# CLI: py -m arsenal.media shots <src> [--detector auto|content|spike] [--sheet]
# =================================================================================================

def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media shots",
                                 description="scene detection: find the cuts/shots in a video on a 360p proxy "
                                             "(PySceneDetect ContentDetector, or ffmpeg's scene score + the spike "
                                             "rule); League clock jumps from a clockmap")
    ap.add_argument("video")
    ap.add_argument("--detector", choices=("auto", "content", "spike"), default="auto")
    ap.add_argument("--threshold", type=float, help=f"content: {CONTENT_THRESHOLD:g} (0-100); spike: "
                                                    f"{SPIKE_THRESHOLD:g} (0-1, the outright cut score)")
    ap.add_argument("--min-shot", type=float, default=0.25, help="shortest shot in seconds (default 0.25)")
    ap.add_argument("--no-proxy", action="store_true", help="scan the source itself (slow on long 1080p files)")
    ap.add_argument("--clockmap", help="a studio.clockmap.v1 file: game-time jumps become cuts")
    ap.add_argument("--sheet", action="store_true", help="one frame per shot on a labelled contact sheet")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = shots(a.video, detector=a.detector, threshold=a.threshold, min_shot_s=a.min_shot,
                use_proxy=not a.no_proxy, clockmap=a.clockmap)
    if a.sheet:
        res["sheet"] = sheet(res, clock=a.clockmap) or "(arsenal.media.sheet is not built yet)"
    if a.json:
        print(json.dumps(res, indent=1, default=str))
        return 0
    tm = res["timings"]
    print(f"{len(res['cuts'])} cuts, {len(res['shots'])} shots in {res['duration_s']:.1f} s  "
          f"(detector {res['detector_ran']}; proxy {tm['proxy_s']} s, detect {tm['detect_s']} s, "
          f"{tm['realtime_x']}x realtime)")
    if res["fallback_reason"]:
        print(f"  note: {res['fallback_reason']}")
    for c in res["clock_cuts_dropped"]:
        print(f"  dropped: clock pass {c.get('pass')} starts at {c['t']:.3f} s, outside this "
              f"{res['duration_s']:.3f} s file (is the clock map for another file?)")
    for c in res["cuts"]:
        score = "-" if c.get("score") is None else f"{c['score']:.3f}"
        print(f"  cut {int(c['t'] // 60)}:{c['t'] % 60:06.3f}  ({c['t']:.3f} s)  score {score}  {c['source']}")
    if a.sheet:
        print(f"sheet: {res['sheet']}")
    print(f"receipt: {res.get('receipt')}")
    return 0
