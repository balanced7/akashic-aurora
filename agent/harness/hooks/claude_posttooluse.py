#!/usr/bin/env python3
"""Claude Code PostToolUse hook -> resolve the recall-at-action implicit-useful signal.

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PostToolUse":[{"matcher":"Bash|PowerShell|Edit|Write|NotebookEdit","hooks":[
    {"type":"command","command":"py agent/harness/hooks/claude_posttooluse.py"}]}]}}
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
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

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


# --- RENEW Strand A' (label capture): a tool action that FAILED (and is being retried) is a REWORK
# event -- the durable degraded-output GROUND TRUTH a context-health estimator must correlate against.
# The FAIL->SUCCESS flip was already durable, but it measures RECALL utility and clusters in the most
# productive sessions (Strand A finding, 2026-07-07); the FAIL half -- the actual degraded-output
# signal -- was computed here then discarded. Emitted exactly once per failure (gated by the same
# tool_use_id watermark as the resolve). Best-effort + fail-soft: a label capture must never affect
# the action. See docs/library/report/20260707_renew-strand-a-cheap-deterministic-conte_6eba11.md.
def _capture_fail(target: str, tool: str) -> None:
    try:
        from core.events.event_log import capture_event
        capture_event("fail", f"FAIL: {target}",
                      agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
                      detail={"target": target, "tool": tool})
    except Exception:
        pass


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


# --- S2 seat liveness: every tool action ticks this seat's worklive key.
# WHY THIS EXISTS: roster.heartbeat had exactly ONE production caller (agent/bifrost_pull.py --
# boot, manual sync, SessionStart, UserPromptSubmit), so a seat working continuously inside one
# turn read DEAD after WORKLIVE_TTL_S=180. The reaper, the bus UNATTENDED RECIPIENT warning and
# doctor's "genuinely working" retraction all consume that sensor as truth. Measured 2026-08-01:
# 89 seats, ZERO live -- including the seat taking the measurement.
# WHY IT SITS ABOVE EVERY GATE IN main(): the recall kill switch, the Task branch, the tool
# filter and _in_scope() each return early. _in_scope is TARGET-scoped -- for a shell tool it is
# true only when cwd is under the repo or the command text names it -- so a home-rooted seat
# working on non-repo paths would miss it. That is precisely the seat that goes DEAD, which
# would make the failure CORRELATED with the thing being measured, and silent.
# Pinned UNPATCHED by tests/test_seat_heartbeat_wiring.py (W1/W2/W2b/W3/W4).
def _beat_seat(data) -> None:
    """Beat this seat's liveness. SESSION-scoped (not target-scoped), own kill switch, never
    raises, and NEVER guesses an identity -- a phantom row is worse than a missing one, and this
    fleet has already rendered one physical session as two seats under two different names."""
    if os.getenv("AKASHIC_SEAT_HEARTBEAT", "1") == "0":
        return
    try:
        from agent.harness.scope import session_in_scope
        d = data or {}
        if not session_in_scope(d.get("cwd") or os.getcwd()):
            return
        # PAYLOAD FIRST, env only as fallback. The payload's session_id is the ground truth for
        # WHICH SESSION made this tool call; the environment is merely ambient and can be
        # inherited from a parent or a sibling. Env-first was the original shape here and the
        # unpatched pin caught it attributing one session's action to another live session --
        # the same wrong-attribution class that already rendered one physical session as two
        # roster rows under two names. A beat that names the wrong seat is worse than no beat:
        # it marks a corpse alive and leaves the real worker reapable.
        sid = (str(d.get("session_id") or "")
               or os.environ.get("BIFROST_INCARNATION")
               or os.environ.get("CLAUDE_CODE_SESSION_ID") or "").strip()
        if not sid:
            return
        # AGENT AXIS, the other half of the same bug. The payload-first fix above settled WHICH
        # SESSION; this settles WHICH SEAT. Env-only resolution beat every session under
        # AKASHIC_AGENT_ID (default "claude"), so a correctly-named seat stayed DEAD while its
        # own tool calls beat the conductor's row -- one physical session, two rows, and the
        # row carrying the real worker's name was the reapable one. Measured live before this
        # fix: claude#6ac75463 LIVE 1.1s / opus-engineer#6ac75463 DEAD 13020s, same session.
        # W4 IS PRESERVED DELIBERATELY: when nothing is bound and no env is set the identity is
        # genuinely unknown, and we still emit NO ROW rather than a phantom -- a beat naming
        # unknown-<sid8> would be honest but would still invent a seat.
        from core.comm.seat_identity import resolve as _resolve, resolved_from as _resolved_from
        if _resolved_from(sid) == "unknown":
            return
        agent = _resolve(sid)
        from core.comm import roster as _roster
        from core.comm.bus import NS as _DEFAULT_NS
        # CAPTURE THE RETURN. heartbeat() never raises -- it swallows internally and returns
        # {"ok": False} (roster.py:153-154). bus._connect() returns None when Redis is
        # unreachable, so the most likely production failure is a caught AttributeError inside
        # heartbeat, not an exception out here. Discarding this value made the receipt below
        # unable to fire for exactly that case: exit 0, empty log, no row -- byte-identical to
        # the no-op this whole slice exists to end. Found by the audit's critic pass.
        _r = _roster.heartbeat(os.environ.get("BIFROST_NAMESPACE", _DEFAULT_NS),
                               agent, sid, phase="working")
        if _r is False or (isinstance(_r, dict) and not _r.get("ok", True)):
            raise RuntimeError(f"heartbeat refused: {_r!r} (seat {agent}#{sid[:8]})")
    except Exception as e:
        # A sensor must never break the action it observes. But a SILENT swallow is exactly what
        # made today's other no-op invisible, so leave a bounded receipt: the unpatched pin
        # catches absence in CI, this catches it at 3am in production.
        try:
            with open(os.path.join(tempfile.gettempdir(), "akashic_heartbeat_err.log"), "a",
                      encoding="utf-8") as fh:
                fh.write(f"{time.time():.0f} {type(e).__name__}: {e}\n")
        except Exception:
            pass


def main() -> int:
    # stdin first, then BEAT, then every pre-existing gate -- liveness must not be a hostage of
    # the recall feature's kill switch (a seat that turns recall off must not become invisible
    # to the reaper).
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    _beat_seat(data)
    # THE TOOL IS DONE, SO THE MODEL IS COMPOSING AGAIN. Placed beside _beat_seat and above every
    # gate below for the same reason liveness is: presence must not be a hostage of the recall
    # feature's kill switch. A seat that turns recall off must still show as working.
    try:
        from agent.harness.hooks._activity import report
        report("thinking", "", data.get("cwd") or "")
    except Exception:
        pass
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return 0
    if not data:
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
                fid = data.get("tool_use_id")
                fresh = not (fid and _failure_processed(sid, target, fid))
                resolve_action_outcome(sid, target, False)
                if fresh:
                    _capture_fail(target, tool)   # durable degraded-output label (RENEW A'), exactly-once
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
                _capture_fail(target, tool)       # durable degraded-output label (RENEW A'), exactly-once
                _mark_failure_processed(sid, target, fid)
        rep = resolve_action_outcome(sid, target, ok)
        if rep.get("flipped"):
            try:   # durable funnel signal (flips observed vs lessons recorded) -- best-effort
                from core.events.event_log import capture_event
                # F0b: carry the full retrieval context with the credit (this event is the
                # Forge gate's axis-A validation set; at ~5/week the enrichment is free).
                # alt is "action" by construction: plan-time impressions open no action
                # target, so only action-altitude surfacings can ever credit.
                q = ""
                try:
                    from core.recall.at_action import _query_from
                    from core.recall.replay import parse_target
                    p, c = parse_target(target)
                    q = _query_from(p, c) if (p or c) else ""
                except Exception:
                    q = ""
                capture_event("flip", f"FAIL->SUCCESS: {target}",
                              agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
                              detail={"target": target, "credited": rep.get("credited", 0),
                                      "sources": rep.get("sources", []),
                                      "alt": "action", "query": q})
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
