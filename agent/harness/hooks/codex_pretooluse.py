#!/usr/bin/env python3
"""Codex-native PreToolUse adapter for Bash and canonical ``apply_patch`` events."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from agent.harness.hooks.codex_common import (
    action_paths,
    capture_payload,
    dedup_should_skip,
    event_in_scope,
    event_seat,
    in_scope_paths,
    subject_context,
    touch_working,
)


TOOLS = {"Bash", "apply_patch"}


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def emit_context(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}))


def lock_reason(path: str, seat: str) -> str:
    try:
        from agent.harness.guards import lock_veto

        return lock_veto(path, seat, "Codex session binding or AKASHIC_AGENT_ID=sol")
    except Exception:
        return ""


def bash_reason(data: Dict[str, Any]) -> str:
    try:
        from agent.harness.guards import git_veto

        ti = data.get("tool_input")
        ti = ti if isinstance(ti, dict) else {}
        return git_veto(str(ti.get("command") or ""))
    except Exception:
        return ""


def id_fact(path: str) -> str:
    try:
        from agent.harness.hooks.claude_pretooluse import id_facts_for_path

        return id_facts_for_path(path)
    except Exception:
        return ""


def recall_context(data: Dict[str, Any], seat: str, primary_path: str = "") -> str:
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    ti = data.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    command = str(ti.get("command") or "") if data.get("tool_name") == "Bash" else ""
    if not primary_path and not command:
        return ""
    sid = str(data.get("session_id") or "")
    try:
        from core.recall.at_action import recall_at, render, mark_impression, normalize_target, log_injection
        from agent.harness.seen import load_seen, mark_seen

        res = recall_at(
            path=primary_path or None,
            command=command or None,
            agent_id=seat,
            exclude_sources=load_seen(sid),
            count_surface=True,
        )
        out = render(res)
        if out:
            sources = [row.get("source") for row in res.get("lessons", []) if row.get("source")]
            mark_seen(sid, sources)
            target = normalize_target(primary_path or None, command or None)
            mark_impression(sid, target, sources)
            log_injection(sid, "action", target, sources, len(out))
        return out
    except Exception:
        return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        sid = str(data.get("session_id") or "")
        seat = event_seat(data)
        touch_working(seat, sid)
        if str(data.get("tool_name") or "") not in TOOLS:
            return 0
        if dedup_should_skip(data):
            return 0
        capture_payload(data)
        if not event_in_scope(data):
            return 0

        paths = in_scope_paths(data)
        reason = bash_reason(data) if data.get("tool_name") == "Bash" else ""
        if not reason:
            for path in paths:
                reason = lock_reason(path, seat)
                if reason:
                    break
        if reason:
            deny(reason)
            return 0

        pieces = [id_fact(path) for path in paths]
        pieces.append(recall_context(data, seat, paths[0] if paths else ""))
        pieces = [piece for piece in pieces if piece]
        if pieces:
            emit_context(subject_context(seat, sid) + "\n" + "\n".join(pieces))
    except Exception as exc:
        print(f"[codex-pretool] suppressed: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
