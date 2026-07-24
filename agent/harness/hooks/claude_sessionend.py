#!/usr/bin/env python3
"""Claude Code SessionEnd / PreCompact hook -> auto-draft a where-we-are from the session's activity,
and (SessionEnd only) fold the session transcript into ONE durable `session_signals` event.

Wire it in .claude/settings.json for BOTH events (PreCompact is the high-value one -- it fires right
before context is compacted away, the main "lost where-we-are" moment):
  {"hooks":{"PreCompact":[{"hooks":[{"type":"command","command":"py agent/harness/hooks/claude_sessionend.py"}]}],
            "SessionEnd":[{"hooks":[{"type":"command","command":"py agent/harness/hooks/claude_sessionend.py"}]}]}}

DRAFT (both events): distills the session's own commits + lessons + notes into
chronicles/last-session-draft.md (a DRAFT FILE, not a note -- so it never clutters the curated
substrate or passes off an unreviewed activity list as truth). `boot` surfaces a one-line pointer;
promote it with `py agent_cli.py wrap --commit` only if it's worth keeping.

SESSION SIGNALS (SessionEnd only; RENEW slice A''): the transcript records EVERY tool call --
including Read/Grep and failures, which the PostToolUse hook never sees -- so the signal fold
happens HERE, once, off the hot path (zero per-call cost; the two-birds recorder lesson). Pairing
logic mirrors claude_posttooluse.py's transcript synthesis: tool_use blocks join tool_result blocks
by tool_use_id; is_error is the failure marker; un-resulted calls are dropped. Targets use the SAME
normalize_target() as the `fail`/`flip` labels so the correlation join is exact. Scope-guarded
(repo/home sessions only), watermarked per session (re-emits ONLY if the call count grew -- a
resumed session that ends again updates rather than duplicates; consumers keep the newest event
per session_id). Kill switch: AKASHIC_SESSION_SIGNALS=0.

Silent + fail-OPEN throughout: a capture must never block the session ending.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# State root shared with the other claude hooks (honors AKASHIC_RECALL_STATE_DIR for test isolation).
_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_SIG_DIR = os.path.join(_STATE_ROOT, "session_signals")

# Bounded read: signals fold over at most this much transcript tail. A session that overflows it
# gets `window_truncated: true` in the event (honest bound, never a silent cap).
_MAX_BYTES = int(os.getenv("AKASHIC_SESSION_SIGNALS_MAX_BYTES", str(16 * 1024 * 1024)))

_FILE_TOOLS = ("Read", "Edit", "Write", "NotebookEdit")
_SHELL_TOOLS = ("Bash", "PowerShell")


def _tail_lines(path: str, max_bytes: int):
    """Last <= max_bytes of complete lines (drops a partial first line after a seek), plus a
    truncation flag. Same shape as claude_posttooluse._tail_lines; must never throw."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        start = max(0, size - max_bytes)
        f.seek(start)
        blob = f.read()
    truncated = start > 0
    if truncated:
        nl = blob.find(b"\n")
        blob = blob[nl + 1:] if nl >= 0 else b""
    return [raw.decode("utf-8", errors="ignore") for raw in blob.splitlines()], truncated


def parse_transcript_calls(transcript_path: str):
    """Transcript JSONL -> (ordered call list for core.renew.session_signals.fold_signals,
    window_truncated). Pins the live payload shape (tests/fixtures/claude_payloads/): tool_use
    blocks in assistant records carry {id, name, input}; tool_result blocks in user records carry
    {tool_use_id, is_error}. Calls without a result (e.g. interrupted) are dropped."""
    from core.recall.at_action import normalize_target
    lines, truncated = _tail_lines(transcript_path, _MAX_BYTES)
    order = []          # tool_use ids in appearance order
    uses = {}           # id -> {"tool", "target", "at"}
    results = {}        # id -> ok(bool)
    for line in lines:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        ts = rec.get("timestamp") or ""
        for b in content:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt == "tool_use" and b.get("id"):
                inp = b.get("input") or {}
                name = str(b.get("name") or "")
                if name in _FILE_TOOLS:
                    target = normalize_target(inp.get("file_path") or None, None)
                elif name in _SHELL_TOOLS:
                    target = normalize_target(None, inp.get("command") or None)
                else:
                    target = ""
                order.append(b["id"])
                uses[b["id"]] = {"tool": name, "target": target, "at": ts}
            elif bt == "tool_result" and b.get("tool_use_id") in uses:
                results[b["tool_use_id"]] = (b.get("is_error") is not True)
    calls = [{**uses[i], "ok": results[i]} for i in order if i in results]
    return calls, truncated


def _already_emitted_calls(session_id: str) -> int:
    """Watermark: how many calls the last emission for this session covered (-1 = never)."""
    try:
        with open(os.path.join(_SIG_DIR, _safe(session_id) + ".json"), encoding="utf-8") as f:
            return int(json.load(f).get("calls", -1))
    except Exception:
        return -1


def _mark_emitted(session_id: str, calls: int) -> None:
    try:
        os.makedirs(_SIG_DIR, exist_ok=True)
        with open(os.path.join(_SIG_DIR, _safe(session_id) + ".json"), "w", encoding="utf-8") as f:
            json.dump({"calls": calls}, f)
    except Exception:
        pass


def _safe(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


def emit_session_signals(data) -> None:
    """Fold + capture the durable `session_signals` event (SessionEnd only; see module docstring)."""
    if os.getenv("AKASHIC_SESSION_SIGNALS", "1") == "0":
        return
    if (data.get("hook_event_name") or "") != "SessionEnd":
        return   # PreCompact mid-session partials would double-count; the final fold covers all
    try:
        from agent.harness.scope import session_in_scope
        if not session_in_scope(data.get("cwd") or os.getcwd()):
            return
        transcript = data.get("transcript_path") or ""
        sid = data.get("session_id") or ""
        if not transcript or not os.path.exists(transcript):
            return
        calls, truncated = parse_transcript_calls(transcript)
        if not calls or len(calls) <= _already_emitted_calls(sid):
            return   # nothing new since the last emission for this session
        from core.renew.session_signals import fold_signals
        signals = fold_signals(calls)
        signals["window_truncated"] = truncated
        try:   # recall economy for the same session (vNext loop 3): one dataset serves both pillars
            from core.recall.at_action import session_recall_summary
            signals["recall"] = session_recall_summary(sid)
        except Exception:
            pass
        from core.events.event_log import capture_event
        capture_event(
            "session_signals",
            f"SESSION SIGNALS: {signals['total_calls']} calls, {signals['fail_count']} fails, "
            f"{signals['progress_count']} progress",
            agent_id=os.getenv("AKASHIC_AGENT_ID") or "unknown",
            session_id=sid, detail=signals)
        _mark_emitted(sid, len(calls))
    except Exception:
        pass   # signal capture is best-effort; never block the end


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        import agent_cli
        from core.learning.agent_memory import get_agent_memory
        commits = agent_cli._recent_commits(24)
        lessons = agent_cli._recent_lessons(8)
        notes = get_agent_memory().get_decisions(days=1)
        try:   # FAIL->SUCCESS flips -> pre-filled candidate lessons in the draft (friction audit D5)
            from core.recall.at_action import recent_flips, recent_injections
            flips = recent_flips(24)
            injections = recent_injections(24)   # -> RECALL REVIEW + corpus gaps (vNext loop 3/4)
        except Exception:
            flips, injections = [], []
        agent_cli.write_last_session_draft(
            agent_cli.last_session_draft_path(), commits, lessons, notes,
            trigger=str(data.get("hook_event_name") or "session end"), flips=flips,
            injections=injections)
    except Exception:
        pass   # auto-capture is best-effort; never block the end
    emit_session_signals(data)
    try:   # T081-W8: close the open episode at SESSION END so it never dangles across sessions
        #    (the 189h 'Untitled episode'). SessionEnd only -- PreCompact is mid-session, still live.
        if (data.get("hook_event_name") or "") == "SessionEnd":
            from core.narrative.episode import close_open_episode_for_session_end
            close_open_episode_for_session_end()
    except Exception:
        pass   # bookend close is best-effort; never block the end
    try:   # T075 M1-beta clean-death trio (seat + card + listener); event guard +
        #    kill switch live INSIDE clean_death -- PreCompact passes through as a no-op.
        from core.comm.session_exit import clean_death
        clean_death(os.getenv("AKASHIC_AGENT_ID") or "claude",
                    str(data.get("session_id") or ""),
                    event=str(data.get("hook_event_name") or ""))
    except Exception:
        pass   # the trio is best-effort; never block the end
    return 0


if __name__ == "__main__":
    sys.exit(main())
