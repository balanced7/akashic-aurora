#!/usr/bin/env python3
"""Install the repo git hooks (Concurrency design C4).

Points git at the TRACKED hooks dir (`scripts/githooks`) via core.hooksPath, so every stage
in it is version-controlled and shared across every worktree:

    pre-commit   the staged-file backstops (peer locks, attribution, private-plane FILES,
                 derived docs, the guardrail ratchet)
    commit-msg   the private-plane guard for the commit MESSAGE -- its own stage because git
                 writes the message file only after pre-commit has run (defer dd0c36b406)
    pre-push     the door gate

Repo-local config isn't committed, so run this once per clone / worktree set:

    py scripts/githooks/install_git_hooks.py

A stage file missing from the dir is a WIRING DEFECT and is reported as one: git runs
whatever is there and says nothing about what is not, so absence would otherwise read as
success.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS_DIR = os.path.join(ROOT, "scripts", "githooks")
HOOKS = ("pre-commit", "commit-msg", "pre-push")


def missing_hooks(hooks_dir=None):
    """Expected stage files absent from the hooks dir, in HOOKS order."""
    d = hooks_dir or HOOKS_DIR
    return [h for h in HOOKS if not os.path.isfile(os.path.join(d, h))]


def main():
    r = subprocess.run(["git", "config", "core.hooksPath", "scripts/githooks"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        return r.returncode
    gone = missing_hooks()
    active = [h for h in HOOKS if h not in gone]
    print("[hooks] core.hooksPath -> scripts/githooks  (active: %s)" % ", ".join(active))
    print("        set AKASHIC_AGENT_ID=<your agent> so it can check your peer locks.")
    if gone:
        sys.stderr.write("[hooks] WIRING DEFECT: expected stage(s) missing from "
                         "scripts/githooks: %s -- git runs what is there and is silent "
                         "about what is not.\n" % ", ".join(gone))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
