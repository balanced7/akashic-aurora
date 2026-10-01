"""Render a recorded performance session as a piano-roll scroll -- SVG and PNG.

WHY THIS EXISTS. state/arsenal/performance/<session>/events.jsonl is note-level truth
(on/off/vel/pedal + the detector's chord readings), but it is unreadable as text at any
useful length: 6,000 note events is a wall. The visualizer renders it live and then it is
gone. This makes the same scroll INSPECTABLE after the fact, which is what any forensic
question about a session needs -- who played, what was played, and whether the notes were
chosen for the MUSIC or for the PICTURE.

TWO OUTPUTS, ON PURPOSE. The geometry pass runs once and emits both:
  SVG -- vector, one <rect> per sounding note. Zoomable, diffable, and the rect list IS the
         feature table the shape heuristics read, so the picture and the analysis cannot
         disagree about what was played.
  PNG -- raster, for eyes (human or vision model). A crude shape drawn on a keyboard is a
         SPATIAL pattern; no amount of text summary substitutes for looking at it.

AXES follow the instrument, not the data's convenience: pitch 21..108 runs left-to-right as
on a keyboard, time runs DOWNWARD as in every falling-note display. Velocity drives opacity,
so a hammered cluster and a brushed one do not look alike.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERF = ROOT / "state" / "arsenal" / "performance"
LO, HI = 21, 108  # A0..C8, the full 88
WHITE = {0, 2, 4, 5, 7, 9, 11}


def load(session: str):
    """Note rectangles + pedal spans. An unmatched `on` is closed at session end rather than
    dropped: a held final chord is real and discarding it would silently shorten the picture."""
    p = PERF / session / "events.jsonl"
    if not p.exists():
        raise SystemExit(f"no such session: {p}")
    ons, rects, pedal = {}, [], []
    tmax, pdown = 0, None
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue  # a torn last line is not a reason to render nothing
        t = e.get("t_ms", 0)
        tmax = max(tmax, t)
        k = e.get("kind")
        if k == "on":
            ons.setdefault(e["note"], []).append((t, e.get("vel", 64)))
        elif k in ("off", "sound_end") and e.get("note") in ons and ons[e["note"]]:
            t0, v = ons[e["note"]].pop(0)
            rects.append((e["note"], t0, max(t - t0, 30), v))  # 30ms floor: a staccato note must still be visible
        elif k == "pedal":
            if e.get("down") and pdown is None:
                pdown = t
            elif not e.get("down") and pdown is not None:
                pedal.append((pdown, t))
                pdown = None
    for note, rest in ons.items():
        for t0, v in rest:
            rects.append((note, t0, max(tmax - t0, 30), v))
    if pdown is not None:
        pedal.append((pdown, tmax))
    return rects, pedal, tmax


def render_svg(rects, pedal, t0, t1, out: Path, kw=12, pxs=60.0, title=""):
    """pxs = pixels per second of music."""
    w, h = (HI - LO + 1) * kw, max(1, int((t1 - t0) / 1000 * pxs))
    L = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<title>{title}</title><rect width="{w}" height="{h}" fill="#0b0d12"/>',
    ]
    for n in range(LO, HI + 1):  # keyboard stripes, so pitch is readable without a ruler
        if n % 12 not in WHITE:
            L.append(f'<rect x="{(n - LO) * kw}" y="0" width="{kw}" height="{h}" fill="#151922"/>')
        if n % 12 == 0:
            L.append(
                f'<line x1="{(n - LO) * kw}" y1="0" x2="{(n - LO) * kw}" y2="{h}" stroke="#2a3140" stroke-width="1"/>'
            )
    for a, b in pedal:
        if b < t0 or a > t1:
            continue
        ya, yb = (max(a, t0) - t0) / 1000 * pxs, (min(b, t1) - t0) / 1000 * pxs
        L.append(f'<rect x="0" y="{ya:.1f}" width="{w}" height="{max(1, yb - ya):.1f}" fill="#ffd36e" opacity="0.06"/>')
    for note, ts, dur, vel in rects:
        if ts + dur < t0 or ts > t1:
            continue
        y = (ts - t0) / 1000 * pxs
        hh = max(2.0, dur / 1000 * pxs)
        op = 0.25 + 0.75 * min(1.0, vel / 110)
        col = "#7fd4ff" if note % 12 in WHITE else "#ff9ad5"
        L.append(
            f'<rect x="{(note - LO) * kw + 1}" y="{y:.1f}" width="{kw - 2}" height="{hh:.1f}" '
            f'rx="2" fill="{col}" opacity="{op:.2f}"/>'
        )
    L.append("</svg>")
    out.write_text("\n".join(L), encoding="utf-8")
    return out


def render_png(rects, pedal, t0, t1, out: Path, kw=10, pxs=60.0):
    from PIL import Image, ImageDraw

    w, h = (HI - LO + 1) * kw, max(1, int((t1 - t0) / 1000 * pxs))
    im = Image.new("RGB", (w, h), (11, 13, 18))
    d = ImageDraw.Draw(im, "RGBA")
    for n in range(LO, HI + 1):
        if n % 12 not in WHITE:
            d.rectangle([(n - LO) * kw, 0, (n - LO) * kw + kw - 1, h], fill=(21, 25, 34))
        if n % 12 == 0:
            d.line([((n - LO) * kw, 0), ((n - LO) * kw, h)], fill=(42, 49, 64))
    for a, b in pedal:
        if b < t0 or a > t1:
            continue
        d.rectangle([0, (max(a, t0) - t0) / 1000 * pxs, w, (min(b, t1) - t0) / 1000 * pxs], fill=(255, 211, 110, 16))
    for note, ts, dur, vel in rects:
        if ts + dur < t0 or ts > t1:
            continue
        y = (ts - t0) / 1000 * pxs
        hh = max(2.0, dur / 1000 * pxs)
        a = int(255 * (0.25 + 0.75 * min(1.0, vel / 110)))
        col = (127, 212, 255, a) if note % 12 in WHITE else (255, 154, 213, a)
        d.rectangle([(note - LO) * kw + 1, y, (note - LO) * kw + kw - 2, y + hh], fill=col)
    im.save(out)
    return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: piano_roll_render.py <session> [--pxs N] [--out DIR] [--from S] [--to S] [--tag NAME]")
    session = argv[1]

    def opt(flag, default=None, cast=str):
        return cast(argv[argv.index(flag) + 1]) if flag in argv else default

    pxs = opt("--pxs", 60.0, float)
    outdir = Path(opt("--out", str(ROOT / "logs" / "piano-forensics-20260927")))
    outdir.mkdir(parents=True, exist_ok=True)
    rects, pedal, tmax = load(session)
    t0 = opt("--from", 0.0, float) * 1000
    t1 = opt("--to", tmax / 1000, float) * 1000
    tag = opt("--tag", "")
    stem = f"{session}{('-' + tag) if tag else ''}"
    s = render_svg(rects, pedal, t0, t1, outdir / f"{stem}.svg", pxs=pxs, title=stem)
    p = render_png(rects, pedal, t0, t1, outdir / f"{stem}.png", pxs=pxs)
    print(
        f"{session}: {len(rects):,} notes, {tmax / 1000:.0f}s -> {s.name} + {p.name} "
        f"({(HI - LO + 1) * 10}x{int((t1 - t0) / 1000 * pxs)}px @ {pxs}px/s)"
    )


if __name__ == "__main__":
    main(sys.argv)
