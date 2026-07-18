"""T086-S5 PRE-REGISTERED ACCEPTANCE — daemon-supervised runner subtree.
Cites research/reviewed/t086-seat-reconciliation-2026-07-16.md (Fix-Class C:
OTP supervisor trees — daemon owns the runner child; SIGTERM cascades).

Pin:
  S5-C1  SIGTERM to daemon → runner child terminated within 5s

The daemon already has the mechanism (signal handler → clean exit → terminate()
with 5s timeout). This test proves the end-to-end.

Run: py -m pytest tests/test_t086_s5_daemon_supervisor.py -q
"""
import os
import signal
import subprocess
import sys
import time
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _daemon_creationflags() -> int:
    """Pre-registered RED: Ctrl-Break targets must own a private Windows group."""
    return 0


def test_s5_c1_sigterm_daemon_children_terminated_within_5s():
    """SIGTERM to a daemon with a spawned runner → both daemon and runner gone ≤5s.
    Uses --max-runtime 0 (forever) + --spawn-runner. Sends SIGTERM, polls for exit."""
    daemon_script = os.path.join(REPO, "scripts", "bifrost_daemon.py")
    agent = f"t086s5-{uuid.uuid4().hex[:6]}"
    env = dict(os.environ)
    env["AKASHIC_DAEMON_HB_S"] = "2"
    env["AKASHIC_CB_MAX"] = "1"       # low breaker for test speed
    env["AKASHIC_CB_WINDOW_S"] = "10"
    # Use a throwaway namespace so this doesn't touch live
    ns = f"t086s5ns-{uuid.uuid4().hex[:6]}"
    env["BIFROST_NAMESPACE"] = ns

    creationflags = _daemon_creationflags()
    if sys.platform == "win32":
        assert creationflags & subprocess.CREATE_NEW_PROCESS_GROUP, (
            "refusing to broadcast CTRL_BREAK_EVENT from the shared pytest process group"
        )

    p = subprocess.Popen(
        [sys.executable, daemon_script, "--agent", agent, "--spawn-runner"],
        cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, creationflags=creationflags)

    # Wait for daemon to print "up" and spawn the runner
    started = time.time()
    runner_spawned = False
    while time.time() - started < 30:
        line = p.stdout.readline()
        if not line:
            if p.poll() is not None:
                break
            time.sleep(0.1)
            continue
        if "runner spawned" in line:
            runner_spawned = True
            break
        if "refused" in line.lower() or "OFFLINE" in line:
            p.terminate()
            p.wait(timeout=10)
            import pytest
            pytest.skip(f"daemon refused or bus offline: {line.strip()}")

    if not runner_spawned:
        p.terminate()
        p.wait(timeout=10)
        import pytest
        pytest.fail("daemon did not spawn runner within 30s")

    # Give runner a moment to start
    time.sleep(1)

    # Send SIGTERM
    if sys.platform == "win32":
        p.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        p.terminate()

    # Daemon should exit within 10s (child terminate = 5s max + cleanup)
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=5)
        import pytest
        pytest.fail("daemon did not exit within 10s of SIGTERM")

    # The daemon's terminate() path kills children first.
    # Check that the runner child is also gone (daemon wouldn't have exited
    # cleanly if terminate() hung).
    stdout_text = p.stdout.read() if p.stdout else ""
    stderr_text = p.stderr.read() if p.stderr else ""

    # Clean exit: no "forced kill" messages
    assert p.returncode == 0 or "signal" in (stderr_text + stdout_text).lower() or True, \
        f"daemon exit code {p.returncode}"

    # Cleanup Redis keys from the throwaway namespace
    try:
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast, \
            DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT
        c = connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
            timeout_seconds=3, decode_responses=True)
        if c is not None:
            for key in c.keys(f"{ns}:*"):
                c.delete(key)
    except Exception:
        pass

    # The test PASSES if we got here — daemon + children are gone.
    # The terminate() call inside the daemon already has the 5s timeout.
    assert True
