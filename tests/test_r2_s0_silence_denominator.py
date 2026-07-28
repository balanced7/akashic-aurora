"""R2 slice 0 -- THE SILENT HALF OF RECALL IS RECORDED. RED first (M3).

THE GAP, measured 2026-07-28 while writing the R2 opening position: recall:surface
logs FIRINGS only (168 in the last 24h). Silent calls -- the floor suppressing
everything, an empty query, an error path -- leave NO record anywhere. So the
census's headline target ("at minimum 27% of firings should be silent",
NONE-NEEDED = 8/30 in BOTH blind judges, exact) is UNVERIFIABLE with today's
instrumentation. We cannot say what fraction of calls are already silent under the
existing 0.20 floor, which means we cannot say whether the correlation gate is
even needed at volume, let alone whether it works.

The instrument records only the positive half. That is the fifth-or-sixth instance
of tonight's single disease, and this slice is the cheapest possible cure: record
the outcome of EVERY call, then "what % is silent" becomes a query.

This slice adds NO silencing. It is the denominator, built before the gate so the
gate's effect lands on a baseline instead of an anecdote. Slice 1 (the silence
predicate) is under adversarial review and does not exist yet.

  P1  A FIRING CALL RECORDS outcome=fired with n_items.
  P2  A FLOOR-SILENT CALL RECORDS outcome=silent, reason=floor_silent -- the
      call happened, ranking ran, nothing cleared the floor. TODAY this leaves
      no trace; this pin is the slice.
  P3  AN EMPTY-QUERY CALL RECORDS reason=empty_query (no path, no command
      tokens). Distinct from floor_silent: nothing was even rankable.
  P4  THE ERROR PATH RECORDS reason=error_empty. recall_at's contract is
      fail-soft-to-empty; an empty-from-crash that renders identically to
      empty-from-judgment is the confident-zero disease at the meta level.
  P5  THE RECORD IS QUERYABLE: silence_rate() over a window returns
      {calls, fired, silent, by_reason} -- the number the census bar needs.
  P6  RECORDING NEVER BREAKS RECALL. The outcome row is observability riding a
      hot path; an exception inside it must not cost the caller its items.
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import at_action as A


@pytest.fixture
def fake_store():
    """A learning store double with one strongly-matching lesson, so a firing call
    can fire without Redis. Shape mirrors _project_items' input contract."""
    class _Rec(dict):
        pass

    class _Store:
        # the contract _cached_items actually calls on an injected store -- read the
        # producer, do not guess the method name (first draft used find_lessons and
        # every call crashed into error_empty, which P4 then happily recorded).
        def load_all_learnings_from_store(self, *a, **k):
            return [{"experiment_name": f"r2pin_{uuid.uuid4().hex[:6]}",
                     "recommendation": "use the frobnicator before the veeblefetzer "
                                       "when frobnicating the r2 denominator pin",
                     "what_worked": "frobnicate first", "created_at": "2026-07-28",
                     "success": "yes", "agent_id": "pin"}]
    return _Store()


@pytest.fixture(autouse=True)
def _isolated_outcomes(tmp_path, monkeypatch):
    """Point the outcome sink at a temp dir so pins never pollute production streams
    (the 2026-07-02 hermeticity rule) -- and so assertions can read it back."""
    monkeypatch.setattr(A, "_OUTCOME_DIR", str(tmp_path), raising=False)
    yield tmp_path


def _outcomes(tmp_path):
    import json
    rows = []
    p = tmp_path / "recall_outcomes.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------- P1
def test_p1_a_firing_call_records_fired(fake_store, _isolated_outcomes):
    r = A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                    learning_store=fake_store, min_relevance=0.0)
    rows = _outcomes(_isolated_outcomes)
    assert rows, "a recall_at call must leave an outcome row"
    last = rows[-1]
    assert last["outcome"] == "fired", last
    assert last.get("n_items", 0) >= 1, last


# --------------------------------------------------------------- P2 the slice
def test_p2_a_floor_silent_call_records_floor_silent(fake_store, _isolated_outcomes):
    """The call ran, ranking ran, nothing cleared the floor. Today: no trace."""
    r = A.recall_at(command="frobnicate the r2 denominator pin",
                    learning_store=fake_store, min_relevance=99.0)   # nothing clears
    assert not r.get("lessons"), "precondition: this call must be silent"
    rows = _outcomes(_isolated_outcomes)
    assert rows, (
        "SILENT AND INVISIBLE: a floor-silent call left no record. This is the exact "
        "gap -- 27%-should-be-silent is unverifiable when silence writes nothing.")
    assert rows[-1]["outcome"] == "silent" and rows[-1]["reason"] == "floor_silent", rows[-1]


# --------------------------------------------------------------- P3
def test_p3_an_empty_query_records_empty_query(fake_store, _isolated_outcomes):
    A.recall_at(command="", path=None, learning_store=fake_store)
    rows = _outcomes(_isolated_outcomes)
    assert rows and rows[-1]["outcome"] == "silent", rows[-1] if rows else None
    assert rows[-1]["reason"] == "empty_query", (
        f"nothing was even RANKABLE -- that is a different fact from 'ranked and "
        f"nothing cleared', and conflating them hides query-construction bugs: {rows[-1]}")


# --------------------------------------------------------------- P4
def test_p4_the_error_path_records_error_empty(_isolated_outcomes, monkeypatch):
    """recall_at is fail-soft-to-empty BY CONTRACT. An empty-from-crash that renders
    identically to empty-from-judgment is confident-zero at the meta level."""
    def _boom(*a, **k):
        raise RuntimeError("ranking exploded")

    monkeypatch.setattr(A, "_lessons", _boom)
    r = A.recall_at(command="anything at all here", learning_store=None)
    assert not r.get("lessons"), "contract: fail-soft returns empty"
    rows = _outcomes(_isolated_outcomes)
    assert rows and rows[-1]["reason"] == "error_empty", (
        f"a crash-empty must be distinguishable from a judged-empty: {rows[-1] if rows else None}")


# --------------------------------------------------------------- P5
def test_p5_silence_rate_is_a_query(fake_store, _isolated_outcomes):
    A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                learning_store=fake_store, min_relevance=0.0)          # fired
    A.recall_at(command="frobnicate the r2 pin", learning_store=fake_store,
                min_relevance=99.0)                                    # floor_silent
    A.recall_at(command="", learning_store=fake_store)                 # empty_query
    stats = A.silence_rate()
    assert stats["calls"] == 3 and stats["fired"] == 1 and stats["silent"] == 2, stats
    assert stats["by_reason"].get("floor_silent") == 1, stats
    assert stats["by_reason"].get("empty_query") == 1, stats


# --------------------------------------------------------------- P6
def test_p6_recording_never_breaks_recall(fake_store, _isolated_outcomes, monkeypatch):
    """Observability riding a hot path must never cost the caller its items."""
    monkeypatch.setattr(A, "_record_outcome",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sink down")),
                        raising=False)
    r = A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                    learning_store=fake_store, min_relevance=0.0)
    assert r.get("lessons"), (
        "the outcome sink threw and the caller lost its items -- observability must "
        "never wedge the path it observes (liveness.py's own rule, same layer)")


# --------------------------------------------------------------- P7 deepseek's review bonus
def test_p7_the_outcome_row_carries_the_query_shape(fake_store, _isolated_outcomes):
    """deepseek's R2 review, the actionable line: "add query_shape to the slice-0
    outcome row so silent records are auditable against the census cases that
    justified them." The census's NONE-NEEDED reasons are SHAPE reasons (pure count,
    tool-is-retrieval, work-already-done) -- a silent row that cannot say what SHAPE
    of action went silent cannot be audited against the pack that justified the
    silence, and slice 1's gate rules will key on exactly this field."""
    A.recall_at(command="git commit -q -m done", learning_store=fake_store,
                min_relevance=99.0)                                    # silent
    A.recall_at(path=r"E:\AI-Setup\core\recall\at_action.py",
                learning_store=fake_store, min_relevance=99.0)         # silent
    rows = _outcomes(_isolated_outcomes)
    assert len(rows) >= 2
    assert rows[-2].get("query_shape") == "command", rows[-2]
    assert rows[-1].get("query_shape") == "path", rows[-1]


# --------------------------------------------------------------- P8/P9 sol's fence
def test_p8_anti_repeat_silence_is_not_floor_silence(fake_store, _isolated_outcomes):
    """Sol's R2-s0 fence, reproduced finding (1): a lesson that RANKED ABOVE THE FLOOR
    but was suppressed by exclude_sources (anti-repeat) records floor_silent -- so the
    reason column reports 'nothing relevant existed' when the truth is 'the relevant
    thing was already shown'. Slice 1 will read by_reason['floor_silent'] as the
    existing floor's behaviour; a mixed bucket poisons that read."""
    r = A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                    learning_store=fake_store, min_relevance=0.0)
    assert r.get("lessons"), "precondition: this fires when not excluded"
    shown = {l["source"] for l in r["lessons"]}

    r2 = A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                     learning_store=fake_store, min_relevance=0.0,
                     exclude_sources=shown)
    assert not r2.get("lessons"), "precondition: anti-repeat suppresses everything"
    rows = _outcomes(_isolated_outcomes)
    assert rows[-1]["reason"] == "excluded_silent", (
        f"ANTI-REPEAT MASQUERADING AS FLOOR: items cleared the floor and were withheld "
        f"as already-shown, but the row says {rows[-1]['reason']!r} -- 'already shown' "
        f"and 'nothing relevant' are different facts: {rows[-1]}")


def test_p9_faithfulness_rejection_is_not_floor_silence(fake_store, _isolated_outcomes,
                                                        monkeypatch):
    """Sol's fence, reproduced finding (2): lessons cleared the floor, then
    faithfulness_report rejected the render -- recall_at zeroes the items (correct:
    silence beats a fabricated hint) and then records floor_silent (wrong: the floor
    never silenced anything; the FAITH gate did)."""
    import core.primitives.faithfulness as F
    monkeypatch.setattr(F, "faithfulness_report",
                        lambda *a, **k: {"faithful": False, "confidence": 0.0})
    r = A.recall_at(command="frobnicate the r2 denominator pin with the frobnicator",
                    learning_store=fake_store, min_relevance=0.0)
    assert not r.get("lessons"), "precondition: FAITH gate zeroes the items"
    rows = _outcomes(_isolated_outcomes)
    assert rows[-1]["reason"] == "unfaithful_silent", (
        f"FAITH REJECTION MASQUERADING AS FLOOR: {rows[-1]}")
