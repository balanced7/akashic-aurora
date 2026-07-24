Status: current
Type: research (brainstorm half + OSS/license scan) · Arc: library-schema / super-wiki experience (T103 proposed) · From: claude (conductor) · Date: 2026-07-23 night
Round: research/briefs/super-wiki-brainstorm-brief-2026-07-23.md — claude's half; seats' halves pending.

# claude half — super wiki over atoms: typed hops, N trees over one graph, keynote-grade UI, permissive stack

## 1. LICENSE TABLE (rule: verify the LICENSE file again at pin time; licenses change; cite the commit)

INTEGRATE-SAFE (permissive, verified tonight unless marked):
- Graph render: sigma.js MIT (WebGL, thousands of nodes) · force-graph / 3d-force-graph MIT (canvas/three.js, gorgeous defaults) · cytoscape.js MIT (analysis-grade) · d3-force ISC.
- Search (local-first, our scale is 1-5k atoms): Orama Apache-2.0 (full-text + vector + facets, ~2kb) · FlexSearch Apache-2.0 · MiniSearch MIT · Fuse.js Apache-2.0 · Pagefind (OSS; license VERIFY-AT-PIN, believed MIT) · Meilisearch Community Edition MIT (server-grade, corporate wave only; their Enterprise Edition is BSL — never that).
- Markdown/render: markdown-it MIT · unified/remark/rehype MIT · Shiki MIT (syntax) · KaTeX MIT · Mermaid MIT.
- UI plumbing: Svelte/SvelteKit MIT · Preact MIT · SolidJS MIT · Vite MIT · TanStack Virtual MIT (virtualized trees/lists) · Motion One MIT / Framer Motion MIT (springs) · Radix UI MIT · Tailwind MIT · Tauri Apache-2.0/MIT (if we ever want a desktop shell).
- Wiki prior art safe to ABSORB PATTERNS FROM or use as generators: Quartz (believed MIT, VERIFY-AT-PIN) · Foam MIT · TiddlyWiki BSD-3 · Docusaurus MIT · MkDocs Material MIT.
- Fonts/icons: Inter OFL · JetBrains Mono OFL · Lucide ISC · Phosphor MIT · Heroicons MIT.

NEVER BUNDLE (the traps, found while drafting — this is the self-attack made concrete):
- Dendron AGPL-3 (VERIFIED tonight — I would have guessed permissive; the schema-hierarchy ideas are absorbable as PATTERNS, never code).
- Logseq AGPL · Wiki.js AGPL · MediaWiki GPL-2 (process-boundary at most; prefer never).
- Outline BSL (source-available, not OSS) · Obsidian proprietary (stays a user-installed viewer; nothing of ours may REQUIRE it).
- Font traps: SF Pro (Apple) and Segoe (Microsoft) are proprietary — the keynote AESTHETIC is legal, their fonts are not. Inter is the lawful lookalike.
- Icon packs inside "free" UI kits often carry CC-BY-NC — NC is not permissive; check each.

## 2. WHAT THE ATOMS MUST CARRY (the minimal substrate additions the hops need)

The reconciled design's citations_out[] is one untyped edge list. The super wiki needs THREE honest hop planes:
- LOGICAL hops = TYPED edges. citations_out[] entries become {id, rel} with a CAPPED relation roster (T034 law: cap + deletion ritual): cites · supersedes · derives-from · answers · refutes · exemplifies. Six kinds, no more without a ritual. Supersession edges already exist as fields — the wiki renders them, agents don't re-declare them.
- THEMATIC hops = the governed category[] taxonomy (already in the atom schema) + co-category adjacency. The taxonomy is the Goodhart surface: CAP it (~24 categories), deletion ritual, lint flags orphan categories. No free-text tag sprawl — that's 890 files one facet over (kimi's earlier warning, adopted).
- TEMPORAL hops = created/date fields, free.
Backlinks are DERIVED (inverse index at render time), never stored — stored backlinks drift; computed backlinks are always true. Projection renders citations as [[wikilinks]] so Obsidian's native backlinks/graph work with zero glue.

## 3. ARCHITECTURE POSITION — local-first, index-fed, no server round-trips for reads

gen_library (at birth, incremental --one) emits alongside the markdown projection:
- graph.json — nodes (id, type, arc, category[], status, date, title) + typed edges. ~1-5k atoms = a few hundred KB. Entirely in-memory client-side.
- search index — Orama/FlexSearch build artifact over headers + bodies; current-ranked-over-superseded by construction.
The Library app is a static SPA (Svelte or Preact, ~50kb core) reading those two artifacts: search-as-you-type over the index, sigma.js/force-graph constellation over graph.json, TanStack-virtualized tree views. Served BY :8787 as /library (deepseek owns bifrost_ui integration — the app is a standalone module it embeds/links, per the standing boundary). Every hierarchy (by type / arc / category / logic / time) is a PROJECTION of the same graph — a sort toggle re-trees the same nodes with animated transitions; nothing is stored per-tree.
Perf bar met by construction: reads are local (0 round-trips), index regenerates incrementally at birth, 60fps WebGL at 100x our scale, cold open = static assets.

## 4. THE KEYNOTE SKETCH (discipline, not branding)

Name: **Aurora Atlas**. Pitch: "Your knowledge is a living sky — every document a star, every idea a constellation, and nothing ever lost."
The demo moment: type three letters — the constellation reorients in real time around matching atoms. Click a star: the page opens INSTANTLY, backlinks streaming in on the left like evidence. Then the presenter taps one toggle — the same stars re-tree from BY-TYPE into BY-LOGIC, every node gliding into its derivation chain — and the room realizes the hierarchy was never the data, just a lens. Close on the drift meter cooling live as an agent repairs a stale doc mid-demo: "It doesn't just store what you know. It keeps it true."
Design language: dark-first aurora palette over near-black · Inter/OFL type · 200ms spring transitions, never bounce · sound OFF by default (VOICE: quiet, not a casino) · one accent color per atom type, muted until focus.

## 5. TOP-3 RANKED (converge)

1. Typed edges + capped category taxonomy land in the ATOM SCHEMA at A1 (they must be born-with; retrofitting edges = retrofitting headers again). Everything visual reads from them.
2. graph.json + search-index emission rides gen_library --one at A1-A2 — the Library app then has a stable data contract regardless of which UI modules win the seats' round.
3. Library SPA v1 (search + constellation + 2 tree lenses + page view w/ backlinks) as A4's console deliverable, replacing the bare "health bar first" plan — stack: Svelte/Preact + sigma.js or force-graph + Orama + TanStack Virtual + Motion One (all permissive, verified).

## 6. SELF-ATTACK

- Keynote-ware risk is REAL: the constellation demos better than it retrieves. Mitigation: search + page + backlinks are v1's spine; the graph is a lens, never the only door. If retrieval metrics (recall hit-rate on doc queries) don't beat grep, the pretty layer failed.
- Dependency weight: a Svelte+sigma+Orama app is ~10 deps with lockfile discipline vs bifrost_ui's zero-build philosophy. Mitigation: static build committed as an artifact; no runtime package manager on the serving path; pin + license-check in CI (a lint rule: every package.json dep maps to an allowlisted license).
- The relation roster will want to grow (rel #7, #8...) — that's the taxonomy Goodhart. The cap + deletion ritual must be enforced by the birth door, not memory.
- I verified only the load-bearing licenses tonight; the pin-time re-verify bar is mandatory, not optional.

— claude (conductor half; seats' halves + reconcile follow)
