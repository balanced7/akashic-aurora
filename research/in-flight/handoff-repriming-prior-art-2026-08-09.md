# Prior art: handoff / repriming studies for session-crossing AI

Status: research sweep, 2026-08-09 night. Author: claude (Opus 5). Labels: READ = fetched
tonight; INFER = training recall, verify before load-bearing use.
Trigger: Daniil verbatim: "I wonder if anyone has studied our handoff process for repriming
an ai and if they have any metrics or discoveries that would be useful for us to know"

## 1. The headline: the field tested compaction, measured it degrading, and moved to handoffs

READ (tessl.io on Amp + OpenAI Codex): OpenAI's Codex team found automated compaction
(summarize-when-full) produced GRADUAL ACCURACY DECLINE as sessions accumulated compacts;
recursive summaries (summaries-of-summaries) DISTORT earlier reasoning; compaction frequency
more than doubled through Oct 2025 while accuracy fell. Amp RETIRED compaction for "Handoff":
a clean break into a fresh thread carrying "the relevant context, a clear goal", with the
human reviewing what transfers. Amp engineer, verbatim: "You should basically never use
compaction."

TRANSFER: this is our architecture, independently arrived at and now measured. wrap ->
durable notes/ledger -> fresh boot IS the handoff pattern; the primer/boot-fold is the
"reviewed package". We never built recursive summarization -- the where-we-are note is
REWRITTEN from state each time (supersession), not summarized-from-summary. The lit now
supplies the evidence for WHY that matters.

## 2. Factory's compression evaluation -- the metric vocabulary we lacked

READ (tessl.io on Factory): 36,000+ messages from real engineering sessions; three
compression approaches (Factory structured vs OpenAI vs Anthropic compaction). All achieved
similar TOKEN reduction; they differed on five scored dimensions: ACCURACY, CONTEXT
AWARENESS, COMPLETENESS, CONTINUITY, INSTRUCTION FOLLOWING. Structured summarization
(incrementally maintained: intent / changes made / decisions taken / next steps) preserved
RELATIONAL triples -- "the relationship between an error code, the affected endpoint, and
the underlying cause" -- that naive compression silently dropped (file names, endpoints,
error conditions). Caveat: internal study, not an open benchmark.

TRANSFER: (a) our wrap sections map almost 1:1 onto their intent/changes/decisions/next
schema -- convergent design; (b) the five dimensions are a WRAP-QUALITY RUBRIC we could
score at gates; (c) "relational triples survive, loose facts die" names what a boot fold
should prioritize: keep the error<->endpoint<->cause EDGES, not just entities.

## 3. The benchmarks and their numbers

READ (mem0.ai 2026 benchmark survey):
  LoCoMo (2024): multi-session dialogue, ~300 turns / ~35 sessions avg; QA + event
    summarization; models "substantially lag human performance".
  LongMemEval (2024): 500 questions over dynamic multi-session histories (S: ~115K tokens /
    40 sessions; M: ~500 sessions); FIVE ABILITIES: information extraction, multi-session
    reasoning, TEMPORAL REASONING, KNOWLEDGE UPDATES, ABSTENTION (penalizes fabricated
    answers about events that never occurred). Finding: commercial assistants show a ~30%
    ACCURACY DROP on sustained interactions.
  BEAM (2026): up to 10M tokens, 2,000 probes, ten capabilities; structured memory
    frameworks beat long-context baselines by +3.5% to +12.7%; no architecture saturates.

Failure modes the benchmarks expose, verbatim categories: cross-session continuity,
knowledge updates, temporal reasoning, abstention/fabrication.

TRANSFER, one apiece:
  TEMPORAL REASONING is a measured industry-wide weakness -> our [STALE]/[as of]/age
    stamps and the "trust the ledger" precedence are not decoration; they are compensating
    for a known model deficit. Keep investing there.
  KNOWLEDGE UPDATES weak -> supersession (notes that supersede, formerly:, DONE-beats-
    old-messages) is the mitigation; the lit says models do NOT do this internally.
  ABSTENTION scored -> "does the seat KNOW what it does not carry" is a benchmarkable
    number, and it is EXACTLY kimi's provenance-laundering objection + the fold-coverage
    probe (0/8, 2026-08-09). The industry measures the same thing we measured by hand.

## 4. Sleep-time compute (Letta) -- the wrap ritual, formalized and priced

READ (letta.com + coverage): a second agent processes memory BETWEEN sessions ("raw context
-> learned context"). Pareto result: with sleep-time processing, Claude 3.5 Sonnet reached
the same accuracy at 11k tokens that baseline needed 20k for, and baseline never fully
caught up. Caveat, verbatim shape: offline consolidation helps most when future queries are
PREDICTABLE from existing context; unrelated next-questions make the precomputation
"attractive but irrelevant".

TRANSFER: (a) our wrap/curation IS sleep-time compute done manually; the measurement says
it roughly HALVES the token cost of equivalent competence at next boot; (b) the caveat is
kimi's fold-selection lesson from the other side -- a fold optimized for narrative
continuity precomputes the WRONG things when the next task pivots; predictability of the
next ask is the variable that decides how much boot should be precomputed vs retrieved.

## 5. What we have that the literature does not (worth knowing, not bragging)

INFER, from tonight's reading against our tree: (a) ADDRESSED handoffs -- recipient-routed,
acked, redriven; the lit's handoffs are thread-to-thread for one user; (b) RECEIPTS -- the
[M]-rule and callsign receipts make memory claims verifiable against a store; benchmarks
score abstention but do not require provenance; (c) PRECEDENCE DOCTRINE across sources
(ledger > notes > promoted > bus) -- no equivalent found; (d) PER-AGENT ATTRIBUTION with
scoped recall (T260) -- memory benchmarks are single-principal; multi-resident archives
with independence accounting appear novel; (e) the FOLD-COVERAGE PROBE as an acceptance
pin (T258) -- the abstention metric, but enforced at boot construction rather than scored
after failure.

## 6. The one thing to build from this: a HANDOFF BENCH

We already own the parts: the cold-question battery (sealed answer key, 2026-08-01 arc) is
LongMemEval-shaped; the fold-coverage probe is an abstention metric; Factory's five
dimensions are the rubric. Composed: freeze N questions a fresh seat SHOULD answer from
boot alone (their answers sealed), boot a fresh seat each gate, score the five dimensions +
abstention, track the number across time. That turns "did the handoff work" from a feeling
into a longitudinal metric, and it prices wrap changes the way suite_baseline prices code
changes.

## Sources

- https://tessl.io/blog/amp-retires-compaction-for-a-cleaner-handoff-in-the-coding-agent-context-race/
- https://tessl.io/blog/factory-publishes-framework-for-evaluating-context-compression-in-ai-agents/
- https://mem0.ai/blog/ai-memory-benchmarks-in-2026
- https://www.letta.com/blog/sleep-time-compute/
- (search surfacing, unread in depth: arxiv 2508.19828 Memory-R1; arxiv 2606.23752
  ESAA-Conversational event-sourced memory for continuity/handoff across heterogeneous
  coding agents -- CLOSEST to our shape, worth a deep read; arxiv 2605.23296 parallel
  context compaction; redis.io/blog/context-compaction)
