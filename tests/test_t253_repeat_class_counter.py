"""T253 -- nothing measures whether a lesson PREVENTED anything.

Recall exists to stop a mistake from recurring. Every instrument we had measured something
else:

  value rate 5.1%   -- (useful + helped) / surfaced. 95.2% of that denominator was never voted
                       on at all, and of the 327 surfacings actually judged, 87% were positive.
                       A FEEDBACK COVERAGE number reported under a QUALITY label.
  related_to edges  -- 180 of 831 lessons resemble an existing one, but ZERO reach the 4-5 dim
                       "update the existing one instead" threshold and only 9 match on
                       problem+solution. The corpus is CLEAN. That measures corpus redundancy,
                       which is a different thing from behavioural repetition.

MEASURED ON ONE DAY, 2026-08-08, five repeats of a class that already had a lesson:

  character-iteration over a string  x4  (ask_many `files`; `_note_exclusion` kinds; my own
                                          related_to analysis; and the original)
  shell backticks substituting prompt text  x3
  built-not-wired  x2
  inline `&` inside a background command, silently detaching the job  x1 -- against a lesson
                                          read at boot THAT MORNING

Not one produced a duplicate-lesson flag, because the pattern is: write ONE lesson, then repeat
the mistake without writing more. Every existing instrument is blind to the whole class.

THE HONESTY CONSTRAINT IS THE POINT OF THE SLICE. This counts only repeats someone NOTICED, so
it is a FLOOR, never a rate. Rendering it as a percentage would recreate exactly the sin it
replaces -- a number whose denominator is unknowable, presented as though it were known.

Daniil, 2026-08-08: "I want all of our metrics to evolve and be true to what is / be useful for
their purpose. metrics that don't serve a purpose or mislead are not great."
"""
import os
import tempfile

import pytest

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore


@pytest.fixture
def store(tmp_path):
    s = LearningStore(store=FileStore(os.path.join(str(tmp_path), "learn.json")))
    s.record_learning({
        "experiment_name": "the_original_lesson", "agent_id": "claude",
        "category": "tooling", "success": "yes",
        "what_tried": "iterated a value that turned out to be a string",
        "recommendation": "Use when iterating a value that might be a string: a bare string is "
                          "iterable and will be walked character by character.",
    })
    return s


def test_a_repeat_records_its_original(store):
    """The link is the finding. A repeat with no original is just another lesson."""
    r = store.record_repeat(of="the_original_lesson", agent_id="claude",
                            what="iterated a string in _note_exclusion", recall_outcome="excluded_silent")
    assert r["of"] == "the_original_lesson"
    # Deliberately via the report: a second accessor for the same number is a second thing to
    # keep in agreement, and check_wiring flagged the standalone counter as having no caller.
    assert store.repeat_report()["count"] == 1


def test_a_repeat_captures_elapsed_time_since_the_original(store):
    """How long the lesson survived before being violated is the sharpest single field.

    Today's worst case was minutes, against a lesson read at boot that morning.
    """
    r = store.record_repeat(of="the_original_lesson", agent_id="claude",
                            what="again", recall_outcome="fired")
    assert "elapsed_s" in r and isinstance(r["elapsed_s"], (int, float)), r
    assert r["elapsed_s"] >= 0


def test_a_repeat_captures_what_recall_did_at_that_moment(store):
    """Closes the loop with T251. 'The lesson existed' and 'the lesson was shown' differ.

    A repeat where recall FIRED is a reading failure. A repeat where it was SUPPRESSED is a
    targeting failure. Those need opposite fixes, and one field separates them.
    """
    r = store.record_repeat(of="the_original_lesson", agent_id="claude",
                            what="again", recall_outcome="excluded_silent:self_echo")
    assert r["recall_outcome"] == "excluded_silent:self_echo"


def test_a_repeat_of_an_unknown_lesson_is_refused_by_name(store):
    """An unresolvable pointer is how a ledger fills with claims nobody can check."""
    with pytest.raises(ValueError) as e:
        store.record_repeat(of="no_such_lesson_exists", agent_id="claude", what="x")
    assert "no_such_lesson_exists" in str(e.value)


def test_the_surface_reports_a_count_and_a_list_never_a_rate(store):
    """THE constraint. This counts only NOTICED repeats, so a percentage would be a lie.

    An undercount rendered as a rate is the exact defect this task exists to replace: a
    denominator nobody can know, presented as though it were known.
    """
    store.record_repeat(of="the_original_lesson", agent_id="claude", what="a",
                        recall_outcome="fired")
    store.record_repeat(of="the_original_lesson", agent_id="claude", what="b",
                        recall_outcome="floor_silent")
    r = store.repeat_report()

    assert r["count"] == 2
    assert r["floor_not_rate"] is True, "the report must declare itself a floor"
    blob = repr(r)
    assert "%" not in blob, f"no percentage may appear anywhere in this report: {blob}"
    assert "rate" not in {k.lower() for k in r}, f"no key may be named a rate: {sorted(r)}"


def test_the_report_ranks_lessons_by_how_often_they_were_violated(store):
    """This list IS the training set for the recall targeting problem.

    A lesson that exists, is good, and gets violated anyway is a targeting failure with a
    known right answer -- which is the rarest and most useful thing in the corpus.
    """
    store.record_learning({"experiment_name": "second_lesson", "agent_id": "claude",
                           "category": "tooling", "success": "yes",
                           "what_tried": "a different thing", "recommendation": "Use when..."})
    for _ in range(3):
        store.record_repeat(of="the_original_lesson", agent_id="claude", what="x",
                            recall_outcome="excluded_silent")
    store.record_repeat(of="second_lesson", agent_id="claude", what="y", recall_outcome="fired")

    top = store.repeat_report()["most_violated"]
    assert top[0][0] == "the_original_lesson" and top[0][1] == 3, top


def test_recording_a_repeat_does_not_create_a_new_lesson(store):
    """A repeat is evidence ABOUT a lesson, not a new one.

    Filing it as a lesson would inflate the corpus with duplicates and hide the repeat inside
    the very count that failed to notice it.
    """
    before = len(store.get_all_learnings())
    store.record_repeat(of="the_original_lesson", agent_id="claude", what="x")
    assert len(store.get_all_learnings()) == before, "the corpus must not grow"
