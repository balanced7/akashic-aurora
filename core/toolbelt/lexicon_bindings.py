"""CONCEPT -> MECHANISM bindings, and the audit that keeps them honest.

THE ARC THIS CLOSES. Forked semantics is the DUAL of a homonym: one CONCEPT implemented by
several MECHANISMS whose tokens deliberately differ. A token-level tool searches for a shared
token, which is exactly what this class is DEFINED by lacking -- proven 2026-08-07 on
`drained`, whose three cursor families contain the word nowhere. So the guard Daniil has asked
for since 2026-06-19 cannot be a grep over SOURCE.

It CAN be a grep over a TABLE. claude#42d00626's construction:

    the fan DRAFTS the binding    ->    a human RATIFIES it    ->    this VERIFIES it forever

which converts "costly to author" from a permanent human cost into a one-time fan cost, and
is the grep everyone wanted -- pointed at data instead of at source.

THIS IS A DOMAIN, NOT A NEW CHECKER. core/toolbelt/audit.py already does belief-vs-state with
MATCH/DRIFT/UNKNOWN rows; this supplies rows to it. After a night whose standing lesson was
"grep for the successor before writing one", building a parallel auditor would have been the
joke writing itself.

THREE RULES:
  R1 MISSING     a bound mechanism no longer resolves -- the binding rotted.
  R2 UNCLAIMED   something matches the concept's `discover` pattern and is NOT bound.
                 THE RATCHET, and the rule that earns the file: this is how `drained` grew a
                 third cursor family with nobody noticing.
  R3 DOUBLE-BOUND  one mechanism under two concepts -- the dual of a homonym, invisible to
                 every token checker because there is no duplicate token to find.

UNKNOWN IS FIRST-CLASS. A file this process cannot read is UNKNOWN, never DRIFT: reading it
as drift would be the absence-inference this whole arc exists to end, committed by the guard
built to end it.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.toolbelt.audit import Row

ROOT = Path(__file__).resolve().parents[2]
BINDINGS_PATH = ROOT / "data" / "lexicon-bindings.json"


def load_bindings(path: Optional[Path] = None) -> Dict[str, Any]:
    """The table, minus its README block. {} when absent -- an unconfigured guard is a state."""
    p = Path(path or BINDINGS_PATH)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _read(rel: str) -> Optional[str]:
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def audit_bindings(bindings: Optional[Dict[str, Any]] = None) -> List[Row]:
    """Cross-read the binding table (belief) against the live tree (ground truth)."""
    tbl = load_bindings() if bindings is None else bindings
    rows: List[Row] = []
    seen_mech: Dict[str, str] = {}          # "file::pattern" -> first concept that claimed it

    for concept, rec in sorted(tbl.items()):
        mechs = rec.get("mechanisms") or []

        # ---- R1 MISSING / R3 DOUBLE-BOUND, per mechanism
        for m in mechs:
            f, pat = str(m.get("file", "")), str(m.get("pattern", ""))
            ref = f"{concept}::{os.path.basename(f)}"
            key = f"{f}::{pat}"

            if key in seen_mech and seen_mech[key] != concept:
                rows.append(Row(
                    domain="LEXICON", entry_ref=ref,
                    belief_a=concept, source_a="bindings",
                    belief_b=seen_mech[key], source_b="bindings",
                    verdict="DRIFT", rule="DOUBLE-BOUND",
                    detail=(f"{f}:{pat!r} is bound to BOTH {seen_mech[key]!r} and "
                            f"{concept!r} -- two concepts sharing one implementation means "
                            f"one of them is lying about what it is")))
                continue
            seen_mech.setdefault(key, concept)

            src = _read(f)
            if src is None:
                rows.append(Row(
                    domain="LEXICON", entry_ref=ref,
                    belief_a=pat, source_a="bindings",
                    belief_b=None, source_b="tree",
                    verdict="UNKNOWN", rule="",
                    detail=(f"cannot read {f} -- UNKNOWN, not drift. An unreadable file is "
                            f"not evidence that a binding rotted")))
                continue

            if pat and pat in src:
                rows.append(Row(
                    domain="LEXICON", entry_ref=ref,
                    belief_a=pat, source_a="bindings", belief_b=pat, source_b="tree",
                    verdict="MATCH",
                    detail=f"{m.get('sense') or pat}"))
            else:
                rows.append(Row(
                    domain="LEXICON", entry_ref=ref,
                    belief_a=pat, source_a="bindings", belief_b=None, source_b="tree",
                    verdict="DRIFT", rule="MISSING",
                    detail=(f"{f} no longer contains {pat!r} -- the binding rotted "
                            f"(renamed or deleted while the table still claims it)")))

        # ---- R2 UNCLAIMED: the ratchet
        disc = rec.get("discover")
        if not disc:
            continue
        claimed = [str(m.get("pattern", "")) for m in mechs]
        for f in (rec.get("discover_files") or []):
            src = _read(str(f))
            if src is None:
                rows.append(Row(
                    domain="LEXICON", entry_ref=f"{concept}::discover",
                    belief_a=disc, source_a="bindings", belief_b=None, source_b="tree",
                    verdict="UNKNOWN", rule="",
                    detail=f"cannot read discover_file {f}"))
                continue
            try:
                rx = re.compile(disc)
            except re.error as e:
                rows.append(Row(
                    domain="LEXICON", entry_ref=f"{concept}::discover",
                    belief_a=disc, source_a="bindings", belief_b=None, source_b="tree",
                    verdict="UNKNOWN", rule="",
                    detail=f"discover pattern does not compile: {e}"))
                continue
            for line in src.splitlines():
                if not rx.search(line):
                    continue
                # A hit is CLAIMED when some bound pattern appears on the same line.
                if any(c and c in line for c in claimed):
                    continue
                rows.append(Row(
                    domain="LEXICON", entry_ref=f"{concept}::discover",
                    belief_a=sorted(set(claimed)), source_a="bindings",
                    belief_b=line.strip()[:120], source_b="tree",
                    verdict="DRIFT", rule="UNCLAIMED",
                    detail=(f"{f}: {line.strip()[:100]!r} matches {concept!r}'s discover "
                            f"pattern but is bound to no mechanism -- either add it to the "
                            f"table or say why it is not this concept")))
    return rows


class LexiconDomain:
    """The audit domain. Belief = the ratified binding table; ground truth = the tree."""

    name = "LEXICON"

    def __init__(self, ground_truth_source: str = "bindings"):
        self._ground = ground_truth_source

    def run(self) -> List[Row]:
        return audit_bindings()
