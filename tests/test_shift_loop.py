"""Pins for the pure decision core of the autonomous shift loop (core/coord/shift_loop.py).

Hermetic — no ledger, no Redis, no git, no clock. next_beat() takes a REDUCED view
(statuses + gating facts about the first candidate) and returns an action + reason.
Fail direction: idle. The claim is the mutex at the ledger (task_ledger.claim); this
module only DECIDES, it never claims.

Run: py -m pytest tests/test_shift_loop.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import shift_loop as SL


# ---------------------------------------------------------------- next_beat decisions
def test_empty_ledger_is_idle():
    r = SL.next_beat(statuses={})
    assert r["action"] == "idle"
    assert r["reason"], "a decision needs a reason (idle must name WHY)"


def test_approved_free_deps_done_is_claim():
    r = SL.next_beat(statuses={"T001": "approved"}, deps_done=True, files_held_by_other=False)
    assert r["action"] == "claim"
    assert r["task"] == "T001"


def test_approved_with_blocked_deps_is_blocked():
    r = SL.next_beat(statuses={"T001": "approved"}, deps_done=False)
    assert r["action"] == "blocked", "must not claim a task whose deps are not DONE"


def test_approved_with_files_held_is_blocked():
    r = SL.next_beat(statuses={"T001": "approved"}, deps_done=True, files_held_by_other=True)
    assert r["action"] == "blocked", "must not claim a task whose files another task holds"


def test_active_not_done_is_work():
    r = SL.next_beat(statuses={"T001": "in_progress"}, current_task_done=False)
    assert r["action"] == "work"
    assert r["task"] == "T001"


def test_active_done_is_land():
    r = SL.next_beat(statuses={"T001": "verifying"}, current_task_done=True)
    assert r["action"] == "land"
    assert r["task"] == "T001"


def test_done_task_is_not_acted_on():
    r = SL.next_beat(statuses={"T001": "done"})
    assert r["action"] == "idle", "a DONE task must never be re-claimed or re-worked"


def test_stale_restart_only_when_idle_and_past_floors():
    # behind threshold, idle, past uptime -> restart
    r = SL.next_beat(statuses={}, stale_behind=5, stale_min=3, uptime_s=1000, uptime_min=900)
    assert r["action"] == "restart"
    # behind threshold but mid-flight -> never restart
    r2 = SL.next_beat(statuses={"T001": "in_progress"}, current_task_done=False,
                      stale_behind=5, stale_min=3, uptime_s=1000, uptime_min=900)
    assert r2["action"] != "restart", "restart only at a boundary with nothing in flight"
    # behind threshold but under uptime floor -> anti-thrash, no restart
    r3 = SL.next_beat(statuses={}, stale_behind=5, stale_min=3, uptime_s=100, uptime_min=900)
    assert r3["action"] != "restart"


# ---------------------------------------------------------------- shift-state note
def test_new_shift_state_defaults_complete_shape():
    s = SL.new_shift_state(opened="heimdall @ now")
    for k in ("opened", "claimed", "landed", "handoff_for", "context", "cadence_note"):
        assert k in s, f"shift note must carry {k}"


def test_shift_state_incomplete_without_context():
    bare = SL.new_shift_state(opened="x")
    assert SL.shift_state_is_complete(bare) is False, "a handoff with no context is a non-handoff"


def test_shift_state_complete_with_context_or_cadence():
    a = SL.new_shift_state(opened="x", context="continue the T001 fix")
    b = SL.new_shift_state(opened="x", cadence_note="ending at stale-code boundary")
    assert SL.shift_state_is_complete(a) is True
    assert SL.shift_state_is_complete(b) is True


def test_shift_state_title_is_stable():
    assert SL.SHIFT_STATE_TITLE == "shift-state", "re-noting the SAME title is what makes it idempotent"
