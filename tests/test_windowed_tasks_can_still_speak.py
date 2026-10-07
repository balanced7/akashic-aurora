"""Pins: a scheduled task launched without a console had no voice, and nothing noticed for months.

Closes item 0 of the affordance-layer fence reconciliation
(`fences/affordance-layer/reconciliation.md` sec.6), which BOTH sealed halves independently named
as the highest-priority open question and which NEITHER could answer read-only. Heimdall:
*"a notification system whose own background jobs cannot emit is a carriage with no horses."*

WHAT WAS MEASURED, 2026-10-06, by reproduction rather than assertion.

A process started by Task Scheduler gets no console and no inherited standard handles, and CPython
then sets ``sys.stdout``/``sys.stderr`` to **None**. Two obvious attempts do NOT reproduce it and
both gave a false all-clear first:

  * ``pyw script.py`` from a shell INHERITS the shell's handles -- stdout is a live stream;
  * ``Popen(..., creationflags=DETACHED_PROCESS, stdout=None)`` also inherits, because
    ``stdout=None`` means "inherit", not "give it none".

Only ``CreateProcessW(..., bInheritHandles=FALSE, DETACHED_PROCESS)`` with a STARTUPINFO that does
not set ``STARTF_USESTDHANDLES`` reproduces it. Under exactly that::

    sys.stdout is None    -> True        print("hello")        -> OK, silently discarded
    sys.stderr is None    -> True        logging.info("x")     -> OK, silently discarded
                                         sys.stdout.flush()    -> AttributeError

So there are two classes: ``print``/``logging`` vanish WITHOUT raising, which is why this hid for
months; anything touching a ``sys.stdout`` ATTRIBUTE raises and kills the task partway.

THE CENSUS, and it corrects the claim that prompted it. The claim was "7 of 13 AkashicAurora
scheduled tasks launch pythonw.exe with sys.stdout is None".

  * 13 tasks exist -- the count is right.
  * **12 of 13 are windowed**, not 7: five name ``pythonw.exe`` outright and seven name ``pyw``,
    which IS the windowed launcher (it resolves to ``pythonw.exe`` -- verified by reading
    ``sys.executable`` from a process launched as ``pyw``). A first pass of mine classified ``pyw``
    as a console launcher and undercounted exactly as the claim did; the launcher's short name is
    the trap.
  * **but 5 of those 12 were ALREADY FIXED** before anyone filed the claim: four go through the
    ``run_aurora_service.py`` wrapper, which repairs the streams at lines 41-54, and
    ``scripts/trader_archivist.py:60`` carries its own ``configure_background_stdio``. Someone hit
    this before and fixed it twice, locally, and the fix did not reach the siblings.
  * So the genuinely exposed set was **7 tasks over 6 scripts** -- numerically the claim's "7", by
    coincidence rather than by the membership it meant.
  * The claim's SEVERITY ("the FACT layer destroyed at launch") is literally true for exactly two
    of them: ``check_secrets.py --history`` (11 prints, **zero** file writes -- the weekly secret
    scan's entire output vanished) and ``failsafe_watcher.py`` (3 prints, zero file writes). The
    other four write durable files, so only their progress prints were lost.
  * NO crash-class exposure: zero direct ``sys.stdout.`` attribute use outside the repair blocks.

RECEIPT. ``failsafe_watcher.py --dry`` launched under the reproduced condition, before and after:
the log file did not exist, and afterwards holds ``[failsafe] silent -- stood down`` (33 bytes) --
output that was discarded on every prior run of that task.

Run::

    py -m pytest tests/test_windowed_tasks_can_still_speak.py -q
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.infrastructure import background_stdio as B  # noqa: E402

#: Entry scripts of the WINDOWED AkashicAurora scheduled tasks that live in THIS repo and are
#: launched directly (not through the run_aurora_service.py wrapper). Enumerated explicitly rather
#: than read from Task Scheduler, so the pin is deterministic and does not pass vacuously on a host
#: where the tasks are not registered.
DIRECT_WINDOWED_TASK_SCRIPTS = (
    "scripts/revive.py",                      # AkashicAurora-DaemonWatchdog
    "scripts/ops/archive_ephemeral.py",       # AkashicAurora-EphemeralArchive-Daily
    "scripts/ops/failsafe_watcher.py",        # AkashicAurora-Failsafe-Deadman
    "scripts/ops/mem_watch.py",               # AkashicAurora-MemWatch
    "scripts/checkers/check_secrets.py",      # AkashicAurora-SecretScan-HistoryWeekly
    "scripts/ops/archive_transcripts.py",     # AkashicAurora-TranscriptArchive-{Daily,VerifyWeekly}
    "scripts/ops/eye_ingest_task.py",         # AkashicAurora-EyeIngest-Daily (2026-10-07)
    "scripts/bifrost_daemon.py",              # AkashicAurora-WakeDaemon (2026-10-07)
)

#: The one that already had its own correct copy. Pinned for AGREEMENT, not folded into the helper:
#: it is running, it is right, and a pin that two surfaces agree is this house's actual remedy
#: (tests/test_every_draining_door_names_its_lane.py:135 is the precedent) rather than a rule that
#: there be only one emitter.
PRE_EXISTING_COPY = "scripts/trader_archivist.py"


def _src(rel: str) -> str:
    return io.open(ROOT / rel, encoding="utf-8").read()


# ------------------------------------------------------------------ the helper
def test_the_repair_is_a_noop_when_the_streams_are_live():
    """Safe to call unconditionally, which is what lets it be the first line of every main()."""
    assert B.repair_background_stdio("pin-probe") is None


def test_the_repair_never_raises_even_when_it_cannot_open_its_log(monkeypatch):
    """A diagnostics helper that kills the job it was meant to make debuggable is worse than the
    silence it replaces. So a failure to open the log leaves the streams as they were."""
    monkeypatch.setattr(B, "log_root", lambda: Path("\\\\?\\nonexistent-device\\nope"))
    monkeypatch.setattr(sys, "stdout", None)
    try:
        assert B.repair_background_stdio("pin-probe") is None
    finally:
        monkeypatch.undo()


def test_the_helper_and_the_pre_existing_copy_agree_on_where_logs_go():
    """AGREEMENT PIN. Two implementations exist on purpose; an operator must still have ONE
    directory to look in. Both prefer LOCALAPPDATA and both fall back to the repo's state/."""
    helper = _src("core/infrastructure/background_stdio.py")
    older = _src(PRE_EXISTING_COPY)
    for token in ("LOCALAPPDATA", "AkashicAurora", "logs"):
        assert token in helper, f"the helper does not reference {token!r}"
        assert token in older, f"{PRE_EXISTING_COPY} does not reference {token!r}"
    assert 'open("a"' in helper or '.open("a"' in helper, "the helper does not APPEND"
    assert '"a"' in older, f"{PRE_EXISTING_COPY} does not append"


# ------------------------------------------------------------------ coverage
@pytest.mark.parametrize("rel", DIRECT_WINDOWED_TASK_SCRIPTS)
def test_every_direct_windowed_task_script_repairs_its_streams(rel):
    """THE PIN. Each of these is launched by `pyw` from Task Scheduler, so every print() in it is
    discarded unless it repairs stdout first. Two of them wrote NO files at all, so their whole
    output was the only evidence they ran."""
    src = _src(rel)
    assert "repair_background_stdio" in src, (
        "%s is a windowed scheduled-task entry point and does not repair its streams. Launched by "
        "pyw (= pythonw.exe) with no console and no inherited handles, sys.stdout is None and every "
        "print() in it is silently discarded -- no exception, no output, no evidence it ran." % rel)


@pytest.mark.parametrize("rel", DIRECT_WINDOWED_TASK_SCRIPTS)
def test_the_repair_runs_before_anything_can_print(rel):
    """Ordering is the whole value: a repair that happens after argument parsing misses every
    usage error, and one that happens after an import misses anything that prints at import time."""
    src = _src(rel)
    i = src.index("repair_background_stdio(")
    head = src[:i]
    for late in ("parse_args(", "argparse.ArgumentParser("):
        j = head.rfind(late)
        assert j == -1 or "def main" not in src[j:i], (
            "%s parses arguments before repairing stdout, so an argparse error message -- which "
            "goes to stderr and exits -- is still lost" % rel)


def test_no_task_script_touches_a_stdout_attribute_outside_a_guard():
    """The CRASH class, as opposed to the silent one. `sys.stdout.flush()` raises AttributeError
    when stdout is None, which kills a scheduled task partway with nobody watching. Measured as
    absent across these scripts; this keeps it absent."""
    offenders = []
    for rel in DIRECT_WINDOWED_TASK_SCRIPTS:
        for n, line in enumerate(_src(rel).splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or "is None" in s or "is not None" in s:
                continue
            for attr in ("sys.stdout.", "sys.stderr."):
                if attr in s:
                    offenders.append("%s:%d %s" % (rel, n, s[:70]))
    assert not offenders, (
        "a windowed task script touches a stdout/stderr ATTRIBUTE, which raises AttributeError "
        "when the stream is None and kills the task partway: %s" % offenders)


def test_pyw_is_recognised_as_the_windowed_launcher_in_the_record():
    """The trap that made both the original claim and my own first pass undercount: `pyw` is the
    WINDOWED launcher (it resolves to pythonw.exe), so a classifier matching only /pythonw|\\.pyw/
    reads seven windowed tasks as console tasks. Pinned in prose so the next reader of this file
    does not repeat it."""
    doc = __doc__ or ""
    assert "pyw" in doc and "windowed launcher" in doc, (
        "the module docstring no longer records that `pyw` IS pythonw.exe -- the single fact that "
        "made three separate counts of this defect wrong")
