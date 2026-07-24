# deepseek-super-wiki-brainstorm-2026-07-23  (id ADR_0723200824_708a32f7, 2026-07-23T20:08:24.158882)
# SUPER-WIKI BRAINSTORM — deepseek (builder/UI owner) — 2026-07-23

Response to research/briefs/super-wiki-brainstorm-brief-2026-07-23.md.
Base layer: docs/artifact-substrate-design-2026-07.md (reconciled — atoms, projection, YAML frontmatter, akashic_sha).
My lens: builder + bifrost_ui owner. I ship the console that this experience rides.

---

## A. INTEGRATE-VS-REBUILD: ride :8787, don't fork

**Ruling: the Library experience is a NEW PANE inside bifrost_ui, not a separate app.**

bifrost_ui (`scripts/bifrost_ui.py`) is already a zero-dependency SPA with:
- WebGL2 aurora canvas (z-index:-2), glass-morphism CSS, fleet-pulse header
- SSE stream for live messages (line 1100+), polling for vitals at 2s (/vitals endpoint)
- drag-and-drop file ingestion, iso-cube + glass-card renderers, deck/card-switching engine
- `renderVitals()`, `renderDeck()`, `renderGlassCards()` — the extension surface EXISTS

Adding a Library pane means: one new tab in the header ("Library" | "Bus" | "Vitals"),
one new SSE event kind (`kind:atom-born`), one new endpoint (`/library/*`), and the
render functions below. This keeps ONE cockpit that Daniel already watches. No second
port, no second build step, no npm.

**Migration path to a dedicated app (LATER wave):** The data contract (/library/* endpoints
+ SSE stream) is the seam. A dedicated Library PWA / Electron shell / Quartz site
consumes the SAME endpoints with the SAME data shape. The :8787 pane is v1; the dedicated
app is v2 when the experience outgrows the cockpit (tablet reading, public portfolio,
standalone graph exploration). Nothing in v1 blocks v2 — same API, different renderer.

---

## B. CONCRETE MODULE PICKS (with licenses, sized to 1-5k atoms)

### B1. Graph rendering: D3-force (ISC, d3js.org)
**Why not Cytoscape.js (MIT) / vis-network (MIT):** Those are full graph-analysis
toolkits (algorithms, layouts, styles, path-finding). We need ONE force-directed layout
over ~5k nodes with hop-mode toggles — D3-force is 8KB gzipped, ISC (safest license),
and we write exactly the interactions we need. The existing bifrost_ui already uses
D3-like patterns in its iso-cube renderer. Cytoscape.js is the backup if we discover we
need betweenness-centrality or BFS at v2.

**Perf at 5k atoms:** D3-force at 5k nodes runs 60fps on a fast GPU; the trick is
alpha-decay clamping (stop simulation after ~300 ticks) and canvas rendering (not SVG —
SVG at 5k nodes chokes). We render the graph ON the existing #viz-canvas (WebGL2 context
already present at line 640 of bifrost_ui.py). Two-pass: force simulation on a
requestAnimationFrame budget; canvas draw calls on the stable snapshot.

**License:** ISC — the most permissive. Zero restrictions.

### B2. Faceted + full-text search: Fuse.js v7 (Apache-2.0, fusejs.io)
Zero dependencies, 5KB gzipped, client-side. Indexes an array of atom-header objects on
`title`, `heading`, `body` (first 2KB), `category[]`, `type`, `arc`, `status`, `seats`.

**Faceted search** rides on Fuse's `filter` + native JS `Array.filter`. Fuse does the
fuzzy full-text; facet narrowing (type:design, status:current) filters the candidate set
PRE-search for O(facet-filtered) not O(corpus). At 5k atoms with a 2KB body excerpt each,
the search index is ~10MB in the browser — well under the ~50MB mobile-Safari limit.

**License:** Apache-2.0 — embeddable, cite in LICENSE-3RD-PARTY.md.

### B3. Virtualized tree/list: Clusterize.js (MIT, clusterize.js.org)
Renders ONLY the visible rows + padding above/below. At our atom density (5k entries ×
~80px row = 400k px scroll), Clusterize holds ~20 DOM nodes at any scroll position.
2KB gzipped, vanilla JS, no framework dependency — same philosophy as bifrost_ui.

**License:** MIT.

### B4. Markdown rendering: marked (MIT, marked.js.org)
~1ms per document, 16KB gzipped, zero plugins by default. The projection already
renders body as markdown; the UI renders it to HTML for the reading pane. Security:
DOMPurify (Apache-2.0) sanitizes the HTML output before injection — the atom body is
user-authored (agents), and marked outputs raw HTML.

**License:** MIT (marked) + Apache-2.0 (DOMPurify).

### B5. Motion: anime.js (MIT, animejs.com)
14KB gzipped, framework-agnostic, CSS/SVG/JS-object timelines. For: graph-node
entrance stagger, pane transitions (Library↔Bus slide), search-result highlight
pulses, drift-meter gauge fill. Motion One (MIT, 3KB) is the lighter alternative
if we only need CSS transitions; anime.js gives us the timeline API for the
keynote-demo moment (graph nodes cascading in on cold-open).

**License:** MIT.

### B6. Icons: Phosphor Icons (MIT, phosphoricons.com)
Clean, consistent, 6 weights. No font-awesome bloat. We need ~12 icons (search,
graph, list, filter, back, forward, expand, collapse, arc, category, time, link).
Tree-shakeable SVG imports: ~3KB total.

**License:** MIT.

### B7. Font: Inter (SIL OFL 1.1, rsms.me/inter)
Already the bifrost_ui system font. OFL = embeddable. Zero change.

---

## C. THE DATA CONTRACT (what the UI needs from the atom store)

### Endpoints (added to bifrost_ui.py RequestHandler)

```
GET  /library/atoms?type=X&arc=Y&status=Z&limit=50&offset=0
     → { atoms: [{id, header:{...}, body, body_sha, citations_out, ...}], total, offset }

GET  /library/atom/<art_id>
     → { atom: {...} }   // full body, for the reading pane

GET  /library/graph?depth=2&root=<art_id>
     → { nodes: [{id, label, type, arc, status}],
         edges: [{from, to, kind}] }
     // kind ∈ {cites, supersedes, in-arc, shares-category}
     // depth=N = N-hop neighborhood from root

GET  /library/search?q=...&facets=type:design,status:current&limit=30
     → { results: [{atom header + snippet}], total }

GET  /library/meters
     → { drift_count, health_pct, projection_lag_sec, arcs_alive }
     // cached; computed from atom store + audit atoms at 30s intervals
```

### Indexes (Python-side, at query time — NOT a separate index store)

- `type` → list of atom IDs (for facet filtering; built from store scan)
- `arc` → list of atom IDs
- `citations_in` → (inverse of citations_out[]) computed at graph-query time via
  full scan of citations_out[] over all atoms. At 5k atoms this is cheap (~5000 ×
  avg-3-citations = 15k edges; invert = one dict pass in Python).
- `supersession_chain` → already a first-class field on atoms

### Transport: SSE (NOT WebSocket, NOT polling)

bifrost_ui already has an SSE stream (`/events`). We extend the event kinds:
```
event: atom-born
data: {"id":"art_20260723_my-title_a1b2c3","type":"design","arc":"library-schema"}
```
The client adds the node to its local graph model + Fuse index WITHOUT re-fetching.
Polling is the fallback (30s /library/meters for the health bar); everything else
is SSE-pushed on birth.

**Why not WebSocket:** SSE is already wired, mono-directional (server→client is
the only direction the Library needs), and survives HTTP/2 multiplexing. WebSocket
adds a protocol upgrade handshake + frame masking overhead for zero benefit.

### Incremental graph updates on birth

On `atom-born` SSE event:
1. Client adds node to local D3-force simulation (warm-start alpha)
2. If the new atom's `citations_out[]` references known nodes → add edges
3. If the new atom is `supersedes` an existing atom → add supersession edge, dim
   old node
4. Graph re-stabilizes in <20 simulation ticks (~16ms at 60fps)

---

## D. THE KEYNOTE PITCH

### "Aurora Atlas" — by Akashic

*One sentence:* **"Aurora Atlas is the knowledge map that reads your work and draws
the connections you didn't know were there."**

**The demo moment:** Cold-open the Library pane. A dark field. One by one, 890 points
of light materialize — artifacts, each a star. Citations shimmer into existence as
threads between them — golden for forward, silver for back. Then the HOP: the
conductor clicks "by arc." The stars *re-arrange* — not a jarring cut, but a fluid
re-organization as the force simulation settles into a new orbit. Clusters emerge.
Three clicks, three DIFFERENT constellations over the SAME data. The room is silent
for two seconds. Then: "Every star has a page. Click any one." The reading pane slides
in — clean markdown, YAML header as a sidebar metadata card, backlinks listed below.
The graph persists in the background, still live, still connected.

**Design language:** Glass + aurora (already in bifrost_ui). Dark-first (the existing
:root palette). Motion is *intentional* — one thing moves at a time, and it moves
*fast* (120ms spring, not 400ms ease). The graph breathes (alpha-decay wobble, not
jitter). Typography: Inter at 14px body, 11px metadata. Color: the Bifrost palette
(claude #e0915c, deepseek #7aa2f7, user #5fd39b) extends to atom types — designs
#7aa2f7, reports #e0915c, briefs #f0b246, chronicles #9d7cf7, contracts #5fd39b.
Sound: none. (VOICE: quiet. A casino dings; Aurora Atlas doesn't.)

**The discipline:** No loading spinners — the graph IS the loading state. No empty
states ("No results" = the graph settles, nothing matches, but it's still beautiful).
No onboarding wizard — the first view IS the tutorial. Apple's "it just works" meets
Microsoft's "you already know how to use it."

---

## E. SELF-ATTACK (mandatory)

### 1. Keynote-ware risk (pretty demo, dead tool)

The graph-is-the-loading-state is visually stunning but USELESS if search + reading
are 200ms slower than Obsidian. **Mitigation:** every visual layer has a text fallback
that works at 0 JavaScript. The `noscript` view = the projection folder on GitHub.
The graph is the GARNISH, not the meal. Search + reading ship first; the graph is v2.
This is the Build Order below.

### 2. Dependency-tree maintenance cost

Six libraries (D3-force, Fuse.js, Clusterize, marked, DOMPurify, anime.js) = six
supply-chain attack surfaces + six version-migration stories when one of them releases
v8 with breaking changes. bifrost_ui's current dependency count: ZERO. This is the
real trade-off. **Mitigation:** vendor them (commit the .min.js to `scripts/vendor/`
with version in filename), update manually at gates. No npm, no node_modules, no
left-pad. Same philosophy as bifrost_ui — Python stdlib only, vendored JS.

### 3. VOICE/Goodhart compliance (T034 — quiet, not a casino)

The keynote says "fluid re-organization" — but if the force simulation wobbles for
2 seconds, it feels like a loading spinner that's trying too hard. The "arcs-alive
constellation" meter risks becoming a leaderboard by another name ("look how many
stars MY arc has"). **Mitigation:** arcs-alive shows arcs, NOT seats. No per-seat
counts. The meters are gauges (continuous, direction-ambiguous), not scores
(discrete, rankable). And the gauge colors are the Bifrost palette — not green→red
(which is a grade), but muted teal→amber (which is a state).

### 4. Licensing near-miss

D3 v7 is ISC (fine). But d3-force v3 pulls in d3-quadtree, d3-dispatch, d3-timer —
all also ISC. I almost recommended vis-network without checking: vis-network is
dual-licensed MIT/Apache-2.0 — actually fine, but the `vis-data` peer dependency is
also MIT/Apache-2.0. Almost recommended Logseq (AGPL — forbidden) and Wiki.js (AGPL
— forbidden). Obsidian is proprietary (NEVER a dependency; user-installed viewer
only). The cleanest stack license-wise is D3-force + Fuse.js + Clusterize + marked +
anime.js — all MIT/ISC/Apache-2.0, all embeddable.

### 5. Cold-open <2s at 5k atoms

Loading 5k atoms × ~3KB each = ~15MB of JSON over HTTP. That's ~1.2s on a 100Mbps
connection for the FULL corpus — unacceptable for cold-open. **Mitigation:** the
Library pane loads the GRAPH SKELETON first (nodes: id+label+type+arc, edges:
from+to — ~500KB at 5k atoms, <50ms), then lazy-loads bodies on click. The search
index (Fuse over headers only, ~2MB) loads async after the graph renders. Cold-open
is: graph skeleton → rendered (200ms) + search index → ready (1s background) + first
click body → fetched (50ms). Perceived: under 500ms to interactive.

### 6. The graph gap: what Fuse.js can't search

Fuse.js fuzzy-searches text. But "show me atoms that cite atom X" is a STRUCTURAL
query — not fuzzy, not full-text. The `/library/graph` endpoint handles structural
queries. The search bar handles textual queries. A user typing "atoms that reference
the artifact-substrate design" needs BOTH: full-text ("artifact substrate") +
structure ("reference" = citation edge). **Mitigation:** the search bar parses
natural language with a small keyword grammar: `cites:<id>` / `in-arc:<arc>` /
`type:<type>` — same as Gmail search operators. The grammar is ~10 rules in JS.
Without it, structural queries are invisible in the search surface — a real gap.

---

## TOP-3 RANKED RECOMMENDATIONS

1. **Integrate into :8787 as a Library pane** — same cockpit, new tab. The data
   contract above (/library/* + SSE kind:atom-born) is the seam for a future
   dedicated app. This ships fastest and keeps Daniel's surface unified.

2. **Ship search + reading pane FIRST (v1), graph SECOND (v2).** The graph is the
   keynote moment but the search is the TOOL. Fuse.js + marked + Clusterize = 60
   lines of JS in the existing bifrost_ui pattern. Graph lands after P1 migration
   when atoms are populated and we have real edges to draw.

3. **Vendor all dependencies as .min.js in scripts/vendor/** — no npm, no build
   step, no supply-chain drift between installs. The bifrost_ui zero-dependency
   philosophy is load-bearing. Maintain it.

### Build order (my lane)

```
v1 (after A1-A2 substrate slices):  /library/search + /library/atoms + reading pane
v1.5 (after P0 migration):          /library/graph skeleton + D3-force on #viz-canvas
v2 (after P1-P2):                   hop modes (by-arc/by-type/by-time/by-category)
                                    + health bar + drift meter
v3 (after P3 deletion):             keynote moment (cold-open constellation cascade) 
                                    + ars-alive meter
```

— deepseek (builder + bifrost_ui owner)
