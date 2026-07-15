"""Fence workspace (R2 / T053) -- the fence as a first-class object, not a naming convention.

The r2 failure this retires: a fence was 3-4 files bound by convention, a half confabulated
the filenames, and the round died on the convention. Here the workspace OWNS the structure:

  fences/<id>/brief.md            (M1-BRIEF: five sections, checked at seal)
  fences/<id>/half_a.md           (M1-CF: every verdict tagged, checked at seal)
  fences/<id>/half_b.md
  fences/<id>/pv_report.json      (M1-PV: machine-written by run_pv, never by hand)
  fences/<id>/reconciliation.md   (seals ONLY after both halves sealed + PV run + every
                                   MISSING citation acknowledged + authors independent)
  fences/<id>/fence.json          (state: question, tier, seals{slot: {by, at}})

Slot paths are DERIVED (`slot_path`), never typed: an unknown slot name is a refusal, so
the confabulated-filename class is unrepresentable. The method contract's mechanical
checks run AT SEAL TIME (the moment of commitment), not at post-mortem:
  - brief        -> M1-BRIEF sections 1-5 present;
  - half_a/b     -> every verdict line carries exactly one M1-CF tag;
  - reconciliation -> order (both halves sealed), PV run, each PV-MISSING citation
                    acknowledged BY NAME in the text (section-scoped invalidation, M1-PV),
                    and half authors differ (P2: wrongness caught by INDEPENDENCE).

A seal is append-only state, not cryptography: the enforcement layer is the door verb +
guards, same trust model as the task ledger. Root overridable via AKASHIC_FENCE_ROOT
(tests run hermetic); default lives under the repo so fences are git-durable.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SLOTS = ("brief", "half_a", "half_b", "reconciliation")
_SLOT_FILES = {"brief": "brief.md", "half_a": "half_a.md", "half_b": "half_b.md",
               "reconciliation": "reconciliation.md"}
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

# M1-BRIEF: the five mandatory sections, matched loosely on the heading text.
_BRIEF_SECTIONS = ("CHARTER", "INPUTS", "RULES OF ENGAGEMENT", "THE QUESTION", "OUTPUT CONTRACT")
# M1-CF: exactly one tag per verdict line. A verdict line = starts with V<number>.
_CF_TAGS = ("CERTAIN", "DESIGN", "INFERRED", "UNCERTAIN")
_VERDICT_RE = re.compile(r"^\s*V\d+[.)]\s", re.MULTILINE)
_TAG_RE = re.compile(r"\[(%s)\]" % "|".join(_CF_TAGS))
# M1-PV: file citations = repo-relative paths with an extension, optionally :line.
_CITE_RE = re.compile(r"\b((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,6})(?::(\d+))?")


def _root() -> str:
    return os.environ.get("AKASHIC_FENCE_ROOT") or os.path.join(_REPO_ROOT, "fences")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir(fence_id: str) -> str:
    if not _ID_RE.match(fence_id or ""):
        raise ValueError(f"illegal fence id {fence_id!r}")
    return os.path.join(_root(), fence_id)


def _state_path(fence_id: str) -> str:
    return os.path.join(_dir(fence_id), "fence.json")


def _load(fence_id: str) -> Dict[str, Any]:
    p = _state_path(fence_id)
    if not os.path.exists(p):
        raise ValueError(f"no such fence {fence_id!r} (open it first: fence open)")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(fence_id: str, state: Dict[str, Any]) -> None:
    with open(_state_path(fence_id), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------- the door verbs
def open_fence(fence_id: str, *, question: str, tier: str = "full", by: str = "") -> Dict[str, Any]:
    """Create the workspace. Idempotent for the same id (re-open returns existing state)."""
    d = _dir(fence_id)
    if os.path.exists(_state_path(fence_id)):
        return _load(fence_id)
    os.makedirs(d, exist_ok=True)
    state = {"id": fence_id, "question": question, "tier": tier, "opened_by": by,
             "opened_at": _now(), "seals": {}, "pv": None}
    _save(fence_id, state)
    return state


def slot_path(fence_id: str, slot: str) -> str:
    """THE anti-confabulation seam: the tool derives the path; an unknown slot is a refusal."""
    if slot not in _SLOT_FILES:
        raise KeyError(f"unknown slot {slot!r} -- slots are exactly {list(_SLOT_FILES)}")
    _load(fence_id)   # fence must exist
    return os.path.join(_dir(fence_id), _SLOT_FILES[slot])


def write_slot(fence_id: str, slot: str, text: str, *, by: str = "") -> str:
    """Write INTO a slot. Sealed slots are immutable (correct by a new fence, never edit)."""
    p = slot_path(fence_id, slot)
    state = _load(fence_id)
    if slot in state["seals"]:
        raise ValueError(f"slot {slot!r} is SEALED -- sealed slots are immutable")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    state.setdefault("authors", {})[slot] = by
    _save(fence_id, state)
    return p


def read_slot(fence_id: str, slot: str) -> str:
    p = slot_path(fence_id, slot)
    if not os.path.exists(p):
        return ""
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- M1-PV
def run_pv(fence_id: str, *, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """The pre-reconciliation verification pass, mechanical: glob every file citation in
    BOTH halves against the live repo. Line numbers beyond the file's length count as
    MISSING (fabricated detail). Writes pv_report.json -- machine-written, never by hand."""
    root = repo_root or _REPO_ROOT
    state = _load(fence_id)
    missing: List[str] = []
    verified: List[str] = []
    for slot in ("half_a", "half_b"):
        text = read_slot(fence_id, slot)
        for m in _CITE_RE.finditer(text):
            rel, line = m.group(1), m.group(2)
            cite = f"{rel}:{line}" if line else rel
            p = os.path.join(root, rel.replace("/", os.sep))
            ok = os.path.exists(p)
            if ok and line:
                try:
                    with open(p, encoding="utf-8", errors="replace") as f:
                        ok = int(line) <= sum(1 for _ in f)
                except OSError:
                    ok = False
            (verified if ok else missing).append(f"{slot}: {cite}")
    report = {"ran_at": _now(), "verified": sorted(set(verified)),
              "missing": sorted(set(missing))}
    with open(os.path.join(_dir(fence_id), "pv_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    state["pv"] = {"ran_at": report["ran_at"], "missing_count": len(report["missing"])}
    _save(fence_id, state)
    return report


# ---------------------------------------------------------------- seal-time checks
def _check_brief(text: str) -> List[str]:
    up = text.upper()
    return [f"M1-BRIEF section missing: {s}" for s in _BRIEF_SECTIONS if s not in up]


def _check_half(text: str) -> List[str]:
    problems = []
    if not _VERDICT_RE.search(text):
        problems.append("no verdict lines found (expected V1./V2./... items)")
    for line in text.splitlines():
        if re.match(r"^\s*V\d+[.)]\s", line) and not _TAG_RE.search(line):
            problems.append(f"M1-CF tag missing on verdict: {line.strip()[:80]!r} "
                            f"(tag with one of {list(_CF_TAGS)})")
    return problems


def _check_reconciliation(fence_id: str, text: str, state: Dict[str, Any],
                          by: str) -> List[str]:
    problems = []
    for h in ("half_a", "half_b"):
        if h not in state["seals"]:
            problems.append(f"order: {h} is not sealed yet (reconciliation comes LAST)")
    if not state.get("pv"):
        problems.append("M1-PV has not run (run_pv / fence pv) -- verify evidence before reading arguments")
    else:
        try:
            with open(os.path.join(_dir(fence_id), "pv_report.json"), encoding="utf-8") as f:
                report = json.load(f)
        except OSError:
            report = {"missing": []}
        for cite in report.get("missing", []):
            bare = cite.split(": ", 1)[-1].split(":")[0]
            if bare not in text:
                problems.append(f"M1-PV MISSING citation unacknowledged: {cite} -- name it "
                                "and retire its section (section-scoped invalidation)")
    authors = state.get("authors", {})
    a, b = authors.get("half_a"), authors.get("half_b")
    if a and b and a == b:
        problems.append(f"author independence violated: both halves by {a!r} "
                        "(P2 -- separate contexts or it is not a fence)")
    return problems


def seal(fence_id: str, slot: str, *, by: str = "") -> Tuple[bool, List[str]]:
    """Seal a slot: run its mechanical checks; on pass, freeze it. Returns (ok, problems)."""
    state = _load(fence_id)
    if slot not in _SLOT_FILES:
        raise KeyError(f"unknown slot {slot!r}")
    if slot in state["seals"]:
        return True, []   # idempotent: already sealed
    text = read_slot(fence_id, slot)
    if not text.strip():
        return False, [f"slot {slot!r} is empty -- nothing to seal"]
    if slot == "brief":
        problems = _check_brief(text)
    elif slot in ("half_a", "half_b"):
        problems = _check_half(text)
    else:
        problems = _check_reconciliation(fence_id, text, state, by)
    if problems:
        return False, problems
    state["seals"][slot] = {"by": by, "at": _now()}
    _save(fence_id, state)
    return True, []


def fence_status(fence_id: str) -> Dict[str, Any]:
    """Render-ready state: slots present/sealed, authors, PV summary."""
    state = _load(fence_id)
    slots = {}
    for s in SLOTS:
        slots[s] = {"written": bool(read_slot(fence_id, s).strip()),
                    "sealed": s in state["seals"],
                    "author": state.get("authors", {}).get(s, "")}
    return {"id": state["id"], "question": state["question"], "tier": state["tier"],
            "slots": slots, "seals": state["seals"], "pv": state.get("pv"),
            "closed": "reconciliation" in state["seals"]}


def list_fences() -> List[Dict[str, Any]]:
    root = _root()
    out = []
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return []
    for n in names:
        try:
            out.append(fence_status(n))
        except (ValueError, OSError, json.JSONDecodeError):
            continue
    return out
