"""Contract tests for the Claude Code PostToolUse hook (scripts/hooks/claude_posttooluse.py).

The fixtures in tests/fixtures/claude_payloads/ are LIVE CAPTURES (2026-07-01, Claude Code on
Windows) -- the ground truth this hook's assumptions are pinned to. Verified live and encoded here:

  1. PostToolUse fires ONLY for successful tool calls (failures produce NO event), and success
     payloads carry NO error/exit markers -- so _is_success must call every real payload a success.
  2. The FAIL half of the FAIL->SUCCESS flip is therefore SYNTHESIZED from the session transcript
     (tool_result blocks with is_error=true, paired to tool_use blocks by tool_use_id).
  3. Each transcript failure is processed exactly once (per-session watermark by tool_use_id).
  4. PostToolUseFailure (the complementary fast path) records a FAIL immediately + watermarks it.

If the harness changes shape, re-capture (the hook auto-captures to %TEMP%/akashic_recall/payloads/
-- kill switch AKASHIC_PAYLOAD_CAPTURE=0), diff against these fixtures, and update BOTH.
"""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hooks import claude_posttooluse as hook
from core.recall.at_action import normalize_target

_FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "claude_payloads")


def _load(name):
    with open(os.path.join(_FIX, name), encoding="utf-8") as f:
        return json.load(f)


def _transcript_path():
    return os.path.join(_FIX, "transcript_fail_then_success.jsonl")


# --- 1. success payloads: every real captured payload must resolve success=True -------------------

@pytest.mark.parametrize("name", ["posttooluse_bash_success.json",
                                  "posttooluse_edit_success.json",
                                  "posttooluse_write_success.json"])
def test_live_success_payloads_are_success(name):
    assert hook._is_success(_load(name)) is True


def test_bash_success_payload_has_no_error_markers():
    """Pin the observed truth: no is_error / error / success / exit-code family fields exist. If
    this ever FAILS, the harness added outcome markers -- revisit _is_success (it could get direct
    signal) and the transcript synthesis (maybe no longer needed)."""
    tr = _load("posttooluse_bash_success.json")["tool_response"]
    for marker in ("is_error", "error", "success", "exit_code", "exitCode", "returncode", "code"):
        assert marker not in tr


def test_interrupted_is_not_success():
    data = _load("posttooluse_bash_success.json")
    data["tool_response"]["interrupted"] = True
    assert hook._is_success(data) is False


# --- 2. transcript synthesis: find the newest failure for a target --------------------------------

def test_latest_failure_id_bash_target_newest_wins():
    tgt = normalize_target(None, "cd E:/AI-Setup && py probe_thing.py --flag")
    assert hook._latest_failure_id(_transcript_path(), tgt) == "toolu_fail_bash_2"


def test_latest_failure_id_edit_target():
    tgt = normalize_target("E:\\AI-Setup\\.t1_scratch.txt", None)
    assert hook._latest_failure_id(_transcript_path(), tgt) == "toolu_fail_edit_1"


def test_latest_failure_id_success_only_target_is_none():
    tgt = normalize_target(None, "cd E:/AI-Setup && echo fine")
    assert hook._latest_failure_id(_transcript_path(), tgt) is None


def test_latest_failure_id_unknown_target_and_bad_path():
    assert hook._latest_failure_id(_transcript_path(), "c:no such command") is None
    assert hook._latest_failure_id(os.path.join(_FIX, "missing.jsonl"), "c:x") is None
    assert hook._latest_failure_id("", "c:x") is None


# --- 3. watermark: a failure is processed exactly once ---------------------------------------------

def test_failure_watermark_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "_TXW_DIR", str(tmp_path))
    assert hook._failure_processed("sess-1", "c:x", "toolu_a") is False
    hook._mark_failure_processed("sess-1", "c:x", "toolu_a")
    assert hook._failure_processed("sess-1", "c:x", "toolu_a") is True
    # a NEWER failure id for the same target is unprocessed (the watermark tracks the latest only)
    assert hook._failure_processed("sess-1", "c:x", "toolu_b") is False
    # other targets/sessions unaffected
    assert hook._failure_processed("sess-1", "c:y", "toolu_a") is False
    assert hook._failure_processed("sess-2", "c:x", "toolu_a") is False


# --- 4. end-to-end through main(): the flip fires from a real-shaped payload ----------------------

def _run_main(monkeypatch, payload, calls, tmp_txw):
    monkeypatch.setattr(hook, "_TXW_DIR", str(tmp_txw))
    monkeypatch.setattr(hook, "_CAP_DIR", str(tmp_txw / "cap"))
    import core.recall.at_action as aa
    monkeypatch.setattr(aa, "resolve_action_outcome",
                        lambda sid, tgt, ok, **kw: (calls.append((sid, tgt, ok)) or
                                                    {"flipped": False, "credited": 0, "sources": []}))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert hook.main() == 0


def _bash_success_payload_for(command):
    data = _load("posttooluse_bash_success.json")
    data["tool_input"]["command"] = command
    data["transcript_path"] = _transcript_path()
    data["session_id"] = "contract-e2e"
    return data


def test_main_backfills_fail_then_resolves_success_once(tmp_path, monkeypatch):
    cmd = "cd E:/AI-Setup && py probe_thing.py --flag"   # the fixture's failed-then-retried target
    tgt = normalize_target(None, cmd)
    calls = []
    _run_main(monkeypatch, _bash_success_payload_for(cmd), calls, tmp_path)
    assert calls == [("contract-e2e", tgt, False), ("contract-e2e", tgt, True)], \
        "first success after a transcript failure must backfill FAIL then resolve SUCCESS"
    # same event again: the failure is watermarked -> no second backfill (never farm one failure)
    calls2 = []
    _run_main(monkeypatch, _bash_success_payload_for(cmd), calls2, tmp_path)
    assert calls2 == [("contract-e2e", tgt, True)]


def test_main_first_try_success_no_backfill(tmp_path, monkeypatch):
    cmd = "cd E:/AI-Setup && echo fine"                  # succeeded in the transcript, never failed
    tgt = normalize_target(None, cmd)
    calls = []
    _run_main(monkeypatch, _bash_success_payload_for(cmd), calls, tmp_path)
    assert calls == [("contract-e2e", tgt, True)]


def test_main_posttoolusefailure_records_fail_and_watermarks(tmp_path, monkeypatch):
    cmd = "cd E:/AI-Setup && py probe_thing.py --flag"
    tgt = normalize_target(None, cmd)
    data = _bash_success_payload_for(cmd)
    data["hook_event_name"] = "PostToolUseFailure"
    data["tool_use_id"] = "toolu_fail_bash_2"            # matches the transcript's newest failure
    calls = []
    _run_main(monkeypatch, data, calls, tmp_path)
    assert calls == [("contract-e2e", tgt, False)], "direct failure path records FAIL immediately"
    # the follow-up success must NOT double-backfill: the fast path already watermarked this failure
    calls2 = []
    _run_main(monkeypatch, _bash_success_payload_for(cmd), calls2, tmp_path)
    assert calls2 == [("contract-e2e", tgt, True)]


def test_main_out_of_scope_is_silent(tmp_path, monkeypatch):
    data = _load("posttooluse_bash_success.json")
    data["tool_input"]["command"] = "echo unrelated"
    data["cwd"] = "C:\\Somewhere\\Else"
    calls = []
    _run_main(monkeypatch, data, calls, tmp_path)
    assert calls == []
