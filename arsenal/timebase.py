"""Exact time for the arsenal: one representation, several honest clocks.

A time is (clock, epoch, ticks, timebase). Ticks are integers and the timebase is an exact
Fraction of a second per tick, so nothing here ever passes through a float. The epoch changes
on seek, loop, source replacement or device reset: a value from before a seek can never be
compared with, or mistaken for, a value after it.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Tuple

__all__ = [
    "ClockMismatch", "StaleEpoch", "tb", "parse_tb", "format_tb", "TimeRef", "TimeSpan",
    "Clock", "ClockMap", "CLOCK_DOMAINS", "MASTER_BY_MODE",
]


class ClockMismatch(ValueError):
    """Two times on different clocks met."""


class StaleEpoch(ValueError):
    """A time from an older epoch met a newer one."""


CLOCK_DOMAINS = ("media", "audio", "presentation", "virtual", "timeline", "musical")

#: Which clock leads, by mode (contract F2). Election is not ontology.
MASTER_BY_MODE = {
    "live_audio": "audio",
    "live_silent": "presentation",
    "offline": "virtual",
    "edit": "timeline",
}


def _strict_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, not {type(value).__name__}")
    return value


def _as_timebase(value) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError(f"timebase must be an int or Fraction, not {type(value).__name__}")
    value = Fraction(value)
    if value <= 0:
        raise ValueError(f"timebase must be positive, got {value}")
    if value > 1:
        # Nothing in media ticks slower than once a second, so this is a rate passed where a
        # timebase belongs (48000 for 1/48000). Refuse it loudly rather than keep a wrong time.
        n, d = value.numerator, value.denominator
        raise ValueError(f"a timebase is seconds per tick, and {n}/{d} would be over a second per tick; "
                         f"for a rate of {n}/{d} per second use tb({d}, {n})")
    return value


def tb(num: int, den: int) -> Fraction:
    """Seconds per tick as an exact Fraction: tb(1001, 30000) for 29.97 fps, tb(1, 48000) for 48 kHz."""
    _strict_int(num, "num")
    if _strict_int(den, "den") == 0:
        raise ValueError("a timebase denominator must not be zero")
    return _as_timebase(Fraction(num, den))


def parse_tb(text) -> Fraction:
    """'1001/30000' -> Fraction(1001, 30000); '1' -> Fraction(1)."""
    s = str(text).strip()
    if "/" in s:
        num, den = s.split("/", 1)
        return tb(int(num), int(den))
    return _as_timebase(int(s))


def format_tb(value) -> str:
    v = _as_timebase(value)
    return f"{v.numerator}/{v.denominator}"


@dataclass(frozen=True)
class TimeRef:
    clock: str
    epoch: int
    ticks: int
    timebase: Fraction

    def __post_init__(self):
        if not isinstance(self.clock, str) or not self.clock:
            raise TypeError("clock must be a non-empty string")
        if _strict_int(self.epoch, "epoch") < 0:
            raise ValueError("epoch must not be negative")
        _strict_int(self.ticks, "ticks")
        object.__setattr__(self, "timebase", _as_timebase(self.timebase))

    @property
    def seconds(self) -> Fraction:
        return self.ticks * self.timebase

    def rescale(self, timebase, *, exact: bool = True) -> "TimeRef":
        target = _as_timebase(timebase)
        q = self.seconds / target
        if q.denominator != 1:
            if exact:
                raise ValueError(
                    f"{self.ticks} ticks at {format_tb(self.timebase)} is not exactly "
                    f"representable at {format_tb(target)}")
            q = Fraction(round(q))  # Fraction rounding is half to even
        return TimeRef(self.clock, self.epoch, int(q), target)

    def _check(self, other) -> None:
        if not isinstance(other, TimeRef):
            raise TypeError(f"cannot compare a TimeRef with {type(other).__name__}")
        if other.clock != self.clock:
            raise ClockMismatch(f"clock {self.clock!r} vs {other.clock!r}")
        if other.epoch != self.epoch:
            raise StaleEpoch(f"epoch {self.epoch} vs {other.epoch} on clock {self.clock!r}")

    def __eq__(self, other):
        if not isinstance(other, TimeRef):
            return False
        self._check(other)
        return self.seconds == other.seconds

    def __hash__(self):
        return hash((self.clock, self.epoch, self.seconds))

    def __lt__(self, other):
        self._check(other)
        return self.seconds < other.seconds

    def __le__(self, other):
        self._check(other)
        return self.seconds <= other.seconds

    def __gt__(self, other):
        self._check(other)
        return self.seconds > other.seconds

    def __ge__(self, other):
        self._check(other)
        return self.seconds >= other.seconds

    def __add__(self, other):
        if isinstance(other, bool) or not isinstance(other, int):
            raise TypeError("only an int number of ticks can be added to a TimeRef")
        return TimeRef(self.clock, self.epoch, self.ticks + other, self.timebase)

    def to_json(self) -> dict:
        return {"clock": self.clock, "epoch": self.epoch, "ticks": self.ticks,
                "timebase": format_tb(self.timebase)}

    @classmethod
    def from_json(cls, d: dict) -> "TimeRef":
        return cls(d["clock"], d["epoch"], d["ticks"], parse_tb(d["timebase"]))


@dataclass(frozen=True)
class TimeSpan:
    start: TimeRef
    duration_ticks: int

    def __post_init__(self):
        if not isinstance(self.start, TimeRef):
            raise TypeError("start must be a TimeRef")
        if _strict_int(self.duration_ticks, "duration_ticks") < 0:
            raise ValueError("duration_ticks must not be negative")

    @property
    def end(self) -> TimeRef:
        return self.start + self.duration_ticks

    def contains(self, ref: TimeRef) -> bool:
        """Start-inclusive, end-exclusive; raises across clocks or epochs."""
        return self.start <= ref < self.end


class Clock:
    """A named clock whose epoch advances on every discontinuity."""

    def __init__(self, name: str, domain: str):
        if not isinstance(name, str) or not name:
            raise ValueError("a clock needs a name")
        if domain not in CLOCK_DOMAINS:
            raise ValueError(f"unknown clock domain {domain!r}; expected one of {CLOCK_DOMAINS}")
        self.name = name
        self.domain = domain
        self._epoch = 0
        self._history: List[Tuple[int, str]] = []

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def history(self) -> List[Tuple[int, str]]:
        return list(self._history)

    def bump_epoch(self, reason: str) -> int:
        self._epoch += 1
        self._history.append((self._epoch, str(reason)))
        return self._epoch

    def stamp(self, ticks: int, timebase) -> TimeRef:
        return TimeRef(self.name, self._epoch, ticks, timebase)

    def is_current(self, ref) -> bool:
        return isinstance(ref, TimeRef) and ref.clock == self.name and ref.epoch == self._epoch


@dataclass(frozen=True)
class ClockMap:
    """A measured affine map between two clocks, with its uncertainty stated."""

    source: str
    target: str
    slope: Fraction
    offset: Fraction
    uncertainty_ns: int
    observed_at: str

    def __post_init__(self):
        for name in ("slope", "offset"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
                raise TypeError(f"{name} must be an int or Fraction, not {type(value).__name__}")
            object.__setattr__(self, name, Fraction(value))
        if _strict_int(self.uncertainty_ns, "uncertainty_ns") < 0:
            raise ValueError("uncertainty_ns must not be negative")

    def map_seconds(self, ref: TimeRef) -> Fraction:
        if not isinstance(ref, TimeRef):
            raise TypeError("map_seconds takes a TimeRef")
        if ref.clock != self.source:
            raise ClockMismatch(f"map from {self.source!r} given a time on {ref.clock!r}")
        return self.slope * ref.seconds + self.offset
