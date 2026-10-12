"""arsenal.media.avsync: offset and drift by onset-envelope cross-correlation.

A copy shifted with -itsoffset 0.083 comes back as 83 +- 2 ms, two tracks of one file are compared, a synthetic drift
is measured, a click track lines up with its own times, two sources of one sound show up as two lobes, and the
practice-log oracle (session 20261011-165503-f62d348c against the 17-06-22 recording) runs when both are on this
machine. Every signal here is generated at test time.
"""
from __future__ import annotations

import wave
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from arsenal.media import avsync, ff

REPO = Path(__file__).resolve().parents[1]
RECORDING = Path(r"E:\Video Output E\2026-10-11 17-06-22.mp4")
SESSION = "20261011-165503-f62d348c"
SESSION_DIR = REPO / "state" / "arsenal" / "performance" / SESSION


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))


def _clicks(times, dur: float, sr: int = 48000, seed: int = 1, noise: float = 0.003) -> np.ndarray:
    """Decaying noise bursts at the given times over a quiet noise floor: onsets with no rhythm to confuse."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(int(dur * sr)).astype(np.float32) * noise
    n = int(0.05 * sr)
    for t in times:
        i = int(round(t * sr))
        if 0 <= i < len(x):
            burst = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.015 * sr)) * rng.uniform(0.1, 0.5)
            x[i:i + n] += burst[:len(x) - i].astype(np.float32)
    return x


def _wav(path: Path, x: np.ndarray, sr: int = 48000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def _times(seed: int, until: float) -> np.ndarray:
    t = np.cumsum(np.random.default_rng(seed).uniform(0.12, 0.6, int(until * 4)))
    return t[t < until - 1.0]


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
        ff.ffprobe()
    except ff.MediaError:
        pytest.skip("no ffmpeg/ffprobe on this machine")
    d = tmp_path_factory.mktemp("avsync")
    times = _times(3, 40.0)
    clicks = _wav(d / "clicks.wav", _clicks(times, 40.0))
    a = d / "a.mp4"
    ff.run(["-v", "error", "-f", "lavfi", "-i", "testsrc2=s=160x120:r=30:d=40", "-i", str(clicks), "-map", "0:v",
            "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-y", str(a)])
    b = d / "b.mp4"   # the spec's construction: the same audio, its timestamps moved 83 ms later
    ff.run(["-v", "error", "-i", str(a), "-itsoffset", "0.083", "-i", str(a), "-map", "0:v", "-map", "1:a",
            "-c", "copy", "-y", str(b)])
    two = d / "two_tracks.mp4"   # track 1 is track 0 delayed 40 ms: the "is the Discord track late?" case
    ff.run(["-v", "error", "-i", str(clicks), "-filter_complex", "[0:a]asplit[x][y];[y]adelay=40[z]",
            "-map", "[x]", "-map", "[z]", "-c:a", "aac", "-b:a", "128k", "-y", str(two)])
    silent = d / "silent two.mp4"   # two tracks nobody spoke on: a muted mic, an empty Discord track
    ff.run(["-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=12", "-f", "lavfi",
            "-i", "anullsrc=r=48000:cl=mono:d=12", "-map", "0:a", "-map", "1:a", "-c:a", "aac", "-y", str(silent)])
    return SimpleNamespace(dir=d, times=times, clicks=clicks, a=a, b=b, two=two, silent=silent)


# ------------------------------------------------------------------------------------------------- two signals

def test_itsoffset_copy_is_recovered_as_83_ms(media):
    r = avsync.offset(media.a, media.b, window_s=10)
    assert r["offset_ms"] == pytest.approx(83.0, abs=2.0), r["reading"]
    assert r["confidence"] >= 3
    assert abs(r["drift_ms_per_min"]) < 1.0
    assert r["api"] == "arsenal.media.avsync/v0"
    assert {"a_track", "b_track", "span", "max_offset_s", "window_s", "hop_ms"} <= set(r["params"])
    assert r["blind"] and len(r["source"]) == 2
    assert Path(r["receipt"]).is_file()


def test_the_sign_follows_the_order(media):
    r = avsync.offset(media.b, media.a, window_s=10)
    assert r["offset_ms"] == pytest.approx(-83.0, abs=2.0), r["reading"]
    assert "earlier" in r["reading"]


def test_two_tracks_of_one_file(media):
    r = avsync.offset(media.two)          # b=None: track 1 of the same file against track 0
    assert r["params"]["b_track"] == 1
    assert r["offset_ms"] == pytest.approx(40.0, abs=2.0), r["reading"]


def test_synthetic_drift_is_measured(tmp_path):
    times = _times(5, 120.0)
    rate = 12.0 / 60000                    # b's clock runs 12 ms per minute fast, and starts 40 ms late
    a = _wav(tmp_path / "a.wav", _clicks(times, 120.0, sr=16000, seed=11), sr=16000)
    b = _wav(tmp_path / "b.wav", _clicks(times * (1 + rate) + 0.040, 120.0, sr=16000, seed=11), sr=16000)
    r = avsync.offset(a, b, window_s=20)
    assert r["drift_ms_per_min"] == pytest.approx(12.0, abs=1.0), r["reading"]
    assert r["offset_at_start_ms"] == pytest.approx(40.0, abs=3.0)
    assert r["windows_used"] >= 4


def test_flux_does_not_depend_on_how_the_stream_is_cut():
    x = _clicks(_times(9, 6.0), 6.0, sr=16000, seed=2)
    whole = avsync.flux([x])
    pieces = avsync.flux(np.array_split(x, 37))
    assert len(whole) == len(pieces) == (len(x) - avsync.N_FFT // 2) // avsync.HOP + 1
    assert np.allclose(whole, pieces, rtol=1e-4, atol=1e-3)


def test_cli_reads_the_offset_aloud(media, capsys):
    from arsenal.media.__main__ import main
    assert main(["avsync", str(media.a), str(media.b), "--window", "10"]) == 0
    out = capsys.readouterr().out
    assert "b is 82." in out and "later than a" in out


# ------------------------------------------------------------------------------------------------- event lists

def test_a_click_track_lines_up_with_its_own_times(media):
    r = avsync.against_events(media.clicks, media.times, window_s=10)
    assert abs(r["offset_ms"]) <= 1.0, r["reading"]
    assert r["matched"] >= 0.95 * r["events_in_audio"]
    assert r["match_resid_ms"]["median"] <= 5
    assert r["match_lift"] >= 2 * avsync.MIN_LIFT, (r["matched"], r["matched_chance"])
    assert r["candidates"][0]["matched"] >= 0.95 * r["events_in_audio"]
    assert "no better than chance" not in r["reading"]


@pytest.mark.parametrize("shift_s", [0.25, -0.4, 0.0371])
def test_events_early_or_late_are_measured(media, shift_s):
    r = avsync.against_events(media.clicks, media.times - shift_s, window_s=10)
    assert r["offset_ms"] == pytest.approx(shift_s * 1000, abs=2.0), r["reading"]


def test_two_sources_of_one_sound_show_as_two_lobes(tmp_path):
    times = _times(4, 40.0)
    both = _clicks(times, 40.0, sr=16000, seed=1) + _clicks(times + 0.080, 40.0, sr=16000, seed=2)
    src = _wav(tmp_path / "twin.wav", both, sr=16000)
    r = avsync.against_events(src, times, window_s=10)
    lobes = sorted(c["offset_ms"] for c in r["candidates"][:2])
    assert lobes == [pytest.approx(0, abs=5), pytest.approx(80, abs=5)]
    assert r["confidence"] < avsync.MIN_CONFIDENCE
    assert "WEAK" in r["reading"]


# ------------------------------------------------------------------------------------------------- refusals

def test_refusals(media):
    with pytest.raises(ff.MediaError, match="itself"):
        avsync.offset(media.a, None, a_track=0, b_track=0)
    with pytest.raises(ff.MediaError, match="missing"):
        avsync.offset(media.a, media.b, b_track=3)
    with pytest.raises(ff.MediaError, match="too short"):
        avsync.offset(media.a, media.b, span=(0, 4), max_offset_s=2.0)
    with pytest.raises(ff.MediaError, match="clock"):
        avsync.against_events(media.clicks, [1000.0 + i for i in range(10)])


def test_a_silent_track_is_refused_not_read_as_the_search_edge(media, capsys):
    """An all-zero envelope correlates as zeros everywhere; its argmax used to come back as -2000 ms, exit 0."""
    from arsenal.media.__main__ import main
    with pytest.raises(ff.MediaError, match="silent"):
        avsync.offset(media.silent)
    with pytest.raises(ff.MediaError, match="silent"):
        avsync.against_events(media.silent, [1.0 + 0.5 * i for i in range(16)])
    assert main(["avsync", str(media.silent)]) == 1
    assert "silent" in capsys.readouterr().err


def test_a_best_match_on_the_search_edge_is_refused():
    """A smooth bump 3 s later than its twin, searched within +-2 s: the correlation still climbs at the edge."""
    i = np.arange(2400)
    a = np.exp(-0.5 * ((i - 1200) / 120.0) ** 2)
    b = np.exp(-0.5 * ((i - 1800) / 120.0) ** 2)
    with pytest.raises(ff.MediaError, match="edge"):
        avsync._align(a, b, 0.0, 2.0, 30.0)
    assert avsync._at_edge(np.array([3.0, 2.0, 1.0])) and not avsync._at_edge(np.array([1.0, 3.0, 2.0]))


def test_malformed_events_fail_closed(media, tmp_path, capsys):
    from arsenal.media.__main__ import main
    with pytest.raises(ff.MediaError, match="weights"):
        avsync.against_events(media.clicks, media.times[:3], weights=[1.0, 2.0])
    with pytest.raises(ff.MediaError, match="numbers"):
        avsync.against_events(media.clicks, ["soon", 2.0])
    bad = tmp_path / "times tms.json"
    bad.write_text('[{"t_ms": 1000}, {"t_ms": 2000}]', encoding="utf-8")
    assert main(["avsync", str(media.clicks), "--events", str(bad)]) == 1
    assert '"t"' in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------- the practice log

def test_session_anchor_follows_jam_align():
    from arsenal.jam import align
    info = {"meta": {"opened_at_client": "2026-10-11T20:55:03.791Z"}, "opened_at": "2026-10-11T20:55:03.803+00:00"}
    anchor = avsync.session_anchor(info)
    assert anchor["method"] == "L3" and anchor["error_ms"] == align.ERROR_MS["L3"]
    assert anchor["epoch_ms"] == align.epoch_ms_of("2026-10-11T20:55:03.791Z")
    assert avsync.session_anchor({"opened_at": info["opened_at"]})["method"] == "L4"
    with pytest.raises(ff.MediaError, match="buffered"):
        avsync.session_anchor({"meta": {"buffered": True}, "opened_at": info["opened_at"]})


def test_obs_file_name_time_is_local():
    want = datetime(2026, 10, 11, 17, 6, 22).timestamp() * 1000
    assert avsync.obs_start_epoch_ms("E:/x/2026-10-11 17-06-22.mp4") == want
    assert avsync.obs_start_epoch_ms("clip.mp4") is None


@pytest.fixture(scope="module")
def practice(tmp_path_factory):
    """One run of the practice-session oracle (8 s) shared by the tests below, its receipt kept out of the state."""
    if not (RECORDING.is_file() and (SESSION_DIR / "events.jsonl").is_file()):
        pytest.skip("the practice recording or its session log is not on this machine")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp_path_factory.mktemp("practice")))
        return avsync.against_session(RECORDING, SESSION)


def test_practice_session_oracle(practice):
    """Note-ons placed by jam.align's L3 anchor and the OBS file-name time. The name holds whole seconds, so the true
    start is up to 1 s later: the offset must fall in (-1000 ms - anchor error, + output latency].

    The offset band alone accepts a wrong answer, and so does the raw match count: on this dense piano 32-35% of
    note-ons find an onset within 50 ms at ANY offset. So the count must beat the same count at offsets 0.5-1.5 s
    away. Measured 2026-10-12: -628 ms, lift 1.19 (5326 matched, 4492 by chance); the second lobe at -535 ms (the key
    thump on the mic and the synth on desktop audio) matches more, 5859; wrong offsets score 1.01-1.05 (0 ms 1.01,
    -300 ms 1.05, +300 ms 1.02, -1000 ms 1.02)."""
    r = practice
    assert r["prior"]["anchor"]["method"] == "L3"
    assert -1050 <= r["offset_ms"] <= 300, r["reading"]
    assert all(-1050 <= c["offset_ms"] <= 300 for c in r["candidates"][:2]), r["candidates"]
    assert r["match_lift"] >= avsync.MIN_LIFT, (r["matched"], r["matched_chance"], r["reading"])
    assert all(c["matched"] >= avsync.MIN_LIFT * r["matched_chance"] for c in r["candidates"][:2]), r["candidates"]


@pytest.mark.xfail(strict=True, reason="spec P12 acceptance not met on this oracle (Vandor's ruling): every key "
                                       "sounds twice, so the window offsets wander over ~100 ms between two lobes "
                                       "93 ms apart, and the OBS name gives the start only to the second")
def test_practice_session_holds_steady_to_one_frame(practice):
    """The spec's bar: steady within 16.7 ms across the recording. Strict, so it reports when it starts passing."""
    assert practice["spread_ms"] is not None and practice["spread_ms"] <= 16.7, practice["spread_ms"]
