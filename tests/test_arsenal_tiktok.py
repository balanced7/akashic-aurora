"""Vandor's tests for py -m arsenal tiktok: border detection, aspect math, silence and stream parsing,
audio sync (notes on their picture flashes through dropouts and late audio), naming, ffmpeg
discovery, the drag-and-drop wording, and end-to-end encodes of synthetic screen recordings.

All media is synthetic (pure-Python frames, or ffmpeg lavfi sources in tmp_path); no real recording
is read. The module skips cleanly when no ffmpeg is discoverable.
"""
import array
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WRAPPER = ROOT / "arsenal" / "tools" / "tiktok-ready.cmd"

from arsenal import tiktok  # noqa: E402
from arsenal.__main__ import main  # noqa: E402
from arsenal.tiktok import Box, Trim  # noqa: E402

try:
    FFMPEG = tiktok.find_ffmpeg()
except tiktok.TikTokError:
    pytest.skip("no ffmpeg discoverable (set ARSENAL_FFMPEG or install imageio-ffmpeg)",
                allow_module_level=True)


# =================================================================================================
# synthetic frames (pure Python, grey levels)
# =================================================================================================

def _frame(w, h, value=0):
    return bytearray([value]) * (w * h)


def _rect(buf, w, x, y, rw, rh, value):
    row = bytes([value]) * rw
    for yy in range(y, y + rh):
        buf[yy * w + x: yy * w + x + rw] = row


def _scene(buf, w, x, y, rw, rh, lo=30, hi=90, bump=60):
    """A canvas-like picture: a vertical gradient with a brighter checkerboard over it."""
    for yy in range(y, y + rh):
        base = lo + (yy - y) * (hi - lo) // max(1, rh)
        buf[yy * w + x: yy * w + x + rw] = bytes(
            min(255, base + (bump if ((xx // 16 + (yy - y) // 16) % 2) else 0)) for xx in range(rw))


def test_centred_strip_ignores_the_edge_tab_and_the_cursor():
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 164, 0, 152, 270)
    _rect(buf, w, 472, 90, 6, 60, 220)    # the narrow bright CARDS tab at the right edge
    _rect(buf, w, 100, 60, 6, 10, 255)    # the mouse cursor on the black
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(164, 0, 152, 270)
    _rect(buf, w, 326, 120, 6, 10, 255)   # the cursor parked just beside the canvas edge
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(164, 0, 152, 270)
    detection = tiktok.combine_boxes([tiktok.detect_frame_box(bytes(buf), w, h)] * 5, w, h)
    assert detection.box == Box(164, 0, 152, 270) and detection.reason == "borders"
    assert (detection.found, detection.sampled) == (5, 5)


def test_a_cursor_or_tab_touching_the_canvas_edge_does_not_widen_the_box():
    # a stray that touches the scene is not across a gap, so only the sparse-edge trim can drop it
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 164, 0, 152, 270)
    _rect(buf, w, 158, 120, 8, 12, 255)   # the cursor straddling the canvas's left edge
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(164, 0, 152, 270)

    buf = _frame(w, h)
    _scene(buf, w, 318, 0, 152, 270)      # the canvas pushed right, ending where the tab starts
    _rect(buf, w, 470, 110, 10, 40, 232)  # the CARDS tab, touching it
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(318, 0, 152, 270)

    w, h = 270, 480                       # a wide picture in a tall frame, cursor over its top edge
    buf = _frame(w, h)
    _scene(buf, w, 0, 164, 270, 152)
    _rect(buf, w, 90, 156, 7, 11, 255)
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(0, 164, 270, 152)
    # the trim is bounded: it never eats more than EDGE_TRIM of the frame from one end
    counts = [0] * 40 + [5] * 60 + [100] * 300 + [0] * 80
    assert tiktok.trim_sparse_ends((40, 400), counts, 480) == (64, 400)


def test_off_centre_strip():
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 24, 0, 152, 270)
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(24, 0, 152, 270)


def test_wide_box_letterboxed_in_a_tall_frame():
    w, h = 270, 480
    buf = _frame(w, h)
    _scene(buf, w, 0, 164, 270, 152)
    box = tiktok.detect_frame_box(bytes(buf), w, h)
    assert box == Box(0, 164, 270, 152)
    assert tiktok.combine_boxes([box], w, h).box == Box(0, 164, 270, 152)


def test_full_frame_content_is_not_cropped():
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 0, 0, w, h)
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(0, 0, w, h)
    detection = tiktok.combine_boxes([Box(0, 0, w, h)] * 5, w, h)
    assert detection.box is None and detection.reason == "no-borders"


def test_a_dark_full_frame_scene_with_a_bright_patch_is_not_a_box_on_black():
    # sparse dim speckle everywhere (too faint to light a line) plus one bright window: the area
    # outside the window is not a quiet border, so nothing is cropped
    w, h = 480, 270
    buf = bytearray(12 if (x * 7 + y * 13) % 25 < 2 else 0 for y in range(h) for x in range(w))
    _rect(buf, w, 180, 85, 120, 100, 200)
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(0, 0, w, h)
    flat = tiktok.background_level(bytes(_frame(w, h)), w, h)
    assert flat == (0, 1.0, tiktok.LIT_DELTA_MIN)
    busy = bytes((x // 8 + y // 8) % 3 * 100 for y in range(h) for x in range(w))
    assert tiktok.background_level(busy, w, h)[1] < tiktok.RING_UNIFORM
    assert tiktok.detect_frame_box(busy, w, h) == Box(0, 0, w, h)


def test_a_dark_stripe_inside_the_strip_does_not_split_it():
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 164, 0, 152, 270)
    _rect(buf, w, 220, 0, 8, 270, 0)       # a pure-black vertical stripe through the canvas
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(164, 0, 152, 270)


def test_a_dim_canvas_with_a_black_band_is_found_whole():
    # a dim canvas (grey 4..10) on flat black, with a black band across it
    w, h = 480, 270
    buf = _frame(w, h)
    _scene(buf, w, 164, 0, 152, 270, lo=4, hi=10, bump=2)
    _rect(buf, w, 164, 180, 152, 10, 0)    # a black band across the canvas
    assert tiktok.detect_frame_box(bytes(buf), w, h) == Box(164, 0, 152, 270)


def test_an_all_black_frame_finds_nothing_and_does_not_vote():
    w, h = 480, 270
    black = bytes(_frame(w, h))
    assert tiktok.detect_frame_box(black, w, h) is None
    assert tiktok.combine_boxes([None] * 5, w, h).reason == "no-content"
    buf = _frame(w, h)
    _scene(buf, w, 164, 0, 152, 270)
    good = tiktok.detect_frame_box(bytes(buf), w, h)
    detection = tiktok.combine_boxes([None, good, good, None, good], w, h)
    assert detection.box == Box(164, 0, 152, 270) and (detection.found, detection.sampled) == (3, 5)


def test_boxes_snap_inward_to_even_numbers_and_clamp():
    assert tiktok.snap_box(25, 3, 177, 270, 480, 270) == Box(26, 4, 150, 266)
    assert tiktok.snap_box(-4, -2, 999, 999, 480, 270) == Box(0, 0, 480, 270)
    assert tiktok.snap_box(10, 10, 11, 11, 480, 270) is None
    assert tiktok.combine_boxes([Box(1, 0, 479, 270)], 480, 270).reason == "no-borders"


def test_sample_times_cover_the_middle_ninety_percent():
    assert tiktok.sample_times(100.0) == [5.0, 27.5, 50.0, 72.5, 95.0]
    assert tiktok.sample_times(None) == [0.0]


# =================================================================================================
# aspect math
# =================================================================================================

def test_exact_and_near_nine_by_sixteen_scale_without_padding():
    exact = tiktok.plan_framing(1080, 1920)
    assert (exact.mode, exact.scaled_w, exact.scaled_h, exact.scale) == ("exact", 1080, 1920, 1.0)
    canvas = tiktok.plan_framing(608, 1080, "fill")   # 0.08% off 9:16: exact in either mode
    assert (canvas.mode, canvas.scaled_w, canvas.scaled_h) == ("exact", 1080, 1920)
    assert round(canvas.scale, 3) == 1.778
    assert tiktok.plan_framing(604, 1080).mode == "exact"      # 0.6% off
    off = tiktok.plan_framing(600, 1080)                      # 1.2% off: padded
    assert (off.mode, off.scaled_w, off.scaled_h, off.offset_x, off.offset_y) == ("fit", 1066, 1920, 6, 0)


def test_wide_boxes_fit_with_bars_or_fill_with_a_centre_crop():
    fit = tiktok.plan_framing(1920, 1080, "fit")
    assert (fit.scaled_w, fit.scaled_h, fit.offset_x, fit.offset_y) == (1080, 608, 0, 656)
    fill = tiktok.plan_framing(1920, 1080, "fill")
    assert (fill.scaled_w, fill.scaled_h, fill.offset_x, fill.offset_y) == (3414, 1920, 1166, 0)
    assert fill.scale < tiktok.UPSCALE_WARN
    assert tiktok.video_filter(Box(0, 164, 270, 152), fit, "60") == \
        "fps=60,crop=270:152:0:164,scale=1080:608:flags=lanczos,pad=1080:1920:0:656:color=black,setsar=1,format=yuv420p"
    assert tiktok.video_filter(None, fill) == \
        "scale=3414:1920:flags=lanczos,crop=1080:1920:1166:0,setsar=1,format=yuv420p"


def test_friendly_warnings_for_upscaling_length_and_size():
    small = tiktok.plan_framing(1280, 540, "fill")             # a small wide box filling the phone
    assert round(small.scale, 2) == 3.56
    notes = tiktok.warnings_for({"framing": small, "keep": 700.0, "out_info": None,
                                 "out_bytes": 300 * 1024 * 1024})
    assert len(notes) == 3
    assert "3.6x" in notes[0] and "10 minutes" in notes[1] and "250 MB" in notes[2]
    assert tiktok.warnings_for({"framing": tiktok.plan_framing(608, 1080), "keep": 95.0,
                                "out_info": None, "out_bytes": 150 * 1024 * 1024}) == []


def test_fps_is_the_source_rate_capped_at_sixty():
    assert tiktok.choose_fps(60.0) == ("60", 60.0)
    assert tiktok.choose_fps(144.0) == ("60", 60.0)
    assert tiktok.choose_fps(1000.0) == ("60", 60.0)          # an mkv's "1k tbr"
    assert tiktok.choose_fps(59.94)[0] == "60000/1001"
    assert tiktok.choose_fps(30.0, "60") == ("60", 60.0)
    assert tiktok.choose_fps(None) == ("30", 30.0)


# =================================================================================================
# silence and loudness parsing (captured from ffmpeg 7.1 silencedetect,volumedetect on lavfi tones:
# sine=frequency=440:sample_rate=48000:samples_per_frame=48 with volume='0.25*(between(t,a,b)+...)')
# =================================================================================================

# tone at 3.2-6.05 s and 6.9-11.35 s, 14 s long
SILENCE_LEAD_AND_TAIL = """\
[Parsed_volumedetect_1 @ 000002c4e4fede00] n_samples: 0
[silencedetect @ 000002c4e4ff2440] silence_start: 0
[silencedetect @ 000002c4e4ff2440] silence_end: 3.201 | silence_duration: 3.201
[silencedetect @ 000002c4e4ff2440] silence_start: 6.051
[silencedetect @ 000002c4e4ff2440] silence_end: 6.901 | silence_duration: 0.85
[silencedetect @ 000002c4e4ff2440] silence_start: 11.351
[silencedetect @ 000002c4e4ff2440] silence_end: 14 | silence_duration: 2.649
[Parsed_volumedetect_1 @ 000002c4e500c280] n_samples: 1344000
[Parsed_volumedetect_1 @ 000002c4e500c280] mean_volume: -39.0 dB
[Parsed_volumedetect_1 @ 000002c4e500c280] max_volume: -33.1 dB
size=N/A time=00:00:14.00 bitrate=N/A speed= 224x
"""

# tone at 0-0.02 s (like codec priming), 1.1-1.22 s (a hotkey click), 4.6-6.35 s and 7.05-25 s
# (the playing), 33.6-33.8 s (the stop click), 34.2 s long
SILENCE_CLICKS = """\
[silencedetect @ 0000017015615dc0] silence_start: 0.021
[silencedetect @ 0000017015615dc0] silence_end: 1.101 | silence_duration: 1.08
[silencedetect @ 0000017015615dc0] silence_start: 1.221
[silencedetect @ 0000017015615dc0] silence_end: 4.600062 | silence_duration: 3.379062
[silencedetect @ 0000017015615dc0] silence_start: 6.351
[silencedetect @ 0000017015615dc0] silence_end: 7.050063 | silence_duration: 0.699063
[silencedetect @ 0000017015615dc0] silence_start: 25.001
[silencedetect @ 0000017015615dc0] silence_end: 33.600062 | silence_duration: 8.599063
[silencedetect @ 0000017015615dc0] silence_start: 33.801
[silencedetect @ 0000017015615dc0] silence_end: 34.2 | silence_duration: 0.399
[Parsed_volumedetect_1 @ 000001701561f2c0] n_samples: 3283200
[Parsed_volumedetect_1 @ 000001701561f2c0] mean_volume: -38.4 dB
[Parsed_volumedetect_1 @ 000001701561f2c0] max_volume: -33.1 dB
size=N/A time=00:00:34.20 bitrate=N/A speed= 226x
"""


def test_silence_parsing_finds_the_first_and_last_sound():
    spans = tiktok.parse_silence(SILENCE_LEAD_AND_TAIL)
    assert spans == [(0.0, 3.201), (6.051, 6.901), (11.351, 14.0)]
    assert tiktok.parse_volume(SILENCE_LEAD_AND_TAIL) == (-39.0, -33.1)
    audio_end = tiktok.parse_last_time(SILENCE_LEAD_AND_TAIL)
    assert audio_end == pytest.approx(14.0)
    window = tiktok.sound_window(spans, audio_end)
    assert window == (3.201, 11.351)
    trim = tiktok.plan_trim(window, 14.0, lead=0.5, tail=2.0)
    assert (trim.start, trim.end) == (2.701, 13.351) and trim.fade


def test_silence_edge_cases():
    # a silence still open at the end (older ffmpeg prints no silence_end at EOF)
    assert tiktok.parse_silence("silence_start: 2.02\n") == [(2.02, None)]
    assert tiktok.sound_window([(2.02, None)], 4.0) == (0.0, 2.02)
    # no silence at all: sound from start to end, and nothing to trim
    assert tiktok.sound_window([], 6.0) == (0.0, 6.0)
    trim = tiktok.plan_trim((0.0, 6.0), 6.0, 0.5, 2.0)
    assert (trim.start, trim.end, trim.fade) == (0.0, None, False)
    # silent all the way through
    assert tiktok.sound_window([(0.0, 6.0)], 6.0) is None
    assert "silent" in tiktok.plan_trim(None, 6.0, 0.5, 2.0).note
    # a negative mkv start is clamped; lead never goes below zero
    assert tiktok.parse_silence("silence_start: -0.023\nsilence_end: 0.3 | silence_duration: 0.323") == [(0.0, 0.3)]
    assert tiktok.plan_trim((0.3, 5.0), 9.0, 0.5, 2.0).start == 0.0


def test_short_clicks_at_either_end_are_not_the_first_or_last_sound():
    spans = tiktok.parse_silence(SILENCE_CLICKS)
    audio_end = tiktok.parse_last_time(SILENCE_CLICKS)
    assert audio_end == pytest.approx(34.2)
    window = tiktok.sound_window(spans, audio_end)
    assert window == (4.600062, 25.001)
    assert [(round(a, 2), round(n, 2)) for a, n in tiktok.edge_blips(spans, audio_end, window)] == \
        [(1.1, 0.12), (33.6, 0.2)]
    trim = tiktok.plan_trim(window, audio_end, 0.5, 2.0)
    assert (trim.start, trim.end) == (4.1, 27.001)
    # only clicks, each cut off by long silences: nothing counts as sound, so nothing is trimmed
    assert tiktok.sound_window([(0.1, 2.0), (2.1, 6.0)], 6.0) is None


def test_a_short_first_or_last_note_after_a_quick_rest_is_music_not_a_click():
    # invented timings: a 0.26 s staccato first note at 3.60 s, then a 0.26 s rest, then the playing
    # and at the end, a 0.24 s last note after a 0.3 s rest
    spans = [(0.0, 3.6), (3.86, 4.12), (30.0, 30.3), (30.54, 36.0)]
    window = tiktok.sound_window(spans, 36.0)
    assert window == (3.6, 30.54)                 # the first note and the short last note both stay
    assert tiktok.plan_trim(window, 36.0, 0.5, 2.0).start == 3.1
    assert tiktok.edge_blips(spans, 36.0, window) == []
    # the same blips cut off by a full second of silence, the last one right before the file ends,
    # are clicks after all
    spans = [(0.0, 3.6), (3.86, 5.0), (29.8, 31.0), (31.24, 31.8)]
    assert tiktok.sound_window(spans, 31.8) == (5.0, 29.8)


def test_a_short_final_note_long_after_the_playing_is_kept():
    # invented timings: the playing ends at 20.0 s, then a 0.2 s staccato final note at 23.5 s (3.5 s
    # later, more than --tail), then 6.3 s of silence before the recording stops at 30.0 s
    spans = [(0.0, 3.0), (20.0, 23.5), (23.7, 30.0)]
    window = tiktok.sound_window(spans, 30.0)
    assert window == (3.0, 23.7)                  # the final note is the last sound, not a click
    trim = tiktok.plan_trim(window, 30.0, lead=0.5, tail=2.0)
    assert (trim.start, trim.end) == (2.5, 25.7)  # so the tail runs on from it, not from 20.0 s
    assert tiktok.edge_blips(spans, 30.0, window) == []


def test_a_short_sound_right_at_the_end_of_the_file_is_the_stop_click():
    # the same shape, but the 0.2 s sound starts 0.6 s before the recording stops: the stop hotkey
    spans = [(0.0, 3.0), (20.0, 29.4), (29.6, 30.0)]
    window = tiktok.sound_window(spans, 30.0)
    assert window == (3.0, 20.0)
    ignored = tiktok.edge_blips(spans, 30.0, window)
    assert [(round(a, 2), round(n, 2)) for a, n in ignored] == [(29.4, 0.2)]
    trim = tiktok.plan_trim(window, 30.0, lead=0.5, tail=2.0)
    trim.ignored = ignored
    report = tiktok.format_report(_dry_report(trim))
    assert "ignored a 0.20 s click at 29.40 s" in report


def _dry_report(trim):
    """The smallest result dict format_report reads, for a dry run of an invented 30 s recording."""
    out = Path("take tiktok.mp4")
    return {"source": Path("take.mp4"), "source_bytes": 1, "duration": 30.0, "width": 1080, "height": 1920,
            "fps": 60.0, "video_codec": "h264", "bit_depth": 8, "audio_codec": "aac",
            "detection": tiktok.Detection(None, 5, 5, "no-borders"), "framing": tiktok.plan_framing(1080, 1920),
            "trim": trim, "keep": 20.0, "fps_value": 60.0, "loud_before": (None, None),
            "loud_after": (None, None), "loudnorm": False, "output": out, "output_existed": False,
            "force": False, "command": ["ffmpeg", "-i", "take.mp4", str(tiktok.partial_path_for(out))],
            "shown_command": ["ffmpeg", "-i", "take.mp4", str(out)],
            "partial": tiktok.partial_path_for(out), "dry_run": True, "preview": None, "warnings": []}


def test_audio_filter_keeps_the_clock_normalises_restamps_then_fades_at_the_new_end():
    clock = "aresample=async=1:min_hard_comp=0.01:first_pts=0"
    assert tiktok.audio_filter(Trim(2.701, 13.351), -16.0) == \
        clock + ",loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asetpts=STARTPTS+N/SR/TB," \
        "afade=t=out:st=10.350:d=0.3"
    # --no-loudnorm keeps the same clock and re-stamp: sync never depends on the loudness flag
    assert tiktok.audio_filter(Trim(1.0, None), None) == clock + ",asetpts=STARTPTS+N/SR/TB"
    silence = tiktok.silence_command("ffmpeg", "take.mkv", 1)
    assert clock in silence[silence.index("-af") + 1]


def _audio_jumps(path):
    """(timestamp jumps over 2 ms between decoded audio frames, where the audio ends) read via ashowinfo."""
    text = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0",
                           "-af", "ashowinfo", "-f", "null", "-"], capture_output=True).stderr.decode("utf-8", "replace")
    frames = [(float(t), int(n), int(r)) for t, r, n in
              re.findall(r"pts_time:(\S+).*?rate:(\d+) nb_samples:(\d+)", text)]
    assert frames, text[-500:]
    jumps = [(round(t, 3), round((frames[i + 1][0] - t - n / r) * 1000, 1))
             for i, (t, n, r) in enumerate(frames[:-1]) if abs(frames[i + 1][0] - t - n / r) > 0.002]
    t, n, r = frames[-1]
    return jumps, t + n / r


def test_loudnorm_output_has_no_audio_timestamp_jump(tmp_path):
    # loudnorm alone leaves an ~86 ms jump in the stamps after about 3 s, so players put the sound late
    src = tmp_path / "tone.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:sample_rate=48000:duration=6", "-c:a", "libopus", "-ac", "2",
                    str(src)], check=True, capture_output=True)
    out = tmp_path / "tone out.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(src),
                    "-af", tiktok.audio_filter(Trim(), -16.0), "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    str(out)], check=True, capture_output=True)
    jumps, end = _audio_jumps(out)
    assert jumps == [] and abs(end - 6.0) < 0.03, (jumps, end)


def _sound_onsets(path):
    """Where each sound starts (silencedetect silence_end), leaving out the end-of-file one."""
    text = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0",
                           "-af", "silencedetect=noise=-50dB:d=0.1", "-f", "null", "-"],
                          capture_output=True).stderr.decode("utf-8", "replace")
    return [float(t) for t in re.findall(r"silence_end: (\S+)", text)]


@pytest.mark.parametrize("trim, expected", [(Trim(), [2.0, 4.0, 6.0, 8.0]),
                                            (Trim(1.5, None), [0.5, 2.5, 4.5, 6.5])])
def test_audio_dropout_in_the_source_does_not_pull_later_sounds_early(tmp_path, trim, expected):
    # beeps at 2/4/6/8 s; 200 ms of audio frames are dropped at 3.0 s, leaving a timestamp gap (as a
    # dropout in an MKV recording does). The re-stamp after loudnorm counts samples, so without
    # aresample=async=1 every beep after the gap came out 205 ms early.
    src = tmp_path / "gap.mkv"
    beeps = "+".join(f"between(t,{s},{s + 0.4})" for s in (2, 4, 6, 8))
    subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=0x204060:s=64x114:r=10:d=10",
                    "-f", "lavfi", "-i", f"sine=f=880:r=48000:samples_per_frame=240:d=10,"
                    f"volume='0.4*({beeps})':eval=frame,aformat=channel_layouts=stereo,"
                    "aselect='not(between(t,3.0,3.2))'",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(src)],
                   check=True, capture_output=True)
    gaps, _ = _audio_jumps(src)
    assert any(ms > 150 for _, ms in gaps), gaps          # the source really has the dropout
    out = tmp_path / "gap out.mp4"
    cmd = tiktok.encode_command(FFMPEG, src, out, video_index=0, audio_index=1, vf="scale=108:192",
                                af=tiktok.audio_filter(trim, -16.0), trim=trim, crf=30, force=True)
    subprocess.run(cmd, check=True, capture_output=True)
    onsets = _sound_onsets(out)[:4]
    assert len(onsets) == 4 and all(abs(a - b) < 0.02 for a, b in zip(onsets, expected)), onsets


NOTES = (1.0, 2.0, 3.0, 4.0, 5.0)   # each 0.25 s, with the picture flashing white for as long
# nine 25 ms holes and one 60 ms hole, all in the rests: each under swresample's default 100 ms
# hard-compensation threshold, 285 ms together
SHORT_HOLES = ((1.40, 25), (1.55, 25), (1.70, 60), (2.40, 25), (2.55, 25), (3.40, 25), (3.55, 25),
               (4.40, 25), (4.55, 25), (4.70, 25))


def _make_notes_recording(path, holes=(), audio_offset=0.0, acodec=("-c:a", "pcm_s16le")):
    """6 s of a 64x114 black picture at 50 fps that flashes white on each note, with an 880 Hz note
    at the same moments. holes: (start s, length ms) of audio frames (5 ms each) removed, leaving
    timestamp holes as a dropout does. audio_offset: the audio track starts this much later than the
    picture (its notes still land on their flashes)."""
    flash = "+".join(f"between(t,{n},{n + 0.25})" for n in NOTES)
    notes = "+".join(f"between(t,{n - audio_offset:.3f},{n + 0.25 - audio_offset:.3f})" for n in NOTES)
    audio = (f"sine=f=880:r=48000:samples_per_frame=240:d={6 - audio_offset:.3f},"
             f"volume='0.4*({notes})':eval=frame,aformat=channel_layouts=stereo")
    if holes:
        audio += ",aselect='not(" + "+".join(f"between(n,{round(s * 200)},{round(s * 200) + ms // 5 - 1})"
                                             for s, ms in holes) + ")'"
    picture = (f"color=c=black:s=64x114:r=50:d=6,drawbox=w=64:h=114:color=white:t=fill:enable='{flash}',"
               "format=yuv420p")
    subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", picture,
                    "-itsoffset", str(audio_offset), "-f", "lavfi", "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "ultrafast", *acodec, str(path)], check=True, capture_output=True)


def _flash_times(path):
    """When the picture turns white, by frame timestamp."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0",
                           "-vf", "scale=4:4,format=gray,showinfo", "-fps_mode", "passthrough",
                           "-f", "rawvideo", "-"], capture_output=True)
    times = [float(t) for t in re.findall(r"pts_time:(\S+)", proc.stderr.decode("utf-8", "replace"))]
    flashes, lit = [], False
    for i, t in enumerate(times):
        now = sum(proc.stdout[i * 16:(i + 1) * 16]) > 16 * 128
        if now and not lit:
            flashes.append(t)
        lit = now
    return flashes


def _note_times(path):
    """When each note starts as a player hears it: the first audio timestamp plus the sample count.
    Players play samples back to back, so a timestamp hole left in the file does not delay them."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0",
                           "-af", "ashowinfo", "-f", "s16le", "-ac", "1", "-"], capture_output=True)
    first = re.search(r"pts_time:(\S+).*?rate:(\d+)", proc.stderr.decode("utf-8", "replace"))
    start, rate = float(first.group(1)), int(first.group(2))
    samples = array.array("h", proc.stdout[: len(proc.stdout) // 2 * 2])
    loud = max(abs(v) for v in samples) * 0.1
    notes, last = [], None
    for i, v in enumerate(samples):
        if abs(v) > loud:
            if last is None or i - last > rate // 10:
                notes.append(start + i / rate)
            last = i
    return notes


def _assert_notes_on_flashes(path):
    flashes, notes = _flash_times(path), _note_times(path)
    assert len(flashes) == len(NOTES) and len(notes) == len(NOTES), (flashes, notes)
    offsets_ms = [round((n - f) * 1000, 1) for f, n in zip(flashes, notes)]
    assert all(abs(ms) <= 20 for ms in offsets_ms), offsets_ms


@pytest.mark.parametrize("trim", [Trim(), Trim(0.5, None)], ids=["whole", "trimmed"])
def test_short_audio_dropouts_do_not_pull_later_notes_early(tmp_path, trim):
    # with swresample's default 100 ms threshold these holes were not filled, so the sample-count
    # re-stamp pulled the notes after them early (nine 25 ms holes drifted about -215 ms)
    src = tmp_path / "dropouts.mkv"
    _make_notes_recording(src, holes=SHORT_HOLES)
    gaps, _ = _audio_jumps(src)
    assert len(gaps) == len(SHORT_HOLES), gaps               # the source really has the holes
    out = tmp_path / "dropouts out.mp4"
    cmd = tiktok.encode_command(FFMPEG, src, out, video_index=0, audio_index=1, vf="scale=64:114",
                                af=tiktok.audio_filter(trim, -16.0), trim=trim, crf=30, force=True)
    subprocess.run(cmd, check=True, capture_output=True)
    _assert_notes_on_flashes(out)


def test_no_loudnorm_fills_the_same_holes_and_keeps_the_notes_on_their_flashes(tmp_path, capsys):
    # --no-loudnorm used to pass the holes straight into the MP4 (a 200 ms hole put every later note
    # 205 ms early for a player); it now shares the audio clock and the re-stamp
    src = tmp_path / "take.mkv"
    _make_notes_recording(src, holes=((1.40, 200), (2.40, 25), (3.40, 25), (4.40, 25)))
    assert main(["tiktok", str(src), "--no-loudnorm", "--out", str(tmp_path / "posts")]) == 0
    capsys.readouterr()
    out = tmp_path / "posts" / "take tiktok.mp4"
    _assert_notes_on_flashes(out)
    jumps, _ = _audio_jumps(out)
    assert jumps == [], jumps


def test_audio_that_starts_after_the_video_is_silence_until_its_first_sample(tmp_path):
    # an Opus MKV whose audio track starts 0.3 s after the picture: silencedetect used to report its
    # first silence at the track's start, so 0-0.3 s counted as a sound and the trim started at 0
    src = tmp_path / "late.mkv"
    _make_notes_recording(src, audio_offset=0.3, acodec=("-c:a", "libopus", "-b:a", "96k"))
    first = re.search(r"pts_time:(\S+)", subprocess.run(
        [FFMPEG, "-hide_banner", "-nostdin", "-i", str(src), "-map", "0:a:0", "-af", "ashowinfo",
         "-frames:a", "1", "-f", "null", "-"], capture_output=True).stderr.decode("utf-8", "replace"))
    assert abs(float(first.group(1)) - 0.3) < 0.02, first.group(1)   # the audio really starts late
    trim = tiktok.process(src, tiktok.Options(dry_run=True, out=str(tmp_path)), ffmpeg=FFMPEG)["trim"]
    assert abs(trim.first_sound - 1.0) < 0.05 and abs(trim.start - 0.5) < 0.05, trim


# =================================================================================================
# "ffmpeg -i" stderr parsing. MP4_OPUS and MKV_AAC_10BIT are captured from ffmpeg 7.1 on lavfi-made
# files: synth.mp4 = testsrc2 1280x720 60 fps (libx265) + sine (libopus), 3.5 s; s.mkv = testsrc2
# 640x360 30000/1001 fps (libx264 10-bit) + sine 44.1 kHz mono (aac), 3 s
# =================================================================================================

MP4_OPUS = """\
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'synth.mp4':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2mp41
    encoder         : Lavf61.7.100
  Duration: 00:00:03.50, start: 0.000000, bitrate: 1663 kb/s
  Stream #0:0[0x1](und): Video: hevc (Main) (hev1 / 0x31766568), yuv420p(tv, progressive), 1280x720 [SAR 1:1 DAR 16:9], 1543 kb/s, 60 fps, 60 tbr, 15360 tbn (default)
      Metadata:
        handler_name    : VideoHandler
        vendor_id       : [0][0][0][0]
        encoder         : Lavc61.19.100 libx265
  Stream #0:1[0x2](und): Audio: opus (Opus / 0x7375704F), 48000 Hz, stereo, fltp, 98 kb/s (default)
      Metadata:
        handler_name    : SoundHandler
        vendor_id       : [0][0][0][0]
At least one output file must be specified
"""

MKV_AAC_10BIT = """\
Input #0, matroska,webm, from 's.mkv':
  Metadata:
    ENCODER         : Lavf61.7.100
  Duration: 00:00:03.02, start: -0.023000, bitrate: 1979 kb/s
  Stream #0:0: Video: h264 (High 10), yuv420p10le(tv, progressive), 640x360 [SAR 1:1 DAR 16:9], 29.97 fps, 29.97 tbr, 1k tbn
      Metadata:
        ENCODER         : Lavc61.19.100 libx264
        DURATION        : 00:00:03.003000000
  Stream #0:1(eng): Audio: aac (LC), 44100 Hz, mono, fltp
      Metadata:
        ENCODER         : Lavc61.19.100 aac
        DURATION        : 00:00:03.023000000
At least one output file must be specified
"""

# hand-written in the layout ffmpeg prints for a phone clip tagged -90 with cover art
PHONE_ROTATED = """\
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'phone.mov':
  Duration: 00:00:10.00, start: 0.000000, bitrate: 16000 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 1920x1080, 15900 kb/s, 30 fps, 30 tbr, 600 tbn (default)
      Metadata:
        handler_name    : Core Media Video
      Side data:
        displaymatrix: rotation of -90.00 degrees
  Stream #0:1[0x2](und): Video: mjpeg (Baseline), yuvj420p(pc, bt470bg/unknown/unknown), 320x240, 90k tbr, 90k tbn (attached pic)
"""


def test_stream_parsing_mp4_with_opus():
    info = tiktok.parse_media_info(MP4_OPUS)
    assert info.duration == pytest.approx(3.5) and info.container.startswith("mov,mp4")
    v, a = info.video, info.audio
    assert (v.index, v.codec, v.width, v.height, v.fps, v.pix_fmt, v.bit_depth) == \
        (0, "hevc", 1280, 720, 60.0, "yuv420p", 8)
    assert (a.index, a.codec, a.sample_rate, a.channels) == (1, "opus", 48000, "stereo")


def test_stream_parsing_mkv_with_aac_and_ten_bit_video():
    info = tiktok.parse_media_info(MKV_AAC_10BIT)
    assert info.duration == pytest.approx(3.02) and info.container == "matroska,webm"
    v, a = info.video, info.audio
    assert (v.codec, v.width, v.height, v.pix_fmt, v.bit_depth) == ("h264", 640, 360, "yuv420p10le", 10)
    assert tiktok.choose_fps(v.fps)[0] == "30000/1001"
    assert (a.index, a.codec, a.sample_rate, a.channels) == (1, "aac", 44100, "mono")


def test_stream_parsing_rotation_and_cover_art():
    info = tiktok.parse_media_info(PHONE_ROTATED)
    assert info.video.index == 0 and info.video.display_size == (1080, 1920)
    assert info.audio is None
    assert tiktok.parse_media_info("Duration: N/A, bitrate: N/A\n").duration is None


# =================================================================================================
# naming, refusals, --latest, ffmpeg discovery
# =================================================================================================

def test_output_naming_and_out_as_a_folder(tmp_path):
    src = tmp_path / "2026-02-14 19-30-00.mp4"
    assert tiktok.output_path_for(src) == tmp_path / "2026-02-14 19-30-00 tiktok.mp4"
    folder = tmp_path / "posts"
    folder.mkdir()
    assert tiktok.output_path_for(src, str(folder)) == folder / "2026-02-14 19-30-00 tiktok.mp4"
    assert tiktok.output_path_for(src, str(tmp_path / "new") + os.sep, many=True) == \
        tmp_path / "new" / "2026-02-14 19-30-00 tiktok.mp4"
    assert tiktok.output_path_for(src, str(tmp_path / "clip.mp4")) == tmp_path / "clip.mp4"
    assert tiktok.output_path_for(src, str(tmp_path / "clip.v2")) == tmp_path / "clip.v2.mp4"
    with pytest.raises(tiktok.TikTokError, match="folder"):
        tiktok.output_path_for(src, str(tmp_path / "one.mp4"), many=True)
    out = tiktok.output_path_for(src, str(folder))
    assert tiktok.preview_path_for(src, out) == folder / "2026-02-14 19-30-00 tiktok-preview.jpg"


def test_out_without_an_extension_is_a_new_folder(tmp_path):
    src = tmp_path / "take.mkv"
    new = tmp_path / "newfolder"
    assert tiktok.output_path_for(src, str(new)) == new / "take tiktok.mp4"      # not 'newfolder.mp4'
    assert tiktok.output_path_for(src, str(new), many=True) == new / "take tiktok.mp4"
    assert not new.exists()                                  # made only when something is saved into it
    existing = tmp_path / "notes"
    existing.write_bytes(b"x")                               # an existing file with no extension: ask
    with pytest.raises(tiktok.TikTokError, match="no extension"):
        tiktok.output_path_for(src, str(existing))


def test_preview_is_not_replaced_without_force(tmp_path):
    src = tmp_path / "take.mp4"
    src.write_bytes(b"never decoded: the refusal comes first")
    old = tmp_path / "take tiktok-preview.jpg"
    old.write_bytes(b"old preview")
    for dry_run in (True, False):
        with pytest.raises(tiktok.TikTokError, match="preview .* already exists; add --force"):
            tiktok.process(src, tiktok.Options(dry_run=dry_run, preview=True), ffmpeg=FFMPEG)
    assert old.read_bytes() == b"old preview"


def test_a_dropped_video_whose_copy_exists_is_told_to_delete_or_rename_it(tmp_path, capsys):
    src = tmp_path / "take.mp4"
    src.write_bytes(b"source")
    copy = tmp_path / "take tiktok.mp4"
    copy.write_bytes(b"old copy")
    # run exactly what the drag-and-drop wrapper runs for one dropped file
    line = next(ln.strip() for ln in WRAPPER.read_text().splitlines()
                if ln.strip().startswith("py -m arsenal tiktok"))
    args = [str(src) if a == "%~1" else a for a in shlex.split(line)[3:]]
    assert main(args) == 1
    err = capsys.readouterr().err
    assert "a TikTok copy of this video already exists" in err, err
    assert "Delete or rename that copy, then drop the video again" in err and "--force" not in err
    assert main(["tiktok", str(src)]) == 1                   # typed at a prompt, --force is still the advice
    assert "add --force" in capsys.readouterr().err
    assert copy.read_bytes() == b"old copy" and src.read_bytes() == b"source"


def test_refuses_to_overwrite_without_force_and_never_the_source(tmp_path):
    src = tmp_path / "take.mp4"
    src.write_bytes(b"source")
    out = tmp_path / "take tiktok.mp4"
    tiktok.check_output(src, out, force=False)            # nothing there yet: fine
    out.write_bytes(b"old")
    with pytest.raises(tiktok.TikTokError, match="--force"):
        tiktok.check_output(src, out, force=False)
    tiktok.check_output(src, out, force=True)
    with pytest.raises(tiktok.TikTokError, match="source"):
        tiktok.check_output(src, tmp_path / "TAKE.mp4" if os.name == "nt" else src, force=True)
    with pytest.raises(tiktok.TikTokError, match="source"):
        tiktok.process(src, tiktok.Options(out=str(src), force=True), ffmpeg=FFMPEG)
    assert src.read_bytes() == b"source"
    # the encode writes a partial file and renames it when done; that name must never be the source
    assert tiktok.partial_path_for(out) == tmp_path / "take tiktok.partial.mp4"
    clip = tmp_path / "clip.partial.mp4"
    clip.write_bytes(b"source")
    with pytest.raises(tiktok.TikTokError, match="source"):
        tiktok.process(clip, tiktok.Options(out=str(tmp_path / "clip.mp4")), ffmpeg=FFMPEG)
    assert clip.read_bytes() == b"source"


def test_latest_picks_the_newest_recording_but_not_our_outputs(tmp_path, monkeypatch):
    for i, name in enumerate(["old.mkv", "newer.mov", "notes.txt", "newer tiktok.mp4", "x tiktok-preview.jpg",
                                  "newer tiktok.partial.mp4"]):
        path = tmp_path / name
        path.write_bytes(b"x")
        os.utime(path, (1_700_000_000 + i * 100, 1_700_000_000 + i * 100))
    assert tiktok.latest_video(tmp_path).name == "newer.mov"
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(tiktok.TikTokError, match="no .mp4"):
        tiktok.latest_video(empty)
    with pytest.raises(tiktok.TikTokError, match="does not exist"):
        tiktok.latest_video(tmp_path / "missing")
    # the default folder is whatever serve.py's library default is, not a second copy of the path
    from arsenal import serve
    monkeypatch.setattr(serve, "DEFAULT_ROOTS", [str(tmp_path)])
    assert tiktok.default_folder() == tmp_path.resolve()


def test_ffmpeg_discovery_order(tmp_path, monkeypatch):
    configured = tmp_path / "my-ffmpeg.exe"
    configured.write_bytes(b"")
    calls = []

    def which(name):
        calls.append("which")
        return "C:/on/path/ffmpeg.exe"

    def bundled():
        calls.append("bundled")
        return "C:/bundled/ffmpeg.exe"

    monkeypatch.setattr(tiktok.shutil, "which", which)
    monkeypatch.setattr(tiktok, "_bundled_ffmpeg", bundled)
    monkeypatch.setenv("ARSENAL_FFMPEG", str(configured))
    assert tiktok.find_ffmpeg() == str(configured) and calls == []

    monkeypatch.delenv("ARSENAL_FFMPEG")
    assert tiktok.find_ffmpeg() == "C:/on/path/ffmpeg.exe" and calls == ["which"]

    monkeypatch.setattr(tiktok.shutil, "which", lambda name: calls.append("which") or None)
    assert tiktok.find_ffmpeg() == "C:/bundled/ffmpeg.exe" and calls[-2:] == ["which", "bundled"]

    monkeypatch.setattr(tiktok, "_bundled_ffmpeg", lambda: None)
    with pytest.raises(tiktok.TikTokError, match="imageio-ffmpeg"):
        tiktok.find_ffmpeg()

    monkeypatch.setenv("ARSENAL_FFMPEG", str(tmp_path / "missing.exe"))
    with pytest.raises(tiktok.TikTokError, match="ARSENAL_FFMPEG"):
        tiktok.find_ffmpeg()


def test_cli_usage_problems_exit_two(capsys):
    assert main(["tiktok"]) == 2
    assert main(["tiktok", "--latest", "a.mp4"]) == 2
    assert main(["tiktok", "a.mp4", "--lead", "-1"]) == 2
    assert main(["tiktok", "a.mp4", "--lufs", "3"]) == 2
    err = capsys.readouterr().err
    assert "--latest" in err and "--lead" in err and "--lufs" in err


def test_cli_turns_os_errors_into_one_sentence(tmp_path, monkeypatch, capsys):
    def broken_default():
        raise PermissionError(13, "Access is denied", str(tmp_path / "recordings"))

    monkeypatch.setattr(tiktok, "default_folder", broken_default)
    assert main(["tiktok", "--latest", "--dry-run"]) == 2
    err = capsys.readouterr().err
    assert "Access is denied" in err and "--folder" in err and "Traceback" not in err


def test_latest_with_a_broken_serve_module_is_one_sentence(monkeypatch, capsys):
    # --latest reads its default folder from arsenal/serve.py, which other work edits; any failure to
    # import it (not only ImportError) must end in a plain sentence naming --folder
    import importlib.abc
    import importlib.util

    class BrokenServe(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path=None, target=None):
            return importlib.util.spec_from_loader(name, self) if name == "arsenal.serve" else None

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            raise SyntaxError("invalid syntax (serve.py, line 1)")

    monkeypatch.delitem(sys.modules, "arsenal.serve", raising=False)
    monkeypatch.setattr(sys, "meta_path", [BrokenServe()] + sys.meta_path)
    assert main(["tiktok", "--latest", "--dry-run"]) == 2
    err = capsys.readouterr().err
    assert "serve.py" in err and "SyntaxError" in err and "--folder" in err, err


def test_dry_run_prints_the_final_name_and_notes_the_partial_file(tmp_path, capsys):
    src = tmp_path / "take.mkv"
    _make_notes_recording(src)
    assert main(["tiktok", str(src), "--dry-run"]) == 0
    report = capsys.readouterr().out
    command = next(ln for ln in report.splitlines() if ln.startswith("  command"))
    assert command.endswith('take tiktok.mp4"') and "tiktok.partial" not in command, command
    assert " -n " in command                                 # a copy-pasted command does not replace a copy
    assert "a real run writes 'take tiktok.partial.mp4' first and renames it to 'take tiktok.mp4'" in report
    assert sorted(p.name for p in tmp_path.iterdir()) == ["take.mkv"]


# =================================================================================================
# end to end: a synthetic 1280x720 screen recording with a 9:16 canvas, a tab, and a silent start
# =================================================================================================

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _make_recording(path):
    graph = ("[0:v][1:v]overlay=x=438:y=0:shortest=1[c];"
             "[c][2:v]overlay=x=490:y=200:shortest=1,"
             "drawbox=x=1270:y=300:w=8:h=60:color=white:t=fill,"      # the narrow bright tab
             "drawbox=x=432:y=200:w=10:h=14:color=white:t=fill,"      # a cursor over the canvas's left edge
             "format=yuv420p[v];"
             "[3:a]volume=volume=0:enable='lt(t,1.5)',aformat=channel_layouts=stereo[a]")
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-y",
           "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=25:d=6",
           "-f", "lavfi", "-i", "color=c=0x3399ff:s=404x720:r=25:d=6",
           "-f", "lavfi", "-i", "testsrc2=s=300x300:r=25:d=6",
           "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6",
           "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "libopus", "-b:a", "96k", "-t", "6", str(path)]
    subprocess.run(cmd, check=True, capture_output=True)


def test_end_to_end_makes_a_tiktok_ready_copy(tmp_path, capsys):
    src_dir = tmp_path / "recordings"
    src_dir.mkdir()
    src = src_dir / "2026-01-01 12-00-00.mp4"
    _make_recording(src)
    before = (_sha(src), src.stat().st_size, src.stat().st_mtime_ns)
    source_info = tiktok.probe(FFMPEG, src)
    assert source_info.audio.codec == "opus"
    out_dir = tmp_path / "posts"                             # no extension, not there yet: a new folder

    # dry run: reports the box and the command, writes only the preview
    assert main(["tiktok", str(src), "--dry-run", "--preview", "--out", str(out_dir)]) == 0
    report = capsys.readouterr().out
    assert "box 404x720 at x=438, y=0" in report and "crop=404:720:438:0" in report
    assert "libx264" in report and "dry run" in report
    assert "tiktok.partial.mp4" in report                    # ffmpeg writes a partial file, renamed at the end
    assert sorted(p.name for p in out_dir.iterdir()) == ["2026-01-01 12-00-00 tiktok-preview.jpg"]

    # the preview is not replaced without --force, and is with it
    preview = out_dir / "2026-01-01 12-00-00 tiktok-preview.jpg"
    preview.write_bytes(b"old")
    assert main(["tiktok", str(src), "--dry-run", "--preview", "--out", str(out_dir)]) == 1
    assert "already exists" in capsys.readouterr().err and preview.read_bytes() == b"old"
    assert main(["tiktok", str(src), "--dry-run", "--preview", "--force", "--out", str(out_dir)]) == 0
    capsys.readouterr()
    assert preview.read_bytes()[:2] == b"\xff\xd8"           # a fresh JPEG

    # --latest finds the recording, not a newer output (or a killed run's partial file) beside it
    decoys = [src_dir / "2026-01-01 12-00-00 tiktok.mp4", src_dir / "2026-01-01 12-00-00 tiktok.partial.mp4"]
    for decoy in decoys:
        decoy.write_bytes(b"not a video")
    assert tiktok.latest_video(src_dir) == src
    for decoy in decoys:
        decoy.unlink()

    # a bad --out is one plain sentence, not a traceback
    blocker = tmp_path / "not a folder.txt"
    blocker.write_bytes(b"x")
    assert main(["tiktok", str(src), "--dry-run", "--preview", "--out", str(blocker / "sub") + os.sep]) == 1
    assert main(["tiktok", str(src), "--out", str(blocker / "sub") + os.sep]) == 1
    err = capsys.readouterr().err
    assert err.count("could not use") == 2, err

    # the real encode, over the broken partial file a killed run left behind
    stale = out_dir / "2026-01-01 12-00-00 tiktok.partial.mp4"
    stale.write_bytes(b"half an mp4")
    assert main(["tiktok", str(src), "--out", str(out_dir)]) == 0
    report = capsys.readouterr().out
    out = out_dir / "2026-01-01 12-00-00 tiktok.mp4"
    assert out.is_file() and "saved" in report
    assert sorted(p.name for p in out_dir.iterdir()) ==         ["2026-01-01 12-00-00 tiktok-preview.jpg", "2026-01-01 12-00-00 tiktok.mp4"]
    info = tiktok.probe(FFMPEG, out)
    assert (info.video.width, info.video.height) == (1080, 1920)
    assert info.video.codec == "h264" and info.video.pix_fmt == "yuv420p"
    assert info.audio.codec == "aac" and info.audio.sample_rate == 48000 and info.audio.channels == "stereo"
    expected = source_info.duration - (1.5 - 0.5)
    assert abs(info.duration - expected) <= 0.15, (info.duration, expected)
    jumps, audio_end = _audio_jumps(out)
    assert jumps == [] and abs(audio_end - info.duration) <= 0.05, (jumps, audio_end, info.duration)

    # no black border columns: the picture reaches every edge
    frame = tiktok.grab_gray_frame(FFMPEG, out, 2.5, info.video.index, 1080, 1920)
    assert frame is not None
    edge_columns = [sum(frame[x::1080]) / 1920 for x in list(range(6)) + list(range(1074, 1080))]
    assert min(edge_columns) > 40, edge_columns
    edge_rows = [sum(frame[y * 1080:(y + 1) * 1080]) / 1080 for y in list(range(4)) + list(range(1916, 1920))]
    assert min(edge_rows) > 40, edge_rows

    # running again refuses to overwrite; the source is untouched throughout
    assert main(["tiktok", str(src), "--out", str(out_dir)]) == 1
    assert "--force" in capsys.readouterr().err
    assert (_sha(src), src.stat().st_size, src.stat().st_mtime_ns) == before
