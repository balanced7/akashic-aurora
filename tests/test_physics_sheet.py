"""Physics-sheet pins (master-map M2b, static half): the census FINDS the truths we bled on,
and the render is deterministic so --check can gate staleness.

Anchors are bounds/flags this week's incidents made famous: BIFROST_STALE_MS (D2, added
2026-07-19), TOOL_SEND_TEXT_MAX=8000 (D3, the door that clipped deepseek's own verdict),
MAX_FILE_BYTES=120000 (hit 3x in one session, T067). If a refactor renames one, this pin
failing is the reminder that PHYSICS.md must follow. Run: py -m pytest tests/test_physics_sheet.py -q
"""
from scripts.gen_physics_sheet import render, scan


def _census():
    flags, bounds = scan()
    return flags, {name: val for name, val, _, _ in bounds}


def test_census_finds_the_collision_famous_truths():
    flags, bounds = _census()
    assert "BIFROST_STALE_MS" in flags                      # D2's gate threshold
    assert bounds.get("TOOL_SEND_TEXT_MAX") == 8000         # D3's raised door
    assert bounds.get("MAX_FILE_BYTES") == 120_000          # the T067 read cap
    assert bounds.get("DEFAULT_MAX_MESSAGE_BYTES") == 65_536  # packet MTU


def test_flags_carry_sites_and_render_is_deterministic():
    flags, bounds = scan()
    assert all(sites for sites in flags.values())           # every flag names a read site
    one = render(flags, bounds, sha="pin")
    two = render(*scan(), sha="pin")
    assert one == two                                       # same code -> same sheet
    assert "Status: current" in one                         # doc-currency law applies to organs too
