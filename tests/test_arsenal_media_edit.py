"""arsenal.media.edit: the timeline document (round trip, one writer by revision), the clip operations and their
refusals, and the render -- two clips, two audio tracks, one muted -- checked with ffprobe (duration to one frame)
and ebur128 behind a band-pass (the muted track's tone is absent, the other's is there).

Fixtures are synthetic and made at test time: testsrc2 + two sine tracks titled Voice (440 Hz) and Game (1000 Hz).
State is isolated with ARSENAL_MEDIA_STATE; nothing is written near a real recording."""
from __future__ import annotations

import array
import copy
import json
import re
import shutil
import threading
from pathlib import Path

import pytest

from arsenal.media import edit, ff

ORACLE = Path(r"E:\AI-Setup\state\arsenal\media-oracles\clips\multitrack_test.mp4")
FAST = {"id": "test_x264", "width": "source", "height": "source", "fps": "source", "fit": "pad", "loudness": "none",
        "vcodec": ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p"],
        "acodec": ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"], "container": "mp4"}


def make_clip(path: Path, seconds: float = 4.0) -> Path:
    acodec = ["-c:a", "libopus", "-b:a", "96k"] if ff.has_encoder("libopus") else ["-c:a", "aac", "-b:a", "96k"]
    ff.run(["-f", "lavfi", "-i", f"testsrc2=s=320x240:r=30:d={seconds}",
            "-f", "lavfi", "-i", f"sine=f=440:sample_rate=48000:d={seconds}",
            "-f", "lavfi", "-i", f"sine=f=1000:sample_rate=48000:d={seconds}",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast", "-g", "15",
            "-bf", "0", "-pix_fmt", "yuv420p", *acodec,
            "-metadata:s:a:0", "title=Voice", "-metadata:s:a:1", "title=Game", "-y", str(path)])
    return path


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    return make_clip(tmp_path_factory.mktemp("edit_src") / "two tracks.mkv")


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture()
def media(clip):
    return edit.import_media(clip)


def band_loudness(path: Path, hz: int) -> float:
    """Integrated loudness (LUFS) of the first audio stream through a narrow band-pass at hz."""
    res = ff.run(["-nostats", "-i", str(path), "-filter_complex",
                  f"[0:a:0]bandpass=f={hz}:width_type=q:w=8,ebur128=framelog=quiet", "-f", "null", "-"])
    tail = res.stderr[res.stderr.rfind("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))


def video_duration(path: Path) -> float:
    j = ff.probe_json(path, entries=("-show_streams",))
    return float(next(s for s in j["streams"] if s["codec_type"] == "video")["duration"])


# --------------------------------------------------------------------------------------------- document

def test_new_project_round_trips_as_lf_utf8_json(state):
    doc = edit.new_project("Draven review", settings={"fps": 30, "width": 1280, "height": 720})
    assert doc["api"] == "arsenal.media.timeline/v0" and doc["rev"] == 1
    assert re.fullmatch(edit.PID_PATTERN, doc["id"])
    assert doc["lanes"]["video"] == [{"id": "V1"}] and doc["lanes"]["audio"][0]["id"] == "A1"
    assert edit.load(doc["id"]) == doc
    raw = (state / "edits" / f"{doc['id']}.json").read_bytes()
    assert b"\r\n" not in raw and json.loads(raw.decode("utf-8")) == doc
    assert [p["id"] for p in edit.list_projects()] == [doc["id"]]


def test_a_document_names_what_it_is_a_projection_of():
    doc = edit.new_project("master field")
    assert doc["master"] == "timeline-v0"
    page = copy.deepcopy(doc)
    page.pop("master")                       # a client that does not know the field must not erase it
    assert edit.save(page, media_lookup=None)["master"] == "timeline-v0"


def test_save_takes_the_loaded_rev_and_a_stale_one_conflicts():
    doc = edit.new_project("p")
    saved = edit.save(dict(doc, name="renamed"))
    assert saved["rev"] == 2 and saved["name"] == "renamed" and saved["created_at"] == doc["created_at"]
    with pytest.raises(edit.Conflict) as err:
        edit.save(dict(doc, name="stale writer"))
    assert err.value.status == 409 and err.value.current["rev"] == 2 and err.value.current["name"] == "renamed"
    assert edit.load(doc["id"])["name"] == "renamed"


def test_two_writers_on_one_rev_one_wins_one_gets_409():
    doc = edit.new_project("race")
    gate = threading.Barrier(2)
    outcomes = []

    def writer(name):
        mine = dict(copy.deepcopy(doc), name=name)
        gate.wait()
        try:
            outcomes.append(("ok", edit.save(mine)["rev"]))
        except edit.Conflict as exc:
            outcomes.append(("409", exc.current["rev"]))

    threads = [threading.Thread(target=writer, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert sorted(o[0] for o in outcomes) == ["409", "ok"]
    assert all(o[1] == 2 for o in outcomes)
    assert edit.load(doc["id"])["rev"] == 2
    assert not list((edit.edits_dir()).glob("*.lock")) and not list(edit.edits_dir().glob(".*.tmp"))


# --------------------------------------------------------------------------------------------- media + ops

def test_import_reads_duration_and_titled_tracks(media, clip):
    assert re.fullmatch(edit.MID_PATTERN, media["id"])
    assert media["duration_s"] == pytest.approx(4.0, abs=0.05)
    assert media["n_audio"] == 2 and [t["label"] for t in media["audio"]] == ["Voice", "Game"]
    assert media["facts_from"] in ("catalog", "probe", "ffprobe")
    assert edit.get_media(media["id"])["path"] == str(clip.resolve())
    with pytest.raises(edit.EditError):
        edit.import_media(clip.with_suffix(".txt"))


def test_add_clip_names_lanes_from_the_tracks_and_appends(media):
    doc = edit.new_project("p")
    doc, a = edit.add_clip(doc, media, src_in=0.5, src_out=2.0)
    doc, b = edit.add_clip(doc, media, src_in=2.5, src_out=3.5)
    assert [ln["label"] for ln in doc["lanes"]["audio"]] == ["Voice", "Game"]
    assert a["at"] == 0.0 and b["at"] == pytest.approx(1.5)
    assert [x["lane"] for x in a["audio"]] == ["A1", "A2"] and a["audio"][1]["src_track"] == 1
    assert edit.duration(doc) == pytest.approx(2.5)
    assert edit.save(doc)["rev"] == 2


def test_operations_refuse_bad_ranges_overlaps_unknown_lanes_and_gains(media):
    doc, a = edit.add_clip(edit.new_project("p"), media, src_in=0.0, src_out=1.5)
    with pytest.raises(edit.EditError, match="before src_out"):
        edit.add_clip(doc, media, src_in=2.0, src_out=2.0)
    with pytest.raises(edit.EditError, match="past the media's end"):
        edit.add_clip(doc, media, src_in=1.0, src_out=9.0)
    with pytest.raises(edit.EditError, match="overlap on V1"):
        edit.add_clip(doc, media, src_in=0.0, src_out=1.0, at=1.0)
    with pytest.raises(edit.EditError, match="lane 'V2' does not exist"):
        edit.add_clip(doc, media, src_in=0.0, src_out=1.0, lane="V2")
    with pytest.raises(edit.EditError, match="gain_db"):
        edit.set_lane_gain(doc, "A1", gain_db=20)
    with pytest.raises(edit.EditError, match="not inside"):
        edit.split(doc, a["id"], 1.5)
    bad = copy.deepcopy(doc)
    bad["clips"][0]["audio"][0]["lane"] = "A9"
    assert any("A9" in p for p in edit.validate(bad))
    with pytest.raises(edit.EditError):
        edit.save(bad)
    assert edit.load(doc["id"])["rev"] == 1


def test_trim_split_move_remove_and_track_gain(media):
    doc, a = edit.add_clip(edit.new_project("p"), media, src_in=0.0, src_out=3.0)
    doc = edit.trim(doc, a["id"], src_in=0.5)            # dragging the head: the picture stays put on the timeline
    c = doc["clips"][0]
    assert (c["src_in"], c["at"]) == (0.5, 0.5)
    doc = edit.move(doc, a["id"], 0.0)
    doc, right = edit.split(doc, a["id"], 1.0)
    left = next(x for x in doc["clips"] if x["id"] == a["id"])
    assert (left["src_in"], left["src_out"]) == (0.5, 1.5)
    assert (right["src_in"], right["src_out"], right["at"]) == (1.5, 3.0, 1.0)
    doc = edit.set_clip_track_gain(doc, right["id"], 1, gain_db=-6, mute=True)
    entry = next(x for x in doc["clips"] if x["id"] == right["id"])["audio"][1]
    assert entry == {"src_track": 1, "lane": "A2", "gain_db": -6.0, "mute": True}
    doc = edit.remove(doc, a["id"])
    assert [x["id"] for x in doc["clips"]] == [right["id"]]
    assert edit.save(doc)["rev"] == 2


# --------------------------------------------------------------------------------------------- render

def test_render_two_clips_with_one_muted_track(media, tmp_path):
    doc, _ = edit.add_clip(edit.new_project("mix test", settings={"fps": 30, "width": 320, "height": 240}), media,
                           src_in=0.5, src_out=2.0)
    doc, _ = edit.add_clip(doc, media, src_in=2.5, src_out=3.5)
    doc = edit.save(doc)
    both = edit.render(doc, FAST, out_root=tmp_path / "renders")
    doc = edit.save(edit.set_lane_gain(doc, "A2", mute=True))
    muted = edit.render(doc, FAST, out_root=tmp_path / "renders")

    for res in (both, muted):
        out = Path(res["path"])
        assert out.is_file() and out.parent == tmp_path / "renders" / "mix test"
        assert video_duration(out) == pytest.approx(2.5, abs=1 / 30)       # the sum of the clips, to one frame
        assert res["duration_ok"] and res["api"] == "arsenal.media.edit/v0"
        streams = ff.probe_json(out, entries=("-show_streams",))["streams"]
        assert [s["codec_type"] for s in streams] == ["video", "audio"]
    assert Path(both["path"]) != Path(muted["path"])                       # never over an earlier render
    # Game (1000 Hz) is in the unmuted mix and gone from the muted one; Voice (440 Hz) is in both
    assert band_loudness(Path(both["path"]), 1000) > -30
    assert band_loudness(Path(muted["path"]), 1000) < band_loudness(Path(both["path"]), 1000) - 15
    assert band_loudness(Path(muted["path"]), 440) > -30
    qc = muted["qc"]
    assert qc is not None and ("skipped" in qc or qc.get("api") == "arsenal.media.qc/v0")


def test_render_fills_gaps_and_never_overwrites(media, tmp_path):
    doc, _ = edit.add_clip(edit.new_project("gap", settings={"fps": 30, "width": 320, "height": 240}), media,
                           src_in=0.0, src_out=1.0, at=0.5)
    doc = edit.save(doc)
    out = tmp_path / "gap.mp4"
    res = edit.render(doc, FAST, out=out)
    assert video_duration(out) == pytest.approx(1.5, abs=1 / 30) and res["duration_expected_s"] == pytest.approx(1.5)
    for existing in (out, Path(media["path"])):            # an earlier render, and the original itself
        with pytest.raises(edit.EditError, match="never overwrite"):
            edit.render(doc, FAST, out=existing)
    assert Path(media["path"]).stat().st_size == media["size"]


def test_trim_lossless_keeps_every_titled_track(media, tmp_path):
    doc, c = edit.add_clip(edit.new_project("lossless"), media, src_in=1.2, src_out=3.0)
    doc = edit.save(doc)
    try:
        res = edit.trim_lossless(doc, c["id"], out=tmp_path / "clip.mkv")
    except edit.NotBuilt as exc:
        pytest.skip(str(exc))
    out = Path(res["out"])
    assert out == tmp_path / "clip.mkv" and out.is_file() and res["mode"] in ("smart", "copy", "exact")
    streams = [s for s in ff.probe_json(out, entries=("-show_streams",))["streams"] if s["codec_type"] == "audio"]
    assert [(s.get("tags") or {}).get("title") for s in streams] == ["Voice", "Game"]
    assert res["frames"] == 54                              # 1.2-3.0 s at 30 fps, to the frame


def test_cli_new_add_trim_show(clip, capsys):
    assert edit.cli("edit", ["new", "cli project", "--fps", "30", "--width", "320", "--height", "240"]) == 0
    pid = json.loads(capsys.readouterr().out)["id"]
    assert edit.cli("edit", ["add", pid, str(clip), "--in", "0.5", "--out", "2"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["rev"] == 2 and added["clip"]["src_in"] == 0.5
    assert edit.cli("edit", ["trim", pid, added["clip"]["id"], "--out", "1.5"]) == 0
    assert json.loads(capsys.readouterr().out)["src_out"] == 1.5
    assert edit.cli("edit", ["split", pid, added["clip"]["id"], "0.5"]) == 0
    capsys.readouterr()
    assert len(edit.load(pid)["clips"]) == 2 and edit.load(pid)["rev"] == 4
    assert edit.cli("edit", ["trim", pid, added["clip"]["id"], "--out", "9"]) == 1


# --------------------------------------------------------------------------------------------- review fixes

def make_sync_clip(path: Path, audio_start: float) -> Path:
    """Black 160x120 at 30 fps with a white flash at absolute 2.0 s, and a PCM track that starts audio_start s into
    the container and beeps 1 kHz at absolute 2.0 s: a render either keeps the two together or it does not."""
    v = path.with_name(path.stem + " v.mkv")
    a = path.with_name(path.stem + " a.wav")
    ff.run(["-f", "lavfi", "-i", "color=c=black:s=160x120:r=30:d=4",
            "-vf", "drawbox=c=white:t=fill:enable='between(t,2,2.0999)'", "-c:v", "libx264", "-preset", "ultrafast",
            "-g", "15", "-bf", "0", "-pix_fmt", "yuv420p", "-y", str(v)])
    ff.run(["-f", "lavfi", "-i", f"aevalsrc=exprs='if(between(t,{2 - audio_start},{2.1 - audio_start}),"
                                 f"0.5*sin(2*PI*1000*t),0)':s=48000:d={4 - audio_start}", "-y", str(a)])
    ff.run(["-i", str(v), "-itsoffset", f"{audio_start}", "-i", str(a), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "pcm_s16le", "-y", str(path)])
    return path


@pytest.fixture(scope="module")
def sync_clips(clip, tmp_path_factory):
    folder = tmp_path_factory.mktemp("edit_sync")
    return {s: make_sync_clip(folder / f"flash beep audio at {s}.mkv", s) for s in (0.0, 0.5)}


def flash_and_beep(path: Path, fps: float = 30.0):
    """(time of the first frame brighter than mid-grey, time of the first sample over 0.1) in a render."""
    vid = ff.run(["-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", "scale=16:12,format=gray",
                  "-f", "rawvideo", "-"], binary=True).stdout
    flash = next((i / fps for i in range(len(vid) // 192) if sum(vid[i * 192:(i + 1) * 192]) > 128 * 192), None)
    pcm = array.array("f")
    pcm.frombytes(ff.run(["-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "48000",
                          "-f", "f32le", "-"], binary=True).stdout)
    beep = next((i / 48000 for i, x in enumerate(pcm) if abs(x) > 0.1), None)
    return flash, beep


@pytest.mark.parametrize("audio_start,src_in", [(0.5, 0.0), (0.5, 1.0), (0.0, 1.0)])
def test_render_keeps_picture_and_sound_together(sync_clips, tmp_path, audio_start, src_in):
    """Each stream is anchored on src_in, not on its own first timestamp: before, these three rendered the beep
    500 ms, 12 ms and 24 ms ahead of the flash."""
    media = edit.import_media(sync_clips[audio_start])
    doc, _ = edit.add_clip(edit.new_project("sync", settings={"fps": 30, "width": 160, "height": 120}), media,
                           src_in=src_in, src_out=3.9)
    res = edit.render(edit.save(doc), FAST, out=tmp_path / "sync.mp4")
    flash, beep = flash_and_beep(Path(res["path"]))
    assert flash == pytest.approx(2.0 - src_in, abs=0.5 / 30)
    assert beep == pytest.approx(2.0 - src_in, abs=0.002)


def test_contiguous_clips_keep_their_frames_and_duration_ok_holds_to_the_timeline(media, tmp_path):
    doc = edit.new_project("ten", settings={"fps": 30, "width": 320, "height": 240})
    for i in range(10):                                      # 0.1167 s each: 3.5 frames, the worst case for rounding
        doc, _ = edit.add_clip(doc, media, src_in=0.1 + i * 0.3, src_out=0.1 + i * 0.3 + 0.1167)
    segs = edit._segments(doc, 30.0)
    assert not any(s.get("gap") for s in segs) and sum(s["frames"] for s in segs) == 35   # not 10 x 4 = 40
    assert [s["start"] for s in segs] == [int(round(c["at"] * 30)) for c in sorted(doc["clips"], key=lambda c: c["at"])]
    res = edit.render(edit.save(doc), FAST, out=tmp_path / "ten.mp4")
    assert res["duration_expected_s"] == pytest.approx(edit.duration(doc), abs=1e-6)
    assert video_duration(Path(res["path"])) == pytest.approx(edit.duration(doc), abs=1 / 30) and res["duration_ok"]
    assert res["frames"] == 35


def test_two_renders_at_once_never_share_a_file(media, tmp_path):
    docs = []
    for lo in (0.2, 1.2):                                    # same name, same rev, same preset, same folder
        d, _ = edit.add_clip(edit.new_project("review", settings={"fps": 30, "width": 320, "height": 240}), media,
                             src_in=lo, src_out=lo + 1.0)
        docs.append(edit.save(d))
    gate, results = threading.Barrier(2), [None, None]

    def go(i):
        gate.wait()
        try:
            results[i] = edit.render(docs[i], FAST, out_root=tmp_path / "r")["path"]
        except Exception as exc:  # noqa: BLE001 - the assertion below shows it
            results[i] = exc

    threads = [threading.Thread(target=go, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert all(isinstance(r, str) for r in results), results
    assert sorted(p.name for p in (tmp_path / "r" / "review").iterdir()) == \
        ["review r2 test_x264 (2).mp4", "review r2 test_x264.mp4"]
    claimed = tmp_path / "claimed.mp4"                       # an explicit out another render is writing
    (tmp_path / "claimed.mp4.part").write_bytes(b"")
    with pytest.raises(edit.EditError, match="being rendered") as err:
        edit.render(docs[0], FAST, out=claimed)
    assert err.value.status == 409 and not claimed.exists() and (tmp_path / "claimed.mp4.part").exists()


@pytest.mark.parametrize("change", [
    {"settings": [1, 2]}, {"markers": 5}, {"clips": "x"}, {"lanes": []}, {"lanes": {"video": "V1", "audio": 3}},
    {"clips": [{"id": ["x"], "lane": "V1", "src_in": 0, "src_out": 1, "at": 0, "audio": 5}]}, {"name": 7},
])
def test_validate_lists_problems_for_any_json(change):
    doc = edit.new_project("p")
    problems = edit.validate(dict(doc, **change))
    assert problems and all(isinstance(x, str) for x in problems)
    with pytest.raises(edit.EditError) as err:
        edit.save(dict(doc, **change))
    assert err.value.status == 400 and edit.load(doc["id"])["rev"] == 1
    assert edit.validate([1]) == ["a project must be a JSON object, not list"]


def test_a_byte_identical_copy_does_not_repoint_the_media(clip, tmp_path):
    a, b = tmp_path / "a" / "take.mkv", tmp_path / "b" / "take copy.mkv"
    for p in (a, b):
        p.parent.mkdir()
        shutil.copy2(clip, p)
    first = edit.import_media(a)
    doc, _ = edit.add_clip(edit.new_project("repoint", settings={"fps": 30, "width": 320, "height": 240}), first,
                           src_in=0.5, src_out=1.5)
    doc = edit.save(doc)
    again = edit.import_media(b)                             # the same take dropped from a backup folder
    assert again["id"] == first["id"] and again["path"] == str(a.resolve())
    assert again["paths"] == [str(a.resolve()), str(b.resolve())]
    b.unlink()                                               # the backup goes; the original is untouched
    assert Path(edit.render(doc, FAST, out=tmp_path / "1.mp4")["path"]).is_file()
    shutil.copy2(clip, b)
    a.unlink()                                               # now only the copy is left: paths finds it
    assert Path(edit.render(doc, FAST, out=tmp_path / "2.mp4")["path"]).is_file()


def test_peaks_start_where_the_track_starts(sync_clips):
    media = edit.import_media(sync_clips[0.5])
    try:
        edit.build_peaks(media["id"])
    except edit.NotBuilt as exc:
        pytest.skip(str(exc))
    body = edit.read_json(edit.derived_path(edit.get_media(media["id"]), "peaks", 0))
    assert body["start_s"] == pytest.approx(0.5, abs=1e-3)
    first = next(i for i in range(body["length"]) if body["data"][2 * i + 1] > 0.2)
    # pixel 0 is the track's first sample, so start_s + pixel time lands on the beep's absolute 2.0 s
    assert body["start_s"] + first * body["spp"] / body["sample_rate"] == pytest.approx(2.0, abs=0.02)


def test_render_holds_qc_to_the_loudness_target(media, tmp_path, monkeypatch):
    audio = pytest.importorskip("arsenal.media.audio")
    seen = {}
    real = audio.qc

    def spy(path, *, expect=None, **kw):
        seen.update(expect or {})
        return real(path, expect=expect, **kw)

    monkeypatch.setattr(audio, "qc", spy)
    doc, _ = edit.add_clip(edit.new_project("loud", settings={"fps": 30, "width": 320, "height": 240}), media,
                           src_in=0.0, src_out=3.5)
    res = edit.render(edit.save(doc), dict(FAST, loudness={"I": -16.0, "TP": -1.5}), out=tmp_path / "loud.mp4")
    assert seen["I"] == -16.0 and seen["TP_max"] == -1.5 and res["loudness_pass1"]
    assert res["qc"]["ok"], res["qc"]["problems"]


def test_a_silent_timeline_renders_plainly_with_a_loudness_preset(tmp_path):
    """Digital silence measures input_i -inf, which loudnorm's pass 2 refuses ('Value -inf for parameter
    measured_I'): the render skips normalisation and says why in blind instead of failing."""
    pytest.importorskip("arsenal.media.audio")
    src = tmp_path / "silent.mkv"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=160x120:r=30:d=2", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", "2", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "pcm_s16le", "-y", str(src)])
    media = edit.import_media(src)
    doc, _ = edit.add_clip(edit.new_project("hush", settings={"fps": 30, "width": 160, "height": 120}), media,
                           src_in=0.0, src_out=1.5)
    res = edit.render(edit.save(doc), dict(FAST, loudness={"I": -14.0, "TP": -1.0}), out=tmp_path / "hush.mp4")
    assert Path(res["path"]).is_file() and res["duration_ok"]
    assert any("digital silence" in b for b in res["blind"]), res["blind"]
    assert "loudnorm" not in res["graph"]


def test_cli_says_a_bad_time_in_one_line(clip, capsys):
    assert edit.cli("edit", ["new", "times"]) == 0
    pid = json.loads(capsys.readouterr().out)["id"]
    assert edit.cli("edit", ["add", pid, str(clip), "--in", "abc"]) == 1
    assert capsys.readouterr().err.strip() == "edit: 'abc' is not a time (seconds, m:ss or h:mm:ss)"


@pytest.mark.skipif(not ORACLE.is_file(), reason="the 3-track oracle recording is not on this machine")
def test_render_real_three_track_recording(tmp_path):
    media = edit.import_media(ORACLE)
    assert media["n_audio"] == 3
    doc = edit.new_project("oracle", settings={"fps": 60, "width": 1280, "height": 720})
    doc, _ = edit.add_clip(doc, media, src_in=30.0, src_out=34.0)
    doc, _ = edit.add_clip(doc, media, src_in=80.0, src_out=83.0)
    doc = edit.save(edit.set_lane_gain(doc, "A2", mute=True))
    preset = dict(FAST, vcodec=["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"])
    res = edit.render(doc, preset, out=tmp_path / "oracle.mp4")
    assert video_duration(Path(res["path"])) == pytest.approx(7.0, abs=1 / 60)
    assert res["duration_ok"]
