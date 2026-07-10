# Research: context handling, compaction, and the "skeleton of an idea"

Status: historical  (2026-07-09, P4: Research snapshot; context pillar supersedes)

Date: 2026-06-20. Research to de-risk the Context pillar (Wave 2) + Distiller
(Wave 3). Honesty note: the *internal* mechanisms of specific models (Fable, Opus)
are not public — this synthesizes Anthropic's **published** agentic-context guidance
(what Claude Code itself uses) + the broader literature, and maps it to our system.

## 1. How frontier agentic systems handle context (published)

Anthropic's guidance for long-horizon agents centers on three complementary
techniques + one principle + one architecture:

- **Context rot** (the core pitfall): as tokens in the window grow, recall
  *degrades* — you get less per token, even before the hard limit. So **more
  context is not better.** This validates a hard token budget (our 8–10k) as a
  *feature*, not a constraint.
- **Compaction**: near the limit, summarize the conversation and reinitiate a new
  window from the summary.
- **Structured note-taking**: externalize durable state to notes outside the window.
- **Multi-agent**: isolate context per sub-agent.
- **Guiding principle**: find the **smallest set of high-signal tokens** that
  maximizes the desired outcome.
- **Architecture**: the **harness owns context management** — it queries any slice
  of the **event stream** at runtime, transforms it for the current model, and
  injects the result. Context logic lives in the harness and *changes per model
  generation*.

**This is exactly our shape already:** our `Ledger` *is* the append-only event
stream; the **Context pillar is the harness** that queries slices, transforms
(rank + compact), and injects within budget. We don't need to invent the pattern —
we need to implement the harness over the Ledger/Store we built.

**Pitfall called out explicitly:** *irreversible discard* — it's hard to know which
tokens future turns need, so destroying raw context causes failures. → never delete
the raw; compaction must be a *derived view* with a path back.

## 2. Compaction — shrink the footprint, keep the data

- **Hierarchical / tree summarization** (e.g. MEMWALKER): iteratively summarize raw
  → section summaries → a top summary, forming a tree; navigate the tree to answer
  queries. → tiered summaries with drill-down.
- **Lossy summary + lossless pointer** (compensatory/residual paths): keep a pointer
  so pruned detail can be reconstructed. → **the key design rule for us:** a
  compacted entry stores a *pointer* (Ledger cursor id / experiment id) back to the
  raw events. Footprint drops (you read the summary) but nothing is lost (raw stays
  in the Ledger).
- **Faithfulness**: structured compression (discourse-unit decomposition) and a
  **writer→critic** check guard against lossy/hallucinated summaries — exactly our
  Distiller spec (Mem0's writer→critic).
- Other token-reduction families (LLMLingua pruning, Gisting soft-tokens) exist but
  are overkill here; summarization + structured extraction is the practical path.

## 3. The "skeleton of the shape of an idea" — accurate, readable, fast

The literature's answer is a **structured, hierarchical skeleton with progressive
disclosure**:

- **Progressive disclosure**: organize into ~3 levels; load only the currently-
  necessary subset; keep the rest a drill-down away. The *skeleton is the top
  level*; detail is fetched on demand.
- **Structured outline (a "Skeleton Agent")**: a globally organized, content-aware
  backbone, recorded as **Markdown + YAML** — machine-parseable *and* human-readable,
  version-controllable, categorized by `type`/`tags`. This is precisely "accurate
  readable skeleton."
- **Knowledge graph / Context Tree**: hierarchical `Domain > Topic > Subtopic >
  Entry` as a directed graph where **edges are explicit cross-references**. Graphs
  condense volume while preserving meaning, and connect facts across sources so
  retrieval needn't re-stitch them.

**This is where our assets line up uniquely:** our **66 relationship types are the
graph edges**; the skeleton is a `Domain > Topic > Entry` tree with relationship-
typed links. It also matches our own `cache_hierarchy_architecture` (L1/L2/L3 +
skeleton-linking) and is exactly what the reserved **`chronicles/`** layer should be.

## 4. Pitfalls → how we avoid each

| Pitfall | Our defense |
|---------|-------------|
| Context rot (overfilling) | hard token budget (8–10k); rank to smallest-high-signal set |
| Irreversible discard | never delete raw (Ledger is append-only); compaction = derived view + pointer |
| Hallucinated / lossy summaries | Distiller writer→critic faithfulness gate |
| Stale facts surfacing | Supersession (retired facts excluded) |
| Lost-in-the-middle / distractors | Ranker orders high-signal first; budget keeps it short |
| Per-model coupling | context logic lives in the Context pillar (the harness), swappable |

## 5. What this means for our build (Wave 2–3 design decisions)

1. **Two tiers, never destroy the raw.** Raw events stay lossless and append-only in
   the **Ledger**. The **compacted skeleton** is a *derived* view in **`chronicles/`**.
2. **Every compacted entry carries a `source` pointer** (Ledger cursor id / experiment
   id) → drill-down + reconstruction; footprint drops without data loss.
3. **Skeleton format = Markdown + YAML**, hierarchical `Domain > Topic > Entry`, each
   entry: `type`, `tags`, `relates` (relationship_type + target id), `confidence`,
   `source`. Human-readable, machine-parseable, version-controllable. This *is* the
   "shape of an idea."
4. **The Context pillar is the harness**: query Ledger/Store slices → `Ranker`
   (relevance×importance×recency + relationship-type) → `Distiller` (hierarchical,
   writer→critic, to budget) → inject. Logic isolated so it can change per model.
5. **Budget is a feature.** Target the smallest high-signal 8–10k; resist the urge to
   "include everything" — context rot makes that *worse*, not safer.

## Sources
- [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Cookbook — memory, compaction, tool clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)
- [Hierarchical Token Compression (overview)](https://www.emergentmind.com/topics/hierarchical-token-compression)
- [Active Context Compression: Autonomous Memory Management in LLM Agents](https://arxiv.org/abs/2601.07190)
- [Faithful structured context compression (EDU decomposition)](https://arxiv.org/pdf/2512.14244)
- [ByteRover — agent-native memory via LLM-curated hierarchical context](https://arxiv.org/pdf/2604.01599)
- [Neo4j — knowledge graphs + LLM multi-hop reasoning](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/)
