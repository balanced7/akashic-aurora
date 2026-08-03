"""
D3 + D5 — a trigger surface for domains that have no files, and promotion earned across them.

D3. recall-at fires on `--path` and `--command`. Both are SYSTEM-shaped triggers: they assume the
point of action is a file being edited or a shell command about to run. A vfx action is neither.
"about to add tanh-tonemap after superlinear-highlight" has no path and no command, so the moment
where the chunk-ordering rule would be worth knowing is a moment recall cannot be asked about.
D1/D2 made vfx lessons RETRIEVABLE; without a trigger they are still never RETRIEVED.

Checked first, per the standing rule that the hook layer is often already the mediation layer: the
hooks call recall_at(path=..., command=...) and nothing else, so this extends that ONE surface
rather than adding a second door.

D5. Cross-domain learning, and the reason it needs no new machinery: a lesson credited useful in
>= 2 DOMAINS is promoted to domain-general and surfaces everywhere. That is the existing funnel
measured across a boundary. Promotion is EARNED, never declared -- which matters most for its first
case, which is already sitting in the corpus: "an instrument that cannot see its subject returns a
confident answer, not silence" was found this day in a PNG decoder, in a metric suite, and in recall
itself. If I hand-labelled that lesson general, the mechanism would ship untested on the one example
that motivated it.

Run: py -m pytest tests/test_domain_recall_triggers.py -q
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore


def _ls():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(prefix="d35_"), "l.json")))


def _lesson(ls, name, rec, domain, tried="tried it"):
    ls.persist_learning_derived_from_experiment(
        {"experiment_name": name, "what_tried": tried, "recommendation": rec,
         "domain": domain, "success": "yes", "category": "test"})


# ---- D3: the trigger surface --------------------------------------------------------------------

def test_a_composition_gesture_builds_a_query():
    """A vfx action has no path and no command. It must still be askable."""
    from core.recall.at_action import _query_from
    q = _query_from(None, None, subject="geodesic-original", gesture="add tanh-tonemap after superlinear-highlight")
    assert "tanh" in q and "tonemap" in q
    assert "superlinear" in q and "highlight" in q
    assert "geodesic" in q


def test_the_old_triggers_are_untouched():
    """Regression guard: every existing caller passes path/command positionally or by name."""
    from core.recall.at_action import _query_from
    q = _query_from("scripts/bifrost_ui.py", "py -m pytest tests/test_recall_at.py")
    assert "bifrost" in q and "pytest" in q


def test_a_gesture_is_a_vfx_trigger_and_a_path_still_is_not():
    """The trigger decides the domain when the caller does not. A gesture only exists in the bench."""
    from core.recall.at_action import _domain_from_trigger
    assert _domain_from_trigger(None, None, "swirl", "add kaleido") == "vfx"
    assert _domain_from_trigger("design/vfx-chunks/swirl.glsl", None, None, None) == "vfx"
    assert _domain_from_trigger("core/comm/bus.py", "py agent_cli.py boot", None, None) == "system"
    assert _domain_from_trigger(None, None, None, None) is None      # nothing to go on: do not guess


def test_the_projection_carries_the_domain():
    """RED before D3: _project_items dropped `domain`, so nothing downstream could scope on it --
    the same seam its own comment already flags for provenance fields."""
    from core.recall.at_action import _project_items
    items = _project_items([{"experiment_name": "x", "recommendation": "do the thing",
                             "success": "yes", "domain": "vfx", "timestamp": ""}])
    assert items and items[0]["domain"] == "vfx"


def test_an_adopted_chunk_rule_carries_a_PARSEABLE_trigger():
    """Found live, not in a test: D2 made the chunk rules retrievable by keyword and they still
    never surfaced at a gesture, because recall-at ranks on the corpus convention
    'Use when <symptom>, before <action>: <advice>' and a chunk note has no such clause. Every
    adopted lesson scored ~0.17 against a 0.20 floor with trigger=''. A projection must bridge to
    the consumer's authoring surface, not merely copy the text across."""
    from core.learning.vfx_chunk_lessons import adopt_chunk_lessons
    from core.recall.at_action import _parse_trigger
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ls = _ls()
    adopt_chunk_lessons(ls, os.path.join(repo, "design", "vfx-chunks"))
    rec = ls.search_learnings_by_keyword("tanh tonemap filmic shoulder", domain="vfx")[0]
    trig = _parse_trigger(rec["recommendation"])
    assert trig, "an adopted rule with no trigger clause cannot clear recall-at's floor"
    assert "tanh-tonemap" in trig, "the trigger must name the chunk a gesture would mention"
    assert "NEVER clips" in rec["recommendation"], "the author's own note must survive intact"


def test_a_gesture_surfaces_the_chunk_rule_and_not_the_bus_lesson():
    """The whole point of D1-D3 end to end: ask at a composition gesture, get the composition rule."""
    from core.recall.at_action import recall_at
    ls = _ls()
    _lesson(ls, "vfx_chunk_tanh-tonemap",
            "Maps [0,inf) onto [0,1) with a filmic shoulder and NEVER clips. Must follow the "
            "superlinear highlight, or the highlight has nothing to roll off.", "vfx")
    _lesson(ls, "wake_drain_the_lane_you_armed",
            "drain the lane you ARMED, not the lane any doc names", "system")
    res = recall_at(subject="geodesic", gesture="add tanh-tonemap after superlinear-highlight",
                    learning_store=ls, limit=3, min_relevance=0.0)
    got = [i["source"] for i in res.get("lessons", [])]
    assert any("tanh-tonemap" in s for s in got), got
    assert not any("wake_drain" in s for s in got), "a bus lesson has no business at a shader gesture"


# ---- D5: promotion earned across domains --------------------------------------------------------

def test_one_domains_credit_is_not_promotion():
    from core.recall.at_action import credit_useful, is_general
    store = FileStore(os.path.join(tempfile.mkdtemp(prefix="use_"), "s.json"))
    credit_useful("learn:experiment:silence_law", "vfx", store=store)
    credit_useful("learn:experiment:silence_law", "vfx", store=store)
    assert is_general("learn:experiment:silence_law", store=store) is False, \
        "twice in one domain is a popular lesson, not a general one"


def test_credit_in_two_domains_promotes():
    from core.recall.at_action import credit_useful, is_general
    store = FileStore(os.path.join(tempfile.mkdtemp(prefix="use_"), "s.json"))
    credit_useful("learn:experiment:silence_law", "vfx", store=store)
    assert is_general("learn:experiment:silence_law", store=store) is False
    credit_useful("learn:experiment:silence_law", "system", store=store)
    assert is_general("learn:experiment:silence_law", store=store) is True


def test_promotion_does_not_destroy_the_ordinary_counters():
    """The funnel's existing fields must survive -- promotion reads the same record the value
    measurement reads, and a promotion that reset `useful` would corrupt the gauge it depends on."""
    from core.recall.at_action import credit_useful, _load_use, _store
    store = FileStore(os.path.join(tempfile.mkdtemp(prefix="use_"), "s.json"))
    credit_useful("learn:experiment:x", "vfx", store=store)
    credit_useful("learn:experiment:x", "system", store=store)
    use = _load_use(store, "learn:experiment:x")
    assert int(use.get("useful", 0)) == 2
    assert sorted(use.get("useful_domains") or []) == ["system", "vfx"]


def test_a_general_lesson_surfaces_in_every_domain():
    """The payoff: a law learned in one domain reaches the other, without being declared general."""
    from core.recall.at_action import recall_at, credit_useful
    ls = _ls()
    _lesson(ls, "silence_law",
            "An instrument that cannot see its subject returns a confident answer, not silence. "
            "Refuse to report a trend when every input returns the identical value.", "vfx")
    src = "learn:experiment:silence_law"
    from core.recall.at_action import _store as at_store
    st = at_store()
    credit_useful(src, "vfx", store=st)
    credit_useful(src, "system", store=st)
    try:
        res = recall_at(path="core/learning/learning_store.py",
                        command="confident answer identical value trend instrument subject",
                        learning_store=ls, limit=3, min_relevance=0.0)
        got = [i["source"] for i in res.get("lessons", [])]
        assert any("silence_law" in s for s in got), \
            "a lesson promoted by credit in two domains must reach a system-domain action"
    finally:
        try:
            st.delete("recall:use:" + src)
        except Exception:
            pass
