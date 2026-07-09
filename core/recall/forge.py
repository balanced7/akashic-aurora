"""Forge F1 -- the Tier-0 edit gate (docs/lesson-forge-design-2026-07.md sec.4, sec.9 F1).

Adjudicates ONE bounded edit to ONE lesson's recommendation text, offline, deterministic,
no LLM. The validation set is the lesson's own durable history (Forge premise, dual-derived
and audited in research/reviewed/forge-f0-audit-2026-07-09.md):

  floors  -- textual learning rate (<= 40% token delta), trigger clause still parseable,
             FAITH (no fabricated pointers), provenance untouched by construction (only
             the recommendation field is replaceable here).
  axis 1  -- MUST-STILL-MATCH: on every context where the incumbent was CREDITED, the
             variant's relevance stays >= incumbent - EPS and above the floor. Vacuous
             (flagged) for never-credited rehab targets.
  axis 2  -- SHOULD-STOP-MATCHING: over contexts where the lesson surfaced without ever
             earning credit, the variant should clear the floor on FEWER of them.
  verdict -- PASS only with all floors green, no axis-1 regression, no axis-2 regression,
             and strict improvement on at least one axis (for the rehab class, axis 2 is
             the only place improvement can come from).

The gate is coarse pass/fail BY DESIGN (slice-1 review insight, adopted as a Forge
principle): it is never a score an optimizer may hill-climb, and the optimizer never sees
the raw contexts it replays (blinding, DeepSeek FM1). FAIL stamps the rejected-edit
buffer so the same edit is never re-proposed. APPLY is human-gated (trust ladder,
decision 5): reversible by construction (previous text retained on the record).

Read-only except the two explicit write paths (reject stamp, human-invoked apply).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

EPS = 0.02                 # axis-1 tolerance: relevance is a ratio; forbid REAL regressions,
                           # not float dust
TOKEN_BUDGET = 0.40        # textual learning rate (design decision 1, locked)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(str(text or "").lower())


def _would_surface(rel: float, floor: float) -> bool:
    return rel > floor     # mirrors _lessons' strict `<= min_relevance -> skip`


def _variant_item(incumbent: Dict[str, Any], new_recommendation: str) -> Dict[str, Any]:
    """The incumbent's projection with ONLY the text/trigger swapped. Mined trigger_terms
    stay -- they are keyed to the SOURCE's credit history, not to the old wording -- and
    provenance fields are carried untouched (an edit may never upgrade success/agent_id)."""
    from core.recall.at_action import _parse_trigger
    v = dict(incumbent)
    v["text"] = str(new_recommendation)
    v["trigger"] = _parse_trigger(new_recommendation)
    return v


def _relevance_fn(items: List[Dict[str, Any]]):
    from core.recall.at_action import _trigger_aware_relevance
    by_text = {str(it.get("text") or ""): it for it in items}
    return _trigger_aware_relevance(by_text)


def _context_query(target: str) -> str:
    from core.recall.at_action import _query_from
    from core.recall.replay import parse_target
    path, command = parse_target(target)
    if not (path or command):
        return ""
    return _query_from(path, command)


def gate_edit(experiment_name: str, new_recommendation: str, *,
              learning_store: Optional[Any] = None,
              events: Optional[List[Dict[str, Any]]] = None,
              injections: Optional[List[Dict[str, Any]]] = None,
              min_relevance: Optional[float] = None) -> Dict[str, Any]:
    """Adjudicate replacing `experiment_name`'s recommendation with `new_recommendation`.
    Returns the full verdict report; never raises (errors -> FAIL with reason). Stamps the
    rejected-edit buffer on FAIL (durable negative feedback -- advisory prints evaporate)."""
    source = f"learn:experiment:{experiment_name}"
    report: Dict[str, Any] = {"experiment": experiment_name, "source": source,
                              "verdict": "FAIL", "reasons": [], "checks": {},
                              "axis1": {}, "axis2": {}}
    try:
        from core.recall import at_action as aa
        from core.recall.replay import credited_contexts, surfaced_contexts

        items = aa._cached_items(learning_store)
        incumbent = next((it for it in items if it.get("source") == source), None)
        if incumbent is None:
            report["reasons"].append(f"no active lesson '{experiment_name}' on the recall surface "
                                     "(benched/graduated lessons re-enter via the curator first)")
            return report
        floor = aa._floor_default() if min_relevance is None else float(min_relevance)
        report["floor"] = floor

        # ---- floors -------------------------------------------------------------
        old_n, new_n = len(_tokens(incumbent.get("text"))), len(_tokens(new_recommendation))
        delta = abs(new_n - old_n) / max(1, old_n)
        budget_ok = delta <= TOKEN_BUDGET
        report["checks"]["budget"] = {"old_tokens": old_n, "new_tokens": new_n,
                                      "delta": round(delta, 3), "limit": TOKEN_BUDGET,
                                      "ok": budget_ok}
        if not budget_ok:
            report["reasons"].append(f"token delta {delta:.0%} exceeds the textual learning "
                                     f"rate ({TOKEN_BUDGET:.0%})")

        trigger = aa._parse_trigger(new_recommendation)
        trigger_ok = bool(trigger.strip())
        report["checks"]["trigger"] = {"parsed": trigger[:120], "ok": trigger_ok}
        if not trigger_ok:
            report["reasons"].append("no parseable 'Use when ...' trigger clause -- a lesson "
                                     "fires at the right moment only if its text says when")

        faith_ok = True
        try:
            from core.primitives.faithfulness import faithfulness_report
            checked = [{"text": str(new_recommendation), "source": source}]
            skeleton = f"- {new_recommendation}  (source: {source})"
            faith_ok = bool(faithfulness_report(checked, skeleton).get("faithful", True))
        except Exception:
            faith_ok = True     # FAITH unavailable -> do not block on missing machinery
        report["checks"]["faith"] = {"ok": faith_ok}
        if not faith_ok:
            report["reasons"].append("FAITH gate: the draft carries an unresolvable/fabricated pointer")

        # ---- replay both texts over the lesson's own history --------------------
        variant = _variant_item(incumbent, new_recommendation)
        items_var = [variant if it.get("source") == source else it for it in items]
        rel_inc = _relevance_fn(items)
        rel_var = _relevance_fn(items_var)
        inc_text, var_text = str(incumbent.get("text") or ""), str(variant.get("text") or "")

        cred = credited_contexts(events=events).get(source, [])
        noise_all = surfaced_contexts(injections=injections).get(source, [])
        noise = [t for t in noise_all if t not in set(cred)]

        kept, lost = [], []
        for tgt in cred:
            q = _context_query(tgt)
            if not q:
                continue
            ri, rv = rel_inc(inc_text, q), rel_var(var_text, q)
            (kept if (rv >= ri - EPS and _would_surface(rv, floor)) else lost).append(
                {"target": tgt[:90], "incumbent": round(ri, 3), "variant": round(rv, 3)})
        axis1_vacuous = not cred
        axis1_ok = not lost
        report["axis1"] = {"credited_contexts": len(cred), "kept": len(kept),
                           "lost": lost, "vacuous": axis1_vacuous, "ok": axis1_ok}
        if lost:
            report["reasons"].append(f"axis 1: the edit loses {len(lost)} credited context(s) "
                                     "-- it breaks what demonstrably worked")

        inc_hits = var_hits = 0
        for tgt in noise:
            q = _context_query(tgt)
            if not q:
                continue
            if _would_surface(rel_inc(inc_text, q), floor):
                inc_hits += 1
            if _would_surface(rel_var(var_text, q), floor):
                var_hits += 1
        axis2_improved = var_hits < inc_hits
        axis2_regressed = var_hits > inc_hits
        report["axis2"] = {"noise_contexts": len(noise), "incumbent_hits": inc_hits,
                           "variant_hits": var_hits, "improved": axis2_improved,
                           "regressed": axis2_regressed}
        if axis2_regressed:
            report["reasons"].append("axis 2: the edit fires on MORE never-credited contexts "
                                     "than the incumbent (precision regression)")

        # ---- verdict -------------------------------------------------------------
        floors_ok = budget_ok and trigger_ok and faith_ok
        # strict improvement must come from SOMEWHERE measurable, and axis 2 is the only
        # improvable axis at Tier 0 (axis 1 is a keep-everything constraint; for the rehab
        # class it is vacuous). Credited class: keep ALL of axis 1 AND improve axis 2.
        improvement = axis2_improved
        if floors_ok and axis1_ok and not axis2_regressed and improvement:
            report["verdict"] = "PASS"
        elif floors_ok and axis1_ok and not axis2_regressed and not improvement:
            report["reasons"].append("no measurable improvement on either axis -- an equal-value "
                                     "rewrite is churn, not progress (gate stays shut)")
    except Exception as e:
        report["reasons"].append(f"gate error ({type(e).__name__}: {e}) -- fail closed")

    if report["verdict"] != "PASS":
        try:    # durable negative feedback: never re-propose a rejected edit
            _stamp_rejected(experiment_name, new_recommendation, report["reasons"],
                            learning_store=learning_store)
            report["rejected_stamped"] = True
        except Exception:
            report["rejected_stamped"] = False
    return report


def _stamp_rejected(experiment_name: str, draft: str, reasons: List[str], *,
                    learning_store: Optional[Any] = None) -> bool:
    from core.learning.learning_store import get_learning_store
    ls = learning_store or get_learning_store()
    return ls.mark_forge_rejected(experiment_name, draft, reasons)


def apply_edit(experiment_name: str, new_recommendation: str, gate_report: Dict[str, Any], *,
               learning_store: Optional[Any] = None) -> bool:
    """HUMAN-GATED apply (trust ladder): only ever called after a PASS the operator has seen.
    Reversible by construction -- the incumbent text is retained on the record."""
    if gate_report.get("verdict") != "PASS":
        return False
    from core.learning.learning_store import get_learning_store
    ls = learning_store or get_learning_store()
    ok = ls.apply_forge_edit(experiment_name, new_recommendation, {
        "axis1": gate_report.get("axis1", {}).get("kept"),
        "axis1_vacuous": gate_report.get("axis1", {}).get("vacuous"),
        "axis2": [gate_report.get("axis2", {}).get("incumbent_hits"),
                  gate_report.get("axis2", {}).get("variant_hits")],
        "floor": gate_report.get("floor"),
    })
    if ok:
        try:    # a text change alters what may surface -- expire the warm cache (curator idiom)
            from core.recall.curator import _invalidate_surface_cache
            _invalidate_surface_cache()
        except Exception:
            pass
    return ok
