"""arsenal.media on the house clock: a file time is seconds from the file's start (README, "The house clock").

An MPEG-TS starts its own clock late (1.4 s here), so its container pts and its file times differ by 1.4 s; with the
sound muxed ahead of the picture its first frame is not at 0 either (0.021 s in `ts`; 0.521 s in `late`, whose
picture starts 0.5 s after its sound). Every primitive must name a frame by the same file time: probe.keyframes and
the sidecar, frames, cut.plan/cut, sheet cells, shots, and the editor's render and the numbers its page offsets by.

The references here are independent of the code under test: a decode with no seek at all (frame k of a constant-rate
stream sits at the video's first file time + k / fps) and ffprobe's own stream and format start times. OBS MP4 starts
every stream at 0, so none of this differs on Daniel's recordings.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from arsenal.media import cut, edit, ff, frames, probe, sheet, shots

FPS = 30
TS_START = 1.4                       # the mpegts muxer's default: the container clock starts 1.4 s in
FAST = {"id": "test_x264", "width": "source", "height": "source", "fps": "source", "fit": "pad", "loudness": "none",
        "vcodec": ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p"],
        "acodec": ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"], "container": "mp4"}


@pytest.fixture(scope="module", autouse=True)
def _state(tmp_path_factory):
    """State (sidecars, facts cache, proxies, edits) in a temp folder; the saved house ffmpeg is still found."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ARSENAL_MEDIA_STATE", str(tmp_path_factory.mktemp("state")))
        mp.setenv("ARSENAL_MEDIA_RECEIPTS", "0")
        cut._memo.clear()
        yield
        cut._memo.clear()


def _clocks(path) -> SimpleNamespace:
    """ffprobe's starts: the container's own (format start_time) and each stream's first time on the file clock."""
    j = ff.probe_json(path, entries=("-show_entries", "format=start_time,format_name:stream=codec_type,start_time"))
    f0 = float(j["format"]["start_time"])
    first = {}
    for s in j["streams"]:
        first.setdefault(s["codec_type"], float(s["start_time"]) - f0)
    return SimpleNamespace(f0=f0, v0=first["video"], a0=first.get("audio"), format=j["format"]["format_name"])


def _make_ts(out: Path, *, video_delay: float = 0.0) -> Path:
    """testsrc2 for 3 s then testsrc for 5 s (a hard cut at 3 s, every frame distinct), 30 fps, libx264 -g 60 (a
    keyframe every 2 s, none at the cut), a noise track; MPEG-TS, so the container clock starts at 1.4 s. The delay
    goes on the first segment only: concat appends the second after it, so the picture stays gapless."""
    delay = ["-itsoffset", f"{video_delay}"] if video_delay else []
    ff.run(["-v", "error", "-y", *delay, "-f", "lavfi", "-i", f"testsrc2=s=320x180:r={FPS}:d=3",
            "-f", "lavfi", "-i", f"testsrc=s=320x180:r={FPS}:d=5",
            "-f", "lavfi", "-i", "anoisesrc=d=8.6:c=white:seed=7:a=0.3",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-bf", "0", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-f", "mpegts", str(out)])
    return out


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    d = tmp_path_factory.mktemp("house_clock")
    ts = _make_ts(d / "clock.ts")
    late = _make_ts(d / "late picture.ts", video_delay=0.5)
    mkv = d / "clock 1.4.mkv"             # the editor imports MKV, not TS: the same packets, the same 1.4 s clock
    ff.run(["-v", "error", "-y", "-copyts", "-i", str(ts), "-map", "0", "-c", "copy", str(mkv)])
    return {"dir": d, "ts": ts, "late": late, "mkv": mkv}


@pytest.fixture(params=["ts", "late"])
def clip(request, media):
    return media[request.param]


def test_the_fixtures_are_what_they_claim(media):
    for key, v0 in (("ts", 0.021), ("late", 0.521), ("mkv", 0.021)):
        c = _clocks(media[key])
        assert c.f0 == pytest.approx(TS_START, abs=0.01), key
        assert c.v0 == pytest.approx(v0, abs=0.005) and c.a0 == pytest.approx(0.0, abs=1e-6), key
    assert "mpegts" in _clocks(media["ts"]).format and "matroska" in _clocks(media["mkv"]).format


# ------------------------------------------------------------------------------------------- references

_REF: dict = {}


def _reference(path, size=None) -> np.ndarray:
    """Every frame, decoded from the start with no seek at all: frame k sits at file time v0 + k / FPS."""
    key = (str(path), tuple(size) if size else None)
    if key not in _REF:
        vf = ["-vf", f"scale={size[0]}:{size[1]}:flags=area"] if size else []
        w, h = size or (320, 180)
        res = ff.run(["-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode", "passthrough", *vf,
                      "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"], binary=True)
        _REF[key] = np.frombuffer(res.stdout, np.uint8).reshape(-1, h, w, 3)
    return _REF[key]


def _grid(path) -> np.ndarray:
    """File time of every reference frame."""
    return _clocks(path).v0 + np.arange(len(_reference(path))) / FPS


def _index_at(path, t: float) -> int:
    """The reference frame shown at file time t: the first whose time >= t - 1 ms (frames.at_times' rule)."""
    return int(np.flatnonzero(_grid(path) >= t - 1e-3)[0])


def _closest(path, img: np.ndarray) -> int:
    ref = _reference(path).astype(np.float64)
    return int(np.argmin(((ref - img.astype(np.float64)) ** 2).mean(axis=(1, 2, 3))))


def _decode_all(path) -> np.ndarray:
    res = ff.run(["-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode", "passthrough", "-pix_fmt", "rgb24",
                  "-f", "rawvideo", "pipe:1"], binary=True)
    return np.frombuffer(res.stdout, np.uint8).reshape(-1, 180, 320, 3)


def _pcm(path, dur: float = 9.0) -> np.ndarray:
    """Track 0 as mono 48 kHz from the start, no seek, each sample placed by its own timestamp (a cut's audio may
    start a partial packet late): sample n sits at the track's first file time + n / 48000."""
    res = ff.run(["-v", "error", "-i", str(path), "-map", "0:a:0", "-t", f"{dur}", "-af",
                  "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], binary=True)
    return np.frombuffer(res.stdout, np.float32)


def _lag_ms(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    c = np.fft.irfft(np.fft.rfft(a[:n], 2 * n) * np.conj(np.fft.rfft(b[:n], 2 * n)))
    k = int(np.argmax(c))
    return (k if k < n else k - 2 * n) / 48.0


def _keyframes(path):
    """The keyframes by definition: packet flags K, container pts minus the format start_time."""
    res = ff.run(["-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,flags", "-of",
                  "csv=p=0", str(path)], tool="ffprobe")
    f0 = _clocks(path).f0
    return sorted(float(p) - f0 for p, _, fl in (ln.partition(",") for ln in res.stdout.split()) if "K" in fl)


# ------------------------------------------------------------------------------------------- probe

def test_probe_keyframes_are_file_times(clip):
    v0 = _clocks(clip).v0
    want = [v0 + 2.0 * k for k in range(4)]
    assert _keyframes(clip) == pytest.approx(want, abs=1e-3)
    assert probe.keyframes(clip) == pytest.approx(want, abs=1e-3)
    decoded = [t for t, _ in frames.keyframes(clip, size=(32, 18), hw=None)]
    assert decoded == pytest.approx(want, abs=1e-3)          # the decoder's own labels agree with the packet scan


def test_the_sidecar_stores_file_times_and_says_where_the_container_clock_starts(clip):
    c = _clocks(clip)
    sc = probe.probe(clip, keyframes=True)
    assert sc["keyframes"] == pytest.approx(_keyframes(clip), abs=1e-3)
    assert sc["video"]["start_s"] == pytest.approx(c.v0, abs=1e-3)       # where the first frame sits in the file
    assert sc["start_s"] == pytest.approx(c.f0, abs=1e-3)                # file time 0 on the container's clock
    assert sc["clock"] == "file"


def test_a_sidecar_written_on_the_container_clock_is_moved_onto_the_file_clock(media):
    ts = media["ts"]
    sc = probe.probe(ts, keyframes=True)
    path = Path(sc["sidecar_path"])
    old = json.loads(path.read_text(encoding="utf-8"))
    old.pop("clock", None)                                              # what the 2026-10-12 build wrote
    old["keyframes"] = [k + old["start_s"] for k in old["keyframes"]]
    old["video"]["start_s"] += old["start_s"]
    path.write_text(json.dumps(old), encoding="utf-8")
    again = probe.probe(ts)
    assert again["keyframes"] == pytest.approx(_keyframes(ts), abs=1e-3)
    assert again["video"]["start_s"] == pytest.approx(_clocks(ts).v0, abs=1e-3)
    assert json.loads(path.read_text(encoding="utf-8"))["clock"] == "file"


# ------------------------------------------------------------------------------------------- frames

def test_frames_name_every_frame_by_its_file_time(clip):
    got = list(frames.frames(clip, size=(32, 18), hw=None))
    assert [t for t, _ in got] == pytest.approx(list(_grid(clip)), abs=1e-3)


def test_at_times_is_one_clock_before_and_after_the_first_keyframe(clip):
    """A window that needs no seek and one that seeks must agree: the first decodes from the file's start."""
    for t_req, t_pts, img in frames.at_times(clip, [0.0, 0.3, 0.6, 3.0, 5.55]):
        k = _index_at(clip, t_req)
        assert t_pts == pytest.approx(_grid(clip)[k], abs=1e-3), t_req
        assert np.array_equal(img, _reference(clip)[k]), t_req


# ------------------------------------------------------------------------------------------- cut

def test_cut_plan_speaks_file_time(clip):
    p = cut.plan(clip, 3.0, 5.0)
    (_, t_pts, _), = list(frames.at_times(clip, [3.0], size=(32, 18)))
    kfs = _keyframes(clip)
    assert p["mode_suggested"] == "smart"
    assert p["start_real"] == pytest.approx(t_pts, abs=1e-4)
    assert p["start_keyframe"] == pytest.approx(max(k for k in kfs if k <= t_pts), abs=1e-4)
    assert p["next_keyframe"] == pytest.approx(min(k for k in kfs if k > t_pts), abs=1e-4)


@pytest.mark.parametrize("mode", ["smart", "copy", "exact"])
def test_a_cut_holds_the_frames_and_sound_of_its_file_time_range(media, mode):
    ts = media["ts"]
    out = media["dir"] / f"cut_{mode}.mp4"
    res = cut.cut(ts, 3.0, 5.0, out, mode=mode)
    assert res["mode"] == mode and res["verify"]["ok"], res["verify"]
    start = res["start_real"]
    k0 = _index_at(ts, start)
    assert _grid(ts)[k0] == pytest.approx(start, abs=1e-4)
    if mode == "copy":
        assert start == pytest.approx(max(k for k in _keyframes(ts) if k <= 3.0), abs=1e-4)
    else:
        assert start == pytest.approx(_grid(ts)[_index_at(ts, 3.0)], abs=1e-4)
    got = _decode_all(out)
    assert len(got) == res["frames"] == _index_at(ts, 5.0) - k0
    for i in (0, len(got) - 1):
        assert _closest(ts, got[i]) == k0 + i, (mode, i)
    if mode == "copy":
        assert np.array_equal(got[0], _reference(ts)[k0])             # a copied keyframe: the very same pixels
    c = _clocks(ts)
    src = _pcm(ts)
    off = int(round((start - c.a0) * 48000))
    lag = _lag_ms(_pcm(out, 1.5), src[off:off + 72000])
    assert abs(lag) < 2.0, (mode, lag)


def test_a_cut_of_a_picture_that_starts_late_starts_on_the_right_frame(media):
    late = media["late"]
    out = media["dir"] / "late_cut.mp4"
    res = cut.cut(late, 3.0, 4.0, out, mode="smart")
    assert res["verify"]["ok"], res["verify"]
    k0 = _index_at(late, 3.0)
    assert res["start_real"] == pytest.approx(_grid(late)[k0], abs=1e-4)
    assert _closest(late, _decode_all(out)[0]) == k0


# ------------------------------------------------------------------------------------------- sheet

def _cell(res: dict, c: dict) -> np.ndarray:
    png = np.asarray(Image.open(res["png"]).convert("RGB"))
    return png[c["y"]:c["y"] + c["h"], c["x"]:c["x"] + c["w"]]


def _regrab(src, c: dict) -> tuple:
    (_t, t_pts, img), = list(frames.at_times(src, [c["pts"]], crop=c.get("crop"), size=tuple(c["size"])))
    return t_pts, img


def test_sheet_cells_are_labelled_with_file_times_and_regrab_bit_identical(clip, media):
    times = [0.3, 3.0, 6.05]
    res = sheet.sheet([(clip, t) for t in times] + [{"src": str(clip), "t": 4.2, "crop": (0.25, 0.25, 0.5, 0.5)}],
                      cell_w=160, out=media["dir"] / f"sheet_{Path(clip).stem}.png")
    for c, t in zip(res["cells"], times + [4.2]):
        k = _index_at(clip, t)
        assert c["pts"] == pytest.approx(_grid(clip)[k], abs=1e-4), t
        t_pts, img = _regrab(clip, c)
        assert t_pts == pytest.approx(c["pts"], abs=1e-6)
        assert np.array_equal(_cell(res, c), img), t
        assert c["label"].startswith(sheet.fmt_time(c["pts"])), c["label"]
    full = res["cells"][1]
    assert np.array_equal(_cell(res, full), _reference(clip, full["size"])[_index_at(clip, 3.0)])


@pytest.mark.parametrize("ratio", [0.0, 100.0])            # one process per keyframe, or one keyframe-only pass
def test_video_sheet_keyframe_cells_are_the_keyframes_on_the_file_clock(clip, media, monkeypatch, ratio):
    monkeypatch.setattr(sheet, "SCAN_MAX_RATIO", ratio)
    vs = sheet.video_sheet(clip, n=4, cols=4, cell_w=160, out=media["dir"] / f"vs_{Path(clip).stem}_{ratio}.png")
    assert [c["pts"] for c in vs["cells"]] == pytest.approx(_keyframes(clip), abs=1e-4)
    for c in vs["cells"]:
        t_pts, img = _regrab(clip, c)
        assert t_pts == pytest.approx(c["pts"], abs=1e-6)
        assert np.array_equal(_cell(vs, c), img), c["pts"]


def test_filmstrip_slots_and_waveform_on_the_file_clock(clip, media):
    strip = sheet.filmstrip(clip, 2.0, 6.0, n=4, width=640, out=media["dir"] / f"strip_{Path(clip).stem}.png")
    for c, mid in zip(strip["cells"], (2.5, 3.5, 4.5, 5.5)):
        assert c["pts"] == pytest.approx(_grid(clip)[_index_at(clip, mid)], abs=1e-4), mid
        png = np.asarray(Image.open(strip["png"]).convert("RGB"))[c["y"]:c["y"] + c["h"], c["x"]:c["x"] + c["w"]]
        assert np.array_equal(png, _regrab(clip, c)[1]), mid
    assert strip["waveform"]["samples"] == pytest.approx(4 * 48000, abs=2048)


def test_a_filmstrip_from_the_files_start_draws_the_sound_where_it_is(media):
    """The late picture's sound starts at file time 0: a strip of the first second has a full waveform."""
    strip = sheet.filmstrip(media["late"], 0.0, 1.0, n=2, width=320, out=media["dir"] / "strip_head.png")
    assert strip["waveform"]["samples"] == pytest.approx(48000, abs=2048)
    assert strip["cells"][0]["pts"] == pytest.approx(_grid(media["late"])[_index_at(media["late"], 0.25)], abs=1e-4)


# ------------------------------------------------------------------------------------------- shots

def test_a_shot_change_is_found_at_its_file_time(media):
    late = media["late"]
    res = shots.shots(late, detector="spike")
    v0 = _clocks(late).v0
    (found,) = res["cuts"]
    assert found["t"] == pytest.approx(v0 + 3.0, abs=1 / FPS + 1e-3)       # 3.0 s into the picture
    assert res["video_start_s"] == pytest.approx(v0, abs=1e-3)
    assert res["shots"][0][0] == 0.0 and res["shots"][-1][1] == pytest.approx(res["duration_s"])


# ------------------------------------------------------------------------------------------- the editor

@pytest.fixture(scope="module")
def imported(media):
    rec = edit.import_media(media["mkv"])
    edit.build_demux(rec["id"])
    return edit.get_media(rec["id"])


def test_the_page_gets_file_times_and_the_container_start_it_converts_by(media, imported):
    """The page's frame grid, keyframe ticks, lane offsets and peaks all count from the file's start; Chrome's
    currentTime counts on the container clock, so the page needs container_start_s to convert (measured on
    Chrome 154: a source whose container clock starts at 1.4 s opens at currentTime 1.4)."""
    from arsenal.media import editapi
    c = _clocks(media["mkv"])
    view = editapi.media_view(imported)
    assert view["container_start_s"] == pytest.approx(c.f0, abs=1e-3)
    assert view["video"]["start_s"] == pytest.approx(c.v0, abs=1e-3)
    assert [a["start_s"] for a in view["audio"]] == pytest.approx([c.a0], abs=1e-3)
    assert edit.track_starts(imported) == pytest.approx([c.a0], abs=1e-3)
    assert edit.keyframes(imported["id"]) == pytest.approx(_keyframes(media["mkv"]), abs=1e-3)
    try:
        edit.build_peaks(imported["id"])
    except edit.NotBuilt as exc:
        pytest.skip(str(exc))
    body = edit.read_json(edit.derived_path(edit.get_media(imported["id"]), "peaks", 0))
    assert body["start_s"] == pytest.approx(c.a0, abs=1e-3)


def test_the_render_shows_the_frame_and_sound_the_page_names(media, imported, tmp_path):
    mkv = media["mkv"]
    doc, _ = edit.add_clip(edit.new_project("clock", settings={"fps": FPS, "width": 320, "height": 180}),
                           imported, src_in=3.0, src_out=4.5)
    res = edit.render(edit.save(doc), FAST, out=tmp_path / "clock.mp4")
    out = Path(res["path"])
    got = _decode_all(out)
    assert _closest(mkv, got[0]) == _index_at(mkv, 3.0)
    c = _clocks(mkv)
    src = _pcm(mkv)
    off = int(round((3.0 - c.a0) * 48000))
    assert abs(_lag_ms(_pcm(out, 1.4), src[off:off + 67200])) < 2.0

