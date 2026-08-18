"""T341 acceptance pins — the operator re-entry render (assembly, not charge).

Pre-registered BEFORE implementation (M3: the RED commit carries these alone).

Laws under pin, each earned in the 2026-08-17 fence (Heimdall + Navi, decorrelated):
  ORDER LAW (Navi's attack, adopted): evidence -> open door -> your move.
    Never his-words -> his-debt -> his-silence.
  SELECTION LAW (Heimdall): select by TIME / LIVENESS / POINTER, never by meaning.
  CITATION LAW (house): any operator quote is verbatim WITH its eye address —
    a quote the corpus cannot resolve is a render bug, not a liberty.
  NO-GUILT LAW (Navi's refusal list): no counts, no ages on what waits on him;
    open loops OFF the default render.
  LEGEND LAW (Daniil, QUESTIONS.md 2026-07-29, the tension-map entry): the render
    declares its own bounds — what is shown, what is excluded, why.
  CAVEAT LAW (kimi, on the row): the render buys the assembly, not the charge,
    and must say so.

Run:  py -m pytest tests/test_t341_reentry_pins.py -v
"""

from __future__ import annotations

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ADDR_RE = re.compile(r"[0-9a-f-]{8,}:\d+")          # session:line eye address
AGE_RE = re.compile(r"\b\d+\s*(day|week|hour|minute)s?\b", re.I)


def _mod():
    try:
        from core import reentry
    except ImportError:
        pytest.fail("core.reentry missing — T341 not built (RED)")
    return reentry


@pytest.fixture(scope="module")
def built():
    return _mod().build_reentry()


@pytest.fixture(scope="module")
def rendered(built):
    return _mod().render_reentry(built)


# ---- P1: the builder exists and returns the contract shape -------------------
def test_p1_builder_contract(built):
    for key in ("since", "evidence", "open_door", "your_move", "legend", "caveat"):
        assert key in built, f"builder missing contract key: {key}"


# ---- P2: ORDER LAW — evidence before open door before your move --------------
def test_p2_section_order(rendered):
    i_ev = rendered.find("WHAT MOVED")
    i_od = rendered.find("OPEN DOOR")
    i_ym = rendered.find("YOUR MOVE")
    assert -1 not in (i_ev, i_od, i_ym), "a required section is missing from render"
    assert i_ev < i_od < i_ym, (
        "order law violated: must be evidence -> open door -> your move")


# ---- P3: open loops OFF by default, ON only by explicit flag -----------------
def test_p3_open_loops_default_absent(built, rendered):
    assert "open_loops" not in built, "open loops leaked into the default build"
    assert "OPEN LOOPS" not in rendered
    with_loops = _mod().build_reentry(show_open_loops=True)
    assert "open_loops" in with_loops, "flag did not surface open loops"


# ---- P4: CITATION LAW — his words carry their eye address --------------------
def test_p4_quotes_carry_addresses(built):
    last = built["since"].get("last_word")
    if last is not None:
        assert ADDR_RE.search(str(last.get("addr", ""))), (
            "last_word quoted without a resolvable eye address")
    door = built["open_door"]
    if door is not None:
        assert ADDR_RE.search(str(door.get("addr", ""))), (
            "open door quoted without a resolvable eye address")
        assert door.get("selected_by"), (
            "open door must disclose its mechanical selection rule")


# ---- P5: NO-GUILT LAW — your_move carries no counts, no ages -----------------
def test_p5_no_counts_no_ages(built, rendered):
    for item in built["your_move"]:
        for k in ("age", "days_waiting", "count", "waiting_since"):
            assert k not in item, f"guilt-ledger field '{k}' in your_move"
    ym = rendered[rendered.find("YOUR MOVE"):]
    assert not AGE_RE.search(ym), "an age crept into the YOUR MOVE section"
    assert "waiting" not in ym.lower(), "'waiting' framing in YOUR MOVE"


# ---- P6: LEGEND LAW — the render declares its own bounds ---------------------
def test_p6_legend_declares_bounds(built, rendered):
    leg = built["legend"]
    for k in ("shown", "excluded", "why"):
        assert leg.get(k), f"legend missing '{k}'"
    assert "shown:" in rendered.lower() and "excluded:" in rendered.lower()


# ---- P7: CAVEAT LAW — assembly, not charge, stated ---------------------------
def test_p7_caveat_present(built, rendered):
    assert "assembly, not the charge" in built["caveat"]
    assert "assembly, not the charge" in rendered


# ---- P8: VERBATIM LAW — a quoted word resolves byte-true in the corpus -------
def test_p8_quote_is_verbatim(built):
    door = built["open_door"]
    if door is None:
        pytest.skip("no open door selected in this corpus state")
    from core.eye import index as eye
    ev = eye.get_event(door["addr"])
    if ev is None:
        pytest.fail(f"open door addr {door['addr']} does not resolve in the eye")
    assert door["text"] in ev["text"], (
        "open door text is not verbatim from the corpus — paraphrase is the "
        "one forbidden operation (entry 8: a paraphrase cannot restore excitement)")
