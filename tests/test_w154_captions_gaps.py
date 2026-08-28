"""W154-gaps pins: the tier-two caption punctuators -- gap-based (deterministic,
champion) and model-based (challenger). RED until scripts.yt_captions exports
punctuate_gaps and punctuate_model.

GAP-BASED: the VTT cue timing is the sentence-boundary signal the line-tier
cannot see -- a long pause between cues ends a sentence; a quick roll is a
phrase. Deterministic, free, meaning-safe.

MODEL-BASED: a lazy, optional challenger (rpunct). The core verb must never
hard-depend on it -- a missing package raises the teaching error.
"""
import pytest

from scripts.yt_captions import (punctuate_gaps, punctuate_model, punctuate_hybrid,
                                 MODEL_PUNCT_HINT)


VTT_GAPS = """WEBVTT

00:00:00.000 --> 00:00:01.200
hello there

00:00:01.400 --> 00:00:02.000
and goodbye

00:00:05.500 --> 00:00:07.000
a new thought arrives

00:00:05.600 --> 00:00:07.000
a new thought arrives
"""


def test_g1_long_gap_ends_the_sentence():
    out = punctuate_gaps(VTT_GAPS, gap_s=1.0)
    assert out == "Hello there and goodbye.\nA new thought arrives."


def test_g2_existing_terminal_is_not_doubled():
    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello there.\n\n00:00:05.000 --> 00:00:06.000\nnext line\n"
    out = punctuate_gaps(vtt, gap_s=1.0)
    assert out == "Hello there.\nNext line."


def test_g3_rolling_duplicate_cue_collapses():
    out = punctuate_gaps(VTT_GAPS, gap_s=1.0)
    assert out.lower().count("a new thought arrives") == 1


def test_g4_empty_input_stays_empty():
    assert punctuate_gaps("") == ""


def test_m1_missing_model_package_teaches():
    assert "deepmultilingualpunctuation" in MODEL_PUNCT_HINT


def test_m2_model_punctuates_when_available():
    # lazy challenger: if the package+model are available this passes with its
    # output; absent, the teaching RuntimeError is the honest contract
    try:
        out = punctuate_model("this is a sentence and another one")
    except RuntimeError as e:
        assert "deepmultilingualpunctuation" in str(e)
        pytest.skip("model challenger offline (honest contract)")
    assert out and "." in out


def test_h1_hybrid_capitalizes_and_punctuates():
    try:
        out = punctuate_hybrid("this is a sentence and another one")
    except RuntimeError as e:
        assert "deepmultilingualpunctuation" in str(e)
        pytest.skip("hybrid offline (model absent -- honest contract)")
    assert out[0].isupper()
    assert out.rstrip()[-1] in ".!?"


def test_h2_hybrid_has_no_lowercase_sentence_openings():
    import re
    try:
        out = punctuate_hybrid("this is a sentence and another one. and then some more")
    except RuntimeError as e:
        assert "deepmultilingualpunctuation" in str(e)
        pytest.skip("hybrid offline (model absent -- honest contract)")
    assert re.search(r"(^|[.!?] )[a-z]", out) is None


def test_h3_hybrid_teaches_when_model_absent():
    assert "deepmultilingualpunctuation" in MODEL_PUNCT_HINT
