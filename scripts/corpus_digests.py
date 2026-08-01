#!/usr/bin/env python3
"""corpus_digests -- land structured corpus digests as a durable, queryable dataset.

WHY THIS EXISTS (2026-08-01). A 36-agent sweep read 1,598 artifacts and returned one structured
digest per artifact: what it IS, what it SETTLED, what it SUPERSEDES, whether it is ORPHANED,
whether it claims a state it is not in, and Daniil's directives quoted verbatim. That output --
the genuinely valuable half of the run, far more than the prose map it produced -- existed only
inside workflow scratch files under .claude/, which is exactly the class of directory people
clean out. This lands it in git.

THE DEEPER REASON. The corpus's `rel:` roster is 94% one ungoverned value (`cites` 786, vs
`discusses` 41, `derives-from` 8, `supports` 3), so the logical-hop plane the super-wiki was
designed on is born nearly empty -- you cannot derive a hierarchy from a graph with one edge
type. Every digest field is a typed relation in disguise: `settled` -> artifact SETTLES a claim;
`staleness_signal` -> CONTRADICTED-BY; `orphaned` -> design HAS-NO implementation; a directive
quote -> artifact SERVES an operator ask. So the sweep did not just produce a report; it produced
the edge set the graph has been missing since the beginning.

STANDARD PRACTICE (the point). Re-run this after any sweep. It is idempotent, it dedupes by
(path, run), and it never deletes -- so digests accumulate as a longitudinal record of what the
corpus claimed about itself over time, which is the only way "is this still true?" ever becomes
answerable without another full read.

    py scripts/corpus_digests.py                 # land everything found, print a coverage table
    py scripts/corpus_digests.py --stats         # report on what is already landed, write nothing
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "corpus-digests")
OUT = os.path.join(OUT_DIR, "digests.jsonl")

# Workflow journals live beside the session transcripts, not in the repo.
JOURNAL_GLOB = os.path.join(
    os.path.expanduser("~"), ".claude", "projects", "*", "*", "subagents", "workflows",
    "*", "journal.jsonl")

# Fields a digest may carry. Absent != empty: a field missing from a shard's schema is unknown,
# not false, and the coverage table below reports population per field so a reader can tell.
FIELDS = ("path", "date", "status_claimed", "gist", "settled", "orphaned",
          "staleness_signal", "gold", "themes", "daniil_directives")


def _journals(extra=None):
    found = sorted(glob.glob(JOURNAL_GLOB))
    if extra:
        found += [p for p in extra if os.path.exists(p)]
    return found


def _digests_from(journal):
    """Yield (run_id, artifact_dict) from one workflow journal."""
    run = os.path.basename(os.path.dirname(journal))
    with open(journal, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue                       # a partial line is not a reason to lose the file
            if rec.get("type") != "result":
                continue
            val = rec.get("value") or rec.get("result") or {}
            if not isinstance(val, dict):
                continue
            shard = val.get("shard") or rec.get("label") or "?"
            for art in (val.get("artifacts") or []):
                if isinstance(art, dict) and art.get("path"):
                    yield run, shard, art
            # A sweep over TRANSCRIPTS returns operator utterances rather than artifact digests.
            # The first version of this extractor only understood `artifacts` and silently landed
            # zero from those runs -- a coverage hole in a tool whose whole job is coverage, and
            # exactly the failure class it was written to catch. Both shapes are digests; the unit
            # differs (an artifact vs. a thing he said), so `path` is synthesised for the latter.
            for i, d in enumerate(val.get("directives") or []):
                if not isinstance(d, dict) or not d.get("quote"):
                    continue
                # The key MUST carry the index. Keying on `source` alone collapsed every quote
                # from the same transcript file into one record and silently dropped ~half his
                # utterances -- losing operator speech to a dedup bug is the worst available
                # failure here, and it looked like success because the count was still large.
                yield run, shard, {
                    "path": f"utterance:{shard}:{i}:{d.get('source') or '?'}",
                    "date": d.get("date"),
                    "gist": d.get("about") or "",
                    "themes": [d.get("kind")] if d.get("kind") else [],
                    "daniil_directives": [{k: v for k, v in d.items() if v}],
                }


def load_existing():
    if not os.path.exists(OUT):
        return {}
    out = {}
    with open(OUT, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            out[(d.get("run"), d.get("path"))] = d
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="report on landed digests, write nothing")
    ap.add_argument("--journal", action="append", help="extra journal path (repeatable)")
    args = ap.parse_args(argv)

    existing = load_existing()
    if args.stats:
        _report(list(existing.values()), "landed")
        return 0

    journals = _journals(args.journal)
    if not journals:
        print("[digests] no workflow journals found -- nothing to land (this is not an error)")
        return 0

    added = 0
    for j in journals:
        for run, shard, art in _digests_from(j):
            key = (run, art["path"])
            if key in existing:
                continue                       # idempotent: same run + same artifact = same digest
            rec = {"run": run, "shard": shard}
            rec.update({f: art.get(f) for f in FIELDS if art.get(f)})
            existing[key] = rec
            added += 1

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = sorted(existing.values(), key=lambda d: (d.get("run", ""), d.get("path", "")))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[digests] {len(journals)} journal(s) -> {OUT}")
    print(f"[digests] +{added} new, {len(rows)} total")
    _report(rows, "landed")
    return 0


def _report(rows, label):
    """Coverage table. A count of what IS populated, so absence is legible rather than assumed."""
    if not rows:
        print(f"[digests] 0 {label}")
        return
    runs, pop = {}, {}
    for r in rows:
        runs[r.get("run", "?")] = runs.get(r.get("run", "?"), 0) + 1
        for f in FIELDS:
            if r.get(f):
                pop[f] = pop.get(f, 0) + 1
    n = len(rows)
    print(f"[digests] {n} {label} across {len(runs)} run(s)")
    for run, c in sorted(runs.items()):
        print(f"    {run}: {c}")
    print("[digests] field population (blank = the shard did not report it, NOT 'false'):")
    for f in FIELDS:
        c = pop.get(f, 0)
        print(f"    {f:<20} {c:>5}  ({100.0 * c / n:.0f}%)")


if __name__ == "__main__":
    sys.exit(main())
