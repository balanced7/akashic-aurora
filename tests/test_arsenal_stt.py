"""The cadence render of arsenal/stt.py: timing becomes layout (Daniel, 2026-10-08).

Pure tests on synthetic word lists. No model is loaded and nothing is transcribed. The real-audio check is the module
itself: py -m arsenal.stt <audio> <stem>.
"""
from arsenal.stt import mmss, render


def w(start, end, word, p=0.99):
    return {"start": start, "end": end, "word": word, "p": p}


def test_mmss():
    assert mmss(0) == "0:00"
    assert mmss(27.4) == "0:27"
    assert mmss(75.0) == "1:15"


def test_close_words_share_a_line_and_short_pauses_get_a_dot():
    out = render([w(0.0, 0.3, "What's"), w(0.32, 0.6, "up"), w(0.9, 1.2, "dudes?")], 2.0)
    assert out == "[0:00] What's up · dudes?"


def test_a_breath_starts_a_new_line_with_its_time():
    out = render([w(0.0, 0.5, "First."), w(1.3, 1.6, "Second.")], 2.0)
    assert out.splitlines() == ["[0:00] First.", "[0:01] Second."]


def test_a_long_silence_gets_its_own_line_with_the_duration():
    # the clip starts on the first word and ends just after the last, so only the middle silence is stated
    out = render([w(0.0, 1.0, "riff."), w(14.3, 14.6, "That's")], 15.0)
    assert out.splitlines() == ["[0:00] riff.", "       [13.3s no speech]", "[0:14] That's"]


def test_a_short_word_stretched_over_a_pause_is_marked_held():
    out = render([w(30.4, 30.74, "using"), w(30.74, 32.96, "F,"), w(32.98, 33.36, "A,")], 34.0)
    assert "F, [held 2.2s] A," in out


def test_a_long_word_that_takes_its_time_is_not_held():
    assert "held" not in render([w(0.0, 1.2, "different")], 2.0)


def test_unsure_words_carry_a_question_mark():
    out = render([w(0.0, 0.2, "We're", 0.22), w(0.21, 0.4, "using", 0.01)], 1.0)
    assert out == "[0:00] We're(?) using(?)"


def test_leading_and_trailing_silence_are_stated():
    out = render([w(5.0, 5.4, "Hello.")], 12.0).splitlines()
    assert out[0] == "       [5.0s no speech]"
    assert out[-1] == "       [6.6s no speech to the end]"


def test_no_words_renders_nothing():
    assert render([], 10.0) == ""
