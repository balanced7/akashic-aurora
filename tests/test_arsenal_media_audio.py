"""arsenal.media.audio: track names, per-track loudness, demux for Chromium, mix (gains, mutes, spans), split, silences,
two-pass loudnorm and qc, on synthetic multi-track files generated here (lavfi sines and noise at known dBFS)."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from arsenal.media import audio, ff

LEVELS = (-20.0, -26.0, -30.0)
REC_17_51 = Path(r"E:\Video Output E\2026-10-11 17-51-11.mp4")


def _house():
    try:
        ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    return tmp_path / "state"


def _sine(db: float, d: float, f: float = 997.0) -> str:
    e = f"{10 ** (db / 20):.9f}*sin(2*PI*{f}*t)"
    return f"aevalsrc={e}|{e}:s=48000:c=stereo:d={d}"


def _build(out: Path, codec: str, *, titles=("Voice", "Game", "Comms"), sources=None, d: float = 6.0) -> Path:
    """A 160x90 video + one audio track per source (default: 997 Hz sines at LEVELS), FLAC/Opus/AAC in MP4."""
    sources = sources or [_sine(db, d) for db in LEVELS]
    args = ["-y", "-f", "lavfi", "-i", f"testsrc2=s=160x90:r=30:d={d}"]
    for s in sources:
        args += ["-f", "lavfi", "-i", s]
    args += ["-map", "0:v"] + [x for k in range(len(sources)) for x in ("-map", f"{k + 1}:a")]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", codec, "-ac", "2"]
    for k, t in enumerate(titles or []):
        args += [f"-metadata:s:a:{k}", f"title={t}"]
    ff.run(args + [str(out)])
    return out


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    _house()
    d = tmp_path_factory.mktemp("audio_fx")
    noise = [f"anoisesrc=color=pink:amplitude=0.2:seed=1:d=6:r=48000",
             f"anoisesrc=color=white:amplitude=0.1:seed=2:d=6:r=48000"]
    return {
        "flac": _build(d / "flac.mp4", "flac"),
        "opus": _build(d / "opus.mp4", "libopus"),
        "aac": _build(d / "aac.mp4", "aac", titles=None),
        "noise": _build(d / "noise.mp4", "flac", titles=None, sources=noise),
        "dir": d,
    }


def _pcm(path, track: int = 0, extra=()) -> np.ndarray:
    raw = ff.run(["-v", "error", *extra, "-i", str(path), "-map", f"0:a:{track}", "-ac", "2", "-f", "s16le", "-"],
                 binary=True).stdout
    return np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.int64)


# ------------------------------------------------------------------------------------------------- names

def test_title_beats_the_house_map_and_generic_names_do_not_count():
    assert audio.track_name(0, {"title": "Voice"}) == ("Voice", "Voice", "title")
    assert audio.track_name(0, {"name": "simple_opus_recording0", "handler_name": "OBS Audio Handler"}) == \
        (None, "Mix", "map")
    assert audio.track_name(3, {"handler_name": "SoundHandler"}) == (None, "Comms", "map")
    assert audio.track_name(7, {}) == (None, "Track 8", "map")


def test_tracks_lists_every_track_with_its_name(media):
    flac = audio.tracks(media["flac"])
    assert [(t["index"], t["codec"], t["house_name"]) for t in flac] == \
        [(0, "flac", "Voice"), (1, "flac", "Game"), (2, "flac", "Comms")]
    assert all(t["sample_rate"] == 48000 and t["channels"] == 2 and abs(t["duration_s"] - 6.0) < 0.01 for t in flac)
    assert [t["house_name"] for t in audio.tracks(media["aac"])] == ["Mix", "Voice", "Game"]   # untitled: the map


def test_pick_accepts_indices_names_and_refuses_missing_tracks(media):
    trs = audio.tracks(media["flac"])
    assert audio.pick("all", trs) == [0, 1, 2]
    assert audio.pick("2,0", trs) == [2, 0]
    assert audio.pick(["Game", 0], trs) == [1, 0]
    with pytest.raises(ff.MediaError, match="audio track 5 is not in"):
        audio.pick(5, trs, media["flac"])
    with pytest.raises(ff.MediaError, match="no audio track named 'Piano'"):
        audio.pick("Piano", trs, media["flac"])


# ------------------------------------------------------------------------------------------------- loudness

@pytest.mark.parametrize("kind", ["flac", "opus"])
def test_loudness_per_track_within_0_1_lu(media, kind):
    res = audio.loudness(media[kind])
    assert [r["index"] for r in res["tracks"]] == [0, 1, 2]
    for row, level in zip(res["tracks"], LEVELS):
        # a 997 Hz sine on both channels reads exactly its dBFS in LUFS (BS.1770's -0.691 offset)
        assert abs(row["I"] - level) <= 0.1, row
        assert abs(row["TP"] - level) <= 0.2, row
    assert res["api"] == "arsenal.media.loudness/v0" and res["source"]["id"] and res["blind"]
    assert Path(res["receipt"]).is_file()


def test_loudness_over_a_span(media):
    res = audio.loudness(media["flac"], tracks="Game", span=(1.0, 3.0))
    assert len(res["tracks"]) == 1 and abs(res["tracks"][0]["I"] - LEVELS[1]) <= 0.1


# ------------------------------------------------------------------------------------------------- mix

@pytest.mark.parametrize("ext", [".wav", ".m4a"])
def test_mixdown_matches_the_coherent_sum_within_0_2_lu(media, tmp_path, ext):
    out = tmp_path / f"mix{ext}"
    res = audio.mix(media["flac"], out, gains_db={0: 0, 1: -6}, mute=[2])
    # same-phase 997 Hz sines add in amplitude: 0.1 + 10^(-32/20)
    predicted = 20 * math.log10(10 ** (LEVELS[0] / 20) + 10 ** ((LEVELS[1] - 6) / 20))
    check = audio.loudness(out)["tracks"][0]["I"]
    assert abs(check - predicted) <= 0.2, (check, predicted)
    assert abs(res["measured"]["I"] - predicted) <= 0.2
    assert res["spans"][0]["tracks"] == [0, 1] and res["spans"][0]["muted"] == [2]


def test_mix_by_track_names(media, tmp_path):
    res = audio.mix(media["flac"], tmp_path / "named.flac", gains_db={"Voice": -6}, mute=["Game", "Comms"])
    assert abs(res["measured"]["I"] - (LEVELS[0] - 6)) <= 0.1


def test_mix_spans_place_clips_sample_exact(media, tmp_path):
    src = media["noise"]
    t0, t1 = _pcm(src, 0), _pcm(src, 1)
    out = tmp_path / "timeline.wav"
    res = audio.mix(None, out, measure=False, spans=[
        {"src": src, "start": 1.0, "end": 2.5, "tracks": [0]},                              # timeline 0.0-1.5
        {"src": src, "start": 0.5, "end": 1.0, "tracks": "all", "mute": [1], "at": 2.0},   # 2.0-2.5, track 1 muted
        {"src": src, "start": 4.0, "end": 5.0, "tracks": [1], "gains_db": {1: -6}, "at": 3.0},  # 3.0-4.0
    ])
    got = _pcm(out)
    assert len(got) == 4 * 48000 and res["timeline_s"] == 4.0
    assert np.abs(got[0:72000] - t0[48000:120000]).max() <= 1          # float path: within 1 LSB
    assert np.abs(got[72000:96000]).max() == 0 and np.abs(got[120000:144000]).max() == 0
    assert np.abs(got[96000:120000] - t0[24000:48000]).max() <= 1
    assert np.abs(got[144000:192000] - np.round(t1[192000:240000] * 10 ** (-6 / 20))).max() <= 1


def test_mix_many_spans_reads_its_graph_from_a_file(media, tmp_path, state):
    src = media["noise"]
    spans = [{"src": src, "start": 0.1 * k, "end": 0.1 * k + 0.05, "tracks": [k % 2]} for k in range(60)]
    res = audio.mix(None, tmp_path / "many.wav", spans=spans, measure=False)
    assert len(res["graph"]) > 8000 and "-/filter_complex" in res["argv"]
    assert len(_pcm(tmp_path / "many.wav")) == 60 * 2400
    assert len(list((state / "tmp").glob("graph-*.txt"))) == 1
    too_many = [{"src": src, "start": 0.0, "end": 0.01}] * 400
    with pytest.raises(ff.MediaError, match="command line"):
        audio.mix(None, tmp_path / "x.wav", spans=too_many)


def test_mix_refuses_a_bad_span(media, tmp_path):
    with pytest.raises(ff.MediaError, match="bad span|need 0 <= start < end"):
        audio.mix(media["flac"], tmp_path / "x.wav", span=(3.0, 2.0))


def test_spans_past_the_end_are_refused_everywhere(media, tmp_path):
    src = media["flac"]                                        # 6.0 s
    # Wholly past the end used to measure I -70 / TP 0.0 and mix zero samples; crossing it misplaced later spans.
    for call in (lambda: audio.loudness(src, span=(100.0, 200.0)),
                 lambda: audio.silences(src, span=(100.0, 200.0)),
                 lambda: audio.loudnorm_2pass(src, tmp_path / "ln.wav", span=(4.0, 10.0)),
                 lambda: audio.mix(src, tmp_path / "m.wav", span=(4.0, 10.0)),
                 lambda: audio.mix(None, tmp_path / "m2.wav", spans=[{"src": src, "start": 4.0, "end": 10.0},
                                                                    {"src": src, "start": 0.0, "end": 1.0}])):
        with pytest.raises(ff.MediaError, match="bad span"):
            call()
    ok = audio.mix(src, tmp_path / "edge.wav", span=(4.0, 6.0005), measure=False)    # within export's 1 ms
    assert ok["timeline_s"] == 2.0005 and len(_pcm(tmp_path / "edge.wav")) == round(2.0005 * 48000)


def test_a_track_shorter_than_its_file_pads_its_span(tmp_path):
    _house()
    src = _build(tmp_path / "short_audio.mp4", "flac", titles=None, sources=[_sine(-20.0, 4.0)], d=6.0)
    trs = audio.tracks(src)
    assert abs(trs[0]["duration_s"] - 4.0) < 0.01 and abs(trs[0]["file_duration_s"] - 6.0) < 0.01
    res = audio.mix(None, tmp_path / "pad.wav", measure=False,
                    spans=[{"src": src, "start": 3.0, "end": 6.0}, {"src": src, "start": 0.0, "end": 1.0}])
    got = _pcm(tmp_path / "pad.wav")
    assert res["spans"][1]["at"] == 3.0 and res["timeline_s"] == 4.0 and len(got) == 4 * 48000
    assert np.abs(got[:48000]).max() > 2000 and np.abs(got[48000:144000]).max() == 0    # audio ends at 4.0 s
    assert np.abs(got[144000:]).max() > 2000                                              # span 2 lands at 3.0
    with pytest.raises(ff.MediaError, match="the audio of short_audio.mp4 ends at 4.000 s"):
        audio.mix(src, tmp_path / "x.wav", span=(4.5, 6.0))


def test_mix_argument_shapes_fail_closed(media, tmp_path):
    src = media["flac"]
    assert audio.mix(src, tmp_path / "a.wav", mute=1, measure=False)["spans"][0]["muted"] == [1]
    assert audio.mix(src, tmp_path / "b.wav", mute="Game", measure=False)["spans"][0]["muted"] == [1]
    assert audio.mix(src, tmp_path / "c.wav", mute="Game,Comms", measure=False)["spans"][0]["tracks"] == [0]
    video_only = tmp_path / "video_only.mp4"
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=1", "-c:v", "libx264", "-preset", "ultrafast",
            str(video_only)])
    for call, why in ((lambda: audio.mix(None, tmp_path / "x.wav", spans=[]), "empty list of spans"),
                      (lambda: audio.mix(video_only, tmp_path / "x.wav"), "has no audio track"),
                      (lambda: audio.mix(src, tmp_path / "x.wav", mute=1.5), "mute=1.5"),
                      (lambda: audio.mix(src, tmp_path / "x.wav", gains_db=-6), "gains_db=-6"),
                      (lambda: audio.mix(src, tmp_path / "x.wav", tracks=[]), "picks no audio track")):
        with pytest.raises(ff.MediaError, match=why):
            call()


def test_mono_is_upmixed_at_minus_3_db_keeping_its_loudness(tmp_path):
    _house()
    mono = tmp_path / "mono.wav"
    ff.run(["-y", "-f", "lavfi", "-i", "aevalsrc=0.5*sin(2*PI*997*t):s=48000:c=mono:d=2", "-c:a", "pcm_s16le",
            str(mono)])
    res = audio.mix(mono, tmp_path / "up.wav")
    got = _pcm(tmp_path / "up.wav")
    raw = ff.run(["-v", "error", "-i", str(mono), "-f", "s16le", "-"], binary=True).stdout     # mono as itself
    ratio = np.abs(got).max(axis=0) / np.abs(np.frombuffer(raw, np.int16).astype(np.int64)).max()
    assert np.all(np.abs(ratio - 10 ** (-3 / 20)) < 0.002), ratio
    assert abs(res["measured"]["I"] - audio.loudness(mono)["tracks"][0]["I"]) <= 0.1
    assert any("-3 dB per channel" in b for b in res["blind"])


# ------------------------------------------------------------------------------------------------- demux

def test_demux_copy_gives_browser_containers_bit_identical(media, tmp_path):
    for kind, ext in (("opus", ".ogg"), ("aac", ".m4a"), ("flac", ".flac")):
        res = audio.demux(media[kind], tmp_path / kind, codec="copy")
        assert len(res["files"]) == 3
        for row in res["tracks"]:
            assert row["how"] == "copy" and row["path"].endswith(ext)
            inv = audio.streams(row["path"])
            assert [s["type"] for s in inv["streams"]] == ["audio"]
            assert inv["streams"][0]["codec"] == audio.tracks(media[kind])[0]["codec"]
            assert inv["streams"][0]["house_name"] == row["house_name"]
        src0, got0 = _pcm(media[kind], 0), _pcm(res["files"][0])
        n = min(len(src0), len(got0))
        assert np.array_equal(src0[:n], got0[:n])
    ogg = audio.demux(media["opus"], tmp_path / "o2", tracks="Game")["files"]
    assert len(ogg) == 1 and len(_pcm(ogg[0])) == 6 * 48000      # Ogg trims Opus end padding: the nominal length


def test_demux_reencode_to_flac_and_wav(media, tmp_path):
    for codec, ext in (("flac", ".flac"), ("wav", ".wav")):
        res = audio.demux(media["opus"], tmp_path / codec, tracks=[1], codec=codec)
        assert res["tracks"][0]["how"] == codec and res["files"][0].endswith(ext)
    with pytest.raises(ff.MediaError, match="copy, flac or wav"):
        audio.demux(media["opus"], tmp_path / "x", codec="mp3")


def test_split_channels(media, tmp_path):
    left_right = [("aevalsrc=0.2*sin(2*PI*997*t)|0.05*sin(2*PI*2000*t):s=48000:c=stereo:d=2")]
    src = _build(tmp_path / "lr.mp4", "flac", titles=None, sources=left_right, d=2)
    res = audio.split_channels(src, 0, tmp_path / "split")
    assert len(res["files"]) == 2 and res["layout"] == "stereo"
    both = _pcm(src)
    for k, f in enumerate(res["files"]):
        assert audio.tracks(f)[0]["channels"] == 1
        mono = np.frombuffer(ff.run(["-v", "error", "-i", f, "-f", "s16le", "-"], binary=True).stdout, np.int16)
        assert np.array_equal(mono, both[:, k])
    # a mono channel is measured as mono: amplitude 0.2 at 997 Hz -> -13.98 dBFS - 3.01
    assert abs(audio.loudness(res["files"][0])["tracks"][0]["I"] - (20 * math.log10(0.2) - 3.01)) <= 0.1


# ------------------------------------------------------------------------------------------------- silences

def test_silences_finds_a_gap_on_the_source_clock(tmp_path):
    _house()
    gap = ["aevalsrc=0.1*sin(2*PI*440*t)*(1-between(t\\,2\\,3.5))|0.1*sin(2*PI*440*t)*(1-between(t\\,2\\,3.5))"
           ":s=48000:c=stereo:d=6"]
    src = _build(tmp_path / "gap.mp4", "flac", titles=None, sources=gap)
    res = audio.silences(src, noise_db=-50, min_s=0.5)
    assert len(res["silences"]) == 1
    s0, s1 = res["silences"][0]
    assert abs(s0 - 2.0) < 0.02 and abs(s1 - 3.5) < 0.02
    later = audio.silences(src, noise_db=-50, min_s=0.5, span=(1.0, 5.0))["silences"]
    assert abs(later[0][0] - 2.0) < 0.02 and abs(later[0][1] - 3.5) < 0.02


# ------------------------------------------------------------------------------------------------- loudnorm

@pytest.mark.parametrize("source,out_name,tp", [
    ("anoisesrc=color=pink:amplitude=0.02:seed=7:d=10:r=48000", "pink.m4a", -1.5),   # starts near -48.6 LUFS
    ("aevalsrc=0.05*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*0.5*t))+0.03*sin(2*PI*1330*t)*between(t\\,3\\,7)"
     "|0.05*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*0.5*t)):s=48000:c=stereo:d=10", "tones.wav", -1.0),
], ids=["pink-noise-to-aac", "modulated-tones-to-wav"])
def test_loudnorm_2pass_lands_within_half_a_lu(tmp_path, source, out_name, tp):
    _house()
    src = tmp_path / "src.flac"
    ff.run(["-y", "-f", "lavfi", "-i", source, "-ac", "2", "-c:a", "flac", str(src)])
    res = audio.loudnorm_2pass(src, tmp_path / out_name, target_i=-14.0, tp=tp)
    check = audio.loudness(tmp_path / out_name)["tracks"][0]
    assert abs(check["I"] + 14.0) <= 0.5 and check["TP"] <= tp, check
    assert res["after"]["I"] == check["I"] and res["mode"] in ("linear", "dynamic")
    assert res["before"]["input_i"] is not None and res["attempts"]
    assert res["ok"] and res["problems"] == [] and res["normalized"] is True


def test_digital_silence_renders_plainly_with_a_note(tmp_path):
    _house()
    src = _build(tmp_path / "silent.mp4", "aac", titles=None, sources=["anullsrc=r=48000:cl=stereo:d=3"], d=3.0)
    ln = audio.loudnorm_2pass(src, tmp_path / "ln.m4a")       # pass 2 used to fail: measured_I -inf
    assert ln["ok"] and ln["normalized"] is False and "digital silence" in ln["notes"][0]
    assert ln["before"]["input_i"] == "-inf" and ln["after"]["TP"] is None and ln["mode"] is None
    mixed = audio.mix(src, tmp_path / "mix.wav", loudnorm=-14.0)
    assert mixed["ok"] and mixed["normalized"] is False and mixed["notes"] and len(_pcm(tmp_path / "mix.wav")) > 0
    assert audio.loudnorm_unmeasurable({"input_i": "-23.1", "input_tp": "-5.0", "input_lra": "3.0",
                                        "input_thresh": "-33.4", "target_offset": "0.2"}) is None


def test_a_loudnorm_miss_after_the_last_render_is_a_problem(tmp_path):
    _house()
    # sparse content (a 50 ms beep over a -54 dBFS pink floor) drives loudnorm into dynamic mode; its first render
    # lands about 3.4 LU loud, so one render (tries=1) must come back with a problem rather than look finished
    src = tmp_path / "sparse.flac"
    ff.run(["-y", "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.002:seed=9:d=8:r=48000",
            "-f", "lavfi", "-i", "aevalsrc=0.5*sin(2*PI*997*t)*between(t\\,3\\,3.05):s=48000:d=8",
            "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0[a]", "-map", "[a]", "-ac", "2", "-c:a", "flac",
            str(src)])
    plan = [{"src": str(src), "start": 1.0, "end": 6.0, "dur": 5.0, "at": 0.0, "tracks": [0], "muted": [],
             "gains_db": {0: 0.0}, "fade_in_s": 0.0, "fade_out_s": 0.0}]
    inputs, graph = audio.mix_graph(plan)
    once = audio.normalize_render(inputs, graph, "mix", tmp_path / "once.wav", audio.CODECS["wav"][0],
                                  target={"I": -14.0, "TP": -1.0, "LRA": 11.0}, tries=1)
    assert once["normalized"] and abs(once["measured"]["I"] + 14.0) > 0.5
    assert once["problems"] and "within 0.5 LU after 1 render(s) (dynamic mode)" in once["problems"][0]
    res = audio.loudnorm_2pass(src, tmp_path / "twice.wav", span=(1.0, 6.0))
    met = abs(res["after"]["I"] + 14.0) <= 0.5 and res["after"]["TP"] <= -1.0
    assert res["ok"] == met and bool(res["problems"]) == (not met)


# ------------------------------------------------------------------------------------------------- qc

def test_qc_flags_a_dropped_track_and_passes_the_whole_file(media, tmp_path):
    dropped = tmp_path / "dropped.mp4"
    ff.run(["-y", "-i", str(media["opus"]), "-map", "0:v", "-map", "0:a:0", "-c", "copy", str(dropped)])
    want = {"video_streams": 1, "audio_streams": 3, "duration_s": 6.0, "frames": 180, "w": 160, "h": 90, "fps": 30}
    bad = audio.qc(dropped, expect=want)
    assert not bad["ok"] and bad["problems"] == ["expected 3 audio streams, found 1"]
    good = audio.qc(media["opus"], expect={**want, "titles": ["Voice", "Game", "Comms"], "I": -20.0, "I_tol": 0.2})
    assert good["ok"], good["problems"]
    assert [round(r["I"]) for r in good["loudness"]] == [-20, -26, -30]


def test_qc_sees_black_freeze_and_silence(tmp_path):
    _house()
    src = tmp_path / "defects.mp4"
    ff.run(["-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=6", "-f", "lavfi",
            "-i", "aevalsrc=0.1*sin(2*PI*997*t)*lt(t\\,4):s=48000:c=stereo:d=9",
            "-filter_complex", "[0:v]drawbox=t=fill:c=black:enable=between(t\\,1\\,2.5),"
                               "tpad=stop_mode=clone:stop_duration=3[v]",
            "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-t", "9", str(src)])
    res = audio.qc(src, expect={"no_black": True, "no_freeze": True, "no_silence": True})
    assert len(res["black"]) == 1 and abs(res["black"][0][0] - 1.0) < 0.05 and abs(res["black"][0][1] - 2.5) < 0.1
    assert res["freeze"] and res["freeze"][0][0] >= 5.9
    assert res["silence"][0] and abs(res["silence"][0][0][0] - 4.0) < 0.05
    assert len(res["problems"]) == 3 and not res["ok"]


# ------------------------------------------------------------------------------------------------- cli + real file

def test_cli_audio_mix_qc(media, tmp_path, capsys):
    assert audio.cli("audio", [str(media["flac"]), "--loudness"]) == 0
    assert '"house_name": "Voice"' in capsys.readouterr().out
    assert audio.cli("mix", [str(media["flac"]), str(tmp_path / "m.wav"), "--gains", "0:0,1:-6", "--mute", "2"]) == 0
    assert audio.cli("qc", [str(tmp_path / "m.wav"), "--expect", '{"audio_streams": 2}']) == 1


@pytest.mark.skipif(not REC_17_51.is_file(), reason="Daniel's recording 2026-10-11 17-51-11 is not on this machine")
def test_real_obs_recording_has_one_opus_mix_track():
    _house()
    trs = audio.tracks(REC_17_51)
    assert [(t["codec"], t["channels"], t["house_name"], t["name_source"]) for t in trs] == \
        [("opus", 2, "Mix", "map")]
    assert abs(trs[0]["duration_s"] - 2028.254) < 0.01
    row = audio.loudness(REC_17_51, span=(600.0, 660.0))["tracks"][0]
    assert -60.0 < row["I"] < -20.0 and row["TP"] < 0.0
