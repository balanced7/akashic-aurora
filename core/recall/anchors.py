"""Lesson anchor resolver -- does a lesson's premise still hold?

Build spec: docs/library/design/20260725_lesson-decay-reconciled-design_194ab2.md
(two rounds: claude + deepseek + kimi, on Daniel's reframe.)

Semantic Relationship: Lessons derive_currency_from StableAnchors

WHY THIS EXISTS
---------------
A lesson is a claim about a system that keeps moving. Measured 2026-07-25: 435 lessons, 92
citing a repo path, 23 citing a path that is gone. Worse than the count, the demonstration:
`intelligence_roadmap_and_spine1` fired into a live agent context prescribing work that was
already DONE, citing a roadmap that no longer exists -- and would have kept doing so forever.

Four tiers of decay were observed the same day. This module addresses tiers 1-2 (dead pointer,
completed imperative) and provides the anchor substrate tier 3 needs. Tier 4 -- a lesson that
is TRUE but silent about its boundary -- is deliberately NOT handled here; per the spec it is
boundary annotation driven by the outcome loop, not expiry, and pretending otherwise would be
the overclaim this whole arc exists to prevent.

WHAT THIS MODULE REFUSES TO DO
------------------------------
It does not retire, demote, hide or rank anything. It returns an advisory banner and per-
anchor verdicts; a human or the reading agent decides. That refusal is load-bearing:
`pytest_destroys_the_live_learning_index` had an obsolete RITUAL and a still-true second-order
lesson ("a suite that is dangerous to run is a suite nobody runs"). Auto-retirement would have
thrown away the part worth keeping.

THE THREE CONFESSIONS (kimi's, and the reason the module is shaped this way)
---------------------------------------------------------------------------
    UNCHECKABLE -- no anchor, or one this resolver cannot evaluate. NEVER "true".
    MISSING     -- the anchor resolved to nothing.
    STARVED     -- nothing at all was checkable. NEVER "all clean".
Four organs this week reported a confident zero while measuring nothing (the token meter, the
door-parity parser, the census OK-line, the pointer that failed open). A resolver that cannot
confess its own blindness becomes the fifth.

ANCHORS ARE STABLE IDS, NOT PATHS
---------------------------------
deepseek measured path-anchoring at ~78% false positive: two thirds of the dead-path lessons
cite `scripts/hooks/ -> agent/harness/hooks/` and are ABOUT that migration -- dead path,
current knowledge. Paths are still accepted (most existing lessons have nothing else) but they
carry `weak=True` and must never be treated as proof.

PIN ANCHORS AND THE GREEN-WHEN-BLIND MODE
-----------------------------------------
Settled by probe, not argument: a test marked `skipif(True)` whose body asserts False is
listed by `pytest --co` alongside real tests, and the run reports "1 passed, 1 skipped" with a
GREEN exit code. Collection cannot distinguish a guard from a ghost. 69 of 313 test files here
carry skips, including "pre-registered; impl pending (assertions frozen)" -- pins that have
never executed once. So a pin anchor resolves ONLY against an execution receipt, and SKIPPED
reads UNCHECKABLE (blindness), never RESOLVED and never MISSING (absence).
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))

_ATOM = re.compile(r"^art_\d{8}_[a-z0-9\-]+_[0-9a-f]{6}$")
_TASK = re.compile(r"^T\d{2,4}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_PIN = re.compile(r"^tests?/[A-Za-z0-9_\-./]+\.py::[A-Za-z0-9_]+$")
_PATH = re.compile(r"^(?:core|scripts|tests|docs|agent)/[A-Za-z0-9_\-./]+\.[a-z]{2,4}$")

# Anchors are mined from lesson text as a fallback for the 435 lessons written before `cites`
# existed. Deliberately conservative: a miss is silence, a false hit is noise, and noise is
# what gets an advisory muted.
_MINE = re.compile(
    r"\b(art_\d{8}_[a-z0-9\-]+_[0-9a-f]{6})\b"
    r"|\b(T\d{3})\b"
    r"|\b((?:core|scripts|tests|docs|agent)/[A-Za-z0-9_\-./]+\.(?:py|md|json))\b"
)


@dataclass
class Verdict:
    anchor: str
    kind: str
    status: str                 # RESOLVED | MISSING | UNCHECKABLE
    detail: str = ""
    weak: bool = False          # true for path anchors: usable, never authoritative


@dataclass
class Review:
    verdicts: List[Verdict] = field(default_factory=list)
    starved: bool = True
    banner: str = ""


def classify(anchor: str) -> str:
    a = (anchor or "").strip()
    if _ATOM.match(a):
        return "atom"
    if _TASK.match(a):
        return "task"
    if _PIN.match(a):
        return "pin"
    if _PATH.match(a):
        return "path"
    if _COMMIT.match(a):
        return "commit"
    return "unknown"


def _atom_exists(anchor: str, root: Path) -> bool:
    lib = root / "docs" / "library"
    if not lib.is_dir():
        return False
    tail = anchor[len("art_"):] if anchor.startswith("art_") else anchor
    return any(tail in p.name for p in lib.rglob("*.md"))


def _task_status(anchor: str, root: Path) -> Optional[str]:
    import json
    f = root / "state" / "coord" / "tasks.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    tasks = data.get("tasks", data)
    items = tasks.values() if isinstance(tasks, dict) else tasks
    for t in items:
        if isinstance(t, dict) and str(t.get("id") or t.get("task") or "") == anchor:
            return str(t.get("status") or t.get("state") or "")
    return None


def _commit_exists(anchor: str, root: Path) -> Optional[bool]:
    try:
        r = subprocess.run(["git", "-C", str(root), "cat-file", "-t", anchor],
                           capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and r.stdout.strip() == "commit"
    except (OSError, subprocess.SubprocessError):
        return None            # git unavailable -> blindness, not absence


def resolve(anchor: str, *, root: Path = ROOT,
            receipts: Optional[Dict[str, str]] = None) -> Verdict:
    """One anchor -> one verdict. Never raises; an error is UNCHECKABLE, not a pass."""
    kind = classify(anchor)
    try:
        if kind == "atom":
            ok = _atom_exists(anchor, root)
            return Verdict(anchor, kind, "RESOLVED" if ok else "MISSING",
                           "" if ok else "no atom projection carries this id")

        if kind == "task":
            st = _task_status(anchor, root)
            if st is None:
                return Verdict(anchor, kind, "MISSING", "not in the task ledger")
            # A DONE task does not invalidate a lesson by itself -- it means a lesson phrased
            # as an imperative ("next: build X") has been SATISFIED. Say that; do not judge.
            return Verdict(anchor, kind, "RESOLVED", f"ledger status: {st}")

        if kind == "pin":
            if not receipts:
                return Verdict(anchor, kind, "UNCHECKABLE",
                               "no execution receipt: a skipped pin reads green, so a green "
                               "suite is not proof this guard ran")
            state = str(receipts.get(anchor, "")).lower()
            if state == "passed":
                return Verdict(anchor, kind, "RESOLVED", "ran and passed")
            if state == "failed":
                return Verdict(anchor, kind, "MISSING", "ran and FAILED -- the guard is red")
            if state == "skipped":
                return Verdict(anchor, kind, "UNCHECKABLE",
                               "SKIPPED -- the guard did not execute; blindness, not absence")
            return Verdict(anchor, kind, "UNCHECKABLE", f"no receipt for this pin ({state!r})")

        if kind == "commit":
            ok = _commit_exists(anchor, root)
            if ok is None:
                return Verdict(anchor, kind, "UNCHECKABLE", "git unavailable")
            return Verdict(anchor, kind, "RESOLVED" if ok else "MISSING",
                           "" if ok else "no such commit")

        if kind == "path":
            ok = (root / anchor).exists()
            return Verdict(anchor, kind, "RESOLVED" if ok else "MISSING",
                           "path anchors are WEAK (~78% false-positive as a decay signal): a "
                           "moved file does not make the knowledge wrong",
                           weak=True)
    except Exception as exc:                       # never let a resolver failure read as a pass
        return Verdict(anchor, kind, "UNCHECKABLE", f"resolver error: {exc}")

    return Verdict(anchor, "unknown", "UNCHECKABLE", "unrecognised anchor form")


def mine(lesson: Dict[str, Any]) -> List[str]:
    """Anchors declared in `cites`, else mined from the text (pre-`cites` lessons)."""
    cites = lesson.get("cites")
    if isinstance(cites, (list, tuple)) and cites:
        return [str(c) for c in cites if c]
    blob = " ".join(str(v) for v in lesson.values() if isinstance(v, str))
    out, seen = [], set()
    for m in _MINE.finditer(blob):
        a = next(g for g in m.groups() if g)
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def review(lesson: Dict[str, Any], *, root: Path = ROOT,
           receipts: Optional[Dict[str, str]] = None) -> Review:
    """A whole lesson -> verdicts + an advisory banner. Decides nothing, retires nothing."""
    anchors_found = mine(lesson or {})
    verdicts = [resolve(a, root=root, receipts=receipts) for a in anchors_found]
    checkable = [v for v in verdicts if v.status != "UNCHECKABLE"]

    if not checkable:
        # STARVED. Not "clean" -- the distinction the census OK-line got wrong.
        n = len(verdicts)
        why = f"{n} anchor(s), none checkable" if n else "no anchors"
        return Review(verdicts, True, f"[premise UNCHECKED: {why} -- this is not a clean bill]")

    missing = [v for v in verdicts if v.status == "MISSING"]
    if missing:
        strong = [v for v in missing if not v.weak]
        weak_only = not strong
        lead = "premise may have moved" if weak_only else "premise MISSING"
        detail = ", ".join(f"{v.anchor} ({v.kind})" for v in missing[:3])
        tail = " -- weak path anchors only; a moved file is not a wrong lesson" if weak_only else ""
        return Review(verdicts, False, f"[{lead}: MISSING {detail}{tail}]")

    # "anchors resolve", NOT "premise holds". The difference is the whole tier-4 problem:
    # wake_consume_then_arm's anchors all resolve and the lesson is still incomplete -- it was
    # right about the transient case, silent about the structural one, and it nearly cost a
    # live 20%-of-a-core defect. Saying "premise holds" would endorse exactly the lesson this
    # resolver cannot judge. It reports what it checked, not what it did not.
    return Review(verdicts, False,
                  f"[{len(checkable)} anchor(s) resolve -- anchors only; "
                  f"says nothing about whether the lesson is complete]")
