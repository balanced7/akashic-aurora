#!/usr/bin/env python3
"""Credit the operator as co-author on seat-authored commits.

WHY THIS EXISTS (2026-09-26). T384 makes a seat the AUTHOR of its own work and leaves the
machine owner as COMMITTER -- correct, and it closed a real attribution hole. But GitHub
builds a contribution graph from the AUTHOR, and a seat's address
(`<seat>@akashic-aurora.local`) resolves to no GitHub account. Measured that night:

    2026-07   1282 commits authored by the operator
    2026-08    731 operator + 210 seat
    2026-09      0 operator + 382 seat

382 commits in his biggest month, credited to nobody. The API confirms the mechanism --
`author_login: UNMATCHED, committer_login: balanced7` -- and for a seat whose committer is
also the seat, BOTH are unmatched and the work belongs to no account at all.

A `Co-authored-by` trailer is counted by GitHub for every co-author whose address is linked
to an account. It is ADDITIVE: the seat stays the author, t384 is untouched, and nothing
about who wrote the code is restated.

AND IT IS TRUE, which is why this is not a workaround. These commits happen at his
direction, under his rulings, on his machine, with him as committer. Co-authorship is the
honest description.

CARVE-OUT, STATED SO A LATER SEAT DOES NOT STRIP IT. The house rule is "no Co-Authored-By
trailers", and it exists to stop Claude/Anthropic stamping itself on his work. This trailer
runs the other way -- it credits HIM, never us -- so it is the rule's purpose, not its
violation. Do not add a seat, a model or a vendor here.

Fail-open by construction: any error returns None and the commit proceeds. A credit line is
not worth bricking a commit over.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# The operator's GitHub-linked address. A noreply address is deliberate: it is the one
# GitHub resolves without exposing a real mailbox.
OPERATOR = "balanced7 <61030820+balanced7@users.noreply.github.com>"
OPERATOR_EMAIL = "61030820+balanced7@users.noreply.github.com"

_TRAILER_RE = re.compile(r"^\s*co-authored-by:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def author_email(run=subprocess.run) -> str:
    """The effective author of the commit being written, lowercased ('' if unknowable)."""
    try:
        out = run(["git", "var", "GIT_AUTHOR_IDENT"], capture_output=True, text=True,
                  timeout=15)
        m = re.search(r"<([^>]+)>", out.stdout or "")
        return (m.group(1) if m else "").strip().lower()
    except Exception:
        return ""


def needs_credit(text: str, email: str) -> bool:
    """True when this message should gain the operator's trailer.

    No when he is already the author (the graph counts him anyway), and no when any
    co-author line already names his address -- the hook must be idempotent across amends
    and rebases or a message grows a trailer per attempt.
    """
    if not email or email == OPERATOR_EMAIL.lower():
        return False
    for existing in _TRAILER_RE.findall(text):
        if OPERATOR_EMAIL.lower() in existing.lower():
            return False
    return True


def ensure_operator_coauthor(msg_path, *, run=subprocess.run) -> str | None:
    """Append the trailer to the message file when it is missing. Returns a note, or None.

    Never raises: the caller is a git hook and a crash here would refuse a good commit.
    """
    try:
        p = Path(msg_path)
        text = p.read_text(encoding="utf-8", errors="replace")
        # git's own comment lines are stripped later; a trailer must sit above them, so
        # split them off, append, and put them back exactly as they were.
        lines = text.splitlines(keepends=True)
        body = [l for l in lines if not l.startswith("#")]
        comments = [l for l in lines if l.startswith("#")]
        joined = "".join(body)
        if not needs_credit(joined, author_email(run=run)):
            return None
        if not joined.endswith("\n"):
            joined += "\n"
        if not joined.rstrip("\n").endswith(">"):
            joined += "\n"          # a blank line before a trailer block
        joined += f"Co-authored-by: {OPERATOR}\n"
        p.write_text(joined + "".join(comments), encoding="utf-8")
        return "commit-msg: credited the operator as co-author (t384 keeps the seat as author)"
    except Exception:
        return None
