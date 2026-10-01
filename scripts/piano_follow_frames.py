"""Reconstruct what the 9:16 follow view actually SHOWED, at true scale.

WHY A SECOND RENDERER. piano_roll_render.py draws the whole session at whatever scale fits a
file; that is right for reading a performance and WRONG for judging what was on screen. The
page's own constants fix the scale:

    RAIL_Y = 1.12, TRAIL_SPEED = 6.5 world units/sec, TRAIL_LIFE = 7.0 s   (arsenal/web/piano.js)

A struck note emits a COLUMN from the rail that rises at 6.5 u/s and is black past 7 s, so the
screen at any instant is the last SEVEN SECONDS of playing, pitch across, age upward, inside a
9:16 portrait frame whose horizontal span the follow camera sets from the notes themselves
(clamp(hi-lo+6, 16, 57), piano.js easeCamera).

THE ERROR THIS EXISTS TO FIX, recorded because it cost a whole investigation: the overview
renders used 1.4 px/s. Against a screen that gives its full height to 7 seconds, that compresses
the time axis about 200x -- a gesture 7 s tall and 40 keys wide arrives as a 10-pixel smear, and
no heuristic run over that image can find it. A companion mistake in the same pass collapsed a
4-second window into ONE frame with every note at full brightness: that discards age AND order,
so "sides first, then the middle" renders identically to "all at once" -- which is precisely the
distinction being looked for. Time is not a detail of this picture; it is the picture.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from piano_roll_pack import pack, unpack  # noqa: E402

TRAIL_SPEED = 6.5
TRAIL_LIFE = 7.0
WHITE = {0, 2, 4, 5, 7, 9, 11}


def frame(notes, T, cw=270, ch=480, label=""):
    """One instant, as the follow camera framed it. T in ms."""
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (cw, ch), (5, 6, 10))
    dr = ImageDraw.Draw(im, "RGBA")
    vis = [n for n in notes if n[0] <= T and (T - n[0]) / 1000.0 < TRAIL_LIFE]
    if not vis:
        return im
    lo = min(n[1] for n in vis)
    hi = max(n[1] for n in vis)
    span = max(hi - lo + 6, 16)  # easeCamera's clamp, minus the 57 ceiling
    span = min(span, 57)
    cx = (lo + hi) / 2

    def x_of(m):
        return cw / 2 + (m - cx) / span * cw

    keyy = ch - 26
    pps = (ch - 26) / TRAIL_LIFE  # 7 s of column fills the sky, as on screen

    for m in range(21, 109):  # the keyboard, for scale
        x = x_of(m)
        if -20 < x < cw + 20:
            w = max(1.5, cw / span * 0.9)
            col = (34, 38, 50) if m % 12 in WHITE else (13, 15, 21)
            dr.rectangle([x - w / 2, keyy, x + w / 2, ch], fill=col)

    for t0, pitch, dur, vel in sorted(vis, key=lambda n: n[0]):
        x = x_of(pitch)
        w = max(2.0, cw / span * 0.8)
        # the column: its OLD end left the rail at t0, its NEW end at t0+dur (or now, if held)
        y_old = keyy - (T - t0) / 1000.0 * pps
        y_new = keyy - (T - min(t0 + dur, T)) / 1000.0 * pps
        age = (T - t0) / 1000.0
        fade = max(0.0, 1.0 - age / TRAIL_LIFE)  # "past TRAIL_LIFE it is black"
        a = int(235 * fade * (0.35 + 0.65 * vel / 127))
        col = (150, 220, 255, a) if pitch % 12 in WHITE else (255, 160, 215, a)
        dr.rectangle([x - w / 2, min(y_old, y_new), x + w / 2, max(y_old, y_new)], fill=col)
        if age < 0.25:  # the key itself, freshly struck
            dr.rectangle(
                [x - w / 2, keyy, x + w / 2, keyy + 9], fill=(240, 250, 255, int(255 * (0.4 + 0.6 * vel / 127)))
            )
    if label:
        dr.text((5, 4), label, fill=(185, 200, 220))
    return im


def sheet(session, instants, cols=6, out=None):
    from PIL import Image

    _meta, notes, _ped, _ch = unpack(pack(session))
    cw, chh = 270, 480
    rows = (len(instants) + cols - 1) // cols
    im = Image.new("RGB", (cw * cols, chh * rows), (0, 0, 0))
    for k, T in enumerate(instants):
        im.paste(frame(notes, T, cw, chh, f"{session[9:15]} {T / 1000:.1f}s"), (cw * (k % cols), chh * (k // cols)))
    out = out or (ROOT / "logs" / "piano-forensics-20260927" / f"FOLLOW-{session[:15]}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


if __name__ == "__main__":
    s = sys.argv[1]
    meta, notes, ped, chd = unpack(pack(s))
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 3.5
    t0 = float(sys.argv[3]) * 1000 if len(sys.argv) > 3 else 0
    t1 = float(sys.argv[4]) * 1000 if len(sys.argv) > 4 else int(meta["dur_ms"])
    instants = [t0 + k * step * 1000 for k in range(int((t1 - t0) / 1000 / step) + 1)]
    print(f"{s}: {len(instants)} frames every {step}s over {(t1 - t0) / 1000:.0f}s")
    print(sheet(s, instants[:60]))
