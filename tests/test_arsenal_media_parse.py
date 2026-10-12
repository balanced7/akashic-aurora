"""arsenal.media.parse: OBS file-name times, WebVTT/SRT/ASS captions to words or segments, FFMETADATA chapters both
ways (and through ffmpeg into a file that probe reads back)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from arsenal.media import parse

SESSION = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "performance" / "20261011-165503-f62d348c"


# ------------------------------------------------------------------------------------------------- OBS names
def test_obs_time_reads_the_local_stamp_anywhere_in_the_name():
    assert parse.obs_time("2026-10-11 17-51-11.mp4") == datetime(2026, 10, 11, 17, 51, 11)
    assert parse.obs_time(r"E:\Video Output E\2026-09-17 00-38-36 tiktok 28-52.mp4") == datetime(2026, 9, 17, 0, 38, 36)
    assert parse.obs_time("Lisa Goal.mp4") is None
    assert parse.obs_time("2026-13-45 10-00-00.mp4") is None        # stamp-shaped, not a time
    assert parse.obs_time("x12026-10-11 17-51-112.mp4") is None      # digits glued on either side


def test_local_epoch_round_trips_through_local_time():
    dt = datetime(2026, 10, 11, 16, 55, 3)
    assert datetime.fromtimestamp(parse.local_epoch(dt)) == dt


@pytest.mark.skipif(not (SESSION / "session.json").is_file(), reason="practice session oracle not on this machine")
def test_local_epoch_agrees_with_the_practice_log_clock():
    """The session folder is named by its LOCAL opening time; session.json holds the UTC instant."""
    meta = json.loads((SESSION / "session.json").read_text(encoding="utf-8"))
    dt = datetime.strptime(SESSION.name[:15], "%Y%m%d-%H%M%S")
    assert parse.local_epoch(dt) == pytest.approx(meta["opened_ns"] / 1e9, abs=1.0)


# ------------------------------------------------------------------------------------------------- captions
YOUTUBE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000 align:start position:0%
so<00:00:01.400><c> the</c><00:00:01.700><c> idea</c>

00:00:03.000 --> 00:00:03.010 align:start position:0%
so the idea


00:00:03.010 --> 00:00:05.000 align:start position:0%
so the idea
is<00:00:03.500><c> simple</c>
"""


def test_youtube_vtt_gives_words_once_each_with_their_own_times():
    words = parse.subtitles(YOUTUBE_VTT)
    assert [w["word"] for w in words] == ["so", "the", "idea", "is", "simple"]
    assert [w["start"] for w in words] == [1.0, 1.4, 1.7, 3.01, 3.5]
    assert words[1]["end"] == 1.7                     # the next word's start
    assert words[2]["end"] == 2.7                     # capped at 1 s, inside its cue (ends 3.0)
    assert words[-1]["end"] == 4.5


def test_youtube_vtt_segments_merge_the_rolling_repeat():
    segs = parse.subtitles(YOUTUBE_VTT, level="segments")
    assert segs[0] == {"start": 1.0, "end": 3.01, "text": "so the idea"}
    assert segs[1]["text"] == "so the idea\nis simple"


SRT = """1
00:00:01,000 --> 00:00:02,500
Hello <i>there</i>

2
00:01:02,250 --> 00:01:04,000
General Kenobi
"""


def test_srt_gives_segments_and_spreads_words_on_request(tmp_path):
    p = tmp_path / "x.srt"
    p.write_text(SRT, encoding="utf-8")
    assert parse.subtitles(p) == [{"start": 1.0, "end": 2.5, "text": "Hello there"},
                                  {"start": 62.25, "end": 64.0, "text": "General Kenobi"}]
    words = parse.subtitles(str(p), level="words")
    assert [w["word"] for w in words] == ["Hello", "there", "General", "Kenobi"]
    assert words[2]["start"] == 62.25 and words[3]["start"] == pytest.approx(63.125)
    assert all(w["timed"] is False for w in words)


ASS = """[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,{\\an8}Top, with a comma\\Nsecond line
Dialogue: 0,0:00:03.00,0:00:04.20,Default,,0,0,0,,{\\k50}kar{\\k30}a{\\k40}oke
"""


def test_ass_segments_keep_commas_and_karaoke_gives_words(tmp_path):
    p = tmp_path / "x.ass"
    p.write_text(ASS, encoding="utf-8")
    segs = parse.subtitles(p, level="segments")
    assert segs[0] == {"start": 1.0, "end": 2.0, "text": "Top, with a comma second line"}
    words = parse.subtitles(p)                   # auto: the file has karaoke, so words
    kar = [w for w in words if w.get("timed", True)]
    assert [(w["word"], w["start"], w["end"]) for w in kar] == [("kar", 3.0, 3.5), ("a", 3.5, 3.8),
                                                               ("oke", 3.8, 4.2)]


def test_a_missing_caption_path_refuses_instead_of_reading_as_no_captions(tmp_path):
    """A mistyped path used to be read as caption text, and 'no cues' looked like 'this file has no captions'."""
    with pytest.raises(FileNotFoundError):
        parse.subtitles(str(tmp_path / "nope" / "missing captions.srt"))
    with pytest.raises(FileNotFoundError):
        parse.subtitles(tmp_path / "missing.vtt")
    with pytest.raises(FileNotFoundError):
        parse.subtitles(str(tmp_path / "no extension at all"))              # an absolute path, not text
    with pytest.raises(FileNotFoundError):
        parse.read_ffmetadata(str(tmp_path / "chapters.txt"))
    assert parse.subtitles("WEBVTT") == []                                   # one line of real caption text


def test_unknown_level_refuses():
    with pytest.raises(ValueError):
        parse.subtitles(SRT, level="lines")


# ------------------------------------------------------------------------------------------------- FFMETADATA
def test_ffmetadata_round_trip_with_escapes(tmp_path):
    chapters = [{"t0": 0.0, "t1": 12.5, "title": "Intro = setup; #1 \\ part"},
                {"t0": 12.5, "t1": 70.25, "title": "line one\nline two"},
                {"t0": 70.25, "title": "the end"}, ]
    with pytest.raises(ValueError, match="needs an end"):
        parse.write_ffmetadata(chapters)
    chapters[-1]["t1"] = 90.0
    text = parse.write_ffmetadata(chapters, tmp_path / "ch.txt", tags={"title": "Game 1; draft"})
    assert text.startswith(";FFMETADATA1\ntitle=Game 1\\; draft\n")
    assert b"\r\n" not in (tmp_path / "ch.txt").read_bytes()
    back = parse.read_ffmetadata(tmp_path / "ch.txt")
    assert back["tags"] == {"title": "Game 1; draft"}
    assert [(c["t0"], c["t1"], c["title"]) for c in back["chapters"]] == [(c["t0"], c["t1"], c["title"])
                                                                          for c in chapters]


def test_ffmetadata_reads_each_chapters_timebase():
    text = ";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/90000\nSTART=90000\nEND=450000\ntitle=A\n\n[STREAM]\ntitle=x\n"
    out = parse.read_ffmetadata(text)
    assert out["chapters"] == [{"t0": 1.0, "t1": 5.0, "title": "A", "tags": {}}]
    with pytest.raises(ValueError):
        parse.read_ffmetadata("[CHAPTER]\nSTART=0\n")


def test_written_chapters_survive_ffmpeg_and_probe(tmp_path, monkeypatch):
    from arsenal.media import ff, probe
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")
    monkeypatch.setenv("ARSENAL_MEDIA_STATE", str(tmp_path / "state"))
    meta = tmp_path / "chapters.txt"
    parse.write_ffmetadata([{"t0": 0.0, "t1": 1.5, "title": "warm up"}, {"t0": 1.5, "t1": 3.0, "title": "play"}],
                           meta)
    out = tmp_path / "with chapters.mkv"
    ff.run(["-f", "lavfi", "-i", "testsrc2=s=160x120:r=10:d=3", "-i", str(meta), "-map", "0:v", "-map_chapters", "1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(out)])
    got = probe.probe(out)["chapters"]
    assert [(c["t0"], c["t1"], c["title"]) for c in got] == [(0.0, 1.5, "warm up"), (1.5, 3.0, "play")]
