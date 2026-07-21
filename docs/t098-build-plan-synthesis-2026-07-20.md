# T098 Build-Our-Own — Synthesized Sliced Plan (2026-07-20)

**Authorship:** claude synthesis over independent rankings from deepseek (build-execution / adversarial-review seat) and kimi (third voice, "operator sees fleet TRUTH in 60s" lens). Grounded in the finalized T098 charter, kimi's sequencing-position, the competitive pain-point research, and deepseek's T094 R0 verification.

**Status:** DRAFT for Daniel's gate. Both peers say "Daniel gates the re-base." Slice 0 is unanimous + prereg'd and can start immediately under Daniel's "begin building" directive.

---

## Where the two axes landed

| Rank | deepseek (floor / can't-silently-break) | kimi (moat / operator-sees-truth) |
|------|------------------------------------------|-----------------------------------|
| 1 | T094 R0 recall journal (context-visibility substrate) | **T097-S1 H0 sub-threshold wedge visibility** |
| 2 | T098-E0 capture-first event fixtures (gates slice 1) | **API door v0 + Mission/Run object** |
| 3 | **T097-S1 H0 sub-threshold wedge visibility** | Context-recovery UX (painpoint #5) |
| 4 | **Run registry + mission object** (= slice 1) | Forward cost estimation (painpoint #4) |
| 5 | Typed face artifact + CI parse gate (kills C10-1) | Multi-repo shared-plan (painpoint #7) |

**Unanimous (bolded above):**
- **T097-S1 H0 is the prerequisite** before any program face ships (deepseek #3, kimi #1). A mission face that reads "fleet healthy" during a 25–40 min sub-threshold stall bakes the C1-8/C10 disease into the new program on day one.
- **Run registry + mission object IS program slice 1** (deepseek #4, kimi #2). The run becomes a first-class addressable object.
- deepseek's #2 (capture-first fixtures) and #5 (typed face + CI gate) are exactly what kimi *folds into* slice 1's acceptance bar. They agree; deepseek wants them explicit as gates.

**Complementary divergence (the value of two axes):**
- deepseek pushes the **engineering-discipline floor** (recall journal, pinned event fixtures, parse-gated face) — build it so it *can't* silently break.
- kimi pushes the **genuinely-new product moats** the research demands (context-recovery UX, forward cost, multi-repo) — the surfaces no competitor has.

---

## The synthesized slices

### Slice 0 — Truthful floor · `T097-S1 H0` (UNANIMOUS · S · FLOOR)
Extend `doctor.examine` to surface a consumer stuck in **[0, 300s)** as a default-on **"approaching wedge"** dashboard signal. Today truth exists in the substrate but the render is silent below the page threshold. PREREG **P-S1-0** stands (kimi fence verdict on file).
**Why first:** cheapest slice in the ledger, and the credibility prerequisite for every face that follows. Painpoint theme #4 (observability, the only VERIFIED-3-0 need) is our first-class differentiator — we cannot render a lie.

### Slice 1 — The program is born · Run registry + API door v0 + thin typed face (UNANIMOUS · L)
`RUN-REGISTRY {run_id, mission, participants, state, budget, created_by}`; `POST /missions → run_id`, `GET /missions/{id}`; run-scoped SSE lifecycle; a thin typed face renders the mission strip. ~60–70% formalizes existing doors (launcher, SSE `/events`, status/vitals, pause/resume, conductor, ledger_update, Cap ladder, recall/MCP); the new 30–40% is the run-registry + mission POST + run-scoped frames + approvals-as-objects.
**Acceptance pins (deepseek's discipline, non-negotiable):**
- (a) **capture-first event-schema registry** — every emitted event has a pinned fixture proving the runtime actually produces it, before any consumer trusts it (deepseek #2 / T098-E0).
- (b) **face is a separately-built typed artifact with a CI parse gate** — kills the C10-1 genus (2700-line f-string HTML/JS served from the working tree) structurally (deepseek #5).

### Slice 2 — Context-visibility substrate · `T094 R0` recall journal (deepseek #1 · M · FLOOR)
Journal every recall decision so the program's context-inspector has data to render. Prereg **verified** (all 5 amendments + 2 gap pins folded; 14 pins), zero new design, buildable now. Ships with its face per the convergence rule.

### Slice 3 — Context-recovery UX · painpoint #5 (kimi #3 · M/L · MOAT/FACE)
Live context-budget fill gauge + graceful-degradation ladder (summarize-oldest → narrow-scope → checkpoint → resume). Generalize the RB-5 confession doctrine into product. **Unmet by ALL competitors** (Codex hard-fails at the ceiling, Cline unrecoverable-at-limit, Goose's own insider filed it) — our most defensible new moat. Aurora already has the seeds (SpendMeter, bound_tool_text, abandon-but-confess).

### Slice 4 — Forward cost estimation · painpoint #4 (kimi #4 · S · FLOOR+FACE)
Forward estimate of the *next* call's cost from prefix size + `turn_metrics` median completion per `ask_kind` (we only show retrospective totals today). The floor emits a versioned cost event; the face renders the gauge — the worked example of the every-floor-ships-a-face rule. Cheap, proves the convergence rule in public.

### Slice 5 — Multi-repo shared-plan coordination · painpoint #7 (kimi #5 · L · MOAT)
Orchestrate across repos against a shared evolving plan (the orchestrator gap the whole category is groping toward). Larger, genuinely new; **depends on the run-registry (slice 1)** to hang the shared-plan object on. Pull as slice 2–3 of the program proper, not before the run object is real.

---

## Cross-cutting rules & gates (both peers agree)

1. **Convergence rule:** EVERY floor slice ships *with* its API-door face. Acceptance bar = emits a versioned event + the face renders it. No new headless module with a "GAP" UI consumer.
2. **Honesty gate:** before any "top-3 unmet = our core" headline reaches PUBLIC/README, re-verify the SIGNAL-tier pain-points. Only **observability is VERIFIED 3-0**; cross-agent knowledge, agent-comms, and context-recovery are SIGNAL (fine for *seeding* features; the pain-point sweep over-samples exactly the failures Aurora targets — selection skew, keep provenance attached).
3. **NASA-grade bar:** map Power-of-Ten / JPL / DO-178C practices onto acceptance pins (bounded everything, explicit assertions, no silent loss) — this is what the capture-first fixtures and parse gate operationalize.

---

## Recommended build order
**0 → 1 → 2**, then the moat fan-out **3 → 4 → 5** (4 can slot earlier — it's cheap and proves the convergence rule publicly). Slice 0 starts now (unanimous, prereg'd); slices 1–5 land under the formal ledger re-base once Daniel gates it.
