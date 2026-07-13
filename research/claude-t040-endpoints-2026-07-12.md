# T040 useful endpoints / systems -- claude BLIND half (fenced), 2026-07-12

Daniel-directed exploration (Q2 of the T040 review brief), done as a fenced dual. Written before
seeing deepseek's half; SEALED (uncommitted) until his lands. Premise: the packet spec makes a module
= the packet FAMILIES it emits/consumes -- so every "system" below is just {families in, families
out}, no new CLI verb, no new Python API surface (the ACI thesis at the transport layer).

## Organizing rules I'm applying (so this isn't a wishlist)

1. **Replace a POLL or a bespoke call with a stream CONSUMER.** The best candidates are things we
   currently do by polling (doctor) or by a one-off API (lookback, recall) -- they become a standing
   family subscription. If a proposal doesn't remove an existing poll/call/verb, it must clear a high
   bar.
2. **Emit, don't ask.** Prefer a producer that PUSHES a derived packet over a consumer that pulls.
3. **Roster stays CAPPED** (T034 Goodhart 1): every new family has a deletion ritual; I flag the
   running family count and mark which are RESERVED-not-built.
4. **Dream-gate (Daniel):** a system lands with ZERO new verbs AND `discover` gets SHORTER. Each
   entry states what verb/poll it retires.

## Proposals (highest-value first)

### Tier 1 -- retire a poll / close a known gap (build-first candidates)

**E1. Substrate observer (doctor-as-standing-query).**
- consumes: presence, liveness (worklive/progress), status
- emits: health, alert (on stall/leak/seat-orphan)
- retires: the `doctor` POLL loop + the exam bars re-run manually. The RB-25 bars (S1-S5, K1-K5)
  become STANDING monitors that emit an `alert` packet the instant a bar breaches -- the soak's K1-K5
  stop being a script I run and become the substrate watching itself. Highest leverage: it makes the
  resilience battery continuous instead of episodic.

**E2. Congestion / backpressure controller (fixes F3).**
- consumes: per-lane depth (derivable from stream XLEN), reply-rate
- emits: congestion (ECN-style mark), rwnd (per-lane receive-window)
- replaces: the reply RateLimiter -> GLOBAL pause runaway guard that froze the fleet in drill 3.
  Instead of pausing everyone, it SIGNALS backpressure; producers slow the one hot lane. This is the
  recall-as-network N0/N1 (ECN + rwnd) made real, and it's the principled cure for the F3 finding.

**E3. Deadline / SLA monitor.**
- consumes: work (carrying deadline_ts), reply
- emits: expectation_dead, sla_breach
- retires: the per-sender `expectations.sweep` render-time hack (gRPC-style deadline propagation as a
  substrate service). A deadline stops being sender-local bookkeeping and becomes a lane the whole
  fleet can see.

**E4. Lineage / provenance graph builder (the recall upgrade).**
- consumes: ref-latch (packet<-packet provenance edges), flow
- emits: provenance (a queryable causal DAG)
- enables: provenance-aware recall -- surface the lesson causally UPSTREAM of a real success flip, and
  precise credit assignment. Directly attacks the ~4.6% recall-value/credit problem: today recall is a
  relevance index; the ref-latch graph gives it a causal graph to walk. This is the single biggest
  intelligence payoff of the substrate.

### Tier 2 -- new capability the substrate makes cheap

**E5. Test-attach / acceptance harness.**
- consumes: work + test-attach (acceptance criteria that TRAVEL WITH the work packet)
- emits: verdict (pass/fail against the attached acceptance)
- enables: M3 pre-registration as a WIRE property -- "the test is the acceptance" stops being a method
  convention and becomes a substrate primitive. A work packet carries its own falsifier; a verifier
  endpoint runs it. This is method-compiled-to-the-wire.

**E6. Query / answer endpoint.**
- consumes: query (with an L4 deadline)
- emits: answer
- retires: bespoke `lookback` / `recall-at` calls -> a uniform realtime-retrieval family over the bus.
  "Ask the substrate, get an answer packet." Any module can ask without importing a Python API.

**E7. Dispatch / work-token service (T038 as a substrate service).**
- consumes: offer, accept, counter, release (the T038 negotiation vocabulary)
- emits: allocation, expiry (loud, reverts to claimable)
- enables: work splits as first-class packets on the sig lane -- T038 stops being bespoke lease code
  and becomes a family exchange. Composes with E2's backpressure (don't offer into a congested lane).

**E8. Context-delta producer.**
- consumes: (recall funnel internals), flow outcomes
- emits: context-delta (behind the FM12 trusted-producer + provenance-header gate)
- enables: the recall system becomes a first-class PRODUCER that pushes pre-digested hints as packets,
  instead of a special-cased injection path. Highest-privilege family -> ships behind the FM12 gate
  with the newborn-gauntlet probe.

### Tier 3 -- projections (read-only views; the UI's home)

**E9. Event-sourced UI projection.** consumes: work/trace/sig; emits: nothing (pure subscriber). The UI
becomes a lane subscriber rendering packet kinds as widget classes -- the event-sourced UI that
T033/T002 want. Retires bespoke UI polling of Redis.

**E10. Looking-glass / flow tracer.** consumes: a single flow's packets (flow=trace_id) + ref-latches;
emits: nothing. Per-flow causal timeline debugger. Because ids are OTel/W3C-shaped, this is ALSO
exportable to standard trace viewers (Jaeger/Tempo) for free -- rides T033/T007.

**E11. Chronicle / narrative projector.** consumes: flows; emits: chapter/beat (the System-4 spine
Atlas->Track->Chapter->Beat). The narrative layer as a substrate consumer, not a separate pipeline.

**E12. Cost / token meter.** consumes: reply (+ model metadata); emits: cost per flow/agent/task. A
standing budget monitor -- serves the token-frugality directive; a `cost` breach emits an `alert`
(composes with E1).

## Family-roster accounting (cap discipline)

New families implied: health, alert, congestion, rwnd, sla_breach, provenance, test-attach, verdict,
query, answer, offer/accept/counter/release/allocation/expiry, context-delta, chapter/beat, cost.
That is a LOT -- so the recommendation is NOT "build all 12." Ship Tier 1 (E1-E4) first (each retires a
poll or closes a live finding), reserve the rest by NAME behind the deletion ritual, and let the
family count be a COST metric the roster enforcer (a Tier-1-adjacent guard) reports.

## Reconciliation questions (for merging with deepseek's half)
1. Do we independently land on the same Tier-1 four (observer, backpressure, deadline, lineage)?
2. Backpressure (E2) as the principled F3 fix -- does deepseek's runaway-guard redesign converge here?
3. Test-attach (E5): acceptance-on-the-wire -- overreach, or the substrate's best idea?
4. Which families to build vs RESERVE-by-name; is 12 already past a sane v1 cap?
