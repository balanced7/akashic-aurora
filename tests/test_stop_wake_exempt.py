"""Pin: AKASHIC_STOP_WAKE=0 (ephemeral-seat exemption) waives the wake ritual -- the stop hook
exits 0 with NO block payload, and says so on stderr. Guards the kimi headless-walk exit path
(2026-07-18: four sessions paid a multi-minute deny/retry exit tax before this exemption).
Also pins the default: unset env keeps the ritual armed (the block machinery still runs)."""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "agent", "harness", "hooks", "claude_stop.py")
PAYLOAD = json.dumps({"session_id": "pin-ephemeral-0000", "transcript_path": "", "cwd": os.getcwd()})


def _run(extra_env):
    env = {**os.environ, **extra_env}
    return subprocess.run([sys.executable, HOOK], input=PAYLOAD, env=env,
                          capture_output=True, text=True, timeout=30)


def test_exempt_seat_never_blocks():
    r = _run({"AKASHIC_STOP_WAKE": "0", "AKASHIC_AGENT_ID": "pin-agent"})
    assert r.returncode == 0, f"exempt seat must exit 0, got {r.returncode}: {r.stderr[:300]}"
    assert "waived" in r.stderr, f"waiver line missing on stderr: {r.stderr[:300]}"
    assert not r.stdout.strip(), f"exempt seat must emit no block payload, got: {r.stdout[:300]}"


def test_default_keeps_ritual():
    env = {"AKASHIC_AGENT_ID": "pin-agent"}
    env.update({k: v for k, v in os.environ.items() if k != "AKASHIC_STOP_WAKE"})
    r = subprocess.run([sys.executable, HOOK], input=PAYLOAD, env=env,
                       capture_output=True, text=True, timeout=30)
    assert "waived" not in r.stderr, "unset env must NOT waive the ritual"
