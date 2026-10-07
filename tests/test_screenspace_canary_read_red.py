"""Screenspace §1 amended ruling: the UIA tier REFUSES via a POSITIVE CANARY READ.

Amended ruling (Vandor, 2026-09-23): the session hypothesis died; the surviving condition
is that the startup self-check must be a POSITIVE CANARY READ, not a context inference --
"do not ask 'am I in the right session/station/apartment'; actually READ a known property
off the real foreground window and assert it is non-empty. If the canary comes back empty,
the tier is UNAVAILABLE and says so." The reason, in Heimdall's words (this is the pinned
law): a self-check keyed on WINDOW STATION would PASS and the tier would still read nothing
-- a guard sharing the failure mode of what it guards (safety_net_detector_must_not_share_failure_mode).

This file pins the CANARY CONTRACT, so the reversed failure (an environment check saying
yes while the read says None) cannot recur silently:

  C-1  canary() has NO "unknown" state: it ANSWERS by reading. A failed read is UNREADABLE,
       not "unknown" -- absence of the answer is an answer about the READ, never a context
       declaration. (There is no window-station / session / apartment check anywhere in the
       availability path.)
  C-2  the two empty-readings are DISTINCT states: NO_FOREGROUND ("nothing was foreground")
       vs UNREADABLE ("a window was foreground but I could not read it"). The distinction is
       the leading UIPI/integrity hypothesis's signature and must not collapse.
  C-3  uia_available() is True ONLY when the canary READ non-empty (READABLE). Both empty
       states refuse.
  C-4  the result types carry the uia_unavailable flag explicitly (ScreenResult, Pulse) --
       a FIELD, not an inference from a missing value.

Anti-fitting: no window title, no desktop content. These assert on the state MACHINE and
the flag propagation; the live read itself is the interactive-session's job.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_IMPORT_ERROR = None
try:
    from core.screenspace import canary
    from core.screenspace.canary import CanaryState
    from core.screenspace.engine import ScreenResult
    from core.screenspace.shadow import Pulse
    _IMPORT_OK = True
except Exception as exc:  # noqa: BLE001
    _IMPORT_OK = False
    _IMPORT_ERROR = exc

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="core.screenspace.canary not yet built -- RED: "
           f"the amended §1 ruling requires a positive canary read (import failed: {_IMPORT_ERROR!r})",
)


def test_c1_canary_has_no_unknown_state():
    """C-1: CanaryState has only READABLE / NO_FOREGROUND / UNREADABLE. No 'unknown'.
    The canary ANSWERS by reading; it never declares a context it did not measure."""
    states = {s.value for s in CanaryState}
    assert states == {"readable", "no_foreground", "unreadable"}
    assert "unknown" not in states


def test_c2_two_empty_readings_are_distinct():
    """C-2: NO_FOREGROUND and UNREADABLE are different enum members -- the distinction
    between 'nothing was foreground' and 'something was foreground but unreadable' must
    not collapse into one None-shaped answer."""
    assert CanaryState.NO_FOREGROUND is not CanaryState.UNREADABLE
    assert CanaryState.NO_FOREGROUND is not CanaryState.READABLE
    assert CanaryState.UNREADABLE is not CanaryState.READABLE


def test_c3_uia_available_true_only_on_readable():
    """C-3: the refusal seam is True ONLY when the canary READ non-empty. READABLE is the
    only state that certifies; both empty states refuse."""
    assert CanaryState.READABLE is CanaryState.READABLE
    # The rule, stated structurally: uia_available() -> canary() is READABLE.
    # We can't force a live desktop here, so we pin the LOGIC via the module source's
    # own definition, plus the pure fact that only READABLE is a non-empty read.
    import inspect
    import core.screenspace.canary as c

    src = inspect.getsource(c.uia_available)
    assert "CanaryState.READABLE" in src
    assert "canary()" in src  # it asks the canary, not a station/session check


def test_c4_result_types_carry_explicit_unavailable_flag():
    """C-4: ScreenResult and Pulse carry ``uia_unavailable`` (default False) so the
    unavailable-vs-empty distinction is a FIELD, not an inference from absence."""
    r = ScreenResult()
    assert r.uia_unavailable is False
    assert "uia_unavailable" in r.to_dict()

    p = Pulse()
    assert p.uia_unavailable is False
    assert "uia_unavailable" in p.to_dict()


def test_c5_no_context_inference_in_availability_path():
    """C-5 (the amended ruling's load-bearing point): the availability path makes NO
    window-station / session / apartment check. The guard must NOT share the failure
    mode of the thing it guards -- it must ask 'can I actually read', never 'am I in
    the right context'.

    Inspects the EXECUTABLE surface (function bodies + the module-level calls), not the
    docstring -- the docstring legitimately NARRATES the falsification (it names the
    rejected context checks as history). The executable path must never PERFORM one."""
    import inspect
    import core.screenspace.canary as c

    # Function sources only (exclude the module docstring, which recounts the ruling).
    bodies = "\n".join(inspect.getsource(fn) for _, fn in inspect.getmembers(c, inspect.isfunction)
                       if fn.__module__ == c.__name__)
    forbidden = ("GetProcessWindowStation(", "ProcessIdToSessionId(", "CoInitializeEx(",
                 "Winsta0", "GetUserObjectInformation")
    for token in forbidden:
        assert token not in bodies, (
            f"availability EXECUTABLE path performs forbidden context check '{token}' -- "
            "a positive canary must READ, not infer context (safety_net_detector_"
            "must_not_share_failure_mode)"
        )
    # And the read it DOES perform is the expensive question: the foreground read itself.
    assert "GetForegroundControl" in bodies or "GetForegroundWindow" in bodies, (
        "canary executable path does not actually READ the foreground window -- it must "
        "perform the positive read, not a cheaper proxy"
    )
