#!/usr/bin/env python3
"""Cursor `beforeShellExecution` hook -> git-safety guard (Concurrency design C0).

Same rulebook as the Claude hook (agent/policy/git_guard.py) so the policy can't
drift between the two agents. Reads the hook JSON on stdin; if the shell command
blanket-stages git, DENY with a teaching message (agentMessage is fed to Cursor's
agent, userMessage is shown to the human).

Wire it in Cursor's hooks config (owned by Cursor -- ask Cursor to add it):
  beforeShellExecution -> command: py scripts/hooks/cursor_beforeshell.py
Set the hook fail-closed in Cursor if you want a parse error to block rather than
allow; this script itself fails OPEN (allow) so a bug never bricks the agent.

NOTE: verify the exact field names against the live Cursor hooks docs -- this reads
`command` (with a `tool_input.command` fallback) and emits {permission:"deny",...}.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0
    command = data.get("command") or ((data.get("tool_input") or {}).get("command")) or ""
    try:
        from agent.policy.git_guard import check_git_command
        allowed, reason = check_git_command(command)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0
    if allowed:
        print(json.dumps({"permission": "allow"}))
    else:
        print(json.dumps({
            "permission": "deny",
            "agentMessage": reason,
            "userMessage": "Blocked blanket git staging in the shared tree (see agent message).",
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
