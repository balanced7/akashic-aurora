"""arsenal.panel.limit -- the throttle, because the client is a phone on a tailnet.

Three separate bounds, and they answer three different failures:

  * ATTEMPT BOUND (all POSTs, refusals included): a client that is wrong -- wrong token, wrong
    service, a loop of retries after a tailnet hiccup -- must not be able to make the panel do
    unbounded work. This bucket counts the request, not the action.
  * ACTION BOUND: how many verbs may actually be executed per minute. Sized so a human thumb can
    never hit it and a script always does.
  * DESTRUCTIVE BOUND, PER SERVICE: stop/restart specifically, per service. This is the one that
    matters: a start/stop flap against a preview server is a page that will not load, and a flap
    against the bus runners or the log task is worse. Four per service per minute is generous for a
    person and useless for a loop.

A SLIDING WINDOW, not a fixed one: a fixed window lets a client spend the whole budget in the last
second of one window and the first second of the next, which is the bug that makes rate limits look
like they work in a test and not in practice.

`check()` MUTATES NOTHING; `note()` records. The caller decides whether a tuple is worth spending (a
refused request is recorded by the attempt bucket, a performed action by the other two), which keeps
the decision in one place instead of split across a decorator.
"""
from __future__ import annotations

import time
from typing import Callable, Deque, Dict, List, Tuple
from collections import deque

#: A person taps a button a few times a minute. A script is not a person.
DEFAULT_ATTEMPTS = 60
DEFAULT_ACTIONS = 20
DEFAULT_DESTRUCTIVE = 4
DEFAULT_WINDOW_S = 60.0


class RateLimiter:
    """Sliding-window limits over one client (the panel is loopback-only, so there is one)."""

    def __init__(self, *, attempts: int = DEFAULT_ATTEMPTS, actions: int = DEFAULT_ACTIONS,
                 destructive: int = DEFAULT_DESTRUCTIVE, window_s: float = DEFAULT_WINDOW_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.attempts_max = int(attempts)
        self.actions_max = int(actions)
        self.destructive_max = int(destructive)
        self.window_s = float(window_s)
        self._clock = clock
        self._attempts: Deque[float] = deque()
        self._actions: Deque[float] = deque()
        self._destructive: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------------------- public
    def check(self, service: str = "", verb: str = "") -> Tuple[bool, float, str]:
        """(allowed, retry_after_s, why). Changes nothing; call `note()` for a spent request."""
        now = self._clock()
        self._trim(now)
        if len(self._attempts) >= self.attempts_max:
            return False, self._retry(self._attempts, now), \
                f"{self.attempts_max} requests in {int(self.window_s)}s"
        if len(self._actions) >= self.actions_max:
            return False, self._retry(self._actions, now), \
                f"{self.actions_max} actions in {int(self.window_s)}s"
        if verb in ("stop", "restart") and service:
            rows = self._destructive.get(service, [])
            if len(rows) >= self.destructive_max:
                return False, self._retry(rows, now), \
                    f"{self.destructive_max} {verb} on {service!r} in {int(self.window_s)}s"
        return True, 0.0, ""

    def note(self, service: str = "", verb: str = "", *, acted: bool = False) -> None:
        """Record a request. `acted` is True only when the verb was actually executed."""
        now = self._clock()
        self._attempts.append(now)
        if acted and verb:
            self._actions.append(now)
            if verb in ("stop", "restart") and service:
                self._destructive.setdefault(service, []).append(now)

    def snapshot(self) -> Dict[str, int]:
        now = self._clock()
        self._trim(now)
        return {"attempts": len(self._attempts), "actions": len(self._actions),
                "destructive_live": sum(len(v) for v in self._destructive.values()),
                "window_s": int(self.window_s)}

    # ------------------------------------------------------------------------------- private
    def _trim(self, now: float) -> None:
        floor = now - self.window_s
        for bucket in (self._attempts, self._actions):
            while bucket and bucket[0] < floor:
                bucket.popleft()
        for service, rows in list(self._destructive.items()):
            kept = [t for t in rows if t >= floor]
            if kept:
                self._destructive[service] = kept
            else:
                del self._destructive[service]

    def _retry(self, bucket, now: float) -> float:
        if not bucket:
            return 0.0
        return max(0.0, round(float(bucket[0]) + self.window_s - now, 1))
