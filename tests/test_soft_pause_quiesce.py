"""RED pins — the SOFT PAUSE (Daniil's "pause nudge"), 2026-07-30.

THE GAP, stated as a table. Two axes: how hard we stop, and whether the process survives.

                  | stop NOW              | stop GRACEFULLY
    --------------+-----------------------+-----------------------
    and HOLD      | pause / halt   [have] | ***MISSING***
    and EXIT      | kill           [have] | drain          [have]

`pause()` is honored through `is_halted()`, which the runners pass as a MID-TURN interrupt
callback (bifrost_runner_deepseek.py:424, :921, :1028 -> outcome "abandoned"). So today a
pause ABANDONS in-flight work. `drain()` is graceful -- loop-top only, so the current
message finishes -- but it EXITS the process and costs a relaunch.

Daniil's ask: "a pause nudge alongside our pause drop all work." That is the empty cell:
finish the message you are on, then HOLD. Stay alive, stay on the roster, resume normally.

DESIGN CONSTRAINT, learned tonight: this must not become a THIRD invisible pause state.
The fleet already has two organs answering "is it paused" at different scopes (the global
control key and the per-runner stand-down port), and no way to tell from outside which one
someone meant -- the same two-worlds-sharing-a-name class cursor_grok found in roster
liveness. A soft pause that does not RENDER is that bug again, authored deliberately.

  P1  A soft pause does NOT make is_halted() true -- in-flight work must survive it.
      This is the whole point; if it fails, soft pause is just pause.
  P2  A soft pause IS visible to the loop-top gate, so a runner stops taking NEW work.
  P3  resume() clears BOTH kinds. A soft pause must never outlive a resume.
  P4  REGRESSION: a hard pause still halts exactly as before. Purely additive.
  P5  VISIBILITY: pause_status() reports WHICH kind is live, and format_pause_line()
      renders it. No new invisible state.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _online():
    from core.comm.bus import Bus
    return Bus("t-softpause").online


@pytest.fixture()
def ns(monkeypatch):
    n = f"t-soft-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", n)
    from core.comm import control
    control.resume()
    yield n
    control.resume()


def test_p1_soft_pause_does_not_halt(ns):
    """is_halted() is the MID-TURN interrupt. A soft pause must be invisible to it, or
    the current message is abandoned and we have built nothing new."""
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control
    assert control.pause(reason="wind down", by="daniil", soft=True) is True
    assert control.is_halted("deepseek") is False, (
        "a SOFT pause must not halt: is_halted() is passed as the mid-turn interrupt, so "
        "returning True here abandons the message the seat is holding")


def test_p2_soft_pause_stops_new_work(ns):
    """The loop-top gate. A soft-paused runner finishes what it has and takes nothing new."""
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control
    control.pause(reason="wind down", by="daniil", soft=True)
    assert control.is_frozen("deepseek") is True, (
        "a soft pause must stop NEW work at the loop top even though it does not halt "
        "mid-turn -- otherwise the nudge does nothing at all")


def test_p3_resume_clears_soft(ns):
    """A pause that survives its own resume is the RB-30 forever-freeze failure."""
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control
    control.pause(reason="wind down", by="daniil", soft=True)
    control.resume()
    assert control.is_frozen("deepseek") is False, "resume() must clear a SOFT pause"
    assert control.pause_status().get("paused") is False


def test_p4_hard_pause_unchanged(ns):
    """Regression guard: the new state is purely additive. A hard pause still halts."""
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control
    assert control.pause(reason="stop now", by="daniil") is True
    assert control.is_halted("deepseek") is True, "hard pause must still halt mid-turn"
    assert control.is_frozen("deepseek") is True, "hard pause must also stop new work"


def test_p5_soft_pause_is_visible(ns):
    """No new INVISIBLE state. Two organs already answer 'is it paused' at different
    scopes with no way to tell them apart; a third would be that bug authored on purpose."""
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control
    control.pause(reason="wind down", by="daniil", soft=True)
    st = control.pause_status()
    assert st.get("paused") is True, "a soft pause is still a pause to any status reader"
    assert st.get("soft") is True, "pause_status() must say WHICH kind is live"
    line = control.format_pause_line(st)
    assert line, "a live soft pause must render, never render empty"
    assert "soft" in line.lower() or "wind" in line.lower() or "graceful" in line.lower(), (
        f"the rendered line must distinguish a soft pause from a hard one. Got: {line!r}")
