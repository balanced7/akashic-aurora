"""Tests for arsenal.analysis -- PyAV probe, hw_decode_evidence, audio_features.

Fast and independent of any other arsenal file: builds its own synthetic clips in
tmp_path and loads analysis.py directly if arsenal/__init__.py isn't there yet.
"""
from __future__ import annotations

import importlib.util
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

_ARSENAL_DIR = Path(__file__).resolve().parent.parent / "arsenal"


def _load_analysis():
    try:
        from arsenal import analysis  # type: ignore
        return analysis
    except ImportError:
        spec = importlib.util.spec_from_file_location(
            "arsenal_analysis_standalone", _ARSENAL_DIR / "analysis.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module


analysis = _load_analysis()

FPS = Fraction(30000, 1001)
DURATION_S = 3.0
SR = 48000


def _make_clip(path: Path, *, with_audio: bool) -> None:
    """A small synthetic clip: 320x240 h264 @ 30000/1001 fps, 3s. If with_audio, a stereo
    48kHz aac track: a 60 Hz sine for the first second, a 5 kHz sine after."""
    width, height = 320, 240
    n_frames = round(FPS * DURATION_S)

    out = av.open(str(path), mode="w")
    vstream = out.add_stream("libx264", rate=FPS)
    vstream.width = width
    vstream.height = height
    vstream.pix_fmt = "yuv420p"

    astream = None
    if with_audio:
        astream = out.add_stream("aac", rate=SR)
        astream.codec_context.layout = "stereo"

    for i in range(n_frames):
        arr = np.full((height, width, 3), (i * 2) % 256, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(arr, format="rgb24").reformat(format="yuv420p")
        frame.pts = i
        frame.time_base = Fraction(1, 1) / FPS
        for packet in vstream.encode(frame):
            out.mux(packet)
    for packet in vstream.encode():
        out.mux(packet)

    if astream is not None:
        t = np.arange(int(DURATION_S * SR)) / SR
        freq = np.where(t < 1.0, 60.0, 5000.0)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        sig = (0.3 * np.sin(phase)).astype(np.float32)
        stereo = np.stack([sig, sig], axis=0)
        chunk = 1024
        apts = 0
        for start in range(0, stereo.shape[1], chunk):
            block = stereo[:, start:start + chunk]
            if block.shape[1] == 0:
                continue
            aframe = av.AudioFrame.from_ndarray(block, format="fltp", layout="stereo")
            aframe.sample_rate = SR
            aframe.pts = apts
            apts += block.shape[1]
            for packet in astream.encode(aframe):
                out.mux(packet)
        for packet in astream.encode():
            out.mux(packet)

    out.close()


@pytest.fixture()
def clip_with_audio(tmp_path) -> Path:
    path = tmp_path / "clip.mp4"
    _make_clip(path, with_audio=True)
    return path


@pytest.fixture()
def clip_no_audio(tmp_path) -> Path:
    path = tmp_path / "clip_silent.mp4"
    _make_clip(path, with_audio=False)
    return path


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def test_probe_video_and_audio_fields(clip_with_audio):
    result = analysis.probe(str(clip_with_audio))

    assert result["api"] == "arsenal.probe/v0"
    assert result["size"] > 0
    assert isinstance(result["container"], str)

    assert result["duration"]["timebase"] == "1/1000000"
    assert 2_900_000 < result["duration"]["ticks"] < 3_100_000

    video = result["video"]
    assert video is not None
    assert video["codec"] == "h264"
    assert video["width"] == 320
    assert video["height"] == 240
    assert video["pix_fmt"] == "yuv420p"
    # exact rate/timebase strings, as required
    assert video["rate"] == "30000/1001"
    assert video["timebase"] == "1/30000"
    # our encoder never sets these -- probe must say None, never guess a value
    assert video["primaries"] is None
    assert video["transfer"] is None
    assert video["matrix"] is None
    assert video["range"] is None

    audio = result["audio"]
    assert audio is not None
    assert audio["codec"] == "aac"
    assert audio["rate"] == 48000
    assert audio["channels"] == 2
    assert audio["layout"] == "stereo"
    assert audio["timebase"] == "1/48000"


def test_probe_no_audio_stream_is_null(clip_no_audio):
    result = analysis.probe(str(clip_no_audio))
    assert result["video"] is not None
    assert result["audio"] is None


# ---------------------------------------------------------------------------
# hw_decode_evidence -- must not need hardware; shape + never-raises only
# ---------------------------------------------------------------------------

def test_hw_decode_evidence_shape_and_never_raises(clip_with_audio):
    result = analysis.hw_decode_evidence(
        str(clip_with_audio), devices=("d3d12va", "d3d11va", "not_a_real_device"), frames=5
    )
    assert set(result.keys()) == {"tried", "ok_device"}
    assert len(result["tried"]) == 3

    devices_seen = set()
    for entry in result["tried"]:
        assert set(entry.keys()) == {"device", "ok", "frames", "frame_format", "error"}
        assert isinstance(entry["ok"], bool)
        assert isinstance(entry["frames"], int)
        devices_seen.add(entry["device"])
    assert devices_seen == {"d3d12va", "d3d11va", "not_a_real_device"}

    assert result["ok_device"] is None or result["ok_device"] in devices_seen
    # An unrecognised device name is NOT guaranteed to fail: PyAV's av_hwdevice_find_type_by_name
    # silently maps an unknown string to HWDeviceType.none, and HWAccel then treats that as a
    # wildcard and accepts the codec's first advertised hardware config (verified empirically --
    # on this machine "not_a_real_device" actually decodes via dxva2_vld). The real contract this
    # test can hold onto is just: it has the right shape and it never raises.
    bogus = next(e for e in result["tried"] if e["device"] == "not_a_real_device")
    assert bogus["error"] is None or isinstance(bogus["error"], str)


def test_hw_decode_evidence_missing_file_never_raises(tmp_path):
    missing = tmp_path / "does-not-exist.mp4"
    result = analysis.hw_decode_evidence(str(missing), devices=("d3d12va",), frames=5)
    assert result["ok_device"] is None
    entry = result["tried"][0]
    assert entry["ok"] is False
    assert entry["error"] is not None


# ---------------------------------------------------------------------------
# audio_features
# ---------------------------------------------------------------------------

def test_audio_features_shape(clip_with_audio):
    result = analysis.audio_features(str(clip_with_audio))

    assert result["api"] == "arsenal.features/v0"
    assert result["timebase"] == "1/48000"
    assert result["hop_ticks"] == 480
    assert result["window_ticks"] == 2048
    assert result["names"] == ["rms", "bass", "mid", "high", "flux"]
    assert isinstance(result["start_ticks"], int)
    assert result["start_ticks"] == 0  # our fixture's first audio frame pts is 0
    assert result.get("no_audio", False) is False

    frames = result["frames"]
    assert len(frames) > 0
    for row in frames:
        assert len(row) == 5
        for value in row:
            assert 0.0 <= value <= 1.0


def test_audio_features_bass_then_high(clip_with_audio):
    result = analysis.audio_features(str(clip_with_audio))
    names = result["names"]
    bass_i, high_i = names.index("bass"), names.index("high")
    hop = result["hop_ticks"]
    start = result["start_ticks"]
    frames = result["frames"]

    def row_at(seconds: float):
        idx = round((seconds * SR - start) / hop)
        return frames[idx]

    early = row_at(0.4)   # inside the 60 Hz second
    late = row_at(2.0)    # inside the 5 kHz stretch

    assert early[bass_i] > early[high_i]
    assert late[high_i] > late[bass_i]


def test_audio_features_cache_hit(clip_with_audio, monkeypatch):
    first = analysis.audio_features(str(clip_with_audio))

    def _boom(*_args, **_kwargs):
        raise AssertionError("audio_features should not re-open the file on a cache hit")

    monkeypatch.setattr(analysis.av, "open", _boom)

    second = analysis.audio_features(str(clip_with_audio))
    assert second == first


def test_audio_features_no_audio(clip_no_audio):
    result = analysis.audio_features(str(clip_no_audio))
    assert result["frames"] == []
    assert result["no_audio"] is True


def test_audio_features_progress_reaches_one(clip_with_audio):
    values = []
    analysis.audio_features(str(clip_with_audio), progress=values.append)
    assert values, "progress should be called at least once"
    assert all(0.0 <= v <= 1.0 for v in values)
    assert values[-1] == 1.0
