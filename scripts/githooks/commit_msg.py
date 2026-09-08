#!/usr/bin/env python3
"""Git commit-msg backstop: refuse a commit MESSAGE that names private-plane content.

WHY A SEPARATE STAGE (defer dd0c36b406). The private-plane guard covers two things: the
STAGED FILES (scripts/githooks/pre_commit.py, unchanged) and the COMMIT MESSAGE -- a derived
description of the work, and a derived record does not inherit its sources' visibility
(four pushed messages named private artifacts on 2026-08-16 while every staged file was
clean). The message scan first lived in pre-commit and read git's message file from there.
git writes that file AFTER the pre-commit stage runs, so pre-commit was judging commit N by
commit N-1's message: a marker-naming message passed its own commit and the clean commit
after it was refused. In a linked worktree `.git` is a file, so the read failed silently and
the scan never ran at all.

git's commit-msg stage receives the LIVE message file as argv[1] -- the one place where the
message being committed is the message that gets scanned. `git commit --no-verify` skips
this stage together with pre-commit, so the sanctioned emergency bypass is unchanged.

FAIL-OPEN ON A CRASH, LOUDLY. Same policy as pre_commit.py: a guard that cannot run must not
brick every commit, but it must never look like a pass -- absence that reads as success is
the defect this house has paid for repeatedly. A FINDING fails CLOSED even if the refusal
cannot be printed: the decision never depends on the console.

Install once per clone/worktree:  py scripts/githooks/install_git_hooks.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

# Test seam: point the guard at a plane that is not this checkout's (a hermetic git repo
# under pytest). Unset in production, where core.trust.private_plane derives the plane from
# its own location.
PLANE_ROOT_ENV = "AKASHIC_PRIVATE_PLANE_ROOT"
LABEL = "commit message"
COMMENT_CHAR = "#"          # git's default core.commentChar
SCISSORS = "------------------------ >8 ------------------------"


def message_body(text, comment_char=COMMENT_CHAR):
    """The part of the message file git will actually record.

    git's default cleanup drops comment lines and everything from a scissors line down
    (`git commit -v` puts the staged diff there) BEFORE creating the commit, and its status
    template lists branch names and paths under the comment char. None of that can leak; a
    guard that refused on it would fire on healthy commits, and a guard that fires on
    healthy commits gets --no-verify'd until it guards nothing."""
    kept = []
    for line in str(text or "").splitlines():
        if line.startswith(comment_char):
            if SCISSORS in line:
                break
            continue
        kept.append(line)
    return "\n".join(kept)


def _plane_root(root):
    if root is not None:
        return root
    return os.environ.get(PLANE_ROOT_ENV) or None


def scan_message(path, root=None):
    """Findings for the message file git handed this stage. Raises when the guard itself is
    broken (unreadable path, missing module) so main() can fail open LOUDLY."""
    from core.trust.private_plane import scan_text
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return scan_text(message_body(text), label=LABEL, root=_plane_root(root))


def refusal(findings):
    out = ["commit-msg BLOCKED: the commit message carries PRIVATE-PLANE identifiers.\n"]
    for f in findings[:6]:
        out.append(f"  {f['path']} -- marker {f['marker']!r}\n    {f['remedy']}\n")
    out.append("  Existence metadata is a leak: an id or title alone is enough, no body "
               "required.\n  Nothing was committed and the index is untouched: rewrite the "
               "message and commit again.\n  Emergency bypass: `git commit --no-verify` -- "
               "and if you use it, say so out loud, because this one does not fail safe.\n")
    return "".join(out)


def _say(text):
    """Best-effort stderr. Printing must never decide the outcome."""
    try:
        sys.stderr.write(text)
    except Exception:
        pass


def main(argv=None, root=None):
    argv = sys.argv if argv is None else argv
    try:
        # a marker the console's codepage cannot print must not turn a refusal into a crash
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass
    if len(argv) < 2 or not argv[1]:
        _say("commit-msg WARNING: git passed no message path, so the private-plane message "
             "guard did not run. Commit allowed; the gate is not protecting you.\n")
        return 0
    try:
        findings = scan_message(argv[1], root=root)
    except Exception as exc:
        _say("commit-msg WARNING: the private-plane message guard did not run (%s: %s). "
             "Commit allowed; the gate is not protecting you.\n" % (type(exc).__name__, exc))
        return 0
    if not findings:
        return 0
    _say(refusal(findings))
    return 1


if __name__ == "__main__":
    sys.exit(main())
