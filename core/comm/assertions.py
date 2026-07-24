"""Pre-flight assertions (T068-R3 / deepseek M10) -- verify a directed answer's FACTUAL
claims before it leaves the runner.

Design: docs/library/report/20260715_deepseek-t068-r3-design-pre-flight-asser_5eb933.md ("the seat this gate
protects -- I know exactly what claims I'm tempted to make"). NOT a fence review (that
is post-send, different agent) and NOT a quality gate: a wrong design with verifiable
citations passes; a correct design with a fabricated citation holds.

Three assertions:
  A1  file:line citations resolve (file exists, line within bounds)   -> HOLD
  A2  event:...:<id> evidence citations exist in the event store       -> HOLD
  A3  closure language (fixed/shipped/...) names a pin/task/commit     -> WARNING only

Fail-open doctrine everywhere: a broken resolver, a store hiccup, or the kill switch
(BIFROST_PREFLIGHT_ASSERT=0, read at CALL time) must never wedge a runner -- losing a
reply is the worse bug. The caller owns the two-cycle retry-then-send-anyway policy;
this module only reports. Pure text-in, findings-out: testable without a runner.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

# path/with/slashes.ext:line -- the fence_workspace citation shape, line REQUIRED
# (a bare path has no bounds to verify; prose mentions of files stay unflagged).
_CITE_RE = re.compile(
    r"\b((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,6}):(\d{1,6})\b")
# event:<anything>:<ms>-<seq> -- resolve() owns the exact ref grammar
_EVENT_RE = re.compile(r"\bevent:[A-Za-z0-9_.:-]*?(\d{6,}-\d+)\b")
_CLOSURE_RE = re.compile(r"\b(fixed|resolved|shipped|built|closes|done)\b", re.IGNORECASE)
# pins (P1/B2/R3...), task ids, commit hashes, test paths -- any ONE satisfies A3
_EVIDENCE_RE = re.compile(
    r"\b[PBQRSFK]\d{1,2}\b|\bT\d{2,3}\b|\b[0-9a-f]{7,40}\b|\btests?/[\w./-]+\.py\b")


def _root(root: Optional[str] = None) -> Path:
    return Path(root) if root else Path(__file__).resolve().parents[2]


def check_file_line_cites(text: str, root: Optional[str] = None) -> List[str]:
    """A1: every path:line citation resolves. Returns human-readable failures."""
    failures: List[str] = []
    base = _root(root)
    for rel, line_s in _CITE_RE.findall(str(text or "")):
        try:
            p = base / rel.replace("/", os.sep)
            if not p.is_file():
                failures.append(f"{rel}:{line_s} -> file does not exist")
                continue
            line = int(line_s)
            with open(p, "rb") as fh:
                n = sum(1 for _ in fh)
            if line < 1 or line > n:
                failures.append(f"{rel}:{line_s} -> file has {n} lines, "
                                f"line {line_s} is out of bounds")
        except Exception:
            continue                     # fail-open per finding: a parser edge never holds
    return failures


def check_event_cites(text: str) -> List[str]:
    """A2: every event citation resolves in the event store. A resolver ERROR is
    fail-open (skip); only a clean not-found is a fabrication finding."""
    failures: List[str] = []
    refs = ["event:" + m.split("event:", 1)[-1] if False else m
            for m in (mm.group(0) for mm in _EVENT_RE.finditer(str(text or "")))]
    if not refs:
        return failures
    try:
        from core.events.event_query import get_event_query
        eq = get_event_query()
    except Exception:
        return failures
    for ref in refs:
        try:
            ev, _why = eq.resolve(ref)
            if ev is None:
                failures.append(f"{ref} -> no such event in the store (fabricated evidence?)")
        except Exception:
            continue
    return failures


def check_closure_evidence(text: str) -> List[str]:
    """A3 (warning-only): closure language should name a pin, task id, commit, or test
    path so the recipient can verify the claim."""
    t = str(text or "")
    if _CLOSURE_RE.search(t) and not _EVIDENCE_RE.search(t):
        return ["reply claims closure ('fixed'/'shipped'/...) but names no pin, task, "
                "commit, or test -- add a reference (e.g. 'pins P1-P3 green, T068')"]
    return []


def run_preflight(text: str, root: Optional[str] = None) -> Tuple[bool, str, str]:
    """The orchestrator: returns (held, feedback, warnings). held=True means A1/A2
    findings exist -- the caller should feed `feedback` back for ONE fix round, then
    send anyway LOUDLY (two-cycle fail-open). `warnings` is A3, never holds."""
    if os.environ.get("BIFROST_PREFLIGHT_ASSERT", "1") == "0":
        return False, "", ""
    try:
        a1 = check_file_line_cites(text, root)
        a2 = check_event_cites(text)
        a3 = check_closure_evidence(text)
    except Exception:
        return False, "", ""             # the gate itself failing must never hold a reply
    held = bool(a1 or a2)
    feedback = ""
    if held:
        lines = ["PRE-FLIGHT ASSERTION FAILED:"]
        if a1:
            lines.append("  file:line citations that don't resolve:")
            lines += [f"    - {f}" for f in a1]
        if a2:
            lines.append("  evidence citations that don't resolve:")
            lines += [f"    - {f}" for f in a2]
        lines.append("  Fix these citations or remove the claims, then the reply will send.")
        feedback = "\n".join(lines)
    return held, feedback, "; ".join(a3)
