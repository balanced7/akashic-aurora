#!/usr/bin/env python3
"""Git pre-commit backstop (Concurrency design C4).

Defense-in-depth beneath the per-agent editor hooks (C0/C2): reject a commit that stages
a file a PEER holds an advisory lock on -- regardless of which agent, or which missing
per-agent hook, produced it. Keyed on AKASHIC_AGENT_ID; if unset (e.g. a human commit) it
fails OPEN. A non-zero exit aborts the commit (standard git-hook contract -- here exit 1
is correct; the exit-2 rule was specific to Claude Code PreToolUse, not git hooks).

Install once per clone/worktree:  py scripts/hooks/install_git_hooks.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def _staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def check_staged(files, agent, client=None):
    """Return (ok, reason). ok=False -> abort the commit. With an `agent` id, only a PEER's lock
    blocks (you may commit files you hold). WITHOUT one we can't verify ownership, so we fail
    CLOSED on any staged locked file (teaching the fix) rather than silently allowing -- an unset
    id must not disable the backstop (the RC-01 fail-open). Lock layer unavailable -> allow."""
    try:
        from core.comm.locks import path_conflict
    except Exception:
        return True, ""
    who_me = agent or "(unidentified)"
    conflicts = []
    for f in files:
        try:
            c = path_conflict(f, who_me, client=client)
        except Exception:
            continue
        if c.get("conflict"):
            conflicts.append((f, c.get("held_by")))
    if not conflicts:
        return True, ""
    body = "\n".join(f"  {f} -> locked by {who}" for f, who in conflicts)
    if not agent:
        return False, ("pre-commit BLOCKED: AKASHIC_AGENT_ID is not set, so lock ownership can't be "
                       "verified and you staged file(s) a peer may hold a lock on:\n" + body +
                       "\nSet AKASHIC_AGENT_ID=<your agent id> (e.g. in .claude/settings.json env).")
    return False, ("pre-commit BLOCKED: you staged file(s) a peer holds an advisory lock on:\n" + body +
                   "\nCommit only files you hold, or coordinate via the bus (see docs/concurrency-design.md C2/C4).")


def _comprehensibility_fast():
    """The drift immune system's FAST checks (stale-ref + filename-case) as a commit-time backstop --
    so drift can't reach the shared repo via `mirror`/`git commit`, not just `ship.py` (property
    UNBYPASSABLE). Fail-OPEN on a guard CRASH (a broken guard must never brick every commit; CI + ship
    run the full guard anyway); real drift fails CLOSED. Emergency bypass: `git commit --no-verify`."""
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "check_comprehensibility.py"), "--fast"],
            capture_output=True, text=True, timeout=60)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception:
        return 0, ""   # guard unavailable/slow -> fail open


def main():
    ok, reason = check_staged(_staged_files(), os.getenv("AKASHIC_AGENT_ID"))
    if not ok:
        sys.stderr.write(reason + "\n")
        return 1
    rc, out = _comprehensibility_fast()
    if rc == 1:
        sys.stderr.write("pre-commit BLOCKED: comprehensibility drift (a stale repo reference or a "
                         "filename case-mismatch):\n" + out +
                         "\nFix it, or `git commit --no-verify` to bypass in a genuine emergency.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
