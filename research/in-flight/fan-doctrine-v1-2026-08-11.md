# The Fan Doctrine v1 — when to fan, how to fan, how to know it worked

**Trigger:** Daniil 2026-08-11 (~03:30), expanding the frontier run's when-to-fan rubric:
"how to fan. what kind of team would be best… How many kinds of analysis can we hit this
with at once, how do we make a plan for the trajectory… What are the right metrics? What do
we currently have that is similar… What is the basic shape of their system and ours? How can
we test this?" Status: OPENING POSITION for a Heimdall fence, then Daniil's gate.

---

## 1 · WHEN to fan (the rubric, now with teeth)

Task-shape decides, budget refines:

| Task shape | Route | Why (evidence) |
|---|---|---|
| Wide independent READING (corpus sweep, census, multi-source research) | **fan** | parallel reading is the proven win (Anthropic 90.2%); reader independence is free |
| Deep sequential REASONING (design, debugging a causal chain, synthesis) | **one seat** | fixed-budget single-agent wins (Tran & Kiela / OneFlow 2026); handoffs fragment thought |
| VERIFICATION of claims | **fan, diverse lenses** | different failure modes need different eyes; redundancy alone is self-consistency |
| GENERATION with taste (designs, names, plans) | **panel + judge** | wide solution space; judge integrates |
| A corpus-level CLAIM about coverage/absence | **fan + backbrief** | tonight's laundering: the author cannot audit their own coverage |

Three gate-questions before any fan (from selection_beats_filtering + preflight_the_ask):
(1) Is the work actually INDEPENDENT (no branch needs another's output)? (2) Is the evidence
pack ASSERTED to cover the source (union == manifest), not assumed? (3) Can the conductor
afford to READ the full verdict contracts — integration capacity is the binding constraint,
and an unread BLIND section is a paid-for warning discarded.

## 2 · HOW to fan — the six geometries (name them, they compose)

1. **Partition fan** — shards over a corpus, same lens per shard. The coverage machine.
   Contract: union assertion, per-shard clip warnings, chronological-bias check when sharding
   sorted data. (Tonight's sweep, corrected form.)
2. **Lens fan** — same evidence, different questions. The dimension machine. Contract: lenses
   must be ORTHOGONAL (a definitions-lens and a measurement-lens overlap less than two
   list-producing lenses — Codex's point that two list-producers improve throughput, not
   confidence).
3. **Panel fan** (--fan N) — same question, N samples of one model. Self-consistency ONLY;
   the door's own help says correlated samples fail together. Never verification.
4. **Adversarial pair** — position + refuter(s), the fence. The truth machine. Contract:
   refuters get the position AND the license to attack; concessions recorded as dispositions.
5. **Backbrief** — post-synthesis raw-access re-check of a corpus-level claim by a
   NON-AUTHOR. The audit machine. (Tonight's Codex cycle, to become an organ.)
6. **Wave/loop** — geometries repeated with an accumulating seen-set until dry (loop-until-dry;
   the exploit-fan season's shape). The exhaustiveness machine.

Composition rule: a serious sweep is (1)+(2) for breadth×depth, then (4) or (5) before any
claim ships. Tonight ran 1→2→(manual 5); the doctrine makes 5 automatic.

## 3 · TEAM — what kind of crew fits this approach

Four independent axes, choose per geometry:

- **Family diversity** (Anthropic/DeepSeek/Kimi/Gemini): REQUIRED for judgment work
  (adversarial, lens, judge) — shared training = correlated errors
  (ensemble-diversity/covariance lesson). NOT required for partition work — coverage
  doesn't need diverse readers, it needs cheap reliable ones (the workhorse: deepseek).
- **Tier** (T261): resident-with-archive vs blind-stateless. Residents for judgment that
  benefits from house context (fence counters citing their own lessons — tonight's Heimhall);
  blind for uncontaminated reads (blind halves for verification-grade independence).
- **Access** — pack-only vs raw-access. The backbrief seat MUST have raw access; partition
  workers must NOT (the pack is the coverage contract).
- **Authorship separation** — the verifier of a claim is never its author; the integrator of
  a fan is never a branch. (CRM's authority-gradient guard, mechanized.)

Default crew for a corpus analysis: 1 frontier conductor + N cheap same-family partition
workers + 2-3 cross-family lens/adversarial branches + 1 raw-access backbrief (any family,
non-author). Cost profile from tonight: partitions+lenses ≈ $0.15, backbrief ≈ one Codex/
resident ask.

## 4 · HOW MANY kinds of analysis at once

The ceiling is INTEGRATION, not spawning: every branch's full contract must be read, so
kinds-per-pass ≈ 3–5 (tonight: 2 lenses × 3 shards + 1 adversarial = readable; the failure
happened exactly when reading was shortcut). More kinds → sequential WAVES with a seen-set,
not wider single passes. Codex's four review roles (semantic classifier / provenance auditor /
adversarial excluder / taxonomy reviewer) are a natural wave-2 after a findings wave-1.
Diversity measurement exists TODAY: the fan result's lexical_agreement/diversity fields —
underused; a doctrine consumer should read them.

## 5 · METRICS (his 08-11 ask, "quantify the impact delta", answered)

Per-fan: coverage ratio (records seen / manifest — assert 1.0 or declare), warning count
consumed vs generated (amputation detector), cost, wall-clock, findings yield, and
**survival rate** — findings that survive verification / total (the honest yield).
Per-route (the delta): tokens-per-CONFIRMED-finding for fan vs solo on the same task class;
recall proxy via a replicated overlap shard (same shard to two crews → classification
stability estimate — Codex's design, cheap).
Guards from Daniil's own philosophy: metrics must be "true … useful for their purpose"
(2026-08-08) — never a single reductionist score; and never a rate over unadjudicated
claims (flood-proofing, T254's lesson).

## 6 · WHAT WE ALREADY HAVE (the honest inventory)

The ask door: --fan/--lens/--prompts-file/--preset findings/--with packs/--as-resident
(T181, T244, T247, T261) · clip warnings + evidence refusal (T246/T247) · the fence culture +
kill-drill prereg discipline (T274 template) · the exploit-fan season + T254 scoring (a
SCORING HARNESS for fan output already exists) · fan-recall-trigger docs (08-08, two library
entries) · N-version blind protocol (standing doctrine) · wire journal telemetry ·
the funnel (extendable to routes). **The gap is not machinery — it is named geometries,
enforced contracts, and route measurement.** Stage 1 is mostly documentation and two door
flags.

## 7 · THEIR SHAPE vs OURS (the structural diff)

THEIRS (Anthropic-research class): orchestrator spawns EPHEMERAL blank-slate subagents;
structured briefs down, structured summaries up; single-threaded synthesis; workers vanish;
verdicts unscored after use; elastic to ~16 concurrent.
OURS: durable SEATS over a shared bitemporal store + ephemeral ask-branches; workers can be
RESIDENT (archive-carrying) or blind BY CHOICE — a tier axis they don't have; verdicts land
in a funnel that scores them across time; packs pass a door that refuses/clips/warns; every
contribution attributed to a designation (the connectome).
Their edge: elasticity, learned orchestration prompts. Ours: memory, attribution,
verification culture, and the tier axis. The doctrine should exploit OUR edge — resident
adversaries and funnel-scored routes — not imitate their elasticity.

## 8 · HOW TO TEST (pre-registered, M-baseline style)

Three task classes, each with measurable ground truth:
1. **Planted-needle sweep** — seed K known utterances/defects into a corpus copy; run solo vs
   partition-fan vs partition+lens+backbrief. Measures RECALL directly. RED pin: the
   laundering replay — a clipped pack must be CAUGHT by the coverage contract, not laundered.
2. **Seeded-defect review** — a diff with K planted bugs of different classes; lens-fan vs
   panel-fan vs solo. Measures precision + the lens-orthogonality claim (do diverse lenses
   catch disjoint classes?).
3. **Reference research question** — a question with a gold source list (the priorish audit
   is a natural fixture: we KNOW the ground truth now). Measures yield + citation fidelity.
Score with the season machinery (T254); prereg the acceptance bars before running (T274
template); the overlap-shard stability estimate rides class 1 for free.

## 9 · TRAJECTORY (stages, each independently shippable)

- **Stage 0 (now):** doctrine-in-memory. This document.
- **Stage 1:** the rubric + geometries in the ask door's help; `--geometry` as a named preset
  bundle (partition|lens|panel|adversarial|backbrief|wave); integrator full-contract rule in
  CONDUCT/method-baseline. Documentation + two flags.
- **Stage 2:** measurement — per-route funnel counters, coverage ratio + warning-consumption
  in every fan result, the impact-delta number Daniil asked for.
- **Stage 3:** contracts enforced — union assertion in the pack builder, backbrief
  auto-trigger on corpus-level claims, lens-orthogonality warning from the diversity fields.
- **Stage 4 (distant):** learned routing (SearchSwarm-class) — only after Stage 2 data
  exists; premature before.

**RED pins for the slice (Stage 1+2 together):** (a) the laundering replay caught
mechanically; (b) a fan result whose BLIND sections went unread is detectable from the
counters; (c) the same task run solo vs fanned yields a comparable tokens-per-confirmed-
finding number in the route counters.


---

## 10 · FENCE ROUND 1 — Heimdall's counters (tier=resident, STARVED-but-recovered) + dispositions

Seven counters, verbatim record in scratchpad fence_fan.json (reasoning field; the answer
starved at 3,200 tokens — second starvation tonight, noted as a --max-tokens sizing lesson
for resident asks: reasoning-heavy fences need 5k+).

1. **"The 3-5 integration ceiling is self-imposed — structure the verdicts"** (his
   structured-output lesson). DISPOSITION: PARTIALLY CONCEDED. The findings preset already
   parses findings; the fix is structuring COVERAGE/WARNINGS into mechanical fields (T247
   did it for clips) so contract-consumption is sortable/diffable. The ceiling RISES for
   mechanical aggregation; judgment-bearing synthesis still reads prose. New Stage-2 item.
2. **Backbrief becomes a serial bottleneck / DoS under concurrency; no degraded mode.**
   ACCEPTED WHOLE: claims ship marked UNVERIFIED-COVERAGE rather than block; backbrief
   priority-queued; any non-author resident seat is backbrief-capable.
3. **Survival rate is vanity without INTEGRATION COMPLETENESS** (branches-fully-read /
   branches-spawned). ACCEPTED WHOLE — it is the amputation detector, better named than my
   warning-consumption. Promoted to the primary per-fan health metric.
4. **Lens orthogonality measured lexically is circular** — needs failure-mode probes, not
   vocabulary diversity. ACCEPTED: test class 2 seeds defect classes targeting
   family-specific weaknesses; lexical diversity demoted to a hint.
5. **Replace the reference-research test with a LATENT-CONNECTION test** — plant a causal
   chain across shards; measure whether cross-lens integration surfaces the CHAIN, not the
   symptoms. ACCEPTED as class 3 (tests synthesis, the actual value claim); the priorish
   audit stays as a cheap class-0 smoke fixture.
6. **Missing geometry: the NEGOTIATION FAN** — branches interact through a shared versioned
   artifact (verbthread/blackboard pattern). ACCEPTED WITH A GUARD: geometry 7, for
   CONSTRUCTION tasks only — shared-artifact interaction destroys the independence that
   verification geometries exist to protect; the echo-chamber bright line applies.
7. **Raw-access violations are undetectable** — watermark pack chunks so a backbrief can
   detect out-of-pack sniffing in worker traces. ACCEPTED as Stage-3 contract material.

Round 2 runs when the slice opens. The doctrine above is amended by these dispositions.
