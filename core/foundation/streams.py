"""streams -- process plumbing for long-lived agent processes (T030 L3 / RB-28).

A live runner's stdout is BEST-EFFORT display, never load-bearing: the bus and the
ledger carry the real work. Two consequences, both pinned in
tests/test_t030_l3_pipe_immunity.py:

  - a closed pipe (a truncating reader like `| Select-Object -First N` hung up) must
    never kill the process -- writes latch dead and the runner keeps serving the bus;
  - a piped stdout must speak in REAL TIME (line-buffered), not at buffer-fill -- a
    live runner that looks dead for minutes is the RB-29-lineage complaint.

Spec: docs/library/design/20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79.md FINAL SLICE LIST L3.
"""
from __future__ import annotations

import sys


class _PipeImmune:
    """Wraps a text stream: write/flush swallow OSError/ValueError and LATCH dead after
    the first failure. A dead pipe stays dead -- retrying every line is a storm, not
    resilience; the latch makes post-mortem writes free no-ops."""

    def __init__(self, stream):
        self._s = stream
        self._dead = False

    def write(self, s):
        if self._dead:
            return len(s)
        try:
            return self._s.write(s)
        except (OSError, ValueError):     # closed pipe / closed file object
            self._dead = True
            return len(s)

    def flush(self):
        if self._dead:
            return
        try:
            self._s.flush()
        except (OSError, ValueError):
            self._dead = True

    def __getattr__(self, name):          # encoding/isatty/fileno/... delegate through
        return getattr(self._s, name)


def pipe_immune(stream):
    """Idempotent wrap: a stream that can never raise from write/flush."""
    return stream if isinstance(stream, _PipeImmune) else _PipeImmune(stream)


def self_bless_stdout() -> None:
    """Bless sys.stdout/sys.stderr for a long-lived piped process: utf-8 (never die on
    cp1252), line-buffered (visible in real time when piped), pipe-immune (a truncating
    reader cannot kill the process). Idempotent; the process blesses ITSELF, so the
    launcher env (PYTHONUNBUFFERED, T019 drainers) is belt and braces, not a
    precondition."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or isinstance(s, _PipeImmune):
            continue
        try:
            s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except Exception:
            pass                           # non-reconfigurable stream: immunity still applies
        setattr(sys, name, pipe_immune(s))
