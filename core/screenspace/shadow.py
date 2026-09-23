"""Screenspace shadow model — L0 pulse (T386 §1.1, F2-gated).

The low-latency claim of the organ: foreground window, focus path, window roster,
recent deltas, and activity level answered from an in-memory model in <1ms
server-side instead of walking the tree per call (§1.1: "the walk already
happened").

F2 STATUS: F2 has LANDED v1 BY CONSTRUCTION (fence
``fences/screenspace/f2-shadow-model-v1-vs-v2-and-launch-posture.md``, pending
claude's ratification). The foreground source is now the WinEventHook
``ForegroundTracker`` (core/screenspace/foreground.py), and ``pulse()`` reads its
CACHE through ``engine._current_focus()`` — which returns ``_tracker.focus``
(cache-first, O(1) warm), NOT a per-call UIA poll. The earlier "v2 fallback /
fresh read / O(call)" semantics described in a prior revision of this docstring
NO LONGER EXIST in the call chain: the placeholder GetForegroundControl poll was
replaced by the tracker. Do not resurrect the v2 wording — it would describe a
code path that is gone.

The currency (gen monotonicity) is owned by engine.ObservationStream and shared
here by import — do NOT mint a second clock (the "three subtly different
implementations" anti-pattern, §1). NOTE the two distinct ordinals in play and do
not conflate them: ``tracker.gen`` is a DELIVERY ordinal (+1 per on_foreground_change),
while ``engine._stream.gen`` is an OBSERVATION ordinal (+1 per observe()). This module's
``pulse()`` observes ``_stream`` (the currency the delta/peek ladder pins against),
and reads the tracker cache for the focus VALUE — it never re-derives gen from the
tracker.

Latency note (§5): L0 pulse / L3 delta <5ms server-side is a CACHE claim for v1.
The warm cache-hit is the number §5 certifies; cold-start populate and
event-delivery latency are SEPARATE v1 numbers measured by the bench, not promised
by "L0 <5ms" in the abstract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.screenspace.engine import ObservationStream, _current_focus, _stream
from core.screenspace import canary  # §1 amended ruling: positive canary read


@dataclass
class Pulse:
    """L0 pulse: the §2 lowest rung — foreground/focus/roster-delta/elevated/activity.

    Content is §2's L0 row: foreground window, focus path, window-roster delta,
    elevated?, activity level. Kept to the CHEAP fields; anything heavier is a
    higher ladder level and belongs to engine.peek / the text/walk increment.
    """

    foreground: Optional[str] = None
    focus_path: list = None
    roster_delta: list = None
    elevated: Optional[bool] = None
    activity: int = 0
    gen: int = 0
    stale_ms: int = 0
    uia_unavailable: bool = False  # §1 ruling: non-interactive station -> reads UNCHECKABLE

    def __post_init__(self):
        if self.focus_path is None:
            self.focus_path = []
        if self.roster_delta is None:
            self.roster_delta = []

    def to_dict(self) -> dict:
        return {
            "foreground": self.foreground,
            "focus_path": self.focus_path,
            "roster_delta": self.roster_delta,
            "elevated": self.elevated,
            "activity": self.activity,
            "gen": self.gen,
            "stale_ms": self.stale_ms,
            "uia_unavailable": self.uia_unavailable,
        }


def pulse() -> Pulse:
    """One L0 pulse. v1 cache-first: focus comes from the tracker cache via
    _current_focus() (O(1) warm read), gen from the observation stream, roster
    still empty (roster + roster-delta is the F2-gated-increment's job)."""
    focus = _current_focus()
    gen = _stream.observe(focus)
    return Pulse(
        foreground=focus,
        focus_path=[focus] if focus else [],
        roster_delta=[],   # roster + roster-delta is the v1 shadow model's job (F2)
        elevated=None,
        activity=1 if focus else 0,
        gen=gen,
        stale_ms=0,
        uia_unavailable=not canary.uia_available(),
    )
