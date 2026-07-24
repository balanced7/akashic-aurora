---
akashic_id: art_20260711_gpt-retrieval-v2-vision-verbatim-via-dan_46a918
akashic_sha: e5da6fb5b2a2
status: draft
type: report
date: 2026-07-11
title: "GPT retrieval-v2 vision (verbatim, via Daniel) -- context transformation over similarity"
gist: "# GPT retrieval-v2 vision (verbatim, via Daniel) -- context transformation over similarity Provenance: Daniel-relayed 2026-07-11 ~01:15; pre"
tenant: solo
visibility: fleet
seats: []
category: [recall, wiki]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T01:14:02"
updated: "2026-07-11T01:14:02"
---
<!-- GENERATED PROJECTION of art_20260711_gpt-retrieval-v2-vision-verbatim-via-dan_46a918 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# GPT retrieval-v2 vision (verbatim, via Daniel) -- context transformation over similarity

# GPT retrieval-v2 vision (verbatim, via Daniel) -- context transformation over similarity

Provenance: Daniel-relayed 2026-07-11 ~01:15; preserved verbatim per M6. Ledger: T032
(proposed). Claude's built-vs-new triage rides in the T032 acceptance: a substantial
fraction of this describes SHIPPED Aurora systems (the funnel's outcome-weighted credit
loop, the L1-L3 cache hierarchy concept, anti-pattern lessons, recall-AT-ACTION
triggering, notes-as-decision-lineage) -- the genuinely new axes are the explicit
intent/obligation layer, the policy-engine seam, numeric confidence on decisions, and
proactive violation warnings. GPT's closing line independently restates the project
thesis: "the product is not the memory. The product is the measurement loop."

---

Given the direction Akashic Aurora has been moving, I think the biggest application of
the "new approach" to context retrieval is this: stop thinking of retrieval as finding
information. Start thinking of retrieval as performing a context transformation.

Your system is already close to this. The mistake most memory systems make is: "User
asks X -> search memory -> inject relevant chunks." Aurora's stronger framing is:
"Current state + intent -> determine what knowledge transformation is required ->
construct the minimum context state that improves the decision."

I would evolve the retrieval pipeline into: Raw Experience -> Event Ledger (immutable)
-> Chapter Formation -> Lesson Extraction -> Knowledge Graph / Relationships ->
Retrieval Planning -> Context Assembly -> Agent Action -> Outcome Measurement ->
Credit Assignment -> Knowledge Updates. The retrieval planner becomes the intelligence
layer.

## 1. Replace similarity retrieval with "context obligation"

The question should not be "what memories are similar to this prompt?" It should be:
"What does this agent need to know to avoid known failure modes while completing this
task?" Example: "Refactor authentication module." A vector database sees old auth
discussions, code snippets, security notes. A context obligation engine asks: what are
the risks? (breaking API contracts, violating architecture boundaries, repeating
previous mistakes, ignoring project conventions) -- then retrieves Required Context
(architecture constraints, previous auth failures, naming conventions, tests that
caught regressions, decisions still active) vs Optional Context (old implementation
details, exploratory notes). This is much closer to how a senior engineer operates.

## 2. Make retrieval a "policy decision"

Every retrieval passes through a policy engine: intent -> need architecture? need
historical precedent? need failure memory? need implementation details? Instead of
query -> embedding -> top-k, you get intent -> retrieval strategy -> evidence
selection. The embedding becomes a tool, not the brain.

## 3. Use the CPU cache analogy more aggressively

Formalize: L0 Working Context Cache (current file, current bug, active constraints);
L1 Chapter Cache (recent coherent experiences); L2 Knowledge Graph (stable
relationships, "this naming convention exists because X"); L3 Archive (raw evidence,
old conversations, discarded approaches). Retrieval always attempts the smallest cache
level first. The agent should not search the ocean when the answer is already in RAM.

## 4. Add "retrieval confidence" based on outcome history

Most systems ask "how confident are we this memory is relevant?" Aurora should ask:
"Historically, did this class of memory improve outcomes?" Example: a lesson retrieved
47 times, helpful 39, neutral 6, harmful 2 -> confidence 83%. Retrieval becomes
self-optimizing: the system learns which kinds of memories are valuable.

## 5. Make "negative knowledge" first class

Not "here is what worked" but "do not do this again." The ledger architecture is
perfect for this: lesson, origin, evidence, confidence -- and when a similar action
appears: "potential violation detected: previous failures indicate this pattern causes
drift." That is much closer to engineering memory.

## 6. The biggest architectural shift: retrieve decisions, not documents

A document-oriented memory system retrieves text. An engineering memory system
retrieves decision lineage. Instead of "README.md chunk 143": Decision ("use
append-only ledger"), Why (avoid destructive forgetting), Evidence (experiment #17),
Rejected alternatives (mutable summaries), Current confidence (0.91). This fits the
"names must not lie" philosophy extremely well.

## Retrieval v2 milestone

1. Intent classifier -- what kind of context does this task require?
2. Context obligation generator -- what must be known before acting?
3. Cache hierarchy selector -- where should we look first?
4. Outcome-weighted ranking -- has this type of memory actually helped?
5. Evidence-backed injection -- every injected memory has provenance.

That would turn Aurora from a "better memory system" into something closer to an agent
cognitive architecture. The interesting part is that this also aligns with your
existing thesis: the product is not the memory. The product is the measurement loop
that discovers what context actually changes behavior. That is the piece most AI
memory systems still do not have.
