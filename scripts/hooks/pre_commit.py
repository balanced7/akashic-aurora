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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def check_staged(files, agent, client=None):
    """Return (ok, reason). ok=False -> abort the commit. Fail-open (allow) when there is
    no agent id, or the lock layer is unavailable -- a backstop must not block humans."""
    if not agent:
        return True, ""
    try:
        from core.comm.locks import path_conflict
    except Exception:
        return True, ""
    conflicts = []
    for f in files:
        try:
            c = path_conflict(f, agent, client=client)
        except Exception:
            continue
        if c.get("conflict"):
            conflicts.append((f, c.get("held_by")))
    if conflicts:
        body = "\n".join(f"  {f} -> locked by {who}" for f, who in conflicts)
        return False, ("pre-commit BLOCKED: you staged file(s) a peer holds an advisory lock on:\n"
                       + body + "\nCommit only files you hold, or coordinate via the bus "
                       "(see docs/concurrency-design.md C2/C4).")
    return True, ""


def main():
    ok, reason = check_staged(_staged_files(), os.getenv("AKASHIC_AGENT_ID"))
    if not ok:
        sys.stderr.write(reason + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
