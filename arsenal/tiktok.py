"""TikTok-ready copies of screen recordings: cut the borders, trim the silence, 1080x1920.

OBS records the whole screen; the /piano canvas is a strip in the middle with black around it (plus
a cursor and the narrow CARDS tab). This verb finds the lit box by reading pixels, trims the silence
before the first note and after the last, and encodes a phone-friendly MP4: H.264 High 8-bit 4:2:0,
AAC 256k 48 kHz stereo, loudness-normalised, index at the front (+faststart).

No ffprobe, numpy or Pillow: duration, fps, size and streams come from parsing ``ffmpeg -i`` stderr,
and pixels come from ffmpeg piping raw grey frames into pure Python.

--from/--to confine the copy to a window of the recording (a 30-minute take whose keeper is at the
end; TikTok stops at 10 minutes). The box is sampled, the silence trimmed and the loudness measured
inside the window only; a copy that starts inside sound fades in, one that ends inside sound fades
out, and the window goes into the output name ('<stem> tiktok 28-52-end.mp4').

Two layers. Pure functions (ffmpeg discovery order, stderr parsing, box detection, aspect math,
silence math, time parsing, naming, command building) that the tests drive directly; and a thin
run layer (``process``/``run_cli``) that calls ffmpeg and prints the report.

Known limits (documented, not fixed):
  - a recording that is not fullscreen, with a full-width taskbar across it, has no quiet border
    (the taskbar lights whole rows to the frame's edges), so nothing is cropped;
  - the box is a per-coordinate median over the sample frames, so when most samples catch a partly
    drawn canvas (mid-transition), the box can follow that partial canvas;
  - the sparse-edge trim (EDGE_SPARSE) can cut up to EDGE_TRIM of the frame off a canvas whose outer
    strip is pure black, because those lines look like a cursor or tab touching the canvas.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple

TARGET_W, TARGET_H = 1080, 1920
VIDEO_SUFFIXES = (".mp4", ".mkv", ".mov")
OUTPUT_TAG = " tiktok"
PREVIEW_TAG = " tiktok-preview"
PARTIAL_TAG = ".partial"  # the encode writes '<stem> tiktok.partial.mp4', renamed only when it finishes
FFMPEG_ENV = "ARSENAL_FFMPEG"

# --- detection tuning (grey levels 0..255; fractions of the frame dimension) -------------------
SAMPLE_FRAMES = 5
RING_FRACTION = 0.01      # the outer ring the background level is read from
RING_UNIFORM = 0.5        # at least half the ring must sit at the background level, or there is no border
LIT_DELTA_MIN = 2         # a pixel is "lit" when it differs from the background by more than this
LIT_DELTA_MAX = 12        # (raised to the ring's noise, but never past this)
LIT_FRACTION = 0.10       # a line is part of the scene when this share of its pixels is lit...
MEAN_DELTA = 1.5          # ...or its mean difference from the background is at least this
MIN_RUN = 0.15            # the scene must span at least 15% of the frame
GAP = 0.05                # dark gaps up to this wide inside the scene are bridged
PIECE = 0.02              # thin bits hanging off the scene's ends across a gap are dropped
EDGE_SPARSE = 0.25        # end lines lit under this share of the scene's typical line are trimmed
EDGE_TRIM = 0.05          # (a cursor or tab touching the canvas; at most this much per end)
QUIET_DELTA = 4           # outside the box, pixels this close to the background count as border...
OUTSIDE_NOISY_MAX = 0.05  # ...and no more than this share may be anything else
EDGE_MARGIN = 0.01        # margins thinner than this are not borders
NEAR_RATIO = 0.01         # within 1% of 9:16 scales exactly, no padding
UPSCALE_WARN = 2.5
LONG_WARN_S = 600.0
BIG_WARN_BYTES = 250 * 1024 * 1024

# --- trim --------------------------------------------------------------------------------------
SILENCE_DB = -50
SILENCE_MIN_S = 0.25
MIN_SOUND_S = 0.3         # shorter sounds at either end are clicks, not the first or last note...
CLICK_GAP_S = 1.0         # ...but only when this much silence cuts them off from the playing...
STOP_CLICK_S = 1.0        # ...and, at the end, only when they start this close to the end of the file
BLIP_REPORT_S = 0.05      # (clicks at least this long are named in the report)
FADE_S = 0.3              # the fade-out, whenever the copy is cut short of the end of the recording
FADE_IN_S = 0.4           # the fade-in, when the copy starts inside sound (a ringing pedal would pop in)
START_SOUND_S = 0.1       # "inside sound": sound within this much of the copy's start (or end)
END_SLACK_S = 0.05        # --to may overshoot the recording's end by this much (the length is shown to 10 ms)

# --- audio clock -------------------------------------------------------------------------------
# Every audio path starts with this, so the sound stays on its picture whatever the flags:
#   async=1          fill timestamp holes (dropouts) with silence and drop overlapping samples; never
#                    stretch, so the notes' pitch and samples are untouched;
#   min_hard_comp    do it for any mismatch over 10 ms (swresample's default is 100 ms, and holes under
#                    that were left in, so the sample-count re-stamp pulled every later note early).
#                    Smaller mismatches add up until they pass 10 ms and are then filled at once, so a
#                    note drifts at most 10 ms from its key strike: under one 60 fps frame (16.7 ms).
#                    One lost packet of the usual codecs (AAC 21.3 ms, Opus 20 ms, MP3 24-26 ms) is
#                    bigger, so it is filled where it happens. It is still ten times MKV's 1 ms
#                    timestamp resolution, whose rounding does not set it off (clean AAC, Opus and MP3
#                    in MKV and MP4 decode sample-identical with and without it);
#   first_pts=0      audio that starts after the video begins with real silence from 0, rather than
#                    a start offset some players ignore; the silence pass uses the same clock, so the
#                    time before the audio's first sample counts as silence there too.
HOLE_FILL_S = 0.01
AUDIO_CLOCK = f"aresample=async=1:min_hard_comp={HOLE_FILL_S:g}:first_pts=0"


class TikTokError(Exception):
    """A problem worth one plain sentence to Daniel; the CLI prints it and exits non-zero."""


# =================================================================================================
# ffmpeg discovery
# =================================================================================================

NO_FFMPEG = ("no ffmpeg found. Fix it one of three ways: install the bundled copy with "
             "'py -m pip install imageio-ffmpeg', put ffmpeg.exe on PATH, or set "
             f"{FFMPEG_ENV} to the full path of ffmpeg.exe")


def _bundled_ffmpeg() -> Optional[str]:
    """imageio-ffmpeg's bundled binary, if that package is installed (it is optional)."""
    try:
        import imageio_ffmpeg  # type: ignore
    except ImportError:
        return None
    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
    return path if path and os.path.isfile(path) else None


def find_ffmpeg() -> str:
    """ARSENAL_FFMPEG, then ffmpeg on PATH, then imageio-ffmpeg's bundled copy; else one friendly error."""
    configured = os.environ.get(FFMPEG_ENV, "").strip().strip('"')
    if configured:
        if os.path.isfile(configured):
            return configured
        found = shutil.which(configured)
        if found:
            return found
        raise TikTokError(f"{FFMPEG_ENV} is set to {configured!r}, but there is no ffmpeg there; "
                          f"fix the path or clear {FFMPEG_ENV}")
    found = shutil.which("ffmpeg")
    if found:
        return found
    bundled = _bundled_ffmpeg()
    if bundled:
        return bundled
    raise TikTokError(NO_FFMPEG)


# =================================================================================================
# "ffmpeg -i" stderr parsing
# =================================================================================================

@dataclass
class Stream:
    index: int
    kind: str                      # "video" | "audio" | "subtitle" | "data" | "attachment"
    codec: str
    width: int = 0
    height: int = 0
    fps: Optional[float] = None
    pix_fmt: Optional[str] = None
    bit_depth: int = 8
    sample_rate: Optional[int] = None
    channels: Optional[str] = None
    rotation: float = 0.0
    attached_pic: bool = False

    @property
    def display_size(self) -> Tuple[int, int]:
        """Frame size after ffmpeg's autorotate (a phone clip tagged -90 decodes portrait)."""
        if round(abs(self.rotation)) % 180 == 90:
            return self.height, self.width
        return self.width, self.height


@dataclass
class MediaInfo:
    duration: Optional[float]
    container: str = ""
    streams: List[Stream] = field(default_factory=list)

    @property
    def video(self) -> Optional[Stream]:
        return next((s for s in self.streams if s.kind == "video" and not s.attached_pic), None)

    @property
    def audio(self) -> Optional[Stream]:
        return next((s for s in self.streams if s.kind == "audio"), None)


_INPUT_RE = re.compile(r"^Input #0, (.+?), from ", re.M)
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")
_STREAM_RE = re.compile(r"^\s*Stream #0:(\d+)(?:\[0x[0-9a-fA-F]+\])?(?:\([^)]*\))?:\s*"
                        r"(Video|Audio|Subtitle|Data|Attachment):\s*(.*)$")
_SIZE_RE = re.compile(r"(?<![\w.])(\d{2,5})x(\d{2,5})(?![\w.])")
_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)(k?)\s*fps\b")
_TBR_RE = re.compile(r"(\d+(?:\.\d+)?)(k?)\s*tbr\b")
_ROTATION_RE = re.compile(r"rotation of\s*(-?\d+(?:\.\d+)?)\s*degrees")
_HZ_RE = re.compile(r"(\d+)\s*Hz\b")
_DEPTH_RE = re.compile(r"p(\d{2})(?:le|be)?$")


def split_top_level(text: str) -> List[str]:
    """Split on commas that are not inside parentheses or brackets."""
    parts, depth, current = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return [p for p in parts if p]


def _rate(match) -> float:
    value = float(match.group(1))
    return value * 1000 if match.group(2) else value


def parse_media_info(text: str) -> MediaInfo:
    """Read duration, container and streams out of ``ffmpeg -i`` stderr (ffmpeg 4 to 7 layouts)."""
    duration = None
    m = _DURATION_RE.search(text)
    if m:
        duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = _INPUT_RE.search(text)
    info = MediaInfo(duration=duration, container=m.group(1) if m else "")
    current: Optional[Stream] = None
    for line in text.splitlines():
        sm = _STREAM_RE.match(line)
        if sm:
            kind, rest = sm.group(2).lower(), sm.group(3)
            parts = split_top_level(rest)
            codec = parts[0].split()[0] if parts and parts[0].split() else "unknown"
            current = Stream(index=int(sm.group(1)), kind=kind, codec=codec,
                             attached_pic="attached pic" in rest)
            if kind == "video":
                for part in parts[1:]:
                    size = _SIZE_RE.search(part)
                    if size and not current.width:
                        current.width, current.height = int(size.group(1)), int(size.group(2))
                if len(parts) > 1:
                    fmt = re.match(r"[a-z0-9_]+", parts[1])
                    if fmt and not _SIZE_RE.search(parts[1]):
                        current.pix_fmt = fmt.group(0)
                        depth = _DEPTH_RE.search(current.pix_fmt)
                        current.bit_depth = int(depth.group(1)) if depth else 8
                fps = _FPS_RE.search(rest) or _TBR_RE.search(rest)
                if fps:
                    current.fps = _rate(fps)
            elif kind == "audio":
                hz = _HZ_RE.search(rest)
                current.sample_rate = int(hz.group(1)) if hz else None
                if len(parts) > 2:
                    current.channels = parts[2]
            info.streams.append(current)
            continue
        rot = _ROTATION_RE.search(line)
        if rot and current is not None and current.kind == "video":
            current.rotation = float(rot.group(1))
        elif line.startswith("Input #") or line.startswith("Output #"):
            current = None
    return info


def _run(cmd: Sequence[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(list(cmd), capture_output=True, stdin=subprocess.DEVNULL)
    except OSError as exc:
        raise TikTokError(f"could not start ffmpeg ({cmd[0]}): {exc}") from exc


def _text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def probe(ffmpeg: str, path) -> MediaInfo:
    proc = _run([ffmpeg, "-hide_banner", "-nostdin", "-i", str(path)])
    text = _text(proc.stderr)
    if "Input #0" not in text:
        last = [ln for ln in text.strip().splitlines() if ln.strip()]
        raise TikTokError(f"ffmpeg cannot read {Path(path).name}: {last[-1] if last else 'no details'}")
    return parse_media_info(text)


# =================================================================================================
# content detection (pure Python over raw grey frames)
# =================================================================================================

class Box(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    @property
    def x1(self) -> int:
        return self.x + self.w

    @property
    def y1(self) -> int:
        return self.y + self.h


def _runs(active: Sequence[bool]) -> List[Tuple[int, int]]:
    runs, start = [], None
    for i, on in enumerate(active):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(active)))
    return runs


def scene_span(active: Sequence[bool], size: int) -> Optional[Tuple[int, int]]:
    """The longest stretch of active lines, bridging short dark gaps and ignoring thin strays.

    Runs closer than GAP merge into one scene (a dark stripe inside the canvas does not split it);
    thin runs (under PIECE) hanging off either end of a merged scene are dropped (a cursor or a UI
    tab near the canvas edge does not widen it). The winner must span MIN_RUN of the frame.
    """
    runs = _runs(active)
    if not runs:
        return None
    gap = max(2, round(size * GAP))
    piece = max(2, round(size * PIECE))
    groups: List[List[Tuple[int, int]]] = [[runs[0]]]
    for run in runs[1:]:
        if run[0] - groups[-1][-1][1] <= gap:
            groups[-1].append(run)
        else:
            groups.append([run])
    best = None
    for group in groups:
        while len(group) > 1 and group[0][1] - group[0][0] < piece:
            group.pop(0)
        while len(group) > 1 and group[-1][1] - group[-1][0] < piece:
            group.pop()
        span = (group[0][0], group[-1][1])
        if best is None or span[1] - span[0] > best[1] - best[0]:
            best = span
    if best[1] - best[0] < size * MIN_RUN:
        return None
    return best


def trim_sparse_ends(span: Tuple[int, int], counts: Sequence[int], size: int) -> Optional[Tuple[int, int]]:
    """Cut sparse lines off the span's ends: a cursor or UI tab touching the canvas edge.

    scene_span only drops strays across a gap; one that touches the scene joins it. Its lines are
    lit far less than the scene's typical line (a 22 px cursor in a 1080 px column), so end lines
    lit under EDGE_SPARSE of the median are cut, at most EDGE_TRIM of the frame per end.
    """
    a, b = span
    floor = EDGE_SPARSE * statistics.median(counts[a:b])
    most = max(1, round(size * EDGE_TRIM))
    start, end = a, b
    while a < b and a - start < most and counts[a] < floor:
        a += 1
    while b > a and end - b < most and counts[b - 1] < floor:
        b -= 1
    if b - a < size * MIN_RUN:
        return None
    return a, b


def _table(fn) -> bytes:
    return bytes(fn(v) for v in range(256))


def background_level(frame: bytes, width: int, height: int) -> Tuple[int, float, int]:
    """(background level, share of the outer ring at that level, lit threshold) from the frame's ring."""
    t = max(1, round(min(width, height) * RING_FRACTION))
    pieces = [frame[: t * width], frame[(height - t) * width: height * width]]
    pieces += [frame[x: width * height: width] for x in range(t)]
    pieces += [frame[width - 1 - x: width * height: width] for x in range(t)]
    ring = b"".join(pieces)
    ordered = sorted(ring)
    bg = ordered[len(ordered) // 2]
    # The ring's own noise sets the lit threshold: a grainy border needs a higher bar than flat black.
    # The 75th percentile, because a quarter of the ring may legitimately be scene (a full-height
    # canvas crosses the top and bottom rows); capped, because a border that noisy is no border.
    deviations = sorted(ring.translate(_table(lambda v: min(255, abs(v - bg)))))
    noise = deviations[int(len(deviations) * 0.75)]
    delta = min(LIT_DELTA_MAX, max(LIT_DELTA_MIN, noise + 1))
    uniform = 1.0 - ring.translate(_table(lambda v: 1 if abs(v - bg) > delta else 0)).count(1) / len(ring)
    return bg, uniform, delta


def detect_frame_box(frame: bytes, width: int, height: int) -> Optional[Box]:
    """The lit scene's box in one grey frame; the full frame when there is no border; None when empty.

    None means "no content found here" (black, blank): such frames do not vote in combine_boxes.
    """
    if width < 4 or height < 4 or len(frame) < width * height:
        return None
    frame = bytes(frame[: width * height])
    full = Box(0, 0, width, height)
    bg, uniform, delta = background_level(frame, width, height)
    if uniform < RING_UNIFORM:
        return full  # the scene runs off the edges: nothing to cut
    mask = frame.translate(_table(lambda v: 1 if abs(v - bg) > delta else 0))
    diff = frame.translate(_table(lambda v: min(255, abs(v - bg))))

    lit_col, mean_col = LIT_FRACTION * height, MEAN_DELTA * height
    col_counts = [mask[x::width].count(1) for x in range(width)]
    active_cols = [col_counts[x] >= lit_col or sum(diff[x::width]) >= mean_col for x in range(width)]
    cols = scene_span(active_cols, width)
    if cols is not None:
        cols = trim_sparse_ends(cols, col_counts, width)
    if cols is None:
        return None
    x0, x1 = cols
    band = x1 - x0
    lit_row, mean_row = LIT_FRACTION * band, MEAN_DELTA * band
    active_rows, row_counts = [], []
    for y in range(height):
        a = y * width + x0
        row_counts.append(mask[a:a + band].count(1))
        active_rows.append(row_counts[-1] >= lit_row or sum(diff[a:a + band]) >= mean_row)
    rows = scene_span(active_rows, height)
    if rows is not None:
        rows = trim_sparse_ends(rows, row_counts, height)
    if rows is None:
        return None
    y0, y1 = rows

    # A real border is quiet. If the area outside the box is busy, this is a dark full-frame scene
    # with a bright patch, not a box on black: crop nothing.
    outside_area = width * height - band * (y1 - y0)
    if outside_area <= 0:
        return full
    noisy = frame.translate(_table(lambda v: 1 if abs(v - bg) > max(QUIET_DELTA, delta) else 0))
    inside = sum(noisy[y * width + x0: y * width + x1].count(1) for y in range(y0, y1))
    if noisy.count(1) - inside > OUTSIDE_NOISY_MAX * outside_area:
        return full
    return Box(x0, y0, band, y1 - y0)


def snap_box(x0: int, y0: int, x1: int, y1: int, width: int, height: int) -> Optional[Box]:
    """Even origin and size, snapped inward (never a border line), clamped to the frame."""
    x0 = min(max(0, x0 + (x0 % 2)), width)
    y0 = min(max(0, y0 + (y0 % 2)), height)
    x1 = min(max(x0, x1), width)
    y1 = min(max(y0, y1), height)
    w = (x1 - x0) - (x1 - x0) % 2
    h = (y1 - y0) - (y1 - y0) % 2
    if w < 2 or h < 2:
        return None
    return Box(x0, y0, w, h)


def fills_frame(box: Box, width: int, height: int) -> bool:
    mx, my = max(2, width * EDGE_MARGIN), max(2, height * EDGE_MARGIN)
    return box.x <= mx and box.y <= my and width - box.x1 <= mx and height - box.y1 <= my


@dataclass
class Detection:
    box: Optional[Box]   # None: crop nothing
    found: int           # sample frames that found content
    sampled: int         # sample frames read
    reason: str          # "borders" | "no-borders" | "no-content"


def combine_boxes(boxes: Sequence[Optional[Box]], width: int, height: int) -> Detection:
    """The median box of the frames that found content, snapped even; None when nothing to cut."""
    found = [b for b in boxes if b is not None]
    if not found:
        return Detection(None, 0, len(boxes), "no-content")
    box = snap_box(statistics.median_low(b.x for b in found), statistics.median_low(b.y for b in found),
                   statistics.median_low(b.x1 for b in found), statistics.median_low(b.y1 for b in found),
                   width, height)
    if box is None or fills_frame(box, width, height):
        return Detection(None, len(found), len(boxes), "no-borders")
    return Detection(box, len(found), len(boxes), "borders")


def sample_times(duration: Optional[float], count: int = SAMPLE_FRAMES, start: float = 0.0) -> List[float]:
    """Frames spread across the middle 90% of the stretch that begins at `start` and lasts `duration`
    (the whole video, or the --from/--to window: a dark intro outside it never votes)."""
    if not duration or duration <= 0:
        return [round(start, 3)]
    if count == 1:
        return [round(start + duration / 2, 3)]
    return [round(start + duration * (0.05 + 0.9 * i / (count - 1)), 3) for i in range(count)]


def grab_gray_frame(ffmpeg: str, path, t: float, stream_index: int, width: int, height: int) -> Optional[bytes]:
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
           "-map", f"0:{stream_index}", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    data = _run(cmd).stdout
    return data if len(data) == width * height else None


# =================================================================================================
# aspect math
# =================================================================================================

def _even_round(v: float) -> int:
    return max(2, 2 * round(v / 2))


def _even_up(v: float) -> int:
    return max(2, 2 * math.ceil(v / 2 - 1e-9))


def _even_down(v: float) -> int:
    return max(0, 2 * math.floor(v / 2 + 1e-9))


@dataclass
class Framing:
    mode: str       # "exact" | "fit" | "fill"
    scale: float    # picture scale factor
    scaled_w: int
    scaled_h: int
    offset_x: int   # fit: padding left/top; fill: crop left/top
    offset_y: int


def plan_framing(w: int, h: int, mode: str = "fit") -> Framing:
    """How a w x h picture becomes 1080x1920: exact (within 1% of 9:16), fit (pad), or fill (crop)."""
    if w <= 0 or h <= 0:
        raise ValueError("the picture has no size")
    if abs((w / h) / (TARGET_W / TARGET_H) - 1) <= NEAR_RATIO:
        return Framing("exact", TARGET_H / h, TARGET_W, TARGET_H, 0, 0)
    if mode == "fill":
        s = max(TARGET_W / w, TARGET_H / h)
        sw, sh = max(TARGET_W, _even_up(w * s)), max(TARGET_H, _even_up(h * s))
        return Framing("fill", s, sw, sh, _even_down((sw - TARGET_W) / 2), _even_down((sh - TARGET_H) / 2))
    if mode != "fit":
        raise ValueError(f"unknown mode {mode!r}")
    s = min(TARGET_W / w, TARGET_H / h)
    sw, sh = min(TARGET_W, _even_round(w * s)), min(TARGET_H, _even_round(h * s))
    return Framing("fit", s, sw, sh, _even_down((TARGET_W - sw) / 2), _even_down((TARGET_H - sh) / 2))


def choose_fps(source_fps: Optional[float], choice: str = "auto") -> Tuple[str, float]:
    """(ffmpeg fps value, number): the source's own rate capped at 60, or a forced 30/60."""
    if choice in ("30", "60"):
        return choice, float(choice)
    if not source_fps or source_fps <= 0:
        return "30", 30.0
    if source_fps > 60.5:
        return "60", 60.0
    for num in (24000, 30000, 60000):
        if abs(source_fps - num / 1001) < 0.02:
            return f"{num}/1001", num / 1001
    if abs(source_fps - round(source_fps)) < 0.02:
        return str(round(source_fps)), float(round(source_fps))
    return f"{source_fps:.3f}", source_fps


def video_filter(box: Optional[Box], framing: Framing, fps: Optional[str] = None) -> str:
    # fps goes first: after a scale, ffmpeg 7.1's fps filter drops the final frame at end of stream
    # (a 150-frame clip came out as 149); first, it keeps them all and scales only the frames kept
    parts = [f"fps={fps}"] if fps else []
    if box is not None:
        parts.append(f"crop={box.w}:{box.h}:{box.x}:{box.y}")
    parts.append(f"scale={framing.scaled_w}:{framing.scaled_h}:flags=lanczos")
    if framing.mode == "fit":
        parts.append(f"pad={TARGET_W}:{TARGET_H}:{framing.offset_x}:{framing.offset_y}:color=black")
    elif framing.mode == "fill":
        parts.append(f"crop={TARGET_W}:{TARGET_H}:{framing.offset_x}:{framing.offset_y}")
    parts.append("setsar=1")
    parts.append("format=yuv420p")
    return ",".join(parts)


# =================================================================================================
# silence and loudness
# =================================================================================================

_NUM = r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_SILENCE_RE = re.compile(r"silence_(start|end):\s*" + _NUM)
_MEAN_RE = re.compile(r"mean_volume:\s*" + _NUM + r"\s*dB")
_MAX_RE = re.compile(r"max_volume:\s*" + _NUM + r"\s*dB")
_TIME_RE = re.compile(r"time=\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


def parse_silence(text: str) -> List[Tuple[float, Optional[float]]]:
    """silencedetect output as (start, end) pairs; end is None when the silence ran off the end."""
    spans: List[Tuple[float, Optional[float]]] = []
    for kind, value in _SILENCE_RE.findall(text):
        if kind == "start":
            spans.append((max(0.0, float(value)), None))
        elif spans and spans[-1][1] is None:
            spans[-1] = (spans[-1][0], float(value))
    return spans


def parse_volume(text: str) -> Tuple[Optional[float], Optional[float]]:
    """The last volumedetect (mean dB, max dB) in the text."""
    means, maxes = _MEAN_RE.findall(text), _MAX_RE.findall(text)
    return (float(means[-1]) if means else None, float(maxes[-1]) if maxes else None)


def parse_last_time(text: str) -> Optional[float]:
    """The final time= of ffmpeg's progress line: where the decoded stream actually ended."""
    found = _TIME_RE.findall(text)
    if not found:
        return None
    h, m, s = found[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def sound_segments(silences: Sequence[Tuple[float, Optional[float]]],
                   audio_end: float) -> List[Tuple[float, float]]:
    """The stretches between the silences: where there is sound."""
    segments, cursor = [], 0.0
    for start, end in silences:
        if start > cursor:
            segments.append((cursor, min(start, audio_end)))
        cursor = audio_end if end is None else max(cursor, end)
    if audio_end > cursor:
        segments.append((cursor, audio_end))
    return [(a, b) for a, b in segments if b - a > 1e-6]


def sound_window(silences: Sequence[Tuple[float, Optional[float]]], audio_end: float,
                 min_sound: float = MIN_SOUND_S, click_gap: float = CLICK_GAP_S,
                 stop_click: float = STOP_CLICK_S) -> Optional[Tuple[float, float]]:
    """(first sound, last sound) in seconds; None when there is no real sound at all.

    A blip shorter than min_sound at either end (the OBS hotkey click, a mouse click, codec
    priming) is not the first or last sound, but only when at least click_gap of silence follows
    it (at the start) or comes before it (at the end): a short staccato first note followed by a
    quick rest is music, and must not be cut.

    The end is stricter, because the end of the music is sacred: a short sound long after the
    playing may be the final staccato note, and a wrong guess there cuts the piece's last note. The
    one end click worth dropping is the stop hotkey, and the recording stops a moment after it, so
    a short end sound is a click only when it also starts within stop_click of the end of the
    audio. Anything earlier stays as music; what was dropped is named in the report (edge_blips).
    """
    segments = sound_segments(silences, audio_end)
    while (segments and segments[0][1] - segments[0][0] < min_sound
           and (segments[1][0] if len(segments) > 1 else audio_end) - segments[0][1] >= click_gap):
        segments.pop(0)
    while (segments and segments[-1][1] - segments[-1][0] < min_sound
           and segments[-1][0] >= audio_end - stop_click
           and segments[-1][0] - (segments[-2][1] if len(segments) > 1 else 0.0) >= click_gap):
        segments.pop()
    if not segments:
        return None
    return segments[0][0], segments[-1][1]


def edge_blips(silences: Sequence[Tuple[float, Optional[float]]], audio_end: float,
               window: Optional[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """(start, length) of the audible blips sound_window passed over, for the report."""
    if window is None:
        return []
    return [(a, b - a) for a, b in sound_segments(silences, audio_end)
            if (b <= window[0] or a >= window[1]) and b - a >= BLIP_REPORT_S]


def sound_near(silences: Sequence[Tuple[float, Optional[float]]], audio_end: float,
               a: float, b: float) -> bool:
    """True when some sound (a stretch silencedetect did not call silent) touches [a, b]."""
    return any(s < b and e > a for s, e in sound_segments(silences, audio_end))


class Window(NamedTuple):
    """The stretch of the recording the copy is confined to (--from/--to), in seconds from its start."""
    start: float = 0.0
    end: Optional[float] = None          # None: to the end of the recording

    @property
    def length(self) -> Optional[float]:
        return None if self.end is None else self.end - self.start


@dataclass
class Trim:
    start: float = 0.0
    end: Optional[float] = None          # None: keep to the end of the recording
    first_sound: Optional[float] = None
    last_sound: Optional[float] = None
    note: str = ""
    ignored: List[Tuple[float, float]] = field(default_factory=list)
    fade_in: bool = False                # the copy starts inside sound: fade the audio in (given the room)
    ends_in_sound: bool = False          # the copy is cut inside sound (no tail room): said in the report

    @property
    def fade(self) -> bool:
        """The fade-out: whenever the copy is cut short of the end of the recording (given the room).

        fade_in and fade say where the copy meets sound; fades_for says which ramps a copy this long
        can hold, and the filter chain and the report both read that one answer.
        """
        return self.end is not None


def plan_trim(sound: Optional[Tuple[float, float]], duration: float, lead: float, tail: float,
              window: Optional[Window] = None) -> Trim:
    """Where the copy starts and ends: `lead` before the first sound and `tail` after the last, kept
    inside the window (the whole recording when None). All times count from the recording's start.

    With a window whose end was given (--to), the copy always ends there or earlier: its end is never
    None, so it always fades out. Without one, a tail that reaches the end of the recording means
    "keep to the end" (end None, no fade), as before.
    """
    w0 = window.start if window is not None else 0.0
    w1 = window.end if window is not None else None
    if sound is None:
        where = " in the window" if window is not None else ""
        return Trim(round(w0, 3), w1, note=f"no sound found{where} (silent all the way through), "
                                            "so nothing was trimmed")
    first, last = sound[0], min(sound[1], duration if w1 is None else w1)
    start = max(w0, first - lead)
    if start - w0 < 0.05:
        start = w0
    end: Optional[float] = last + tail
    if w1 is not None:
        if end >= w1 or end <= start + 1.0:
            end = w1
    elif end >= duration - 0.05 or end <= start + 1.0:
        end = None
    return Trim(round(start, 3), None if end is None else round(end, 3), first, last)


def fades_for(trim: Trim) -> Tuple[bool, bool]:
    """(fade in, fade out): the fades the audio filter applies, so the report names exactly those.

    A copy too short to hold a ramp gets none there: the fade-in needs more than FADE_IN_S + FADE_S
    (room for both ramps), the fade-out more than FADE_S. A copy that keeps to the end of the
    recording has room for anything.
    """
    keep = None if trim.end is None else trim.end - trim.start
    fade_in = bool(trim.fade_in and (keep is None or keep > FADE_IN_S + FADE_S))
    fade_out = bool(trim.fade and keep > FADE_S)
    return fade_in, fade_out


# =================================================================================================
# times and naming
# =================================================================================================

_TIME_PART = re.compile(r"\d+")
_TIME_LAST = re.compile(r"\d+(?:\.\d+)?")
TIME_FORMS = "seconds (1732 or 1731.6), m:ss (28:52) or h:mm:ss (1:05:03.2)"


def parse_time(text: str) -> float:
    """Seconds from '1732', '1731.6', '28:52', '28:52.5' or '1:05:03.2'; one plain sentence otherwise."""
    raw = str(text).strip()
    if raw.startswith("-"):
        raise TikTokError(f"{raw} is a negative time; the recording starts at 0:00")
    parts = raw.split(":")
    if not (1 <= len(parts) <= 3 and all(_TIME_PART.fullmatch(p) for p in parts[:-1])
            and _TIME_LAST.fullmatch(parts[-1])):
        raise TikTokError(f"cannot read the time {raw!r}; give {TIME_FORMS}")
    values = [float(p) for p in parts]
    if any(v >= 60 for v in values[1:]):
        raise TikTokError(f"cannot read the time {raw!r}: after a colon, minutes and seconds go up to 59")
    seconds = 0.0
    for value in values:
        seconds = seconds * 60 + value
    return seconds


def name_time(seconds: float) -> str:
    """'28-52', '28-51.6' or '1-05-03.2': a time as it goes into a file name."""
    seconds = round(max(0.0, seconds), 3)
    whole = int(seconds)
    minutes, secs = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    text = f"{hours}-{minutes:02d}-{secs:02d}" if hours else f"{minutes}-{secs:02d}"
    fraction = f"{seconds - whole:.3f}".rstrip("0")
    return text + (fraction[1:] if fraction != "0." else "")


def window_tag(start: Optional[float], end: Optional[float]) -> str:
    """' 28-52-end' for the output name; '' when neither --from nor --to was given."""
    if start is None and end is None:
        return ""
    return f" {'start' if start is None else name_time(start)}-{'end' if end is None else name_time(end)}"


# ' tiktok', then optionally a space and a tag that starts like a time ('28-52-end', 'start-3-00', or
# a copy cut by hand and named '28-52'), then optionally '-preview'
_OURS_RE = re.compile(rf"{OUTPUT_TAG}(?: (?:start|\d)[\w.-]*)?(?:-preview)?$")


def is_our_output(path: Path) -> bool:
    """'<stem> tiktok', '<stem> tiktok 28-52-end' (or any '<stem> tiktok <time...>' cut by hand),
    their -preview pictures and .partial files: copies, never the recording --latest looks for."""
    stem = path.stem.lower()
    return stem.endswith(PARTIAL_TAG) or _OURS_RE.search(stem) is not None


def _looks_like_dir(out: str) -> bool:
    """A trailing slash, an existing folder, or a new name with no extension (made when saving)."""
    path = Path(out)
    return out.endswith(("/", "\\")) or path.is_dir() or (not path.suffix and not path.exists())


def output_path_for(source: Path, out: Optional[str] = None, many: bool = False, tag: str = "") -> Path:
    """'<stem> tiktok.mp4' beside the source, inside --out when it is a folder, or --out itself.

    tag: window_tag(--from, --to), so a windowed copy is '<stem> tiktok 28-52-end.mp4' and never
    replaces the whole-recording copy (or another window's) beside it.
    """
    name = f"{source.stem}{OUTPUT_TAG}{tag}.mp4"
    if not out:
        return source.with_name(name)
    if _looks_like_dir(out):
        return Path(out) / name
    if not Path(out).suffix:
        raise TikTokError(f"--out {out} is an existing file with no extension; "
                          "give a folder, or a file name ending in .mp4")
    if many:
        raise TikTokError("--out names one file, but more than one video was given; "
                          "point --out at a folder instead")
    path = Path(out)
    if path.suffix.lower() not in (".mp4", ".m4v", ".mov"):
        path = path.with_name(path.name + ".mp4")
    return path


def preview_path_for(source: Path, output: Path, tag: str = "") -> Path:
    return output.parent / f"{source.stem}{OUTPUT_TAG}{tag}-preview.jpg"


def partial_path_for(output: Path) -> Path:
    """Where the encode writes until it finishes: a killed run never leaves a broken '<stem> tiktok.mp4'."""
    return output.with_name(f"{output.stem}{PARTIAL_TAG}{output.suffix}")


def same_path(a: Path, b: Path) -> bool:
    if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)):
        return True
    try:
        return a.exists() and b.exists() and os.path.samefile(a, b)
    except OSError:
        return False


def check_output(source: Path, output: Path, force: bool, dropped: bool = False) -> None:
    if same_path(source, output):
        raise TikTokError(f"refusing: {output} is the source video itself; it is never overwritten")
    if output.exists() and not force:
        if dropped:  # a drag-and-drop cannot add --force, so do not suggest it
            raise TikTokError(f"a TikTok copy of this video already exists: {output}. "
                              "Delete or rename that copy, then drop the video again.")
        raise TikTokError(f"{output} already exists; add --force to replace it")


def check_preview(preview: Path, force: bool) -> None:
    if preview.exists() and not force:
        raise TikTokError(f"the preview {preview} already exists; add --force to replace it")


def default_folder() -> Path:
    """The library root py -m arsenal serve uses when given no --root."""
    try:
        from .serve import DEFAULT_ROOTS
        root = DEFAULT_ROOTS[0]
    except Exception as exc:  # serve.py is busy shared code: a broken import is a sentence, not a traceback
        raise TikTokError("could not find the default recordings folder, because arsenal/serve.py did not "
                          f"load ({type(exc).__name__}: {exc}). Say where the recordings are with --folder, "
                          "for example: py -m arsenal tiktok --latest --folder \"D:\\my recordings\"") from exc
    return Path(root).resolve()


def latest_video(folder: Path) -> Path:
    folder = Path(folder)
    if not folder.is_dir():
        raise TikTokError(f"the folder {folder} does not exist")
    candidates = []
    for path in folder.iterdir():
        if path.suffix.lower() in VIDEO_SUFFIXES and not is_our_output(path):
            try:
                if path.is_file():
                    candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue
    if not candidates:
        raise TikTokError(f"no .mp4, .mkv or .mov recordings in {folder}")
    return max(candidates)[1]


# =================================================================================================
# commands
# =================================================================================================

def silence_command(ffmpeg: str, source, audio_index: int, window: Optional[Window] = None) -> List[str]:
    # volumedetect first, so "before" measures the recording's own samples. Then the encode's audio
    # clock: audio that starts after the video (a late track in an MKV) is silence from 0 up to its
    # first sample, not an unheard stretch that silencedetect would count as the first sound.
    # The window is cut the way the encode cuts it (-ss before -i, -t after), so every time this
    # scan reports counts from the window's start, on the encode's own clock.
    cmd = [ffmpeg, "-hide_banner", "-nostdin"]
    if window is not None and window.start > 0:
        cmd += ["-ss", f"{window.start:.3f}"]
    cmd += ["-i", str(source)]
    if window is not None and window.end is not None:
        cmd += ["-t", f"{window.length:.3f}"]
    return cmd + ["-map", f"0:{audio_index}",
                  "-af", f"volumedetect,{AUDIO_CLOCK},silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_S}",
                  "-vn", "-sn", "-dn", "-f", "null", "-"]


def audio_filter(trim: Trim, lufs: Optional[float]) -> str:
    # Holes in the source audio (dropouts) are filled with silence first (AUDIO_CLOCK), then the
    # stamps are rebuilt from the sample count, on every path: sync never depends on --no-loudnorm.
    parts = [AUDIO_CLOCK]
    if lufs is not None:
        parts.append(f"loudnorm=I={lufs:g}:TP=-1.5:LRA=11")
        parts.append("aresample=48000")
    # loudnorm leaves a ~86 ms jump in its output timestamps (the samples are right, the stamps are
    # not), so players put the audio late. Re-stamp from the sample count, which the clock above made
    # match the timeline; STARTPTS keeps where the stream starts.
    parts.append("asetpts=STARTPTS+N/SR/TB")
    # both fades come after loudnorm, so its gain does not undo their ramps; fades_for decides which
    # ramps fit the copy, and the report reads the same answer
    fade_in, fade_out = fades_for(trim)
    if fade_in:
        parts.append(f"afade=t=in:st=0:d={FADE_IN_S}")
    if fade_out:
        parts.append(f"afade=t=out:st={trim.end - trim.start - FADE_S:.3f}:d={FADE_S}")
    return ",".join(parts)


def encode_command(ffmpeg: str, source, output, *, video_index: int, audio_index: Optional[int],
                   vf: str, af: Optional[str], trim: Trim, crf: int, force: bool) -> List[str]:
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-nostats", "-progress", "pipe:1",
           "-y" if force else "-n"]
    if trim.start > 0:
        cmd += ["-ss", f"{trim.start:.3f}"]
    cmd += ["-i", str(source)]
    if trim.end is not None:
        cmd += ["-t", f"{trim.end - trim.start:.3f}"]
    cmd += ["-map", f"0:{video_index}"]
    if audio_index is not None:
        cmd += ["-map", f"0:{audio_index}"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", str(crf)]
    if audio_index is not None:
        if af:
            cmd += ["-af", af]
        cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd += ["-sn", "-dn", "-movflags", "+faststart", str(output)]
    return cmd


def preview_command(ffmpeg: str, source, preview, *, video_index: int, vf: str, at: float) -> List[str]:
    return [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0.0, at):.3f}",
            "-i", str(source), "-map", f"0:{video_index}", "-frames:v", "1", "-vf", vf,
            "-q:v", "3", str(preview)]


_PLAIN_ARG = re.compile(r"^[A-Za-z0-9_\-+./:=\\]+$")


def show_command(cmd: Sequence[str]) -> str:
    """The command as one copy-pasteable line (quoted wherever a shell could misread it)."""
    return " ".join(a if _PLAIN_ARG.match(a) else '"' + a.replace('"', '\\"') + '"' for a in cmd)


# =================================================================================================
# run layer
# =================================================================================================

@dataclass
class Options:
    out: Optional[str] = None
    force: bool = False
    dry_run: bool = False
    preview: bool = False
    mode: str = "fit"
    trim: bool = True
    lead: float = 0.5
    tail: float = 2.0
    lufs: float = -16.0
    loudnorm: bool = True
    crf: int = 17
    fps: str = "auto"
    dropped: bool = False   # started by dragging videos onto tiktok-ready.cmd (messages cannot say --force)
    start: Optional[float] = None   # --from, seconds (None: the start of the recording)
    end: Optional[float] = None     # --to, seconds (None: the end of the recording)


def window_problem(start: Optional[float], end: Optional[float]) -> Optional[str]:
    """Why --from/--to make no window: --to at or before the start, which is 0:00 without --from
    ('--to 0' alone used to slip through and leave a zero-length, stream-less copy)."""
    if end is not None and end <= (start or 0.0):
        after = f"--from {clock(start)}" if start is not None else "the start of the recording"
        return f"--to {clock(end)} must come after {after}"
    return None


def validate(opts: Options) -> List[str]:
    problems = []
    problem = window_problem(opts.start, opts.end)
    if problem:
        problems.append(problem)
    if opts.lead < 0:
        problems.append("--lead must be 0 or more seconds")
    if opts.tail < 0:
        problems.append("--tail must be 0 or more seconds")
    if not -70 <= opts.lufs <= -5:
        problems.append("--lufs must be between -70 and -5 (TikTok sounds right around -16)")
    if not 0 <= opts.crf <= 51:
        problems.append("--crf must be between 0 and 51 (17 is near-lossless to the eye)")
    if opts.mode not in ("fit", "fill"):
        problems.append("choose --fit or --fill")
    if opts.fps not in ("auto", "30", "60"):
        problems.append("--fps must be auto, 30 or 60")
    return problems


def _loudness(ffmpeg: str, path, audio_index: int,
              window: Optional[Window] = None) -> Tuple[str, Tuple[Optional[float], Optional[float]]]:
    text = _text(_run(silence_command(ffmpeg, path, audio_index, window)).stderr)
    return text, parse_volume(text)


def fit_window(opts: Options, duration: Optional[float]) -> Optional[Window]:
    """The --from/--to window checked against the recording's length; None when neither was given."""
    if opts.start is None and opts.end is None:
        return None
    problem = window_problem(opts.start, opts.end)   # validate said so at the prompt; process() callers too
    if problem:
        raise TikTokError(problem)
    start, end = opts.start or 0.0, opts.end
    if duration is not None:
        if start >= duration:
            raise TikTokError(f"--from {clock(start)} is past the end of the recording, "
                              f"which is {clock(duration)} long")
        if end is not None and end > duration + END_SLACK_S:
            raise TikTokError(f"--to {clock(end)} is past the end of the recording, "
                              f"which is {clock(duration)} long")
        if end is not None:
            end = min(end, duration)
    return Window(start, end)


def _encode(cmd: List[str], seconds: float, output: Path) -> None:
    show = sys.stdout.isatty()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    errors: List[bytes] = []
    reader = threading.Thread(target=lambda: errors.append(proc.stderr.read()), daemon=True)
    reader.start()
    try:
        for raw in proc.stdout:
            line = raw.decode("ascii", errors="replace").strip()
            if show and line.startswith("out_time_us=") and seconds > 0:
                value = line.split("=", 1)[1]
                if value.lstrip("-").isdigit():
                    pct = max(0.0, min(100.0, int(value) / 1e6 / seconds * 100))
                    sys.stdout.write(f"\r  encoding {pct:5.1f}%")
                    sys.stdout.flush()
        proc.wait()
    except BaseException:
        proc.kill()
        proc.wait()
        _remove(output)
        raise
    finally:
        reader.join(timeout=5)
        if show:
            sys.stdout.write("\r" + " " * 24 + "\r")
            sys.stdout.flush()
    if proc.returncode != 0:
        _remove(output)
        detail = [ln for ln in _text(b"".join(errors)).strip().splitlines() if ln.strip()]
        raise TikTokError("ffmpeg stopped with an error: " + (" | ".join(detail[-3:]) if detail else
                                                              f"exit code {proc.returncode}"))


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def process(source, opts: Options, ffmpeg: Optional[str] = None, many: bool = False) -> dict:
    """Detect, plan, and (unless dry-run) encode one video. Returns the facts the report prints."""
    ff = ffmpeg or find_ffmpeg()
    src = Path(source)
    if not src.is_file():
        raise TikTokError(f"cannot find the video {src}")
    tag = window_tag(opts.start, opts.end)
    output = output_path_for(src, opts.out, many, tag)
    partial = partial_path_for(output)
    for target in (output, partial):
        if same_path(src, target):
            raise TikTokError(f"refusing: {target} is the source video itself; it is never overwritten")
    output_existed = output.exists()
    if not opts.dry_run:
        check_output(src, output, opts.force, opts.dropped)
    if opts.preview:  # the preview is written even on a dry run, so it is checked either way
        check_preview(preview_path_for(src, output, tag), opts.force)

    info = probe(ff, src)
    video = info.video
    if video is None:
        raise TikTokError(f"{src.name} has no video stream")
    width, height = video.display_size
    if not width or not height:
        raise TikTokError(f"could not read the picture size of {src.name}")
    duration = info.duration
    window = fit_window(opts, duration)
    # the copy's bounds before any trim: the window, or the whole recording
    w0 = window.start if window is not None else 0.0
    w1 = window.end if window is not None else None
    bound = w1 if w1 is not None else duration           # where the copy can run to (None: unknown length)

    boxes = []
    for t in sample_times(None if bound is None else bound - w0, start=w0):
        frame = grab_gray_frame(ff, src, t, video.index, width, height)
        if frame is not None:
            boxes.append(detect_frame_box(frame, width, height))
    if not boxes:
        raise TikTokError(f"could not read any frames from {src.name}")
    detection = combine_boxes(boxes, width, height)
    content_w, content_h = (detection.box.w, detection.box.h) if detection.box else (width, height)
    framing = plan_framing(content_w, content_h, opts.mode)
    fps_text, fps_value = choose_fps(video.fps, opts.fps)

    audio = info.audio
    loud_before: Tuple[Optional[float], Optional[float]] = (None, None)
    trim = Trim(round(w0, 3), w1)
    if audio is None:
        trim.note = "no audio track: kept video-only and not trimmed"
    else:
        # the scan is cut to the window, so its times count from w0 on the encode's own clock
        text, loud_before = _loudness(ff, src, audio.index, window)
        audio_end = parse_last_time(text) or (bound - w0 if bound is not None else 0.0)
        silences = parse_silence(text)
        if opts.trim:
            # a --to point is not the end of the file: no stop hotkey click lives there, and the end
            # rule that drops one must not drop a short last note before the point Daniel chose
            stop_click = 0.0 if w1 is not None else STOP_CLICK_S
            sound = sound_window(silences, audio_end, stop_click=stop_click)
            total = duration if duration is not None else w0 + audio_end
            trim = plan_trim(None if sound is None else (sound[0] + w0, sound[1] + w0),
                             total, opts.lead, opts.tail, window)
            trim.ignored = [(at + w0, length) for at, length in edge_blips(silences, audio_end, sound)]
        else:
            trim.note = "trimming is off (--no-trim)"
        at = trim.start - w0
        trim.fade_in = sound_near(silences, audio_end, at, at + START_SOUND_S)
        if trim.end is None and sound_near(silences, audio_end, audio_end - START_SOUND_S, audio_end):
            # the recording itself stops inside sound (OBS was stopped while a note rang): cut the
            # copy at the audio's end, so it fades out there instead of stopping dead
            trim.end = round(w0 + audio_end, 3)
        if trim.fade:
            at = trim.end - w0
            trim.ends_in_sound = sound_near(silences, audio_end, at - START_SOUND_S, at)

    vf = video_filter(detection.box, framing, fps_text)
    af = audio_filter(trim, opts.lufs if opts.loudnorm else None) if audio is not None else None
    # force=True only lets ffmpeg replace a stale partial file (ours); the real output was checked above
    cmd = encode_command(ff, src, partial, video_index=video.index,
                         audio_index=audio.index if audio is not None else None,
                         vf=vf, af=af, trim=trim, crf=opts.crf, force=True)
    # what --dry-run prints: the same encode written straight to the final name, so a copy-pasted
    # command makes '<stem> tiktok.mp4' (and, like the verb, refuses to replace it without --force)
    shown = encode_command(ff, src, output, video_index=video.index,
                           audio_index=audio.index if audio is not None else None,
                           vf=vf, af=af, trim=trim, crf=opts.crf, force=opts.force)
    keep = ((trim.end if trim.end is not None else (duration or 0.0)) - trim.start)

    result = {
        "source": src, "source_bytes": src.stat().st_size, "duration": duration,
        "width": width, "height": height, "fps": video.fps, "video_codec": video.codec,
        "bit_depth": video.bit_depth, "audio_codec": audio.codec if audio else None,
        "detection": detection, "framing": framing, "trim": trim, "keep": keep, "window": window,
        "fps_text": fps_text, "fps_value": fps_value, "loud_before": loud_before, "loud_after": (None, None),
        "loudnorm": opts.loudnorm and audio is not None, "output": output, "output_existed": output_existed,
        "force": opts.force, "command": cmd, "shown_command": shown, "partial": partial,
        "dry_run": opts.dry_run, "preview": None,
        "out_info": None, "out_bytes": None, "warnings": [],
    }

    if opts.preview:
        preview = preview_path_for(src, output, tag)
        preview.parent.mkdir(parents=True, exist_ok=True)
        at = trim.start + keep / 2 if keep > 0 else 0.0
        proc = _run(preview_command(ff, src, preview, video_index=video.index,
                                    vf=video_filter(detection.box, framing), at=at))
        if proc.returncode != 0 or not preview.is_file():
            raise TikTokError(f"could not write the preview {preview.name}: "
                              f"{_text(proc.stderr).strip().splitlines()[-1:] or 'no details'}")
        result["preview"] = preview

    if not opts.dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        _remove(partial)  # left by a run that was killed mid-encode
        _encode(cmd, keep, partial)
        try:
            os.replace(partial, output)
        except OSError as exc:
            _remove(partial)
            raise TikTokError(f"could not save {output.name} (is it open in a player?): "
                              f"{exc.strerror or exc}") from exc
        out_info = probe(ff, output)
        result["out_info"] = out_info
        result["out_bytes"] = output.stat().st_size
        if out_info.audio is not None:
            result["loud_after"] = _loudness(ff, output, out_info.audio.index)[1]

    result["warnings"] = warnings_for(result)
    return result


def warnings_for(result: dict) -> List[str]:
    notes = []
    if result["framing"].scale > UPSCALE_WARN:
        notes.append(f"the picture is enlarged {result['framing'].scale:.1f}x (more than {UPSCALE_WARN}x), "
                     "so it may look soft")
    out_info = result.get("out_info")
    length = out_info.duration if out_info and out_info.duration else result["keep"]
    if length and length > LONG_WARN_S:
        notes.append(f"it is {clock(length)} long; TikTok uploads stop at 10 minutes")
    if result.get("out_bytes") and result["out_bytes"] > BIG_WARN_BYTES:
        notes.append(f"the file is {megabytes(result['out_bytes'])}, over 250 MB; "
                     "a slower upload, and some apps may refuse it")
    return notes


# =================================================================================================
# report
# =================================================================================================

def clock(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown length"
    seconds = max(0.0, seconds)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    return f"{minutes}:{secs:05.2f}"


def megabytes(n: Optional[int]) -> str:
    return "unknown size" if n is None else f"{n / (1024 * 1024):.1f} MB"


def _fps(value: Optional[float]) -> str:
    if not value:
        return "unknown fps"
    return f"{value:g} fps" if abs(value - round(value)) < 0.005 else f"{value:.2f} fps"


def _db(pair: Tuple[Optional[float], Optional[float]]) -> str:
    mean, peak = pair
    if mean is None:
        return "not measured"
    return f"mean {mean:.1f} dB, max {peak:.1f} dB"


def format_report(r: dict) -> str:
    d: Detection = r["detection"]
    f: Framing = r["framing"]
    t: Trim = r["trim"]
    lines = [f"{r['source'].name}" + ("  (dry run: nothing encoded)" if r["dry_run"] else "")]
    depth = f", {r['bit_depth']}-bit" if r["bit_depth"] != 8 else ""
    audio = f", {r['audio_codec']} audio" if r["audio_codec"] else ", no audio"
    lines.append(f"  source    {clock(r['duration'])}, {r['width']}x{r['height']}, {_fps(r['fps'])}, "
                 f"{r['video_codec']}{depth}{audio}, {megabytes(r['source_bytes'])}")
    if d.box is not None:
        lines.append(f"  borders   box {d.box.w}x{d.box.h} at x={d.box.x}, y={d.box.y} "
                     f"(found in {d.found} of {d.sampled} sample frames)")
    elif d.reason == "no-content":
        lines.append(f"  borders   no borders found (no picture found in {d.sampled} sample frames); nothing cropped")
    else:
        lines.append("  borders   no borders found; nothing cropped")
    if f.mode == "exact":
        how = "already 9:16, scaled exactly, no padding"
    elif f.mode == "fit":
        how = f"fits as {f.scaled_w}x{f.scaled_h} with black above/below or beside"
    else:
        how = f"fills the screen; {f.scaled_w}x{f.scaled_h} with the edges cut"
    lines.append(f"  scale     x{f.scale:.2f} to {TARGET_W}x{TARGET_H} ({how})")
    duration = r["duration"] or 0.0
    w: Optional[Window] = r.get("window")
    if w is not None:
        to = "the end" if w.end is None else clock(w.end)
        bound = w.end if w.end is not None else r["duration"]
        length = clock(None if bound is None else bound - w.start)
        lines.append(f"  window    {clock(w.start)} to {to} ({length} of the {clock(r['duration'])} recording)")
    if t.note:
        lines.append(f"  trim      {t.note}")
    elif w is None:
        cut_end = max(0.0, duration - t.end) if t.end is not None else 0.0
        blips = "".join(f"; ignored a {length:.2f} s click at {at:.2f} s" for at, length in t.ignored[:2])
        lines.append(f"  trim      cut {t.start:.2f} s at the start and {cut_end:.2f} s at the end "
                     f"(first sound {t.first_sound:.2f} s, last sound {t.last_sound:.2f} s{blips})")
    else:
        bound = w.end if w.end is not None else duration
        cut_end = max(0.0, bound - t.end) if t.end is not None else 0.0
        blips = "".join(f"; ignored a {length:.2f} s click at {clock(at)}" for at, length in t.ignored[:2])
        lines.append(f"  trim      cut {t.start - w.start:.2f} s at the start and {cut_end:.2f} s at the end "
                     f"of the window (first sound {clock(t.first_sound)}, last sound {clock(t.last_sound)}{blips})")
    fade_in, fade_out = fades_for(t)     # the fades the filter chain applies, never one it dropped
    fades = []
    if fade_in:
        fades.append(f"in over the first {FADE_IN_S:g} s (the copy starts inside sound)")
    if fade_out and r["audio_codec"]:
        fades.append(f"out over the last {FADE_S:g} s" + (" (it ends inside sound)" if t.ends_in_sound else ""))
    if fades:
        lines.append(f"  fades     {'; '.join(fades)}")
    if r["loudnorm"] or r["loud_before"][0] is not None:
        after = _db(r["loud_after"]) if not r["dry_run"] else "measured after a real run"
        lines.append(f"  loudness  before: {_db(r['loud_before'])}; after: {after}")
    if r["dry_run"]:
        lines.append(f"  final     {TARGET_W}x{TARGET_H}, {_fps(r['fps_value'])}, about {clock(r['keep'])} long")
        state = ""
        if r["output_existed"]:
            state = " (already exists: a real run would replace it)" if r["force"] else \
                " (already exists: a real run would refuse without --force)"
        lines.append(f"  output    {r['output']}{state}")
    else:
        o: MediaInfo = r["out_info"]
        ov = o.video if o else None
        size = f"{ov.width}x{ov.height}" if ov else "unknown size"
        lines.append(f"  output    {clock(o.duration if o else None)}, {size}, {_fps(ov.fps if ov else None)}, "
                     f"{megabytes(r['out_bytes'])}")
        lines.append(f"  saved     {r['output']}")
    if r["preview"] is not None:
        lines.append(f"  preview   {r['preview']}")
    if r["dry_run"]:
        lines.append(f"  command   {show_command(r['shown_command'])}")
        lines.append(f"  note      a real run writes '{r['partial'].name}' first and renames it to "
                     f"'{r['output'].name}' when the encode finishes")
    for note in r["warnings"]:
        lines.append(f"  warning   {note}")
    return "\n".join(lines)


def _say(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    try:
        print(text, file=stream, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), file=stream, flush=True)


def os_problem(exc: BaseException) -> str:
    """An OSError as one plain sentence: what could not be used, and why."""
    reason = getattr(exc, "strerror", None) or str(exc) or type(exc).__name__
    where = getattr(exc, "filename", None)
    return f"could not use {where}: {reason}" if where else reason


def options_from_args(args) -> Options:
    """The parser's namespace as Options; --from/--to are parsed here (a TikTokError names the bad one)."""
    times = {}
    for flag, name in (("--from", "start"), ("--to", "end")):
        text = getattr(args, name, None)
        try:
            times[name] = None if text is None else parse_time(text)
        except TikTokError as exc:
            raise TikTokError(f"{flag}: {exc}") from exc
    return Options(out=args.out, force=args.force, dry_run=args.dry_run, preview=args.preview,
                   mode=args.shape, trim=not args.no_trim, lead=args.lead, tail=args.tail,
                   lufs=args.lufs, loudnorm=not args.no_loudnorm, crf=args.crf, fps=args.fps,
                   dropped=getattr(args, "dropped", False), start=times["start"], end=times["end"])


def run_cli(args) -> int:
    """py -m arsenal tiktok: 0 when every video succeeded, 1 when any failed, 2 for a usage problem."""
    try:
        opts = options_from_args(args)
    except TikTokError as exc:
        _say(f"tiktok: {exc}", sys.stderr)
        return 2
    problems = validate(opts)
    if args.latest and args.videos:
        problems.append("give video files or --latest, not both")
    if args.folder and not args.latest:
        problems.append("--folder only goes with --latest")
    if not args.latest and not args.videos:
        problems.append("give one or more videos, or --latest for the newest recording "
                        "(example: py -m arsenal tiktok --latest)")
    if problems:
        for problem in problems:
            _say(f"tiktok: {problem}", sys.stderr)
        return 2
    try:
        ff = find_ffmpeg()
        if args.latest:
            try:
                folder = Path(args.folder) if args.folder else default_folder()
            except (OSError, ImportError) as exc:
                raise TikTokError(f"could not work out the recordings folder ({os_problem(exc)}); "
                                  "name it with --folder") from exc
            videos = [str(latest_video(folder))]
            _say(f"newest recording in {folder}: {Path(videos[0]).name}")
        else:
            videos = list(args.videos)
    except TikTokError as exc:
        _say(f"tiktok: {exc}", sys.stderr)
        return 2
    except OSError as exc:
        _say(f"tiktok: {os_problem(exc)}", sys.stderr)
        return 2
    failures = 0
    for i, video in enumerate(videos):
        if i:
            _say("")
        try:
            _say(format_report(process(video, opts, ffmpeg=ff, many=len(videos) > 1)))
        except TikTokError as exc:
            failures += 1
            _say(f"tiktok: {Path(video).name}: {exc}", sys.stderr)
        except OSError as exc:  # a bad --out, a missing drive, no permission: one sentence, not a traceback
            failures += 1
            _say(f"tiktok: {Path(video).name}: {os_problem(exc)}", sys.stderr)
        except KeyboardInterrupt:
            _say("tiktok: stopped; the unfinished output was removed", sys.stderr)
            return 130
    return 1 if failures else 0
