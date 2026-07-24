"""Git-safety policy (Concurrency design Layer 2, slice C0).

THE RULE: never let an agent blanket-stage the working tree. In a two-agent shared
tree, `git add -A` / `git add .` / `git commit -a` bundle the OTHER agent's
unreviewed, in-progress changes into your commit and push them -- the FM1 failure
observed 2026-06-28 (see docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md). Stage explicit pathspecs, or
use `py scripts/mirror.py "msg" <paths...>`.

This module is the single rulebook. Both hooks -- agent/harness/hooks/claude_pretooluse.py
and agent/harness/hooks/cursor_beforeshell.py -- call check_git_command() so the policy
cannot drift between Claude and Cursor. Enforcement lives in the harness (the hook),
not in the agent's memory, because agents skip docs.
"""
from __future__ import annotations

import re
import shlex
from typing import Tuple

# args to `git add` that stage indiscriminately
_ADD_BLANKET = {"-A", "--all", ".", ":/", ":"}

_REASON = (
    "BLOCKED: blanket git staging ({hit}). Two agents share this working tree -- this "
    "bundles the OTHER agent's unreviewed changes into your commit and pushes them "
    "(the FM1 failure, 2026-06-28). Stage what is YOURS explicitly:\n"
    "  git add <path...>   then commit\n"
    '  or  py scripts/mirror.py "msg" <path...>\n'
    "Need to sweep everything anyway? `py scripts/mirror.py \"msg\" --all` is the "
    "explicit opt-in. See docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md (Layer 2 / C0)."
)


def _segments(command: str):
    """Split a (possibly compound) shell command on ; | & so each git invocation is
    inspected on its own (covers `cd x && git add -A`, `a | git add .`, etc.)."""
    return re.split(r"[;|&]+", command or "")


def _tokens(segment: str):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def check_git_command(command: str) -> Tuple[bool, str]:
    """Inspect a shell command. Return (allowed, reason).

    allowed=False means the caller (a hook) should DENY the command. The reason is
    written FOR the agent -- it names the violated rule and the correct next action
    ("errors that teach"). Never raises.
    """
    try:
        for seg in _segments(command):
            toks = _tokens(seg)
            if "git" not in toks:
                continue
            rest = toks[toks.index("git") + 1:]   # tolerate env-var prefixes before `git`
            if len(rest) < 1:
                continue
            sub, args = rest[0], rest[1:]
            if sub == "add" and any(a in _ADD_BLANKET for a in args):
                hit = ("git add " + " ".join(a for a in args if a in _ADD_BLANKET)).strip()
                return False, _REASON.format(hit=hit)
            if sub == "commit":
                # -a / -am / - am ... stages every tracked file (a short flag containing 'a')
                for a in args:
                    if a.startswith("-") and not a.startswith("--") and "a" in a[1:]:
                        return False, _REASON.format(hit="git commit " + a)
    except Exception:
        return True, ""   # a guard must never brick the agent -> fail open
    return True, ""
