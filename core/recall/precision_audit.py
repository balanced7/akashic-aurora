"""precision_audit -- the missing instrument: is recall ACCURATE?

WHY THIS EXISTS
---------------
Every architecture position in the 2026-07-27 arc -- Sol's cells, deepseek's rules-as-data,
claude's selection-first order -- was argued without a single retrieval accuracy number. kimi
named the hole, and it was aimed at the person who had spent the night hunting exactly this
shape:

    "We have never demonstrated a ranking failure BECAUSE WE HAVE NEVER MEASURED RANKING. The
     only instrument we built this arc was a membership census, so the only failures it COULD
     find were selection-shaped. Finding selection failures under a selection streetlight does
     not make selection the constraint; it makes it the only place we looked."

A missing instrument reporting as an absent problem is the confident-zero disease. This module
is the instrument.

WHAT IT MEASURES, AND WHY BOTH HALVES ARE REQUIRED
--------------------------------------------------
RAGAS splits retrieval evaluation in two (kimi's prior-art read), and we need both because the
open question is precisely which half is broken:

  CONTEXT PRECISION -- of what we surfaced, how much was on-point for the ACTION ACTUALLY TAKEN.
                       Low precision => RANKING is the constraint.
  CONTEXT RECALL    -- what should have surfaced and did not.
                       Misses => SELECTION is the constraint.

A precision-only audit cannot tell them apart: an item that never surfaced never enters the
sample, so the missing-item failure is invisible by construction. Building precision alone would
have reproduced the streetlight error one level down.

NOT THE SKIM TEST. kimi killed that one with claude's own walkthrough: usage is not relevance.
A dismissed item can be relevant; a used item can be wrong. "Did the agent use it" answers a
different question than "should it have been shown".

DISCIPLINE BAKED IN
-------------------
* BLIND packs. No usefulness counters, no credit history, no seat identity. A labeller who can
  see the ranker's prior opinion is echoing the instrument, not measuring it.
* LABEL COVERAGE always travels with precision (claude's lesson, after a Codex cross-check
  overturned an earlier framing): UNLABELLED IS NOT NEGATIVE. Counting unlabelled items as
  off-point turns an honest 50% into a false 20%.
* SEED-DETERMINISTIC sampling, so any published number is re-auditable.
* STARVED, never 100%, on an empty ledger. The audit must be able to confess its own blindness.

PRE-REGISTERED GO/NO-GO (fixed BEFORE looking at any data -- lesson: dual_blind_preregistration)
------------------------------------------------------------------------------------------------
  precision >= 0.80 AND misses_rate <= 0.20  -> SELECTION was the constraint. Ranking is
                                                adequate; proceed to injection/coverage work.
  precision <  0.60                          -> RANKING is broken corpus-wide. The build order
                                                inverts: fix ranking before adding planes.
  misses_rate > 0.40                         -> SELECTION confirmed dominant; give dark planes
                                                a retrieval path before touching the ranker.
  anything else                              -> INCONCLUSIVE. Say so; do not round toward the
                                                answer we already like.
"""
from __future__ import annotations

import glob
import json
import os
import random
from typing import Any, Dict, List, Optional

_DEFAULT_IMP = os.path.join(os.environ.get("TEMP", "/tmp"), "akashic_recall", "imp")

PRECISION_OK = 0.80
PRECISION_BROKEN = 0.60
MISSES_OK = 0.20
MISSES_DOMINANT = 0.40


def harvest(imp_dir: str = "", limit: int = 0) -> List[Dict[str, Any]]:
    """Read the impression ledger into (action, surfaced) records.

    NO NEW INSTRUMENTATION: the hook has been writing {"t": <target>, "s": [<sources>]} per
    firing all along. The audit corpus already existed -- it just had no reader.
    """
    d = imp_dir or _DEFAULT_IMP
    out: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(os.path.join(d, "*"))):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    t = str(row.get("t") or "")
                    srcs = [str(s) for s in (row.get("s") or []) if s]
                    if not t or not srcs:
                        continue
                    kind, _, rest = t.partition(":")
                    out.append({
                        "action": rest or t,
                        "action_kind": {"p": "path", "c": "command"}.get(kind, "other"),
                        "surfaced": srcs,
                        "session": os.path.basename(path).split(".")[0],
                    })
        except OSError:
            continue
    return out[-limit:] if limit else out


def sample(items: List[Dict[str, Any]], n: int = 30, seed: int = 1) -> List[Dict[str, Any]]:
    """Seed-deterministic draw: a published number that cannot be re-drawn cannot be audited."""
    if n >= len(items):
        return list(items)
    return random.Random(seed).sample(list(items), n)


def render_pack(items: List[Dict[str, Any]], bodies: Optional[Dict[str, str]] = None) -> str:
    """A BLIND labelling pack.

    Deliberately omits usefulness counters, credit history and seat identity. A labeller who can
    see that a lesson has 'helped 4x' is not judging relevance -- they are reading the ranker's
    prior opinion back to it, and the audit would measure our own agreement with ourselves.
    """
    bodies = bodies or {}
    lines = [
        "# RECALL PRECISION AUDIT -- blind labelling pack",
        "",
        "For each SURFACED item, judge it against THE ACTION ACTUALLY TAKEN (not the query text):",
        "  on   = this item was on-point for that action",
        "  off  = it was not",
        "  skip = you cannot tell (skip is NOT 'off' -- unlabelled is not negative)",
        "",
        "Then, per case, name any lesson that SHOULD have surfaced and did not (the recall arm).",
        "Reply as: <case>:<slot> on|off|skip   and   MISS <case> <source-id or description>",
        "",
    ]
    for i, it in enumerate(items, 1):
        lines.append(f"## case {i}  [{it['action_kind']}]")
        lines.append(f"ACTION: {it['action'][:300]}")
        for j, src in enumerate(it["surfaced"]):
            slot = chr(ord("a") + j)
            body = (bodies.get(src) or "").strip().replace("\n", " ")
            lines.append(f"  {i}:{slot}  {src}")
            if body:
                lines.append(f"        {body[:240]}")
        lines.append("")
    return "\n".join(lines)


def score(labels: Dict[str, Dict[str, str]], *, total_surfaced: int = 0,
          misses: Optional[Dict[str, Dict[str, List[str]]]] = None) -> Dict[str, Any]:
    """Precision + coverage + agreement + the recall arm. Never precision alone.

    `labels`: {labeller: {"<case>:<slot>": "on"|"off"|"skip"}}
    `misses`: {labeller: {"<case>": [source_or_description, ...]}}
    """
    misses = misses or {}
    per_item: Dict[str, List[str]] = {}
    for who, marks in (labels or {}).items():
        for key, val in (marks or {}).items():
            v = str(val).lower().strip()
            if v in ("on", "off"):
                per_item.setdefault(key, []).append(v)

    if not per_item:
        return {"status": "STARVED", "precision": None, "recall": None,
                "labelled": 0, "label_coverage": 0.0, "agreement": None,
                "disputed": [], "misses_named": 0, "verdict":
                "no labelled observations -- the audit measured nothing, which is a "
                "confession, not a score"}

    # MAJORITY per item; a tie is DISPUTED and goes to a fence round rather than a coin flip.
    on = off = 0
    disputed: List[str] = []
    for key, votes in per_item.items():
        n_on, n_off = votes.count("on"), votes.count("off")
        if n_on and n_off:
            disputed.append(key)
        if n_on > n_off:
            on += 1
        elif n_off > n_on:
            off += 1
    labelled = on + off
    agreement = 1.0 - (len(disputed) / len(per_item)) if per_item else None

    # UNLABELLED IS NOT NEGATIVE. Precision is computed over labelled items only, and always
    # travels with the coverage it was computed over.
    coverage = (labelled / total_surfaced) if total_surfaced else 1.0
    precision = (on / labelled) if labelled else None

    named = sum(len(v) for m in misses.values() for v in m.values())
    cases = {k.split(":")[0] for k in per_item}
    miss_cases = {c for m in misses.values() for c in m}
    misses_rate = (len(miss_cases) / len(cases)) if cases else None
    recall = (1.0 - misses_rate) if misses_rate is not None else None

    if precision is None:
        verdict = "INCONCLUSIVE -- nothing labelled on|off"
    elif precision >= PRECISION_OK and (misses_rate is None or misses_rate <= MISSES_OK):
        verdict = ("SELECTION was the constraint -- ranking is adequate; the next work is "
                   "injection and giving dark planes a path")
    elif precision < PRECISION_BROKEN:
        verdict = ("RANKING is broken corpus-wide -- the build order INVERTS: fix ranking "
                   "before adding planes")
    elif misses_rate is not None and misses_rate > MISSES_DOMINANT:
        verdict = ("SELECTION dominant -- give the dark planes a retrieval path before "
                   "touching the ranker")
    else:
        verdict = "INCONCLUSIVE -- do not round toward the answer we already like"

    return {"status": "OK", "precision": precision, "recall": recall,
            "labelled": labelled, "on": on, "off": off,
            "label_coverage": round(coverage, 4), "agreement": agreement,
            "disputed": sorted(disputed), "misses_named": named,
            "misses_rate": misses_rate, "verdict": verdict}
