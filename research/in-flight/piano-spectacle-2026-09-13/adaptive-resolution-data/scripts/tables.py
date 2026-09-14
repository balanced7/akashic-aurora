# Markdown tables from the aa-bench runs, so the report quotes the JSON instead of hand-copied numbers.
import json, sys
from pathlib import Path
RUNS = Path(r"C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/res-lab/runs")
out = []
for label in sys.argv[1:]:
    p = RUNS / label / "aa-bench.json"
    if not p.exists():
        out.append(f"\n(run {label}: no data yet)\n"); continue
    r = json.loads(p.read_text())
    n = r["native"]["output"]
    out.append(f"\n#### {label}: window {r['window'][0]}x{r['window'][1]}, DPR {r['dpr']}, {r['framing']}, canvas buffer {n['w']}x{n['h']}; "
               f"reference scene {r['reference']['internal']['w']}x{r['reference']['internal']['h']}; pan {r['pan']['frames']} frames at {r['pan']['pxPerFrame']} px/frame\n")
    out.append("| config | scene px | MSAA | MAE | edge MAE | PSNR dB | shimmer | edge shimmer | ms median | ms p95 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    best = min(c["edgeMae"] for c in r["configs"])
    for c in r["configs"]:
        mark = " **(best)**" if c["edgeMae"] == best else ""
        out.append(f"| {c['id']}{mark} | {c['internal']['w']}x{c['internal']['h']} | {c['msaa']} | {c['mae']:.5f} | {c['edgeMae']:.5f} | {c['psnr']:.2f} | "
                   f"{c['shimmer']:.5f} | {c['edgeShimmer']:.5f} | {c['cost']['median']} | {c['cost']['p95']} |")
    refm = r["configs"][0]["refMotion"]
    out.append(f"\nReference motion between pan frames (mean abs change of the reference itself): {refm:.5f}. "
               f"Edge pixels: {r['configs'][0]['edgeShare']*100:.1f}% of the frame.\n")
    if r.get("display"):
        a = r["displayAlign"]
        out.append(f"Display path (page screenshots, overlay on). Screenshot vs drawing buffer read back directly: MAE {a['offset']['mae']} at offset ({a['offset']['dx']},{a['offset']['dy']}).\n")
        out.append("| as displayed | buffer | scene px | MAE | edge MAE | PSNR dB | shimmer | edge shimmer |")
        out.append("|---|---|---|---|---|---|---|---|")
        for d in r["display"]:
            out.append(f"| {d['id']} | {d['buffer'][0]}x{d['buffer'][1]} | {d['internal']['w']}x{d['internal']['h']} | {d['mae']:.5f} | {d['edgeMae']:.5f} | {d['psnr']:.2f} | {d['shimmer']:.5f} | {d['edgeShimmer']:.5f} |")
    out.append("")
text = "\n".join(out)
(RUNS / "tables.md").write_text(text, encoding="utf-8")
print(text)
