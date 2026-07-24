---
akashic_id: art_20260701_multi-agent-memory-recall-design-assessm_7807ba
akashic_sha: d4b3a8fdf0d9
status: fossil
type: design
date: 2026-07-01
title: "Multi-agent memory/recall: design assessment (2026-07-06)"
gist: "Prompted by Daniel's question (\"how do we give the right AI the right context at the right time?\") + DeepSeek's 5-point proposal. Assessed a"
tenant: solo
visibility: fleet
seats: []
category: [substrate, recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260701_multi-agent-memory-recall-design-assessm_7807ba -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Multi-agent memory/recall: design assessment (2026-07-06)

Prompted by Daniel's question ("how do we give the right AI the right context at the right
time?") + DeepSeek's 5-point proposal. Assessed against the GROUND TRUTH of the current code
(mapped 2026-07-06), not the guessed structure DeepSeek designed for.

## Ground truth of the current system
- **Lesson record** (`core/learning/learning_store.py`): stores `agent_id` as *source/provenance
  only*. No target/recipient, no role tags, no per-agent outcomes, no consumed-by, no visibility.
- **Ranking** (`core/primitives/ranker.py`): deterministic, agent-AGNOSTIC. 4 dims
  (relevance 0.4 / importance 0.2 / recency 0.2 / relationship 0.2). In `recall_at`, the requesting
  agent_id is used ONLY for lock-checking — never for scoring/filtering.
- **Usefulness** (`core/recall/funnel.py`): `value = (useful+helped)/surfaced`, credited GLOBALLY
  per lesson (summed across all agents/sessions). Current value ≈ **1%**. Triage buckets already
  exist: PROTECT / COST_NO_RETURN / NOISE_VOTED / WATCH / DORMANT / GHOSTS, plus
  `flips_corpus_gap` (a FAIL→SUCCESS flip that credited NO lesson = a corpus gap).
- **Faithfulness gate** (`core/primitives/faithfulness.py`): deterministic — every distilled line
  must carry a resolving source pointer + no fabricated numbers; else recall returns EMPTY
  ("silence beats fabrication"). A real strength; the right multi-agent safety property.
- **Cross-agent sharing**: only the Promoter (salient bus kinds → durable ledger, a LOG not a
  retrieval index) + per-instance AgentMemory (`mem:`, not shared). Narrative spine is per-session,
  NOT cross-agent chained.

## The reframe
DeepSeek's proposal optimizes the READER (5 heuristic scoring dims, recipient tags, session chains,
broadcast channels, visibility gates). But the system's own instrumentation says the bottleneck is
the CORPUS + precision, not reader sophistication — corpus lessons `recall_dissent_slice01`
("binding constraint is corpus content, not the reader") and `t3_stats_funnel_first_slice`
("instrument by reading records, not adding write paths"). Adding knobs to a 1%-value funnel mostly
adds mis-tuning surface.

## Verdict on the 5 ideas
1. **Agent tagging** — source exists; skip speculative *target* tags → do per-agent CREDIT instead.
2. **Multi-dim ranking** — risky on a corpus-limited system; adopt ONLY per-agent usefulness (measured).
3. **Cross-agent session chains** — real value for HANDOFFS only; medium build; partly served by the
   promoted ledger; defer.
4. **Proactive context broadcast** — ⚠️ DANGEROUS: it manufactures the ambient-context pollution that
   already derails the weak agent (E4). Prefer PULL from the promoted ledger over PUSH broadcasts
   (the stigmergy principle: read the environment, don't shout into it).
5. **Visibility/permission gates** — premature (DeepSeek agrees, Phase 4); ~4 agents, one trust domain.

## The answer to "right AI, right context, right time" (prioritized, Akashic-native)
- **"Right time" is already solved** — recall at the tool boundary, faithfulness-gated. Leave it.
- **1. Fix the corpus, not the reader (highest leverage, already instrumented).** Act on the funnel
  triage: merge/retire `COST_NO_RETURN`; mine `flips_corpus_gap` (succeeded-after-failing with NO
  lesson) as the source of NEW lessons. Attacks the 1% directly.
- **2. Per-agent CREDIT, not per-lesson TAGS.** Make the usefulness counter per-agent
  (`recall:use:<source>:<agent>`) so the system MEASURES which lessons help which agent instead of
  guessing an audience. Satisfies DeepSeek's own guardrail ("universal but must be tested across
  agents") the evidence way. Low effort, high alignment.
- **3. Role-context lives in the HAT, not the lesson.** DeepSeek's "role_tags + role alignment" IS
  the swappable-hats idea (Wave 3). A hat declares which categories/tracks it attends to; recall
  filters by the hat's scope. Declarative at the agent, not smeared across the corpus. The
  memory-context problem and the onboarding problem are the SAME problem — the hat solves both.

## Avoid
- Proactive broadcast (#4) — pollution risk. Pull, don't push.
- Heuristic multi-dim ranking (#2 as proposed) — tuning surface on a corpus-limited system.
- Visibility gates (#5) — premature.

## Convergences worth remembering
- Role-based context == **hats** (Wave 3 O5). Build it there, once.
- "Read the environment, don't broadcast" == the **stigmergy** steer from the actor/ROS/stigmergy
  research detour. Same principle, second domain.
- Per-agent credit == the evidence-driven ethos (measure autonomy/usefulness, don't assume it).
