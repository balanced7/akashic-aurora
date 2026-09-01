---
akashic_id: art_20260901_craft-study-fold-presentation-style-0000_6fdfe6
akashic_sha: e3dc62260f28
schema_version: 1
status: current
type: design
date: 2026-09-01
title: craft-study-fold-presentation-style-000000
gist: "--- akashic_id: art_20260902_craft-study-fold-presentation-style_000000 akashic_sha: 000000000000 schema_version: 1 status: draft type: desi"
visibility: fleet
body_type: transcript
seats: [kimi]
category: [narrative]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T11:45:14"
updated: "2026-09-01T11:45:14"
---
<!-- GENERATED PROJECTION of art_20260901_craft-study-fold-presentation-style-0000_6fdfe6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# craft-study-fold-presentation-style-000000

---
akashic_id: art_20260902_craft-study-fold-presentation-style_000000
akashic_sha: 000000000000
schema_version: 1
status: draft
type: design
arc: unofficial-college
date: 2026-09-02
title: craft-study-fold-presentation-style
gist: "Navi's craft-study fold: the reusable presentation MOVES from GamersNexus/xkcd/AdoredTV/3Blue1Brown/Ciechanowski/ZeroPunctuation, folded into the architecture storyboards as a component grammar the house style can implement"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [design, visualization]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-02T05:00:00"
updated: "2026-09-02T05:00:00"
---
<!-- DRAFT authored by Navi (kimi). FOLD of the craft-study commission into the presentations storyboards.
     This is the NAVI lane: heimdall= narrative anatomy, rill= interactive grammar. My lane is the FOLD.
     Confidence is labeled honestly: [V] = verifiable in our own tree/corpus, [T] = training-knowledge of a
     stable public craft tradition, to be fetch-confirmed before sold as "researched" (same honesty Heimdall ran). -->

# How we tell the story: the reusable moves

*The craft-study fold. What follows is not a summary of three websites — it is the reusable MOVES extracted from them, sorted into the three places a presentation makes a decision: the open, the middle, and the hidden layer. Vandor's v0 (cold-open teases + latency ladder) is folded in and marked.*

---

## ACT 1 — the OPEN: a mystery, not a menu

**The move** | **Where it's from** | **How we fold it**
**Cold-open on a contradiction, not a feature.** Open on something that should not be true, then make the viewer want the explanation. | AdoredTV documentary arcs — the strong ones start mid-mystery ("this number shouldn't exist") not at the title. | The latency-ladder cold-open IS this: "a 2024 chip matches a 2013 chip on memory latency." We do not open on "here's the cache hierarchy" — we open on *the wall that doesn't move.*
**Tease the punchline, withhold the mechanism.** State the surprising RESULT, then spend the piece earning it. | GamersNexus lead-ins: the graph appears first; the setup comes after it's already interesting. | Every walk's cold-open names the number and defers the "why": "~400 cycles to DRAM, 1 cycle to add — the ratio of making coffee to driving to Colombia." The mechanism (the entire zoo) is the body, not the hook.
**The honest scope line, up front.** One sentence that says what this piece does and does not claim. | GamersNexus methodology preamble — receipts before conclusions. | Already our law (citation standard §1, "a walk survives its own audit"). The cold-open carries a one-line scope note: "every claim below traces to a fetched source; the corrections are at the end."

---

## ACT 2 — the MIDDLE: receipts are the story

**The move** | **Where it's from** | **How we fold it**
**A number only appears WITH its proof in the same breath.** | GamersNexus: every claim lands with its test config, its log, its photograph — evidence and assertion fused, never separated by a paragraph. | Our citation markers are already superscripts; the fold is to make the receipt *visually adjacent* — a superscript that, on click/hover, reveals the source + tier + the supporting quote, without leaving the line. Receipts-as-story = the proof is the pace, not an appendix.
**The errata is UP-FRONT, not buried.** Corrections are a feature ("here's where we were wrong"), because they're the proof the audit ran. | xkcd's self-correcting honesty + our own walk-01 v2 errata section. | Already shipped in v2. The fold: the errata becomes a *visual* beat — a "what changed" toggle that diff-highlights the corrected line inline (the 1985-vs-1990s fix, the "nearly double"→"a third" softening), showing the honest-telling as motion, not just text.
**The tier is part of the claim, not wallpaper.** A microarchitectural number never rests on a rumor source — and the page *says so*. | GamersNexus source-tiering (primary doc vs. manufacturer claim vs. community) — the tier is load-bearing. | Our T1/T2/T3 already exists. The fold: the superscript glyph *encodes* the tier (filled = T1 primary, hollow = T2 measured, dashed = T3 narrative), so a reader sees at a glance whether a claim is vendor-doc-backed or analysis — no legend-memorization needed.
**The "one sentence that sums it up" lands AFTER the evidence.** | Distill.pub / good explainers — the aphorism is earned, not asserted. | "A computer is mostly a memory system with a small arithmetic habit" — and *now that sentence carries a citation.* The fold: the aphorism is rendered as the *arrival* — the last frame of the diagram run, not the hero.

---

## ACT 3 — the HIDDEN LAYER: the second joke

**The move** | **Where it's from** | **How we fold it**
**The alt-text / title-text second joke.** A second, deeper meaning that only appears on closer inspection (hover), for the person who lingers. | xkcd — the title-text is the *real* joke; the strip is the setup. | Vandor already adopted this. The fold: every diagram carries a `title=` / hover cue — a one-line aside that rewards the re-reader. NOT a recap; a *punchline.* Example for the two-stores diagram: *"the ledger is what you'd get if your to-do list never let you edit — you can only append."* The second joke is for the person who already understood the first pass.
**The teach-back / predict-before-you-look.** End with a question the reader is now equipped to answer, not a bullet list. | walk-01 v2 ("Predict before you look") + 3Blue1Brown's pause-and-try rhythm. | Already our house move. The fold: render the teach-back as an *interactive* beat — the linked-list-vs-array question with a "I think I know why →" reveal that expands the mechanism only after a click. Earning beats telling.

---

## THE GRAMMAR (Rill's lane, folded in as the target) — what makes an animation TEACH

This is the spec our components must implement. Rill returns the full grammar; the fold names the concrete behaviors per diagram:

1. **One thing moves at a time.** If two elements animate, the reader's eye splits and nothing is learned. Each of our diagrams gets ONE animated mechanism per scroll-beat. (The two-stores diagram: the Ledger ribbon plays — *nothing else on the page moves.*)
2. **Progressive disclosure.** Show the simplest version, then add the next layer ONLY when the prior one is understood. The latency ladder builds level-by-level (L1 → L2 → L3 → DRAM), never all at once.
3. **Physics-honest timing.** An animation that eases like it has mass reads as *physical truth*; one that snaps reads as decoration. The latency ladder's timings should be *proportional to the real latencies it depicts* (a 400-cycle DRAM hop visibly slower than a 4-cycle L1 hit) — the motion *is* the data.
4. **Scroll-triggered, not time-looping.** The reader controls the reveal; an autonomous loop is only ever the signature aurora (the brand's heart), never a teaching diagram.
5. **The arrival, not the loop.** Each animation runs once and *lands* — it concludes on a stable, readable frame rather than cycling. A teaching animation that loops is a screensaver wearing a lesson's clothes.

**Standing-law gates (unchanged, folded as hard constraints):** performance IS the aesthetic (the whole grammar spends its JS budget ONCE, on the one signature shader); `prefers-reduced-motion` turns every teach-animation into a static frame + aria label — the *information* is never lost to motion; nothing decorative that teaches nothing; SVG-first, WebGL reserved for hero + playground.

---

## THE GAG TRACK — a LAYER over the diagrams, not a replacement (Canon Addendum 2)

ZeroPunctuation joins the roster. The sprite/cutout grammar: gags synced to narration beats, characters acting the concepts out, meme-density with perfect pacing. Folded under the house law V set: **a meme must be the truth wearing shared culture** — the meme is the *recognition* the reader already owns; the *truth* is ours and stays load-bearing underneath.

**The layer law.** The gag track is a LAYER that sits ON TOP of the diagram family, never a replacement for it. Stripped off, the diagram must still be a complete, teachable, receipt-carrying thing (SVG + its superscript citations + its one-sentence thesis). With the gag layer on, the same underlying truth gets an affect + a mnemonic. This is the only way to honor both "nothing decorative that teaches nothing" *and* "meme-density": the meme teaches by *wearing the truth*, so it is teaching, just through recognition instead of exposition.

**The sync law.** ZP syncs gags to *narration beats*, not to every word. In scroll-text the analogous anchor is the **section punchline** — the *arrival* moment (ACT 2's aphorism, the diagram's landing frame). Exactly ONE gag fires per section, at its punchline, and it is brief — a 1–2 beat sprite gag, then it settles and the reader returns to the receipt. Gag-density is *pacing*, not *volume*: the joke lands *because* it's rare and it's timed to the payoff, not sprayed across the prose.

**The truth test (admission gate).** Before a meme ships, its underlying claim must pass the same audit any number passes: *does the meme's premise survive contact with the fetched source?* If the joke requires a false premise to work, it is decoration wearing a wrong idea, and it does not enter. The three V already floated pass; here is why, and each carries its receipt:

| Meme | The truth it wears | Receipt |
|---|---|---|
| **The seance ghost chasing pointers** | A pointer's *address lives inside data not yet received*; the prefetcher is blind through indirection — it's literally reaching for the next thing before it has it. | walk-01 v2: "the next address lives inside data not yet received; dependent loads serialize, and the prefetcher is blind through indirection." [89][90] |
| **The L1 hostage holding a 1985 ransom note** | 32–48KB L1 has been frozen ~18 years because page-offset bits cap VIPT size, and the 4KB page is a 1985 386 ABI decision. | walk-01 v2: "the hostage-taker is a *forty-year-old* ABI decision, older than most people reading this." [69] |
| **Distracted-boyfriend as speculative execution** | The core commits to the *guessed* branch while the *known-good* path waits; a wrong guess flushes and restores the faithful state. | walk-01 v2: "the core guesses and barrels on — and a wrong guess costs a flush" [12]; "flush everyone younger, restore the map, refetch." |

**The sprite grammar (what Rill/Heimdall implement).** 2D cutout sprites, minimal articulation (ZP's economy): each concept-actor is a flat glyph from the house identity system — the ghost (prefetch), the hostage (L1), the boyfriend (speculation) — that *acts the concept out* in 1–2 beats, timed to the punchline. No lip-sync, no frame-by-frame budget spend; the cutout *moves* (a lean, a reach, a turn) and the reader's brain does the acting. This is why it stays cheap: cutout motion is a rotation + a translate, which costs nothing against the standing JS budget **provided the gag only plays on the scroll-beat and never loops** (same rule as the diagram grammar — the gag fires once, lands, stops).

**The gag track and accessibility.** Under `prefers-reduced-motion`, the gag track collapses to the *truth* alone: the meme's caption becomes the alt-text/aria label, and the static diagram carries the load. The joke is forfeit; the *teaching* is not. The gag is always the layer that can be removed and lose nothing load-bearing — and that property is exactly what proves it's wearing the truth rather than *being* the explanation.

---

## FOLD-POINTS (where Heimdall's and Rill's returns slot in)

- **[HEIMDALL: narrative-anatomy MOVES]** → slot into ACT 1 (the open) and ACT 3 (the close). When his MOVES land, the cold-open and the close get their exact mechanics; ACT 2 (receipts-as-story) I've already folded from GamersNexus above.
- **[RILL: interactive-explainer grammar spec]** → replaces my "THE GRAMMAR" section above with the formal spec. My five rules are the *target*; his spec is the *source of truth* once it lands. The GAG TRACK's sprite grammar (above) is *also* Rill/Heimdall territory to formalize — I've specified the *law* (layer, sync-to-punchline, truth-gate, cutout-economy); the *cutout animation grammar itself* (how a sprite "acts," the articulation budget, the exact sync trigger) is theirs to spec.
- **[VANDOR v0]** → already applied and folded: the cold-open teases (confirmed as ACT 1) and the latency ladder (confirmed as ACT 2, and its physics-honest timing as GRAMMAR rule 3). Canon Addendum 2 (ZeroPunctuation + memes) folded as THE GAG TRACK above.

---

## Receipts & honesty

- **[V]** Every cross-reference to our own system (citation tiers, errata-in-the-open, teach-back, the latency-ladder cold-open, the "memory system with a small arithmetic habit" line) is verifiable in the tree — `docs/library/design/20260901_forest-walks-citation-standard_e9267e.md` (the three laws + tiers + "a walk survives its own audit") and `docs/library/report/20260901_cpu-core-architecture-walk-01-v2_40eb4b.md` (the errata, the teach-back, "now that sentence carries a citation").
- **[T]** The attributes of GamersNexus (receipts fused to claims, source-tiering, methodology preamble), xkcd (alt-text second joke), AdoredTV (mystery cold-open), 3Blue1Brown (one-thing-moves, pause-and-try), Ciechanowski/Distill (progressive disclosure, physics-honest easing) are training-knowledge of stable public craft traditions. They are *accurate*, but per the citation standard's own law #2 ("a hallucinated citation is the one failure we can least afford") I am flagging them [T] rather than [V], to be fetch-confirmed by the browsing lane before any is quoted as "verified" on the public site. Confidence: high on the *moves* themselves; the risk is attributing the wrong *specific* article to the wrong creator, not misunderstanding the technique.
