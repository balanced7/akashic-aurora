"""Harness for the semantic-gate yardsticks (measurement-first; the gate itself is a later slice).

Run: py tests/test_semantic_eval.py   (prints baselines + a best-effort LLM-judge probe)
 or: py -m pytest tests/test_semantic_eval.py

Companion: docs/recall-critic-decision.md. Scores a binary JUDGE against the labeled datasets in
fixtures/semantic_eval_fixture. Ships a null baseline (characterizes class balance -- the number a
real judge must beat) and, in __main__ only, a best-effort probe of an LLM judge (the future gate),
so we get an early read on viability WITHOUT making the gate a dependency or the network a test req.
The pytest tests are hermetic (no network): they check the datasets are well-formed and the metric
behaves. The gate is graded here once it exists; today we just lay the honest starting line.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.semantic_eval_fixture import contradiction_pairs, action_applicability_cases

Judge = Callable[[Dict[str, Any]], bool]
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def score_binary(cases: List[Dict[str, Any]], judge: Judge, gold_key: str) -> Dict[str, Any]:
    """Precision/recall/accuracy/F1 for a bool judge over labeled cases (gold in `gold_key`)."""
    tp = fp = tn = fn = 0
    for c in cases:
        pred, gold = bool(judge(c)), bool(c[gold_key])
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif (not pred) and gold:
            fn += 1
        else:
            tn += 1
    n = (tp + fp + tn + fn) or 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "accuracy": (tp + tn) / n, "f1": f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": n, "pos": tp + fn, "neg": tn + fp}


def null_judge(case: Dict[str, Any]) -> bool:
    """The floor: predict 'no contradiction / does not apply' for everything. A real judge must beat it."""
    return False


# ----------------------------------------------------------------------------- tests (hermetic)
def test_datasets_wellformed():
    cp, aa = contradiction_pairs(), action_applicability_cases()
    assert len(cp) >= 20, f"expected a real contradiction set, got {len(cp)}"
    assert any(p["contradicts"] for p in cp), "need positive (genuine-contradiction) pairs"
    assert any(not p["contradicts"] for p in cp), "need negative (agreement/adjacent) pairs"
    for p in cp:
        assert p["a"] and p["b"], "every pair needs text on both sides"
    # the hard negatives must be present: an on-topic anti-pattern the thesis AGREES with
    assert any(p["case"].startswith("syn-antipattern-agrees") and not p["contradicts"] for p in cp), \
        "the agrees-distractor hard negatives must be in the eval (they sank the deterministic finder)"
    assert len(aa) >= 6 and any(c["instantiates"] for c in aa) and any(not c["instantiates"] for c in aa)
    for c in aa:
        assert c["action"] and c["ap_text"]
    print(f"--- datasets ---\n  {len(cp)} contradiction pairs ({sum(p['contradicts'] for p in cp)} pos), "
          f"{len(aa)} action-applicability cases ({sum(c['instantiates'] for c in aa)} pos) OK")


def test_null_baseline_characterizes_balance():
    m = score_binary(contradiction_pairs(), null_judge, "contradicts")
    a = score_binary(action_applicability_cases(), null_judge, "instantiates")
    assert m["recall"] == 0.0 and m["fp"] == 0, "always-false -> 0 recall, 0 false positives"
    assert a["recall"] == 0.0 and a["fp"] == 0
    # accuracy-by-always-false = the negative rate; a judge that can't beat it is worthless
    print(f"--- null baseline ---\n  contradiction: {m['pos']}/{m['n']} pairs are true contradictions "
          f"(always-false acc={m['accuracy']:.2f}); action: {a['pos']}/{a['n']} true "
          f"(acc={a['accuracy']:.2f}). The semantic gate is graded against these here once it exists")


def test_metric_can_fail_and_reward():
    """A metric must be able to move (narrative_metric_pinned_at_100): a perfect oracle scores 1.0,
    an always-true judge tanks precision. If neither held, the harness would be measuring nothing."""
    cp = contradiction_pairs()
    oracle = score_binary(cp, lambda c: c["contradicts"], "contradicts")
    always = score_binary(cp, lambda c: True, "contradicts")
    assert oracle["f1"] == 1.0, "a perfect judge must score F1 1.0"
    assert always["precision"] < 1.0 and always["recall"] == 1.0, "always-true must tank precision"
    print(f"--- metric sanity ---\n  oracle F1={oracle['f1']:.2f}; always-true precision="
          f"{always['precision']:.2f} -> the metric rewards right and punishes noise OK")


# ----------------------------------------------------------------------------- best-effort LLM probe
def _llm_contradiction(case: Dict[str, Any]):
    """Probe the FUTURE gate early: ask a cheap LLM if B contradicts A. Returns bool, or None on any
    failure (network/quota). Never used by pytest -- only the __main__ dogfood."""
    import subprocess
    prompt = (f"Lesson A: {case['a']}\nLesson B: {case['b']}\n\n"
              "Does B GENUINELY CONTRADICT A -- advocate an opposing action or conclusion on the SAME "
              "decision? Sharing a topic while AGREEING is NOT a contradiction. Answer exactly YES or NO.")
    try:
        out = subprocess.run([sys.executable, "scripts/ask_gemini.py"], cwd=_ROOT, input=prompt,
                             capture_output=True, text=True, timeout=60,
                             env={**os.environ, "PYTHONUTF8": "1"})
        ans = (out.stdout or "").strip().upper()
        if ans.startswith("YES"):
            return True
        if ans.startswith("NO"):
            return False
    except Exception:
        pass
    return None


if __name__ == "__main__":
    print("=" * 64)
    print("SEMANTIC-GATE YARDSTICKS (measurement-first; gate is a later slice)")
    print("=" * 64)
    for name, cases, key in (("contradiction", contradiction_pairs(), "contradicts"),
                             ("action-applies", action_applicability_cases(), "instantiates")):
        m = score_binary(cases, null_judge, key)
        print(f"[{name}] null baseline: acc={m['accuracy']:.2f} recall={m['recall']:.2f} "
              f"({m['pos']} true / {m['n']} total) -- a real judge must beat this")
    print("\nLLM-judge probe (best-effort; the FUTURE gate, sampled to bound cost):")
    sample = contradiction_pairs()[:8]
    hits = tot = 0
    for p in sample:
        v = _llm_contradiction(p)
        if v is None:
            print("  (probe unavailable -- network/quota; skipping)")
            break
        ok = (v == p["contradicts"])
        hits += ok
        tot += 1
        print(f"  {'OK ' if ok else 'XX '} pred={str(v):5} gold={str(p['contradicts']):5} A~{p['a'][:44]}")
    if tot:
        print(f"  -> LLM judge sample accuracy: {hits}/{tot} (early signal on whether an LLM gate clears the bar)")
    print("\nOK -- `py -m pytest tests/test_semantic_eval.py -q` for the hermetic asserts.")
