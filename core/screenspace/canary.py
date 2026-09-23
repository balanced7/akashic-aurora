"""Screenspace UIA availability — POSITIVE CANARY READ, not a context inference.

AMENDED RULING (Vandor, 2026-09-23): the session hypothesis died (ProcessIdToSessionId
said session 1 interactive all along; CoInitializeEx APARTMENTTHREADED succeeded while
GetForegroundControl() still returned None). The important correction is Heimdall's, in
his words: a self-check keyed on WINDOW STATION would PASS and the tier would still read
nothing -- a guard sharing the failure mode of the thing it guards
(safety_net_detector_must_not_share_failure_mode). So the AMENDED CONDITION is:

  the startup self-check must be a POSITIVE CANARY READ, not a context inference. Do not
  ask "am I in the right session / station / apartment". Actually READ a known property
  off the real foreground window and assert it is non-empty. If the canary comes back
  empty, the tier is UNAVAILABLE and says so. An environment check answers a cheaper
  question than "can I actually read", and this organ demonstrated twice that the cheap
  question says yes while the expensive one says None.

This module is the canary. It DELIBERATELY does NOT look at the window station, session
id, or apartment state -- those are the cheaper questions that already lied. It attempts
the one thing the organ must actually be able to do: read a property off the real
foreground window. The verdict is the READ ITSELF, never an inference about context.

TWO EMPTY READINGS, KEPT DISTINCT (this is the measurement the ruling still wants):
  - CanaryState.NO_FOREGROUND  -> GetForegroundControl() gave no window (nothing foreground).
    A genuine "empty desktop" state -- a real observation (D-1: foreground lost), not an
    availability failure per se.
  - CanaryState.UNREADABLE      -> a window EXISTS but the property read off it returned
    None/empty. This is the "valid handle, silent read failure" signature -- mechanism (b)
    in Vandor's ruling, the leading UIPI/integrity hypothesis. This is what an environment
    check CANNOT see and why the canary must be a real read.

Both come back "empty" and both mark the tier UNAVAILABLE for UIA reads (the refusal) --
but they are DISTINCT empty-readings, and reporting WHICH one is how the organ stops
collapsing "nothing in the foreground" with "I cannot read the foreground".

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md §1,
the 2026-09-23 §1 ratification, and its same-day amendment.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple


class CanaryState(str, Enum):
    """What a POSITIVE CANARY READ actually observed -- the read, not the context."""

    READABLE = "readable"            # a property read off the foreground window came back non-empty
    NO_FOREGROUND = "no_foreground"  # no foreground window to read at all (genuine empty desktop)
    UNREADABLE = "unreadable"        # a window exists, but the property read returned None/empty
    # NOTE: no "unknown" state. The canary ANSWERS by reading; it does not declare a context.
    # A failed READ attempt is UNREADABLE, not "unknown" -- absence of the answer is an answer
    # about the read, never about the session.


def _read_foreground_name() -> Tuple[Optional[int], Optional[str]]:
    """One REAL foreground read: name via UIA, hwnd as the validity proxy.

    Returns (hwnd_or_none, name_or_none). The signature distinctions:
      - name non-empty            -> READABLE (the read worked)
      - name None AND hwnd None   -> NO_FOREGROUND (nothing was foreground to read)
      - name None AND hwnd valid  -> UNREADABLE (valid handle, silent read failure --
        the UIPI/integrity mechanism (b) the ruling wants measured)

    This is the EXPENSIVE question, asked directly -- the one the organ must answer,
    never a cheaper proxy for it. Import is lazy and fail-soft: if the uiautomation
    surface is absent entirely, the read fails and that is UNREADABLE, not a context
    detection.
    """
    try:
        import uiautomation as auto  # type: ignore

        win = auto.GetForegroundControl()
        if win is None:
            return (None, None)
        name = win.Name
        hwnd = getattr(win, "NativeWindowHandle", None)
        return (hwnd, name)
    except Exception:  # noqa: BLE001 -- the READ failed; that is UNREADABLE, not "unknown"
        return (None, None)


def canary() -> CanaryState:
    """The positive canary: actually READ the foreground window and report the outcome.

    READABLE iff a property read returned a non-empty value. Anything else is an empty
    reading, and the tier is UNAVAILABLE -- but WHICH empty reading it was is preserved,
    because the ruling's leading hypothesis (UIPI/integrity) lives in the NO_FOREGROUND
    vs UNREADABLE distinction.
    """
    hwnd, name = _read_foreground_name()
    if name:
        return CanaryState.READABLE
    if hwnd is None:
        return CanaryState.NO_FOREGROUND
    return CanaryState.UNREADABLE


def uia_available() -> bool:
    """The consumer-facing refusal seam: True iff the canary READ non-empty.

    This now answers the EXPENSIVE question ("can I actually read?") rather than the
    cheap one ("am I in the right station?"). NO_FOREGROUND and UNREADABLE both mark the
    UIA tier unavailable for reads -- but the STATE (not this bool) tells the caller WHICH
    empty-reading it was, so "nothing in the foreground" and "I cannot read the
    foreground" never collapse. Callers that need the distinction read canary() directly.
    """
    return canary() is CanaryState.READABLE
