"""
mirror.py -- commit local changes and push to GitHub in one step.

    py scripts/mirror.py "commit message" [path ...]   # stage+commit those paths
    py scripts/mirror.py "commit message"              # commit only what's STAGED
    py scripts/mirror.py "commit message" --all        # sweep the WHOLE tree (opt-in)
    py scripts/mirror.py --push-only                   # just push unpushed commits

Two agents share this working tree, so mirror does NOT blanket-stage by default --
that bundles the other agent's unreviewed work into your commit (the FM1 failure,
2026-06-28; see docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md). Name the paths that are yours, or stage
them first with `git add <path>`. `--all` is the explicit opt-in to stage everything
(it prints the full file list first).

This mirrors the CODE/architecture. Knowledge DATA is not in git -- snapshot it
separately:  py scripts/ops/snapshot_knowledge.py snapshot

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


def _emit_commit_beat(msg, files):
    """Narrative spine (Slice 1): a commit is a Beat in the code tracks. Salience-
    weighted so routine 'Mirror progress' commits stay quiet drill-down. Best-effort."""
    try:
        sys.path.insert(0, ROOT)
        from core.narrative.beat_log import get_beat_log
        from core.narrative.track_router import RouteHint
        sha = git("rev-parse", "HEAD", check=False).stdout.strip()[:12]
        salient = msg.lower().startswith(("feat", "fix")) or any(f.startswith("core/") for f in files)
        get_beat_log().emit("commit", summary=msg, source=f"git:{sha}", weight=4 if salient else 2,
                            hint=RouteHint(paths=files))
        # Auto-logger (Slice 2): the commit is also a RAW event -- full file list as the
        # drill-down detail beneath the salient Beat. Best-effort; never blocks the commit.
        try:
            from core.events.event_log import capture_event
            capture_event("command", f"git commit: {msg}", agent_id="mirror",
                          refs=[f"git:{sha}"],
                          detail={"sha": sha, "message": msg, "files": files})
        except Exception:
            pass
    except Exception:
        pass


def main():
    push_only = "--push-only" in sys.argv
    add_all = "--all" in sys.argv
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    if not push_only:
        msg = pos[0] if pos else None
        paths = pos[1:]
        if add_all:
            # explicit opt-in to blanket staging -- show exactly what we're about to grab
            dirty = git("status", "--porcelain").stdout.strip()
            print("[mirror] --all: staging the ENTIRE working tree:")
            print(dirty or "  (clean)")
            git("add", "-A")
        elif paths:
            git("add", "--", *paths)
        # else: stage nothing -- commit only what the agent already staged explicitly

        if paths and not add_all:
            # C2-4: the index is SHARED between seats -- another agent's staged work may
            # be sitting in it. Named-path mode must commit the named paths and nothing
            # else, leaving stranger staged entries staged for their own author.
            staged = git("diff", "--cached", "--name-only", "--", *paths).stdout.strip()
        else:
            staged = git("diff", "--cached", "--name-only").stdout.strip()
        # Rule-8 pre-commit mojibake guard (D3, deepseek): scan staged .md files for
        # known byte-level corruption signatures before the commit. A hit REFUSES the
        # commit — fix the source bytes, not the .md. Best-effort; never blocks a
        # commit on hook failure (the guard is an optimization; check_boundaries is
        # the permanent backstop).
        if staged:
            md_files = [f for f in staged.strip().split("\n") if f.endswith(".md")]
            # CHUNKED argv (2026-07-23, exposed by the A3 migration's 661-file commit):
            # Windows CreateProcess caps the command line at ~32K chars -- one hook call
            # per <=150 files stays far under it at any corpus size.
            hook = os.path.join(ROOT, "scripts", "githooks", "mojibake_signatures.py")
            for i in range(0, len(md_files), 150):
                chunk = md_files[i:i + 150]
                r = subprocess.run(
                    [sys.executable, hook, *chunk],
                    cwd=ROOT, env=ENV, capture_output=True, text=True)
                if r.returncode != 0:
                    print(r.stdout.strip())
                    print(r.stderr.strip() if r.stderr else "")
                    print("[mirror] rule-8 mojibake guard REFUSED commit — fix and re-stage.")
                    sys.exit(1)
        # Rule-13 birth guard (A1, T101): new .md is born through the door (atoms +
        # projections), never loose. REFUSES new docs/*.md outside docs/library/ +
        # crown; research/chronicles WARN during the migration window (P3 flips them).
        # Same posture as rule-8: the guard optimizes, the census backstops.
        if staged:
            hook13 = os.path.join(ROOT, "scripts", "githooks", "birth_guard.py")
            if os.path.exists(hook13):
                # SCOPED like rule-8 above (C2-4): pass the staged list this invocation is
                # actually committing. Called bare, the guard re-derives the WHOLE shared
                # index -- so another seat's loose .md refused THIS commit of an entirely
                # allowed path, and kept refusing until someone ran `git reset` (W111,
                # lesson mirror_refusal_leaves_tree_staged; two false refusals on a crown
                # doc, 2026-07-31). Same 150-file chunking as rule-8 for the Windows
                # ~32K argv cap.
                staged13 = [f for f in staged.strip().split("\n") if f.endswith(".md")]
                for i in range(0, len(staged13), 150):
                    chunk13 = staged13[i:i + 150]
                    r13 = subprocess.run([sys.executable, hook13, *chunk13],
                                         cwd=ROOT, env=ENV, capture_output=True, text=True)
                    if (r13.stdout or "").strip():
                        print(r13.stdout.strip())
                    if r13.returncode != 0:
                        print("[mirror] rule-13 birth guard REFUSED commit — born-through-the-door: "
                              "py agent_cli.py doc new (or --draft), or fix the path.")
                        sys.exit(1)
        if staged:
            msg = msg or f"Mirror progress {datetime.now():%Y-%m-%d %H:%M}"
            if paths and not add_all:
                git("commit", "-m", msg, "--", *paths)
            else:
                git("commit", "-m", msg)
            committed = git("diff-tree", "--no-commit-id", "--name-only", "-r",
                            "HEAD").stdout.strip() or staged
            print(f"[mirror] committed {len(committed.splitlines())} file(s): {msg}")
            _emit_commit_beat(msg, committed.splitlines())
        else:
            dirty = git("status", "--porcelain").stdout.strip()
            if dirty and not add_all and not paths:
                # refuse to silently do nothing on a dirty tree -- teach the agent
                print("[mirror] nothing staged -- refusing to blanket-commit a shared tree.")
                print("  Name what's YOURS:")
                print('    py scripts/mirror.py "msg" path1 path2   (stage + commit those)')
                print("  or stage first (git add <path>), or --all to sweep everything.")
                print("  Dirty files:")
                print(dirty)
                sys.exit(2)
            print("[mirror] no staged changes to commit")

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
