"""Forge F1 -- the Tier-0 edit gate (docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.md sec.4, sec.9 F1).

Adjudicates ONE bounded edit to ONE lesson's recommendation text, offline, deterministic,
no LLM. The validation set is the lesson's own durable history (Forge premise, dual-derived
and audited in docs/library/report/20260709_forge-f0-data-sufficiency-audit-dual-pre_9749e0.md):

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
    """Re-derive the query from the target with TODAY'S query builder -- a deliberate
    choice (DeepSeek review 2026-07-09, argued to ground): the gate asks 'would the
    CURRENT matcher surface this text for that context', not 'what did the historical
    matcher see'. The F0b-captured query on enriched flip events exists for forensic
    comparison, not for gating."""
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

        # BODY floor (red-team exploit 2, "body hollowing"): the advice after the trigger
        # colon must survive -- a gutted body with an intact trigger passes every other
        # floor while destroying the lesson's value. Coarse and mechanical on purpose.
        def _body_of(text: str) -> str:
            _, _, rest = str(text or "").partition(":")
            return rest or str(text or "")
        inc_body_n = len(_tokens(_body_of(incumbent.get("text"))))
        var_body_n = len(_tokens(_body_of(new_recommendation)))
        body_ok = var_body_n >= max(4, int(0.5 * inc_body_n))
        had_contra = "don't when" in str(incumbent.get("text") or "").lower()
        contra_ok = (not had_contra) or ("don't when" in str(new_recommendation).lower())
        report["checks"]["body"] = {"incumbent_body_tokens": inc_body_n,
                                    "variant_body_tokens": var_body_n,
                                    "contraindication_kept": contra_ok, "ok": body_ok and contra_ok}
        if not body_ok:
            report["reasons"].append("body floor: the advice after the trigger was hollowed "
                                     f"({var_body_n} tokens vs incumbent {inc_body_n}) -- a lesson "
                                     "is its advice, not its trigger")
        if not contra_ok:
            report["reasons"].append("body floor: the incumbent's \"Don't when\" contraindication "
                                     "was dropped -- disconfirmers are load-bearing")

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
        inc_hit_targets: List[str] = []
        for tgt in noise:
            q = _context_query(tgt)
            if not q:
                continue
            if _would_surface(rel_inc(inc_text, q), floor):
                inc_hits += 1
                inc_hit_targets.append(tgt)
            if _would_surface(rel_var(var_text, q), floor):
                var_hits += 1

        # GROUNDING floor (red-team exploit 1, "over-narrow to dead-letter"): for a
        # vacuous-axis-1 lesson, axis 2 rewards ANY narrowing -- including gibberish that
        # matches nothing, ever. The variant's trigger must share a discriminative token
        # with the lesson's REAL CURRENT HOME: credited targets (always) plus the noise
        # targets the incumbent actually clears the floor on TODAY. Pre-regime misfire
        # contexts deliberately don't count (grounding to noise would force re-anchoring
        # toward it); when the home set is empty the floor is vacuous -- that class is
        # UNMEASURABLE's territory. Coarser than the axes on purpose: "related to
        # anything real at all", not "still matches what earned credit".
        home_tokens: set = set()
        try:
            from core.recall.at_action import _STOP
            for t in list(cred) + inc_hit_targets:
                home_tokens.update(w for w in _tokens(t) if len(w) > 3 and w not in _STOP)
        except Exception:
            home_tokens = set()
        trig_tokens = {w for w in _tokens(trigger) if len(w) > 3}
        grounding_vacuous = not home_tokens
        grounding_ok = grounding_vacuous or bool(trig_tokens & home_tokens)
        report["checks"]["grounding"] = {"shared": sorted(trig_tokens & home_tokens)[:6],
                                         "vacuous": grounding_vacuous, "ok": grounding_ok}
        if not grounding_ok:
            report["reasons"].append("grounding floor: the new trigger shares NO discriminative "
                                     "token with any context this lesson actually lives in "
                                     "(credited targets + currently-matching surfacings) -- a "
                                     "trigger that matches nothing real is a dead letter, not "
                                     "precision")
        axis2_improved = var_hits < inc_hits
        axis2_regressed = var_hits > inc_hits
        report["axis2"] = {"noise_contexts": len(noise), "incumbent_hits": inc_hits,
                           "variant_hits": var_hits, "improved": axis2_improved,
                           "regressed": axis2_regressed}
        if axis2_regressed:
            report["reasons"].append("axis 2: the edit fires on MORE never-credited contexts "
                                     "than the incumbent (precision regression)")

        # ---- verdict -------------------------------------------------------------
        floors_ok = (budget_ok and trigger_ok and faith_ok and grounding_ok
                     and body_ok and contra_ok)
        # strict improvement must come from SOMEWHERE measurable, and axis 2 is the only
        # improvable axis at Tier 0 (axis 1 is a keep-everything constraint; for the rehab
        # class it is vacuous). Credited class: keep ALL of axis 1 AND improve axis 2.
        improvement = axis2_improved
        # UNMEASURABLE (found by DeepSeek's red-team drill 2026-07-09): a never-credited
        # lesson whose historical surfacings all pre-date the current matcher regime has
        # inc_hits == 0 -- there is nothing to improve AND nothing broken. That is not
        # churn; it is the gate having no evidence to judge with. Abstain distinctly (the
        # human decides unaided, or the F0b stream accrues fresh contexts first) and do
        # NOT stamp the rejected buffer -- the draft was never refuted.
        unmeasurable = (floors_ok and axis1_vacuous and inc_hits == 0 and var_hits == 0)
        if unmeasurable:
            report["verdict"] = "UNMEASURABLE"
            report["reasons"].append(
                "no current-regime evidence to adjudicate with: never credited, and the "
                "incumbent clears the floor on none of its recorded contexts today (they "
                "pre-date the calibrated matcher). Options: wait for the durable surface "
                "stream to accrue fresh contexts, or apply on human judgment alone.")
        elif floors_ok and axis1_ok and not axis2_regressed and improvement:
            report["verdict"] = "PASS"
        elif floors_ok and axis1_ok and not axis2_regressed and not improvement:
            report["reasons"].append("no measurable improvement on either axis -- an equal-value "
                                     "rewrite is churn, not progress (gate stays shut)")
    except Exception as e:
        report["reasons"].append(f"gate error ({type(e).__name__}: {e}) -- fail closed")

    if report["verdict"] == "FAIL":
        try:    # durable negative feedback: never re-propose a REFUTED edit. UNMEASURABLE
            # is not a refutation -- stamping it would poison a possibly-good draft.
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
    baseline: Dict[str, Any] = {}
    try:    # counters snapshot for the F4 watch -- best-effort (an empty baseline just
        # means the watch falls back to its noise/age triggers)
        from core.recall.at_action import _load_use, _store
        baseline = dict(_load_use(_store(), f"learn:experiment:{experiment_name}") or {})
    except Exception:
        baseline = {}
    ok = ls.apply_forge_edit(experiment_name, new_recommendation, {
        "axis1": gate_report.get("axis1", {}).get("kept"),
        "axis1_vacuous": gate_report.get("axis1", {}).get("vacuous"),
        "axis2": [gate_report.get("axis2", {}).get("incumbent_hits"),
                  gate_report.get("axis2", {}).get("variant_hits")],
        "floor": gate_report.get("floor"),
    }, baseline=baseline)
    if ok:
        try:    # a text change alters what may surface -- expire the warm cache (curator
            # idiom), then re-warm so the next hook call reads ~1ms file, not the store
            # (DeepSeek review F2 polish)
            from core.recall.curator import _invalidate_surface_cache
            from core.recall.at_action import warm_cache
            _invalidate_surface_cache()
            warm_cache()
        except Exception:
            pass
    return ok
