"""Forge F2 -- the optimizer pass (docs/lesson-forge-design-2026-07.md sec.5, sec.9 F2).

Proposes ONE bounded rewrite per curator-named target, through an INJECTED model call --
this module owns selection, the blinded payload, parsing, and proposal bookkeeping; it
never talks to a network itself (the CLI layer bridges scripts/deepseek_chat, per the
locked optimizer-lane decision: deepseek offline, claude allowed at wrap).

Blinding (DeepSeek FM1, locked): the optimizer sees the lesson RECORD, AGGREGATE counters,
MINED vocabulary, and the REJECTED buffer -- never the raw contexts the gate replays.
Every draft goes straight through the Tier-0 gate (forge.gate_edit); PASS and UNMEASURABLE
stamp a pending proposal for the HUMAN to apply (trust ladder -- nothing here writes
lesson text); FAIL lands in the rejected buffer via the gate itself.

Proposal lifecycle: stamped -> reviewed by the human (--forge-check --apply on PASS, or an
ordinary re-record on UNMEASURABLE) -> or EXPIRED by the curator after PROPOSAL_TTL_DAYS
(sec.5: unreviewed proposals expire; the process-level textual learning rate).
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

MAX_TARGETS_PER_PASS = 2          # locked design decision 1
PROPOSAL_TTL_DAYS = 7.0           # unreviewed proposals expire (curator sweeps)
REHAB_MIN_SURFACED = 10           # rehab class definition (mirrors the audit / curator)

_DRAFT_RE = re.compile(r"PROPOSED-RECOMMENDATION-BEGIN\s*(.+?)\s*PROPOSED-RECOMMENDATION-END",
                       re.S | re.I)
_RATIONALE_RE = re.compile(r"RATIONALE:\s*(.+)", re.I)


# --------------------------------------------------------------------- selection
def select_targets(limit: int = MAX_TARGETS_PER_PASS, *,
                   store=None, learning_store=None) -> List[Dict[str, Any]]:
    """Curator-named rehab targets (surfaced >= 10, zero credit, active), minus lessons
    already provisional or carrying an unexpired pending proposal. Ordered by surfaced
    desc (the biggest surface-cost first). Fail-soft to []."""
    out: List[Dict[str, Any]] = []
    try:
        from core.learning.learning_store import get_learning_store, is_graduated, is_benched
        from core.recall.at_action import _load_use, _store
        from core.recall.curator import _credit
        ls = learning_store or get_learning_store()
        st = store or _store()
        for rec in ls.load_all_learnings_from_store():
            name = rec.get("experiment_name")
            if not name or is_graduated(rec) or is_benched(rec):
                continue
            if str(rec.get("forge_provisional") or "").strip():
                continue          # one edit in flight per lesson (echo-loop guard, sec.11)
            if _proposal_pending(rec):
                continue          # already queued for the human this cycle
            use = _load_use(st, f"learn:experiment:{name}")
            surfaced = int(use.get("surfaced", 0) or 0)
            if surfaced >= REHAB_MIN_SURFACED and _credit(use) == 0:
                out.append({"experiment_name": name, "surfaced": surfaced, "record": rec})
        out.sort(key=lambda r: -r["surfaced"])
    except Exception:
        return []
    return out[:max(0, int(limit))]


def _proposal_pending(rec: Dict[str, Any]) -> bool:
    try:
        prop = json.loads(str(rec.get("forge_proposal") or "") or "null")
    except Exception:
        return False
    if not isinstance(prop, dict) or not prop.get("draft"):
        return False
    from core.foundation.timeutil import to_epoch
    import time
    at = to_epoch(prop.get("at") or 0)
    return bool(at and (time.time() - at) / 86400.0 <= PROPOSAL_TTL_DAYS)


# --------------------------------------------------------------------- payload
def build_prompt(rec: Dict[str, Any], *, counters: Optional[Dict[str, Any]] = None,
                 trigger_terms: Optional[List[str]] = None) -> str:
    """The BLINDED optimizer prompt for one lesson. Contains the record, aggregates,
    mined vocabulary, and the rejected buffer -- and none of the replay contexts."""
    try:
        rejected = json.loads(str(rec.get("forge_rejected") or "[]"))
    except Exception:
        rejected = []
    rej_block = "\n".join(
        f"- REJECTED ({', '.join(r.get('reasons', [])[:2])}): {r.get('draft', '')[:200]}"
        for r in rejected[-5:]) or "(none yet)"
    counters = counters or {}
    parts = [
        # Goal framing per the red-team's own critique of its seat: "earn recall credit"
        # invites gaming; the real objective is help-at-the-right-moment.
        "You are the Forge optimizer for the Akashic Aurora lesson store. Rewrite ONE",
        "lesson's recommendation text so it HELPS an agent at exactly the right moment",
        "and stays silent otherwise. Credit follows help; it is never the goal itself.",
        "You see ONLY: the record, aggregate counters, mined trigger vocabulary, and",
        "previously-REJECTED drafts. You never see the raw contexts the deterministic",
        "gate replays, and the gate's checks are not scores to optimize against.",
        "",
        "RULES (violations are auto-rejected):",
        "1. Replace the RECOMMENDATION field only; output the full replacement text.",
        "2. Keep the shape: 'Use when <specific moment>, before <action>: <advice>.",
        "   Don't when <contraindication>.' Keep the contraindication if one exists.",
        "3. Token delta <= 40% of the incumbent.",
        "4. NO new factual claims: tighten, rephrase, reorder, drop -- never invent",
        "   tools, paths, numbers, or behaviors not present in the record.",
        "5. The trigger must name a REAL moment an agent hits (a plausible file, command,",
        "   or situation) -- never an artificially narrow token that matches nothing.",
        "6. MINED VOCABULARY terms mark where this lesson actually helped: keep the ones",
        "   that belong in a natural sentence; do NOT stuff them -- keyword lists are",
        "   rejected as noise.",
        "7. The advice after the colon is the lesson: it must stay complete and",
        "   actionable. Never hollow the body to fit the budget.",
        "8. Never repeat a REJECTED draft or a trivial variant of one.",
        "",
        f"LESSON: {rec.get('experiment_name')}",
        f"CATEGORY: {rec.get('category') or 'uncategorized'}   SUCCESS: {rec.get('success')}",
        f"AGGREGATES: surfaced={counters.get('surfaced', 0)} helped={counters.get('helped', 0)} "
        f"useful={counters.get('useful', 0)} engaged={counters.get('engaged', 0)}",
        f"MINED VOCABULARY: {', '.join(trigger_terms or []) or '(none -- no credited history)'}",
        "",
        f"INCUMBENT RECOMMENDATION:\n{rec.get('recommendation') or ''}",
        "",
        f"WHAT WAS TRIED: {rec.get('what_tried') or ''}",
        f"ACTUAL OUTCOME: {rec.get('actual_outcome') or ''}",
        f"ROOT CAUSE: {rec.get('root_cause') or '(not recorded)'}",
        f"ANTI-PATTERN TAG: {rec.get('anti_pattern') or '(none)'}",
        "",
        f"REJECTED DRAFTS (never repeat):\n{rej_block}",
        "",
        "OUTPUT exactly:",
        "PROPOSED-RECOMMENDATION-BEGIN",
        "<text>",
        "PROPOSED-RECOMMENDATION-END",
        "RATIONALE: <one sentence>",
    ]
    return "\n".join(parts)


def parse_reply(text: str) -> Dict[str, str]:
    """Extract {draft, rationale} from an optimizer reply; {} when the markers are absent
    (a malformed reply is DROPPED, never guessed at -- the gate can only judge what the
    markers delimit)."""
    m = _DRAFT_RE.search(str(text or ""))
    if not m:
        return {}
    draft = m.group(1).strip()
    if not draft:
        return {}
    r = _RATIONALE_RE.search(text)
    return {"draft": draft, "rationale": (r.group(1).strip()[:200] if r else "")}


# --------------------------------------------------------------------- the pass
def run_pass(propose_fn: Callable[[str], str], *, limit: int = MAX_TARGETS_PER_PASS,
             store=None, learning_store=None,
             events: Optional[List[Dict[str, Any]]] = None,
             injections: Optional[List[Dict[str, Any]]] = None,
             min_relevance: Optional[float] = None) -> List[Dict[str, Any]]:
    """One optimizer pass: select -> prompt -> propose_fn (the injected model call) ->
    parse -> Tier-0 gate -> stamp pending proposal (PASS / UNMEASURABLE only; FAIL is
    closed by the gate's rejected buffer). Returns a row per target for the operator."""
    from core.recall.forge import gate_edit
    from core.recall.at_action import _load_use, _store, _cached_items
    from core.learning.learning_store import get_learning_store
    ls = learning_store or get_learning_store()
    st = store or _store()

    rows: List[Dict[str, Any]] = []
    items_by_source = {it.get("source"): it for it in _cached_items(learning_store)}
    for tgt in select_targets(limit, store=st, learning_store=ls):
        name = tgt["experiment_name"]
        source = f"learn:experiment:{name}"
        row: Dict[str, Any] = {"experiment": name, "surfaced": tgt["surfaced"]}
        try:
            counters = _load_use(st, source)
            terms = (items_by_source.get(source) or {}).get("trigger_terms") or []
            prompt = build_prompt(tgt["record"], counters=counters, trigger_terms=terms)
            reply = propose_fn(prompt)
            parsed = parse_reply(reply)
            if not parsed:
                row["outcome"] = "malformed-reply (dropped)"
                rows.append(row)
                continue
            rep = gate_edit(name, parsed["draft"], learning_store=learning_store,
                            events=events, injections=injections, min_relevance=min_relevance)
            row["verdict"] = rep["verdict"]
            row["rationale"] = parsed.get("rationale", "")
            if rep["verdict"] in ("PASS", "UNMEASURABLE"):
                stamped = ls.stamp_forge_proposal(name, parsed["draft"], rep["verdict"],
                                                  by="deepseek-optimizer",
                                                  rationale=parsed.get("rationale", ""))
                row["outcome"] = ("queued for human review" if stamped
                                  else "STAMP FAILED (store write)")
            else:
                row["outcome"] = "rejected by gate (buffered)"
                row["reasons"] = rep.get("reasons", [])[:3]
        except Exception as e:
            row["outcome"] = f"error: {type(e).__name__}: {e}"
        rows.append(row)
    return rows


def pending_proposals(*, learning_store=None) -> List[Dict[str, Any]]:
    """All unexpired pending proposals, newest first (the --forge-proposals listing)."""
    out: List[Dict[str, Any]] = []
    try:
        from core.learning.learning_store import get_learning_store
        ls = learning_store or get_learning_store()
        for rec in ls.load_all_learnings_from_store():
            if not _proposal_pending(rec):
                continue
            prop = json.loads(str(rec.get("forge_proposal")))
            out.append({"experiment": rec.get("experiment_name"),
                        "verdict": prop.get("verdict"), "at": prop.get("at"),
                        "by": prop.get("by"), "rationale": prop.get("rationale", ""),
                        "draft": prop.get("draft", "")})
        out.sort(key=lambda p: str(p.get("at") or ""), reverse=True)
    except Exception:
        pass
    return out
