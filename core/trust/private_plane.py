"""The private-plane leak guard: ingress, at the one place everything must pass.

DANIIL'S RULING, 2026-08-16: "Lets not commit the competency and surname stuff to the repo.
I want to make sure its internally accesible." His standing directive, 2026-08-15: "instead of
a dance for redaction we have procedures and protocol." His ingress principle: police traffic
closest to the source.

WHAT HAPPENED. Personal assessment material (a competency register grading the operator, two
peer portraits of him) was authored into research/in-flight/ (tracked), adopted into atoms
whose bodies landed in store/docs/report.jsonl (tracked), and rendered into docs/library/
(tracked). The repo is public. It was caught by hand at push -- pure egress, the position he
criticised.

WHY THE DIRECTORY MOVE WAS NOT ENOUGH, and this is the whole reason this module exists.
deepseek's fence counter (ask 4ec09cc3) named the class: "any generator that walks the merged
atom stream and writes to docs/ or store/ becomes an egress point", and -- the sharper half --
"existence metadata is a leak": a generator can publish private TITLES and IDS while publishing
no body at all. Verified minutes later on live data: chronicles/memory.md is a TRACKED,
auto-regenerated distillation of 633 notes, and its working-tree diff had already absorbed a
private portrait note. THE LEAK PATH IS REGENERATION, NOT AUTHORING. Moving files only stops
the author; it does nothing about every generator that will rebuild a tracked artifact
tomorrow from a store that still remembers.

MARKERS ARE DERIVED, NEVER DECLARED. The guard reads whatever actually lives in private/ and
builds its own markers -- atom short-hashes, slugs, note titles. A hand-maintained denylist
rots the moment someone adds a file, which is the same failure mode that made the allowlist
inversion right for the plane itself.

AND IT MUST STAY SPECIFIC. A marker like "daniil" or "report" would refuse every commit in the
repo, and a guard that fires on healthy commits trains everyone to pass --no-verify -- after
which its silence reads as all-clear while it is being routed around. Generic tokens are
dropped on purpose; precision is what keeps a guard alive.

SCOPE. This is the BACKSTOP half. The write-path half -- visibility stamped at mint,
plane-routed writes, plane-aware projectors -- is the larger arc deepseek's counter corrected:
two physical stores turn visibility into a second primary key, with real work required on id
allocation, CAS (hash the plane with the body or public/private collide), cross-plane
supersession (a migration event, never a store primitive), rebuild order (private is an
OVERLAY; public tombstones are authoritative subtraction) and backup (snapshot must cover both
without writing private cleartext into an artifact). None of that is this slice. This slice
makes the live hole un-reopenable while that gets built properly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

_REPO_ROOT = Path(__file__).resolve().parents[2]
PLANE_DIRNAME = "private"

# A marker must be distinctive enough that its appearance in a tracked file is evidence of a
# leak rather than a coincidence. These are dropped even if they appear in the plane.
_TOO_GENERIC = {
    "the", "and", "for", "with", "from", "this", "that", "report", "notes", "note", "md",
    "json", "jsonl", "txt", "atoms", "atom", "private", "assessments", "register", "daniil",
    "claude", "kimi", "deepseek", "codex", "session", "2026", "docs", "library",
}
_MIN_MARKER = 6


def plane_root(root: Optional[Path] = None) -> Path:
    return (Path(root) if root else _REPO_ROOT) / PLANE_DIRNAME


def _tokens_from_name(name: str) -> Set[str]:
    """Atom short-hashes and multi-word slugs are the distinctive parts of a filename."""
    out: Set[str] = set()
    stem = re.sub(r"\.(md|jsonl?|txt|ya?ml)$", "", name, flags=re.I)
    # trailing short hash, e.g. ..._ff00aa (SYNTHETIC example on purpose -- the first draft
    # of this comment used a real private id and the guard blocked its own commit)
    m = re.search(r"_([0-9a-f]{6,12})$", stem)
    if m:
        out.add(m.group(1))
    # Hyphenated slug, e.g. `someone-assessment-dossier`. THE FILTER APPLIES TO THE WHOLE
    # MARKER, NOT TO ITS PARTS -- caught by pin P1: requiring >=2 non-generic WORDS dropped
    # the live leak's real slug, because two of its three words are individually generic. A
    # multi-word slug is distinctive even when every word in it is common; it is drop-worthy
    # only when NO part carries information.
    #
    # (Examples here are SYNTHETIC by necessity, and the guard taught that lesson the hard
    # way: an earlier draft of this very comment quoted the real slug, so the module
    # describing the leak class became an instance of it and blocked its own commit. A guard's
    # own source is a tracked file like any other.)
    for chunk in re.split(r"[_\s]+", stem):
        parts = [p for p in chunk.split("-") if p and not p.isdigit()]
        if len(parts) >= 2 and any(p.lower() not in _TOO_GENERIC for p in parts):
            out.add("-".join(parts).lower())
    return out


def markers(root: Optional[Path] = None) -> Set[str]:
    """Every distinctive token identifying something that lives in the private plane.

    Derived from filenames plus any `id`/`title` fields inside jsonl records, because the
    store copy is the one that generators regenerate from -- and that copy is what published
    itself in the live incident."""
    base = plane_root(root)
    out: Set[str] = set()
    if not base.is_dir():
        return out
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        out |= _tokens_from_name(p.name)
        if p.suffix.lower() in (".jsonl", ".json"):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:                                # pragma: no cover - io guard
                continue
            for line in text.splitlines():
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                for field in ("id", "title", "name", "slug"):
                    v = str(rec.get(field) or "")
                    if v:
                        out |= _tokens_from_name(v)
    return {m for m in out
            if len(m) >= _MIN_MARKER and m.lower() not in _TOO_GENERIC}


def _inside_plane(path: Path, root: Optional[Path] = None) -> bool:
    try:
        path.resolve().relative_to(plane_root(root).resolve())
        return True
    except Exception:
        return False


def scan(paths: Iterable[str], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Findings for tracked files carrying a private marker.

    Files INSIDE the plane are never flagged: the guard protects the boundary, not the room,
    and a guard that fires on its own subject gets bypassed."""
    marks = markers(root)
    if not marks:
        return []
    findings: List[Dict[str, Any]] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = (Path(root) if root else _REPO_ROOT) / raw
        if not p.is_file() or _inside_plane(p, root):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:                                    # pragma: no cover - io guard
            continue
        low = text.lower()
        for m in sorted(marks):
            if m not in low:
                continue
            line_no = next((i for i, ln in enumerate(text.splitlines(), 1)
                            if m in ln.lower()), 0)
            findings.append({
                "path": str(p),
                "marker": m,
                "line": line_no,
                "remedy": (f"{p.name} carries {m!r}, which identifies private-plane content. "
                           "Either regenerate it with the private records excluded, or move "
                           "the artifact into private/. Do NOT hand-edit the marker out -- "
                           "the generator will put it back on the next run."),
            })
            break
    return findings


def scan_text(text: str, label: str = "text",
              root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Findings for a blob of prose that is about to become durable and public.

    ADDED 2026-08-16, AFTER THE MISS THAT PROVED IT NECESSARY. The first purge rewrote file
    CONTENT and was verified with `git log -S`, which searches content -- so four pushed
    COMMIT MESSAGES still named the artifacts and one carried the real atom ids. I verified
    the thing that was easy to query rather than the thing I had claimed.

    It is the generalised form of kimi's fence counter (ask 4ec09cc3): DERIVED RECORDS DO NOT
    INHERIT THEIR SOURCES' VISIBILITY -- "private material escapes not as a copied file, but
    as a paraphrase or summary written into the public plane". A commit message is a derived
    description; so is a ledger row, a lesson, a chronicle, a PR body. Any of them can name
    what it must not name while every file on disk stays clean."""
    marks = markers(root)
    if not marks or not text:
        return []
    low = str(text).lower()
    out: List[Dict[str, Any]] = []
    for m in sorted(marks):
        if m in low:
            out.append({
                "path": label, "marker": m, "line": 0,
                "remedy": (f"this {label} names {m!r}, which identifies private-plane "
                           "content. Describe the work without naming the artifact -- "
                           "existence metadata is a leak even when no body is published."),
            })
    return out


def report(paths: Iterable[str], root: Optional[Path] = None) -> Dict[str, Any]:
    """The frame that ships with the number. An empty result must be distinguishable from a
    guard that never ran -- absence of findings is not evidence of a clean tree."""
    marks = markers(root)
    paths = list(paths)
    if not marks:
        return {
            "markers": 0, "scanned": 0, "findings": [],
            "why": (f"no private plane at {plane_root(root)} -- nothing to protect, so this "
                    "is NOT a clean bill, it is an empty subject"),
            "scope": "derived markers from private/**; none found",
        }
    findings = scan(paths, root)
    return {
        "markers": len(marks), "scanned": len(paths), "findings": findings,
        "why": ("clean: no tracked path carries a private marker" if not findings
                else f"{len(findings)} tracked path(s) carry private-plane identifiers"),
        "scope": (f"{len(paths)} path(s) checked against {len(marks)} marker(s) derived "
                  f"from {plane_root(root)}; files inside the plane are exempt by design"),
    }
