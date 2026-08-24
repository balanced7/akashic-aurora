"""
Pytest bootstrap for the test suite.

Puts the repo root AND this tests/ directory on sys.path so tests can import both
project packages (``core.*``, ``context.*``) and test-local helpers (``isolate_canonical``,
``narrative_metrics``, ``fixtures.*``) regardless of the invocation cwd. Previously
several tests only collected when pytest happened to be run from inside tests/ -- this
makes ``py -m pytest tests/`` from the repo root work the same way.

Backend isolation (Redis db 15 + temp AI_SETUP) stays opt-in per-test via
``import isolate_canonical`` so suites that intentionally exercise the real backends are
unaffected. Recall SCRATCH state is the one universal exception (see below).
"""
import os
import sys
import tempfile

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TESTS)
for _p in (_ROOT, _TESTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Recall scratch state (warm cache / seen / impressions / flips / nudges / injections) is
# UNIVERSALLY isolated: core/recall/at_action.py and the hook scripts derive their state dir
# from this env var at import time. Without it, any test that transitively warms the cache
# (e.g. a hook main()) OVERWRITES the production cache file with isolated-store contents --
# live recall then serves [] until the TTL heals it (found 2026-07-02 by dogfooding: 64 green
# unit tests + a blank production cache). Unlike backend isolation, NO test ever legitimately
# wants the real recall scratch, so this one is unconditional.
os.environ.setdefault("AKASHIC_RECALL_STATE_DIR",
                      tempfile.mkdtemp(prefix="akashic_recall_test_"))

# ---------------------------------------------------------------------------
# T070: BACKEND ISOLATION IS NOW UNIVERSAL TOO (2026-07-25).
#
# It used to be opt-in per file via `import isolate_canonical`, on the reasoning that some
# suites "intentionally exercise the real backends". The census that ended that argument:
# 150 test files touch a default store or knowledge surface; EIGHT imported the helper. The
# other 142 were free to read and write canonical Redis db 0 and the live
# session_logs/store_state.json -- which is exactly the standing hazard every boot carried,
# "the pytest suite DESTROYS the live learning index, run repair_learning_index --check
# after ANY suite run".
#
# The opt-in never protected what it claimed to: isolate_canonical redirects Redis to
# **db 15**, not to nothing, so a test that wants a live Redis still gets one. Only a test
# asserting on CANONICAL CONTENT could break -- and those are flaky by construction, which
# T070 itself recorded (a boot under the flag read live data, "8 lesson(s)", and live notes
# leaked non-ASCII into an ASCII pin).
#
# The real cost was second-order: a suite that is dangerous to run is a suite nobody runs.
# It rotted unnoticed until CI was found red for over a day with the whole suite skipped.
# The hazard and the rot were one loop.
#
# So this mirrors the recall-scratch decision immediately above -- isolate by default, and
# make the escape hatch explicit rather than implicit-by-forgetting.
if not os.environ.get("AKASHIC_TEST_USE_CANONICAL"):
    import isolate_canonical  # noqa: F401,E402  (side-effect: temp AI_SETUP + db 15 + flush)
else:
    # Deliberate operator override, e.g. reproducing a canonical-state incident. Loud, so
    # nobody discovers afterwards that a run touched real data.
    print("[conftest] AKASHIC_TEST_USE_CANONICAL set -- tests will touch REAL backends. "
          "Run scripts/repair_learning_index.py --check afterwards.")

# ---------------------------------------------------------------------------
# WINDOWS: CHILD PROCESSES RUN WITHOUT POPPING A CONSOLE WINDOW (2026-07-25, Daniel-asked).
#
# 35 test files spawn subprocesses -- killwindow drills, daemon supervisors, durable-job
# guards, the FileStore coherence pin. When pytest runs without an attached console (any
# agent harness, an IDE runner, a scheduled task), each child console app has no console to
# inherit, so Windows gives it a NEW ONE: a cmd box flashes on screen per spawn. A full
# suite run turns the desktop into a strobe light. It is cosmetic, but it makes the suite
# unrunnable while a human is using the machine, and a suite nobody runs rots -- which is
# the same second-order failure T070 records immediately above.
#
# Fixed here rather than in 35 files because it is a property of running the SUITE, not of
# any one test, and because a per-file convention is one someone forgets on file 36.
#
# The rule is conservative -- add CREATE_NO_WINDOW only when the caller has expressed no
# opinion about consoles:
#   - CREATE_NEW_CONSOLE set  -> the caller WANTS a visible console; never override intent.
#   - DETACHED_PROCESS set    -> child already gets no console; CREATE_NO_WINDOW is also
#                                mutually exclusive with it in Win32 (ERROR_INVALID_PARAMETER),
#                                so adding it would break the spawn outright.
#   - CREATE_NO_WINDOW set    -> already correct, leave it alone.
# Everything else gets the flag. Popen is the single chokepoint: run/call/check_output all
# funnel through it, so patching here covers production code the tests drive (launcher.py
# spawns with CREATE_NEW_PROCESS_GROUP and no window flag) as well as direct test spawns.
#
# Tests that ASSERT on creationflags are unaffected: they capture kwargs at their own
# monkeypatched seam, which sits above this one, and they test bits rather than equality.
#
# Escape hatch, deliberately explicit: AKASHIC_TEST_SHOW_CONSOLES=1 to watch the windows
# when debugging a spawn that dies before it can log anything.
if sys.platform == "win32" and not os.environ.get("AKASHIC_TEST_SHOW_CONSOLES"):
    import subprocess as _subprocess

    _CREATE_NO_WINDOW = getattr(_subprocess, "CREATE_NO_WINDOW", 0x08000000)
    _CREATE_NEW_CONSOLE = getattr(_subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
    _DETACHED_PROCESS = getattr(_subprocess, "DETACHED_PROCESS", 0x00000008)
    _CONSOLE_INTENT = _CREATE_NEW_CONSOLE | _DETACHED_PROCESS | _CREATE_NO_WINDOW

    _popen_init = _subprocess.Popen.__init__

    def _quiet_popen_init(self, *args, **kwargs):
        flags = kwargs.get("creationflags", 0)
        if not flags & _CONSOLE_INTENT:
            kwargs["creationflags"] = flags | _CREATE_NO_WINDOW
        return _popen_init(self, *args, **kwargs)

    _subprocess.Popen.__init__ = _quiet_popen_init

    # GRANDCHILDREN. The patch above lives in THIS process, so it covers what a test spawns
    # directly -- and nothing deeper. Measured 2026-08-01: tests spawn scripts/mirror.py 17
    # times (silenced here), and mirror.py then spawns git 3 times from a process that never
    # imported this file, so every one of those git.exe children still got a console window.
    # That is where the remaining flashing came from.
    #
    # PYTHONPATH is an ENVIRONMENT variable and is therefore inherited transitively, so naming
    # a directory that holds sitecustomize.py makes every descendant -- child, grandchild,
    # great-grandchild -- auto-import it and apply the same rule. Same argument as the comment
    # above ("fixed here rather than in 35 files"), carried one level further out.
    #
    # A DEDICATED directory, never the repo root: putting the root on PYTHONPATH would place
    # every top-level module here on the import path of every python process that inherits the
    # env, which is a shadowing hazard traded for a cosmetic fix. scripts/quiet/ holds exactly
    # one file and nothing else can be shadowed by it.
    _quiet = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "scripts", "quiet")
    _pp = os.environ.get("PYTHONPATH", "")
    if _quiet not in _pp.split(os.pathsep):
        os.environ["PYTHONPATH"] = (_quiet + os.pathsep + _pp) if _pp else _quiet


# ---------------------------------------------------------------------------
# The conductor gate's audit trail must never be written by a test run.
#
# 2026-08-24: `append_provenance` resolves to a machine-global %TEMP% path, so
# tests/drill_conductor_gate.py -- which deliberately raises
# RuntimeError("probe exploded") and runs a dry_run activation -- wrote into the
# PRODUCTION audit log. During the triage of a real 2h44m conductor outage those
# lines parsed as a live 12:04:59 detection-that-crashed and nearly became the
# post-mortem's headline finding. An audit log that manufactures false incident
# narratives is worse than no audit log, because it is believed.
#
# Fixed HERE rather than in each drill file, and autouse rather than opt-in, for
# the same reason the console-quieting above is: isolation that depends on the
# next author remembering is isolation that will lapse. A new gate drill added
# by any seat is now safe by default.
import pytest as _pytest


@_pytest.fixture(autouse=True)
def _isolate_conductor_gate_provenance(tmp_path_factory, monkeypatch):
    try:
        from core.comm.conductor_gate import PROVENANCE_ENV, _reset_heartbeat
    except Exception:                                                   # noqa: BLE001
        return                      # gate absent/renamed: nothing to isolate
    d = tmp_path_factory.mktemp("conductor_gate_prov")
    monkeypatch.setenv(PROVENANCE_ENV, str(d / "conductor_gate.provenance.log"))
    _reset_heartbeat()              # rate-limit state must not leak between tests
