# Virtual Stage preset packs: the census and the design (2026-10-29)

Workflow run wf_d6d7ed76-3fa (task w8u4y3p08): three read-only census lanes over the stage-v4 code, then one design.
Daniel, verbatim: "can you save this for later I just played with http://127.0.0.1:8796/web/stage/index.html?demo=1 and it looks AMAZING!!!!! so many problems have been fixed! What did you have planned next for it! lets also save a snapshot of current build and settings on that page so we can revert if things don't go how we like. or at least comparable settings and presets so we don't have to undo redo whole components, perhaps making the logic and animation sequences be preset packs"

The whole-build revert is already covered: tag snapshot/stage-2026-10-29-amazing (e9f5e3cbc) plus a bundle and a zip in
state/backups/stage-snapshot-2026-10-29/ (private, with SNAPSHOT.md). Nothing was built from this design yet; it waits for
Daniel's answers. Verbatim; local paths shortened.

---

## Summary (verbatim)

Preset-pack design is done. Daniel, nothing was edited; the files I used are in E:/AI-Setup/.claude/worktrees/stage-v4/arsenal/web/stage/.
- A pack works like a lighting desk's show file: 13 separate pools (colour, looks, effects, phrases, aim, formations, lasers, camera, running order, kick, haze, controls, viewer), each saved with its own version. A "show" picks one version of each, and any pool it leaves out comes from its base show.
- The first pack, "amazing-2026-10-29", is copied straight out of the tagged files from e9f5e3cbc. With no pack, or with that pack, the stage behaves exactly as it does now.
- That is checked by: a test that the pack matches the tagged files exactly; all ~380 stage tests passing unchanged; a Node run of 512 bars with identical camera cuts and phrases; stage_verify on the tag, no-pack and with-pack, run in automation mode and in your HDR/HAL/rotate mode; and a pixel diff of the stills.
- Safety: packs can't touch the flash limiter, FlashGate, strobe or laser gates, or camera clearance. Numbers like punch and luma_cap can only be lowered, and phrases can't add or strengthen a flash.
- v0 changes no engine module, only one branch in stage.js plus new packs.js, packs/ and a Node CLI (freeze/diff/fork). Shows switch by reload (?pack=, ?pack.phrases=...). Work happens off the tag, so your live page stays untouched until you say yes.
- v1 adds live switching (each pool at its safe moment: bar, section or phrase repeat), [ and ] plus show pads, and moves code constants into tables with the same numbers, one per commit. v2 turns sequences that are written as code into data with a small interpreter, never scripts.
- Three questions for you: should your page load the pack by default (I say not until v1); should saving be a download button first and a real save button later (I say yes); and should a pad show-change land in stages within 8 bars (I say yes).

---

## The design (verbatim)

# Virtual Stage preset packs: design

*For Daniel. Built from the three census lanes (colour-light, motion-sequences, camera-page-persistence). Verified against the stage-v4 worktree: HEAD is `e9f5e3cbc`, the tag `snapshot/stage-2026-10-29-amazing` exists, there is no `packs/` folder yet, and the scene is loaded with a single `fetch` at `stage.js:148`.*

> "lets also save a snapshot of current build and settings on that page so we can revert if things don't go how we like. or at least comparable settings and presets so we don't have to undo redo whole components, perhaps making the logic and animation sequences be preset packs"

The tag already covers the first half ("revert the whole build"). This design covers the second half: settings you can compare, saved per component, so one part can be swapped or put back without touching the rest.

---

## 0. The risk, stated first

You just called this build AMAZING. The danger in this work is that "making it configurable" quietly changes something you love. Four rules handle that:

1. **v0 changes no engine module.** Nothing in programmer, phrases, lasers, camera, render, kick, effects or formations changes. The only edit to existing code is one branch in `stage.js` boot, and it runs only when the URL asks for a pack. With no `?pack=` in the URL, that branch never runs and the page runs exactly the code at `e9f5e3cbc`.
2. **The first pack holds today's numbers, copied out of the tagged files.** A test checks this: applying it to today's scene must give back a scene that is deep-equal to the original. If anyone edits the pack by hand, the test fails.
3. **Your live page is not touched.** The stage-v4 worktree serves :8796 and stays read-only. Pack work happens on a new branch and worktree cut from the tag, served on a different port. Your page moves only after you have looked at it and said yes.
4. **v1 lifts one constant per commit, with the same numbers.** Each lift moves a code literal into a table without changing its value. A test pins each one by name, so any single lift can be reverted on its own.

The safety layer (the flash limiter, FlashGate, the strobe caps, the laser gates, the camera clearance) is never something a pack can reach. Section 3 covers this.

---

## 1. What a pack is

**The lighting-desk version.** A grandMA or ChamSys show file is not one blob. It holds separate pools: colour presets, position presets, effects, cue lists. You can import a single pool from another show file without touching the others. Packs work the same way. Each part of the stage is its own pool, called a **layer**. Each layer is saved and versioned on its own. A **show** is a named list that says which version of each layer to use.

**The synth version.** Patch banks hold the sounds. A *Performance* (or *Multi*) holds no sounds of its own. It points at one patch per part. Swapping the bass patch leaves the pads alone. Here a layer version is a patch, and a show is a Performance.

**The PC version.** On a motherboard the XMP profile, the fan curve and the PBO settings are each saved separately, and a saved BIOS profile bundles one of each. If a fan curve goes wrong, you load the old fan curve and keep your memory timings.

### The layers (taken from the census)

| # | layer | what it holds, in plain words | where it lives today | when a change shows on stage | slice |
|---|---|---|---|---|---|
| 1 | **colour** | the 8 setups (ice-spine … black-and-one), their order, rotate every 16 bars / hold at least 8 / fade over 4 beats, first setup ice-spine; the starting palette (source-violet); the 6 themes; the palette book | `sets/setups.json`, `show.setups`, `show.palette`/`theme`, `themes`, `../palettes.json` | setups already crossfade live (beginSetup); a palette change crossfades on P | v0 |
| 2 | **looks** | the base state of each of the 5 sections (each group's dimmer, pan, tilt, zoom, colour role and effects) | `looks` | at the next section | v0 |
| 3 | **effects** | the pattern library: 34 effects (levels-step, pinch-step, vert-step, hrow-pan, corona-chop, the ring-* effects …) and the 14-item ring-effect menu | `effects`, `ring_fx` | when the next effect starts | v0 |
| 4 | **phrases** | the 6 sequences, including halo-levels: the 3 levels → horizontal flash and pan → verticals 1-2-3 → lasers → halo chop; the variant deck (daniel, pinch, ascend, rush, depth); the per-repeat colour and pan cycles | `phrases` | at the next repeat or Go | v0 |
| 5 | **aim** | the position presets: the 3 levels at 26 / 15 / 8 m, horizon Tilt 86, vertical, corona | `presets` | at the next phrase step | v0 |
| 6 | **formations** | the strand waves (high and low), the 5 still strand shapes, the ring poses and reveal order, the ring deck (all except hero, column and the orrery's shimmer) | `formations`, `strand_shapes`, `ring_formations` | at the next landing | v0 |
| 7 | **lasers** | the 13 laser groups and how far each bank throws (A 0.9, B 0.6 …) | `laser_groups`, `lasers.reach` | on reload (v1: between phrases) | v0 |
| 8 | **camera** | the 58 shots, 8 section sequences, 11 landing views, and the safe wide shot | `cameras.*` | on reload (v1: at the next section) | v0 |
| 9 | **running order** | per section: which look, formation, laser look and level, camera sequence and phrase, and how fast; plus the demo plan | `show.sections`, `show.demo` | at the next section | v0 |
| 10 | **kick** | pad 1 / pad 5 feel: colour and motion, the 4 areas a kick deals to, the velocity bands, the level curve, release, hold and chase | `kick` (without the strobe and governor parts) | on reload | v0 |
| 11 | **haze** | haze lag 1.5 s, pre-haze 0.12, wind and noise (not the hazer positions, not the density caps) | `atmos` | on reload (v1: re-init) | v0 |
| 12 | **controls** | the pad map (14 pads), the fader CC map, where the faders start (haze 0.85 …) | `show.pads`, `show.faders`, `show.fader_defaults` | pads: on the next press; faders: on reload | v0 |
| 13 | **viewer** | the same things a URL can set today: finish look, cube style, tumble, cube colours, setups mode, grammar on or off. A URL parameter still wins | URL parameters | on reload | v0 (the first pack leaves it empty, see §2) |
| 14 | **finish** | the 4 finish looks (HDR Night, punch, velvet, classic): saturation, glow, black floor … | `render.js` LOOKS (code table) | live, every frame | v1 |
| 15 | **feel** | chord timing windows, fade speed, how the camera distance eases (gentler only), handheld wander, small timing constants | `grammar.js` G, `ensemble.js` BREATH, `distance.js`, `camera.js` | varies | v1 |
| 16 | **shapes** | laser group-shape defaults (spread, beams, measure, swing), cube glow mix and spin | `lasers.js`, `cubes.js` | live | v1 |
| — | *(v2)* | section laser looks, the hit-engine deck, formation numbers, cube shader constants, kick-5 bank order: sequences written as code today | code | — | v2 |

**What is never a layer:** the rig itself (fixtures, mounts, groups, the halo's thirds, ring clearances). That is the build, not the show. Also anything in the safety list in §3.

### A show, and what happens when a layer is missing

A show names a version for each layer and names a **base** show. If a layer is not named, it comes from the base show, then that show's base, and so on. At the end of the chain is the set file itself (`sets/source-v1.json` plus `setups.json` and `palettes.json`). The first pack names all 13 v0 layers, so it is a complete snapshot. New shows are forks of it, with `base: "amazing-2026-10-29"`. That way a fork stays stable even if someone later edits the set file.

---

## 2. The first pack: `amazing-2026-10-29`

The first pack is frozen from the tagged commit `e9f5e3cbc`. The freezer reads the files from git (`git show e9f5e3cbc:arsenal/web/stage/sets/source-v1.json` and the others), not from a working copy that might have drifted. It writes one file per layer at version 1, plus `shows/amazing-2026-10-29.json`.

Points to get exactly right:
- **Setup rotation is merged from three places today.** The order is code default → `setups.json` → `show.setups` (`stage.js:342`). The colour layer records the values that actually take effect (16 / 8 / 4, first ice-spine). It overlays them in both places with the same numbers, so the merge comes out the same.
- **The viewer layer is empty in this pack, on purpose.** Today's viewer defaults depend on who is looking. Automation gets classic, solid cubes and setups off. Your browser gets HDR Night (or your last L choice), HAL cubes and rotation. If the pack wrote `look: hdr`, the automation runs would change. The snapshot holds today's behaviour by not overriding it.
- **Safety keys are left out** (§3). The overlay merges at field level, so the base values for those keys stay in place.

### The invariant

> With no pack chosen, **and** with `?pack=amazing-2026-10-29`, the stage behaves exactly as `e9f5e3cbc`.

### How that is proven (cheapest first; all of it uses the house's own tools)

| step | what runs | what is compared | pass bar |
|---|---|---|---|
| P0 | `tests/stage_packs.test.mjs` (new) | each layer of the pack against the same blocks read from the tagged files | deep-equal |
| P1 | same test | `applyPacks(scene, amazing)` against `scene`, for source-v1, setups.json and palettes.json; then `expandScene` on both | deep-equal |
| P2 | `node --test tests/stage_*.test.mjs` (24 files, about 380 tests) | everything they compare today: tolerances, the exact cut lists (`stage_camera.test.mjs:304, 344-345`), GATE_FLOOR, MODES.real | all pass, with no test edited |
| P3 | new pure-Node equivalence test | a Director, a CameraDistance and a PhraseRunner built from the plain scene and from the packed scene, driven through the demo plan for 512 bars | `director.cuts`, `director.landings`, `camDist.moves` and the phrase log are exactly deep-equal |
| P4 | `arsenal/lanes/stage_verify.mjs`, logic phases (clock, camera, phrase), on the virtual clock | three runs: **the tagged tree**, **the new tree with no pack**, **the new tree with `?pack=amazing-2026-10-29`**. Compare `__stage.state()`: cuts, lands, phraseSteps, FlashGate grants and refusals, limiter stats, setup landings | identical across all three; limiter interventions stay 0 |
| P4b | P4 again in **your** mode | `&look=hdr&cubes=hal&setups=rotate`. Automation turns setups off, so the colour layer is only exercised here | identical |
| P5 | `arsenal/lanes/stage_stills.mjs` at fixed bars and shots, before and after, on the same GPU backend, under the GPU lock | the PNGs, with a new pixel-diff step | zero differing pixels |

The tagged tree for P4 and P5 is a fresh read-only worktree checked out at `snapshot/stage-2026-10-29-amazing`. It is never stage-v4, so your live server is not touched. The virtual clock makes runs repeat exactly, so the bar is exact equality, not "close enough".

---

## 3. The file format

### Layout under `arsenal/web/stage/packs/`

```
packs/
  index.json                         # list of shows and layers (a static server can't list folders)
  shows/amazing-2026-10-29.json
  colour/amazing-2026-10-29.v1.json
  phrases/amazing-2026-10-29.v1.json
  ...one folder per layer
```

**Files are never overwritten.** A change becomes a new version file (`.v2.json`), so the history is the folder itself. This is the gap in pianolooks: its `rev` stops two windows saving over each other, but it keeps no history. Here, reverting one component means pointing the show back at the earlier version.

### A layer file

```json
{
  "format": "arsenal.stage-pack/v1",
  "layer": "phrases",
  "id": "amazing-2026-10-29",
  "version": 1,
  "parent": null,
  "created": "2026-10-29T21:40:00Z",
  "from": { "commit": "e9f5e3cbc", "set": "source-v1" },
  "notes": "frozen from the AMAZING build",
  "hash": "sha256:…",
  "content": { "phrases": { "halo-levels": { … }, … } }
}
```

### A show file

```json
{
  "format": "arsenal.stage-show/v1",
  "id": "amazing-2026-10-29",
  "base": null,
  "set": "source-v1",
  "layers": { "colour": "amazing-2026-10-29@1", "phrases": "amazing-2026-10-29@1", … },
  "created": "…", "notes": "…", "hash": "sha256:…"
}
```

- **Ids** use the same rule as set names: `^[a-z0-9][a-z0-9-]{0,40}$`. A reference is `id@version`, and `parent` is `layer/id@version`.
- **Hash** is SHA-256 over canonical JSON (keys sorted, no whitespace) of `content`. It uses a small pure-JS SHA-256 shared by Node and the browser, because `crypto.subtle` is missing when the page is opened over a LAN address (your phone, plain http).
- **Size limits:** 2 MB per layer file, 16 layers per show, base chain at most 8 deep.

### How a layer is applied

`content` is a **patch over the scene**. Objects merge field by field, arrays replace whole, and nothing is deleted. All of this happens in a new pure module `packs.js`, which is called in `stage.js` right after the scene JSON is fetched and **before** `validateScene`, `validatePhrases`, `validateRingFormations` and `validateKick`. The same is done for the setups document before its setup validator and for palettes before theirs. Every check the stage already has therefore still runs on the patched result. The pack loader is a second fence in front of the existing ones, not a replacement for them.

### How the loader validates, in order

1. **Format and hash.** A wrong format, a malformed id or a hash mismatch refuses the layer with a reason. A hash mismatch means someone edited the file by hand; the CLI fork is the right way. That layer falls back to the base. The rest of the show loads, the same way a bad setup is refused today while the others load.
2. **Allowlist per layer.** Each layer may only carry its own paths: the phrases layer can only touch `phrases`, the haze layer only `atmos.{tau,pre_haze,wind,noise}`, and so on. Any other key refuses the layer.
3. **Denylist: refused outright, whatever the layer.**
   - `kick.strobe`, `kick.governor` (the whole blocks)
   - `ring_formations.hero`, `ring_formations.column`, `ring_formations.*.shimmer`
   - any `atmos` cap, `hazers`, and anything that is rig structure (`objects`, `types`, `groups`, mounts)
   - `bloommix` and the `flash` / `flashProtection` consent in the viewer layer
   - **phrase `flash` lines:** a phrase may carry a flash line only if it is deep-equal to the base set's flash line for the same phrase, step and line. A pack can never add, move or strengthen a flash. A new phrase can carry no flash at all.
4. **One-sided values are clamped toward safe and reported.** These numbers were measured against the limiter, so a pack may lower them but never raise them:
   - `kick.kinds.*.punch` ≤ 0.15
   - `kinds.*.strobe` may go true → false, never false → true
   - setup `luma_cap` ≤ 0.35
   - in v1: the fly-out pop ≤ 0.85, and distance comfort `LOG_RATE_MAX` ≤ 4.5 and `LOG_ACCEL_MAX` ≤ 25

   Each clamp is listed in `__stage.state().pack.problems`, and the HUD shows a `*` next to the show name.
5. **The engines keep their caps whatever the pack says.** These are code and stay code: FlashGate (one flash per bar), FLASH_MIN_DECAY 0.5, FLASH_LIFT, PIN_TAU 1.2 s, PALETTE_DIP, the red refusal and the red-free wheel path, `governEffect` (unison floor 60 %), the frame limiter and its LIMIT/SOLVE tables, STROBE_HZ_CAP 1.9, the kick governor, the ensemble `attack()` join rule, GATE_FLOOR 0.7, MIN_ONSET 0.25, the GATES table and groupGate, the fast-hit choke, the laser red swap, the 2° camera exclusion, the 4 m near-camera fade, power share, CLEARANCE_M and GUARD_M, the hoist MODES, RING_CLEARANCE and the motor slews. **A pack may name a gate, a flash or a mode. It can never define or loosen one.**

Packs are data only: no scripts and no `eval`, ever. This is the house's provenance rule applied to show files.

---

## 4. Switching

### URL (v0)

- `?pack=amazing-2026-10-29` loads a show.
- `?pack.phrases=my-halo@2` overrides one layer on top of the show, or on top of the set if no show is given. If `@N` is left off, the newest version is used and the HUD shows which one that was.
- `?pack=none` forces the plain set.
- When a URL parameter and a pack disagree, the URL wins. Explicit beats implicit.

In v0 every switch is a **reload**. It is the simplest option and fully covered by the proof above.

### Live switching (v1)

Each layer switches at the earliest moment the census shows to be safe:

| when it lands | layers | how |
|---|---|---|
| **at once / frame** | finish, pads (controls), feel (ensemble), setup library | finish: `render.look` is read every frame. Pads: `padMap` is read on each press. Setups: through the existing beginSetup crossfade (which keeps its safety dip) |
| **next bar line** | colour palette | the existing beginPalette, which keeps its 1-beat dip |
| **next entry** | looks (next section), effects (next effect start), aim (next step), running order (next section), formations (next landing) | swap the tables in `rig` in place; the engines read them when the next thing starts |
| **next phrase repeat or Go** | phrases | replace the keys inside `rig.phrases` (the runner holds a reference to that object, so swapping in a new object would be missed), then clear `runner.decks[name]`. The repeat counters persist on purpose, so the per-repeat cycles do not restart |
| **next section, rebuilt** | camera (new Director, about 0.25 s of setup work, so it is built ahead and swapped on the section line), lasers (`buildLaserGroups` between phrases) | re-init hooks |
| **reload only** | kick, haze, fader map and starting values, viewer | kick stays reload-only in v1: a fresh Kicks object would reset the governor's own state mid-show, and that is not worth the risk. Haze gets a re-init hook in v1 |

When a show is changed live, everything that can land does so at its moment. The HUD lists anything still waiting: `waiting for reload: kick, haze`.

### Key and pad

- `]` and `[` step to the next and previous show in `index.json`. These keys are free today; used keys are Q W E P O H U L F C Esc and the digits.
- Two new pad-map actions, `show-next` and `show-prev`, can be put on any spare pad. The pad map is data, so this is a controls-layer change.

### HUD and page doors

- The HUD gets one new line: `SHOW amazing-2026-10-29` (plus `*` if anything was refused or clamped). In expanded form it lists `colour v1 · phrases v2 …`.
- `window.__stage.state().pack` = `{show, layers: {name: {id, version, hash, from}}, problems}`. `stage_verify` writes this into `receipt.json`, so every receipt says which show it ran.
- A window event `arsenal:pack` fires on change, the same pattern as `arsenal:setup`.

---

## 5. Compare, freeze and fork: `arsenal/lanes/stage_packs.mjs`

This is a Node CLI. It uses the same `packs.js` the page uses, so the CLI and the page validate the same way.

| verb | what it does |
|---|---|
| `freeze <show> [--from e9f5e3cbc \| --tree <path>] [--set source-v1]` | reads every layer's current values and writes new versions only for layers whose hash changed (unchanged layers point at their existing version), plus a show that points at them |
| `diff <showA> <showB> [--layer phrases]` | goes layer by layer in plain words, e.g. `colour: same` · `phrases: halo-levels, per-repeat colour went from beamA → W → beamB to W → beamA → beamB; variant deck lost "rush"` · `effects: levels-step measure 3 → 4 beats`. A label table built from the census turns paths into names (`per_repeat.hpan` → "horizontal pan swing") |
| `fork <layer> <from id@v> <new-id>` | copies one layer with `parent` set, so you can change that component alone |
| `show <id> --base amazing-2026-10-29 --set phrases=my-halo@1` | builds a show from layers |
| `check <file>` | runs the loader's validation and prints every refusal and clamp |
| `list` / `url <show> [--port]` | the shelf, and the URL to open a show |
| `import <downloaded.json>` | takes a show frozen from the page (below), checks it and files it |

**Freezing from the page (v0):** a HUD button, **Freeze**, builds the current show from what is on screen: the current setup, palette, fader positions and the loaded layers. The browser then downloads it as a JSON file. That download is your click. `stage_packs.mjs import` then files it.

**Side-by-side:** `stage_packs.mjs compare A B` prints two URLs. In engine mode both tabs follow the same beat engine (:8794), so they land on the same beat. In demo mode each tab runs its own clock, so they drift. Use `&quality=low` on the comparison tabs: running two full-quality renders at once doubles the GPU load. In v1, `compare.html` puts the two shows in one window as two iframes.

---

## 6. Slices

### v0: "the snapshot shelf". Data only, switch by reload.

- **Layers:** colour, looks, effects, phrases, aim, formations, lasers, camera, running order, kick, haze, controls, viewer (13). Every one is already JSON in `source-v1.json`, `setups.json` or `palettes.json`, or is something a URL parameter already sets.
- **Files touched:**
  - new `arsenal/web/stage/packs.js` (merge, allowlists, denylist, clamps, hash): about 300 lines
  - new `packs/` with the 13 layer files and the show, which are copies of the tagged blocks
  - `stage.js`: about 30 lines. Read `?pack`, fetch the show and its layers, apply them before the validators, expose `api.pack`, add the HUD line and the Freeze button
  - new `arsenal/lanes/stage_packs.mjs`: about 350 lines
- **Tests to add:** `tests/stage_packs.test.mjs`
  - P0, P1, the hash round-trip, and fallback from a missing layer to the base
  - one refusal fixture per denylist entry
  - the clamps (punch 0.2 → 0.15, luma_cap 0.5 → 0.35, strobe false → true refused)
  - a new or moved flash line refused
  - an unknown key refused
  - diff and fork output on fixtures
- **Proof of no change:** P0 to P4b, and P5 as well before your page moves.
- **Size:** about a day of build plus a proof run.

### v1: "live and lifted". Medium.

- **Live switching** as in §4: `[` and `]`, the show pads, the camera and laser-group rebuild hooks, the haze re-init.
- **Code constants lifted into tables, same numbers, one per commit, old exported names kept as the defaults** (the tests import `LOG_RATE_MAX`, `WIDTH`, `STOPS`, `MIN_SHOT_BEATS` and others by name):
  - render LOOKS (finish layer)
  - laser `SHAPE_DEFAULTS` (`lasers.js:346-397`)
  - Grammar G and ensemble BREATH, passed as constructor opts (feel layer)
  - `Director` `opts.safe` and `opts.glides` (stage.js then passes `rig.cameras.glides`)
  - distance comfort as a config object, gentler-only
  - handheld wander
  - small timing constants: default look fade 2, phrase release 1, held-go +4, Lantern Walk 64 / ×4, fly-out tilt, delay and envelope with the pop capped at 0.85
  - HAL.glowMix and the cube spin rates, the haze feel constants, show.js speed detents and demo defaults
- **One rotation block:** the colour layer becomes the single source for rotate, min and fade. The old three-way merge is kept for runs with no pack.
- **Saving from the page:** an append-only loopback endpoint that writes new version files only. It answers 409 if `id@version` already exists. It uses pianolooks' rules: loopback Host and Origin only, JSON only, atomic temp-file-then-`os.replace`, size limits, never overwrite a file it cannot read. This depends on Q2.
- **Tests:**
  - for each lift, defaults equal the old literals, pinned by name
  - a new `stage_verify` phase: switch A → B → A at bars 16 and 32; flash counts and FlashGate grants stay within the base run's bounds, limiter interventions stay 0, and state after returning to A matches A
  - "switch to the identical show mid-run" leaves the receipt unchanged
- **Proof:** P2 to P5 for every lift commit, in both modes.
- **Size:** about 2 to 3 times v0, best done as 8 to 10 small commits.

### v2: "code sequences become data". Hard; each item is its own slice.

This is where your "logic and animation sequences as preset packs" really lands.

- **The pattern:** a code sequence is turned into data, plus a small declarative interpreter that turns that data into the forms the engines already use (EffectInstance waveforms, group-shape lines, keyframes). There is never a script inside a pack.
- **Items, roughly in order of value:**
  1. Section laser looks (`lasers.js:486` lattice, ceiling, tunnel, fans) rewritten as group-shape lines.
  2. The pad-2 hit engine's pattern deck and bank rotation. The tiers, the choke and the gates stay code because they are safety.
  3. The `formations.js` LOOKS and SCENERY numbers, and the `kinetics.js` shape defaults. The shapes themselves stay code until a shape vocabulary exists.
  4. Kick-5's bank order when no setup is active (programmer bankCycle).
  5. HAL shader constants, behind a hook that re-pushes the uniforms.
  6. The director's landing-window numbers.
- **Proof for each item:** frame-by-frame equality at the module's output (beam list, fixture values, ring targets) for every section over 64+ bars, before against after, exact or within 1e-9. Then P4 and P5.
- **Size:** days per item.

---

## 7. Open questions for Daniel (recommendation first)

1. **Should your page load `amazing-2026-10-29` by default?** *Recommend: not in v0.* No pack means the code path is literally unchanged. Once v1 live switching exists, make it the default so the HUD always names a show. The two are identical, so nothing on stage changes either way.
2. **How should "save the current settings" work on the page?** *Recommend: a Freeze button that downloads the file in v0, so there is no server change; then an append-only save button in v1.* The v1 button needs a small endpoint on the server that runs your page (:8796). The census did not check whether that server already routes `/api`.
3. **When you step to another show from a pad mid-set, where should it land?** *Recommend: one press, and each layer lands at its natural moment* (colour and finish on the next bar, looks and the running order on the next section, phrases on their next repeat). The HUD shows what is still to come, so the change settles within 8 bars rather than snapping all at once.

---

*Census sources: the three census lanes, quoted in the brief; the spot-checks in this design were read from `E:/AI-Setup/.claude/worktrees/stage-v4/arsenal/web/stage/` (`stage.js:144-160, 338-404`, `phrases.js:396-418`), with no edits.*

---

## Census lane: colour-light (verbatim)

## Colour-light census, stage-v4 (read only; worktree untouched)

Root: `E:/AI-Setup/.claude/worktrees/stage-v4/arsenal/web/stage/`. "Load" means the value is read once when the page starts, so a pack swap needs a re-init. "Entry" means it is read when a section, look, phrase step or effect starts, so a swap takes effect at the next change. "Frame" means it is read every frame, so a swap takes effect at once.

**SAFETY** marks something a pack must never carry or loosen. **SAFETY-adj** marks a brightness or flicker number that was measured against the limiter: a pack may lower it, never raise it.

---

### 1. sets/setups.json (format `arsenal.stage-setups/v1`): already a pack

| file:line | name | on stage | value | data/code | lift | readers | when read |
|---|---|---|---|---|---|---|---|
| setups.json:4 | rotate_bars | bars between automatic setup changes | 16 | data | easy | setups.js loadSetups → stage.js:342 | load |
| :5 | min_bars | least bars a hand-landed setup stays | 8 | data | easy | same | load |
| :6 | fade_beats | crossfade length into a new setup | 4 | data | easy | stage.js:373/386 → programmer.beginSetup | load |
| :7 | order | rotation order | 8 ids | data | easy | loadSetups, stepSetup | load |
| :19–764 | setups[] | palette x placement: which colour goes on each of 13 light groups | 8 setups (ice-spine, gold-sapphire, neon-split, aurora-column, source-fan, ember-cathedral, cyan-crown, black-and-one). Each has 3–8 named hex colours, a `cycle` of 2–4 colours, `place` for all 13 groups (a/b/w, left/right, pin, join), `lasers` 1–3, `laser_bank`, `cubes.glow` [2] | data | easy (validated on load; a bad setup is refused and the rest load) | compileSetup → programmer.js:836 tableInto, :844/:951 cubesAt, :610/:870/:913 lasersAt | load; the active setup's tables are read every frame; switching setups is already live through the beginSetup crossfade |
| per setup | cycle | the colours kick 5 turns through inside the setup | e.g. ice-spine blue/violet/sky | data | easy | nameAt, cubesAt | frame |
| per setup | place.strand.{heads,dots,bars}.pin | Daniel's white centre row held | pinned in 7 of 8 (not black-and-one) | data | easy | compileSetup | frame |
| per setup | luma_cap (optional) | that setup's brightness ceiling | not set in any setup (falls back to 0.35) | data | easy, but **SAFETY-adj** (see setups.js:71) | levelOf | frame |
| per setup | warm | allows amber-hue colours | true on gold-sapphire and ember-cathedral | data | easy | validateSetup amber guard | load |

### 2. setups.js (code)

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 43 | SETUP_GROUPS | the 13 groups a setup places (must match programmer BANK_GROUPS; a test pins it) | 13 names | code table | leave (it is a schema) | everything | load |
| 48 | ROLE_SLOT | which slot each stage role shows (a/b/w) | 12 roles | code table | medium | tableInto | frame |
| 55–60 | SETUP_LIMITS bank_de 0.08, bank_mid_de 0.04, cycle_de 0.1, cycle_chroma 0.06, laser_floor 0.58, path_samples 17 | validator bars: every press visibly changes every group, lasers bright enough | as listed | code constant | easy, but these are the pack *validator*, not pack content | validateSetup, bankProblems, cycleOf | load / per cycle |
| 71 | luma_cap | caps setup colours to the dimmest cycle colour; centre row ≤ 0.35 luminance. Measured: without it the limiter acted on 35–49 of 480 frames | 0.35 | code (per-setup override exists) | **SAFETY-adj**: may only go down | levelled, levelOf → tableInto | frame |
| 75–121 | PATH, mixPath, pathClean, pathOf | crossfade route OKLab → OKLCh short → long → cut, never through red | logic | code | hard | programmer crossfade, lasersAt fan ramp | frame |
| 111, 264–265 | redMax > RED_CAP, inRedSector | red rule on every crossfade sample and setup colour | RED_CAP 0.78 (palettes.js:24) | code | **SAFETY** | validateSetup, pathClean | load / per fade |
| 266 | AMBER guard | non-warm setups may not hold amber | hues 40–105 (palettes.js:26) | code | taste rule, not safety; keep in validator | validateSetup | load |
| 226 | laser fan ramp | 32-sample gradient between the first two laser colours | 32 | code | easy | lasersAt | per bank step |
| 387–394 | nextAutoLine, nextBarLine | where O and the automatic rotation land | logic | code | leave | stage.js | frame |

### 3. sets/source-v1.json: the live set (the default; `?set=source-v1`)

**Colour**

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 728–812 | themes | legacy palettes: 12 roles + laser[3] + ambient (+ air_tint) | 6 themes (source-violet, molten, dreaming-city, genesis-indigo, vex-conflux, anti-sun) | data | easy | programmer (theme roles), stage.js ?theme | load; P crossfades |
| 1290–1291 | show.theme / show.palette | starting palette | "source-violet" | data | easy | stage.js:113 | load |
| 766 | dreaming-city.air_tint | haze takes the ambient hue at the same luminance | 0.8 | data | easy (atmos.airTint keeps luminance) | render.js airTint | frame |
| outside lane | arsenal/web/palettes.json | the 30 palettes that kick 5's bank cycles (the bank order is built in programmer.js bankCycle) | 30 palettes + wheel + rules | data (bank ordering is code) | palettes easy; bank ordering hard | programmer, kick, setups "@Role" | load |

**Looks, effects, ring_fx**

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 604–673 | looks | per section, each group's Dimmer/Pan/Tilt/Zoom/Color role (+Color2) and effect list | 5 looks (intro, build, drop, break, groove) x 7–8 lines; fade 0.25–4 beats | data | easy | programmer | entry (section change) |
| 259–523 | effects | the pattern library: waveform x spread x measure in beats | 34 defs. Ring ones are polar, step, colour, chopper, colour-bump, spiral, sunburst, ripple, wipe, sparkle, sweep, thirds, segment-hold, shimmer | data | easy | effects.js EffectInstance (governEffect applied on start), lasers.js, phrases | entry (copied when the effect starts) |
| 1373–1391 | ring_fx.effects | the ring-effect menu | 14 names (pointers into effects) | data | easy | phrases / ringfx | load |

**The 3 levels of light, horizontal flash and pan, verticals 1-2-3**

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 344 | levels-step | the 3 halo levels one per beat: top, middle, bottom | square, width 0.3333, measure 3, order level, block ties, phase 0 → −360, clean | data | easy | EffectInstance | entry |
| 356 / 367 | pinch-step / levels-rush | variants: top+bottom then middle; fast rush | width 0.5 measure 2 / width 0.3333 measure 0.75, floor 0.6 | data | easy | same | entry |
| 1393–1400 | presets.layers | altitude each third aims at over the crowd | y {0: 26, 1: 15, 2: 8} m, x_scale 1.8, z 30, shift $layer_shift | data | easy | phrases presetTarget | entry |
| 1401 | presets.horizon | horizontal row aim | Pan 0, Tilt 86 | data | easy | phrases | entry |
| 1402 | presets.vertical | straight up | Pan 0, Tilt 0 | data | easy | phrases | entry |
| 379 | hrow-pan | the horizontal pan sweep | rampUp, size 40, measure 2, shots 1, delay 1, order x, 0 → −45 | data | easy | EffectInstance | entry |
| ~1445 | step B `flash` line | the horizontal flash | to 1.0, decay 0.5 beat, **via FlashGate**, refused → lift | data | **SAFETY**: packs must not carry or alter it | phrases.js → programmer FlashGate | entry |
| 389 / 400 | vert-step / vert-depth | verticals 1-2-3 outward by column / by depth | square, width 0.25, measure 4, 0 → −270, block ties, clean | data | easy | EffectInstance | entry |
| 1405–1536 | phrases.halo-levels | the whole sequence: A levels 12 beats, B hflash+pan 4, C verticals 4, D lasers 8, E halo pattern 4 | 5 steps, base 7 lines, 8 bars, go on bar | data | medium (the step structure is data, but `$vars`, `vary` and `cues` are interpreted by phrases.js) | phrases.js | entry (per repeat) |
| 1526–1536 | vary.deck / variants | variant rotation | deck daniel, pinch, ascend, rush, depth; no_repeat | data | easy | phrases.js | per repeat |
| 1537–1550 | per_repeat | the colour and motion cycles per repeat | colour [beamA, W, beamB]; vert_colour [W, beamB, A]; laser_colour [0, 2, 1]; laser_colour2 [1, 0, 2]; hpan ±40; hpan_start ∓40; halo_group [halo, r0, r1, r2]; chop_offset +0.2856 mod 1; chop_to ±720; layer_shift seeded [−2, 2] | data | **easy, high value** | phrases.js | per repeat |
| ~1478–1495 | step E halo pattern | halo chop pattern | corona-chop (411: width 0.39, floor 0.85, size 0.4, measure 0.5) + ring-chopper (422: width 0.39, measure 0.5); Color beamB / W+A | data | easy | phrases, effects | entry |
| 1584–1867 | other phrases (single-thread, pillars, scissor-gates, tunnel-spokes, drumroll-iris) | 5 more sequences, each with per_repeat | 5 phrases | data | medium | phrases.js | entry |

**Kick**

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 1334–1337 | kick.kinds | pad 1 = white, pad 5 = bank | colour white / bank, motion bands, repeat motion / colour, strobe true, punch 0.15 | data | easy for colour, motion, repeat; **strobe and punch are SAFETY-adj** | kick.js kickConfig | load (new Kicks) |
| 1338–1343 | kick.deck | the 4 areas a kick deals | rings, beams (6 rows), halo, strand | data | medium (validator forbids shared members) | kickConfig resolveCard | load |
| 1344–1348 | kick.bands | velocity → animation | peak 0 / sweep 0.45 (M1 25°) / drive 0.85 (M1 50°) | data | easy | bandFor | load |
| 1349 | kick.level | strip height → intensity | floor 0.5, gamma 0.5, slew 0.06 s | data | easy | intensityOf | load |
| 1350–1353 | release 0.3, tap_hold 0.125, max_hold 64, chase {0.8, 0.6} | fade and hold feel | as listed | data | easy | Kicks | load |
| 1354 | kick.strobe | strobe | from_level 0.95, max_hz 1.9, beats [0.5, 1, 2, 4], on 0.35, hold 0.25 s | data | **SAFETY**: never pack | Kicks | load |
| 1355 | kick.governor | limiter-headroom governor | need 2, defer 2 s, bank_min 0.2 s, comb_floor 0.35, equal_luma 0.35, linger 1, punch_s 0.15 | data | **SAFETY**: never pack (linger_s is feel but sits in the same block) | Kicks | load |

**Show, faders, atmosphere, formations**

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 1292–1312 | show.sections | per section: look, formation, laser look and level, camera, speed_by_bar, phrase | 5 sections; drop 24 bars + halo-levels x2 | data | easy | show.js, stage.js | entry |
| 1313–1324 | show.demo | ?demo=1 plan and scheduled pads | 150 BPM; plan 8/8/24/8; 6 pad rules | data | easy | show.js | load |
| 1325 | show.pads | pad → action | 14 entries (5 kick-colour, 11/12 palette, 13/14 setup) | data | easy | stage.js | load |
| 1326 | show.setups | first setup + rotation | first ice-spine, 16/8/4 (**duplicates setups.json:4–6 and stage.js:342; the set's values win**) | data | easy (consolidate) | stage.js:342 | load |
| 1327–1328 | faders / fader_defaults | CC map; starting levels | strand 1, lasers 1, haze 0.85, speed 0.5, grand 1 | data | easy | stage.js:398 | load |
| 712–727 | atmos | haze lag, pre-haze, wind, noise, 8 hazers | tau 1.5 s, pre_haze 0.12, wind [0.25, 0, −0.1], noise 0.6 | data | easy | stage.js:220 → Atmosphere | load |
| 542–603 | ring_formations | 6 formations: light, heads, lasers, core, bands, planets, motes, reveal | deck of 6; orrery core role A, 5 bands, sweep_beats [31, 29, 23, 19]; spiral gap 60° step 40°; vortex chase 3.7°/beat; crown period 64 | data | easy for colour roles, levels and rates | formations.js (this.F / def(key)) | frame |
| 546–547 | ring_formations.hero / column | the energy-beam discharge | charge 8 bars; hero_flux_lm 180000; core.hero_hot 1.2 | data | **SAFETY** (flash through FlashGate) | formations heroLevel | frame |
| 568 | orrery.shimmer | line-work flicker near the camera | depth 0.45 at 18 Hz | data | **SAFETY-adj** (18 Hz flicker): never raise | formations _bandShimmer | frame |

### 4. sets/source-v0.json (234 lines)
Legacy; it only loads with `?set=source-v0`. It has the same blocks in smaller form: 2 themes (source-violet, molten), 5 looks, 15 effects, 2 formations, atmos, show. It has no kick block, so it runs the v0 strand lift (kick.js:352). All of it is data. **Leave it out of packs.**

### 5. show.js

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 24 | SPEED_DETENTS | F6 speed steps | [0.25, 0.5, 1, 2, 4] | code | easy | speedFromFader | frame |
| 57, 85, 101 | default groove / drop length | engine-mode section lengths | 16 bars | code literal | easy | Show.update | entry |
| 138–139 | demo pad vel / hold defaults | used when a pad rule omits them | vel 0.85, hold 0.25 beat | code literal | easy | _demoPads | per beat |

Everything else in show.js is sequencing logic and stays code.

### 6. kick.js (pads 1 and 5)

| line | name | on stage | value | data/code | lift | when |
|---|---|---|---|---|---|---|
| 158–161 | KICK_VISIBLE {de 10, share 0.5}, VIS margins, SAT_COLOUR 0.3 | dealer's "the hit shows" bar | as listed | code | leave (verifier bars) | per press |
| 164–165, 341 | STROBE_HZ_CAP 1.9, min edge 0.263 s; the set's max_hz is clamped to it | strobe cap | 1.9 | code | **SAFETY** | load |
| 174 | PHASE_JUMP | pattern lurch on a colour kick | 0.25 cycle, eases over 1 beat | code | easy | per press |
| 176 | STRAND_EVERY | strand dealt at least once every N presses | 3 | code | easy | per press |
| 192–209 | DEFAULT_KINDS, KICK_DEFAULTS | fallbacks behind the set's kick block | same values as source-v1:1331–1357 | code | already overridable from the set | load |

The kick 5 colour bank itself: inside a setup the bank is data (setups.json `cycle` and `laser_bank`). Without a setup the bank is built from the palette in programmer.js bankCycle/bankAdvance, which is code and outside this lane, so it is hard to lift.

### 7. effects.js

| line | name | on stage | value | data/code | lift | when |
|---|---|---|---|---|---|---|
| 40–41, 213–233 | UNISON_FLOOR 0.6, UNISON_SPREAD_DEG 90, governEffect | a unison Dimmer pulse never goes below 60 %; full-depth pulses only as chases spread ≥ 90° | 0.6 / 90 | code | **SAFETY**: never pack. It is applied at every effect start, so pack effect defs stay protected | entry |
| 160–206 | FORMS / waveform | the 11 shapes (sine … sparkle) | 11 | code | hard (new shapes need code); packs only choose among them | frame |
| 71 | ORDERS | spread orders (level, column, depth, clock …) | list | code | leave | load |
| 254 | setScale grace | speed change lands on a line | 0.05 beat | code | leave | frame |

Effect definitions are data (source-v1 :259–523). An EffectInstance copies its def when it starts, so a pack swap takes effect at the next look or step.

### 8. formations.js (ring morphs, colour of the halo and rings)

| line | name | on stage | value | data/code | lift | when |
|---|---|---|---|---|---|---|
| 509–656 | LOOKS orrery, spiral, vortex, crown, portal | the per-cell patterns: dial ticks every 6th slat, lancet frieze, dot chain, comb, spiral gap, ladder chase, bead, comet | patterns written as code; the tunable numbers are read from data through `?? default` | code | **hard** for the shapes; **easy** for the numbers already in ring_formations | frame |
| 494 | DEFAULT_ROLES | fallback role colours (8 RGB) | 8 x 3 | code table | easy | frame |
| 658–694 | LASERS (orrery, spiral, vortex) | ring and hero laser aim, colour index, level | levels 0.18–0.4 | code with data fallbacks | medium | frame |
| 696–780 | SCENERY (orrery core, bands, planets, motes; spiral bead) | emitter nits and textures | dot 9000, port 30000, planet 700 / 4000 nits | mostly data with code fallbacks; the 4000-nit planet arm and the spiral bead's 9000 are code literals | medium; **SAFETY-adj** wherever the hero `hl` multiplies brightness | frame |
| 242–271 | hero: charge, FlashGate request, attack 0 if granted / 0.125 if refused | discharge timing | 8 bars | code + data | **SAFETY** | frame |
| 783–813 | BEAM_END_OK, beamEnds | beams never end on the crowd | roof, deck, backwall, orb | code | **SAFETY** (crowd) | test |

### 9. cubes.js

| line | name | on stage | value | data/code | lift | readers | when |
|---|---|---|---|---|---|---|---|
| 44–69 | HAL | HAL 4000 cube look: 3 loop rings (half, radius, gain, glow, pen), widthPx 1.5, haloPx 18, hotFloor 0.4, heat 0.35, lineGain 1.1, haloGain 0.5, innerGain 0.1, backDim 0.4, defocus 0.45, glowMix 0.7, tumble 1 | 15 fields + 3 x 5 ring table | code (frozen table) | medium: render.js:260–267 copies it into shader uniforms once, so a live switch needs a uniform update | render.js | load |
| 67 | HAL.glowMix | how far each cube's glow leans to the strand gradient | 0.7 | code; overridable per setup (`cubes.glow_mix`) | **easy** | cubeTintOf | frame |
| 76–78 | SPIN_RATE 0.16, WOBBLE_RATES, HAL_WOBBLE 0.14 | cube tumble | as listed | code | easy | tumbleAngles (render) | frame |
| 105 | LUT_N | gradient samples | 17 | code | leave | — | — |
| 132 | DEEP_FALLBACK | glow fallback colour | [0.03, 0.01, 0.2] | code | easy | — | — |
| stage.js:745 | palette defaults | glow runs from the palette's deep to its B | — | code | medium | stage.js | frame |

The setup's cube glow and core are already data (setups.json `cubes`). The `?cubeglow`, `?cubecore` and `?cubetumble` URL switches and api.cubeTint are already live.

### 10. atmos.js (haze)

| line | name | on stage | value | data/code | lift | when |
|---|---|---|---|---|---|---|
| 45–46 | SIGMA_MIN 0.003, SIGMA_MAX 0.02 | full-fader haze density | 0.02 | code | leave (receipts are drawn at it) | frame |
| 47–48 | HAZE_CAP 0.26, PLUME_CAP 15 | density ceilings (tested at stage_atmos.test:80) | as listed | code | **SAFETY-adj** (whiteout): never pack | frame |
| 50–51 | HAZE_G 0.75, FOG_G 0.85 | scatter lobe | as listed | code | easy, but changes every beam's brightness; leave | frame |
| 53–55 | HAZE_MIN_RATE 0.05, HAZE_ARRIVE 0.02, HAZE_CURVE_K 3 | fader feel and curve | as listed | code | easy | frame |
| 125–127 | plume drift 6 s, radius 7 m, plume strength 0.012 x output | hazer plumes | as listed | code literals | easy | frame |
| 89 | constructor defaults | tau, preHaze, wind, noiseAmp | overridden by the set's atmos block | data | easy | load |

### 11. flash.js: SAFETY, list only, do not pack

- `LIMIT` (62–65): N_MAX 5 transitions per 1.01 s window, TH [0.07, red 14], HYST [0.02, 2], TH_REST [0.09, 18], MARGIN, RUN_S 5, REST_S 2, REST_COUNT 4.
- `SOLVE` (67–85): PARTIAL, sweep counts (24 soft, 600 hard), RELAX 1.5, RISE_FLOOR, LIFT_FIRST, WHITE 0.15, GAIN_BACK, Q_MIN_Y, AIM, LIFT_SLACK.
- Grid and windows (87–96): 4 x 4 cells, 5 x 5 corners, 18 windows.
- Classes: Tracker, FrameLimiter, applyRGBA8, presentGains (the `protect` toggle).

Related SAFETY items outside flash.js:
- programmer.js:118 `FlashGate` (minBeats 4).
- stage.js: the flash-consent toggle (`?flash=on|off`, the HUD checkbox, remembered in the browser; test stage_flash_consent).
- palettes.js:24 `RED_CAP 0.78` and the red sector.
- The phrase `flash` lines.
- Everything marked SAFETY above.

**Pack rule:** a pack loader should refuse any of these keys: kick.strobe, kick.governor, kinds.*.strobe or a punch above 0.15, luma_cap above 0.35, phrase `flash` lines, ring_formations.hero / column / shimmer, and any change to the haze caps. Dimmer floors in effect defs need no rule, because governEffect re-applies the floor anyway.

---

## Best candidates for pack v1 (all already data, no behaviour change)

1. **The setup library**, setups.json whole: 8 setups, their order, rotate 16 / min 8 / fade 4. It is already validated and refuses bad entries. Switching is already live through the beginSetup crossfade. Snapshot = copy the file.
2. **Palette choice and palette order**: show.palette plus a pick or order from palettes.json (30 palettes). Kick 5's bank follows the palette on its own.
3. **One rotation block.** Today rotate/min/fade lives in three places: setups.json:4–6, source-v1:1326 and stage.js:342. Make the pack the single source.
4. **halo-levels per_repeat cycles** (source-v1:1537–1550): colour, vert_colour, laser_colour 1 and 2, hpan ±40, halo_group, chop offset. These are the colour and pan sequence of the 3 levels, the horizontal pan and verticals 1-2-3. They are read per repeat, so they swap live at the next repeat.
5. **The vary deck and variants**: daniel, pinch, ascend, rush, depth.
6. **The light-pattern effect library**: levels-step, pinch-step, levels-rush, vert-step, vert-depth, hrow-pan, corona-chop and the ring-* effects (source-v1:259–523). They swap at the next effect start, and governEffect keeps them safe.
7. **Looks**: the 5 sections' role and dimmer lines (604–673). They swap at the next section.
8. **presets.layers / horizon / vertical**: the level altitudes 26 / 15 / 8 m, Tilt 86.
9. **Ring-formation colour roles and rates** (ring_formations light / heads / lasers / core roles and levels), excluding hero, column and shimmer. Read every frame.
10. **Look-and-feel extras**: fader_defaults (haze 0.85), the atmos block (wind, noise, pre_haze, tau), HAL.glowMix and setups' cubes.glow_mix.

## Hard: leave for later

- **programmer.js bankCycle/bankAdvance** (outside this lane): kick 5's ordering without a setup is code.
- **formations.js LOOKS / SCENERY**: the orrery dial, lancet, comb and spiral shapes are code. Pack only their numbers.
- **HAL shader constants**: loaded once into uniforms. Packing them needs a "re-push uniforms" hook in render.js.
- **The setups.js crossfade path rules and the waveform shapes**: code.
- **The kick dealer and governor logic**: code and SAFETY.
- **Phrase step structure as a whole**: it is data, but `$vars`, `cues` and `split` are interpreted by phrases.js. It is packable as a whole phrase, but riskier than item 4.
- **source-v0**: legacy, skip.

## Notes

- Two settings are read only at load: the kick block (new Kicks in programmer.js:383) and the atmos block (stage.js:220). Switching packs live for these needs re-init hooks.
- The snapshot tag `snapshot/stage-2026-10-29-amazing` (e9f5e3cbc) already pins every value listed here. Pack v1 = setups.json plus the source-v1 blocks in items 2–10, copied out under that tag.

---

## Census lane: motion-sequences (verbatim)

## Motion-sequences census (stage-v4, READ ONLY)

Root: `E:/AI-Setup/.claude/worktrees/stage-v4/arsenal/web/stage/`. No files were edited, no git commands that change anything were run, no servers were touched, nothing was rendered.

**The finding that matters most:** most of the sequencing is **already data** in `sets/source-v1.json`. stage.js:148 fetches that file once at page load and stage.js:153 runs `expandScene` on it once. The data includes:
- 6 phrases (the phrase steps, variants and per-repeat values)
- 13 `laser_groups`
- 4 position `presets`
- 5 `looks`
- the `show.sections` map (each section's look, formation, laser look and phrase)
- 2 strand `formations`, 6 `strand_shapes`, 11 `ring_formations`, the `ring_rig` motion numbers
- 34 `effects`, 14 `ring_fx`
- `show.pads`, and `seed` 2014

The code modules are engines that read that data. The **laser shapes** (lasers.js) and **strand formation shapes** (kinetics.js) are the main animations still written as code.

Notation:
- **DATA** = JSON in the set file (or a frozen exported table that already accepts overrides). **CODE** = a literal, a function or a sequence written in code.
- Lift difficulty = **E** easy / **M** medium / **H** hard.
- **SAFETY** = flash safety. Packs must never carry or loosen these.
- **GUARD** = a physical or realism limit (not about flashes). Also keep out of packs.
- When it is read: **load** (once, when the page loads), **boundary** (at a section change, a phrase repeat or a Go), **frame** (live, every frame).

---

### phrases.js (the cue sequencer)
| file:line | name | what it does on stage | current value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| source-v1.json `phrases` | phrase defs | The sequences themselves: steps, beats, follow/go, lines, cues, camera, ambient, variants deck, per-repeat values | 6 phrases: halo-levels (8 bars, 5 steps, 5 variants, 12 per-repeat values), single-thread (8 bars, 1 step, 2 variants), pillars (8 bars, 3 steps, 2), scissor-gates (4 bars, 2 steps, 2), tunnel-spokes (8 bars, 3 steps, 2), drumroll-iris (8 bars, 4 steps, 2) | DATA | E | `PhraseRunner._compileNext` → `compileRepeat`; **boundary** (every repeat or Go reads `rig.phrases[name]` fresh) |
| phrases.js:400 | `this.phrases = rig.phrases` | Runner holds a **reference** to the set's phrase table | same object | — | note | Changing keys inside it works live: stage_verify.mjs:2102 already does this. Swapping in a whole new object would leave the runner on the old one |
| phrases.js:409-416 | `decks[name]` cache | Variant deck per phrase. Seeded shuffle, `first`, `no_repeat` | built once per phrase name | CODE (reads DATA) | M | A pack swap must clear `runner.decks[name]`, or the old variant names keep being dealt. `repeats[name]` persists across runs on purpose |
| phrases.js:68 | `resolveMods` rules | Per-repeat values: cycle, alternate, add/mod, seeded, value | grammar fixed; values in DATA | CODE grammar | — | once per repeat |
| phrases.js:43 | `GO_GRACE_BEATS` | A Go pressed this soon after a bar line lands on that line | 0.05 beat | CODE const | E | `goLine`; on every pad Go/Next/Stop |
| phrases.js:571 | goLine "4" | Go/Next/Stop quantise to the bar (4 beats is hard-coded) | 4 | CODE | M (it is the bar length; keep) | frame of the press |
| phrases.js:538 | held "go" step | A `trigger:"go"` step extends by 4 beats until Next | +4 beats | CODE | E | frame |
| phrases.js:132-135 | camera validator | `then.beats` at least 2 from either end; `precut_beats` in (0, 2] (precut stops a camera cut landing on a step's flash frame) | 2 / 2 | CODE rule | keep in code (sits next to safety) | load (validatePhrases, stage.js:154) |
| phrases.js:229-262 | preset defaults | world: y 15, z 30; radial: forward_deg 25, length 60 m; twist: centre along_normal 20; axis: p1 30 m; node/radial-from-point: point [0,14,-11] | inline `??` | CODE defaults; the presets themselves are DATA | E (defaults); presets are already data | `aimPreset`. **frame** while a ring is off its home pose (re-aimed), otherwise once per step |
| source-v1.json `presets` | position presets | Where head groups point | 4: layers (world), horizon (values), vertical (values), corona (radial) | DATA | E | per compile (**boundary**). `presets.layers.target` is also copied onto every laser line (phrases.js:357) |
| phrases.js:591 | `playPhraseEvents` releaseBeats | The look takes the fixtures back over this many beats when a phrase ends | 1 (stage.js:667 does not pass it) | CODE default | E | at phrase end |
| phrase `line.flash` | `{at,to,decay_beats}` | A horizontal flash written inside a phrase | data per line | DATA (passes through the FlashGate) | E, but **SAFETY**: a pack may name a flash, but can never change the gate or the minimum decay | programmer `_flashLevel` |

### programmer.js (the console: looks, phrase layer, playbacks)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| source-v1.json `looks` | section looks | The base state per section: group values and effects | 5 looks (intro, build, drop, break, groove); drop has 8 lines, fade 0.25 | DATA | E | `setLook`; **boundary** (section change) |
| programmer.js:1041 | default look fade | Crossfade beats when a look has no `fade` | 2 | CODE | E | setLook |
| programmer.js:118-128 | **FlashGate** `minBeats` | At most one horizontal flash per bar | 4 beats | CODE | **SAFETY** | `_flashLevel`, frame |
| programmer.js:114 | **FLASH_MIN_DECAY_BEATS** | A granted flash decays over at least this many beats | 0.5 | CODE | **SAFETY** | setOverlay |
| programmer.js:115 | **FLASH_LIFT_BEATS** | A refused flash becomes a lift over this time | 0.125 | CODE | **SAFETY** | frame |
| programmer.js:112 | **PIN_TAU_S** | Pinned cells follow the level this slowly, so no strobe or flash shows in them | 1.2 s | CODE | **SAFETY** | frame |
| programmer.js:113 | **PALETTE_DIP_BEATS** | Palette cut = the whole rig dips to black and back | 1 beat | CODE | **SAFETY** (a full-rig luminance swing) | beginPalette |
| programmer.js:166-168, 1084+ | **red refusal**, red-free wheel path, `bankDip` uses `kick.canDip()` | Saturated red never pulses; the wheel never runs lit through red; the bank's far wheel move happens in black only when the governor has room | code | CODE | **SAFETY** | frame |
| programmer.js:288 | `flyout_groups` | Which heads fly-out bursts | set: `show.flyout_groups`; fallback truss.heads + lip.heads | DATA (fallback in code) | E | load (constructor) |
| programmer.js:1136-1141 | fly-out shape | Outward tilt 28° × vel, delay \|x\|/40 (max 0.5 beat), 2-beat sine envelope, dimmer pop to 0.85 decaying to 0.15 | inline literals | CODE | E to lift; **flash-adjacent**: the pop does not go through the FlashGate, so a pack must not raise the pop level (0.85) | frame |
| programmer.js:809 | Lantern Walk | The bed walks one stop per 64 beats, crossfading over the first quarter (16 beats) | 64 / ×4 | CODE | E | frame |
| programmer.js:97-111 | BANK_ROLES / BANK_ORD / BANK_GROUPS / BANK_* tolerances / TEMPO_EFFECTS | Kick-5 colour bank: role order, the 13 groups it deals to, grey/pastel/twin thresholds; which effects follow the palette's tempo | frozen tables | CODE tables | M (colour lane, not motion; BANK_GROUPS is easy) | load (constructor) + setTheme |
| programmer.js:296-300 | slew fallbacks | Motor speeds when a fixture type lacks attrs (Pan 2.2 s, Tilt 1.4 s, Dim 0.08 s, Zoom 0.6 s, wheel 0.12 s/slot) | fallbacks; real values come from set `types` | DATA mostly | GUARD (physical motor limits; not pack material) | load |
| programmer.js:390-449 | overlay merge semantics | Phrase layer = latest takes precedence per attribute; dimmers crossfade over `line.fade` | logic | CODE | H (leave alone) | frame |

### grammar.js (chord phrasing recogniser)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| grammar.js:59-67 | `G` | Gesture windows. chord W = clamp(B×0.25, 60, 110) ms; strum gap 90 ms / span 300 ms / 3 keys; sweep interval [max(110, 0.28B), min(450, 0.95B)], ends after 450 ms; walk min(800, 2B); breathStep 1/9; settle slack 50; fallback beat 400 ms | 15 numbers in one frozen table | **DATA-ready**: the constructor already merges `opts` | E | `new Grammar` (stage.js:532) → **load**. Windows are frozen per lineage when it begins (grammar.js:78), so a live swap needs a new Grammar object or a change to `this.o`. A tempo change never reclassifies keys already played |
| grammar.js:69-70 | BREATH_CONTROL "B", CAMERA_CONTROL "C" | Which keys are modifiers | "B", "C" | CODE | M (key binding; belongs with the pad map) | frame |
| grammar.js:99 | B() bounds | Valid beat length range | 200..2000 ms | CODE | E | per candidate |

### ensemble.js (what chords and fades do)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| ensemble.js:30 | `BREATH` | Fade speed: one step (1/9) per 120 ms; Esc hands back over 4 beats; floor 0 | {1/9, 120, 4, 0} | **DATA-ready** (ctor merges opts) | E | `new Ensembles()` (stage.js:226) → load. `tick` reads `this.o` every frame, so editing `this.o` works live |
| ensemble.js:29 | `TRANSPORT_RANK` | Transport collapses STOP > NEXT > GO inside one chord | {"3":1,"4":2,"7":3} | CODE table | M: tied to `show.pads` 3/4/7; must change in step with the pad map | frame |
| ensemble.js:131 | handBack clamp | Beat length clamped to 250..1000 ms for the hand-back | 250/1000 | CODE | E | Esc |
| ensemble.js:120-130 | `attack()` join rule | A later chord member joins the first kick's punch at its current age; never a second punch; a re-strike never renews | logic | CODE | **SAFETY** (stops chords adding flash; review F1) | per kick press |

### kinetics.js (strand hoists, rings)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| kinetics.js:40-43 | `MODES` | Hoist limits. real: 0.5 m/s, 0.4 m/s², jerk 2, roll ±50; dream: ×3, roll 180 | 2 rows | CODE table | GUARD: a pack should *choose* real or dream, never edit these numbers | Strand setMode; load + mode switch |
| source-v1.json `formations` | high-wave / low-wave | Strand wave: centre 17 / 14.5, size 0.9, roll 16, measure 32 beats | 2 | DATA | E | `strand.land` at a section change (stage.js:440), **boundary**; lands on the next bar |
| source-v1.json `strand_shapes` | arch, valley, ramp, stairs, helix-sine | Still strand shapes (?strand=) | 5 + _about | DATA (params) | E | land |
| kinetics.js:160-197 | `formationTarget` switch | The shape maths: ceiling, low, helix, zigzag, star, arch, valley, ramp, stairs, wave. Inline defaults (helix roll0 -82.5 step 15; star front 6; wave centre 16, measure 32, spread 1) | 10 shapes as code | CODE | H for new shapes; E for the defaults (params already override them) | **frame** (target every step) |
| kinetics.js:46 | `SCURVE_MIN_M` | Moves longer than this may use the S-curve with cruise | 1.5 m | CODE | E | land |
| kinetics.js:201 | Strand home/limits | Rung home y 20; legal y 8..22; roll ±50 | ctor defaults | CODE | GUARD | load |
| kinetics.js:120 | Axis `omega` | Tracking stiffness of the follower | 5 | CODE | E but leave alone (feel, untested) | load |
| kinetics.js:250-274 | land "bar"/"phrase", 16 tries | Time-priority landing on the next bar/phrase line | "bar" from stage.js | CODE | E (land mode is a param) | land |
| kinetics.js:354-357 + source-v1.json `ring_rig` | ring motion numbers | Real hoist 0.5/0.4/2; dream scale 3, rotator 60°/s etc. | set file overrides the code defaults | DATA | GUARD | load / land |
| source-v1.json `ring_formations` | ring poses + reveal | Per-ring tilt/lift/yaw/spin(_beats)/axial, reveal order, stagger_beats; deck of 6 | 11 entries | DATA | E | formations.js `land` (**boundary**); validated (tilt 0..90; yaw/spin dream-only) |
| kinetics.js:476 | land lookahead | Ring target sampled 8 beats after the start | 8 | CODE | E | land |

### lasers.js (laser brain: hits, section looks, group shapes)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| source-v1.json `laser_groups` | laser groups | Ties projectors together by bank/level (A, B, towers, hero, core, halo top/mid/bot/tb, all…) | 13 | DATA | E, but built once by `buildLaserGroups` (rig.js:352). A pack must rebuild `rig.laserGroups` (a pure function of projectors + defs) | **load** |
| source-v1.json `show.sections[*].lasers` | section laser look | Which look and level per section (intro lattice 0.55, build tunnel 0.6, drop ceiling 0.75 reach 8, break fans 0.5, groove lattice 0.6) | 5 | DATA | E | stage.js:443, **boundary** |
| lasers.js:486-512 | `_look` lattice/ceiling/tunnel/fans | The section looks' animation. lattice breathes ±0.16 rad over 16 beats; ceiling 5 beams, sway over 8 beats; tunnel 16 beams, one spin per 8 beats; fans 7 beams, opening over 8 beats | 4 looks as code | CODE | H (sequence as code; could take the group-shape params) | **frame** |
| lasers.js:74, 340-397 | `GROUP_SHAPES` + `_groups` | The phrase laser animations. fan (spread 36°, 5 beams), sweep (measure 4, swing 30, spread 24, 4 beams, mirror), chase (measure 2, spread 30, 4 beams), scissors (±0.35 rad on the half beat), ceiling, lattice, tunnel (12 beams), fans (7), rain, bloom (open_beats 1, spread 64, 7 beams), levels, rim-corona | 12 shapes; defaults inline `??`, overridable per phrase line (dir, spread, beams, measure, swing, mirror, open_beats, forward_deg, k, from_beats/until_beats, level 0.8, colour/colour2) | CODE shapes; DATA params | E for the param defaults (one switch); H for new shapes | **frame**; lines set per step (`setGroupLines`, **boundary**); an unknown shape throws |
| lasers.js:406-408 | `_levels` fallback schedule + layers | Halo lasers fire with their third. Square, width 1/3, measure 3; layers y {26, 15, 8}, x_scale 1.8, z 30 | fallbacks; normally from the step's effect + `presets.layers` | DATA normally | E | frame |
| lasers.js:428 | `_corona` fallback | Spoke lit as the chopper blade passes: square 0.39, measure 0.5, -720° | fallback | DATA normally (followDef) | E | frame |
| lasers.js:86, 190-226, 449-483 | pad hit engine (pad 2) | PATTERNS deck of 8 (seeded shuffle); tier by beats since the last press (more than 4 → burst, more than 1 → onetwo, else triple); onset quantised to the quarter beat (1/8 grace); bank rotation A, B, both, alternate; 3-6 beams, 18-48° spread (seeded); level ×(0.55 + 0.45·vel) | code | CODE | M: deck list and bank rotation are easy tables; tiers and choke are **SAFETY**-adjacent | per press + frame |
| lasers.js:93 | **GATE_FLOOR** | Fast gates dip to 0.7, never to black | 0.7 | CODE (tests pin it) | **SAFETY** | frame |
| lasers.js:94 | **MIN_ONSET_BEATS** | Presses within 1/4 beat retrigger the same hit (a pad storm becomes one gate) | 0.25 | CODE | **SAFETY** | per press |
| lasers.js:95-100 | **GATES** | Pulse tables: burst, onetwo, triple, hold | 4 rows | CODE table | **SAFETY** (pulse rate) | frame |
| lasers.js:78-84 | **groupGate** none/onetwo/triple | Group strobe pattern, floored at GATE_FLOOR | 3 | CODE | **SAFETY** (a pack may *name* a gate, never define one) | frame |
| lasers.js:218, 222 | fast-hit choke, max 4 hits | A new fast hit kills the older fast ones | code | CODE | **SAFETY** | per press |
| lasers.js:103, 114 | red swap / `laserPalette` | Saturated red is never emitted | code | CODE | **SAFETY** | setColours |
| lasers.js:51-58 | head layout | 21 Lasers-v2 heads (A1-8, B1-8, SL/SR, HERO) at fixed picture spots | frozen | CODE (contract) | do not lift (vj-lasers contract) | load |

### lasers3d.js (picture → 3D beams)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| source-v1.json `lasers.reach` | reach per bank | How far beams are thrown over the crowd | A 0.9, B 0.6, S 0.4, H 1, R 8 | DATA | E | rig.js:405 at load; × the section's `reach` at frame |
| lasers3d.js:115 | **exclusionDeg** | A beam within 2° of the camera is cut to 10 % | 2° / 0.1 | CODE | **SAFETY** | frame |
| lasers3d.js:~129 | **near-camera fade** | A beam passing closer than 4 m to the camera fades | 4 m | CODE | **SAFETY** | frame |
| lasers3d.js:115 | **gamma / power share** | A projector's watts are shared across its beams (2/3/3 W from types) | gamma 1 | CODE + DATA types | **SAFETY** (power cap) | frame |
| lasers3d.js:68 | roomHit venue defaults | Roof 38, crowd 1.9, deck… | DATA venue | — | leave | frame |

### rig.js (mounting, groups)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| source-v1.json `objects`/`types`/`groups` | rig structure | Fixtures, mounts (projectors mount on a ring at angle_deg), groups (where/union) | 12 objects, 11 types, 41 groups, 33 projectors | DATA | not pack material (it is the build, not the show) | **load** (expandScene) |
| rig.js:209 | LEVEL_TOP_DEG / MID | The halo's thirds: top under 60°, mid 60-120°, bottom beyond | 60 / 120 | CODE | M: changes group membership; needs a re-expand. Leave out | load |
| rig.js:631 | COLUMN_TOL_M / DEPTH_TOL_M | Clustering for the column and depth order keys (verticals 1-2-3) | 2.0 / 4.0 m | CODE | M (load) | load |
| rig.js:448 | **RING_CLEARANCE** | Rings vs deck 2.5 m, wall 0.5, grid 0.4, heads 0.45 | table | CODE | GUARD (collision) | load + land |
| rig.js:715 | aimAt ranges | Pan 270, tilt 135, head offset 0.32 m | defaults | CODE | GUARD | frame (re-aim) |

### grid.js (beat and bar timing)
| file:line | name | what it does | value | data/code | lift | read by / when |
|---|---|---|---|---|---|---|
| grid.js:23-25 | SLEW_MAX_ERROR / SLEW_STRETCH / PHRASE_BARS | Clock correction (±0.25 beat, ±10 %); a phrase is 8 bars | 0.25 / 0.10 / 8 | CODE | infra: keep out of packs (one clock for everything). PHRASE_BARS feeds `nextPhrasePos` only | frame |
| grid.js:28 | BeatGrid defaults | bpm 150, presentLag 16.7 ms, flywheel 4000 ms | ctor | CODE | infra | load |
| grid.js:156 | DemoBeats | Demo lead 220 ms, conf 0.95; bpm from stage.js `demoBpm` | ctor | CODE | E (demo bpm is the only show-ish one) | load |

---

### Best candidates for pack v1 (behaviour stays the same; everything is data or a one-line read)
1. **`phrases`** (all 6, whole objects). Already JSON and already read fresh every repeat. To swap: change the keys inside `rig.phrases`, then clear `runner.decks[name]`. Takes effect on the next repeat or Go.
2. **`show.sections` sequencing map** (each section's look, formation, laser look/level/reach, phrase name/repeats/camera, `speed_by_bar`). DATA, read at each section change.
3. **`looks`** (5). DATA, read at `setLook`. Safe at section boundaries.
4. **`laser_groups`** (13). DATA. A swap needs one `buildLaserGroups(rig.projectors, defs)` call, done between phrases.
5. **`presets`** (4) and **`formations`/`strand_shapes`/`ring_formations` (+ deck)**. DATA, read at compile or land time.
6. **Laser group-shape defaults** (lasers.js:346-397: spread, beams, measure, swing, open_beats, level 0.8). Lift the inline `??` numbers into one `SHAPE_DEFAULTS` table that the switch reads. Byte-identical output, and phrase lines already override them.
7. **`G` (grammar) and `BREATH` (ensemble)**. Already frozen tables whose constructors merge `opts`. A pack passes opts at construction (Grammar needs re-creating to apply live; ensemble can edit `this.o`).
8. **Small one-place constants**: default look fade 2, phrase releaseBeats 1, held-go +4, Lantern Walk 64/×4, fly-out tilt 28 / delay x/40 / 2-beat envelope (keep the 0.85 pop capped at today's value, since it bypasses the FlashGate), the section `lasers.reach` values, demo bpm.

### Leave for later (hard: logic or sequences written as code)
- **Section laser looks** `_look` (lasers.js:486): lattice/ceiling/tunnel/fans are hard-coded sequences. They could be re-expressed as group-shape lines, but only after checking the numbers match exactly.
- **Pad hit engine** (lasers.js:190-226, 449-483): pattern maths, tiers and bank rotation. The deck list is liftable; the tiers and choke sit right next to the safety rules.
- **New laser shapes or strand formation shapes** (`_groups` switch, `formationTarget` switch). Packs can only *name* the existing 12 + 10.
- **Overlay merge, the move in black, wheel paths, the bank cycle search** (programmer.js). Core console logic.
- **Rig structure** (LEVEL thirds, column/depth tolerances, mounts). It is the build, not the show; it needs a full re-expand.

### Never in a pack (SAFETY / GUARD)
- **Flash (SAFETY):** FlashGate minBeats 4; FLASH_MIN_DECAY 0.5; FLASH_LIFT 0.125; PIN_TAU_S 1.2; PALETTE_DIP_BEATS 1; red refusal and red-free wheel path; kick.canDip governor; ensemble `attack()` join rule.
- **Laser (SAFETY):** GATE_FLOOR 0.7; MIN_ONSET 0.25; GATES table; groupGate; fast-hit choke; laser red swap; camera exclusion 2° → 10 %; near-camera fade under 4 m; power share.
- **Physical (GUARD):** MODES real limits, ring_rig, RING_CLEARANCE, motor slews, aimAt ranges.
- **Rule for packs:** a pack may *name* a gate or a flash line. The engine keeps the caps.

**Tests that pin values:** GATE_FLOOR (stage_lasergroups.test.mjs:43,45, stage_lasers.test.mjs:59); MODES.real (stage_kinetics.test.mjs:20); the windowsFor relation to G (stage_grammar.test.mjs:43). 16 stage tests load `source-v1.json` directly, so pack data must not change the file's defaults.

---

## Census lane: camera-page-persistence (verbatim)

## Camera, page and persistence census (stage-v4, read only)

I edited nothing, ran no git commands, started no servers and opened no browser. Paths below are relative to `E:/AI-Setup/.claude/worktrees/stage-v4/arsenal/web/stage/` unless stated.

**Four facts that shape the pack design:**
- **The set is already a whole-show pack.** `stage.js:148` fetches `sets/${SET}.json` once at boot (`fetch`, not `import`). `?set=` picks it (default `source-v1`; regex `^[a-z0-9][a-z0-9-]{0,40}$`, line 108).
  - All camera shots (58), sequences (8), formation views (11), `safe`, pads, faders and section-to-camera links already live in that JSON.
  - So the cheapest "snapshot of current settings" is a copy of `source-v1.json` plus `setups.json` and `../palettes.json`, at the tag.
- **There is already an overlay door.** `window.__extraShots` is merged by `stills.js:53` (`withExtraShots`), which checks each shot and adds or replaces it. `stage_stills.mjs:295` injects it before boot.
  - A camera pack can reuse this exact pattern: overlay the set's data, never replace it.
- **Automation does not see what Daniel sees.** When `navigator.webdriver` is true (every lane), the page uses the classic look, solid cubes and setups off (`stage.js:190,193,345`).
  - Daniel's page defaults to HDR Night (or his last L choice from localStorage), HAL cubes, and setups rotating from `ice-spine`.
  - A "nothing changed" proof has to run both ways: the automation defaults, and `?look=hdr&cubes=hal&setups=rotate` (or his URL).
- **The piano store keeps no history.** In `pianolooks.py`, `rev` is a lock against two windows saving at once (a stale rev gets a 409), not a version history. Each save replaces the whole list, so the old version is gone.
  - Its settings are flat (string, number or true/false only), so shots and sequences (arrays and objects) cannot be stored in it as it is.
  - For "revert", stage packs need numbered files or a history list, not just `rev`.

Key: **D** = already data, **C** = code. Lift = how hard to move into a JSON pack: E = easy, M = medium, H = hard. Read = when it is read: **load** = once at boot, **frame** = every frame, **press** = on each key or pad press.

### camera.js (the shots and the director)
| file:line | name | what it does on stage | value | D/C | lift | read by | read |
|---|---|---|---|---|---|---|---|
| sets/source-v1.json `cameras.shots` | shot library | every camera position, path, orbit and strand shot | 58 shots (21 static, 27 path, 8 orbit, 2 strand); 1 held (RING_THREAD) | D | E (already JSON) | Director (camera.js:549 `prepareShot`), distance.js `shotFrame`, stills.js | load (arc tables and validity worked out in the constructor, about 0.25 s) |
| sets `cameras.sequences` | section camera sequences | which shots each section cuts through, and for how many bars | 8 sequences: intro 2, build 1, drop 9, break 5, groove 16, showcase 4, build-dive 2, drop-v2 8 | D | E | Director.start (camera.js:603), from stage.js:246,447,462 | load; a sequence starts at each section change |
| sets `cameras.formation_views` | landing grammar lists | when a formation lands: one glide shot, then a cut to a hero shot | 11 entries `{glide[], hero[], hero_bars}` | D | E | Director (camera.js:558), landing deal at ~693-704 | load; turned through live |
| sets `cameras.safe` | safe wide | fallback when a shot would hit the rig | "FOH_WIDE" | D | E | camera.js:570 | load |
| sets `show.sections.*.camera` / `.phrase.camera` | section to sequence | which sequence each section plays | 5 sections | D | E | stage.js:447,451,462 | at each section change |
| camera.js:46 | MIN_SHOT_BEATS | no shot shorter than 2 beats | 2 | C const | E, but keep it fixed (cut grammar) | camera.js:554,613,821,840; distance.js:80 has its own copy | frame |
| camera.js:47-48 | CLEARANCE_M / GUARD_M | camera never within 1.5 m of the rig; cut away below 1.0 m | 1.5 / 1.0 | C const | E, but keep out of packs (collision rule, tests pin it) | camera.js, distance.js:61 | frame |
| camera.js:49 | DRONE | speed limit of the virtual drone; caps how far FAR can stretch a fast shot | {vmax 15, amax 5} | C const | E | distance.js:189 | load (worked out per shot) |
| camera.js:50 | NOMINAL_BPM | tempo used to turn beats into seconds at load | 150 | C const | E | camera.js:413, distance.js:177 | load |
| camera.js:59-64 | EASES | movement curve names a shot can choose | minjerk, linear, arrive_fast (u^2.2), snap (from 0.75) | C (a table of functions) | H (functions); the names are already data in each shot's `ease` | baseEase:65 | load |
| camera.js:288-295 | handheld wander | gentle camera shake on handheld shots | yaw/pitch 0.6°, roll 0.3°, fixed sine rates | C literals | E (one place) | shotPose | frame |
| camera.js:303-310 | isJumpCut | what counts as a jump cut | under 30° and under 1.5x lens change; "same pose" under 0.25 m and 0.5° | C | E | tests and receipts | when called |
| camera.js:334 | RUNG_BOXES | the rung's collision boxes | 6 boxes | C table | leave (geometry; must match render.js) | clearance functions | frame |
| camera.js:509 | UNDER_LIMITS | how fast an under-ride shot follows the rungs | {6, 4, 16, 5} | C const | E | underFollower | frame |
| camera.js:543 | SAFE_SHOTS | fallback shots after `cameras.safe` | 4 ids | C array | E (the constructor already takes `opts.safe`) | Director constructor | load |
| camera.js:544 | DEFAULT_GLIDES | glide shots used when no list is given | 4 ids | C array | E: `opts.glides` exists but stage.js:240 never passes it | Director constructor | load |
| camera.js:545 | LINE_LIMITS | how smoothly the camera's idea of the strand line follows it | {3, 2, 8, 4} | C const | E | Director followers | frame |
| camera.js:~696/701/703 | landing glide window | glide starts at most 2x its own bars before landing; hero gets `hero_bars` (default 8) | 2x, 8 | C | H (grammar logic) | Director | at each landing |
| camera.js:~821 / ~840 | swap / guard cut lines | a shot swap lands on a 4-beat line; the guard's emergency cut on a 2-beat line | 4 / 2 | C | H | Director.update | frame |

### distance.js (CLOSE / MEDIUM / FAR and comfort)
| file:line | name | what it does on stage | value | D/C | lift | read by | read |
|---|---|---|---|---|---|---|---|
| :64-65 | STOPS / STOP_ORDER | the CLOSE / MEDIUM / FAR settings | 0 / 0.5 / 1 | C frozen table | M (tests import them by name) | distance.js, stage.js through camDist | frame |
| :66-67 | WIDTH / LN_RANGE | how much of the stage fits across the frame at CLOSE and at FAR | 14 m / 80 m | C | M (`widthOf` and `vOfWidth` read them; tests pin 14 and 80) | distance.js; stage_verify distance phase | frame |
| :68 | LOG_RATE_MAX | comfort: fastest the picture may grow or shrink | 4.5 ln a second | C const | M (ES const: would need a config object; tests and verify use the name) | :101, :394, :521-523 | frame |
| :75 | LOG_ACCEL_MAX | comfort: fastest that change may speed up or slow down | 25 ln/s² | C const | M (same as above) | :520-528, :617 | frame |
| :69-72 | MIN_MOVE_BEATS / HANDBACK_BEATS / SOFT_M / SUBJECT_MIN_M | a move lands at least ½ beat after the press; 2-beat blend back to the director; aim for 2.5 m clearance; never nearer than 3 m to the subject | 0.5 / 2 / 2.5 / 3 | C | E–M | distance.js | frame |
| :73 | K_MIN / K_MAX | how far CLOSE/FAR may scale a shot's own size | 0.12 / 4; each shot may override with `distance:{k_min,k_max}` or `distance:false` (no shot in v1 does) | C, with a data override per shot | E | shotFrame:191 | load (each shot worked out once) |
| :74, :76-78, :84 | TAKEOVER_EPS, LOOKAHEAD_S, SETTLE_S, GRID_MARGIN_M, KNEE | how close the fader must come to take over; how far ahead the room is read; settle time; 1 m from the rigging grid; smoothing near limits | 0.03, [0.15, 0.3, 0.45], 0.25, 1, 0.06 | C | E | distance.js | frame |
| :98 | KEY_STOPS | keys for the stops | Q close, W medium, E far | C table | E | stage.js:883 | press |
| :394 | fader follow | how quickly the F8 fader moves the distance | omega 12, speed cap LOG_RATE_MAX/LN_RANGE | C literal | E | camDist.fader | frame |
| :197, :204-207 | room limits | rigging grid height, floor margins, crowd and roof heights | from `venue` (grid_y 33, roof_y−2, crowd_y−0.1) | D (venue JSON) plus C defaults | M | makeRoom | load |

### stage.js: URL parameters (all read once at load from `QS`, line 100)
| line | param | what it does | default |
|---|---|---|---|
| 101 | `?demo=1` | built-in demo show, no engine | off |
| 102-107 | `?engine=off` or `http(s)://…` | where the beat engine is | demo: none; else http://127.0.0.1:8794 |
| 108 | `?set=` | which sets/*.json file loads | source-v1 |
| 112 | `?theme=`, `?phrase=`, `?ring=` | start on this set theme, phrase for pad 3, ring formation | first of each |
| 113 | `?palette=` (falls back to `?theme=`) | start palette | the show's palette |
| 114 | `?strand=` | replace the sections' strand formations with this shape | none |
| 117-118 | `?setup=`, `?setups=hold\|off\|rotate` | start on this setup / the rotation mode (rules at line 345) | rotate for a viewer; off for automation |
| 120 | `?grammar=0` | turn chord phrasing off | on |
| 121 | `?quality=high\|receipt\|low` | render quality | high |
| 122 | `?w=`, `?h=` | fixed render size | from the window × DPR, DPR capped at 2 (line 129) |
| 128 | `?bloommix=` | glow strength, for A/B tests (safety-adjacent: changes brightness before the limiter) | 0.05 |
| 189 | `?look=hdr\|punch\|velvet\|classic` | the finish look | localStorage, then hdr; classic for automation |
| 193 | `?cubes=hal\|solid` | cube style | HAL for a viewer; solid for automation |
| 194 | `?cubetumble=0..1` | cube tumble | `HAL.tumble` |
| 198 | `?cubeglow=hex[,hex]`, `?cubecore=` | override cube colours | none |
| 406 (stills.js:67) | `?shot=ID`, `?shot_u=0..1` | force a camera shot; hold it still at u | none |
| 779 | `?hud=0` | hide the HUD | shown |
| lib/touchbar.js:107 | `?pads=0\|1` | phone pad bar off / forced on | shows on touch screens |
| lib/flash-consent.js:17-18,66 | `?flash=on\|off\|ask` **SAFETY** | flash protection decided by the URL; nothing stored | the first-visit warning screen |
| (lanes only) | `vt=1` | the page never reads it; the virtual clock is injected by the harness | — |

### stage.js: storage, keys, pads, faders, HUD
| file:line | name | what it does | value | D/C | lift | read |
|---|---|---|---|---|---|---|
| stage.js:188 | localStorage `arsenal.stage.look` | remembers the last look chosen with L | look id | — | (already per viewer) | load; written on L |
| lib/flash-consent.js:28 | localStorage `arsenal.flashProtection` **SAFETY** | remembers the flash protection choice | "on"/"off" | — | never in a pack | load |
| lib/touchbar.js:79-83 | localStorage, one key per page | whether the phone bar is collapsed | — | — | — | load |
| stage.js:855 | KEYPAD | number keys to pads | Digit1..0 → pads 1..10 | C | E | press |
| stage.js:883-896 | other keys | Q/W/E distance (Shift = cut on the beat), P/Shift+P palette, O/Shift+O setup, H HUD, U cube style, L look, F fullscreen, C next shot, Esc back to auto | — | C | M | press |
| sets `show.pads` | pad map | what each pad number does | 14 entries (1 kick-white, 2 lasers, 3 phrase-go, 4 phrase-next, 5 kick-colour, 6 flyout, 7 phrase-stop, 8 morph, 9 hero, 10 drop, 11/12 palette, 13/14 setup); also accepts `distance-close/medium/far/auto` (line 525) | D | E | **press** (stage.js:504 reads `padMap` each press, so it could be swapped live) |
| sets `show.faders` + stage.js:401 | fader map | which MIDI CC drives which fader | cc105 strand, cc108 lasers, cc109 haze, cc110 speed, cc113 grand; cc112 = distance added in code | D, with one C default | E | load |
| stage.js:398 + sets `show.fader_defaults` | fader starting values | where the faders start | strand 1, lasers 1, haze 0.85, speed 0.5, grand 1 | D, with a C fallback | E | load; then live values in the `faders` object |
| stage.js:342 + setups.json + `show.setups` | setup rotation | how setups rotate and fade | rotate_bars 16, min_bars 8, fade_beats 4, first ice-spine | D (3 layers merged) | E | load |
| stage.js:208 | demo tempo | demo BPM | `show.demo.bpm` 150 | D | E | load |
| stage.js:220-221 | haze settings | haze timing, pre-haze, wind, noise | from `rig.atmos` (defaults 1.5, 0.12, [0.25, 0, −0.1], 0.6) | D, with C defaults | E | load |
| stage.js:403 | starting energy | energy level before the engine sends one | 0.6 | C | E | live (the engine updates it at 621) |
| stage.js:~763-850 | HUD | text only, shows state; tunes nothing; updates every 100 ms | — | C | — | frame |
| index.html:43 | HUD key legend | key help text written into the HTML (would drift if a pack remaps keys) | text | C | E | static |
| stage.css:4-16 | HUD colours and fonts | look of the HUD panel only | 10 tokens | D (CSS variables) | n/a | static |

### stage.js / render.js: flash safety (packs must never carry or loosen these)
| file:line | item |
|---|---|
| stage.js:274, 749, 852, 991 | **SAFETY** `FrameLimiter` is built once, judges every drawn frame when protection is on, starts fresh when protection is turned back on, and `resetLimiter` reaches it |
| stage.js:681-682 | **SAFETY** kick governor: how much room the limiter has left (`LIMIT.N_MAX` minus its counters) |
| stage.js:144, ~850, 994-995 | **SAFETY** flash consent: `flashProtection`, the HUD checkbox, `setFlashProtection` (for tests, not remembered) |
| stage.js:931 | **SAFETY** `programmer.flashGate` grants and refusals (shown in status only) |
| camera.js:18-20 (via phrases.js cameraPlan) | **SAFETY-adjacent** a step that opens with a flash cuts one beat early, so a cut never lands on the flash frame |
| render.js:857-880 | **SAFETY** meter, then limiter, then apply. This runs after the finish pass, so looks, bloom and EV change what the limiter has to judge but cannot get around it |

### render.js / shaders.js (the finish)
| file:line | name | what it does on stage | value | D/C | lift | read by | read |
|---|---|---|---|---|---|---|---|
| render.js:62-74 | LOOKS | the finish presets: saturation, vignette, hue-keep, black floor, vibrance, contrast, glow, haze glow, fill light, highlight curve | 4 looks × 11 fields (classic, hdr, punch, velvet) | D (plain frozen table) | E | render.js:783 (haze glow and fill), 850-855 (finish); stage.js L key | **frame** (`this.look` is looked up every frame, so it can switch live) |
| render.js:75 | LOOK_ORDER | order L cycles through | hdr, punch, velvet, classic | D | E | stage.js:888 | press |
| render.js:52-56 | QUALITY | anti-aliasing, beam resolution and samples, glow levels | 3 tiers × 5 fields | D table | M (render targets and shader programs are built in the constructor) | StageRenderer constructor:169 | load only |
| render.js:172 | features | which layers draw | 9 switches, all on | D | E | render (also `api.features`) | frame |
| render.js:184 | cubes.tumble | cube tumble | `HAL.tumble` (cubes.js) | C | E | render | frame |
| render.js:784-788 | haze glow and fill constants | strength of the haze's room glow and the fill light | 0.5e-6, 0.0006, 0.6, 0.02; fill 0.004/0.006 + amb×0.01 | C literals | M | render | frame |
| render.js:848-849 | glow mix, EV | final glow strength; exposure | `fs.bloomMix`/6 × look.bloom; EV = shot `ev` + fs.ev | D (per-shot `ev` is in the set JSON) | E | render | frame |
| render.js:43, 50 | UNIT_NITS, LUM_PER_WATT | light units | 30; [644, 839, 331] | C | leave (physics) | — | — |
| shaders.js:61-62 | CROWD_CULL_NEAR_M / CROWD_FREEZE_M | hide crowd figures near the lens; freeze far ones | 4 / 10 m (each shot may set `crowd_cull`) | C | E | render.js:241, 568 | frame |
| shaders.js:23 | MAX_SPOTS | most spotlights drawn | 32 | C (baked into the shader) | leave | render | compile |
| shaders.js:632-718 | finish shader formulas | the curves behind the looks (black floor ×0.5/×1.6, core white ×0.6/×3.0, dither) | GLSL | C | H (leave) | — | compile |
| shaders.js:45 | HAZE_CAP (atmos.js) | densest haze allowed | 0.26 per metre | C | leave (physical cap) | — | compile |

### stills.js
| line | name | what it does | D/C | read |
|---|---|---|---|---|
| 15 | SHOT_KINDS | allowed shot kinds | C | load |
| 24-50 | shotProblems | the checker a pack shot must pass (id 1-48 chars; fields each kind needs; hfov between 5 and 150; finite pose at u 0, .25, .5, .75, 1) | C | load |
| 53-64 | withExtraShots | lays extra shots over the set's: adds new ids, replaces existing ones, leaves out bad ones and reports why | C | load |

### How the tests and lanes load modules and what they compare
- **tests/stage_*.test.mjs** (`node --test`, 24 files, about 380 tests). They import the ES modules directly and read set JSON with `readFileSync` (camera tests: source-v0 and v1; distance and stills: v1).
  - They compare numbers with tolerances, and some exact cut lists, e.g. `stage_camera.test.mjs:304` (the first cut is FOH_WIDE standing in for STRAND_FLYTHROUGH) and `:344-345` (glide at 32 = PROFILE_GRAPH, hero at 96 = REAR_TELE_ZIGGURAT).
  - They import constants by name (`LOG_RATE_MAX`, `LOG_ACCEL_MAX`, `WIDTH`, `STOPS`, `MIN_SHOT_BEATS`, `CLEARANCE_M`…), so these names must stay exported even once a pack supplies the values.
- **arsenal/lanes/stage_verify.mjs** runs headless Chrome on SwiftShader (on the GPU only with `--gpu`).
  - It serves `arsenal/web` on ports 8900-8999 and injects a virtual clock (`addScriptToEvaluateOnNewDocument`), so runs repeat exactly.
  - It opens `index.html?w=&h=&hud=0&quality=receipt&set=…[&demo=1][&setup=…]` (lines 305, 424, 918…).
  - It compares numbers through `check()`: cut lines, landings, clearance on every frame, flash counts, limiter interventions = 0, FlashGate grants, and distance size ratios (CLOSE at least 3x FAR).
  - PNGs are for the eye only; there is no pixel golden-image comparison. It writes `state/arsenal/receipts/stage-<stamp>/receipt.json`.
  - Page doors it uses: `__stage.state()`, `setShot`, `playShot`, `land`, `distance(…, {now})`, `skipRender`, `identityProbe`.
- **arsenal/lanes/stage_stills.mjs** renders on the real GPU under the GPU lock, on the virtual clock: logic runs up to each bar, then `setShot` and a screenshot.
  - It writes PNGs, a contact sheet and `stills.json` (each still's camera pose and facts). It has no before/after diff.
  - With `--facts-only` it needs no browser: it imports camera.js and stills.js and prints clearances.
- **Proving a pack changes nothing, cheapest first:**
  1. All `node --test tests/stage_*.test.mjs` pass unchanged.
  2. A new pure-Node equivalence test: a Director and CameraDistance built from today's values versus from the default pack, driven through the demo plan for several hundred bars. Compare `director.cuts`, `director.landings` and `camDist.moves` with exact deep-equal.
  3. stage_verify logic phases (clock, camera, phrase) before and after: diff `__stage.state()` cuts, lands, phraseSteps, flashGate and limiter stats.
  4. stage_stills at the same bars, shots, look and setup before and after, then a pixel diff. This step is new and needs the GPU lock.
  - Run 3 and 4 in both modes: automation defaults, and Daniel's (`look=hdr&cubes=hal&setups=rotate`).

### pianolooks.py (`E:/AI-Setup/arsenal/pianolooks.py`), the precedent
- **API and routes:** `arsenal.piano.looks/v1`. `GET` and `PUT /api/piano/looks`, routed by `arsenal/serve.py`. File: `state/arsenal/looks/presets.json` (git-ignored).
- **Versioning (lines 193-201):** a whole-document `rev` counter. A `PUT {rev, presets}` replaces the whole list and returns `rev+1`. A stale rev gets a 409 with the current copy. There is no history of earlier versions.
- **Limits (36-40):** body at most 256 KB, at most 100 presets, names 1-60 characters, at most 64 settings per preset, strings at most 200 characters.
  - Preset ids `[A-Za-z0-9_-]{1,64}`; setting names `[A-Za-z][A-Za-z0-9_]{0,39}`.
  - Setting values: string, finite number or true/false only. No arrays or objects.
  - Unknown fields are refused; NaN and Infinity are refused (`parse_constant`).
- **Atomic write (204-219):** writes a temp file `.<name>.<pid>.<tid>.tmp` in the same folder, then `fsync`, then `os.replace`; the temp file is removed on failure. One thread lock covers read, rev check and write.
  - An unreadable file is never overwritten; it answers 500 and leaves the file as it is (188-190).
- **Access (59-84):** answers only when the Host header is loopback on the server's own port and any Origin is that same http origin. A PUT must be `application/json` (else 415).
- **Starter looks** are built into the page and never stored.
- **Gaps for the stage:**
  - It needs nested data (shots, sequences), so it needs its own schema with nested types.
  - "Revert" needs a history: keep N earlier files (`packs/<id>/rev-<n>.json`) or a `history` list.
  - The stage is served from a worktree on :8796, and I did not check whether that server routes any `/api`.
  - A pack checker must refuse any safety key.

### Best candidates for pack v1
1. **The camera block** (`cameras.shots`, `sequences`, `formation_views`, `safe`, plus `show.sections.*.camera`). Already JSON, already overlay-able through the `withExtraShots` pattern, and `shotProblems` is a ready checker. Read at load, so a live switch means building a new Director at a section line (about 0.25 s of validity work).
2. **LOOKS** (render.js:62). A plain table read every frame, so it can switch live. It sits ahead of the limiter, which still judges every frame.
3. **Pad map** (`show.pads`). JSON, read on each press, so it can switch live. The pack can name actions; it cannot change what a kick or the flash gate does.
4. **Fader map and fader starting values** (`show.faders`, `fader_defaults`). JSON, read at load.
5. **Setup rotation settings** (setups.json and `show.setups`: rotate_bars, min_bars, fade_beats, first). JSON, read at load.
6. **Viewer settings** that are URL parameters today (look, cubes, tumble, cubeglow/cubecore, palette, setup, setups mode, bloommix, grammar). Easy: a pack becomes a URL, or a JSON file applied at boot.
7. **Director fallback lists** `SAFE_SHOTS` and `DEFAULT_GLIDES` (camera.js:543-544). The constructor already accepts `opts.safe` and `opts.glides`; stage.js just needs to pass `rig.cameras.glides`.
8. **Distance comfort** (STOPS, WIDTH, LOG_RATE_MAX, LOG_ACCEL_MAX, MIN_MOVE_BEATS, HANDBACK_BEATS, SETTLE_S, fader omega 12). Medium: these are ES constants read every frame and imported by name in tests, so they need a config object while keeping the exported names as defaults. I suggest a pack may only make LOG_RATE_MAX and LOG_ACCEL_MAX gentler (lower), never faster: they are motion comfort, not flash safety, but the same idea.
9. **Handheld wander amplitudes** (camera.js:288-295). Easy, one place.

### Leave for later
- **The director's grammar:** landing glide window, 4-beat swap and 2-beat guard lines, dealing rotation (camera.js ~690-840). Sequence logic written as code.
- **Easing functions** (EASES), the strand-frame maths, and the distance room walk (`_walk`, `_seek`).
- **CLEARANCE_M and GUARD_M.** The collision rule, pinned by tests: keep them out of packs, like safety.
- **QUALITY** (sizes render targets at construction), **RUNG_BOXES and geometry**, the finish shader formulas, **MAX_SPOTS** and **HAZE_CAP**.
- **Anything marked SAFETY:** the limiter, the governor's `LIMIT.N_MAX`, `?flash=` and `arsenal.flashProtection`, FlashGate, and the pre-cut before a flash step. A pack checker must refuse these keys outright.
