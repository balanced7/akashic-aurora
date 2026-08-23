"""
T376 S5 -- the wedged-vs-thinking discriminator (pins, RED-first).

The reconciled design (fences/t376-metabolism/reconciliation.md, rule 1 +
V4) adopts half_a §2 VERBATIM as the wedged arm's decision rule: the
tiebreaker between "wedged" and "thinking" is the THREAD STACK, never the
timeout alone. py-spy gate REQUIRED before any kill; fail toward THINKING;
scope = polling runners only (Claude Code harness seats are mark-dead +
reroute, never recovered -- they need no discriminator).

The classifier is a pure function over the stack-dump text + the liveness
signals the doctor already computes (phase age, pulse age, beat age). No new
thresholds: the phase-age floor is the existing liveness.DEFAULT_WEDGE_S.

  P1  WEDGED: aged non-idle phase + dead pulse, AND the MainThread stack is
      blocked writing its own output (streams.py write/flush, the T019
      pipe family) -> kill/relaunch is on the table.
  P2  THINKING: MainThread above the model call, OR idle in a
      _process_one / producer-consumer wait with a live beat -- no matter
      how long the phase has aged -> do NOT relaunch.
  P3  INSTRUMENT-FAULT: beat fresh + pulse "dead" but the stack shows a
      healthy wait -- the two liveness organs disagree -> fix the organ,
      not the worker (fires LONG before phase_age reaches the wedge floor).
  P4  fail-direction: absent/empty/garbled stack evidence -> THINKING,
      never WEDGED (the stack is REQUIRED before a kill). A kill on no
      positive evidence of a blocked write is the forbidden false-WEDGED.

Run: py -m pytest tests/test_t376_s5_wedge_discriminator.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.wedge_discriminator import classify


# ---- the two live receipts from half_a §2.2, rendered as stack texts ----
# deepseek receipt: MainThread blocked in streams.py write, worker in flush.
_WEDGED_STACK = """\
Thread 0 (MainThread): depth sleeping (on_worker)
    core/foundation/streams.py:32 in write
    core/foundation/streams.py:41 in flush
    scripts/deepseek_chat.py:453 in _stream_turn
Thread 3 (_heartbeat): (idle)
"""

# kimi receipt: MainThread parked in _process_one's threading wait, beat live.
_THINKING_STACK = """\
Thread 0 (MainThread): depth sleeping (on_worker)
    core/comm/_process_one.py:87 in wait
Thread 3 (_heartbeat): (idle)
"""

# a model call in flight: MainThread above the model client, not in I/O.
_ABOVE_MODEL_STACK = """\
Thread 0 (MainThread): depth running
    scripts/deepseek_chat.py:300 in _completion
    openai/resources/chat.py:450 in create
"""


# ------------------------------------------------------------------ P1 wedged
def test_p1_wedged_mainthread_blocked_writing_its_own_output():
    v = classify(_WEDGED_STACK, phase_age_s=400.0, pulse_age_s=120.0,
                 beat_age_s=2.0)
    assert v == "wedged", (
        "MainThread blocked in streams.py write/flush is the T019 pipe family "
        f"-- genuine wedge, must NOT be labeled thinking; got {v!r}")


def test_p1_wedged_requires_the_aged_phase_and_dead_pulse_too():
    # Same blocked-write stack, but a FRESH pulse -> the runner is progressing,
    # so the stack alone must not kill. The four conditions are ANDed.
    v = classify(_WEDGED_STACK, phase_age_s=400.0, pulse_age_s=1.0,
                 beat_age_s=2.0)
    assert v != "wedged", (
        "a fresh pulse means progress; the stack alone must not label a "
        "progressing runner wedged")


# ------------------------------------------------------------------ P2 thinking
def test_p2_thinking_idle_wait_with_live_beat_is_not_wedged():
    v = classify(_THINKING_STACK, phase_age_s=1500.0, pulse_age_s=300.0,
                 beat_age_s=3.0)
    assert v == "thinking", (
        "the kimi receipt: MainThread parked in _process_one wait with a live "
        f"beat is a HEALTHY runner -- age alone is not a wedge; got {v!r}")


def test_p2_thinking_above_the_model_call_is_not_wedged():
    v = classify(_ABOVE_MODEL_STACK, phase_age_s=900.0, pulse_age_s=200.0,
                 beat_age_s=4.0)
    assert v == "thinking", (
        "a runner blocked in a model call is THINKING, not wedged, no matter "
        f"how long the phase has aged; got {v!r}")


# ------------------------------------------------------------------ P3 instrument fault
def test_p3_instrument_fault_fresh_beat_dead_pulse_healthy_wait():
    # This case fires BEFORE the phase reaches the wedge floor, so pass a
    # phase_age under DEFAULT_WEDGE_S but a dead pulse + fresh beat.
    v = classify(_THINKING_STACK, phase_age_s=10.0, pulse_age_s=60.0,
                 beat_age_s=1.0)
    assert v == "instrument_fault", (
        "fresh beat + dead pulse + healthy wait = the two liveness organs "
        f"disagreeing; fix the organ, not the worker; got {v!r}")


def test_p3_instrument_fault_is_the_sub_floor_form_thinking_is_the_over_floor():
    # The SAME healthy-wait stack (the kimi receipt) is instrument_fault while
    # the phase is still short, but becomes plain THINKING once the phase has
    # aged past the wedge floor -- "age alone is not a wedge" (half_a §2.3).
    # This boundary is the whole reason the two labels do not collapse.
    under = classify(_THINKING_STACK, phase_age_s=100.0, pulse_age_s=60.0,
                     beat_age_s=1.0)
    over = classify(_THINKING_STACK, phase_age_s=1500.0, pulse_age_s=300.0,
                    beat_age_s=3.0)
    assert under == "instrument_fault", (
        f"sub-floor healthy wait + dead pulse = instrument fault; got {under!r}")
    assert over == "thinking", (
        f"over-floor healthy wait + dead pulse = thinking (never kill); "
        f"got {over!r}")


# ------------------------------------------------------------------ P4 fail toward thinking
def test_p4_empty_stack_is_thinking_never_wedged():
    for empty in ("", None, "garbage not a stack at all"):
        v = classify(empty, phase_age_s=500.0, pulse_age_s=300.0,
                     beat_age_s=5.0)
        assert v == "thinking", (
            f"no positive evidence of a blocked write -> THINKING, never a "
            f"kill; classify({empty!r}) returned {v!r}")


def test_p4_unknown_threshold_inputs_do_not_kill():
    # A kill on missing/unknown numbers is the forbidden false-WEDGED.
    v = classify(_WEDGED_STACK, phase_age_s=None, pulse_age_s=None,
                 beat_age_s=None)
    assert v != "wedged", (
        "unknown phase/pulse/beat ages must fail toward thinking, never kill")
