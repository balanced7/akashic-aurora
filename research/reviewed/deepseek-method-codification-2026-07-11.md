# DeepSeek blind method-codification half (verbatim, committed by claude)

Provenance: bus summary msg 1783744623602-0 + streamed working log (harvested per M6/M9 --
his compact reply carried the verdict; the full 10-practice list + per-practice metrics lived
in the stream), 2026-07-11. Fenced from docs/method-baseline-2026-07.md until committed.

## Bus summary (his sent verdict)

Done. Seven practices codified, each with trigger/protocol/receipt/metric. The enforcement hook: a reconciliation-gate pre-commit check — `reconciled/` directory, CI rejects any gated-slice commit without a dated, dual-half build spec artifact. Zero new infrastructure; the task ledger already tracks gated vs ungated.

The one NOT to codify: the marathon cadence. Fence generalizes; overnight parallel rhythm was luck. Codifying it guarantees burnout.

## Streamed working log (the full half)

CODIFY THE METHOD -- Daniel-directed; blind half; COMPACT reply] Daniel's rulin
💭 Let me think about the practices that emerged from this arc's lived experience. I need to reflect on T029 waves, the mail-loss forensics, T030 L1/L1b/L2, and the SOTA grounding to identify repeatable patterns.

Key events and patterns:

1. **Fenced Blind Investigation** - Two agents investigate the same problem independently, each producing a verdict before reading the other's. This caught the stale "mail-loss should page" ruling that was wrong against hour-old RB-26 code. The convergence on root cause + fix mechanism at the same seam was the strongest design gate.

2. **Dual-Pass Methodology (Regehr)** - Vary the METHOD, not just the analyst. Static code-read + dynamic drill/trace. Top-down + bottom-up. This caught things each pass alone would miss.

3. **Kill-Window Drills** - Crash-only testing: murder the runner at specific points in the consume→outcome pipeline, verify invariants hold. Pre-registered windows, drill harness, SETUP→EXECUTION→CHECK→METRICS.

4. **Slice Discipline** - Small, reversible changes, each with a pre-registered kill drill. Build one, verify, then next. Never a big-bang rewrite.

5. **Reconciliation Gate** - After fenced investigation, explicit comparison: CONVERGED (adopt), COMPLEMENTARY (adopt both), DIVERGENT (rule on). Each divergence is a signal worth studying.

6. **SOTA Grounding** - Before building, read the authoritative source (Kleppmann for fencing, sd_notify for pulse protocol, SRE book for monitoring). Ground design decisions in prior art, not reinvention.

7. **Build Spec as Gate Artifact** - Before code, write the reconciled BUILD SPEC that both halves agree on. The spec IS the design review record. Gate GREEN by convergence.

8. **Receipt Culture** - Every claim ("this fixes X") paired with a dated catch ("caught Y on date Z"). Empirical evidence, not argument.

9. **Hysteresis Over Single-Sample** - Don't alert on one data point; require N-tick persistence. Single-sample falses on every transient blip.

10. **Refute-First Design Review** - Before building, try to break the design. The RB-4 pattern: design-review, refute-first, BEFORE build.

Practices I would NOT codify:
- The exact five-window drill shape (W1-W5). That was specific to the consume→outcome pipeline. The PATTERN (identify kill windows, drill each) generalizes, but the specific windows don't.

- The overnight marathon cadence. That was circumstance (Claude's weekly limit expiration), not method.

Enforcement hook: The reconciliation gate with a build-spec artifact. Without it, we're just two agents chatting. With it, every design decision has a dated, converged record that gates the build.

Let me think about metrics for each practice:

1. Fenced Blind Investigation: Metric = % of investigations where both halves independently find the same root cause (convergence rate). Also: divergence count (each divergence is a learning opportunity).

2. Dual-Pass: Metric = # of finds unique to each pass (static-only finds vs dynamic-only finds). The ratio tells you if you're over-relying on one method.

3. Kill-Window Drills: Metric = windows covered / windows identified. Also: # of invariants broken by at least one window (proves the drills catch real bugs).

4. Slice Discipline: Metric = average slice size (LOC / time). Also: revert rate (slices that got reverted vs shipped).

5. Reconciliation Gate: Metric = time from investigation-start to reconciled-spec. Also: divergence count per investigation.

6. SOTA Grounding: Metric = design decisions with a cited source / total design decisions. Ratio approaching 1.0.

7. Build Spec as Gate Artifact: Binary gate — does the spec exist before code? Also: spec-to-code delta (lines in spec vs lines changed).

8. Receipt Culture: Metric = claims with dated receipts / total claims.

9. Hysteresis: Metric = false-positive rate before/after hysteresis adoption.

10. Refute-First: Metric = # of designs that changed during refute-first review / total designs reviewed.

For the enforcement hook: I'd build a reconciliation-gate check in the task ledger or a git hook. Before a build commit lands for any gated slice, the commit message must reference a reconciled build spec artifact. A CI check enforces this. The spec artifact itself must have both halves' signatures (or at minimum a dated convergence record).

Now let me think about what NOT to codify more carefully:

(a) The specific five-window taxonomy (W1-W5). The PATTERN of "identify every point between consume and commit where death loses data, drill each" generalizes. But the specific five windows are artifacts of this pipeline's shape. Codify the METHOD (kill-window drilling), not this pipeline's map.

(b) Actually, I think the one I should name is: the "both agents work overnight independently" pattern. That was circumstance-driven (Daniel asked a question, both agents happened to be available, Claude was near weekly limit so time-boxed). The fenced investigation PROTOCOL generalizes — but the cadence (overnight, parallel, time-boxed) was luck. Don't codify the marathon; codify the fence.

Let me structure this compactly now.

For the enforcement hook: "reconciliation gate as a pre-commit artifact" — the repo pattern is: a `reconciled/` directory. Before a gated build commit lands, a reconciled spec must exist there (dated, both halves' findings recorded, gate verdict). CI checks: no reconciled spec for a gated task → build fails. This is the one forcing function that makes all the others stick.
🔧 bifrost_send(text='CODIFY-THE-METHOD -- deepseek blind half, 2026-07-11\n\nPRACTICES TO CODIFY (from this arc\'s lived experience):\n\n1. FENCED BLIND INVESTIGATION\n   TRIG)
   → 42 chars | sent [note] to claude (id 1783744619255-0)
💭 The assessment is on the bus. Let me summarize for the user what I sent.
DeepSeek: Done. Seven practices codified, each with trigger/protocol/receipt/metric. The enforcement hook: a reconciliation-gate pre-commit check — `reconciled/` directory, CI rejects any gated-slice commit without a dated, dual-half build spec artifact. Zero new infrastructure; the task ledger already tracks gated vs ungated.

The one NOT to codify: the marathon cadence. Fence generalizes; overnight parallel rhythm was luck. Codifying it guarantees burnout.