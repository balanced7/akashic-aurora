"""W153 pins: no pid dies unidentified -- the janitor kill window, closed.

Build authority: research/in-flight/w153-janitor-reconciliation-2026-08-13.md
(atom art_20260813_w153-janitor-reconciliation_cb84b6; claude+deepseek fence).
Intent, Daniil verbatim: "I thought I lost a friend last night, safety first."

The confirmed defect (fan 2026-08-13, verified by read): the fresh-marker fast
path synthesized pid_is_watcher=True without is_watcher, and a tombstoned sid
then returned kill -- for up to fresh_minutes after a session ended, a RECYCLED
pid could be killed unidentified.

Reconciled contract highlights the pins encode:
  K1' kill warrant = is_watcher AND agent-match on a same-pass snapshot; the
      fence caught that name-match alone can kill ANOTHER agent's watcher, and
      the reconciliation caught that the agent token needs a word boundary
      (--agent codex is a substring of --agent codex_root).
  Tri-state identity: None=unverified (never judged), False=verified-not-ours
      (clean), True=verified-ours (kill eligible). deepseek's honest-inputs
      sketch with a bare False would have cleaned every healthy fresh seat at
      reap_decision's not-a-watcher gate -- the tri-state is the reconciliation.
  K3  taskkill success = returncode 0; a failed kill RETAINS the seat file.
  K4  exact-component seat enumeration; codex never touches codex_root seats.
  K6' malformed seats: young -> skip (fail-toward-alive), old -> clean (drains).
  P5  inertness guard: a REAL dead watcher must still die.
"""
import os
import time

import pytest

from core.comm import wake_seat as ws


SID = "aaaabbbb-cccc-dddd-eeee-ffff00001111"
AGENT = "claude"


def _seat(tmp_path, agent, sid, body="4242"):
    p = tmp_path / f"bifrost_wake_{agent}_{sid}.pid"
    p.write_text(body, encoding="utf-8")
    return p


def _marker(tmp_path, agent, sid, age_min=0.0):
    p = tmp_path / f"bifrost_wake_{agent}_{sid}.alive"
    p.write_text(str(time.time() - age_min * 60), encoding="utf-8")
    return p


def _tomb(tmp_path, sid):
    p = tmp_path / f"akashic_session_ended_{sid}.tomb"
    p.write_text(str(time.time()), encoding="utf-8")
    return p


class KillRecorder:
    def __init__(self, result=True):
        self.calls, self.result = [], result

    def __call__(self, pid):
        self.calls.append(pid)
        return self.result


def test_p1_tombstoned_recycled_pid_is_never_killed(tmp_path):
    """The confirmed defect's exact shape: tombstoned sid + FRESH marker +
    seat pid recycled to a non-watcher. Must clean the seat, never kill."""
    seat = _seat(tmp_path, AGENT, SID)
    _marker(tmp_path, AGENT, SID, age_min=1)
    _tomb(tmp_path, SID)
    snap = {4242: {"ppid": 1, "name": "python.exe",
                   "cmdline": "python totally_unrelated_job.py", "created": 1}}
    kills = KillRecorder()
    results = ws.janitor(AGENT, my_session=None, tmp=str(tmp_path),
                         snapshot_fn=lambda: snap, kill_fn=kills)
    assert kills.calls == [], f"kill_fn invoked on a recycled pid: {kills.calls}"
    acted = {os.path.basename(p): a for p, a, _ in results}
    assert acted.get(os.path.basename(str(seat))) == "clean"
    assert not seat.exists()


def test_p2_another_agents_watcher_is_not_a_kill_warrant(tmp_path):
    """K1': name-match alone is insufficient -- the pid IS a bifrost_wake, but
    it is KIMI's. Clean our stale seat; never kill their watcher."""
    _seat(tmp_path, AGENT, SID)
    _marker(tmp_path, AGENT, SID, age_min=1)
    _tomb(tmp_path, SID)
    snap = {4242: {"ppid": 1, "name": "python.exe",
                   "cmdline": "py scripts/bifrost_wake.py --agent kimi --session other",
                   "created": 1}}
    kills = KillRecorder()
    ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=kills)
    assert kills.calls == []


def test_p2b_agent_token_needs_a_word_boundary(tmp_path):
    """The reconciliation's own catch: for agent codex, a codex_root watcher's
    cmdline CONTAINS the substring --agent codex. It must not satisfy the
    codex kill warrant."""
    sid2 = "11112222-3333-4444-5555-666677778888"
    _seat(tmp_path, "codex", sid2)
    _marker(tmp_path, "codex", sid2, age_min=1)
    _tomb(tmp_path, sid2)
    snap = {4242: {"ppid": 1, "name": "python.exe",
                   "cmdline": "py scripts/bifrost_wake.py --agent codex_root --session x",
                   "created": 1}}
    kills = KillRecorder()
    ws.janitor("codex", tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=kills)
    assert kills.calls == []


def test_p3_failed_taskkill_retains_the_seat(tmp_path):
    """K3: a kill that did not provably succeed leaves the seat file for the
    next pass -- never remove evidence of a live watcher."""
    seat = _seat(tmp_path, AGENT, SID)
    _marker(tmp_path, AGENT, SID, age_min=1)
    _tomb(tmp_path, SID)
    snap = {4242: {"ppid": 1, "name": "python.exe",
                   "cmdline": f"py scripts/bifrost_wake.py --agent {AGENT} --session {SID}",
                   "created": 1}}
    kills = KillRecorder(result=False)          # taskkill fails (rc != 0)
    results = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap,
                         kill_fn=kills)
    assert kills.calls == [4242]                 # the kill WAS attempted
    assert seat.exists(), "seat file removed after a FAILED kill"
    reasons = " | ".join(r for _, _, r in results)
    assert "FAILED" in reasons.upper() or "kept" in reasons.lower()


def test_p4_codex_janitor_never_touches_codex_root_seats(tmp_path):
    """K4: exact-component enumeration. A codex_root seat file is invisible to
    the codex janitor -- and still visible to its own."""
    sid2 = "11112222-3333-4444-5555-666677778888"
    foreign = _seat(tmp_path, "codex_root", sid2)
    results = ws.janitor("codex", tmp=str(tmp_path),
                         snapshot_fn=lambda: {}, kill_fn=KillRecorder())
    touched = [p for p, _, _ in results]
    assert not any("codex_root" in p for p in touched)
    assert foreign.exists()
    own = ws.janitor("codex_root", tmp=str(tmp_path),
                     snapshot_fn=lambda: {}, kill_fn=KillRecorder())
    assert any("codex_root" in p for p, _, _ in own), \
        "codex_root's own janitor must still see its seats"


def test_p5_a_real_dead_watcher_still_dies(tmp_path):
    """The inertness guard (claude drill 3): tombstoned sid whose pid IS our
    watcher -- the janitor must kill it and clean the seat. Closing the window
    must not lobotomize the reaper."""
    seat = _seat(tmp_path, AGENT, SID)
    _marker(tmp_path, AGENT, SID, age_min=1)
    _tomb(tmp_path, SID)
    snap = {4242: {"ppid": 1, "name": "python.exe",
                   "cmdline": f"py scripts/bifrost_wake.py --agent {AGENT} --session {SID}",
                   "created": 1}}
    kills = KillRecorder(result=True)
    ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=kills)
    assert kills.calls == [4242]
    assert not seat.exists()


def test_p6_unreadable_young_seat_survives(tmp_path):
    """K6': a nonempty-unparseable seat younger than fresh_minutes may be a
    torn write -- fail toward alive, keep it."""
    seat = _seat(tmp_path, AGENT, SID, body="not-a-pid-yet")
    kills = KillRecorder()
    results = ws.janitor(AGENT, tmp=str(tmp_path),
                         snapshot_fn=lambda: {}, kill_fn=kills)
    assert seat.exists(), "young unreadable seat removed (torn-write race)"
    assert kills.calls == []
    reasons = " | ".join(r for _, _, r in results)
    assert "unread" in reasons.lower() or "K8" in reasons


def test_p7_unreadable_old_seat_drains(tmp_path):
    """K6' age gate: the same garbage older than fresh_minutes is just garbage
    -- it cleans, so the janitor never goes hoarder."""
    seat = _seat(tmp_path, AGENT, SID, body="not-a-pid")
    old = time.time() - (ws.fresh_minutes() + 10) * 60
    os.utime(seat, (old, old))
    ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: {},
               kill_fn=KillRecorder())
    assert not seat.exists()
