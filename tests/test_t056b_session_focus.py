"""Pins for session focus -- the missing input to T056's cost telemetry.

WHY THIS EXISTS. T056 shipped per-task cost telemetry with `tool_calls` as one of its four
fields and recorded ZERO across 172 completed tasks. Not a bug: task_costs._active_task_for()
attributes to "the ONE task owned by this agent in in_progress or verifying" and refuses on 0 or
>1. Measured 2026-09-27: ELEVEN tasks are active, nine owned by `claude` and two by `sol`, so both
owners refuse and nothing is ever attributed. Owner matching cannot disambiguate nine open tasks;
a session declaring which one it is on can. These pins hold that primitive, and the two widenings
in task_costs it required, in place.

  F1  attribution lands on task_costs' OWN accumulator (no second ledger)
  F2  hits and misses are distinguished by the task's declared files
  F3  the nudge is evidence-based: silent below the miss threshold
  F4  the nudge NEVER fires for a task that declares no files (no evidence -> no nagging)
  F5  quiet() silences notes while attribution continues
  F6  two dismissals silence it without the operator doing anything
  F7  finalize() no longer discards a tool-calls-only accumulator (the gate that ate it)
  F8  cost_line() renders a tool-calls-only task instead of returning ''
  F9  a focus on an unknown task id is refused, not silently accepted
"""
import json
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A throwaway namespace, a throwaway ledger, and SF pointed at both."""
    ns = f"t056b_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    from core.coord.task_ledger import TaskLedger
    from core.coord import session_focus as SF

    # TaskLedger.load() reads `tasks` as a LIST and keys it by id itself (task_ledger.py:283).
    tasks = [
        {"id": "T900", "title": "with files", "owner": "claude", "status": "in_progress",
         "files": ["core/eye/index.py", "scripts/hooks/"], "history": []},
        {"id": "T901", "title": "no files", "owner": "claude", "status": "in_progress",
         "files": [], "history": []},
    ]
    p = tmp_path / "tasks.json"
    p.write_text(json.dumps({"seq": 1, "tasks": tasks}), encoding="utf-8")
    led = TaskLedger(path=str(p), client=None)
    monkeypatch.setattr(SF, "_ledger", lambda: led)
    c = _client()
    monkeypatch.setattr(SF, "_client", lambda: c)
    from core.coord import task_costs as TC
    monkeypatch.setattr(TC, "_client", lambda: c)
    sid = f"sess-{uuid.uuid4().hex[:8]}"
    yield SF, TC, sid, ns, c
    for k in c.scan_iter(match=f"{ns}:*", count=200):
        c.delete(k)


def test_f1_attribution_lands_on_the_t056_accumulator(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    for _ in range(3):
        SF.record_call(sid, "Read", "core/eye/index.py")
    assert c.hget(TC._acc_key("T900"), "tool_calls") == "3", \
        "F1: calls must land on task_costs' own key so its DONE path finalizes them"


def test_f2_hits_and_misses_follow_the_declared_files(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    SF.record_call(sid, "Read", "core/eye/index.py")          # exact file
    SF.record_call(sid, "Write", "scripts/hooks/whatever.py")  # under a declared dir
    SF.record_call(sid, "Read", "arsenal/web/piano.js")        # elsewhere
    st = SF.current(sid)
    assert (st["hits"], st["misses"]) == (2, 1), f"F2: got {st}"
    assert st["streak"] == 1, "F2: the miss streak counts consecutive misses only"
    SF.record_call(sid, "Read", "core/eye/index.py")
    assert SF.current(sid)["streak"] == 0, "F2: a hit resets the streak"


def test_f3_the_nudge_is_silent_below_the_threshold(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    for _ in range(SF.MISS_BEFORE_NUDGE - 1):
        SF.record_call(sid, "Read", "somewhere/else.txt")
    assert SF.drift_note(sid) is None, "F3: a run shorter than the threshold must stay quiet"
    SF.record_call(sid, "Read", "somewhere/else.txt")
    note = SF.drift_note(sid)
    assert note and "T900" in note, "F3: the nudge fires at the threshold and names the task"
    assert "call" in note.lower(), "F3: it reports the EVIDENCE (a run of calls), not elapsed time"
    assert SF.drift_note(sid) is None, "F3: it must earn the next one, not repeat every call"


def test_f4_a_task_with_no_declared_files_is_never_nagged(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T901")                                  # declares no files
    for _ in range(SF.MISS_BEFORE_NUDGE * 2):
        SF.record_call(sid, "Read", "anything/at/all.py")
    assert SF.drift_note(sid) is None, \
        "F4: with nothing declared there is no evidence of drift, and a nudge would be a guess"
    assert c.hget(TC._acc_key("T901"), "tool_calls") == str(SF.MISS_BEFORE_NUDGE * 2), \
        "F4: attribution still works for a task that declares no files"


def test_f5_quiet_silences_notes_but_keeps_counting(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    SF.quiet(sid)
    for _ in range(SF.MISS_BEFORE_NUDGE + 2):
        SF.record_call(sid, "Read", "elsewhere.py")
    assert SF.drift_note(sid) is None, "F5: quiet means quiet"
    assert int(c.hget(TC._acc_key("T900"), "tool_calls")) == SF.MISS_BEFORE_NUDGE + 2, \
        "F5: silencing the NOTE must not silence the ATTRIBUTION"


def test_f6_two_dismissals_silence_it_on_their_own(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    for _ in range(SF.DISMISS_QUIET):
        for _ in range(SF.MISS_BEFORE_NUDGE):
            SF.record_call(sid, "Read", "elsewhere.py")
        assert SF.drift_note(sid), "F6: it should still be speaking before the dismissals land"
        SF.dismiss(sid)
    for _ in range(SF.MISS_BEFORE_NUDGE):
        SF.record_call(sid, "Read", "elsewhere.py")
    assert SF.drift_note(sid) is None, \
        "F6: a detector the operator keeps waving off must stop asking by itself"


def test_f7_finalize_keeps_a_tool_calls_only_accumulator(env):
    SF, TC, sid, ns, c = env
    SF.set_focus(sid, "T900")
    for _ in range(5):
        SF.record_call(sid, "Read", "core/eye/index.py")
    task = {"id": "T900", "status": "done"}
    stamped = TC.finalize("T900", task)
    assert stamped.get("cost_tool_calls") == 5, \
        ("F7: the old gate required turns>0 and DELETED an accumulator fed per tool call -- "
         f"got {stamped}")
    assert not c.exists(TC._acc_key("T900")), "F7: the accumulator is still consumed once"
    assert TC.finalize("T900", dict(task)) == {}, "F7: an empty accumulator still stamps nothing"


def test_f8_cost_line_renders_a_tool_calls_only_task(env):
    SF, TC, sid, ns, c = env
    line = TC.cost_line({"status": "done", "cost_tool_calls": 42})
    assert line and "42" in line, f"F8: a tool-calls-only task must not render as nothing: {line!r}"
    assert TC.cost_line({"status": "in_progress", "cost_tool_calls": 42}) == "", \
        "F8: K5 still holds -- live tasks never render cost"


def test_f9_an_unknown_task_is_refused(env):
    SF, TC, sid, ns, c = env
    r = SF.set_focus(sid, "T99999")
    assert not r.get("ok"), "F9: focusing a typo would attribute a day's work to nothing"
    assert SF.current(sid) is None, "F9: a refused focus must leave no record behind"
