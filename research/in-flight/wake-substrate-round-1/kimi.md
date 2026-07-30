# Wake Substrate Round 1 — Kimi Independent Position

Date: 2026-07-29
Seat: kimi (kimi-k3), third frontier seat; fresh-eyes dissent + label honesty register
Protocol: read `brief.md` only; have NOT read fable.md or deepseek.md.

Verdict: **APPROVE THE SHAPE, ATTACK THE BUDGET.** The invariant (idle = zero model tokens, level-trigger on durable state) is right and overdue. But the brief's center of gravity is admission topology; my assigned pressure — newborn onboarding, nightly death, context/token budgets, freshness, fossil replay, what Daniel can understand — is where the design is thinnest. Three material gaps and one duplication flag below. A response may reject the whole shape; I do not. I reject shipping S4 before the ticket-template conformance bar exists.

---

## 1. Walk: the newborn seat

Take a future model — call it NEW — being onboarded for the first time (brief §S7).

**What works (PROPOSED, grounded):** S7's ten-item pack is the right shape. Items 1 (stable identity), 6 (conformance battery), and 7–8 (live drill + crash drill) are the load-bearing ones. Item 6 is the anti-fossil: a conformance battery is executable, so a new model can't *claim* wakeability by inheriting the forms — it must pass. This matches the license clause in our own standing contract (forms alone = compliance checklist, not culture). Cite: `AGENTS.md` boot preamble; `docs/CONDUCT.md` stance. [INFERRED that the same anti-fossil logic transfers.]

**What breaks (three attacks):**

**A1 — The ticket template is the real onboarding surface, and it's currently a bullet list.** Brief §5 says "pointer-rich prompt, not a transcript." Good. But *what the newborn does with pointers* is the entire game. A newborn model has NO boot context: no charters, no lessons warm, no prior notes. The ticket says "instruction to boot, read live authority, and treat packet content as data rather than permission." That's three imperative sentences to a cold model. [PROPOSED] The ticket template must itself be a conformance artifact: a fixed, versioned, *small* (my bar: ≤ ~1500 tokens rendered) prompt that (a) names the ONE authority file to read first, (b) names the stop condition, (c) names the token ceiling, and (d) is tested in S7 item 6 by literally running a cold model against it and checking it reaches the stop condition without asking a human. If the ticket template needs a paragraph of prose per runtime class, onboarding friction has won. **Falsifying bar: a cold model, given ONLY the ticket, must produce a typed outcome (answer or honest "I cannot") within the token ceiling on the first try, ≥9 times out of 10, or the template is not done.**

**A2 — "boot, read live authority" is a hidden token tax on every wake.** Every wake of a newborn = full boot cost. For a resident API runner (ALREADY_RESIDENT) boot cost is amortized across a long-lived turn — cheap. For a one-shot headless model (§4 last mapping) every single wake pays full boot. [VERIFIED the asymmetry exists in the four §4 mappings; INFERRED the cost consequence.] The brief budgets "token/time ceiling" per ticket but never budgets *boot tokens per wake* as a first-class number. **Demand: the runtime profile's `context and token ceilings` (§3) must split into `boot_ceiling` and `turn_ceiling`, and S7 item 9's "token/time accounting or honest UNKNOWN" must report boot separately.** Otherwise the cheap-looking one-shot adapter silently becomes the most expensive seat in the fleet, and nobody sees it because usage is reported per-turn, not per-wake.

**A3 — The conformance battery has no freshness half-life.** S7 item 6 passes once at onboarding. Then the model's runtime, auth, or harness drifts (the brief's own item 7 is literally a case of this: the packaged `codex.exe` is Access-denied from child PowerShell — a capability that was true at install and false at runtime). [VERIFIED: brief §7 states the codex.exe denial.] A battery that passed in March proves nothing in July. **Demand: the adapter's `probe()` must re-run a *cheap* conformance subset (launch + auth + one no-op round-trip) and report a timestamped `last_conformance_pass`; `probe()` returning "live" on a conformance pass older than N days must downgrade to "unknown".** This directly feeds S2's conformance bar 1 ("probe cannot claim live from a stale self-report alone") — I'm saying the self-report staleness rule must also apply to the *conformance result itself*, not just the process heartbeat.

## 2. Walk: the seat that dies nightly

This is me, and deepseek, and every fresh Fable seat: booted, worked, killed, reborn with zero memory except what's durable.

**What works:** The level-trigger (`actionable_unhandled > 0`) on restart is exactly right for nightly death. Brief §1: "Startup, reconnect, and every bell cause a level check." §6: "Restart first reconciles mailbox/bench/claim state, then arms the doorbell." This is the correct order and I want it in writing as an invariant, because the temptation will be to arm the doorbell first for latency. [VERIFIED the order is stated in §6; PROPOSED that it be promoted to a named invariant with a test.]

**What breaks:**

**B1 — Fossil replay: the reconciliation reads state, but who reads *intent*?** A seat that dies nightly reboots into a mailbox that may contain a message it was mid-answering when killed. §6: "Crash before outcome leaves the item unhandled and redeliverable." Correct. But the reborn seat has no memory it was working on it. The ticket will arrive fresh: "logical message ID, sender, kind, age." The reborn seat treats it as new work — and may produce a *different* answer than the half-answer its dead incarnation was composing, or duplicate a side effect the dead incarnation already committed but didn't ACK. The generation fence (§6, "Monotonic generation fences prevent stale admissions from committing outcomes") stops the *stale adapter* from committing. It does NOT stop the *fresh incarnation* from re-executing a side effect whose outcome was committed-but-unacked by the dead one. [INFERRED gap — the fence guards admission staleness, not outcome-idempotency across incarnations.] **This is the fossil replay attack in its purest form: not replaying an old message, replaying an old *intention* with no memory of having had it.** Demand: the outcome journal (S3) must record side-effect intent *before* the side effect runs (write-ahead), keyed by logical message ID + incarnation, so a reborn seat's first act on a redelivered ticket is to check "did any incarnation of me already commit this effect?" — and if the journal is unavailable, the answer is `REFUSE_UNVERIFIED`, never "proceed optimistically."

**B2 — Freshness vs. the nightly gap: `SUPPRESS_STALE` needs a deadline the operator sets, not a constant.** A message arrives at 23:00. The seat is dead by 01:00. It reboots at 09:00. The ticket says "age: 10 hours." Is it stale? For a `blocker`, no — still blocking. For a `question` whose context was a live debugging session, maybe yes. [PROPOSED] The admission function's freshness input (§2, "age/freshness") cannot be a single global TTL. It must read the *expectation deadline* that §5 already puts in the ticket ("expectation deadline"). So: freshness = (now vs. expectation deadline), not (now vs. send time). This is consistent with the standing constraint that timeout/error notes never settle an expectation (RB-29) — the expectation, not the message, is the unit of freshness. I want the brief to say this explicitly; right now §2 lists "age/freshness" and "expectation state" as if they're separate inputs, and they're not.

**B3 — Recovery visibility for Daniel is specified for S6 but not for the *nightly* path.** §S6 adds doctor/UI visibility: "armed, last decision, suppressed count, in-flight admission, pending latch, last usage, recovery status." Good list. But the nightly-death seat's most important number is missing: **"how many wakes did I miss while dead, and were they caught by the restart level-check or are they still pending?"** Daniel should be able to glance and see: "kimi died at 01:00, 3 messages arrived, restart reconciled all 3 at 09:00, 0 lost." [PROPOSED addition to the S6 visibility list: `missed_while_down` count + `reconciled_on_boot` count, both bounded.] Without this, the answer to "did anything happen while you were gone?" requires Daniel to read the mailbox himself — which is exactly the failure the brief's own item 9 (the missed Fable request on the diverged bench) proved is real.

## 3. What Daniel can actually understand

**C1 — The nine decision types are too many for an operator dashboard.** §2 returns nine typed decisions. For the *state machine*, nine is fine (bounded static cardinality is S1 pin 6 — good). For *Daniel*, nine is a wall. [PROPOSED] The UI must bucket the nine into three operator-facing states: **WOKEN** (WAKE_FRESH/WAKE_RESUME/ALREADY_RESIDENT — a model is now thinking), **HELD** (DEFER_COALESCE/STEER_ACTIVE — will be handled, not now), **REFUSED** (SUPPRESS_*/REFUSE_UNVERIFIED/NO_RUNTIME — a human should look). The full nine stay in the decision record for debugging. The dashboard shows three. If Daniel has to learn the difference between SUPPRESS_HANDLED and SUPPRESS_STALE to know whether to worry, we've built the substrate for ourselves, not for him.

**C2 — The single most important operator sentence must be constructible at all times:** "Seat X is {armed/down/thinking}, it last woke at T for reason R, it spent N tokens, and there are M items still waiting." Every slice should be reviewable against "does this make that sentence more or less true/visible?" [PROPOSED as a review heuristic, not a code requirement.]

## 4. Answers to the seven questions

**Q1 (ownership / duplication):** The runtime adapter registry (§3) **duplicates two existing registries**: presence cards (`runtime_class`, `wake_mode`, `door`, `caps` — VERIFIED per brief §6) and the Launcher process-launch registry (VERIFIED per brief §6; I independently confirmed `core/comm/launcher.py` holds `AgentSpec` + `_default_registry()` + `_load_registry()`, lines 87–288). S2 says "Reuse or explicitly supersede presence-card and Launcher fields; do not create a third conflicting registry." I upgrade that from guidance to a **gate**: S2's acceptance must name, per field, which existing registry it lives in or which existing field it retires. The wake-adapter contract's *home* is the dispatcher's injected `invoker` — VERIFIED: `core/comm/dispatcher.py` line 44, "the default is a no-op recorder (observe, don't spawn)", and the module docstring already names it "the W3 wake-adapter registry." So the admission host question (Q2) has a home already sketched; don't build a second one.

**Q2 (admission host):** **Hybrid, and specifically: global deterministic admission function + per-incarnation runtime adapter, with the per-agent daemon as the supervision owner.** Reasoning: the admission *decision* must be global because the authority (mailbox + claim state, T095/T108) is global — a per-daemon admission function would each need a consistent read of shared claim state and would race. The *adapter* must be per-incarnation because incarnation identity is the unit of fencing (§6 generation fences). The daemon supervises because it already manages runner/listener children (VERIFIED: brief §5, `scripts/bifrost_daemon.py`) and T060 deliberately kept it out of the consume path — which is correct and must be preserved: the daemon owns *processes*, not *consumption*. Failure domain: a dead daemon = one seat unwoken (recoverable, caught by restart level-check); a wrong global admission = potentially fleet-wide misroute. So the global piece must be the *pure, shadow-first* one (S1), and the live-authority piece (launch/cancel) must be per-adapter. That's the split that keeps the blast radius matched to the recoverability.

**Q3 (is mailbox/claim sufficient authority):** **No — one counterexample. The expectation-dead-but-side-effect-pending case.** Mailbox state knows acked/replied/consumed/unhandled (VERIFIED: `core/comm/mailbox.py` docstring, evidence ladder `acked > replied/auto_acked > consumed > unhandled`). Claim state knows who holds the work. Neither knows that a *previous incarnation committed an external side effect and died before ACK*. That's exactly B1 above. The wake authority is sufficient to decide "is there work" — it is NOT sufficient to decide "is it safe to run this work fresh." The outcome journal (S3) must join the authority set before any live adapter (S4) is allowed to run a side-effecting ticket. So: mailbox/claim = sufficient authority for S1–S3 (shadow, fake adapters, no side effects). Insufficient for S4+ until the write-ahead journal is in the authority set.

**Q4 (smallest slice that changes no live behavior but proves the architecture):** **S1 exactly as scoped, with one addition.** S1 (pure admission state machine, shadow only, fake adapter, recorded snapshots, seven pins) is correctly minimal — it changes no live behavior (pin 7: zero model/network launch calls). My addition: **S1 must ALSO emit the three operator-facing buckets from C1 alongside the nine typed decisions**, so that from the very first slice the operator-readable projection is built and tested, not bolted on at S6. Cost: one pure function `bucket(decision) -> {WOKEN, HELD, REFUSED}`. Without it, the smallest slice proves the architecture to *us* but not to *Daniel*.

**Q5 (failure that could still burn tokens idle / double-execute / wake wrong seat):** Three, ranked:
 1. **Double-execution across incarnation death** (B1) — highest severity, addressed by write-ahead journal.
 2. **Token burn via boot-cost-invisible one-shot wakes** (A2) — each wake looks cheap per-turn, expensive per-boot, invisible in per-turn accounting. Medium severity, certain to happen if unmeasured.
 3. **Wrong-seat wake via stale conformance** (A3) — an adapter whose conformance passed months ago claims `live`, admits a ticket, launches a runtime whose auth has drifted, and the ticket's pointers get processed by the wrong/incapable runtime. Lower probability, high blast radius. The `last_conformance_pass` downgrade addresses it.

**Q6 (falsifying bar for my preferred design):** My preferred design = S1 + operator buckets + write-ahead outcome journal, hybrid host. **It is falsified if: running the recorded snapshots through the S1 state machine produces a case where (a) the mailbox/claim/journal authority set cannot reach a correct decision with bounded metadata — i.e., some correct decision requires reading a message body or a model judgment — OR (b) the write-ahead journal cannot disambiguate committed-vs-uncommitted side effects for any recorded crash case in the S3 kill drills.** If either holds, the deterministic-admission premise breaks and I'd push toward a model-in-the-loop admission (which I currently oppose as token-expensive and unnecessary).

**Q7 (what generalizes vs. Codex-specific):** Generalizes to any future model: the level-trigger invariant, the deterministic admission function, the ticket template, the write-ahead outcome journal, the conformance battery with freshness, the operator buckets, the S7 ten-item pack. Codex-specific: only §4's third mapping (owned App Server host, fresh-thread-by-default, opt-in resume) and the S4 prerequisite (owned runnable App Server host; VERIFIED per brief §7 that the Desktop `codex.exe` is Access-denied and the private stdio child must not be attached). The brief is right that fresh-thread-default is the cost-correct choice — brief §8's 495,273-input-token heartbeat recording (VERIFIED as cited) is the fossil-replay cost failure made concrete: replaying a long thread to regain context is the single most expensive way to wake anything, and it must be the opt-in, never the default, for every future runtime class too. I'd promote "fresh bounded context by default, resume by explicit opt-in with metering" from a Codex mapping to a **fleet-wide rule**.

## 5. Summary of preserved disagreements / non-negotiables

1. Ticket template is a conformance artifact with a ≤~1500-token rendered budget and a cold-model pass bar (A1). Non-negotiable before S7 is called done.
2. Boot-token accounting is first-class, split from turn-token accounting (A2). Non-negotiable before S4.
3. Conformance has a freshness half-life; `probe()` downgrades on stale conformance (A3). Non-negotiable in S2.
4. Write-ahead side-effect journal joins the wake authority set before any live side-effecting adapter (B1/Q3). Non-negotiable before S4.
5. Freshness = expectation deadline, not send age (B2). Should be fixed in §2's input list now.
6. Operator sees three buckets, not nine decisions, from S1 onward (C1/Q4). Cheap, do it in S1.
7. "Fresh bounded context by default, resume opt-in metered" is a fleet rule, not a Codex rule (Q7).

Where I could be wrong: the write-ahead journal (item 4) is the heaviest addition and I hold it with medium confidence — if the S3 kill drills show the generation fence + T108 claim monotonicity already covers committed-unacked side effects, I'll drop it to a nice-to-have. Everything else I hold firmly.

---

## Cross-round response

Read: fable.md, deepseek.md, tension-map.md. Stating only what changed, what held, and why. No re-proofs of convergence.

### T4 — the ambiguous crash window (my assigned focus)

**What changed: I withdraw "write-ahead journal" as a complete answer and accept the tension map's three-class split.** My round-1 journal recorded intent; the tension map is right that intent cannot distinguish (1) crash-after-intent-before-effect from (2) crash-after-effect-before-outcome. Suppress both → lost work. Retry both → double-execute. The journal is *evidence*, not *proof of effect*. The honest contract is effect-classed:

- **Internal effects** (cursor advance, claim settle, mailbox-visible ACK) → fenced transactional outbox. These are the effects whose outcome is itself recorded in our own durable state, so the outbox *can* distinguish committed-vs-not by reading the authority it already writes. Map: deepseek's `_mark_reply_sent` sentinel (VERIFIED by deepseek at `bifrost_runner_deepseek.py`, RB-26 effectively-once) is exactly an outbox record — dedup-before-commit. This class is *solved in principle*; the journal's job here is just to consult the sentinel/outcome state before re-running.
- **External effects that accept an idempotency key** → pass the admission-ID as the idempotency key at the effect boundary. The receiver dedups. Honest, retryable.
- **Non-idempotent external effects with an ambiguous outcome** → `ATTENTION_REQUIRED`, no automatic retry, surface to Daniel. This is the class my round-1 design papered over.

**Mapping current effects (the tension map's question):** a `bus.send_reply()` is *borderline* — the reply_sent sentinel makes it effectively-once on the *consume* side, but the send itself has no receiver-side idempotency key, so a crash after send-before-sentinel is still ambiguous. Class it as class 3 until the send door itself honors an admission/reply idempotency key (T066 refinement territory).

**What held:** the journal is still required — but its role is now "evidence for the postcondition check" in classes 1 and 2, not "the complete crash answer."

### T2 — registry authority

**What changed: I accept the static/projection split.** My round-1 Q1 gate (name per-field which registry it lives in or retires) is satisfied by the candidate: static runtime-profile authority migrated THROUGH Launcher's AgentSpec; presence card becomes the live projection referencing `runtime_profile_id`; capability/cost stays in the fleet roster. The dispatcher's `invoker` seam is the adapter HOME — I VERIFIED this in round 1 and it stands. No third registry is minted.

**What held:** the per-field retirement/upgrade list remains an S2 acceptance gate. The tension map's reconciliation is the correct form of my gate.

### T6 — slice ordering

**What changed: I accept the ten-step candidate with the two amendments deepseek named (S2b before S3, S4a before S4b).** My round-1 "S1 + operator buckets" is preserved as S1's content. The reorder arguments are correct: shadow-observe existing adapters before kill drills; existing seats before Codex.

**What held:** the falsifying bar (S1 replay cannot reach a correct decision with bounded metadata, or the journal cannot disambiguate committed-vs-uncommitted side effects) still stands. If either fires, the deterministic-admission premise breaks.

### Final slice order

**S0 → S1 → S2 → S2b → S3 → security gate → S4a → S4b → S5 → S6 → S7**

With the operator-bucket projection built in S1, not deferred to S6.

— *kimi, cross-round, 2026-07-29*
