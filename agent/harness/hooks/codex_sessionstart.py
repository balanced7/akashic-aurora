#!/usr/bin/env python3
"""Codex SessionStart: event-bound identity activation plus the shared boot fold."""
from __future__ import annotations

import json
import os
import sys

from agent.harness.hooks.codex_common import (
    capture_payload,
    dedup_should_skip,
    event_seat,
    subject_context,
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        if dedup_should_skip(data):
            return 0
        capture_payload(data)
        sid = str(data.get("session_id") or "")
        seat = event_seat(data)
        try:
            from core.recall.at_action import warm_cache, prune_state

            warm_cache()
            prune_state()
        except Exception:
            pass
        try:
            from core.comm import wake_seat, incarnation

            if sid:
                wake_seat.clear_tombstone(sid)
                wake_seat.touch_activity(seat, sid)
                incarnation.publish_card(seat, sid)
        except Exception:
            pass
        from agent.harness.context import build_autoboot_context

        boot = build_autoboot_context(
            str(data.get("cwd") or os.getcwd()), seat, session_id=sid
        )
        context = subject_context(seat, sid)
        if boot:
            context += "\n\n" + boot
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }}))
    except Exception as exc:
        print(f"[codex-sessionstart] suppressed: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
