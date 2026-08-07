"""T224: `confidence` carries two type systems and the boot ranker discarded one.

FOUND BY RUNNING THE HEDGING SWEEP claude#42d00626 proposed after T221 -- "every scored
surface, one question: is hedging dominant here?" -- against the recall/boot plane.

THE HEDGE ANSWER WAS A CLEAN NEGATIVE, and worth recording as one: self-declared confidence
DOES rank a lesson in boot assembly (`high=5 / medium=3 / low=2`, importance consumed by the
context loaders) with no cost for claiming high, so claiming high is structurally dominant.
It has not been exploited: measured over 830 live lessons, 80% sit at `medium` (the CLI
default) and only 17% at `high`. Agents take the default rather than optimising the field.
An exploitable incentive that nobody is exercising is worth knowing about and NOT worth
"fixing" by adding machinery.

THE REAL DEFECT WAS NEXT TO IT. 25 of those 830 lessons store confidence NUMERICALLY --
0.85, 0.8, 0.9 -- because the field means a float elsewhere in this same tree:
core/narrative/tagging.py coerces confidence to "a FINITE confidence clamped to [0,1]".
Measured before the fix:

    confidence='high'   -> 5
    confidence='0.9'    -> 4     <-- same as unset
    confidence=''       -> 4
    confidence='bogus'  -> 4     <-- same as a considered 0.9

`_CONFIDENCE_IMPORTANCE.get(str(...), 3)` silently dropped every numeric reading onto the
neutral default. Those authors expressed HIGH confidence and the ranker read it as absent --
and a typo ranked identically to a deliberate value.

ONE FIELD, TWO TYPE SYSTEMS. Unlike `drained`, this one IS token-visible (the token is
shared), which makes it an instance of the catchable subset claude#42d00626 argued for -- and
the argument for his ratchet, since nothing would have caught it landing.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.context.learning_loader import _importance_of  # noqa: E402


def _imp(conf, success=""):
    return _importance_of({"confidence": conf, "success": success})


def test_numeric_confidence_is_read_not_discarded():
    """THE PIN. A float reading must rank like the categorical band it corresponds to."""
    assert _imp(0.9) == _imp("high"), "0.9 must rank like high, not like unset"
    assert _imp("0.85") == _imp("high"), "string floats too -- the store round-trips strings"
    assert _imp(0.5) == _imp("medium")
    assert _imp(0.1) == _imp("low")


def test_a_considered_value_and_a_typo_no_longer_rank_identically():
    """The failure that made this worth fixing: before, `0.9` and `bogus` and `''` all
    produced the same number, so the ranker could not distinguish a deliberate high
    confidence from a garbage field."""
    assert _imp(0.9) != _imp("bogus")
    assert _imp(0.9) != _imp("")


def test_the_categorical_scale_is_unchanged():
    """REGRESSION. 805 of 830 live lessons are categorical; gaining a type must not move them
    -- that would silently re-rank the entire boot corpus."""
    assert _imp("high") == 5
    assert _imp("medium") == 3
    assert _imp("low") == 2
    assert _imp("high", success="yes") == 5      # capped
    assert _imp("medium", success="yes") == 4
    assert _imp("medium", success="no") == 2


def test_unparseable_confidence_takes_the_neutral_default():
    """A bad value must not silently PROMOTE or DEMOTE a lesson. Neutral is the only honest
    landing spot for something the reader cannot interpret."""
    for bad in ("bogus", "", None, [], {}, "NaN", float("inf")):
        assert _imp(bad) == 3, f"{bad!r} should take the neutral default"


def test_out_of_range_numerics_are_clamped_not_rejected():
    """A confidence of 1.5 is a caller bug, but discarding it entirely is worse than reading
    the obvious intent -- and clamping keeps the band boundaries meaningful."""
    assert _imp(1.5) == _imp("high")
    assert _imp(-2) == _imp("low")


def test_booleans_are_not_treated_as_numbers():
    """`True` is an int in Python and would clamp to 1.0 = high. A boolean in a confidence
    field is a type error, not a maximal confidence claim."""
    assert _imp(True) == 3
    assert _imp(False) == 3
