"""worktree.py -- per-agent git worktrees (Concurrency design C1).

Each agent works in its OWN linked worktree on its OWN branch (`agent/<name>`),
sharing the one `.git`. This makes "the other agent edited my files / staged into the
shared index" (failure modes FM1/FM2) *structurally impossible* -- git refuses to
check out the same branch in two worktrees. The shared SUBSTRATE (Redis bus / Store /
Ledger on 16379) is process-level and unaffected: every worktree's code talks to the
same Redis, so the agents still see one bus, one memory, one ledger.

    py scripts/worktree.py setup <agent> [--base DIR]   # create agent/<agent> + a worktree
    py scripts/worktree.py list                          # show all worktrees
    py scripts/worktree.py sync <agent>                  # rebase your branch on origin/master
    py scripts/worktree.py integrate <agent> [--no-ff]   # merge agent/<agent> -> master, push
    py scripts/worktree.py remove <agent> [--force]      # remove the worktree (branch kept)

Daily flow:
  1. Once per agent:  py scripts/worktree.py setup claude   (then open that dir in your IDE)
  2. Work in your worktree; commit to your branch; mirror to push (explicit paths -- C0).
  3. Slice green?  py scripts/worktree.py integrate claude   (from the main repo on master)
  4. Peer picks it up:  py scripts/worktree.py sync cursor
The main checkout (E:\\AI-Setup on master) becomes the integration point -- agents
live in their worktrees, master is where green slices land.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}   # never hang on a credential prompt
DEFAULT_BRANCH = "master"


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), env=ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(r.returncode)
    return r


def slugify(agent: str) -> str:
    s = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (agent or "").strip().lower())
    return s.strip("-") or "agent"


def branch_name(agent: str) -> str:
    return f"agent/{slugify(agent)}"


def worktree_path(agent: str, root=ROOT, base=None) -> Path:
    """Default location is a sibling of the repo: <repo>-<agent> (e.g. AI-Setup-claude)."""
    root = Path(root)
    base = Path(base) if base else root.parent
    return base / f"{root.name}-{slugify(agent)}"


def setup(agent: str, root=ROOT, base=None) -> Path:
    br, wt = branch_name(agent), worktree_path(agent, root, base)
    if wt.exists():
        print(f"[worktree] {wt} already exists -- open it in your IDE.")
        return wt
    wt.parent.mkdir(parents=True, exist_ok=True)
    have = _git(root, "rev-parse", "--verify", "--quiet", br, check=False).returncode == 0
    if have:
        _git(root, "worktree", "add", str(wt), br)
    else:
        _git(root, "worktree", "add", "-b", br, str(wt), DEFAULT_BRANCH)
    print(f"[worktree] {agent}: {wt}  (branch {br})")
    print(f"  -> Open THIS dir in your IDE: {wt}")
    print(f"  -> Commit to {br}; `py scripts/mirror.py \"msg\" <paths>` to push.")
    print(f"  -> When a slice is green: py scripts/worktree.py integrate {slugify(agent)}")
    return wt


def list_worktrees(root=ROOT) -> str:
    out = _git(root, "worktree", "list").stdout.strip()
    print(out)
    return out


def sync(agent: str, root=ROOT, base=None, onto=None) -> None:
    """Rebase the agent's branch onto the latest integrated master (origin/master)."""
    wt = worktree_path(agent, root, base)
    if not wt.exists():
        raise SystemExit(f"[worktree] no worktree for {agent} -- run setup first.")
    onto = onto or f"origin/{DEFAULT_BRANCH}"
    if _git(wt, "fetch", "origin", check=False).returncode != 0:
        print("[worktree] fetch failed (offline?) -- rebasing on local master instead.")
        onto = DEFAULT_BRANCH
    _git(wt, "rebase", onto)
    print(f"[worktree] {agent} rebased on {onto}")


def integrate(agent: str, root=ROOT, no_ff=False) -> None:
    """Merge agent/<agent> into master and push. Run from the MAIN repo, on master."""
    br = branch_name(agent)
    cur = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if cur != DEFAULT_BRANCH:
        raise SystemExit(f"[worktree] integrate must run on {DEFAULT_BRANCH} (HEAD is '{cur}').")
    margs = ["merge", br] if not no_ff else ["merge", "--no-ff", br, "-m", f"Integrate {br}"]
    _git(root, *margs)
    print(f"[worktree] merged {br} -> {DEFAULT_BRANCH}")
    pushed = _git(root, "push", "origin", DEFAULT_BRANCH, check=False)
    print("[worktree] pushed master" if pushed.returncode == 0
          else "[worktree] merge done; push skipped/failed (push manually when online).")


def remove(agent: str, root=ROOT, base=None, force=False) -> None:
    wt = worktree_path(agent, root, base)
    args = ["worktree", "remove", str(wt)] + (["--force"] if force else [])
    r = _git(root, *args, check=False)
    if r.returncode == 0:
        print(f"[worktree] removed {wt} (branch {branch_name(agent)} kept)")
    else:
        sys.stderr.write(r.stdout + r.stderr)
        print("[worktree] remove failed -- commit/mirror your work, or pass --force.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="worktree.py", description="Per-agent git worktrees (C1).")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("setup", "sync", "remove"):
        s = sub.add_parser(name); s.add_argument("agent"); s.add_argument("--base")
    sub.choices["remove"].add_argument("--force", action="store_true")
    sub.add_parser("list")
    si = sub.add_parser("integrate"); si.add_argument("agent"); si.add_argument("--no-ff", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "setup":      setup(a.agent, base=a.base)
    elif a.cmd == "list":     list_worktrees()
    elif a.cmd == "sync":     sync(a.agent, base=a.base)
    elif a.cmd == "integrate": integrate(a.agent, no_ff=a.no_ff)
    elif a.cmd == "remove":   remove(a.agent, base=a.base, force=a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
