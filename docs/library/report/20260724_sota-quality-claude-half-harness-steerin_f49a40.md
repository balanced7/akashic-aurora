---
akashic_id: art_20260724_sota-quality-claude-half-harness-steerin_f49a40
akashic_sha: 2f628f6b92b8
status: current
type: report
arc: sota-quality
date: 2026-07-24
title: sota-quality-claude-half-harness-steering
gist: "Claude T105 half: context-quality consensus, structured-brief SOTA, stance drift now measured (30pct/8-12 turns), memory shape at-SOTA; slices S1-S6 + 3 tool wishes"
tenant: solo
visibility: fleet
seats: [claude]
category: [frontier, recall, migration]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_sota-agentic-quality-research-round_8eb04e
    rel: discusses
created: "2026-07-24T00:42:53"
updated: "2026-07-24T00:42:53"
---
<!-- GENERATED PROJECTION of art_20260724_sota-quality-claude-half-harness-steerin_f49a40 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# sota-quality-claude-half-harness-steering

CLAUDE'S HALF -- T105 SOTA sweep, HARNESS/STEERING lens (web-grounded 2026-07-24 night). Method: 5 web sweeps (context engineering, agent memory, multi-agent orchestration, coding-agent quality practice, persona drift). Honesty bar: SEARCH-GROUNDED -- claims ride result summaries + abstracts, not deep-reads; numeric claims are single-source and labeled. Sibling halves: deepseek (generation-side), kimi (verification-side) -- boundaries respected.

## FINDING 1 -- Context quality beats prompt quality (the 2026 consensus)
The field converged on "context engineering": output quality is bottlenecked by what rides the window, not by prompt wording. Named failure classes: context poisoning, context overload/rot, lost-in-the-middle. Canonical practices: minimal-first (add only on insufficiency), context ROUTING (each agent gets only its slice), history compaction, retrieval-over-frontloading.
WHERE WE STAND: ahead on retrieval (recall funnel + value-rate 6.3% is a real measurement most shops lack), aligned on fixed-budget boot (T074 primer). GAPS: (a) no mid-session compaction ritual -- long conductor sessions accumulate rot unmeasured; (b) no poisoning guard -- a wrong note propagates until superseded (A2 helps); (c) T071-R1 relevance budget is EXACTLY the SOTA move and sits claimed-unbuilt.
SLICE CANDIDATES: S1 mid-session compaction verb (distill working context -> note, cadence or size-triggered). S2 prioritize T071-R1 (already designed, now frontier-affirmed).

## FINDING 2 -- Structured briefs are the delegation SOTA; free-form delegation is a documented failure mode
Production consensus (5 major vendors converged): orchestrator owns full context, subagents get ROLE-SCOPED context via structured briefs -- objective / format / tools / boundaries -- and return compressed summaries. Passing full history to every subagent is named counterproductive.
WHERE WE STAND: the Conductor's doctrine (intent-first, verbatim charter, calibrated question) independently matches this and adds the verbatim-words law the SOTA lacks. GAP: our briefs vary in DELIVERABLE-SHAPE and BOUNDARIES slots (tonight's briefs carried them; not all do).
SLICE CANDIDATE: S3 brief scaffold in the door -- doc new --type brief emits the five-slot skeleton (intent-verbatim / ground / deliverable-shape / boundaries / calibrated-question). Cheap, ratchets every future round.

## FINDING 3 -- Stance drift is now a measured phenomenon (Daniel's "stance recall," named by the field)
Persona/stance self-consistency degrades >30% after 8-12 turns EVEN WITH CONTEXT INTACT (single-source benchmark claim; multiple 2025-26 papers agree on the direction). A recurring named failure: the agent forgets user-flagged constraints and confabulates agreements. Mitigations in the literature: episodic memory consolidation, drift-aware routing, ADAPTIVE BEHAVIORAL ANCHORING, snapshot-then-probe measurement (ContextEcho), attractor-state analysis.
WHERE WE STAND: we independently invented behavioral anchoring (boot stance block + conductor_* lessons riding recall-at + kata scorer). The field adds what we lack: MEASUREMENT and RE-ANCHORING CADENCE. We anchor once at boot and never re-probe.
SLICE CANDIDATES: S4 stance re-anchor -- re-inject the stance block on a turn-count or wake cadence (recall-at already has the injection rail). S5 drift probe in the kata scorer -- score stance adherence per session window, trend it in stats (gives Daniel the drift curve, not vibes).

## FINDING 4 -- Memory architecture: we are at the SOTA shape; retrieval blending is the gap
2026 memory surveys decompose agent memory into factual / experiential / working tiers with multi-strategy retrieval (semantic + keyword + graph + temporal, reranked) and name STALENESS the top open problem. Our stack maps 1:1 (atoms=factual, lessons=experiential, notes=working; knowledge_map=graph; supersession law + [STALE] labels = staleness discipline). The gap is retrieval BLENDING: our recall is keyword+category; semantic/temporal rerank is parked (N0-N7 transport, T094 adaptive rules).
SLICE CANDIDATE: S6 fold the multi-strategy-rerank frame into T094's next round (design exists; the frontier just affirmed its direction).

## FINDING 5 (boundary line -- kimi's half owns depth here)
Industry practice: treat agent output like a junior dev's PR -- same review, same CI gates; token efficiency (fewer retries, stronger first pass) dominates sticker price. Our fence/pins/suite-baseline already embody this; deferring detail to kimi's half.

## TOOLS WISHLIST (mine, felt friction tonight)
1. Stance-drift probe (S5) -- the kata scorer grows a per-window stance score; surfaces in stats.
2. Brief scaffold (S3) -- the five-slot skeleton in doc new.
3. Compaction verb (S1) -- "distill my working state to a note" one-liner for long conductor sessions.

## SOURCES (search-surfaced; deep-reads pending if any slice is gated)
- mem0.ai/blog/context-engineering-ai-agents-guide · blog.getbind.co context-engineering 2026 guide · ivern.ai context-window optimization 2026
- mem0.ai state-of-ai-agent-memory-2026 · cognee.ai memory frameworks · arxiv 2603.14212 (memory as asset) · Agent-Memory-Paper-List survey
- digitalapplied.com 5-orchestration-patterns · beam.ai orchestration patterns · niteagent.com multi-agent production 2026 · addyosmani.com code-agent-orchestra
- faros.ai / firecrawl.dev / teamday.ai coding-agent 2026 practice roundups
- emergentmind.com persona-drift + persona-collapse · arxiv 2605.24279 (ContextEcho) · arxiv 2601.04170 (Agent Drift) · arxiv 2606.30571 (attractor states)
