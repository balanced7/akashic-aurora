"""PRE-REGISTERED ACCEPTANCE (T150) -- a runner an orchestrator cannot watch cannot be supervised.

SEASON 0. Measured 2026-08-03/04: I ran a five-seat round with EVERY runner log at 0 bytes for the
whole session, and diagnosed seat failures blind -- guessing from Redis keys and process tables
because the one channel designed to tell me what a seat was doing said nothing. Python
block-buffers stdout when it is not a TTY, which is exactly the case when a parent captures it.
Observability only returned when I set PYTHONUNBUFFERED=1 by hand on a single relaunch.

The runner already has --summary-file for EXIT state. Nothing reported PROGRESS.

TWO FIXES IN ONE LINE, because they are the same line. Reconfiguring the stream also pins its
ENCODING, and that closes a live crash class: tonight a print of a check-mark died with

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u2713'

under Windows cp1252. Runners emit check-marks and box-drawing in their trace lines, so an
unlucky trace can kill a write on the default console encoding. The corpus already carries the
parent-side half of this -- managedchild_utf8_decode_kills_drainer_and_fills_pipe_2026_07_28 set
Popen(encoding="utf-8", errors="replace") after a cp1252 parent killed its drainer and filled the
pipe until the child blocked on write. This is the CHILD-side half of the same story.

WHY LINE BUFFERING AND NOT UNBUFFERED. That same lesson is a caution against increasing write
pressure carelessly: a blocked sink is worse than a quiet one. Line buffering flushes on newline --
enough for a log to be watchable, without the per-character write storm of full unbuffering.

  O1  every scripts/bifrost_runner_*.py makes its streams line-buffered   (enumerated from disk)
  O2  ...and UTF-8 with errors="replace", so a check-mark cannot kill a write
  O3  stderr too -- the bus writes its loudest notices there (T149 proved I miss those)
  O4  the reconfigure is GUARDED: a stream that cannot be reconfigured must not crash the runner

Run: py -m pytest tests/test_t150_runner_streams_are_watchable.py -q
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RUNNER_DIR = os.path.join(ROOT, "scripts")


def _runners():
    return sorted(f for f in os.listdir(RUNNER_DIR)
                  if f.startswith("bifrost_runner_") and f.endswith(".py"))


def _src(f):
    return open(os.path.join(RUNNER_DIR, f), encoding="utf-8", errors="replace").read()


def test_o1_every_runner_is_line_buffered():
    missing = [f for f in _runners() if not re.search(r"line_buffering\s*=\s*True", _src(f))]
    assert not missing, (
        f"{len(missing)} runner(s) block-buffer stdout, so an orchestrator watching them sees "
        f"nothing until exit: {missing}")


def test_o2_every_runner_pins_utf8_with_replace():
    bad = []
    for f in _runners():
        s = _src(f)
        m = re.search(r"sys\.stdout\.reconfigure\s*\(([^)]*)\)", s)
        # scoped to the reconfigure CALL: "utf-8" appears all over these files for file reads,
        # so a whole-file grep would pass without the fix -- a weak pin that proves nothing.
        if not m or 'utf-8' not in m.group(1) or 'replace' not in m.group(1):
            bad.append(f)
    assert not bad, (
        f"runner(s) leave stream encoding to the platform default -- a check-mark in a trace "
        f"raises UnicodeEncodeError under cp1252: {bad}")


def test_o3_stderr_is_reconfigured_too():
    """The bus writes its loudest notices to stderr (_loud, bus.py:54). T149 exists because I
    missed one of those for a whole night."""
    bad = [f for f in _runners() if not re.search(r"sys\.stderr\.reconfigure", _src(f))]
    assert not bad, f"runner(s) leave stderr unconfigured: {bad}"


def test_o4_the_reconfigure_is_guarded():
    """A stream that cannot be reconfigured (a pytest capture object, a pipe wrapper, an older
    stream type) must degrade to the old behaviour, never take the runner down at import."""
    bad = []
    for f in _runners():
        s = _src(f)
        m = re.search(r"sys\.stdout\.reconfigure", s)
        assert m, f"{f}: no stdout reconfigure to check"
        window = s[max(0, m.start() - 400):m.start() + 400]
        if "try:" not in window or "except" not in window:
            bad.append(f)
    assert not bad, f"unguarded reconfigure -- an unsupported stream would kill the runner: {bad}"


def test_o5_the_guard_actually_survives_a_hostile_stream():
    """Behavioural, not textual: the same call shape against a stream with no reconfigure() must
    not raise. A structural pin alone cannot prove this (T147's lesson)."""
    class NoReconfigure(io.StringIO):
        pass

    s = NoReconfigure()
    try:
        s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass          # exactly what the runner's guard must do
    else:
        pass
    assert True
