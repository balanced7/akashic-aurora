"""ogham-edge: Ogham letter-name feda + the five forfeda as stroke data.

Our own polylines, redrawn from the traditional shapes (public domain).
Orientation: vertical stemline (the stone edge), read bottom-to-top, as on
the standing stones. Rotating the Unicode horizontal layout 90 deg CCW puts
the B-aicme (below the line) on the RIGHT, the H-aicme (above) on the LEFT,
and turns the M-aicme '/' slant into a '\\' slant across the stem.

Box: 0..1, y down. Stroke 0 is always the stemline (the core every letter
shares); the cuts follow bottom-up, the order an Ogham reader meets them,
so a velocity reveal 'cuts' the letter upward like a rising meter.
"""
import json, math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))   # ogham-edge.json, read by uk_glyphs_v2.py
SHEETS = os.path.join(OUT, "out")                   # the review sheet
ID = "ogham-edge"

R3 = lambda v: round(v, 3)

STEM_TOP, STEM_BOT = 0.05, 0.95
SIDE = 0.25      # consonant cut length, stem to tip (footprint ~0.5 wide: the
                 # brief's ~10 x 22 px slot under a 16.7 px white key)
ACROSS = 0.21    # half-length of a vowel cut straight across
PITCH = 0.2      # spacing between cuts along the stem


def stem():
    return [0.5, STEM_TOP, 0.5, STEM_BOT]


def ys(n, pitch=PITCH):
    """Cut positions centred on the stem, returned bottom-first (reading order)."""
    return [0.5 + (i - (n - 1) / 2) * pitch for i in range(n)][::-1]


def side(n, right, pitch=PITCH):
    # drawn from the stem outward, like a cut into the edge
    x1 = 0.5 + SIDE if right else 0.5 - SIDE
    return [[0.5, y, x1, y] for y in ys(n, pitch)]


def across(n, pitch=PITCH):
    return [[0.5 - ACROSS, y, 0.5 + ACROSS, y] for y in ys(n, pitch)]


def oblique(n, pitch=0.30, rise=0.12, half=0.25):
    # M-aicme: long slanted cuts through the stem, '\' in the vertical layout
    return [[0.5 - half, y - rise, 0.5 + half, y + rise] for y in ys(n, pitch)]


def ebhadh():
    # X straddling the stem (Unicode: a tall narrow X across the line;
    # rotated, a broad flat X). Rising diagonal first.
    w, h = 0.25, 0.16
    return [[0.5 - w, 0.5 + h, 0.5 + w, 0.5 - h],
            [0.5 - w, 0.5 - h, 0.5 + w, 0.5 + h]]


def or_():
    # lozenge straddling the stem, one closed polyline from the bottom vertex
    w, h = 0.24, 0.24
    return [[0.5, 0.5 + h, 0.5 + w, 0.5, 0.5, 0.5 - h, 0.5 - w, 0.5, 0.5, 0.5 + h]]


def uilleann():
    # squared spiral hanging off the B side (right), entered from the stem.
    # Horizontal reference shape (u along the line, v below it):
    #   (0,0)->(0,1)->(1,1)->(1,.4)->(.4,.4)->(.4,.78)
    # rotated 90 deg CCW: X = .5 + v*D, Y = Y0 - u*H
    D, H, Y0 = 0.26, 0.48, 0.74
    pts = [(0, 0), (0, 1), (1, 1), (1, 0.4), (0.4, 0.4), (0.4, 0.78)]
    poly = []
    for u, v in pts:
        poly += [0.5 + v * D, Y0 - u * H]
    return [poly]


def ifin():
    # 'double X' on the B side (right): two saltires chained up the stem,
    # lower first. (Unicode overlaps them more; chained, they stay two X's at 16 px.)
    D = 0.26
    out = []
    for y0, y1 in ((0.5, 0.8), (0.2, 0.5)):
        out.append([0.5, y1, 0.5 + D, y0])   # rising diagonal
        out.append([0.5, y0, 0.5 + D, y1])   # falling diagonal
    return out


def eamhancholl():
    # 'twin of coll': a lattice on the H side (left). The stem is one upright of
    # a '#': two rungs (coll's cuts) crossed by one rail parallel to the stem.
    # A 4 x 4 lattice (the Unicode form) is a blot at 16 px; this stays a '#'.
    return [[0.5, 0.66, 0.2, 0.66],
            [0.5, 0.34, 0.2, 0.34],
            [0.32, 0.16, 0.32, 0.84]]


GLYPHS = [
    ("C",  "coll",        "U+1689", "4 cuts on the H side (left)",            side(4, right=False)),
    ("C#", "eabhadh",     "U+1695", "forfid EA: X across the stem",           ebhadh()),
    ("D",  "dair",        "U+1687", "2 cuts on the H side (left)",            side(2, right=False)),
    ("D#", "or",          "U+1696", "forfid OI: lozenge across the stem",     or_()),
    ("E",  "eadhadh",     "U+1693", "4 cuts straight across",                 across(4)),
    ("F",  "fearn",       "U+1683", "3 cuts on the B side (right)",           side(3, right=True)),
    ("F#", "uilleann",    "U+1697", "forfid UI: squared spiral, B side",      uilleann()),
    ("G",  "gort",        "U+168C", "2 oblique cuts through the stem",        oblique(2)),
    ("G#", "ifin",        "U+1698", "forfid IO/P: double X, B side",          ifin()),
    ("A",  "ailm",        "U+1690", "1 cut straight across",                  across(1)),
    ("A#", "eamhancholl", "U+1699", "forfid AE/X: lattice ('twin coll') as a #, H side", eamhancholl()),
    ("B",  "beith",       "U+1681", "1 cut on the B side (right)",            side(1, right=True)),
]

TALLY = [("beith", "U+1681"), ("luis", "U+1682"), ("fearn", "U+1683"),
         ("sail", "U+1684"), ("nion", "U+1685")]


def build():
    glyphs = []
    for pc, name, cp, shape, cuts in GLYPHS:
        strokes = [stem()] + cuts
        assert 2 <= len(strokes) <= 5, (pc, len(strokes))
        glyphs.append({"pc": pc, "name": name, "unicode": cp, "shape": shape,
                       "strokes": [[R3(v) for v in s] for s in strokes]})
    tally = []
    for i, (name, cp) in enumerate(TALLY):
        n = i + 1
        strokes = [stem()] + side(n, right=True, pitch=0.17)
        tally.append({"level": n, "vel": [[1, 25], [26, 50], [51, 76], [77, 101], [102, 127]][i],
                      "name": name, "unicode": cp,
                      "strokes": [[R3(v) for v in s] for s in strokes]})
    data = {
        "id": ID,
        "name": "Ogham",
        "found_or_ours": "found",
        "origin": "Primitive Irish Ogham inscriptions, 4th-6th c. CE; forfeda from the Old Irish manuscript tradition. Shapes are public domain; these polylines are our own redraw.",
        "orientation": "vertical stemline centred under the key, read bottom-to-top as on the standing stones; B-aicme cuts to the right of the stem, H-aicme to the left, M-aicme slant '\\', vowels straight across (manuscript form; stones use notches)",
        "reveal": "stroke 0 = the stemline (shared by every letter: the lit edge); strokes 1.. = the cuts, bottom-up. Velocity reveals count = max(1, ceil(n * vel/127)); show at least 2 if the letter must be identifiable at pp.",
        "pitch_order": "chromatic; white keys = the feda whose letters are the note names (A ailm, B beith, C coll, D dair, E eadhadh, F fearn, G gort); black keys = the five forfeda in traditional order going up (C# eabhadh, D# or, F# uilleann, G# ifin, A# eamhancholl)",
        "glyphs": glyphs,
        "alt_tally": {
            "note": "ALTERNATE velocity tally, not a pitch mapping: every key shows the B-aicme ladder, 1 to 5 cuts by velocity band; stroke order is already core-first (stem, then cuts bottom-up).",
            "levels": tally,
        },
    }
    with open(os.path.join(OUT, ID + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1)
    return data


# ---------------------------------------------------------------- rendering
BG = (14, 10, 24)
FG = (236, 228, 255)
LAB = (150, 138, 180)
SS = 8  # supersample


def draw_glyph(strokes, size, bright=1.0, glow=0.0, frac_strokes=None):
    """Render one glyph into a size x size RGB tile (anti-aliased)."""
    S = size * SS
    lw = max(1.0, 0.08 * S)
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    pad = 0.0
    use = strokes if frac_strokes is None else strokes[:frac_strokes]
    for s in use:
        pts = [((s[i] * (1 - 2 * pad) + pad) * S, (s[i + 1] * (1 - 2 * pad) + pad) * S)
               for i in range(0, len(s), 2)]
        d.line(pts, fill=255, width=int(round(lw)), joint="curve")
        r = lw / 2
        for (x, y) in (pts[0], pts[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    tile = Image.new("RGB", (size, size), BG)
    col = tuple(int(BG[k] + (FG[k] - BG[k]) * bright) for k in range(3))
    if glow > 0:
        halo = mask.filter(ImageFilter.GaussianBlur(radius=max(1, size * 0.06)))
        gcol = tuple(int(BG[k] + (c - BG[k]) * 0.9) for k, c in enumerate((170, 120, 255)))
        halo = halo.point(lambda v: int(min(255, v * glow * 1.6)))
        tile.paste(Image.new("RGB", (size, size), gcol), (0, 0), halo)
    tile.paste(Image.new("RGB", (size, size), col), (0, 0), mask)
    return tile


def font(sz):
    for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            pass
    return ImageFont.load_default()


KEY_X = {"C": 0.5, "C#": 0.93, "D": 1.5, "D#": 2.07, "E": 2.5, "F": 3.5, "F#": 3.9,
         "G": 4.5, "G#": 5.0, "A": 5.5, "A#": 6.1, "B": 6.5}   # in white-key units


def slip_band(glyphs, lit, box=22, pitch=16.7):
    from PIL import ImageChops
    W, H = int(7 * pitch) + 10, 28
    acc = Image.new("L", (W, H), 0)
    for g in glyphs:
        if g["pc"] not in lit:
            continue
        t = draw_glyph(g["strokes"], box).convert("L").point(lambda v: max(0, v - 14) * 255 // 241)
        sub = Image.new("L", (W, H), 0)
        sub.paste(t, (int(round(5 + KEY_X[g["pc"]] * pitch - box / 2)), (H - box) // 2))
        acc = ImageChops.lighter(acc, sub)
    band = Image.new("RGB", (W, H), (22, 16, 36))
    dd = ImageDraw.Draw(band)
    for k in range(8):   # white-key seams as faint ticks along the top edge
        x = int(round(5 + k * pitch))
        dd.line([(x, 0), (x, 2)], fill=(70, 60, 100))
    band.paste(Image.new("RGB", (W, H), FG), (0, 0), acc)
    return band


def render(data):
    glyphs = data["glyphs"]
    n = len(glyphs)
    CELL = 160
    M = 24
    W = M * 2 + n * CELL
    rows = []
    f_big, f_sm, f_hd = font(22), font(14), font(17)

    sheet_h = 1500
    img = Image.new("RGB", (W, sheet_h), BG)
    d = ImageDraw.Draw(img)
    y = 12
    d.text((M, y), "ogham-edge  -  Ogham letter-name feda + the five forfeda (vertical stem, read upward; B-aicme right, H-aicme left)", font=f_hd, fill=LAB)
    y += 34

    # row 1: 160 px
    d.text((M, y), "160 px", font=f_sm, fill=LAB); y += 20
    for i, g in enumerate(glyphs):
        x = M + i * CELL
        img.paste(draw_glyph(g["strokes"], CELL - 16), (x + 8, y))
        d.text((x + 10, y + CELL - 14), f'{g["pc"]}  {g["name"]}', font=f_big if len(g["name"]) < 9 else f_sm, fill=FG)
    y += CELL + 22

    # row 2: 48 px
    d.text((M, y), "48 px (Cinema buffer)", font=f_sm, fill=LAB); y += 20
    for i, g in enumerate(glyphs):
        x = M + i * CELL + (CELL - 48) // 2
        img.paste(draw_glyph(g["strokes"], 48), (x, y))
    y += 48 + 18

    # row 3: 16 px, native
    d.text((M, y), "16 px (live view), native", font=f_sm, fill=LAB); y += 20
    for i, g in enumerate(glyphs):
        x = M + i * CELL + (CELL - 16) // 2
        img.paste(draw_glyph(g["strokes"], 16), (x, y))
        d.text((x + 22, y), g["pc"], font=f_sm, fill=LAB)
    y += 16 + 14

    # row 3b: 16 px, magnified 6x nearest so the pixels can be judged
    d.text((M, y), "the same 16 px tiles, magnified 6x (nearest neighbour)", font=f_sm, fill=LAB); y += 20
    for i, g in enumerate(glyphs):
        t = draw_glyph(g["strokes"], 16).resize((96, 96), Image.NEAREST)
        x = M + i * CELL + (CELL - 96) // 2
        img.paste(t, (x, y))
    y += 96 + 18

    # row 3c: slip preview -- glyphs at their real key positions under one octave
    # (white keys 16.7 px apart, black-key glyphs near the white-key seams),
    # 22 px glyph box in the 28 px slip band, composited as light.
    d.text((M, y), "slip preview at real key positions (one octave = 7 x 16.7 px, 22 px glyph box, 28 px band): C7 chord (C E G A#), then all 12 lit (worst case) -- native, then 4x", font=f_sm, fill=LAB); y += 20
    bx = M
    for lit in (("C", "E", "G", "A#"), tuple(g["pc"] for g in glyphs)):
        band = slip_band(glyphs, lit)
        img.paste(band, (bx, y + 42))
        img.paste(band.resize((band.width * 4, band.height * 4), Image.NEAREST), (bx + band.width + 16, y))
        bx += band.width * 5 + 60
    y += 28 * 4 + 22

    # row 4: velocity reveal of one glyph (C coll, 5 strokes) at 4 levels
    d.text((M, y), "velocity: C coll at vel 32 / 64 / 96 / 127  (strokes = max(1, ceil(n*v)), brightness and halo rise)", font=f_sm, fill=LAB); y += 20
    g = glyphs[0]
    ns = len(g["strokes"])
    for k, vel in enumerate((32, 64, 96, 127)):
        v = vel / 127
        cnt = max(1, math.ceil(ns * v))
        x = M + k * CELL
        img.paste(draw_glyph(g["strokes"], CELL - 16, bright=0.35 + 0.65 * v, glow=v * v, frac_strokes=cnt), (x + 8, y))
        d.text((x + 10, y + CELL - 14), f"vel {vel}: {cnt}/{ns}", font=f_sm, fill=LAB)
    # and the 48 px versions beside it
    for k, vel in enumerate((32, 64, 96, 127)):
        v = vel / 127
        cnt = max(1, math.ceil(ns * v))
        x = M + 4 * CELL + 40 + k * 70
        img.paste(draw_glyph(g["strokes"], 48, bright=0.35 + 0.65 * v, glow=v * v, frac_strokes=cnt), (x, y + 50))
    y += CELL + 22

    # row 5: alternate tally
    d.text((M, y), "alternate velocity tally (every key): beith . luis . fearn . sail . nion  =  vel 1-25 / 26-50 / 51-76 / 77-101 / 102-127", font=f_sm, fill=LAB); y += 20
    for k, t in enumerate(data["alt_tally"]["levels"]):
        v = t["vel"][1] / 127
        x = M + k * CELL
        img.paste(draw_glyph(t["strokes"], CELL - 16, bright=0.35 + 0.65 * v, glow=v * v), (x + 8, y))
        d.text((x + 10, y + CELL - 14), f'{t["name"]}  {t["vel"][0]}-{t["vel"][1]}', font=f_sm, fill=LAB)
    for k, t in enumerate(data["alt_tally"]["levels"]):
        x = M + 5 * CELL + 40 + k * 40
        img.paste(draw_glyph(t["strokes"], 16), (x, y + 60))
    y += CELL + 16

    img = img.crop((0, 0, W, y))
    os.makedirs(SHEETS, exist_ok=True)
    img.save(os.path.join(SHEETS, ID + ".png"))
    # a zoomed crop of the small rows for review
    return img


if __name__ == "__main__":
    data = build()
    render(data)
    print("ok", len(data["glyphs"]), "glyphs")
