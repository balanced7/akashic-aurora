"""MAP.md v0 pins (T096-M0): the census matrix is grounded, honest about gaps, deterministic.

Run: py -m pytest tests/test_master_map.py -q
"""
from scripts.gen_master_map import build, render


def test_matrix_contains_known_organs_with_truthful_columns():
    rows = build()
    comm = {r["module"]: r for r in rows.get("core/comm", ())}
    assert "bus.py" in comm and comm["bus.py"]["doc"] != "(no docstring)"
    assert "packet_spec.py" in comm
    assert not comm["packet_spec.py"]["gap"]          # pinned + papered this very week
    assert "BIFROST_STALE_MS" not in comm["bus.py"]["flags"]  # D2 kept the flag OUT of bus.py


def test_gap_column_exists_and_render_is_deterministic():
    rows = build()
    text = render(rows)
    assert "## GAP queue" in text                     # the honest backfill queue renders
    assert "Status: current" in text                  # doc-currency law
    assert text == render(build())                    # same code -> same map
