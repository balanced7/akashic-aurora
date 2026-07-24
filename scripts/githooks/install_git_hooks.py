#!/usr/bin/env python3
"""Install the repo git hooks (Concurrency design C4).

Points git at the TRACKED hooks dir (`scripts/githooks`) via core.hooksPath, so the
pre-commit backstop is version-controlled and shared across every worktree. Repo-local
config isn't committed, so run this once per clone / worktree set.

    py scripts/githooks/install_git_hooks.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    r = subprocess.run(["git", "config", "core.hooksPath", "scripts/githooks"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        return r.returncode
    print("[hooks] core.hooksPath -> scripts/githooks  (C4 pre-commit backstop active)")
    print("        set AKASHIC_AGENT_ID=<your agent> so it can check your peer locks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
