"""claude_browser_guard.py -- PreToolUse deny for GPU-heavy pages in the EMBEDDED browser.

THE RECEIPT (2026-08-12 23:33:48, codex investigation): a subagent opened Shadertoy in the
embedded Browser/preview pane; the Electron GPU child died 6.192s later and took the whole
app with it -- the zombie main process kept the single-instance lock plus 53 open AppX
handles, so every relaunch quit instantly ("bricked"), repair failed, and the forced
reinstall erased main.log AND restarted the MCP door onto a different interpreter (the
2026-08-13 ask-verb outage). Second occurrence: 2026-08-01 (21MB prime session lost).
Lesson: claude_embedded_preview_crash_trigger_2026_08_12.

SCOPE: the EMBEDDED surface only (mcp__Claude_Browser__navigate / preview_start). The
claude-in-chrome tools drive Daniil's real Chrome -- a GPU crash there kills a Chrome tab,
not the app. Deny is BY URL, fail-open on any parse trouble: a guard that wedges an
unrelated preview costs more trust than it saves.
"""
import json
import re
import sys

BLOCK = re.compile(
    r"shadertoy\.com|glslsandbox\.com|vertexshaderart\.com|shdr\.bkcore\.com"
    r"|webglsamples\.org|threejs\.org/examples|playground\.babylonjs\.com"
    r"|webglreport\.com|chrome://gpu",
    re.I)


def main():
    try:
        payload = json.loads(sys.stdin.read().lstrip("﻿"))
    except Exception:
        return                             # fail-open: never wedge on bad stdin
    ti = payload.get("tool_input") or {}
    url = str(ti.get("url") or "") if isinstance(ti, dict) else ""
    if url and BLOCK.search(url):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "BLOCKED: GPU-heavy page in the EMBEDDED browser. Receipt 2026-08-12: "
                "Shadertoy in the preview pane killed the Electron GPU child and bricked "
                "the whole app (zombie process, forced reinstall, session lost -- twice "
                "now). Read the page with WebFetch, or use the claude-in-chrome tools "
                "(real Chrome: a crash there costs a tab, not the app). Lesson: "
                "claude_embedded_preview_crash_trigger_2026_08_12")}}))


if __name__ == "__main__":
    main()
