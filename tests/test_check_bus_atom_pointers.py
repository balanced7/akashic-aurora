"""Pins for the bus-side library lint (check_bus_atom_pointers, Daniel-gated 2026-07-24).

Hermetic by design: every pin drives the PURE classifier -- no Redis, no tempdir,
no live bus (tonight's own tempdir_sidecar_test_selfpoison lesson applied at birth).
The founding LIVE photograph (claude's round-2 leak flagged) is a run receipt in the
build commit, not a pin.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.checkers.check_bus_atom_pointers import THRESHOLD, classify_body

_DOC = "# Reconciliation\n## Converged\n## Refused\n" + ("position word " * 200)
assert len(_DOC) >= THRESHOLD, "fixture must clear the length bar"


def test_long_design_body_without_pointer_is_flagged():
    reason = classify_body(_DOC, "handoff")
    assert reason and "NO durable pointer" in reason


def test_atom_id_pointer_suppresses():
    assert classify_body(_DOC + "\nfiled: art_20260724_some-slug_9ebbcf", "handoff") is None


def test_note_id_pointer_suppresses():
    assert classify_body(_DOC + "\nfiled: ADR_0724000024_a7e00d70", "reply") is None


def test_library_path_pointer_suppresses():
    assert classify_body(
        _DOC + "\nsee docs/library/design/20260724_x_9ebbcf.md", "handoff") is None


def test_short_body_is_clean():
    assert classify_body("ACK -- read the atom, counters tomorrow.", "reply") is None


def test_trace_kind_never_flagged():
    assert classify_body(_DOC, "trace") is None


def test_long_unstructured_prose_is_clean():
    prose = ("we talked for a while about the library and the night went on " * 40)
    assert len(prose) >= THRESHOLD
    assert classify_body(prose, "chat") is None


def test_wire_escaped_newlines_still_classify():
    """The founding-run find: the bus stores newlines as literal backslash-n; the
    guard must see headings/bullets through the escaping or it is blind by design."""
    wire = _DOC.replace("\n", "\\n")
    assert "\n" not in wire
    reason = classify_body(wire, "handoff")
    assert reason and "NO durable pointer" in reason
