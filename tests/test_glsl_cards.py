"""Slow pins for module test cards: every card renders on SwiftShader, is not flat, and has no NaN or Inf pixel.

SLOW, AND MARKED SO. Each test here launches headless Chrome on SwiftShader under the house GPU lock
(arsenal/shaders/headless.mjs, bursts under three minutes). Deselect with:  py -m pytest -m "not slow"

Two halves:
  * THE HOUSE CARDS. Every arsenal/web/glsl/cards/*.card against the real library. Until the first card lands this
    skips, saying so.
  * THE DRILLS. A check that has never been seen to fire is presumed broken (the house drill doctrine). So the fixture
    library renders its two example cards (which must pass) and three drills that must each fail for their own reason:
    drill-nan paints exactly half its pixels NaN, drill-flat is one grey, drill-broken does not compile.

When the machine cannot render (no node, or the GPU lock stays busy past the wait) the tests skip with the reason;
anything about a card itself is a failure.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from arsenal.shaders import cards as K

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")]

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "glsl_cards"
LOCK_WAIT_MIN = 5


def _render(names, out_root, **kw):
    report = K.render_cards(names, out_root=out_root, allow_tracked=True, lock_wait_min=LOCK_WAIT_MIN, quiet=True,
                            **kw)
    driver = report["driver"]
    if driver.get("error") and "lock" in str(driver["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {driver['error']}")
    assert not driver.get("refused"), f"the driver refused to render: {driver['refused']}"
    return {r["name"]: r for r in report["cards"]}


def _why(row) -> str:
    return (f"{row['name']}: compile_ok={row.get('compile_ok')} flat={row.get('flat')} nan={row.get('nan_pixels')} "
            f"error={row.get('error')} receipt={row.get('receipt')}")


def test_every_house_card_renders_not_flat_and_nan_free(tmp_path):
    names = K.list_cards()
    if not names:
        pytest.skip("no cards yet under arsenal/web/glsl/cards")
    rows = _render(names, tmp_path / "cards")
    bad = [_why(r) for r in rows.values() if not r["ok"]]
    assert not bad, "\n".join(bad)


@pytest.fixture(scope="module")
def drills(tmp_path_factory):
    """The fixture cards and drills, rendered once, in one run (one lock, one Chrome)."""
    cards_dir = tmp_path_factory.mktemp("cards")
    for src in list((FIX / "cards").glob("*.card")) + list((FIX / "drills").glob("*.card")):
        shutil.copyfile(src, cards_dir / src.name)
    return _render(K.list_cards(cards_dir), tmp_path_factory.mktemp("out"), cards_dir=cards_dir,
                   lib_dirs=[FIX / "lib"])


@pytest.mark.parametrize("name", ["core-shaping", "debug-views"])
def test_the_example_cards_pass(drills, name):
    row = drills[name]
    assert row["ok"] is True, _why(row)
    assert row["compile_ok"] is True and row["flat"] is False and row["nan_pixels"] == 0


def test_the_nan_drill_counts_exactly_its_nan_half(drills):
    row = drills["drill-nan"]
    assert row["compile_ok"] is True, _why(row)
    assert row["nan_pixels"] == 32 * 36, _why(row)      # 64x36, x < 32 is NaN: every one of them, and no other
    assert row["ok"] is False


def test_the_flat_drill_is_called_flat(drills):
    row = drills["drill-flat"]
    assert row["compile_ok"] is True and row["flat"] is True and row["nan_pixels"] == 0, _why(row)
    assert row["ok"] is False


def test_the_broken_drill_fails_to_compile_and_names_the_culprit(drills):
    row = drills["drill-broken"]
    assert row["compile_ok"] is False and row["ok"] is False, _why(row)
    assert "cardDrillUndeclared" in (row.get("error") or ""), _why(row)
