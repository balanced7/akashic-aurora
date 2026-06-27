"""
mirror.py -- commit local changes and push to GitHub in one step.

    py scripts/mirror.py ["commit message"]

Stages everything tracked-or-new (respecting .gitignore -> code/docs only, never the
17GB bulk or the volatile knowledge data), commits, and pushes the current branch to
origin. If there's nothing to commit it still pushes any unpushed commits.

This mirrors the CODE/architecture. Knowledge DATA is not in git -- snapshot it
separately:  py scripts/snapshot_knowledge.py snapshot

Optional: install as a post-commit hook so every commit auto-pushes --
    echo 'py scripts/mirror.py --push-only' > .git/hooks/post-commit   (advanced)
"""
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}   # never hang on a credential prompt


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, env=ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        sys.exit(r.returncode)
    return r


def main():
    push_only = "--push-only" in sys.argv
    msg_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    if not push_only:
        git("add", "-A")
        staged = git("diff", "--cached", "--name-only").stdout.strip()
        if staged:
            msg = msg_args[0] if msg_args else f"Mirror progress {datetime.now():%Y-%m-%d %H:%M}"
            git("commit", "-m", msg)
            print(f"[mirror] committed {len(staged.splitlines())} file(s): {msg}")
        else:
            print("[mirror] no file changes to commit")

    # Push (also flushes any earlier unpushed commits). Fail-soft on a missing upstream.
    ahead = git("rev-list", "--count", f"origin/{branch}..{branch}", check=False).stdout.strip()
    push = git("push", "origin", branch, check=False)
    out = ((push.stdout or "") + (push.stderr or "")).strip()
    if push.returncode == 0:
        moved = ahead and ahead != "0"
        print(f"[mirror] pushed to origin/{branch}" + (f" ({ahead} commit(s))" if moved else " (already up to date)"))
    else:
        print(f"[mirror] PUSH FAILED (commit is saved locally):\n{out}")
        print("  -> if auth expired: run `gh auth login` then re-run this.")
        sys.exit(1)


if __name__ == "__main__":
    main()
