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


def _reap_stale_watcher() -> None:
    """P0/T017 (D4): a bifrost_wake watcher outliving its session is an orphan -- its completion
    re-invokes a DEAD session, and its live heartbeat satisfies the stop hook's wake_armed(), so
    the NEW session never arms its own listener (the T016 double-failure: unwakeable AND, before
    the detect-only fix, mail-eating). At session start the seat belongs to THIS session: kill a
    verified orphan (command line must contain bifrost_wake -- never kill a recycled pid) and
    clear the heartbeat so the first stop re-arms fresh. Every path is self-healing: a wrongly
    cleared heartbeat just makes the stop hook arm a new watcher, and the newest-wins singleton
    stands any survivor down. Best-effort, bounded, never blocks the session."""
    import subprocess
    import tempfile
    agent = os.getenv("AKASHIC_AGENT_ID") or "claude"
    hb = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{agent}.pid")
    try:
        pid = int(open(hb).read().strip())
    except Exception:
        return                       # no heartbeat -> nothing to reap
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, timeout=5).stdout or ""
        if "bifrost_wake" in out:    # verified: it really is a prior session's watcher
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=5)
    except Exception:
        pass                         # verification failed -> still clear the stale heartbeat
    try:
        os.remove(hb)
    except Exception:
        pass


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
        # P0: the wake seat belongs to the NEW session -- but only a NEW lane reaps.
        # On resume/compact the SAME lane continues and its own armed watcher still
        # serves it; killing it would be self-harm (stop hook would re-arm, with a gap).
        if str(data.get("source") or "startup") not in ("resume", "compact"):
            _reap_stale_watcher()
    except Exception:
        pass
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
