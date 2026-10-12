"""arsenal.media.sheet: labelled contact sheets under one image read, keyframe sheets, filmstrips over the waveform.

The index round trip is the core promise: re-grab any cell with frames.at_times(src, [pts], crop, size) and get
the cell's exact pixels back. Synthetic fixtures are made at test time; the real recording skips when absent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from arsenal.media import cut, ff, frames, sheet

RECORDING = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")
CLOCKMAP = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "media-oracles" / "clockmaps" / \
    "rec_17-51-11.clockmap.json"


@pytest.fixture(scope="module", autouse=True)
def _state(tmp_path_factory):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp_path_factory.mktemp("state")))
        mp.setenv("ARSENAL_MEDIA_RECEIPTS", "0")
        cut._memo.clear()
        yield
        cut._memo.clear()


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("sheet")
    video = d / "ts.mp4"
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=60:d=12", "-f", "lavfi", "-i",
            "sine=f=440:d=12", "-c:v", "libx264", "-bf", "0", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(video)])
    silent = d / "silent.mp4"
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=4", "-c:v", "libx264", "-bf", "0",
            "-pix_fmt", "yuv420p", str(silent)])
    pngs = []
    for i, color in enumerate(((200, 40, 40), (40, 200, 40), (40, 40, 200))):
        p = d / f"still_{i}.png"
        Image.new("RGB", (400, 300), color).save(p)
        pngs.append(p)
    tb60 = d / "tb60.mp4"                     # a 1/60 timebase, as the OBS recordings have: one tick per frame
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60:d=3", "-c:v", "libx264", "-bf", "0",
            "-g", "60", "-pix_fmt", "yuv420p", "-video_track_timescale", "60", str(tb60)])
    mpegts = d / "gop1.ts"                    # its container clock starts at 1.4 s
    ff.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60:d=8", "-f", "lavfi", "-i",
            "sine=f=440:d=8", "-c:v", "libx264", "-bf", "0", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-f", "mpegts", str(mpegts)])
    return {"dir": d, "video": video, "silent": silent, "pngs": pngs, "ts": mpegts, "tb60": tb60}


def _cell_pixels(res: dict, c: dict) -> np.ndarray:
    png = np.asarray(Image.open(res["png"]).convert("RGB"))
    return png[c["y"]:c["y"] + c["h"], c["x"]:c["x"] + c["w"]]


def _regrab(src, c: dict) -> np.ndarray:
    (_t, _pts, img), = list(frames.at_times(src, [c["pts"]], crop=c["crop"], size=tuple(c["size"])))
    return img


# ------------------------------------------------------------------------------------------- sheet

def test_mixed_items_one_sheet_with_an_index(media):
    v = str(media["video"])
    res = sheet.sheet([*media["pngs"], (v, 1.5), {"src": v, "t": 7.25, "label": "the fight"}],
                      out=media["dir"] / "mixed.png")
    assert len(res["cells"]) == 5 and max(res["size"]) <= 1600
    labels = [c["label"] for c in res["cells"]]
    assert labels[:3] == ["still_0.png", "still_1.png", "still_2.png"]
    assert labels[3] == "0:01.500" and labels[4] == "the fight"
    index = json.loads(Path(res["index"]).read_text(encoding="utf-8"))
    assert index["cells"][3]["pts"] == pytest.approx(1.5) and index["png"] == res["png"]
    assert res["api"] == "arsenal.media.sheet/v0" and res["blind"]
    # a still keeps its colour, a video cell holds exactly the re-grabbed frame
    assert tuple(_cell_pixels(res, res["cells"][0])[5, 5]) == (200, 40, 40)
    for c in res["cells"][3:]:
        img = _regrab(v, c)
        assert hashlib.md5(img.tobytes()).hexdigest() == c["md5"]
        assert np.array_equal(_cell_pixels(res, c), img)


def test_a_cell_between_frames_shows_the_frame_it_labels(media):
    """2.625 s lies between frames 2.6167 and 2.6333: the cell must show 2.6333 and say so. A plain at_times(2.625)
    returned the earlier frame under the later pts (frames.py's CFR duplicate; sheet._grab picks frames by pts)."""
    v = str(media["video"])
    res = sheet.sheet([(v, 2.625), (v, 3.875), (v, 5.1251)], cell_w=240, out=media["dir"] / "between.png")
    decoded = {round(t, 6): img for t, img in frames.frames(v, start=0.0, dur=6.0, size=(240, 134), hw=None)}
    for c, want in zip(res["cells"], (2.633333, 3.883333, 5.133333)):
        assert c["pts"] == pytest.approx(want, abs=1e-5) and tuple(c["size"]) == (240, 134)
        assert np.array_equal(_cell_pixels(res, c), decoded[min(decoded, key=lambda t: abs(t - want))])


def test_long_edge_stays_under_max_however_many_cells(media):
    v = str(media["video"])
    res = sheet.sheet([(v, i * 0.19) for i in range(60)], cell_w=600, out=media["dir"] / "many.png")
    assert max(res["size"]) <= 1600 and len(res["cells"]) == 60
    assert Image.open(res["png"]).size == tuple(res["size"])
    tall = sheet.sheet([(v, i * 0.5) for i in range(20)], cols=1, out=media["dir"] / "tall.png")
    assert max(tall["size"]) <= 1600


def test_zoom_adds_a_magnified_cell_after_each_item(media):
    v = str(media["video"])
    res = sheet.sheet([(v, 2.0), (v, 4.0)], zoom=[(0, 0, 64, 36)], cell_w=384, out=media["dir"] / "zoom.png")
    kinds = [c["zoom_of"] for c in res["cells"]]
    assert kinds == [None, 0, None, 1]
    z = res["cells"][1]
    assert z["upscale"] >= 5 and z["label"].startswith(f"zoom x{z['upscale']}")
    assert (z["w"], z["h"]) == (64 * z["upscale"], 36 * z["upscale"])
    small = _regrab(v, z)                                   # the zoom cell is the crop, magnified by nearest
    big = np.repeat(np.repeat(small, z["upscale"], axis=0), z["upscale"], axis=1)
    assert np.array_equal(_cell_pixels(res, z), big)


def test_fraction_and_pixel_crops_make_the_same_cell(media):
    v = str(media["video"])
    px = sheet.sheet([{"src": v, "t": 3.0, "crop": (160, 90, 320, 180)}], out=media["dir"] / "px.png")
    fr = sheet.sheet([{"src": v, "t": 3.0, "crop": (0.25, 0.25, 0.5, 0.5)}], out=media["dir"] / "fr.png")
    assert px["cells"][0]["md5"] == fr["cells"][0]["md5"] and px["cells"][0]["crop"] == [160, 90, 320, 180]


def test_clock_adds_game_time_to_labels(media):
    clock = {"schema": "studio.clockmap.v1", "passes": [{"id": "a", "file": [0, 5], "speed": 1.0, "offset": 120.0},
                                                        {"id": "b", "file": [5, 12], "speed": 0.25, "offset": 300}]}
    v = str(media["video"])
    res = sheet.sheet([(v, 2.0), (v, 8.0)], clock=clock, out=media["dir"] / "clock.png")
    assert res["cells"][0]["label"] == "0:02.000  g 2:02"
    assert res["cells"][1]["label"] == "0:08.000  g 5:02"          # 0.25 * 8 + 300 = 302 s


def test_bad_items_fail_closed(media):
    with pytest.raises(ff.MediaError, match="give it a time"):
        sheet.sheet([str(media["video"])])
    with pytest.raises(ff.MediaError, match="no such file"):
        sheet.sheet([media["dir"] / "missing.png"])
    with pytest.raises(ff.MediaError, match="at least one"):
        sheet.sheet([])


def test_in_memory_images_for_storyboard(media):
    arr = np.zeros((90, 160, 3), np.uint8)
    arr[:, :80] = 255
    res = sheet.sheet([{"image": arr, "src": str(media["video"]), "t": 1.0}, {"image": arr, "label": "b"}],
                      cols=2, cell_w=160, out=media["dir"] / "mem.png")
    assert [c["label"] for c in res["cells"]] == ["0:01.000", "b"]
    assert np.array_equal(_cell_pixels(res, res["cells"][0]), arr)


# ------------------------------------------------------------------------------------------- video_sheet

def test_video_sheet_6x5_recipe_times_and_honest_labels(media):
    """The tested recipe (fps=1/T, tile=6x5) labels tile k with k*T but shows the frame at k*T + T/2 - 1 frame;
    video_sheet keeps the 6x5 grid and the k*T times, and each cell really is the frame at its label."""
    v = str(media["video"])
    res = sheet.video_sheet(v, n=30, cols=6, start=0, end=12, keyframes_only=False, out=media["dir"] / "6x5.png")
    assert (res["cols"], res["rows"], len(res["cells"])) == (6, 5, 30) and max(res["size"]) <= 1600
    assert [c["pts"] for c in res["cells"]] == pytest.approx([k * 0.4 for k in range(30)], abs=1e-6)
    assert res["cells"][7]["label"] == "0:02.800"
    for c in res["cells"][::9]:
        assert np.array_equal(_cell_pixels(res, c), _regrab(v, c))
    # the recipe, run tonight on the same file: same grid, row-major, but half a slot late
    T = 0.4
    rec = ff.run(["-v", "error", "-i", v, "-vf", f"fps=1/{T},scale=320:-2,tile=6x5", "-frames:v", "1",
                  "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"], binary=True)
    grid = np.frombuffer(rec.stdout, np.uint8).reshape(5 * 180, 6 * 320, 3).astype(np.float32)
    for k in (0, 7, 29):
        tile = grid[(k // 6) * 180:(k // 6 + 1) * 180, (k % 6) * 320:(k % 6 + 1) * 320]
        (_t, at_label, a), (_t2, shown, b) = frames.at_times(v, [k * T, k * T + T / 2 - 1 / 60], size=(320, 180))
        assert np.abs(b.astype(np.float32) - tile).mean() < 2.0 < np.abs(a.astype(np.float32) - tile).mean()


@pytest.mark.parametrize("ratio", [0.0, 100.0])
def test_video_sheet_keyframes_both_decode_paths_agree(media, monkeypatch, ratio):
    monkeypatch.setattr(sheet, "SCAN_MAX_RATIO", ratio)      # 0: one process per keyframe; 100: one scan pass
    v = str(media["video"])
    res = sheet.video_sheet(v, n=6, cols=3, out=media["dir"] / f"kf_{ratio}.png")
    kfs = cut.facts(v)["keyframes"]
    assert [c["pts"] for c in res["cells"]] == pytest.approx([0.0, 2.0, 4.0, 6.0, 8.0, 10.0])
    assert all(any(abs(c["pts"] - k) < 1e-6 for k in kfs) for c in res["cells"])
    for c in res["cells"]:
        assert np.array_equal(_cell_pixels(res, c), _regrab(v, c))


def test_video_sheet_short_span_collapses_duplicate_keyframes(media):
    res = sheet.video_sheet(str(media["video"]), n=10, start=2.0, end=5.0, out=media["dir"] / "short.png")
    assert res["picked"] == len(res["cells"]) == 3                  # keyframes at 2, 3 and 4 s only


# ------------------------------------------------------------------------------------------- filmstrip

def test_filmstrip_is_the_1920x256_recipe_with_slot_middles(media):
    v = str(media["video"])
    res = sheet.filmstrip(v, 2.0, 12.0, out=media["dir"] / "strip.png")
    assert res["size"] == [1920, 256] and res["tile"] == [240, 136]
    assert Image.open(res["png"]).size == (1920, 256)
    assert [c["t"] for c in res["cells"]] == pytest.approx([2.0 + (i + 0.5) * 1.25 for i in range(8)])
    w = res["waveform"]
    assert w["sample_rate"] == 44100 and w["samples"] == pytest.approx(10 * 44100, abs=2048)
    assert w["peak_dbfs"] == pytest.approx(-18.1, abs=1.0)           # lavfi sine: amplitude 1/8
    for c in res["cells"][::3]:
        assert np.array_equal(_cell_pixels(res, c), _regrab(v, c))


def test_filmstrip_words_clock_and_no_audio(media):
    words = {"words": [{"start": 3.0, "end": 3.4, "word": "flash"}, {"start": 3.05, "end": 3.3, "word": "now"}]}
    res = sheet.filmstrip(str(media["video"]), 2.0, 6.0, n=4, width=960, words=words,
                          clock=lambda t: 60 + t, out=media["dir"] / "words.png")
    assert res["size"][0] == 960 and res["waveform"]["peak_dbfs"] < -10
    quiet = sheet.filmstrip(str(media["silent"]), 0.0, 4.0, out=media["dir"] / "silent.png")
    assert quiet["waveform"] is None and quiet["size"] == [1920, 256]


def test_waveform_memory_stays_flat_on_a_long_span(media):
    peak, rms, n = sheet._envelope(str(media["video"]), 0.0, 12.0, 0, 1920, 48000)
    assert len(peak) == 1920 and n == pytest.approx(576000, abs=2048)
    assert float(peak.min()) > 0.1 and float(rms.max()) <= float(peak.max())


# ------------------------------------------------------------------------------------------- MPEG-TS clock

def _all_frames(path, size) -> np.ndarray:
    """Every frame decoded from the file start with no seek: the reference a seek bug cannot share."""
    res = ff.run(["-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode", "passthrough", "-vf",
                  f"scale={size[0]}:{size[1]}:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"],
                 binary=True)
    return np.frombuffer(res.stdout, np.uint8).reshape(-1, size[1], size[0], 3)


def _shows_its_label(res: dict, src) -> None:
    """Every cell's pixels are exactly the frame its pts names, counted from the video's start_time."""
    v0 = cut.facts(src)["video"]["start"]
    ref = {}
    for c in res["cells"]:
        size = tuple(c["size"])
        if size not in ref:
            ref[size] = _all_frames(src, size)
        k = round((c["pts"] - v0) * 60)
        assert np.array_equal(_cell_pixels(res, c), ref[size][k]), (c["pts"], k)


def test_a_container_that_starts_at_1_4_s_gets_the_right_frames(media, monkeypatch):
    """Before the fix the keyframe cells were the frame 2 s after their label, and sheet() through frames.at_times
    hung on this file (its rawvideo output repeated a frame dozens of times and its stderr reader deadlocked)."""
    ts = media["ts"]
    v0 = cut.facts(ts)["video"]["start"]
    assert cut.facts(ts)["format_start"] == pytest.approx(1.4, abs=0.01)
    res = sheet.sheet([(ts, 2.5), (ts, 2.7), (ts, 6.05)], cell_w=160, out=media["dir"] / "ts.png")
    for c, t in zip(res["cells"], (2.5, 2.7, 6.05)):
        assert t - 1e-3 <= c["pts"] < t - 1e-3 + 1 / 60            # the first frame at or after t, as at_times
    _shows_its_label(res, ts)
    for ratio in (0.0, 100.0):
        monkeypatch.setattr(sheet, "SCAN_MAX_RATIO", ratio)
        vs = sheet.video_sheet(ts, n=4, cols=4, start=3.0, end=7.0, cell_w=160, out=media["dir"] / f"ts_kf{ratio}.png")
        # 3.0-7.0 are file times: the keyframes inside are 3, 4, 5 and 6 s after the first frame (until the house
        # clock ruling the span was read on the container's clock, 1.4 s earlier, and these were 2, 3, 4 and 5)
        assert [c["pts"] for c in vs["cells"]] == pytest.approx([v0 + k for k in (3, 4, 5, 6)], abs=1e-5)
        _shows_its_label(vs, ts)
    strip = sheet.filmstrip(ts, 2.0, 6.0, n=4, width=640, out=media["dir"] / "ts_strip.png")
    assert [c["pts"] for c in strip["cells"]] == pytest.approx([2.5, 3.5, 4.5, 5.5], abs=1 / 60)
    _shows_its_label(strip, ts)
    assert strip["waveform"]["samples"] == pytest.approx(4 * 44100, abs=2048)


def test_a_one_tick_per_frame_timebase_grabs_every_cell(media):
    """On a 1/60 timebase, trim bounds round to whole frames: a quarter-frame end margin dropped the frame at 0 s
    (measured on the 17-51-11 recording)."""
    v = media["tb60"]
    res = sheet.sheet([(v, 0.0), (v, 1.0), (v, 2.99)], cell_w=160, out=media["dir"] / "tb60.png")
    assert [c["pts"] for c in res["cells"]] == pytest.approx([0.0, 1.0, 2.983333], abs=1e-5)
    _shows_its_label(res, v)
    for c in res["cells"]:
        assert np.array_equal(_cell_pixels(res, c), _regrab(v, c))


# ------------------------------------------------------------------------------------------- fail closed

def test_layout_never_passes_the_long_edge_and_refuses_what_cannot_fit():
    tall = sheet.sheet([{"image": np.zeros((2000, 20, 3), np.uint8), "label": "tall"}])
    assert max(tall["size"]) <= 1600
    with pytest.raises(ff.MediaError, match="cannot fit"):
        sheet.sheet([{"image": np.zeros((90, 160, 3), np.uint8), "label": "x"}] * 300, cols=1)
    with pytest.raises(ff.MediaError, match="fewer columns"):
        sheet.sheet([{"image": np.zeros((90, 160, 3), np.uint8)}] * 120, cols=120)


def test_spans_tracks_and_images_that_do_not_exist_fail_closed(media):
    v = str(media["video"])
    with pytest.raises(ff.MediaError, match="bad span"):
        sheet.filmstrip(v, 20.0, 30.0, n=4)
    with pytest.raises(ff.MediaError, match="bad span"):
        sheet.filmstrip(v, 6.0, 30.0, n=4)
    with pytest.raises(ff.MediaError, match="bad span"):
        sheet.video_sheet(v, start=2.0, end=40.0)
    with pytest.raises(ff.MediaError, match="missing audio track 5"):
        sheet.filmstrip(v, 1.0, 3.0, track=5)
    bad = media["dir"] / "zero.png"
    bad.write_bytes(b"")
    with pytest.raises(ff.MediaError, match="cannot read the image"):
        sheet.sheet([bad])


# ------------------------------------------------------------------------------------------- CLI

def test_cli_sheet_and_filmstrip(media, capsys):
    v = str(media["video"])
    assert sheet.cli("sheet", [f"{v}@1.5", f"{v}@0:03", "--out", str(media["dir"] / "cli.png")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert Path(out["png"]).is_file() and out["cols"] >= 1
    assert sheet.cli("filmstrip", [v, "0:02", "0:04", "--n", "4", "--out", str(media["dir"] / "cli_s.png")]) == 0
    assert json.loads(capsys.readouterr().out)["size"][1] > 120


# ------------------------------------------------------------------------------------------- the real recording

@pytest.mark.skipif(not RECORDING.is_file(), reason="Daniel's 2026-10-11 17-51-11 recording not on this machine")
def test_recording_keyframe_sheet_with_game_time():
    res = sheet.video_sheet(RECORDING, n=30, cols=6, clock=CLOCKMAP if CLOCKMAP.is_file() else None)
    assert (res["cols"], res["rows"], len(res["cells"])) == (6, 5, 30)
    assert max(res["size"]) <= 1600
    assert res["wall_s"] < 15                                        # measured 4.0 s
    if CLOCKMAP.is_file():
        assert any("  g " in c["label"] for c in res["cells"])
    c = res["cells"][11]
    assert np.array_equal(_cell_pixels(res, c), _regrab(RECORDING, c))
