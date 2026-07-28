"""T116 -- STALENESS MUST BE VISIBLE ON PROCESSES THAT PREDATE THE DETECTOR. RED first (M3).

T114 made a heartbeat stamp the commit its process is executing, and the roster
derive STALE-CODE from it. It closed the gap for every process started AFTERWARDS
and could not see a single one of the processes that caused the gap. I said so to
the fleet at the time -- "the first process to benefit from a staleness detector is
the one started after it" -- and then left it there, which is the wrong place to
leave a known hole.

It is solvable, and the evidence is already on the machine. The runner lock records
a pid; the OS records when that pid started; git records when each commit landed.

    bifrost:runner:deepseek  pid 44680  started 2026-07-28T04:38:49
    bifrost:runner:kimi      pid 47800  started 2026-07-28T04:38:55
    HEAD                                committed 2026-07-28T05:51:27

Both runners are older than HEAD by over an hour, and every commit in between is
code they cannot be running. No cooperation from the process required -- which is
the whole point, because the processes that most need to be caught are exactly the
ones too old to have been taught to report.

WHAT THIS MAY AND MAY NOT CLAIM. A process older than a commit definitely does not
contain it. A commit landing after a process started does not necessarily CHANGE
that process's behaviour -- it may touch nothing it imports. So this reports a FACT
("N commits have landed since this process started"), never a verdict ("this process
is wrong"). Where T114's stamp is present it is exact and wins; this is the fallback
for everyone else, and it says which of the two answered.

  P1  A PROCESS OLDER THAN HEAD REPORTS THE COMMITS IT CANNOT CONTAIN.
  P2  A FRESH PROCESS REPORTS ZERO -- no crying wolf, the standing rule of this arc.
  P3  THE EXACT STAMP WINS WHEN PRESENT. Process age is an upper bound; a self-
      reported sha is ground truth, and a fallback must never override evidence.
  P4  THE ANSWER SAYS WHICH SOURCE IT CAME FROM. A number whose provenance is
      invisible cannot be argued with, and "started before / definitely running
      the wrong code" are different claims that must not be confused.
  P5  A DEAD OR UNREADABLE PID IS UNKNOWN, NEVER STALE.
  P6  NEVER RAISES, AND NEVER BLOCKS. The doctor runs this on a hot path; an
      observability probe that can hang the diagnostic is worse than no probe.
  P7  THE PER-PID PROBE IS CACHED. A process's start time cannot change, so
      spawning a subprocess per doctor tick to re-learn a constant is waste.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import runtime_age


# --------------------------------------------------------------- P1
def test_p1_an_old_process_reports_the_commits_it_cannot_contain():
    """deepseek's runner, live: started 04:38:49 while HEAD landed 05:51:27."""
    got = runtime_age.describe(pid=1234, started_at="2000-01-01T00:00:00+00:00",
                               stamped_sha="")
    assert got["commits_behind"] > 0, (
        f"a process from the year 2000 must report commits it cannot contain: {got}")
    assert got["state"] == "stale", got


# --------------------------------------------------------------- P2
def test_p2_a_fresh_process_reports_zero():
    """No crying wolf. This arc has spent all night on what false pages cost."""
    got = runtime_age.describe(pid=1234, started_at="2099-01-01T00:00:00+00:00",
                               stamped_sha="")
    assert got["commits_behind"] == 0, f"a future-dated process is not behind: {got}"
    assert got["state"] == "current", got


# --------------------------------------------------------------- P3
def test_p3_the_exact_stamp_wins_over_the_age_estimate():
    """Process age is an UPPER BOUND on what a process can contain; a self-reported
    sha is ground truth. A fallback that overrides evidence is not a fallback."""
    head = runtime_age.head_sha()
    got = runtime_age.describe(pid=1234, started_at="2000-01-01T00:00:00+00:00",
                               stamped_sha=head)
    assert got["state"] == "current", (
        f"an ancient process that STAMPED the current HEAD has been restarted into it "
        f"-- or is running it some other way -- and the stamp is the better witness: {got}")
    assert got["source"] == "stamp", got


# --------------------------------------------------------------- P4
def test_p4_the_answer_names_its_source():
    by_age = runtime_age.describe(pid=1234, started_at="2000-01-01T00:00:00+00:00",
                                  stamped_sha="")
    assert by_age["source"] == "process_age", (
        f"'started before' and 'definitely running the wrong code' are different claims; "
        f"the reader must be able to tell which one this is: {by_age}")


# --------------------------------------------------------------- P5
def test_p5_a_dead_or_unreadable_pid_is_unknown_never_stale():
    got = runtime_age.describe(pid=0, started_at="", stamped_sha="")
    assert got["state"] == "unknown", (
        f"absence of evidence gets its own word -- accusing a process we cannot read is "
        f"how a real staleness report gets ignored: {got}")
    assert got["commits_behind"] == 0


# --------------------------------------------------------------- P6
def test_p6_never_raises_and_never_blocks(monkeypatch):
    """The doctor calls this on a hot path."""
    def _boom(*a, **k):
        raise RuntimeError("no such process, and the shell is on fire")

    monkeypatch.setattr(runtime_age, "_probe_start_time", _boom)
    got = runtime_age.for_agent("nobody-home")          # must not raise
    assert got["state"] == "unknown", got


# --------------------------------------------------------------- P7
def test_p7_the_per_pid_probe_is_cached(monkeypatch):
    """A process's start time cannot change. Spawning a subprocess per doctor tick to
    re-learn a constant is waste on a path that runs constantly."""
    calls = []

    def _counted(pid):
        calls.append(pid)
        return "2000-01-01T00:00:00+00:00"

    runtime_age._START_CACHE.clear()
    monkeypatch.setattr(runtime_age, "_probe_start_time", _counted)
    for _ in range(5):
        runtime_age.start_time(4242)
    assert len(calls) == 1, f"probed {len(calls)} times for one pid; expected 1"
