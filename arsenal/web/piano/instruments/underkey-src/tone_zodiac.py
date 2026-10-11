# tone-zodiac: the twelve zodiac glyphs redrawn as our own stroke data (public-domain shapes;
# nothing traced from a font). Writes tone-zodiac.json and the review sheet tone-zodiac.png.
#
# Coordinates: 0..1 box, y down. Each stroke is a flat [x,y,x,y,...] polyline.
# Strokes are ORDERED core-first; "core" = how many leading strokes make the sign readable.
import json, math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")   # review files only
ID = "tone-zodiac"

# ---------------------------------------------------------------- geometry helpers
def arc(cx, cy, rx, ry, a0, a1, step=7.0):
    n = max(2, int(math.ceil(abs(a1 - a0) / step)) + 1)
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]

def cubic(p0, p1, p2, p3, n=14):
    pts = []
    for i in range(n):
        t = i / (n - 1); u = 1 - t
        pts.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return pts

def seg(*pts):
    return list(pts)

def join(*parts):
    out = []
    for p in parts:
        for q in p:
            if out and abs(out[-1][0] - q[0]) < 1e-6 and abs(out[-1][1] - q[1]) < 1e-6:
                continue
            out.append(q)
    return out

def rot180(pts):
    return [(1 - x, 1 - y) for x, y in pts]

def mirror_x(pts):
    return [(1 - x, y) for x, y in pts]

def flat(pts):
    return [round(v, 3) for p in pts for v in p]

# ---------------------------------------------------------------- the twelve signs (sign index 0..11)
SIGNS = {}

# 0 Aries: the ram's horns as ONE stroke (left curl, up, over, down to the cusp, up, over, right curl),
# then the stem.
SIGNS[0] = dict(name="Aries", core=1, strokes=[
    join(arc(0.30, 0.35, 0.20, 0.22, -218, 0), arc(0.70, 0.35, 0.20, 0.22, -180, 38)),
    seg((0.50, 0.35), (0.50, 0.92)),
])

# 1 Taurus: the head (circle), then the horns (a cup whose tips flick outward).
_tl = cubic((0.08, 0.08), (0.20, 0.20), (0.27, 0.40), (0.50, 0.40))
SIGNS[1] = dict(name="Taurus", core=2, strokes=[
    arc(0.50, 0.645, 0.235, 0.235, -90, 270),
    join(_tl, list(reversed(mirror_x(_tl)))),
])

# 2 Gemini: two pillars, then the two lintels (convex outward).
SIGNS[2] = dict(name="Gemini", core=2, strokes=[
    seg((0.355, 0.15), (0.355, 0.85)),
    seg((0.645, 0.15), (0.645, 0.85)),
    cubic((0.10, 0.19), (0.35, 0.09), (0.65, 0.09), (0.90, 0.19)),
    cubic((0.10, 0.81), (0.35, 0.91), (0.65, 0.91), (0.90, 0.81)),
])

# 3 Cancer: upper tail sweeping left into its loop; lower = the same turned 180 degrees.
_cu = join(cubic((0.95, 0.45), (0.94, 0.22), (0.62, 0.12), (0.27, 0.20)),
           arc(0.27, 0.355, 0.155, 0.155, -90, -450))
SIGNS[3] = dict(name="Cancer", core=2, strokes=[_cu, rot180(_cu)])

# 4 Leo: the head (circle) drawn into the mane (arch over and down), then the closing flick.
SIGNS[4] = dict(name="Leo", core=1, strokes=[
    join(arc(0.25, 0.71, 0.145, 0.145, 0, -360),
         cubic((0.395, 0.71), (0.40, 0.42), (0.36, 0.09), (0.61, 0.09)),
         cubic((0.61, 0.09), (0.84, 0.09), (0.88, 0.34), (0.77, 0.54)),
         cubic((0.77, 0.54), (0.67, 0.72), (0.66, 0.90), (0.80, 0.91))),
    cubic((0.80, 0.91), (0.88, 0.91), (0.93, 0.86), (0.94, 0.78), n=8),
])

# m-shape shared by Virgo and Scorpio: legs at x = 0.07, 0.27, 0.47, humps r = 0.10. The m is kept
# to the left half so the tails (the only difference between the two) get the whole right half.
_LX = (0.07, 0.27, 0.47); _HR = 0.10; _HY = 0.31; _LB = 0.84
_mB = join(seg((_LX[0], _LB), (_LX[0], _HY)), arc(_LX[0] + _HR, _HY, _HR, _HR, 180, 360),
           seg((_LX[1], _HY), (_LX[1], _LB)))
_hump2 = arc(_LX[1] + _HR, _HY, _HR, _HR, 180, 360)

# 5 Virgo: hump + third leg + the tall closed loop that crosses back over the leg and exits
# down-left under the m (exaggerated), then the first two legs.
SIGNS[5] = dict(name="Virgo", core=1, strokes=[
    join(_hump2, seg((_LX[2], _HY), (_LX[2], 0.70)),
         cubic((0.47, 0.70), (0.47, 0.88), (0.70, 0.90), (0.79, 0.70)),
         cubic((0.79, 0.70), (0.89, 0.50), (0.89, 0.24), (0.75, 0.21)),
         cubic((0.75, 0.21), (0.61, 0.18), (0.57, 0.46), (0.52, 0.62)),
         seg((0.52, 0.62), (0.34, 0.97))),
    _mB,
])

# 7 Scorpio: hump + third leg + the sting running up-right, the arrowhead (big), then the first legs.
SIGNS[7] = dict(name="Scorpio", core=2, strokes=[
    join(_hump2, seg((_LX[2], _HY), (_LX[2], 0.72)),
         cubic((0.47, 0.72), (0.47, 0.87), (0.55, 0.91), (0.65, 0.86), n=10),
         seg((0.65, 0.86), (0.94, 0.50))),
    seg((0.71, 0.50), (0.94, 0.50), (0.94, 0.73)),
    _mB,
])

# 6 Libra: the sun-on-the-horizon line (arms + dome), then the base line.
SIGNS[6] = dict(name="Libra", core=2, strokes=[
    join(seg((0.06, 0.56), (0.30, 0.56)), arc(0.50, 0.455, 0.225, 0.225, 152, 388),
         seg((0.70, 0.56), (0.94, 0.56))),
    seg((0.06, 0.77), (0.94, 0.77)),
])

# 8 Sagittarius: shaft, arrowhead, crossbar.
SIGNS[8] = dict(name="Sagittarius", core=2, strokes=[
    seg((0.10, 0.90), (0.88, 0.12)),
    seg((0.48, 0.12), (0.88, 0.12), (0.88, 0.52)),
    seg((0.24, 0.48), (0.52, 0.76)),
])

# 9 Capricorn: from the V's floor up, over the arch, down into the fish-tail loop and out;
# then the V's left arm; then the entry hook.
SIGNS[9] = dict(name="Capricorn", core=2, strokes=[
    join(seg((0.29, 0.80), (0.43, 0.30)),
         cubic((0.43, 0.30), (0.47, 0.13), (0.64, 0.13), (0.65, 0.32)),
         seg((0.65, 0.32), (0.65, 0.66)),
         arc(0.775, 0.70, 0.125, 0.125, 180, -150),
         cubic((0.667, 0.637), (0.60, 0.74), (0.52, 0.88), (0.38, 0.92), n=10)),
    seg((0.12, 0.22), (0.29, 0.80)),
    cubic((0.03, 0.30), (0.04, 0.20), (0.10, 0.17), (0.12, 0.22), n=8),
])

# 10 Aquarius: two zigzag waves (2 crests each: reads at 16 px where 3 crests clot).
def _zig(y_low, y_high, xs=(0.06, 0.28, 0.50, 0.72, 0.94)):
    return [(x, y_low if i % 2 == 0 else y_high) for i, x in enumerate(xs)]
SIGNS[10] = dict(name="Aquarius", core=2, strokes=[
    _zig(0.45, 0.22),
    _zig(0.80, 0.57),
])

# 11 Pisces: the two fishes back to back, then the cord.
_pl = arc(0.06, 0.50, 0.30, 0.45, -68, 68)
SIGNS[11] = dict(name="Pisces", core=2, strokes=[
    _pl,
    mirror_x(_pl),
    seg((0.22, 0.50), (0.78, 0.50)),
])

UNICODE = {i: "U+%04X" % (0x2648 + i) for i in range(12)}
PC_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
FIFTHS = [(7 * pc) % 12 for pc in range(12)]       # sign index per pitch class (Steiner/von Gleich)
CHROMATIC = list(range(12))                          # Henschel: Aries C, Taurus C#, ...

def glyphs_by_pc():
    out = []
    for pc in range(12):
        s = FIFTHS[pc]; g = SIGNS[s]
        out.append(dict(pc=pc, name=g["name"], sign=s, unicode_ref=UNICODE[s], core=g["core"],
                        strokes=[flat(st) for st in g["strokes"]]))
    return out

def reveal_count(n, core, v):
    """strokes lit at velocity v in 0..1: the core always, the rest unlock with velocity."""
    return max(min(core, n), min(n, math.ceil(v * n - 1e-9)))

# ---------------------------------------------------------------- rendering
BG = (13, 8, 22)
INK = (240, 232, 255)
SS = 8

def mask_for(strokes, cell, pad=0.12, lw_frac=0.08, ss=SS):
    big = cell * ss
    m = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(m)
    lw = lw_frac * big
    box = big * (1 - 2 * pad); off = big * pad
    for st in strokes:
        pts = [(off + st[i] * box, off + st[i + 1] * box) for i in range(0, len(st), 2)]
        for a, b in zip(pts, pts[1:]):
            d.line([a, b], fill=255, width=max(1, int(round(lw))))
        r = lw / 2
        for p in pts:
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)
    return m.resize((cell, cell), Image.BOX)

def paste_glyph(sheet, xy, strokes, cell, color=INK, gain=1.0, halo=0.0):
    m = mask_for(strokes, cell)
    if halo > 0:
        h = m.filter(ImageFilter.GaussianBlur(cell * 0.05))
        hal = h.point(lambda v: int(min(255, v * halo)))
        core_layer = Image.new("RGB", (cell, cell), tuple(int(c * gain * 0.55) for c in color))
        sheet.paste(core_layer, xy, hal)
    lay = Image.new("RGB", (cell, cell), tuple(int(c * gain) for c in color))
    sheet.paste(lay, xy, m)

def main():
    os.makedirs(OUT, exist_ok=True)
    data_glyphs = glyphs_by_pc()
    doc = dict(
        id=ID,
        name="Zodiac (circle of fifths)",
        found_or_ours="found",
        description="The twelve zodiac glyphs, redrawn as our own strokes from the traditional public-domain "
                    "shapes, laid on the tone-zodiac (Steiner / von Gleich): Aries = C, going round the circle "
                    "of fifths.",
        mapping="fifths",
        mappings=dict(
            fifths=dict(sign_of_pc=FIFTHS, rule="sign = 7*pc mod 12 (Aries C, Taurus G, Gemini D, ... Pisces F)"),
            chromatic=dict(sign_of_pc=CHROMATIC, rule="sign = pc (Henschel: Aries C, Taurus C#, ... Pisces B)"),
        ),
        sign_order=[SIGNS[i]["name"] for i in range(12)],
        reveal=dict(rule="lit = max(core, ceil(v*n)), v = vel/127; brightness rises with v (sheet uses 0.25+0.75*v^2)",
                    note="glyphs are ordered by pitch class under the fifths mapping; for the chromatic mapping "
                         "pick the glyph whose 'sign' equals the pitch class"),
        licence="Shapes: the traditional zodiac glyphs (public domain). Stroke data: drawn for Akashic Aurora, "
                "not traced from any font or icon set.",
        glyphs=data_glyphs,
    )
    with open(os.path.join(OUT, ID + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, separators=(",", ":"))

    # ---- sheet
    PITCH = 172; L = 40; W = L * 2 + PITCH * 12
    font_b = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 22)
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 15)
    font_s = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)
    H = 1500
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    dim = (150, 138, 185)
    d.text((L, 14), "tone-zodiac  -  zodiac glyphs on the circle of fifths (Steiner / von Gleich: sign = 7*pc mod 12)",
           font=font_b, fill=(225, 215, 250))
    d.text((L, 44), "our strokes from the public-domain shapes; line width 8% of cell, round caps; strokes ordered core-first",
           font=font, fill=dim)

    y = 80
    # row 1: 160 px
    d.text((L, y), "160 px", font=font_s, fill=dim); y += 18
    for i, g in enumerate(data_glyphs):
        x = L + i * PITCH
        d.text((x + 4, y), PC_NAMES[g["pc"]], font=font_b, fill=(235, 225, 255))
        d.text((x + 52, y + 6), g["name"], font=font, fill=dim)
        paste_glyph(sheet, (x, y + 32), g["strokes"], 160)
    y += 32 + 160 + 16

    # row 1b: stroke order (colour per stroke; core strokes solid, extras tinted)
    ORDER = [(255, 255, 255), (110, 220, 255), (255, 190, 90), (255, 110, 170), (150, 255, 150)]
    d.text((L, y), "stroke order  (1 white, 2 cyan, 3 amber, 4 rose)   |c = core strokes", font=font_s, fill=dim); y += 18
    for i, g in enumerate(data_glyphs):
        x = L + i * PITCH + 40
        for k, st in enumerate(g["strokes"]):
            paste_glyph(sheet, (x, y), [st], 80, color=ORDER[k])
        d.text((x - 36, y + 30), "n%d\nc%d" % (len(g["strokes"]), g["core"]), font=font_s, fill=dim)
    y += 80 + 18

    # row 2: 48 px
    d.text((L, y), "48 px  (Cinema buffer, 3x)", font=font_s, fill=dim); y += 18
    for i, g in enumerate(data_glyphs):
        paste_glyph(sheet, (L + i * PITCH + 56, y), g["strokes"], 48)
    y += 48 + 18

    # row 3: 16 px, actual size, then magnified x6 nearest-neighbour
    d.text((L, y), "16 px  (live, 1x)", font=font_s, fill=dim); y += 18
    smalls = []
    for i, g in enumerate(data_glyphs):
        im = Image.new("RGB", (16, 16), BG); paste_glyph(im, (0, 0), g["strokes"], 16); smalls.append(im)
        sheet.paste(im, (L + i * PITCH + 72, y))
    y += 16 + 14
    d.text((L, y), "16 px magnified x6 (nearest)", font=font_s, fill=dim); y += 18
    for i, im in enumerate(smalls):
        sheet.paste(im.resize((96, 96), Image.NEAREST), (L + i * PITCH + 32, y))
    y += 96 + 20

    # strip: as under the keys, chromatic C..B at 16.7 px pitch on a 28 px band (x1 and x4)
    d.text((L, y), "under the keys: one octave C..B at 16.7 px pitch on the 28 px key-slip band (1x, then 4x nearest)",
           font=font_s, fill=dim); y += 20
    band = Image.new("RGB", (int(16.7 * 14), 28), (18, 12, 30))
    for i, g in enumerate(data_glyphs):
        paste_glyph(band, (int(round(16.7 * (i + 1) - 8)), 6), g["strokes"], 16)
    sheet.paste(band, (L, y))
    sheet.paste(band.resize((band.width * 4, band.height * 4), Image.NEAREST), (L + band.width + 40, y))
    y += 28 * 4 + 24

    # velocity row: one glyph at 4 velocity levels
    demo_pc = 2  # Gemini on D: four strokes, so every level adds one
    g = data_glyphs[demo_pc]
    n = len(g["strokes"])
    d.text((L, y), "velocity reveal (%s on %s): lit = max(core, ceil(v*n)), brightness 0.25 + 0.75 v^2, with bloom halo"
           % (g["name"], PC_NAMES[demo_pc]), font=font_s, fill=dim); y += 20
    for k, vel in enumerate((32, 64, 96, 127)):
        v = vel / 127
        lit = reveal_count(n, g["core"], v)
        gain = 0.25 + 0.75 * v * v
        x = L + k * 2 * PITCH
        paste_glyph(sheet, (x + 20, y), g["strokes"][:lit], 160, gain=gain, halo=1.6 * gain)
        d.text((x + 190, y + 60), "vel %d\nv = %.2f\n%d of %d strokes\ngain %.2f" % (vel, v, lit, n, gain),
               font=font, fill=dim)
    # second demo: Scorpio core-first (sting before the m)
    g2 = data_glyphs[1]
    for k, vel in enumerate((32, 127)):
        v = vel / 127; n2 = len(g2["strokes"])
        lit = reveal_count(n2, g2["core"], v); gain = 0.25 + 0.75 * v * v
        x = L + (8 + k * 2) * PITCH
        paste_glyph(sheet, (x + 20, y), g2["strokes"][:lit], 160, gain=gain, halo=1.6 * gain)
        d.text((x + 190, y + 60), "%s vel %d\n%d of %d strokes" % (g2["name"], vel, lit, n2), font=font, fill=dim)
    y += 160 + 20
    sheet = sheet.crop((0, 0, W, y))
    sheet.save(os.path.join(OUT, ID + ".png"))
    print("sheet", sheet.size)

if __name__ == "__main__":
    main()
