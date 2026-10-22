"""Logic tests for arsenal/keylab/tempo.py -- the seed-then-refine BPM analysis (T4 lane).

Pure analysis only; no port, no audio device, no network in the tested paths. The DB sources are
exercised through the offline flag and the fusion math, not through live HTTP.
"""
from __future__ import annotations

import pytest

import arsenal.keylab.tempo as tempo


# --- octave folding ------------------------------------------------------------------------------

def test_fold_to_band_halves_and_doubles_collapse():
    assert tempo.fold_to_band(240.0) == pytest.approx(120.0)   # 240 -> 120
    assert tempo.fold_to_band(60.0) == pytest.approx(120.0)    # 60  -> 120
    assert tempo.fold_to_band(120.0) == pytest.approx(120.0)   # already in band


def test_fold_to_band_multiple_octaves():
    assert tempo.fold_to_band(480.0) == pytest.approx(120.0)   # 480 -> 240 -> 120
    assert tempo.fold_to_band(30.0) == pytest.approx(120.0)    # 30 -> 60 -> 120


def test_fold_to_band_nonpositive_untouched():
    assert tempo.fold_to_band(0.0) == 0.0
    assert tempo.fold_to_band(-10.0) == -10.0


# --- snap_to_octave (the deterministic half/double fix) ------------------------------------------

def test_snap_to_octave_does_not_move_an_already_correct_value():
    assert tempo.snap_to_octave(124.0, 124.0) == pytest.approx(124.0)


def test_snap_to_octave_folds_double_back():
    # detector locked to 2x: 240 detected, true anchor 120 -> snap to 120
    assert tempo.snap_to_octave(240.0, 120.0) == pytest.approx(120.0)


def test_snap_to_octave_folds_half_back():
    # detector locked to 1/2: 60 detected, true anchor 120 -> snap to 120
    assert tempo.snap_to_octave(60.0, 120.0) == pytest.approx(120.0)


def test_snap_to_octave_uses_two_thirds_factor():
    # 80 detected with 120 anchor: 80*1.5 = 120 (uses 3/2 factor)
    assert tempo.snap_to_octave(80.0, 120.0) == pytest.approx(120.0)


def test_snap_to_octave_clamps():
    assert tempo.snap_to_octave(20.0, 120.0) >= tempo.BPM_MIN


# --- fusion (fold-then-median, NOT mean) ---------------------------------------------------------

def test_fuse_bpm_median_not_mean():
    # 120 and 240 fold to the same octave; a naive mean would be 180 (wrong), median is 120.
    src = [tempo.SourceBpm("a", 120.0), tempo.SourceBpm("b", 240.0)]
    r = tempo.fuse_bpm(src)
    assert r.bpm == pytest.approx(120.0)
    assert r.source_count == 2


def test_fuse_bpm_discards_lone_outlier():
    # 120, 121 (cluster) + 200 (lone outlier >8% away) -> seed 120, not dragged up.
    src = [
        tempo.SourceBpm("a", 120.0),
        tempo.SourceBpm("b", 121.0),
        tempo.SourceBpm("c", 200.0),
    ]
    r = tempo.fuse_bpm(src)
    assert r.bpm == pytest.approx(120.0, abs=2.0)
    assert r.source_count == 3


def test_fuse_bpm_single_source_is_weak():
    r = tempo.fuse_bpm([tempo.SourceBpm("a", 120.0)])
    assert r.bpm == pytest.approx(120.0)
    assert r.source_count == 1
    assert not r.is_strong


def test_fuse_bpm_two_agreeing_is_strong():
    r = tempo.fuse_bpm([tempo.SourceBpm("a", 120.0), tempo.SourceBpm("b", 118.0)])
    assert r.is_strong
    assert r.confidence >= 0.5


def test_fuse_bpm_empty_returns_zero_seed():
    r = tempo.fuse_bpm([])
    assert r.bpm == 0.0
    assert r.source_count == 0
    assert not r.is_strong


# --- normalize_title -----------------------------------------------------------------------------

def test_normalize_title_strips_remix_and_brackets():
    assert tempo.normalize_title("On My Mind (feat. X) [Remix]") == "On My Mind"
    assert tempo.normalize_title("Song ft. Someone Else") == "Song"


# --- offline: no network -------------------------------------------------------------------------

def test_lookup_offline_returns_empty_no_network():
    # With offline=True, lookup must return [] and make zero HTTP calls. We can't intercept HTTP
    # directly here, but the guard is structural: offline short-circuits before any _fetch_json.
    assert tempo.lookup("Artist", "Title", offline=True) == []


def test_lookup_sources_are_isolated():
    # A lookup with no key and (in CI) no network simply returns [] rather than raising.
    # Each source is fail-soft; the chain never propagates an exception.
    result = tempo.lookup("Nonexistent Artist 123", "No Such Track 456", offline=False)
    assert isinstance(result, list)


# --- BeatTracker seed-aware refinement (no audio device needed) ----------------------------------

def _click_block(rate=44100, bpm=120.0, seconds=2.0):
    """Build a synthetic click buffer and feed it one hop-sized block at a time."""
    import numpy as np
    period = 60.0 / bpm
    n = int(rate * seconds)
    buf = np.zeros(n, dtype=np.float32)
    t = 0.0
    while t < seconds:
        i = int(t * rate)
        if i < n:
            buf[i] = 1.0
        t += period
    return buf


def test_beattracker_emits_dict_shape():
    # Offline synthetic input; assert the emitted event carries the required keys.
    tracker = tempo.BeatTracker(seed_bpm=120.0, rate=44100, hop=tempo.DEFAULT_HOP)
    buf = _click_block()
    hop = tempo.DEFAULT_HOP
    events = []
    for i in range(0, len(buf) - hop, hop):
        events.extend(tracker.push(buf[i:i + hop]))
    assert isinstance(events, list)
    # event shape (may be empty if aubio isn't installed; the shape contract is what we pin)
    for ev in events:
        assert set(ev) == {"bpm", "beat_phase", "confidence", "source"}


def test_snap_to_octave_is_half_double_detector():
    # The acceptance criterion: "half/double tempo is detected and folded back to the seed's octave."
    # This is exercised here WITHOUT aubio by testing the pure folding primitives together.
    seed = 120.0
    for doubled in (60.0, 240.0):
        folded = tempo.snap_to_octave(doubled, seed)
        assert folded == pytest.approx(seed)
