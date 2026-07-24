"""
RB-25 exam findings F1 + F2 -- pre-registered acceptance (committed BEFORE the fixes,
M3/T031). Both surfaced by the newborn-gauntlet re-run (drill 1 of the RB-25 exam,
2026-07-12); rubric + verdict in docs/library/design/20260701_newborn-gauntlet-pre-registered-rubric-t_16fdb3.md, transcript in
docs/library/report/20260712_rb-25-drill-1-newborn-gauntlet-re-run-ve_419213.md.

F1 -- a runner must self-refuse at startup when its OWN id is quarantined. The conscious
     tool doors are airtight (proven live), but the runner's reply/trace lanes are not
     ACL-gated, so a quarantined runner still narrated + replied to the bus. The clean
     fix per the threat model: a quarantined id gets no runner at all.
F2 -- a fresh agent's cursor must seed at the LIVE TAIL, not virgin "0": the newborn
     drained the stale broadcast backlog and acted on a months-old directive as current.
     Same P0 discipline the wake watcher already uses (only NEW mail wakes it).

Contract frozen:
  runner_lock / trust: a helper that answers "may this id run a runner?" -> False for
     quarantined. Named: core.trust.registry.may_run_runner(agent_id) -> bool.
  Bus.seed_cursor_at_tail() -> None: idempotent; sets the shared cursor to the current
     inbox+bc tail ONLY when the agent has never read (virgin cursor at "0"); a returning
     agent with real cursor progress is untouched.

Run: py -m pytest tests/test_rb25_newborn_findings.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trust.registry import resolve
from core.comm.bus import Bus

try:
    from core.trust.registry import may_run_runner
    _F1 = True
except ImportError:
    _F1 = False

_F2 = hasattr(Bus, "seed_cursor_at_tail")

try:
    _ONLINE = bool(Bus("rb25f-probe").online)
except Exception:
    _ONLINE = False


# ---------------- F1: runner self-refusal for a quarantined id ----------------

@pytest.mark.skipif(not _F1, reason="F1 pre-registered; may_run_runner pending")
def test_quarantined_id_may_not_run_a_runner():
    assert resolve("newborn-gauntlet-1").role == "quarantined"
    assert may_run_runner("newborn-gauntlet-1") is False, \
        "a quarantined id gets no runner -- its reply/trace lanes would otherwise reach the bus"


@pytest.mark.skipif(not _F1, reason="F1 pre-registered; may_run_runner pending")
def test_known_privileged_id_may_run():
    # deepseek is a bootstrap admin -- must still be allowed to run.
    assert may_run_runner("deepseek") is True


@pytest.mark.skipif(not _F1, reason="F1 pre-registered; may_run_runner pending")
def test_runner_startup_wired_to_the_check():
    # BOTH runner scripts must self-refuse -- the generic bifrost_runner.py was the
    # coverage gap deepseek's F1/F2 fence review caught (same reply/trace lanes, no guard).
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for runner in ("bifrost_runner_deepseek.py", "bifrost_runner.py"):
        src = open(os.path.join(root, "scripts", runner), encoding="utf-8").read()
        assert "may_run_runner" in src, f"{runner} self-refuses at startup (built != wired)"
        # The offline-drill escape exists and is gated on the never-in-production signal, so
        # throwaway-id kill-window drills still run while production stays airtight.
        assert "AKASHIC_DRILL_ECHO" in src.split("may_run_runner")[0].rsplit("RB-25 F1", 1)[-1], \
            f"{runner}'s quarantine refusal is bypassed ONLY under the offline-drill signal"


# ---------------- F2: virgin cursor seeds at the live tail ----------------

# Isolated namespace: these pins broadcast, and the live 'bifrost' stream is read by real
# wake listeners -- a test broadcast there spuriously wakes the running fleet (observed live
# 2026-07-12: the newborn-drill verify run woke claude's listener repeatedly). Route every
# Bus here to a disposable namespace; harness-only, no assertion changed (M3-safe).
_NS = "test-rb25f"


def _cleanup_ns(client):
    try:
        for k in client.keys(f"{_NS}:*") or []:
            client.delete(k)
    except Exception:
        pass


@pytest.mark.skipif(not (_F2 and _ONLINE), reason="F2 pre-registered / bus offline")
def test_virgin_cursor_seeds_at_tail_and_skips_backlog():
    backlog_sender = Bus(f"rb25f-old-{uuid.uuid4().hex[:6]}", namespace=_NS)
    aid = f"rb25f-newborn-{uuid.uuid4().hex[:6]}"
    # stale backlog exists BEFORE the newborn onboards
    backlog_sender.broadcast("chat", "months-old directive nobody should act on")
    newborn = Bus(aid, namespace=_NS)
    try:
        newborn.seed_cursor_at_tail()                 # onboarding step
        fresh = newborn.inbox(limit=50, advance=False)
        assert fresh == [], "a seeded newborn sees NO stale backlog -- only new mail after it"
        backlog_sender.broadcast("chat", "a NEW message after onboarding")
        after = newborn.inbox(limit=50, advance=False)
        assert any("NEW message" in str(m.content) for m in after), \
            "new mail after seeding still arrives -- seed skips backlog, not the future"
    finally:
        _cleanup_ns(newborn._client)


@pytest.mark.skipif(not (_F2 and _ONLINE), reason="F2 pre-registered / bus offline")
def test_seed_is_idempotent_and_spares_a_returning_agent():
    backlog = Bus(f"rb25f-b-{uuid.uuid4().hex[:6]}", namespace=_NS)
    aid = f"rb25f-return-{uuid.uuid4().hex[:6]}"
    a = Bus(aid, namespace=_NS)
    try:
        backlog.broadcast("chat", "m1")
        a.seed_cursor_at_tail()
        backlog.broadcast("chat", "m2 real work the agent consumed")
        a.inbox(limit=50, advance=True)               # agent makes real progress
        before = dict(a.cursor())
        a.seed_cursor_at_tail()                        # a second call must NOT rewind
        assert dict(a.cursor()) == before, "seed only acts on a virgin cursor, never rewinds progress"
    finally:
        _cleanup_ns(a._client)
