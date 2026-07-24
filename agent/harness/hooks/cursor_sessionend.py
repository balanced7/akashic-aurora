#!/usr/bin/env python3
"""Cursor `sessionEnd` hook -> auto-draft a where-we-are from the session's activity.

Same distillation as the Claude adapter (claude_sessionend.py): the session's own commits +
lessons + notes + FAIL->SUCCESS flips become chronicles/last-session-draft.md -- a DRAFT
FILE, not a note, so it never passes an unreviewed activity list off as truth. `boot`
surfaces a one-line pointer; promote with `py agent_cli.py wrap --commit` if worth keeping.

Payload capture comes first (payload-truth discipline; shape unpinned until H2).
Silent + fail-OPEN: a capture must never block the session ending.
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
        data = {}
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label="sessionEnd")
    except Exception:
        pass
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
            trigger="cursor " + str(data.get("hook_event_name") or "sessionEnd"), flips=flips)
    except Exception:
        pass   # auto-capture is best-effort; never block the end
    return 0


if __name__ == "__main__":
    sys.exit(main())
