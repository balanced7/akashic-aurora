#!/usr/bin/env python3
"""Claude Code SessionEnd / PreCompact hook -> auto-draft a where-we-are from the session's activity.

Wire it in .claude/settings.json for BOTH events (PreCompact is the high-value one -- it fires right
before context is compacted away, the main "lost where-we-are" moment):
  {"hooks":{"PreCompact":[{"hooks":[{"type":"command","command":"py scripts/hooks/claude_sessionend.py"}]}],
            "SessionEnd":[{"hooks":[{"type":"command","command":"py scripts/hooks/claude_sessionend.py"}]}]}}

It distills the session's own commits + lessons + notes into chronicles/last-session-draft.md (a DRAFT
FILE, not a note -- so it never clutters the curated substrate or passes off an unreviewed activity
list as truth). `boot` surfaces a one-line pointer; promote it with `py agent_cli.py wrap --commit`
only if it's worth keeping. Silent + fail-OPEN: a capture must never block the session ending.
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
        import agent_cli
        from core.learning.agent_memory import get_agent_memory
        commits = agent_cli._recent_commits(24)
        lessons = agent_cli._recent_lessons(8)
        notes = get_agent_memory().get_decisions(days=1)
        try:   # FAIL->SUCCESS flips -> pre-filled candidate lessons in the draft (friction audit D5)
            from core.recall.at_action import recent_flips
            flips = recent_flips(24)
        except Exception:
            flips = []
        agent_cli.write_last_session_draft(
            agent_cli.last_session_draft_path(), commits, lessons, notes,
            trigger=str(data.get("hook_event_name") or "session end"), flips=flips)
    except Exception:
        pass   # auto-capture is best-effort; never block the end
    return 0


if __name__ == "__main__":
    sys.exit(main())
