# System Inventory + Prior-Art Register — Part 4: Recall, Learning, Narrative, Library, Primitives
## DeepSeek, 2026-07-26 — overnight program

---

## core/recall/ (the recall system — census filed separately at scratch/recall-census-2026-07-26.md)

### 26. Recall-at-Action (at_action.py)

**WHAT IT DOES:** The recall engine. Given a target (file path or command), ranks active lessons by relevance, surfaces ≤3, faithfulness-gates, provenance-tags. Warmed from a TTL disk cache. Anti-repeat per session. The PreToolUse hook calls this on every tool invocation.

Detailed census filed separately. Here I cover only the comparable-systems analysis not in the census.

**COMPARABLE SYSTEMS:**
1. **mem0** — "memory layer for AI agents." Stores facts as graph nodes with embeddings. Our recall is keyword+path deterministic; mem0 uses embeddings + graph traversal. mem0 scored 68.5 on LoCoMo with graph variant.
2. **Letta** — agent memory with plain files + iterative search. Scored 74.0 on LoCoMo — ABOVE mem0's graph variant — by letting the agent search iteratively rather than using single-hop retrieval. Our recall-at-action IS single-hop retrieval (≤3 lessons injected before the tool call).
3. **Claude Code's own memory** — injected at session start. Our recall fires per-tool-call (PreToolUse) AND per-prompt (UserPromptSubmit). Claude's fires once.
4. **RAG (Retrieval-Augmented Generation)** — vector search + LLM reranking. Our recall is deterministic keyword+path, no LLM on the hot path, no embeddings.

**THE DELTA:**
- Letta: iterative search beats single-hop. The agent searches when it needs to, not when the system decides. Our recall injects before the agent asks — the agent might not need it, or might need something different.
- mem0: graph-based memory with entity extraction. Our recall is flat keyword matching; mem0 would extract entities and their relationships.
- Claude Code: session-start injection only. Our per-tool-call injection is more frequent but potentially noisier.

**THE IMPORT:** **Iterative retrieval over single-hop.** Letta's finding (74.0 vs 68.5) is direct evidence that single-hop injection at tool-call time may be the wrong shape. Instead of injecting ≤3 lessons before every tool call, expose recall as a TOOL the agent can call when it needs to: `recall("how do I fix the FileStore coherence hole?")`. This changes recall from push to pull — the agent decides when it's relevant. This is the direction Daniel's question ("should we turn off recall while we refit?") points toward.

**THE ANTI-IMPORT:** **Graph-based memory (mem0).** Adding entity extraction + graph traversal on the hot path would require LLM calls (entity extraction) and embeddings. Our deterministic, no-LLM, keyword-first approach is simpler and auditable. The mem0 graph variant scoring BELOW Letta's plain files suggests graph memory isn't the differentiator — retrieval strategy is.

**STATUS:** LIVE. Detailed census at `scratch/recall-census-2026-07-26.md`. Per-tool-call injection, warm cache, anti-repeat, faithfulness-gated. Funnel metric is defective (double-logged impressions).

---

### 27. Ranker (ranker.py in core/primitives/)

**WHAT IT DOES:** Shared relevance ranker. `score(item, query)` returns a 0..1 relevance score. Composable: keyword relevance + importance + usefulness + recency, with configurable weights. Used by recall-at-action and the search path.

**COMPARABLE SYSTEMS:**
1. **BM25** — the standard probabilistic relevance function. TF-IDF with document length normalization. Our ranker uses IDF weighting (`_idf_weights`) but no document length normalization — a 10,000-word lesson and a 50-word lesson get the same keyword match score.
2. **Learn-to-Rank (LambdaMART, XGBoost)** — ML model trained on click/credit data. Our ranker has fixed weights; LTR would learn weights from the funnel data (which lessons surfaced → which got credit).
3. **Elasticsearch relevance** — BM25 + field boosting + function scores. Our ranker has fixed component weights; ES would let you tune per-field boosts.

**THE DELTA:**
- BM25: document length normalization. A long recommendation gets penalized because its keywords are diluted. Our ranker doesn't normalize for length — a verbose lesson with one hit keyword scores the same as a concise lesson with one hit.
- LTR: learned weights from outcome data. Our usefulness_factor adjusts based on feedback (0.5–1.5×), but the keyword-vs-importance-vs-recency weights are fixed. LTR would learn optimal weights from "which surfaced lessons led to flips?"

**THE IMPORT:** **BM25 document length normalization.** Add `log(1 + doc_length / avg_doc_length)` to the keyword relevance score. This is a ~5-line change to `_damped_overlap()` and would penalize verbose lessons that match on generic terms. The IDF weighting already handles corpus-common terms; length normalization handles within-document dilution.

**THE ANTI-IMPORT:** **Learn-to-Rank with ML.** Training a model on funnel data requires a TRUSTWORTHY funnel — and ours is double-logged with a mixed pre/post-fix series. Fix the measurement before learning from it. Fixed weights with deterministic rules are correct for now.

**STATUS:** LIVE. `core/primitives/ranker.py`. Deterministic, composable, IDF-weighted. No BM25 normalization.

---

### 28. Faithfulness Critic (faithfulness.py in core/primitives/)

**WHAT IT DOES:** No-LLM faithfulness gate. Checks that lesson recommendations don't contain fabricated pointers, fabricated numbers, or unresolvable source references. `faithfulness_report(text)` returns `{faithful: bool, confidence: float, issues: [...]}`. Used by the recall render to gate what reaches the agent.

**COMPARABLE SYSTEMS:**
1. **Factual consistency metrics (QuestEval, SummaC)** — NLI-based factual consistency for summarization. Use natural language inference to check if a summary is consistent with source. Our critic is regex-based (pointer patterns, number patterns); NLI-based would catch semantic contradictions.
2. **RAGAS faithfulness** — checks if an LLM answer is grounded in retrieved context. Our critic checks if pointers resolve — a narrower, cheaper check.
3. **Grover / GLTR** — detects machine-generated text by statistical patterns. Our critic doesn't detect generated text — it validates structural claims.

**THE DELTA:**
- NLI-based: semantic consistency. Our critic catches "this pointer doesn't resolve" but not "this claim contradicts the source it points to." NLI would catch both.
- RAGAS: groundedness in retrieved context. Our critic doesn't compare against source documents — it only validates internal consistency.

**THE IMPORT:** UNVERIFIED. The critic is characterized for zero false-positives on extractive output. Its discrimination on LLM-written text is unproven. Adding NLI-based consistency checking would require an LLM call — which violates the no-LLM-on-hot-path constraint. **This is a deliberate design trade-off, not a gap.**

**THE ANTI-IMPORT:** **RAGAS faithfulness.** Adding LLM calls to the recall hot path. The no-LLM constraint is correct — recall must be cheap and deterministic. An LLM-based faithfulness check would add latency and non-determinism.

**STATUS:** LIVE. `core/primitives/faithfulness.py`. No-LLM, regex-based. Characterized for extractive output only. Characterized confidence: 1.0 on zero false-positives.

---

## core/library/ (the artifact-atom family)

### 29. Atom Family (atoms.py)

**WHAT IT DOES:** The artifact-atom substrate. Mints typed atoms (design docs, reports, chronicles, contracts) with `id`, `citations_out`, `supersedes`/`superseded`, `schema_version`. Append-only JSONL + Store duality. Version-gated (refuses newer-than-known). Supersession is first-class, never deletion.

**COMPARABLE SYSTEMS:**
1. **Wikidata items** — Q-IDs with statements, references, ranks. Our atoms have `id` (like Q-IDs), `citations_out` (like statements), and `supersedes` (like "replaces" property). Wikidata has 1.5B statements with preferred/normal/deprecated ranks; our atoms have ~200 with current/draft/superseded statuses.
2. **Roam Research / Athens** — bidirectional linking between pages. Our atoms have `citations_out` edges; Roam has `[[wikilinks]]` that create backlinks automatically. Our backlink index (`cited-by`) is manually maintained.
3. **Datomic schema** — typed attributes with cardinality, uniqueness, and history. Our atoms are JSON documents; Datomic would decompose them into typed facts.
4. **Content-addressed storage (IPFS, git)** — identify by hash, never mutate. Our atoms have `body_sha` (content hash) and version numbers. Git IS the history — JSONL files are git-tracked.

**THE DELTA:**
- Wikidata: 1.5B statements, preferred/normal/deprecated ranks, qualifiers, ~10K properties. Our atom model is a tiny fraction — ~200 atoms, no ranks, no qualifiers, 50 relationship types. The gap is scale and richness, not design.
- Roam: automatic backlinks. Writing `[[art_20260725_...]]` in any atom body creates a citation edge automatically. Our citations are explicit JSON lists; Roam would parse them from markdown.
- Datomic: typed refs with schema enforcement. `citations_out` is `[{target: str, rel: str}]` — no type checking on `target`, no cardinality constraints.

**THE IMPORT:** **Wikidata-style ranks on atoms.** Atom status is `current | draft | superseded | fossil`. Adding `preferred | normal | deprecated` ranks (orthogonal to status) would let an atom be "current but deprecated" (still valid, but superceded by a better source). This maps directly to the lesson `is_benched` / `is_graduated` pattern — the atom plane gets the same decay vocabulary as the lesson plane.

**THE ANTI-IMPORT:** **Roam-style automatic backlinks from markdown parsing.** Parsing `[[wikilinks]]` from atom bodies would couple the citation graph to prose formatting. Explicit `citations_out` lists are more robust — they survive renames, refactors, and format changes.

**STATUS:** LIVE. `core/library/atoms.py`. ~200 atoms. JSONL git-tracked, Store-backed. Schema v1, version-gated. Supersession-aware.

---

### 30. Projection (projection.py)

**WHAT IT DOES:** Renders atoms into human-readable surfaces. `render(atom)` produces a markdown section. `lineage(atom_id)` follows `supersedes` chains backward. `backlinks(atom_id)` reads the `cited-by` index.

**CONNECTED TO:**
- Reads from: `atoms.py` (atom retrieval), Store (indexes)
- Used by: `agent_cli.py story`, `knowledge_map.py`

**COMPARABLE SYSTEMS:**
1. **Wikidata Query Service** — SPARQL queries over the knowledge graph. Our projection is Python rendering; Wikidata Query would let you ask "show me all atoms that cite X, sorted by date."
2. **Obsidian Dataview** — query plugin that treats notes as a database. `TABLE supersedes FROM #design WHERE category = "recall"`. Our projection is imperative Python; Dataview is declarative.
3. **Gatsby / Next.js data layer** — GraphQL over content. Our projection renders markdown; Gatsby would let you query atoms with GraphQL.

**THE DELTA:**
- Wikidata Query: graph queries. "What atoms cite atoms that cite X?" is one SPARQL query. In our system, it's a Python loop over `citations_out`.
- Dataview: declarative queries in markdown. Writers embed queries in their notes; our projection is called imperatively by CLI verbs.

**THE IMPORT:** **SPARQL-like query over atoms.** With SQLite, this is a SQL query: `SELECT * FROM atoms WHERE id IN (SELECT target FROM citations WHERE source = ?)`. This is free once atoms have SQL-backed storage. The projection becomes a thin render layer over SQL.

**THE ANTI-IMPORT:** **GraphQL.** Adding a query language layer for 200 atoms. SQL is simpler and we already have it.

**STATUS:** LIVE. `core/library/projection.py`. Markdown rendering, lineage traversal, backlink queries. No declarative query interface.

---

## core/learning/ (lesson CRUD)

### 31. Learning Store (learning_store.py)

**WHAT IT DOES:** Lesson CRUD over the Store. `learn(signal)` writes a lesson. `load_all_learnings_from_store()` lists all. `mark_benched()`, `mark_graduated()`, `tag_anti_pattern()` mutate lesson status. `find_related()` computes near-duplicate edges at write time.

**COMPARABLE SYSTEMS:**
1. **Contentful / Sanity** — headless CMS with content types, versioning, and references. Our learning store is a homegrown CMS for lessons. Contentful has draft/published states; we have confidence + success + benched + graduated.
2. **Notion databases** — flexible schemas with properties, relations, and filters. Our lessons are flat hashes; Notion would give each lesson a typed schema with linked databases.
3. **MongoDB** — document store with flexible schema and indexing. Our Redis hashes are the document store; MongoDB would add rich queries and indexing.

**THE DELTA:**
- Contentful: content modeling and versioning. Our lessons have no schema (beyond the hash fields); Contentful enforces field types and validations.
- MongoDB: rich queries (`find({agent_id: "claude", success: "yes"})`). We load ALL lessons and filter in Python.

**THE IMPORT:** **Schema for lessons.** A lesson should have typed fields with defaults and validations: `experiment_name: str (required)`, `recommendation: str (required)`, `confidence: enum(high, medium, low)`, `success: enum(yes, no, partial)`, etc. This prevents malformed lessons (like the fixture data that pollutes the corpus with `agent_id: messy_agent`). The schema can be a Python dataclass with `__post_init__` validation — no new dependency.

**THE ANTI-IMPORT:** **MongoDB.** Swapping Redis for MongoDB would replace one external dependency with another. We just landed SQLite — adding MongoDB would give us three backends (Redis + SQLite + Mongo) with three different query models.

**STATUS:** LIVE. `core/learning/learning_store.py`. Hash-based CRUD. No typed schema. Near-duplicate detection at write time via `find_related()`.

---

## core/narrative/ (the narrative spine)

### 32. Beat Log + Chronicler (beat_log.py, chronicler.py)

**WHAT IT DOES:** Beat log records discrete narrative events (beats) with tracks, themes, and importance. Chronicler consolidates beats into chapters, generates the narrative spine (Atlas), and handles time-series grouping.

**COMPARABLE SYSTEMS:**
1. **ActivityPub / Mastodon** — federated timeline of activities. Our beat log is a local timeline; ActivityPub would federate it across instances.
2. **Twitter / X timeline** — chronological feed with ranking. Our beat log is chronological; Twitter adds relevance ranking.
3. **Lifelogging (Gordon Bell, MyLifeBits)** — capture everything, index, retrieve. Our beat log is selective (only significant events); lifelogging captures everything.

**THE DELTA:**
- ActivityPub: federation. Our beats are local; ActivityPub would let other instances subscribe to our beat log.
- Lifelogging: completeness. Our beat log captures selected events; lifelogging would capture every tool call, every message, every state change.

**THE IMPORT:** UNVERIFIED. The narrative spine is working and stable. No obvious gap that prior art would fill. The chronicler's chapter consolidation is the novel part — grouping beats into coherent chapters by time and theme. Prior art in text segmentation (TextTiling, C99) might improve chapter boundaries, but this is speculative.

**THE ANTI-IMPORT:** **ActivityPub federation.** Adding federation for a single-node narrative log. The beat log is internal; federation adds complexity without a use case.

**STATUS:** LIVE. `beat_log.py` (events), `chronicler.py` (consolidation→chapters). The narrative spine is load-bearing for the knowledge map.

---

## core/primitives/ (shared algorithmic primitives)

### 33. Embedder + Clusterer (embedder.py, clusterer.py)

**WHAT IT DOES:** Semantic embeddings for lessons and atoms. `Embedder.embed(text)` → vector. `Clusterer.cluster(items)` → domain clusters. Hardware-gated (requires sentence-transformers) and OFF by default. The deterministic keyword pipeline is always-on; embeddings are opt-in.

**COMPARABLE SYSTEMS:**
1. **sentence-transformers / SBERT** — the library we use. Standard for semantic similarity.
2. **OpenAI Embeddings / Cohere Embed** — API-based embeddings. Would replace local models with cloud APIs. Higher quality, adds network dependency.
3. **FAISS / Annoy / USearch** — vector similarity search at scale. Our embedder uses cosine similarity over numpy; FAISS would add approximate nearest neighbor search for millions of vectors.

**THE DELTA:**
- FAISS: ANN search at scale. Our brute-force cosine (O(n) per query) is fine at 455 lessons. At 1M lessons, FAISS would find the top-100 in milliseconds vs seconds.
- Cloud embeddings: higher quality, API cost, network dependency. Our local embeddings are free and offline but lower quality.

**THE IMPORT:** **Keep embeddings OFF by default.** The deterministic keyword pipeline is fast, auditable, and works offline. Embeddings are a premium tier for when keyword matching fails. This is the correct architecture. The hardware gate (sentence-transformers not installed → embeddings disabled) is the right design.

**THE ANTI-IMPORT:** **Cloud embeddings.** Adding an API dependency for a feature that's OFF by default. Local embeddings are sufficient for the opt-in use case.

**STATUS:** LIVE. `core/primitives/embedder.py`, `clusterer.py`. OFF by default. Hardware-gated. Deterministic keyword pipeline is the default.

---

## SYSTEM INVENTORY: COMPLETENESS CHECK

- [x] core/foundation (8 modules) — Parts 1
- [x] core/events (3) — Part 1
- [x] core/comm (36) — Part 2 (11 deep-dived, 25 inventoried)
- [x] core/coord (11) — Part 3
- [x] core/trust (2) — Part 3
- [x] agent/harness (9) — Part 3
- [x] scripts/hooks + checkers — Part 3
- [x] core/recall (9+) — Part 4 + separate census
- [x] core/learning (4) — Part 4
- [x] core/narrative (7) — Part 4
- [x] core/library (2) — Part 4
- [x] core/primitives (8) — Part 4
- [ ] scripts/runners — not inventoried (executables, not subsystems)
- [ ] scripts/bifrost_ui — not inventoried (UI, separate surface)
- [ ] core/fleet (2) — covered in Part 3 autopilot section
- [ ] core/perspectives (1) — not inventoried (small)
- [ ] core/renew (1) — not inventoried (small)
- [ ] core/signals (1) — not inventoried (small)
- [ ] core/codex (3) — not inventoried (codex-specific)

Remaining areas are small or already partially covered. The load-bearing subsystems (store, bus, lanes, wake, recall, atoms, hooks) are all inventoried with comparables.
