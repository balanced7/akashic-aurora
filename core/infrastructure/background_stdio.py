"""Repair stdout/stderr for a process launched with no console — the windowed-task blind spot.

MEASURED 2026-10-06, closing item 0 of the affordance-layer fence reconciliation, which both
sealed halves independently named as the highest-priority open question and which neither could
answer read-only.

THE MECHANISM, reproduced rather than asserted. A process started by Task Scheduler gets no
console and no inherited standard handles, and CPython then sets ``sys.stdout`` and ``sys.stderr``
to **None**. Reproducing this takes real care, and two obvious attempts do NOT reproduce it:

  * running ``pyw script.py`` from a shell INHERITS that shell's handles -- stdout is a real
    stream and everything prints normally;
  * ``subprocess.Popen(..., creationflags=DETACHED_PROCESS, stdout=None)`` also inherits, because
    ``stdout=None`` means "inherit the parent's handle", not "give it none".

The condition only appears with ``CreateProcessW(..., bInheritHandles=FALSE, DETACHED_PROCESS)``
and a STARTUPINFO that does NOT set ``STARTF_USESTDHANDLES``. Measured under exactly that:

    sys.stdout is None       -> True
    sys.stderr is None       -> True
    print("hello")           -> OK, silently discarded   (no exception)
    logging.info("probe")    -> OK, silently discarded   (no exception)
    sys.stdout.flush()       -> AttributeError: 'NoneType' object has no attribute 'flush'

So there are TWO failure classes, and they want different responses. ``print`` and ``logging``
do not raise -- output simply vanishes, which is why this hides for months. Anything that touches
a ``sys.stdout`` ATTRIBUTE (``.flush()``, ``.write()``, ``.isatty()``, ``.reconfigure()``) raises,
which kills the task partway through with nobody watching.

WHY THIS FUNCTION EXISTS RATHER THAN A SIXTH COPY. Two correct implementations of this repair
already existed when I measured: ``scripts/trader_archivist.py:60`` (``configure_background_stdio``)
and the wrapper ``run_aurora_service.py:41-54``. Someone hit this before and fixed it twice,
locally, and the fix did not reach the six sibling scripts that need it. That is the
``capability_without_a_door`` shape pointed at a helper instead of a verb -- and it is also the one
case the same fence said a single builder IS right for: one string, one job, one seam
(``arm_command`` was the precedent, and its own reviewer's rule was that a single builder earns its
place only when the seam is genuinely single). Repairing a dead stream is that.

This is deliberately NOT applied to the two existing copies: ``run_aurora_service.py`` lives in
another seat's worktree, and ``trader_archivist.py``'s copy is correct and running. A pin asserts
they AGREE in behaviour rather than that there is only one of them -- the remedy this house
actually uses (``tests/test_every_draining_door_names_its_lane.py:135`` is the precedent).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def log_root() -> Path:
    """Where a background task's rescued diagnostics land.

    Mirrors ``trader_archivist.configure_background_stdio`` exactly, including the LOCALAPPDATA
    preference and the ``state/`` fallback, so the two implementations put their logs in the same
    place and an operator has one directory to look in rather than two.
    """
    base = os.getenv("LOCALAPPDATA")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "state"
    return root / "AkashicAurora" / "logs"


def repair_background_stdio(name: str) -> Optional[Path]:
    """Point ``sys.stdout``/``sys.stderr`` at a log file when they are None. Returns its path.

    Call this FIRST in a script's ``main``, before argument parsing and before importing anything
    that might print or log -- a module that prints at import time does so before any repair that
    comes after the import.

    Returns None when the streams are already live, which is the normal interactive case: this is
    a no-op for every console run, so it is safe to call unconditionally. It never raises; a
    failure to open the log leaves the streams as they were, because a diagnostics helper that
    kills the job it was meant to make debuggable is worse than the silence it replaces.

    Args:
        name: a short slug for the log file, e.g. ``"mem-watch"`` -> ``mem-watch.log``.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    try:
        root = log_root()
        root.mkdir(parents=True, exist_ok=True)
        path = root / ("%s.log" % name)
        stream = path.open("a", encoding="utf-8", errors="replace", buffering=1)
    except Exception:  # noqa: BLE001 -- see docstring: never make the job fail
        return None
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    return path
