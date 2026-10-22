"""The predictive beat march's timing decision (beatsync.fire_time): audio time -> wall clock, minus the lead."""
from __future__ import annotations

import pytest

from arsenal.keylab.beatsync import fire_time

BLOCK = 512 / 44100          # one block period, ~11.6 ms


def test_a_beat_far_ahead_is_left_for_a_later_block():
    assert fire_time(t_beat=10.5, audio_t=10.0, wall_at_audio_t=100.0, wall_now=100.0, lead_s=0.015, block_s=BLOCK) is None


def test_a_beat_due_within_this_block_fires_at_beat_minus_lead():
    t = fire_time(t_beat=10.02, audio_t=10.0, wall_at_audio_t=100.0, wall_now=100.0, lead_s=0.015, block_s=BLOCK)
    assert t == pytest.approx(100.0 + 0.02 - 0.015)


def test_an_overdue_beat_fires_now_rather_than_never():
    t = fire_time(t_beat=10.0, audio_t=10.05, wall_at_audio_t=100.0, wall_now=100.001, lead_s=0.015, block_s=BLOCK)
    assert t is not None and t < 100.001


def test_a_bigger_lead_paints_earlier():
    early = fire_time(10.012, 10.0, 100.0, 100.0, 0.019, BLOCK)   # both paints fall inside this block
    late = fire_time(10.012, 10.0, 100.0, 100.0, 0.005, BLOCK)
    assert early < late and late - early == pytest.approx(0.014)
