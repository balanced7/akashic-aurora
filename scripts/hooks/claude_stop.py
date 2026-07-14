"""Stop hook: keep THIS Claude session wakeable from idle + audit the turn's ending.

Fires when the turn ends. Two independent, independently-latched checks:

1. WAKE (original): if no bifrost.wake listener (scripts/bifrost_wake.py) is armed for this
   agent, BLOCK the stop and tell the model to re-arm -- turning "always wakeable" from fragile
   discipline into a harness-enforced invariant ("the environment decides" applied to Claude's
   own idling). The listener writes a PID heartbeat; this hook checks that PID is alive.
   Loop-guarded (won't block twice within 25s).

2. PROMISE (first-party fold-in 2026-07-08): if the turn's FINAL paragraph reads as a promise
   of future work ("I'll ...", "Next I'll ...") rather than an outcome, bounce ONCE per session
   with a teaching reason -- the last-paragraph check from the frontier harness, ported to the
   stop boundary we already own. High-precision patterns only; paragraphs that ask the user a
   question, condition on the user ("once you...", "say the word"), or announce a STOP in
   future-tense grammar ("I'll wait for your review") are legitimate endings and never bounced.
   Scoped to Akashic sessions (agent.harness.scope), kill switch AKASHIC_STOP_PROMISE=0.

Ordering + precision contract (made explicit after DeepSeek's 2026-07-08 review): at most ONE
block per stop attempt -- wake precedes promise, so an unarmed session hears about the promise
only on its NEXT stop (self-correcting across turns, never a wedge). And grammar-level matching
has a precision ceiling: past the opener/carve-out lists, false positives and negatives differ
only in INTENT, which a regex cannot see -- the chosen mitigation is the once-per-session latch
bounding any misfire to a single nudge, NOT an ever-growing stopword list.

Both checks fail OPEN (never wedge the session).
"""
import json, os, re, subprocess, sys, tempfile, time

AGENT = os.environ.get("AKASHIC_AGENT_ID", "claude")
HEARTBEAT = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}.pid")   # legacy (no session id)
MARKER = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_stophook.ts")
PROMISE_LATCH = os.path.join(tempfile.gettempdir(), f"claude_stop_promise_{AGENT}.sid")


def _seat_path(session_id: str) -> str:
    """Per-SESSION wake seat (T029 Wave 2): concurrent sessions of one agent id each arm
    their own watcher; nobody satisfies this check with another session's seat. Falls back
    to the legacy per-agent path when the payload carries no session id."""
    if session_id:
        return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_{session_id}.pid")
    return HEARTBEAT


def _loop_guard_path(session_id: str) -> str:
    """The 25s block-throttle latch -- session-scoped so twin sessions don't eat each
    other's block window (pre-Wave-2 they shared one file)."""
    if session_id:
        return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_{session_id}_stophook.ts")
    return MARKER


def _touch_activity(session_id: str) -> None:
    """Every stop-hook firing stamps the session ALIVE -- the janitor's cheap liveness fast
    path (K7). Turn cadence alone never proves death; this marker only ever proves LIFE."""
    if not session_id:
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from core.comm import wake_seat
        wake_seat.touch_activity(AGENT, session_id)
    except Exception:
        pass

# High-precision promise openers only -- a false bounce teaches the model to distrust the hook.
# Matched at the start of the (bullet/emphasis-stripped, lowercased) final paragraph.
PROMISE_OPENERS = re.compile(
    r"^(i'll |i will |now i'll |next,? i'll |let me now |i'm going to |i am going to )", re.I)
# A final paragraph that hands the turn to the USER is a legitimate ending, never a promise.
USER_CONDITIONAL = ("if you", "when you", "once you", "whenever you", "say the word",
                    "let me know", "your call", "want me to", "shall i", "should i")
# "I'll <stop-verb>" is an outcome statement in future-tense clothing ("I'll wait for your
# review"), not a promise of work (DeepSeek review finding 1). Tight list on purpose --
# ambiguous verbs (keep/stay/watch) stay OUT so "I'll keep working" still bounces.
STOP_VERBS = {"wait", "pause", "stop", "hold", "defer", "stand", "leave", "yield", "idle"}
_OPENER_VERB = re.compile(
    r"^(?:i'll|i will|now i'll|next,? i'll|let me now|i'm going to|i am going to)\s+([a-z']+)", re.I)


def final_paragraph(text: str) -> str:
    """Last non-empty prose block of the message ('' when none). Trailing code fences are not
    prose -- keep walking up."""
    for block in reversed(re.split(r"\n\s*\n", text or "")):
        p = block.strip()
        if not p or p.startswith("```"):
            continue
        return p
    return ""


def promise_shaped(paragraph: str):
    """The matched excerpt when the paragraph is a promise of future work, else None. PURE."""
    p = (paragraph or "").strip()
    if not p or p.endswith("?"):
        return None            # a question hands the turn to the user -- legitimate ending
    low = p.lower()
    if any(k in low for k in USER_CONDITIONAL):
        return None            # user-conditional ending ("once you approve, I'll...") -- legitimate
    norm = re.sub(r"^[\s>*\-\d.]+", "", low)   # strip list bullets / numbering / emphasis prefixes
    if PROMISE_OPENERS.match(norm):
        m = _OPENER_VERB.match(norm)
        if m and m.group(1) in STOP_VERBS:
            return None        # "I'll wait/pause/stop..." announces an ending, not future work
        return p[:120]
    return None


def last_assistant_text(transcript_path: str, tail_bytes: int = 400_000) -> str:
    """Final assistant text message from a Claude Code transcript JSONL ('' on any failure)."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            if size > tail_bytes:
                f.seek(size - tail_bytes)
            raw = f.read().decode("utf-8", "replace")
    except Exception:
        return ""
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue               # the first line after a mid-file seek may be partial
        if e.get("type") != "assistant":
            continue
        msg = e.get("message") or {}
        parts = [b.get("text", "") for b in (msg.get("content") or [])
                 if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        if text:
            return text
    return ""


def _pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True, timeout=6).stdout
        return str(pid) in out
    except Exception:
        return True  # fail-open: on detection error, assume alive (don't wedge the session)


def wake_armed(session_id: str = ""):
    try:
        pid = int(open(_seat_path(session_id)).read().strip())
    except Exception:
        return False
    return _pid_alive(pid)


def _promise_block(payload: dict):
    """Blocking reason for a promise-shaped ending, or None. Once per session; fail-open."""
    if os.getenv("AKASHIC_STOP_PROMISE", "1") == "0":
        return None
    session_id = str(payload.get("session_id") or "")
    transcript = payload.get("transcript_path") or ""
    if not session_id or not transcript:
        return None
    try:   # scope to Akashic sessions -- an unrelated project never gets bounced
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from agent.harness.scope import session_in_scope
        if not session_in_scope(payload.get("cwd") or os.getcwd()):
            return None
    except Exception:
        return None
    try:
        if open(PROMISE_LATCH).read().strip() == session_id:
            return None        # already bounced this session -- once is a nudge, twice is a wedge
    except Exception:
        pass
    excerpt = promise_shaped(final_paragraph(last_assistant_text(transcript)))
    if not excerpt:
        return None
    try:
        open(PROMISE_LATCH, "w").write(session_id)
    except Exception:
        pass
    return (f"Turn-ending check: your final paragraph reads as a promise of future work "
            f"(\"{excerpt}...\"). Do that work NOW with tool calls, or end on the outcome and "
            "state plainly why you are stopping (task complete / blocked on the user). "
            "This check fires once per session.")


def main():
    try:
        payload = json.loads(sys.stdin.read().lstrip("﻿"))   # BOM-tolerant (PS pipes)
    except Exception as e:
        # fail-open for the agent, never silent for the operator (the 2026-07-02 lesson)
        print(f"[stop-hook] stdin unparseable: {type(e).__name__}: {e}", file=sys.stderr)
        payload = {}
    session_id = str(payload.get("session_id") or "")
    _touch_activity(session_id)          # stamp ALIVE on every firing -- K7 fast path
    if session_id:
        try:                             # RB-21: keep the consumer seat alive while the
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from core.comm import runner_lock   # session is (heartbeat refuses foreign
            runner_lock.refresh_consumer(AGENT, f"session:{session_id}")   # tokens -> safe no-op)
        except Exception:
            pass
    if not wake_armed(session_id):
        # T050 Q6 (the arm-vs-hook race): a JUST-launched watcher needs ~1-2s of python+import
        # startup before its seat exists -- five false blocks on 2026-07-13/14 were this race,
        # each spawning a redundant watcher into newest-wins churn. One grace recheck.
        time.sleep(1.5)
    if not wake_armed(session_id):
        guard = _loop_guard_path(session_id)
        now = time.time()
        try:
            last = float(open(guard).read().strip())
        except Exception:
            last = 0.0
        if now - last >= 25:   # loop guard: never block twice within 25s
            try:
                open(guard, "w").write(str(now))
            except Exception:
                pass
            arm_cmd = f"py scripts/bifrost_wake.py --agent {AGENT}" + (
                f" --session {session_id}" if session_id else "")
            print(json.dumps({"decision": "block", "reason": (
                f"No bifrost.wake listener is armed for '{AGENT}' -- this session is not wakeable from idle "
                f"(DeepSeek/Daniel can't reach you). Re-arm it before stopping: launch "
                f"`{arm_cmd}` as a run_in_background task (so it's harness-"
                "tracked and its completion re-invokes you). Then stop.")}))
            return
    try:
        reason = _promise_block(payload)
    except Exception:
        reason = None          # fail-open: the audit must never wedge the session
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
