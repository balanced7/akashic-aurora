"""PRE-REGISTERED ACCEPTANCE (T170) -- silence must be unrepresentable at a boundary.

Six defects fixed on 2026-08-04 were one defect in six costumes: a boundary that failed and said
nothing (T147 T149 T150 T151 T167 T169). Each subsystem had its own answer to "what happened" --
an int that swallows, a mid plus a side channel contradicted by stdout, a dict annotated `-> bool`,
a str-or-empty, a silent downgrade -- and NONE of them could express PARTIAL, which is why partial
work vanished.

WHY A TYPE AND NOT A GUARD. The obvious check -- scan for `except: return <falsy>` -- measures 1559
silent handlers in this tree, or 523 narrowed to ones manufacturing a falsy verdict. Freezing
either is theater. Narrowing further needs a hand-list of "action verbs", which would drift exactly
as `_CONTAINERS` drifted past `match` in T146. So the rule lives in the constructor instead: a
failed BoundaryOutcome with no reason cannot be constructed. Silence is not a state you can reach.

  O1  a FAILED outcome with no reason cannot be built
  O2  a PARTIAL outcome with no reason cannot be built    (the state five dialects lacked)
  O3  a successful outcome needs no reason                (the common path stays cheap)
  4  PARTIAL is FALSY                                     (ignoring partiality must not read as success)
  O5  caught() records the exception WITHOUT re-raising   (fail-open, never silent -- the T167 shape)
  O6  every outcome renders one way                       (one vocabulary, one surface)

Run: py -m pytest tests/test_t170_outcome_cannot_be_silent.py -q
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.outcome import BoundaryOutcome  # noqa: E402


def test_o1_a_failure_without_a_reason_cannot_be_built():
    with pytest.raises(ValueError, match="why"):
        BoundaryOutcome(ok=False)
    with pytest.raises(ValueError):
        BoundaryOutcome(ok=False, why="   ")
    assert BoundaryOutcome.failed("spawn refused: lock held").why


def test_o2_a_partial_without_a_reason_cannot_be_built():
    """The state that did not exist. deepseek-red produced 109KB of correct analysis and returned
    "" because there was no way to say 'I did some of it'."""
    with pytest.raises(ValueError):
        BoundaryOutcome(ok=True, partial=True)
    o = BoundaryOutcome.partially("budget exhausted after 30 tool rounds", ref="msg-1")
    assert o.partial and o.why and o.ref == "msg-1"


def test_o3_success_needs_no_reason():
    o = BoundaryOutcome.done(ref="1785818229175-0")
    assert o.ok and o.why == "" and bool(o) is True


def test_o4_partial_is_falsy():
    """A caller writing `if send(...)` must not read a partial as a success -- that is precisely
    how a collapsed send rendered as delivered (T149)."""
    assert not BoundaryOutcome.partially("only 3 of 5 fragments landed")
    assert not BoundaryOutcome.failed("recipient unknown")
    assert BoundaryOutcome.done()


def test_o5_caught_records_the_exception_without_reraising():
    """The T167 shape exactly: consume_rearms must keep failing open, but never silently."""
    try:
        raise TypeError("_spawn_listener() takes 1 positional argument but 2 were given")
    except TypeError as e:
        o = BoundaryOutcome.caught(e, where="spawn_listener", ref="cdfb9126")
    assert o.ok is False
    assert "TypeError" in o.why and "2 were given" in o.why
    assert o.ref == "cdfb9126"
    assert o.detail.get("exception") == "TypeError"


def test_o6_one_render_for_every_surface():
    assert BoundaryOutcome.done(ref="abc").line().startswith("OK")
    assert "FAILED" in BoundaryOutcome.failed("no live seat", ref="x").line()
    p = BoundaryOutcome.partially("budget exhausted", ref="m1").line()
    assert p.startswith("PARTIAL") and "budget exhausted" in p and "ref=m1" in p


def test_o7_an_outcome_drops_into_a_bool_expecting_callsite_unchanged():
    """MIGRATION IS INCREMENTAL, which is why this is adoptable at all.

    consume_rearms does `ok = bool(spawn_fn(sid))` and treats falsy as "leave the trigger for the
    next tick". A spawn_fn upgraded to return BoundaryOutcome needs NO change at that callsite -- __bool__
    already means "fully happened" -- and the caller gains a REASON it can print. That is the T167
    fix falling out of the type instead of being hand-written per boundary.
    """
    def spawn_ok(sid):
        return BoundaryOutcome.done(ref=f"pid-{sid}")

    def spawn_broken(sid):
        try:
            raise TypeError("_spawn_listener() takes 1 positional argument but 2 were given")
        except TypeError as e:
            return BoundaryOutcome.caught(e, where="spawn_listener", ref=sid)

    # the EXISTING consumer logic, verbatim in shape
    assert bool(spawn_ok("cdfb9126")) is True
    bad = spawn_broken("cdfb9126")
    assert bool(bad) is False                      # trigger correctly left for the next tick
    assert "TypeError" in bad.line()               # ...and the silence is gone, for free
