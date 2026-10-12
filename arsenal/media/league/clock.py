"""arsenal.media.league.clock -- read the League of Legends HUD clock and map video time to game time.

Why it exists: Riot's timeline gives every kill to the millisecond in GAME time, and Daniel's recordings are in FILE
time with replays rewound, slowed to 0.25x/0.5x and skipped. Fifteen agents rewrote a clock reader in 19 transcripts
before this. A clockmap is the bridge: a chain of passes, each `game_t = speed * file_t + offset` over a file span,
written in the studio's studio.clockmap.v1 shape, so "show me the 24:02 fight" finds every pass that shows it.

How it is built (clockmap):
  1. the clock box is read on every keyframe (no inter-frame decode: 487 reads in about 5 s on the 33-minute
     17-51-11, whose keyframes are 4.17 s apart), or every `every` seconds on frames named by their own pts;
  2. reads are chained into runs where one replay speed (0, 0.25, 0.5, 1, 2, 4, 8) and one offset explain every read
     (a read N at file_t says N <= speed * file_t + offset < N + 1, give or take one frame); a read that breaks a run
     while the next reads continue it is a misread and is dropped; a run with no tick of its own hands the next
     pass's first tick back to it (_settle);
  3. edge fit: the gaps between runs are decoded at the full frame rate, then one window per run that still has no
     trusted tick, and again while the joins move. The frame where the seconds digit changes pins an offset to one
     frame x speed (17 ms at 1x, 4 ms at 0.25x) instead of the +-0.5 s a keyframe read gives, and a rewind or skip
     to the exact frame;
  4. where two runs join without a jump (a speed change), the boundary is where their two lines cross.
Convention: the first frame showing second N is game time N exactly (the yuumi/ttk tick fits used the same).
Measured 2026-10-12 on 17-51-11: all 11 hand-calibrated passes reproduced (the four tight ones within 0.042 s),
59 passes and 7 seek transients, about 22 s per 33-minute file with edge fit (40 windows), 5 s without. Four short
slow passes (file 27.4, 470.9, 716.9, 1470.7 s) had borrowed the next pass's first tick and claimed +-0.004 s; they
now fit from their reads and say +-0.29 to 0.37 s.

Reader: RapidOCR recognition-only when it is importable (29/29 on the excerpt, 5.8 ms a crop); otherwise a digit-
template reader on cv2, whose templates are cut from clock crops RapidOCR labelled (`clockmap --train-templates`,
written under <state>/league/digit_templates/, never into the repo: they are Riot's font). Measured on 826 labelled
keyframe crops of 3 recordings (replay and live), even ones building and odd ones held out: 412/412 held-out
reads right, 0 wrong; about 0.4 ms a read; training takes about 40 s.
"""
from __future__ import annotations

import json
import math
import os
import re
import statistics
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple, Union

from .. import api, ff, frames, receipt
from . import hud

_HUD = hud          # the module, for the functions whose `hud` keyword (the spec's name) shadows it
SCHEMA = "studio.clockmap.v1"
SPEEDS: Tuple[float, ...] = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
#: When a short run fits several speeds, the most common replay speeds win.
SPEED_PREFERENCE: Tuple[float, ...] = (1.0, 0.25, 0.5, 2.0, 4.0, 8.0, 0.0)
CLOCK_RE = re.compile(r"(\d{1,2})\s*[:.]\s*(\d{2})")

TEMPLATE_SUBDIR = Path("league") / "digit_templates"
TEMPLATE_FILE = "digits.npz"
LINE_H = 40                 # crops are rescaled to this height before segmentation (resolution independent)
GLYPH_H, GLYPH_W = 24, 16   # each digit is compared at this size
MIN_TEMPLATE_SCORE = 0.70   # lowest digit correlation a template read may have
MIN_TEMPLATE_MARGIN = 0.03  # best minus second-best digit correlation
MIN_RAPID_SCORE = 0.80

OCR_PYTHON_ENV = "ARSENAL_OCR_PYTHON"
NO_READER = ("no clock reader: rapidocr is not installed (Daniel's yes, spec Part 7) and no digit templates exist; "
             "build them once with `py -m arsenal.media clockmap --train-templates <replay.mp4> <live.mp4> "
             f"--ocr-python <python with rapidocr>` (or set {OCR_PYTHON_ENV})")


# =================================================================================================
# glyphs: the clock crop cut into normalised digit patches
# =================================================================================================

def _segment(img) -> Tuple[Optional[list], str]:
    """Digit patches of an 'MM:SS' clock crop, or (None, why). The minimum over channels keeps the white clock and
    drops coloured things that drift into the box (a pink spell effect read as a fifth glyph in max-channel)."""
    import cv2
    import numpy as np
    g = img.min(axis=2) if img.ndim == 3 else img
    g = g.astype(np.float32)
    h, w = g.shape
    if h < 6 or w < 12:
        return None, "crop too small"
    scale = LINE_H / h
    g = cv2.resize(g, (max(1, int(round(w * scale))), LINE_H), interpolation=cv2.INTER_CUBIC)
    lo, hi = float(np.percentile(g, 50)), float(np.percentile(g, 99.5))
    if hi - lo < 50:
        return None, "no contrast"
    mask = (g > lo + 0.5 * (hi - lo)).astype(np.uint8)
    n, _lab, st, _cen = cv2.connectedComponentsWithStats(mask, connectivity=8)
    H, W = mask.shape
    comps = [st[i].tolist() for i in range(1, n)
             if st[i][4] >= 6 and st[i][0] > 0 and st[i][0] + st[i][2] < W]   # edge-cut blobs are icons/neighbours
    if not comps:
        return None, "nothing bright"
    hmax = max(c[3] for c in comps)
    tall = sorted((c for c in comps if c[3] >= 0.75 * hmax), key=lambda c: c[0])
    if len(tall) < 3:
        return None, f"{len(tall)} glyphs"
    top = int(statistics.median(c[1] for c in tall))
    bot = int(statistics.median(c[1] + c[3] for c in tall))
    dh = max(1, bot - top)
    wexp = 0.78 * dh                                     # a digit's width; '1' is narrower, two touching are wider
    cells = []
    for x, _y, cw, _ch, _a in tall:
        k = max(1, int(round(cw / wexp))) if cw > 1.3 * wexp else 1
        cells += [(x + j * cw / k, cw / k) for j in range(k)]
    if len(cells) != 4:
        return None, f"{len(cells)} glyphs"
    dots = [c for c in comps if c[3] < 0.45 * dh and c[2] < 0.6 * dh and top - 2 <= c[1] and c[1] + c[3] <= bot + 2]
    centres = [x + cw / 2 for x, cw in cells]
    colons = [(a[0] + a[2] / 2 + b[0] + b[2] / 2) / 2 for i, a in enumerate(dots) for b in dots[i + 1:]
              if abs((a[0] + a[2] / 2) - (b[0] + b[2] / 2)) <= 2.5 and abs(a[1] - b[1]) >= 0.25 * dh]
    if not any(centres[1] < cx < centres[2] for cx in colons):
        return None, "no colon between the minutes and the seconds"
    patches = []
    for x, cw in cells:
        x0, x1 = max(0, int(np.floor(x)) - 1), min(W, int(np.ceil(x + cw)) + 1)
        p = cv2.resize(g[max(0, top - 1):min(H, bot + 1), x0:x1], (GLYPH_W, GLYPH_H), interpolation=cv2.INTER_AREA)
        p = p - p.mean()
        patches.append((p / (float(np.linalg.norm(p)) or 1.0)).astype(np.float32))
    return patches, ""


# =================================================================================================
# readers
# =================================================================================================

def _parse(text: str) -> Optional[int]:
    m = CLOCK_RE.search(text or "")
    if not m or int(m.group(2)) >= 60:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


class TemplateReader:
    """Digit templates cut from RapidOCR-labelled crops of Daniel's recordings (Riot's font, kept local)."""

    name = "templates"

    def __init__(self, path: Path):
        import numpy as np
        with np.load(path) as z:
            self.glyphs = z["glyphs"].astype(np.float32)        # (10, GLYPH_H, GLYPH_W), each zero-mean unit-norm
            self.count = z["count"].tolist()
        self.path = path
        self.flat = self.glyphs.reshape(10, -1)
        if self.glyphs.shape[1:] != (GLYPH_H, GLYPH_W) or min(self.count) == 0:
            raise ff.MediaError(f"digit templates at {path} are incomplete or from another version; "
                                f"rebuild them with `clockmap --train-templates`")

    def read_text(self, img) -> Tuple[Optional[str], float]:
        import numpy as np
        patches, _why = _segment(img)
        if patches is None:
            return None, 0.0
        scores = np.stack([p.reshape(-1) for p in patches]) @ self.flat.T          # (4, 10) correlations
        order = np.argsort(-scores, axis=1)
        best = scores[np.arange(4), order[:, 0]]
        margin = best - scores[np.arange(4), order[:, 1]]
        if best.min() < MIN_TEMPLATE_SCORE or margin.min() < MIN_TEMPLATE_MARGIN:
            return None, float(best.min())
        d = "".join(str(int(i)) for i in order[:, 0])
        return f"{d[:2]}:{d[2:]}", float(best.min())

    def read(self, img) -> Tuple[Optional[int], float]:
        text, conf = self.read_text(img)
        n = _parse(text) if text else None
        return n, (conf if n is not None else 0.0)


class RapidReader:
    """RapidOCR (PP-OCR ONNX) in recognition-only mode on the clock crop."""

    name = "rapidocr"

    def __init__(self):
        import logging
        from rapidocr import RapidOCR
        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        self.engine = RapidOCR()

    def read_text(self, img) -> Tuple[str, float]:
        import numpy as np
        r = self.engine(np.ascontiguousarray(img[:, :, ::-1]) if img.ndim == 3 else img, use_det=False,
                        use_cls=False)
        txts, scores = getattr(r, "txts", None) or (), getattr(r, "scores", None) or ()
        return (txts[0] if txts else ""), (float(scores[0]) if scores else 0.0)

    def read(self, img) -> Tuple[Optional[int], float]:
        text, score = self.read_text(img)
        n = _parse(text)
        return (n, score) if n is not None and score >= MIN_RAPID_SCORE else (None, 0.0)


def template_paths() -> List[Path]:
    """Where digit templates are looked for: <state>, then the repo's default state (so a test that relocates
    state for isolation still finds the ones this machine built)."""
    out = [ff.state_dir() / TEMPLATE_SUBDIR / TEMPLATE_FILE,
           ff._default_state_dir() / TEMPLATE_SUBDIR / TEMPLATE_FILE]
    return list(dict.fromkeys(out))


def find_templates() -> Optional[Path]:
    return next((p for p in template_paths() if p.is_file()), None)


def rapidocr_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("rapidocr") is not None


_readers: Dict[str, object] = {}


def get_reader(kind: str = "auto"):
    """'auto' (rapidocr when importable, else templates), 'rapidocr' or 'templates'; raises MediaError naming the
    fix when neither exists."""
    if kind == "auto":
        kind = "rapidocr" if rapidocr_available() else "templates"
    if kind in _readers:
        return _readers[kind]
    if kind == "rapidocr":
        if not rapidocr_available():
            raise ff.MediaError("reader 'rapidocr' asked for, but rapidocr is not installed in this Python")
        rd = RapidReader()
    elif kind == "templates":
        path = find_templates()
        if path is None:
            raise ff.MediaError(NO_READER)
        rd = TemplateReader(path)
    else:
        raise ff.MediaError(f"unknown clock reader {kind!r}: auto, rapidocr or templates")
    _readers[kind] = rd
    return rd


def read(img, *, reader: str = "auto") -> Tuple[Optional[int], float]:
    """(game seconds shown, confidence) for one clock crop; (None, 0.0) when it does not read as MM:SS."""
    return get_reader(reader).read(img)


# =================================================================================================
# training the template reader (offline, once per machine)
# =================================================================================================

_LABEL_SCRIPT = r"""
import json, logging, sys
from pathlib import Path
import numpy as np
from PIL import Image
from rapidocr import RapidOCR
logging.disable(logging.INFO)
eng = RapidOCR()
out = {}
for p in sorted(Path(sys.argv[1]).glob("*.png")):
    img = np.asarray(Image.open(p).convert("RGB"))[:, :, ::-1]
    r = eng(np.ascontiguousarray(img), use_det=False, use_cls=False)
    t = list(getattr(r, "txts", None) or [""])[0]
    s = list(getattr(r, "scores", None) or [0.0])[0]
    out[p.name] = [t, float(s)]
print(json.dumps(out))
"""


def _label(crops: Sequence, ocr_python: Optional[str]) -> List[Tuple[str, float]]:
    """RapidOCR text and score for each crop: in this Python when rapidocr imports, else in `ocr_python`."""
    if rapidocr_available():
        rd = RapidReader()
        return [rd.read_text(c) for c in crops]
    if not ocr_python:
        raise ff.MediaError("labelling clock crops needs rapidocr: pass --ocr-python <python.exe with rapidocr> "
                            f"(or set {OCR_PYTHON_ENV}); this Python lacks it")
    from PIL import Image
    with tempfile.TemporaryDirectory(prefix="clock-label-", dir=str(_scratch_dir())) as tmp:
        for i, c in enumerate(crops):
            Image.fromarray(c).save(Path(tmp) / f"{i:06d}.png")
        try:
            proc = subprocess.run([ocr_python, "-c", _LABEL_SCRIPT, tmp], capture_output=True, timeout=1800)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ff.MediaError(f"the labelling Python {ocr_python!r} failed to run: {exc}") from exc
        if proc.returncode != 0:
            tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
            raise ff.MediaError(f"the labelling Python exited {proc.returncode}: {' | '.join(tail)}")
        got = json.loads(proc.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
    return [tuple(got.get(f"{i:06d}.png", ["", 0.0])) for i in range(len(crops))]


def _scratch_dir() -> Path:
    d = ff.state_dir() / "league" / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _keyframe_crops(src, box) -> Tuple[List[float], list]:
    ts, crops = [], []
    for t, img in frames.keyframes(src, crop=box):
        ts.append(t)
        crops.append(img.copy())
    return ts, crops


def _templates_from(labelled: Iterable[Tuple[object, str]]):
    """Mean normalised glyph per digit over crops whose label is MM:SS and that segment into exactly 4 digits."""
    import numpy as np
    acc: Dict[int, list] = {d: [] for d in range(10)}
    for img, text in labelled:
        m = re.fullmatch(r"(\d{2}):(\d{2})", (text or "").strip())
        if not m or int(m.group(2)) >= 60:
            continue
        patches, _why = _segment(img)
        if patches is None:
            continue
        for ch, p in zip(m.group(1) + m.group(2), patches):
            acc[int(ch)].append(p)
    glyphs = np.zeros((10, GLYPH_H, GLYPH_W), np.float32)
    count = np.array([len(acc[d]) for d in range(10)], np.int32)
    for d in range(10):
        if acc[d]:
            t = np.mean(acc[d], axis=0)
            t = t - t.mean()
            glyphs[d] = t / (float(np.linalg.norm(t)) or 1.0)
    return glyphs, count


def train_templates(videos: Sequence, *, hud: Optional[str] = None, ocr_python: Optional[str] = None,
                    out_dir=None, min_score: float = 0.9) -> dict:
    """Cut the digit templates from keyframe clock crops of `videos`, labelled by RapidOCR, and say how well they
    read the crops they were not built from (even keyframes build, odd ones test; then all of them build).
    hud: 'replay' or 'live' for every video; None tries both layouts per video and keeps the one that labels more."""
    import numpy as np
    t_start = time.perf_counter()
    ocr_python = ocr_python or os.environ.get(OCR_PYTHON_ENV)
    labelled, sources = [], []
    for v in videos:
        info = frames.video_info(v)
        layouts = [hud] if hud else list(_HUD.LAYOUTS)
        best = None
        for layout in layouts:
            _ts, crops = _keyframe_crops(v, _HUD.box("clock", layout, (info["h"], info["w"])))
            labels = _label(crops, ocr_python)
            parsed = [(c, _parse(t), s) for c, (t, s) in zip(crops, labels)]
            # the label is the clock RapidOCR found, as MM:SS ("09:09 anisit" had chat text in the box)
            ok = [(c, f"{n // 60:02d}:{n % 60:02d}") for c, n, s in parsed if s >= min_score and n is not None]
            if best is None or len(ok) > len(best[1]):
                best = (layout, ok, len(crops))
        layout, ok, n = best
        labelled.append(ok)
        sources.append({**receipt.source(v), "layout": layout, "keyframes": n, "labelled": len(ok)})
    train = [x for crops in labelled for i, x in enumerate(crops) if i % 2 == 0]
    test = [x for crops in labelled for i, x in enumerate(crops) if i % 2 == 1]
    glyphs, count = _templates_from(train)
    if count.min() == 0:
        missing = [d for d in range(10) if count[d] == 0]
        raise ff.MediaError(f"the labelled crops never showed digit(s) {missing}; add a longer recording")
    probe = _template_probe(glyphs, count)
    right = wrong = refused = 0
    for img, text in test:
        got, _conf = probe.read_text(img)
        if got is None:
            refused += 1
        elif got == text.strip():
            right += 1
        else:
            wrong += 1
    glyphs, count = _templates_from(train + test)
    out = Path(out_dir) if out_dir else ff.state_dir() / TEMPLATE_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / TEMPLATE_FILE, glyphs=glyphs, count=count)
    manifest = {"api": api("clockmap.templates"), "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "labeller": "rapidocr (recognition only)", "min_label_score": min_score,
                "glyph": [GLYPH_H, GLYPH_W], "line_h": LINE_H, "count": count.tolist(), "sources": sources,
                "held_out": {"n": len(test), "right": right, "wrong": wrong, "refused": refused},
                "wall_s": round(time.perf_counter() - t_start, 2),
                "note": "Cut from Riot's game font in Daniel's recordings: local only, never committed."}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _readers.pop("templates", None)
    return {**manifest, "path": str(out / TEMPLATE_FILE)}


def _template_probe(glyphs, count) -> TemplateReader:
    rd = TemplateReader.__new__(TemplateReader)
    rd.glyphs, rd.count, rd.path = glyphs, count.tolist(), None
    rd.flat = glyphs.reshape(10, -1)
    return rd


# =================================================================================================
# runs: reads chained under one speed and one offset
# =================================================================================================

@dataclass
class _Run:
    """Reads (file_t, N) explained by game = speed * file_t + offset for some speed in `feas`."""
    eps_frames: float
    fps: float
    reads: List[Tuple[float, int]] = field(default_factory=list)
    feas: Dict[float, Tuple[float, float]] = field(default_factory=dict)

    def _bounds(self, s: float, t: float, n: int) -> Tuple[float, float]:
        eps = self.eps_frames * max(s, 0.25) / self.fps
        return n - s * t - eps, n + 1 - s * t + eps

    def trial(self, t: float, n: int) -> Dict[float, Tuple[float, float]]:
        cand = self.feas if self.reads else {s: (-1e12, 1e12) for s in SPEEDS}
        out = {}
        for s, (lo, hi) in cand.items():
            a, b = self._bounds(s, t, n)
            lo2, hi2 = max(lo, a), min(hi, b)
            if lo2 < hi2:
                out[s] = (lo2, hi2)
        return out

    def add(self, t: float, n: int) -> bool:
        nxt = self.trial(t, n)
        if not nxt:
            return False
        self.feas = nxt
        self.reads.append((t, n))
        return True

    @property
    def t0(self) -> float:
        return self.reads[0][0]

    @property
    def t1(self) -> float:
        return self.reads[-1][0]

    def speed(self) -> float:
        return next(s for s in SPEED_PREFERENCE if s in self.feas)

    def ticks(self) -> List[Tuple[float, int]]:
        """(file_t of the first frame showing N, N) wherever two reads one frame apart differ by one second."""
        gap = 1.5 / self.fps
        return [(t1, n1) for (t0, n0), (t1, n1) in zip(self.reads, self.reads[1:]) if n1 == n0 + 1 and t1 - t0 <= gap]

    def trusted_ticks(self) -> List[Tuple[float, int]]:
        """Ticks followed by most of a tick interval inside the run. A run whose offset is still loose can swallow
        the first tick of the NEXT pass after a speed change (it shows up near the run's end); this drops it."""
        s = self.speed()
        if s <= 0:
            return []
        return [(t, n) for t, n in self.ticks() if self.t1 - t >= 0.9 / s]


def _chain(reads: Sequence[Tuple[float, Optional[int]]], fps: float, eps_frames: float = 1.0,
           lookahead: int = 3) -> Tuple[List[_Run], List[Tuple[float, int]]]:
    """Greedy runs over time-sorted reads; a read that breaks a run while most of the next `lookahead` reads still
    fit it is a misread (dropped and returned)."""
    good = sorted({(t, n) for t, n in reads if n is not None})     # a frame two windows both read counts once
    runs: List[_Run] = []
    dropped: List[Tuple[float, int]] = []
    for i, (t, n) in enumerate(good):
        if runs and runs[-1].add(t, n):
            continue
        if runs:
            ahead = good[i + 1:i + 1 + lookahead]
            probe = _Run(eps_frames, fps, list(runs[-1].reads), dict(runs[-1].feas))
            fit = sum(1 for ta, na in ahead if probe.add(ta, na))
            if ahead and fit >= min(2, len(ahead)):
                dropped.append((t, n))
                continue
        run = _Run(eps_frames, fps)
        run.add(t, n)
        runs.append(run)
    return _settle(runs, fps, eps_frames), dropped


def _rebuilt(reads: Sequence[Tuple[float, int]], fps: float, eps_frames: float) -> _Run:
    run = _Run(eps_frames, fps)
    for t, n in sorted(reads):
        run.add(t, n)                      # a subset of reads one run already held: every one fits
    return run


def _settle(runs: List[_Run], fps: float, eps_frames: float) -> List[_Run]:
    """Hand a run's tail to the next run when the next run's line explains the tick that starts it.

    The greedy chain keeps a slow run with no tick of its own going after a speed change: its offset is loose, so the
    first tick of the NEXT pass fits it too (a 2 s 0.25x tap swallowed the 1x pass's first tick and reported offset
    109.475 +-0.008 for a truth of 109.4; on 17-51-11, 1.7 s of 12:28 at file 27.4 claimed 0.25x +-0.004 off the 1x
    pass's first tick). If the next run's line explains that tick, the frame before it included, the tick and
    everything after it may be the next pass's: they move there, and this run keeps only what it alone explains, so
    its fit falls back to its reads and states their width. A tick the next line cannot explain stays.

    Only a run with no trusted tick gives, and only to a run pinned by trusted ticks: a loose next line explains
    anything continuous (a 3-frame seek transient took the last tick of a 400 s 1x pass and became a fake 0.25x
    pass when this rule was missing)."""
    out = list(runs)
    i = 0
    while i < len(out) - 1:
        a, b = out[i], out[i + 1]
        if a.trusted_ticks() or not b.trusted_ticks():
            i += 1
            continue
        index = {r: k for k, r in enumerate(a.reads)}                # reads are unique (see _chain)
        for tick in a.ticks():
            k = index[tick]
            head, tail = a.reads[:k], a.reads[k:]
            probe = _Run(eps_frames, fps, list(b.reads), dict(b.feas))
            if all(probe.add(t, n) for t, n in (head[-1], *tail)):
                out[i] = _rebuilt(head, fps, eps_frames)
                out[i + 1] = _rebuilt([*tail, *b.reads], fps, eps_frames)
                break
        i += 1
    return out


def _fit(run: _Run, fps: float) -> dict:
    """speed, offset and its tolerance for one run: from ticks when it saw any, else the middle of the interval.
    A tick near the run's end is used only when no trusted tick exists: _settle has already moved every tick the
    next run's line explains, so what is left is this run's own."""
    s = run.speed()
    ticks = run.trusted_ticks() or run.ticks()
    if s > 0 and len(ticks) >= 2:                          # tick spacing names the speed exactly
        (ta, na), (tb, nb) = ticks[0], ticks[-1]
        if tb - ta > 0.5:
            measured = (nb - na) / (tb - ta)
            near = min((x for x in SPEEDS if x > 0 and x in run.feas), key=lambda x: abs(x - measured), default=s)
            s = near
    lo, hi = run.feas[s]
    frame = 1.0 / fps
    if s > 0 and ticks:
        offs = [n - s * t for t, n in ticks]
        off = statistics.median(offs)
        spread = (max(offs) - min(offs)) / 2 if len(offs) > 1 else 0.0
        tol = max(s * frame, spread)
        how = "ticks"
    else:
        eps = run.eps_frames * max(s, 0.25) * frame
        lo_s, hi_s = lo + eps, hi - eps
        if lo_s >= hi_s:
            lo_s, hi_s = lo, hi
        off, tol, how = (lo_s + hi_s) / 2, (hi_s - lo_s) / 2, "reads"
    return {"speed": s, "offset": off, "tol_s": tol, "fit": how, "n_ticks": len(ticks), "speeds_possible":
            sorted(run.feas)}


# =================================================================================================
# clockmap
# =================================================================================================

def _read_window(src, start: float, dur: float, box, rd) -> List[Tuple[float, Optional[int]]]:
    """Every frame of [start, start+dur) read (the dense pass edge fit uses). The clock crop is byte-identical to the
    previous frame most of the time (227 of 250 frames in a 0.25x window), so an unchanged crop reuses its read."""
    import numpy as np
    out: List[Tuple[float, Optional[int]]] = []
    prev, prev_n = None, None
    for t, img in frames.frames(src, start=max(0.0, start), dur=dur, crop=box):
        if t is None:
            continue
        if prev is None or not np.array_equal(prev, img):
            prev, prev_n = img, rd.read(img)[0]
        out.append((t, prev_n))
    return out


def tick_offset(src, layout: str, near_file_t: float, *, speed: float = 1.0, reader: str = "auto") -> Optional[float]:
    """The offset (game_t - speed * file_t) one clock tick pins near near_file_t, or None when no tick reads there.
    One tick is enough when the speed is known, e.g. a live game (league.live calibrate=True)."""
    info = frames.video_info(src)
    fps = info["fps"] or 60.0
    box = hud.box("clock", layout, (info["h"], info["w"]))
    reads = [(t, n) for t, n in _read_window(src, near_file_t, 1.0 / max(speed, 0.25) + 4.0 / fps, box,
                                             get_reader(reader)) if n is not None]
    for (t0, n0), (t1, n1) in zip(reads, reads[1:]):
        if n1 == n0 + 1 and t1 - t0 <= 1.5 / fps:
            return n1 - speed * t1
    return None


def _joins(runs: List["_Run"], step: float, frame: float) -> List[Tuple[float, float]]:
    """The gaps between runs, as decode spans. A span starts ON the earlier run's last read (a keyframe, when that
    read is a sample), so the decoder has next to no pre-roll."""
    spans: List[Tuple[float, float]] = []
    for a, b in zip(runs, runs[1:]):
        if b.t0 - a.t1 <= 1.5 * frame:
            continue                                      # already frame-adjacent
        if b.t0 - a.t1 <= 2.5 * step:
            spans.append((a.t1, b.t0 + frame))
        else:                                             # a long unreadable stretch: only its two edges
            spans += [(a.t1, a.t1 + step), (b.t0 - step, b.t0 + frame)]
    return spans


def _merge(spans: Iterable[Tuple[float, float]], bridge_s: float = 2.0) -> List[Tuple[float, float]]:
    """Spans closer than bridge_s as one ffmpeg call: starting a decoder and seeking costs more than decoding the
    two seconds between them."""
    merged: List[Tuple[float, float]] = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1] + bridge_s:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _tick_spans(r: "_Run", samples, frame: float, tick_every_s: float,
                max_tick_windows: int) -> List[Tuple[float, float]]:
    """Windows inside a run, each starting on a keyframe and one tick interval long, until the run holds one trusted
    tick per tick_every_s of its length (at most max_tick_windows)."""
    s = r.speed()
    want = min(max_tick_windows, 1 + int((r.t1 - r.t0) / tick_every_s)) - len(r.trusted_ticks())
    if s <= 0 or want <= 0:
        return []
    ks = [t for t, _n in samples if r.t0 <= t <= r.t1 - 1.0 / s] or [r.t0]
    out = []
    for j in range(want):
        k = ks[min(len(ks) - 1, (2 * j + 1) * len(ks) // (2 * want))]
        out.append((k, k + min(1.0 / s + 4 * frame, max(r.t1 - k, 0.0) + 2 * frame)))
    return out


def _edge_fit(src, box, rd, samples, fps: float, eps_frames: float, tick_every_s: float, max_tick_windows: int,
              span: Tuple[float, float], max_rounds: int = 5):
    """Decode the joins and tick windows at the full frame rate, re-chain, and repeat while the joins move: a run
    pinned by its first true tick stops swallowing its neighbour's reads, which uncovers the real join. The stretch
    before the first read and after the last one (up to one sample step) is read too, so the outer passes reach the
    first and last frame that shows the clock."""
    frame = 1.0 / fps
    step = statistics.median(b[0] - a[0] for a, b in zip(samples, samples[1:])) if len(samples) > 1 else 4.0
    reads = list(samples)
    decoded: List[Tuple[float, float]] = []
    calls = 0

    def covered(a: float, b: float) -> bool:
        return any(x <= a + 1e-6 and b <= y + 1e-6 for x, y in decoded)

    for _round in range(max_rounds):
        runs, _dropped = _chain(reads, fps, eps_frames)
        todo = [sp for sp in _joins(runs, step, frame) if not covered(*sp)]
        if runs and runs[0].t0 - span[0] > 1.5 * frame:
            todo.append((max(span[0], runs[0].t0 - step), runs[0].t0 + frame))
        if runs and span[1] - runs[-1].t1 > 1.5 * frame:
            todo.append((runs[-1].t1, min(span[1], runs[-1].t1 + step)))
        todo = [sp for sp in todo if not covered(*sp)]
        if _round:                         # the joins first: their frames hold most runs' ticks already
            for r in runs:
                todo += [sp for sp in _tick_spans(r, samples, frame, tick_every_s, max_tick_windows)
                         if not covered(*sp)]
        if not todo:
            break
        for a, b in _merge(todo):
            reads += _read_window(src, a, b - a, box, rd)
            decoded.append((a, b))
            calls += 1
    runs, dropped = _chain(reads, fps, eps_frames)
    return reads, runs, dropped, calls


def _detect_hud(src, info: dict, rd, max_keyframes: int = 150, need: int = 5) -> str:
    """Which layout this recording shows: read both clock boxes on keyframes until one has `need` reads."""
    shape = (info["h"], info["w"])
    bx = {lay: hud.box("clock", lay, shape) for lay in hud.LAYOUTS}
    x0, y0 = min(b[0] for b in bx.values()), min(b[1] for b in bx.values())
    x1, y1 = max(b[0] + b[2] for b in bx.values()), max(b[1] + b[3] for b in bx.values())
    votes: Counter = Counter()
    gen = frames.keyframes(src, crop=(x0, y0, x1 - x0, y1 - y0))
    try:
        for k, (_t, img) in enumerate(gen):
            for lay, (x, y, w, h) in bx.items():
                if rd.read(img[y - y0:y - y0 + h, x - x0:x - x0 + w])[0] is not None:
                    votes[lay] += 1
            if (votes and votes.most_common(1)[0][1] >= need) or k + 1 >= max_keyframes:
                break
    finally:
        gen.close()
    return votes.most_common(1)[0][0] if votes else "none"


def _pass_id(game_t: float, speed: float, used: set) -> str:
    g = max(0, int(game_t))
    base = f"p{g // 60:02d}{g % 60:02d}_{speed:g}x"
    pid, k = base, 1
    while pid in used:
        k += 1
        pid = f"{base}{chr(ord('a') + k - 1)}"
    used.add(pid)
    return pid


def _passes(runs: List[_Run], fps: float) -> Tuple[List[dict], List[dict]]:
    """Runs -> studio passes + the events between them (rewind, skip_forward, speed_change)."""
    frame = 1.0 / fps
    fits = [_fit(r, fps) for r in runs]
    spans = [[r.t0, r.t1] for r in runs]
    events = []
    for i in range(len(runs) - 1):
        a, b = fits[i], fits[i + 1]
        ta, tb = runs[i].t1, runs[i + 1].t0
        cross, reach = None, 0.0
        if abs(a["speed"] - b["speed"]) > 1e-9:
            cross = (b["offset"] - a["offset"]) / (a["speed"] - b["speed"])
            reach = 1.0 / abs(a["speed"] - b["speed"])     # how long reads can fit both lines after the change
        slack = 2 * frame + a["tol_s"] + b["tol_s"]
        if cross is not None and max(spans[i][0], ta - reach) - slack <= cross <= tb + slack:
            t_b = min(max(cross, spans[i][0]), spans[i + 1][1])
            spans[i][1] = max(spans[i][0], t_b)
            spans[i + 1][0] = min(t_b, spans[i + 1][1])
            kind, at = "speed_change", t_b
            tol = (a["tol_s"] + b["tol_s"]) / abs(a["speed"] - b["speed"])   # the crossing moves with both offsets
        else:
            g_before = a["speed"] * ta + a["offset"]
            g_after = b["speed"] * tb + b["offset"]
            kind = "rewind" if g_after < g_before else "skip_forward"
            at, tol = tb, max(frame, tb - ta)                   # the jump is somewhere after the last old frame
        events.append({"file_t": round(at, 4), "tol_s": round(max(tol, 1e-4), 4), "kind": kind, "from_pass": i,
                       "to_pass": i + 1, "from_speed": a["speed"], "to_speed": b["speed"],
                       "gap_s": round(max(0.0, tb - ta), 4) if kind != "speed_change" else 0.0})
    used: set = set()
    out = []
    for r, f, (f0, f1) in zip(runs, fits, spans):
        g0 = f["speed"] * f0 + f["offset"]
        out.append({"id": _pass_id(g0, f["speed"], used), "file": [round(f0, 4), round(f1, 4)],
                    "speed": f["speed"], "offset": round(f["offset"], 4), "tol_s": round(max(f["tol_s"], 1e-4), 4),
                    "game": [round(g0, 3), round(f["speed"] * f1 + f["offset"], 3)], "fit": f["fit"],
                    "n_reads": len(r.reads), "n_ticks": f["n_ticks"],
                    **({"speeds_possible": f["speeds_possible"]} if len(f["speeds_possible"]) > 1 else {})})
    for e in events:
        e["from_pass"], e["to_pass"] = out[e["from_pass"]]["id"], out[e["to_pass"]]["id"]
    return out, events


def _sample(src, box, rd, every: Union[str, float], start: float, end: float) -> List[Tuple[float, Optional[int]]]:
    """The cheap first pass: the clock read on every keyframe in [start, end), or every `every` seconds.

    Timed samples come from frames.at_times, which names each frame by its own pts. The fps filter does not: it
    labels a frame with its output tick while the picture is from up to half a sample period later, and a clock
    read on the wrong time made every=1 report two 0x pauses, a fake skip and a fake rewind on the synthetic replay."""
    out: List[Tuple[float, Optional[int]]] = []
    if every == "keyframes":
        gen = frames.keyframes(src, crop=box)
        try:
            for t, img in gen:
                if t is None or t < start:
                    continue
                if t >= end:
                    break                                     # keyframes come in time order: stop decoding here
                out.append((t, rd.read(img)[0]))
        finally:
            gen.close()
        return out
    step = float(every)
    times = [start + k * step for k in range(int(math.ceil((end - start) / step)))]
    for _req, t, img in frames.at_times(src, times, crop=box, hw="d3d11va", past_end="skip"):
        if not out or t > out[-1][0]:                         # two requests can land on one frame
            out.append((t, rd.read(img)[0]))
    return out


def _span(src, info: dict, every, start: float, dur: Optional[float]) -> float:
    """The end of the file span to read; refuses a range that holds no frame."""
    if every != "keyframes" and not (isinstance(every, (int, float)) and every > 0):
        raise ff.MediaError(f"every={every!r}: 'keyframes' or a number of seconds > 0")
    if start < 0 or (dur is not None and dur <= 0):
        raise ff.MediaError(f"bad range start={start} dur={dur}: start >= 0, dur > 0 (None = to the end)")
    if start >= info["duration"]:
        raise ff.MediaError(f"start={start} s is past the end of {Path(src).name} ({info['duration']:.3f} s)")
    return min(start + dur, info["duration"]) if dur is not None else info["duration"]


def cache_path(src) -> Path:
    """Where the OCR clockmap of this exact file is kept: <state>/clockmap/<media id>.clockmap.json, the catalog's
    key, so `import`, `clockmap` and `events` share one map per recording."""
    return ff.state_dir() / "clockmap" / f"{receipt.quick_id(src)}.clockmap.json"


def clockmap(src, *, hud: str = "auto", every: Union[Literal["keyframes"], float] = "keyframes",
             start: float = 0.0, dur: Optional[float] = None, edge_fit: bool = True, out=None,
             reader: str = "auto", eps_frames: float = 1.0, min_pass_s: float = 0.25, tick_every_s: float = 300.0,
             max_tick_windows: int = 5) -> dict:
    """studio.clockmap.v1 for one recording: the passes that map its file time to League game time.

    hud: 'auto' | 'replay' | 'live'. every: 'keyframes' (cheapest) or seconds between reads. start/dur limit
    the file span read. edge_fit decodes the joins and one window per tick-less run at the full frame rate; with
    it, a run shorter than min_pass_s that shows no tick (frames a seek passes through) goes to transients, and each
    run gets one tick window per tick_every_s of its length (at most max_tick_windows): the offset is their median.
    Fails closed (MediaError, one line) on a range with no frame, and when no pass is read.
    """
    t_all = time.perf_counter()
    rd = get_reader(reader)
    info = frames.video_info(src)
    end = _span(src, info, every, start, dur)
    fps = info["fps"] or 60.0
    shape = (info["h"], info["w"])
    timing: Dict[str, float] = {}
    t0 = time.perf_counter()
    layout = _detect_hud(src, info, rd) if hud == "auto" else hud
    timing["detect_hud_s"] = round(time.perf_counter() - t0, 3)
    if layout not in _HUD.LAYOUTS:
        raise ff.MediaError(f"no League clock found on {Path(src).name} (read both HUD layouts on its keyframes); "
                            f"pass hud='replay' or 'live' if the HUD is there")
    box = _HUD.box("clock", layout, shape)
    t0 = time.perf_counter()
    samples = _sample(src, box, rd, every, start, end)
    timing["sample_s"] = round(time.perf_counter() - t0, 3)

    reads = list(samples)
    runs, dropped = _chain(reads, fps, eps_frames)
    windows = 0
    if edge_fit and runs:
        t0 = time.perf_counter()
        reads, runs, dropped, windows = _edge_fit(src, box, rd, samples, fps, eps_frames, tick_every_s,
                                                  max_tick_windows, (start, end))
        timing["edge_fit_s"] = round(time.perf_counter() - t0, 3)
    transients = []
    if edge_fit:                 # a few frames a seek shows on its way (no tick, under min_pass_s): not a pass
        keep = []
        for r in runs:
            if r.t1 - r.t0 < min_pass_s and not r.ticks():
                transients.append({"file": [round(r.t0, 4), round(r.t1, 4)], "shown": [r.reads[0][1], r.reads[-1][1]],
                                   "n_reads": len(r.reads)})
            else:
                keep.append(r)
        runs = keep
    if not runs:
        readable = sum(1 for _t, n in samples if n is not None)
        raise ff.MediaError(f"no League clock pass on {Path(src).name} in the {layout} HUD box over file "
                            f"{start:.3f}-{end:.3f} s ({len(samples)} samples, {readable} read, {len(transients)} "
                            f"seek transients): wrong layout, or the HUD is hidden there")
    passes, events = _passes(runs, fps)
    timing["total_s"] = round(time.perf_counter() - t_all, 3)

    params = {"hud": hud, "every": every, "start": start, "dur": dur, "edge_fit": edge_fit,
              "reader": reader, "eps_frames": eps_frames, "min_pass_s": min_pass_s, "tick_every_s": tick_every_s,
              "max_tick_windows": max_tick_windows, "speeds": list(SPEEDS),
              "out": str(out) if out else None}
    payload = {
        "schema": SCHEMA, "file": Path(src).resolve().as_posix(), "fps": fps, "duration_s": info["duration"],
        "what": f"OCR clockmap of the League HUD clock ({layout} layout): game_t = speed * file_t + offset per pass",
        "how_built": ("clock box read on every keyframe" if every == "keyframes" else f"clock read every {every} s")
                     + (", joins and tick-less runs decoded at the full frame rate (edge fit)" if edge_fit else "")
                     + f"; reader {rd.name}",
        "hud": layout, "box_px": list(box), "reader": rd.name, "passes": passes, "events": events,
        "transients": transients,
        "reads": {"samples": len(samples), "readable": sum(1 for _t, n in samples if n is not None),
                  "total": len(reads), "dropped_as_misread": len(dropped), "windows_decoded": windows},
        "samples": [[t, n] for t, n in samples], "timing": timing,
    }
    blind = [
        "the replay speed box is not read: speed is fitted from clock ticks (snapped to 0/0.25/0.5/1/2/4/8x)",
        "a pause (speed 0) keeps its offset only to +-0.5 s: a frozen clock has no tick",
        "frames whose clock is hidden or unreadable (menus, loading, death recap over the box) belong to no pass",
        "HUD boxes are 1080p fractions; a non-default HUD scale or a 4K replay is untested",
    ]
    res = receipt.result("clockmap", src, params, payload, blind, engine={"reader": rd.name})
    if out:
        save(res, out)
    return res


def save(cmap: dict, out) -> str:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {k: v for k, v in cmap.items() if k != "receipt"}
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(body, fh, indent=1, default=str)
        fh.write("\n")
    return str(p)


def load(path) -> dict:
    """A studio.clockmap.v1 file (hand-made or OCR)."""
    cmap = json.loads(Path(path).read_text(encoding="utf-8"))
    if cmap.get("schema") != SCHEMA:
        raise ff.MediaError(f"{path} is not a {SCHEMA} file (schema {cmap.get('schema')!r})")
    return cmap


# =================================================================================================
# queries
# =================================================================================================

def to_game(cmap: dict, file_t: float) -> Optional[Tuple[float, str]]:
    """(game_t, pass id) shown at file_t, or None outside every pass."""
    for p in cmap["passes"]:
        f0, f1 = p["file"]
        if f0 <= file_t <= f1:
            return p["speed"] * file_t + p["offset"], p["id"]
    return None


def to_file(cmap: dict, game_t: float, *, margin_s: float = 0.0) -> List[Tuple[float, str, float]]:
    """Every (file_t, pass id, speed) that shows game_t; a paused pass counts when game_t is its frozen second."""
    out = []
    for p in cmap["passes"]:
        f0, f1 = p["file"]
        s = p["speed"]
        if s > 0:
            ft = (game_t - p["offset"]) / s
        elif abs(game_t - p["offset"]) <= max(p.get("tol_s", 0.5), 0.5):
            ft = f0
        else:
            continue
        if f0 - margin_s <= ft <= f1 + margin_s:
            out.append((ft, p["id"], s))
    return sorted(out)


def as_clockmaps(cmap: dict) -> list:
    """One timebase.ClockMap per pass (source = the recording's media clock, target = League game time); each holds
    only inside its pass's file span, which observed_at names."""
    from arsenal import timebase
    src = cmap.get("source") or {}
    media = f"media:{src.get('id') or Path(cmap.get('file', 'recording')).name}"
    out = []
    for p in cmap["passes"]:
        out.append(timebase.ClockMap(
            source=media, target="league.game_t",
            slope=Fraction(str(p["speed"])), offset=Fraction(str(round(p["offset"], 6))),
            uncertainty_ns=int(round(float(p.get("tol_s", 0.0)) * 1e9)),
            observed_at=f"{p['id']}@file[{p['file'][0]:.4f},{p['file'][1]:.4f}]"))
    return out


# =================================================================================================
# CLI: py -m arsenal.media clockmap <video> [--hud auto|replay|live] [--out f.json] | --train-templates <videos>
# =================================================================================================

def _mmss(t: float) -> str:
    sign = "-" if t < 0 else ""
    t = abs(t)
    return f"{sign}{int(t // 60)}:{t % 60:06.3f}"


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media clockmap",
                                 description="League of Legends HUD clock OCR: map video time to game time, pass by "
                                             "pass (replay rewinds, 0.25x/0.5x slow motion, skips)")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--hud", default="auto", choices=["auto", *hud.LAYOUTS])
    ap.add_argument("--every", default="keyframes", help="'keyframes' or seconds between reads")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--no-edge-fit", action="store_true", help="skip the full-frame-rate decode of the joins")
    ap.add_argument("--reader", default="auto", choices=["auto", "rapidocr", "templates"])
    ap.add_argument("--out", help="clockmap JSON (default <state>/clockmap/<media id>.clockmap.json, the catalog's)")
    ap.add_argument("--train-templates", action="store_true",
                    help="build the digit templates from these recordings (RapidOCR labels the crops)")
    ap.add_argument("--ocr-python", help=f"a python.exe that has rapidocr, for --train-templates (or {OCR_PYTHON_ENV})")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.train_templates:
        rep = train_templates(a.videos, hud=None if a.hud == "auto" else a.hud, ocr_python=a.ocr_python)
        print(json.dumps(rep, indent=2) if a.json else
              f"templates -> {rep['path']}\nheld out: {rep['held_out']}\nper digit: {rep['count']}")
        return 0
    if len(a.videos) != 1:
        ap.error("give one video (several only with --train-templates)")
    video = a.videos[0]
    if not Path(video).is_file():
        raise ff.MediaError(f"no such video: {video}")
    out = a.out or str(cache_path(video))
    try:
        every = a.every if a.every == "keyframes" else float(a.every)
    except ValueError:
        raise ff.MediaError(f"--every {a.every!r}: 'keyframes' or a number of seconds") from None
    res = clockmap(video, hud=a.hud, every=every, start=a.start, dur=a.dur, edge_fit=not a.no_edge_fit,
                   out=out, reader=a.reader)
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != "samples"}, indent=1, default=str))
        return 0
    sampled = "keyframes" if every == "keyframes" else f"samples (every {every:g} s)"
    print(f"{Path(video).name}: {len(res['passes'])} passes, hud {res['hud']}, reader {res['reader']}, "
          f"{res['reads']['readable']}/{res['reads']['samples']} {sampled} read, {res['timing']['total_s']} s")
    for p in res["passes"]:
        print(f"  {p['id']:<16} file {_mmss(p['file'][0])}-{_mmss(p['file'][1])}  game {_mmss(p['game'][0])}-"
              f"{_mmss(p['game'][1])}  {p['speed']:g}x  offset {p['offset']:+.4f} +-{p['tol_s']:.3f} ({p['fit']})")
    print(f"clockmap -> {out}\nreceipt  -> {res.get('receipt')}")
    return 0
