---
akashic_id: art_20260709_integration-plan-a-unified-agent-memory_a58608
akashic_sha: bcc69d354ba1
status: fossil
type: design
date: 2026-07-09
title: "Integration plan: a unified agent-memory layer"
gist: "How to fold the richer learning model (`learning/store.py`) into our system in the best way, refined by the literature and practitioner fail"
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_integration-plan-a-unified-agent-memory_a58608 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Integration plan: a unified agent-memory layer

How to fold the richer learning model (`learning/store.py`) into our system in
the best way, refined by the literature and practitioner failure modes in the
[analysis](learning-memory-analysis.md). Status: PROPOSED — not yet started.

## Design principles (each traces to a practitioner lesson)

1. **Map memory types onto the two primitives we already have** — no new storage
   tech. Episodic → `Ledger` (append-only "what happened"). Semantic + procedural
   → `Store` (curated, supersedable "what is true / what works"). *(Our State-vs-
   Events split already is the taxonomy.)*
2. **Everything persists through `HybridStore`/`Ledger`** — so memory survives
   Redis being down (fixes the Redis-only gap) and degrades gracefully.
3. **Distill, don't just store** (Reflexion's weakness). Raw reflections/experiences
   are episodic; value comes from consolidating them into reusable semantic lessons.
4. **Guard distilled memory** (catastrophic-bad-reflection lesson): every semantic
   memory carries `confidence`, `provenance` (which experiences evidenced it), and
   is **supersedable**. A **writer→critic gate** validates a consolidation before it
   is committed (checks data loss / hallucination / conflict). Never auto-trust.
5. **Temporal correctness**: timestamps on everything + an explicit `supersedes`
   relationship (reuse our 66-type relationship vocabulary) so changed facts retire
   old ones instead of contradicting them.
6. **Importance + decay retrieval** (Generative Agents): score = relevance ×
   importance × recency. Importance (1–5) set at write; vital facts never expire;
   trivia decays. Start keyword-based with a clean seam for embeddings later.
7. **Keep ephemera out**: a session-only tier that consolidation ignores.
8. **Learn from failure first** (failures outnumber successes) — keep the existing
   `log_failure` bias.
9. **Multi-agent dimension** (we are not a single-user assistant): memory is either
   per-agent or shared; dedup shared lessons across agents.
10. **Consolidation feeds `chronicles/`** — the curated highlights layer is the
    *output* of the episodic→semantic loop. Raw ledger → writer→critic → chronicle.

## Target shape

```
AgentMemory  (facade — the one thing agents/coordinator call)
  ├─ episodic   -> Ledger   : experiences, raw reflections (append-only, decays)
  ├─ semantic   -> Store    : decisions/ADRs + distilled lessons (curated, superseded)
  ├─ procedural -> Store    : approaches per component (+ success/failure counts)
  └─ consolidate(): writer->critic distillation  episodic -> semantic -> chronicles/
retrieval: get_context() = relevance x importance x recency over the above
```

This resolves the duplicate-`LearningStore` collision: the simple
experiment-signal store stays as-is for signals; this becomes the richer
`AgentMemory` layer beside it (final naming TBD — applies genus/species rule).

## Phased plan (each phase independently shippable + verifiable)

- **Phase A — Foundation fit (coherence, no new behavior). ✅ DONE (2026-06-19).**
  Ported `learning/store.py` to `core/learning/agent_memory.py` as `AgentMemory`,
  persisting through a `Store` (Hybrid) — gains file durability + dual-write +
  fail-fast. Distinct name (`AgentMemory`) + namespace (`mem:`) resolves the
  collision with the experiment-signal `LearningStore` (`learn:`). Added the
  sorted-set ops the model needs (`zrangebyscore`/`zcard`/`zremrangebyrank`) to the
  `Store` primitive (a real `zremrangebyrank` rank-math bug was found and fixed).
  Orphaned `learning/store.py` + `learning/session_briefing.py` retired.
  *Verified: `tests/test_agent_memory.py` — full round-trip with Redis down,
  including durability-across-reload.* (`session_briefing.py`'s markdown-summary
  idea is a precursor to Phase D consolidation — preserved as a note here.)
- **Phase B — Memory model + temporal fields.** Formalize episodic/semantic/
  procedural placement; add `importance`, `confidence`, `provenance`, `supersedes`,
  timestamps. *Verify: a superseded decision stops surfacing; provenance links hold.*
- **Phase C — Retrieval upgrade.** Composite relevance × importance × recency with
  decay; embeddings seam left open. *Verify: fresh/important memories outrank stale.*
- **Phase D — Guarded consolidation (the chronicle loop).** Periodic writer→critic
  distillation of episodic → semantic lessons, committing curated output to
  `chronicles/`, with confidence + provenance + supersession. *Verify: critic
  rejects a lossy/hallucinated consolidation; bad lessons are retirable.*
- **Phase E — Multi-agent memory.** Per-agent vs shared scoping; dedup shared
  lessons. *Verify: two agents' memories stay isolated unless promoted to shared.*

## Open decisions before building
- Final naming for the memory layer (ties to the deferred `learning/store.py`
  decision — see memory `open-decision-learning-store-vision`).
- Embeddings now or later (Phase C seam vs. real vectors).
- Consolidation cadence + which LLM runs the writer/critic.
- Whether `chronicles/` becomes a generated artifact (recommended) vs hand-curated.
