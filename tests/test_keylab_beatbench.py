"""Pins for arsenal.keylab.beatbench: the ruler must be right before anything is measured with it.
Oracle trackers whose scores are known in advance prove each metric; the synthetic cases prove the ground truth."""
from __future__ import annotations

import numpy as np
import pytest

from arsenal.keylab import beatbench as BB

RATE, HOP = 22050, 512


class Oracle:
    """Knows the answer: announces each true beat `lead` seconds early, predicts the next one exactly (+ err)."""

    def __init__(self, beats, lead=0.2, shift=0.0, scale=1.0, pred_err=0.0):
        self.beats, self.lead, self.shift, self.scale, self.pred_err = beats, lead, shift, scale, pred_err

    def factory(self, rate, hop, seed_bpm=None):
        o = self
        est = np.arange(o.beats[0] + o.shift, o.beats[-1] + 1e-9, (o.beats[1] - o.beats[0]) * o.scale)

        class T:
            def __init__(self):
                self.now, self.done = 0.0, 0

            def feed(self, block):
                self.now += len(block) / rate
                out = []
                while self.done < len(est) and est[self.done] <= self.now + o.lead:
                    out.append({"t_beat": float(est[self.done]), "bpm": 60.0 / (est[1] - est[0]), "phase": 0.0,
                                "confidence": 1.0, "is_downbeat": None})
                    self.done += 1
                return out

            def predict(self, now):
                nxt = est[est > now]
                return [{"t_beat": float(nxt[0] + o.pred_err), "bpm": 60.0 / (est[1] - est[0]), "phase": 0.0,
                         "confidence": 1.0}] if len(nxt) else []
        return T()


@pytest.fixture(scope="module")
def case120():
    return BB.synth_case("t120", 120, secs=20.0, rate=RATE)


def test_synthetic_beats_are_exact(case120):
    assert np.allclose(np.diff(case120.beats), 0.5)
    assert case120.beats[0] == pytest.approx(0.5)
    assert case120.audio.dtype == np.float32 and len(case120.audio) == 20 * RATE


def test_ramp_ground_truth_speeds_up():
    c = BB.synth_case("ramp", 100, secs=20.0, rate=RATE, ramp_to=130)
    ibi = np.diff(c.beats)
    assert ibi[0] > ibi[-1] and 60 / ibi[0] == pytest.approx(100, rel=0.02) and 60 / ibi[-1] == pytest.approx(130, rel=0.03)


def test_perfect_oracle_scores_perfectly(case120):
    o = Oracle(case120.beats, lead=0.2)
    row = BB.score(case120, BB.run_tracker(o.factory, case120, HOP))
    assert row["F"] == 1.0 and row["CMLt"] == pytest.approx(1.0, abs=0.06) and row["Acc1"] is True
    assert row["lock_s"] == pytest.approx(0.5)
    assert row["pred_hit"] == 1.0 and row["pred_err_ms"] == pytest.approx(0.0, abs=1.0)
    assert row["lead_ms"] > 100, "announced ~200 ms ahead"


def test_a_100ms_late_tracker_misses_every_beat(case120):
    o = Oracle(case120.beats, shift=0.1)
    row = BB.score(case120, BB.run_tracker(o.factory, case120, HOP))
    assert row["F"] == 0.0 and row["Acc1"] is True, "right tempo, wrong phase: F punishes it, Acc1 does not"


def test_half_tempo_passes_acc2_and_aml_but_not_acc1_or_cml(case120):
    o = Oracle(case120.beats, scale=2.0)
    row = BB.score(case120, BB.run_tracker(o.factory, case120, HOP))
    assert row["Acc1"] is False and row["Acc2"] is True
    assert row["AMLt"] > 0.9 and row["CMLt"] < 0.1
    assert row["octave_err"] == 1.0


def test_offbeat_tracker_is_allowed_by_aml_only(case120):
    o = Oracle(case120.beats, shift=0.25)
    row = BB.score(case120, BB.run_tracker(o.factory, case120, HOP))
    assert row["CMLt"] < 0.1 and row["AMLt"] > 0.9


def test_prediction_error_is_measured_in_ms(case120):
    o = Oracle(case120.beats, pred_err=0.05)
    row = BB.score(case120, BB.run_tracker(o.factory, case120, HOP))
    assert row["pred_err_ms"] == pytest.approx(50.0, abs=1.0) and row["pred_hit"] == 0.0


def test_dedupe_keeps_the_last_word_on_a_beat():
    evs = [{"t_beat": 1.00, "_at": 0.7}, {"t_beat": 1.02, "_at": 0.9}, {"t_beat": 1.5, "_at": 1.2}]
    out = BB.dedupe(evs)
    assert [e["t_beat"] for e in out] == [1.02, 1.5]


def test_f_measure_edge_cases():
    ref = np.array([1.0, 2.0, 3.0])
    assert BB.f_measure(ref, ref) == 1.0
    assert BB.f_measure(np.array([]), ref) == 0.0
    assert BB.f_measure(np.array([1.0, 1.01, 1.02]), ref) == pytest.approx(2 * (1 / 3) * (1 / 3) / (2 / 3))


def test_contract_check_accepts_a_conforming_tracker_and_names_a_broken_one(case120):
    # the oracle knows beats past the 10 s contract case, so it never runs out of future to predict (round 2's
    # contract: predict() must not come back empty after lock)
    good = Oracle(BB.beat_times(120, 12.0, 0.5), lead=0.1).factory
    assert BB.check_tracker(good, rate=RATE) == []

    class Broken:
        def __init__(self, rate, hop, seed_bpm=None):
            pass

        def feed(self, block):
            return [{"t_beat": 1.0, "confidence": 2.0}]

    problems = BB.check_tracker(Broken, rate=RATE)
    assert any("missing" in p for p in problems) and any("confidence" in p for p in problems)


def test_unavailable_tracker_is_a_skipped_row_not_a_crash(case120):
    class Missing:
        def __init__(self, rate, hop, seed_bpm=None):
            raise ImportError("no such library")

    BB.register("missing_for_test", Missing, note="test")
    rep = BB.bench([case120], ["missing_for_test"], hop=HOP, log=lambda s: None)
    assert rep["trackers"]["missing_for_test"]["unavailable"] is True


# --- the drift ruler (Daniel 2026-10-22: hold the grid, don't chase the notes) ---------------------------------

def test_a_steady_tracker_has_no_drift():
    beats = [{"t_beat": 5.0 + i * 0.5, "bpm": 120.0} for i in range(30)]
    d = BB.drift(beats)
    assert d == {"bpm_spread": 0.0, "tempo_flips": 0, "bpm_missing": 0}


def test_a_wobbling_tracker_is_caught():
    bpms = [140, 124, 140, 83, 167, 125, 126, 159, 124, 130]          # tonight's TYNAN log, in miniature
    beats = [{"t_beat": 6.0 + i * 0.45, "bpm": float(b)} for i, b in enumerate(bpms)]
    d = BB.drift(beats)
    assert d["tempo_flips"] >= 6 and d["bpm_spread"] > 0.3


def test_halftime_bass_ground_truth_keeps_the_bass_off_the_beat():
    assert not set(BB.SYNC_BASS_16THS) & {0, 4, 8, 12}, "the bass must never sit on a beat"
    c = BB.synth_case("hb", 140, secs=12.0, rate=22050, style="halftime_bass")
    assert np.allclose(np.diff(c.beats), 60 / 140) and c.meta["style"] == "halftime_bass"


def test_drift_suite_is_constant_tempo():
    for c in BB.drift_suite(rate=22050, secs=12.0):
        assert c.meta["ramp_to"] is None and np.allclose(np.diff(c.beats), np.diff(c.beats)[0])


def test_step_ground_truth_changes_tempo_once_at_the_step():
    b = BB.beat_times(128, 30.0, 0.5, step_at=15.0, step_to=140)
    ibi = np.diff(b)
    assert np.allclose(ibi[b[1:] < 15.0], 60 / 128) and np.allclose(ibi[b[:-1] >= 15.0], 60 / 140)


def test_relock_is_measured_from_the_step():
    c = BB.synth_case("st", 120, secs=24.0, rate=22050, step_at=12.0, step_to=140)
    est = c.beats

    class Exact:
        def __init__(self, rate, hop, seed_bpm=None):
            self.now, self.i = 0.0, 0

        def feed(self, block):
            self.now += len(block) / c.rate
            out = []
            while self.i < len(est) and est[self.i] <= self.now:
                out.append({"t_beat": float(est[self.i]), "bpm": 120.0, "phase": 0.0, "confidence": 1.0})
                self.i += 1
            return out

    row = BB.score(c, BB.run_tracker(Exact, c, 512))
    assert row["relock_s"] == pytest.approx(0.0, abs=0.5)
    assert row["F"] >= 0.98          # the last beat can fall after the final audio block
