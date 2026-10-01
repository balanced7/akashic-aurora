"""Screenspace organ — observe-only slice (T386, §6 build step 2).

The Aurora Program door-plane: a per-user engine that SEES the screen (and later,
gated on step 0, acts on it). This package is the OBSERVE half only — capture,
peek, delta, refs, read_text. The act/input/watch/locate verbs are §6 step 3+,
gated on the Sunshine --allow-write/--allow-gui unlock, and are deliberately NOT
exported here.

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md
(sha 054b79f0, [CURRENT], status: settled).

Surface contract (locked with kimi/Navi, 2026-09-23):
  ``from core.screenspace import peek, delta, refs, read_text, capture``  # flat
  ``from core.screenspace.capture import screen``                          # deep (substrate)
  ``from core.screenspace import shadow``                                  # L0 pulse (F2-gated)

Shape discipline: ``capture`` is the SUBSTRATE (pixels + hash, ``ScreenFrame``);
``engine`` is the FACADE (digest verdicts, ``ScreenResult`` / ``ScreenDelta``).
``shadow`` is the low-latency pulse model, F2-open (v1 cached vs v2 poll-per-call).

The substrate (mss / uiautomation / dxcam) is OPTIONAL and host-installed — it is
NOT a pinned repo dependency (requirements.txt is stdlib-by-design). Every import
here is lazy and fail-soft, so the package imports cleanly and exposes the full
contract on any host, degrading honestly (structured ``NoDisplay`` / absence
results) when the OS has no interactive desktop or the substrate is unpinned.
"""

from core.screenspace import (
    canary,
    capture,
    foreground,
    shadow,
)
from core.screenspace.engine import (
    delta,
    peek,
    read_text,
    refs,
)
from core.screenspace.foreground import ForegroundTracker

__all__ = [
    "ForegroundTracker",
    "canary",
    "capture",
    "delta",
    "foreground",
    "peek",
    "read_text",
    "refs",
    "shadow",
]
