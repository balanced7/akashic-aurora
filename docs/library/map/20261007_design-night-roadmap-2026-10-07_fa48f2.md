---
akashic_id: art_20261007_design-night-roadmap-2026-10-07_fa48f2
akashic_sha: a41373663616
schema_version: 1
status: current
type: map
arc: media-suite
date: 2026-10-07
title: design-night-roadmap-2026-10-07
gist: "Tonight's designs organized: tracks H/NP/F/P/C/O, five waves, H1 Rescan hint first with pre-registered acceptance"
visibility: fleet
body_type: markdown
seats: [claude]
category: [ergonomics, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20261007_presentation-grammar-screens-scenes_236d39
    rel: discusses
created: "2026-10-07T23:47:18"
updated: "2026-10-07T23:47:18"
---
<!-- GENERATED PROJECTION of art_20261007_design-night-roadmap-2026-10-07_fa48f2 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# design-night-roadmap-2026-10-07

# Roadmap: the design night of 2026-10-07, organized

Status: map, organized by Vandor at Daniel's request. It is living: update it as slices land. Arc: media-suite, plus an ergonomics track.

Daniel (verbatim): "order is up to you , I gave us the design specs and things to make into plans and slices, lets organize and structure them and then you pick what you want to build first ^__^"

## Sources

- art_20261007_second-press-gentle-hints_db25d1: gentle hints and the one-world UI. It also carries the house round:
  - Heimdall: the authored/derived plane split, a mode schema with a bounds legend, and the floor as a wall plus a canary.
  - Navi: the floor as a manifest of loud absence, the self-adjudicated-silence blind spot, and a `confessed` edge class.
  - Rill: the cursor divergence behind the unread count.
- art_20261007_now-playing-multilayer-live-hook_1328e1: the Now Playing stage, slices S0–S15, and the content-system frame.
- art_20261007_fact-sourcing-provenance-ladder_84c3e2: the draft sourcing rules.
- art_20261007_presentation-grammar-screens-scenes_236d39: the claim passport, the stage translation, screens and scenes.
- docs/WISHLIST.md (2026-10-07): the boot gate and a doc revise verb.

## Tracks

### H — Gentle hints and the house's own surfaces (ergonomics)

- **H1 Piano Rescan hint** ← FIRST
  - An escalating hint that names the layer and leaves on success.
  - The status footer stops hiding a missing keyboard.
  - A read-only /api/midi/ports endpoint.
  - It births P1 (the hint primitive) and the first H7 signal chain.
- **H1b "Start the MIDI service" action.** POST and admin-aware. Build it only if a stopped service is ever actually seen.
- **H2 mem_watch voice.** A floor entry for the kernel pool and commit, with a max-silence budget (Navi) and a positive canary (Heimdall), reaching Daniel on a real surface.
- **H3 Repeated whispers change or go quiet.** The unread line names directed asks and their age. It rides on Rill's cursor fix (W173).
- **H4 Recall second-press mode.** A retry after a failure gets the louder, more specific lesson; the credit join is the detector.
- **H5 Did-you-mean doors.** On a CLI typo, suggest the nearest flag or verb.
- **H6 Receipts on success.** Every write door prints what it wrote.
- **H7 Signal-chain view.** Generalized from H1's chain; the fleet chain comes next.
- **H8 Boot gate.** The first repo tool call made without a boot bounces once.
- **H9 One-world UI core.**
  - The world model, session-keyed view state, modes, the floor and the bounds legend.
  - It gets its own reconciled design round. The house takes are in, and Heimdall's mode-schema contract is the opening move.
- **H10 Fleet-ops verbs:** seat pulse / take / free / restart. Always drain; never hand-spawn.
- **H11 Doc revise verb** (wish).

### NP — Now Playing stage (S0–S15, see 1328e1)

- **Phase A, the first show:** S0 Spotify spike [needs Daniel's OAuth click], S1, S2, S3, plus S9.
- **Phase B:** S4 ears, S5 color on three timescales.
- **Phase C:** S6 facts pipeline, S7 dossiers, S8 first dossier + reveal [needs artist #1 from Daniel].
- **Phase D:** S9–S12, the specialist layers.
- **Phase E:** S13–S15, the co-performer.

### F — Facts and provenance

- **F1** Ratify the sourcing rules [Daniel].
- **F2** Fact store = the claim passport. It is bitemporal; verify Heimdall's lifecycle.py report first.
- **F3** Retrieval adapters (they feed S6).
- **F4** Corrections ledger.

### P — Presentation grammar

- **P1 Gentle-hint / annotation primitive.** Born in H1; reused by the S2 cards and the F whisper-lines.
- **P2 Screens.**
  - A texture-source uniform (preset contract v2).
  - First treatments: LED wall, hologram in steam, archival film.
  - A floating screen.
- **P3 Timeline grammar component:** line styles, forks, journey maps.
- **P4 Luminous callouts on 3D objects.**
- **P5 Scenes:**
  - camera-flight transitions;
  - the forest-of-strings interior;
  - artist rooms;
  - musical spells;
  - hidden-roadmap structures.

### C — Content system

- **C1** Content-strategy round: pillars, series arc, cadence [Daniel + the house].
- **C2** Episode planner (news windows → calendar).
- **C3** Clip library with source and license records.
- **C4** Deep-dive template.
- **C5** Build Log format: each landed slice is an episode.

### O — Loose ends from tonight

- **O1** Reboot [Daniel]. The kernel pool is past the 09-11 outage line, and the reboot also makes Navi's unlimited turn budget live.
- **O2** Fix the auto-category stamps on tonight's atoms (at wrap).
- **O3** Rill's cursor-divergence fix (in flight, his lane).

## Waves

- **Wave 0** (tonight, needs nobody): H1.
- **Wave 1** (one touch from Daniel each): O1 reboot, the S0 click, F1 ratify, artist #1.
- **Wave 2:**
  - the NP first show (S1–S3 + S9), which makes the first Performance video;
  - H2 mem_watch voice;
  - H8 boot gate;
  - the small wins H5 and H6.
- **Wave 3:** S4–S5; P2 screens; F2–F3, leading to S6–S8 (the first dossier + reveal).
- **Wave 4:** S10–S12, P3, and the C1 strategy round; the H9 design round.
- **Wave 5:** S13–S15 co-performer; P5 scenes and hidden-roadmap teasers; H3, H4, H7 and H10.

Ordering logic:
- Prove small things before big ones, and unknowns before polish.
- Reuse what each slice births (H1 → P1 → the S2 cards).
- One Daniel touch per gated step.
- Every landed slice is a Build Log episode.

## H1 acceptance (pre-registered before any code)

- **A1 — a pure decide() covers every case:**
  - first press → no hint;
  - a scan that finds no inputs → hint at once;
  - a second press within 90 s with nothing bound → a hint naming the most likely layer:
    - Windows sees a keyboard but the browser doesn't → "the browser's list is stale", with restart guidance for that browser;
    - Windows sees none → check power and cable;
    - the MIDI service is stopped → say so;
    - endpoint unavailable → browser-only wording that does not overclaim;
    - MIDI permission denied → the site-settings path;
  - third press → the signal chain, with the dim node shown;
  - bound but silent after a rescan → a sound check ("play any key"), then "Heard you";
  - REC active → deferred, never shown, and re-offered after REC if still relevant;
  - an input binds → a success message, then auto-dismiss;
  - a hint never repeats the same level for the same cause.
- **A2 — tests:** `node --test tests/piano_midi_hint.test.mjs` is green and includes a calibration test that fails if decide() always returns null.
- **A3 — the endpoint:**
  - /api/midi/ports returns inputs, outputs and the service state, and on this host lists "KeyLab 88 mk3 MIDI";
  - it is read-only and fails soft with JSON;
  - pytest is green.
- **A4 — placement:**
  - the hint anchors beside Rescan wherever the workbench put it, in the house type;
  - it never covers the stage and is never in the REC canvas;
  - the footer names a missing remembered keyboard instead of "Computer keyboard ready".
- **A5 — no regression:** the existing piano suites stay green, and the page boots with no new console errors.
- **A6 — going live:**
  - the page side is live on the next reload;
  - the endpoint goes live after a serve.py restart at a moment Daniel chooses, and until then the page degrades gracefully.
