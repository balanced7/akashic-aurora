"""OUR rune set for the Crystal grand's under-key light: "Clockwork of Fifths".

Pitch class p is split by the Chinese remainder theorem into (p mod 3, p mod 4):
  * CUP    = a half-circle whose mouth faces 12, 4 or 8 o'clock      <- p mod 3
             notes a MINOR third apart share the cup (a dim7 chord is one cup)
  * NEEDLE = a line through the centre at |, /, -, \ (45 deg steps)  <- p mod 4
             notes a MAJOR third apart share the needle (an augmented triad is one needle)
Up a fifth (+7 = +1 mod 3, -1 mod 4) the cup turns 120 deg clockwise and the needle
45 deg clockwise: a 3-tooth gear and a 4-tooth gear that only line up again after
twelve fifths. Every triad is a chain: root-third share one part, third-fifth the
other. Mirror a glyph left-right and you get its inversion about C (E <-> Ab, F <-> G).
The needle is rooted on the cup wall, runs through the centre and its free tip leaves
through the mouth, so every glyph is ONE connected mark.

Strokes are core-first: 1 the cup, 2 the needle from the cup wall to the centre,
3 the needle from the centre out to its tip. Velocity reveals them in this order.
"""
import json, math, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.dirname(os.path.abspath(__file__))   # ours.json, read by uk_glyphs_v2.py
SHEETS = os.path.join(OUT, "out")                   # the review sheet

NAMES = ["C", "C\u266F", "D", "E\u266D", "E", "F", "F\u266F", "G", "A\u266D", "A", "B\u266D", "B"]
LONG = ["C", "C sharp / D flat", "D", "D sharp / E flat", "E", "F", "F sharp / G flat", "G",
        "G sharp / A flat", "A", "A sharp / B flat", "B"]

CX, CY = 0.5, 0.5
R = 0.34            # cup radius (0..1 box)
TIP = 1.30          # the needle's free tip reaches TIP*R from the centre
ARC_STEPS = 24


def clock(deg, rad):
    """point at clock angle deg (0 = 12 o'clock, clockwise; y down), distance rad."""
    a = math.radians(deg)
    return (CX + rad * math.sin(a), CY - rad * math.cos(a))


def glyph(p):
    k3, k4 = p % 3, p % 4
    mouth = (120 * k3) % 360          # C: mouth up (a bowl). +1 mod 3 = +1 fifth -> 120 deg clockwise
    keel = (mouth + 180) % 360        # deepest point of the cup
    nang = (-45 * k4) % 180           # C: vertical. -1 mod 4 = +1 fifth -> 45 deg clockwise
    arc = [clock(keel - 90 + 180 * i / ARC_STEPS, R) for i in range(ARC_STEPS + 1)]

    def on_arc(d):
        return abs((d - keel + 540) % 360 - 180) <= 90 + 1e-6

    e1, e2 = nang, nang + 180
    root, free = (e1, e2) if on_arc(e1) else (e2, e1)
    free_r = R if on_arc(free) else TIP * R   # lidded (F#): both ends on the rim
    strokes = [arc, [clock(root, R), (CX, CY)], [(CX, CY), clock(free, free_r)]]
    flat = [[round(c, 4) for xy in s for c in xy] for s in strokes]
    return {"pc": p, "name": LONG[p], "label": NAMES[p], "mod3_cup_mouth_deg": mouth,
            "mod4_needle_deg": nang, "strokes": flat}


GLYPHS = [glyph(p) for p in range(12)]

# ---- rendering ---------------------------------------------------------
BG = (13, 8, 22)
INK = (236, 226, 255)
LAB = (150, 132, 190)
DIM = (96, 82, 128)


def draw_strokes(strokes, size, frac=1.0, bright=1.0, lw=0.08, ss=8, glow=True):
    """render glyph into an RGB tile of size px (supersampled ss x).
    frac = how much of the total path length (core-first) is lit."""
    S = size * ss
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    w = max(1.0, lw * S)
    lengths = []
    for s in strokes:
        pts = list(zip(s[0::2], s[1::2]))
        lengths.append(sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)))
    budget = frac * sum(lengths)
    for s, L in zip(strokes, lengths):
        if budget <= 1e-9:
            break
        pts = list(zip(s[0::2], s[1::2]))
        use = min(L, budget)
        budget -= use
        acc, out = 0.0, [pts[0]]
        for i in range(len(pts) - 1):
            seg = math.dist(pts[i], pts[i + 1])
            if acc + seg >= use:
                t = (use - acc) / seg if seg else 0
                out.append((pts[i][0] + t * (pts[i + 1][0] - pts[i][0]),
                            pts[i][1] + t * (pts[i + 1][1] - pts[i][1])))
                break
            out.append(pts[i + 1])
            acc += seg
        P = [(x * S, y * S) for x, y in out]
        for i in range(len(P) - 1):
            d.line([P[i], P[i + 1]], fill=255, width=int(round(w)))
        r = w / 2
        for x, y in P:
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    tile = Image.new("RGB", (size, size), BG)
    if glow and size >= 40:
        halo = mask.filter(ImageFilter.GaussianBlur(size * 0.05)).point(lambda v: int(v * 0.55 * bright))
        tile.paste(Image.new("RGB", (size, size), (150, 110, 255)), (0, 0), halo)
    tile.paste(Image.new("RGB", (size, size), tuple(int(c * bright) for c in INK)), (0, 0), mask)
    return tile


def font(sz, bold=False):
    for f in (["seguisym.ttf", "segoeuib.ttf"] if bold else ["seguisym.ttf", "segoeui.ttf"]):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


VEL_LEVELS = [(None, 0.40, "pp  v=24"), (None, 0.60, "mp  v=56"), (None, 0.80, "f  v=92"), (None, 1.0, "ff  v=124")]


def sheet(path):
    cell, gap, pad = 160, 14, 40
    W = pad * 2 + 12 * cell + 11 * gap
    H = 1130
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    y = pad
    d.text((pad, y), "CLOCKWORK OF FIFTHS  (ours)", fill=INK, font=font(32, True))
    d.text((pad + 470, y + 8), "cup = pitch mod 3: mouth at 12 / 4 / 8 o'clock      needle = pitch mod 4: | / - \\      "
           "up a fifth: cup turns 120\u00b0, needle 45\u00b0, both clockwise", fill=LAB, font=font(19))
    y += 62
    for p, g in enumerate(GLYPHS):                               # row 1: 160 px
        x = pad + p * (cell + gap)
        img.paste(draw_strokes(g["strokes"], cell), (x, y))
        d.text((x + cell / 2, y + cell + 4), g["label"], fill=LAB, font=font(26, True), anchor="mt")
    y += cell + 58
    d.text((pad, y - 20), "48 px (Cinema buffer)", fill=DIM, font=font(16))
    for p, g in enumerate(GLYPHS):                               # row 2: 48 px
        img.paste(draw_strokes(g["strokes"], 48), (pad + p * (cell + gap) + (cell - 48) // 2, y))
    y += 48 + 36
    d.text((pad, y - 20), "16 px (live view), native pixels", fill=DIM, font=font(16))
    for p, g in enumerate(GLYPHS):                               # row 3: 16 px
        img.paste(draw_strokes(g["strokes"], 16, glow=False), (pad + p * (cell + gap) + (cell - 16) // 2, y))
    y += 16 + 36
    d.text((pad, y - 20), "the same 16 px pixels, magnified 5x (nearest neighbour)", fill=DIM, font=font(16))
    for p, g in enumerate(GLYPHS):
        t = draw_strokes(g["strokes"], 16, glow=False).resize((80, 80), Image.NEAREST)
        img.paste(t, (pad + p * (cell + gap) + (cell - 80) // 2, y))
    y += 80 + 40
    d.text((pad, y - 20), "velocity: whole strokes revealed core-first (pp cup / mp + needle root / f + needle tip / ff full), brightness rising",
           fill=DIM, font=font(16))
    for gi, p in enumerate([0, 7]):                              # row 4: velocity ladder
        L = [sum(math.dist(s[k:k + 2], s[k + 2:k + 4]) for k in range(0, len(s) - 2, 2)) for s in GLYPHS[p]["strokes"]]
        tiers = [L[0] / sum(L), (L[0] + L[1]) / sum(L), 1.0, 1.0]   # whole strokes, core first
        for i, ((_, br, lab), fr) in enumerate(zip(VEL_LEVELS, tiers)):
            x = pad + (gi * 6 + i) * (cell + gap)
            img.paste(draw_strokes(GLYPHS[p]["strokes"], 130, frac=fr, bright=br), (x + 15, y))
            d.text((x + cell / 2, y + 134), f"{GLYPHS[p]['label']}   {lab}", fill=LAB, font=font(17), anchor="mt")
    y += 134 + 56
    d.text((pad, y - 20), "chords rhyme: in every triad one neighbour pair shares the needle (major third), "
           "the other shares the cup (minor third)", fill=DIM, font=font(16))
    chords = [("C major", [0, 4, 7], "C-E needle, E-G cup"), ("A minor", [9, 0, 4], "A-C cup, C-E needle"),
              ("C augmented", [0, 4, 8], "one needle"), ("C dim7", [0, 3, 6, 9], "one cup"),
              ("F  C  G", [5, 0, 7], "inversion = mirror")]
    x = pad
    for name, pcs, note in chords:
        for j, p in enumerate(pcs):
            img.paste(draw_strokes(GLYPHS[p]["strokes"], 92), (x + j * 96, y))
            d.text((x + j * 96 + 46, y + 96), GLYPHS[p]["label"], fill=LAB, font=font(18, True), anchor="mt")
        d.text((x, y + 126), name, fill=INK, font=font(20, True))
        d.text((x, y + 152), note, fill=LAB, font=font(16))
        x += len(pcs) * 96 + 44
    img.save(path)


if __name__ == "__main__":
    os.makedirs(SHEETS, exist_ok=True)
    sheet(os.path.join(SHEETS, "ours.png"))
    data = {
        "id": "ours",
        "name": "Clockwork of Fifths",
        "licence": "Original work drawn for Akashic Aurora (no font or icon outlines used).",
        "system": ("Pitch class p = (p mod 3, p mod 4). CUP: half-circle, mouth at 12/4/8 o'clock for p mod 3 = 0/1/2; "
                   "minor thirds share a cup. NEEDLE: line through the centre at 0/135/90/45 deg for p mod 4 = 0/1/2/3; "
                   "major thirds share a needle. Up a fifth: cup +120 deg, needle +45 deg, both clockwise. "
                   "Left-right mirror = inversion about C. Strokes core-first: cup, needle root half, needle tip half."),
        "glyphs": [{"pc": g["pc"], "name": g["name"], "strokes": g["strokes"]} for g in GLYPHS],
    }
    with open(os.path.join(OUT, "ours.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1)
    print("ok")
