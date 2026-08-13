"""W154 pins: the `captions` verb -- YouTube captions to clean readable text.

Born 2026-08-13 from Daniil mid-laughter: "Can we make the transcription process
into a verb? I am having a blast!" The Clarke & Dawe archive run proved the flow
by hand (yt-dlp caption pull -> strip cues -> dedupe rolling repeats); this verb
institutionalizes the blast.

Named `captions`, NOT `transcript`: transcripts are dead sessions in this house
(the eye's plane), and we do not fork load-bearing words for recreation.

Pins cover the PURE cleaner (scripts/yt_captions.py:clean_vtt_text) and the
teaching error when yt-dlp is absent. The network half is a thin yt-dlp
passthrough, deliberately unpinned (their contract, not ours).
"""
import pytest

from scripts.yt_captions import clean_vtt_text, MISSING_YTDLP_HINT


VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.320 --> 00:00:02.480
Glenn Stevens, thank you for your time.

00:00:02.480 --> 00:00:05.120
Glenn Stevens, thank you for your time.
Brian, the eerily moving conversation

2
00:00:05.120 --> 00:00:07.800
Brian, the eerily moving conversation
we had about <c.colorE5E5E5>interest rates</c> was a
"""


def test_c1_cues_headers_and_indices_are_stripped():
    out = clean_vtt_text(VTT)
    assert "WEBVTT" not in out and "-->" not in out
    assert "Kind:" not in out and "Language:" not in out
    assert "\n2\n" not in f"\n{out}\n"          # bare cue index lines dropped


def test_c2_rolling_duplicates_collapse_preserving_order():
    lines = clean_vtt_text(VTT).splitlines()
    assert lines.count("Glenn Stevens, thank you for your time.") == 1
    assert lines.count("Brian, the eerily moving conversation") == 1
    assert lines.index("Glenn Stevens, thank you for your time.") < \
           lines.index("Brian, the eerily moving conversation")


def test_c3_inline_styling_tags_are_stripped_content_kept():
    out = clean_vtt_text(VTT)
    assert "<c." not in out and "</c>" not in out
    assert "interest rates" in out


def test_c4_empty_and_headerless_input_never_raise():
    assert clean_vtt_text("") == ""
    assert clean_vtt_text("just a bare line\n") == "just a bare line"


def test_c5_missing_ytdlp_teaches_the_install():
    """Errors that teach (the ACI law): the hint names the exact install command
    and the interpreter family, because this house has TWO pythons and a launcher
    with opinions."""
    assert "pip install yt-dlp" in MISSING_YTDLP_HINT
    assert "yt_dlp" in MISSING_YTDLP_HINT or "yt-dlp" in MISSING_YTDLP_HINT
