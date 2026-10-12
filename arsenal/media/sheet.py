"""arsenal.media.sheet -- many frames on one labelled picture, and a filmstrip over the sound of the same seconds.

Why it exists: the contact-sheet grid was hand-built 333 times by 68 agents (about 588k output tokens), and agents
read frames one image at a time (134 streaks of 3+ single reads, 560 images, each carried a median 28 turns). One
labelled sheet costs about one image read, so every sheet keeps its long edge at or under max_long_edge (1600 px):
it is never downscaled into unreadable labels on its way into a model.

    sheet(["a.png", ("rec.mp4", 601.5), {"src": "rec.mp4", "t": 640, "crop": (0.45, 0, 0.1, 0.05)}])
    video_sheet("rec.mp4", n=30, cols=6)        # 30 keyframes spread over the file, keyframe-only decode
    filmstrip("rec.mp4", 720, 730)              # 8 frames over the waveform of the same 10 s (1920 x 256)

Every cell is labelled with where it came from (file time; game time too when a clockmap is given), and the index
(<out>.json) says how to get it back: a video cell is decoded by ffmpeg straight to its final size and pasted
unmodified, so frames.at_times(src, [pts], crop=crop, size=size) returns the cell's exact pixels (md5 in the index),
MPEG-TS included: the cells of sheet() and filmstrip() ARE frames.at_times grabs.

The tested ffmpeg recipe (`fps=1/T,...,tile=6x5` with drawtext `%{pts}`) labels tile k with k*T but shows the frame
from k*T + T/2 - 1 frame (the fps filter keeps the last frame of each slot): its labels were up to 5 s early on a
5-minute sheet. Here every label is the shown frame's own pts.

Times are file times (README, "The house clock"): seconds from the file's start, what ffmpeg's `-ss` means and what
probe.keyframes reports. A container whose own clock starts later (MPEG-TS: 1.4 s) changes nothing here; the one
container time read directly, an audio track's start_time, has the format start subtracted. A cell's frame is the
one frames.at_times shows, decoded from the keyframe before it and picked by its own time, never by counting frames
from wherever a seek happened to land.

Measured 2026-10-12 on "2026-10-11 17-51-11.mp4" (33 min, 1080p60 HEVC), software decode, four runs on a machine
other builders were loading:
  video_sheet, 30 keyframes over the whole file: 3.1-4.1 s (one process per keyframe, 0.10 s each; a keyframe-only
    pass costs 27 ms per keyframe in the span, 14 s for all 487); 29 keyframes over 600-720 s: 1.1-1.2 s (one pass)
  video_sheet with exact times (keyframes_only=False), 30 cells: 9.6 s (each decodes from its keyframe; 9.1-12.4 s
    through frames.at_times before _grab replaced it); 12 cells inside 4.4 s: 0.7 s (one decode)
  filmstrip of 10 s with the waveform: 1.5-2.1 s; sampled cells re-grabbed by frames.at_times are bit-identical (9/9)
Re-measured the same evening once _grab became frames.at_times again (house clock slice), quiet machine, two runs:
  video_sheet with exact times, 30 cells: 9.05-9.23 s; filmstrip of 720-730 s: 1.46-1.49 s, 8/8 cells re-grabbed
  bit-identical
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from . import ff, frames, receipt

Item = Union[str, Path, Tuple[str, float], dict]

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")
MAX_LONG_EDGE = 1600
MIN_CELL_H = 8                # px: a shorter cell shows nothing a reader can use, so the layout refuses instead
GAP = 2
BG = (22, 22, 26)
BAND = (10, 10, 12)
INK = (255, 214, 64)          # the recipe's yellow on black: readable over any frame
DIM = (150, 150, 160)
WAVE_PEAK = (120, 200, 255)
WAVE_RMS = (40, 120, 200)
WAVE_FLOOR_DB = -60.0
_FONTS: Dict[int, object] = {}
_CLOCKS: Dict[tuple, Tuple[float, float]] = {}


def _require() -> None:
    """Pillow and numpy draw every sheet: name the missing one in one line instead of a traceback."""
    for module, package in (("PIL", "Pillow"), ("numpy", "numpy")):
        try:
            importlib.import_module(module)
        except ImportError as exc:
            raise ff.MediaError(f"sheets need {package}, which this Python cannot import ({exc})") from None


def _open_image(path: str):
    from PIL import Image
    try:
        return Image.open(path)
    except OSError as exc:            # UnidentifiedImageError is an OSError
        raise ff.MediaError(f"cannot read the image {path}: {exc}") from None


def _file_clock(src) -> Tuple[float, float]:
    """(format start_time, end): where the container's own clock starts (file time 0 on it), and the file time the
    file ends at."""
    p = Path(src)
    st = p.stat()
    key = (str(p.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _CLOCKS:
        fmt = ff.probe_json(p, entries=("-show_entries", "format=start_time,duration")).get("format") or {}
        _CLOCKS[key] = (float(fmt.get("start_time") or 0.0), float(fmt.get("duration") or 0.0))
    return _CLOCKS[key]


def _check_span(src, t0: float, t1: float, fps: float, what: str) -> None:
    """Fail closed on a span the video does not cover (one frame of slack at the end)."""
    end = _file_clock(src)[1]
    frame = 1.0 / fps if fps else 1.0 / 30
    if t0 >= end or t1 > end + frame:
        raise ff.MediaError(f"bad span: {what} {t0:.3f}-{t1:.3f} s is not inside {Path(src).name} "
                            f"(0.000-{end:.3f} s)")


# =================================================================================================
# fonts, times, labels
# =================================================================================================

def _font_candidates() -> List[str]:
    out = []
    spec = importlib.util.find_spec("matplotlib")      # DejaVu ships with matplotlib; located without importing it
    if spec and spec.submodule_search_locations:
        ttf = Path(list(spec.submodule_search_locations)[0]) / "mpl-data" / "fonts" / "ttf"
        out += [str(ttf / "DejaVuSans-Bold.ttf"), str(ttf / "DejaVuSans.ttf")]
    return out + ["DejaVuSans-Bold.ttf", "segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"]


def font(px: int):
    """A TrueType font at px, resolved once from a DejaVu/Segoe/Arial fallback list (Pillow's own font last)."""
    from PIL import ImageFont
    if px not in _FONTS:
        got = None
        for cand in _font_candidates():
            try:
                got = ImageFont.truetype(cand, px)
                break
            except OSError:
                continue
        _FONTS[px] = got if got is not None else ImageFont.load_default(size=px)
    return _FONTS[px]


def fmt_time(t: Optional[float]) -> str:
    """601.5 -> '10:01.500'; 3725.25 -> '1:02:05.250'."""
    if t is None:
        return "?"
    sign = "-" if t < 0 else ""
    ms = int(round(abs(t) * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{sign}{h}:{m:02d}:{s:02d}.{ms:03d}" if h else f"{sign}{m}:{s:02d}.{ms:03d}"


def _game_clock(game_t: float) -> str:
    """The HUD's whole-second clock; a pts a microsecond under a frame boundary must not drop a second."""
    m, s = divmod(int(math.floor(game_t + 1e-4)), 60)
    return f"{m}:{s:02d}"


def clock_fn(clock) -> Optional[Callable[[float], Optional[float]]]:
    """file_t -> game_t, from a studio.clockmap.v1 dict or file (inside a pass, game_t = speed * file_t + offset),
    an object with game_t(file_t), or a callable. None when no clock is given."""
    if clock is None:
        return None
    if hasattr(clock, "game_t"):
        return clock.game_t
    if callable(clock):
        return clock
    if isinstance(clock, (str, Path)):
        clock = json.loads(Path(clock).read_text(encoding="utf-8"))
    if isinstance(clock, dict) and isinstance(clock.get("passes"), list):
        passes = [p for p in clock["passes"] if isinstance(p.get("file"), (list, tuple)) and len(p["file"]) == 2]

        def game_t(file_t: float) -> Optional[float]:
            for p in passes:
                if p["file"][0] <= file_t <= p["file"][1]:
                    return float(p.get("speed", 1.0)) * file_t + float(p["offset"])
            return None
        return game_t
    raise ff.MediaError("clock: give a studio.clockmap.v1 dict or path, an object with game_t(), or a callable")


def _time_label(t: Optional[float], game: Optional[Callable]) -> str:
    text = fmt_time(t)
    g = game(t) if (game is not None and t is not None) else None
    return text + (f"  g {_game_clock(g)}" if g is not None else "")


def _md5(img) -> str:
    import numpy as np
    return hashlib.md5(np.ascontiguousarray(img).tobytes()).hexdigest()


# =================================================================================================
# geometry
# =================================================================================================

def _fit(w: int, h: int, box_w: int, box_h: int) -> Tuple[int, int]:
    """The largest even-sided size with w:h's aspect inside the box."""
    s = min(box_w / w, box_h / h)
    return min(box_w, max(2, int(w * s) // 2 * 2)), min(box_h, max(2, int(h * s) // 2 * 2))


def _zoom_fit(w: int, h: int, box_w: int, box_h: int) -> Tuple[Tuple[int, int], int]:
    """A zoom crop is magnified by a whole factor, nearest neighbour, so its pixels stay visible; a region bigger than
    the cell is scaled down by ffmpeg instead. Returns ((decode w, h), upscale factor)."""
    k = min(box_w // w, box_h // h)
    return ((w, h), k) if k >= 1 else (_fit(w, h, box_w, box_h), 1)


def _auto_cols(n: int, aspect: float) -> int:
    """Columns that make the sheet roughly 16:9, label bands included: 30 cells of 16:9 -> 6 x 5."""
    return max(1, min(n, int(round(math.sqrt(n * (16 / 9) * 1.12 / aspect)))))


def _layout(n: int, cols: int, aspect: float, cell_w: int, labels: bool, title: bool, max_long_edge: int) -> dict:
    """Cell and sheet geometry whose long edge is <= max_long_edge, or a one-line refusal: cells shrink to 16 px wide,
    then (a tall aspect, many rows) get shorter than their aspect and letterbox the picture, never below MIN_CELL_H."""
    rows = max(1, math.ceil(n / cols))

    def geom(cw: int, ch_cap: Optional[int] = None) -> dict:
        ch = max(2, int(round(cw / aspect / 2)) * 2)
        if ch_cap is not None:
            ch = min(ch, ch_cap)
        fpx = max(10, min(18, cw // 17))
        lh = fpx + 6 if labels else 0
        th = fpx + 12 if title else 0
        return {"cell_w": cw, "cell_h": ch, "font_px": fpx, "label_h": lh, "title_h": th, "rows": rows, "cols": cols,
                "w": cols * cw + (cols + 1) * GAP, "h": th + rows * (lh + ch) + (rows + 1) * GAP}

    g = geom(max(16, cell_w))
    scale = min(1.0, max_long_edge / max(g["w"], g["h"]))
    cw = max(16, int(g["cell_w"] * scale) // 2 * 2)
    g = geom(cw)
    while max(g["w"], g["h"]) > max_long_edge and cw > 16:
        cw -= 2
        g = geom(cw)
    if g["h"] > max_long_edge:
        cap = (max_long_edge - (g["h"] - rows * g["cell_h"])) // rows // 2 * 2
        if cap >= MIN_CELL_H:
            g = geom(cw, cap)
    if max(g["w"], g["h"]) > max_long_edge:
        raise ff.MediaError(f"{n} cells in {cols} column(s) x {rows} row(s) cannot fit a sheet of {max_long_edge} px: "
                            f"give {'fewer' if g['w'] > max_long_edge else 'more'} columns, fewer items, or a larger "
                            f"max_long_edge")
    return g


def _cell_xy(g: dict, k: int) -> Tuple[int, int]:
    r, c = divmod(k, g["cols"])
    return GAP + c * (g["cell_w"] + GAP), g["title_h"] + GAP + r * (g["label_h"] + g["cell_h"] + GAP)


# =================================================================================================
# render: cells with pixels -> one PNG + index
# =================================================================================================

def _render(cells: List[dict], g: dict, title: Optional[str], out: Path) -> dict:
    """Paste every cell's img into its box (centred), draw its label band, write the PNG and the index."""
    from PIL import Image, ImageDraw
    canvas = Image.new("RGB", (g["w"], g["h"]), BG)
    draw = ImageDraw.Draw(canvas)
    fnt = font(g["font_px"])
    for c in cells:
        pil = c.pop("img")
        pil = pil if isinstance(pil, Image.Image) else Image.fromarray(pil)
        if c.get("upscale", 1) > 1:
            pil = pil.resize((pil.width * c["upscale"], pil.height * c["upscale"]), Image.NEAREST)
        if pil.width > g["cell_w"] or pil.height > g["cell_h"]:        # an image file larger than its cell
            pil = pil.resize(_fit(pil.width, pil.height, g["cell_w"], g["cell_h"]), Image.LANCZOS)
        x, y = _cell_xy(g, c["i"])
        c["row"], c["col"] = divmod(c["i"], g["cols"])
        ox = x + (g["cell_w"] - pil.width) // 2
        oy = y + g["label_h"] + (g["cell_h"] - pil.height) // 2
        canvas.paste(pil.convert("RGB"), (ox, oy))
        c.update({"x": ox, "y": oy, "w": pil.width, "h": pil.height})
        if g["label_h"] and c.get("label"):
            draw.rectangle([x, y, x + g["cell_w"] - 1, y + g["label_h"] - 1], fill=BAND)
            draw.text((x + 4, y + 2), c["label"], font=fnt, fill=INK)
    if title:
        draw.text((GAP + 4, 4), title, font=font(g["font_px"] + 2), fill=(235, 235, 235))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    index = out.with_suffix(".json")
    payload = {"png": str(out), "index": str(index), "size": [g["w"], g["h"]], "cols": g["cols"], "rows": g["rows"],
               "cell_w": g["cell_w"], "cell_h": g["cell_h"], "cells": cells}
    with open(index, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({k: v for k, v in payload.items() if k != "index"}, fh, indent=1, default=str)
        fh.write("\n")
    return payload


def _default_out(verb: str, stem: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return ff.state_dir() / verb / f"{stem}_{stamp}_{time.perf_counter_ns() % 1_000_000:06d}.png"


def _sources(cells: List[dict]):
    srcs = list(dict.fromkeys(c["src"] for c in cells if c.get("src") and os.path.isfile(c["src"])))
    return None if not srcs else (srcs[0] if len(srcs) == 1 else srcs)


# =================================================================================================
# sheet
# =================================================================================================

def _norm(item: Item, i: int) -> dict:
    if isinstance(item, dict):
        d = dict(item)
    elif isinstance(item, (tuple, list)) and len(item) == 2:
        d = {"src": str(item[0]), "t": float(item[1])}
    elif isinstance(item, (str, Path)):
        d = {"src": str(item)}
    else:
        raise ff.MediaError(f"item {i}: give an image path, (video, t), or a dict {{src, t, crop, label, zoom}}")
    if d.get("image") is None and not d.get("src"):
        raise ff.MediaError(f"item {i}: no src and no image")
    if d.get("src") is not None:
        d["src"] = str(d["src"])
    if d.get("t") is not None:
        d["t"] = float(d["t"])
    if d.get("image") is not None:
        d["kind"] = "array"
        return d
    if not os.path.isfile(d["src"]):
        raise ff.MediaError(f"item {i}: no such file {d['src']}")
    d["kind"] = "image" if Path(d["src"]).suffix.lower() in IMAGE_EXT else "video"
    if d["kind"] == "video" and d.get("t") is None:
        raise ff.MediaError(f"item {i}: {Path(d['src']).name} is a video; give it a time, as (path, t)")
    return d


def _pil(image):
    from PIL import Image
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    import numpy as np
    arr = np.asarray(image)
    if arr.ndim == 2:
        return Image.fromarray(arr.astype("uint8")).convert("RGB")
    return Image.fromarray(np.ascontiguousarray(arr[:, :, :3]).astype("uint8"))


def _full_dims(d: dict, info: Dict[str, dict]) -> Tuple[int, int]:
    if d["kind"] == "video":
        if d["src"] not in info:
            info[d["src"]] = frames.video_info(d["src"])
        return info[d["src"]]["w"], info[d["src"]]["h"]
    if d["kind"] == "image":
        with _open_image(d["src"]) as im:
            return im.size
    return _pil(d["image"]).size


def _load_still(d: dict, crop) -> "Image":
    if d["kind"] == "image":
        with _open_image(d["src"]) as im:
            pil = im.convert("RGB")
    else:
        pil = _pil(d["image"])
    return pil.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3])) if crop else pil


def _grab(src, times: Sequence[float], crop, size) -> List[Tuple[float, "np.ndarray"]]:
    """(time, image) of the frame shown at each time, in the order given: frames.at_times(past_end="last"), so a cell
    IS the grab its index tells you to repeat, bit for bit (the first frame whose time >= t - 1 ms; past the last
    frame, that frame with its own time). Times within at_times' max_gap share one software decode from the keyframe
    before them, MPEG-TS included.

    This replaced a second copy of the same job (2026-10-12): a decode that picked frames by packet pts with -copyts,
    written while at_times still came back empty on MPEG-TS. It labelled cells in container pts, 1.4 s off the file
    clock on a TS."""
    order = sorted(range(len(times)), key=lambda i: times[i])
    got = list(frames.at_times(src, [times[i] for i in order], crop=crop, size=size, pix_fmt="rgb24", hw=None,
                               past_end="last"))
    if len(got) != len(times):
        raise ff.MediaError(f"decoded {len(got)} of the {len(times)} frames wanted from {Path(src).name}")
    out: List[Optional[Tuple[float, "np.ndarray"]]] = [None] * len(times)
    for i, (_t_req, t_pts, img) in zip(order, got):
        out[i] = (round(t_pts, 6), img)
    return out                                # type: ignore[return-value]


def _grab_video(cells: List[dict]) -> None:
    """img and pts for every video cell: one _grab() per (video, crop, size), software decode."""
    groups: Dict[tuple, List[dict]] = {}
    for c in cells:
        key = (c["src"], tuple(c["crop"]) if c["crop"] else None, tuple(c["size"]))
        groups.setdefault(key, []).append(c)
    for (src, crop, size), cs in groups.items():
        for c, (pts, img) in zip(cs, _grab(src, [c["t"] for c in cs], crop, size)):
            c["img"], c["pts"], c["md5"] = img, pts, _md5(img)


def _label(c: dict, d: dict, labels, game, multi: bool) -> Optional[str]:
    if labels in (None, False):
        return None
    if d.get("label") is not None and c["zoom_of"] is None:
        text = str(d["label"])
    elif isinstance(labels, (list, tuple)):
        text = str(labels[c["item"]])
    elif callable(labels):
        text = str(labels(c))
    elif c.get("pts") is None:
        text = Path(c["src"]).name if c.get("src") else f"#{c['item']}"
    else:
        text = _time_label(c["pts"], game)
        if multi and c.get("src"):
            text = f"{Path(c['src']).stem}  {text}"
    if c["zoom_of"] is not None:
        text = (f"zoom x{c['upscale']}  " if c["upscale"] > 1 else "zoom  ") + text
    return text


_SHEET_BLIND = [
    "a sheet is a SAMPLE: what happens between cells is not shown",
    "an item whose aspect differs from the first item's is letterboxed inside the same cell box",
    "labels give each decoded frame's own pts (file time); game time only inside a clockmap pass",
    "a time past the last frame shows the last frame, labelled with its own (earlier) pts",
]


def sheet(items: Sequence[Item], *, cols: Optional[int] = None, cell_w: int = 384, labels="auto",
          zoom: Sequence = (), max_long_edge: int = MAX_LONG_EDGE, title: Optional[str] = None, out=None,
          clock=None, _extra_params: Optional[dict] = None) -> dict:
    """Many frames or images on one labelled grid whose long edge is <= max_long_edge.

    items: image paths, (video, t) pairs, or dicts {src, t, crop, label, zoom, image}; image may be an array or a
    PIL image already in memory (storyboard's thumbs), with src/t kept for the label and the index. crop and zoom
    boxes are pixels, or fractions when all four values are <= 1.0, of the full frame. zoom adds one magnified cell
    per box right after each item. labels: "auto", None/False, a list (one per item) or a callable(cell) -> str.
    clock: a studio.clockmap.v1 (dict or path) to add game time to auto labels."""
    started = time.perf_counter()
    if not items:
        raise ff.MediaError("sheet needs at least one item")
    _require()
    norm = [_norm(it, i) for i, it in enumerate(items)]
    if isinstance(labels, (list, tuple)) and len(labels) != len(norm):
        raise ff.MediaError(f"labels: {len(labels)} given for {len(norm)} items")
    game = clock_fn(clock)
    info: Dict[str, dict] = {}
    cells: List[dict] = []
    for i, d in enumerate(norm):
        fw, fh = _full_dims(d, info)
        c = frames.resolve_crop(d.get("crop"), fw, fh) if d.get("crop") else None
        cells.append({"i": len(cells), "item": i, "src": d.get("src"), "t": d.get("t"), "kind": d["kind"],
                      "crop": list(c) if c else None, "zoom_of": None, "_wh": (c[2], c[3]) if c else (fw, fh)})
        for box in (d["zoom"] if d.get("zoom") is not None else zoom) or ():
            z = frames.resolve_crop(box, fw, fh)
            cells.append({"i": len(cells), "item": i, "src": d.get("src"), "t": d.get("t"), "kind": d["kind"],
                          "crop": list(z), "zoom_of": i, "_wh": (z[2], z[3])})
    aspect = cells[0]["_wh"][0] / cells[0]["_wh"][1]
    ncols = int(cols) if cols else _auto_cols(len(cells), aspect)
    g = _layout(len(cells), ncols, aspect, cell_w, labels not in (None, False), bool(title), max_long_edge)
    for c in cells:
        w, h = c.pop("_wh")
        if c["zoom_of"] is None:
            c["size"], c["upscale"] = list(_fit(w, h, g["cell_w"], g["cell_h"])), 1
        else:
            size, c["upscale"] = _zoom_fit(w, h, g["cell_w"], g["cell_h"])
            c["size"] = list(size)
    _grab_video([c for c in cells if c["kind"] == "video"])
    multi = len({c["src"] for c in cells if c["kind"] == "video"}) > 1
    for c in cells:
        d = norm[c["item"]]
        if c["kind"] != "video":
            c["img"] = _load_still(d, c["crop"])
            c["pts"] = d.get("t")
        c["label"] = _label(c, d, labels, game, multi)
    stem = Path(norm[0]["src"]).stem if norm[0].get("src") else "sheet"
    outp = Path(out) if out else _default_out("sheet", stem)
    payload = _render(cells, g, title, outp)
    payload["wall_s"] = round(time.perf_counter() - started, 3)
    params = {"n_items": len(norm), "cols": cols, "cell_w": cell_w,
              "labels": labels if isinstance(labels, str) or labels in (None, False) else "custom",
              "zoom": [list(z) for z in zoom], "max_long_edge": max_long_edge, "title": title, "out": str(outp),
              "clock": None if clock is None else "given", "hw": None,
              "decode": "from the keyframe before, frames picked by pts, software, scaled by ffmpeg (flags=area)",
              **(_extra_params or {})}
    return receipt.result("sheet", _sources(cells), params, payload, _SHEET_BLIND)


# =================================================================================================
# video_sheet: n frames spread over a span; keyframes only by default (one pass, no inter-frame decode)
# =================================================================================================

def _keyframe_times(src) -> List[float]:
    from .cut import facts            # keyframes cached per (path, size, mtime), shared with cut.plan
    return list(facts(src)["keyframes"])


def _ss(t: float) -> str:
    """A file time as ffmpeg's input -ss takes it: the same number (-ss counts from the format start_time)."""
    return f"{max(0.0, t):.6f}"


def _pick_keyframes(kfs: Sequence[float], targets: Sequence[float]) -> List[float]:
    """The keyframe nearest each target, each used once, in time order."""
    out: List[float] = []
    for t in targets:
        k = min(kfs, key=lambda x: abs(x - t))
        if not out or k > out[-1]:
            out.append(k)
    return out


#: Keyframe decode costs measured 2026-10-12 on the 33-min 1080p60 HEVC file, software decode to 264x148:
#: one process per keyframe 0.10 s each (30 cells: 3.0 s); one `-skip_frame nokey` pass 27 ms per keyframe in the
#: span (all 487: 14 s). The two break even at ~3.7 keyframes per wanted cell; the pass is chosen up to 3.0, a
#: margin for the pass's cost growing with the span while the per-keyframe processes do not.
SCAN_MAX_RATIO = 3.0


def _filter_chain(crop, size) -> str:
    """The same chain frames.at_times builds (crop, then scale with flags=area), so pixels match a re-grab."""
    return ",".join(([f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}"] if crop else [])
                    + [f"scale={size[0]}:{size[1]}:flags=area"])


def _decode_keyframes(src, want: Sequence[float], kfs: Sequence[float], crop, size, fps: float
                      ) -> Iterator[Tuple[float, "np.ndarray"]]:
    """The frame at each wanted keyframe time, decoding nothing but keyframes: one short process per keyframe, or
    one `-skip_frame nokey` pass when the span is dense with wanted keyframes (SCAN_MAX_RATIO)."""
    span = [k for k in kfs if want[0] - 1e-6 <= k <= want[-1] + 1e-6]
    if len(span) <= SCAN_MAX_RATIO * len(want):
        yield from _scan_keyframes(src, want, kfs, span, crop, size, fps)
        return
    import numpy as np
    n = size[0] * size[1] * 3
    for k in want:
        seek = ["-noaccurate_seek", "-ss", _ss(k + 0.25 / fps)] if k > kfs[0] + 1e-6 else []
        res = ff.run(["-v", "error", *seek, "-i", str(src), "-map", "0:v:0", "-frames:v", "1",
                      "-fps_mode", "passthrough", "-vf", _filter_chain(crop, size), "-pix_fmt", "rgb24",
                      "-f", "rawvideo", "pipe:1"], binary=True)
        if len(res.stdout) < n:
            raise ff.MediaError(f"no frame at the keyframe {k:.3f} s of {Path(src).name}")
        yield k, np.frombuffer(res.stdout[:n], np.uint8).reshape(size[1], size[0], 3)


def _scan_keyframes(src, want: Sequence[float], kfs: Sequence[float], span: Sequence[float], crop, size,
                    fps: float) -> Iterator[Tuple[float, "np.ndarray"]]:
    """One `-skip_frame nokey` pass from the first wanted keyframe to the last: the i-th decoded frame is the i-th
    keyframe of the span (the packet-flag list)."""
    import numpy as np
    first, last = want[0], want[-1]
    seeking = first > kfs[0] + 1e-6
    seek = first - 0.5 / fps          # half a frame early: the keyframe before is decoded, then dropped by -ss
    t_from = seek if seeking else 0.0
    args = ["-nostats", "-v", "error", "-skip_frame", "nokey"]
    args += (["-ss", _ss(seek)] if seeking else [])
    args += ["-t", f"{last - t_from + 1.0 / fps:.6f}", "-i", str(src), "-map", "0:v:0",
             "-fps_mode", "passthrough", "-vf", _filter_chain(crop, size), "-pix_fmt", "rgb24", "-f", "rawvideo",
             "pipe:1"]
    proc = ff.popen(args)
    n = size[0] * size[1] * 3
    wanted = {round(k, 6) for k in want}
    got = 0
    try:
        for k in span:
            buf = proc.stdout.read(n)
            if len(buf) < n:
                break
            got += 1
            if round(k, 6) in wanted:
                yield k, np.frombuffer(buf, np.uint8).reshape(size[1], size[0], 3)
    finally:
        if proc.poll() is None:
            proc.kill()
        ff.finish(proc, check=False)
    if got < len(span):
        raise ff.MediaError(f"keyframe decode of {Path(src).name} gave {got} of {len(span)} keyframes")


def video_sheet(src, *, n: int = 30, cols: Optional[int] = 6, start: float = 0.0, end: Optional[float] = None,
                keyframes_only: bool = True, crop=None, out=None, cell_w: int = 384,
                max_long_edge: int = MAX_LONG_EDGE, clock=None, title: Optional[str] = None) -> dict:
    """n frames spread over [start, end) at start + i * (end - start) / n (the 6x5 recipe: 30 frames over 300 s are
    0, 10, ..., 290 s) on one labelled sheet. keyframes_only snaps each time to the nearest keyframe and decodes
    keyframes only, in one pass (near-duplicate picks collapse, so a short span can give fewer cells); with
    keyframes_only=False the exact times are grabbed (each the frame frames.at_times would show)."""
    started = time.perf_counter()
    _require()
    info = frames.video_info(src)
    file_end = _file_clock(src)[1]
    end = float(file_end if end is None else end)
    start = float(start)
    if not (end > start) or n < 1:
        raise ff.MediaError(f"bad span {start}-{end} s (or n < 1)")
    _check_span(src, start, end, info["fps"], "video_sheet")
    targets = [start + i * (end - start) / n for i in range(n)]
    if not keyframes_only:
        return sheet([{"src": str(src), "t": t, "crop": crop} for t in targets], cols=cols, cell_w=cell_w,
                     out=out or _default_out("sheet", Path(src).stem), max_long_edge=max_long_edge, clock=clock,
                     title=title, _extra_params={"n": n, "start": start, "end": end, "keyframes_only": False,
                                                 "crop": crop})
    kfs = _keyframe_times(src)
    in_span = [k for k in kfs if start - 1e-6 <= k < end]
    if not in_span:
        raise ff.MediaError(f"no keyframe in {start}-{end} s of {Path(src).name}; pass keyframes_only=False")
    picks = _pick_keyframes(in_span, targets)
    c = frames.resolve_crop(crop, info["w"], info["h"]) if crop else None
    w0, h0 = (c[2], c[3]) if c else (info["w"], info["h"])
    g = _layout(len(picks), cols or _auto_cols(len(picks), w0 / h0), w0 / h0, cell_w, True, bool(title),
                max_long_edge)
    size = _fit(w0, h0, g["cell_w"], g["cell_h"])
    game = clock_fn(clock)
    cells = []
    for i, (t, img) in enumerate(_decode_keyframes(src, picks, kfs, c, size, info["fps"] or 30.0)):
        cells.append({"i": i, "item": i, "src": str(src), "t": t, "pts": t, "kind": "video",
                      "crop": list(c) if c else None, "zoom_of": None, "size": list(size), "upscale": 1,
                      "img": img, "md5": _md5(img), "label": _time_label(t, game)})
    outp = Path(out) if out else _default_out("sheet", Path(src).stem)
    payload = _render(cells, g, title, outp)
    payload["picked"] = len(cells)
    payload["wall_s"] = round(time.perf_counter() - started, 3)
    params = {"n": n, "cols": cols, "start": start, "end": end, "keyframes_only": True, "crop": crop, "out": str(outp),
              "cell_w": cell_w, "max_long_edge": max_long_edge, "clock": None if clock is None else "given",
              "title": title, "hw": None,
              "decode": "-skip_frame nokey, software decode, scaled by ffmpeg (flags=area) to the cell"}
    blind = _SHEET_BLIND + ["keyframes_only: each cell is the keyframe nearest its target time (OBS: up to "
                            "half a keyframe interval, 2.1 s, away)"]
    return receipt.result("sheet", src, params, payload, blind)


# =================================================================================================
# filmstrip: a row of frames over the waveform of the same seconds
# =================================================================================================

def _audio_track(src, track: int) -> Optional[dict]:
    """The audio track a:track, None when the file has no audio at all; a missing track on a file that has audio
    fails closed with the tracks it does have."""
    j = ff.probe_json(src, entries=("-show_streams",), extra=("-select_streams", "a"))
    streams = j.get("streams") or []
    if not streams:
        return None
    if not 0 <= track < len(streams):
        names = ", ".join(f"{i} {(s.get('tags') or {}).get('title') or '(untitled)'!r}" for i, s in enumerate(streams))
        raise ff.MediaError(f"missing audio track {track}: {Path(src).name} has {len(streams)} ({names})")
    s = streams[track]
    return {"codec": s.get("codec_name"), "sample_rate": int(s.get("sample_rate") or 48000),
            "channels": s.get("channels"), "start": float(s.get("start_time") or 0.0)}


def _envelope(src, t0: float, t1: float, track: int, columns: int, sr: int, *, a_start: float = 0.0):
    """Per-column peak and RMS (linear, 0..1) of one audio track over [t0, t1) (file times), mixed to mono and
    streamed from ffmpeg in 1 MiB chunks: memory stays flat however long the span is. A span that begins before the
    track's first sample (a_start, a file time) leaves its first columns empty: reading this one track, ffmpeg starts
    its output at that sample when it is later than the seek point. Returns (peak, rms, samples decoded)."""
    import numpy as np
    total = max(1, int(round((t1 - t0) * sr)))
    peak = np.zeros(columns)
    sq = np.zeros(columns)
    cnt = np.zeros(columns)
    first = max(t0, a_start)                  # the file time of the first sample ffmpeg hands over
    lead, dur = max(0, int(round((first - t0) * sr))), t1 - first
    if dur <= 0:                              # the track starts after the span ends
        return peak, sq, 0
    # no -ss at the file's start: an explicit `-ss 0` turns AAC priming into ~10 ms of leading zeros
    seek = ["-ss", _ss(t0)] if t0 > 0 else []
    proc = ff.popen(["-v", "error", *seek, "-t", f"{dur:.6f}", "-i", str(src),
                     "-map", f"0:a:{track}", "-ac", "1", "-ar", str(sr), "-f", "f32le", "pipe:1"])
    pos = lead
    rest = b""
    try:
        while True:
            buf = proc.stdout.read(1 << 20)
            if not buf:
                break
            buf, rest = rest + buf, b""
            cut = len(buf) // 4 * 4
            buf, rest = buf[:cut], buf[cut:]
            x = np.frombuffer(buf, np.float32).astype(np.float64)
            if not len(x):
                continue
            idx = np.minimum((np.arange(pos, pos + len(x)) * columns) // total, columns - 1)
            pos += len(x)
            starts = np.concatenate(([0], np.flatnonzero(np.diff(idx)) + 1))
            col = idx[starts]
            np.maximum.at(peak, col, np.maximum.reduceat(np.abs(x), starts))
            np.add.at(sq, col, np.add.reduceat(x * x, starts))
            np.add.at(cnt, col, np.diff(np.concatenate((starts, [len(x)]))))
    finally:
        ff.finish(proc, check=False)
    return np.minimum(peak, 1.0), np.minimum(np.sqrt(sq / np.maximum(cnt, 1)), 1.0), pos - lead


def _db_height(v, half: int):
    import numpy as np
    db = 20 * np.log10(np.maximum(v, 1e-6))
    return np.clip((db - WAVE_FLOOR_DB) / -WAVE_FLOOR_DB, 0, 1) * half


def _load_words(words) -> List[dict]:
    if words is None:
        return []
    if isinstance(words, (str, Path)):
        words = json.loads(Path(words).read_text(encoding="utf-8"))
    if isinstance(words, dict):
        words = words.get("words", [])
    out = []
    for w in words:
        t = w.get("start", w.get("t0", w.get("t")))
        text = str(w.get("word", w.get("text", ""))).strip()
        if t is not None and text:
            out.append({"t": float(t), "text": text})
    return out


def _draw_wave(draw, src, t0: float, t1: float, track: int, meta: Optional[dict], x_w: int, y0: int, wh: int,
               words) -> Optional[dict]:
    fnt = font(13)
    draw.rectangle([0, y0, x_w - 1, y0 + wh - 1], fill=(14, 14, 18))
    if meta is None:
        draw.text((8, y0 + 8), "no audio in this file", font=fnt, fill=INK)
        return None
    mid, half = y0 + (wh - 17) // 2, (wh - 19) // 2
    peak, rms, n_samples = _envelope(src, t0, t1, track, x_w, meta["sample_rate"],
                                     a_start=meta["start"] - _file_clock(src)[0])
    hp, hr = _db_height(peak, half), _db_height(rms, half)
    for x in range(x_w):
        if hp[x] >= 0.5:
            draw.line([x, mid - hp[x], x, mid + hp[x]], fill=WAVE_PEAK)
        if hr[x] >= 0.5:
            draw.line([x, mid - hr[x], x, mid + hr[x]], fill=WAVE_RMS)
    pk = float(peak.max()) if len(peak) else 0.0
    pk_db = round(20 * math.log10(pk), 1) if pk > 0 else None
    note = f"a:{track} peak {pk_db if pk_db is not None else '-inf'} dBFS"
    draw.text((x_w - 8 - draw.textlength(note, font=fnt), y0 + 2), note, font=fnt, fill=DIM)
    placed = -1e9
    for w in _load_words(words):
        if t0 <= w["t"] < t1:
            x = int((w["t"] - t0) / (t1 - t0) * x_w)
            if x >= placed + 4:
                draw.text((x + 2, y0 + 2), w["text"], font=fnt, fill=(235, 235, 235))
                placed = x + 2 + draw.textlength(w["text"], font=fnt)
    return {"track": track, "codec": meta["codec"], "sample_rate": meta["sample_rate"], "samples": n_samples,
            "peak_dbfs": pk_db, "floor_db": WAVE_FLOOR_DB, "scale": "dB"}


_STRIP_BLIND = [
    "one frame per slot: motion inside a slot is not shown",
    "a file with no audio at all gets the strip without a waveform (waveform: null)",
    "the waveform is one track mixed to mono, on a dB scale (-60 dBFS floor): peak (light) over RMS (dark)",
    "a word is drawn where it starts; a word that would overlap the one before is left out",
]


def filmstrip(src, t0: float, t1: float, *, n: int = 8, width: int = 1920, waveform: bool = True, track: int = 0,
              words=None, clock=None, out=None, wave_h: int = 120) -> dict:
    """n frames of [t0, t1) in one row over the waveform of the same seconds; frame i shows the middle of its slot
    [t0 + i*D/n, t0 + (i+1)*D/n), the stretch of waveform drawn under it. Default geometry is the tested recipe:
    8 tiles of 240 x 136 over a 1920 x 120 waveform = 1920 x 256. Tick labels at each slot edge give file time (and
    game time with a clockmap); words (arsenal.stt words.json) are written over the waveform."""
    started = time.perf_counter()
    _require()
    from PIL import Image, ImageDraw
    t0, t1 = float(t0), float(t1)
    if not (t1 > t0) or n < 1:
        raise ff.MediaError(f"bad span {t0}-{t1} s (or n < 1)")
    info = frames.video_info(src)
    _check_span(src, t0, t1, info["fps"], "filmstrip")
    meta = _audio_track(src, track) if waveform else None
    tw = width // n
    th = max(2, int(round(tw * info["h"] / info["w"] / 2)) * 2)
    slot = (t1 - t0) / n
    wh = wave_h if waveform else 0
    canvas = Image.new("RGB", (tw * n, th + wh), BG)
    draw = ImageDraw.Draw(canvas)
    cells = []
    times = [t0 + (i + 0.5) * slot for i in range(n)]
    for i, (t_pts, img) in enumerate(_grab(src, times, None, (tw, th))):
        canvas.paste(Image.fromarray(img), (i * tw, 0))
        cells.append({"i": i, "src": str(src), "t": times[i], "pts": t_pts, "x": i * tw, "y": 0, "w": tw, "h": th,
                      "size": [tw, th], "crop": None, "md5": _md5(img),
                      "slot": [round(t0 + i * slot, 6), round(t0 + (i + 1) * slot, 6)]})
    wave = _draw_wave(draw, src, t0, t1, track, meta, tw * n, th, wh, words) if waveform else None
    game = clock_fn(clock)
    fnt = font(13)
    for i in range(n):
        x, t = i * tw, t0 + i * slot
        if waveform:
            draw.line([x, th, x, th + wh - 1], fill=(70, 70, 80))
            draw.text((x + 3, th + wh - 16), _time_label(t, game), font=fnt, fill=INK)
        else:
            draw.text((x + 3, 2), _time_label(t, game), font=fnt, fill=INK)
    outp = Path(out) if out else _default_out("filmstrip", Path(src).stem)
    outp.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(outp)
    index = outp.with_suffix(".json")
    payload = {"png": str(outp), "index": str(index), "size": [tw * n, th + wh], "tile": [tw, th], "cells": cells,
               "waveform": wave, "wall_s": round(time.perf_counter() - started, 3)}
    with open(index, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({k: v for k, v in payload.items() if k != "index"}, fh, indent=1, default=str)
        fh.write("\n")
    params = {"t0": t0, "t1": t1, "n": n, "width": width, "waveform": waveform, "track": track, "wave_h": wave_h,
              "words": None if words is None else "given", "clock": None if clock is None else "given",
              "out": str(outp), "hw": None, "anchor": "slot middle"}
    return receipt.result("filmstrip", src, params, payload, _STRIP_BLIND)


# =================================================================================================
# CLI
#   py -m arsenal.media sheet a.png b.png rec.mp4@10:01.5 [--cols 6] [--zoom x,y,w,h] [--title T] [--out p.png]
#   py -m arsenal.media sheet --video rec.mp4 [--n 30] [--start 0] [--end 300] [--exact-times] [--crop x,y,w,h]
#   py -m arsenal.media filmstrip rec.mp4 12:00 12:10 [--n 8] [--width 1920] [--track 0] [--words w.json]
# =================================================================================================

def _parse_item(s: str) -> Item:
    if "@" in s:
        path, _, t = s.rpartition("@")
        return (path, frames.parse_time(t))
    return s


def _box(s: Optional[str]):
    return tuple(float(v) for v in s.split(",")) if s else None


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    if verb == "filmstrip":
        ap = argparse.ArgumentParser(prog="py -m arsenal.media filmstrip",
                                     description="filmstrip: a row of frames over the waveform of the same seconds, "
                                                 "to watch 10 s of video in one image")
        ap.add_argument("video")
        ap.add_argument("t0", help="seconds or m:ss(.fff)")
        ap.add_argument("t1", help="seconds or m:ss(.fff)")
        ap.add_argument("--n", type=int, default=8)
        ap.add_argument("--width", type=int, default=1920)
        ap.add_argument("--track", type=int, default=0, help="audio track (a:N) drawn as the waveform")
        ap.add_argument("--no-waveform", action="store_true")
        ap.add_argument("--words", help="words.json (arsenal.stt) written over the waveform")
        ap.add_argument("--clock", help="studio.clockmap.v1 file: game time on the tick labels")
        ap.add_argument("--out")
        a = ap.parse_args(argv)
        res = filmstrip(a.video, frames.parse_time(a.t0), frames.parse_time(a.t1), n=a.n, width=a.width,
                        waveform=not a.no_waveform, track=a.track, words=a.words, clock=a.clock, out=a.out)
        print(json.dumps({k: res[k] for k in ("png", "index", "size", "waveform", "wall_s", "receipt")}, indent=2))
        return 0
    ap = argparse.ArgumentParser(prog="py -m arsenal.media sheet",
                                 description="contact sheet: many frames or images on one labelled grid (file time + "
                                             "game time), long edge <= 1600 px so it costs one image read")
    ap.add_argument("items", nargs="*", help="image paths, or video@time (rec.mp4@10:01.5)")
    ap.add_argument("--video", help="sheet a video (whole, or --start/--end) instead of listed items")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--start", default="0")
    ap.add_argument("--end")
    ap.add_argument("--exact-times", action="store_true", help="grab exact times instead of the nearest keyframes")
    ap.add_argument("--cols", type=int)
    ap.add_argument("--cell-w", type=int, default=384)
    ap.add_argument("--crop", help="x,y,w,h in pixels or fractions (with --video)")
    ap.add_argument("--zoom", action="append", help="x,y,w,h: a magnified cell of this box after each item")
    ap.add_argument("--clock", help="studio.clockmap.v1 file: game time on the labels")
    ap.add_argument("--title")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.video:
        res = video_sheet(a.video, n=a.n, cols=a.cols or 6, start=frames.parse_time(a.start),
                          end=frames.parse_time(a.end) if a.end else None, keyframes_only=not a.exact_times,
                          crop=_box(a.crop), out=a.out, cell_w=a.cell_w, clock=a.clock, title=a.title)
    elif a.items:
        res = sheet([_parse_item(s) for s in a.items], cols=a.cols, cell_w=a.cell_w,
                    zoom=[_box(z) for z in (a.zoom or [])], title=a.title, out=a.out, clock=a.clock)
    else:
        ap.error("give items, or --video <file>")
    print(json.dumps({k: res[k] for k in ("png", "index", "size", "cols", "rows", "cell_w", "wall_s", "receipt")},
                     indent=2))
    return 0
