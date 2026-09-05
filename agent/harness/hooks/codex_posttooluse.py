#!/usr/bin/env python3
"""Codex-native PostToolUse adapter with direct outcome accounting.

Unlike Claude Code, Codex emits PostToolUse after non-zero Bash commands.  This adapter uses
that event directly and never reconstructs failures from Codex's unstable rollout transcript.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

from agent.harness.hooks.codex_common import (
    action_targets,
    capture_payload,
    dedup_should_skip,
    event_in_scope,
    event_seat,
    in_scope_paths,
    touch_working,
)


TOOLS = {"Bash", "apply_patch"}


def is_success(data: Dict[str, Any]) -> bool:
    response = data.get("tool_response")
    if isinstance(response, dict):
        if response.get("is_error") is True or response.get("isError") is True:
            return False
        if response.get("error"):
            return False
        if "success" in response:
            return bool(response.get("success"))
        for key in ("exit_code", "exitCode", "returncode"):
            if key in response:
                try:
                    return int(response[key]) == 0
                except (TypeError, ValueError):
                    return False
    if data.get("is_error") is True or data.get("isError") is True or data.get("error"):
        return False
    return True


def resolve(session_id: str, target: str, success: bool, seat: str) -> None:
    try:
        from core.recall.at_action import resolve_action_outcome

        resolve_action_outcome(session_id, target, success, agent_id=seat)
    except Exception:
        pass


def capture_failure(target: str, tool: str, seat: str) -> None:
    try:
        from core.events.event_log import capture_event

        capture_event(
            "fail",
            f"FAIL: {target}",
            agent_id=seat,
            detail={"target": target, "tool": tool, "harness": "codex-desktop"},
        )
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        sid = str(data.get("session_id") or "")
        seat = event_seat(data)
        touch_working(seat, sid)
        tool = str(data.get("tool_name") or "")
        if tool not in TOOLS:
            return 0
        if dedup_should_skip(data):
            return 0
        capture_payload(data)
        if not event_in_scope(data):
            return 0
        success = is_success(data)
        targets = action_targets(data)
        if tool == "apply_patch":
            from core.recall.at_action import normalize_target

            targets = [normalize_target(path=path) for path in in_scope_paths(data)]
        for target in targets:
            resolve(sid, target, success, seat)
            if not success:
                capture_failure(target, tool, seat)
    except Exception as exc:
        print(f"[codex-posttool] suppressed: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
