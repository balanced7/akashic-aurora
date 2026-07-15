# Model-Attribute Transfer — Reconciliation (claude ⋈ deepseek) — 2026-07-15

Status: reconciled from two BLIND halves (claude-model-attribute-transfer-2026-07-15.md,
deepseek-model-attribute-transfer-2026-07-15.md). Daniel's challenge verbatim: "how can we
augment opus 4.8's behavior to be more like fable. What attributes make fable and gpt sol
more robust? are there any elements we can capture for ourselves?"

## Blind convergences (both halves, independently — the strongest findings)

1. **THE GAUGE INVERSION.** deepseek (from the seat): "the hop counter MADE me as effective
   as a stronger model for that decision." claude (from the transcript): "gauges help weaker
   models MORE — instrumentation is a prosthetic for weak seats, not a luxury for strong
   ones." Same law, both directions: visible budget/state substitutes for implicit triage.
2. **HARNESS TIER BEATS MODEL TIER.** deepseek's formulation is the keeper: the question is
   not "make opus behave like fable" but "make the harness so strong that opus+harness ≥
   fable alone — and fable+harness ≥ fable+2." claude's twin claim: with amplify+bound both
   running, a weaker model's deficit degrades into COST (review cycles), not CORRECTNESS.
3. **FORCED ADVERSARIAL SELF-REVIEW.** claude's required attack-surface slot at seal ≡
   deepseek's false-positive hunt prompt: both force the author into verify-mode against
   its own work. (Receipt: both of cursor's real defects sat inside its self-flagged list.)
4. **EVIDENCE-BEFORE-CLAIM AS A GATE.** claude's verify-before-mutate + deepseek's M10
   pre-flight assertions + his M1 pre-send consistency: one family — claims must resolve
   against committed reality BEFORE they leave the agent. (Graduates the
   fence_report_citation_path_gate lesson from advice to automation.)

## Merged proposal roster (ranked: transfer-value / build-cost)

| R | Proposal | From | Shape |
|---|----------|------|-------|
| 1 | **Constraint pack at boot** — ~300-char LIVE CONSTRAINTS block (RB-26, RB-29, T026, T039a, T045) in every seat's boot | ds M9 | context; trivial build |
| 2 | **Three-strikes diagnosis hook** — 3rd identical (action,failure) blocked: "cite a root cause or a lesson" (+ list 2 alternative causes) | cl B/H | hook; small build |
| 3 | **Pre-flight assertion runner** — reply/review sends held until file:line cites resolve, evidence events exist, "fixed" claims name a pin; kind-gated (directed answers only) | ds M10 + cl A | runner gate |
| 4 | **Attack-surface slot + hunt prompt** — required, seal-checked fence section + "find one failure sequence" injection | cl C + ds M13 | fence v1.1 |
| 5 | **Universal gauges** — hop counters on every seat + M8 context fuel gauge slice 1 + 80% auto-escalate | both | instrumentation |
| 6 | **Handoff + forensics templates, send-enforced** — self-contained handoff fields (what/files/bars/format) refused if missing; ordered-exoneration incident template | ds M2/M3 | templates + check |
| 7 | **3-pass design gate** — create → constraints re-injected, verify-mode re-read → send | ds M11 | prompt sequencing |
| 8 | **Model-tier-aware recall + behavior-diff mining** — tier-tagged lessons weighted by the ACTIVE seat; every confirmed fence finding + self-reported anti-pattern auto-drafts a trigger-phrased lesson (Forge F1 gate) | cl 4/5 + ds 1.5 | recall pipeline |
| 9 | **Capability routing per slice stage** — reconciliation/kill-condition stages pinned to the strongest live seat via `fleet` capability-select; mechanical stages to any seat | cl 6 | doctrine + dispatch |
| 10 | **Replay-the-bug step** — evidence-cited bug tasks get a forced trace-first STEP 0 | ds M12 | prompt sequencing |
| 11 | **Transcript mining (Sol/Fable ingestion)** — harness payload captures (post-T065) + any Sol transcripts Daniel drops in research/ feed pipeline R8 | cl 7 | uses R8 |

## Honest limits (both halves agree)

Judgment does not transfer: constraint-application (which rule matters HERE), adversarial
creativity, and calibration quality stay model-bound. The harness triggers a model's best
behavior reliably, catches its failures cheaply, and routes the hardest calls to the
strongest seat — it does not manufacture judgment. The fence exists precisely because
amplification has a ceiling.

## The line for Daniel

Robustness in this system is a harness property first and a model property second — and
tonight was the measurement: the same mid-tier model made a strong-seat decision at hop 51
because a counter existed; an unassisted agent followed the whole protocol because the
contract was legible; and the strongest seat's two defects (cursor's) died in review, not
production. Creative energy goes to HARNESS TIER advancement; model upgrades then compound
on top of it instead of substituting for it.
