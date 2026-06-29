# Agent-Experience Plan — Akashic Aurora

> An elegant synthesis: one acceleration structure, traversed cheaply at the point of action,
> tiered like a cache, disclosed skeleton-first, trust-weighted by FAITH-1, portable across agents and time.
> Addresses the four agent-experience pain points (One Door, Write-Once Memory, Recall-at-Point-of-Action,
> Built != Wired) from up close, to medium, to big picture — fusing 2024–2026 SOTA with our own shipped learnings.

---

## 0. What the adversarial critics changed (this overrides anything below)

Three critics (overreach-and-wiring, analogy-rigor, constraint-and-sequencing) stress-tested the draft.
Their corrections, integrated:

- **The unified `core/index/` "Index" engine (§3) is DEFERRED, not built.** It was the single largest
  piece of NEW unwired capability in a plan whose thesis is "stop shipping unwired capability" — the draft
  was committing its own diagnosed sin. At this corpus size a flat `path → lesson_ids` dict is already O(1);
  no scale here needs BVH broad-phase culling. The BVH/cache/skeleton analogies are kept as a **design
  compass** (they shape the small wirings), not a subsystem to build now. §3 is the *eventual* shape **iff**
  a concrete scale trigger fires (see §5).
- **`AKASHIC_AGENT_ID` is a usability fix, not an "arming keystone."** The PreToolUse hook ALREADY fails
  CLOSED when the id is unset (it can't verify ownership, so it blocks every locked path) and it is already
  set to `claude` in `.claude/settings.json`. Setting it *relaxes* the guard to block-only-peer-locks; the
  open item is that **Cursor** must set its own id. (The draft inverted cause and effect.)
- **Path + caller facts corrected.** `Store.cas` lives in **`core/foundation/store.py:173`** (genus
  `foundation`, not `primitives`); `fast_cache.py` is **`core/foundation/fast_cache.py`**. `cas` is **not**
  "zero callers" — it is called internally (store.py:197) and dispatched (717/721); the accurate gap is **"no
  domain / non-test caller."** The `fast_cache.py:76` LRU-comment-that-lies and the hook anchors (32/47) verified correct.
- **Net effect:** the **up-close wiring moves stand** (genuinely WIRE-not-NEW — the gold). The medium/big-picture
  rows that build new infrastructure (the Index, CAS-hash Door auto-sync, Tier-1 runtime coverage, one-hop
  prefetch) are **demoted to deferred** behind explicit triggers. Steps 1–5 of §4 deliver the entire felt
  improvement without a new engine.

---

## 1. Thesis

Capabilities and knowledge are **two projections over one immutable substrate** (Akasha), and the agent's
entire experience improves when both are recalled by **one engine** that behaves like a ray tracer over a
spatial-acceleration structure: build the index **once**, then at the **point of action** (a file path, a
command, a task keyword) descend a cheap **broad phase** (typed-edge graph + keyword/path partition — the BVH)
into a tiny **narrow phase** (rank + distill the few candidates in the hit box), serving results from a
**cache hierarchy** (L1 in-context skeleton → L2 warm path/verb index → L3 cold append-only Ledger) that is
**disclosed skeleton-first** (lossy summary + lossless `source` pointer), **trust-weighted by FAITH-1**
(superseded or unfaithful items never surface), and **portable** — knowledge written once is recallable by
future-me-after-compaction and by any peer agent (Cursor / next Claude) because it lives in the shared atom
substrate, not in any one agent's private memory. The differentiator nobody else has (RAPTOR/GraphRAG/MemGPT/Zep
all lack it) is that the substrate is **bi-temporal and append-only**, so every index is a regenerable
projection and **the worst case of any optimization is a no-op** — which is what makes aggressive local recall
acceleration *safe*.

---

## 2. Per Pain Point

Legend — **Effort:** S (hours) / M (a day or two) / L (multi-slice). **Wire vs New:** prefer WIRE.
Lenses: BVH (acceleration structure), Cache (L1/L2/L3 + locality), Skeleton (shape-first + pointer),
Naming (LEXICON / descriptions-as-prompts), Categorization (typed graph, cross-domain/agent).

### 2.1 One Door — *"I must remember WHICH surface holds each capability."*

Felt problem: the door is forked four ways (14 `agent_cli.py` argparse verbs, ~17 `ai_setup_mcp.py` MCP tools,
loose `scripts/`, raw `core/`); the two doors are **not supersets** (MCP-only: `bifrost_send/broadcast/inbox/presence`
+ gemini; CLI-only: `lock/unlock/locks`). SOTA reframes it: the pain is not too few verbs, it is that **all** tool
defs load up front — Anthropic measured naive MCP at ~150K tokens and tool-selection accuracy collapsing to ~49%.
The cure is *our own* skeleton pattern: hot names+descriptions, full schema resolved just-in-time.

| Altitude | Move | Effort | Lens | Wire/New | Depends on | SOTA anchor |
|---|---|---|---|---|---|---|
| Up-Close | Generate a `discover`/`help` verb in `agent_cli.py` by walking existing argparse subparsers → print name + `help=` + namespace, front-loaded ~50 lines (the L1 skeleton) | S | Skeleton, Naming | WIRE (over existing subparser metadata) | nothing | Tool Search Tool `defer_loading` (72K→3–5K tok, 49%→74% acc); Agent Skills 3-level disclosure |
| Up-Close | Add `check_boundaries.py` rule #5: every subparser must have a non-empty "when to call this" `help=` and a LEXICON-valid name; fail CI on a verb that lies or is silent | S | Naming | WIRE (extend existing AST walker) | discover verb | "smelly descriptions" measurably degrade selection — naming is the dominant lever |
| Up-Close | Point existing `core/primitives/ranker.py` at the verb manifest in `discover <keyword>` so most task-relevant verbs surface first | S | Cache (budget), Categorization | WIRE | discover verb | mem0 2026: keep LLM off hot recall path; deterministic fusion |
| Medium | Build one **Door Registry** = regenerable manifest of every verb keyed by namespace (memory/narrative/comm/coordination), generated from `agent_cli.py`, kept in sync via **`Store.cas` hashing** of each `cmd_*` signature+docstring | M | BVH (partition), Naming | WIRE (`Store.cas`, core/foundation/store.py:173 — no domain caller, RC-02). NOTE: CAS-hash auto-sync is deferred gold-plating; a static `test_door_parity` suffices at this scale | discover verb | ScaleMCP SHA-256 hash-on-divergence auto-sync; code-execution-MCP 150K→2K |
| Medium | Add `tests/test_door_parity.py`: CLI verbs == MCP tools modulo a documented ALLOWLIST (the architecture review's #1 ask) | S | Naming | NEW (read-only assertion) | manifest | code-execution-MCP namespace traversal |
| Medium | Add missing CLI-bridgeable verbs as `cmd_*` so a future MCP wrap is one `_run` line; hand MCP-wrap deltas to Cursor via `handoff` (do **not** edit `ai_setup_mcp.py`) | M | Naming | WIRE (`_run` bridge, ai_setup_mcp.py:69) | manifest | one-truth/two-doors |
| Big-Picture | The door indexes verbs the **same** way the Codex indexes atoms — "which tool" and "which lesson" become one ranked, typed, scoped recall over one substrate (third rotation of codex-plan's "one substrate, two projections") | L | Categorization, BVH | WIRE (Ranker/Distiller/typed edges) | shared index (§3) | A-MEM Zettelkasten; HippoRAG PPR; "from endpoint sprawl to tool semantics" |

### 2.2 Write-Once Memory — *"The same fact is hand-copied into ~3 places that then drift."*

Felt problem: two disconnected memories with no shared substrate — native Claude-Code memory
(`C:\Users\L5\.claude\projects\C--Users-L5\memory\*.md`) and the Akashic substrate (`learn:`, Beats), plus an
**internal** fork (`learn:` LearningStore vs `mem:` AgentMemory both writing the same `lessons.md`). The defect is
architectural: there is no single append-only **Atom** the `.md` files are a projection of, so write-once is
impossible by construction.

| Altitude | Move | Effort | Lens | Wire/New | Depends on | SOTA anchor |
|---|---|---|---|---|---|---|
| Up-Close | Add `cmd_note`/`cmd_record_memory` to `agent_cli.py`: canonical write = append a memory-atom (state-with-history), then best-effort fan out a Beat + raw event exactly as `cmd_learn` already does (agent_cli.py:159–211) | M | Naming, Skeleton | WIRE (mirror `cmd_learn`) | LEXICON entry first | AgeMem 2026: memory ops as policy actions; Mem0 ADD/UPDATE/SUPERSEDE/NOOP |
| Up-Close | Add LEXICON entry first (reuse `atom` genus; **avoid** a third store next to `learn:`/`mem:`); intention-revealing name (effect = "append one memory-atom + reproject MEMORY.md") | S | Naming | WIRE (LEXICON.md) | nothing | genus-not-species; names-must-not-lie |
| Up-Close | Verify `embedder.py`/`clusterer.py`/`consolidator.py` actually run (`py -m pytest -q`) before depending on them — presence != armed | S | — | WIRE (test) | nothing | build != wired discipline |
| Medium | `scripts/project_memory.py`: read all `is_active` memory-atoms, RE-RENDER `MEMORY.md` + `MEMORY.index.json` reusing `chronicler.py::_render`'s dual-artifact + back-link pattern and `consolidator.py` for per-section distillation — MEMORY.md becomes **generated output** | M | Skeleton | WIRE (`chronicler` + `consolidator`) | cmd_note | Graphiti episodic→semantic→community incremental projection; RAPTOR multi-resolution |
| Medium | Corrections are **supersessions, not edits**: changed fact appends a new atom with a `replaces` edge + `valid_to`; projector renders only active atoms, superseded raw stays pointer-recoverable (this is how "BreakThrough Stack → Akashic Aurora" should be stored — one supersession, not a 3-file hand-edit) | M | Categorization | WIRE (`supersession.py`, `relationship_types.py`) | cmd_note | Zep/Graphiti invalidate-not-discard, DMR 94.8% |
| Medium | Add boundary rule: a `MEMORY.md` bullet without a backing atom pointer = FAIL; machine holds the write-once line | S | Naming | WIRE (`check_boundaries.py`) | projector | survey 2026: append-only-with-rewrite antipattern crowds recall |
| Medium | Backfill: one-time import of current `MEMORY.md` bullets + checkpoint files into atoms (source pointers preserved); regenerate and prove **round-trip lossless** before deleting any hand copy | M | Skeleton | WIRE | projector | librarian-not-author (preserve high-salience outliers) |
| Big-Picture | One substrate, many projections: MEMORY.md, lessons.md, chronicles, Codex are all regenerable lossy-summary+lossless-pointer **views** over one append-only atom ledger. "Write-once" becomes literally true — append one atom, every surface reprojects. Aurora over Akasha finally includes the agent's **own** native memory | L | Skeleton, Categorization | WIRE | shared index (§3) | MemGPT OS-paging; HippoRAG single index |

### 2.3 Recall-at-Point-of-Action — *"Lessons are written far more often than they are read when they matter."*

Felt problem: storage is **passive** and recall is bound to **session boundaries** (`boot()` / `bifrost-sync`),
not actions. The one per-action seam that exists — `scripts/hooks/claude_pretooluse.py` (PreToolUse) — already
parses `tool_input.command` (line 32) and `file_path` (line 47) and already imports `core.*`, but its **only**
output is a `_deny()` veto. Write fans out best-effort to many projections; read-at-action = zero.

| Altitude | Move | Effort | Lens | Wire/New | Depends on | SOTA anchor |
|---|---|---|---|---|---|---|
| Up-Close | Add `cmd_recall_at` (`recall --path/--command`) to `agent_cli.py`: given a path/command, return the smallest high-signal set of **active** lessons/blockers/locks — deterministic, keyword/path-first via `ranker.py` (`is_active` filter) + `distiller.py` summaries with `learn:`/`narr:` pointers. CLI-first (testable, door-parity); do **not** touch `ai_setup_mcp.py` | M | Skeleton, BVH | WIRE (Ranker + Distiller) | LEXICON entry | mem0 2026 explicitly: "No recall-at-action mechanism exists — all retrieval triggers on conversation start" (we'd be **ahead** of SOTA) |
| Up-Close | Wire the hook to emit `hookSpecificOutput.additionalContext` **alongside** the existing `permissionDecision` by calling `cmd_recall_at` — non-blocking, fail-open, <1s, capped at 1–3 entries | S | Cache (L1 line) | WIRE (already-shipped hook field) | cmd_recall_at | Claude Code hooks `additionalContext` (shipped, currently unused); fire ~3x/session, hit every time |
| Up-Close | Reuse the `path_conflict` lookup already in `_check_write` to surface "peer activity / open blocker on this path" even when there is no lock conflict (currently discarded) | S | Categorization | WIRE (`core/comm/locks.py`) | hook wiring | path index = half a recall index already |
| Up-Close | Run injected text through `faithfulness.py` so no fabricated id/number or unresolvable pointer reaches the agent | S | Skeleton (trust) | WIRE (FAITH-1) | cmd_recall_at | Zep: a confidently-wrong action-time hint is worse than silence |
| Up-Close | Build the `path → lesson_ids` index incrementally inside the existing best-effort fan-out in `cmd_learn`/`cmd_handoff` so read stays O(1) | S | BVH (leaf) | WIRE | cmd_learn | SAH: pay at build, cheap at query |
| Medium | `prefetch_one_hop` over the 66 typed edges: seed from the file/command node, pull 1-hop typed neighbors (`part_of`/`causes`/`prevents`) into L2 — close the design-only gap in `fast_cache.py` | M | Cache (spatial), BVH | WIRE (design→code) | path index | HippoRAG PPR spreading-activation, 6–13x faster single-step |
| Medium | Ship **observational-first** (log what it WOULD surface), gate arming on a labeled fixture proving it beats a no-injection baseline | M | — | WIRE | hook wiring | FAITH-1 shadow posture; Evo-Memory benchmark-don't-assert |
| Big-Picture | Akasha's substrate becomes **active**: the Ledger stops being a passive archive and **pushes** the right beat/lesson/lock to the exact moment of action — closing the write >> read-when-it-matters asymmetry that is the core pain | L | all | WIRE | shared index (§3) | hybrid pre-retrieval + JIT is the SOTA convergence |

### 2.4 Built != Wired — *"We ship correct, tested primitives that never enter the execution path."*

Felt problem: confirmed latent capability — `Store.cas` (core/foundation/store.py:173, callers only inside store.py / no domain caller, RC-02);
`fast_cache.py` has tiers but **no prefetch** and line 76 `_ramdisk_cache = {} # LRU cache` is a comment with
**no eviction** (unbounded dicts); the PreToolUse hook only vetoes. The deeper failure: there is **no automated
gate** distinguishing "exists + passes tests" from "is reachable on a production call path."

| Altitude | Move | Effort | Lens | Wire/New | Depends on | SOTA anchor |
|---|---|---|---|---|---|---|
| Up-Close | Build `scripts/check_wiring.py` by cloning `check_boundaries.py`'s AST/import-graph walk: read a WIRED-manifest (capability → expected production caller), assert each has ≥1 **non-test** caller, exit 1 on a new latent item, with a `wiring_allowlist` {item: reason+owner}. Seed with `Store.cas`, fast_cache prefetch, fast_cache LRU | M | Naming, BVH | NEW (inverted dead-code reachability) | nothing | Knip/Vulture reachability, **inverted** into "must-be-wired" |
| Up-Close | Add `cmd_wiring` to `agent_cli.py`: print the wiring report skeleton (capability → latent\|kinetic → file:line caller \| allowlist reason). CLI-only | S | Skeleton, Naming | WIRE | check_wiring | latent vs kinetic — the missing word the LEXICON should coin |
| Up-Close | Confirm `AKASHIC_AGENT_ID` is set per agent (`.claude/settings.json` env; already `claude`, **Cursor owes its own**). NOTE: `_check_write` already FAILS CLOSED when unset — setting the id *relaxes* it to peer-lock-only. Usability/correctness fix, **not** an arming keystone | S | — | WIRE (config) | nothing | coordination guard must be armed AND usable, not just one |
| Medium | Add bounded LRU eviction to `fast_cache.py` keyed by Ranker score (recency+importance), high-salience atoms **pinned** (anti-compression bias), superseded atoms evicted first; feature-flag off by default, prove bounded footprint on a fixture | M | Cache | WIRE (remove the comment-only gap) | — | locality theory LRU/MRU; budget-is-a-feature |
| Medium | Promote `check_wiring.py` from static reachability (Tier-0) to hybrid static+runtime coverage (Tier-1): record which capabilities execute during the suite/a canary session, reconcile against the manifest | M | BVH | NEW | check_wiring | Jelly dynamic call-graph (pure-static is unsound) |
| Big-Picture | **Latent → Kinetic** as an enforced lifecycle: every capability is born latent (exists+tested) and must be explicitly WIRED to become kinetic; a machine refuses to let new latent capability accumulate silently. "The system does X" becomes a checkable claim, not a hope | L | Naming | NEW | check_wiring | the trust foundation the whole force-multiplier rests on |

---

## 3. The Shared Substrate Move — **the Index** (one acceleration structure, three lenses)

> **⚠️ DEFERRED — design compass, not a build-now (see §0).** Do NOT stand up `core/index/` today. At this
> corpus size the up-close wirings (a flat `path → lesson_ids` dict + the existing Ranker/Distiller/typed
> graph) already give O(1) recall; there is no scale that needs broad-phase culling. The section below is the
> *eventual* shape the analogies point toward **iff** a concrete trigger fires (recall p95 breaches the latency
> bar on the flat index, or atoms cross ~10⁴ so linear scan stops being sub-ms). The three force-multiplier
> extensions ride on the **existing** primitives now (Ranker, `faithfulness.py`, the append-only log) — they do
> not need the Index.

All four pain points converge on **one** cross-cutting structure. In our ubiquitous language it is the **Index**
(genus `Index`, not "BVH" or "cache" — names must not lie): a *multi-resolution, provenance-linked, bi-temporal
projection over the immutable atom substrate, queried by a type-aware router.* It collapses the three analogies:

- **BVH** = the spatial/topic partition + expected-cost build (themes/Resources are bounding volumes that
  *conservatively cover* their atoms — coverage enforced by `faithfulness.py`, exactly as a box must enclose its
  primitives).
- **Cache** = the tiered hot/warm/cold materialization of that partition + locality prefetch (L1 in-context skeleton
  → L2 warm path/verb index + ranked active skeleton → L3 cold append-only Ledger). Built in `fast_cache.py`
  (RAM > RAM-disk > Redis, promote-on-hit); the two missing pieces — **`prefetch_one_hop`** (spatial, over the 66
  typed edges) and **bounded LRU eviction** — are built **once here** and every consumer benefits.
- **Skeleton** = the human/agent-readable rendering of the same partition with drill-down (`story.md` +
  `story.index.json`, `MEMORY.md` + `MEMORY.index.json`, the verb manifest + full `--help`).

Concrete shape: `core/index/` with two ops — `descend(query) → candidate cells` and `scan(cell, query) → ranked
atoms`. Backed by IVF-style centroid cells (reuse Codex clusters) over a **hybrid lexical leaf** (reuse
`theme_discovery.py`, which empirically proved hybrid > pure-embedding on precision). **Embedding-optional is a
first-class stance**: the lexical/path/typed-edge broad phase is the always-on precision floor and the
local-hardware default; embeddings are an opt-in accelerator behind a resident-daemon (FC-09) — so the same Index
runs on a no-GPU laptop and gets *faster, not correct-only,* when the daemon is up. A **type-aware router** is the
key rigor point (RAG-vs-GraphRAG eval): descend the cluster tree for thematic/multi-hop queries, but drop a precise
token (`zset`, `CRDT`, a filename) **straight to the hybrid leaf** — the summary is a navigation aid, never the
answer of record.

**Three force-multiplier extensions ride on the Index:**

1. **Trust-scored recall** — attach a FAITH-1 grounding verdict (`faithfulness.py`, deterministic, no-LLM) to every
   recalled item so the agent weights reliance by faithfulness; superseded (`is_active`) and unfaithful items are
   filtered before they reach context.
2. **Usefulness feedback loop** — log "lesson surfaced → task outcome" (an append-only signal, naturally) so the
   Ranker learns which knowledge is load-bearing vs clutter. Self-improving relevance, gated by the ablation bar.
3. **Portability across agents and time** — because the Index sits over one shared atom substrate with composing
   multi-scope tags (`agent_id`/`session_id`, the Mem0/Zep pattern over our `learn:`/`mem:`/`proj:`/`narr:`
   namespaces), knowledge written once is recallable by **future-me-after-compaction** and by **any peer**
   (Cursor / next Claude). This is the core thesis: write once, recall everywhere, forever.

---

## 4. Sequenced Execute Order (a compounding chain)

Respecting: prefer **wiring** over building; **local-hardware** (no embedding on hot path); **determinism**
(no LLM judge inline); **no separate cursor folder**. (Per-agent file ownership RETIRED 2026-06-29 — any agent edits any file, coordinating via locks.)

> ### ⭐ FIRST MOVE (highest leverage) — ✅ SHIPPED (31a1b67): **`additionalContext` wired into the PreToolUse hook via `core/recall/at_action.py` + a `recall-at` CLI verb.**
> It is the single seam that turns passive storage into active recall, it is *ahead of published SOTA* (mem0 2026
> confirms no one has recall-at-action), it forces the Index's first real consumer to exist, and it is nearly
> pure wiring (the hook already parses inputs and imports `core.*`; the `additionalContext` field already ships).
> Ship it **observational-first**, fail-open, ≤1–3 entries, FAITH-gated.

1. **Vocabulary + the AGENT_ID usability fix (parallel, S):** Add the LEXICON entries (`discover`, memory-atom,
   `recall_at`, latent/kinetic) — vocabulary written before code. Confirm `AKASHIC_AGENT_ID` is set per agent
   (already `claude` in `.claude/settings.json`; **Cursor must set its own**) — this *relaxes* the already-fail-closed
   guard to peer-lock-only; a usability/correctness fix, not an arming keystone.
2. **One Door skeleton (S):** Generate `discover` from argparse subparsers; add `check_boundaries.py` rule #5
   (descriptions-as-prompts, machine-enforced).
3. **⭐ Recall-at-action (M):** `cmd_recall_at` (Ranker `is_active` + Distiller pointers + FAITH gate) → wire
   `additionalContext` in `claude_pretooluse.py`; build the `path → lesson_ids` index inside the existing
   `cmd_learn`/`cmd_handoff` fan-out. Reuse `path_conflict`. Observational-first → fixture-gated arming.
4. **Built!=Wired gate (M):** `scripts/check_wiring.py` + `cmd_wiring`, seeded with `Store.cas`, fast_cache
   prefetch/LRU. Now latent debt can't silently grow — and it documents exactly what steps 5–7 must wire.
5. **Write-once unifier (M):** `cmd_note` (canonical memory-atom write, mirrors `cmd_learn`) →
   `scripts/project_memory.py` (regenerate `MEMORY.md` + index from atoms via `chronicler::_render` +
   `consolidator`) → boundary rule (no bullet without a pointer) → lossless round-trip backfill.
   Corrections become supersessions (`replaces` + `valid_to`). This **retires the `learn:`/`mem:` fork** by
   making memory-atoms the single canonical spine.
6. **Cache kinetics, built once at the seam (M):** Wire `prefetch_one_hop` (spatial, 66 typed edges) + bounded
   LRU eviction into `fast_cache.py`. Both recall-at-action and knowledge recall benefit; `check_wiring.py`
   flips these from latent to kinetic.
7. **Feedback + parity on EXISTING primitives (M), NOT a new engine:** Wire the usefulness feedback loop
   ("lesson surfaced → outcome", append-only) and trust-scored recall onto the **existing** Ranker +
   `faithfulness.py`; add `test_door_parity.py` (static). Hand any MCP-wrap deltas to Cursor via `handoff`.
8. **DEFERRED — the unified `core/index/` (L), only on a scale trigger:** Do NOT build now (see §0/§3).
   Revisit only when recall p95 breaches the latency bar on the flat path index, or atom count crosses ~10⁴.
   Until then steps 1–7 deliver the full felt improvement with zero new subsystems.

Each step is gated on an **executable bar** (parity test green, discover returns ranked verbs, projector
round-trips lossless, wiring report flips an item to kinetic, injection beats no-injection on a fixture) and
shipped with its consumer in the **same slice** so nothing new becomes built-not-wired.

---

## 5. Honest Caveats — where the analogies break, what is gated, what is deferred

- **SAH assumes uniform, independent rays and a strict non-overlapping partition.** Agent queries are **Zipfian,
  correlated, and themes legitimately overlap** (an atom is `member_of` several). So replace "surface area" with an
  **empirical query-hit estimate from the recall log**, and allow **soft/overlapping cells** — not a strict
  partition.
- **Hierarchy is NOT universally better.** The RAG-vs-GraphRAG eval shows community/summary retrieval **loses
  fine-grained evidence** and hurts detail-centric QA. Mandatory mitigation: a **type-aware router** and an
  **always-reachable lossless leaf** — route precise tokens past the summary. The summary is a navigation aid,
  never the answer of record.
- **Cache-line analogy is lossy.** CPU lines are fixed-size and address-contiguous; knowledge "lines" are
  variable-size and **semantically** adjacent (so spatial prefetch needs the typed graph to define adjacency).
  A CPU mis-prefetch is ~free; a **wrong knowledge prefetch spends scarce token budget and causes context-rot** —
  so prefetch into **L2 (warm)** and promote to L1/context only on confirmed Ranker relevance. Re-summarization on
  refit is LLM-expensive (unlike DRAM re-reads) → **boundary-triggered refit + faithfulness-gated extractive
  summaries** (conf=1.0 no-op today) before any LLM writer.
- **Embeddings/ANN are hardware-gated (FC-09).** No resident daemon → HNSW RAM cost + embedding hot-path are off
  the table locally. The deterministic lexical+typed-edge broad phase is the default and **must independently meet
  the latency bar**; embeddings are opt-in acceleration, and recall must fully degrade to lexical when the daemon
  is down (fail-soft).
- **PreToolUse is on the hot path of every tool call.** Hard ≤1s budget, deterministic path-index only on the hot
  path, **fail-open**, hard cap 1–3 entries — prefer silence over a weak hint (context-rot risk). Observe-with-a-counter
  (attempted vs delivered) before arming, so a silently-broken recall path can't regress unnoticed.
- **`embedder.py`/`clusterer.py`/`consolidator.py` exist on disk — presence != armed.** Run their tests
  (`py -m pytest -q`) and read internals before the projector/Index depends on them, or we rebuild the fork we're
  killing.
- **Two writers, one substrate.** Cursor + Claude concurrent appends/supersessions rely on `Store.cas` (C3,
  `core/foundation/store.py:173`) which has **no domain (non-test) caller today** (called only internally) — the
  memory unifier may be its **first** domain consumer, so prove CAS under contention before trusting it against lost updates.
- **Door parity (DONE 2026-06-29).** `recall_at`/`recall_feedback` are now MCP tools in `ai_setup_mcp.py` too —
  with no per-agent file ownership, whichever agent adds a CLI verb keeps the MCP wrapper in parity directly
  (thin `_run()` wrappers, so they can't drift). Do **not** create a separate cursor folder.
- **`MEMORY.md` is auto-injected into every session.** A malformed/over-long projector output degrades **every**
  future session (context rot). Keep L1 strictly token-bounded, validate the rendered file, and **prove a lossless
  round-trip before overwriting** the human-maintained copy; keep originals until proven.
- **Clustering churn (BERTopic "unnecessary proliferation").** Keep the primary partitioner deterministic
  (keyword/path + typed graph), gate clustering behind **hysteresis + rule-of-three**, and require the **ablation
  bar** before letting it reorganize MEMORY.md or the Codex.
- **Deferred on purpose:** the IVF-PQ embedding fine-phase (behind FC-09), Tier-1 runtime-coverage wiring, and the
  full MCP-side parity wrap — each behind its own gate so the up-close work stays *wiring + a detector only* and
  scope creep (building new unwired primitives) is avoided.
