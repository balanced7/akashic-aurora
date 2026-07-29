"""RED pin for kimi's T121 S-cut glyph renderer (Daniel's foundation go 2026-07-28).

kimi's lane: the GLYPH VOCABULARY + RENDER half of F3 (G4 product type). This is
the acceptance harness for the S-cut spec in research/in-flight/vr-build-order-kimi
-2026-07-28.md (S1) narrowed to glyphs on already-stamped artifacts, per claude's
conductor brief. Stamp-at-mint (the mint-choke half) is codex+claude's and is NOT
pinned here.

These probes are RED-FIRST: they assert the glyph render EXISTS in scripts/
bifrost_ui.py before it is built. RED today, GREEN after the render change.

The acceptance line, verbatim from kimi's round-3 truth-ground G11:
    "if a focus dial can dim the glyph, the cut failed."

Coordination boundary (codex owns the typed EpistemicView CONTRACT; kimi owns the
glyph VOCABULARY + render): the render maps
    currency   -> staleness glyph  fresh=● aging=◐ stale=○
    claim_kind -> text marker      inferred=[infer] guessed=[guess]
and degrades any missing stamped field to UNKNOWN (G4-amended: UNKNOWN is a
rendering state, never blank, never default-fresh).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "scripts" / "bifrost_ui.py"


def _src() -> str:
    return TARGET.read_text(encoding="utf-8")


# ---------------------------------------------------------------- vocabulary
def test_red_staleness_glyph_vocabulary_exists():
    """The three staleness glyphs (fresh/aging/stale) must be defined in the UI.
    Accept either the literal char or its \\uXXXX JS escape (the honest form in a
    JS string literal inside the Python template)."""
    src = _src()
    forms = {"fresh": ("●", "\\u25CF"), "aging": ("◐", "\\u25D0"),
             "stale": ("○", "\\u25CB")}
    for name, variants in forms.items():
        assert any(v in src for v in variants), (
            f"S-cut glyph MISSING: no {name} staleness glyph ({variants[0]!r} or "
            f"its escape {variants[1]!r}) in bifrost_ui.py. The S-cut vocabulary "
            f"(● fresh / ◐ aging / ○ stale) is not defined, so a stale artifact "
            f"renders identically to a fresh one. This is the RED state the cut "
            f"fixes.")


def test_red_infer_guess_markers_exist():
    """[infer] / [guess] text markers for INFER/GUESS claim kinds must exist."""
    src = _src()
    for marker in ("[infer]", "[guess]"):
        assert marker in src, (
            f"S-cut marker MISSING: {marker!r} not found in bifrost_ui.py. "
            f"INFER/GUESS content has no visible epistemic marker, so a guess "
            f"renders with the same confidence as a verified claim.")


def test_red_glyph_mapping_function_present():
    """A pure mapping (stamped fields -> {tier, glyph, marker}) must exist as one
    named function, so the derivation is auditable and reused by every surface."""
    src = _src()
    # accept any of a few conventional names for the single derivation function
    named = re.search(r"function\s+(epiGlyph|epistemicGlyph|stalenessGlyph|glyphFor)\s*\(", src)
    assert named, (
        "S-cut derivation MISSING: no single named glyph-mapping function "
        "(epiGlyph/epistemicGlyph/stalenessGlyph/glyphFor) in bifrost_ui.py. "
        "The tier derivation must live in ONE function (auditable, reused), not "
        "inline at the call site.")


# ---------------------------------------------------------------- G4-amended
def test_red_unknown_is_default_not_blank():
    """G4-amended: a message with NO stamped status must render UNKNOWN, never
    blank and never default-fresh. The derivation must have an explicit UNKNOWN
    branch reachable when stamped fields are absent."""
    src = _src()
    assert re.search(r"UNKNOWN|unknown", src), (
        "G4-amended VIOLATED: no UNKNOWN branch in the render path. A message "
        "missing stamped status would render blank or default-fresh. UNKNOWN-by-"
        "default is the difference between honesty as virtue and honesty as "
        "physics.")


# ---------------------------------------------------------------- G11 (the gate)
def test_red_glyph_is_structural_not_dial_suppressible():
    """G11 (kimi's acceptance line): the glyph must render as a STRUCTURAL sibling
    of the message header (beside .time), NOT via the content renderer
    (_msgRenderer) and NOT behind a focus/density/dial gate. A dial that can dim
    a truth glyph fails the cut."""
    src = _src()
    # The glyph element must exist as its own class/hook, not be folded into
    # _msgRenderer(content). Look for a dedicated epistemic/glyph element.
    structural = re.search(r"class=[\"'][^\"']*(epi|glyph|staleness)[^\"']*[\"']", src)
    assert structural, (
        "G11 VIOLATED (RED): no structural glyph element (a dedicated epi/glyph/"
        "staleness class) in the message render. If the glyph is only emitted by "
        "_msgRenderer(content) or is gated behind a focus/density dial, a dial "
        "can dim it and the cut has failed. Red pierces the blur is the "
        "invariant.")
    # Negative guard: the glyph must NOT be routed through the content renderer.
    routed_via_content = re.search(r"_msgRenderer[^;]*(epi|glyph|staleness)", src)
    assert not routed_via_content, (
        "G11 VIOLATED: the glyph is routed through _msgRenderer (the content "
        "path). Content can be re-rendered / dial-adjusted; the truth glyph must "
        "be a structural sibling that no dial reaches.")
