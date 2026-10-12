#!/usr/bin/env python3
"""Which seat built which commit -- a plane that survives the author field being overwritten.

DANIEL'S RULING, 2026-09-26, verbatim: "If we need to have a second plane to track ideas and who
built what, so be it, but the commits should display with my name on the github project page."
And: "I've been pouring the best of my thinking into this for months, spent over 1 grand in
credits and tokens to build this thing, I want my name on it."

This inverts t384, which made the seat the git AUTHOR. That was right about one thing -- a seat's
work should be attributable -- and wrong about where to put it, because git's author field is
also GitHub's display field and its contribution graph. One field was carrying two jobs, so the
attribution won and the operator's name lost. This file takes the attribution job so the author
field can go back to doing the other one.

WHY THIS MUST BE BUILT FIRST, AND WHY THAT IS NOT A FORMALITY. For 537 of the 598 seat-authored
commits the committer is ALREADY the operator, so the author field is the ONLY place the seat is
recorded. A rewrite that sets author=operator without capturing this first destroys the record
it is trying to preserve, silently and irreversibly. The ledger is the prerequisite, not the
follow-up.

KEYED TWO WAYS ON PURPOSE. A rewrite changes every SHA, so a ledger keyed on SHA alone goes stale
the moment it is used. Each row therefore carries:

  sha    the commit as it stands now -- exact, and mortal
  key    (author-date, subject) -- survives a rewrite, since neither is touched by one

After a rewrite, `rekey` walks the T410 commit-maps to find each row's successor and CONFIRMS it
against the stable key before writing it. Two independent routes to the same answer, and it
refuses when they disagree.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: Where the ledger lived while it was tracked in git. Read once to seed the local ledger.
LEGACY = ROOT / "state" / "authorship" / "seats.jsonl"
#: Points the ledger somewhere else (tests, a relocated home).
LEDGER_ENV = "AKASHIC_AUTHORSHIP_LEDGER"
#: What a commit-time row copies from the session's provenance record (core/fleet/provenance.py).
#: A snapshot, because effort and config can change inside one session; `provenance` points at
#: the full session record.
PROVENANCE_FIELDS = (
    "session_id",
    "provenance",
    "harness",
    "harness_version",
    "model",
    "effort",
    "project_fingerprint",
    "user_fingerprint",
    "branch",
)
SEP = "\x1f"


def ledger_path() -> Path:
    """The local ledger: <shared state root>/state/authorship/seats.jsonl.

    LOCAL, NOT TRACKED (2026-10-12). The ledger used to be committed, so every push published
    which agent seat made which commit. Which session, harness, model and effort produced a
    commit is our working record, not public repository data, so it now lives in the world's
    instance state, the same place as the transcript index and the embedded Redis files. Every
    checkout and worktree of a world writes to the one file. Without an Aurora home it falls back
    to the old path, which git now ignores.
    """
    override = (os.getenv(LEDGER_ENV) or "").strip()
    if override:
        return Path(override)
    try:
        from core.paths import shared_state_root

        return shared_state_root() / "state" / "authorship" / "seats.jsonl"
    except Exception:
        return LEGACY


def _seed(path: Path) -> None:
    """First use of a local ledger: copy the rows the tracked ledger held, so nothing is lost
    when a checkout drops the tracked file."""
    if path.exists() or path.resolve() == LEGACY.resolve() or not LEGACY.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(LEGACY.read_bytes())
    _seal(path)


def _seal(path: Path) -> None:
    """Make the file read-only between appends, so an editor or a stray write cannot change a
    recorded row. Only append() and the explicit rewrite verbs (build, rekey) unseal it."""
    with contextlib.suppress(OSError):
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def _unseal(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def append(row: dict) -> Path:
    """Add one row at the end. Rows are written once and never edited here; a correction is a
    new row. Returns the ledger path."""
    path = ledger_path()
    _seed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    _unseal(path)
    try:
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
    finally:
        _seal(path)
    return path


def _rewrite(rows) -> Path:
    """The one place a whole ledger is replaced: `build` and `rekey --write`, run on purpose."""
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _unseal(path)
    try:
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    finally:
        _seal(path)
    return path


# The operator's GitHub-linked address, and the placeholder an unconfigured git left behind.
OPERATOR = "61030820+balanced7@users.noreply.github.com"
PLACEHOLDER = "you@email.com"


def git(*a, root=None):
    p = subprocess.run(
        ["git", "-C", str(root or ROOT), *a], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return p.stdout or ""


def history(root=None):
    """Every commit as (sha, author_name, author_email, at, subject, committer_email)."""
    fmt = SEP.join(["%H", "%an", "%ae", "%at", "%s", "%ce"])
    for line in git("log", "--all", "--format=" + fmt, root=root).splitlines():
        p = line.split(SEP)
        if len(p) >= 6:
            # a subject containing the separator would split further; rejoin the middle
            yield (p[0], p[1], p[2], p[3], SEP.join(p[4:-1]), p[-1])


def cmd_build(args):
    """Record every commit an identity other than the operator authored."""
    rows, seats = [], Counter()
    for sha, an, ae, at, subj, ce in history():
        if ae == OPERATOR:
            continue
        seat = "operator-unconfigured-git" if ae == PLACEHOLDER else ae.split("@")[0]
        rows.append(
            {
                "sha": sha,
                "seat": seat,
                "seat_name": an,
                "seat_email": ae,
                "at": at,
                "subject": subj,
                "committer_email": ce,
            }
        )
        seats[seat] += 1
    if not rows:
        raise SystemExit("no non-operator-authored commits found -- nothing to record")

    # Sorted by author date so the file reads as a history and diffs stay local.
    rows.sort(key=lambda r: (int(r["at"]), r["sha"]))
    path = _rewrite(rows)

    print(f"wrote {len(rows):,} rows -> {path}")
    for seat, n in seats.most_common():
        print(f"  {seat:<28} {n:,}")
    dup = _ambiguous_keys(rows)
    print(f"\nrows whose (author-date, subject) is shared inside this ledger: {dup:,}")
    print("  (rekey resolves those by SHA and refuses to guess)")
    return 0


def _ambiguous_keys(rows):
    c = Counter((r["at"], r["subject"]) for r in rows)
    return sum(n for n in c.values() if n > 1)


def load():
    """Every row: the local ledger, or the tracked one when no local ledger exists yet."""
    path = ledger_path()
    if not path.is_file():
        path = LEGACY
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def cmd_rekey(args):
    """After a rewrite: move every row onto its successor SHA, confirming by the stable key."""
    from core.git.rewrite_map import Resolver

    rows = load()
    if not rows:
        raise SystemExit(f"{ledger_path()} is empty -- run `build` before the rewrite, not after")
    r = Resolver(repo=ROOT)
    live = {}
    for sha, _an, _ae, at, subj, _ce in history():
        live.setdefault((at, subj), []).append(sha)

    # PRECONDITION, stated loudly because getting it wrong produces a very convincing wrong
    # number. Run before the rewrite lands, every row's map target is absent from this repo while
    # the stable key still finds the OLD commit -- so the two routes disagree on almost every row
    # and the report reads as 593 corrupt rows instead of "you ran this too early". Measured
    # exactly that on the first attempt.
    # Sample the NEWEST rows, not the oldest. The oldest chains terminate on identity rows -- a
    # rewrite leaves a commit alone when its identities were already the operator's -- so a
    # head-of-file sample sees no absent targets and the precondition silently fails to fire,
    # which is exactly what happened on the first attempt.
    sample = rows[-40:]
    hits = 0
    for row in sample:
        res = r.resolve(row["sha"], check_remote=False)
        if res.ok and res.sha and res.sha not in {s for v in live.values() for s in v}:
            hits += 1
    if sample and hits > len(sample) * 0.5:
        print(
            f"REFUSING: {hits} of {len(sample)} sampled map targets do not exist in this "
            f"repository.\n"
            f"  The maps describe a rewrite that has NOT been applied here yet, so every\n"
            f"  comparison would disagree and the output would look like mass corruption.\n"
            f"  Apply the rewrite first, then run rekey. Nothing was changed."
        )
        return 1

    moved = kept = refused = lost = 0
    for row in rows:
        res = r.resolve(row["sha"], check_remote=False)
        by_map = res.sha if res.ok else None
        hits = live.get((row["at"], row["subject"])) or []
        if len(hits) > 1:
            # AMBIGUOUS BECAUSE BOTH LINEAGES ARE STILL HERE. After a rewrite this machine keeps
            # the pre-rewrite lineage alive on local refs (pre-rewrite-backup, refs/original), so
            # a commit and its own successor share (author-date, subject) and the key matches
            # two. Prefer the one a CLONE can see: that is the live answer, and the other is the
            # ancestor we just superseded. Same rule T410's resolver uses, one plane up.
            visible = [h for h in hits if r.visible(h)]
            hits = visible if len(visible) == 1 else hits
        by_key = hits[0] if len(hits) == 1 else None

        if by_map and by_key and by_map != by_key:
            # Two independent routes disagreeing is exactly the case not to guess through.
            row["rekey"] = "REFUSED: the map and the stable key name different commits"
            row["map_says"], row["key_says"] = by_map, by_key
            refused += 1
            continue
        target = by_map or by_key
        if not target:
            row["rekey"] = "no successor found by map or by key"
            lost += 1
            continue
        if target == row["sha"]:
            kept += 1
            continue
        row["was_sha"], row["sha"] = row["sha"], target
        row["rekey"] = "map+key agree" if (by_map and by_key) else ("map only" if by_map else "stable key only")
        moved += 1

    print(f"rows: {len(rows):,}")
    print(f"  moved to a successor : {moved:,}")
    print(f"  already current      : {kept:,}")
    print(f"  REFUSED (disagreement): {refused:,}")
    print(f"  no successor found   : {lost:,}")
    if not args.write:
        print("\n(dry run -- pass --write to update the ledger)")
        return 1 if refused else 0
    print(f"\nupdated {_rewrite(rows)}")
    return 1 if refused else 0


def seat_for(sha, rows=None):
    """The seat that authored a commit, by SHA or by any unambiguous prefix."""
    rows = rows if rows is not None else load()
    sha = (sha or "").strip().lower()
    if not sha:
        return None
    hits = [r for r in rows if r["sha"].startswith(sha) or r.get("was_sha", "").startswith(sha)]
    return hits[0] if len(hits) == 1 else None


def cmd_who(args):
    rows = load()
    if not rows:
        raise SystemExit(f"no ledger at {ledger_path()} -- run `build`")
    for sha in args.sha:
        hit = seat_for(sha, rows)
        if not hit:
            print(f"  {sha}  no ledger row (the operator authored it, or the id is ambiguous)")
            continue
        was = f"  (was {hit['was_sha'][:12]})" if hit.get("was_sha") else ""
        print(f"  {sha}  {hit['seat']}{was}")
        print(f"      {hit['subject'][:88]}")
        made = [f"{k}={hit[k]}" for k in PROVENANCE_FIELDS if hit.get(k) and hit[k] != "unknown"]
        if made:
            print(f"      {' '.join(made)}")
    return 0


def cmd_verify(args):
    """Every row must name a commit that exists, and its stable key must still match."""
    rows = load()
    if not rows:
        raise SystemExit(f"no ledger at {ledger_path()}")
    byhash = {sha: (at, subj) for sha, _n, _e, at, subj, _c in history()}
    missing = [r for r in rows if r["sha"] not in byhash]
    drifted = [r for r in rows if r["sha"] in byhash and byhash[r["sha"]] != (r["at"], r["subject"])]
    print(f"rows: {len(rows):,}")
    print(f"  SHA names no commit here : {len(missing):,}")
    print(f"  stable key disagrees     : {len(drifted):,}")
    for r in (missing + drifted)[:6]:
        print(f"    {r['sha'][:12]}  {r['seat']:<12} {r['subject'][:58]}")
    if missing:
        print("\n  A row whose SHA is gone is what `rekey` is for -- run it after a rewrite.")
    return 1 if (missing or drifted) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="record who authored what, from the live history")
    b.set_defaults(fn=cmd_build)
    k = sub.add_parser("rekey", help="after a rewrite, move rows onto their successors")
    k.add_argument("--write", action="store_true")
    k.set_defaults(fn=cmd_rekey)
    w = sub.add_parser("who", help="which seat authored these commits")
    w.add_argument("sha", nargs="+")
    w.set_defaults(fn=cmd_who)
    v = sub.add_parser("verify", help="every row still names a real commit")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
