"""Port types, memory domains and caps checks for arsenal graphs (contract §4.2)."""
from __future__ import annotations

from typing import List

PORT_TYPES = (
    "stream.video",
    "stream.audio",
    "media.video_frame",
    "media.audio_block",
    "media.encoded_packet",
    "media.subtitle_cue",
    "control.event",
    "control.curve",
    "analysis.features",
    "asset.reference",
    "timeline.sequence",
)

#: Types that carry media payloads: moving these between engines is a copy.
MEDIA_PORT_TYPES = tuple(t for t in PORT_TYPES if t.startswith(("stream.", "media.")))

#: Where a payload lives. "browser" means inside a browser engine, where copies are not observable.
MEMORY_DOMAINS = ("cpu", "d3d11", "d3d12", "vulkan", "opengl", "webgl", "webgpu", "browser", "encoded")

#: Binding sources must produce one of these.
PRODUCER_TYPES = ("control.event", "control.curve", "analysis.features")

CAPS_KEYS = ("memory", "primaries", "transfer", "matrix", "range", "alpha_mode",
             "sample_rate", "channels", "layout")


def check_caps(out_caps, in_caps) -> List[str]:
    """Reasons an output's caps cannot feed an input's; an empty list means compatible.

    Only keys the input states are checked, and an input value of "any" accepts anything.
    An output that does not state a key the input requires is a mismatch: unknown is not a yes.
    """
    out_caps = out_caps or {}
    in_caps = in_caps or {}
    reasons = []
    for key in CAPS_KEYS:
        if key not in in_caps:
            continue
        want = in_caps[key]
        if want == "any":
            continue
        if key not in out_caps:
            reasons.append(f"{key}: input needs {want!r} but the output does not state it (unknown)")
        elif out_caps[key] != want:
            reasons.append(f"{key}: output gives {out_caps[key]!r}, input needs {want!r}")
    return reasons
