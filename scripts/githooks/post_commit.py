#!/usr/bin/env python3
"""post-commit -> record WHICH SEAT made this commit, because git can no longer say.

WHY THIS EXISTS, and it is a hole this repo opened on purpose and then left open.

2026-09-27, T411: every commit's author AND committer were inverted to the operator
(balanced7) so GitHub's contribution graph credits Daniel for the house's work. The stated
trade was that seat attribution moves to an INTERNAL plane -- "our tracking for who does what
is internal and if someone wants that they can scrape for it".

The internal plane was built (state/authorship/) and populated ONCE from history. It was never
wired to receive anything after that, and its builder cannot help: authorship_ledger.cmd_build
records commits whose author email is NOT the operator, and after the inversion that set is
empty by construction. So every commit made since the inversion has attribution NOWHERE -- not
on the git plane (deliberately erased) and not on the internal one (never written).

Measured 2026-09-28: `authorship_ledger.py who <sha>` answers "no ledger row" for all 17
commits of that day, and scripts/mirror.py -- which refuses to publish commits authored by
someone other than the invoking seat -- flagged every one of them NOT YOURS and refused the
push. A guard that cannot see ownership does not fail open or closed; it fails BLIND, and the
tempting move is to wave it through with --include-others, which converts a real check into a
formality permanently.

So: the seat is recorded HERE, at the moment of the commit, from the environment that made it.
That is the only place the fact still exists.

LOCAL SINCE 2026-10-12. The row goes to the world's local ledger (authorship_ledger.ledger_path()),
never into the repository, and it also records the session, harness, model and effort that made
the commit. That is our working record; a public commit carries only the operator.

FAIL-OPEN, ALWAYS. A commit that has already happened must never be undone by its own
bookkeeping, and a missing row is recoverable (the sha and its subject are in git forever)
while a refused commit loses work. Every failure path exits 0 in silence.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _git(*args):
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, stdin=subprocess.DEVNULL, close_fds=True)
    if out.returncode != 0:
        raise RuntimeError("git failed")
    return out.stdout.decode("utf-8", "replace").strip()


def seat() -> str:
    """The seat that made this commit, or '' when nothing declares one.

    An UNDECLARED seat writes no row rather than guessing 'claude': a wrong attribution is
    worse than an absent one, because absence is visibly absent while a wrong name is
    indistinguishable from a right one and survives into every later read.
    """
    for var in ("AKASHIC_AGENT_ID", "AKASHIC_SEAT", "AI_AGENT"):
        v = (os.environ.get(var) or "").strip()
        if v:
            return v.split("_")[0].split("-")[0][:40]
    return ""


def main() -> int:
    try:
        who = seat()
        if not who:
            return 0  # nothing declared -> no row, no guess
        sha, at, subject, ce = _git("log", "-1", "--format=%H%n%at%n%s%n%ce").split("\n", 3)
        row = {
            "sha": sha[:12],
            "seat": who,
            "at": at,
            "subject": subject,
            "committer_email": ce,
            # How this row was decided, so a later reader can tell a recorded fact from a
            # reconstructed guess. cmd_build's rows carry seat_email; these cannot.
            "seat_source": "env-at-commit",
        }
        row.update(made_by())
        from scripts.authorship_ledger import append

        append(row)
    except Exception:
        return 0  # bookkeeping never costs a commit
    return 0


def made_by() -> dict:
    """The session, harness, model and effort that made this commit, as known right now.

    This is why the ledger is local: the commit shows only the operator, and this row is where
    the rest of the story lives, joined to the session's full record by `provenance`. Fields a
    harness does not expose stay out of the row rather than reading as a guess. Never raises.
    """
    try:
        from core.fleet import provenance
        from scripts.authorship_ledger import PROVENANCE_FIELDS

        rec = provenance.detect(env=os.environ)
        rec["provenance"] = provenance.pointer(rec.get("session_id", ""))
        return {k: rec[k] for k in PROVENANCE_FIELDS if rec.get(k) and rec[k] != provenance.UNKNOWN}
    except Exception:
        return {}


if __name__ == "__main__":
    sys.exit(main())
