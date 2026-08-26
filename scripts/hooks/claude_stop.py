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

# LEGACY, no-session paths only (below). Session-scoped paths resolve via _seat().
# Default is NOT a peer name: a session with no env previously wrote bifrost_wake_claude.pid
# on a SHARED path, i.e. it impersonated the conductor on disk. Unknown is honest and unshared.
AGENT = os.environ.get("AKASHIC_AGENT_ID", "").strip() or "unknown"
HEARTBEAT = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}.pid")   # legacy (no session id)
MARKER = os.path.join(tempfile.gettempdir(), f"bifrost_wake_{AGENT}_stophook.ts")
PROMISE_LATCH = os.path.join(tempfile.gettempdir(), f"claude_stop_promise_{AGENT}.sid")


def _seat(session_id: str = "") -> str:
    """Session-scoped seat identity: binding -> env -> loud unknown-<sid8>.

    AGENT (module-level, env-only) stays for the LEGACY no-session paths above, which have no
    session to key on. Every SESSION-SCOPED path resolves here instead -- that is what lets the
    wakeability check find a correctly-named seat's watcher rather than hunting for a
    claude-named one that will never exist and then prescribing a duplicate.
    """
    try:
        from core.comm.seat_identity import resolve
        return resolve(session_id)
    except Exception:
        return (os.environ.get("AKASHIC_AGENT_ID") or "").strip() or "unknown"

def _seat_path(session_id: str) -> str:
    """Per-SESSION wake seat (T029 Wave 2): concurrent sessions of one agent id each arm
    their own watcher; nobody satisfies this check with another session's seat. Falls back
    to the legacy per-agent path when the payload carries no session id."""
    if session_id:
        return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{_seat(session_id)}_{session_id}.pid")
    return HEARTBEAT


def _loop_guard_path(session_id: str) -> str:
    """The 25s block-throttle latch -- session-scoped so twin sessions don't eat each
    other's block window (pre-Wave-2 they shared one file)."""
    if session_id:
        return os.path.join(tempfile.gettempdir(), f"bifrost_wake_{_seat(session_id)}_{session_id}_stophook.ts")
    return MARKER


def _touch_activity(session_id: str) -> None:
    """Every stop-hook firing stamps the session ALIVE -- the janitor's cheap liveness fast
    path (K7). Turn cadence alone never proves death; this marker only ever proves LIFE."""
    if not session_id:
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from core.comm import wake_seat
        wake_seat.touch_activity(_seat(session_id), session_id)
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


def _rearm_trigger_fresh(session_id: str, max_age_s: float = 6 * 3600) -> bool:
    """A fresh .rearm trigger = the watcher CYCLED (planned, T073 P8), not died --
    the backstop message says so instead of crying wolf."""
    name = (f"bifrost_wake_{_seat(session_id)}_{session_id}.rearm" if session_id
            else f"bifrost_wake_{AGENT}.rearm")
    p = os.path.join(tempfile.gettempdir(), name)
    try:
        return os.path.isfile(p) and (time.time() - os.path.getmtime(p)) < max_age_s
    except Exception:
        return False


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


def _beat_idle(session_id: str) -> None:
    """Turn boundary: the seat is idle-ALIVE, not working. Closes the F5 false-page window.

    WHY: the PostToolUse heartbeat beats phase="working", and roster.heartbeat carries
    since_ts forward, so "working" persisted across the gaps BETWEEN turns while the beat
    went stale. doctor.py:378-391 pages hard_wedge on exactly that shape -- non-idle phase
    aged past DEFAULT_WEDGE_S with no fresh pulse -- so an ordinary thinking gap rendered as
    "worker died inside the turn". Measured live 2026-08-01: opus-engineer#6ac75463 paged
    HARD WEDGE at 608s while merely between turns, and was beating again (seq=52) minutes
    later. Before the per-action heartbeat existed this window could not open, because the
    worklive key simply expired; the pulse fix opened it. This closes it at the boundary
    rather than by loosening the detector, which would blind it to REAL wedges.

    IDLE_PHASES = {"idle","online","replied"} (liveness.py:84), so "idle" makes non_idle
    False and no wedge is computed. Identity resolves through seat_identity (B1) -- never
    guessed, and no row at all when unknown, per the W4 pin.
    """
    if os.getenv("AKASHIC_SEAT_HEARTBEAT", "1") == "0":
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        agent = _seat(session_id)
        if not agent or agent == "unknown" or not session_id:
            return
        from core.comm import roster as _roster
        from core.comm.bus import NS as _DEFAULT_NS
        _roster.heartbeat(os.environ.get("BIFROST_NAMESPACE", _DEFAULT_NS),
                          agent, session_id, phase="idle")
    except Exception:
        pass   # a liveness marker must never break the turn boundary


def _draft_keepalive() -> None:
    """Turn boundary: refresh chronicles/last-session-draft.md when stale (the organ
    agent/harness/draft_keepalive.py, wired 2026-08-26). Throttled 600s; never raises;
    kill switch AKASHIC_DRAFT_KEEPALIVE=0. A crash kills the next graceful hook -- this
    keeps the auto-handoff younger than any death."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from agent.harness import draft_keepalive
        import agent_cli

        def _write():
            from core.learning.agent_memory import get_agent_memory
            commits = agent_cli._recent_commits(24)
            lessons = agent_cli._recent_lessons(8)
            notes = get_agent_memory().get_decisions(days=1)
            try:
                from core.recall.at_action import recent_flips, recent_injections
                flips, injections = recent_flips(24), recent_injections(24)
            except Exception:
                flips, injections = [], []
            agent_cli.write_last_session_draft(
                agent_cli.last_session_draft_path(), commits, lessons, notes,
                trigger="claude Stop-hook keepalive", flips=flips, injections=injections)

        out = draft_keepalive.refresh(agent_cli.last_session_draft_path(), write=_write)
        print("[stop-hook] draft keepalive: wrote=%s (%s)" % (out["wrote"], out["reason"]),
              file=sys.stderr)
    except Exception:
        pass   # a keepalive must never alter the stop verdict


def main():
    try:
        payload = json.loads(sys.stdin.read().lstrip("﻿"))   # BOM-tolerant (PS pipes)
    except Exception as e:
        # fail-open for the agent, never silent for the operator (the 2026-07-02 lesson)
        print(f"[stop-hook] stdin unparseable: {type(e).__name__}: {e}", file=sys.stderr)
        payload = {}
    session_id = str(payload.get("session_id") or "")
    _beat_idle(session_id)
    if session_id:
        try:   # T086 S1b: a resurrected turn of an ENDED session stands down QUIETLY --
            #    no marker touch (that would fake renewal), no seat refresh, no wake-arm
            #    demand. Breaks the C1-5 resurrection loop by record, not by judgment.
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from core.comm import wake_seat as _ws
            if _ws.is_tombstoned(session_id):
                print("[stop-hook] session tombstoned (ended) -- standing down unarmed (T086 S1)",
                      file=sys.stderr)
                return
        except Exception:
            pass   # fail-open: tombstone probe errors never change stop-hook behavior
    _touch_activity(session_id)          # stamp ALIVE on every firing -- K7 fast path
    _draft_keepalive()                   # turn boundary: refresh a stale auto-handoff draft
    # THE TURN IS OVER, so stop claiming work. Without this the last verb lingers until its 25s
    # TTL expires and the avatar shows the seat mid-tool-call for half a minute after it went
    # quiet -- an overstatement, which is the one thing the state codebook exists to prevent.
    # Clearing is distinct from going absent: the seat is present and idle, not dead.
    try:
        from agent.harness.hooks._activity import report
        report("", "", "", session_id or "")
    except Exception:
        pass
    if session_id:
        try:                             # RB-21: keep the consumer seat alive while the
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from core.comm import runner_lock   # session is (heartbeat refuses foreign
            runner_lock.refresh_consumer(AGENT, f"session:{session_id}")   # tokens -> safe no-op)
        except Exception:
            pass
        try:                             # T074 W11: every stop re-arms this session's
            from core.comm import incarnation   # incarnation card (30m TTL = W12 expiry;
            incarnation.refresh_card(AGENT, session_id)   # a lost card self-heals, R12)
        except Exception:
            pass
    # EPHEMERAL-SEAT EXEMPTION (2026-07-18, kimi headless walks; mirrors AKASHIC_STOP_PROMISE):
    # a -p session's watcher would outlive the session and wake NOTHING -- for those seats the
    # wake ritual is only a multi-minute exit tax (live receipts: four kimi sessions, each caught
    # in deny/retry loops at exit; a phase-1 sandbox cannot even run the arm command). The
    # LAUNCHER opts out explicitly (env AKASHIC_STOP_WAKE=0); interactive seats never set this.
    # Unset keeps the full ritual -- the safe default stays fail-ARMED.
    if os.getenv("AKASHIC_STOP_WAKE", "1") == "0":
        print("[stop-hook] ephemeral seat (AKASHIC_STOP_WAKE=0) -- wake ritual waived by launcher",
              file=sys.stderr)
        _finish_nonwake_checks(payload)
        return
    # AUTOPILOT A1 (presence-autopilot-reconciliation, kill switch AKASHIC_DAEMON_WAKE=0):
    # a LIVE daemon owns wakeability -- this hook never blocks again while it runs; a
    # missing listener seat becomes a .rearm trigger the daemon answers within a tick.
    # Daemon down -> the ONCE-latched nag rides stderr and the legacy path decides.
    if os.getenv("AKASHIC_DAEMON_WAKE", "1") != "0":
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from core.comm import daemon_state
            _v = daemon_state.stop_hook_wake_verdict(AGENT, session_id)
            if _v.get("pass"):
                print(_v.get("line", ""), file=sys.stderr)
                _finish_nonwake_checks(payload)
                return
            if _v.get("nag"):
                print(_v.get("line", ""), file=sys.stderr)
        except Exception:
            pass   # fail-open to the legacy path -- the fast path is never a right
    if not wake_armed(session_id):
        # T050 Q6 (the arm-vs-hook race): a JUST-launched watcher needs ~1-2s of python+import
        # startup before its seat exists -- five false blocks on 2026-07-13/14 were this race,
        # each spawning a redundant watcher into newest-wins churn. One grace recheck.
        time.sleep(1.5)
    if not wake_armed(session_id):
        # T086-S3a: an ARMING ATTEMPT is in flight (standby touched its marker <90s ago) --
        # nagging now spawns exactly the redundant-watcher churn the nag exists to prevent
        # (live receipt 2026-07-16 ~09:16: the backstop fired mid-retry-loop).
        try:
            _arm_marker = os.path.join(tempfile.gettempdir(),
                                       f"bifrost_wake_{AGENT}_{session_id}.arming" if session_id
                                       else f"bifrost_wake_{AGENT}.arming")
            if os.path.isfile(_arm_marker) and (time.time() - os.path.getmtime(_arm_marker)) < 90:
                print("[stop-hook] arming attempt in flight -- standing by, no nag (T086 S3a)",
                      file=sys.stderr)
                return
        except Exception:
            pass
        # T086-S3b: a LIVE TWIN session holds the consumer seat -- the twin is the wakeable
        # seat-holder (plan-wall law); demanding a watcher HERE arms a redundant one. A
        # TOMBSTONED holder falls through (dead by record -> this seat SHOULD arm).
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from core.comm import runner_lock as _rl, wake_seat as _ws3
            _tok = str((_rl.holder(AGENT) or {}).get("token") or "")
            if (_tok.startswith("session:") and session_id
                    and _tok != f"session:{session_id}"
                    and not _ws3.is_tombstoned(_tok[len("session:"):])):
                print(f"[stop-hook] consumer seat held by live twin {_tok[len('session:'):][:8]} "
                      f"-- the twin is the wakeable seat; no watcher here (T086 S3b)",
                      file=sys.stderr)
                return
        except Exception:
            pass
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
            arm_cmd = f"BIFROST_WAKE_LANE=work py scripts/bifrost_wake.py --agent {AGENT}" + (
                f" --session {session_id}" if session_id else "")   # T045: lane-mode watch
            # T073 P3: this block is the BACKSTOP, not a per-turn chore -- the watcher is
            # long-lived (hours). Distinguish a planned deadline cycle from a death.
            how = "cycled its deadline (planned)" if _rearm_trigger_fresh(session_id) \
                else "died or was never armed"
            print(json.dumps({"decision": "block", "reason": (
                f"Your wake watcher {how} -- this session is not wakeable from idle "
                f"(DeepSeek/Daniel can't reach you). Re-launch it ONCE: "
                f"`{arm_cmd}` as a run_in_background task (harness-tracked; its completion "
                "re-invokes you). It stays armed for HOURS -- this backstop should be rare. "
                "Then stop.")}))
            return
    _finish_nonwake_checks(payload)


def _finish_nonwake_checks(payload):
    """Everything the hook owes REGARDLESS of wakeability (the A1 fast path and
    the legacy path both land here): the promise audit -- a content-quality
    gate, never a liveness concern (reconciliation convergence 3)."""
    try:
        reason = _promise_block(payload)
    except Exception:
        reason = None          # fail-open: the audit must never wedge the session
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
