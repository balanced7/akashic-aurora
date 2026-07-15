#!/usr/bin/env python3
"""Cursor `sessionStart` hook -> agent identity (T1) + light auto-boot whisper (T2).

Pinned from the live Cursor hooks docs (cursor.com/docs/agent/hooks, fetched 2026-07-02):
sessionStart may return {"env": {...}, "additional_context": "..."} and the env vars
PROPAGATE to every later hook in the session -- so identity and the session cue ship in
ONE hook. (beforeSubmitPrompt cannot inject, so Cursor has no plan-time altitude; see
docs/integration-tiers.md.)

Identity: AKASHIC_AGENT_ID defaults to "composer" (the Cursor peer's id); an explicitly
set env wins. The whisper is agent/harness/context.py -- the same text every harness
speaks. Payload capture comes FIRST (payload-truth discipline): the exact sessionStart
shape has no pinned fixture yet, so field reads are defensive until H2 pins captures
from %TEMP%/akashic_recall/payloads_cursor/ into tests/fixtures/cursor_payloads/.
Fail-OPEN and silent on any error -- session start must never be delayed or broken.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CAP_DIR = os.path.join(_STATE_ROOT, "payloads_cursor")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label="sessionStart")
    except Exception:
        pass
    try:
        from core.recall.at_action import warm_cache, prune_state
        warm_cache()
        prune_state()
    except Exception:
        pass   # warm-up is best-effort; never block session start
    agent_id = os.getenv("AKASHIC_AGENT_ID") or "composer"
    out = {"env": {"AKASHIC_AGENT_ID": agent_id}}
    try:
        from agent.harness.context import build_autoboot_context
        cwd = (data.get("cwd") or data.get("workspace_root")
               or os.getenv("CURSOR_PROJECT_DIR") or os.getcwd())
        ctx = build_autoboot_context(cwd, agent_id,
                                     session_id=str(data.get("session_id")
                                                    or data.get("conversation_id") or ""))
        if ctx:
            out["additional_context"] = ctx
    except Exception:
        pass   # the whisper is a bonus; identity still ships
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
