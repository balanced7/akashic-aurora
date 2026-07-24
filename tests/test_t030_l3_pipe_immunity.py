"""
T030 L3 / RB-28 -- pipe immunity + real-time stdout: pre-registered acceptance
(committed BEFORE impl, M3/T031). Spec: docs/library/design/20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79.md FINAL SLICE
LIST L3 (reconciled dual-half record, 2026-07-10).

The failure modes under pin:
  - a truncating reader (`| Select-Object -First N`, `| head`) closes the pipe; the next
    print raises BrokenPipeError/OSError and KILLS the runner mid-run (T019 fixed the
    LAUNCHER side; this is the runner's own stdout).
  - block-buffered stdout when piped: nothing visible until the buffer fills -- a live
    runner looks dead for minutes (the RB-29 lineage complaint).

Contract frozen here:
  core.foundation.streams.pipe_immune(stream) -> stream-like  (write/flush swallow
      OSError, latch dead after the first failure, never raise, never spin)
  core.foundation.streams.self_bless_stdout() -> None  (idempotent: utf-8 + line
      buffering + pipe immunity on sys.stdout/sys.stderr -- the runner blesses ITSELF,
      the launcher env is belt-and-braces)
  bifrost_runner_deepseek calls self_bless_stdout at startup (wired, not just built)
  AGENTS.md carries the blessed-launch rule (no truncating pipes on live runners)

Run: py -m pytest tests/test_t030_l3_pipe_immunity.py -q
"""
import io
import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.foundation import streams
    _BUILT = hasattr(streams, "pipe_immune") and hasattr(streams, "self_bless_stdout")
except ImportError:
    streams = None
    _BUILT = False

pytestmark = pytest.mark.skipif(
    not _BUILT, reason="L3 pins pre-registered; impl pending (assertions frozen)")


class _DeadPipe(io.TextIOBase):
    """A stream that dies on the first write -- the closed-pipe shape."""
    def __init__(self):
        self.write_attempts = 0
    def write(self, s):
        self.write_attempts += 1
        raise OSError(22, "The pipe has been ended")
    def flush(self):
        raise OSError(232, "The pipe is being closed")


# --- P1: the wrapper survives a dead stream, latches, never spins ---

def test_wrapper_survives_dead_stream_and_latches():
    dead = _DeadPipe()
    w = streams.pipe_immune(dead)
    for i in range(50):
        w.write(f"line {i}\n")        # must never raise
        w.flush()                     # must never raise
    assert dead.write_attempts == 1, \
        "latched after the FIRST failure -- no per-line retry storm on a dead pipe"


# --- P2: a child printing through the blessing SURVIVES a truncating reader ---

_CHILD_SPEW = (
    "import sys, os; sys.path.insert(0, r'%s');"
    "from core.foundation.streams import self_bless_stdout; self_bless_stdout();"
    "[print(f'line {i}') for i in range(500)]; sys.exit(0)"
)

def test_truncating_reader_cannot_kill_the_child():
    p = subprocess.Popen([sys.executable, "-c", _CHILD_SPEW % _ROOT],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for _ in range(3):
        p.stdout.readline()           # take three lines, then hang up mid-spew
    p.stdout.close()
    assert p.wait(timeout=15) == 0, \
        "the -First-N reader class must not kill the runner (exit 0, not EPIPE death)"


# --- P3: first line visible within 1s while the process still runs (line buffering) ---

_CHILD_SLOW = (
    "import sys, os, time; sys.path.insert(0, r'%s');"
    "from core.foundation.streams import self_bless_stdout; self_bless_stdout();"
    "print('first line out'); time.sleep(8)"
)

def test_first_line_visible_within_one_second():
    p = subprocess.Popen([sys.executable, "-c", _CHILD_SLOW % _ROOT],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        t0 = time.time()
        line = p.stdout.readline()
        elapsed = time.time() - t0
        assert "first line out" in line
        assert elapsed < 1.0, \
            f"line-buffered when piped: visible in {elapsed:.2f}s, not at buffer-fill/exit"
        assert p.poll() is None, "the process was still RUNNING when the line arrived"
    finally:
        p.kill()


# --- P4: the runner is WIRED to the blessing (built != wired) ---

def test_runner_wired_to_self_bless():
    src = open(os.path.join(_ROOT, "scripts", "bifrost_runner_deepseek.py"),
               encoding="utf-8").read()
    assert "self_bless_stdout" in src, "the runner calls the blessing at startup"


# --- P5: AGENTS.md carries the blessed-launch rule ---

def test_agents_md_carries_the_launch_rule():
    src = open(os.path.join(_ROOT, "AGENTS.md"), encoding="utf-8").read().lower()
    assert "truncating pipe" in src, \
        "the contract doc teaches: never launch a live runner through a truncating pipe"
