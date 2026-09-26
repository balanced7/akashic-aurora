"""check_rewrite_maps -- did a history rewrite run without leaving us a way back?

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS
---------------
2026-09-26 (T410). This repo has rewritten its history three times and only ever kept a usable
map for one of them by design:

  2026-07-23  Apple/Samsung reference purge. Map left in .git/filter-repo/commit-map, which the
              NEXT filter-repo run overwrites. Nothing read it for 65 days. It is the first link
              in our chain, so losing it would have cut recovery from 870 citations to 86.
  2026-08-12  Third-party PII redaction. Map archived off-repo to two drives -- better, and
              still invisible to every clone and to every search plane this house uses.
  post-08-16  An attribution rewrite that moved 104 commits from 'you@email.com' to the
              operator's GitHub-linked address. NO MAP AT ALL. Found only because it left a
              stray refs/original ref behind, and reconstructed after the fact.

Measured that day: 877 of the 1,436 commit SHAs our own tracked corpus cites -- 61% -- resolved
on the authoring machine ONLY, because two local refs pinned the pre-rewrite lineage and a clone
never receives them. The chronicle was the worst affected file in the repo.

A law that stays a lesson keeps recurring; a law that becomes a checker stops. Three instances
is the threshold, so this refuses instead of reminding.

WHAT IT ASKS
------------
  1. Is there a rewrite map sitting in .git/ that no committed map covers?  (volatile)
  2. Does a pre-rewrite ref hold commits that no map can resolve?          (unmapped rewrite)
  3. How many corpus citations does no map reach a live commit for?        (stranded)

COULD NOT CHECK IS NOT CLEAN. Every plane reports its own failure separately, because an
absence that reads as success is the defect this family of checkers exists for.

REPORT BY DEFAULT. `--gate` opts into the ratchet.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASELINE = ROOT / "state" / "rewrites" / "citation_baseline.json"
# Accepted residue: commits a rewrite genuinely destroyed, which no map can ever resolve. The
# manifest idiom check_door_parity established -- fail on NEW drift, and require a rationale per
# entry, because an entry without one is how known debt becomes forgotten debt. A gate that can
# never go green gets ignored, and an ignored gate guards nothing.
ACCEPTED = ROOT / "state" / "rewrites" / "accepted_unresolvable.json"
HEX = re.compile(rb"\b[0-9a-f]{7,40}\b")
CORPUS = ["docs/", "research/", "fences/", "chronicles/", "*.md", "state/coord/"]

# Refs that exist ONLY because a rewrite ran. filter-branch writes refs/original/*; our own
# rewrites have left a pre-rewrite-backup branch. Each is a rewrite's fingerprint.
REWRITE_REF_PATTERNS = ("refs/original/", "pre-rewrite", "pre-scrub", "before-rewrite")


class NotARepo(Exception):
    """No git plane to read. A checker must never report this as a pass."""


def git(*a, root=None):
    root = root or ROOT
    p = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode and "not a git repository" in (p.stderr or "").lower():
        raise NotARepo(str(root))
    return p.stdout or ""


# ------------------------------------------------------------------ 1. the volatile map
def unarchived_map(maps):
    """A map in .git/ whose rows no committed map holds: a rewrite ran and was not captured."""
    vol = [m for m in maps if not m.durable]
    if not vol:
        return None
    m = vol[0]
    durable_rows = set()
    for other in maps:
        if other.durable:
            durable_rows |= set(other.rows.items())
    missing = [old for old, new in m.rows.items() if (old, new) not in durable_rows]
    if not missing:
        return None
    return {"path": str(m.path), "rows": len(m.rows), "uncovered": len(missing)}


# --------------------------------------------------------------- 2. the unmapped rewrite
def rewrite_refs():
    out = []
    for line in git("for-each-ref", "--format=%(refname)").splitlines():
        if any(p in line for p in REWRITE_REF_PATTERNS):
            out.append(line.strip())
    return out


def accepted():
    """{sha: why} for residue we have decided is genuinely unrecoverable.

    An entry with no reason is itself a finding: a bare SHA on an allow-list is indistinguishable
    from a defect somebody got tired of.
    """
    try:
        raw = json.loads(ACCEPTED.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, []
    except Exception as exc:
        return {}, [f"{ACCEPTED.name} is unreadable ({exc}); treating nothing as accepted"]
    ok, bad = {}, []
    for sha, why in (raw.get("unresolvable") or {}).items():
        if isinstance(why, str) and why.strip():
            ok[sha.lower()] = why
        else:
            bad.append(f"{sha[:12]} is allow-listed with no reason")
    return ok, bad


def unmapped_rewrites(resolver, waived):
    """For each rewrite ref, the commits in its lineage that no map can resolve forward."""
    refs = rewrite_refs()
    if not refs:
        return []
    visible = set(git("rev-list", "--remotes").split())
    findings = []
    for ref in refs:
        lineage = git("rev-list", ref).split()
        if not lineage:
            continue
        orphans = [o for o in lineage if o not in visible]
        lost = [o for o in orphans
                if o not in waived and not resolver.resolve(o, check_remote=False).ok]
        if lost:
            findings.append({"ref": ref, "lineage": len(lineage),
                             "orphans": len(orphans), "unresolvable": len(lost),
                             "examples": lost[:3]})
    return findings


# ------------------------------------------------------------------ 3. stranded citations
def stranded_citations(resolver, waived):
    """Cited SHAs for which no map reaches a commit a clone can fetch."""
    cand = {}
    for rel in git("ls-files", "--", *CORPUS).splitlines():
        try:
            blob = (ROOT / rel).read_bytes()
        except OSError:
            continue
        for m in HEX.findall(blob):
            cand.setdefault(m.decode(), set()).add(rel)
    if not cand:
        return {"checked": False, "reason": "no tracked corpus files matched", "stranded": []}

    probe = "\n".join(f"{s}^{{commit}}" for s in cand) + "\n"
    out = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch-check"], input=probe,
                         capture_output=True, text=True).stdout.splitlines()
    real = [sha for line, sha in zip(out, cand) if " commit " in line]

    stranded, waived_hits = [], 0
    for sha in real:
        res = resolver.resolve(sha)
        if res.ok and (res.status == "current" or resolver.visible(res.sha)):
            continue
        if sha.lower() in waived or any(w.startswith(sha.lower()) for w in waived):
            waived_hits += 1
            continue
        stranded.append({"sha": sha, "status": res.status,
                         "files": sorted(cand[sha])[:2]})
    return {"checked": True, "commits": len(real), "stranded": stranded,
            "waived": waived_hits}


def report(gate=False, freeze=False):
    from core.git.rewrite_map import Resolver

    r = Resolver(repo=ROOT)
    waived, waiver_problems = accepted()
    out = {"maps": [{"label": m.label, "rows": len(m.rows), "durable": m.durable,
                     "method": m.method} for m in r.maps]}
    out["unarchived"] = unarchived_map(r.maps)
    out["unmapped"] = unmapped_rewrites(r, waived)
    out["citations"] = stranded_citations(r, waived)

    print("[rewrite-maps] maps this checkout carries:")
    if not r.maps:
        print("  NONE. If a rewrite has ever run here, there is no way back from a stale SHA.")
    for m in out["maps"]:
        tag = "" if m["durable"] else "   VOLATILE -- the next rewrite overwrites it"
        print(f"  {m['label']:<34} {m['rows']:5,} rows  [{m['method']}]{tag}")

    findings = 0
    if waived:
        print(f"  {len(waived)} commit(s) accepted as unrecoverable "
              f"({ACCEPTED.name}), each with a stated reason")
    for problem in waiver_problems:
        findings += 1
        print(f"\n  BAD WAIVER -- {problem}")
        print("    A bare SHA on an allow-list is indistinguishable from a defect someone got")
        print("    tired of. Give it a reason or remove it.")

    if out["unarchived"]:
        u = out["unarchived"]
        findings += 1
        print(f"\n  UNCAPTURED REWRITE -- {u['path']}")
        print(f"    {u['uncovered']:,} of {u['rows']:,} rows are in no committed map. This file")
        print("    is overwritten by the next filter-repo run. Capture it now:")
        print("      py scripts/rewrite_recover.py capture --label <slug> --why \"...\"")

    if out["unmapped"]:
        findings += 1
        print(f"\n  UNMAPPED REWRITE -- {len(out['unmapped'])} ref(s) hold commits no map can")
        print("  resolve. A rewrite ran and left no map; reconstruct one from content identity:")
        for f in out["unmapped"]:
            print(f"    {f['ref']}")
            print(f"      lineage {f['lineage']:,}, orphaned {f['orphans']:,}, "
                  f"unresolvable {f['unresolvable']:,}")
        print("      py scripts/rewrite_recover.py reconstruct --from-ref <ref>")

    cit = out["citations"]
    if not cit["checked"]:
        findings += 1
        print(f"\n  COULD NOT CHECK CITATIONS -- {cit['reason']}")
        print("    This is not a pass. Nothing was measured.")
    else:
        n = len(cit["stranded"])
        print(f"\n  citations: {cit['commits']:,} commit SHAs cited, {n:,} stranded")
        for s in cit["stranded"][:8]:
            print(f"    {s['sha'][:14]}  {s['status']:<10} {', '.join(s['files'])}")
        if n > 8:
            print(f"    ... +{n - 8} more")

    if freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(
            {"stranded": len(cit.get("stranded") or []),
             "frozen_at": git("rev-parse", "--short", "HEAD").strip(),
             "note": "Stranded citations at freeze time. The gate ratchets: this may fall, "
                     "never rise. A rise means a rewrite ran without capturing its map."},
            indent=2) + "\n", encoding="utf-8")
        print(f"\n[rewrite-maps] froze {len(cit.get('stranded') or []):,} stranded at "
              f"{BASELINE.relative_to(ROOT)}")
        return 0

    if gate:
        if findings:
            print(f"\n[rewrite-maps] GATE FAIL -- {findings} finding(s) above.")
            return 1
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8"))["stranded"]
        except Exception:
            print("\n[rewrite-maps] GATE FAIL -- no baseline to ratchet against. Freeze one "
                  "deliberately with --freeze.")
            return 1
        now = len(cit["stranded"])
        if now > base:
            print(f"\n[rewrite-maps] GATE FAIL -- stranded citations rose {base} -> {now}.")
            print("  A rewrite ran without capturing its map, or a doc cited a stale SHA.")
            return 1
        print(f"\n[rewrite-maps] gate ok -- {now} stranded, baseline {base}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate", action="store_true", help="fail on a finding or a regression")
    ap.add_argument("--freeze", action="store_true", help="re-freeze the stranded baseline")
    args = ap.parse_args(argv)
    try:
        return report(gate=args.gate, freeze=args.freeze)
    except NotARepo as exc:
        print(f"[rewrite-maps] COULD NOT CHECK -- {exc} is not a git repository.")
        print("  This is not a pass: no plane was read.")
        return 1 if args.gate else 0


if __name__ == "__main__":
    sys.exit(main())
