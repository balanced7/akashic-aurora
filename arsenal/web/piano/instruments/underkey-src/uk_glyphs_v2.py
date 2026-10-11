# Under-key runes, v2: the four KEPT sets with every judge fix applied, simplified to straight segments, and packed
# into the compact table pasted into ../glass-piano.js (RUNE_SETS). Nothing here is traced from a font; the source
# strokes are the set generators' own polylines (runes_note_names.py, ogham_edge.py, ours_gen.py and tone_zodiac.py,
# beside this file; the first three write the .json this reads), edited below where the glyph judge asked. The page
# never loads this folder.
#
#   py uk_glyphs_v2.py   -> out/<id>.json, out/underkey-glyphs.js, out/sheet-<id>.png, out/band-9x16-span44.png, report
#
# To change a glyph: edit its set generator (or the fix below), re-run that generator and then this, check the sheets'
# look-alike report, and paste out/underkey-glyphs.js over the RUNE_SETS block in glass-piano.js (from
# "const RUNE_SETS" to its closing "]);"; the comment block above it in glass-piano.js is the file's own).
#
# Stroke classes: 0 identity (always drawn whole), 1 ghost (dim dial, ours only), 2 ornament (revealed by velocity).
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
UK = HERE                                 # the set sources sit beside this file
OUTDIR = os.path.join(HERE, "out")        # generated files only (out/ is git-ignored)
sys.path.insert(0, UK)
import tone_zodiac as TZ   # its main() is guarded; we reuse its helpers and SIGNS

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
WHITE_PC = {0, 2, 4, 5, 7, 9, 11}

def load(fn):
    with open(os.path.join(UK, fn), encoding='utf-8') as f:
        return json.load(f)

def pts(flat):
    return [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]

def flat(p):
    return [c for xy in p for c in xy]

# ------------------------------------------------------------------ simplification (Douglas-Peucker)
def dp(p, tol):
    if len(p) < 3:
        return p
    a, b = np.array(p[0]), np.array(p[-1])
    ab = b - a; L = np.hypot(*ab)
    best, bi = -1, -1
    for i in range(1, len(p) - 1):
        q = np.array(p[i])
        if L < 1e-9:
            d = np.hypot(*(q - a))
        else:
            d = abs(ab[0] * (q - a)[1] - ab[1] * (q - a)[0]) / L
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [p[0], p[-1]]
    return dp(p[:bi + 1], tol)[:-1] + dp(p[bi:], tol)

# ------------------------------------------------------------------ the four sets, with the judge's fixes
def set_runes():
    d = load('runes-note-names.json')               # alternates (ansuz, kaunan) left out of the build, judge fix 4
    out = []
    for g in d['glyphs']:
        out.append(dict(pc=NAMES.index(g['pc']), name=g['name'], strokes=[(0, pts(s)) for s in g['strokes']]))
    return out

def uilleann():
    # judge fix 4: one round curl that crosses the stem (was a boxy spiral on the B side, read as "l9"). A bowl hung on
    # one side of the stem reads as b, d, p or q (a note letter under the wrong key), so the curl is centred ON the stem:
    # a spiral low on the stem, 1.25 turns inward with an open eye (inner radius 0.12, so the hole survives at 22 px).
    # Chosen by a parameter search for the lowest worst-case 16/22 px correlation with the other eleven (0.57, C#).
    cx, cy, a0, sweep, r0, r1, n = 0.50, 0.65, 60.0, 450.0, 0.26, 0.12, 48
    return [(cx + (r0 + (r1 - r0) * i / n) * math.cos(math.radians(a0 + sweep * i / n)),
             cy + (r0 + (r1 - r0) * i / n) * math.sin(math.radians(a0 + sweep * i / n))) for i in range(n + 1)]

def set_ogham():
    d = load('ogham-edge.json')                     # alt_tally dropped, judge fix 2
    out = []
    for g in d['glyphs']:
        pc = NAMES.index(g['pc'])
        strokes = []
        cuts = [pts(s) for s in g['strokes'][1:]]
        if g['name'] == 'ailm':                      # fix 3: the full crossbar
            cuts = [[(0.15, 0.5), (0.85, 0.5)]]
        if g['name'] == 'beith':                     # fix 3: beith's one cut moves up, so A and B differ by place too
            cuts = [[(0.5, 0.3), (0.75, 0.3)]]
        if g['name'] == 'uilleann':
            cuts = [uilleann()]
        # fix 1: the stem grows with velocity. Identity stem 0.15..0.85 written bottom-up (the stones read upward),
        # ornament stubs to 0.05 and 0.95 revealed toward forte. The cuts never change.
        strokes.append((0, [(0.5, 0.85), (0.5, 0.15)]))
        for c in cuts:
            strokes.append((0, c))
        strokes.append((2, [(0.5, 0.85), (0.5, 0.95)]))
        strokes.append((2, [(0.5, 0.15), (0.5, 0.05)]))
        out.append(dict(pc=pc, name=g['name'], strokes=strokes))
    return out

def scale_y(p, f, c=0.5):
    return [(x, c + (y - c) * f) for x, y in p]

def zodiac_signs():
    S = {k: dict(v) for k, v in TZ.SIGNS.items()}
    arc, cubic, seg, join, rot180 = TZ.arc, TZ.cubic, TZ.seg, TZ.join, TZ.rot180
    # fix 3: Libra and Aquarius fill ~70 % of the box height (were 0.54 and 0.58)
    S[6]['strokes'] = [scale_y(s, 0.70 / 0.54) for s in TZ.SIGNS[6]['strokes']]
    S[10]['strokes'] = [scale_y(s, 0.70 / 0.58, 0.51) for s in TZ.SIGNS[10]['strokes']]
    # fix 3: Cancer's loops opened: smaller loops, wider gap between the two halves
    cu = join(cubic((0.95, 0.42), (0.94, 0.17), (0.62, 0.08), (0.25, 0.16)), arc(0.25, 0.27, 0.11, 0.11, -90, -450))
    S[3]['strokes'] = [cu, rot180(cu)]
    # fix 5: Sagittarius' crossbar at least 40 % of the shaft (46 %), still square to it
    S[8]['strokes'] = [TZ.SIGNS[8]['strokes'][0], TZ.SIGNS[8]['strokes'][1], seg((0.20, 0.44), (0.56, 0.80))]
    # fix 2: the m-pair told apart by outline. Scorpio's sting rises above the humps to an arrowhead ~30 % of the
    # glyph's width pointing up-right; Virgo's m is raised and its closed loop hangs below the baseline.
    LX, HR = TZ._LX, TZ._HR
    hump2 = arc(LX[1] + HR, 0.31, HR, HR, 180, 360)
    mB = join(seg((LX[0], 0.84), (LX[0], 0.31)), arc(LX[0] + HR, 0.31, HR, HR, 180, 360), seg((LX[1], 0.31), (LX[1], 0.84)))
    S[7]['strokes'] = [
        join(hump2, seg((LX[2], 0.31), (LX[2], 0.72)), cubic((0.47, 0.72), (0.47, 0.87), (0.55, 0.91), (0.65, 0.86), n=10),
             seg((0.65, 0.86), (0.94, 0.08))),
        seg((0.68, 0.08), (0.94, 0.08), (0.94, 0.34)),
        mB,
    ]
    VY, VB = 0.22, 0.62
    hump2v = arc(LX[1] + HR, VY, HR, HR, 180, 360)
    mBv = join(seg((LX[0], VB), (LX[0], VY)), arc(LX[0] + HR, VY, HR, HR, 180, 360), seg((LX[1], VY), (LX[1], VB)))
    S[5]['strokes'] = [
        join(hump2v, seg((LX[2], VY), (LX[2], 0.78)),
             cubic((0.47, 0.78), (0.47, 0.97), (0.74, 0.99), (0.78, 0.82)),
             cubic((0.78, 0.82), (0.82, 0.62), (0.62, 0.52), (0.56, 0.68)),
             seg((0.56, 0.68), (0.40, 0.98))),
        mBv,
    ]
    return S

def set_zodiac():
    S = zodiac_signs()
    out = []
    for pc in range(12):
        s = (7 * pc) % 12                             # tone-zodiac: Aries on C, round the circle of fifths
        out.append(dict(pc=pc, name=S[s]['name'], strokes=[(0, list(st)) for st in S[s]['strokes']]))
    return out

def set_ours():
    d = load('ours.json')
    out = []
    for g in d['glyphs']:
        st = [pts(s) for s in g['strokes']]
        cup = st[0]
        a0 = math.degrees(math.atan2(cup[0][0] - 0.5, -(cup[0][1] - 0.5)))      # clock angles (0 = 12 o'clock, cw)
        a1 = math.degrees(math.atan2(cup[-1][0] - 0.5, -(cup[-1][1] - 0.5)))
        R = math.hypot(cup[0][0] - 0.5, cup[0][1] - 0.5)
        # fix 1: the ghost dial, the missing half of the circle (class 1: ~25 % bright, ~60 % stroke width)
        ghost = []
        for i in range(25):
            a = math.radians(a1 + 180 * i / 24)
            ghost.append((0.5 + R * math.sin(a), 0.5 - R * math.cos(a)))
        # check round 3 fix: the needle's free tip stops inside the dial (TIP_IN x R from the centre), never out past
        # the rim. Leaving through the mouth, C's needle (a bowl, a vertical needle, the ghost upper half) drew the IEC
        # power symbol. The lidded glyph (F#, both ends on the rim) is unchanged; the cup and the needle's angle, so
        # the set's system (cup = pc mod 3, needle = pc mod 4, mirror = inversion about C), are untouched.
        free = st[2]
        (fx, fy), fr = free[-1], math.hypot(free[-1][0] - 0.5, free[-1][1] - 0.5)
        if fr > R + 1e-6:
            k = TIP_IN * R / fr
            free = [free[0], (0.5 + (fx - 0.5) * k, 0.5 + (fy - 0.5) * k)]
        out.append(dict(pc=g['pc'], name=g['name'], strokes=[(0, cup), (0, st[1]), (0, free), (1, ghost)]))
    return out

TIP_IN = 0.55   # the needle's free tip, as a share of the cup's radius (was 1.30 in ours.json: out past the rim;
                # at 0.72 the ff ghost dial closed round a near-full diameter, the power on-off sign)

SETS = [
    # value, menu name, title (tooltip), builder
    ('runes', 'Runes (note names)', 'Anglo-Saxon runes that spell their note names: A ac, B beorc, C cen, D daeg, E eh, F feoh, '
     'G gyfu; the black keys take nyd, ur, ing, thorn and peorth. The M under E is the rune eh.', set_runes),
    ('clockwork', 'Clockwork of fifths (ours)', 'Our own set: a half-moon cup and a needle. Up a fifth, the cup turns a third of '
     'a turn and the needle an eighth. Notes a major third apart share a needle, a minor third apart share a cup; a mirror '
     'image is the inversion about C (F and G are mirror twins).', set_ours),
    ('ogham', 'Ogham', 'The Irish tree alphabet, cut along the slip like an edge of stone: coll C, dair D, eadhadh E, fearn F, '
     'gort G, ailm A, beith B; the five forfeda take the black keys.', set_ogham),
    ('zodiac', 'Tone zodiac (Steiner)', 'The tone-zodiac of Rudolf Steiner and Sigismund von Gleich: Aries on C, then round '
     'the circle of fifths, so neighbouring signs are a fifth apart and a held chord lights a compact arc of the wheel.', set_zodiac),
]

TOL = 0.004   # box units: at the white row's 0.80 em that is 0.0032 instrument units, ~0.15 Cinema px at span 44

def build():
    packed = []
    for value, name, title, fn in SETS:
        glyphs = fn()
        assert len(glyphs) == 12 and sorted(g['pc'] for g in glyphs) == list(range(12)), value
        glyphs.sort(key=lambda g: g['pc'])
        for g in glyphs:
            g['strokes'] = [(c, dp([tuple(map(float, q)) for q in p], TOL)) for c, p in g['strokes']]
        packed.append(dict(value=value, name=name, title=title, glyphs=glyphs))
    return packed

def nseg(g):
    return sum(len(p) - 1 for c, p in g['strokes'])

# ------------------------------------------------------------------ rendering (review only)
SS = 8
def raster(strokes, size, lw=0.08, ghost=0.25, orn=1.0, frac=1.0):
    S = size * SS
    im = Image.new('F', (S, S), 0.0)
    layers = {}
    for c, p in strokes:
        if c not in layers:
            layers[c] = Image.new('L', (S, S), 0)
        dr = ImageDraw.Draw(layers[c])
        w = max(1, int(round(lw * S * (0.6 if c == 1 else 1.0))))
        q = [(x * S, y * S) for x, y in p]
        dr.line(q, fill=255, width=w, joint='curve')
        for e in (q[0], q[-1]):
            dr.ellipse([e[0] - w / 2, e[1] - w / 2, e[0] + w / 2, e[1] + w / 2], fill=255)
    acc = np.zeros((S, S), dtype=float)
    for c, L in layers.items():
        k = {0: 1.0, 1: ghost, 2: orn}[c]
        acc = np.maximum(acc, np.asarray(L, dtype=float) / 255 * k)
    out = Image.fromarray((acc * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    return np.asarray(out, dtype=float) / 255

def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum() + 1e-9))

def distinct(glyphs, size=16, orn=0.0):
    r = {g['pc']: raster(g['strokes'], size, orn=orn) for g in glyphs}
    pairs = sorted(((ncc(r[a], r[b]), NAMES[a], NAMES[b]) for a in range(12) for b in range(a + 1, 12)), reverse=True)
    return pairs

def sheet(entry):
    g = entry['glyphs']
    cell = 112
    W = 12 * cell + 40
    H = 520
    im = Image.new('RGB', (W, H), (12, 9, 20))
    dr = ImageDraw.Draw(im)
    dr.text((20, 8), f"{entry['value']}  -  {entry['name']}   (v2: judge fixes applied; identity strokes always whole; ghost 25 %, ornaments shown at ff)", fill=(220, 210, 245))
    y = 30
    for row, (size, orn, label) in enumerate([(96, 1.0, '96 px, ff (ornaments on)'), (96, 0.0, '96 px, pp (identity only)'),
                                              (43, 1.0, 'white row, 9:16 Cinema span 44 (em 43 px)'),
                                              (22, 1.0, 'black row, 9:16 Cinema span 44 (em 22 px)'),
                                              (16, 0.0, '16 px (the distinctness test size)')]):
        dr.text((20, y), label, fill=(150, 138, 185)); y += 14
        for i, gl in enumerate(g):
            r = raster(gl['strokes'], size, orn=orn)
            tile = Image.fromarray((np.clip(r, 0, 1) * np.array([236, 228, 255])[None, None, :]).astype(np.uint8)
                                   if False else (np.stack([r * 236, r * 228, r * 255], -1)).astype(np.uint8))
            x = 20 + i * cell
            im.paste(tile, (x, y))
            if row == 0:
                dr.text((x, y + size + 1), f"{NAMES[gl['pc']]} {gl['name'][:14]}", fill=(170, 160, 200))
        y += size + (16 if row == 0 else 8)
    pairs = distinct(g)
    dr.text((20, y + 4), 'closest pairs at 16 px (NCC, identity strokes): ' + ', '.join(f'{a}/{b} {s:.2f}' for s, a, b in pairs[:5]), fill=(200, 190, 230))
    im = im.crop((0, 0, W, y + 26))
    im.save(os.path.join(OUTDIR, f"sheet-{entry['value']}.png"))
    return pairs

# the 9:16 Performance band at span 44 in the Cinema buffer: 48 px per white key, the flat face 89 px tall
# (53.5 px per instrument unit vertically). Rows per the spec: white cell centre y -1.62, em 0.80; black centre -0.89,
# em 0.42. The resting key-front bottoms show through the top 0.17 units (strip y -0.46..-0.63).
PXU_X, PXU_Y, YTOP = 48.0, 53.5, -0.46
BLACK_CENTER = {1: 0.9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5.0, 10: 3 + 4 / 7 * 5.5}
WHITE_OFFSET = [0, -1, 1, -1, 2, 3, -1, 4, -1, 5, -1, 6]
def octx(pc):
    return BLACK_CENTER[pc] if pc in BLACK_CENTER else WHITE_OFFSET[pc] + 0.5

def band(entries, lit, octaves=2, pressed=()):
    W = int(octaves * 7 * PXU_X); Hb = int(1.66 * PXU_Y)
    rows = []
    for e in entries:
        im = np.zeros((Hb, W, 3))
        # resting key-front bottoms, ivory, seen through the top 0.17 units; a pressed key's front drops to -0.63-dip
        for k in range(octaves * 7):
            x0 = int(k * PXU_X + 0.03 * PXU_X); x1 = int((k + 1) * PXU_X - 0.03 * PXU_X)
            pcs = [0, 2, 4, 5, 7, 9, 11][k % 7]
            dip = 0.44 if (k // 7, pcs) in pressed else 0.0
            yb = int((YTOP - (-0.63 - dip)) * PXU_Y)
            im[0:yb, x0:x1] = (0.32, 0.30, 0.27) if dip == 0 else (0.55, 0.35, 0.60)
        for (o, pc) in lit:
            g = next(gl for gl in e['glyphs'] if gl['pc'] == pc)
            white = pc in WHITE_PC
            em = (0.80 if white else 0.42)
            cy = -1.62 if white else -0.89
            cx = (o * 7 + octx(pc)) * PXU_X
            sz_y = em * PXU_Y; sz_x = em * PXU_X
            n = int(round(max(sz_x, sz_y)))
            r = raster(g['strokes'], n, lw=(0.08 if white else 0.10), orn=0.5)
            r = np.asarray(Image.fromarray((r * 255).astype(np.uint8)).resize((max(1, int(round(sz_x))), max(1, int(round(sz_y)))), Image.LANCZOS), dtype=float) / 255
            h, w = r.shape
            x0 = int(round(cx - w / 2)); y0 = int(round((YTOP - cy) * PXU_Y - h / 2))
            ys, xs = slice(max(0, y0), min(Hb, y0 + h)), slice(max(0, x0), min(W, x0 + w))
            sub = r[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
            col = np.array([0.55, 0.85, 1.0]) if white else np.array([1.0, 0.75, 0.45])
            im[ys, xs] = im[ys, xs] * (1 - 0.9 * sub[..., None]) + sub[..., None] * col
        rows.append(im)
    return rows

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    packed = build()
    report = []
    for e in packed:
        pairs = sheet(e)
        segs = [nseg(g) for g in e['glyphs']]
        report.append(dict(value=e['value'], max_segments=max(segs), total_segments=sum(segs),
                           closest=[(round(s, 3), a, b) for s, a, b in pairs[:4]]))
        with open(os.path.join(OUTDIR, f"{e['value']}.json"), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(dict(value=e['value'], name=e['name'], title=e['title'], box='0..1, y down',
                           classes={'0': 'identity', '1': 'ghost', '2': 'ornament'},
                           glyphs=[dict(pc=g['pc'], name=g['name'], strokes=[[c] + [round(v, 3) for v in flat(p)] for c, p in g['strokes']])
                                   for g in e['glyphs']]), f, ensure_ascii=False, indent=1)
    # the compact table for glass-piano.js: per glyph, strokes as [class, x0, y0, x1, y1, ...] in thousandths of the box
    lines = ['// RUNE_SETS: generated by arsenal/web/piano/instruments/underkey-src/uk_glyphs_v2.py from our own stroke data (public-domain shapes',
             '// redrawn; nothing traced from a font). Per set: 12 glyphs by pitch class (0 = C); per glyph, strokes as',
             '// [class, x0, y0, x1, y1, ...] in thousandths of a 0..1 box, y down. Class 0 identity (always whole), 1 ghost',
             '// (the dim half dial), 2 ornament (revealed toward forte). Strokes are listed in writing order.',
             'const RUNE_SETS = Object.freeze([']
    for e in packed:
        gl = ',\n'.join('    [' + ', '.join('[' + ','.join([str(c)] + [str(int(round(v * 1000))) for v in flat(p)]) + ']' for c, p in g['strokes']) + ']'
                        for g in e['glyphs'])
        lines.append(f'  {{ value: {json.dumps(e["value"])}, name: {json.dumps(e["name"])},\n    title: {json.dumps(e["title"], ensure_ascii=True)},\n    glyphs: [\n{gl}] }},')
    lines.append(']);')
    js = '\n'.join(lines) + '\n'
    with open(os.path.join(OUTDIR, 'underkey-glyphs.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(js)
    # the band check: a C7 chord, a pedalled chromatic run, all 12 lit, and all 12 over a pressed ff neighbour
    scen = [('C7 (C E G Bb)', [(0, 0), (0, 4), (0, 7), (0, 10)], ()),
            ('pedalled run C..E', [(0, p) for p in range(5)], ()),
            ('all 12', [(0, p) for p in range(12)], ()),
            ('all 12, C D E pressed ff', [(0, p) for p in range(12)], ((0, 0), (0, 2), (0, 4)))]
    tiles = []
    for name, lit, pressed in scen:
        tiles.append((name, band(packed, lit, octaves=1, pressed=pressed)))
    Wt = sum(t[1][0].shape[1] for t in tiles) + 20 * len(tiles) + 120
    Hr = tiles[0][1][0].shape[0]
    out = Image.new('RGB', (Wt, 30 + len(packed) * (Hr + 12)), (8, 6, 14))
    dr = ImageDraw.Draw(out)
    x = 120
    for name, rows in tiles:
        dr.text((x, 8), name, fill=(200, 190, 230))
        for i, r in enumerate(rows):
            out.paste(Image.fromarray((np.clip(r, 0, 1) * 255).astype(np.uint8)), (x, 26 + i * (Hr + 12)))
        x += rows[0].shape[1] + 20
    for i, e in enumerate(packed):
        dr.text((6, 26 + i * (Hr + 12) + Hr // 2 - 6), e['value'], fill=(170, 160, 200))
    out.save(os.path.join(OUTDIR, 'band-9x16-span44.png'))
    print(json.dumps(report, indent=1))
    print('js bytes', len(js.encode()))

if __name__ == '__main__':
    main()
