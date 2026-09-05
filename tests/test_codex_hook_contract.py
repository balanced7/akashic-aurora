"""Codex lifecycle contract pins.

The fixtures are documentation-shaped, not claimed live captures.  They encode the current
Codex hook contract documented on 2026-08-26; the adapter also captures bounded live payloads
under ``%TEMP%/akashic_recall/codex_payloads`` so a fresh-task drill can promote observed shapes
to fixtures later.  The distinction is load-bearing: configured is not observed.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from agent.harness import registry
from agent.harness.hooks import codex_common as common
from agent.harness.hooks import codex_posttooluse as post
from agent.harness.hooks import codex_pretooluse as pre


ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "codex_payloads"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_docs_apply_patch_uses_command_and_extracts_every_path():
    payload = _load("pretooluse_apply_patch_docs.json")
    assert payload["tool_name"] == "apply_patch"
    paths = common.action_paths(payload)
    fixture_root = Path(payload["cwd"])
    assert paths == [
        os.path.normpath(str(fixture_root / "agent/harness/registry.py")),
        os.path.normpath(str(fixture_root / "tests/fixtures/codex_payloads/new.txt")),
    ]


def test_patch_move_destination_is_a_guarded_target():
    payload = _load("pretooluse_apply_patch_docs.json")
    payload["tool_input"]["command"] = (
        "*** Begin Patch\n*** Update File: old.txt\n*** Move to: moved/new.txt\n*** End Patch"
    )
    fixture_root = Path(payload["cwd"])
    assert common.action_paths(payload) == [
        os.path.normpath(str(fixture_root / "old.txt")),
        os.path.normpath(str(fixture_root / "moved/new.txt")),
    ]


def test_subject_header_names_address_session_and_unratified_hint(monkeypatch):
    monkeypatch.setenv("AKASHIC_CALLSIGN_HINT", "Sunshine")
    monkeypatch.setenv("AKASHIC_CALLSIGN_STATUS", "historical-unratified")
    monkeypatch.setenv(
        "AKASHIC_IDENTITY_POINTER",
        str(ROOT / "research/in-flight/sol-sunshine-identity-history-2026-08-26.md"),
    )
    monkeypatch.setenv("AKASHIC_IDENTITY_POINTER_SUBJECT", "sol")
    out = common.subject_context("sol", "session-123")
    assert "subject: sol" in out
    assert "session: session-123" in out
    assert "Sunshine" in out and "historical-unratified" in out
    assert "attribution is not verification" in out.lower()
    assert "identity-history pointer [subject=sol]" in out
    assert "sol-sunshine-identity-history" in out


def test_identity_pointer_is_refused_when_its_declared_subject_differs(monkeypatch):
    monkeypatch.setenv("AKASHIC_IDENTITY_POINTER", "eye route walk the-string-of-the-name")
    monkeypatch.setenv("AKASHIC_IDENTITY_POINTER_SUBJECT", "dsh_agent")
    out = common.subject_context("sol", "session-123")
    assert "REFUSED" in out
    assert "declared=dsh_agent, active=sol" in out
    assert "the-string-of-the-name" not in out


def test_subject_header_never_promotes_a_hint_to_registry_truth(monkeypatch):
    monkeypatch.setenv("AKASHIC_CALLSIGN_HINT", "Sunshine")
    monkeypatch.setenv("AKASHIC_CALLSIGN_STATUS", "historical-unratified")
    monkeypatch.setattr(common, "ratified_callsign", lambda _seat: "")
    out = common.subject_context("sol", "s")
    assert "historical-unratified" in out
    assert "ratified callsign: Sunshine" not in out


def test_event_seat_is_resolved_from_payload_session_not_process_env(monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    seen = []
    monkeypatch.setattr(common, "resolve_seat", lambda sid: seen.append(sid) or "sol")
    assert common.event_seat({"session_id": "event-session"}) == "sol"
    assert seen == ["event-session"]


def test_direct_posttool_failure_does_not_depend_on_transcript():
    payload = _load("posttooluse_bash_failure_docs.json")
    payload["transcript_path"] = "C:/definitely/missing.jsonl"
    assert post.is_success(payload) is False
    payload["tool_response"]["exit_code"] = 0
    assert post.is_success(payload) is True


def test_pretool_apply_patch_checks_every_repo_path(monkeypatch, tmp_path, capsys):
    payload = _load("pretooluse_apply_patch_docs.json")
    checked = []
    monkeypatch.setattr(pre, "event_seat", lambda _data: "sol")
    monkeypatch.setattr(pre, "dedup_should_skip", lambda _data: False)
    monkeypatch.setattr(pre, "capture_payload", lambda _data: None)
    # This test proves every translated path reaches the lock gate. Scope
    # routing has separate pins and the documentation-shaped fixture names the
    # canonical E:/AI-Setup host path, which must not make the test clone-bound.
    monkeypatch.setattr(pre, "event_in_scope", lambda _data: True)
    monkeypatch.setattr(pre, "in_scope_paths", lambda data: common.action_paths(data))
    monkeypatch.setattr(pre, "lock_reason", lambda path, seat: checked.append((path, seat)) or "")
    monkeypatch.setattr(pre, "recall_context", lambda *_args, **_kw: "")
    monkeypatch.setattr(pre, "id_fact", lambda _path: "")
    monkeypatch.setattr(pre, "touch_working", lambda *_args: None)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert pre.main() == 0
    assert checked == [(p, "sol") for p in common.action_paths(payload)]
    assert capsys.readouterr().out == ""


def test_posttool_resolves_direct_failure_for_the_same_command(monkeypatch):
    payload = _load("posttooluse_bash_failure_docs.json")
    calls = []
    monkeypatch.setattr(post, "dedup_should_skip", lambda _data: False)
    monkeypatch.setattr(post, "capture_payload", lambda _data: None)
    monkeypatch.setattr(post, "event_seat", lambda _data: "sol")
    monkeypatch.setattr(post, "event_in_scope", lambda _data: True)
    monkeypatch.setattr(post, "touch_working", lambda *_args: None)
    monkeypatch.setattr(post, "resolve", lambda sid, target, ok, seat: calls.append((sid, target, ok, seat)))
    monkeypatch.setattr(post, "capture_failure", lambda *_args: None)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert post.main() == 0
    assert calls == [
        ("codex-docs-session", common.action_targets(payload)[0], False, "sol")
    ]


def test_repo_hooks_are_codex_native_and_single_handler_per_event():
    cfg = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hooks = cfg["hooks"]
    for event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"):
        commands = [h["command"] for group in hooks[event] for h in group["hooks"]]
        assert commands and all("codex_" in command for command in commands)
        assert all("claude_" not in command for command in commands)
        assert all(command.startswith("py scripts/hooks/codex_") for command in commands), (
            "repository hooks must be clone-relative; user-level hooks may carry an absolute root"
        )
    assert len(hooks["PreToolUse"]) == 1
    assert len(hooks["PostToolUse"]) == 1


def test_codex_desktop_is_registered_without_false_live_claims():
    assert "codex-desktop" in registry.HARNESSES
    assert registry.HARNESSES["codex-desktop"]["default_agent_id"] == "sol"
    assert "codex_app_server.py" in registry.HARNESSES["codex-desktop"]["adapters"]
    assert registry.HARNESSES["codex-desktop"]["wake"].startswith("armed --")
    assert "remain unobserved" in registry.HARNESSES["codex-desktop"]["wake"]
    assert registry.supported("codex-desktop", "T0") is True
    assert registry.supported("codex-desktop", "T1") is True
    for tier in ("T2", "T3", "T4", "T5", "T6"):
        assert registry.supported("codex-desktop", tier) is False
        assert registry.capability("codex-desktop", tier).startswith("pending ")
