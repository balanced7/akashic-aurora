"""Screenspace organ — observe-only slice (T386, §6 build step 2).

The Aurora Program door-plane: a per-user engine that SEES the screen (and later,
gated on step 0, acts on it). This package carries the OBSERVE half (capture,
peek, delta, refs, read_text) and, since 2026-10-06, the ACT half (``act.locate`` /
``act.act`` / ``act.settle``) on Daniel's explicit operator order. The act verbs are
NOT gated by absence from this door -- they are gated per call against the house ACL
(``Cap.SCREEN_*`` in core/trust/capabilities.py, present in no role template, so even
super_admin must be granted them time-boxed). A capability hidden from the door it
should live on is a capability that stays dead; a capability whose gate is enforced in
its own code is one the fleet can find and still cannot misuse.

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

from core.screenspace import act       # noqa: F401  (ACTUATOR, sec.6 steps 1+3 -- gated
#                                        per call against core.trust ACL caps screen.*,
#                                        which sit in NO role template. The gate lives in
#                                        the code, not in absence from this door: a
#                                        capability with no door stays dead.
from core.screenspace import canary    # noqa: F401  (§1 amended ruling: positive canary read) — imported FIRST: leaf-most (no package-internal imports), consumed by engine/shadow
from core.screenspace import capture  # noqa: F401  (module attribute, deep substrate)
from core.screenspace import foreground  # noqa: F401  (WinEventHook foreground source, §1.1)
from core.screenspace import shadow    # noqa: F401  (L0 pulse, F2-gated)
from core.screenspace.engine import (  # noqa: F401  (flat verb seam)
    delta,
    peek,
    read_text,
    refs,
)
from core.screenspace.foreground import ForegroundTracker  # noqa: F401  (the §1.1 source)

__all__ = [
    "act",
    "canary",
    "capture",
    "foreground",
    "shadow",
    "ForegroundTracker",
    "peek",
    "delta",
    "refs",
    "read_text",
]
