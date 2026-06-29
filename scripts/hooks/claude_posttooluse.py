#!/usr/bin/env python3
"""Claude Code PostToolUse hook -> resolve the recall-at-action implicit-useful signal.

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PostToolUse":[{"matcher":"Bash|Edit|Write|NotebookEdit","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_posttooluse.py"}]}]}}
Or user-level with an ABSOLUTE path (same as the PreToolUse hook).

After a tool runs, if the target (file path / command) JUST FAILED and now SUCCEEDS, the lessons
recall surfaced for it are credited 'helped' -- the contrastive auto-positive (a first-try success
credits nothing). Scope-guarded to this repo, fail-OPEN, side-effect-only (the action already ran).
Success detection is conservative: when unsure it assumes success, so the signal stays INERT rather
than mis-crediting. Disable with AKASHIC_RECALL_AT_ACTION=0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_ROOT = os.path.normcase(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _under_root(p):
    if not p:
        return False
    try:
        a = os.path.normcase(os.path.abspath(p))
    except Exception:
        return False
    return a == _ROOT or a.startswith(_ROOT + os.sep)


def _in_scope(tool, data):
    """Silent no-op outside this repo (so a global registration is safe). Mirrors the PreToolUse guard."""
    ti = data.get("tool_input") or {}
    if tool in ("Edit", "Write", "NotebookEdit"):
        return _under_root(ti.get("file_path") or "")
    cwd = data.get("cwd") or os.getcwd()
    if _under_root(cwd):
        return True
    cl = (ti.get("command") or "").lower()
    return "ai-setup" in cl or "agent_cli.py" in cl


def _is_success(data) -> bool:
    """Best-effort, CONSERVATIVE: only call it a failure on a clear error marker; otherwise success.
    Biasing to success keeps the FAIL->SUCCESS signal inert when the payload is unclear (never mis-credits)."""
    tr = data.get("tool_response")
    if isinstance(tr, dict):
        if tr.get("is_error") is True or tr.get("error"):
            return False
        if "success" in tr:
            return bool(tr.get("success"))
        for k in ("exit_code", "exitCode", "returncode", "code"):
            if k in tr:
                try:
                    return int(tr[k]) == 0
                except Exception:
                    pass
    if isinstance(tr, str):
        low = tr.lower()
        if "traceback (most recent call last)" in low or "command not found" in low:
            return False
    return True


def main() -> int:
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name") or ""
    if tool not in ("Bash", "Edit", "Write", "NotebookEdit"):
        return 0
    if not _in_scope(tool, data):
        return 0
    try:
        from core.recall.at_action import normalize_target, resolve_outcome
        ti = data.get("tool_input") or {}
        target = normalize_target(ti.get("file_path") or None, ti.get("command") or None)
        resolve_outcome(data.get("session_id") or "", target, _is_success(data))
    except Exception:
        pass   # resolving a credit must never affect the agent
    return 0


if __name__ == "__main__":
    sys.exit(main())
