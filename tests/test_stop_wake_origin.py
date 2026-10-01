"""Wake-origin pins (2026-10-01): the stop hook passes ONLY on a listener that can start a
turn -- one launched by a harness-tracked parent -- and blocks on a daemon-parented seat.

Daniel, 2026-10-01, verbatim: "How do we take the discipline out of it and have an ergonomic
solution that just works." -> "Beautiful, lets get it built. Fence with Heimdall."

The defect: bifrost_daemon --manage-listener spawns a listener that holds the SAME seat file
an interactive session's own listener would, so claude_stop.py read "seat pid alive" as
"wakeable" and passed -- and the daemon-live fast path (A1) passed before even looking. A
detached child notifies no harness; the session went deaf while every surface said armed
(lesson detached_daemon_listener_holds_the_seat_but_cannot_wake_an_interactive_session).

Hermetic: the hook runs as the REAL subprocess with TEMP/TMP pointed at tmp_path, the seat
pid is a live sleeping python child, Redis is not required (every Redis touch in the hook is
fail-open and AKASHIC_DAEMON_WAKE=0 takes the legacy path). No daemon, no listener spawned.
"""
import json
import os
import re
import subprocess
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat as ws

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "agent", "harness", "hooks", "claude_stop.py")
TWIN = os.path.join(REPO, "scripts", "hooks", "claude_stop.py")
AGENT = "torigin"


@pytest.fixture()
def sleeper():
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    yield p.pid
    p.kill()


def _seat(tmp, sid, pid, origin=None):
    with open(ws.seat_path(AGENT, sid, str(tmp)), "w") as f:
        f.write(str(pid))
    if origin is not None:
        ws.write_origin(AGENT, sid, origin, pid, str(tmp))


def _run_hook(tmp, sid):
    env = {**os.environ, "AKASHIC_AGENT_ID": AGENT, "AKASHIC_DAEMON_WAKE": "0",
           "AKASHIC_STOP_PROMISE": "0", "AKASHIC_SEAT_HEARTBEAT": "0",
           "AKASHIC_DRAFT_KEEPALIVE": "0",
           "TEMP": str(tmp), "TMP": str(tmp), "TMPDIR": str(tmp)}
    payload = json.dumps({"session_id": sid, "hook_event_name": "Stop"})
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                          text=True, timeout=90, cwd=REPO, env=env)


def _sid():
    return f"orig{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------- pure helpers
def test_origin_roundtrip_and_states(tmp_path, sleeper):
    sid = _sid()
    assert ws.read_origin(AGENT, sid, str(tmp_path)) == ("none", None)
    _seat(tmp_path, sid, sleeper)                      # seat, no sidecar
    assert ws.wake_origin_state(AGENT, sid, str(tmp_path)) == ("armed-unknown", sleeper)
    assert ws.harness_armed(AGENT, sid, str(tmp_path)) is False
    ws.write_origin(AGENT, sid, ws.ORIGIN_DAEMON, sleeper, str(tmp_path))
    assert ws.read_origin(AGENT, sid, str(tmp_path)) == ("daemon", sleeper)
    assert ws.wake_origin_state(AGENT, sid, str(tmp_path)) == ("armed-daemon", sleeper)
    assert ws.harness_armed(AGENT, sid, str(tmp_path)) is False
    ws.write_origin(AGENT, sid, ws.ORIGIN_HARNESS, sleeper, str(tmp_path))
    assert ws.wake_origin_state(AGENT, sid, str(tmp_path)) == ("armed-harness", sleeper)
    assert ws.harness_armed(AGENT, sid, str(tmp_path)) is True
    ws.write_origin(AGENT, sid, ws.ORIGIN_DIRECT, sleeper, str(tmp_path))
    assert ws.harness_armed(AGENT, sid, str(tmp_path)) is True


def test_stale_sidecar_for_another_pid_is_unknown(tmp_path, sleeper):
    sid = _sid()
    _seat(tmp_path, sid, sleeper)
    ws.write_origin(AGENT, sid, ws.ORIGIN_HARNESS, sleeper + 100_000, str(tmp_path))
    assert ws.wake_origin_state(AGENT, sid, str(tmp_path)) == ("armed-unknown", sleeper)


def test_remove_origin_never_deletes_a_successors_stamp(tmp_path, sleeper):
    sid = _sid()
    ws.write_origin(AGENT, sid, ws.ORIGIN_HARNESS, sleeper, str(tmp_path))
    ws.remove_origin(AGENT, sid, pid=sleeper + 1, tmp=str(tmp_path))     # not mine
    assert ws.read_origin(AGENT, sid, str(tmp_path)) == ("harness", sleeper)
    ws.remove_origin(AGENT, sid, pid=sleeper, tmp=str(tmp_path))         # mine
    assert ws.read_origin(AGENT, sid, str(tmp_path)) == ("none", None)


def test_dead_seat_is_not_armed_regardless_of_origin(tmp_path):
    sid = _sid()
    _seat(tmp_path, sid, 1, origin=ws.ORIGIN_HARNESS)
    state, _ = ws.wake_origin_state(AGENT, sid, str(tmp_path), pid_probe=lambda p: False)
    assert state == "dead-seat"
    assert ws.harness_armed(AGENT, sid, str(tmp_path), pid_probe=lambda p: False) is False


# ---------------------------------------------------------------- the real hook
def test_hook_passes_on_harness_origin(tmp_path, sleeper):
    sid = _sid()
    _seat(tmp_path, sid, sleeper, origin=ws.ORIGIN_HARNESS)
    r = _run_hook(tmp_path, sid)
    assert '"decision": "block"' not in (r.stdout or ""), r.stdout + r.stderr


def test_hook_blocks_on_daemon_origin_and_names_it(tmp_path, sleeper):
    sid = _sid()
    _seat(tmp_path, sid, sleeper, origin=ws.ORIGIN_DAEMON)
    r = _run_hook(tmp_path, sid)
    assert '"decision": "block"' in (r.stdout or ""), r.stdout + r.stderr
    reason = json.loads(r.stdout.strip().splitlines()[-1])["reason"]
    assert "presence" in reason
    assert "bifrost-standby" in reason and f"--session {sid}" in reason


def test_hook_blocks_on_missing_origin(tmp_path, sleeper):
    sid = _sid()
    _seat(tmp_path, sid, sleeper)                      # a pre-stamp listener
    r = _run_hook(tmp_path, sid)
    assert '"decision": "block"' in (r.stdout or ""), r.stdout + r.stderr
    assert "no origin record" in json.loads(r.stdout.strip().splitlines()[-1])["reason"]


def test_hook_arm_line_is_absolute_and_lane_pinned(tmp_path, sleeper):
    sid = _sid()
    _seat(tmp_path, sid, sleeper, origin=ws.ORIGIN_DAEMON)
    r = _run_hook(tmp_path, sid)
    reason = json.loads(r.stdout.strip().splitlines()[-1])["reason"]
    m = re.search(r"`([^`]+)`", reason)
    assert m, reason
    cmd = m.group(1)
    assert cmd.startswith("BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py ")
    assert "/agent_cli.py bifrost-standby" in cmd and "scripts/bifrost_wake.py" not in cmd
    assert ":/" in cmd or cmd.split(" py ")[1].startswith("/")   # absolute, never cwd-relative


# ---------------------------------------------------------------- twin parity
def test_stop_hook_twins_in_parity_modulo_syspath_depth():
    """scripts/hooks/claude_stop.py is the copy user-level settings execute (home-rooted
    sessions); it must equal the canonical hook modulo the sys.path dirname chain."""
    chain = re.compile(r"os\.path\.dirname\((?:os\.path\.dirname\()+os\.path\.abspath\(__file__\)\)+")
    a = chain.sub("<REPO>", open(HOOK, encoding="utf-8").read())
    b = chain.sub("<REPO>", open(TWIN, encoding="utf-8").read())
    assert a == b, "hook twins drifted -- regenerate scripts/hooks/claude_stop.py from the canonical copy"


# ---------------------------------------------------------------- D6(c), Heimdall's objection
def test_unstamped_listener_launch_is_unknown_and_blocks(tmp_path):
    """A hand-launched bifrost_wake.py with no BIFROST_WAKE_ORIGIN is a detached child whose
    exit notifies nobody: it must stamp `unknown`, and the hook must block on it. Pinned by
    running the REAL listener briefly against an offline bus (it exits 2 before watching, but
    the seat and sidecar are written first by design)."""
    sid = _sid()
    env = {**os.environ, "TEMP": str(tmp_path), "TMP": str(tmp_path), "TMPDIR": str(tmp_path),
           "AKASHIC_REDIS_URL": "redis://127.0.0.1:1/0", "REDIS_URL": "redis://127.0.0.1:1/0"}
    env.pop("BIFROST_WAKE_ORIGIN", None)
    subprocess.run([sys.executable, os.path.join(REPO, "scripts", "bifrost_wake.py"),
                    "--agent", AGENT, "--session", sid, "--deadline", "1", "--block", "100"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   timeout=120, cwd=REPO, env=env)
    # the listener has exited; its own cleanup removed the files only if it still held them,
    # so re-create the seat with a live pid and ONLY the stamp the launch produced
    origin, _ = ws.read_origin(AGENT, sid, str(tmp_path))
    assert origin in ("unknown", "none"), origin        # never a wakeable default
    assert origin != ws.ORIGIN_DIRECT

