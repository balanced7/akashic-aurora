"""SEAT HEARTBEAT WIRING pins -- RED first (M3).

WHY THIS EXISTS. Measured 2026-08-01: 89 seats in the roster, ZERO live. `roster.heartbeat`
(core/comm/roster.py:103) has ONE production caller, agent/bifrost_pull.py, reached only from
boot / manual sync / SessionStart / UserPromptSubmit. WORKLIVE_TTL_S is 180, so a seat working
continuously inside one turn reads DEAD after three minutes. Three organs consume that sensor
as truth -- the reaper (reaper.py:90 treats DEAD as reapable), the bus UNATTENDED RECIPIENT
warning, and doctor's "genuinely working" retraction. The conductor seat that wrote today's
handover read two live peers as dead and re-sent one brief four times, because the instrument
told it they were corpses. Fix: beat from the PostToolUse hook -- a genuine per-action tick.

WHY THESE PINS LOOK LIKE THIS (lesson fail_open_plus_monkeypatched_pins_equals_invisible_noop,
earned in this repo hours before this file): a fix shipped today was a pure no-op and every one
of its four pins was green, because every pin MONKEYPATCHED the method under test. Fail-open
plus mocked pins makes a guard's ABSENCE byte-identical to its SILENCE. So:

    Monkeypatched pins prove the POLICY. Only an UNPATCHED pin proves the WIRING.

Every pin below runs the REAL hook file as a REAL subprocess over stdin and asserts the
OBSERVABLE EFFECT in the store. Nothing is patched, stubbed, or imported-and-called. If the
beat is missing, misplaced, swallowed by a bare except, or living in the wrong one of the two
hook copies, these go red.

THE THREE FAILURE PATHS PINNED, each one measured as a live no-op risk before writing:

  W1 WIRING       the hook actually beats. Fails today: nothing beats.
  W2 SCOPE GATE   the beat survives `_in_scope` (claude_posttooluse.py:253). That guard is
                  TARGET-scoped: for a shell tool it returns True only when the command text
                  contains "ai-setup"/"agent_cli.py", or cwd is under the repo. A seat working
                  from C:/Users/L5 on non-repo paths therefore misses it -- and that is exactly
                  the seat that goes DEAD, so the failure is CORRELATED with the thing being
                  measured. The payload here deliberately uses a home cwd and a bare command:
                  if anyone later moves the beat below that gate, this pin goes red.
  W3 TWIN PARITY  BOTH hook copies carry it. scripts/hooks/ and agent/harness/hooks/ are two
                  real files (not symlinks), differing only by sys.path depth. A HOME-rooted
                  session loads ONLY C:/Users/L5/.claude/settings.json, which runs the
                  scripts/ copy -- while check_wiring.py, the project settings, and every
                  convention in the tree point a developer at the agent/ copy. Patching the
                  "authoritative" copy alone is a perfect no-op in precisely the seat profile
                  that reads DEAD.

KNOWN BOUND, stated rather than hidden: the hook process is only spawned for tools named in the
settings matcher (Bash|PowerShell|Edit|Write|NotebookEdit|Task). A turn made purely of Read /
Grep / Glob / mcp__* calls still produces no beat. That gap is real, is NOT closed by this file,
and is not pinned here because no pin over this hook can observe an event the harness never
sends. See the commit message for the follow-on.
"""

import json
import os
import subprocess
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The two real copies. The scripts/ one is what a home-rooted session actually executes.
HOOKS = {
    "scripts": os.path.join(REPO, "scripts", "hooks", "claude_posttooluse.py"),
    "agent_harness": os.path.join(REPO, "agent", "harness", "hooks", "claude_posttooluse.py"),
}

AGENT = "pintest-seat"
SESSION = "beef9999-0000-4444-8888-1234567890ab"
SID8 = SESSION[:8]

# HOME cwd + a command naming NEITHER "ai-setup" NOR "agent_cli.py". This payload is
# deliberately OUT of _in_scope's target scope and IN session scope -- the exact shape that
# the scope gate drops and that a correctly-placed beat must still serve (W2).
PAYLOAD = {
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "session_id": SESSION,
    "cwd": os.path.expanduser("~"),
    "tool_input": {"command": "ls -la"},
    "tool_response": {"stdout": "", "stderr": "", "interrupted": False},
}


def _run_hook(path: str, ns: str, payload: dict) -> subprocess.CompletedProcess:
    """Execute the REAL hook file exactly as the harness does: fresh process, JSON on stdin.
    No import, no patch -- so an ImportError, a signature drift, a swallowed exception or a
    beat that simply is not there all present as a missing row rather than a green test."""
    env = dict(os.environ)
    env["BIFROST_NAMESPACE"] = ns
    env["AKASHIC_AGENT_ID"] = AGENT
    env.pop("AKASHIC_SEAT_HEARTBEAT", None)     # default-on must be what ships
    env.pop("BIFROST_INCARNATION", None)        # force the payload's session_id to be used
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    return subprocess.run(
        [sys.executable, path],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=90,
        cwd=REPO, env=env,
    )


def _beats(ns: str):
    from core.comm.roster import roster as read_roster
    return {(r.get("agent"), r.get("sid8")): r for r in read_roster(ns)}


@pytest.fixture()
def ns():
    return f"hbwire{uuid.uuid4().hex[:8]}"


@pytest.mark.parametrize("which", sorted(HOOKS))
def test_w1_posttooluse_hook_actually_beats_the_seat(which, ns):
    """W1+W3: the REAL hook file writes a REAL worklive row. Both copies (W3 twin parity).

    RED TODAY: no hook beats roster.heartbeat, so the roster stays empty.
    """
    path = HOOKS[which]
    assert os.path.exists(path), f"hook copy missing: {path}"

    proc = _run_hook(path, ns, PAYLOAD)
    assert proc.returncode == 0, f"hook must never fail the tool call: {proc.stderr[-2000:]}"

    rows = _beats(ns)
    assert (AGENT, SID8) in rows, (
        f"[{which}] no heartbeat written for {AGENT}#{SID8}. The hook ran and exited 0, which "
        f"is what a swallowed/absent beat looks like from outside -- that is the whole point of "
        f"this pin. Namespace {ns} held: {sorted(rows)}. stderr: {proc.stderr[-800:]}"
    )


@pytest.mark.parametrize("which", sorted(HOOKS))
def test_w2_beat_survives_the_target_scope_gate(which, ns):
    """W2: the beat must precede _in_scope, which is TARGET-scoped and would drop this payload.

    The payload's cwd is HOME and its command names no repo path, so shell_in_scope() is False.
    A beat placed anywhere at or below claude_posttooluse.py:253 cannot fire here. This is the
    regression that would silently return the fleet to zero-live for home-rooted seats.
    """
    from agent.harness.scope import shell_in_scope, session_in_scope
    # Establish the premise rather than assume it: this payload really is out of target scope
    # and really is in session scope. If that ever stops being true the pin is meaningless.
    assert not shell_in_scope(PAYLOAD["cwd"], PAYLOAD["tool_input"]["command"]), (
        "premise broken: payload is now IN target scope, so this pin no longer tests the gate"
    )
    assert session_in_scope(PAYLOAD["cwd"]), "premise broken: home cwd must be in SESSION scope"

    proc = _run_hook(HOOKS[which], ns, PAYLOAD)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (AGENT, SID8) in _beats(ns), (
        f"[{which}] beat did not survive the target-scope gate -- it is placed at or below "
        f"_in_scope(). Move it above every early return in main()."
    )


@pytest.mark.parametrize("which", sorted(HOOKS))
def test_w2b_beat_is_not_hostage_to_the_recall_kill_switch(which, ns):
    """W2b: liveness must not inherit an unrelated feature's off-switch.

    AKASHIC_RECALL_AT_ACTION=0 disables recall-at-action credit. A seat that turns recall off
    must not thereby become invisible to the reaper.
    """
    env_payload = dict(PAYLOAD)
    proc = subprocess.run(
        [sys.executable, HOOKS[which]],
        input=json.dumps(env_payload), capture_output=True, text=True, timeout=90, cwd=REPO,
        env={**os.environ, "BIFROST_NAMESPACE": ns, "AKASHIC_AGENT_ID": AGENT,
             "AKASHIC_RECALL_AT_ACTION": "0"},
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (AGENT, SID8) in _beats(ns), (
        f"[{which}] the beat is placed BELOW the AKASHIC_RECALL_AT_ACTION kill switch, so "
        f"disabling recall silently disables liveness."
    )


def test_w3_both_hook_copies_stay_in_sync():
    """W3: the two copies must differ ONLY by sys.path depth.

    They are separate real files that have already drifted once (uncommitted edits landed in
    scripts/ alone). If a future fix lands in one copy, a home-rooted session and a repo-rooted
    session get different liveness behaviour -- and the difference is invisible.
    """
    def norm(p):
        with open(p, encoding="utf-8") as f:
            body = f.read().replace("\r\n", "\n")
        return [ln for ln in body.split("\n") if "sys.path.insert" not in ln]

    a, b = norm(HOOKS["scripts"]), norm(HOOKS["agent_harness"])
    if a != b:
        diff = [f"  line {i+1}:\n    scripts/: {x!r}\n    agent/:   {y!r}"
                for i, (x, y) in enumerate(zip(a, b)) if x != y][:5]
        pytest.fail("hook copies have drifted (modulo sys.path):\n" + "\n".join(diff)
                    + ("" if len(a) == len(b) else f"\n  line counts differ: {len(a)} vs {len(b)}"))


@pytest.mark.parametrize("which", sorted(HOOKS))
def test_w4_never_invents_a_seat_when_identity_is_absent(which, ns):
    """W4: no identity -> no row. A phantom seat is worse than a missing one.

    This fleet has a known bug where missing identity defaults to `claude`, which has already
    produced one physical session appearing as two roster rows under two different names. A
    beat that cannot name its seat must stay silent rather than guess.
    """
    proc = subprocess.run(
        [sys.executable, HOOKS[which]],
        input=json.dumps(PAYLOAD), capture_output=True, text=True, timeout=90, cwd=REPO,
        env={k: v for k, v in {**os.environ, "BIFROST_NAMESPACE": ns}.items()
             if k not in ("AKASHIC_AGENT_ID", "BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID")},
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    rows = _beats(ns)
    assert not rows, f"[{which}] invented a seat with no AKASHIC_AGENT_ID: {sorted(rows)}"
