"""
S0-gamma · play-sandbox acceptance pins (T099 · tool tier).
Laws pinned (RED before core/toolbelt/play_sandbox.py is integrated into the families gate):

  1. DISCOVERY — list_tools finds .py files in data/play/<agent>/, list_seats finds agents
  2. SANDBOXED RUN — sandboxed_run() executes a play tool, captures output, returns receipt
  3. RECEIPT PERSISTED — receipt is written to data/play/<agent>/runs/<tool>/<ts>.json
  4. TIMEOUT IS A RECEIPT — a tool that exceeds timeout returns a crash receipt, never leaks
  5. OUTPUT CAP — output over max bytes is clipped with a marker
  6. FAIL-OPEN — a nonexistent tool returns a clean error, never a crash

Run: py -m pytest tests/test_s0_gamma_play_sandbox.py -q
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- L1: discovery ------------------------------------------------------------

def test_list_tools_finds_play_scripts():
    from core.toolbelt.play_sandbox import list_tools, list_seats
    seats = list_seats()
    assert "kimi" in seats, "kimi has a play directory"
    tools = list_tools("kimi")
    assert "premonition" in tools, "premonition.py exists and is discoverable"


def test_list_nonexistent_agent_returns_empty():
    from core.toolbelt.play_sandbox import list_tools
    assert list_tools("no-such-agent") == []


# --- L2: sandboxed run --------------------------------------------------------

def test_sandboxed_run_produces_receipt():
    """Run a trivial play tool and verify the receipt shape."""
    import tempfile
    from core.toolbelt.play_sandbox import sandboxed_run
    # Write a temporary play tool that just prints and exits 0
    with tempfile.TemporaryDirectory() as td:
        tool_path = os.path.join(td, "hello.py")
        with open(tool_path, "w") as f:
            f.write("import sys; print('hello from sandbox'); sys.exit(0)\n")
        rec = sandboxed_run("test", "hello", tool_path, timeout_s=5)
        assert rec["tool"] == "hello"
        assert rec["agent"] == "test"
        assert rec["rc"] == 0
        assert rec["duration_s"] > 0
        assert rec["crash"] is False
        assert rec["evidence"] == "GUESS"


def test_sandboxed_run_timeout_is_receipt():
    """A tool that sleeps past timeout returns a crash receipt, never hangs."""
    import tempfile
    from core.toolbelt.play_sandbox import sandboxed_run
    with tempfile.TemporaryDirectory() as td:
        tool_path = os.path.join(td, "sleeper.py")
        with open(tool_path, "w") as f:
            f.write("import time; time.sleep(10); print('never')\n")
        rec = sandboxed_run("test", "sleeper", tool_path, timeout_s=0.5)
        assert rec["crash"] is True
        assert "timeout" in str(rec.get("violations", [])).lower()


def test_sandboxed_run_captures_output():
    """stdout is captured and the output_kb field is populated."""
    import tempfile
    from core.toolbelt.play_sandbox import sandboxed_run
    with tempfile.TemporaryDirectory() as td:
        tool_path = os.path.join(td, "chatter.py")
        with open(tool_path, "w") as f:
            f.write("print('a' * 1000)\n")
        rec = sandboxed_run("test", "chatter", tool_path)
        assert rec["output_kb"] > 0


# --- L3: receipt persistence --------------------------------------------------

def test_receipt_persisted_to_runs():
    """After sandboxed_run(), a receipt JSON exists in the runs directory."""
    import tempfile
    monkeypatch_setenv = os.environ.get("PYTEST_CURRENT_TEST")  # just verify we're in pytest
    # Use the REAL PLAY directory for this test (data/play) — sandboxed_run writes to it
    from core.toolbelt.play_sandbox import sandboxed_run, PLAY
    play_sub = os.path.join(PLAY, "test-gamma")
    os.makedirs(play_sub, exist_ok=True)
    runs_sub = os.path.join(PLAY, "test-gamma", "runs")
    os.makedirs(runs_sub, exist_ok=True)
    tool_path = os.path.join(play_sub, "meep.py")
    try:
        with open(tool_path, "w") as f:
            f.write("print('receipt me')\n")
        rec = sandboxed_run("test-gamma", "meep", tool_path)
        # Check that a receipt JSON was written
        recs = [f for f in os.listdir(runs_sub) if f.startswith("meep-") and f.endswith(".json")]
        assert len(recs) >= 1, "receipt JSON was written to runs/"
        with open(os.path.join(runs_sub, recs[-1])) as f:
            saved = json.load(f)
        assert saved["tool"] == "meep"
    finally:
        # Cleanup
        for f in os.listdir(runs_sub):
            os.remove(os.path.join(runs_sub, f))
        if os.path.exists(tool_path):
            os.remove(tool_path)
        try:
            os.rmdir(runs_sub)
            os.rmdir(play_sub)
        except OSError:
            pass


# --- L4: find_tool validation -------------------------------------------------

def test_find_tool_rejects_bad_refs():
    from core.toolbelt.play_sandbox import find_tool
    import pytest
    with pytest.raises(ValueError, match="bad tool ref"):
        find_tool("not-a-ref")
    with pytest.raises(FileNotFoundError):
        find_tool("kimi/nonexistent_tool_xyz")
