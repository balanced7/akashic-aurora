"""floors pins: the visual linter must FAIL dead, blown, flat and illegible frames, and pass
the ones that merely happen to be dark-but-alive. Synthetic frames only -- the real receipts
are evidence, not fixtures, so regenerating them never breaks the suite."""
from __future__ import annotations

import numpy as np
import pytest

import av

from arsenal import floors as F


def _frame(value=0, shape=(120, 240, 3)):
    return np.full(shape, value, dtype=np.uint8)


def test_black_frame_is_dead_and_flat():
    black = _frame(4)
    assert F.floor_not_dead(black)["pass"] is False
    assert F.floor_variety(black)["pass"] is False


def test_dark_but_alive_frame_passes_the_dead_floor():
    """A mostly-dark visualizer frame with some structure must NOT be failed: the floor is
    'not a void', not 'bright'."""
    frame = _frame(6)
    frame[40:80, 60:180] = np.array([90, 70, 190], dtype=np.uint8)   # a glowing shape
    assert F.floor_not_dead(frame)["pass"] is True
    assert F.floor_variety(frame)["pass"] is True


def test_blown_region_fails_and_is_region_scoped():
    frame = _frame(30)
    frame[90:, :] = 255                      # the bottom band: a keyboard-like blowout
    whole = F.floor_not_blown(frame)
    band = F.floor_not_blown(frame, region=F.KEYBOARD_REGION)
    assert band["pass"] is False
    assert band["measured"]["clipped_fraction"] > 0.1
    assert whole["pass"] is False            # the band is a big share of the whole frame too


def test_legibility_separates_text_from_flat_field():
    flat = _frame(120)
    assert F.floor_legibility(flat)["pass"] is False        # nothing to read
    text = _frame(20)
    text[50:70, 20:200] = 220                               # dark field, bright label
    assert F.floor_legibility(text)["pass"] is True


def test_check_returns_a_receipt_and_drops_unknown_thresholds(tmp_path):
    frame = _frame(200)
    path = tmp_path / "flat.png"
    with av.open(str(path), mode="w", format="image2") as out:
        stream = out.add_stream("png", rate=1)
        stream.width, stream.height, stream.pix_fmt = 240, 120, "rgb24"
        for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
            out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    receipt = F.check(str(path), min_contrast=2.0, some_unknown_threshold=1)
    assert receipt["api"] == F.API and receipt["size"] == [240, 120]
    assert {r["floor"] for r in receipt["results"]} == set(F.FLOORS)
    assert receipt["pass"] is False                          # a flat 200 field is not a picture
    assert any("taste" in note for note in receipt["not_measured"])


def test_a_broken_floor_is_a_failed_floor_not_a_traceback(monkeypatch, tmp_path):
    frame = _frame(60)
    path = tmp_path / "x.png"
    with av.open(str(path), mode="w", format="image2") as out:
        stream = out.add_stream("png", rate=1)
        stream.width, stream.height, stream.pix_fmt = 240, 120, "rgb24"
        for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
            out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    def _boom(rgb, **kw):
        raise RuntimeError("floor broke")
    monkeypatch.setitem(F.FLOORS, "variety", _boom)
    receipt = F.check(str(path), floors=["variety"])
    assert receipt["pass"] is False
    assert "RuntimeError" in receipt["results"][0]["error"]
