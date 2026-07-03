#!/usr/bin/env python3
"""Claude Code PostToolUse hook -> resolve the recall-at-action implicit-useful signal.

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PostToolUse":[{"matcher":"Bash|PowerShell|Edit|Write|NotebookEdit","hooks":[
    {"type":"command","command":"py scripts/hooks/claude_posttooluse.py"}]}]}}
Or user-level with an ABSOLUTE path (same as the PreToolUse hook).

PowerShell is the harness's PRIMARY shell tool on Windows; treat it exactly like Bash (its
tool_input carries the same `command` field). Its tool_response SHAPE has no pinned fixture yet
-- _is_success stays conservative (an event arriving at all means success; see below), and the
auto-capture will grab real PowerShell payloads to pin in tests/fixtures/claude_payloads/.

After a tool runs, if the target (file path / command) JUST FAILED and now SUCCEEDS, the lessons
recall surfaced for it are credited 'helped' -- the contrastive auto-positive (a first-try success
credits nothing). Scope-guarded to this repo, fail-OPEN, side-effect-only (the action already ran).

PAYLOAD GROUND TRUTH (captured live 2026-07-01; fixtures in tests/fixtures/claude_payloads/):
Claude Code fires PostToolUse ONLY for SUCCESSFUL tool calls. A failing Bash (nonzero exit) or a
failed Edit produces NO hook event at all, and success payloads carry NO error/exit markers
(Bash tool_response = {stdout, stderr, interrupted, isImage, noOutputExpected}). So the FAIL half
of the flip can never arrive as a hook event -- it is SYNTHESIZED from the session transcript
(`transcript_path` in the payload), where every tool_result INCLUDING failures is recorded with
is_error + tool_use_id. Each failure is processed once (per-session watermark by the failure's
tool_use_id), then handed to the engine as resolve_outcome(False) BEFORE the current success, so
core/recall's contrastive gate sees FAIL->SUCCESS exactly as designed. Harness-specific transcript
parsing lives in THIS adapter on purpose -- core/recall stays harness-agnostic.

COMPLEMENTARY FAST PATH: current Claude Code also ships a PostToolUseFailure event (register this
same script for it). When it fires, the FAIL is recorded immediately + watermarked. It is NOT
sufficient alone: per docs/issue #24908 it does not fire for tool_use_error failures of built-in
tools (e.g. Edit old_string-not-found -- confirmed live), so the transcript synthesis above stays
the primary, version-tolerant mechanism. Disable with AKASHIC_RECALL_AT_ACTION=0.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_FILE_TOOLS = ("Edit", "Write", "NotebookEdit")
_SHELL_TOOLS = ("Bash", "PowerShell")


def _in_scope(tool, data):
    """Silent no-op outside this repo (so a global registration is safe). Claude tool names ->
    the shared scope policy (agent/harness/scope.py), same mapping as the PreToolUse guard:
    file tools scope by target path, shell tools by session cwd or the command itself."""
    from agent.harness.scope import file_in_scope, shell_in_scope
    ti = data.get("tool_input") or {}
    if tool in _FILE_TOOLS:
        return file_in_scope(ti.get("file_path") or "")
    return shell_in_scope(data.get("cwd") or os.getcwd(), ti.get("command") or "")


# --- payload capture (agent/harness/capture.py): the ONLY ground truth for what tool_response
# actually looks like per harness version (the _is_success contract). Feeds tests/fixtures/
# claude_payloads/ so the contract test tracks the LIVE harness, not an assumption.
# State root honors AKASHIC_RECALL_STATE_DIR (test isolation; in sync with core/recall/at_action.py).
_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CAP_DIR = os.path.join(_STATE_ROOT, "payloads")


def _capture(data) -> None:
    try:
        from agent.harness.capture import capture
        capture(data, _CAP_DIR, label=data.get("tool_name") or "unknown")
    except Exception:
        pass   # capture is diagnostics; it must never affect the agent


def _is_success(data) -> bool:
    """Best-effort, CONSERVATIVE: only call it a failure on a clear marker; otherwise success.
    GROUND TRUTH: every event that reaches this hook IS a success (failures never fire PostToolUse),
    and real payloads carry none of the error markers below -- they are kept only as cheap
    future-proofing against harness changes. `interrupted` is the one real negative signal observed
    in live payloads: a user-aborted command must not count as the SUCCESS half of a flip."""
    tr = data.get("tool_response")
    if isinstance(tr, dict):
        if tr.get("is_error") is True or tr.get("error"):
            return False
        if tr.get("interrupted") is True:
            return False
        if "success" in tr:
            return bool(tr.get("success"))
        for k in ("exit_code", "exitCode", "returncode", "code"):
            if k in tr:
                try:
                    return int(tr[k]) == 0
                except Exception:
                    pass
    if isinstance(tr, str):
        low = tr.lower()
        if "traceback (most recent call last)" in low or "command not found" in low:
            return False
    return True


# --- transcript-derived FAIL synthesis: the hook never receives failure events, but the session
# transcript records every tool_result -- failures included -- as JSONL. At each (success) event we
# look for the NEWEST failed attempt of the SAME normalized target and, if not yet processed
# (per-session watermark keyed by the failure's tool_use_id), backfill resolve_outcome(False) so the
# engine's contrastive FAIL->SUCCESS gate fires exactly as designed. Bounded tail read, fail-soft.
_TAIL_BYTES = int(os.getenv("AKASHIC_TRANSCRIPT_TAIL_BYTES", str(4 * 1024 * 1024)))
_TXW_DIR = os.path.join(_STATE_ROOT, "txw")


def _tail_lines(path: str):
    """Yield the transcript's last <= _TAIL_BYTES worth of complete lines (drops a partial first line
    after a seek). Text lines, utf-8, errors ignored -- the parse must never throw."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        start = max(0, size - _TAIL_BYTES)
        f.seek(start)
        blob = f.read()
    if start > 0:
        nl = blob.find(b"\n")
        blob = blob[nl + 1:] if nl >= 0 else b""
    for raw in blob.splitlines():
        yield raw.decode("utf-8", errors="ignore")


def _latest_failure_id(transcript_path: str, target: str):
    """tool_use_id of the NEWEST failed (is_error) tool call whose normalized target == `target`,
    or None. Pairs assistant tool_use blocks (id -> target) with user tool_result blocks."""
    if not transcript_path or not target:
        return None
    try:
        from core.recall.at_action import normalize_target
        uses = {}
        latest = None
        for line in _tail_lines(transcript_path):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "tool_use":
                    inp = b.get("input") or {}
                    tgt = normalize_target(inp.get("file_path") or None, inp.get("command") or None)
                    if tgt:
                        uses[b.get("id")] = tgt
                elif bt == "tool_result" and b.get("is_error") is True:
                    if uses.get(b.get("tool_use_id")) == target:
                        latest = b.get("tool_use_id")
        return latest
    except Exception:
        return None


def _safe(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


# --- JIT learn nudge (friction audit D5): a FAIL->SUCCESS flip is the moment a lesson was just
# earned, so THAT is when we ask for it -- one small additionalContext block, silent otherwise.
# Rate limiting is the shared agent/harness/nudge.py (once per target, session cap, kill switch).
_NUDGE_DIR = os.path.join(_STATE_ROOT, "nudge")


def _nudge_allowed(session_id: str, target: str) -> bool:
    from agent.harness.nudge import nudge_allowed
    return nudge_allowed(_NUDGE_DIR, session_id, target)


def _mark_nudged(session_id: str, target: str) -> None:
    from agent.harness.nudge import mark_nudged
    mark_nudged(_NUDGE_DIR, session_id, target)


def _emit_context(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": text,
    }}))


def _txw_path(session_id: str) -> str:
    return os.path.join(_TXW_DIR, _safe(session_id) + ".json")


def _failure_processed(session_id: str, target: str, fid: str) -> bool:
    try:
        with open(_txw_path(session_id), encoding="utf-8") as f:
            return json.load(f).get(target) == fid
    except Exception:
        return False


def _mark_failure_processed(session_id: str, target: str, fid: str) -> None:
    try:
        os.makedirs(_TXW_DIR, exist_ok=True)
        p = _txw_path(session_id)
        d = {}
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        d[target] = fid
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


def main() -> int:
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name") or ""
    if tool == "Task":
        # Agent-result payloads: CAPTURE ONLY for now (payload-truth discipline -- the
        # auto-archive forcing function builds against pinned shapes, not assumptions).
        # Session-scoped: repo/home sessions only, so unrelated projects never land here.
        try:
            from agent.harness.scope import session_in_scope
            if session_in_scope(data.get("cwd") or os.getcwd()):
                _capture(data)
        except Exception:
            pass
        return 0
    if tool not in _SHELL_TOOLS + _FILE_TOOLS:
        return 0
    if not _in_scope(tool, data):
        return 0
    _capture(data)
    try:
        from core.recall.at_action import normalize_target, resolve_action_outcome, build_learn_nudge
        ti = data.get("tool_input") or {}
        target = normalize_target(ti.get("file_path") or None, ti.get("command") or None)
        sid = data.get("session_id") or ""
        if (data.get("hook_event_name") or "") == "PostToolUseFailure":
            # Direct failure signal (fast path; Bash/Write only per #24908). Record the FAIL now and
            # watermark its tool_use_id so the transcript scan never double-processes this failure.
            if target:
                resolve_action_outcome(sid, target, False)
                fid = data.get("tool_use_id")
                if fid:
                    _mark_failure_processed(sid, target, fid)
            return 0
        ok = _is_success(data)
        if ok and target:
            # Backfill the FAIL the hook never received (see module docstring), exactly once per
            # failure, BEFORE resolving the current success -- the engine then sees FAIL->SUCCESS.
            fid = _latest_failure_id(data.get("transcript_path") or "", target)
            if fid and not _failure_processed(sid, target, fid):
                resolve_action_outcome(sid, target, False)
                _mark_failure_processed(sid, target, fid)
        rep = resolve_action_outcome(sid, target, ok)
        if rep.get("flipped"):
            try:   # durable funnel signal (flips observed vs lessons recorded) -- best-effort
                from core.events.event_log import capture_event
                capture_event("flip", f"FAIL->SUCCESS: {target}",
                              agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
                              detail={"target": target, "credited": rep.get("credited", 0),
                                      "sources": rep.get("sources", [])})
            except Exception:
                pass
            # JIT learn nudge at the moment of insight (friction audit D5) -- rate-limited.
            if _nudge_allowed(sid, target):
                _emit_context(build_learn_nudge(target, rep.get("credited", 0), rep.get("sources"),
                                                os.getenv("AKASHIC_AGENT_ID")))
                _mark_nudged(sid, target)
    except Exception:
        pass   # resolving a credit must never affect the agent
    return 0


if __name__ == "__main__":
    sys.exit(main())
