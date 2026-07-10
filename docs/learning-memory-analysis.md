# Agent Memory: analysis of `learning/store.py` + prior-art research

Status: historical  (2026-07-09, P4: Research; integration plan supersedes)

Research date: 2026-06-19. Purpose: evaluate the richer learning model
(`learning/store.py`) against the literature and real-world practitioner
experience, to refine how we integrate it. See the companion
[integration plan](learning-memory-integration-plan.md).

## 1. What `learning/store.py` is

It is a **multi-type agent-memory system** that independently mirrors the
canonical academic taxonomy (CoALA — Cognitive Architectures for Language
Agents). Mapping:

| `learning/store.py` | Memory type (CoALA) | Captures |
|---------------------|---------------------|----------|
| `Decision` (ADR-style) | Semantic | durable facts/rules ("we decided X because Y") |
| `Experience` (task/approach/result/success/score) | Episodic | what happened on one attempt |
| `Reflection` (what went wrong / what would help) | Reflexion loop | episodic → semantic self-improvement |
| `Approach` (per-component working/failed/in_progress) | Procedural | what works for a component |
| `get_context` / `get_similar` | Retrieval | assembling relevant memory before a task |

Four of four memory types the field converged on. The design instinct is sound;
the work is fitting it onto our foundation and adopting refinements the
literature has settled.

Note: it *does* use the fail-fast Redis connector (no 48s-hang risk). Its real
gap is that it is **Redis-only** — when Redis is down it returns empty, with no
file durability, unlike everything else we built on `HybridStore`.

## 2. Prior art (this has been built many times)

- **CoALA** — the reference taxonomy: working / episodic / semantic / procedural
  memory + reflection. Letta, Mem0, LangChain all use it as their foundation.
- **Reflexion** — exactly our `reflect()`: agents improve by reflecting on
  failures in language, no retraining.
- **Voyager** — `Approach` taken further: a *skill library* of verified
  procedures that grows through use.
- **Generative Agents** — `get_similar()` done right: retrieval scored by a
  composite **recency × importance × relevance**, not keyword overlap.
- **Production systems** — Mem0 (extract/consolidate salient memories, vector+graph),
  Letta (OS-style tiered memory the agent manages), Zep (temporal knowledge graph,
  bi-temporal edges).

## 3. Practitioner lessons (failure modes people actually hit)

These shape our design more than the happy-path docs:

1. **Day-2 failure = stale memory across sessions.** Demos work because the whole
   conversation fits one context window; production breaks across sessions, days,
   topics. (We are multi-session + multi-agent — this is our central risk.)
2. **Temporal correctness is the hardest part.** Facts change; Zep scores ~64% vs
   Mem0 ~49% on temporal retrieval. Memories need timestamps + **supersession**
   (a later fact retires an older one).
3. **Reflexion's core weakness: reflections are episodic, unstructured, and
   instance-specific — not distilled into reusable knowledge**, and shallow error
   analysis yields "general and useless" corrections. Storing reflections is not
   enough; they must be *distilled*.
4. **A bad reflection in a long-running agent is catastrophic** — one wrong
   distilled belief can taint thousands of later decisions; severity scales with
   agent lifetime. Distilled memory needs confidence, provenance, and the ability
   to be superseded/retired. Never auto-trust.
5. **Failures outnumber successes.** Methods that learn only from successful
   trajectories are impractical; learning from failure (our `log_failure`) is the
   right bias.
6. **Importance scoring at write time (1–5).** Vital facts (constraints) get top
   importance and never expire; trivia decays.
7. **Consolidation with a writer→critic gate.** One LLM proposes the consolidated
   memory; a second checks for data loss, hallucination, and correct conflict
   resolution, and only commits if VALID. (Matches our adversarial-verify habit.)
8. **Keep ephemera out.** Mark session-only notes so consolidation filters them;
   otherwise every offhand comment becomes permanent.
9. **Decay + recall.** Episodic decays; semantic is curated/superseded; procedural
   accumulates success/failure counts that feed consolidation. Old facts shouldn't
   rank like fresh ones; a recall lifts a fact back up.

## 4. Our unique advantage

The production systems bolt memory types onto one store after the fact. We
already have the **State vs. Events** split that the taxonomy *wants*:

- **Ledger** (events, append-only, ordered) = natural home for **episodic** memory
  (raw experiences, reflections, signals — "what happened").
- **Store** (state by key, curated, supersedable) = natural home for **semantic**
  (decisions, distilled lessons) and **procedural** (approaches with outcome counts).
- **Consolidation (episodic → semantic) is precisely the `chronicles/` layer** we
  reserved: raw ledger → writer→critic distillation → curated chronicle.

So integration is mostly *mapping the model onto primitives we already have*,
plus adopting importance/decay retrieval and a guarded consolidation loop.

## Sources
- [Cognitive Architectures for Language Agents (CoALA)](https://arxiv.org/html/2309.02427v3)
- [Reflexion: Verbal Reinforcement Learning](https://openreview.net/pdf?id=vAElhFcKW6)
- [Types of AI Agent Memory](https://atlan.com/know/types-of-ai-agent-memory/)
- [Mem0: Production-Ready Long-Term Memory](https://arxiv.org/html/2504.19413v1)
- [State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Mem0 vs Zep vs Letta compared](https://www.agenticwire.news/article/mem0-zep-letta-agent-memory)
- [Meta-Policy Reflexion (reusable reflective memory)](https://arxiv.org/html/2509.03990v2)
- [Agent Memory Systems: A Complete Engineering Guide](https://medium.com/@tejpal.abhyuday/a-framework-agnostic-reference-for-designing-memory-in-any-ai-agent-not-just-travel-bots-0554fe803f59)
- [Memory in LLM-based Multi-agent Systems (survey)](https://www.techrxiv.org/users/1007269/articles/1367390/master/file/data/LLM_MAS_Memory_Survey_preprint_/LLM_MAS_Memory_Survey_preprint_.pdf?inline=true)
- [Awesome-Agent-Memory (papers/systems)](https://github.com/TeleAI-UAGI/Awesome-Agent-Memory)
