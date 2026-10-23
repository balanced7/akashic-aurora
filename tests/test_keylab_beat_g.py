"""Pins for arsenal.keylab.beat_g, the grid tracker (2026-10-22, Daniel: "detect the grid not just the spaced out
notes"). Each pin is one claim the design makes, checked on exact-ground-truth audio from the bench. Short cases, so
the whole file runs in seconds. The pre-registered acceptance (research/reviewed/keylab-liberation-2026-10-22/
grid-tracker-preregistration-2026-10-22.md) is the full bench, not these pins."""
from __future__ import annotations

import numpy as np
import pytest

from arsenal.keylab import beatbench as BB
from arsenal.keylab import beat_g as G

RATE = 22050


def _run(case):
    return BB.score(case, BB.run_tracker(G.Tracker, case))


def test_contract_conforms():
    assert BB.check_tracker(G.Tracker) == []


def test_holds_the_beat_under_loud_offbeat_bass():
    """Tonight's TYNAN failure, in miniature: half-time drums with loud sub-bass on syncopated 16ths. The note-
    chaser locked a wrong grid steadily (171 for 128); the grid tracker must hold 128, ON the beat."""
    s = _run(BB.synth_case("ht128", 128, secs=20.0, rate=RATE, style="halftime_bass"))
    assert abs(s["est_bpm"] / 128 - 1) < 0.02
    assert s["F"] >= 0.9 and s["CMLt"] >= 0.8
    assert s["bpm_spread"] <= 0.02 and s["tempo_flips"] == 0


def test_offbeat_hats_do_not_pull_the_beat_onto_the_and():
    s = _run(BB.synth_case("off95", 95, secs=20.0, rate=RATE, style="offbeat"))
    assert abs(s["est_bpm"] / 95 - 1) < 0.02 and s["F"] >= 0.9


def test_triplet_swing_is_read_in_threes():
    s = _run(BB.synth_case("sw110", 110, secs=20.0, rate=RATE, swing=0.33))
    assert abs(s["est_bpm"] / 110 - 1) < 0.02 and s["F"] >= 0.9


def test_follows_a_real_tempo_step():
    """The other half of the two volatility settings: a sudden 128 -> 140 step must be FOLLOWED, not held. The
    bench's own case at the live sample rate. The change alarm is what makes it fast: measured relock 4.0 s with
    it and 7.0 s without (2026-10-22 ablation), so this pin guards the alarm path."""
    s = _run(BB.synth_case("step", 128, secs=40.0, rate=44100, step_at=20.0, step_to=140))
    assert s["relock_s"] is not None and s["relock_s"] <= 4.5
    assert abs(s["est_bpm"] / 140 - 1) < 0.02


def test_a_slow_beat_with_its_eighths_heard_is_not_doubled():
    """drums_70: kick and snare every 857 ms, hats on the 8ths. Every 8th line holds a note, so a 140 reading
    loses nothing there; what keeps 70 is that a beat usually has its subdivisions heard (pulse continuity and
    the level cost). Measured: 140 without the continuity term (2026-10-22 ablation)."""
    s = _run(BB.synth_case("d70", 70, secs=30.0, rate=44100))
    assert abs(s["est_bpm"] / 70 - 1) < 0.02 and s["F"] >= 0.9


def test_predicts_nothing_before_a_lock_and_ordered_beats_after():
    case = BB.synth_case("d120", 120, secs=8.0, rate=RATE)
    tr = G.Tracker(RATE, 512)
    assert tr.predict(0.0) == []
    for b in range(len(case.audio) // 512):
        tr.feed(case.audio[b * 512:(b + 1) * 512])
    ahead = tr.predict(tr.now)
    times = [p["t_beat"] for p in ahead]
    assert times and times[0] > tr.now and all(np.diff(times) > 0)
    assert abs(ahead[0]["bpm"] / 120 - 1) < 0.02


def test_a_musically_impossible_split_is_refused():
    """A kick each bar plus a click 1/11 of a bar later fits an 11-way grid exactly; music divides in twos and
    threes, so the grid is the bar and the click is an ornament."""
    tr = G.Tracker(RATE, 512)
    bar = 2.8
    t = np.sort(np.concatenate([np.arange(5) * bar, np.arange(5) * bar + bar / 11]))
    w = np.where(np.isclose((t / bar) % 1, 0), 1.0, 0.7)
    tau, _, _ = tr._lattice(t, w)
    assert abs(tau / bar - 1) < 0.02
