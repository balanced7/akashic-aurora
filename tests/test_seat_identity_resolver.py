"""PRE-REGISTERED acceptance for the session-scoped seat identity resolver (fold 2 + fold 1).

Registered BEFORE any implementation, per M3. These pins are RED at registration time and
that is the point: git must show acceptance preceded implementation.

WHY THIS EXISTS -- the defect, measured, not theorised (2026-08-01):
Every Claude Code hook resolves "who am I" from ONE PROCESS-WIDE env var, AKASHIC_AGENT_ID,
whose hardcoded fallback is the literal string "claude" -- the conductor's name. The env comes
from a settings.json shared by every home-rooted session, and a running session cannot mutate
its own process env, so a seat CANNOT declare its own identity. Live consequences on one
session in one day:
  * one physical session held TWO roster rows -- claude#6ac75463 LIVE (hook-beaten, wrong name)
    and opus-engineer#6ac75463 DEAD 3.6h (correct name, nothing beats it), while working
  * the conductor read absence-from-roster as death, wrote "your seat died 10h ago", and
    redelivered one brief four times
  * the stop hook's wakeability check searched for the CLAUDE-named watcher, could not see the
    correctly-named one, and prescribed arming a duplicate under the conductor's name -- a
    guardrail crying wolf AND handing over the wrong medicine (three firings)
  * advisory path-locks became unusable: a lock taken as opus-engineer locked the SAME session
    out of its own files, because the lock hook resolved the holder as claude

THE RULE THESE PINS ENCODE, and it is the transferable half:
A missing identity must FAIL LOUD, never silently borrow a real peer's name. Substituting
"claude" does not merely lose information -- it IMPERSONATES, and every downstream organ
(roster, reaper, locks, traces, wake) then attributes one seat's work to another. XMPP's
Bind 2 settles the same case by REFUSING a stanza with no explicit sender (unknown-sender);
we take the same posture, downgraded to a loud unknown-<sid8> because a hook must never
break a session.

Companion receipts: lesson seat_identity_is_process_scoped_not_session_scoped,
lesson stop_hook_wakeability_check_false_alarms_non_claude_seats, wish W114,
atom art_20260801_concurrent-seats-one-program-prior-art_a69ecf (six systems, all of which
solve this with a two-level name plus an explicit binding step).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

HOOK_NAMES = ("claude_sessionstart.py", "claude_stop.py", "claude_userpromptsubmit.py",
              "claude_pretooluse.py", "claude_posttooluse.py", "claude_sessionend.py")
HOOK_DIRS = {"scripts": os.path.join(ROOT, "scripts", "hooks"),
             "agent_harness": os.path.join(ROOT, "agent", "harness", "hooks")}

# A SYNTHETIC session id, never a real one: these pins must not read live seat state.
# Found the hard way -- the first draft used this seat's REAL session id with the default
# (OS temp) binding dir, so the moment the door worked and a binding existed, r1/r2 flipped
# red against production reality rather than against the code under test.
SID = "testsid0-0000-0000-0000-000000000000"
SID8 = SID[:8]


# --------------------------------------------------------------- R1: the resolver contract
def test_r1_no_identity_anywhere_never_yields_a_real_peer_name(tmp_path, monkeypatch):
    """The load-bearing pin. No binding, no env -> MUST NOT be 'claude' (or any peer id).

    This is the whole slice in one assertion. A resolver that guesses the conductor when it
    does not know is the defect; a resolver that says so is the fix.
    """
    from core.comm import seat_identity

    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    got = seat_identity.resolve(SID, binding_dir=str(tmp_path))

    assert got != "claude", (
        "resolver silently impersonated the conductor with no identity available -- "
        "this is the exact defect the slice exists to remove")
    assert got not in ("deepseek", "kimi", "codex", "gemini", "sol"), (
        f"resolver borrowed a real peer's name: {got!r}")
    assert got.startswith("unknown-"), f"expected a loud unknown-<sid8>, got {got!r}"
    assert SID8 in got, f"unknown id must carry the session discriminator, got {got!r}"


def test_r2_env_is_honoured_when_no_binding_exists(tmp_path, monkeypatch):
    """Backward compatibility is a REQUIREMENT, not a nicety: with no binding file and the env
    set, behaviour must be byte-identical to today or every existing seat changes name."""
    from core.comm import seat_identity

    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    assert seat_identity.resolve(SID, binding_dir=str(tmp_path)) == "claude"


def test_r3_binding_beats_env(tmp_path, monkeypatch):
    """The point of the slice: a session declares its own name and that WINS over the
    process-wide env it cannot mutate."""
    from core.comm import seat_identity

    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    seat_identity.declare("opus-engineer", SID, binding_dir=str(tmp_path))
    assert seat_identity.resolve(SID, binding_dir=str(tmp_path)) == "opus-engineer"


def test_r4_binding_is_per_session_not_global(tmp_path, monkeypatch):
    """A sibling session's binding must never leak into mine -- the twin-seat failure the
    whole N-seat architecture exists to make structurally impossible."""
    from core.comm import seat_identity

    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    other = "ca84109a-12e0-4546-bdab-6c1cadbe922d"
    seat_identity.declare("opus-engineer", SID, binding_dir=str(tmp_path))

    assert seat_identity.resolve(other, binding_dir=str(tmp_path)).startswith("unknown-")
    assert seat_identity.resolve(SID, binding_dir=str(tmp_path)) == "opus-engineer"


def test_r5_resolver_never_raises(tmp_path, monkeypatch):
    """Hooks are fail-open by contract: identity resolution must never break a session.
    Garbage on disk, an unreadable dir, and a missing session id all resolve, never raise."""
    from core.comm import seat_identity

    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    bad = tmp_path / "seat_identity"
    bad.mkdir()
    (bad / f"{SID}.id").write_bytes(b"\xff\xfe not utf-8 \x00")
    assert isinstance(seat_identity.resolve(SID, binding_dir=str(bad)), str)
    assert isinstance(seat_identity.resolve("", binding_dir=str(bad)), str)
    assert isinstance(seat_identity.resolve(SID, binding_dir="/nonexistent/zz"), str)


# --------------------------------------------------- R6: the hooks actually USE the resolver
@pytest.mark.parametrize("which", sorted(HOOK_DIRS))
def test_r6_no_hook_silently_defaults_identity_to_a_peer_name(which):
    """Built-not-wired is the failure mode this slice must not reproduce: a resolver nothing
    calls repairs nothing. No claude_* hook may carry a literal peer-name fallback on an
    AKASHIC_AGENT_ID read.

    Scanned by AST, not by regex, and the reason is a defect this pin itself committed: the
    first draft matched source TEXT and promptly fired on the fix's own docstring, which quotes
    the old `... or "claude"` pattern to explain what it replaces. A rule that cannot tell code
    from prose about the rule makes every future explanation a violation -- the same shape as
    the boundary guardrail flagging a comment that names `sys.path.insert`. Parsing means the
    pin tests the BEHAVIOUR in the tree rather than the characters, so it also catches spellings
    no regex was written for. Importing is still avoided: a hook's module body runs on import.
    """
    import ast

    PEERS = {"claude", "deepseek", "kimi", "codex", "gemini", "sol", "composer"}

    def _reads_agent_env(node) -> bool:
        """os.getenv("AKASHIC_AGENT_ID"...) or os.environ.get("AKASHIC_AGENT_ID"...)"""
        return (isinstance(node, ast.Call) and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "AKASHIC_AGENT_ID")

    offenders = []
    for name in HOOK_NAMES:
        path = os.path.join(HOOK_DIRS[which], name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=name)
        for node in ast.walk(tree):
            # `os.getenv("AKASHIC_AGENT_ID") or "claude"`
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                vals = node.values
                if (any(_reads_agent_env(v) for v in vals[:-1])
                        and isinstance(vals[-1], ast.Constant)
                        and vals[-1].value in PEERS):
                    offenders.append(f"{name}:{node.lineno}: `... or {vals[-1].value!r}`")
            # `os.environ.get("AKASHIC_AGENT_ID", "claude")`
            if _reads_agent_env(node) and len(node.args) > 1:
                d = node.args[1]
                if isinstance(d, ast.Constant) and d.value in PEERS:
                    offenders.append(f"{name}:{node.lineno}: `get(..., {d.value!r})`")

    assert not offenders, (
        f"{which}/ hooks still default a missing identity to a real peer:\n  "
        + "\n  ".join(offenders))


def test_r7_both_hook_copies_resolve_identity_identically():
    """W3's shape, applied to this slice. scripts/hooks/ and agent/harness/hooks/ are TWO REAL
    FILES that differ only by sys.path depth. A home-rooted session runs the scripts/ copy; the
    wiring gate at check_wiring.py:28-34 declares that copy 'not entry points... deliberately
    not walked', so a fix landing in the agent/ copy alone is invisible AND a no-op exactly
    where it is needed. Identity lines must match across both."""
    def ident_lines(d):
        out = []
        for name in HOOK_NAMES:
            p = os.path.join(d, name)
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                out += [(name, ln.strip()) for ln in fh
                        if "AKASHIC_AGENT_ID" in ln or "seat_identity" in ln]
        return out

    a, b = ident_lines(HOOK_DIRS["scripts"]), ident_lines(HOOK_DIRS["agent_harness"])
    assert a == b, ("hook copies disagree on identity resolution -- one seat profile gets the "
                    f"fix and the other does not:\n  scripts/: {a}\n  agent/:   {b}")


# ------------------------------------------------------------------ R8: the declare door
def test_r8_declare_door_is_reachable_from_the_cli():
    """A binding a seat cannot create is not a door. The CLI must expose it, because the seat
    that needs it is mid-session and cannot restart itself to change its own process env."""
    r = subprocess.run([sys.executable, "-X", "utf8", "agent_cli.py", "discover"],
                       capture_output=True, text=True, cwd=ROOT, encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL, close_fds=True, timeout=90)
    assert "seat-identity" in (r.stdout or "") or "seat_identity" in (r.stdout or ""), (
        "no seat-identity verb on the self-describing door -- a seat cannot declare its name")
