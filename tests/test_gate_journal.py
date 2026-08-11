"""Pre-registered pins: the gate journal -- an append-only history of gate verdicts.

Written and committed BEFORE the implementation they gate (M3).

WHY. core/comm/door_probe.py:write_verdict CLOBBERS state/door/last_probe.json on every
run. That file is the only record the door gate keeps, and the gate can block every seat's
push. So the one instrument with veto power over the repo destroys its own history each
time it fires, and nobody -- including the gate -- can answer "was that RED real?"

Observed 2026-08-11, and the reason this exists: the gate refused a push at 5.29s against a
5.0s budget, its own named diagnostic passed, CPU was idle, it had been green three minutes
earlier, and a retry at the IDENTICAL sha measured 2.84s GREEN. I resolved a red gate by
running it again. That was probably correct and it is exactly the habit that eventually
waves a true RED through. The overwritten GREEN 2.52s reading from earlier that day was
already gone.

Prior art in this repo for gates that rot unseen: a door-parity checker that FAILED OPEN on
a moved class (66 phantom failures hid 23 real ones); check_wiring holed four times
(T143/T144/T146, and T159 found by an instrument rather than a person); a park pin that
asserted the opposite of shipped code for days. The funnel scores every LESSON by outcome.
No gate is scored by anything.

PURELY ADDITIVE BY CONSTRUCTION. These pins deliberately assert the CLOBBER still happens
and read_verdict still works. The journal is substrate only: no verdict logic, no
threshold, no gate behaviour may change, because this gate blocks every seat's push and an
instrumentation slice is not allowed to risk that.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import door_probe as DP


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    """Redirect BOTH sinks into tmp so a pin can never touch the live gate history."""
    cache = tmp_path / "door" / "last_probe.json"
    journal = tmp_path / "ci" / "gate_journal.jsonl"
    monkeypatch.setattr(DP, "CACHE", cache)
    monkeypatch.setattr(DP, "GATE_JOURNAL", journal, raising=False)
    return cache, journal


def _v(verdict="GREEN", elapsed=2.5, cause=""):
    return DP._verdict(verdict, "complete", elapsed, cause, detail="d", recovery="r")


def test_a_verdict_appends_a_journal_line(paths):
    cache, journal = paths
    DP.write_verdict(_v())
    assert journal.exists(), "no gate journal was written"
    lines = [l for l in journal.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    json.loads(lines[0])            # one JSON object per line, parseable alone


def test_the_journal_appends_and_never_truncates(paths):
    """THE POINT. last_probe.json may clobber; the journal may only grow."""
    cache, journal = paths
    DP.write_verdict(_v("GREEN", 2.52))
    DP.write_verdict(_v("RED", 5.29, "response_path_slow"))
    DP.write_verdict(_v("GREEN", 2.84))

    lines = [json.loads(l) for l in journal.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3, "a verdict overwrote history instead of appending"
    assert [r["verdict"] for r in lines] == ["GREEN", "RED", "GREEN"]
    assert lines[1]["elapsed_s"] == 5.29, "the RED reading must survive the GREEN that follows"


def test_the_line_carries_what_a_false_positive_rate_needs(paths):
    cache, journal = paths
    DP.write_verdict(_v("RED", 5.29, "response_path_slow"))
    rec = json.loads(journal.read_text(encoding="utf-8").splitlines()[0])
    for field in ("gate", "verdict", "elapsed_s", "budget_s", "sha", "at", "cause"):
        assert field in rec, f"journal line is missing {field!r}"
    assert rec["gate"] == "door", "the gate must name itself so other gates can share the file"
    assert rec["budget_s"] == DP.SLOW_BUDGET_S, "a verdict is meaningless without what it was judged against"


def test_the_clobbering_cache_is_unchanged(paths):
    """ADDITIVE: existing readers must see exactly what they saw before."""
    cache, journal = paths
    DP.write_verdict(_v("GREEN", 2.52))
    DP.write_verdict(_v("RED", 5.29, "response_path_slow"))
    assert json.loads(cache.read_text(encoding="utf-8"))["verdict"] == "RED"
    assert DP.read_verdict()["elapsed_s"] == 5.29


def test_a_journal_failure_never_breaks_the_caller(tmp_path, monkeypatch):
    """Fail-open, same contract write_verdict already holds: a history miss must never
    block a push. Instrumentation that can break the gate is worse than no instrumentation."""
    cache = tmp_path / "door" / "last_probe.json"
    monkeypatch.setattr(DP, "CACHE", cache)
    # a path that cannot be created: an existing FILE standing where a directory must go
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(DP, "GATE_JOURNAL", blocker / "gate_journal.jsonl", raising=False)

    DP.write_verdict(_v("GREEN", 2.5))          # must not raise
    assert json.loads(cache.read_text(encoding="utf-8"))["verdict"] == "GREEN"


def test_journal_records_survive_across_processes(paths):
    """The file is the record, not an in-memory list -- a fresh import must still append."""
    cache, journal = paths
    DP.write_verdict(_v("GREEN", 2.5))
    journal.write_text(journal.read_text(encoding="utf-8"), encoding="utf-8")  # simulate reopen
    DP.write_verdict(_v("RED", 6.0, "response_path_slow"))
    lines = [l for l in journal.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
