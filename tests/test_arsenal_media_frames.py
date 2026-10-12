"""arsenal.media.frames: one-pass frame reads -- exact pts, crops in pixels or fractions, keyframes, at_times
bit-identical to the single-frame `-ss` grabs every earlier script made."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from arsenal.media import ff, frames

RECORDING = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    out = tmp_path_factory.mktemp("frames") / "testsrc_10fps.mp4"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=10:d=3", "-c:v", "libx264", "-g", "10",
            "-keyint_min", "10", "-sc_threshold", "0", "-bf", "0", "-pix_fmt", "yuv420p", "-y", str(out)])
    return out


def _single_grab(path, t, crop=None):
    vf = ["-vf", f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}"] if crop else []
    res = ff.run(["-ss", f"{t:.6f}", "-i", str(path), "-frames:v", "1", *vf, "-pix_fmt", "rgb24", "-f", "rawvideo",
                  "-"], binary=True)
    return res.stdout


def test_every_frame_with_exact_pts(clip):
    got = list(frames.frames(clip, hw=None))
    assert len(got) == 30
    assert [round(t, 3) for t, _ in got[:3]] == [0.0, 0.1, 0.2]
    assert got[0][1].shape == (240, 320, 3)


def test_span_and_resample(clip):
    got = list(frames.frames(clip, start=1.0, dur=1.0, fps=2, hw=None))
    assert len(got) == 2
    assert got[0][0] == pytest.approx(1.0, abs=1e-3)


def test_fraction_and_pixel_crops_give_the_same_pixels(clip):
    px = next(frames.frames(clip, dur=0.1, crop=(80, 60, 160, 120), hw=None))[1]
    fr = next(frames.frames(clip, dur=0.1, crop=(0.25, 0.25, 0.5, 0.5), hw=None))[1]
    assert px.shape == (120, 160, 3)
    assert np.array_equal(px, fr)


def test_crop_outside_the_frame_refuses(clip):
    with pytest.raises(ff.MediaError, match="outside"):
        next(frames.frames(clip, crop=(300, 0, 100, 100), hw=None))


def test_size_keeps_aspect_when_height_is_open(clip):
    _, img = next(frames.frames(clip, dur=0.1, size=(160, None), hw=None))
    assert img.shape == (120, 160, 3)


def test_keyframes_only(clip):
    got = [t for t, _ in frames.keyframes(clip, hw=None)]
    assert [round(t, 3) for t in got] == [0.0, 1.0, 2.0]


def test_at_times_matches_single_frame_grabs_bit_for_bit(clip):
    times = [0.0, 0.55, 1.3, 2.85]
    got = list(frames.at_times(clip, times))
    assert [t for t, _, _ in got] == times
    for t_req, t_pts, img in got:
        assert t_pts + 1e-3 >= t_req
        assert img.tobytes() == _single_grab(clip, t_req), t_req


def test_at_times_past_the_end_refuses_by_default(clip):
    with pytest.raises(ff.MediaError, match="past the end"):
        list(frames.at_times(clip, [9.0]))


def test_at_times_past_the_end_on_request_says_what_it_did(clip):
    (t_req, t_pts, _), = list(frames.at_times(clip, [9.0], past_end="last"))
    assert t_req == 9.0 and t_pts == pytest.approx(2.9, abs=1e-3)      # its own pts: visibly not decoded at 9.0
    assert list(frames.at_times(clip, [1.0, 9.0], past_end="skip"))[0][0] == 1.0
    assert len(list(frames.at_times(clip, [1.0, 9.0], past_end="skip"))) == 1


def test_a_time_inside_the_last_frames_interval_is_a_real_frame(clip):
    (t_req, t_pts, _), = list(frames.at_times(clip, [2.95]))
    assert t_pts == pytest.approx(2.9, abs=1e-3)


def test_vulkan_decode_is_refused_by_name(clip):
    with pytest.raises(ff.MediaError, match="Vulkan"):
        next(frames.frames(clip, hw="vulkan"))


def test_save_writes_a_manifest(clip, tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    res = frames.save(clip, [0.5, 1.5], tmp_path / "out")
    assert res["api"] == "arsenal.media.grab/v0"
    assert [Path(r["file"]).exists() for r in res["frames"]] == [True, True]
    assert Path(res["receipt"]).exists()


@pytest.fixture(scope="module")
def ts_clip(tmp_path_factory):
    """MPEG-TS: container start 1.4 s, keyframes every 2 s. Its seeks land on the first keyframe AT OR AFTER the target,
    which once made frames(start=3.0, dur=1.0) return nothing, silently."""
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    out = tmp_path_factory.mktemp("frames_ts") / "clip.ts"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=160x120:r=30:d=8", "-c:v", "libx264", "-g", "60", "-keyint_min", "60",
            "-sc_threshold", "0", "-bf", "0", "-f", "mpegts", "-y", str(out)])
    return out


def _full_decode(path):
    return list(frames.frames(path, hw=None))


def test_ts_file_clock_counts_from_the_file_start(ts_clip):
    info = frames.video_info(ts_clip)
    assert info["format_start"] == pytest.approx(1.4, abs=0.01) and "mpegts" in info["format"]
    assert _full_decode(ts_clip)[0][0] == pytest.approx(0.0, abs=1e-3)


def test_ts_span_mid_file_is_whole_and_bit_identical(ts_clip):
    full = {round(t, 3): img for t, img in _full_decode(ts_clip)}
    got = list(frames.frames(ts_clip, start=3.0, dur=1.0, hw=None))
    assert len(got) == 30
    assert got[0][0] == pytest.approx(3.0, abs=1e-3) and got[-1][0] == pytest.approx(3.967, abs=1e-3)
    for t, img in got:
        assert img.tobytes() == full[round(t, 3)].tobytes(), t


def test_ts_at_times_between_keyframes(ts_clip):
    full = _full_decode(ts_clip)
    for t_req, t_pts, img in frames.at_times(ts_clip, [3.0, 5.55, 1.9]):
        want_t, want_img = next((t, im) for t, im in full if t + 1e-3 >= t_req)
        assert t_pts == pytest.approx(want_t, abs=1e-3), t_req
        assert img.tobytes() == want_img.tobytes(), t_req


@pytest.mark.skipif(not RECORDING.exists(), reason="Daniel's recording is not on this machine")
def test_recording_keyframes_every_250_frames():
    got = [t for t, _ in frames.keyframes(RECORDING, crop=(0.45, 0.0, 0.1, 0.05), size=(64, None))]
    assert len(got) == 487
    gaps = np.diff(got)
    assert np.median(gaps) == pytest.approx(250 / 60, abs=0.02)
