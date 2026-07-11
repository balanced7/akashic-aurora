"""
L1 kill-window drills (T030, RB-26+L1b acceptance) -- the runner is MURDERED inside the
consume->outcome pipeline and the invariant must hold: NO message lost, NO double reply.

The windows (armed via AKASHIC_KILLPOINT; os._exit(137) = a true crash, finally skipped):
  W1 post-consume-pre-process   -> cursor untouched; successor redelivers and answers
  W4 post-sentinel-pre-advance  -> reply + sentinel exist, cursor stale; successor
                                   redelivers, sentinel SKIPS the duplicate, cursor commits
(W2 post-phase-flip-pre-send, W3 post-send-pre-sentinel, W5 between-batch-messages share
the same machinery; W3's duplicate-reply-accepted case is pinned as a tolerance, and the
remaining windows join the harness in the L1 follow-up with the ReferenceBus CHECK.)

Drill discipline per the reconciled build spec: drill-echo responder (offline -- the
pipeline is under test, not the model), unique agent ids per run (stream isolation),
SETUP -> EXECUTION (kill) -> CHECK (invariants) -> METRICS (seed line).
Redis-backed + subprocess; skips offline. Run: py -m pytest tests/test_killwindow_drill.py -q
"""
import os
import subprocess
import sys
import uuid

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from core.comm.bus import Bus

RUNNER = os.path.join(REPO, "scripts", "bifrost_runner_deepseek.py")


def _fresh(prefix):
    b = Bus(f"{prefix}-{uuid.uuid4().hex[:8]}")
    if not b.online:
        pytest.skip("redis not available")
    # Park the bc cursor at the live tail: a fresh id would otherwise drain the whole
    # SHARED broadcast backlog -- the drill runner would echo-answer days-old broadcast
    # chatter at real agents. Drills speak over DIRECT messages only.
    b._write_cursor("0", b.tail()["bc"])
    return b


def _cleanup(*buses):
    for b in buses:
        try:
            b._client.delete(b._cursor_key(), f"{b.ns}:generation:{b.agent_id}",
                             f"{b.ns}:runner:{b.agent_id}", b._inbox_key(b.agent_id))
        except Exception:
            pass


def _run_runner(agent, killpoint=""):
    env = dict(os.environ, AKASHIC_DRILL_ECHO="1")
    env.pop("AKASHIC_KILLPOINT", None)
    if killpoint:
        env["AKASHIC_KILLPOINT"] = killpoint
    return subprocess.run(
        [sys.executable, RUNNER, "--agent", agent, "--once"],
        env=env, capture_output=True, text=True, timeout=60, cwd=REPO,
        encoding="utf-8", errors="replace")


def _reap_dead_lock(agent):
    """What the launcher's revive path does after a hard kill: the crashed runner's lock
    lingers (os._exit skips the finally-release -- crash-only, working as designed) and
    the successor refuses the seat until LOCK_TTL. clear_if_pid frees it ONLY when the
    holder pid is truly gone -- the drill kills its runner, so it always is."""
    from core.comm import runner_lock
    h = runner_lock.holder(agent)
    if h:
        runner_lock.clear_if_pid(agent, h.get("pid"))


def _echo_replies(sender):
    return [m for m in sender.inbox(limit=50, advance=False)
            if m.kind == "reply" and "[drill-echo]" in str(m.content)]


def test_w1_death_after_consume_loses_nothing():
    """THE incident window (2026-07-10 mail loss): die between detect and process.
    Before RB-26 the cursor had already moved -- the ask was gone. Now: cursor untouched,
    the successor redelivers, answers exactly once, then commits."""
    runner_bus, sender = _fresh("drill-w1"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w1 ping")
        assert mid
        # EXECUTION: armed run dies at the window
        p = _run_runner(runner_bus.agent_id, killpoint="post-consume-pre-process")
        assert p.returncode == 137, f"must die AT the window, got {p.returncode}: {p.stdout[-400:]}"
        assert runner_bus.cursor()["inbox"] == "0", \
            "commit-after-processing: death before handling leaves the cursor untouched"
        assert _echo_replies(sender) == [], "no reply was minted before death"
        # CHECK: unarmed successor redelivers and answers exactly once
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        assert p2.returncode == 0, p2.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, "the lost-mail disease is dead: exactly one answer"
        assert runner_bus.cursor()["inbox"] == mid, "handled -> committed"
        # METRICS/idempotence: a third tenure redelivers nothing, answers nothing
        _reap_dead_lock(runner_bus.agent_id)
        p3 = _run_runner(runner_bus.agent_id)
        assert p3.returncode == 0
        assert len(_echo_replies(sender)) == 1, "no duplicate on an idle tenure"
    finally:
        _cleanup(runner_bus, sender)


def test_w4_death_after_sentinel_never_double_replies():
    """Die between the reply_sent sentinel and the cursor commit: the message REDELIVERS
    (at-least-once) but the sentinel makes the answer effectively-once."""
    runner_bus, sender = _fresh("drill-w4"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w4 ping")
        p = _run_runner(runner_bus.agent_id, killpoint="post-sentinel-pre-advance")
        assert p.returncode == 137, p.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, "reply went out before death"
        assert runner_bus.cursor()["inbox"] == "0", "cursor never committed -- will redeliver"
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        assert p2.returncode == 0, p2.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, \
            "redelivery hit the sentinel: effectively-once, no duplicate reply"
        assert "reply already sent" in p2.stdout, "the skip is loud, not silent"
        assert runner_bus.cursor()["inbox"] == mid, "successor committed past the message"
    finally:
        _cleanup(runner_bus, sender)


def test_w3_duplicate_reply_is_the_accepted_tolerance():
    """Die between send and sentinel: the ONE window where a duplicate reply is possible
    and ACCEPTED (chat-grade cost; the alternative -- sentinel before send -- risks a
    dropped reply, which is worse). Pinned so the tolerance is a decision, not a surprise."""
    runner_bus, sender = _fresh("drill-w3"), _fresh("drill-snd")
    try:
        sender.send(runner_bus.agent_id, "request", "w3 ping")
        p = _run_runner(runner_bus.agent_id, killpoint="post-send-pre-sentinel")
        assert p.returncode == 137, p.stdout[-400:]
        assert len(_echo_replies(sender)) == 1
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        assert p2.returncode == 0
        assert len(_echo_replies(sender)) == 2, \
            "at-least-once: the duplicate is the named, accepted cost of this window"
    finally:
        _cleanup(runner_bus, sender)
