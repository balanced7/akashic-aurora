"""W2 pins -- the mode primitive (spec d622ac, section 3).

A mode is a surface's declaration of what it is PERMITTED and OBLIGATED to draw: three bounded
fields -- regions (named stance-slots), verbosity (per-region, from the shared severity vocabulary),
reach (directions + edge classes, including Navi's `confessed`). The anti-drift law made testable:
a mode may not issue a verdict about a region it never declared it would draw.

The severity and edge-class VOCABULARIES are provisional house grammar chosen here (one place,
Daniel to bless or redraw); these pins fix the SHAPE and the validation, not the particular words.
"""
from __future__ import annotations

import pytest

mode = pytest.importorskip("core.oneworld.mode")


def test_make_mode_builds_the_three_fields():
    m = mode.make_mode(
        regions=("fleet", "floor"),
        verbosity={"fleet": "normal", "floor": "loud"},
        reach={"directions": ("in", "out"), "edges": ("resolved", "confessed")},
    )
    assert set(m["regions"]) == {"fleet", "floor"}
    assert m["verbosity"]["floor"] == "loud"
    assert "confessed" in m["reach"]["edges"]


def test_verbosity_for_undeclared_region_is_refused():
    """You cannot set how loudly to draw a region you never declared you'd draw."""
    with pytest.raises(ValueError):
        mode.make_mode(regions=("fleet",), verbosity={"floor": "loud"})


def test_unknown_severity_level_is_refused():
    with pytest.raises(ValueError):
        mode.make_mode(regions=("fleet",), verbosity={"fleet": "DEAFENING"})


def test_unknown_edge_class_is_refused_but_confessed_is_accepted():
    with pytest.raises(ValueError):
        mode.make_mode(regions=(), reach={"edges": ("teleport",)})
    m = mode.make_mode(regions=(), reach={"edges": ("confessed",)})
    assert "confessed" in m["reach"]["edges"]


def test_permits_only_declared_regions():
    m = mode.make_mode(regions=("fleet",))
    assert mode.permits(m, "fleet") is True
    assert mode.permits(m, "floor") is False


def test_verdict_guard_refuses_an_undeclared_region():
    """The anti-drift law: a verdict about the whole requires the region be declared first."""
    m = mode.make_mode(regions=("fleet",))
    mode.verdict_guard(m, "fleet")  # no raise
    with pytest.raises(ValueError):
        mode.verdict_guard(m, "floor")


def test_empty_mode_is_valid_draws_nothing():
    m = mode.make_mode(regions=())
    assert m["regions"] == () and mode.permits(m, "anything") is False


def test_severity_vocabulary_is_ordered_and_single_sourced():
    """A renderer orders by this; it is the ONE place the words live (routes.py DEPTHS lesson)."""
    assert mode.SEVERITY.index("silent") < mode.SEVERITY.index("loud")
    assert "confessed" in mode.EDGE_CLASSES
