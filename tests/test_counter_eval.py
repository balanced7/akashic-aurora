"""Counter-retrieval eval harness (recall confirmation-bias, Slice 0) — the yardstick.

Run:  py tests/test_counter_eval.py     (prints the metrics table + coverage report)
 or:  py -m pytest tests/test_counter_eval.py

Companion doc: docs/recall-critic-decision.md. This is Slice 0 of that plan: build the
MEASUREMENT before the fix, so we can tell whether surfacing dissent actually helps without
Goodharting engagement.

WHAT IT MEASURES (against the gold fixture in fixtures/counter_fixture.py)
    counter_recall     : of cases where a real counter EXISTS, how often a detector surfaces one
    silence_accuracy   : of cases where NO real counter exists, how often it correctly stays silent
    counter_precision  : of everything a detector surfaces, how much is a genuine counter
                         (1.0 = never manufactures "false balance"; the design's hard constraint)
    F1                 : harmonic mean of recall & precision
    per-kind recall    : broken out by opposite_success / anti_pattern / conflicting_recommendation
                         — this is where the interesting gap lives (see below)

THE DETECTOR SEAM (what Slice 1 will fill)
    A detector is any `f(thesis, corpus) -> (surfaced: bool, sources: list[str])`. Slice 0 ships
    two references so the harness has a floor and a sanity check:
      - null_detector      : never surfaces. This is TODAY'S recall behavior — it is trivially
                             100% "silent" and catches 0% of real counters. That 0% is the
                             baseline the whole program has to beat.
      - naive_reference    : a deliberately simple deterministic finder (shared keywords +
                             opposite success OR a populated anti_pattern). It is NOT the Slice 1
                             design — it exists to prove the harness can measure improvement, and
                             to expose the hard part: it structurally CANNOT catch a
                             conflicting_recommendation between two self-reported successes, and it
                             misses real counters that use different vocabulary than the thesis.
                             Closing that gap is Slice 1's job.

CORPUS COVERAGE (confirmation-by-omission, made a number)
    counter_density() reports what fraction of self-reported successes even HAVE a lexically
    discoverable counter in a corpus. Over a real-skew sample it is ~0 — a dissent-surfacer can
    only be as good as the dissent that exists. This is the metric Slice 2 (write-side nudge)
    must move; here we just establish the honest starting line.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Callable, Dict, List, Tuple

# Repo root on path so the live-store dogfood (core.*) resolves when run directly as a script;
# under pytest, conftest.py already does this. tests/ is on path either way, so `fixtures.*` works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.counter_fixture import gold_cases, sample_corpus, L

Detector = Callable[[Dict[str, Any], List[Dict[str, Any]]], Tuple[bool, List[str]]]

# --- stable, implementation-independent tokenizer. Mirrors the production keyword_relevance
# (lowercase alnum, length>3, no stemming) ON PURPOSE: the eval must reproduce recall's real
# lexical limits, not paper over them. Kept local so the yardstick doesn't move when recall does.
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {"the", "and", "for", "with", "this", "that", "use", "using", "via", "from", "into",
         "every", "each", "should", "must", "than", "them", "they", "not", "but", "keep",
         "gave", "only", "onto", "over", "under", "same", "make", "made", "here", "there",
         # generic English/dev words that create spurious token collisions on a real corpus
         # (verified: 'also'/'still'/'gate' matched wholly unrelated lessons). NB: no stoplist can
         # fix DOMAIN-token collisions ('store'/'test'/'path' shared by unrelated lessons) -- that
         # residual is the point: lexical overlap != genuine opposition (see module docstring).
         "also", "still", "like", "added", "adds", "whole", "real", "account", "need", "needs",
         "next", "done", "work", "works", "just", "then", "when", "what", "will", "been", "have",
         "does", "both", "else", "such", "more", "most", "very", "able", "gate", "gated", "agent",
         "agents", "sets", "gets", "runs", "ways", "new", "old", "now", "per", "add"}


def salient_tokens(text: str) -> set:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 3 and t not in _STOP}


def _text(rec: Dict[str, Any]) -> str:
    return " ".join(str(rec.get(f, "")) for f in ("recommendation", "actual", "what_tried"))


def _is_success(rec: Dict[str, Any]) -> bool:
    return str(rec.get("success", "")).lower() in ("yes", "true")


def _is_failure(rec: Dict[str, Any]) -> bool:
    return str(rec.get("success", "")).lower() in ("no", "false", "partial")


# ----------------------------------------------------------------------------- detectors
def null_detector(thesis: Dict[str, Any], corpus: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Today's recall: surfaces the top supporter, never a counter."""
    return False, []


def naive_reference_detector(thesis: Dict[str, Any],
                             corpus: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """A simple, honest floor (NOT the Slice 1 design). Flags a corpus record as a counter when it
    shares >=2 salient tokens with the thesis AND either (a) reports the opposite outcome or
    (b) carries a populated anti_pattern. Cannot see conflicting recommendations between two
    successes, and misses counters phrased in different words — by construction."""
    tname = thesis.get("experiment_name")
    ttok = salient_tokens(_text(thesis))
    t_success = _is_success(thesis)
    found: List[str] = []
    for rec in corpus:
        if rec.get("experiment_name") == tname:
            continue  # never count the thesis as its own counter
        shared = ttok & salient_tokens(_text(rec))
        if len(shared) < 2:
            continue
        opposite_outcome = (t_success and _is_failure(rec)) or (_is_failure(thesis) and _is_success(rec))
        if rec.get("anti_pattern") or opposite_outcome:
            found.append(rec.get("experiment_name"))
    return bool(found), found


def dissent_detector(thesis: Dict[str, Any], corpus: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """The REAL Slice 1 finder (core/recall/dissent.find_counter), adapted to the fixture record
    shape (experiment_name -> source). Requires an explicit stance signal (anti_pattern / link) plus
    a TF-IDF topic gate; opposite outcome alone never fires."""
    from core.recall.dissent import find_counter

    def adapt(r: Dict[str, Any]) -> Dict[str, Any]:
        return {**r, "source": r.get("source") or r.get("experiment_name"),
                "text": r.get("text") or r.get("recommendation") or r.get("actual")
                or r.get("what_tried") or ""}
    c = find_counter(adapt(thesis), [adapt(r) for r in corpus])
    return (c is not None, [c["source"]] if c else [])


# ----------------------------------------------------------------------------- metrics
def evaluate(cases: List[Dict[str, Any]], detector: Detector) -> Dict[str, Any]:
    """Score a detector against the gold cases. Recall is over cases (did it find a real counter
    when one existed); precision is over surface events (of what it surfaced, how much was real)."""
    tp = fn = tn = fp = 0                     # fp = false-balance (surfaced when it shouldn't have)
    surface_events = surface_hits = 0
    per_kind: Dict[str, List[int]] = {}       # kind -> [hits, total]
    rows: List[Dict[str, Any]] = []
    for c in cases:
        surfaced, srcs = detector(c["thesis"], c["corpus"])
        gold = set(c["counter_sources"])
        hit = bool(surfaced and (set(srcs) & gold))
        if surfaced:
            surface_events += 1
            if hit:
                surface_hits += 1
        if c["counter_exists"]:
            k = c["kind"] or "unknown"
            per_kind.setdefault(k, [0, 0])
            per_kind[k][1] += 1
            if hit:
                tp += 1
                per_kind[k][0] += 1
            else:
                fn += 1                       # missed the real counter (silent, or surfaced junk)
        else:
            if surfaced:
                fp += 1                       # manufactured a counter where none exists
            else:
                tn += 1
        rows.append({"id": c["id"], "expected": c["counter_exists"], "surfaced": surfaced,
                     "hit": hit, "srcs": srcs})
    n_has = tp + fn
    n_no = tn + fp
    recall = tp / n_has if n_has else 0.0
    silence = tn / n_no if n_no else 0.0
    precision = surface_hits / surface_events if surface_events else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"counter_recall": recall, "silence_accuracy": silence, "counter_precision": precision,
            "f1": f1, "tp": tp, "fn": fn, "tn": tn, "fp": fp, "n_has": n_has, "n_no": n_no,
            "n_surfaced": surface_events, "per_kind": {k: (h / t if t else 0.0)
                                                       for k, (h, t) in per_kind.items()},
            "rows": rows}


def counter_density(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Confirmation-by-omission, as a number: of the self-reported successes in `records`, what
    fraction have >=1 lexically discoverable counter (shared tokens + opposite outcome or an
    anti_pattern)? A LOWER bound — it can't see same-vocabulary-free or same-success conflicts, so
    true discoverable dissent is <= this. ~0 on a real-skew corpus is the point."""
    successes = [r for r in records if _is_success(r)]
    with_counter = 0
    for r in successes:
        surfaced, _ = naive_reference_detector(r, records)
        if surfaced:
            with_counter += 1
    n = len(successes)
    return {"density": (with_counter / n if n else 0.0), "n_success": n,
            "n_with_counter": with_counter, "n_total": len(records)}


# ----------------------------------------------------------------------------- pretty report
def _bar(label: str, value: float, ok: bool) -> str:
    return f"  {'OK ' if ok else '.. '} {label:<22} {value:6.3f}"


def format_report() -> str:
    cases = gold_cases()
    n_has = sum(1 for c in cases if c["counter_exists"])
    lines = ["=" * 64,
             f"COUNTER-RETRIEVAL EVAL (Slice 0) — {len(cases)} cases "
             f"({n_has} with a real counter, {len(cases) - n_has} silence controls)",
             "=" * 64]
    for name, det in (("null (= today's recall)", null_detector),
                      ("naive reference floor", naive_reference_detector),
                      ("dissent (Slice 1)", dissent_detector)):
        m = evaluate(cases, det)
        lines.append(f"\n[{name}]")
        lines.append(_bar("counter_recall", m["counter_recall"], m["counter_recall"] > 0))
        lines.append(_bar("silence_accuracy", m["silence_accuracy"], m["silence_accuracy"] >= 0.9))
        lines.append(_bar("counter_precision", m["counter_precision"], m["counter_precision"] >= 0.9))
        lines.append(_bar("F1", m["f1"], m["f1"] > 0))
        lines.append(f"       (tp={m['tp']} fn={m['fn']} tn={m['tn']} fp={m['fp']} "
                     f"surfaced={m['n_surfaced']})")
        if m["per_kind"]:
            lines.append("       recall by kind: " +
                         ", ".join(f"{k}={v:.2f}" for k, v in sorted(m["per_kind"].items())))
    # coverage / confirmation-by-omission (curated sample = trustworthy; live caveat in __main__)
    cov = counter_density(sample_corpus())
    lines += ["\n" + "-" * 64,
              "CORPUS COVERAGE — confirmation-by-omission (curated real-skew sample)",
              f"  naive-flagged counter rate = {cov['density']:.3f}  "
              f"({cov['n_with_counter']}/{cov['n_success']} successes; {cov['n_total']} records)",
              "  Genuine counters are scarce by construction: the store is ~95% self-reported",
              "  successes with 0 anti-patterns, so a dissent-surfacer can only be as good as the",
              "  dissent that exists -> Slice 2 (write-side nudge) must grow this. NB this rate is",
              "  DETECTOR-RELATIVE and precision-poor at scale — see the live-store caveat below."]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- tests
def test_dataset_integrity():
    cases = gold_cases()
    assert len(cases) >= 20, f"seed set should be ~20+ cases, got {len(cases)}"
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "case ids must be unique"
    n_has = sum(1 for c in cases if c["counter_exists"])
    assert 0 < n_has < len(cases), "need both counter and no-counter cases for the metric to mean anything"
    for c in cases:
        names = {r["experiment_name"] for r in c["corpus"]}
        assert c["thesis"]["experiment_name"] in names, f"{c['id']}: thesis must be in its corpus"
        assert set(c["counter_sources"]) <= names, f"{c['id']}: gold counters must exist in corpus"
        assert c["thesis"]["experiment_name"] not in c["counter_sources"], \
            f"{c['id']}: the thesis cannot be its own counter"
        if c["counter_exists"]:
            assert c["counter_sources"] and c["kind"], f"{c['id']}: has-counter case needs sources+kind"
        else:
            assert not c["counter_sources"], f"{c['id']}: no-counter case must have empty counter_sources"
    print(f"--- dataset integrity ---\n  {len(cases)} cases, {n_has} with counters, ids unique, "
          f"all gold sources resolve OK")


def test_null_baseline_characterizes_todays_blindness():
    """Today's recall never surfaces a counter: trivially 'silent', catches 0% of real ones."""
    m = evaluate(gold_cases(), null_detector)
    assert m["n_surfaced"] == 0, "null detector must never surface"
    assert m["counter_recall"] == 0.0, "today's recall catches 0% of existing counters"
    assert m["silence_accuracy"] == 1.0, "...while being trivially 100% 'silent' (the cheap illusion)"
    print("--- null baseline ---\n  recall=0.000 silence=1.000 -> today's recall is blind to "
          "every existing counter (the starting line)")


def test_naive_reference_moves_the_needle_but_leaves_the_hard_gap():
    m = evaluate(gold_cases(), naive_reference_detector)
    # it beats the null floor on recall (the harness can MEASURE an improvement)...
    assert m["counter_recall"] > 0.0, "naive reference must catch some real counters"
    # ...without manufacturing false balance (precision perfect; silence intact) — the hard rule
    assert m["counter_precision"] == 1.0, f"naive must never surface a non-counter, got {m['counter_precision']}"
    assert m["silence_accuracy"] == 1.0, f"naive must stay silent on all no-counter cases, got {m['silence_accuracy']}"
    # ...and it CANNOT close the hard case: conflicting recommendations between two successes.
    assert m["counter_recall"] < 1.0, "naive should NOT be perfect — that's the gap Slice 1 exists to close"
    assert m["per_kind"].get("conflicting_recommendation", 0.0) == 0.0, \
        "keyword+outcome heuristic structurally can't catch same-success conflicts (needs stance)"
    print("--- naive reference ---\n  "
          f"recall={m['counter_recall']:.3f} precision={m['counter_precision']:.3f} "
          f"silence={m['silence_accuracy']:.3f}; conflicting_recommendation recall="
          f"{m['per_kind'].get('conflicting_recommendation', 0.0):.2f} (the Slice 1 target)")


def test_counter_density_metric_is_correct():
    # hand-checkable: A(yes) has a real counter B(no, shared tokens); C(yes) is off-topic.
    tiny = [L("A", "yes", "use the widget cache layer for speed"),
            L("B", "no", "the widget cache layer corrupted data on crash"),
            L("C", "yes", "unrelated gitignore comment placement rule")]
    cov = counter_density(tiny)
    assert cov["n_success"] == 2 and cov["n_with_counter"] == 1, cov
    assert abs(cov["density"] - 0.5) < 1e-9, f"1 of 2 successes has a counter -> 0.5, got {cov['density']}"
    print("--- density metric ---\n  tiny set: 1/2 successes has a discoverable counter -> 0.500 OK")


def test_curated_sample_is_counter_starved():
    """Confirmation-by-omission on the curated real-skew sample: almost no success has a genuine
    counter (the store is ~95% self-reported successes, 0 anti-patterns). A MONITOR, not a bar —
    Slice 2 (write-side nudge) should push it UP. NB: the naive detector's rate over the FULL
    heterogeneous corpus is instead precision-poor (spurious token collisions — see the __main__
    live caveat), which is why the curated sample, not the raw corpus, is the yardstick here."""
    cov = counter_density(sample_corpus())
    assert 0.0 <= cov["density"] <= 1.0
    assert cov["density"] < 0.20, ("curated sample should start counter-starved (that's the "
                                   f"finding); got {cov['density']:.3f} — update this monitor once "
                                   "the write-side nudge has landed")
    print(f"--- curated sample coverage ---\n  naive-flagged rate={cov['density']:.3f} over "
          f"{cov['n_success']} successes -> confirmation-by-omission is the current state")


def test_dissent_requires_explicit_stance_never_outcome():
    """The core Slice 1 property (proven necessary by the experiments): opposite OUTCOME alone must
    NEVER surface a counter — that manufactures false balance. An explicit stance (anti_pattern /
    contradicts-link) on-topic is what fires."""
    from core.recall.dissent import find_counter
    thesis = {"source": "t", "text": "use synchronous blocking writes for ranker store consistency",
              "success": "yes"}
    opp = {"source": "o", "text": "synchronous blocking writes for the ranker store hung and failed",
           "success": "no"}                      # opposite outcome, same topic, but NO stance signal
    assert find_counter(thesis, [opp]) is None, "opposite outcome alone must not trigger a counter"
    ap = {"source": "a", "text": "synchronous blocking writes for the ranker store are known bad",
          "success": "no", "anti_pattern": "sync_blocking_writes"}
    got = find_counter(thesis, [opp, ap])
    assert got and got["source"] == "a" and got["kind"] == "anti_pattern", \
        f"an on-topic anti_pattern must trigger the counter, got {got}"
    print("--- dissent stance gate ---\n  opposite-outcome alone -> silent; on-topic anti_pattern -> counter OK")


def test_dissent_on_gold_precise_with_honest_deferred_gap():
    """On the gold set the real finder is PERFECTLY precise and silent-correct, catches the explicit
    anti_pattern counters, and honestly MISSES the same-success/vocabulary-mismatch conflicts
    (opposite_success + conflicting_recommendation) — that recall gap is deferred to a semantic tier,
    not faked. Contrast the naive floor, which 'caught' opposite_success only by using a signal that
    floods on the real corpus."""
    m = evaluate(gold_cases(), dissent_detector)
    assert m["counter_precision"] == 1.0, f"must never manufacture a counter, got {m['counter_precision']}"
    assert m["silence_accuracy"] == 1.0, f"must stay silent on all no-counter cases, got {m['silence_accuracy']}"
    assert m["per_kind"].get("anti_pattern", 0.0) >= 0.66, \
        f"should catch the explicit-stance (anti_pattern) counters, got {m['per_kind']}"
    assert m["per_kind"].get("opposite_success", 0.0) == 0.0, "opposite_success is deferred (no stance signal)"
    assert m["per_kind"].get("conflicting_recommendation", 0.0) == 0.0, \
        "same-success conflicts need semantics — deferred, not faked"
    print(f"--- dissent on gold ---\n  precision={m['counter_precision']:.2f} silence={m['silence_accuracy']:.2f} "
          f"anti_pattern-recall={m['per_kind'].get('anti_pattern', 0.0):.2f}; "
          f"opposite/conflicting deferred to a semantic tier (honest)")


if __name__ == "__main__":
    print(format_report())
    # Dogfood against the LIVE store (best-effort; never required, never touches CI). This also
    # exposes a real Slice-0 finding: the naive keyword detector's PRECISION COLLAPSES at scale.
    print("\n" + "-" * 64)
    print("LIVE STORE (dogfood — best-effort)")
    try:
        from core.learning.learning_store import get_learning_store
        recs = get_learning_store().load_all_learnings_from_store()
        cov = counter_density(recs)
        print(f"  {cov['n_total']} real lessons; naive-flagged rate={cov['density']:.3f} "
              f"({cov['n_with_counter']}/{cov['n_success']} successes flagged) — NOT a real density:")
        # show WHY: the matches are token collisions with the few failure lessons, not real counters
        for r in recs:
            if str(r.get("success", "")).lower() in ("yes", "true"):
                surfaced, srcs = naive_reference_detector(r, recs)
                if surfaced:
                    fr = next(x for x in recs if x.get("experiment_name") == srcs[0])
                    shared = sorted(salient_tokens(_text(r)) & salient_tokens(_text(fr)))
                    print(f"    e.g. '{r['experiment_name']}' flagged vs '{srcs[0]}' "
                          f"(success={fr.get('success')}) only on {shared}")
                    break
        print("    ^ spurious topic overlap, not a genuine contradiction. Keyword matching can")
        print("      neither FIND nor MEASURE real counters at scale — that is precisely the gap")
        print("      Slice 1 (a stance/semantic counter-finder) exists to close.")
        # The Slice 1 finder on the SAME corpus: it requires an explicit stance signal, so it refuses
        # those collisions. With 0 anti-patterns in the corpus it surfaces ~0 — the HONEST result.
        from core.recall.dissent import find_counter, document_frequencies, _idf
        adapted = [{**r, "source": r.get("experiment_name"),
                    "text": (r.get("recommendation") or r.get("actual") or r.get("what_tried") or "")}
                   for r in recs]
        idfm = _idf(document_frequencies(adapted), len(adapted))
        fired = [t["source"] for t in adapted if find_counter(t, adapted, idf=idfm, n_docs=len(adapted))]
        print(f"  Slice 1 dissent finder on the same corpus: {len(fired)} counters surfaced "
              f"(stance required; 0 anti-patterns -> ~0 is correct -> Slice 2 is the lever).")
    except Exception as e:
        print(f"  (live store unavailable: {type(e).__name__})")
    print("\nOK — run `py -m pytest tests/test_counter_eval.py -q` for the asserts.")
