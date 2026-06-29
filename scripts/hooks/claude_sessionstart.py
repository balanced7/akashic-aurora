#!/usr/bin/env python3
"""Claude Code SessionStart hook -> pre-warm recall-at-action + prune stale session state.

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"SessionStart":[{"hooks":[
    {"type":"command","command":"py scripts/hooks/claude_sessionstart.py"}]}]}}

At session start it (a) force-refreshes the recall lesson-item cache so the FIRST edit is already
warm (no cold-load hint-delay), and (b) prunes per-session anti-repeat files older than a week.
Silent and fail-OPEN -- a warm-up must never delay or break session start. (The read-bootstrap
flow also warms via `agent_cli.py boot`, so this is the repo-launch path's belt-and-suspenders.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main() -> int:
    try:
        from core.recall.at_action import warm_cache, prune_state
        warm_cache()
        prune_state()
    except Exception:
        pass   # warm-up is best-effort; never block session start
    return 0


if __name__ == "__main__":
    sys.exit(main())
