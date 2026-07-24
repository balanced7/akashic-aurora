#!/usr/bin/env python3
"""Cursor `beforeShellExecution` hook -> git-safety guard (Concurrency design C0).

Same rulebook as the Claude adapter -- the verdict comes from agent/harness/guards.py
(which wraps agent/policy/git_guard.py), so the policy can't drift between the two
agents. Reads the hook JSON on stdin; if the shell command blanket-stages git, DENY
with a teaching message (agentMessage is fed to Cursor's agent, userMessage is shown
to the human).

Wired in .cursor/hooks.json (matcher pre-filters to git add/commit; failClosed there
means a CRASH blocks, but this script itself fails OPEN -- prints allow -- so a bug
never bricks the agent). Payload capture comes first (payload-truth discipline);
`command` (with a `tool_input.command` fallback) is the field per the pinned docs
(cursor.com/docs/agent/hooks, 2026-07-02) -- H2 pins live captures as the contract.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CAP_DIR = os.path.join(_STATE_ROOT, "payloads_cursor")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label="beforeShellExecution")
    except Exception:
        pass
    command = data.get("command") or ((data.get("tool_input") or {}).get("command")) or ""
    try:
        from agent.harness.guards import git_veto
        reason = git_veto(command)
    except Exception:
        reason = ""   # policy unavailable -> allow
    if not reason:
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
