#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> git-safety guard (Concurrency design C0).

Wire it in .claude/settings.json:
  {"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_pretooluse.py"}]}]}}

Reads the tool-call JSON on stdin. If the Bash command blanket-stages git, emit a
DENY decision (the reason is fed back to Claude). Everything else is allowed. Fails
OPEN on any unexpected error -- a guard must never brick the agent.

Note: exit 0 + a {permissionDecision:"deny"} JSON is the documented block path.
Do NOT signal a policy block with exit code 1 -- Claude Code treats exit 1 as a
non-blocking error and PROCEEDS with the action.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def _check_bash(data) -> str:
    command = ((data.get("tool_input") or {}).get("command")) or ""
    try:
        from agent.policy.git_guard import check_git_command
        allowed, reason = check_git_command(command)
    except Exception:
        return ""   # policy unavailable -> allow
    return "" if allowed else reason


def _check_write(data) -> str:
    """Block editing a path a PEER holds an advisory lock on (C2). Needs the agent's id
    in AKASHIC_AGENT_ID; without it we can't know who we are, so we allow (fail-open)."""
    me = os.getenv("AKASHIC_AGENT_ID")
    if not me:
        return ""
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return ""
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, me)
    except Exception:
        return ""
    return c["reason"] if c.get("conflict") else ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0   # unparseable -> allow
    tool = data.get("tool_name") or ""
    if tool == "Bash":
        reason = _check_bash(data)
    elif tool in ("Edit", "Write", "NotebookEdit"):
        reason = _check_write(data)
    else:
        return 0
    if reason:
        _deny(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
