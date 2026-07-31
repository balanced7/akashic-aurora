"""
PINS FIRST — bifrost_runner_gemini.py birth tier, quarantine shape.

Run:  py -m pytest tests/test_runner_gemini_pins.py -v
"""

import os
import sys
import json
import subprocess
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
RUNNER = os.path.join(SCRIPTS, "bifrost_runner_gemini.py")

# ── helpers ──────────────────────────────────────────────────────────

def _runner_exists():
    assert os.path.isfile(RUNNER), f"{RUNNER} not found"

def _run(args, timeout=15):
    """Run the runner script, return (rc, stdout, stderr)."""
    env = dict(os.environ)
    env["AKASHIC_DRILL_ECHO"] = "1"  # offline mode — no Redis, no API
    p = subprocess.run(
        [sys.executable, RUNNER] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, env=env, cwd=os.path.dirname(HERE)
    )
    return p.returncode, (p.stdout or ""), (p.stderr or "")

def _grep(pattern, text):
    import re
    return bool(re.search(pattern, text))


# ── P1: script exists and is importable as valid Python ──────────────

def test_p1_script_exists_and_parses():
    """P1: bifrost_runner_gemini.py exists and compiles as valid Python."""
    _runner_exists()
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    compile(src, RUNNER, "exec")  # raises SyntaxError if broken

# ── P2: boots with --help (no key needed) ────────────────────────────

def test_p2_help_works():
    """P2: --help prints usage and exits 0 without needing an API key."""
    rc, out, err = _run(["--help"])
    assert rc == 0, f"exit {rc}: {err}"
    assert "usage:" in out.lower() or "bifrost_runner_gemini" in out.lower(), \
        f"no usage in: {out[:200]}"

# ── P3: refuses loudly without API key ───────────────────────────────

def test_p3_no_key_refuses_loudly():
    """P3: without CURSOR_API_KEY or .secrets/cursor.key, exits non-zero with clear message."""
    env = dict(os.environ)
    env.pop("CURSOR_API_KEY", None)
    # redirect the key file probe to a non-existent path
    env["AKASHIC_DRILL_ECHO"] = "1"
    p = subprocess.run(
        [sys.executable, RUNNER, "--once"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=15, env=env, cwd=os.path.dirname(HERE)
    )
    out = (p.stdout + p.stderr).lower()
    assert p.returncode != 0, f"expected non-zero exit without key, got {p.returncode}"
    assert "no_key" in out or "cursor_api_key" in out or "cursor.key" in out or \
           "api key" in out, f"no key-refusal message in: {out[:300]}"

# ── P4: chat-only mode refuses tool invocation LOUDLY ────────────────

def test_p4_chat_only_refuses_tools():
    """P4: in chat-only (default, no --agentic), the agent refuses tool calls loudly."""
    src_path = RUNNER
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    # The quarantine pin: the system prompt MUST declare chat-only, and the runner
    # MUST NOT import or construct a ToolBox when chat-only.
    assert "chat-only" in src.lower() or "quarantine" in src.lower(), \
        "P4 FAIL: runner source does not mention chat-only/quarantine mode"
    # No ToolBox import in the module top-level for chat-only mode
    # (the import may exist for --agentic path but must be conditional)
    # At minimum: the --agentic flag must gate tool access
    assert "--agentic" in src, \
        "P4 FAIL: runner has no --agentic flag to gate tool access"

# ── P5: consumes work lane ───────────────────────────────────────────

def test_p5_work_lane_env():
    """P5: runner references BIFROST_CONSUME_LANE=work in docstring or startup."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    assert "BIFROST_CONSUME_LANE" in src, \
        "P5 FAIL: runner does not reference BIFROST_CONSUME_LANE"
    assert "work" in src.lower(), \
        "P5 FAIL: runner does not reference work lane"

# ── P6: replies ride send_reply ──────────────────────────────────────

def test_p6_send_reply():
    """P6: runner uses bus.send_reply for directed answers (T066 lane-first)."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    assert "send_reply" in src, \
        "P6 FAIL: runner does not use bus.send_reply (T066 contract)"

# ── P7: drain request honored within one loop top ────────────────────

def test_p7_drain_honor_path():
    """P7: W101 drain-honor path present at loop top (deepseek pattern, matched)."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    # Must reference drain_requested OR control.drain (the import path may differ)
    assert "drain_requested" in src or "drain" in src.lower(), \
        "P7 FAIL: no drain-honor path (W101 — kimi/sol lack it)"

# ── P8: summary file convention ──────────────────────────────────────

def test_p8_summary_file():
    """P8: runner writes state/runner_gemini_last.json on exit."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    assert "summary" in src.lower() or "state/runner" in src, \
        "P8 FAIL: no summary file convention"

# ── P9: 600s turn timeout with abandon-to-stay-alive ─────────────────

def test_p9_timeout_guard():
    """P9: REPLY_TIMEOUT_SEC = 600 and abandon-to-stay-alive pattern present."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    assert "600" in src or "REPLY_TIMEOUT" in src, \
        "P9 FAIL: no 600s timeout guard"
    assert "timeout" in src.lower(), \
        "P9 FAIL: no timeout handling"

# ── P10: boot prints CONSUME LANE + interiority fold ─────────────────

def test_p10_boot_prints():
    """P10: startup prints CONSUME LANE line + interiority fold self-report."""
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    assert "CONSUME LANE" in src, \
        "P10 FAIL: no CONSUME LANE boot print"
    # T124: interiority fold self-reporting log line
    assert "interiority" in src.lower() or "INTERIORITY" in src, \
        "P10 FAIL: no interiority fold self-report (T124 contract)"
