# Leapfrog Plan — Outcome-Grounded Memory

> Status: PLAN (build-in-slices, every slice gated by a test or benchmark).
> Written 2026-07-01. Inputs: full-repo audit, docs deep-read, competitive web survey
> (note `competitive-landscape-2026-07`), and the DS4/DeepSeek-V4-Flash case study.
> Companions: `docs/retrieval-critic-design.md`, `docs/directive-friction-audit.md`,
> `docs/recall-critic-decision.md`, `docs/ROADMAP.md`.

## 1. Thesis — compete on the axis the field does not measure

The entire field (mem0, Zep, Letta, claude-mem, native auto-memory) competes on
**retrieval quality**: did we recall the right fact? Benchmarks: LoCoMo, LongMemEval,
BEAM. Nobody measures **causal memory utility**: did this memory change the action
and improve the outcome?

Nobody measures it because measuring it requires three primitives at once:

1. **Action-time injection** — to tie a specific memory to a specific action
   (session-start injectors structurally cannot; the memory is too far from the act).
2. **An append-only ledger of actions + outcomes** — to establish ground truth and
   replay counterfactuals.
3. **An outcome-credit loop** — to convert outcomes into per-memory usefulness.

We already have all three built. No competitor has more than zero of them, and
retrofitting them means rebuilding their architecture. That is the leapfrog:
**define the outcome-grounded axis, instrument it, benchmark it, publish it, win it.**
The field built remembering machines; this becomes the first memory system that can
*prove* a memory changed an outcome.

The moat that survives Anthropic shipping native action-time recall in a point
release: the ledger data, the replay methodology, the outcome-credit corpus, the
dialectical layer, and cross-harness scope. A native clone gets the hook; it does
not get the evidence loop.

## 2. Assets already in hand (from the 2026-07-01 audit)

- Recall-at-action end-to-end (PreToolUse inject, warm cache, anti-repeat, FAITH-1
  gate, relevance floor) — REAL, tested.
- Append-only Ledger + Store with fail-soft backends — production-grade.
- Usefulness loop designed with the recommender-debiasing literature already
  metabolized (epistemic-risk register F1–F3 + mitigations).
- Dissent finder (precision-first) + counter-eval harness + semantic-gate yardstick.
- Deterministic, auditable ranking — reproducible by construction.
- One-door CLI/MCP that cannot drift; CI + boundary guards; 455+ behavioral tests.

Known soft spots the plan must close first: the PostToolUse payload-shape assumption
(the credit signal may never have fired on live data), a single-digit lesson corpus,
zero external numbers, zero distribution.

## 3. Borrowed principles — the DS4 / antirez case study

The video ("How DeepSeek Runs a 284B LLM on a Laptop") is about inference, but four
durable principles transfer:

1. **Asymmetric fidelity — spend bits where a mistake is fatal.** DS4 crushes the
   redundant expert layers to 2-bit but keeps the router at 8-bit, because a router
   mistake corrupts everything downstream while any one expert is expendable.
   Our stack has the same shape: the **gate path** (ranker, relevance floor, FAITH-1,
   provenance, anti-repeat) is the router — it stays deterministic, fully tested,
   maximum fidelity. The **corpus** (lesson bodies, chronicles, context sections) is
   the expert bulk — compress it aggressively (distillation, MDL-under-faithfulness).
   The token budget is our bit budget. This principle also settles what to build
   from the Codex plan: only the compression/consolidation slice, not the 8-slice
   curator.
2. **Narrow and validated beats general and undefined.** DS4 runs ONE model with
   validated quants and guarantees quality; run-anything llama.cpp leaves quality
   undefined — "that's the difference between a toy and production." Our version:
   own one vertical (Claude Code + Cursor peers) end-to-end with **validated hook
   contracts** — live-captured payload fixtures per harness version, contract tests
   in CI, a published compatibility matrix. This converts our biggest fragility
   (rented hook APIs, assumed payload shapes) into a visible reliability claim
   no competitor makes.
3. **Local flash-tier economics change the architecture.** A frontier-class local
   model at zero marginal cost means judge/critic/consolidation workloads stop
   being budget-rationed: the semantic gate can run on every recall instead of only
   escalations; the dreaming pass can run nightly; the replay bench can run
   continuously. (DS4's disk-persisted KV cache is the same instinct as our warm
   cache — validating parallel.)
4. **One focused person flips a field when the claim is sharp and verifiable.**
   DS4 hit 13k stars in a month because the demo mattered ("first local model I
   reach for for serious work") and the claim was checkable. Our equivalent
   headline: *watch an agent fail, learn, and provably succeed because of the
   recalled lesson — with the counterfactual replay to prove it.* One verifiable
   demo + one reproducible benchmark beats feature breadth.

## 4. Triage — the dependency chain (do in this order)

Everything downstream depends on the step before it:

loop fires → corpus grows → numbers exist → claims are credible → distribution/publication.

- **T1 (days): make the loop real.** Capture live PostToolUse payloads, fix
  `_is_success` against reality, prove the FAIL→SUCCESS credit fires in a real
  session. Closes ADR_0629210203. Until this lands, the differentiator is plumbing
  that has plausibly never executed.
- **T2 (days–2wk): unblock the write side.** The corpus is the limiting reagent
  (~8 lessons, 2 anti-patterns). Ship the friction-audit top fixes: JIT learn
  prompt on the FAIL→SUCCESS instant, auto-draft lessons at wrap, pre-filled
  defaults.
- **T3 (1–2wk): instrument the funnel.** surfaced → acted → outcome, per
  impression id, queryable via a `stats` verb. First honest internal number.
- **T4 (parallel): harness contract tests** (principle 2). Fixture + CI job per
  harness version.
- **Sequencing note vs `next-focus`:** the semantic gate stays queued and endorsed,
  but T1–T3 come first — the gate's own eval wants live payloads, and a proven
  loop makes every later claim land harder.

## 5. The waves

### Wave A — Prove the loop (T1–T4 above)
Gates: credit visibly fires on a live session; corpus growth rate measurably up
(target 30+ lessons in 30 days); `py agent_cli.py stats` prints a real funnel;
contract suite green.

### Wave B — The measurement moat: Ledger Replay Bench
- B1. Replay harness: reconstruct (state, action, outcome) episodes from the
  Ledger; re-run recall variants offline: OFF / session-start-style /
  action-time / action-time+dialectic.
- B2. Outcome metrics: first-try success on previously-failed targets,
  repeated-mistake rate, tokens-to-success. With confidence intervals.
- B3. External anchor: LongMemEval-V2 and/or the coding memory-transfer benchmark
  (arXiv 2604.14004) adapters — one published score, however modest.
- B4. Publish the bench itself (fixtures included, reproducible) — the DS4
  "validated artifact" move; in a field of vendor-claimed numbers, reproducibility
  is the differentiator.
Gates: bench runs nightly on N≥50 real episodes; one honest delta number public.

### Wave C — Retrieval upgrade under asymmetric fidelity
- C1. Semantic gate as designed in `next-focus` (default-suppress, cached,
  budget-bounded, async), gated by tests/test_semantic_eval.py.
- C2. **Local judge provider**: run the judge on a local model (Bifrost provider;
  llama.cpp / ROCm on the AMD box; DS4-class engines as they mature) → zero
  marginal cost → judge every recall, not just escalations. Gate: same eval
  accuracy at ~zero cost within the latency budget.
- C3. Embeddings as ONE audited signal inside the deterministic fusion (ablation-
  gated, never a rip-and-replace). Gate: paraphrase-recall up on the semantic eval
  with no precision loss. "Deterministic" pitch = auditable + reproducible, not
  lexical-only.
- C4. Codify asymmetric fidelity: gate path stays deterministic/full-fidelity;
  corpus compresses. Add to LEXICON/review checklist.

### Wave D — The flywheel
- D1. **Lesson track records surfaced to the agent**: `[helped 3× · noise 1× ·
  unverified — claude's advice]`, with engagement decoupled from corroboration
  (register M2.2). No product shows memories with win rates.
- D2. Causal credit (M2.1): credit lessons overlapping the actual fix / top-ranked,
  not uniform co-surface credit.
- D3. Dialectical retrieval as the headline feature: position = thesis + strongest
  live counter; write-side anti-pattern capture arrives as a byproduct of A/T2.
- D4. **Dreaming pass, local-first**: nightly consolidation (merge near-dupes,
  contradiction → supersession review, distill clusters) on the existing
  Consolidator + a local model. This is the small, high-value slice of Codex —
  build only this. Gate: corpus bounded while bench recall quality is
  non-decreasing.
- D5. Write-time immune system (MemGuard-direction): type/provenance screening at
  learn time + poisoning red-team fixtures. Memory poisoning is now a named,
  studied threat (arXiv 2606.04329); our write side is currently uncurated.

### Wave E — Distribution + research (once Wave B numbers exist)
- E1. Package as a Claude Code plugin that sits ON TOP of native auto-memory
  (import MEMORY.md as atoms; never fight the native layer). Fresh-machine
  install ≤5 minutes.
- E2. Write-up: action-time memory + outcome credit + dialectical retrieval, with
  bench numbers. The research identity is where we are strongest relative to the
  field (CoRM-RAG / FVA-RAG / Memory Contagion / ReasoningBank are converging on
  exactly these problems; no product ships the answers).
- E3. Publish the compatibility matrix (from T4).

### Wave F — Bleeding edge (research track, after B)
- F1. **Self-improving critic** (the 2026-07-01 idea, scoped): a local judge
  evaluated—and eventually DPO/distillation-tuned—against OUR ledger's real
  FAIL→SUCCESS outcomes as ground truth. CriticGPT trains on synthetic bugs; we
  have real ones with real outcomes. Start architectural (frozen local judge +
  held-out ledger eval); train only when data volume justifies. Gate: beats the
  prompted baseline on held-out episodes.
- F2. Provenance-weighted trust (F1 M4): `[confirmed]` only via independent
  corroboration, cross-agent.
- F3. Memory transfer: export/import validated lesson packs across projects
  (the 2604.14004 direction).

## 6. Solidify current wins (cheap, schedule in gaps)

- S1. Refactor `core/foundation/fast_cache.py` onto Store (kills 11 bare excepts +
  three boundary allowlist entries).
- S2. Triage `services/` (~1.2K LOC, never imported): merge redis_sync into the
  reconciler, retire the monitors.
- S3. Resolve the SessionRecovery class duplication.
- S4. README reposition: lead with the proven loop (recall-at-action end-to-end);
  move Codex/Perspectives explicitly under "designed, queued".
- S5. Keep the honesty discipline — it is a genuine competitive asset; the field's
  vendor-benchmark culture makes verifiable modesty stand out.

## 7. Scope freeze (do NOT build until after Wave B)

Full Codex 8-slice curator · Perspectives · spine v2 wave 2 (V6–V9) · Bifrost full
mesh · worktree-per-agent experiment. Revisit with bench numbers in hand.

## 8. Honest risks

- **Hook dependency**: Anthropic could ship native action-time memory any release.
  Mitigation: the evidence loop + published method + cross-harness scope, not the
  hook itself.
- **Replay validity**: environment drift makes strict replay approximate — treat
  the bench as offline evaluation, say so plainly, and keep the live funnel (T3)
  as the ground-truth complement.
- **Corpus volume**: the bench needs N≥50 credited episodes; that is why T2/T3
  precede B, and why the loop must run for weeks before claims.
- **Local GPU reality**: AMD/ZLUDA fine-tuning is rough; inference-only local
  judging is the safe first step (llama.cpp), training is Wave F and may need
  rented compute.
- **Goodharting our own bench**: hold out episodes; never tune the ranker on the
  same episodes it is scored on; keep the register's anti-sycophancy mitigations
  (M2.x) wired into any credit-driven ranking change.
