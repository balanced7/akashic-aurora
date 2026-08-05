"""
Auto-logger Slice 5 -- salience promotion (reflection / episodic->semantic consolidation).

Acceptance bar (docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md):
  - promotion is rate-limited (threshold + per-run cap + dedup) -> no Beat flood;
  - coverage of high-salience events >= 95%;
  - the narrative's faithfulness/coverage bars do not regress (full suite stays green);
  - a promoted Beat preserves provenance (points AT the raw atom).

Prior art grounding (in code docstring): Generative Agents importance + threshold-triggered
reflection; GAM/SEEM write-isolation + provenance pointer; Nemori "heuristics are a baseline".
"""
import os
import sys
import tempfile

import isolate_canonical            # noqa: F401

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)

from core.foundation.store import FileStore
from core.foundation.ledger import FileLedger
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from core.narrative.beat_log import BeatLog
from core.narrative.event_promoter import salience, promote_salient, PROMOTED_SET
from core.narrative.event_bridge import raw_for_beat


def _ctx():
    store = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    eq = EventQuery(EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="prom_"))))
    return store, eq


# ----------------------------------------------------------------- salience scoring

def test_salience_mundane_vs_salient():
    assert salience({"kind": "note", "summary": "idle"}) == 1
    assert salience({"kind": "tool_call", "summary": "listed the files"}) == 1
    assert salience({"kind": "milestone", "summary": "shipped it"}) == 5
    assert salience({"kind": "command", "summary": "error: the build failed"}) >= 4
    assert salience({"kind": "file_edit", "summary": "fixed the crash bug"}) >= 3


def test_salience_clamped_0_5():
    s = salience({"kind": "milestone", "summary": "shipped fix for the crash bug breakthrough"})
    assert 0 <= s <= 5


# ----------------------------------------------------------------- coverage + no flood

def test_coverage_and_no_flood():
    store, eq = _ctx()
    # high-salience (eligible)
    eq.log.capture("command", "error: the build failed", at="2026-06-22T10:00:00")
    eq.log.capture("file_edit", "fixed the crash bug", at="2026-06-22T10:05:00")
    eq.log.capture("milestone", "shipped slice 5", at="2026-06-22T10:10:00")
    eq.log.capture("blocker", "blocked on a missing dependency", at="2026-06-22T10:15:00")
    # mundane (< threshold) -> must NOT be promoted (no flood)
    eq.log.capture("tool_call", "listed the files", at="2026-06-22T10:20:00")
    eq.log.capture("observation", "looked around the repo", at="2026-06-22T10:25:00")
    eq.log.capture("note", "misc scratch", at="2026-06-22T10:30:00")
    # already has a Beat (git ref) -> skipped, never double-promoted
    eq.log.capture("command", "git commit: wip", refs=["git:abc123"], at="2026-06-22T10:35:00")

    rep = promote_salient(store, eq, threshold=3, max_promote=50)
    assert rep["eligible"] == 4
    assert rep["promoted"] / rep["eligible"] >= 0.95          # coverage bar
    assert rep["promoted"] == 4
    assert rep["skipped_beat"] == 1                           # the git-ref one

    beat_summaries = {b.summary for b in BeatLog(store).recent(100)}
    assert "shipped slice 5" in beat_summaries
    assert "listed the files" not in beat_summaries           # mundane stayed out
    assert "misc scratch" not in beat_summaries
    assert "git commit: wip" not in beat_summaries            # already-beat stayed out


def test_dedup_on_rerun():
    store, eq = _ctx()
    eq.log.capture("command", "error: build failed", at="2026-06-22T10:00:00")
    eq.log.capture("milestone", "shipped a thing", at="2026-06-22T10:05:00")
    first = promote_salient(store, eq, threshold=3, max_promote=50)
    second = promote_salient(store, eq, threshold=3, max_promote=50)
    assert first["promoted"] == 2
    assert second["promoted"] == 0                            # nothing re-promoted
    assert second["skipped_dup"] == 2
    assert len(store.smembers(PROMOTED_SET)) == 2


def test_rate_limit_cap():
    store, eq = _ctx()
    for i in range(5):
        eq.log.capture("milestone", f"shipped milestone {i}", at=f"2026-06-22T10:0{i}:00")
    rep = promote_salient(store, eq, threshold=3, max_promote=2)
    assert rep["eligible"] == 5 and rep["promoted"] == 2      # cap respected (no flood)


def test_threshold_gates():
    store, eq = _ctx()
    eq.log.capture("file_edit", "small tweak", at="2026-06-22T10:00:00")   # salience 2
    rep = promote_salient(store, eq, threshold=3, max_promote=50)
    assert rep["promoted"] == 0
    rep2 = promote_salient(store, eq, threshold=2, max_promote=50)
    assert rep2["promoted"] == 1                              # lowering threshold lets it in


# ----------------------------------------------------------------- provenance

def test_promoted_beat_points_at_atom():
    store, eq = _ctx()
    ev = eq.log.capture("command", "error: critical failure", at="2026-06-22T12:00:00")
    promote_salient(store, eq, threshold=3, max_promote=50)
    beat = next(b for b in BeatLog(store).recent(100) if b.summary == "error: critical failure")
    assert beat.source == ev.ref                             # provenance preserved
    # and the bridge can drill back from the Beat to the raw atom
    res = raw_for_beat(beat.id, store=store, event_query=eq)
    assert res["atom"] is not None and res["atom"]["summary"] == "error: critical failure"


def test_promote_empty_never_raises():
    store, eq = _ctx()
    rep = promote_salient(store, eq)
    assert rep == {"scanned": 0, "eligible": 0, "promoted": 0, "skipped_dup": 0, "skipped_beat": 0}
