#!/usr/bin/env python3
"""Cursor `postToolUse` / `postToolUseFailure` hooks -> outcome credit (T4) + one-beat-late recall (T3).

Pinned (cursor.com/docs/agent/hooks, 2026-07-02): BOTH events exist, and postToolUse output
may carry additional_context. The failure event is a DIRECT fail signal -- cleaner than the
Claude adapter, which never receives failures and must synthesize them from the session
transcript (see claude_posttooluse.py); no transcript parsing, no per-failure watermark.
Session key = conversation_id.

Which event fired comes from argv (--event postToolUseFailure, wired in .cursor/hooks.json)
with a payload hook_event_name fallback -- deterministic even while the payload shape is
unpinned. Whether Cursor honors context output on the FAILURE event is unverified; emitting
it is harmless if ignored (conservative until fixtures pinned).

Per event (targets normalized by core/recall/at_action.normalize_target):
  failure -> resolve_action_outcome(sid, target, False): opens the FAIL half of a flip. Then
             inject recall for the target -- the retry is the moment a lesson earns its
             tokens -- and open impressions so a later success credits what was shown.
  success -> resolve_action_outcome(sid, target, True). On a FAIL->SUCCESS flip: durable flip
             event + the JIT learn nudge (rate limit = agent/harness/nudge.py). Otherwise:
             inject any unseen recall for the target (one beat late for THIS action, in time
             for the next one like it -- Cursor's preToolUse cannot inject on allow).

Anti-repeat = agent/harness/seen.py (shared across altitudes and harness surfaces);
injections are ledgered altitude="action". Payload capture comes FIRST and has its own kill
switch (AKASHIC_PAYLOAD_CAPTURE=0) -- while shapes are unpinned, capture IS the product.
Recall/credit kill switch: AKASHIC_RECALL_AT_ACTION=0. Everything fails OPEN.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CAP_DIR = os.path.join(_STATE_ROOT, "payloads_cursor")
_NUDGE_DIR = os.path.join(_STATE_ROOT, "nudge")


def _event(data) -> str:
    for i, a in enumerate(sys.argv):
        if a == "--event" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return str(data.get("hook_event_name") or "postToolUse")


def _fields(data):
    """Best-effort (command, file_path) across the unpinned payload shapes."""
    ti = data.get("tool_input") or {}
    command = data.get("command") or ti.get("command") or ""
    path = data.get("file_path") or ti.get("file_path") or data.get("path") or ti.get("path") or ""
    return command, path


def _emit_context(text: str) -> None:
    print(json.dumps({"additional_context": text}))


def _recall_block(sid: str, path: str, command: str) -> str:
    """Unseen lessons + lock warnings for this target; marks seen/impressions and ledgers the
    push. Same sequence as claude_pretooluse._recall_context -- second copy; a third harness
    triggers extraction (rule of three, the deferred actions.py)."""
    if not path and not command:
        return ""
    try:
        from core.recall.at_action import (recall_at, render, mark_impression, normalize_target,
                                           log_injection)
        from agent.harness.seen import load_seen, mark_seen
        res = recall_at(path=path or None, command=command or None,
                        agent_id=os.getenv("AKASHIC_AGENT_ID"),
                        exclude_sources=load_seen(sid), count_surface=True)
        out = render(res)
        if out:
            srcs = [l.get("source") for l in res.get("lessons", [])]
            mark_seen(sid, srcs)
            target = normalize_target(path or None, command or None)
            mark_impression(sid, target, srcs)
            log_injection(sid, "action", target, srcs, len(out))
        return out
    except Exception:
        return ""   # recall must never brick the agent


def _in_scope(data, command: str, path: str) -> bool:
    """Belt only -- .cursor/hooks.json is project config, so events are this-repo by
    construction; this protects against the config being copied elsewhere."""
    from agent.harness.scope import file_in_scope, shell_in_scope
    if path:
        return file_in_scope(path)
    return shell_in_scope(data.get("cwd") or os.getenv("CURSOR_PROJECT_DIR") or os.getcwd(),
                          command)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label=_event(data))
    except Exception:
        pass
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return 0
    command, path = _fields(data)
    sid = str(data.get("conversation_id") or data.get("session_id") or "")
    try:
        if not _in_scope(data, command, path):
            return 0
        from core.recall.at_action import normalize_target, resolve_action_outcome, build_learn_nudge
        target = normalize_target(path or None, command or None)
        if not target:
            return 0
        if "failure" in _event(data).lower():
            resolve_action_outcome(sid, target, False)
            ctx = _recall_block(sid, path, command)
            if ctx:
                _emit_context(ctx)
            return 0
        rep = resolve_action_outcome(sid, target, True)
        if rep.get("flipped"):
            try:   # durable funnel signal (flips observed vs lessons recorded) -- best-effort
                from core.events.event_log import capture_event
                capture_event("flip", f"FAIL->SUCCESS: {target}",
                              agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
                              detail={"target": target, "credited": rep.get("credited", 0),
                                      "sources": rep.get("sources", [])})
            except Exception:
                pass
            from agent.harness.nudge import nudge_allowed, mark_nudged
            if nudge_allowed(_NUDGE_DIR, sid, target):
                _emit_context(build_learn_nudge(target, rep.get("credited", 0), rep.get("sources"),
                                                os.getenv("AKASHIC_AGENT_ID")))
                mark_nudged(_NUDGE_DIR, sid, target)
        else:
            ctx = _recall_block(sid, path, command)
            if ctx:
                _emit_context(ctx)
    except Exception:
        pass   # credit/recall must never affect the agent
    return 0


if __name__ == "__main__":
    sys.exit(main())
