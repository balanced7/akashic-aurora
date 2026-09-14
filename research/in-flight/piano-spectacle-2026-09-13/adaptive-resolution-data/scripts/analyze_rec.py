# Reads each recording from rec_probe.mjs with PyAV: stream size, frame count, frame timing, decoded size.
# usage: py analyze_rec.py <folder>
import json, statistics, sys
from pathlib import Path
import av

folder = Path(sys.argv[1])
rows = []
for f in sorted(folder.glob("rec-*.*")):
    if f.suffix not in (".mp4", ".webm"):
        continue
    with av.open(str(f)) as c:
        s = c.streams.video[0]
        tb = s.time_base
        pts, sizes = [], set()
        for frame in c.decode(s):
            if frame.pts is not None:
                pts.append(float(frame.pts * tb))
            sizes.add((frame.width, frame.height))
        pts.sort()
        gaps = [b - a for a, b in zip(pts, pts[1:])]
        span = pts[-1] - pts[0] if len(pts) > 1 else 0
        rows.append({
            "file": f.name, "bytes": f.stat().st_size, "codec": s.codec_context.name,
            "stream": [s.codec_context.width, s.codec_context.height], "decodedSizes": sorted(sizes),
            "frames": len(pts), "spanSec": round(span, 3),
            "fps": round((len(pts) - 1) / span, 2) if span else None,
            "gapMedianMs": round(statistics.median(gaps) * 1000, 2) if gaps else None,
            "gapMaxMs": round(max(gaps) * 1000, 2) if gaps else None,
            "gapsOver25ms": sum(1 for g in gaps if g > 0.025),
            "bigGapsAt": [[round(pts[i] - pts[0], 3), round(g * 1000, 1)] for i, g in enumerate(gaps) if g > 0.025],
        })
for r in rows:
    print(json.dumps(r))
(folder / "rec-analysis.json").write_text(json.dumps(rows, indent=2))
