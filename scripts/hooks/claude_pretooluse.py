#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> git-safety guard (Concurrency design C0).

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PreToolUse":[{"matcher":"Bash|PowerShell","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_pretooluse.py"}]}]}}
(PowerShell is the harness's PRIMARY shell tool on Windows -- a Bash-only matcher routes every
shell command around the guard/recall/credit pipeline entirely. Matchers, the tool filter in
main(), and _in_scope must all know a new shell tool, or it is invisible.)
Or register at the USER level with an ABSOLUTE path so it fires for EVERY session launched from
any cwd (the read-bootstrap flow), e.g. command "py E:/AI-Setup/scripts/hooks/claude_pretooluse.py".
The scope guard (agent/harness/scope.py -- shared policy, this adapter only maps Claude's tool
names onto it) makes it a silent no-op outside this repo, so global registration is safe.

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

_FILE_TOOLS = ("Edit", "Write", "NotebookEdit")
_SHELL_TOOLS = ("Bash", "PowerShell")


def _in_scope(tool: str, data) -> bool:
    """Claude tool names -> the shared scope policy (agent/harness/scope.py): file tools scope
    by their target path, shell tools by session cwd or the command itself."""
    from agent.harness.scope import file_in_scope, shell_in_scope
    ti = data.get("tool_input") or {}
    if tool in _FILE_TOOLS:
        return file_in_scope(ti.get("file_path") or "")
    return shell_in_scope(data.get("cwd") or os.getcwd(), ti.get("command") or "")


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
    """Recall-at-action: relevant active lessons + lock/peer warning for the path/command about to be
    acted on. Best-effort, capped, FAITH-gated, fail-open. ANTI-REPEAT: lessons already surfaced this
    session (agent/harness/seen.py, shared across altitudes) are excluded so the same hint never
    repeats. Locks always surface (safety). Kill switch: AKASHIC_RECALL_AT_ACTION=0."""
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    command = ti.get("command") or ""
    if not path and not command:
        return ""
    session_id = data.get("session_id") or ""
    try:
        from core.recall.at_action import (recall_at, render, mark_impression, normalize_target,
                                           log_injection)
        from agent.harness.seen import load_seen, mark_seen
        res = recall_at(path=path or None, command=command or None,
                        agent_id=os.getenv("AKASHIC_AGENT_ID"),
                        exclude_sources=load_seen(session_id), count_surface=True)
        out = render(res)
        if out:
            srcs = [l.get("source") for l in res.get("lessons", [])]
            mark_seen(session_id, srcs)
            target = normalize_target(path or None, command or None)
            # open impression for the implicit FAIL->SUCCESS credit (resolved by the PostToolUse hook)
            mark_impression(session_id, target, srcs)
            # injection ledger: pushed context must be inspectable + cost-measurable (survey C4)
            log_injection(session_id, "action", target, srcs, len(out))
        return out
    except Exception:
        return ""   # recall must never brick the action


def _check_bash(data) -> str:
    """Blanket git-staging veto -- verdict text from the shared policy (agent/harness/guards.py)."""
    try:
        from agent.harness.guards import git_veto
        return git_veto(((data.get("tool_input") or {}).get("command")) or "")
    except Exception:
        return ""   # policy unavailable -> allow


def _check_write(data) -> str:
    """Peer-lock veto (C2), incl. the RC-01 fail-closed-when-unidentified rule -- shared policy
    (agent/harness/guards.py); this adapter only says where Claude sets its env."""
    try:
        from agent.harness.guards import lock_veto
        return lock_veto((data.get("tool_input") or {}).get("file_path") or "",
                         os.getenv("AKASHIC_AGENT_ID"),
                         "e.g. in .claude/settings.json env")
    except Exception:
        return ""   # lock layer unavailable -> allow (advisory)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0   # unparseable -> allow
    tool = data.get("tool_name") or ""
    if tool not in _SHELL_TOOLS + _FILE_TOOLS:
        return 0
    if not _in_scope(tool, data):
        return 0   # outside this repo -> silent no-op (safe for user-level / global registration)
    if tool in _SHELL_TOOLS:
        reason = _check_bash(data)
    else:
        reason = _check_write(data)
    if reason:
        _deny(reason)
        return 0
    # Recall-at-action for ALL in-scope tools (Edit/Write AND Bash). Anti-repeat (per-session
    # exclude_sources) now prevents the same lesson repeating, so Bash recall front-loads relevant
    # knowledge then goes quiet instead of spamming. The git-guard above remains Bash's job.
    ctx = _recall_context(data)
    if ctx:
        _emit_context(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
