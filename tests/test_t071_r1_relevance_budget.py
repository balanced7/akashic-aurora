"""T071-R1 PRE-REGISTERED ACCEPTANCE -- the boot relevance budget v1.

Spec: deepseek's blind half GOVERNS (research/reviewed/deepseek-creative-robustness-
2026-07-15.md Part 5, adopted by creative-robustness-reconciliation R1 row): boot's
lesson section becomes MOST-RELEVANT under a FIXED character budget with the score
ladder task-id(1.0) > constraint(0.8) > file-path(0.7) > category(0.5), recency as
tiebreak, and cited-vs-ignored feedback via the EXISTING funnel credit
(core.recall.at_action.usefulness_factor over recall:use:<source> counters -- zero
new counters). The budget PRIORITIZES, never censors: the full corpus stays one
knowledge_recall away.

REGRESSION STORY: the 2026-07-15 morning boot surfaced 'r', 'use it', 'attempt 3',
'handle me' -- test-residue lessons crowding 8 recency-ranked slots while the task
at hand (T075 morning gate) had real lessons available. The anti-noise property is
the FIXED cap: as the corpus grows, competition gets tougher, the surface stays clean.

Committed RED before context/relevance_budget.py exists (method baseline).

Flagged binds for deepseek's verify (T073 precedent):
  R1-a  constraint tier v1 detector = category 'constraint*' OR an RB-\\d+ token in
        the lesson text, AND keyword overlap with the task (his 'tagged as
        constraint kind' arrives with R2's lifecycle; this is the bridge).
  R1-b  credit joins MULTIPLICATIVELY (usefulness_factor in [0.5,1.5]) so a noise-
        decayed lesson can sink below a clean lower tier -- his feedback-loop
        wording, made concrete.
  R1-c  per-entry clip at render carries an explicit '...[budget]' marker and the
        TOP hit is always included even if it must be clipped (packet law: said,
        never silent).
  R1-d  kill switch AKASHIC_RELEVANCE_BUDGET=0 -> legacy recency/Ranker loader.

Run: py -m pytest tests/test_t071_r1_relevance_budget.py -q   (no Redis needed)
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.context import relevance_budget as rb
except ImportError:
    rb = None


def _built():
    assert rb is not None, \
        "T071-R1 build target context/relevance_budget.py does not exist yet (RED until built)"


def _lesson(name, rec, category="general", ts=None, tried=""):
    return {"experiment_name": name, "recommendation": rec, "what_tried": tried,
            "category": category, "confidence": "medium", "success": "yes",
            "timestamp": ts if ts is not None else time.time()}


class FakeStore:
    def __init__(self, lessons):
        self._lessons = lessons

    def load_all_learnings_from_store(self):
        return list(self._lessons)


NOW = time.time()
TASK = "T077 harden the wake listener seat files in scripts/bifrost_wake.py (comm robustness)"


def _select(lessons, task=TASK, credit=None, cap=2000):
    return rb.select_within_budget(
        FakeStore(lessons), task, cap_chars=cap, now=NOW,
        credit_fn=(credit or (lambda source: {})))


# --------------------------------------------------------------- R1-P1 task-id beats all
def test_p1_task_id_match_outranks_everything():
    _built()
    old_hit = _lesson("hit", "Use when touching T077 seat logic: check K7 first.",
                      category="unrelated", ts=NOW - 86400 * 30)
    fresh_cat = _lesson("cat", "General comm advice.", category="comm robustness", ts=NOW)
    picked = _select([fresh_cat, old_hit])
    assert picked and picked[0]["source"] == "hit", \
        "P1: an exact task-id mention must outrank a fresher category match"
    assert picked[0]["score"] >= 1.0


# --------------------------------------------------------------- R1-P2 constraint tier
def test_p2_constraint_beats_file_path():
    _built()
    constraint = _lesson("rb26", "RB-26 crash-redelivery: consumers stay idempotent on the wake listener.",
                         category="constraint", ts=NOW - 86400 * 10)
    filehit = _lesson("filehit", "When editing scripts/bifrost_wake.py mind the chunk loop.",
                      category="general", ts=NOW)
    picked = _select([filehit, constraint])
    srcs = [p["source"] for p in picked]
    assert srcs.index("rb26") < srcs.index("filehit"), \
        "P2: a keyword-overlapping constraint outranks a file-path match"


# --------------------------------------------------------------- R1-P3 file-path beats category
def test_p3_file_path_beats_category():
    _built()
    filehit = _lesson("filehit", "When editing scripts/bifrost_wake.py mind the chunk loop.",
                      category="general", ts=NOW - 86400 * 20)
    cat = _lesson("cat", "Comm systems reward idempotency.", category="comm robustness", ts=NOW)
    picked = _select([cat, filehit])
    srcs = [p["source"] for p in picked]
    assert srcs.index("filehit") < srcs.index("cat"), \
        "P3: naming the exact file under edit outranks same-domain advice"


# --------------------------------------------------------------- R1-P4 recency tiebreak
def test_p4_recency_breaks_ties():
    _built()
    older = _lesson("older", "Comm advice A.", category="comm robustness", ts=NOW - 86400 * 5)
    newer = _lesson("newer", "Comm advice B.", category="comm robustness", ts=NOW - 3600)
    picked = _select([older, newer])
    srcs = [p["source"] for p in picked]
    assert srcs.index("newer") < srcs.index("older"), "P4: same tier -> newer wins"


# --------------------------------------------------------------- R1-P5 the FIXED cap (the noise regression)
def test_p5_fixed_cap_junk_cannot_crowd_a_real_hit():
    _built()
    junk = [_lesson(f"junk{i}", f"attempt {i}", category="general", ts=NOW - i)
            for i in range(100)]   # the 'r'/'use it'/'attempt 3' shape
    hit = _lesson("hit", "Use when touching T077 seat logic: check K7 first.",
                  category="unrelated", ts=NOW - 86400 * 60)
    picked = _select(junk + [hit])
    assert picked[0]["source"] == "hit", "P5: the task-id hit must survive 100 junk lessons"
    total = sum(len(rb.render_entry(p)) for p in picked)
    assert total <= 2000, f"P5: rendered selection blew the FIXED budget ({total} chars)"


# --------------------------------------------------------------- R1-P6 funnel credit feedback
def test_p6_funnel_credit_boosts_cited_over_ignored():
    _built()
    a = _lesson("cited", "Comm advice A.", category="comm robustness", ts=NOW - 7200)
    b = _lesson("ignored", "Comm advice B.", category="comm robustness", ts=NOW - 7200)
    credit = lambda src: {"helped": 3, "surfaced": 3} if src == "cited" else {"surfaced": 9}
    picked = _select([b, a], credit=credit)
    srcs = [p["source"] for p in picked]
    assert srcs.index("cited") < srcs.index("ignored"), \
        "P6: proven-useful (funnel helped>0) must beat surfaced-and-ignored at equal tier"


# --------------------------------------------------------------- R1-P7 top hit guaranteed + clip confessed
def test_p7_top_hit_always_included_and_clip_is_said():
    _built()
    long_hit = _lesson("hit", "Use when touching T077: " + "detail " * 600,
                       category="general", ts=NOW)
    picked = _select([long_hit], cap=300)
    assert picked and picked[0]["source"] == "hit", "P7: the top hit must ALWAYS be included"
    line = rb.render_entry(picked[0])
    assert len(line) <= 300 and "[budget]" in line, \
        "P7: an over-budget top entry is clipped WITH an explicit marker (packet law)"


# --------------------------------------------------------------- R1-P8 zero-relevance floor
def test_p8_irrelevant_lessons_never_ride_when_a_relevant_one_exists():
    _built()
    junk = [_lesson(f"junk{i}", f"attempt {i}", category="general", ts=NOW - i)
            for i in range(8)]
    hit = _lesson("filehit", "When editing scripts/bifrost_wake.py mind the chunk loop.",
                  category="general", ts=NOW - 86400 * 20)
    picked = _select(junk + [hit])
    assert [p["source"] for p in picked] == ["filehit"], \
        "P8: zero-base lessons must not take boot space while a relevant one exists"
    floor = _select(junk)   # fully irrelevant corpus -> small floor, never the flood
    assert 0 < len(floor) <= 3, "P8: irrelevant-corpus floor is at most 3 entries"


# --------------------------------------------------------------- R1-d kill switch honored by the loader
def test_kill_switch_falls_back_to_legacy(monkeypatch):
    _built()
    from core.context import learning_loader as ll
    monkeypatch.setenv("AKASHIC_RELEVANCE_BUDGET", "0")
    store = FakeStore([_lesson("only", "anything", ts=NOW)])
    out = ll.load_learnings_for_boot(TASK, learning_store=store, now=NOW)
    assert out and out[0]["source"] == "only", \
        "R1-d: kill switch must serve the legacy loader shape, not an empty section"
