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
OUT = os.environ.get("AKASHIC_DIGESTS_FILE") or os.path.join(OUT_DIR, "digests.jsonl")

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
                # Shard labels are agent-authored and one of them returned its entire report as
                # its `shard` -- a 2KB "path" that made the index unreadable. Clamp the label;
                # the index is a NAVIGATION key, and a key nobody can read is not a key.
                _s = " ".join(str(shard).split())[:48]
                yield run, shard, {
                    "path": f"utterance:{_s}:{i}:{d.get('source') or '?'}",
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


# --- the READING surface -------------------------------------------------------------------
# The corpus has never had a skim-then-drill door: you either read a prose map someone authored
# (which drifts -- ROADMAP.md self-declared historical and is still cited as START HERE) or you
# re-read 1,600 artifacts. This is Daniil's own trace method applied to history: pick an AXIS,
# take SHALLOW HOPS across gists, ask for DEPTH on one thing. Same traversal contract as T125
# (walks code) and T103 (walks knowledge); this walks the record.
#
# Every surface below declares its bounds -- N of M, and truncation announced -- because his
# standing law is "half the battle is knowing what the given bounds for a thing are", and a
# count that hides a cut is the defect class this corpus keeps paying for.

# EVERY altitude gets a budget, not just the menu (codex, o200k-measured 2026-08-01:
# --directives printed 284k tokens, --orphans 95k, --stale 63k -- unbounded bands blow a
# context window just as surely as reading the corpus raw). Default cap, announced
# truncation, and a CONTINUATION pointer, lifted only by an explicit --all.
DEFAULT_LIMIT = 40


def _bound(shown, total, what, offset=0):
    line = f"[digests] {shown} of {total} {what}"
    if offset:
        line += f"  (from --offset {offset})"
    if offset + shown < total:
        line += (f"  (TRUNCATED -- {total - offset - shown} more; continue with "
                 f"--offset {offset + shown}, widen with --limit, or --all)")
    return line


def _rows_with(rows, field):
    return [r for r in rows if r.get(field)]


def _print_hits(rows, total, what, field=None, offset=0):
    print(_bound(len(rows), total, what, offset))
    for r in rows:
        extra = ""
        if field:
            v = r.get(field)
            if isinstance(v, list):
                v = "; ".join(json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else str(x)
                              for x in v)
            extra = f"\n      {v}"
        print(f"  {r.get('path')}\n      {r.get('gist','')}{extra}")


# --- the JOIN: narrative <-> specifics -------------------------------------------------------
# The spine's beats already carry pointers, but only `git:SHA` -- never an atom, a lesson, or one
# of his directives. So "skim the general, arrive at the specific" has only ever worked for
# commits. The join key is TIME CONTAINMENT: a chapter carries span_start/span_end and a digest
# carries a date. That is a FACT, not an inference; no prose is interpreted to produce it, which
# is exactly why it is trustworthy where a theme-match would not be.

def _load_chapters():
    """Chapters from the sanctioned door (`story --json`), or an injected file for pins."""
    inj = os.environ.get("AKASHIC_CHAPTERS_FILE")
    if inj:
        try:
            with open(inj, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []
    # `story --json` bare returns an ATLAS (a dict of track NAMES), not chapters. The first
    # version of this loader expected a list, got the dict, returned [] -- and the join then
    # printed a confident "0 of 0 chapters whose span contains 2026-07-31", which I nearly
    # reported as "the spine does not cover recent work". It covers 2026-04-15..2026-07-31.
    # A coverage claim manufactured by the reader's own bug is the exact disease this corpus
    # keeps paying for, produced here by the tool built to detect it. Chapters live PER TRACK.
    import subprocess
    cli = os.path.join(ROOT, "agent_cli.py")

    def _cli(*args):
        try:
            r = subprocess.run([sys.executable, cli, "story", *args],
                               capture_output=True, text=True, timeout=180, cwd=ROOT)
            return json.loads(r.stdout)
        except Exception:
            return None

    atlas = _cli("--json")
    tracks = (atlas or {}).get("tracks") if isinstance(atlas, dict) else None
    if not tracks:
        return []
    out = []
    for t in tracks:
        got = _cli("--track", str(t), "--json")
        if isinstance(got, list):
            out += [c for c in got if isinstance(c, dict) and c.get("id")]
    return out


def _day(value):
    """YYYY-MM-DD or None. A date we cannot parse is UNPLACEABLE, never silently 'now'."""
    s = str(value or "")[:10]
    return s if len(s) == 10 and s[4] == "-" and s[7] == "-" else None


def _contains(ch, day):
    a, b = _day(ch.get("span_start")), _day(ch.get("span_end"))
    return bool(a and b and day and a <= day <= b)


def _query(rows, args):
    if args.chapter_of:
        hits = [r for r in rows if args.chapter_of.lower() in str(r.get("path", "")).lower()]
        if not hits:
            print(f"[digests] no digest matches {args.chapter_of!r}")
            return 1
        chapters = _load_chapters()
        for r in hits:
            day = _day(r.get("date"))
            print(f"  {r.get('path')}\n      {r.get('gist','')}")
            if not day:
                print("      UNPLACEABLE -- this digest carries no parsable date, so it belongs "
                      "to no chapter. That is a gap in the record, not an empty result.")
                continue
            owning = [c for c in chapters if _contains(c, day)]
            print(_bound(len(owning), len(owning), f"chapter(s) whose span contains {day}"))
            for c in owning:
                print(f"      {c.get('id')}  [{c.get('track')}]  {c.get('title')}"
                      f"\n        {_day(c.get('span_start'))} .. {_day(c.get('span_end'))}")
        return 0

    if args.in_chapter:
        chapters = _load_chapters()
        ch = next((c for c in chapters if c.get("id") == args.in_chapter), None)
        if not ch:
            print(f"[digests] no chapter {args.in_chapter!r} (chapters loaded: {len(chapters)})")
            return 1
        placed = [r for r in rows if _contains(ch, _day(r.get("date")))]
        undated = [r for r in rows if not _day(r.get("date"))]
        print(f"[digests] chapter {ch.get('id')} [{ch.get('track')}] {ch.get('title')}")
        print(f"          span {_day(ch.get('span_start'))} .. {_day(ch.get('span_end'))}")
        total = len(placed)
        shown = placed[:args.limit] if args.limit else placed
        _print_hits(shown, total, "artifacts born inside this chapter")
        # UNSCANNED is not EMPTY, applied to the join itself: a digest with no date is not
        # absent from this chapter, it is unplaceable, and the difference is the whole point.
        print(f"[digests] NOTE: {len(undated)} undated digest(s) in the dataset cannot be placed "
              "in ANY chapter -- they are excluded from every span, not from this one.")
        return 0

    # One budget rule for every listing surface: default DEFAULT_LIMIT, --all lifts,
    # --offset continues. No surface prints unbounded unless explicitly told to.
    eff_limit = None if args.all else (args.limit or DEFAULT_LIMIT)
    offset = max(0, args.offset or 0)

    if args.themes:
        counts = {}
        for r in rows:
            for t in (r.get("themes") or []):
                counts[t] = counts.get(t, 0) + 1
        ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        page = ordered[offset:offset + eff_limit] if eff_limit else ordered[offset:]
        print(_bound(len(page), len(ordered),
                     "axes (exact labels) -- --theme matches EXACTLY; --contains to browse",
                     offset))
        for t, c in page:
            print(f"  {c:>5}  {t}")
        return 0

    picks, what, field = None, None, None
    if args.theme:
        t = args.theme.lower()
        if args.contains:
            # Substring browsing stays available, but as a DECLARED different query. The
            # defect this replaces: the menu counted exact labels while the hop matched
            # substrings -- '95 recall' on one surface, '137 of 137' on the other. Two
            # surfaces, two sets, one claiming completeness (codex, reproduced 2026-08-01).
            picks = [r for r in rows
                     if any(t in str(x).lower() for x in (r.get("themes") or []))]
            what = f"artifacts whose labels CONTAIN {args.theme!r} (substring browse)"
        else:
            picks = [r for r in rows
                     if any(t == str(x).lower() for x in (r.get("themes") or []))]
            what = f"artifacts labeled exactly {args.theme!r}"
    elif args.grep:
        g = args.grep.lower()
        picks = [r for r in rows if g in json.dumps(r, ensure_ascii=False).lower()]
        what = f"artifacts matching {args.grep!r}"
    # Band headers say CLAIMS. The critic proved these carry TOON-class false positives --
    # a header that reads as fact launders a sweep agent's assertion into a finding.
    elif args.orphans:
        picks, what, field = (_rows_with(rows, "orphaned"),
                              "orphan CLAIMS (sweep-agent assertions -- verify before citing)",
                              "orphaned")
    elif args.stale:
        picks, what, field = (_rows_with(rows, "staleness_signal"),
                              "staleness CLAIMS (sweep-agent assertions -- verify before citing)",
                              "staleness_signal")
    elif args.gold:
        picks, what, field = (_rows_with(rows, "gold"),
                              "gold CLAIMS (sweep-agent assertions -- verify before citing)",
                              "gold")
    elif args.directives:
        picks, what, field = (_rows_with(rows, "daniil_directives"),
                              "artifacts carrying his words as captured by the sweep",
                              "daniil_directives")
    elif args.show:
        hits = [r for r in rows if args.show.lower() in str(r.get("path", "")).lower()]
        print(_bound(len(hits), len(hits), f"record(s) for {args.show!r}"))
        for r in hits:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if hits else 1
    if picks is None:
        return None
    total = len(picks)
    page = picks[offset:offset + eff_limit] if eff_limit else picks[offset:]
    _print_hits(page, total, what, field, offset=offset)
    return 0


def main(argv=None):
    # These digests were written by agents, not by us, and they carry unicode (check marks,
    # arrows, em dashes). A Windows console is cp1252 and a reader that CRASHES on content it
    # did not author is a reading surface that refuses to read -- so degrade the glyph, never
    # the record. No pin caught this because the fixture was pure ASCII; the real corpus is not.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="report on landed digests, write nothing")
    ap.add_argument("--journal", action="append", help="extra journal path (repeatable)")
    ap.add_argument("--themes", action="store_true", help="list the axes available (start here)")
    ap.add_argument("--theme", help="shallow hop: artifacts on one axis")
    ap.add_argument("--grep", help="free-text search across every digest field")
    ap.add_argument("--orphans", action="store_true", help="designed but apparently never built")
    ap.add_argument("--stale", action="store_true", help="claims a state it may not be in")
    ap.add_argument("--gold", action="store_true", help="mechanisms worth resurfacing")
    ap.add_argument("--directives", action="store_true", help="his words, verbatim")
    ap.add_argument("--show", help="drill: every field recorded for one path")
    ap.add_argument("--chapter-of", dest="chapter_of",
                    help="join: which narrative chapter's span contains this artifact")
    ap.add_argument("--in-chapter", dest="in_chapter",
                    help="join: which artifacts were born inside this chapter's span")
    ap.add_argument("--limit", type=int, default=0,
                    help=f"cap rows (default {DEFAULT_LIMIT}; truncation is ANNOUNCED)")
    ap.add_argument("--all", action="store_true", help="lift the default row budget")
    ap.add_argument("--offset", type=int, default=0, help="continuation: skip the first N rows")
    ap.add_argument("--contains", action="store_true",
                    help="with --theme: substring browse instead of exact label match")
    args = ap.parse_args(argv)

    existing = load_existing()
    rows = list(existing.values())

    if any([args.themes, args.theme, args.grep, args.orphans, args.stale, args.gold,
            args.directives, args.show, args.chapter_of, args.in_chapter]):
        if not rows:
            print(f"[digests] no digests at {OUT} -- land them first: py scripts/corpus_digests.py")
            return 2
        rc = _query(rows, args)
        return 0 if rc is None else rc

    if args.stats:
        _report(rows, "landed")
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
