#!/usr/bin/env python3
"""Claude Code PreToolUse hook -> git-safety guard (Concurrency design C0).

Wire it in .claude/settings.json (project-launch, relative path):
  {"hooks":{"PreToolUse":[{"matcher":"Bash|PowerShell","hooks":[
    {"type":"command","command":"py agent/harness/hooks/claude_pretooluse.py"}]}]}}
(PowerShell is the harness's PRIMARY shell tool on Windows -- a Bash-only matcher routes every
shell command around the guard/recall/credit pipeline entirely. Matchers, the tool filter in
main(), and _in_scope must all know a new shell tool, or it is invisible.)
Or register at the USER level with an ABSOLUTE path so it fires for EVERY session launched from
any cwd (the read-bootstrap flow), e.g. command "py E:/AI-Setup/agent/harness/hooks/claude_pretooluse.py".
The scope guard (agent/harness/scope.py -- shared policy, this adapter only maps Claude's tool
names onto it) makes it a silent no-op outside this repo, so global registration is safe.

Reads the tool-call JSON on stdin. If the Bash command blanket-stages git (or a peer holds
an advisory lock on the target path), emit a DENY decision (the reason is fed back to Claude).
Otherwise the action is ALLOWED -- and on the allow path we attach RECALL-AT-ACTION:
`hookSpecificOutput.additionalContext` carrying the few highest-signal active lessons + any
lock/peer warning for this path/command (core/recall/at_action.py). This is the read-at-the-
moment-of-action seam -- the one native injection that lands AT the locus, not at turn-start.
Recall is best-effort, capped, FAITH-gated, and fails OPEN. Disable with AKASHIC_RECALL_AT_ACTION=0.
Fails OPEN on any unexpected error -- a guard must never brick the agent.

Note: exit 0 + a {permissionDecision:"deny"} JSON is the documented block path.
Do NOT signal a policy block with exit code 1 -- Claude Code treats exit 1 as a
non-blocking error and PROCEEDS with the action.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_FILE_TOOLS = ("Edit", "Write", "NotebookEdit")
_SHELL_TOOLS = ("Bash", "PowerShell")

# --- K0 / C8-3: same-payload dedup guard -------------------------------------------------
# The hook was registered on TWO surfaces (project-relative + user-absolute); both fired per
# call and log_injection() counted twice -- the funnel's `surfaced` denominator ran ~2x hot.
# Registration is now single-surface (user-level absolute; the ledger's routing), and THIS
# guard is the belt-and-suspenders: an ATOMIC marker (O_CREAT|O_EXCL -- no load-then-mark
# race) keyed by (session, tool, payload) makes any residual double-fire a silent no-op.
_DEDUP_WINDOW_S = 3.0


def _dedup_should_skip(data) -> bool:
    """True when an identical hook payload fired within the window (second surface / retry).
    Atomic via O_EXCL; fails OPEN (never skip on error -- a miscount beats a missed guard)."""
    import hashlib
    import tempfile
    import time
    try:
        key = hashlib.sha1(json.dumps(
            [data.get("session_id", ""), data.get("tool_name", ""),
             data.get("tool_input", {})], sort_keys=True, default=str).encode()).hexdigest()[:24]
        d = os.path.join(tempfile.gettempdir(), "akashic-hook-dedup")
        os.makedirs(d, exist_ok=True)
        now = time.time()
        try:                                    # lazy sweep so the dir stays tiny
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if now - os.path.getmtime(p) > 60:
                    os.remove(p)
        except Exception:
            pass
        path = os.path.join(d, key)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return False                        # first fire -- we hold the marker
        except FileExistsError:
            return (now - os.path.getmtime(path)) < _DEDUP_WINDOW_S
    except Exception:
        return False


def _in_scope(tool: str, data) -> bool:
    """Claude tool names -> the shared scope policy (agent/harness/scope.py): file tools scope
    by their target path, shell tools by session cwd or the command itself."""
    from agent.harness.scope import file_in_scope, shell_in_scope
    ti = data.get("tool_input") or {}
    if tool in _FILE_TOOLS:
        return file_in_scope(ti.get("file_path") or "")
    return shell_in_scope(data.get("cwd") or os.getcwd(), ti.get("command") or "")


def _deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def _emit_context(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}))


def _recall_context(data) -> str:
    """Recall-at-action: relevant active lessons + lock/peer warning for the path/command about to be
    acted on. Best-effort, capped, FAITH-gated, fail-open. ANTI-REPEAT: lessons already surfaced this
    session (agent/harness/seen.py, shared across altitudes) are excluded so the same hint never
    repeats. Locks always surface (safety). Kill switch: AKASHIC_RECALL_AT_ACTION=0."""
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    command = ti.get("command") or ""
    if not path and not command:
        return ""
    session_id = data.get("session_id") or ""
    try:
        from core.recall.at_action import (recall_at, render, mark_impression, normalize_target,
                                           log_injection)
        from agent.harness.seen import load_seen, mark_seen
        res = recall_at(path=path or None, command=command or None,
                        agent_id=os.getenv("AKASHIC_AGENT_ID"),
                        exclude_sources=load_seen(session_id), count_surface=True)
        out = render(res)
        if out:
            srcs = [l.get("source") for l in res.get("lessons", [])]
            mark_seen(session_id, srcs)
            target = normalize_target(path or None, command or None)
            # open impression for the implicit FAIL->SUCCESS credit (resolved by the PostToolUse hook)
            mark_impression(session_id, target, srcs)
            # injection ledger: pushed context must be inspectable + cost-measurable (survey C4)
            log_injection(session_id, "action", target, srcs, len(out))
        return out
    except Exception:
        return ""   # recall must never brick the action


#: A minted id looks like T227 in a PATH. THREE OR MORE digits -- an exact {3} expires
#: silently the day the ledger issues T1000, with every pin still green (blind-fan find).
_ID_IN_PATH = re.compile(r"[Tt](\d{3,})(?=[^0-9]|$)")  # 3,: T999 -> T1000 must not silently stop matching
#: Statuses that mean the id is SPENT. Anything else (active, or absent) stays silent.
_TERMINAL = ("done", "abandoned")


def id_facts_for_path(path, *, exists=None, ledger=None) -> str:
    """One FACT about an id being minted into a new path, or "" (T236).

    THE MEASUREMENT THIS EXISTS FOR. On 2026-08-07 the lesson that prevents this fired twice,
    both times on `task propose --help` -- the command where the writer is already doing it
    right -- and was silent 220 minutes later when T227 went into a filename that collided
    with a DONE task. Lessons are indexed by TOPIC, so they land at the trigger site and not
    at the application site. This is the application site.

    FACT, NOT RULE. "MINT THE IDENTIFIER FIRST" is a rule: general, true, context-free, and
    ignorable, because a rule asks something of you. "T227 is DONE: LEXICON gains its MECHANISM
    column" asks nothing at all -- it just closes an information gap, and that is what makes it
    ambient rather than a demand.

    FIRE ON THE ANOMALY, NOT THE ACTION. There are already ~269 injections and ~42k tokens a
    day here, and the corpus's own prior art says reduce volume to increase trust. So precision
    comes from separating MINTING from MENTIONING:
      * a PATH carries a minted id; prose merely references one, and commit bodies name done
        tasks constantly -- those must never fire.
      * a path that already EXISTS is being edited, not minted.
      * an ACTIVE id in a new path is someone working their claim.
    Only a TERMINAL id in a NEW path is the mistake, so this should fire approximately never,
    and its silence carries information too.

    The regex gate runs BEFORE any ledger read, so the overwhelmingly common case costs one
    match on a short string. Fails OPEN on everything: a helper that can brick a Write is not
    a helper.
    """
    try:
        p = str(path or "")
        m = _ID_IN_PATH.search(os.path.basename(p))
        if not m:
            return ""
        tid = "T" + m.group(1)
        if exists is None:
            exists = os.path.exists(p)
        if exists:
            return ""          # editing an existing pin, not minting a new id
        if ledger is None:
            # state_view() is keyed by STATUS BUCKET (done/in_progress/next/proposed/...),
            # each a list of task dicts -- NOT {"tasks": [...]}. The first cut assumed the
            # latter, so every lookup missed and the check was silent on the very case it was
            # built for, while its pins stayed green because they injected a fake ledger.
            # Mocking the seam that was wrong is how a pin certifies nothing.
            from core.coord.task_ledger import state_view
            ledger = {}
            for bucket in (state_view() or {}).values():
                if isinstance(bucket, list):
                    for t in bucket:
                        if isinstance(t, dict) and t.get("id"):
                            ledger[t["id"]] = t
        rec = (ledger or {}).get(tid)
        if not isinstance(rec, dict):
            return ""          # unknown id is FREE, and free is silent
        status = str(rec.get("status") or "").lower()
        if status not in _TERMINAL:
            return ""          # active work on a claimed id -- normal, never interrupt it
        title = str(rec.get("title") or "").strip()
        if len(title) > 90:
            title = title[:87] + "..."
        return f"[ledger] {tid} is {status}: {title}"
    except Exception:
        return ""              # fail open, always


def _check_bash(data) -> str:
    """Blanket git-staging veto -- verdict text from the shared policy (agent/harness/guards.py)."""
    try:
        from agent.harness.guards import git_veto
        return git_veto(((data.get("tool_input") or {}).get("command")) or "")
    except Exception:
        return ""   # policy unavailable -> allow


def _check_write(data) -> str:
    """Peer-lock veto (C2), incl. the RC-01 fail-closed-when-unidentified rule -- shared policy
    (agent/harness/guards.py); this adapter only says where Claude sets its env."""
    try:
        from agent.harness.guards import lock_veto
        return lock_veto((data.get("tool_input") or {}).get("file_path") or "",
                         os.getenv("AKASHIC_AGENT_ID"),
                         "e.g. in .claude/settings.json env")
    except Exception:
        return ""   # lock layer unavailable -> allow (advisory)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0   # unparseable -> allow
    tool = data.get("tool_name") or ""
    if tool not in _SHELL_TOOLS + _FILE_TOOLS:
        return 0
    if _dedup_should_skip(data):
        return 0   # K0/C8-3: identical payload already fired within the window -> silent no-op
    if not _in_scope(tool, data):
        return 0   # outside this repo -> silent no-op (safe for user-level / global registration)
    if tool in _SHELL_TOOLS:
        reason = _check_bash(data)
    else:
        reason = _check_write(data)
    if reason:
        _deny(reason)
        return 0
    # Recall-at-action for ALL in-scope tools (Edit/Write AND Bash). Anti-repeat (per-session
    # exclude_sources) now prevents the same lesson repeating, so Bash recall front-loads relevant
    # knowledge then goes quiet instead of spamming. The git-guard above remains Bash's job.
    ctx = _recall_context(data)
    # T236: a FACT about the id being minted into this path, at the application site. Composed
    # with recall rather than replacing it, and placed FIRST because it is about the action in
    # hand while recall is about the topic. Fires approximately never (terminal id + new path
    # only), so it costs nothing in the volume budget recall already spends.
    if tool in _FILE_TOOLS:
        fact = id_facts_for_path((data.get("tool_input") or {}).get("file_path") or "")
        if fact:
            ctx = (fact + "\n" + ctx) if ctx else fact
    if ctx:
        _emit_context(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
