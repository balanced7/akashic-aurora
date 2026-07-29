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

NOTE (scope, updated T119): to_epoch began on the COMPARISON path only (the chronicler
re-sorts and re-segments from scratch each run). The PERSISTED zset scorers have since been
unified onto it too -- core/events/event_index.py and core/events/event_query.py import
to_epoch as their `_epoch` (S5), with already-stored scores re-aligned by
scripts/migrate_time_scores.py. This module is now the one clock end to end: now_iso()
writes stamps, to_epoch() compares them, render_iso() is the single display door.
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


def now_iso() -> str:
    """The one write-side stamp (T119 G5): aware UTC ISO, self-describing on the wire.
    to_epoch() is its exact inverse; legacy naive rows keep working (naive == UTC)."""
    return datetime.now(timezone.utc).isoformat()


def render_iso(value: Any, *, tz: str = "local") -> str:
    """THE single display door (T119 G5): every rendered timestamp names its frame.

    Accepts an ISO string (naive == UTC, per to_epoch's law), an epoch float/int, or a
    datetime. tz="utc" -> UTC wall clock at seconds precision with a trailing 'Z'
    ("2026-07-28T20:41:26Z"). tz="local" -> the machine's local wall clock plus a short
    tz label (%Z; multi-word Windows names collapse to initials, e.g. "Eastern Daylight
    Time" -> "EDT"; an empty %Z falls back to the UTC offset, e.g. "UTC-04:00").
    Never raises: an unparseable value renders as str(value), unchanged.
    """
    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)          # naive == UTC: one law, one door
        if str(tz).strip().lower() == "utc":
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        local = dt.astimezone()                            # machine-local zone
        label = local.strftime("%Z")
        if label and " " in label:                         # "Eastern Daylight Time" -> "EDT"
            label = "".join(w[0] for w in label.split() if w[:1].isalpha()).upper()
        if not label:                                      # nameless zone -> explicit offset
            off = local.strftime("%z")                     # e.g. "-0400"
            label = f"UTC{off[:3]}:{off[3:]}" if len(off) == 5 else "UTC"
        return local.strftime("%Y-%m-%dT%H:%M:%S") + f" {label}"
    except (ValueError, TypeError, OverflowError, OSError):
        return str(value)
