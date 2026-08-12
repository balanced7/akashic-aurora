"""Pointer-promise census -- does the LINKED TARGET hold what the prose promises?

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS
---------------
2026-07-25: the public README cited `research/reviewed/` five times as "the verdicts,
preserved verbatim -- ~180 records; you can read every disagreement and who turned out to be
right." That directory held 51 files of raw April session JSONL and RB25 drill JSON: zero
verdicts. The records had moved to docs/library/report/ in 425cf52, which re-pointed every
FILE reference -- but a DIRECTORY reference does not 404 when its contents move, so it
survived the sweep and kept rendering as a working link.

All 31 local links on that page resolved. Zero dead. A link checker gives a clean bill of
health to exactly this rot, because it verifies RESOLVABILITY and the rot is in CONTENTS.
(lessons: link_checker_blind_to_moved_contents, readme_directory_pointer_fails_open)

THIS IS A REPORT, NOT A GATE. It always exits 0.
--------------------------------------------------
That is a design decision, not an oversight. kimi's adversarial review: the promise
vocabulary below is a manifest, it will drift, and the first time it false-positives on
Daniel's own prose over a synonym it is dead -- and takes the whole idea with it. The bar is
not "catch the README case", it is "never cry wolf on the principal". So it reports; a human
adjudicates. Wire it into the wrap census or run it by hand; do NOT add it to the CI gate
list without re-opening that decision.

WHAT IT CANNOT DO (stated, not discovered later)
------------------------------------------------
- It verifies GENUS, never INSTANCE. A target holding the right CLASS of file but the wrong
  specific ones passes clean (kimi FM2, unsolved).
- It needs a cardinal in the prose. "See the files here" is unfalsifiable and stays silent.
- It reads a bounded window around the pointer, so a promise separated from its pointer by
  several sentences is missed (kimi FM4, unsolved).
- Policy/practice divergence -- the contract designating one path while artifacts land at
  another -- is deliberately NOT adjudicated here. Which of policy-or-practice is wrong is a
  values call; a checker that decides it has become a seat with an opinion.

Run: py scripts/checkers/check_pointer_promises.py
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))

# Prose nouns that promise a CLASS of artifact, mapped to the filename/extension signature
# that class actually has on disk. Keep this small: every entry is a maintenance liability,
# and an over-broad vocabulary is how this starts crying wolf.
PROMISE_CLASSES: dict[str, tuple[str, ...]] = {
    "record": (".md",),
    "records": (".md",),
    "verdict": (".md",),
    "verdicts": (".md",),
    "review": (".md",),
    "reviews": (".md",),
    "report": (".md",),
    "reports": (".md",),
    "article": (".md",),
    "articles": (".md",),
}

# Directories whose contents are immutable projections: true when written, and our own
# principle is that corrections supersede rather than rewrite. Never scanned.
OUT_OF_SCOPE = (
    "docs/library/", "_archive/", "backups/", ".git/", ".claude/", "node_modules/",
    "tests/data/",
)

# How far below a claimed cardinal counts as a mismatch.
#
# The honest justification (kimi's verify corrected my first one): this is NOT defended by
# "the defining case was 0 against 180" -- that case is caught at ANY threshold above zero.
# 0.5 encodes a READER-TOLERANCE judgement: we call the prose a lie when a reader would find
# fewer than HALF the promised evidence. It is a values call about how misled a reader has to
# feel, not a measurement, and the next person tuning it should know that is what they are
# tuning. Note the admitted cost: 91 records against a claim of 180 passes clean.
#
# Calibrated for LARGE-cardinal promises ("~180 records"). Small claimed cardinals (<= 10)
# are weakly protected by this arithmetic -- check those by hand.
MISMATCH_RATIO = 0.5

# A directory's own scaffolding is not the class of thing prose promises. Counting these was
# the real protection gap kimi found: with K stray .md files present, a false promise of up
# to 2K records passed clean, because observed drifted up toward claimed.
NON_CLASS_STEMS = {"readme", "index", "license", "notice", "contributing", "changelog"}

# Prose scanned either side of a pointer, clipped at sentence boundaries. The binding rule
# is PROXIMITY -- the promise-cardinal nearest the pointer wins -- which answers the
# constructible false positive (kimi PATH 2 / deepseek (b)) without dropping the very common
# case where the cardinal precedes its link.
WINDOW = 240

# Captures [text](href) and [text](href "title") without swallowing the title into href.
_LINK = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_CARDINAL = re.compile(r"~?\s*([0-9][0-9,]*)\s*\+?\s*(?:of\s+\w+\s+)?([a-z]+)", re.I)


@dataclass
class Finding:
    doc: str
    target: str
    promise: str
    claimed: int | None
    observed: int
    verdict: str  # MISMATCH | UNVERIFIABLE | OK | NO-CARDINAL
    detail: str = ""


def live_surfaces(root: Path = ROOT) -> list[str]:
    """Markdown a reader actually reads today -- history is out of scope by design.

    Scoped to GIT-TRACKED files: what a visitor to the repo actually sees, not what
    happens to sit on this disk. The first run of this census scanned 8142 files and
    flagged a stale README inside .claude/worktrees/ -- a true finding about a file no
    reader will ever open. (lesson: repo_presentation_cleanup -- audit git ls-files,
    not ls.) Falls back to a filesystem walk only when git is unavailable, and says so.
    """
    import subprocess

    tracked: list[str] | None = None
    try:
        res = subprocess.run(
            ["git", "-C", str(root), "ls-files", "*.md"],
            capture_output=True, text=True, timeout=30,
        )
        if res.returncode == 0:
            tracked = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    except (OSError, subprocess.SubprocessError):
        tracked = None

    if tracked is None:
        print("[warn] git unavailable -- falling back to a filesystem walk; scope is wider "
              "than what a reader sees, so treat findings outside the repo tree as noise.")
        tracked = [p.relative_to(root).as_posix() for p in root.rglob("*.md")]

    return sorted(
        rel for rel in tracked
        if not any(rel.startswith(x) or f"/{x}" in f"/{rel}" for x in OUT_OF_SCOPE)
    )


def _count_class(target: Path, exts: tuple[str, ...]) -> int:
    """Count files of the promised class, excluding a directory's own scaffolding."""
    if not target.is_dir():
        return 0
    return sum(
        1 for p in target.rglob("*")
        if p.is_file()
        and p.suffix.lower() in exts
        and p.stem.lower() not in NON_CLASS_STEMS
    )


def scan_doc(doc: Path, root: Path = ROOT) -> list[Finding]:
    """Find directory pointers whose surrounding prose makes a falsifiable promise."""
    try:
        text = doc.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:  # unreadable doc is a loud unknown, never a silent pass
        return [Finding(str(doc), "", "", None, 0, "UNVERIFIABLE", f"unreadable: {exc}")]

    findings: list[Finding] = []
    for m in _LINK.finditer(text):
        href = m.group(2).split("#")[0].strip()
        if not href or href.startswith(("http://", "https://", "mailto:")):
            continue
        # Only DIRECTORY pointers: file pointers already fail closed with a 404.
        if not href.endswith("/"):
            continue

        # NEAREST promise-cardinal wins, measured by character distance from the pointer,
        # searching BOTH directions and stopping at sentence boundaries.
        #
        # Real prose puts the cardinal on either side: "~180 records" trails its pointer,
        # while "114 review records live in [docs/library/report/]" precedes it. A
        # forward-only window silently dropped every leading claim -- coverage fell to zero
        # on the live repo, and the honesty line (P8) is what surfaced it. Proximity is the
        # rule; direction is not.
        before = text[max(0, m.start() - WINDOW): m.start()]
        for stop in (". ", ".\n", "\n\n"):
            idx = before.rfind(stop)
            if idx != -1:
                before = before[idx + len(stop):]
        after = text[m.end(): m.end() + WINDOW]
        for stop in (". ", ".\n", "\n\n"):
            idx = after.find(stop)
            if idx != -1:
                after = after[:idx]

        claimed: int | None = None
        promise = ""
        best: int | None = None
        for text_chunk, base in ((before, -len(before)), (f" {m.group(1)} {after}", 0)):
            for cm in _CARDINAL.finditer(text_chunk):
                noun = cm.group(2).lower()
                if noun not in PROMISE_CLASSES:
                    continue
                dist = abs(base + cm.start()) if base < 0 else cm.start()
                if best is None or dist < best:
                    best = dist
                    claimed = int(cm.group(1).replace(",", ""))
                    promise = noun
        if claimed is None:
            # Unfalsifiable prose. Silence is correct -- see P4.
            findings.append(
                Finding(doc.name, href, "", None, 0, "NO-CARDINAL",
                        "directory pointer examined; prose makes no falsifiable claim")
            )
            continue

        target = (root / href.lstrip("/")).resolve()
        if not target.is_dir():
            findings.append(
                Finding(doc.name, href, promise, claimed, 0, "UNVERIFIABLE",
                        "pointer target does not exist or is not a directory")
            )
            continue

        observed = _count_class(target, PROMISE_CLASSES[promise])
        if observed < claimed * MISMATCH_RATIO:
            findings.append(
                Finding(doc.name, href, promise, claimed, observed, "MISMATCH",
                        f"prose promises ~{claimed} {promise}; target holds {observed}")
            )
        else:
            findings.append(Finding(doc.name, href, promise, claimed, observed, "OK"))
    return findings


def census_stats(root: Path = ROOT, live_docs: list[str] | None = None) -> dict:
    """Counts behind the report. `clean_claim` is False unless something was actually checked.

    This exists because the first draft printed "[OK] every falsifiable directory promise
    matches" whenever nothing was flagged -- which reads identically whether three promises
    were verified or zero were ever examined. A checker built against fails-open pointers
    shipped a fails-open summary line.
    """
    docs = live_docs if live_docs is not None else live_surfaces(root)
    findings: list[Finding] = []
    for rel in docs:
        p = root / rel
        if p.is_file():
            findings.extend(scan_doc(p, root=root))

    falsifiable = [f for f in findings if f.verdict != "NO-CARDINAL"]
    flagged = [f for f in findings if f.verdict in ("MISMATCH", "UNVERIFIABLE")]
    return {
        "docs": len(docs),
        "pointers": len(findings),        # every directory pointer examined
        "examined": len(falsifiable),     # those making a checkable claim
        "flagged": len(flagged),
        "clean_claim": bool(falsifiable) and not flagged,
        "findings": findings,
        "flagged_findings": flagged,
    }


def run_census(root: Path = ROOT, live_docs: list[str] | None = None) -> int:
    s = census_stats(root=root, live_docs=live_docs)

    print("=" * 68)
    print("POINTER-PROMISE CENSUS  (report only -- never blocks)")
    print("=" * 68)
    print(f"scanned {s['docs']} live doc(s)")
    print(f"  directory pointers examined : {s['pointers']}")
    print(f"  making a falsifiable claim  : {s['examined']}")
    print(f"  flagged                     : {s['flagged']}")

    if s["clean_claim"]:
        print(f"\n[OK] all {s['examined']} falsifiable promise(s) match their target's contents.")
    elif not s["examined"]:
        print("\n[NOTHING CHECKED] no falsifiable promise was found. This is NOT a clean bill "
              "of health -- it means nothing was verifiable, which may itself be the finding.")
    for f in s["flagged_findings"]:
        print(f"\n  [{f.verdict}] {f.doc} -> {f.target}")
        print(f"      {f.detail}")

    print("\nThis census REPORTS; a human decides. It verifies genus, not instance,")
    print("and it stays silent on promises with no number to check.")
    return 0  # by design -- see the module docstring


if __name__ == "__main__":
    sys.exit(run_census())
