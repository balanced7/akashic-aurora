"""
Domain-aware recall — D1/D2/D4. RED-first: every bar here fails on the corpus as it stands.

WHY THIS EXISTS. Daniil, 2026-08-02: "How can we make a recall system for this work for vfx, and
divide the boundary lines so we can get the same help for aurora for these kinds of help as we would
when working on the system itself?" and then, decisively: "ideally I wouldn't want to build another
system, I would want recall to be domain aware and enable cross domain learning eventually."

THE MEASURED DIAGNOSIS these pins encode:
  * VFX knowledge is NOT absent. 31 of 31 chunks in design/vfx-chunks/*.glsl carry a `note` that is
    already lesson-shaped (trigger + rule + REASON) plus a `from` field that is provenance.
  * Recall cannot reach it AND DOES NOT SAY SO. Three live probes returned 77, 707 and 675 rows for
    shader questions; not one row was about shaders. The rule "tanh must follow the superlinear
    highlight" exists VERBATIM in the repo and its own text retrieves 675 unrelated lessons.
  * The mechanism is in search_learnings_by_keyword: `hits = sum(1 for t in terms if t in haystack)`
    followed by `if hits:`. ANY single SUBSTRING match qualifies, so "a" matches "database" and
    "state" matches "statement". No stopwords, no floor, no cap. A ten-word question therefore
    matches most of the corpus and is returned RANKED, which reads as confidence.

That last one is the same defect this session found twice elsewhere -- a PNG decoder that returned
ten identical confident errors, and a metric suite that returned identical contrast for three
visibly different images. An instrument that cannot see its subject returns a confident answer, not
silence. These pins make recall say "I have nothing" when it has nothing.

Run: py -m pytest tests/test_domain_aware_recall.py -q
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS = os.path.join(REPO, "design", "vfx-chunks")


def _store():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(prefix="dom_"), "l.json")))


def _lesson(ls, name, tried, rec, category="uncategorized", domain=None):
    sig = {"experiment_name": name, "what_tried": tried, "expected_outcome": "",
           "actual_outcome": "", "category": category, "success": "yes", "recommendation": rec}
    if domain:
        sig["domain"] = domain
    assert ls.persist_learning_derived_from_experiment(sig) is True
    return name


# ---- D4: the flood, and the silence that should replace it -------------------------------------

def test_a_question_the_corpus_cannot_answer_returns_nothing():
    """The headline defect. Ask about something absent and get SILENCE, not a ranked flood."""
    ls = _store()
    _lesson(ls, "drain_the_lane_you_armed", "bifrost lane draining",
            "drain the lane you ARMED, not the lane any doc names")
    _lesson(ls, "roster_sensor_wrong", "read a liveness claim",
            "treat a watcher's liveness claim with suspicion")
    hits = ls.search_learnings_by_keyword("tanh tone map must follow the superlinear highlight")
    assert hits == [], "a corpus with no shader knowledge must say so, not rank its lane lessons"


def test_a_broad_query_gets_a_flagged_answer_rather_than_false_silence():
    """The mirror of the headline defect, and it showed up live: a nine-word grab-bag spreads one
    hit across many genuinely relevant lessons, clears no floor, and a strict cut then answers
    'I know nothing' about a corpus that plainly knows. Answer, but confess, and cap it."""
    ls = _store()
    for i in range(9):
        _lesson(ls, "chunk_rule_%d" % i, "the vignette chunk", "normalise by the corner distance",
                domain="vfx")
    got = ls.search_learnings_by_keyword(
        "shader glow tile gap vignette tonemap hue palette wireframe", domain="vfx")
    assert got, "silence about knowledge we hold is the same sin as confidence about knowledge we lack"
    assert all(r.get("weak_match") for r in got), "a weak answer must say it is weak"
    assert len(got) <= 5, "a confession does not scale; cap it"


def test_a_confident_answer_is_never_flagged_weak():
    ls = _store()
    _lesson(ls, "dither_last", "dither before the tone map",
            "dither goes last at about 1.6/255", domain="vfx")
    got = ls.search_learnings_by_keyword("dither tone map", domain="vfx")
    assert got and not got[0].get("weak_match")


def test_stopwords_alone_cannot_summon_the_corpus():
    ls = _store()
    for i in range(5):
        _lesson(ls, "lesson_%d" % i, "a thing that was tried", "a recommendation about the state")
    assert ls.search_learnings_by_keyword("a the of in on it is") == []
    assert ls.search_learnings_by_keyword("the state of the thing") != [], \
        "content terms must still retrieve; the floor is not a mute button"


def test_a_substring_is_not_a_match():
    """'state' must not match 'statement'; 'a' must not match 'database'. Substring matching is what
    let a ten-word question reach most of the corpus."""
    ls = _store()
    _lesson(ls, "statement_parsing", "parse a SQL statement", "use the database driver's parser")
    assert ls.search_learnings_by_keyword("state") == []
    assert ls.search_learnings_by_keyword("statement") != []


def test_a_real_query_still_finds_its_lesson():
    """The floor must not break what works. This is the regression guard on D4."""
    ls = _store()
    _lesson(ls, "wake_listener_harness_tracked", "armed a wake listener with an inline ampersand",
            "arm bifrost_wake ONLY via a harness-tracked background job")
    got = ls.search_learnings_by_keyword("wake listener arm harness tracked")
    assert got and got[0]["experiment_name"] == "wake_listener_harness_tracked"


# ---- D1: the domain axis ------------------------------------------------------------------------

def test_a_lesson_carries_a_domain():
    ls = _store()
    _lesson(ls, "vfx_gap_reads_as_glow", "widened tile gap on the avatar",
            "gap renders as glow; round tiles convert tile area into gap", domain="vfx")
    rec = ls.search_learnings_by_keyword("gap glow tile")[0]
    assert rec.get("domain") == "vfx"


def test_recall_can_scope_to_one_domain():
    """The whole point: shader work must stop competing with bus-lane work."""
    ls = _store()
    _lesson(ls, "bus_lane_rule", "drained the wrong lane",
            "drain the lane you armed", domain="system")
    _lesson(ls, "dither_goes_last", "put dither before the tone map",
            "dither goes last, at about 1.6/255", domain="vfx")
    # One bar per test: this one is about the DOMAIN axis, so the query must match each lesson on
    # its own merits. An earlier version asked "dither tone map lane" and expected the system
    # lesson back on one hit out of four -- which the floor correctly refuses as coincidence, so
    # the test was quietly exercising D4 instead of D1.
    vfx = ls.search_learnings_by_keyword("lane dither", domain="vfx")
    assert [r["experiment_name"] for r in vfx] == ["dither_goes_last"]
    system = ls.search_learnings_by_keyword("lane dither", domain="system")
    assert [r["experiment_name"] for r in system] == ["bus_lane_rule"]
    both = {r["experiment_name"] for r in ls.search_learnings_by_keyword("lane dither")}
    assert both == {"dither_goes_last", "bus_lane_rule"}, "unscoped search must still see everything"


def test_domain_is_inferred_when_not_given_so_the_backfill_is_possible():
    """~840 existing lessons carry no domain and will not be hand-labelled. Inference has to carry
    the backfill, so it is pinned as a contract rather than left as a heuristic nobody checked."""
    from core.learning.domains import infer_domain
    assert infer_domain({"what_tried": "edited design/vfx-chunks/swirl.glsl",
                         "recommendation": "the vignette must normalise by the true corner"}) == "vfx"
    assert infer_domain({"what_tried": "drained the bifrost lane after arming the wake listener",
                         "recommendation": "match BIFROST_CONSUME_LANE to the armed lane"}) == "system"
    # Unknowable stays system: the default must be the corpus's existing meaning, never a guess
    # that quietly relabels 800 lessons into a domain nobody checked.
    assert infer_domain({"what_tried": "", "recommendation": ""}) == "system"


def test_a_domain_is_a_triple_not_a_tag():
    """The design's load-bearing claim: a domain declares what TRIGGERS it, what it is KEYED by, and
    what EVIDENCE settles it. A bare string field would fix only the key and leave the other two
    wrong -- which is exactly why a flat tag was rejected."""
    from core.learning.domains import DOMAINS
    for name in ("system", "vfx"):
        d = DOMAINS[name]
        assert d["triggers"] and d["keys"] and d["evidence"], name
    assert "render" in DOMAINS["vfx"]["evidence"].lower()
    assert "test" in DOMAINS["system"]["evidence"].lower()


# ---- D2: adopt the knowledge that already exists ------------------------------------------------

def test_every_chunk_note_is_lesson_shaped_in_the_first_place():
    """The premise of D2, checked rather than assumed: the notes really are lessons already."""
    names = [f for f in os.listdir(CHUNKS) if f.endswith(".glsl")]
    assert len(names) >= 30
    for f in names:
        with open(os.path.join(CHUNKS, f), "r", encoding="utf-8") as fh:
            head = fh.readline().strip()
        assert head.startswith("//!"), f
        meta = json.loads(head[3:])
        assert meta.get("note"), "%s has no note to adopt" % f


def test_the_chunk_rules_become_retrievable_lessons():
    """RED TODAY, verified live: querying the channel-rotate rule against the real corpus returns
    707 rows and none of them is channel-rotate."""
    from core.learning.vfx_chunk_lessons import adopt_chunk_lessons
    ls = _store()
    n = adopt_chunk_lessons(ls, CHUNKS)
    assert n >= 30

    hue = ls.search_learnings_by_keyword("hue shift destroys the state signal", domain="vfx")
    assert any("channel-rotate" in r["experiment_name"] for r in hue), \
        "the rule exists verbatim in the repo and must be reachable by its own words"

    vign = ls.search_learnings_by_keyword("vignette corner distance widescreen", domain="vfx")
    assert vign, "the vignette normalisation rule must be reachable"


def test_adoption_is_idempotent_and_the_glsl_stays_the_truth():
    """Projection, not migration. Re-running must not fork a second copy -- two truths about one
    rule is the regression this whole pattern exists to avoid."""
    from core.learning.vfx_chunk_lessons import adopt_chunk_lessons
    ls = _store()
    first = adopt_chunk_lessons(ls, CHUNKS)
    second = adopt_chunk_lessons(ls, CHUNKS)
    assert first == second
    names = [r["experiment_name"] for r in ls.search_learnings_by_keyword("chunk", domain="vfx")]
    assert len(names) == len(set(names)), "adoption duplicated a lesson"


def test_a_rejected_technique_is_adopted_as_an_anti_pattern():
    """The LIBRARY's rejections ('FXAA blurs the very lines a wireframe is made of') are
    anti-patterns with reasons. --anti-pattern already exists and has never been used."""
    from core.learning.vfx_chunk_lessons import adopt_chunk_lessons
    ls = _store()
    adopt_chunk_lessons(ls, CHUNKS)
    warned = [r for r in ls.search_learnings_by_keyword("channel rotate hue", domain="vfx")
              if r.get("anti_pattern")]
    assert warned, "a chunk note carrying a WARNING should adopt as an anti-pattern"
