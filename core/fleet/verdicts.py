"""Verdict file-back -- what a fan branch SAID, and what a non-author later ESTABLISHED.

Semantic Relationship: Adjudication judges Verdict (joined on ask_id, never same author).

WHY THIS EXISTS (T290, fence r2 reconciled 2026-08-12 -- see
docs/library/design/20260812_fence-r2-reconciliation_825c9a.md): residents answer fans with
identity and an archive (T261), and nothing remembers whether their answers survived
scrutiny. Without that record, "residency helps" stays an anecdote and kimi's standing
objection (residents.py header: persistence has never been isolated as the cause of a win)
stays permanently open. This module is the raw material for settling it -- either way.

TWO PLANES, TWO AUTHORS, and the separation is the whole design:

    residents:verdicts:log        one record per ask_id: what the branch answered
    residents:adjudications:log   a later record by a NON-AUTHOR: confirmed | refuted

THE LAWS, each bought in the round-2 fence:

  OPERATOR-ONLY ADJUDICATION (Heimdall C1, accepted whole). `by` is a caller-declared
  string and nothing cryptographically verifies it, so the adjudicator set is the guard:
  `by` must be in adjudicators() -- env AKASHIC_ADJUDICATORS, default daniil+claude -- AND
  must not equal the verdict's own agent. A resident grading itself is the T255 class
  (a player-declared field nothing verifies); an operator grading their OWN filed verdict
  is the same defect wearing a badge.

  LESSONS NEVER ADJUDICATE (Heimdall's BLIND, accepted). A lesson, note, or bus message
  citing an ask_id moves nothing here: calibration reads ONLY the adjudication log. The
  learning store is an archive, not a back door.

  ABSENCE IS VISIBLE, NEVER SUCCESS (T178 law). An unadjudicated verdict counts
  adjudicated=0 forever; an undeclared question shape stores as 'undeclared', its own
  bucket. calibration() returns COUNTS ONLY -- rates, Wilson floors and the card render
  are RC2's job (T291), which owns the n>=5 / n>=20 honesty gates.

  COLD TWINS ARE FIRST-CLASS (Navi's fairness amendment -- the pre-registered persistence
  claim needs >=20 adjudicated matched pairs per shape). `cold_twin_of` records the pairing
  at write time; nobody reconstructs it from timestamps. A cold tier-0 branch files under
  agent='blind' (T261's tier vocabulary).

APPEND-ONLY, per the substrate's own physics. Projections derive; nothing rewrites. A
re-adjudication appends and the projection takes the LATEST record per ask_id -- the
history of a corrected call survives, because "what did we believe on Tuesday" is a
question about the past.

NOT IN THIS MODULE, deliberately: rendering and rates (RC2/T291), routing by calibration
(needs RC2 data first), wiring into the ask door (RC3/T292), and any identity verification
stronger than the operator set (that is T088a's registration plane).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.store import create_store

#: One global list per plane, oldest-first. Global rather than per-agent shards because the
#: load-bearing queries are CROSS-resident ("all normative verdicts this month", "every
#: unadjudicated ask") and a single scan cannot miss a shard -- the T259 roles-log posture,
#: restated here so the day it grows chatty the revisit has an address.
_VERDICTS_KEY = "residents:verdicts:log"
_ADJUD_KEY = "residents:adjudications:log"

#: The declared question-shape vocabulary -- the fan doctrine's own rubric rows. 'undeclared'
#: is NOT in the vocabulary: it is the stored name of absence, assignable only by omission.
SHAPES = ("descriptive", "normative", "generative", "coverage")

OUTCOMES = ("confirmed", "refuted")


def _store():
    return create_store()


def _corrupt_row(where: str, index: int, raw: str) -> None:
    """A dropped record announces itself. Never silent (the T262 law, inherited verbatim)."""
    import sys as _sys
    print(f"[verdicts] CORRUPT ROW at {where}[{index}] -- unreadable and SKIPPED "
          f"({str(raw)[:60]!r}). The remaining rows are intact; this one is lost.",
          file=_sys.stderr)


def _rows(key: str) -> List[Dict[str, Any]]:
    raw = _store().lrange(key, 0, -1) or []
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(raw):
        try:
            out.append(json.loads(r))
        except Exception:
            _corrupt_row(key, i, r)
    return out


def adjudicators() -> set:
    """The trusted adjudicator set -- env AKASHIC_ADJUDICATORS (comma-sep), default
    daniil+claude. Config rather than a constant so a new conductor seat is one env edit,
    and lowercase so 'Daniil' and 'daniil' are one person, not two."""
    raw = os.environ.get("AKASHIC_ADJUDICATORS", "") or "daniil,claude"
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def file_verdict(*, agent: str, ask_id: str, question_shape: str, gist: str,
                 geometry: str = "", role: str = "",
                 cold_twin_of: str = "") -> Dict[str, Any]:
    """Record what a branch answered. One verdict per ask_id -- dedup is idempotency
    (the LearningStore law: a second write with the same key is a retry, not a sibling).

    Refusals are LOUD and NAMED, per the house grammar: an unknown shape lists the
    vocabulary, a duplicate names the colliding id.
    """
    agent = str(agent or "").strip()
    ask_id = str(ask_id or "").strip()
    if not agent:
        raise ValueError(
            "file_verdict needs an agent -- the resident that answered, or 'blind' for a "
            "cold tier-0 branch (T261 tier vocabulary)")
    if not ask_id:
        raise ValueError("file_verdict needs an ask_id -- a verdict nothing can join is "
                         "a record about nothing")

    shape = str(question_shape or "").strip().lower()
    if not shape:
        # Stored absence, never a guess and never a drop: 'undeclared' is its own bucket in
        # every projection, so a fan that skipped the declaration is VISIBLE (T228 law).
        shape = "undeclared"
    elif shape not in SHAPES:
        raise ValueError(
            f"unknown question_shape '{question_shape}' -- this plane speaks: "
            f"{', '.join(SHAPES)} (or omit it and the verdict files as 'undeclared'). "
            f"Shapes are the fan doctrine's rubric rows; a new one is a doctrine "
            f"amendment, not a typo.")

    if any(r.get("ask_id") == ask_id for r in _rows(_VERDICTS_KEY)):
        raise ValueError(
            f"refused: a verdict for ask '{ask_id}' is already filed -- one verdict per "
            f"ask, dedup is idempotency. A corrected view is an ADJUDICATION, not a "
            f"second verdict.")

    rec = {
        "agent_id": agent, "ask_id": ask_id, "question_shape": shape,
        "gist": " ".join(str(gist or "").split())[:500],
        "geometry": str(geometry or "").strip(),
        "role": str(role or "").strip(),
        "cold_twin_of": str(cold_twin_of or "").strip(),
        "ts": time.time(),
    }
    _store().rpush(_VERDICTS_KEY, json.dumps(rec, ensure_ascii=False))
    return rec


def adjudicate(*, ask_id: str, outcome: str, by: str,
               receipt: str = "") -> Dict[str, Any]:
    """Record what a NON-AUTHOR established about a filed verdict.

    OPERATOR-ONLY BY DEFAULT (fence r2 H-C1): `by` must be in adjudicators() and must not
    be the verdict's own agent. Both refusals name the party and the rule, because a
    refusal that does not say why trains the reader to route around it.
    """
    ask_id = str(ask_id or "").strip()
    by = str(by or "").strip()
    oc = str(outcome or "").strip().lower()

    if oc not in OUTCOMES:
        raise ValueError(
            f"unknown outcome '{outcome}' -- an adjudication says one of: "
            f"{', '.join(OUTCOMES)}. 'Unadjudicated' is not an outcome; it is the "
            f"absence this record would end.")

    verdict = None
    for r in _rows(_VERDICTS_KEY):
        if r.get("ask_id") == ask_id:
            verdict = r
            break
    if verdict is None:
        raise ValueError(
            f"refused: no filed verdict for ask '{ask_id}' -- an adjudication with "
            f"nothing to join is a record about nothing. File the verdict first "
            f"(resident verdict-file).")

    if by.lower() not in adjudicators():
        raise ValueError(
            f"refused: '{by}' is not in the adjudicator set. Adjudication is "
            f"OPERATOR-ONLY by default (fence r2 H-C1: `by` is caller-declared and "
            f"nothing verifies it, so the set is the guard -- env AKASHIC_ADJUDICATORS). "
            f"A resident's confirmation belongs in a reply or a lesson; neither moves "
            f"calibration.")

    if by.lower() == str(verdict.get("agent_id") or "").lower():
        raise ValueError(
            f"refused: '{by}' filed this verdict and may not adjudicate their own "
            f"answer -- author==adjudicator is the sock-puppet case, refused even "
            f"inside the operator set.")

    rec = {"ask_id": ask_id, "outcome": oc, "by": by,
           "receipt": " ".join(str(receipt or "").split())[:300], "ts": time.time()}
    _store().rpush(_ADJUD_KEY, json.dumps(rec, ensure_ascii=False))
    return rec


def verdicts(*, agent: Optional[str] = None, role: Optional[str] = None,
             shape: Optional[str] = None,
             cold_twin_of: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every verdict matching every given filter, oldest first. A filter nothing matches
    returns [] -- never the unfiltered log (the degraded answer must be a SUBSET)."""
    out = []
    for r in _rows(_VERDICTS_KEY):
        if agent is not None and r.get("agent_id") != agent:
            continue
        if role is not None and r.get("role") != role:
            continue
        if shape is not None and r.get("question_shape") != shape:
            continue
        if cold_twin_of is not None and r.get("cold_twin_of") != cold_twin_of:
            continue
        out.append(r)
    return out


def calibration(*, shape: Optional[str] = None,
                resident: Optional[str] = None) -> Dict[str, Any]:
    """COUNTS ONLY: per (shape, resident) cell and per-shape pool -- filed, adjudicated,
    confirmed, refuted. The latest adjudication per ask_id wins (append-only projection).

    No rates here, deliberately: at this fleet's n a point estimate is a lie with decimals
    (fence r2, convergent H-C2 + N-C2). RC2 renders rates behind its own n-floors; this
    function hands it honest integers.
    """
    latest: Dict[str, Dict[str, Any]] = {}
    for a in _rows(_ADJUD_KEY):
        latest[a.get("ask_id")] = a          # oldest-first scan -> last write wins

    cells: Dict[Tuple[str, str], Dict[str, int]] = {}
    shapes: Dict[str, Dict[str, int]] = {}
    for v in verdicts(shape=shape, agent=resident):
        key = (v.get("question_shape") or "undeclared", v.get("agent_id") or "?")
        cell = cells.setdefault(key, {"filed": 0, "adjudicated": 0,
                                      "confirmed": 0, "refuted": 0})
        pool = shapes.setdefault(key[0], {"filed": 0, "adjudicated": 0,
                                          "confirmed": 0, "refuted": 0})
        cell["filed"] += 1
        pool["filed"] += 1
        adj = latest.get(v.get("ask_id"))
        if adj is not None:
            cell["adjudicated"] += 1
            pool["adjudicated"] += 1
            if adj.get("outcome") in OUTCOMES:
                cell[adj["outcome"]] += 1
                pool[adj["outcome"]] += 1
    return {"cells": cells, "shapes": shapes}
