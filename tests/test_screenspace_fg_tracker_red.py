"""Screenspace organ — WinEventHook foreground tracker, RED pins (T386 §1.1, F2→v1).

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md §1.1
(EVENT_SYSTEM_FOREGROUND via WinEventHook; §1.2 dedicated handler thread).

Heimdall LANDED the ForegroundTracker at core/screenspace/foreground.py with a
pure-seam (Windows-free, synthetic-testable) + Windows-adapter (fail-soft start/stop)
split. These pins drive the PURE SEAM — event-wiring contract, no desktop needed —
against his exact signatures:

  ForegroundTracker()
    .focus  -> Optional[str]   (property; None until a real change delivered)
    .gen    -> int             (property; monotone, +1 per delivery)
    .subscribe(observer)       -> None
    .on_foreground_change(name) -> None   (pure delivery: record + notify; NEVER calls UIA)

TWO DESIGN POINTS this file pins (Heimdall encoded them; pinning makes them
regression-proof):
  D-1  None is a LEGAL delivery (foreground lost): gen still increments, observers
       still fire. None must NOT be misread as "tracker broken."
  D-2  §1.2 handler discipline: on_foreground_change is PURE — it must not import or
       call UIA. (The hook callback records hwnd + wakes worker; the worker resolves
       name OFF-thread THEN calls on_foreground_change. UIA never runs in the pure
       seam.)

Anti-fitting: no specific window title or desktop content; these assert on EVENT
shape (subscribe→deliver→focus+gen update) and the purity/None-legal invariants.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_IMPORT_ERROR = None  # so the skipif reason string is safe when the import SUCCEEDS
try:
    from core.screenspace.foreground import ForegroundTracker  # noqa: F401
    _IMPORT_OK = True
except Exception as exc:  # noqa: BLE001
    _IMPORT_OK = False
    _IMPORT_ERROR = exc

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="core.screenspace.foreground.ForegroundTracker not yet built — RED: "
           f"engine must satisfy this contract (import failed: {_IMPORT_ERROR!r})",
)


def test_f1_subscribe_seam_exists():
    """F-1: subscribe registers an observer (the subscription seam exists and
    accepts a callable). Keeping a subscriber pinned here so F-2's delivery has a
    registered listener to observe against."""
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    seen = []
    t.subscribe(seen.append)


def test_f2_synthetic_delivery_updates_cache_and_notifies():
    """F-2: a synthetic EVENT_SYSTEM_FOREGROUND delivery (on_foreground_change)
    updates the cache (t.focus) AND notifies the subscribed listener with the
    resolved name, in order. This is the PRODUCTION delivery path — the worker
    calls it after resolving hwnd→name off the hook thread — and the synthetic
    injection seam, unified by design (no separate test-only .fire())."""
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    seen = []
    t.subscribe(seen.append)
    t.on_foreground_change("chrome.exe")
    assert t.focus == "chrome.exe"
    assert seen == ["chrome.exe"]

    # in-order multi-delivery: cache tracks the latest, listener sees each
    t.on_foreground_change("notepad.exe")
    assert t.focus == "notepad.exe"
    assert seen == ["chrome.exe", "notepad.exe"]


def test_f3_warm_read_returns_cache_not_poll():
    """F-3: a warm read returns the CACHE, not a poll. With no active hook, a
    poll-per-call would return None (nothing delivered); the cache returns whatever
    on_foreground_change was last given. This certifies the F2→v1 WARM read <5ms
    claim for the pure seam (the warm-hit is structural: cache read vs COM round-trip).
    The cold-start and event-delivery numbers are the bench's job; this pin only
    asserts the warm shape."""
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    t.on_foreground_change("notepad.exe")
    # no hook, no desktop: a poll would give None; the cache gives the last delivery
    assert t.focus == "notepad.exe"


def test_d0_gen_is_monotone_across_deliveries():
    """D-0: gen is a monotone ordinal, +1 per delivery (including same-name
    re-delivery) — the see-side currency the delta/peek ladder depends on."""
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    assert t.gen == 0
    t.on_foreground_change("a.exe")
    assert t.gen == 1
    t.on_foreground_change("b.exe")
    assert t.gen == 2
    t.on_foreground_change("b.exe")  # same name re-delivered still advances
    assert t.gen == 3


def test_d1_none_is_a_legal_delivery_not_a_error():
    """D-1: foreground-LOST is a real observation — None is delivered to observers
    and gen still advances (never misread as 'tracker broken')."""
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    seen = []
    t.subscribe(seen.append)
    t.on_foreground_change("chrome.exe")
    t.on_foreground_change(None)   # foreground lost
    assert seen == ["chrome.exe", None]
    assert t.focus is None
    assert t.gen == 2              # the loss was a DELIVERY, not a no-op


def test_d2_pure_seam_does_not_import_uia():
    """D-2 (§1.2): the pure delivery seam must never call UIA. on_foreground_change
    and the constructor/subscribe are Windows-free and UIA-free — the hook callback's
    §1.2 'never re-enter UIA' discipline is enforced by keeping UIA OUT of the pure
    seam entirely (resolution happens in the Windows adapter's _resolve_name, off-
    thread, never inside on_foreground_change).

    Asserted STRUCTURALLY, not via sys.modules (which is process-global and polluted
    by prior tests in the same run): the module source must import uiautomation LAZILY
    inside _resolve_name (the Windows adapter's off-thread path), NEVER at module
    top-level. A top-level `import uiautomation` would make the pure seam's import
    itself pull UIA, violating §1.2.
    """
    import inspect

    import core.screenspace.foreground as fg

    src = inspect.getsource(fg)
    # The ONLY uiautomation import must be a LAZY import inside a method body
    # (indented), i.e. _resolve_name's `import uiautomation as auto`. A module-level
    # (unindented) `import uiautomation` would be the violation.
    for line in src.splitlines():
        if "import uiautomation" in line:
            assert line.strip() != line, (
                f"uiautomation is imported at MODULE SCOPE (violates §1.2 pure-seam "
                f"purity): {line!r} — it must be lazy, inside _resolve_name only"
            )
    # And the pure seam itself runs clean.
    t = fg.ForegroundTracker()
    t.subscribe(lambda _n: None)
    t.on_foreground_change("x.exe")
    assert t.focus == "x.exe"
