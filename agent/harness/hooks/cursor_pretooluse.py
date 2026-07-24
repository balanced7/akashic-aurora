#!/usr/bin/env python3
"""Cursor `preToolUse` hook -> vetoes only (git-safety + peer-lock).

Pinned constraint (cursor.com/docs/agent/hooks, 2026-07-02): preToolUse output is
DENY-ONLY -- permission / agent_message / updated_input; it CANNOT attach context on an
allow. So unlike the Claude adapter there is no recall injection here: action-time
recall arrives one beat late via cursor_posttooluse.py (the T3 approximation,
docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md). This hook only vetoes, with verdicts from the shared
policy (agent/harness/guards.py):
  - a shell command that blanket-stages git (matcher: Shell)
  - editing a path a PEER holds an advisory lock on (matcher: Write)

The payload shape has no pinned fixture yet -> capture FIRST, extract defensively
(command / file_path with tool_input fallbacks), fail OPEN. Scope: .cursor/hooks.json
is project config, so events only arrive for this repo; the lock guard additionally
no-ops on paths outside it (agent/harness/scope.py) as a belt against surprises.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CAP_DIR = os.path.join(_STATE_ROOT, "payloads_cursor")


def _fields(data):
    """Best-effort (command, file_path) across the unpinned payload shapes."""
    ti = data.get("tool_input") or {}
    command = data.get("command") or ti.get("command") or ""
    path = data.get("file_path") or ti.get("file_path") or data.get("path") or ti.get("path") or ""
    return command, path


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label="preToolUse")
    except Exception:
        pass
    command, path = _fields(data)
    reason = ""
    try:
        from agent.harness.guards import git_veto, lock_veto
        from agent.harness.scope import file_in_scope
        if command:
            reason = git_veto(command)
        if not reason and path and file_in_scope(path):
            reason = lock_veto(path, os.getenv("AKASHIC_AGENT_ID"),
                               "propagated by cursor_sessionstart.py; check .cursor/hooks.json wiring")
    except Exception:
        reason = ""   # guards unavailable -> allow
    if not reason:
        print(json.dumps({"permission": "allow"}))
    else:
        print(json.dumps({
            "permission": "deny",
            "agentMessage": reason,
            "userMessage": "Blocked by the shared-tree guard (see agent message).",
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
