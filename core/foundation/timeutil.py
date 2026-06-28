"""
timeutil -- one deterministic, timezone-safe way to turn an ISO timestamp into a
comparable epoch. The canonical fix for D4 (mixed naive/tz-aware timestamps).

The trap: `datetime.fromisoformat("2026-01-01T00:00:00").timestamp()` interprets a NAIVE
timestamp in the machine's LOCAL timezone (Eastern here -> a 5h skew), while a tz-aware
string is interpreted at its offset. So mixing the two:
  - string-sorts wrong (a `-05:00` value sorts as if it were UTC wall-clock), and
  - crashes elapsed-time math (`naive - aware` raises TypeError), which best-effort code
    then swallows into a silent 0.0 -- a real session gap stops cutting a chapter boundary.

`to_epoch` removes the ambiguity: a naive timestamp is treated as UTC (deterministic, not
locale-dependent), a tz-aware one keeps its offset. Both collapse to the same instant, so
sorting and gap math agree regardless of how each value was written.

NOTE (deliberate scope): this is used on the COMPARISON path (the chronicler re-sorts and
re-segments from scratch each run, so there is no persisted value to migrate). The several
`_epoch` helpers that compute PERSISTED zset scores (timeline, event index) are intentionally
left untouched here -- changing their interpretation would shift already-stored scores by the
local offset and create an ordering discontinuity at the migration boundary. Unifying those
behind a one-time re-score is a separate, deliberate migration.
"""
from datetime import datetime, timezone
from typing import Any


def to_epoch(iso: Any) -> float:
    """ISO timestamp -> UTC epoch seconds. Naive == UTC (deterministic). Bad input -> 0.0.

    For all-naive data this differs from the locale-dependent `.timestamp()` only by a
    constant offset that cancels in any sort or subtraction -- so it is a strict, no-regression
    improvement that ONLY changes behavior when tz-aware timestamps are actually present.
    """
    if isinstance(iso, (int, float)):
        return float(iso)            # already an epoch -> pass through (drop-in for prior _epoch copies)
    try:
        dt = datetime.fromisoformat(str(iso))
    except (ValueError, TypeError):
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def hours_between(a: Any, b: Any) -> float:
    """Absolute elapsed hours between two ISO timestamps, timezone-safe (never raises)."""
    return abs(to_epoch(b) - to_epoch(a)) / 3600.0
