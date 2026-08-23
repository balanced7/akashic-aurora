"""
T381 M1 -- the map's first render: pins, RED-first.

The reconciled laws under test (fences/c-map-design/reconciliation.md):
  P1  TRUST BEFORE BEAUTY: build_map REFUSES to render without its stamp
      ingredients (generation ts, HEAD sha, source cursors) -- an unstamped
      map is not a degraded map, it is a refused map. The stamp block is in
      the output, visibly.
  P2  RED TAKES THE BANNER: any page-grade renders the alarm banner ABOVE
      every other element; zero page-grades renders no banner at all.
  P3  THE DECK IS THE TERRAIN: landmarks (tasks/fences/bets) render from the
      data fold; OVERDUE bets appear in the unscrollable kernel.
  P4  PURE FOLD: build_map(data) is deterministic -- same dict, identical
      html; it takes DATA, never a client or a path.

Run: py -m pytest tests/test_t381_map_m1.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.map_generator import build_map, MapRefusal  # noqa: E402


def _data(page_grades=0):
    return {
        "generated_ts": "2026-08-23T13:00:00+00:00",
        "head_sha": "abc1234",
        "cursors": {"ledger_seq": 381, "forecasts": 5,
                    "newest_event": "1787490000000-0"},
        "page_grades": page_grades,
        "dashboard_count": 17,
        "overdue": [{"id": "F009", "registered_by": "example"}],
        "landmarks": [
            {"id": "T381", "kind": "task", "status": "claimed", "by": "claude",
             "title": "Map v1"},
            {"id": "c-map-design", "kind": "fence", "status": "sealed",
             "title": "the map fence"},
            {"id": "F005", "kind": "bet", "status": "OPEN", "by": "claude",
             "title": "return-visit bet"},
        ],
        "badges": [{"family": "inbox:claude", "count": 123,
                    "last_ts": "2026-08-23T12:59:00+00:00"}],
        "trails": {"routes": 12, "last24h": 7},
    }


def test_p1_stamp_block_or_refusal():
    html = build_map(_data())
    for needle in ("abc1234", "2026-08-23T13:00:00+00:00", "ledger_seq",
                   "1787490000000-0"):
        assert needle in html, f"stamp ingredient {needle!r} missing from render"
    for missing in ("head_sha", "generated_ts", "cursors"):
        broken = _data()
        broken.pop(missing, None)
        with pytest.raises(MapRefusal):
            build_map(broken)


def test_p2_red_takes_the_banner():
    quiet = build_map(_data(page_grades=0))
    assert "map-alarm" not in quiet, "no page-grades must mean no banner"
    loud = build_map(_data(page_grades=2))
    assert "map-alarm" in loud
    assert loud.index("map-alarm") < loud.index("T381"), (
        "the alarm banner must render ABOVE every landmark")


def test_p3_deck_terrain_and_overdue_kernel():
    html = build_map(_data())
    for lid in ("T381", "c-map-design", "F005"):
        assert lid in html, f"landmark {lid} missing from the terrain"
    assert "F009" in html, "OVERDUE bets must surface in the kernel"
    assert "OVERDUE" in html


def test_p4_pure_fold_determinism():
    a = build_map(_data())
    b = build_map(_data())
    assert a == b, "same data must render byte-identical html (pure fold)"
