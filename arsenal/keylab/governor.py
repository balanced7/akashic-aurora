"""arsenal.keylab.governor -- the burst ceiling as a guarantee, not a habit.

The device freezes on ~36 SysEx packets in one tight burst and needs a power cycle; 12 is the measured safe
ceiling (README "Confirmed facts", 2026-10-22). PadRenderer already paces itself, but pacing lives in each
producer: two producers sharing one port (a chord view and a beat march, say) each stay polite and can still
add up to a freeze. The governor sits on the port instead, so every packet from every producer in the process
passes one gate: at most `limit` packets in any sliding `window` seconds. A caller that would break the
ceiling waits; nothing is dropped.

The default window is 0.1 s. PadRenderer has been sending up to ~150 packets/s without a freeze, so 12 per
100 ms (120/s) sits inside behaviour already seen on the hardware. It is a conservative starting value, and
probe P24 (the sustained burst window, added by the A16 design docs) re-measures it.

Thread-safe. The clock and sleep are injectable, so the property test runs on a fake clock and cannot flake.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Deque, List

SAFE_BURST = 12      # packets: the measured safe ceiling
WINDOW_S = 0.1       # seconds: the sliding window the ceiling applies to


class BurstGovernor:
    def __init__(self, limit: int = SAFE_BURST, window: float = WINDOW_S,
                 clock: Callable[[], float] = time.perf_counter, sleep: Callable[[float], None] = time.sleep):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit, self.window = limit, window
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._recent: Deque[float] = deque()   # admit times still inside the window
        self.admitted = 0                      # lifetime packets let through
        self.waited_s = 0.0                    # lifetime time spent holding callers back
        self.log: List[float] = []             # every admit time, kept only when record=True
        self.record = False

    def admit(self) -> float:
        """Block until one more packet fits under the ceiling, then count it. Returns the admit time."""
        with self._lock:
            while True:
                now = self._clock()
                while self._recent and now - self._recent[0] >= self.window:
                    self._recent.popleft()
                if len(self._recent) < self.limit:
                    self._recent.append(now)
                    self.admitted += 1
                    if self.record:
                        self.log.append(now)
                    return now
                wait = self.window - (now - self._recent[0])
                self.waited_s += wait
                self._sleep(wait)


def max_in_window(times, window: float) -> int:
    """The most admits that fall inside any half-open window of length `window` (the property the pin checks)."""
    ts = sorted(times)
    best, lo = 0, 0
    for hi, t in enumerate(ts):
        while t - ts[lo] >= window:
            lo += 1
        best = max(best, hi - lo + 1)
    return best
