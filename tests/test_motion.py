"""motion pins: the temporal twin of the pixel floors must be DERIVED from the segment table,
must say UNKNOWN rather than a fake zero when there is nothing to measure, and must state the
sampling stride that bounds what it could possibly have seen.

Synthetic manifests only -- a real storyboard is evidence, not a fixture, so re-rendering a take
never breaks the suite. Every number below is computed by hand from the segment table.
"""
from __future__ import annotations

import json

import pytest

from arsenal import motion as M


def _seg(kind, start_s, end_s, peak=0.01):
    return {"kind": kind, "start_s": start_s, "end_s": end_s,
            "duration_ms": int(round((end_s - start_s) * 1000)),
            "peak_score": peak, "frames": int(round((end_s - start_s) * 2)) + 1}


def _manifest(segments, *, fps=2.0):
    return {
        "api": "arsenal.storyboard/v0", "source": "synthetic.mp4",
        "sampling": {"fps": fps, "width": 320, "low": 0.02, "high": 0.08,
                     "settle_frames": 3, "max_hamming": 6},
        "frames_examined": 60, "scores": [], "segments": segments,
        "transitions": sum(1 for s in segments if s["kind"] == "transition"),
        "settled": sum(1 for s in segments if s["kind"] == "settled"),
    }


def _six_per_min():
    """3 transitions in 30 s, with settled runs of 5.0 / 4.0 / 8.5 / 8.0 s."""
    return _manifest([
        _seg("settled", 0.0, 5.0),
        _seg("transition", 5.0, 6.0, peak=0.5),
        _seg("settled", 6.0, 10.0),
        _seg("transition", 10.0, 11.5, peak=0.3),
        _seg("settled", 11.5, 20.0),
        _seg("transition", 20.0, 22.0, peak=0.8),
        _seg("settled", 22.0, 30.0),
    ])


def test_a_take_that_never_moves_reads_still():
    p = M.profile(_manifest([_seg("settled", 0.0, 20.0)]))
    assert p["duration_s"] == 20.0
    assert p["transitions"] == 0
    assert p["transitions_per_min"] == 0.0
    assert p["transition_fraction"] == 0.0
    assert p["median_transition_ms"] is None      # nothing to take a median OF -- not 0
    assert p["longest_calm_s"] == 20.0
    assert p["read"] == "still"


def test_the_numbers_are_derived_from_the_segment_table():
    p = M.profile(_six_per_min())
    assert p["duration_s"] == 30.0                      # from the last segment's end, not a field
    assert p["transitions"] == 3 and p["settled"] == 4
    assert p["transitions_per_min"] == 6.0              # 3 in half a minute
    assert p["median_transition_ms"] == 1500
    assert p["p90_transition_ms"] == 1900.0             # default linear percentile of 1000/1500/2000
    assert p["max_transition_ms"] == 2000
    assert p["median_settled_ms"] == 6500.0             # settled 5.0 / 4.0 / 8.5 / 8.0 s -> mean
    assert p["longest_calm_s"] == 8.5                   # of the two middles
    assert p["transition_fraction"] == 0.15             # 4.5 s of change inside 30 s
    assert p["peak_median"] == 0.5


def test_the_read_is_banded_by_declared_thresholds_not_by_hardcoded_words(monkeypatch):
    m = _six_per_min()
    assert M.THRESHOLDS["calm"] == 6.0
    assert M.profile(m)["read"] == "calm"               # 6/min sits exactly on the calm ceiling
    monkeypatch.setitem(M.THRESHOLDS, "calm", 0.0)
    assert M.profile(m)["read"] == "active"             # the band moved, so the read moved
    monkeypatch.setitem(M.THRESHOLDS, "active", 0.0)
    assert M.profile(m)["read"] == "frantic"


def test_the_profile_states_its_resolution_floor_and_its_blind_spots():
    p = M.profile(_six_per_min())
    assert p["stride_ms"] == 500.0                      # fps 2.0 -> half a second between samples
    assert any("audio" in note for note in p["blind"])
    assert any("from a stored manifest" in note for note in p["blind"])
    assert any("500" in note for note in p["blind"])


def test_an_empty_manifest_says_unknown_rather_than_zero():
    p = M.profile(_manifest([]))
    assert p["duration_s"] is None
    assert p["transitions_per_min"] is None
    assert p["transition_fraction"] is None
    assert p["read"] == "unknown"
    assert any("no segments" in note for note in p["blind"])


def test_a_stored_storyboard_profiles_without_decoding_anything(tmp_path):
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(_six_per_min()), encoding="utf-8")
    from_file = M.profile(str(path))
    from_dict = M.profile(_six_per_min())
    assert from_file["transitions_per_min"] == from_dict["transitions_per_min"] == 6.0
    assert from_file["source"] == "synthetic.mp4"
    assert from_file["read"] == from_dict["read"]
