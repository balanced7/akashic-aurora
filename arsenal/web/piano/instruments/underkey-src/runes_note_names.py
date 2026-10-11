# Our own stroke redraw of traditional runic shapes (public-domain shapes).
# Box 0..1, y down. Strokes ordered core-first: stroke 1 alone must already
# read as this rune (and never as a flagged symbol); later strokes complete it.
import json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ID = "runes-note-names"
NAME = "Runes that spell their note names (Anglo-Saxon Futhorc)"

T, B = 0.08, 0.92           # cap line / base line
G = [
 # pc, name, rune, strokes
 ("C",  "cen",    "\u16B3", [[(0.36,T),(0.36,0.48),(0.72,B)],            # top stave flowing into the leg
                             [(0.36,0.48),(0.36,B)]]),                    # rest of the stave
 ("C#", "nyd",    "\u16BE", [[(0.50,T),(0.50,B)],                         # the spindle
                             [(0.26,0.36),(0.74,0.62)]]),                 # the need-cut
 ("D",  "daeg",   "\u16DE", [[(0.25,B),(0.25,T),(0.75,B),(0.75,T)],       # N
                             [(0.75,T),(0.25,B)]]),                       # second diagonal closes the bowtie
 ("D#", "ur",     "\u16A2", [[(0.30,0.60),(0.30,T),(0.72,0.30),(0.72,0.60)],  # the arch
                             [(0.30,0.60),(0.30,B)],
                             [(0.72,0.60),(0.72,B)]]),                    # legs grow with velocity
 ("E",  "eh",     "\u16D6", [[(0.25,0.58),(0.25,T),(0.50,0.32),(0.75,T),(0.75,0.58)],  # short M
                             [(0.25,0.58),(0.25,B)],
                             [(0.75,0.58),(0.75,B)]]),
 ("F",  "feoh",   "\u16A0", [[(0.74,T),(0.34,0.32),(0.34,0.56),(0.74,0.32)],  # both branches + their stave
                             [(0.34,0.56),(0.34,B)],
                             [(0.34,0.32),(0.34,T)]]),
 ("F#", "ing",    "\u16DD", [[(0.27,T),(0.73,0.50),(0.27,B)],             # '>' chevron
                             [(0.73,T),(0.27,0.50),(0.73,B)]]),           # '<' chevron: crossings at top AND bottom
 ("G",  "gyfu",   "\u16B7", [[(0.24,T),(0.76,B)],
                             [(0.76,T),(0.24,B)]]),
 ("G#", "thorn",  "\u16A6", [[(0.34,0.29),(0.74,0.50),(0.34,0.71),(0.34,0.29)],  # closed thorn
                             [(0.34,0.29),(0.34,T)],
                             [(0.34,0.71),(0.34,B)]]),
 ("A",  "ac",     "\u16AA", [[(0.76,T),(0.55,0.26),(0.34,T),(0.34,0.38),(0.76,0.68)],  # notched arm + stave + branch
                             [(0.34,0.38),(0.34,B)]]),
 ("A#", "peordh", "\u16C8", [[(0.76,B),(0.54,0.70),(0.32,B),(0.32,T)],    # stave on its notched foot
                             [(0.32,T),(0.54,0.30),(0.76,T)]]),           # notched head
 ("B",  "beorc",  "\u16D2", [[(0.34,B),(0.34,T),(0.72,0.29),(0.34,0.50)], # stave + upper bowl
                             [(0.34,0.50),(0.72,0.71),(0.34,B)]]),        # lower bowl
]

ALT = [
 ("A", "ansuz (Elder fallback)", "ᚨ", [[(0.74,0.30),(0.34,T),(0.34,0.34),(0.74,0.58)],
                             [(0.34,0.34),(0.34,B)]]),
 ("C", "kaunan (Elder fallback)", "ᚲ", [[(0.68,0.14),(0.32,0.50)],
                             [(0.32,0.50),(0.68,0.86)]]),
]

def data():
    return {"id": ID, "name": NAME, "glyphs": [
        {"pc": pc, "name": f"{nm} {r}",
         "strokes": [[round(c,3) for pt in s for c in pt] for s in st]}
        for pc, nm, r, st in G],
        "alternates": [{"pc": pc, "name": f"{nm} {r}",
         "strokes": [[round(c,3) for pt in s for c in pt] for s in st]}
        for pc, nm, r, st in ALT]}

BG = (16, 10, 24)
INK = (236, 226, 255)
SS = 4  # supersample

def draw_glyph(strokes, size, bright=1.0, nshow=None, lw_frac=0.08, box=None):
    """Render strokes into an RGBA tile of `size` (w,h); box = glyph square side (fit height)."""
    w, h = size if isinstance(size, tuple) else (size, size)
    W, H = w*SS, h*SS
    side = (box or min(w, h)) * SS
    ox, oy = (W-side)/2, (H-side)/2
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    lw = max(1.0, lw_frac*side)
    sel = strokes if nshow is None else strokes[:nshow]
    for s in sel:
        pts = [(ox+x*side, oy+y*side) for x, y in s]
        d.line(pts, fill=255, width=int(round(lw)))
        r = lw/2
        for x, y in pts:
            d.ellipse([x-r, y-r, x+r, y+r], fill=255)
    a = im.resize((w, h), Image.LANCZOS)
    a = a.point(lambda v: int(v*bright))
    return a

def paste_ink(sheet, alpha, xy, glow=0.0):
    x, y = xy
    if glow > 0:
        g = alpha.filter(ImageFilter.GaussianBlur(alpha.size[0]*0.06)).point(lambda v: int(min(255, v*glow*2.2)))
        col = Image.new("RGB", alpha.size, (150, 110, 255))
        sheet.paste(col, (x, y), g)
    sheet.paste(Image.new("RGB", alpha.size, INK), (x, y), alpha)

def reveal(N, v):
    f = v/127
    return max(1, math.ceil(f*N)), 0.25 + 0.75*f*f

def sheet(path):
    lab = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
    small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
    run = ImageFont.truetype(r"C:\Windows\Fonts\seguihis.ttf", 18)
    n = len(G); C1 = 160; PAD = 30
    Wd = n*C1 + 2*PAD
    rows_h = [26, C1+44, 26, 48+10, 26, 16+10, 26, 16*6+10, 26, 28+10, 26, 48+10, 26, 200+40, 26, 130]
    im = Image.new("RGB", (Wd, sum(rows_h)+PAD), BG); d = ImageDraw.Draw(im)
    y = 10
    def title(t):
        nonlocal y
        d.text((PAD, y), t, font=lab, fill=(170, 160, 200)); y += 26
    title(f"{ID}  -  row 1: 160 px cells, stroke 8% of cell, round caps")
    for i, (pc, nm, r, st) in enumerate(G):
        x = PAD + i*C1
        d.rectangle([x+2, y, x+C1-2, y+C1], outline=(40, 30, 56))
        paste_ink(im, draw_glyph(st, C1), (x, y), glow=0.35)
        d.text((x+6, y+C1+4), pc, font=lab, fill=(230, 210, 255))
        d.text((x+44, y+C1+4), r, font=run, fill=(150, 140, 180))
        d.text((x+68, y+C1+6), nm + f" ({len(st)})", font=small, fill=(150, 140, 180))
    y += C1+44
    title("row 2: 48 px (Cinema buffer)")
    for i, (pc, nm, r, st) in enumerate(G):
        paste_ink(im, draw_glyph(st, 48), (PAD + i*C1 + 56, y))
    y += 58
    title("row 3: 16 px (live) - native size, and below magnified x6 (nearest)")
    tiles = []
    for i, (pc, nm, r, st) in enumerate(G):
        a = draw_glyph(st, 16); tiles.append(a)
        paste_ink(im, a, (PAD + i*C1 + 72, y))
    y += 24
    for i, a in enumerate(tiles):
        big = a.resize((96, 96), Image.NEAREST)
        x = PAD + i*C1 + 32
        im.paste(Image.new("RGB", (96, 96), BG), (x, y))
        paste_ink(im, big, (x, y))
    y += 16*6+10+26
    title("row 3b: live slip band cell 17 x 28 px (glyph box fit to height)")
    for i, (pc, nm, r, st) in enumerate(G):
        paste_ink(im, draw_glyph(st, (17, 28), box=28), (PAD + i*C1 + 72, y))
    y += 38
    title("row 4: pianissimo partial (stroke 1 only, v=32) at 48 px - soft notes must still read")
    for i, (pc, nm, r, st) in enumerate(G):
        k, b = reveal(len(st), 32)
        paste_ink(im, draw_glyph(st, 48, bright=max(b, 0.55), nshow=k), (PAD + i*C1 + 56, y))
    y += 58
    gi = [g[0] for g in G].index("F")
    pc, nm, r, st = G[gi]
    title(f"row 5: one glyph ({pc} {nm}) at velocity 32 / 64 / 96 / 127 - strokes revealed core-first, brightness ~ v^2")
    for j, v in enumerate([32, 64, 96, 127]):
        k, b = reveal(len(st), v)
        x = PAD + j*(200+60)
        paste_ink(im, draw_glyph(st, 200, bright=b, nshow=k), (x, y), glow=b*0.6)
        d.text((x+6, y+202), f"v={v}  strokes {k}/{len(st)}  bright {b:.2f}", font=small, fill=(150, 140, 180))
    # extra: same four levels at 16 px
    for j, v in enumerate([32, 64, 96, 127]):
        k, b = reveal(len(st), v)
        paste_ink(im, draw_glyph(st, 16, bright=b, nshow=k), (PAD + 4*260 + 40 + j*40, y + 92))
    d.text((PAD + 4*260 + 40, y + 120), "same, at 16 px", font=small, fill=(150, 140, 180))
    y += 240
    title("row 6: Elder Futhark fallbacks (alternates, not in the 12): 48 px, 16 px, 16 px x6")
    for i, (pc, nm, r, st) in enumerate(ALT):
        x = PAD + i*420
        paste_ink(im, draw_glyph(st, 48), (x, y+20))
        paste_ink(im, draw_glyph(st, 16), (x+70, y+36))
        paste_ink(im, draw_glyph(st, 16).resize((96, 96), Image.NEAREST), (x+110, y))
        d.text((x+220, y+40), f"{pc} = {nm}", font=small, fill=(150, 140, 180))
        d.text((x+220, y+60), r, font=run, fill=(150, 140, 180))
    im.save(path)

if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__))          # runes-note-names.json, read by uk_glyphs_v2.py
    with open(os.path.join(base, ID + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data(), f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(base, "out"), exist_ok=True)
    sheet(os.path.join(base, "out", ID + ".png"))              # the review sheet
    print("ok")
