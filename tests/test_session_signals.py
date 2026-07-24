"""RENEW slice A'' -- session-signal persistence: fold math (core/renew/session_signals.py) and
the SessionEnd hook's transcript fold -> durable `session_signals` event (claude_sessionend.py).

Contract under test (see docs/library/report/20260707_renew-strand-a-cheap-deterministic-conte_6eba11.md):
  1. The fold is deterministic + total: Strand A's revised signal catalog, churn-over-PROGRESS
     family included, reread recorded-but-demoted; bad input degrades, never raises.
  2. The hook parses the SAME live-captured transcript shape the PostToolUse hook pins
     (tests/fixtures/claude_payloads/), joins targets via the SAME normalize_target, and emits
     exactly ONE event per session -- re-emitting ONLY when a resumed session grew.
  3. Emission is SessionEnd-only (PreCompact partials would double-count), scope-guarded,
     kill-switchable -- and always fail-soft.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import normalize_target
from core.renew.session_signals import fold_signals
from agent.harness.hooks import claude_sessionend as hook

_FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "claude_payloads")
_TRANSCRIPT = os.path.join(_FIX, "transcript_fail_then_success.jsonl")

_PROBE = normalize_target(None, "cd E:/AI-Setup && py probe_thing.py --flag")
_FINE = normalize_target(None, "cd E:/AI-Setup && echo fine")
_SCRATCH = normalize_target("E:\\AI-Setup\\.t1_scratch.txt", None)


def _call(tool="Bash", target="", ok=True, at=""):
    return {"tool": tool, "target": target, "ok": ok, "at": at}


# --- 1. fold: deterministic + total ----------------------------------------------------------------

def test_fold_empty_is_zeroed():
    s = fold_signals([])
    assert s["total_calls"] == 0 and s["fail_count"] == 0 and s["progress_count"] == 0
    assert s["reread_rate"] == 0.0 and s["repetition_rate"] == 0.0
    assert s["calls_per_progress"] == 0 and s["tail_calls_after_last_progress"] == 0
    assert s["duration_s"] == 0.0 and s["started_at"] == ""


def test_fold_reread_counts_only_repeat_path_touches():
    s = fold_signals([_call("Read", "p:a"), _call("Read", "p:b"), _call("Edit", "p:a")])
    assert s["path_calls"] == 3 and s["distinct_paths"] == 2
    assert s["reread_count"] == 1 and s["reread_rate"] == round(1 / 3, 4)


def test_fold_repetition_is_consecutive_identical_action_only():
    s = fold_signals([_call("Read", "p:a"), _call("Read", "p:a"), _call("Bash", "c:x"),
                      _call("Read", "p:a")])
    assert s["repetition_count"] == 1 and s["repetition_rate"] == 0.25
    assert s["max_target_touch"] == 3


def test_fold_flip_then_commit_is_progress_and_resets_fail_state():
    calls = [
        _call(target="c:t", ok=False),                    # fail
        _call(target="c:t", ok=True),                     # flip (progress)
        _call(target="c:t", ok=True),                     # NOT a second flip -- state was reset
        _call(target="c:py scripts/ship.py -m x", ok=True),   # commit (progress)
        _call("Read", "p:tail"),                          # churn after last progress
    ]
    s = fold_signals(calls)
    assert s["flip_count"] == 1 and s["commit_count"] == 1 and s["progress_count"] == 2
    assert s["fail_count"] == 1 and s["distinct_fail_targets"] == 1
    assert s["calls_per_progress"] == 2.5
    assert s["tail_calls_after_last_progress"] == 1


def test_fold_commit_markers_and_failed_commit_not_progress():
    ok_commits = [_call(target=f"c:{m} whatever", ok=True)
                  for m in ("git commit", "py scripts/mirror.py", "py scripts/ship.py")]
    s = fold_signals(ok_commits)
    assert s["commit_count"] == 3 and s["progress_count"] == 3
    s2 = fold_signals([_call(target="c:git commit -m x", ok=False)])
    assert s2["commit_count"] == 0 and s2["fail_count"] == 1
    assert s2["calls_per_progress"] == 1   # no progress -> the whole session's calls


def test_fold_duration_from_timestamps():
    s = fold_signals([_call(at="2026-07-02T02:19:02.000Z"), _call(at="2026-07-02T02:20:00.700Z")])
    assert s["duration_s"] == 58.7
    assert s["started_at"].startswith("2026-07-02T02:19:02") and s["ended_at"].startswith("2026-07-02T02:20:00")


def test_fold_tolerates_garbage_fields():
    s = fold_signals([{"tool": None, "target": None, "ok": "yes", "at": "not-a-time"}, {}])
    assert s["total_calls"] == 2   # degraded, not raised


# --- 2. parser: pinned live transcript shape --------------------------------------------------------

def test_parse_fixture_transcript_calls_in_order():
    calls, truncated = hook.parse_transcript_calls(_TRANSCRIPT)
    assert truncated is False
    assert [(c["tool"], c["target"], c["ok"]) for c in calls] == [
        ("Bash", _PROBE, False),
        ("Bash", _FINE, True),
        ("Edit", _SCRATCH, False),
        ("Bash", _PROBE, False),
    ]
    assert calls[0]["at"] == "2026-07-02T02:19:02.000Z"   # timestamp comes from the tool_use record


def test_parse_drops_unresulted_calls(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "u1", "name": "Read", "input": {"file_path": "E:\\AI-Setup\\x"}}]},
         "timestamp": "2026-07-02T02:19:02.000Z"},
        # u1 never gets a tool_result (interrupted) -> dropped
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "u2", "name": "Grep", "input": {"pattern": "x"}}]},
         "timestamp": "2026-07-02T02:19:03.000Z"},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "u2"}]}, "timestamp": "2026-07-02T02:19:04.000Z"},
    ]
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    calls, _ = hook.parse_transcript_calls(str(p))
    assert [(c["tool"], c["target"], c["ok"]) for c in calls] == [("Grep", "", True)]


def test_fixture_fold_end_to_end():
    calls, _ = hook.parse_transcript_calls(_TRANSCRIPT)
    s = fold_signals(calls)
    assert s["total_calls"] == 4 and s["fail_count"] == 3 and s["distinct_fail_targets"] == 2
    assert s["path_calls"] == 1 and s["reread_count"] == 0
    assert s["max_target_touch"] == 2                      # the probe command, tried twice
    assert s["progress_count"] == 0 and s["calls_per_progress"] == 4
    assert s["duration_s"] == 58.0   # at = the tool_use record's timestamp, not the result's


# --- 3. emission: exactly-once, SessionEnd-only, scoped, kill-switchable ---------------------------

def _spy_capture(monkeypatch):
    import core.events.event_log as el
    events = []
    monkeypatch.setattr(el, "capture_event",
                        lambda kind, summary, **kw: events.append((kind, summary, kw)) or None)
    return events


def _payload(transcript=_TRANSCRIPT, event="SessionEnd", sid="sess-sig-1", cwd="E:\\AI-Setup"):
    return {"hook_event_name": event, "session_id": sid, "transcript_path": transcript, "cwd": cwd}


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "_SIG_DIR", str(tmp_path / "session_signals"))


def test_emit_captures_once_then_watermarks(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    hook.emit_session_signals(_payload())
    assert len(events) == 1
    kind, summary, kw = events[0]
    assert kind == "session_signals" and kw["session_id"] == "sess-sig-1"
    assert kw["detail"]["total_calls"] == 4 and kw["detail"]["fail_count"] == 3
    assert kw["detail"]["window_truncated"] is False
    assert "4 calls" in summary and "3 fails" in summary
    hook.emit_session_signals(_payload())               # same session, same size -> suppressed
    assert len(events) == 1


def test_emit_reemits_when_resumed_session_grew(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    grown = tmp_path / "grown.jsonl"
    shutil.copy(_TRANSCRIPT, grown)
    hook.emit_session_signals(_payload(str(grown), sid="sess-sig-2"))
    assert len(events) == 1
    with open(grown, "a", encoding="utf-8") as f:       # the session resumes and does one more call
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "u9", "name": "Bash",
             "input": {"command": "cd E:/AI-Setup && py scripts/ship.py -m done"}}]},
            "timestamp": "2026-07-02T03:00:00.000Z"}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "u9"}]},
            "timestamp": "2026-07-02T03:00:01.000Z"}) + "\n")
    hook.emit_session_signals(_payload(str(grown), sid="sess-sig-2"))
    assert len(events) == 2, "a grown (resumed) session must re-emit an updated row"
    assert events[1][2]["detail"]["total_calls"] == 5
    assert events[1][2]["detail"]["commit_count"] == 1  # the ship.py call counts as progress


def test_emit_precompact_is_silent(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    hook.emit_session_signals(_payload(event="PreCompact"))
    assert events == []


def test_emit_out_of_scope_is_silent(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    hook.emit_session_signals(_payload(cwd="C:\\some\\other\\project"))
    assert events == []


def test_emit_missing_transcript_is_silent(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    hook.emit_session_signals(_payload(transcript=str(tmp_path / "nope.jsonl")))
    assert events == []


def test_emit_kill_switch(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    events = _spy_capture(monkeypatch)
    monkeypatch.setenv("AKASHIC_SESSION_SIGNALS", "0")
    hook.emit_session_signals(_payload())
    assert events == []
