"""arsenal.media.probe -- a file's facts: what it is, every stream, where its keyframes are.

keyframes() is the packet-flag scan: it reads the container index, decodes nothing, and takes 0.8 s on a 33-minute
recording (the `-skip_frame nokey` decode path took 11.8 s and is not used).
"""
from __future__ import annotations

from typing import List

from . import ff
from .receipt import quick_id  # noqa: F401  (re-exported: probe.quick_id is the documented name)


def keyframes(path, *, stream: int = 0) -> List[float]:
    """Presentation times (s, source clock) of every keyframe of video stream `stream`, ascending."""
    res = ff.run(["-v", "error", "-select_streams", f"v:{stream}", "-show_entries", "packet=pts_time,flags",
                  "-of", "csv=p=0", str(path)], tool="ffprobe")
    out = []
    for line in res.stdout.splitlines():
        pts, _, flags = line.partition(",")
        if "K" in flags and pts not in ("", "N/A"):
            out.append(float(pts))
    out.sort()
    return out
