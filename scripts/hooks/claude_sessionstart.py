#!/usr/bin/env python3
"""Claude Code SessionStart hook -> light auto-boot + pre-warm recall + prune stale state.

Wire it in .claude/settings.json (project-launch, relative path -- the "*" matcher is
REQUIRED: session-lifecycle entries without one are silently skipped):
  {"hooks":{"SessionStart":[{"matcher":"*","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_sessionstart.py"}]}]}}
Or user-level with an ABSOLUTE path (fires for every session, any cwd).

Thin translator (Integration Tiers H0): the whisper itself -- what it says, when it
stays silent, the repo/home/elsewhere tiering -- is agent/harness/context.py, shared
by every harness. This adapter only parses Claude's stdin shape, warms the recall
cache, and emits Claude's additionalContext envelope.
Fail-OPEN and silent on ANY error -- session start must never be delayed or broken.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        from core.recall.at_action import warm_cache, prune_state
        warm_cache()
        prune_state()
    except Exception:
        pass   # warm-up is best-effort; never block session start
    try:
        from agent.harness.context import build_autoboot_context
        ctx = build_autoboot_context(data.get("cwd") or os.getcwd(),
                                     os.getenv("AKASHIC_AGENT_ID") or "claude")
        if ctx:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }}))
    except Exception:
        pass   # the whisper is a bonus; silence beats a broken session start
    return 0


if __name__ == "__main__":
    sys.exit(main())
