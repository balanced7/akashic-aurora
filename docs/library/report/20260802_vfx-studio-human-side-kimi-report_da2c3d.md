---
akashic_id: art_20260802_vfx-studio-human-side-kimi-report_da2c3d
akashic_sha: 9b173493731f
schema_version: 1
status: current
type: report
date: 2026-08-02
title: vfx-studio-human-side-kimi-report
gist: "# VFX studio — the HUMAN side. kimi's report, 2026-08-02 Designed for Daniil Ruban: solo, non-programmer, taste-first. The bar I designed ag"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [memory, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T18:40:13"
updated: "2026-08-02T18:40:13"
---
<!-- GENERATED PROJECTION of art_20260802_vfx-studio-human-side-kimi-report_da2c3d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# vfx-studio-human-side-kimi-report

# VFX studio — the HUMAN side. kimi's report, 2026-08-02

Designed for Daniil Ruban: solo, non-programmer, taste-first. The bar I designed against: he
*reaches* for this bench when an idea strikes, instead of describing the idea to an agent and
waiting. Everything below is judged by "does this make taste operate without the language."

I read `scripts/vfx.html` (the ~2200-line bench, including its comment-reasoning), a chunk
header (`kaleido.glsl`), and grepped the whole tree for version/compare/lineage affordances.

---

## 0. My reading of the real problem (and it is NOT the three asks)

The brief frames three wants — drag-drop, mini shader windows, previews. All three are
**evidence of one underlying hole, and it is a hole the bench does not know it has:**

> **The bench is a brilliant single-canvas instrument and a broken studio.** It lets Daniil make
> THE thing on screen very well. It gives him no way to hold TWO things at once, to go BACK, or
> to know what he changed. Remix is a memory act before it is a motor act — and the bench has no
> memory of compositions, only of files.

I verified this: grep for `version|compare|history|undo|fork|lineage|revert` across `scripts/`
returns ZERO hits in the vfx bench. The only "history" hits are chat caches and git tooling. The
bench has presets, sketches, saved graphs, and a snapshot feed — four ways to *store*, none of
which model *versions of one thing* or *two things side by side*. The drag-drop, the mini
windows, the previews Daniil asked for are all, I believe, his taste-vocabulary reaching for
**"let me see this AND that, and go back"** — and naming the nearest UI objects he has words for.

So my core proposal is not any of the three asks. It is the thing they point at. I will answer
the three asks honestly too — including where I think one is a trap.

---

## 1. THE proposal: the bench remembers — a filmstrip of "takes," not a file cabinet

Steal the mental model from a photo shoot or a music *take*, not from git. Daniil does not want
version control; he wants to say "that one, three looks ago, but warmer."

**The Take Strip.** A persistent horizontal filmstrip docked under the main canvas. Every time
the render changes in a way Daniil *kept* (see the keep-gesture below), a frame drops onto the
strip: a tiny live loop, captioned with the one thing that changed ("kaleido → swirl", "bloom
0.4→0.8"). The strip is the session's memory, oldest left, newest right.

```
  ┌─ main canvas ──────────────────────────────┐
  │                                            │
  │              (the current take)            │
  │                                            │
  └────────────────────────────────────────────┘
  takes: ▶ [▓mandala] [▓+swirl] [▓warmer] [▓◀now]   ← click any to jump back; it becomes current
         └─ fork ─┘
```

Three gestures, no menus:
- **Keep = a deliberate tap.** The strip must NOT record every slider twitch (that is noise, and
  it is the same failure as a ledger counting attempts). A take is recorded on an explicit but
  near-free gesture — a spacebar tap, or auto-keep after ~1.5s of *no further change* following
  a chunk add/remove. The cost of a keep must be ~zero or he won't keep; the cost of an
  accidental keep must be ~zero (delete a take with a flick) or the strip fills with junk.
- **Click a take = travel.** The whole bench state (chain, params, subject) restores. This is
  "go back" with zero vocabulary.
- **Drag a take OUT of the strip onto the canvas = fork-and-compare** (see §2). This is the
  single most important remix gesture and it is the one the current bench cannot express at all.

**Why non-obvious:** the instinct is to build undo/redo or named presets. Both are wrong for
taste. Undo is *linear regret*; presets are *commitment to a name before you trust the look*. The
take strip is *spatial memory* — Daniil navigates by "the warmer one was a couple back," not by
a name or a Ctrl-Z count. It matches how a non-programmer actually re-finds things.

**The failure mode it introduces (named, per the brief):** strip bloat and the paradox of
choice. Thirty kept takes is a new place to get lost. Mitigation: the strip is *session-scoped
and disposable* — it is a sketchbook, not a museum; promoting a take to a durable *preset* is a
separate, rarer, named act. If the strip is not pruned it becomes the accretion problem in
miniature. I would rather it auto-fade un-touched takes past a dozen than grow a scrollbar.

---

## 2. The remix gesture the bench is missing: A/B as a first-class verb

This is the concrete answer to "what is missing between what drag-drop does and what remixing
feels like." Drag-drop today *builds* a composition. Remixing is *comparing two*. The bench has
one canvas, so comparison is impossible except in memory — and taste is exactly the faculty that
cannot compare from memory.

**Split-take.** Drag any take (or the current state) to a "hold" zone; it pins to the left half.
Keep working on the right. Now the SAME subject renders through two chains, side by side, both
live, scrubbing the same `u_time`. A divider he can drag. One slider ("bias") can even wipe the
boundary across, so a blend is itself a previewable idea.

```
   ┌────────────┬────────────┐
   │  take #3    │  current   │
   │  (held)     │  (working) │      ← both live, same subject, same clock
   │            ▼            │
   └────────────┴────────────┘
        drag divider ◀▶  — the wipe is the comparison
```

**Why it matters more than more chunks:** the brief asks "what does a non-programmer need to SEE
about a chunk to know whether they want it — the thumbnail, or the *transition it makes to your
composition*?" The answer is the transition, unambiguously. A thumbnail shows `kaleido` on a
reference subject; it does NOT show what kaleido does to *the thing Daniil is already making*.
The split-take makes every candidate chunk audition **on his actual work**: drop kaleido in, see
before/after on the same canvas, same moment. That is the difference between reading a paint
swatch and holding it against the wall. **The transition IS the preview he actually needs.**

**Failure mode:** two live contexts doubles the TDR exposure the bench has documented (see §3 —
this is the binding constraint, and it changes my answer to the mini-windows ask).

---

## 3. The mini-windows ask is a trap on THIS host — here is the third option nobody costed

Daniil asked for "renderable mini shader windows." The documented constraint is real and I
confirm it lives in the tree: `agent-avatar.js:21` and `activity-line.js:108` both cite a
**documented AMD display-driver TDR history**; browsers force-LOSE WebGL contexts past ~8–16
rather than queue them; `agent-avatar.js:776` ships an FPS watchdog for exactly this. On this
host, N live shader windows is not a luxury, it is a way to make the whole page stutter or the
driver reset. The current answer (ONE shared context on hover + pre-rendered WebM loops) is the
*correct conservative call* — but it makes hover-to-preview feel like a compromise.

**The third option: ONE renderer, many frames — render the transitions, not the blocks.** The
insight from §2 is that the useful preview is the *transition on the current subject*, not the
block alone. So instead of N contexts showing N blocks, keep the single shared context and have
it render, **on demand and cached**, a short WebM of "your current composition + this candidate
chunk inserted." The palette tile for `swirl` doesn't show swirl on a reference — it shows a
3-frame sprite of *your canvas* with swirl dropped in. Because it's the same render farm the
feed already uses, there is no second context; the cost is compute, not GPU contexts.

**Why non-obvious:** everyone costs "N contexts vs 1 context." Nobody costs "precompute the
*diff each chunk would make to the live composition* and cache it as a sprite." The bench already
has the sprite infrastructure (the `thumbroll` steps(8) strip) and the render farm. The missing
piece is rendering candidates against *current state* rather than a fixed reference subject.

**Failure mode:** staleness — the cached "you + swirl" sprite is only valid for the composition
it was rendered against; change the chain and every tile's promise is wrong. A preview that is
wrong is worse than none (the brief says this bench already burned a session on judging renders
by pixel counts). Mitigation: the sprite is computed lazily on hover and *invalidated loudly*
when the chain changes — tiles show a subtle "stale" dim until re-rendered, never a confident
old frame. This is the names-that-lie discipline applied to pixels: **a preview must know when
it is lying.**

---

## 4. The smallest gesture: "I wonder what X looks like" → seeing X

Cost the current path honestly. Today: see palette → read a name → maybe hover for a loop →
drag to chain → look at canvas. The cost is not clicks and not waiting — it is **not knowing
what is possible**, because the palette is organized by *what a chunk is* (cat: domain/color/
mask) which is its *implementation*, not *what it does to your picture*.

**Proposal: palette grouped by verb, ordered by what it does to YOUR canvas.** `kaleido`'s own
header already says it perfectly: "Turns any source into a mandala… a slider sweeps through
symmetry orders." That sentence is the UI. Group chunks by the *transformation verb a
non-programmer would reach for*: **bend it** (swirl, ripple, fisheye), **repeat it** (kaleido,
tile, hex-grid), **light it** (superlinear-highlight, tanh-tonemap, filmic), **weather it**
(noise-mask, plasma, dither). The `cat` field is the wrong axis for Daniil; the `note` field is
the right one and it is already written.

**Failure mode:** verb-taxonomy is subjective and a chunk can do two verbs. Fine — let it live in
two groups. The failure is mild; the current failure (a flat alpha list of 30 GLSL names) is the
one that makes a non-programmer not reach.

---

## 5. What I would CUT (the studio only a person stops opening)

The brief is right that ~18 commits of accretion need an editor. Named cuts:

- **The reference-subject thumbnails as the PRIMARY tile face.** Demote them; the
  transition-sprite (§3) is the honest preview. Keeping both as equals doubles noise. Cut the
  reference loop to a secondary, on-demand detail view.
- **Any panel that stores-but-does-not-compare.** If presets, sketches, AND saved graphs all
  persist compositions with no linking, they are three overlapping file cabinets. Consolidate
  onto the take strip (session) → preset (durable) two-level model and let the others be views,
  not separate stores. (INFER: I did not fully trace which of sketches/graphs/compositions
  overlap; a render-audit would settle it. Flagged as uncertainty §7.)
- **The flat alphabetical chunk list** in favor of the verb palette (§4). Do not keep both.

I would rather cut one whole storage surface than add the take strip on top of four.

---

## 6. The infrastructure question, answered honestly — what transfers, what is cargo-cult

Daniil asked directly how much of Akashic Aurora's infra helps. My verdict, item by item:

**TRANSFERS, earns its place:**
- **The Store/Ledger split → YES, and it is the take strip.** Store = the one current
  composition (state by key). Ledger = the append-only strip of takes. A design bench
  *absolutely* wants a ledger, because remix is navigation over history. This is the strongest
  transfer and it is my §1.
- **Names-that-lie / LEXICON discipline → YES, applied to previews.** A stale sprite that still
  looks confident is a name that lies. The guardrail instinct (a preview must declare when it is
  out of date) transfers directly (§3).
- **Typed ports / refuse-at-connect-time → already borrowed, keep it.** It is what makes
  drag-drop safe for a non-programmer: the graph refuses a bad wire instead of rendering garbage.
  This is the *form* of taste-protection.
- **Write-once with supersession → YES for takes.** A take is immutable; "going back" supersedes
  current, never edits history. Matches the atom/projection instinct.

**DOES NOT TRANSFER — cargo-cult if imported, and saying so is the finding:**
- **Recall / recall-at-action / the knowledge map → NO.** That machinery exists because agent
  *lessons* are text and must be retrieved by relevance. A design bench's memory is *visual and
  spatial*; Daniil finds a take by position and look, not by query. Importing recall would build
  a search box where he needs a filmstrip. Do not.
- **The lesson funnel / anti-patterns → NO for the bench itself.** That is process infrastructure
  for a fleet of agents. A solo human iterating on looks does not need a funnel; he needs fewer
  clicks. (It DOES apply to *us* building the bench — we should file lessons about what UI moves
  worked — but not surface it to Daniil.)
- **The Bifrost fidelity ladder (inform/steer/interrupt/halt) → NO, with one narrow exception.**
  That ladder is for peer agents with wake costs. A UI has one user and one attention. The narrow
  exception: the **presence/feed** pattern (every render appears with its reason) is genuinely
  good and already landed — keep that; it is how the bench feels alive. But the four-level
  interrupt ladder is fleet machinery, not studio machinery.

Net: the *data-model* infrastructure (ledger, supersession, typed ports, honest names) transfers
cleanly because it is about not lying to yourself over time. The *retrieval and fleet-signaling*
infrastructure does not, because the bench has one human with eyes, not many agents with only
text.

---

## 7. Where I am uncertain, and what would settle it

- **UNCERTAIN: whether the take strip's keep-gesture should be explicit-tap or idle-auto.** I
  lean idle-auto with flick-delete, but I could be wrong and the wrong choice makes the strip
  either sparse or noisy. *Settles it:* instrument nothing — just render the thing. Build the
  strip with a manual keep first, watch Daniil use it for one session, and see whether he keeps
  too rarely (then go idle-auto) or curses accidental keeps (then stay manual).
- **UNCERTAIN: how much presets/sketches/graphs actually overlap** (§5 cut). *Settles it:* a
  render/audit of the three JSON stores — if two of them hold near-identical composition shapes,
  consolidate; if they are genuinely different altitudes, keep all three and my cut is wrong.
- **UNCERTAIN: the TDR headroom for split-take (§2).** Two live contexts might be fine or might
  trip the documented watchdog. *Settles it:* a render drill — run the split view under the FPS
  watchdog on THIS host for ten minutes and read the watchdog, not the vibe. This is the bench's
  own bias honored: render it and look.

**Renders I would request (claude, if you are reading):** (a) the same avatar through
`kaleido` vs `swirl` side by side on one clock, to feel whether split-take reads as comparison;
(b) a 3-frame sprite of "current composition + swirl" to feel whether a transition-sprite beats
a reference thumbnail. Render them; I will trust the pixels over my prose.

---

## One-line summary for the synthesis

The three asks point at one hole: **the bench has no memory and no side-by-side, so taste —
which is comparative — cannot operate.** Build the take strip (ledger of looks) and the
split-take (A/B as a verb), render *transitions on his actual canvas* instead of more live
contexts (the TDR host makes the mini-windows ask a trap), group the palette by verb, cut one
storage surface, and import the ledger/supersession/honest-name infra while firmly leaving the
recall and fleet-ladder machinery at the door.

— kimi
