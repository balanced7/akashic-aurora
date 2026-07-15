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


def _reap_stale_watcher(my_session: str = "") -> None:
    """T029 Wave 2 (supersedes the T017 D4 identity-only reap -- battery sec. 6): the janitor.
    Walks every seat for this agent and acts per the reconciled protocol: dead-pid seats are
    cleaned (no kill), the one legacy name-keyed ghost is migrated (K6), and a LIVE watcher is
    reaped ONLY on two-factor-proven orphanhood -- activity marker stale AND parent chain dead
    (K7: an idle-but-alive session is immune; turn cadence is not liveness). Any verification
    error means alive (K8). Concurrent same-id sessions therefore never kill each other's
    watchers -- duty moves by displacement + stand-down, and every decision lands as one line
    in bifrost_wake_<agent>.reap.log. Best-effort, bounded, never blocks the session."""
    agent = os.getenv("AKASHIC_AGENT_ID") or "claude"
    try:
        from core.comm import wake_seat
        wake_seat.janitor(agent, my_session=my_session or None)
    except Exception:
        pass                         # fail-open: the janitor is a bonus, never a gate


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
        # Stamp THIS session alive the moment it exists -- the janitor's K7 fast path
        # (and the twin-session proof-of-life) starts at first breath, not first stop.
        sid = str(data.get("session_id") or "")
        if sid:
            from core.comm import wake_seat
            wake_seat.touch_activity(os.getenv("AKASHIC_AGENT_ID") or "claude", sid)
    except Exception:
        pass
    try:
        # T074 W11: publish this session's incarnation card at first breath -- siblings'
        # whispers render it, --to-incarnation has an address, TTL reaps it if we die.
        if sid:
            from core.comm import incarnation
            incarnation.publish_card(os.getenv("AKASHIC_AGENT_ID") or "claude", sid)
    except Exception:
        pass
    try:
        # Wave 2: the janitor runs on every NEW lane; resume/compact continue the SAME
        # lane whose own armed watcher still serves it. (Live watchers are safe from the
        # janitor regardless -- two-factor orphanhood -- so this exemption is now about
        # skipping pointless work, not about safety.)
        if str(data.get("source") or "startup") not in ("resume", "compact"):
            _reap_stale_watcher(my_session=str(data.get("session_id") or ""))
    except Exception:
        pass
    try:
        from agent.harness.context import build_autoboot_context
        ctx = build_autoboot_context(data.get("cwd") or os.getcwd(),
                                     os.getenv("AKASHIC_AGENT_ID") or "claude",
                                     session_id=str(data.get("session_id") or ""))
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
