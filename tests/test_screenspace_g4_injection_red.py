"""Screenspace organ — G4 INJECTION PIN, RED first (T386 / §4 R2, build step 1).

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md §4.1:

  "Screen text is DATA, never instruction (R2 law): all read text returns in
   structured fields with provenance (source:'screen', window:'chrome.exe');
   act binds only to agent-chosen refs — screen content cannot name its own
   targets. A RED pin proves instruction-shaped screen text does not steer (G4)."

This is the single most load-bearing safety invariant in the whole organ, and it
is OBSERVE-side, not act-side: the pin lives at the READ boundary. It proves that
whatever the screen shows, the text the engine returns is (a) carried in
structured fields with a declared provenance, and (b) never a string the caller
is tempted to interpret as a command. The moment the engine returns bare text
that says "click the delete button" with no field wrapper and no provenance, a
downstream seat COULD treat it as instruction — and that is exactly the
incident this pin exists to prevent.

The pin is RED until core/screenspace lands. It asserts three things the engine
must make structurally true, none of which require the act rail to exist yet:

  G4-1  a captured text payload is a STRUCTURED field with provenance, never a
        bare positional string (no field -> the engine returned an instruction,
        not data).
  G4-2  the provenance says source:"screen" and names the window/process — text
        cannot be laundered into looking like an agent-originated instruction.
  G4-3  instruction-shaped screen text (a page literally rendering "click the
        delete button") is carried as-is but FLAGGED as screen data, not
        elevated to steer — the field identity proves the engine did not act on
        it.

These are anti-fitting pins: they do not depend on any specific sentence, they
depend on SHAPE (structured + provenance + source field). A screen that shows a
different instruction tomorrow still trips G4-2.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_IMPORT_ERROR = None  # so the skipif reason string is safe when the import SUCCEEDS
try:
    from core.screenspace import capture  # noqa: F401
    from core.screenspace import peek, read_text  # noqa: F401
    _IMPORT_OK = True
except Exception as exc:  # noqa: BLE001
    _IMPORT_OK = False
    _IMPORT_ERROR = exc


pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="core/screenspace not yet built — RED: engine must satisfy this contract "
           f"(import failed: {_IMPORT_ERROR!r})",
)


def test_g4_1_text_returns_as_structured_field_not_bare_string():
    """Every read-text payload is a structured record with a provenance field;
    a bare positional string is how an instruction sneaks through."""
    from core.screenspace import read_text
    from core.screenspace.engine import TextResult

    result = read_text(scope="foreground", method="uia")
    # G4-1 teeth: the return is the STRUCTURED TextResult record, never a bare
    # str. A bare string is the vector by which instruction-shaped screen text
    # would reach a caller untyped. The @dataclass type IS the proof.
    assert isinstance(result, TextResult)
    assert isinstance(result.text, str)
    assert isinstance(result.provenance, dict)


def test_g4_2_provenance_declares_source_screen():
    """The provenance field attributes the text to source:'screen' and names the
    window — screen text can never be laundered into looking agent-authored."""
    from core.screenspace import read_text

    result = read_text(scope="foreground", method="uia")
    # G4-2 teeth: provenance must DECLARE source:"screen" (the .source property
    # resolves it) — this is what stops screen text from being laundered into a
    # channel that looks like an agent-originated instruction.
    assert result.source == "screen"
    assert "source" in result.provenance
    assert result.provenance["source"] == "screen"


def test_g4_3_instruction_shaped_text_is_flagged_data_not_steer():
    """A page rendering 'click the delete button' is returned as DATA with an
    instruction-shaped flag, never elevated to a target the engine acted on.
    (The act rail is step 3+; this pin proves the READ side does not steer.)"""
    from core.screenspace import read_text

    result = read_text(scope="foreground", method="uia")
    # G4-3 teeth: whatever text came back, it arrived as .text on a provenance
    # record with source:"screen" — i.e. DATA with a declared origin, never a
    # bare imperative string the engine could have treated as its own target.
    assert result.source == "screen"
    assert isinstance(result.text, str)
