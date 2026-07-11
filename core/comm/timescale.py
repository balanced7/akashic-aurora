"""
Timescale (T030 L1 follow-up) -- ONE seam for BUGGIFY-style timeout shrinking.

FDB's lesson: timeout paths are unreachable in tests at production durations; shrink the
knobs and they exercise constantly. AKASHIC_TIMEOUT_MULTIPLIER scales every
liveness-relevant timeout at module-import time (drills set it in the child process env;
production never sets it -> 1.0). A drill at 0.05 turns the 20s lock TTL into 1s, the
600s reply guard into 30s -- expiry/timeout branches become drillable in seconds.

Import-time by design: the constants it feeds are module-level and the consumers are
short-lived drill subprocesses; a live process never legitimately rescales itself.
"""
import os


def scaled(seconds, *, floor=1):
    """`seconds` scaled by AKASHIC_TIMEOUT_MULTIPLIER (default 1.0; junk/<=0 -> 1.0).
    Integer inputs stay integers (callers feed Redis EX args); everything floors at
    `floor` so a tiny multiplier can never mint a zero/negative timeout."""
    try:
        m = float(os.environ.get("AKASHIC_TIMEOUT_MULTIPLIER", "1") or "1")
    except (ValueError, TypeError):
        m = 1.0
    if m <= 0:
        m = 1.0
    v = seconds * m
    if isinstance(seconds, int):
        return max(int(floor), int(round(v)))
    return max(float(floor), v)
