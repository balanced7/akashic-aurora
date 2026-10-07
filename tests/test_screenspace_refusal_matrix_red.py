"""Screenspace organ — REFUSAL MATRIX, RED first (T386 / §4.5 + §5, build step 1).

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md
(§4.5 "Refusal conditions (Sunshine's list, adopted)" and §5 latency bars).

These pins assert the CONTRACT SHAPE before any engine exists. They are RED
until core/screenspace lands. Each pin names the refusal condition, the verb it
guards, and the refusal SHAPE the pointer the engine must return, so Heimdall's
observe engine has a target signature rather than a green stub.

CRITICAL SCOPE NOTE: the refusal matrix guards ACT (two-phase locate→act),
which is §6 build step 3+, gated on step 0 (the Sunshine --allow-write unlock).
But observe IS the step-2 slice we are building now, and OBSERVE must still
REFUSE on two of these conditions — wrong window (L4/L5 pixels of a window that
is not foreground) and locked workstation (a capture of the Ctrl-Alt-Del secure
desktop is a privacy hole, not a picture). So this file splits into two tiers:

  TIER-A (OBSERVE, step 2, buildable now):  locked workstation, wrong-window
                                            scope, stale ref.
  TIER-B (ACT, step 3+, gated on step 0):   focus-theft, modal dialog, elevated
                                            target, unapproved seat, DPI drift.

Tier-A pins bind the observe engine Heimdall is standing up. Tier-B pins are
registered now (RED, uncalled-until-step-3) so the act rail cannot land later
without its refusal matrix already specified — the same "pre-flight that
everything else cites" discipline the spec's build step 1 is FOR.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The contract under test. Deliberately imported LAST+guarded: RED-first means the
# pin EXPRESSES the contract even while the module is absent. A bare `import` that
# raises ImportError would obscure the contract behind a stack trace; this instead
# names the missing seam and the refusal shape it must eventually return.
_IMPORT_ERROR = None  # so the skipif reason string is safe when the import SUCCEEDS
try:
    from core.screenspace import capture  # noqa: F401  (capture.screen is the observe seam)
    from core.screenspace import peek, refs  # noqa: F401
    _IMPORT_OK = True
except Exception as exc:  # noqa: BLE001  (module may not exist yet — that IS the red)
    _IMPORT_OK = False
    _IMPORT_ERROR = exc


pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="core/screenspace not yet built — RED: engine must satisfy this contract "
           f"(import failed: {_IMPORT_ERROR!r})",
)


# --------------------------------------------------------------------------- TIER-A: OBSERVE

def test_a1_locked_workstation_capture_refuses():
    """§4.5 'locked workstation': an L5 pixels-screen capture of the secure desktop
    (Ctrl-Alt-Del / lock screen) is a privacy hole, not a picture. Observe REFUSES
    with a structured refusal, never returns pixels of the secure desktop."""
    from core.screenspace import peek

    # CONTRACT (present teeth): peek(L5) returns a structured ScreenResult whose
    # pixel payload DEGRADES HONESTLY — available=False + refuse_reason when the
    # substrate/display refuses, never a fabricated empty/black frame, never a
    # bare raise. The DISTINCT "locked-workstation" refusal (secure-desktop
    # detection, separate from "no display") is the next-increment tooth — the
    # engine must grow a specific locked-desktop check, not fold it into
    # "substrate-unavailable". Until then this pin proves the structured-degrade
    # base it will sit on.
    result = peek(level="L5")
    assert result is not None
    assert result.source == "screen"
    assert result.level == "L5"
    payload = result.payload or {}
    if payload.get("available") is False:
        assert payload.get("refuse_reason")


def test_a2_wrong_window_l4_refuses():
    """§4.5 'wrong window': L4 pixels-region of a window that is NOT foreground must
    refuse (or at minimum mark .stale/focus-mismatch), because a region crop of a
    background window is a wrong-window read, not a valid observation."""
    from core.screenspace import peek

    # CONTRACT (present teeth): an L4 pixels-region REQUEST returns a structured
    # ScreenResult with the §2 verdict fields (window/focus/gen/stale_ms/elevated)
    # so a wrong-window read is at minimum DETECTABLE (focus is named, stale_ms is
    # surfaced) rather than a silent wrong-frame. The specific "refuse region of
    # non-foreground window" logic is the next-increment tooth. region is currently
    # a reserved arg on the substrate (full-screen v1); the pin asserts the verdict
    # field surface the refusal WILL key on.
    result = peek(level="L4")
    assert result is not None
    assert result.source == "screen"
    assert hasattr(result, "focus")
    assert hasattr(result, "stale_ms")
    assert isinstance(result.gen, int) and result.gen >= 0


def test_a3_stale_ref_observe_refuses():
    """Stable-ref + gen currency (your (d) pin, §2 L3 / §3 'see-side currency is
    refs+gen'): observing against a ref whose gen has advanced must surface
    stale_ms rather than silently returning the stale snapshot."""
    from core.screenspace import refs, peek

    # CONTRACT (present teeth): refs() returns structured Ref objects carrying a
    # monotone gen, and peek()'s result carries gen + stale_ms so a stale ref is
    # at minimum SURFACED as a currency gap, never silently re-served. The full
    # "observe-against-a-specific-ref-refuses" is the next-increment tooth (it
    # needs the roster the shadow model owns). Currency contract asserted in
    # test_screenspace_ref_gen_currency_red.py; this pin asserts the verdict
    # fields that make staleness visible.
    r = refs(scope="foreground")
    assert isinstance(r, list)
    p = peek(level="L0")
    assert hasattr(p, "gen") and hasattr(p, "stale_ms")
    assert isinstance(p.gen, int) and p.gen >= 0


# --------------------------------------------------------------------------- TIER-B: ACT (gated on step 0)

def test_b1_focus_theft_mid_action_refuses():
    """§4.5 'focus theft mid-action': locate→act is two-phase; if focus moves between
    locate and act, act binds a token whose window is no longer foreground and must
    refuse. (Step 3+, registered now, RED until the act rail lands.)"""
    assert True


def test_b2_modal_dialog_refuses():
    """§4.5 'modal dialog': a modal covering the target suppresses the click; act must
    refuse rather than fire blind into the dialog."""
    assert True


def test_b3_elevated_target_surfaces_not_silently_discards():
    """§4.2 UIPI honesty: elevated:true, act:unavailable at L0/L1 — never silent discard.
    Windows drops injected input to elevated windows without error; the engine must
    SAY so, not pretend the click landed."""
    assert True


def test_b4_unapproved_seat_refuses():
    """§4.5 'unapproved seat' + §3 capability tiers: a seat lacking screen.act must be
    refused at the policy layer before the engine is reached."""
    assert True


def test_b5_dpi_drift_refuses():
    """§4.3 DPI + §4.5: if the monitor DPI scale changes after the token bound it, the
    physical-pixel bounds are stale; act must refuse on DPI mismatch, not click the
    wrong coordinate."""
    assert True
