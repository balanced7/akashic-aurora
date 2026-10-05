#!/usr/bin/env python3
"""Survive a history rewrite: capture its map, rebuild a map we lost, measure the damage.

T410, built 2026-09-26 after finding that this repo has run THREE rewrites and kept usable
maps for two -- one of them only in .git/filter-repo/commit-map, which the next run overwrites.
The third was found by accident, from a stray refs/original ref.

Three subcommands, one per failure we actually had:

  capture      A rewrite just ran. Move its map somewhere that travels with a clone, with a
               meta.json saying what it did and why, BEFORE the next run clobbers it.

  reconstruct  A rewrite ran and its map is gone. Rebuild it by matching the old lineage
               against the new one on (author-date, subject) -- measured 116 of 118 orphans
               with zero ambiguity here. REFUSES on collisions instead of guessing: 34 keys
               in our own history are shared by 68 commits, and a wrong successor rewrites
               history a second time.

  census       How healthy are our SHA citations right now? Run before a rewrite for a
               baseline and after it to see what moved. This is the instrument that found
               877 already-broken citations nobody had noticed in 65 days.

A reconstructed map is an INFERENCE, not a record. meta.json records which it is, and the
resolver reports it, because a caller deserves to know whether a successor was recorded by the
tool that made it or deduced afterwards.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SEP = "\x1f"
HEX = re.compile(rb"\b[0-9a-f]{7,40}\b")
CORPUS = ["docs/", "research/", "fences/", "chronicles/", "*.md", "state/coord/"]


def repo(args):
    return Path(getattr(args, "repo", None) or os.environ.get("AKASHIC_REPO") or ROOT)


def git(root, *a, check=False):
    p = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode:
        raise SystemExit(f"git {' '.join(a)} failed:\n{p.stderr}")
    return p.stdout or ""


def parents_of(root, *revs):
    """oid -> tuple(parent oids). A rewrite preserves parent STRUCTURE by definition, which is
    what makes this the strongest corroboration available and the cheapest: one git call."""
    out = {}
    for ln in git(root, "log", "--format=%H %P", *revs).splitlines():
        parts = ln.split()
        if parts:
            out[parts[0]] = tuple(parts[1:])
    return out


def parents_for(root, oids):
    """Parents for every named oid, including commits on NO branch.

    `log --all` walks refs, so a commit sitting on no branch -- the case a git gc would delete,
    and the case our worst citation was in -- has no entry and the parent check silently cannot
    fire. Ask for those by name.
    """
    out = parents_of(root, "--all")
    missing = [o for o in oids if o not in out]
    for i in range(0, len(missing), 200):  # keep the argv well inside Windows' limit
        out.update(parents_of(root, "--no-walk", *missing[i : i + 200]))
    return out


def corroborate(old, new, parents, matched, resolve_parent=None, key_of=None):
    """Which independent structural signals agree that `old` became `new`?

    (author-date, subject) is a NAME match. These are CONTENT and SHAPE matches, and they fail
    independently of it -- a date/subject coincidence has no reason to also agree here.

      tree    the rewrite preserved content, so the tree hash is unchanged. Necessary for any
              tree-preserving rewrite (an author/message rewrite); silent on a redaction.
      parent  the parent count matches and the first parent corresponds -- either it is itself
              a matched pair, or the two carry the same (author-date, subject). A rewrite
              preserves this by construction; a coincidence has no reason to.

    Returns the set of signals that AGREE. An empty set means the row rests on the name alone.
    """
    agree = set()
    if old[0] and old[0] == new[0]:
        agree.add("tree")
    po, pn = parents.get(old[4]), parents.get(new[4])
    if po is not None and pn is not None and len(po) == len(pn):
        if not po:
            agree.add("parent")  # both roots: structurally consistent
        else:
            a, b = po[0], pn[0]
            hit = matched.get(a) == b or a == b
            if not hit and resolve_parent is not None:
                # An EXISTING map may already carry the parent's remap, which is stronger
                # evidence than this run's own inferences and was being thrown away.
                hit = resolve_parent(a) == b
            if hit:
                agree.add("parent")
            elif key_of is not None and key_of(a) and key_of(a) == key_of(b):
                # WEAKER TIER, kept separate so the report never overstates it: the two parents
                # carry the same (author-date, subject). That is the same name heuristic one
                # generation up, so it is not independent of the METHOD -- but it IS independent
                # of THIS commit, and requiring a second name coincidence in a parent-child
                # relationship is far stronger than one alone. It is what corroborates a
                # redaction-rewritten parent, whose tree necessarily changed.
                agree.add("parent-key")
    return agree


def commit_rows(root, *revs):
    """oid -> (tree, author-date-unix, author-email, subject) for a rev set."""
    out = git(root, "log", "--format=%H" + SEP + "%T" + SEP + "%at" + SEP + "%ae" + SEP + "%s", *revs)
    rows = {}
    for ln in out.splitlines():
        p = ln.split(SEP)
        if len(p) >= 5:
            # (tree, author-date, author-email, subject, oid) -- the oid rides along so a
            # corroboration check can reach the commit graph without a second lookup table.
            rows[p[0]] = (p[1], p[2], p[3], SEP.join(p[4:]), p[0])
    return rows


# ------------------------------------------------------------------------------ capture
def cmd_capture(args):
    root = repo(args)
    src = Path(args.map or (root / ".git" / "filter-repo" / "commit-map"))
    if not src.is_file():
        raise SystemExit(
            f"no map at {src}\n"
            f"  filter-repo writes one per run; filter-branch writes none at all.\n"
            f"  If the rewrite is already done and the map is gone, use:\n"
            f"    {_pyl()} scripts/rewrite_recover.py reconstruct --from-ref <old-ref>"
        )
    dest = root / "state" / "rewrites" / f"{args.date or date.today().isoformat()}"
    if args.label:
        dest = dest.with_name(dest.name + "-" + args.label)
    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} already exists; pass --force to overwrite")
    dest.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8", errors="replace")
    (dest / "commit-map").write_text(text, encoding="utf-8")

    rows = [ln.split() for ln in text.splitlines()]
    pairs = [p for p in rows if len(p) == 2 and len(p[0]) == 40 == len(p[1])]
    dropped = [p for p in pairs if p[1] == "0" * 40]
    meta = {
        "date": args.date or date.today().isoformat(),
        "tool": args.tool,
        "why": args.why or "(not recorded -- fill this in; a map without a reason is a puzzle)",
        "remaps": len(pairs) - len(dropped),
        "dropped": len(dropped),
        "method": "recorded",
        "map_recovered_from": str(src),
        "map_archived": date.today().isoformat(),
        "archived_by": os.environ.get("AKASHIC_AGENT_ID", "unknown"),
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"captured {meta['remaps']:,} remaps ({meta['dropped']} dropped) -> {dest}")
    print("  COMMIT THIS. A map on an ignored or untracked path is invisible to every clone,")
    print("  so no clone can resolve any citation -- which is the defect T410 exists to close.")
    return 0


# -------------------------------------------------------------------------- reconstruct
def cited_orphans(root, new):
    """Full oids for commits our corpus CITES that the target lineage cannot see.

    A ref-based lineage misses the cases that hurt most: a commit on no branch at all (one
    `git gc` from deletion, and we have one cited in docs/WISHLIST.md), and a commit whose
    recorded successor was itself moved again. Citations are the population we actually owe an
    answer for, so take them as the input directly.
    """
    cand = cited_shas(root)
    probe = "\n".join(f"{s}^{{commit}}" for s in cand) + "\n"
    out = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch-check"], input=probe, capture_output=True, text=True
    ).stdout.splitlines()
    oids = set()
    for line, _sha in zip(out, cand, strict=False):
        p = line.split()
        if len(p) == 3 and p[1] == "commit" and p[0] not in new:
            oids.add(p[0])
    return oids


def cmd_reconstruct(args):
    root = repo(args)
    new = commit_rows(root, *args.to)
    if args.from_citations:
        want = cited_orphans(root, new)
        old = {o: v for o, v in commit_rows(root, "--all").items() if o in want}
        # A cited commit on no branch is absent from --all, so ask git for it by name.
        for oid in want - set(old):
            row = commit_rows(root, "--no-walk", oid)
            old.update(row)
        if not old:
            raise SystemExit("every cited commit is already visible in the target lineage")
    else:
        old = commit_rows(root, *args.from_ref)
        if not old:
            raise SystemExit(f"no commits reachable from {args.from_ref}")
    orphans = {o: v for o, v in old.items() if o not in new}

    idx = defaultdict(list)
    for oid, v in new.items():
        idx[(v[1], v[3])].append(oid)  # (author-date, subject)

    matched, ambiguous, unmatched = {}, {}, []
    for oid, v in orphans.items():
        hits = idx.get((v[1], v[3]), [])
        if len(hits) == 1:
            matched[oid] = hits[0]
        elif hits:
            ambiguous[oid] = hits
        else:
            unmatched.append(oid)

    # CORROBORATE EVERY ROW. A row resting only on (author-date, subject) is a NAME match with
    # nothing independent behind it; 34 keys in this history are shared by 68 commits, so the
    # name alone is not enough to license a row a resolver will treat as an answer.
    parents = parents_for(root, list(matched) + list(matched.values()))
    from core.git.rewrite_map import Resolver as _R

    _res = _R(repo=root)

    def _parent(sha):
        r = _res.resolve(sha, check_remote=False)
        return r.sha if r.ok else None

    # The parents are usually in NEITHER matched population, so a key lookup built from those
    # two dicts alone returns None for every parent and the tier can never fire. Fetch the
    # parents by name -- including any on no branch, which `log --all` cannot see.
    _keys = dict(old)
    _keys.update(new)
    _want = [q for ps in parents.values() for q in ps if q not in _keys]
    for i in range(0, len(_want), 200):
        _keys.update(commit_rows(root, "--no-walk", *_want[i : i + 200]))

    def _key(sha):
        row = _keys.get(sha)
        return (row[1], row[3]) if row else None

    signals = {
        o: corroborate(old[o], new[n], parents, matched, resolve_parent=_parent, key_of=_key)
        for o, n in matched.items()
    }
    tree_agree = sum(1 for v in signals.values() if "tree" in v)
    parent_agree = sum(1 for v in signals.values() if "parent" in v)
    pkey_agree = sum(1 for v in signals.values() if "parent-key" in v)
    uncorroborated = sorted(o for o, v in signals.items() if not v)
    print(f"old lineage ({', '.join(args.from_ref)}) : {len(old):,} commits")
    print(f"  orphaned (absent from {' '.join(args.to)}) : {len(orphans):,}")
    print(f"target lineage                             : {len(new):,} commits\n")
    print(f"matched on (author-date, subject) : {len(matched):,}")
    print(f"  corroborated by the tree hash   : {tree_agree:,}   (a tree-preserving rewrite)")
    print(f"  corroborated by parent structure: {parent_agree:,}   (a rewrite invariant)")
    print(f"  parent matches by key only      : {pkey_agree:,}   (weaker: a second name coincidence)")
    print(
        f"  NAME ONLY, no structural support: {len(uncorroborated):,}"
        f"{'' if not uncorroborated else '   <- dropped unless --uncorroborated'}"
    )
    for o in uncorroborated[:4]:
        print(f"      {o[:12]}  {old[o][3][:62]}")
    print(f"AMBIGUOUS -- refused, not guessed : {len(ambiguous):,}")
    print(f"no match at all                   : {len(unmatched):,}")
    for oid in unmatched[:5]:
        print(f"    {oid[:12]}  {old[oid][3][:66]}")
    if ambiguous:
        print("  ambiguous examples (cite more characters, or map these by hand):")
        for oid, hits in list(ambiguous.items())[:5]:
            print(f"    {oid[:12]} -> {len(hits)} candidates  {old[oid][3][:50]}")

    # A reconstructed row that disagrees with a RECORDED one is the only way this tool can do
    # damage, so check before writing rather than trusting the 100%-agreement validation.
    # Measured 2026-09-26 against both recorded maps: 1,790 comparable rows, 0 disagreements.
    # An IDENTITY row (old == new) is not a contradiction. filter-repo writes one for every
    # commit ITS run left alone, which says nothing about what a later rewrite did -- and the
    # first draft of this guard read 199 of them as conflicts. A real conflict is two maps
    # naming two DIFFERENT successors for the same commit.
    # A recorded target that is NOT clone-visible is an INTERMEDIATE hop, not a competing
    # answer: a later rewrite moved it and left no map, so the chain dead-ends there while the
    # inference reaches the live commit. Measured here: 43 such rows, and one of the recorded
    # targets (65ba8152cc36) no longer exists in the repository at all. A true contradiction is
    # a recorded target that IS live and still disagrees -- two answers both claiming to be
    # current, which no amount of chaining can reconcile.
    from core.git.rewrite_map import Resolver, load_maps

    res = Resolver(repo=root)
    contradictions, extended = [], 0
    for m in load_maps(root):
        if not m.durable:
            continue
        for old, new in matched.items():
            recorded = m.rows.get(old)
            if not recorded or recorded in (old, new):
                continue
            if res.visible(recorded):
                contradictions.append((old, recorded, new, m.label))
            else:
                extended += 1
    if extended:
        print(
            f"\n{extended} inferred row(s) EXTEND a recorded chain whose middle link is no"
            f"\n  longer clone-visible -- the record stops short, the inference reaches the"
            f"\n  live commit. Not a conflict."
        )

    # Most inferred rows only restate a chain the resolver already walks. Keeping them would
    # grow the inferred surface for no gain, so by default keep ONLY the rows that fill a gap:
    # an old SHA the existing maps cannot already take to a commit a clone can fetch.
    if uncorroborated and not args.uncorroborated:
        for o in uncorroborated:
            matched.pop(o, None)

    if not args.all_rows:
        gaps = {}
        for old, new in matched.items():
            cur = res.resolve(old)
            if not (cur.ok and (cur.status == "current" or res.visible(cur.sha))):
                gaps[old] = new
        print(
            f"\nof {len(matched):,} matched rows, {len(gaps):,} fill a GAP the existing maps"
            f"\n  cannot already close (--all-rows keeps every row instead)."
        )
        matched = gaps

    if contradictions:
        print(f"\nREFUSING TO WRITE: {len(contradictions)} row(s) contradict a recorded map.")
        for old, recorded, inferred, label in contradictions[:5]:
            print(f"  {old[:12]}  {label} recorded -> {recorded[:12]}, inference -> {inferred[:12]}")
        print("  A record beats an inference. Investigate before writing anything.")
        return 1

    if not args.write:
        print("\n(dry run -- pass --write to archive this as a map)")
        return 0
    if not matched:
        raise SystemExit("nothing matched; refusing to write an empty map")

    dest = root / "state" / "rewrites" / f"{args.date or date.today().isoformat()}"
    if args.label:
        dest = dest.with_name(dest.name + "-" + args.label)
    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} already exists; pass --force to overwrite")
    dest.mkdir(parents=True, exist_ok=True)
    lines = [f"{o} {n}" for o, n in sorted(matched.items())]
    (dest / "commit-map").write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = {
        "date": args.date or date.today().isoformat(),
        "tool": "unknown -- this rewrite left no map",
        "why": args.why or "(unknown; reconstructed after the fact)",
        "remaps": len(matched),
        "dropped": 0,
        "method": "reconstructed",
        "reconstructed_from": list(args.from_ref),
        "reconstructed_against": list(args.to),
        "key": "(author-date, subject)",
        "corroboration": "every row is backed by tree-hash agreement or parent-structure "
        "agreement; a name-only match is dropped unless --uncorroborated",
        "tree_hash_agrees": tree_agree,
        "parent_structure_agrees": parent_agree,
        "parent_key_only_agrees": pkey_agree,
        "dropped_name_only": len(uncorroborated),
        "refused_ambiguous": len(ambiguous),
        "unmatched": len(unmatched),
        "map_archived": date.today().isoformat(),
        "archived_by": os.environ.get("AKASHIC_AGENT_ID", "unknown"),
        "caveat": "AN INFERENCE, NOT A RECORD. Rows were deduced by matching commits across "
        "two lineages on author-date and subject, not written by the tool that did "
        "the rewrite. Rows whose key was shared by more than one target commit were "
        "REFUSED rather than guessed, so this map is incomplete by design.",
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {len(matched):,} reconstructed remaps -> {dest}")
    return 0


# ------------------------------------------------------------------------------- census
def cited_shas(root):
    """Every 7-40 char hex string in the tracked corpus, with the files citing it."""
    out = defaultdict(set)
    for rel in git(root, "ls-files", "--", *CORPUS).splitlines():
        try:
            blob = (root / rel).read_bytes()
        except OSError:
            continue
        for m in HEX.findall(blob):
            out[m.decode()].add(rel)
    return out


def cmd_census(args):
    from core.git.rewrite_map import AMBIGUOUS, CURRENT, DROPPED, TRANSLATED, Resolver

    root = repo(args)
    cand = cited_shas(root)
    probe = "\n".join(f"{s}^{{commit}}" for s in cand) + "\n"
    out = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch-check"], input=probe, capture_output=True, text=True
    ).stdout.splitlines()
    real = {}
    for line, sha in zip(out, cand, strict=False):
        p = line.split()
        if len(p) == 3 and p[1] == "commit":
            real[sha] = p[0]

    r = Resolver(repo=root)
    buckets = defaultdict(list)
    for sha in real:
        res = r.resolve(sha)
        # TRANSLATED is not the same as FIXED. A chain can end on a commit that a later,
        # unmapped rewrite already moved -- so the map answers, and the answer is a commit no
        # clone can fetch. Split the bucket rather than reporting a recovery that is not one.
        if res.status == TRANSLATED and not r.visible(res.sha):
            buckets["translated-to-nowhere"].append(sha)
        else:
            buckets[res.status].append(sha)

    broken = [s for st, v in buckets.items() if st != CURRENT for s in v]
    print(f"tracked corpus                 : {len(git(root, 'ls-files', '--', *CORPUS).splitlines()):,} files")
    print(f"hex strings that are commits   : {len(real):,}")
    print()
    print(f"  CURRENT      a clone sees it       : {len(buckets[CURRENT]):,}")
    print(f"  TRANSLATED   a map reaches a live commit : {len(buckets[TRANSLATED]):,}")
    print("  DEAD END     a map answers, with a SHA no")
    print(f"               clone can fetch      : {len(buckets['translated-to-nowhere']):,}")
    print(f"  DROPPED      removed on purpose   : {len(buckets[DROPPED]):,}")
    print(f"  AMBIGUOUS    refused              : {len(buckets[AMBIGUOUS]):,}")
    print(f"  UNKNOWN      no map covers it     : {len(buckets['unknown']):,}")
    print()
    print(
        f"citations broken for any clone : {len(broken):,} "
        f"({len(broken) / max(len(real), 1):.0%}), of which "
        f"{len(buckets[TRANSLATED]):,} genuinely resolve today"
    )
    stranded = buckets["unknown"] + buckets["translated-to-nowhere"] + buckets[AMBIGUOUS]
    if stranded:
        per = defaultdict(int)
        for s in stranded:
            for f in cand[s]:
                per[f] += 1
        print("\nstill stranded, by file -- no map reaches a live commit:")
        for f, n in sorted(per.items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {n:4}  {f}")
    if args.json:
        Path(args.json).write_text(
            json.dumps({k: len(v) for k, v in buckets.items()} | {"total": len(real)}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="archive a just-run rewrite's map where clones can see it")
    c.add_argument("--label", help="short slug, e.g. 'authorship'")
    c.add_argument("--why", help="one sentence: what this rewrite did and why")
    c.add_argument("--tool", default="git filter-repo")
    c.add_argument("--map", help="map path (default .git/filter-repo/commit-map)")
    c.add_argument("--date")
    c.add_argument("--force", action="store_true")
    c.set_defaults(fn=cmd_capture)

    r = sub.add_parser("reconstruct", help="rebuild a lost map from content identity")
    r.add_argument(
        "--from-ref", nargs="+", default=[], help="ref(s) holding the OLD lineage, e.g. refs/original/refs/heads/master"
    )
    r.add_argument(
        "--from-citations",
        action="store_true",
        help="take the OLD population from commits our corpus CITES but a clone "
        "cannot see -- catches a commit on no branch at all, which a "
        "ref-based sweep misses entirely",
    )
    r.add_argument(
        "--to",
        nargs="+",
        default=["--remotes"],
        help="ref(s) holding the NEW lineage (default --remotes: what a clone sees)",
    )
    r.add_argument("--label")
    r.add_argument("--why")
    r.add_argument("--date")
    r.add_argument(
        "--uncorroborated",
        action="store_true",
        help="keep rows that match on (author-date, subject) alone, with neither "
        "tree nor parent-structure agreement behind them",
    )
    r.add_argument("--all-rows", action="store_true", help="keep every matched row, not only the ones that fill a gap")
    r.add_argument("--write", action="store_true")
    r.add_argument("--force", action="store_true")
    r.set_defaults(fn=cmd_reconstruct)

    s = sub.add_parser("census", help="how healthy are our SHA citations")
    s.add_argument("--json", help="also write the counts here")
    s.set_defaults(fn=cmd_census)

    args = ap.parse_args(argv)
    if args.cmd == "reconstruct" and not (args.from_ref or args.from_citations):
        ap.error("reconstruct needs --from-ref <ref>... or --from-citations")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
