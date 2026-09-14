# Contact sheets of the AA bench stills: the same crops from every config, upscaled 4x nearest so pixels stay visible.
# usage: py crops.py <run label>
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

RUN = Path(r"C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/res-lab/runs") / sys.argv[1]
OUT = Path(r"E:/AI-Setup/research/in-flight/piano-spectacle-2026-09-13/aa-crops")
OUT.mkdir(parents=True, exist_ok=True)
rep = json.loads((RUN / "aa-bench.json").read_text())
W, H = rep["native"]["output"]["w"], rep["native"]["output"]["h"]

# crop boxes as fractions of the canvas: keys and rail, the column feet with sparks, a column top in the sky
REGIONS = ({"keys": (0.10, 0.705, 0.55, 0.80), "feet-sparks": (0.30, 0.58, 0.75, 0.72), "sky": (0.25, 0.30, 0.70, 0.45)} if W < H else {"keys": (0.30, 0.66, 0.52, 0.84), "feet-sparks": (0.35, 0.50, 0.57, 0.66), "sky": (0.40, 0.25, 0.62, 0.42)})
IN_PIPE = ["reference", "none", "msaa4", "smaa", "taa-x4", "ss1.5-box+msaa4", "ss2-box", "ss2-box+msaa4"]
rows = {c["id"]: c for c in rep["configs"]}
ZOOM = 4 if W < 600 else 3


def sheet(images, labels, name, region):
    x0, y0, x1, y1 = region
    box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
    tiles = [im.crop(box).resize(((box[2] - box[0]) * ZOOM, (box[3] - box[1]) * ZOOM), Image.NEAREST) for im in images]
    tw, th = tiles[0].size
    cols = 2
    canvas = Image.new("RGB", (cols * tw + (cols + 1) * 8, ((len(tiles) + cols - 1) // cols) * (th + 30) + 8), (24, 24, 28))
    d = ImageDraw.Draw(canvas)
    for i, (t, label) in enumerate(zip(tiles, labels)):
        cx, cy = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 30)
        d.text((cx, cy), label, fill=(235, 235, 235))
        canvas.paste(t, (cx, cy + 20))
    canvas.save(OUT / name)
    return OUT / name


made = []
imgs, labels = [], []
for cid in IN_PIPE:
    p = RUN / f"{cid}.png"
    if not p.exists():
        continue
    imgs.append(Image.open(p).convert("RGB"))
    r = rows.get(cid)
    labels.append(cid if not r else f"{cid}  scene {r['internal']['w']}x{r['internal']['h']}  MAE {r['mae']:.4f}  edge {r['edgeMae']:.4f}  shimmer {r['edgeShimmer']:.4f}")
for rname, region in REGIONS.items():
    made.append(sheet(imgs, labels, f"{sys.argv[1]}-pipeline-{rname}.png", region))

# display path: crop the canvas out of the viewport screenshots
al = rep.get("displayAlign")
if al:
    dpr = al["rect"]["dpr"]
    ox = round(al["rect"]["x"] * dpr) + al["offset"]["dx"]
    oy = round(al["rect"]["y"] * dpr) + al["offset"]["dy"]
    dimgs, dlabels = [Image.open(RUN / "reference.png").convert("RGB")], ["reference (4x, box) - no overlay in this still"]
    for d in rep["display"]:
        p = RUN / f"display-{d['id']}.png"
        full = Image.open(p).convert("RGB")
        dimgs.append(full.crop((ox, oy, ox + W, oy + H)))
        dlabels.append(f"{d['id']} (as displayed)  MAE {d['mae']:.4f}  edge {d['edgeMae']:.4f}  shimmer {d['edgeShimmer']:.4f}")
    for rname, region in {**REGIONS, **({"label": (0.20, 0.08, 0.80, 0.22), "staff": (0.10, 0.36, 0.60, 0.52)} if W < H else {"label": (0.02, 0.06, 0.40, 0.30), "staff": (0.66, 0.05, 0.96, 0.45)})}.items():
        made.append(sheet(dimgs, dlabels, f"{sys.argv[1]}-display-{rname}.png", region))
print("\n".join(str(m) for m in made))
