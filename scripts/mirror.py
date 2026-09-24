"""
mirror.py -- the PUBLISH door: commit named paths and push them to the PUBLIC GitHub repo.

It is not a utility. It does not count, read, diff or inspect anything. Its origin is the
public repo balanced7/akashic-aurora (Apache-2.0), and a push cannot be taken back: once a
commit is on GitHub it is published.

    py scripts/mirror.py "msg" path [path ...]               # DRY RUN: help + the plan, changes nothing
    py scripts/mirror.py "msg" path [path ...] --dry-run     # the plan only
    py scripts/mirror.py "msg" path [path ...] --commit      # stage + commit those paths locally, no push
    py scripts/mirror.py "msg" --commit                      # commit only what is already STAGED
    py scripts/mirror.py "msg" --all --commit                # sweep the WHOLE tree (opt-in)
    py scripts/mirror.py "msg" path [path ...] --push --yes  # commit those paths, then publish
    py scripts/mirror.py --push --yes                        # publish the unpushed commits only

Nothing happens without an intent flag. --commit commits locally and never pushes. --push
publishes, and needs --yes; at a terminal you may instead type the branch name when asked.
Without a terminal and without --yes, --push is refused before anything is staged. Before
it pushes, mirror prints every commit that would be published, and it refuses when any of
them was authored by someone other than the invoking seat unless --include-others is given.
It pushes the exact commit it listed, so a commit landing mid-prompt is not carried along.

WHO MAY RUN IT: Daniel at his own terminal (no AKASHIC_AGENT_ID) and the claude seat. Any
other seat, and any process inside the unattended toolbox door (AKASHIC_SEAT_DOOR=toolbox),
is refused before git is touched. Other seats hand their paths and message to Vandor.

WHY (2026-09-15, commit 97b85ecd): the deepseek seat ran `py scripts/mirror.py
"count-plus-lines" <path>` believing it counted a file's lines. Positional arguments alone
committed a stale .patch file as "count-plus-lines" and pushed it, and the push also
published every unpushed commit since 2026-09-13. Seats' own git verbs are refused under
unattended exec; this script ran git for them. Earlier, `mirror.py --help` committed the
shared index the same way (2026-08-02). These are guards against ACCIDENTS: a determined
process can still call git itself.

Two agents share this working tree, so mirror does NOT blanket-stage by default --
that bundles the other agent's unreviewed work into your commit (the FM1 failure,
2026-06-28; see docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md). Name the paths that are yours, or stage
them first with `git add <path>`. `--all` is the explicit opt-in to stage everything
(it prints the full file list first).

This mirrors the CODE/architecture. Knowledge DATA is not in git -- snapshot it
separately:  py scripts/ops/snapshot_knowledge.py snapshot

Exit codes: 0 done (or --dry-run) | 1 git, guard or push failure | 2 nothing to do, usage,
or the no-flag dry run | 3 refused: not Daniel or the claude seat | 4 refused: the push
would publish other authors' commits | 5 refused: the push was not confirmed
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}   # never hang on a credential prompt

PUBLISHER_SEAT = "claude"
# Seats authorized for the LOCAL-COMMIT leg only (--commit, no push). This list is the
# 2026-09-24 amendment: Daniil authorized ("I authorize amending the mirror.py to allow you
# to make commits") letting admin seats commit their own named paths locally, while the
# PUSH/publish leg stays PUBLISHER_SEAT + Daniel only (a push to the public repo
# balanced7/akashic-aurora cannot be taken back -- that is the 2026-09-15 incident's
# dangerous leg, and it does not broaden). Revert = empty the set.
COMMIT_SEATS = {"deepseek", "kimi", "navi", "heimdall", "sol", "sunshine", "rill"}
EXIT_USAGE, EXIT_SEAT, EXIT_OTHERS, EXIT_UNCONFIRMED = 2, 3, 4, 5


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        sys.exit(r.returncode)
    return r


def runner_refusal(environ=None, push=False):
    """Why this process may not run the mirror at all, or None when it may.

    Two legs are gated separately (2026-09-24 amendment, Daniil's authorization):

      * LOCAL COMMIT (--commit, no push): a seat in COMMIT_SEATS may commit its own named
        paths. The toolbox door is the VERIFIED-caller path for these seats -- AKASHIC_AGENT_ID
        is stamped by the door, not inherited -- and the IR-4 audited family already confined
        the command to canonical script + explicit relative paths + no flags + no trust surfaces.
        A commit never leaves the machine, so it shares no property with the publish incident.

      * PUSH/publish: unchanged. PUBLISHER_SEAT (claude) and Daniel only, and never through the
        unattended toolbox door -- a push to the public repo balanced7/akashic-aurora cannot be
        taken back, and that leg is what 97b85ecd and --help committed (the incidents).

    Uses the identity the doors already stamp: AKASHIC_AGENT_ID (the toolbox door overrides
    any inherited value with the verified caller) and AKASHIC_SEAT_DOOR=toolbox (stamped by
    the unattended runners and by the toolbox's own mirror family). No seat id means Daniel
    at his own terminal, the same reading pre_commit.py makes. The claude seat never runs
    through the toolbox door, so a claude id inside it was inherited from a launcher (the
    2026-07-21 incident) and is refused too."""
    env = os.environ if environ is None else environ
    seat = (env.get("AKASHIC_AGENT_ID") or "").strip()
    door = (env.get("AKASHIC_SEAT_DOOR") or "").strip().lower()

    def _toolbox(why_seat):
        return (f"this process runs inside the unattended toolbox door (AKASHIC_SEAT_DOOR=toolbox, "
                f"AKASHIC_AGENT_ID={why_seat or '(unset)'})")

    if push:
        # The publish leg: no broadening. Refuse the toolbox door and every seat but the publisher.
        if door == "toolbox":
            return _toolbox(seat)
        if seat and seat != PUBLISHER_SEAT:
            return f"this process is the {seat!r} seat (AKASHIC_AGENT_ID={seat}); publishing is {PUBLISHER_SEAT}/Daniel's call"
        return None

    # LOCAL COMMIT leg.
    if door == "toolbox":
        # Verified caller inside the audited IR-4 door: allow a commit-authorized seat.
        if seat in COMMIT_SEATS:
            return None
        return _toolbox(seat)
    # Daniel at his own terminal (no seat id), or the publisher seat, always may commit.
    if not seat or seat == PUBLISHER_SEAT:
        return None
    if seat in COMMIT_SEATS:
        return None
    return f"this process is the {seat!r} seat (AKASHIC_AGENT_ID={seat}) -- not commit-authorized"


def _print_refusal(why):
    print("[mirror] REFUSED: scripts/mirror.py is the PUBLISH door. It commits files and, with\n"
          "  --push, publishes them to the PUBLIC GitHub repo balanced7/akashic-aurora. It does\n"
          "  not count lines, read files or inspect anything.\n"
          f"  {why}.\n"
          "  Nothing was staged, committed or pushed.\n"
          "  To get work committed: commit your own named paths with --commit (no push), or\n"
          "  send Vandor (claude) the explicit paths and a commit message to publish.\n"
          "  (2026-09-15: run as a line counter, it committed 'count-plus-lines' and published\n"
          "  every unpushed commit since 2026-09-13.)")


def _seat_author_env():
    """Author the commit as the seat, the way qm.py and core/comm/seat_identity.git_identity_env
    do, so pre_commit.py's t384 identity check passes and the push check sees the commit as
    the seat's own. Inline rather than imported: tests run a copy of this file in a temp repo."""
    seat = (os.environ.get("AKASHIC_AGENT_ID") or "").strip()
    if seat and not os.environ.get("GIT_AUTHOR_NAME"):
        ENV["GIT_AUTHOR_NAME"] = seat
        ENV["GIT_AUTHOR_EMAIL"] = f"{seat}@akashic-aurora.local"


_OPERATOR = []   # [(user.name, user.email)] once read


def stdin_is_terminal():
    """True only for a real interactive console. On Windows isatty() is also True for the NUL
    device (subprocess.DEVNULL, a detached runner), so ask the console itself."""
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return False
        if os.name != "nt":
            return True
        import ctypes
        import msvcrt
        mode = ctypes.c_ulong()
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    except Exception:
        return False


def _is_own(name, email):
    """Was a commit authored by whoever is invoking the mirror? A seat matches its seat id
    (name, or the local part of seat@akashic-aurora.local); Daniel matches his git config."""
    seat = (os.environ.get("AKASHIC_AGENT_ID") or "").strip()
    if seat:
        return name == seat or email.split("@", 1)[0] == seat
    if not _OPERATOR:
        _OPERATOR.append((git("config", "user.name", check=False).stdout.strip(),
                          git("config", "user.email", check=False).stdout.strip()))
    me_name, me_email = _OPERATOR[0]
    return (bool(me_email) and email == me_email) or (bool(me_name) and name == me_name)


def unpushed(rev="HEAD"):
    """[(sha, author_name, author_email, subject)] reachable from rev and on no origin ref --
    exactly what a push of rev would publish."""
    r = git("log", "--format=%H%x09%an%x09%ae%x09%s", rev, "--not", "--remotes=origin", check=False)
    rows = []
    for line in (r.stdout or "").splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            rows.append(tuple(parts))
    return rows


def _print_publish_list(rows, branch):
    url = git("remote", "get-url", "origin", check=False).stdout.strip() or "(no origin remote)"
    print(f"[mirror] {len(rows)} commit(s) would be published to origin/{branch} ({url}):")
    for sha, name, email, subject in rows:
        mark = "" if _is_own(name, email) else "   <- NOT YOURS"
        print(f"    {sha[:10]}  {name:<12} {subject[:90]}{mark}")


def _foreign(rows):
    return [r for r in rows if not _is_own(r[1], r[2])]


def _refuse_foreign(foreign, committed_locally=False):
    authors = sorted({r[1] for r in foreign})
    print(f"[mirror] REFUSED: {len(foreign)} of those commit(s) were authored by someone else "
          f"({', '.join(authors)}).")
    print("  Publishing them is their author's call, or Daniel's. If that is settled, rerun with "
          "--include-others.")
    if committed_locally:
        print("  Your commit is saved locally; nothing was pushed.")
    return EXIT_OTHERS


def _print_plan(args, branch):
    print("[mirror] DRY RUN -- nothing was staged, committed or pushed.")
    if args.message:
        print(f'  would commit: "{args.message}"')
        if args.all:
            dirty = git("status", "--porcelain").stdout.rstrip()
            print("  staging the ENTIRE working tree (--all):")
            print(dirty or "    (clean)")
        elif args.paths:
            changed = git("status", "--porcelain", "--", *args.paths, check=False).stdout.rstrip()
            print(f"  staging these paths: {' '.join(args.paths)}")
            print(changed or "    (no changes under these paths -- nothing to commit)")
        else:
            staged = git("diff", "--cached", "--name-only").stdout.rstrip()
            print("  committing what is already staged:")
            print(staged or "    (nothing staged -- nothing to commit)")
    rows = unpushed()
    if rows:
        print("  --push would also publish the commits already waiting:")
        _print_publish_list(rows, branch)
    else:
        print(f"  no unpushed commits on {branch}")
    print('  To act: --commit (local only), or --push --yes (commit, then publish).')


def build_parser():
    p = argparse.ArgumentParser(
        prog="mirror.py",
        description="The PUBLISH door: commit named paths and push them to the PUBLIC GitHub repo "
                    "balanced7/akashic-aurora. Not a utility -- it counts and inspects nothing. "
                    "Without --commit or --push it only prints what it would do. Only Daniel and "
                    "the claude seat may run it.")
    p.add_argument("message", nargs="?", help="commit message")
    p.add_argument("paths", nargs="*", help="the EXPLICIT paths to stage and commit")
    p.add_argument("--commit", action="store_true", help="stage the named paths and commit locally; never pushes")
    p.add_argument("--push", action="store_true",
                   help="publish unpushed commits to origin (commits first when a message is given)")
    p.add_argument("--yes", action="store_true",
                   help="confirm --push without a prompt (required when stdin is not a terminal)")
    p.add_argument("--include-others", action="store_true",
                   help="allow publishing commits authored by someone other than the invoking seat")
    p.add_argument("--all", action="store_true", help="with --commit: stage the WHOLE working tree")
    p.add_argument("--dry-run", action="store_true", help="print the plan and exit 0")
    p.add_argument("--push-only", action="store_true", help="old spelling of --push with no message")
    return p


def _commit(args):
    """Stage, run the pre-commit guards, commit. Returns an exit code or None to continue."""
    msg, paths, add_all = args.message, args.paths, args.all
    _seat_author_env()
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
                return 1
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
                    return 1
    if staged:
        if paths and not add_all:
            git("commit", "-m", msg, "--", *paths)
        else:
            git("commit", "-m", msg)
        committed = git("diff-tree", "--no-commit-id", "--name-only", "-r",
                        "HEAD").stdout.strip() or staged
        print(f"[mirror] committed {len(committed.splitlines())} file(s): {msg}")
        _emit_commit_beat(msg, committed.splitlines())
        return None
    dirty = git("status", "--porcelain").stdout.strip()
    if dirty and not add_all and not paths:
        # refuse to silently do nothing on a dirty tree -- teach the agent
        print("[mirror] nothing staged -- refusing to blanket-commit a shared tree.")
        print("  Name what's YOURS:")
        print('    py scripts/mirror.py "msg" path1 path2 --commit   (stage + commit those)')
        print("  or stage first (git add <path>), or --all --commit to sweep everything.")
        print("  Dirty files:")
        print(dirty)
        return EXIT_USAGE
    print("[mirror] no staged changes to commit")
    return None


def _push(args, branch, committed):
    """List exactly what would be published, check authorship, confirm, push that commit."""
    head = git("rev-parse", "HEAD").stdout.strip()
    rows = unpushed(head)
    if not rows:
        print(f"[mirror] nothing to publish -- origin already has {head[:10]} ({branch})")
        return 0
    _print_publish_list(rows, branch)
    foreign = _foreign(rows)
    if foreign and not args.include_others:
        return _refuse_foreign(foreign, committed_locally=committed)
    if not args.yes:
        try:
            answer = input(f'[mirror] Type the branch name "{branch}" to publish {len(rows)} commit(s) '
                           "to the PUBLIC repo: ")
        except EOFError:
            answer = ""
        if answer.strip() != branch:
            print("[mirror] not confirmed -- nothing was pushed"
                  + (" (your commit is saved locally)." if committed else "."))
            return EXIT_UNCONFIRMED
    # Push the listed commit, not the branch: a commit that lands while the prompt waits
    # must not ride along unlisted.
    push = git("push", "origin", f"{head}:refs/heads/{branch}", check=False)
    out = ((push.stdout or "") + (push.stderr or "")).strip()
    if push.returncode == 0:
        print(f"[mirror] pushed {len(rows)} commit(s) to origin/{branch} (now at {head[:10]})")
        return 0
    print(f"[mirror] PUSH FAILED (commit is saved locally):\n{out}")
    print("  -> if auth expired: run `gh auth login` then re-run this.")
    return 1


def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")   # commit subjects can carry characters a cp1252 console lacks
    except AttributeError:
        pass
    parser = build_parser()
    args = parser.parse_intermixed_args(argv)

    # Resolve --push-only before the refusal so the push leg is gated correctly.
    if getattr(args, "push_only", False):
        args.push = True
    why = runner_refusal(push=bool(getattr(args, "push", False)))
    if why:
        _print_refusal(why)
        return EXIT_SEAT

    if args.push_only:
        if args.message:
            parser.error("--push-only takes no message; use --push to commit and publish")
        args.push = True
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    if args.dry_run or not (args.commit or args.push):
        if not args.dry_run:
            parser.print_help()
            print()
        _print_plan(args, branch)
        return 0 if args.dry_run else EXIT_USAGE

    if args.commit and not args.message:
        parser.error('--commit needs a message: py scripts/mirror.py "msg" <paths> --commit')
    if (args.all or args.paths) and not args.message:
        parser.error("paths and --all need a commit message")
    if args.push:
        if branch == "HEAD":
            print("[mirror] refusing to push a detached HEAD -- check out a branch first.")
            return EXIT_USAGE
        if not args.yes and not stdin_is_terminal():
            print("[mirror] REFUSED: --push publishes to the PUBLIC repo and needs --yes when stdin is "
                  "not a terminal. Nothing was staged, committed or pushed.")
            return EXIT_UNCONFIRMED
        # Refuse before committing when the waiting commits already fail the author check.
        waiting = unpushed()
        foreign = _foreign(waiting)
        if foreign and not args.include_others:
            _print_publish_list(waiting, branch)
            return _refuse_foreign(foreign)

    committed = False
    if args.message:
        before = git("rev-parse", "HEAD", check=False).stdout.strip()
        code = _commit(args)
        if code is not None:
            return code
        committed = git("rev-parse", "HEAD", check=False).stdout.strip() != before
    if not args.push:
        return 0
    return _push(args, branch, committed)


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


if __name__ == "__main__":
    sys.exit(main())
