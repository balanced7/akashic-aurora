"""arsenal.media.cut: frame-exact trims (copy | smart | exact) that keep every audio track and its title.

Synthetic fixtures are made at test time: 60 fps HEVC (the OBS codec) with a 2 s keyframe interval, a non-zero video
start_time (the bug the promoted smartcut fixed), and three noise tracks titled Voice, Game, Comms, so audio sync can
be measured by cross-correlation. The real oracles (the 2-min OBS excerpt and the 33-min recording) skip when absent.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import time
from pathlib import Path

import numpy as np
import pytest

from arsenal.media import cut, ff

ORACLES = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles"
EXCERPT = ORACLES / "clips" / "excerpt_600_720.mp4"
RECORDING = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")
TITLES = ["Voice", "Game", "Comms"]


@pytest.fixture(scope="module", autouse=True)
def _state(tmp_path_factory):
    """State (facts cache, default outputs) in a temp folder; the saved house ffmpeg is still found."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp_path_factory.mktemp("state")))
        mp.setenv("ARSENAL_MEDIA_RECEIPTS", "0")
        cut._memo.clear()
        yield
        cut._memo.clear()


def _have_ffmpeg():
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")


def _hevc_encoder():
    if ff.has_encoder("hevc_amf"):
        return ["-c:v", "hevc_amf", "-rc", "cqp", "-qp_i", "20", "-qp_p", "20", "-bf", "0", "-g", "120"]
    if ff.has_encoder("libx265"):
        return ["-c:v", "libx265", "-crf", "20", "-x265-params", "bframes=0:keyint=120:min-keyint=120:scenecut=0"]
    pytest.skip("no HEVC encoder")


def _three_tracks(out: Path, *, offset: float, audio_codec: list) -> Path:
    args = []
    if offset:
        args += ["-itsoffset", str(offset)]
    args += ["-f", "lavfi", "-i", "testsrc2=s=640x360:r=60:d=8"]
    for color, seed in (("white", 1), ("pink", 2), ("brown", 3)):
        args += ["-f", "lavfi", "-i", f"anoisesrc=d=8:c={color}:seed={seed}:a=0.3"]
    args += ["-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:a", *_hevc_encoder(), "-pix_fmt", "yuv420p",
             *audio_codec, "-ar", "48000"]
    for i, t in enumerate(TITLES):
        args += [f"-metadata:s:a:{i}", f"title={t}"]
    ff.run(["-v", "error", "-y", *args, str(out)])
    return out


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    _have_ffmpeg()
    d = tmp_path_factory.mktemp("cut")
    mp4 = _three_tracks(d / "three_offset.mp4", offset=0.025, audio_codec=["-c:a", "libopus", "-b:a", "96k"])
    mkv = _three_tracks(d / "three.mkv", offset=0.0, audio_codec=["-c:a", "aac", "-b:a", "128k"])
    bframes = d / "bframes.mp4"
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=6", "-f", "lavfi", "-i",
            "sine=f=440:d=6", "-c:v", "libx264", "-bf", "2", "-g", "30", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(bframes)])
    return {"dir": d, "mp4": mp4, "mkv": mkv, "bframes": bframes}


@pytest.fixture(scope="module")
def ts_clip(tmp_path_factory):
    """An MPEG-TS: its container clock starts at 1.4 s, so a seek that forgets the format start lands 1.4 s late."""
    _have_ffmpeg()
    out = tmp_path_factory.mktemp("cut_ts") / "gop1.ts"
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60:d=8", "-f", "lavfi", "-i",
            "anoisesrc=d=8:c=white:seed=7:a=0.3", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-bf", "0",
            "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-b:a", "128k", "-ar", "48000", "-f", "mpegts", str(out)])
    return out


def _gray_frames(path) -> np.ndarray:
    """Every frame, decoded from the file start with no seek at all: the reference a seek bug cannot share."""
    res = ff.run(["-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode", "passthrough", "-vf",
                  "scale=160:90", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"], binary=True)
    return np.frombuffer(res.stdout, np.uint8).reshape(-1, 90, 160).astype(np.float64)


def _pcm(path, track: int, ss=None, dur: float = 1.5) -> np.ndarray:
    seek = ["-ss", f"{ss:.6f}"] if ss is not None else []
    res = ff.run(["-v", "error", *seek, "-i", str(path), "-map", f"0:a:{track}", "-t", f"{dur}",
                  "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                 binary=True)
    return np.frombuffer(res.stdout, np.float32)


def _lag_ms(a: np.ndarray, b: np.ndarray) -> float:
    """Where b's content sits in a (ms): 0 means the cut's audio is exactly the source's audio at the real start."""
    n = min(len(a), len(b))
    c = np.fft.irfft(np.fft.rfft(a[:n], 2 * n) * np.conj(np.fft.rfft(b[:n], 2 * n)))
    k = int(np.argmax(c))
    return (k if k < n else k - 2 * n) / 48.0


# ------------------------------------------------------------------------------------------- plan

def test_plan_suggests_copy_exactly_on_a_keyframe(clips):
    f = cut.facts(clips["mp4"])
    st, kfs = f["video"]["start"], f["keyframes"]
    assert 0.02 < st < 0.05 and kfs[:3] == pytest.approx([st, st + 2, st + 4], abs=1e-5)   # not a frame multiple
    on = cut.plan(clips["mp4"], kfs[1], 5.0)
    off = cut.plan(clips["mp4"], 2.5, 5.0)
    assert on["mode_suggested"] == "copy" and on["on_keyframe"] and on["head_reencode_s"] == 0
    assert off["mode_suggested"] == "smart" and not off["on_keyframe"]
    assert off["start_keyframe"] == pytest.approx(kfs[1], abs=1e-6)
    assert off["next_keyframe"] == pytest.approx(kfs[2], abs=1e-6)
    # the first frame whose pts >= 2.5 s - 1 ms, counted from the video's own start_time
    first = math.ceil((2.5 - st - 1e-3) * 60)
    assert off["start_real"] == pytest.approx(st + first / 60, abs=1e-6)
    assert off["head_reencode_s"] == pytest.approx(kfs[2] - off["start_real"], abs=1e-6)
    assert on["est_s"] < off["est_s"]
    assert off["api"] == "arsenal.media.cut/v0" and off["blind"]


def test_plan_is_fast_on_a_cached_keyframe_list(clips):
    cut.plan(clips["mp4"], 1.0, 3.0)
    times = []
    for i in range(20):
        t = time.perf_counter()
        cut.plan(clips["mp4"], 1.0 + i * 0.1, 6.0)
        times.append(time.perf_counter() - t)
    assert statistics.median(times) < 0.1
    cut._memo.clear()                     # a new process: the facts come back from the disk cache
    t = time.perf_counter()
    cut.plan(clips["mp4"], 1.0, 3.0)
    assert time.perf_counter() - t < 0.1


def test_long_exact_encodes_take_the_gpu_lock():
    """The lock decision only (no encode): 2 min of 1080p60 re-encoded is ~32 s at the measured 224 fps."""
    facts = {"video": {"codec": "h264", "w": 1920, "h": 1080, "fps": "60/1", "vfr": False, "has_b_frames": 2,
                       "pix_fmt": "yuv420p", "start": 0.0, "duration": 600.0, "bit_rate": 9_000_000,
                       "color": {}}, "audio": [], "keyframes": [i * 4.0 for i in range(150)]}
    long = cut._plan(facts, 1.0, 121.0)
    short = cut._plan(facts, 1.0, 21.0)
    assert long["mode_suggested"] == "exact" and long["gpu_lock"] and long["est_s"] > 30
    assert not short["gpu_lock"] and short["est_s"] < 30


def test_plan_says_why_smart_cannot_run(clips):
    p = cut.plan(clips["bframes"], 1.2, 4.0)
    assert p["mode_suggested"] == "exact" and "B-frames" in p["smart_blocker"]


# ------------------------------------------------------------------------------------------- cut

@pytest.mark.parametrize("ext", [".mkv", ".mp4"])
@pytest.mark.parametrize("src_key", ["mp4", "mkv"])
def test_smart_cut_is_frame_exact_and_keeps_three_titled_tracks(clips, src_key, ext):
    out = clips["dir"] / f"smart_{src_key}{ext}"
    res = cut.cut(clips[src_key], 1.5, 5.25, out)
    v = res["verify"]
    assert res["mode"] == "smart" and res["head_frames"] > 0 and res["copied_frames"] > 0
    assert v["ok"], v
    assert v["frames_out"] == v["frames_expected"] == res["frames"]
    assert v["decode_errors"] == 0
    assert v["head_psnr_db"] == "inf" or v["head_psnr_db"] > 40
    assert v["copied_identical"] == v["copied_compared"] == res["copied_frames"]
    assert v["titles_out"] == TITLES and v["audio_streams_out"] == 3


def test_copy_snaps_to_the_keyframe_and_says_so(clips):
    res = cut.cut(clips["mp4"], 2.5, 5.0, clips["dir"] / "copy.mp4", mode="copy")
    assert res["mode"] == "copy" and res["start_real"] == pytest.approx(cut.facts(clips["mp4"])["keyframes"][1])
    assert any("before the requested start" in r for r in res["reasons"])
    v = res["verify"]
    assert v["ok"] and v["copied_identical"] == v["frames_out"] == res["frames"]
    assert v["titles_out"] == TITLES


def test_smart_on_a_keyframe_is_a_lossless_copy(clips):
    res = cut.cut(clips["mp4"], cut.facts(clips["mp4"])["keyframes"][1], 5.0, clips["dir"] / "onkey.mkv")
    assert res["mode"] == "copy" and res["head_frames"] == 0
    assert res["verify"]["ok"] and res["verify"]["head_psnr_db"] == "inf"


def test_exact_reencodes_the_whole_range(clips):
    res = cut.cut(clips["mkv"], 0.75, 3.0, clips["dir"] / "exact.mp4", mode="exact")
    v = res["verify"]
    assert res["mode"] == "exact" and res["head_frames"] == res["frames"] == 135
    assert v["ok"] and v["copied_compared"] == 0 and v["head_min_psnr_db"] > 40
    assert v["titles_out"] == TITLES


@pytest.mark.parametrize("mode", ["smart", "copy", "exact"])
def test_audio_stays_in_sync_with_the_picture(clips, mode):
    out = clips["dir"] / f"sync_{mode}.mp4"
    res = cut.cut(clips["mp4"], 1.53, 5.2, out, mode=mode, verify=False)
    for track in (0, 2):
        lag = _lag_ms(_pcm(out, track), _pcm(clips["mp4"], track, ss=res["start_real"]))
        assert abs(lag) < 2.0, (mode, track, lag)          # measured: within 1 ms in every mode and container


def test_track_subset_keeps_titles_and_a_missing_track_refuses(clips):
    res = cut.cut(clips["mp4"], 1.5, 4.5, clips["dir"] / "sub.mp4", tracks=[0, 2])
    assert res["verify"]["titles_out"] == ["Voice", "Comms"] and res["verify"]["ok"]
    with pytest.raises(ff.MediaError, match="missing audio track 5"):
        cut.cut(clips["mp4"], 1.5, 4.5, clips["dir"] / "bad.mp4", tracks=[5])


def test_bad_requests_fail_closed(clips):
    src = clips["mp4"]
    with pytest.raises(ff.MediaError, match="bad range"):
        cut.cut(src, 3.0, 2.0, clips["dir"] / "x.mp4")
    with pytest.raises(ff.MediaError, match="bad range"):
        cut.plan(src, 9.0, 10.0)
    with pytest.raises(ff.MediaError, match="past the end"):
        cut.plan(src, 1.0, 30.0)
    with pytest.raises(ff.MediaError, match="originals are never touched"):
        cut.cut(src, 1.0, 2.0, src)
    with pytest.raises(ff.MediaError, match="cut writes"):
        cut.cut(src, 1.0, 2.0, clips["dir"] / "x.avi")
    with pytest.raises(ff.MediaError, match="unknown mode"):
        cut.cut(src, 1.0, 2.0, clips["dir"] / "x.mp4", mode="fast")


def test_bframes_smart_falls_back_to_exact_and_copy_is_honest(clips):
    res = cut.cut(clips["bframes"], 1.2, 4.0, clips["dir"] / "bf.mp4")
    assert res["mode"] == "exact" and "B-frames" in res["reasons"][0]
    assert res["verify"]["ok"] and res["verify"]["frames_out"] == 84
    cp = cut.cut(clips["bframes"], 1.2, 4.0, clips["dir"] / "bf_copy.mp4", mode="copy")
    assert cp["start_real"] == pytest.approx(1.0)
    assert cp["verify"]["ok"] and abs(cp["verify"]["frames_out"] - cp["frames"]) <= 3
    assert any("container level" in r for r in cp["reasons"])


def test_the_original_is_never_touched(clips):
    st = os.stat(clips["mp4"])
    cut.cut(clips["mp4"], 1.5, 3.0, clips["dir"] / "touch.mp4", verify=False)
    st2 = os.stat(clips["mp4"])
    assert (st.st_size, st.st_mtime_ns) == (st2.st_size, st2.st_mtime_ns)


def test_default_out_goes_under_the_state_folder(clips):
    res = cut.cut(clips["mp4"], 1.5, 3.0, verify=False)
    assert Path(res["out"]).parent == ff.state_dir() / "cut" and Path(res["out"]).suffix == ".mp4"


# ------------------------------------------------------------------------------------------- MPEG-TS clock

@pytest.mark.parametrize("mode", ["smart", "copy", "exact"])
def test_a_container_that_starts_at_1_4_s_cuts_the_right_frames_and_audio(ts_clip, mode):
    """Checked against a decode with no seek: before the fix every mode started 2.000 s late, the audio was 1.4 s
    off, and verify (which sought the same way) said ok. 2.5 and 5.0 are file times (seconds from the file's start);
    the container's own clock starts 1.4 s earlier, which tests/test_arsenal_media_house_clock.py pins."""
    f = cut.facts(ts_clip)
    assert f["format_start"] == pytest.approx(1.4, abs=0.01)
    out = ts_clip.parent / f"ts_{mode}.mp4"
    res = cut.cut(ts_clip, 2.5, 5.0, out, mode=mode)
    assert res["mode"] == mode and res["verify"]["ok"], res["verify"]
    src, got = _gray_frames(ts_clip), _gray_frames(out)
    k = round((res["start_real"] - f["video"]["start"]) * 60)
    assert len(got) == res["frames"]
    for i in (0, len(got) - 1):
        mse = [((got[i] - s) ** 2).mean() for s in src]
        assert int(np.argmin(mse)) == k + i, (mode, i, int(np.argmin(mse)), k + i)
    ref = _pcm(ts_clip, 0, dur=8.0)                      # sample 0 sits at the track's first file time: no -ss
    off = int(round((res["start_real"] - f["audio"][0]["start"]) * 48000))
    lag = _lag_ms(_pcm(out, 0), ref[off:off + 72000])
    assert abs(lag) < 2.0, (mode, lag)                   # measured -0.7 ms (mp4); 1400.7 ms before the fix


def test_verify_picks_frames_by_pts_so_a_wrong_start_fails(ts_clip):
    out = ts_clip.parent / "ts_check.mp4"
    res = cut.cut(ts_clip, 2.5, 5.0, out, mode="copy", verify=False)
    st, end = res["start_real"], res["end_real"]
    assert cut.verify(ts_clip, st, end, out)["ok"]
    wrong = cut.verify(ts_clip, st + 1.0, end + 1.0, out)          # a cut that started one GOP late
    assert not wrong["ok"] and wrong["copied_identical"] == 0
    exact = cut.cut(ts_clip, 2.5, 5.0, ts_clip.parent / "ts_check_exact.mp4", mode="exact", verify=False)
    shifted = cut.verify(ts_clip, exact["start_real"] + 1.0, exact["end_real"] + 1.0, exact["out"], copied_from=None)
    assert not shifted["ok"] and shifted["head_min_psnr_db"] < cut.PSNR_FLOOR_DB


def test_long_outputs_are_verified_on_samples(clips, monkeypatch):
    """Past compare_max, the decode-error pass covers the head through SAMPLE frames past the splice and the last
    SAMPLE frames, as the PSNR pass does (a 120 s copy of the recording: 12.0 s of verify before, 2.9 s after)."""
    res = cut.cut(clips["mp4"], 1.5, 6.5, clips["dir"] / "long.mp4", verify=False)
    monkeypatch.setattr(cut, "SAMPLE", 30)
    v = cut.verify(clips["mp4"], res["start_real"], res["end_real"], res["out"], compare_max=60)
    head = res["head_frames"]
    assert v["ok"] and v["frames_out"] == res["frames"] == 300
    assert v["decode_checked"] == [[0, head + 30], [270, 30]]
    assert v["frames_compared"] == v["frames_compared_expected"] == 60
    p = cut.plan(clips["mp4"], 1.5, 6.5)
    assert p["verify_est_s"] > 0 and p["est_s"] > 0


# ------------------------------------------------------------------------------------------- concat

def test_concat_joins_smart_cuts_and_refuses_a_mismatch(clips):
    d = clips["dir"]
    a = cut.cut(clips["mp4"], 1.5, 3.0, d / "part_a.mp4", verify=False)
    b = cut.cut(clips["mp4"], 4.6, 6.5, d / "part_b.mp4", verify=False)
    res = cut.concat([a["out"], b["out"]], d / "joined.mp4")
    assert res["frames_out"] == res["frames_expected"] == a["frames"] + b["frames"]
    assert res["decode_errors"] == 0 and res["titles_out"] == TITLES
    with pytest.raises(ff.MediaError, match="concat refuses"):
        cut.concat([a["out"], clips["bframes"]], d / "nope.mp4")


# ------------------------------------------------------------------------------------------- CLI

def test_cli_plan_prints_the_cost(clips, capsys):
    rc = cut.cli("cut", [str(clips["mp4"]), "1.5", "0:05.25", "--plan"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["mode_suggested"] == "smart" and out["est_s"] > 0


# ------------------------------------------------------------------------------------------- real oracles

@pytest.mark.skipif(not EXCERPT.is_file(), reason="media oracle excerpt_600_720.mp4 not on this machine")
def test_excerpt_smart_cut_matches_the_verified_numbers():
    res = cut.cut(EXCERPT, 1.5, 12.0, Path(os.environ["ARSENAL_MEDIA_STATE"]) / "excerpt_cut.mp4")
    v = res["verify"]
    assert v["ok"] and v["frames_out"] == 630 and v["decode_errors"] == 0
    assert 47.0 < v["head_psnr_db"] < 60.0                  # the promoted smartcut measured 47.9-50.9 dB
    assert v["copied_identical"] == v["copied_compared"] == res["copied_frames"] > 400


@pytest.mark.skipif(not RECORDING.is_file(), reason="Daniel's 2026-10-11 17-51-11 recording not on this machine")
def test_recording_601_5_to_612_gives_630_frames():
    res = cut.cut(RECORDING, 601.5, 612.0, Path(os.environ["ARSENAL_MEDIA_STATE"]) / "rec_cut.mp4")
    v = res["verify"]
    assert res["mode"] == "smart" and v["ok"]
    assert v["frames_out"] == 630 and v["decode_errors"] == 0
    assert 47.0 < v["head_psnr_db"] < 60.0
    assert v["copied_identical"] == v["copied_compared"] == 470
