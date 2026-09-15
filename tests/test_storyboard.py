"""storyboard pins: the dynamic-capture segmentation must find a KNOWN cut at a KNOWN time.

The synthetic clip is generated here (1.0 s of solid red, then 1.0 s of solid blue at 10 fps),
so the ground truth is exact: one hard cut at t=1.0 s whose transition is a single frame step.
A detector that cannot find that has no business segmenting anything subtler.
"""
from __future__ import annotations

import numpy as np
import pytest

import av

from arsenal import storyboard as sb


def _write_clip(path, *, fps=10, secs=1.0, color_a=(220, 20, 20), color_b=(20, 20, 220)):
    w, h = 160, 120
    with av.open(str(path), mode="w") as out:
        stream = out.add_stream("mpeg4", rate=fps)
        stream.width, stream.height, stream.pix_fmt = w, h, "yuv420p"
        total = int(fps * secs) * 2
        for i in range(total):
            rgb = np.zeros((h, w, 3), dtype=np.uint8)
            rgb[:, :] = color_a if i < total // 2 else color_b
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return path


def test_synthetic_cut_is_found_at_the_right_time(tmp_path):
    clip = _write_clip(tmp_path / "cut.mp4")
    m = sb.analyse(str(clip), fps=10, width=160)
    transitions = [s for s in m["segments"] if s["kind"] == "transition"]
    assert transitions, f"no transition found in a hard cut: {m['segments']}"
    first = transitions[0]
    assert abs(first["start_s"] - 1.0) <= 0.25, first
    assert first["duration_ms"] <= 300, first          # a hard cut is short, not a 2-second fade
    assert m["settled"] >= 2                            # red run and blue run


def test_signature_and_score_pure_contracts():
    red = np.zeros((64, 64, 3), dtype=np.uint8)
    red[:, :, 0] = 200
    blue = np.zeros((64, 64, 3), dtype=np.uint8)
    blue[:, :, 2] = 200
    same = sb.change_score(sb.signature(red), sb.signature(red))
    diff = sb.change_score(sb.signature(red), sb.signature(blue))
    assert same == pytest.approx(0.0, abs=1e-6)
    assert diff > 0.1


def test_segment_hysteresis_keeps_a_slow_fade_as_one_transition():
    scores = [0.0, 0.0, 0.0, 0.05, 0.06, 0.07, 0.06, 0.05, 0.0, 0.0, 0.0]
    times = [i * 0.1 for i in range(len(scores))]
    segs = sb.segment(scores, times, low=0.02, high=0.06, settle_frames=2)
    transitions = [s for s in segs if s.kind == "transition"]
    assert len(transitions) == 1, segs
    assert transitions[0].duration_ms >= 300


def test_dedupe_merges_same_moment_and_keeps_a_different_palette():
    """The pin that caught the flat-frame blindness: dHash says solid green == solid blue,
    so structure alone would merge two different moments. Palette must also agree."""
    green = np.zeros((64, 64, 3), dtype=np.uint8)
    green[:, :, 1] = 180
    near_green = np.zeros((64, 64, 3), dtype=np.uint8)
    near_green[:, :, 1] = 185                     # same moment, tiny exposure wobble
    blue = np.zeros((64, 64, 3), dtype=np.uint8)
    blue[:, :, 2] = 180
    hashes = {0: sb.dhash(green), 1: sb.dhash(near_green), 2: sb.dhash(blue)}
    palettes = {0: sb.palette(green), 1: sb.palette(near_green), 2: sb.palette(blue)}
    assert sb.hamming(hashes[0], hashes[2]) == 0, "flat frames share a gradient signature (the trap)"
    picks = [{"frame_index": i, "t_s": i * 0.2, "kind": "settled", "score": 0.0, "segment_ms": 200}
             for i in (0, 1, 2)]
    kept = sb.dedupe(picks, hashes, palettes)
    assert [p["frame_index"] for p in kept] == [0, 2]


def test_manifest_declares_its_own_sampling(tmp_path):
    clip = _write_clip(tmp_path / "cut2.mp4")
    m = sb.analyse(str(clip), fps=10, width=160)
    for field in ("api", "sampling", "frames_examined", "segments", "picks", "not_measured"):
        assert field in m
    assert m["sampling"]["fps"] == 10 and m["sampling"]["low"] > 0
    assert any("SAMPLE" in note for note in m["not_measured"])
