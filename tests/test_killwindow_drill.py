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


class ReferenceState:
    """FDB-style reference CHECK (L1 follow-up): an independent, zero-I/O encoding of the
    pipeline's crash semantics. The drill replays its op sequence against this model and
    compares the REAL terminal state -- catching off-by-one/wrong-stream/forgotten-state
    divergence that per-assert invariants miss. Deliberately tiny: it models exactly the
    single-inbox drill world (grows with L2, not before)."""

    def __init__(self):
        self.replies = {}      # msg_id -> reply count
        self.cursor = "0"
        self.pending = []      # uncommitted msg ids, oldest first
        self.sentinel = set()  # msg ids whose reply_sent sentinel was written

    def send(self, mid):
        self.pending.append(mid)

    def tenure(self, killpoint=None):
        """One --once run, transliterated: each killpoint is an early-return at its exact
        pipeline position. Redelivery falls out of `pending` naturally."""
        for mid in list(self.pending):
            if killpoint in ("post-consume-pre-process", "post-phase-flip-pre-send"):
                return                              # died before any outcome for this msg
            if mid not in self.sentinel:
                self.replies[mid] = self.replies.get(mid, 0) + 1   # answered (else: skip)
            if killpoint == "post-send-pre-sentinel":
                return                              # died with reply out, sentinel unwritten
            self.sentinel.add(mid)
            if killpoint == "post-sentinel-pre-advance":
                return                              # died before the cursor commit
            self.cursor = mid
            self.pending.remove(mid)
            if killpoint == "between-batch-messages":
                return                              # died before the NEXT message

    def check(self, runner_bus, sender, tags):
        """CHECK phase: real terminal state must equal the model's. `tags` maps
        msg_id -> a content marker unique to that message's echo reply."""
        real_cursor = runner_bus.cursor()["inbox"]
        assert real_cursor == self.cursor, \
            f"ReferenceState divergence: cursor real={real_cursor} model={self.cursor}"
        real = {}
        for m in _echo_replies(sender):
            for mid, tag in tags.items():
                if tag in str(m.content):
                    real[mid] = real.get(mid, 0) + 1
        model = {k: v for k, v in self.replies.items() if v}
        assert real == model, \
            f"ReferenceState divergence: replies real={real} model={model}"


def test_w1_death_after_consume_loses_nothing():
    """THE incident window (2026-07-10 mail loss): die between detect and process.
    Before RB-26 the cursor had already moved -- the ask was gone. Now: cursor untouched,
    the successor redelivers, answers exactly once, then commits."""
    runner_bus, sender = _fresh("drill-w1"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w1 ping")
        assert mid
        ref = ReferenceState(); ref.send(mid)
        # EXECUTION: armed run dies at the window
        p = _run_runner(runner_bus.agent_id, killpoint="post-consume-pre-process")
        ref.tenure("post-consume-pre-process")
        assert p.returncode == 137, f"must die AT the window, got {p.returncode}: {p.stdout[-400:]}"
        assert runner_bus.cursor()["inbox"] == "0", \
            "commit-after-processing: death before handling leaves the cursor untouched"
        assert _echo_replies(sender) == [], "no reply was minted before death"
        # CHECK: unarmed successor redelivers and answers exactly once
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p2.returncode == 0, p2.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, "the lost-mail disease is dead: exactly one answer"
        assert runner_bus.cursor()["inbox"] == mid, "handled -> committed"
        # METRICS/idempotence: a third tenure redelivers nothing, answers nothing
        _reap_dead_lock(runner_bus.agent_id)
        p3 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p3.returncode == 0
        assert len(_echo_replies(sender)) == 1, "no duplicate on an idle tenure"
        ref.check(runner_bus, sender, {mid: "w1 ping"})
    finally:
        _cleanup(runner_bus, sender)


def test_w4_death_after_sentinel_never_double_replies():
    """Die between the reply_sent sentinel and the cursor commit: the message REDELIVERS
    (at-least-once) but the sentinel makes the answer effectively-once."""
    runner_bus, sender = _fresh("drill-w4"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w4 ping")
        ref = ReferenceState(); ref.send(mid)
        p = _run_runner(runner_bus.agent_id, killpoint="post-sentinel-pre-advance")
        ref.tenure("post-sentinel-pre-advance")
        assert p.returncode == 137, p.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, "reply went out before death"
        assert runner_bus.cursor()["inbox"] == "0", "cursor never committed -- will redeliver"
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p2.returncode == 0, p2.stdout[-400:]
        assert len(_echo_replies(sender)) == 1, \
            "redelivery hit the sentinel: effectively-once, no duplicate reply"
        assert "reply already sent" in p2.stdout, "the skip is loud, not silent"
        assert runner_bus.cursor()["inbox"] == mid, "successor committed past the message"
        ref.check(runner_bus, sender, {mid: "w4 ping"})
    finally:
        _cleanup(runner_bus, sender)


def test_w3_duplicate_reply_is_the_accepted_tolerance():
    """Die between send and sentinel: the ONE window where a duplicate reply is possible
    and ACCEPTED (chat-grade cost; the alternative -- sentinel before send -- risks a
    dropped reply, which is worse). Pinned so the tolerance is a decision, not a surprise."""
    runner_bus, sender = _fresh("drill-w3"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w3 ping")
        ref = ReferenceState(); ref.send(mid)
        p = _run_runner(runner_bus.agent_id, killpoint="post-send-pre-sentinel")
        ref.tenure("post-send-pre-sentinel")
        assert p.returncode == 137, p.stdout[-400:]
        assert len(_echo_replies(sender)) == 1
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p2.returncode == 0
        assert len(_echo_replies(sender)) == 2, \
            "at-least-once: the duplicate is the named, accepted cost of this window"
        ref.check(runner_bus, sender, {mid: "w3 ping"})
    finally:
        _cleanup(runner_bus, sender)


def test_w2_death_before_send_answers_once_on_redelivery():
    """Die after the worklive phase flip but before the model call/send: no outcome
    exists, the cursor is untouched, and the successor answers exactly once."""
    runner_bus, sender = _fresh("drill-w2"), _fresh("drill-snd")
    try:
        mid = sender.send(runner_bus.agent_id, "request", "w2 ping")
        ref = ReferenceState(); ref.send(mid)
        p = _run_runner(runner_bus.agent_id, killpoint="post-phase-flip-pre-send")
        ref.tenure("post-phase-flip-pre-send")
        assert p.returncode == 137, p.stdout[-400:]
        assert _echo_replies(sender) == [] and runner_bus.cursor()["inbox"] == "0"
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p2.returncode == 0, p2.stdout[-400:]
        assert len(_echo_replies(sender)) == 1
        ref.check(runner_bus, sender, {mid: "w2 ping"})
    finally:
        _cleanup(runner_bus, sender)


def test_w5_mid_batch_death_loses_only_the_unhandled_tail():
    """TWO messages, die after message 1 commits (between-batch-messages): message 1 is
    settled (committed, answered once), message 2 redelivers to the successor -- the
    mid-batch semantics the per-message commit exists for (his A3 mode, drilled)."""
    runner_bus, sender = _fresh("drill-w5"), _fresh("drill-snd")
    try:
        m1 = sender.send(runner_bus.agent_id, "request", "w5 first")
        m2 = sender.send(runner_bus.agent_id, "request", "w5 second")
        ref = ReferenceState(); ref.send(m1); ref.send(m2)
        p = _run_runner(runner_bus.agent_id, killpoint="between-batch-messages")
        ref.tenure("between-batch-messages")
        assert p.returncode == 137, p.stdout[-400:]
        assert runner_bus.cursor()["inbox"] == m1, "message 1 committed before death"
        assert len(_echo_replies(sender)) == 1, "message 1 answered before death"
        _reap_dead_lock(runner_bus.agent_id)
        p2 = _run_runner(runner_bus.agent_id)
        ref.tenure()
        assert p2.returncode == 0, p2.stdout[-400:]
        replies = _echo_replies(sender)
        assert len(replies) == 2, "message 2 redelivered and answered; message 1 NOT re-answered"
        assert runner_bus.cursor()["inbox"] == m2
        ref.check(runner_bus, sender, {m1: "w5 first", m2: "w5 second"})
    finally:
        _cleanup(runner_bus, sender)


def test_timeout_multiplier_shrinks_the_lock_ttl():
    """BUGGIFY-style knob shrinking (FDB): with AKASHIC_TIMEOUT_MULTIPLIER the drill can
    reach timeout paths in seconds. Pins the seam end-to-end in a child process."""
    out = subprocess.run(
        [sys.executable, "-c",
         "from core.comm import runner_lock, liveness; import scripts.bifrost_runner_deepseek as r; "
         "print(runner_lock.LOCK_TTL, liveness.WORKLIVE_TTL, r.REPLY_TIMEOUT_SEC)"],
        env=dict(os.environ, AKASHIC_TIMEOUT_MULTIPLIER="0.05"),
        capture_output=True, text=True, timeout=60, cwd=REPO,
        encoding="utf-8", errors="replace")
    assert out.returncode == 0, out.stderr[-400:]
    ttl, wl, reply = out.stdout.strip().split()[-3:]
    assert (ttl, wl, reply) == ("1", "2", "30"), \
        f"20s lock -> 1s, 45s worklive -> 2s, 600s reply guard -> 30s; got {ttl},{wl},{reply}"
