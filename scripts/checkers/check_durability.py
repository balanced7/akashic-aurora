"""check_durability -- what does this house believe is landed that is not?

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS
---------------
2026-09-24/25, six findings in one session with one shape:

  * tests/test_find_everything_red.py pinned SHIPPED code while sitting untracked. It surfaced
    only because a peer's bus message happened to name the file.
  * tests/test_eye_seat_capture.py was the SPECIFICATION of an unbuilt slice, carrying the
    operator's verbatim 2026-08-17 directive, untracked for 36 days. A prior-art search ran
    across the lesson store, the transcript index and the task ledger and found nothing --
    none of those planes can contain an uncommitted file -- so part of the slice was rebuilt.
  * 42 of 764 test pins untracked (5.5%), measured at HEAD 2c27a64f.
  * A lesson announced in a session report as "captured" was absent from the store; the
    knowledge survived only in working code and a chat transcript.
  * Wish W214 was filed through the door and its file edit never committed.
  * state/coord/tasks.json carried 577 uncommitted lines while boot's own precedence line reads
    "TASK LEDGER (git-durable, gated transitions) beats durable NOTES ...".

IN EVERY ONE THE REPORTING SURFACE SAID SUCCESS. The door printed [OK]. The suite was green.
The handoff said "everything below is pushed (origin/master ec169def)" while two commits sat
unpushed. That is the shape this checker exists for: not wrong work, but work that believes it
landed.

The last item is why this is a DURABILITY question and not a hygiene one. A forgotten file is
untidy. The task ledger is the house's top precedence authority, read by every seat at boot,
and it self-describes as git-durable -- so a divergence between it and git is the claim
contradicting itself, silently, in the one place seats are told to trust first.

WHAT THE NEIGHBOURS ALREADY ASK (and why none of them covers this)
------------------------------------------------------------------
check_wiring          is built code REACHABLE from a production entry point?
check_pointer_promises does a link's target hold what the prose PROMISES?
check_preregistration  did the pin land BEFORE its implementation?

All three presume the artifact is in git. This one asks whether it is.

THIS IS A REPORT BY DEFAULT. `--gate` opts into the ratchet.
------------------------------------------------------------
Following check_pointer_promises' reasoning: the bar is not "catch the six cases", it is
"never cry wolf". Unpushed commits are usually legitimate mid-work, and a dirty shared ledger
is normal for minutes at a time. Only ONE dimension ratchets cleanly -- a NEW untracked pin --
so only that one can fail a gate, and only against a frozen baseline.

WHAT IT CANNOT DO (stated, not discovered later)
------------------------------------------------
* It cannot see a lesson announced in prose but absent from the store (finding 4). That needs
  text analysis of session reports against the lesson store and is a different instrument.
* It cannot tell a DELIBERATELY untracked file (machine-local scratch, a probe) from an
  orphaned pin. It reports the population; a human adjudicates. That ambiguity is itself the
  finding -- 40 of the 42 are unclassified, and nobody can currently tell which is which.
* Its unpushed check compares against the tracked upstream only. A branch with no upstream
  reports ALL its commits, which is correct and loud on purpose: nothing there is published.
* It reads git and the filesystem. It resolves no credential, by construction.

Run:  py scripts/checkers/check_durability.py             # report, always exit 0
      py scripts/checkers/check_durability.py --gate      # exit 1 on a NEW untracked pin
      py scripts/checkers/check_durability.py --freeze    # write today's population as baseline
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]

# Pins are the population with the measured defect, and the one that ratchets cleanly.
PIN_GLOB = "tests/test_*.py"

# Paths that carry a DURABILITY CLAIM -- written down rather than inferred, because "which
# files matter" is a declaration. The ledger is here because boot names it first in the
# precedence rule AND calls it git-durable; a divergence is the claim contradicting itself.
DURABLE_STATE_PATHS = [
    "state/coord/tasks.json",        # the task ledger: boot's top precedence authority
    "docs/WISHLIST.md",              # append-only by standing rule; W214 was filed and not landed
    "state/coord/defer_queue.json",  # the deferred-work queue a later seat is told to discharge
]

BASELINE = ROOT / "scripts" / "checkers" / "durability_baseline.json"


class NotARepo(Exception):
    """Raised when git cannot answer. NEVER swallowed into an empty list -- see `sweep`."""


def _git(root: Any, *args: str) -> str:
    """Run git, or raise NotARepo. The distinction is the whole point of this module: a git
    that cannot answer must not look like a git that answered 'nothing'."""
    try:
        p = subprocess.run(["git", "-C", str(root)] + list(args),
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:      # pragma: no cover - host dependent
        raise NotARepo(f"git could not run: {e}") from e
    if p.returncode != 0:
        raise NotARepo((p.stderr or p.stdout or "git failed").strip().splitlines()[0][:200])
    return p.stdout


def untracked_pins(root: Any = ROOT) -> List[str]:
    """Test pins that exist on disk and not in git -- invisible to the suite baseline, to a
    fixed-revision review, and to every prior-art search anyone runs."""
    out = _git(root, "ls-files", "--others", "--exclude-standard", "--", PIN_GLOB)
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def unpushed_commits(root: Any = ROOT) -> List[Dict[str, str]]:
    """Commits that exist only on this disk.

    An outside reviewer is structurally incapable of seeing these, which is exactly why a
    handoff can claim everything is pushed and be believed."""
    try:
        upstream = _git(root, "rev-parse", "--abbrev-ref", "@{upstream}").strip()
        rng = f"{upstream}..HEAD"
    except NotARepo:
        # No upstream at all: nothing here has been published. Report every commit rather
        # than reporting clean, because "no remote" is the strongest form of unpublished.
        rng = "HEAD"
    try:
        out = _git(root, "log", "--format=%h\t%s", rng)
    except NotARepo:
        return []
    rows = []
    for line in out.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", 1)
            rows.append({"sha": sha, "subject": subject[:120]})
    return rows


def uncommitted_durable_state(root: Any = ROOT) -> List[Dict[str, Any]]:
    """Declared durability-authority files whose working copy differs from git.

    The measured instance: the task ledger 577 lines ahead of git while every seat is told at
    boot that it is the git-durable authority."""
    rows = []
    for rel in DURABLE_STATE_PATHS:
        if not (Path(root) / rel).exists():
            continue
        try:
            out = _git(root, "diff", "--numstat", "--", rel).strip()
        except NotARepo:
            continue
        if not out:
            continue
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                added, removed, path = parts[0], parts[1], parts[2]
                rows.append({"path": path,
                             "added": int(added) if added.isdigit() else None,
                             "removed": int(removed) if removed.isdigit() else None})
    return rows


def load_baseline() -> List[str]:
    try:
        return sorted(json.loads(BASELINE.read_text(encoding="utf-8")).get("untracked_pins", []))
    except Exception:
        return []


def new_since(root: Any = ROOT, baseline: Optional[List[str]] = None) -> List[str]:
    """Untracked pins that are NOT in the frozen population -- the only gate-able signal.

    The ratchet exists because 42 already existed the day this was written. A gate that fails
    on the inherited population is a gate someone switches off, and then the NEW ones arrive
    unobserved too."""
    known = set(baseline if baseline is not None else load_baseline())
    return [p for p in untracked_pins(root) if p not in known]


def sweep(root: Any = ROOT) -> Dict[str, Any]:
    """The whole answer, with its frame.

    ZERO IS NOT NO. If git cannot answer, this returns unknown=True and a verdict that says
    so. A durability sweep that reported a confident clean when it could not look would be
    the very defect it exists to catch, wearing the organ's badge."""
    scanned = {"root": str(root), "pin_glob": PIN_GLOB,
               "durable_state_paths": list(DURABLE_STATE_PATHS)}
    try:
        pins = untracked_pins(root)
    except NotARepo as e:
        return {"untracked_pins": [], "unpushed_commits": [], "uncommitted_durable_state": [],
                "scanned": scanned, "unknown": True,
                "verdict": f"UNKNOWN -- could not read git at {root}: {e}"}

    unpushed = unpushed_commits(root)
    dirty = uncommitted_durable_state(root)
    fresh = new_since(root, load_baseline())
    findings = len(pins) + len(unpushed) + len(dirty)
    verdict = "CLEAN -- checked, nothing unlanded" if findings == 0 else (
        f"{len(pins)} untracked pin(s), {len(unpushed)} unpushed commit(s), "
        f"{len(dirty)} durable-state file(s) diverged")
    return {"untracked_pins": pins, "unpushed_commits": unpushed,
            "uncommitted_durable_state": dirty, "new_untracked_pins": fresh,
            "scanned": scanned, "unknown": False, "verdict": verdict}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 on a NEW untracked pin (ratchet against the frozen baseline)")
    ap.add_argument("--freeze", action="store_true",
                    help="write today's untracked population as the baseline")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    out = sweep(ROOT)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    if out["unknown"]:
        print(f"[durability] {out['verdict']}")
        return 0

    if args.freeze:
        BASELINE.write_text(json.dumps(
            {"frozen_at_head": _git(ROOT, "rev-parse", "--short", "HEAD").strip(),
             "note": "the inherited population; the gate fails only on additions to this list",
             "untracked_pins": out["untracked_pins"]}, indent=2) + "\n", encoding="utf-8")
        print(f"[durability] froze {len(out['untracked_pins'])} untracked pin(s) -> "
              f"{BASELINE.relative_to(ROOT)}")
        return 0

    print(f"[durability] {out['verdict']}")
    print(f"  scanned: {out['scanned']['pin_glob']} + "
          f"{len(DURABLE_STATE_PATHS)} declared durable-state path(s)")

    pins = out["untracked_pins"]
    if pins:
        print(f"\n  UNTRACKED PINS ({len(pins)}) -- outside git, so outside the suite baseline,")
        print("  outside a fixed-revision review, and outside every prior-art search:")
        for p in pins[:10]:
            print(f"    {p}")
        if len(pins) > 10:
            print(f"    ... +{len(pins) - 10} more")

    unpushed = out["unpushed_commits"]
    if unpushed:
        print(f"\n  UNPUSHED ({len(unpushed)}) -- exists on this disk and nowhere else:")
        for c in unpushed[:10]:
            print(f"    {c['sha']}  {c['subject']}")
        if len(unpushed) > 10:
            print(f"    ... +{len(unpushed) - 10} more")

    dirty = out["uncommitted_durable_state"]
    if dirty:
        print(f"\n  DURABLE STATE DIVERGED ({len(dirty)}) -- these files carry a durability")
        print("  CLAIM that git does not currently back:")
        for d in dirty:
            print(f"    {d['path']}  +{d['added']} -{d['removed']}")

    fresh = out.get("new_untracked_pins") or []
    if args.gate:
        if fresh:
            print(f"\n[durability] GATE FAIL -- {len(fresh)} pin(s) not in the baseline:")
            for p in fresh:
                print(f"    {p}")
            print("  Land them, or re-freeze deliberately with --freeze.")
            return 1
        print("\n[durability] gate ok -- no untracked pin beyond the frozen population")
    return 0


if __name__ == "__main__":
    sys.exit(main())
