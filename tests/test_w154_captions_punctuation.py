"""W154-punct pins: the tier-one captions punctuator.

Restores the cue structure the cleaner used to throw away -- each cleaned line is
one caption cue, so the deterministic upgrade is: capitalize each cue's opening,
end each cue with a period unless terminal punctuation or a closing quote is
already present. No model, no meaning risk, fully reversible (the raw VTT stays
behind --keep-vtt; these pins cover the DERIVED text).

RED by construction until scripts.yt_captions.punctuate_captions exists.
"""
import pytest

from scripts.yt_captions import punctuate_captions


def test_p1_capitalizes_and_terminates_each_cue():
    out = punctuate_captions("glenn stevens, thank you for your time\nbrian, the conversation\n")
    lines = out.splitlines()
    assert lines[0] == "Glenn stevens, thank you for your time."
    assert lines[1] == "Brian, the conversation."


def test_p2_no_double_punctuation():
    assert punctuate_captions("Already done.\n") == "Already done."
    assert punctuate_captions("Question?\n") == "Question?"


def test_p3_closing_quote_is_not_forced():
    # a cue ENDING in a quote is an opening to more speech -- do not invent a period
    assert punctuate_captions('he said "what about it"\n') == 'He said "what about it"'


def test_p4_empty_input_stays_empty():
    assert punctuate_captions("") == ""


def test_p5_preserves_line_count_and_order():
    src = "one cue\ntwo cue\nthree cue\n"
    out = punctuate_captions(src)
    assert len(out.splitlines()) == 3
    assert out.splitlines()[0] == "One cue."
    assert out.splitlines()[2] == "Three cue."


def test_p6_idempotent():
    once = punctuate_captions("a line without punctuation\n")
    twice = punctuate_captions(once)
    assert once == twice
