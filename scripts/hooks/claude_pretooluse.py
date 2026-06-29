#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> git-safety guard (Concurrency design C0).

Wire it in .claude/settings.json:
  {"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_pretooluse.py"}]}]}}

Reads the tool-call JSON on stdin. If the Bash command blanket-stages git (or a peer holds
an advisory lock on the target path), emit a DENY decision (the reason is fed back to Claude).
Otherwise the action is ALLOWED -- and on the allow path we attach RECALL-AT-ACTION:
`hookSpecificOutput.additionalContext` carrying the few highest-signal active lessons + any
lock/peer warning for this path/command (core/recall/at_action.py). This is the read-at-the-
moment-of-action seam -- the one native injection that lands AT the locus, not at turn-start.
Recall is best-effort, capped, FAITH-gated, and fails OPEN. Disable with AKASHIC_RECALL_AT_ACTION=0.
Fails OPEN on any unexpected error -- a guard must never brick the agent.

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


def _emit_context(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}))


def _recall_context(data) -> str:
    """Recall-at-action: relevant active lessons + lock/peer warning for the path/command about to
    be acted on. Best-effort, capped, FAITH-gated, fail-open. Kill switch: AKASHIC_RECALL_AT_ACTION=0."""
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    command = ti.get("command") or ""
    if not path and not command:
        return ""
    try:
        from core.recall.at_action import recall_at, render
        return render(recall_at(path=path or None, command=command or None,
                                agent_id=os.getenv("AKASHIC_AGENT_ID")))
    except Exception:
        return ""   # recall must never brick the action


def _check_bash(data) -> str:
    command = ((data.get("tool_input") or {}).get("command")) or ""
    try:
        from agent.policy.git_guard import check_git_command
        allowed, reason = check_git_command(command)
    except Exception:
        return ""   # policy unavailable -> allow
    return "" if allowed else reason


def _check_write(data) -> str:
    """Block editing a path a PEER holds an advisory lock on (C2). With AKASHIC_AGENT_ID set we
    know who we are and only a PEER's lock blocks. With it UNSET we can't verify ownership, so we
    fail CLOSED on any locked path (teaching the fix) -- a silently-unset id must not disable the
    guard (the RC-01 fail-open). An unlocked path is always allowed; the lock layer being
    unavailable allows (advisory)."""
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return ""
    me = os.getenv("AKASHIC_AGENT_ID")
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, me or "(unidentified)")
    except Exception:
        return ""   # lock layer unavailable -> allow (advisory)
    if not c.get("conflict"):
        return ""
    if not me:
        return (f"AKASHIC_AGENT_ID is not set, so lock ownership can't be verified and this path is "
                f"locked by {c.get('held_by')}. Set AKASHIC_AGENT_ID=<your agent id> "
                f"(e.g. in .claude/settings.json env) so the peer-lock guard can tell your edits from a peer's.")
    return c.get("reason", "")


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
    # Allow path: surface recall-at-action context (non-blocking, fail-open, capped, FAITH-gated).
    ctx = _recall_context(data)
    if ctx:
        _emit_context(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
