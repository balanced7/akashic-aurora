"""arsenal.media.league.hud -- where things sit on the League of Legends HUD, and which HUD a frame shows.

ttk_lib.py and five other scripts hard-coded 1080p pixel boxes; Daniel's OBS base resolution became 3840x2160 on
2026-10-11, so every box lives in hud_boxes.json as FRACTIONS of the frame, one set per layout, and box() turns them
into pixels for whatever frame it is given.

Two layouts are known: "replay" (the replay viewer: clock under the score banner, speed in the replay bar) and "live"
(a game being played: clock at the right end of the top-right stats strip). detect_layout() reads the clock in both
places and keeps the one that parses; a frame with neither (loading screen, client, desktop) is "none".
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Dict, Literal, Sequence, Tuple

Layout = Literal["replay", "live", "none"]
LAYOUTS: Tuple[str, ...] = ("replay", "live")
BOXES_FILE = Path(__file__).with_name("hud_boxes.json")

#: A clock read below this confidence does not count as seeing that layout.
MIN_LAYOUT_CONFIDENCE = 0.75


@functools.lru_cache(maxsize=1)
def boxes() -> Dict[str, dict]:
    """{layout: {"measured_on": [w, h], "boxes": {name: [fx, fy, fw, fh]}}} from hud_boxes.json."""
    return json.loads(BOXES_FILE.read_text(encoding="utf-8"))["layouts"]


def fractions(name: str, layout: str) -> Tuple[float, float, float, float]:
    try:
        fx, fy, fw, fh = boxes()[layout]["boxes"][name]
    except KeyError:
        known = {lay: sorted(v["boxes"]) for lay, v in boxes().items()}
        raise KeyError(f"no HUD box {name!r} in layout {layout!r}; known: {known}") from None
    return float(fx), float(fy), float(fw), float(fh)


def _even(v: float) -> int:
    return 2 * int(round(v / 2))


def box(name: str, layout: str, frame_shape: Sequence[int]) -> Tuple[int, int, int, int]:
    """The named box as pixels (x, y, w, h) on a frame of shape (h, w[, c]), clamped inside the frame.

    Every value is even: ffmpeg's crop filter rounds an odd size down on 4:2:0 video, and a raw frame one row short
    of what the reader expects shears every frame after it (measured: a 17-row box on 1280x720 read as garbage)."""
    fh_px, fw_px = int(frame_shape[0]), int(frame_shape[1])
    fx, fy, fw, fh = fractions(name, layout)
    x, y = min(max(0, _even(fx * fw_px)), fw_px - 2), min(max(0, _even(fy * fh_px)), fh_px - 2)
    w, h = max(2, _even(fw * fw_px)), max(2, _even(fh * fh_px))
    return x, y, min(w, (fw_px - x) // 2 * 2), min(h, (fh_px - y) // 2 * 2)


def crop(frame, name: str, layout: str):
    """The named box cut out of a full frame (a view, not a copy)."""
    x, y, w, h = box(name, layout, frame.shape)
    return frame[y:y + h, x:x + w]


def detect_layout(frame) -> Layout:
    """'replay' | 'live' | 'none' for one full RGB frame: whichever layout's clock box reads as a game clock.
    Raises MediaError (naming the fix) when this machine has no clock reader: rapidocr or the digit templates."""
    from . import clock
    best, best_conf = "none", MIN_LAYOUT_CONFIDENCE
    for layout in LAYOUTS:
        game_s, conf = clock.read(crop(frame, "clock", layout))
        if game_s is not None and conf >= best_conf:
            best, best_conf = layout, conf
    return best  # type: ignore[return-value]
