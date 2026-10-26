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


def test_letters_that_rhyme_with_ee_get_a_line_asking_for_an_ear():
    # the first real run: Misha's rushed "D" lost its d, and the model wrote "E" at p=0.96 with no (?) to warn.
    # Daniel ruled it D by ear (2026-10-08). The probability cannot vouch for a consonant the audio no longer holds.
    words = [
        w(30.3, 30.4, "We're"),
        w(30.4, 30.74, "using"),
        w(30.74, 32.96, "F,", 0.7),
        w(32.98, 33.36, "A,"),
        w(33.66, 33.86, "G,"),
        w(34.28, 34.44, "E,", 0.96),
        w(34.84, 34.96, "A,"),
        w(35.18, 35.36, "D"),
        w(35.36, 35.66, "tuning."),
    ]
    lines = render(words, 36.0).splitlines()
    assert lines[-2].startswith("[0:30] We're using F, [held 2.2s] A, · G, · E, · A, D tuning.")
    assert lines[-1] == '       [G, E, D: letters that rhyme with "ee" are easily confused; confirm by ear]'


def test_the_ear_line_follows_the_breath_line_that_holds_the_letters():
    out = render([w(0.0, 0.3, "Drop"), w(0.3, 0.5, "D."), w(1.5, 1.8, "Thanks.")], 2.0).splitlines()
    assert out == [
        "[0:00] Drop D.",
        '       [D: letters that rhyme with "ee" are easily confused; confirm by ear]',
        "[0:01] Thanks.",
    ]


def test_other_letters_and_words_get_no_ear_line():
    # A, F and I do not rhyme with "ee"; "be" and "Bee." are words, not letters
    out = render([w(0.0, 0.2, "A,"), w(0.2, 0.4, "F,"), w(0.4, 0.5, "I"), w(0.5, 0.7, "be"), w(0.7, 0.9, "Bee.")], 1.0)
    assert "confirm by ear" not in out


def test_leading_and_trailing_silence_are_stated():
    out = render([w(5.0, 5.4, "Hello.")], 12.0).splitlines()
    assert out[0] == "       [5.0s no speech]"
    assert out[-1] == "       [6.6s no speech to the end]"


def test_no_words_renders_nothing():
    assert render([], 10.0) == ""
