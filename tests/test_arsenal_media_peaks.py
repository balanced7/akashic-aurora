"""arsenal.media.peaks: length = ceil(samples / spp), min/max equal numpy per block exactly (8- and 16-bit, mono and
split), the three file formats peaks.js and wavesurfer read, the cache, spans; the 33-min recording when present."""
from __future__ import annotations

import json
import math
import struct
import time
from pathlib import Path

import numpy as np
import pytest

from arsenal.media import ff, peaks

REC_17_51 = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")
SPP = 500          # 6 s at 48 kHz = 288000 samples: not a multiple of 500 * k for the Opus padding, so a partial pixel


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("peaks_fx")
    out = d / "two.mp4"
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=6",
            "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.6:seed=4:d=6:r=48000",
            "-f", "lavfi", "-i", "aevalsrc=0.9*sin(2*PI*50*t)|-0.4*sin(2*PI*7*t):s=48000:c=stereo:d=6",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a:0", "libopus", "-b:a:0", "128k", "-c:a:1", "flac", "-ac", "2",
            "-metadata:s:a:1", "title=Game", str(out)])
    return out


def _pcm(path, track: int, ch: int) -> np.ndarray:
    raw = ff.run(["-v", "error", "-i", str(path), "-map", f"0:a:{track}", "-ac", str(ch), "-f", "s16le", "-"],
                 binary=True).stdout
    return np.frombuffer(raw, np.int16).reshape(-1, ch)


@pytest.mark.parametrize("track", [0, 1])
@pytest.mark.parametrize("channels,bits", [("mono", 8), ("mono", 16), ("split", 8), ("split", 16)])
def test_length_and_min_max_equal_numpy_per_block(media, track, channels, bits):
    w = peaks.compute(media, track=track, spp=SPP, bits=bits, channels=channels)
    ch = 1 if channels == "mono" else 2
    pcm = _pcm(media, track, ch)
    n = math.ceil(len(pcm) / SPP)
    assert (w["length"], w["samples"], w["channels"], w["sample_rate"]) == (n, len(pcm), ch, 48000)
    assert w["length"] == peaks.expected_length(len(pcm), SPP)
    d = w["data"].reshape(n, ch, 2)
    for k in range(n):
        block = pcm[k * SPP:(k + 1) * SPP]          # the last block holds only the leftover samples
        mn, mx = block.min(axis=0), block.max(axis=0)
        if bits == 8:
            mn, mx = mn >> 8, mx >> 8
        assert np.array_equal(d[k, :, 0], mn) and np.array_equal(d[k, :, 1], mx), k
    assert w["data"].dtype == (np.int8 if bits == 8 else np.int16)


def test_three_formats_round_trip(media, tmp_path):
    res = peaks.peaks(media, track="Game", spp=SPP, out_prefix=tmp_path / "game")
    assert res["index"] == 1 and res["house_name"] == "Game" and res["cached"] is False
    w = peaks.compute(media, track=1, spp=SPP)
    with open(res["files"]["dat"], "rb") as fh:
        head = struct.unpack("<iIiiIi", fh.read(24))
        body = np.frombuffer(fh.read(), np.int8)
    assert head == (2, 1, 48000, SPP, w["length"], 1)
    assert np.array_equal(body, w["data"])
    js = json.loads(Path(res["files"]["json"]).read_text(encoding="utf-8"))
    assert {k: js[k] for k in ("version", "channels", "sample_rate", "samples_per_pixel", "bits", "length")} == \
        {"version": 2, "channels": 1, "sample_rate": 48000, "samples_per_pixel": SPP, "bits": 8, "length": w["length"]}
    assert js["data"] == w["data"].tolist() and len(js["data"]) == 2 * w["length"]
    ws = json.loads(Path(res["files"]["wavesurfer"]).read_text(encoding="utf-8"))
    assert abs(ws["duration"] - w["samples"] / 48000) < 1e-6 and len(ws["peaks"][0]) == w["length"]
    assert 0.0 <= min(ws["peaks"][0]) and max(ws["peaks"][0]) <= 1.0
    loudest = np.abs(_pcm(media, 1, 1).astype(np.int32)).max() / 32768.0     # the mono downmix is the channel mean
    assert abs(max(ws["peaks"][0]) - loudest) < 0.01 and 0.6 < loudest < 0.7
    assert res["pixels_per_second"] == 96.0 and Path(res["receipt"]).is_file()


def test_cache_returns_the_same_files_without_decoding(media):
    first = peaks.peaks(media, track=0)
    again = peaks.peaks(media, track=0)
    assert first["cached"] is False and again["cached"] is True
    assert again["files"] == first["files"] and again["length"] == first["length"]
    assert peaks.peaks(media, track=0, refresh=True)["cached"] is False


def test_span_starts_on_the_source_clock(media):
    res = peaks.compute(media, track=1, spp=480, span=(1.0, 3.5))
    assert res["samples"] == int(2.5 * 48000) and res["length"] == 250 and res["start_s"] == 1.0


def test_span_past_the_end_is_refused(media):
    # used to decode nothing and return length 0 as if it had succeeded
    with pytest.raises(ff.MediaError, match="bad span"):
        peaks.peaks(media, track=1, span=(100.0, 200.0))
    with pytest.raises(ff.MediaError, match="bad span"):
        peaks.compute(media, track=1, span=(4.0, 10.0))


def test_refuses_bad_parameters(media):
    with pytest.raises(ff.MediaError):
        peaks.compute(media, spp=1)
    with pytest.raises(ff.MediaError):
        peaks.peaks(media, formats=("png",))
    with pytest.raises(ff.MediaError, match="audio track 4 is not in"):
        peaks.compute(media, track=4)


def test_cli(media, tmp_path, capsys):
    assert peaks.cli("peaks", [str(media), "--track", "1", "--spp", "1024", "--out", str(tmp_path / "p")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["samples_per_pixel"] == 1024 and Path(out["files"]["dat"]).is_file()


@pytest.mark.skipif(not REC_17_51.is_file(), reason="Daniel's recording 2026-10-11 17-51-11 is not on this machine")
def test_33_minute_recording_in_seconds(tmp_path):
    t0 = time.perf_counter()
    res = peaks.peaks(REC_17_51, out_prefix=tmp_path / "rec", formats=("dat",))
    took = time.perf_counter() - t0
    assert res["length"] == 190149 and res["samples"] == 97356168
    assert res["bytes"]["dat"] == 24 + 2 * 190149                   # 371 KB
    # The spec's budget (P6): under 5 s. Measured 3.2-3.9 s alone and 4.5 s with three other build lanes decoding.
    assert took < 5.0, took
