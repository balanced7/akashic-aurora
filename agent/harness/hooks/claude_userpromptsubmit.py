#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook -> PLAN-TIME recall (field-survey C3).

Review leverage runs research > plan > code: a lesson injected at PreToolUse arrives AFTER
the plan is committed and can only save the line in front of the agent. This hook surfaces
the corpus BEFORE planning starts, ranked against the user's prompt itself -- the highest
altitude the harness offers per-turn.

Discipline (same rules as every recall surface):
  - top 2 only, relevance-floored, FAITH-gated, silent-when-empty (recall_at does all of it)
  - SHARED anti-repeat with the PreToolUse hook (one seen-file per session): a lesson shown
    at plan time never re-injects at action time, and vice versa
  - logged to the injection ledger with altitude="plan" (inspectable, cost-measured)
  - scope: repo or home-dir sessions only (the SessionStart whisper's tiering) -- unrelated
    projects stay unpolluted
  - fail-OPEN, kill switch AKASHIC_PLAN_RECALL=0

NOTE on crediting: plan-time impressions bump `surfaced` counters but open NO action-target
impression, so they can earn explicit useful/noise votes but never an implicit 'helped'
(there is no target to join a flip against). This DILUTES value rate by design honesty --
the ledger's altitude field keeps per-altitude analysis possible.

Also carried per-turn (H0b): ONE unread-bus line (silent-at-0) -- mid-session bus mail
otherwise waits for the next session's boot whisper; the turn start is its natural read
point. A cue like the whisper, not a lesson push, so it is not ledgered (and
AKASHIC_PLAN_RECALL=0 kills lesson injection only, never the mail cue).

Wire (user-level absolute path; the "*" matcher is REQUIRED -- lifecycle entries without one
may be silently skipped):
  {"hooks":{"UserPromptSubmit":[{"matcher":"*","hooks":[
    {"type":"command","command":"py E:/AI-Setup/agent/harness/hooks/claude_userpromptsubmit.py"}]}]}}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))



def _seat(session_id: str = "") -> str:
    """Session-scoped seat identity: binding -> env -> loud unknown-<sid8>.

    Replaces os.getenv("AKASHIC_AGENT_ID") or "claude". That fallback did not lose
    information, it IMPERSONATED the conductor: one session held two roster rows, locks
    locked a seat out of its own files, and the wakeability check could not see a correctly
    named watcher. Fail-open by hook contract -- identity must never break a session.
    """
    try:
        from core.comm.seat_identity import resolve
        return resolve(session_id)
    except Exception:
        import os as _os
        return (_os.getenv("AKASHIC_AGENT_ID") or "").strip() or "unknown"

def build_plan_recall(prompt: str, session_id: str, agent_id: str) -> str:
    """The plan-altitude context block for this prompt, or "" for silence."""
    if os.getenv("AKASHIC_PLAN_RECALL", "1") == "0":
        return ""
    if not (prompt or "").strip():
        return ""
    from core.recall.at_action import recall_at, render, log_injection
    from agent.harness.seen import load_seen, mark_seen
    res = recall_at(command=prompt, agent_id=agent_id, limit=2,
                    exclude_sources=load_seen(session_id), count_surface=True)
    out = render(res, header="Plan-time recall (Akashic) - corpus knowledge relevant to this request:")
    if not out:
        return ""
    srcs = [l.get("source") for l in res.get("lessons", [])]
    mark_seen(session_id, srcs)
    log_injection(session_id, "plan", "", srcs, len(out))
    return out


def build_bus_line(agent_id: str) -> str:
    """One line when unread bus mail waits, "" otherwise (silent-at-0). Fail-soft: an
    unreachable bus means no line, never a broken hook."""
    try:
        from agent.harness.context import _unread_count
        n = _unread_count(agent_id)
    except Exception:
        return ""
    if not n:
        return ""
    return f"[akashic] mail: {n} unread bus msg(s) -> py agent_cli.py bifrost-sync {agent_id}"


def build_page_lines() -> list:
    """T078-W4: page-grade findings reach the live seat every turn. The seat's
    doctrine (rendered in each line) is to relay via PushNotification when
    Daniel may be away, then ack. Silent when no pages. Fail-soft."""
    try:
        from core.comm import pager
        return pager.hook_lines()
    except Exception:
        return []


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(f"[plan-recall] stdin unparseable: {type(e).__name__}: {e}", file=sys.stderr)
        return 0
    try:
        from agent.harness.scope import session_in_scope
        cwd = data.get("cwd") or os.getcwd()
        if not session_in_scope(cwd):
            if os.getenv("AKASHIC_DEBUG"):
                print(f"[plan-recall] out of scope: cwd={cwd!r}", file=sys.stderr)
            return 0   # unrelated project -> full silence
        agent_id = _seat(str(data.get("session_id") or ""))
        pieces = [build_plan_recall(data.get("prompt") or "",
                                    data.get("session_id") or "", agent_id),
                  build_bus_line(agent_id)] + build_page_lines()
        ctx = "\n".join(p for p in pieces if p)
        if ctx:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ctx,
            }}))
    except Exception as e:
        # fail-OPEN for the agent, but never SILENT for the operator: a swallowed error here
        # cost a debugging session on 2026-07-02. stderr is invisible to the model.
        print(f"[plan-recall] suppressed: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
