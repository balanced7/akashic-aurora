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
   question or condition on the user ("once you...", "say the word") are legitimate endings and
   never bounced. Scoped to Akashic sessions (agent.harness.scope), kill switch
   AKASHIC_STOP_PROMISE=0.

Both checks fail OPEN (never wedge the session).
"""
import json, os, re, subprocess, sys, tempfile, time

AGENT = os.environ.get("AKASHIC_AGENT_ID", "claude")
HEARTBEAT = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}.pid")
MARKER = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_stophook.ts")
PROMISE_LATCH = os.path.join(tempfile.gettempdir(), f"claude_stop_promise_{AGENT}.sid")

# High-precision promise openers only -- a false bounce teaches the model to distrust the hook.
# Matched at the start of the (bullet/emphasis-stripped, lowercased) final paragraph.
PROMISE_OPENERS = re.compile(
    r"^(i'll |i will |now i'll |next,? i'll |let me now |i'm going to |i am going to )", re.I)
# A final paragraph that hands the turn to the USER is a legitimate ending, never a promise.
USER_CONDITIONAL = ("if you", "when you", "once you", "whenever you", "say the word",
                    "let me know", "your call", "want me to", "shall i", "should i")


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


def wake_armed():
    try:
        pid = int(open(HEARTBEAT).read().strip())
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
    if not wake_armed():
        now = time.time()
        try:
            last = float(open(MARKER).read().strip())
        except Exception:
            last = 0.0
        if now - last >= 25:   # loop guard: never block twice within 25s
            try:
                open(MARKER, "w").write(str(now))
            except Exception:
                pass
            print(json.dumps({"decision": "block", "reason": (
                f"No bifrost.wake listener is armed for '{AGENT}' -- this session is not wakeable from idle "
                f"(DeepSeek/Daniel can't reach you). Re-arm it before stopping: launch "
                f"`py scripts/bifrost_wake.py --agent {AGENT}` as a run_in_background task (so it's harness-"
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
