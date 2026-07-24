"""T086-S3 pins: stop-hook backstop dedup -- the nag never fires into an in-flight arming
attempt (S3a) or against a live twin's held seat (S3b); a tombstoned holder falls through.
Cites t086-seat-reconciliation-2026-07-16.md. Receipts: 2026-07-16 ~09:16 (nag mid-retry-loop)
and ~09:11 (nag would have demanded a watcher while the ghost held the seat).
Exercised through the REAL hook subprocess (the t086-s1 pattern)."""
import json
import os
import subprocess
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import runner_lock, wake_seat
from core.comm.bus import Bus

try:
    _ONLINE = bool(Bus("t086s3-probe").online)
except Exception:
    _ONLINE = False

pytestmark = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "agent", "harness", "hooks", "claude_stop.py")


def _run_hook(agent: str, session_id: str):
    env = {**os.environ, "AKASHIC_AGENT_ID": agent, "AKASHIC_DAEMON_WAKE": "0",
           "AKASHIC_STOP_PROMISE": "0"}
    payload = json.dumps({"session_id": session_id, "hook_event_name": "Stop"})
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                          text=True, timeout=60, cwd=REPO, env=env)


@pytest.fixture()
def agent():
    aid = f"t086s3-{uuid.uuid4().hex[:8]}"
    yield aid
    c = runner_lock._client()
    if c is not None:
        try:
            c.delete(f"bifrost:runner:{aid}")
            c.delete(f"bifrost:generation:{aid}")
        except Exception:
            pass


def _sid() -> str:
    return f"s3sid{uuid.uuid4().hex[:10]}"


def test_s3a_fresh_arming_marker_suppresses_nag(agent):
    sid = _sid()
    m = os.path.join(__import__("tempfile").gettempdir(), f"bifrost_wake_{agent}_{sid}.arming")
    open(m, "w").write(str(time.time()))
    try:
        r = _run_hook(agent, sid)
        assert '"decision": "block"' not in (r.stdout or "")
        assert "arming attempt in flight" in (r.stderr or "")
    finally:
        os.remove(m)


def test_s3b_live_twin_seat_suppresses_nag(agent):
    sid, twin = _sid(), _sid()
    ok, _, _ = runner_lock.claim_consumer(agent, f"session:{twin}")
    assert ok
    r = _run_hook(agent, sid)
    assert '"decision": "block"' not in (r.stdout or "")
    assert "held by live twin" in (r.stderr or "")


def test_s3b_tombstoned_twin_falls_through_to_nag(agent):
    sid, ghost = _sid(), _sid()
    ok, _, _ = runner_lock.claim_consumer(agent, f"session:{ghost}")
    assert ok
    assert wake_seat.write_tombstone(ghost)
    try:
        r = _run_hook(agent, sid)
        assert '"decision": "block"' in (r.stdout or ""), (r.stdout, r.stderr)
    finally:
        try:
            os.remove(wake_seat.tombstone_path(ghost))
        except Exception:
            pass
        c = runner_lock._client()
        if c is not None:
            c.delete(f"bifrost:session:ended:{ghost}")


def test_regression_no_marker_no_twin_still_nags(agent):
    r = _run_hook(agent, _sid())
    assert '"decision": "block"' in (r.stdout or ""), (r.stdout, r.stderr)
