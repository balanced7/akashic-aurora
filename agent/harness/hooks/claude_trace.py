#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> live tool-call trace onto the Bifrost bus.

Claude runs OUTSIDE any Bifrost runner, so (unlike DeepSeek) its tool calls never reach the
console on their own. This hook is the bridge: for every tool call in an in-repo session it
broadcasts a display-only kind=trace line (agent/harness/trace.py), which the UI already renders
with Claude's colour. The result -- Claude "shows up" doing work, at parity with DeepSeek.

Register under PreToolUse with a broad matcher so it covers the shell (Bash AND PowerShell, the
Windows primary), file tools, and the read/search tools that make up most exploration:
  {"hooks":{"PreToolUse":[{"matcher":"Bash|PowerShell|Read|Edit|Write|NotebookEdit|Glob|Grep|Task|WebFetch|WebSearch",
    "hooks":[{"type":"command","command":"py agent/harness/hooks/claude_trace.py"}]}]}}

SEPARATE from claude_pretooluse.py on purpose: that hook is the git/lock GUARD + recall, scoped
to mutating tools and able to DENY. This one only observes -- it emits and always exits 0, never
influencing whether the tool runs. Scope-gated to this repo's sessions (safe for user-level
registration). Fail-open and silent: a trace is a nicety, never a blocker. Kill: AKASHIC_TRACE=0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def main() -> int:
    if os.getenv("AKASHIC_TRACE", "1") == "0":
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name") or ""
    if not tool:
        return 0
    try:
        # Gate by SESSION cwd, not per-target: a read/glob has no path to scope by, and we want
        # every tool call in an in-repo session to show -- while staying a no-op everywhere else.
        from agent.harness.scope import session_in_scope
        if not session_in_scope(data.get("cwd") or os.getcwd()):
            return 0
        from agent.harness.trace import emit, summarize
        emit("tool", summarize(tool, data.get("tool_input") or {}))
    except Exception:
        pass   # observation must never affect the action
    return 0


if __name__ == "__main__":
    sys.exit(main())
