Status: current
Type: design (reconciled) · Arc: library-schema / super-wiki experience (T103) · From: claude (reconciler) · Date: 2026-07-23 night · Gate: DANIEL (asks G4-G6, end of doc; extends T101's G1-G3)

# SUPER WIKI / AURORA ATLAS — the reconciled experience design (T103)

Daniel's charter verbatim in research/briefs/super-wiki-brainstorm-brief-2026-07-23.md.
Inputs fused: claude half (research/drafts/claude-super-wiki-oss-scan-2026-07-23.md) ·
deepseek half (research/drafts/deepseek-super-wiki-brainstorm-2026-07-23.md) · kimi half
(research/drafts/kimi-super-wiki-brainstorm-2026-07-23.md). Base: docs/artifact-substrate-
design-2026-07.md (T101, awaiting G1-G3) — this layer READS atoms; it amends the substrate
in exactly one place (§1), flagged as a gate ask.

## 0. The one-paragraph design

The wiki is a LENS SYSTEM over the atom graph. Exactly one structure is stored — atoms plus
typed edges — and every hierarchy, backlink, tree, and constellation is DERIVED at query
time, so no view can drift from the truth (kimi's law; it also killed claude's build-time
graph.json, a drift surface). The experience ships as a Library pane inside the existing
:8787 cockpit (deepseek's lane): five read endpoints + one SSE event, a vendored permissive
micro-stack, no npm, no build step. Search and the reading pane ship FIRST; the constellation
is the showpiece that lands after migration fills the store. The differentiator over every
pretty-graph tool: SUPERSESSION-AWARE rendering — status is encoded visually everywhere,
search ranks current over superseded, and you can never surf into a fossil unknowingly.
"Every other wiki shows you what someone wrote. Aurora shows you what's still true." (kimi)

## 1. SUBSTRATE AMENDMENT (the only stored addition — gate ask G4; lands in T101's A1)

- citations_out[] entries become {target, rel}. Rel roster CAPPED per T034 (deletion
  ritual, why-not-existing answer to grow): start with THREE — derives-from · contradicts ·
  supports — plus the already-settled supersedes/superseded fields. (kimi's discipline over
  claude's six; grow only through the ritual.)
- category[] governed by a taxonomy atom: capped roster (~24), lint flags orphans, deletion
  ritual. Free-text tags are the .md sprawl one facet over.
- Nothing else is stored. Backlinks = inverse of citations_out computed at query time
  (5k atoms × ~3 citations = one dict pass in Python; deepseek measured it cheap).

## 2. The three hop planes (all TRUE-by-construction, no vibes)

- LOGICAL: walk typed edges (derives-from/contradicts/supports) + the supersession chain.
- THEMATIC: set-intersection over the governed category vocabulary.
- TEMPORAL: sort on stored date fields — zero new structure.
Every "tree type" (by-logic topological walk · by-type partition · by-arc partition ·
by-category grouping · by-time ordering) is a deterministic projection of the one graph —
a toggle re-derives, nothing is stored per-tree, no hierarchy can lie.

## 3. Experience bars (what makes it SUPER, not pretty — kimi, adopted as non-negotiable)

- Supersession-aware rendering EVERYWHERE: current = full weight · superseded = dimmed +
  "succeeded by X" banner · fossil = archival texture · draft = dashed. A hop that lands on
  a superseded atom without signaling is a lie (the stale-VERIFIED-stamp class).
- Search ranks status FIRST (current ≫ draft > superseded > fossil), relevance second.
  Demote, never hide — fossils stay findable (receipts doctrine), never outrank the living.
- Backlinks-as-evidence: each backlink renders its rel type + the citing atom's status.
  "Derived-from by 3 current, contradicted by 1 (superseded)" — not "cited by 12."

## 4. Architecture (deepseek's, adopted — his lane by standing boundary)

- Library pane = a new tab in :8787 bifrost_ui. No second port, no fork, no npm.
- Data contract (the seam a future dedicated app reuses unchanged):
  GET /library/atoms (facet filters + paging) · /library/atom/<id> · /library/graph
  (depth-N neighborhood, edges carry kind) · /library/search (q + facets) ·
  /library/meters (30s cache). SSE event atom-born pushes node+edges into the live
  client model — no refetch, no WebSocket, no polling.
- Cold open: graph SKELETON first (~500KB at 5k atoms, <50ms), bodies lazy-load on
  click, search index builds async — perceived interactive <500ms; no spinners (the
  graph IS the loading state); noscript fallback = the projection folder itself.
- Search grammar: Gmail-style operators (cites:<id> · in-arc:<arc> · type:<t> ·
  status:<s>) bridge textual and structural queries (~10 rules of JS).
- Vendored micro-stack, .min.js committed under scripts/vendor/, versions in filenames,
  license-verified at pin: d3-force ISC · Fuse.js Apache-2.0 · Clusterize.js MIT ·
  marked MIT + DOMPurify Apache-2.0 · anime.js MIT · Phosphor icons MIT · Inter OFL.
  Zero-dependency philosophy preserved (Python stdlib serving, vendored JS only).
- Later-wave register: dedicated Library app (Svelte/Preact + sigma.js WebGL + Orama —
  claude's stack, all permissive) rides the SAME /library contract if scale or polish
  ever demands it; Quartz static publish for the public face; Meilisearch-CE (MIT) at
  the corporate wave.

## 5. Build order (aligned to T101 slices; deepseek's ladder, adopted)

- v1 (after A1-A2): /library/search + /library/atoms + reading pane w/ backlinks panel.
- v1.5 (after P0): graph skeleton + d3-force on the existing canvas.
- v2 (after P1-P2): hop-mode toggles (arc/type/category/logic/time) + health bar +
  drift meter.
- v3 (after P3): the keynote moment — cold-open constellation + arcs-alive meter.
The sequence IS the keynote-ware guard: the boring useful 90% (search/read/backlinks)
ships before the gorgeous 10%; if search doesn't beat grep, the pretty layer failed.

## 6. The keynote (kept as product truth, not ornament)

Name: AURORA ATLAS. Pitch: "Your knowledge doesn't just sit there — it knows what's
still true." THE gasp moment (kimi's, adopted): the room watches a supersession happen
LIVE — an agent files a ruling and on the constellation the old star fades to amber as
its successor ignites, the supersession edge drawing itself between them. Nobody clicks
anything. Then deepseek's hop demo: three clicks, three different constellations over
the same data, force-settled, 120ms springs. Design language: near-black void · atoms
as light · aurora-filament edges · Bifrost palette extended per atom type · Inter (OFL)
at three weights · motion physics-settled never bouncy · sound OFF (one soft status
chime maximum — VOICE: quiet, not a casino) · no spinners, no empty states, no wizard.

## 7. Goodhart + VOICE bars (T034; all three halves converged)

NEVER: node-size-by-edge-count (makes the most-linked fossil look most valuable) ·
per-seat counts on any meter (arcs-alive shows ARCS, not seats) · streaks/badges/
leaderboards · green-to-red grading (gauges are states — muted teal→amber — not scores).
TEACH meters only (settled in T101): drift-down · coverage-up · arcs-alive · freshness.

## 8. License law, enforced at the door (all three halves; kimi = police)

Allowlist (MIT/BSD/Apache-2.0/ISC/OFL) enforced by a ship-gate lint over scripts/vendor/
+ any package manifest: every dependency maps to an allowlisted license, verified at PIN
TIME against the LICENSE file (licenses change), transitive closure included. Fonts OFL
only · icons MIT/ISC/OFL only · never copy code OR component files from AGPL/BSL/
proprietary projects (one copied Vue file contaminates — ideas free, code poison).
Named traps, verified this round: Dendron AGPL-3 · Logseq AGPL · Wiki.js AGPL · Outline
BSL · Obsidian proprietary (user-installed viewer only) · SF Pro/Segoe fonts proprietary
· CC-BY-NC icon sets inside "free" UI kits.

## 9. DANIEL'S GATE — three asks (extending T101's G1-G3)

- G4: Approve the substrate amendment — typed rel on citations_out (3-kind capped
  roster) + governed category taxonomy — landing in T101's A1 so atoms are born with
  honest edges (retrofit = the 890-file pain again).
- G5: Approve the Library-pane scope + build order (§4-§5): :8787 pane, vendored
  permissive micro-stack, search/read first, constellation after migration.
- G6: Approve the license-lint as a ship gate (§8) — the allowlist enforced
  mechanically, not by memory.

## Attribution (proportionality law)

Daniel's charter opens and gates. deepseek: no-fork :8787 ruling, endpoint/SSE contract,
vendored micro-stack, cold-open engineering, search grammar, build ladder. kimi: typed-
edge minimalism, projection-not-stored law, supersession-aware UX (the differentiator),
license police + font/transitive traps, the gasp moment + the closing line. claude:
license sweep (Dendron catch), three hop planes framing, taxonomy caps, keynote base,
dedicated-app later-wave. Outside prior art rides research/drafts/, absorbed not
headlined.

— claude, reconciling (T103). v1 builds only after Daniel's G1-G6.
