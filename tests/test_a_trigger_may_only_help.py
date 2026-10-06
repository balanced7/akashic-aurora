"""RED pins: writing a trigger the way the doctrine demands makes a lesson score WORSE.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

THE DOCTRINE, AGENTS.md, stated to every agent that reads it:

    Write the recommendation trigger-phrased -- "Use when <symptom>, before <action>:
    <advice>. Don't when <contraindication>." -- a lesson fires at the right moment only if
    its text says when that moment is.

THE SCORER, core/recall/at_action.py, inside `_trigger_aware_relevance`:

    if not trig.strip():
        return prose                                   # no trigger -> full prose score
    return 0.6 * _damped_overlap(trig, query, weights) + 0.4 * prose

So a lesson WITHOUT a trigger keeps 100% of its prose score, and a lesson WITH one keeps 40%
plus whatever its trigger earns. When the trigger does not match the query -- which is most
moments, because a trigger names ONE situation -- the compliant lesson scores 0.4x while the
non-compliant one beside it scores 1.0x. **Obeying the doctrine is a 60% penalty at every
moment the lesson was not written for.**

MEASURED TONIGHT over real injections replayed through the live scorer (400 harvested
impressions, the lessons each one actually surfaced):

    trigger HELPED the score : 0
    trigger HURT the score   : 16
    no change                : 7
    (no trigger, unaffected) : 275

    worst: 0.333 -> 0.233, 0.312 -> 0.200, 0.273 -> 0.218

Not once did the trigger term raise a score. Sixteen times it lowered one.

HONEST BOUND ON THAT SAMPLE: these are lessons that ALREADY SURFACED, so it is biased toward
showing harm -- a trigger that helped would have lifted something INTO the set where this
replay cannot see it. That is exactly why the fix is `max(...)` and not "drop the trigger
term": a trigger that genuinely matches must still win. The claim is only that a trigger must
never COST a lesson, which the measurement supports without needing the unbiased sample.

WHY THIS IS THE NIGHT'S LEVER. A separate slice measured that 737 of 1,164 fired lessons
(63.3%) carry a parser-readable trigger, and that ALL 737 earned zero credited flips this
session while the one credited lesson has no trigger at all. The doctrine's prediction is
inverted in the data, and this line is a sufficient mechanism for the inversion: we taught the
corpus to write triggers and then charged it for them.

Run::

    py -m pytest tests/test_a_trigger_may_only_help.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.recall import at_action as A  # noqa: E402

QUERY = "fix the zebrafish counter in the narwhal pipeline"

#: Prose that matches the query PARTIALLY. Deliberately not a perfect match: with the current
#: blend `0.6*trigger + 0.4*prose`, a perfect prose score of 1.0 can never be improved by any
#: trigger at all, so a perfect-prose fixture could only ever demonstrate harm. A partial match
#: is the honest case and the one where a good trigger has room to pay.
PROSE = ("the counter overflows after nine runs on a cold store, and the operator sees "
         "nothing in the log until the ninth")

#: A trigger about something else entirely. This is the COMMON case, not a pathological one:
#: a trigger names one situation, and most moments are not that situation.
OFF_TOPIC_TRIGGER = "Use when provisioning a new Redis container on a fresh host"

#: A trigger that squarely names the moment.
ON_TOPIC_TRIGGER = "Use when the zebrafish counter overflows, before touching the pipeline"


def _score(trigger: str) -> float:
    """Score one projected item through the function the Ranker actually calls."""
    item = {"text": PROSE, "match_text": PROSE, "source": "learn:experiment:probe",
            "trigger": trigger, "trigger_terms": []}
    by_text = {PROSE: item}
    fn = A._trigger_aware_relevance(by_text)
    return float(fn(PROSE, QUERY))


def test_an_off_topic_trigger_does_not_cost_the_lesson_its_prose_match():
    """THE PIN. Two lessons, identical prose, identical query. One wrote a trigger as the
    doctrine demands; the other did not. The compliant one must not score LOWER."""
    without = _score("")
    with_off = _score(OFF_TOPIC_TRIGGER)
    assert with_off >= without - 1e-9, (
        "writing a trigger COST this lesson %.1f%% of its score (%.3f -> %.3f) at a moment the "
        "trigger does not name. AGENTS.md instructs every agent to write triggers; the scorer "
        "charges 0.6 of the weight to a term that misses, so obeying the doctrine is a penalty "
        "at every moment the lesson was not written for."
        % (100.0 * (1 - (with_off / without if without else 1)), without, with_off))


def test_an_on_topic_trigger_still_WINS():
    """RATCHET, and the reason the fix is max() rather than deleting the trigger term. A
    trigger that genuinely names the moment must still raise the score, or we would be
    throwing away the signal the doctrine exists to create."""
    without = _score("")
    with_on = _score(ON_TOPIC_TRIGGER)
    assert with_on > without + 1e-9, (
        "an ON-TOPIC trigger no longer beats having no trigger (%.3f vs %.3f) -- the fix "
        "removed the signal instead of removing the penalty" % (with_on, without))


def test_the_on_topic_trigger_outranks_the_off_topic_one():
    """Ordering survives: a lesson whose trigger names this moment must outrank one whose
    trigger names a different moment."""
    assert _score(ON_TOPIC_TRIGGER) > _score(OFF_TOPIC_TRIGGER) + 1e-9


def test_a_trigger_never_lowers_a_score_across_a_spread_of_queries():
    """THE CLASS, not the instance. Swept over several real-shaped queries so the pin is not
    an artifact of one hand-picked pair."""
    queries = [
        "fix the zebrafish counter in the narwhal pipeline",
        "py agent_cli.py boot claude --task 'drain mail'",
        "edit core/comm/bifrost_api.py to add a lane default",
        "git commit the checker and run the suite",
        "restart the discord gateway after the stale-code warning",
    ]
    bad = []
    for q in queries:
        item = {"text": PROSE, "match_text": PROSE, "source": "s",
                "trigger": OFF_TOPIC_TRIGGER, "trigger_terms": []}
        plain = {"text": PROSE, "match_text": PROSE, "source": "s",
                 "trigger": "", "trigger_terms": []}
        with_t = float(A._trigger_aware_relevance({PROSE: item})(PROSE, q))
        without = float(A._trigger_aware_relevance({PROSE: plain})(PROSE, q))
        if with_t < without - 1e-9:
            bad.append((q[:46], round(without, 3), round(with_t, 3)))
    assert not bad, (
        "a trigger lowered the score on %d of %d queries: %s"
        % (len(bad), len(queries), bad))
