"""
storm_detect — S0-beta storm signature detection (lane-depth spike + repeat-delivery).

Pure detection: takes lane depths + message ids → storm signature or None. The runner
owns the sliding window (in-memory deque); this module only compares. Stateless, no
Redis — the caller feeds history.

S0-beta (deepseek BULKHEAD-0 ∪ kimi R4): when the detector fires, the runner executes
the standby-hard ceremony (pause → skip-to-now → resume) WITH receipt — the conveyor's
first full auto-transit: a human ritual graduates to auto-detected.

AUTHORSHIP: deepseek's build (write-gated seat, night-run 2026-07-21), pre-staged by
claude; the runner wiring holds for kimi's second-observer read (deepseek's rail).

Signatures:
  LANE_DEPTH_SPIKE  — work lane depth >= threshold for N consecutive samples.
  REPEAT_DELIVERY   — M consecutive messages with the same id (redelivery storm from
                       a crash-looping producer or dual-write echo).

Environment dials (read at construction):
  STORM_DEPTH_THRESHOLD  (default 50)
  STORM_DEPTH_WINDOW     (default 3 consecutive samples)
  STORM_REPEAT_THRESHOLD (default 5 consecutive duplicate ids)
"""
from __future__ import annotations

import os
from collections import deque
from typing import Any, Dict, List, Optional


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class StormDetector:
    """Per-runner-session sliding-window storm detector. Instantiate ONCE in main(),
    feed() every consume loop iteration. Pure in-memory state, no Redis — a crash
    resets the window, which is safe (a fresh runner starts with clean windows)."""

    def __init__(self, *,
                 depth_threshold: Optional[int] = None,
                 depth_window: Optional[int] = None,
                 repeat_threshold: Optional[int] = None):
        self.depth_threshold = (depth_threshold
                                if depth_threshold is not None
                                else _int_env("STORM_DEPTH_THRESHOLD", 50))
        self.depth_window = (depth_window
                             if depth_window is not None
                             else _int_env("STORM_DEPTH_WINDOW", 3))
        self.repeat_threshold = (repeat_threshold
                                 if repeat_threshold is not None
                                 else _int_env("STORM_REPEAT_THRESHOLD", 5))
        self._depths: deque = deque(maxlen=self.depth_window)
        self._last_ids: deque = deque(maxlen=self.repeat_threshold)

    def feed(self, work_depth: int, msg_ids: List[str]) -> Optional[Dict[str, Any]]:
        """Feed one sample (lane depth + batch message ids). Returns a storm signature
        dict if a storm is detected, or None. The caller should clear the storm
        immediately — the detector does NOT auto-reset (a second call with the same
        spike returns the same signature; the caller's clear action stops the feed)."""
        self._depths.append(work_depth)
        # LANE-DEPTH SPIKE: all window samples >= threshold
        if (len(self._depths) == self.depth_window
                and all(d >= self.depth_threshold for d in self._depths)):
            return {"kind": "lane_depth_spike",
                    "depth": work_depth,
                    "threshold": self.depth_threshold,
                    "window": list(self._depths)}

        # REPEAT-DELIVERY STORM: N consecutive same ids in the sliding id window.
        # Feed each id individually so cross-batch duplicates still accumulate.
        for mid in msg_ids:
            if not mid:
                continue
            self._last_ids.append(mid)
            if (len(self._last_ids) == self.repeat_threshold
                    and len(set(self._last_ids)) == 1):
                return {"kind": "repeat_delivery_storm",
                        "id": str(mid),
                        "count": self.repeat_threshold}

        return None

    def reset(self) -> None:
        """Clear the sliding windows (call after a storm is cleared)."""
        self._depths.clear()
        self._last_ids.clear()
