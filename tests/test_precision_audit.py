"""PRE-REGISTERED ACCEPTANCE -- the recall precision audit (Daniel-approved 2026-07-27).

WHY THIS EXISTS. Every architecture position in this arc -- Sol's cells, deepseek's rules-as-data,
mine -- was argued without a single retrieval accuracy number. kimi named the hole in my position
and it was the sharpest correction of the session:

    "We have never demonstrated a ranking failure BECAUSE WE HAVE NEVER MEASURED RANKING. The
     only instrument we built this arc was a membership census, so the only failures it COULD
     find were selection-shaped. Finding selection failures under a selection streetlight does
     not make selection the constraint; it makes it the only place we looked. Your A is not a
     conclusion from evidence -- it is the absence of an instrument reporting as the absence of
     a problem."

That is the confident-zero shape, committed by me, inside the architecture I was recommending.
This module is the missing instrument.

THE DESIGN IS kimi's: sample N real hook firings, and for each SURFACED item ask whether it was
on-point FOR THE ACTION ACTUALLY TAKEN -- not for the query text. Precision >= ~80% means
selection was the constraint and ranking is fine. Low precision means ranking is broken across
the whole corpus and the build order inverts.

IT DELIBERATELY IS NOT THE SKIM TEST. kimi killed that one using my own walkthrough: usage is
not relevance. A dismissed item can be relevant; a used item can be wrong. Measuring "did the
agent use it" answers a different question than "should it have been shown".

NO NEW INSTRUMENTATION. The corpus already exists -- the impression ledger has recorded
{"t": <action>, "s": [<surfaced sources>]} per firing all along.

TWO AMENDMENTS FROM RECALL FIRING MID-BUILD, and they change the instrument materially. Both
lessons surfaced on the hook while this file was being written -- the loop working on itself.

(1) `impression_metrics_label_coverage` (mine, after a Codex cross-check overturned an earlier
framing): "before calling a rate precision, check LABEL COVERAGE first -- unlabeled is not
negative". So precision is never reported bare; it always carries the coverage it was computed
over, and an unlabelled item is never counted as off-point.

(2) `research:web:rag_eval_ragas_recall_precision_faithfulness` (kimi): retrieval evaluation
splits into CONTEXT PRECISION (of what we fetched, how much was relevant) and CONTEXT RECALL
(did we fetch what we should have). A precision-only audit CANNOT DISCRIMINATE SELECTION FROM
RANKING -- a relevant lesson that never surfaced never enters the sample, so the missing-item
failure is invisible by construction. That is the same streetlight error kimi caught in my
architecture position, one level down, and it would have made this audit unable to answer the
question it was built to settle. So the pack carries a RECALL ARM: the labeller may name corpus
items that SHOULD have surfaced and did not.

  P1  harvest returns (action, surfaced) pairs from the real ledger shape
  P2  harvest is deterministic under a seed -- the same sample is re-auditable
  P3  the labelling pack is BLIND: no usefulness counters, no credit history, no seat identity,
      so a labeller cannot infer the "expected" answer from the instrument
  P4  score reports precision AND inter-rater agreement, never precision alone
  P5  an EMPTY ledger yields STARVED, never 100% -- the audit must confess its own blindness,
      which is the whole reason it exists
  P6  precision is never reported without LABEL COVERAGE, and unlabelled is never off-point
  P7  the score carries a RECALL arm (misses named by labellers), because precision alone
      cannot tell selection from ranking

Run: py -m pytest tests/test_precision_audit.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ledger(tmp_path, rows):
    d = tmp_path / "imp"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "sess.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return str(d)


ROWS = [
    {"t": "p:e:/ai-setup/core/comm/doctor.py", "s": ["learn:experiment:daemon_needs_spawn_runner"]},
    {"t": "c:py agent_cli.py bifrost-sync claude", "s": ["learn:experiment:wake_watcher_insta_fires"]},
    {"t": "p:e:/ai-setup/docs/WISHLIST.md", "s": ["learn:experiment:semantic_naming", "learn:experiment:x"]},
]


def test_p1_harvest_returns_action_and_surfaced(tmp_path):
    from core.recall import precision_audit as pa
    items = pa.harvest(imp_dir=_ledger(tmp_path, ROWS))
    assert len(items) == 3
    one = next(i for i in items if i["action"].endswith("doctor.py"))
    assert one["action_kind"] == "path"
    assert one["surfaced"] == ["learn:experiment:daemon_needs_spawn_runner"]


def test_p2_sampling_is_deterministic(tmp_path):
    from core.recall import precision_audit as pa
    d = _ledger(tmp_path, ROWS * 20)
    a = [i["action"] for i in pa.sample(pa.harvest(imp_dir=d), n=5, seed=7)]
    b = [i["action"] for i in pa.sample(pa.harvest(imp_dir=d), n=5, seed=7)]
    assert a == b and len(a) == 5, "the same seed must re-draw the same sample, or no audit is re-auditable"


def test_p3_the_pack_is_blind(tmp_path):
    """A labeller who can see credit history is not labelling relevance, they are reading the
    instrument's prior opinion back to it."""
    from core.recall import precision_audit as pa
    items = pa.harvest(imp_dir=_ledger(tmp_path, ROWS))
    pack = pa.render_pack(items, bodies={"learn:experiment:daemon_needs_spawn_runner": "relaunch a seat with --spawn-runner"})
    low = pack.lower()
    for leak in ("helped", "useful", "noise", "surfaced=", "credit", "worked claude"):
        assert leak not in low, f"the pack leaks prior credit signal ({leak!r}) -- labels would echo the ranker"
    assert "daemon_needs_spawn_runner" in pack and "doctor.py" in pack


def test_p4_score_reports_agreement_not_just_precision(tmp_path):
    from core.recall import precision_audit as pa
    labels = {
        "claude":   {"1:a": "on", "2:a": "off", "3:a": "on"},
        "deepseek": {"1:a": "on", "2:a": "off", "3:a": "off"},
    }
    r = pa.score(labels)
    assert 0.0 <= r["precision"] <= 1.0
    assert "agreement" in r and 0.0 <= r["agreement"] <= 1.0
    assert r["disputed"] == ["3:a"], "items the labellers disagree on must be named for the fence round"


def test_p5_an_empty_ledger_is_starved_not_perfect(tmp_path):
    """The audit must confess its own blindness. An instrument that reports 100% precision
    over zero observations is the exact disease this whole arc has been chasing."""
    from core.recall import precision_audit as pa
    items = pa.harvest(imp_dir=str(tmp_path / "nothing"))
    r = pa.score({})
    assert items == []
    assert r["status"] == "STARVED", "no observations rendered as a number instead of a confession"
    assert r["precision"] is None


def test_p6_precision_never_travels_without_its_coverage():
    """My own lesson, after a Codex cross-check overturned an earlier framing: unlabelled is
    NOT negative. A precision figure quoted without the coverage it was computed over invites
    exactly the misreading that overturned the last one."""
    from core.recall import precision_audit as pa
    labels = {"claude": {"1:a": "on", "2:a": "off"}}          # 2 of 5 surfaced items labelled
    r = pa.score(labels, total_surfaced=5)
    assert r["label_coverage"] == 0.4
    assert r["labelled"] == 2 and r["precision"] == 0.5, (
        "precision must be computed over LABELLED items only -- counting the 3 unlabelled as "
        "off-point would report 20% and be a lie")


def test_p7_the_score_carries_a_recall_arm():
    """kimi's RAGAS point. Precision answers 'of what we showed, how much was good'. It cannot
    answer 'what should we have shown and did not' -- and that second question is the entire
    selection-vs-ranking dispute. Without a recall arm this audit cannot settle the thing it
    was built to settle."""
    from core.recall import precision_audit as pa
    r = pa.score({"claude": {"1:a": "on"}}, total_surfaced=1,
                 misses={"claude": {"1": ["learn:experiment:should_have_fired"]}})
    assert r["misses_named"] == 1
    assert "recall" in r and r["recall"] is not None, (
        "no recall arm -- a precision-only audit is blind to the missing-item failure by "
        "construction, which is the selection half of the question")
