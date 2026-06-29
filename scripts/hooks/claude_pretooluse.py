#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> git-safety guard (Concurrency design C0).

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_pretooluse.py"}]}]}}
Or register at the USER level with an ABSOLUTE path so it fires for EVERY session launched from
any cwd (the read-bootstrap flow), e.g. command "py E:/AI-Setup/scripts/hooks/claude_pretooluse.py".
The _in_scope() guard makes it a silent no-op outside this repo, so global registration is safe.

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
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Repo root = three dirs up from scripts/hooks/<this file>. Used to SCOPE the guard: this hook can
# be registered at the USER level (so it fires for every Claude session, launched from any cwd --
# e.g. the read-bootstrap flow), but it MUST stay a silent no-op outside this repo so it never
# blocks edits or injects AI-Setup lessons into unrelated projects.
_ROOT = os.path.normcase(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _under_root(p: str) -> bool:
    if not p:
        return False
    try:
        a = os.path.normcase(os.path.abspath(p))
    except Exception:
        return False
    return a == _ROOT or a.startswith(_ROOT + os.sep)


def _in_scope(tool: str, data) -> bool:
    """True iff this action belongs to THIS repo, so a global registration is a silent no-op
    elsewhere. Edit/Write: the target file is under the repo (the strongest signal). Bash: the
    session cwd is in the repo, or the command clearly invokes it (agent_cli.py / an AI-Setup path).
    In a project-launched session (cwd = repo) both branches are naturally True, so behavior is
    unchanged from before."""
    ti = data.get("tool_input") or {}
    if tool in ("Edit", "Write", "NotebookEdit"):
        return _under_root(ti.get("file_path") or "")
    cwd = data.get("cwd") or os.getcwd()
    if _under_root(cwd):
        return True
    cl = (ti.get("command") or "").lower()
    return "ai-setup" in cl or "agent_cli.py" in cl


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


# --- anti-repeat: a lesson already surfaced THIS session must not be shown again. The hook is a
# fresh process per call, so shown lesson-sources are tracked in a per-session file keyed by session_id.
_SEEN_DIR = os.path.join(tempfile.gettempdir(), "akashic_recall", "seen")


def _seen_path(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:128]
    return os.path.join(_SEEN_DIR, (safe or "nosession") + ".txt")


def _load_seen(session_id: str) -> set:
    if not session_id:
        return set()
    try:
        with open(_seen_path(session_id), encoding="utf-8") as f:
            return {ln.strip() for ln in f if ln.strip()}
    except Exception:
        return set()


def _mark_seen(session_id: str, sources) -> None:
    srcs = [s for s in (sources or []) if s]
    if not session_id or not srcs:
        return
    try:
        os.makedirs(_SEEN_DIR, exist_ok=True)
        with open(_seen_path(session_id), "a", encoding="utf-8") as f:
            for s in srcs:
                f.write(s + "\n")
    except Exception:
        pass


def _recall_context(data) -> str:
    """Recall-at-action: relevant active lessons + lock/peer warning for the path/command about to be
    acted on. Best-effort, capped, FAITH-gated, fail-open. ANTI-REPEAT: lessons already surfaced this
    session (per session_id) are excluded so the same hint never repeats. Locks always surface (safety).
    Kill switch: AKASHIC_RECALL_AT_ACTION=0."""
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    command = ti.get("command") or ""
    if not path and not command:
        return ""
    session_id = data.get("session_id") or ""
    try:
        from core.recall.at_action import recall_at, render
        res = recall_at(path=path or None, command=command or None,
                        agent_id=os.getenv("AKASHIC_AGENT_ID"),
                        exclude_sources=_load_seen(session_id), count_surface=True)
        out = render(res)
        if out:
            _mark_seen(session_id, [l.get("source") for l in res.get("lessons", [])])
        return out
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
    if tool not in ("Bash", "Edit", "Write", "NotebookEdit"):
        return 0
    if not _in_scope(tool, data):
        return 0   # outside this repo -> silent no-op (safe for user-level / global registration)
    if tool == "Bash":
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
