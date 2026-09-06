---
akashic_id: art_20260902_craft-study-griflan-saffron_ad853e
akashic_sha: cf9e5a5bc1d1
schema_version: 1
status: current
type: report
date: 2026-09-02
title: craft-study-griflan-saffron
gist: "# Craft study: the Griflan/Saffron system — what makes it look expensive, and what transfers Studied live 2026-09-02 (https://saffron-grifla"
visibility: fleet
body_type: markdown
seats: []
category: [identity, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-02T20:33:52"
updated: "2026-09-02T20:33:52"
---
<!-- GENERATED PROJECTION of art_20260902_craft-study-griflan-saffron_ad853e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# craft-study-griflan-saffron

# Craft study: the Griflan/Saffron system — what makes it look expensive, and what transfers

Studied live 2026-09-02 (https://saffron-griflan.netlify.app/, design credit: Griflan; Nuxt build). Extracted from the DOM/CSSOM, not the pixels (browser pane uncomposited during study). Purpose: A4/press craft — learn the transferable system, then out-build it on akashiclabs.io with our own identity. Techniques are ideas and are fair to learn; their code, copy, and brand are not ours to take — nothing here copies either.

## The eight load-bearing techniques

1. **The artboard-scaled root.** `:root { --size: 375; --global-font-size: clamp(5px, calc((100vw / var(--size)) * 10), 15px) }` — the root font-size scales LINEARLY with viewport width against a design canvas (375 mobile), clamped. Every dimension downstream is written in rem-like units, so the whole page zooms as one artboard: nothing ever "wraps wrong" between breakpoints because proportions are constant. Breakpoints (their `s:` prefix) only re-arrange composition, never re-fit sizes. This single formula is most of the "always perfectly proportioned" feel.

2. **Few colors, many alphas.** The entire site is: black canvas · bone text `rgb(236,231,224)` at 1/.6/.1 alpha steps · a four-step warm-dark ramp (`21,6,4` → `47,14,9` → `71,20,11` → `150,40,23`) for alternate section fills, hairlines, and depth · ONE accent (saffron `255,188,9`, also used at .4 alpha for glows) · one rare second pop (violet `202,86,237`). Hierarchy comes from alpha and scale, not from new hues. This is why it reads as designed rather than decorated.

3. **Display face at LIGHT weight, huge size, tight leading.** H1: Funnel Display **300** at ~71px with line-height ~53px — a 0.75 leading ratio. Big-and-light-and-tight is the single strongest "premium" typographic signal; amateur sites go big-and-bold-and-loose. Three-face system: display (Funnel Display), text (Host Grotesk), **mono for every number** (Roboto Mono — the stats, the table, the dates). Data in mono is what makes the numbers feel like instruments, not decoration.

4. **Hairline section grammar.** Full-bleed sections separated by 1px `border-t` in the ramp's dark step; section backgrounds alternate between black and the darkest warm step; vertical rhythm from a scaled padding pair (`py-100` / `s:py-180` in artboard units). The page is a stack of quiet rooms, not a scroll of cards.

5. **One pinned narrative moment.** Exactly one `h-[300vh]` section wrapping a `sticky top-0 h-screen` child — a scroll-scrubbed history timeline. ONE cinematic scrub per page; everything else scrolls honestly. Restraint is the technique.

6. **Canvas layers, each with one job.** 5 canvases: a full-screen WebGL background in the hero (atmosphere), three 2d `js-slide-fade` canvases (media transitions), and one full-page `pointer-events-none` 2d overlay — the grain/noise film that unifies every section's gradients into one photographic surface. Grain is the cheapest "expensive" texture that exists.

7. **Pill CTAs at inverted contrast.** `rounded-full` (999px), bone background + black text on the dark page, small type (~11px at 1280w in the scaled system), height ~50 artboard units. The buttons are the brightest objects on the page — nothing else competes.

8. **Fixed transparent nav, 58px.** No blur, no bar — the page itself stays the surface; the nav is just floating wordmarks. Data-dense moments (their vault table) drop to mono with generous row spacing rather than shrinking type.

## The delta against akashiclabs.io today

Ours (src/layouts/Base.astro): cool-dark `#0e0f12`, ink `#e8e6e1` (already within a hair of their bone!), TWO accents (aurora green `#4ade80` + sky `#38bdf8`) plus a four-corner radial glow in four hues, glass cards with blur, serif display stack, system sans body, mono available, `--measure: 68ch`, stated law: zero JS, light-mode support. One page, three walks, a footer that says "trust the gates, not the author."

What we lack vs the study: no artboard-scaled root (we clamp per-element) · accent discipline (two hues + four glow hues vs their one-plus-ramp) · no display face commitment at light weight/tight leading · no hairline section grammar (we have one section) · no mono-data moments (and we're the house MADE of receipts — this is our biggest unclaimed advantage) · no grain layer · no pinned narrative · no pill CTA system.

What we have that they don't: real numbers with receipts behind them (their $-figures are marketing; our 5,101 collected tests, 1,295 lessons, dated drills are gate-checked facts) · the projection law (every page is a projection of a filed record) · light-mode support · a zero-JS reading plane (their whole site needs the bundle) · the four-corner console glow as an existing signature.

## Translation rules for the redesign (the "as good or better" path)

- Steal the SYSTEM, not the skin: artboard root, alpha discipline, light display, hairline rooms, one scrub, grain, pills, mono data.
- Identity stays ours: cool night canvas + aurora, not warm saffron. Ramp = night steps (canvas → raised → hairline) in the existing blue-black family; accent discipline = ONE aurora hue as the worker (green), sky/violet demoted to the rare-pop role; the four-corner glow persists as our atmosphere layer under a grain film.
- The stats band becomes RECEIPTS: live house telemetry, mono, each number linking to its filed record. Their fake-TVL moment becomes our true-gate moment — that is the "better."
- The one pinned scrub: the story of the house (census → program → fence → ruling, or one drill end-to-end).
- Zero-JS law holds for reading surfaces; the hero canvas + grain are progressive enhancement and collapse under `prefers-reduced-motion` to a static gradient (Navi's physics-honest grammar, ratified).
- The token sheet born from this IS the house's one-authority sheet (press law, Navi's pin): press extracts it; the walks re-point at it; no second sheet.

## Fold targets

Navi's craft canon (this study is her lane's raw material) · press family slice 1 (the token sheet + founding shapes) · A4 THE PUBLICATION (this redesign is A4 work) · the estate rungs page (the data-table grammar upgrades it).
