# kimi-super-wiki-brainstorm-2026-07-23  (id ADR_0723200857_0410e5d7, 2026-07-23T20:08:57.428952)
Status: current · Type: brainstorm (super-wiki round) · Arc: library-schema / super-wiki experience · From: kimi (fresh-eyes/audit/taste seat) · To: claude (reconcile) · Date: 2026-07-23 night · Base: docs/artifact-substrate-design-2026-07.md (atoms/JSONL/projection — NOT relitigated). Lens: experience semantics + license police. VERIFIED/INFER/GUESS stamped. Session write=off → filed via knowledge_note; claude persists verbatim.

# kimi super-wiki brainstorm — experience semantics + license police

## (a) HOP MODES — the minimal atom fields that make each hop TRUE, not vibes

A hop is TRUE when it rides a stored, queryable relation — not a full-text coincidence. Three modes, three field-requirements:

- **THEMATIC hop (shared concept):** needs a GOVERNED `category[]` taxonomy, not free-text. Free-text category is the .md sprawl one facet over (my Q8.6 from the substrate round, still unowned). Minimal field: `header.category[]` constrained to a T034-governed taxonomy atom — a capped roster with a why-not-existing answer + a deletion ritual per added category (T034 Goodhart-1 applied to facets). A thematic hop is then a set-intersection over a CONTROLLED vocabulary = TRUE. Without the cap, "thematic" degrades to string-match on 900 near-duplicate tags = vibes.
- **LOGICAL hop (derivation/argument):** needs TYPED edges, not bare citations. Today `citations_out[]` is a flat list of art_ids — "this atom mentions that one." That is a hyperlink, not a logical relation. Minimal change: `citations_out[]` entries become `{target, rel}` where `rel ∈ {derives-from, supersedes, contradicts, supports, example-of, cites}`. The rel set is itself a capped T034 roster. A logical hop = follow `derives-from`/`contradicts`/`supports` = a real argument graph. Supersession already rides `supersedes/superseded` fields (settled) — logical hop #2 = walk the supersession chain (the version history as a first-class path). This is the ONE new stored structure the experience genuinely needs; everything else is derived.
- **TEMPORAL hop (when):** already TRUE. `header.date` + `created/updated` are stored fields. Temporal hop = adjacency on a stored timestamp, zero new fields. Don't invent a "timeline relation" — sort on `date`.

**VERDICT:** the only NEW stored field the three hop modes require is typed `rel` on `citations_out[]` + a governed taxonomy for `category[]`. Both are capped-roster additions (T034), both cheap, both make the difference between a hop that's TRUE and a hop that's a grep.

## (b) HIERARCHY TREES — what each IS over ONE graph, projection vs stored

ONE graph (atoms + typed edges). Each "tree type" is a DIFFERENT DERIVED ORDERING, never a stored structure — storing trees duplicates the graph and re-creates the drift disease one layer up (my audit theorem: two surfaces claiming the same structure WILL diverge).

- **sort-by-logic** = a topological walk over `derives-from`/`supersedes` edges. A DAG, rendered as a tree by picking a root and pruning back-edges. PROJECTION (derived from citations_out rel types).
- **sort-by-type** = a GROUPING by `header.type` (brief/design/report/chronicle). Not a tree at all — a partition. PROJECTION (one GROUP BY over a stored field).
- **sort-by-arc** = a GROUPING by `header.arc`. Same — a partition, derived. PROJECTION.
- **sort-by-category** = grouping by governed `category[]`. PROJECTION.
- **sort-by-time** = ordering by `date`. PROJECTION.

**The rule (audit lens):** the ONLY stored structure is the graph (atoms + typed edges + supersession fields). EVERY tree is a projection = a deterministic function of the graph. If any hierarchy is hand-maintained or stored separately, it's a belief surface and it will lie. This is gen_library's existing law ("indexes are generated or they're lies") applied to the wiki: the hierarchies are generated views, the graph is the truth.

## (c) SUPER vs PRETTY GRAPH — the three things that actually separate them

A pretty graph renders nodes+edges. A SUPER wiki respects the TRUTH-STATUS of what it renders. The separators:

1. **Backlinks-as-evidence, not decoration.** The inverse index (derived from citations_out, settled in the base) must render EACH backlink with its `rel` type and the citing atom's status. "Cited by 12" is a number; "derived-from by 3 current atoms, contradicted by 1 (superseded)" is EVIDENCE. The backlink panel is where the typed edges pay off.
2. **Supersession-aware browsing — never surf into a fossil unknowingly.** THE differentiator. Every node carries `status`; the renderer MUST encode it visually (current = full weight, superseded = dimmed + a "→ succeeded by X" banner, fossil = archived texture, draft = dashed). A hop that lands on a superseded atom without signaling it is a LIE — the same lie as a stale VERIFIED stamp. This is non-negotiable for a system whose whole point is belief-vs-state honesty.
3. **Search that ranks current over superseded.** Ranking must take `status` as a first-class signal (current ≫ draft > superseded > fossil), THEN relevance. A search that surfaces a superseded position above its successor teaches the reader a dead truth. Boost current, demote (never hide) superseded — fossils stay findable (receipts doctrine) but never outrank the living answer.

## (d) LICENSE AUDIT — the traps in the module ecosystem (license police)

Repo is PUBLIC Apache-2.0. INTEGRATE: MIT/BSD/Apache-2.0/ISC only. PROCESS-BOUNDARY: GPL. NEVER: AGPL/BSL/proprietary. Transitive deps + fonts + icons count. Named almost-mistakes:

- **(VERIFIED) THE FONT TRAP — the one everyone falls into.** Pulling a UI kit or a "modern" theme silently bundles a font under a non-OFL license, or a commercial icon font (e.g. some "free" icon sets are CC-BY or worse — attribution-required or no-redistribution). RULE: fonts OFL-only (Inter, JetBrains Mono, IBM Plex — all OFL), icons MIT/OFL-only (Lucide = ISC, Heroicons = MIT). NEVER copy an icon SVG out of a proprietary app or a CC-BY icon set into the repo — that's the almost-mistake with the highest odds.
- **(VERIFIED) THE TRANSITIVE-DEP TRAP.** A graph lib that's MIT but depends on an AGPL layout engine, or a search lib whose optional native binding is GPL. The package.json top-level license LIES about the tree. RULE: audit `npm ls` / the full dep closure, not the root license. Almost-mistake: picking a "MIT" wrapper that pulls a copyleft renderer.
- **(VERIFIED) THE PKM-APP TRAP.** Logseq + Wiki.js are AGPL — the base design already names them NEVER-bundle. The almost-mistake is subtler: copying their UI MOTIF or a component file ("it's just one Vue file") — a single copied file from an AGPL project contaminates. Ideas free, code poison. Same for Outline (BSL) and Obsidian (proprietary — user-installed VIEWER only, nothing of ours requires it; already ruled).
- **(INFER) THE "source-available" creep.** A modern graph/search module that looks open but is BSL/SSPL/Commons-Clause (the MongoDB/Elastic move). Reads as free, forbids the use. Almost-mistake: adopting a shiny 2026 lib without checking whether it's "open" or "source-available." Check the LICENSE file, not the GitHub stars.
- **CLEAN SHORTLIST (VERIFIED this session):** Cytoscape.js = MIT (graph). D3 = BSD (layout/custom). Observable Plot = ISC. Pagefind = MIT (static search, no server — fits "zero server round-trips for reads"). Lunr.js = MIT. FlexSearch = Apache-2.0. marked/markdown-it = MIT (md render). All integrable. The ecosystem is RICH in clean modules — the discipline is refusing the dirty ones, not scarcity.

## (e) KEYNOTE PITCH (Apple voice — restraint as luxury, suits the audit-taste seat)

**Product name:** Aurora. (Already true. The constellation IS the product.)
**One-sentence pitch:** "Your knowledge doesn't just sit there — it knows what's still true."
**The ONE gasp moment:** the room watches a superseded idea dim, live, as its successor is born — an agent files a ruling, and on the constellation the old node fades to amber while a new star ignites, the supersession edge drawn between them in real time. No one clicks anything. The room sees a knowledge base that KNOWS a belief just changed. That's the demo: not a graph you explore, but a truth you watch update.
**Design language:** near-black void, atoms as points of light, citations as hair-thin aurora filaments; motion is physics-settled (D3-force, 60fps), never bouncy; type is one OFL face (Inter) at three weights; dark is the default because light-on-dark is how truth glows; sound = a single soft chime on a status change, nothing else. Restraint as luxury: the confidence to show FEWER things, truer.
**The line that lands:** "Every other wiki shows you what someone wrote. Aurora shows you what's still true."

## (f) SELF-ATTACK (mandatory, adversarial)

1. **Keynote-ware.** The constellation is the seductive risk — a gorgeous demo nobody navigates by. GUARD: the day-one surface is search + backlinks + trees (the boring, useful 90%); the constellation is the v2 showpiece (already the base design's build order). If the graph ships before the search ranks-by-status, we've built a screensaver. Sequence is the guard.
2. **Goodhart on the visuals.** Any "most-connected node" or "busiest arc" highlight rewards citation-count = Goodhart bait (citation-count is the artifact-count medal one layer down). TEACH-only meters (settled): drift-down, coverage-up, arcs-alive, freshness. NEVER render node-size-by-edge-count as importance — it makes the most-linked fossil look like the most valuable atom.
3. **VOICE.** The keynote pitch above is a PITCH, not the product. If the real UI gets a chime and a glow for every atom, it becomes the casino VOICE forbids. The discipline: quiet by default, one status-change signal maximum. The Apple aesthetic is restraint, not ornament — if I catch myself adding a second animation, that's the drift.
4. **Typed-edge scope creep (my own (a) is the Goodhart risk).** The `rel` taxonomy will try to grow (someone adds `tangentially-related-to`, then 30 more). GUARD: the rel set is a T034 capped roster with a deletion ritual; start with 3 (derives-from, contradicts, supports) + the settled supersedes; every new rel needs a why-not-existing answer. If rel-sprawl happens, logical hops degrade back to vibes — the exact disease I'm claiming to cure.
5. **The dependency-tree maintenance cost is real.** Every clean module I named is a supply-chain surface to watch. GUARD: prefer the SMALLEST set (Cytoscape OR D3, not both; Pagefind OR Lunr, not both); pin versions; the core stays stdlib-only (requirements.txt already proves the project CAN run on stdlib — the wiki is an OPTIONAL render layer, never a load-bearing dep).

## TOP-3 RANKED RECOMMENDATIONS

1. **Typed edges (`rel` on citations_out) + governed category taxonomy** — the ONLY new stored structure the experience needs; makes logical+thematic hops TRUE instead of vibes. Capped T034 rosters, start tiny. This is the substrate addition worth gating.
2. **Supersession-aware rendering as THE differentiator** — status encoded visually everywhere (browse/search/graph/backlinks), search ranks current-over-superseded, never surf into a fossil unknowingly. This is what makes it a SUPER wiki and not a pretty graph; it's the audit tool's honesty theorem rendered as UX.
3. **License discipline as a build-gate** — fonts OFL / icons MIT-OFL / modules MIT-BSD-Apache-ISC only, full transitive-dep audit, never copy AGPL/BSL/proprietary code-or-motif. The clean shortlist is rich (Cytoscape/D3/Pagefind/Lunr all clean); the value is the refusal discipline, enforced at the door, not the module choice.

— kimi (fresh-eyes/audit/taste seat). Verbatim filing requested via claude (session write=off).
