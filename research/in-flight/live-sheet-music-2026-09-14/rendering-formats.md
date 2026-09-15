# Lane: rendering and formats for a live score

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Research and design only. No arsenal code edited (a jam build holds `arsenal/web/piano.js`). Nothing installed, downloaded or vendored, no servers, no browsers, no logins. Registry facts were read with WebFetch and read-only `npm view`. |
| Question (Daniel, verbatim) | "what if we keep a rough estimate of bpm and make it possible to save the notes i am playing into something that can render into sheet music with correct notation in real time, I wonder if we can make that happen!" |
| This lane | How the page **draws** a live score and how a take is **exported**: renderer choice (VexFlow, Verovio, OpenSheetMusicDisplay, abcjs, our own canvas renderer, LilyPond or MuseScore offline), file formats (MusicXML, MIDI, MEI, ABC, PDF/SVG), the path to MuseScore and Dorico, and a score in the TikTok frame. Turning rubato into bars (beat tracking, quantizing, hand split, spelling) belongs to the sibling lanes; this lane states what it needs from them (section 5.1). |
| Grounded in | `arsenal/web/piano.js` (overlay: `FONT`, `SMUFL`, `BRAVURA_URL`, `loadFonts`, `LAYOUT`, `makeLayer`, `drawStaff`, the `staffKey` redraw gate), `arsenal/web/piano.html` (import map, three.js r186 from jsDelivr), `arsenal/web/piano/recorder.js` (WebCodecs H.264 at 60 fps, MediaRecorder fallback, canvas-only capture), `arsenal/web/piano/replay.js` (passage replay via `/api/piano/replay`), `arsenal/performance.py` (event kinds `on/off/pedal/chord/sound_end`, `t_ms`, `note`, `vel`), and a read-only density pass over the private practice log (S1..S12, counts only). |

---

## 1. Short answer

1. **Yes, and the page is already halfway there.** `drawStaff` already draws a grand staff on a Canvas2D layer inside
   the WebGL canvas. It uses Bravura clefs, a brace, SMuFL noteheads, stacked accidental columns and ledger lines, and
   the recorder captures it. What a real score adds is time: bars, stems, beams, ties, tuplets, rests, pedal marks and
   a layout engine that spaces them. Hand-writing that layout engine is the expensive part, so do not build it for v1.
2. **v1 live renderer: VexFlow 5.0.0 (MIT), the `core` build, drawing through its Canvas backend into a new overlay
   layer.** Four reasons:
   - **It is canvas-native.** There is no SVG-to-bitmap step and no canvas-taint risk, and REC records the layer
     exactly as it records the staff today.
   - **It is small.** `vexflow-core.js` is 336,625 bytes, and it takes Bravura from the same `@vexflow-fonts/bravura`
     woff2 package the page already loads.
   - **It is programmatic.** Notes are built from our own score model, with no MusicXML or ABC text parsed on every
     update.
   - **It has the piano pieces.** Brace connectors, beams, tuplets, ties, pedal markings and cross-stave voices are all
     there (cross-stave voices since vexflow PR #1434).
3. **Keep our own renderer and give it one new job: a proportional "tape" mode.** Noteheads sit by time on the grand
   staff, with no bar lines and no rhythm claimed. Use it for free-time passages where the tempo estimate is not
   trustworthy. Showing rhythm that has not been heard is the notation version of a false autobiography.
4. **Verovio 6.3.0 (LGPL-3.0-or-later, about 7.3 MB) is the v2 "clean page" view and the export checker.** It renders
   our MusicXML as an engraved page and gives MEI, MIDI and a timemap for free. It is too heavy to be the live renderer,
   and it only produces SVG.
   - **OpenSheetMusicDisplay:** not recommended for live. Every update is a full MusicXML re-parse, and the bundled
     VexFlow is a 1.2.93-based fork.
   - **abcjs:** not recommended either. It renders SVG only, and ABC is a weak fit for dense two-hand pedalled piano.
5. **Export: write MusicXML 4.0 and MIDI ourselves, with no libraries.**
   - **`take.musicxml`:** one Piano part, two staves, `<staff>` per note (cross-staff), `<pedal>`, `<tuplet>`, ties,
     key from the Nashville tracker, and a "c. 80" metronome mark.
   - **`performance.mid`:** raw milliseconds, CC64 pedal, rubato kept.
   - **`quantized.mid`:** snapped to the grid.
   - Both MuseScore Studio and Dorico 6 import MusicXML and MIDI. PDF comes from MuseScore's command line or LilyPond
     2.26 offline, and only if Daniel approves an install.
6. **Video, two paths.**
   - **(a) A live score ribbon in REC.** Closed bars become small texture tiles that slide left in the WebGL overlay, so
     scrolling costs a uniform per frame, never a redraw.
   - **(b) A replay re-render.** Re-record a take with the corrected, retro-quantized score, so the TikTok shows
     settled notation, not live guesses.
7. **Decisions for Daniel** are in section 8. The first is whether to load VexFlow 5.0.0 core from jsDelivr, pinned
   and HEAD-checked like three.js, or to vendor it.

---

## 2. The constraint that picks the renderer

- **The recorder only sees the canvas.** `piano.js` draws the chord label, the Nashville row and the staff as Canvas2D
  layers, and `makeLayer` uploads each one as a `THREE.CanvasTexture` on an overlay mesh. The overlay is composited
  after bloom "so REC records them". `recorder.js` encodes the canvas itself (WebCodecs `VideoEncoder`, or
  `canvas.captureStream(0)` as the fallback).
  - **So whatever draws the score must end as pixels on a canvas that WebGL can upload.** A DOM or SVG score sitting
    beside the canvas would never appear in a TikTok.
- **SVG-only renderers (Verovio, abcjs, OSMD's default) need a rasterize hop:** SVG string, then a Blob or data URI,
  then `Image`, then `drawImage` onto the layer, then a texture upload. The hop is asynchronous (image decode), which
  is acceptable at 2-8 updates per second. It has a trap, though: **a tainted canvas cannot be uploaded to WebGL**, and
  the overlay would fail.
  - Data URIs never taint.
  - Blob-URL SVG with `foreignObject` stopped tainting in Chromium only with the Chrome 131 intent to ship.
  - Any SVG that pulls an external font or image stays unsafe.
  - So an SVG renderer must emit self-contained SVG. Verovio embeds its glyphs as SVG definitions, not web fonts
    (medium confidence; verify in the bench, section 9).
- **Redraw on change only, as the page already does.** `overlay.update` redraws and re-uploads a layer only when its
  key (`staffKey`, `labelKey`) changes, and fades are uniforms. A score layer must keep that discipline:
  - paint when an onset cluster lands or a bar closes (a few Hz), never every frame;
  - cache closed bars as bitmaps.
- **The frame budget is shared with three.js.** At 60 fps there are 16.7 ms per frame, and bloom, trails and sparks
  already spend part of that. Target: a score update's layout plus paint stays under about 8 ms at p95 on the main
  thread. If it cannot, move layout to a Worker (section 5.4).

---

## 3. What the practice log says about the load (S1..S12)

A read-only scratch pass (`scratchpad/sheet/density.py`) over 12 sessions. S8 had 11 notes and is excluded, which
leaves 11. Only rates and fractions were kept. Sessions ran 1.2 to 31.2 minutes.

| Measure | Range over sessions | What it means for rendering |
|---|---|---|
| Note-ons per second | 1.24-6.84 (median session 4.15) | A 4/4 bar at 80 bpm (3 s) carries about 12 notes on a typical session, and far more in bursts. |
| Note-ons in a 3 s window: median / p90 / max | median 0-19; p90 15-43; max 24-67 | The densest bars hold 40-67 noteheads, and layout must stay fast at that size. S11's median of 0 is long silences (free time). |
| Notes per onset column (onsets within 40 ms) | 1.32-2.02 | Mostly single notes and dyads in sequence: **arpeggios**. Beams dominate, and cross-staff beams (bass up into the solo line) will be common. |
| Most keys held at once (on/off only, pedal ignored) | 6-10 | Chord columns of up to about 10 heads across both staves. Needs second-interval head displacement and accidental column stacking. The current `drawStaff` already does both for one chord. |
| Pedal presses per minute | 6.7-22.8 | A pedal change roughly every 2.6-9 s, about one per bar or two at 60-110 bpm. Use **bracket lines with change notches**. "Ped. / *" text at every change would clutter. |
| Share of notes below middle C | 0.29-0.50 | Both staves carry real content, so a fixed middle-C split is a poor hand split. The renderer must accept a per-note staff (cross-staff). |
| Notes above A5 (ledger lines over the treble staff) | 0-20% | The top of the range needs `8va` brackets (VexFlow `TextBracket`, MusicXML `<octave-shift>`), or ledger stacks eat the ribbon's height. |
| Notes below E2 (ledger lines under the bass staff) | 2.5-16% | The same at the bottom: `8vb`, which Daniel's low bass needs. |
| Pitch span | MIDI 21-106 overall | Close to the whole keyboard. |

**A width estimate (unmeasured, low confidence).** The 9:16 staff layer is 860 px wide at staff space `s` = 24. That
leaves about 745 px between the brace and the right edge. A p90 bar has 15-43 onsets, which is roughly 10-30 columns.
At about 1.5 staff spaces per sixteenth-note column (36 px at s = 24), **even one dense bar does not fit at today's
staff size.**
- At s = 14-16, one bar fits and a ribbon can show one or two bars.
- The 16:9 staff layer (640 px wide) is too narrow for metric notation, so the score needs its own band in that layout
  (decision D4).

---

## 4. The options

### 4.0 At a glance

Sizes are jsDelivr file sizes before compression. Dates are npm publish dates (`npm view <pkg> time`).

| | VexFlow | Verovio | OpenSheetMusicDisplay | abcjs | Our canvas renderer | LilyPond / MuseScore (offline) |
|---|---|---|---|---|---|---|
| Version | 5.0.0 (2025-03-05) | 6.3.0 (2026-08-19) | 2.1.2 (2026-08-06) | 6.7.0 (2026-08-07) | `drawStaff` in piano.js | LilyPond 2.26.0 (2026-04-19); MuseScore Studio 4.6 (2025-09-30), 4.7.x current |
| Licence | MIT | LGPL-3.0-or-later | BSD-3-Clause | MIT | ours (repo Apache-2.0) | both GPL-3.0; run as separate programs, no licence effect on the repo |
| Browser payload | core 336,625 B; with Bravura bundled 728,171 B; full 1,128,380 B | `verovio-module.mjs` 7,296,807 B (Humdrum build 12,374,836 B) | `opensheetmusicdisplay.min.js` 1,321,869 B | `abcjs-basic-min.js` 511,903 B | 0 new; Bravura woff2 already loaded | desktop install, not in the page |
| Input it wants | JS objects (StaveNote etc.) | MEI, MusicXML, ABC, Humdrum, PAE | MusicXML | ABC text | our note objects | MusicXML (via `musicxml2ly` or MuseScore import) |
| Output surface | **Canvas** and SVG | SVG strings | SVG (VexFlow canvas backend also exists) | SVG | Canvas2D | PDF, SVG, PNG, MIDI, MusicXML (MuseScore) |
| Live update model | We rebuild the open bar or system and redraw. Cheap because it is small, and caching is ours. | Reload the whole document, then render a page. `edit` is experimental. | Reload MusicXML, then render. 2.0 added system-by-system `renderNext` for large scores. | Re-render the whole tune from text | Draw as today | Batch only |
| Piano grand staff | Brace connector, voices per stave, cross-stave voices and beams (PR #1434, merged 2022-10-16), `Tuplet`, `StaveTie`, `PedalMarking` | Full engraving, strongest of the browser options | Good. 2.1.0 added cross-staff slurs; 2.0 nested tuplets | Brace and multi-voice; dense piano and cross-staff are weak (medium confidence) | Chord column only: no stems, beams or time | Best engraving (LilyPond); MuseScore very good |
| Exports it gives us | SVG (via its SVG backend) | **MEI, MIDI, timemap, Humdrum, PAE** (no MusicXML output) | none beyond render (Braille in 2.1.1) | MIDI | none | PDF/SVG/PNG; MuseScore also MusicXML, MIDI, mscz |
| On jsDelivr | yes (`npm/vexflow@5.0.0`) | yes (`npm/verovio@6.3.0`) | yes | yes | n/a | n/a |

### 4.1 VexFlow 5.0.0: recommended for the live ribbon

- **Why it fits:**
  - Canvas and SVG backends ship in the same library, per the getting-started guide.
  - Fonts load as woff2 web fonts (`VexFlow.loadFonts` / `setFonts`) from the `@vexflow-fonts/*` packages. The page
    already loads `@vexflow-fonts/bravura@1.0.2/bravura.woff2` into `document.fonts` for `drawStaff`, so the score and
    the "now" staff share one font face and look like one instrument.
  - Petaluma, a handwritten jazz face, is `@vexflow-fonts/petaluma@1.0.1` on jsDelivr if Daniel wants a lead-sheet look
    for TikTok (D6).
- **Builds:** `build/cjs/vexflow-core.js` (no fonts bundled), `vexflow-bravura.js`, and `vexflow.js`, which bundles
  Bravura, Petaluma and Gonville glyph data. The ESM entries (`build/esm/entry/vexflow-core.js`, 139 B) re-export
  hundreds of source modules. Through the import map, that means many requests on first load.
  - **Two loading choices:** a pinned `<script>` tag for the cjs core (the getting-started guide shows script-tag CDN
    URLs; medium confidence that it defines a global `VexFlow`), or jsDelivr's bundled `/+esm` endpoint.
  - HEAD-check whichever is chosen, as the three.js comment in `piano.html` does.
- **Grand-staff pieces we need, all present:** `Stave` ×2 with a `StaveConnector` brace; `Voice` per hand;
  `Formatter` joined across both staves so columns align; `Beam`, cross-stave via `System` with per-note staves (issue
  #1373 was closed by PR #1434); `Tuplet`; `StaveTie` across bar lines; `PedalMarking` (bracket or mixed); `TextBracket`
  for 8va; `ClefNote` for clef changes; `Accidental`, `Dot`, rests.
- **What VexFlow leaves to us, and the transcription lane must produce anyway:** beaming groups per time signature,
  voice splitting, filling rests so voices sum to the bar, system breaking, and tie splitting at bar lines. VexFlow is
  a drawing and spacing engine, not a notation editor.
- **Performance:** there are no published benchmarks for this workload. A system of 60-170 notes is small next to the
  whole-page scores VexFlow is used for, so an estimate of low single-digit ms per system is plausible but
  **unmeasured**. Section 9, gate G1, measures it before any commitment.
- **Risks:**
  - VexFlow 5.0.0 is the latest stable release: 18 months old, no 2026 release seen. MIT, so a fork is possible if
    needed.
  - The API changed between 4 and 5 (fonts, styling), so tutorials older than 2025 mislead.

### 4.2 Verovio 6.3.0: v2 clean page, checker and converter

- **Strengths:**
  - The most complete engraving in the browser, from the RISM digital team, with active 2025-2026 releases: offsets,
    timemap and MIDI fixes (5.x); ossia staves and repeats in MIDI and timemap (6.0); voltas (6.3).
  - Reads MusicXML, MEI, ABC and Humdrum.
  - Writes SVG, MEI (several flavours), MIDI (`renderToMIDI`, base64), a **timemap** (millisecond and quarter-note
    stamps with note ids on and off), Humdrum and PAE.
  - `breaks: "none"` renders a piece as one continuous system, which is exactly a scroll strip.
  - `getElementsAtTime` gives playback highlighting.
- **Why not live v1:**
  - Payload is 7.3 MB of WASM in a JS module (compressed transfer is smaller; unmeasured).
  - It produces SVG only, so it needs the rasterize hop (section 2).
  - Every update reloads the document. For a growing session that means re-sending a window of the last N bars on each
    change.
  - The `edit` API is marked experimental.
  - LGPL-3.0-or-later is fine for unmodified use from a CDN or a vendored file. It still adds a notice duty and is a
    heavier dependency than MIT.
- **Where it earns its place:**
  1. A **review page** that opens a saved `take.musicxml` as a clean engraved page, with no three.js involved.
  2. An **export checker**. If Verovio loads our MusicXML without warnings and its timemap note count matches the
     take, the writer is sound (gate G4).
  3. **MEI**, if a scholarly or archival target ever matters.
  4. The **timemap** for a synced page-scroll video (section 7, path B).
- It does **not** write MusicXML, so it cannot be the export writer.
- Default music font is Leipzig; Bravura is selectable.

### 4.3 OpenSheetMusicDisplay 2.1.2: not for live

- 2026 was a strong year:
  - 2.0.0 (2026-06-15) roughly doubled render speed with a geometric skyline and added lazy system-by-system
    `renderNext`, tremolos, nested tuplets and cross-staff slurs;
  - 2.1.0 improved cross-staff slurs (left hand to right hand) and enharmonic ties;
  - 2.1.2 reports about 40% median speedup.
- **Why not live:**
  - The only input is MusicXML, so each update is serialize, parse, graphical model, VexFlow draw.
  - It depends on a VexFlow 1.2.93-based fork, not VexFlow 5, so it would put a second, older copy of the engraving
    stack beside ours.
  - 1.32 MB.
- It is a good MusicXML viewer. Verovio covers the same job and adds exports, so OSMD is a fallback only if Verovio's
  licence or size is refused (D2).

### 4.4 abcjs 6.7.0: not for this piano

- **Strengths:** MIT, 512 KB, active (6.5 to 6.7 through 2025-2026), ABC text in, SVG out, MIDI file export since 6.0,
  and piano braces.
- **Why not:**
  - The ABC model suits melody-and-accompaniment tunes. Two-hand lush voicings, dense cross-staff arpeggios and pedal
    brackets push past it.
  - ABC has `!ped!` / `!ped-up!` decorations in the abcMIDI tradition, but I did not confirm that abcjs engraves pedal
    brackets (low confidence).
  - SVG only, so it needs the rasterize hop.
- **A possible later use:** a one-staff **lead-sheet** export of the solo line with chord symbols, where ABC is compact
  and friendly. Not v1.

### 4.5 Our own canvas renderer: keep it, extend it for the tape mode only

- **Already there:** `drawStaff` has Bravura clefs (`U+E050 gClef`, `U+E062 fClef`), a brace (`U+E000 brace`), whole noteheads
  (`U+E0A2 noteheadWhole`), sharp, flat and double glyphs, accidental columns that never collide, second-interval column offsets,
  ledger lines as wide as the columns that need them, the per-note colour glow and the scrim. There is a fallback
  path to Noto Music glyphs.
- **A full metric engraver in-house is not worth it for v1.** It would need spacing, beam slopes, stem anchors,
  collision avoidance, ties and slurs, and tuplet brackets. SMuFL metadata does supply the hard numbers:
  `bravura_metadata.json` gives `engravingDefaults` (stem, beam, staff-line and ledger thickness) and
  `glyphsWithAnchors` (`stemUpSE`, `stemDownNW`), and it is on jsDelivr via `gh/steinbergmedia/bravura@bravura-1.482`.
  Even so, that is months of edge cases VexFlow and Verovio already solved.
- **The one mode it should own: "tape", proportional notation.**
  - Time runs left to right at a fixed px per second, and noteheads land on the grand staff at their onset times,
    spelled by the page's existing speller.
  - Duration is a faint line to `sound_end`, so pedal ring shows. Pedal is a bar along the bottom, drawn from the real
    CC64 values.
  - No stems, no bar lines, no rhythm claimed.
  - This is honest for free time, where the beat estimate is weak. It needs nothing from the quantizer, so it can ship
    first.
  - The metric ribbon (VexFlow) takes over bar by bar only when the tempo lane reports confidence. The switch policy
    belongs to the quantizer lane.
  - It also works as a debugging view: tape and ribbon side by side show exactly what the quantizer did.

### 4.6 Offline engravers: LilyPond 2.26.0 and MuseScore Studio 4.x

- **MuseScore Studio (GPL-3.0):**
  - Command line `MuseScore4.exe -o take.pdf take.musicxml` exports PDF, SVG, PNG, MusicXML (`.musicxml`/`.mxl`),
    MIDI and `.mscz`.
  - `-j job.json` batches several outputs per score.
  - 4.6 and 4.7.x shipped repeated MusicXML import and export fixes.
  - **Not installed:** only Muse Hub was found under `%LOCALAPPDATA%`, and nothing on PATH or in Program Files.
- **LilyPond 2.26.0 (GPL-3.0-or-later, stable 2026-04-19):**
  - The best printed engraving.
  - `musicxml2ly` imports MusicXML; `midi2ly` exists but loses notation intent.
  - **Not installed.**
- **Role:** PDF for printing or sharing, run from arsenal as a separate process after a take is saved. Neither is
  needed for v1: Daniel can open `take.musicxml` in MuseScore or Dorico by hand. Installing either needs his OK (D3).

---

## 5. Recommended v1 design (rendering side)

### 5.1 The score model this lane needs from the transcription lanes

This is renderer-agnostic, so VexFlow, Verovio, the MusicXML writer and the MIDI writer all read one object.

```
Take { tempo: {bpm, confidence, map?}, key: {fifths, mode, since_bar}[], time: {beats, beatType} | "free",
       bars: Bar[] (closed | open), pedal: {startTick, endTick, changes[]}[], octaveShifts[] }
Bar  { index, startMs, endMs, staves: [treble, bass] of Voice[] }
Note { pitch: {step, alter, octave}  // spelled, from the same speller drawStaff uses (the chord-spelling code in piano.js)
       staff: 1|2, voice, onsetTick, durTicks (rational), tieStart/tieStop, tuplet?: {actual, normal, id},
       midi, vel, onMs, offMs, soundEndMs }  // raw times kept for performance.mid and for the tape
```

- **Spelled pitch comes from the page's speller**, never re-derived from MIDI in the renderer. Otherwise the live
  staff and the score could spell the same note differently on screen.
- **Closed bars are immutable in the live view.** Only the open bar may be re-quantized or re-spelled while Daniel
  plays. Corrections to closed bars go to export and replay (section 7), never into live flicker.
- **Ticks are rational divisions of a quarter.** A divisions value of 840 covers 2, 3, 4, 5, 6, 7 and 8 subdivisions.
  MusicXML's `<divisions>` takes the same number.

### 5.2 Three display modes on one layer family

| Mode | Drawn by | When | Claims rhythm? |
|---|---|---|---|
| **Now** (today's staff) | `drawStaff` | always available | no |
| **Tape** (proportional) | our canvas code, a new function beside `drawStaff` | free time, low tempo confidence, and v0 before the quantizer exists | no |
| **Ribbon** (metric) | VexFlow 5 core, Canvas backend | tempo confident; bars closing | yes |

### 5.3 Update cadence and caching

- **Per bar, one texture tile.** Each bar paints into its own small canvas: bar width × grand-staff height at the
  ribbon's staff size, about 300-700 × 260 px at s = 14-16. That canvas becomes its own `CanvasTexture` plane in
  `overlayScene`, built like `makeLayer`.
  - **The open bar** repaints on each onset cluster, throttled to at most 8 Hz, and re-uploads only its own small
    texture.
  - **A closing bar** does one final paint, then never re-uploads.
  - **Scrolling** moves the tile meshes' `position.x` (or one group's) each frame. That is a matrix update, with no
    canvas work and no upload.
  - **Old tiles** are disposed once off-screen, as `disposeLayer` does.
- **Formatting across bars.** VexFlow formats per system. For a ribbon, each bar is formatted on its own with a
  minimum width derived from its column count, and the pixel width is fixed at close time. Nothing already painted
  reflows.
- **Beams and ties across the bar line.** Ties are drawn as two half-ties, one ending at the tile edge and one starting
  in the next tile. Cross-bar beams are rare in engraved piano music and are avoided by the beaming rules.
- **Fades** use the same material-opacity damping as `staffAlpha`, so a bar re-spelling in the open tile crossfades
  over about 120 ms instead of jumping.

### 5.4 If G1 fails: a Worker

VexFlow's Canvas backend takes any 2D context, and an `OffscreenCanvas` in a Worker can hold Bravura via the Worker's
own font set. The main thread would receive an `ImageBitmap` per open-bar paint and upload it. Only do this if gate G1
shows main-thread p95 over about 8 ms. The first choice is simpler: open-bar work is small.

### 5.5 Notation choices the data (section 3) drives

- **Pedal:** bracket line with change notches, from CC64 `down` edges. MusicXML `<pedal type="start|change|stop"
  line="yes">`; VexFlow `PedalMarking`. Half-pedal values stay in `performance.mid` and are not engraved.
- **Octave lines** once a passage stays above A5 or below E2 for more than about a beat, instead of stacking ledger
  lines.
- **Cross-staff notes are first-class.** The hand split is the transcription lane's call. The renderer must draw a bass
  arpeggio rising into the treble as one beamed voice.
- **Key-signature changes only at a bar line**, and only after the Nashville key tracker's hysteresis settles, with
  courtesy naturals. Never mid-bar.
- **Tempo marking:** "♩ = c. 80" plus "rubato" as words. This is Daniel's "rough estimate of bpm", written the way
  scores write rough tempos. MusicXML `<metronome>` with `<per-minute>` text, and `<sound tempo>` for playback.
- **Free time:** in MusicXML the tape passages can export as `<time><senza-misura/></time>` bars with dashed bar lines.
  This is medium confidence on the element and should be checked against the 4.0 reference before writing. MuseScore
  and Dorico import behaviour is untested.

---

## 6. Export path

### 6.1 MusicXML 4.0: the primary hand-off to MuseScore and Dorico

- **Why MusicXML:** it is the one format both import natively. Dorico 6 (released 2025-04-30) has File > Import >
  MusicXML. MuseScore Studio has a handbook page on MusicXML import.
  - **MusicXML 4.0** is the W3C Community Group final report of 2021-06-01. Its pedal element carries
    start/stop/sostenuto/change/continue/discontinue/resume with `line` and `sign` attributes.
  - **4.1** is in progress (Community Group update, 2026-08-11).
  - **MNX** is still being specified (working-group meetings through 2026-09-08). Its first editor, Veritura, exists,
    but it is not a v1 target.
- **Writer: in-house, about 300-500 lines, no dependency.** Two homes are possible. (a) A JS module that builds the
  string in the page, which serve.py stores next to the session. (b) A Python module in arsenal, using stdlib
  `xml.etree`, that rebuilds from `events.jsonl` plus the saved quantization, so exports can be regenerated when the
  quantizer improves. **Prefer (b)** for regeneration and (a) for an instant "save now" button. They share one fixture
  suite. music21 (BSD-3) could write MusicXML, but it is not installed, and the writer is small enough not to need it.
- **Mapping:**

| Our model | MusicXML 4.0 |
|---|---|
| Piano part, two staves | `<score-part>`; `<attributes><staves>2</staves>`, `<clef number="1">` G, `<clef number="2">` F |
| Ticks | `<divisions>840</divisions>`; `<duration>` in ticks; `<type>`, `<dot/>` from duration |
| Note staff and voice | `<staff>1|2</staff>`, `<voice>`; `<backup>` between staves in a measure |
| Chord column | `<chord/>` on 2nd+ notes of a column |
| Spelled pitch | `<pitch><step><alter><octave>`; `<accidental>` where shown |
| Ties | `<tie type>` (sound) plus `<notations><tied type>` (visual) |
| Tuplets | `<time-modification>` plus `<notations><tuplet type>` |
| Pedal | `<direction><direction-type><pedal type="start|change|stop" line="yes"/>` |
| Octave lines | `<octave-shift type="down|up|stop" size="8">` |
| Key from the tracker | `<key><fifths><mode>` at the bar where the tracker settled |
| Rough tempo | `<metronome><beat-unit>quarter</beat-unit><per-minute>c. 80</per-minute>` plus `<sound tempo="80"/>` plus `<words>rubato</words>` |
| Velocity | `<note dynamics="...">` (playback only; no engraved dynamics in v1) |

- **Save as uncompressed `take.musicxml`** in v1 (diffable, and readable by us in tests). `.mxl` (zip) later if size
  matters.

### 6.2 MIDI: two files per take

- **`performance.mid`:** SMF type 1, one track, the raw `on/off` events at their millisecond times, CC64 from `pedal`
  values, and a tempo meta event from the BPM estimate (the tempo map if the tempo lane gives one).
  - Nothing is lost: rubato, voicing velocities and half-pedal survive.
  - Dorico's MIDI import has its own quantize options, and MuseScore imports MIDI too, so this file lets Daniel
    re-quantize in those apps if ours is wrong.
- **`quantized.mid`:** the same notes on the grid. RH and LH go to tracks 1 and 2 by `staff`, so an app can split
  hands without guessing.
- **Writer:** in-house. SMF with variable-length deltas is about 100 lines in JS or Python. Alternatives if Daniel
  prefers a library: `@tonejs/midi` 2.0.28 (MIT, 287,668 B unpacked, read and write) or `midi-writer-js` 3.2.1 (MIT).
  Either would need his OK to vendor or load; neither is needed.

### 6.3 Other formats

- **MEI:** only via Verovio (`getMEI`) once Verovio is approved. No current consumer; archival value only.
- **ABC:** only as a later lead-sheet export (section 4.4).
- **SVG:** VexFlow's SVG backend can re-render closed bars as one wide SVG for a "save picture" button, or Verovio's
  `renderToSVG` for a paged look.
- **PDF:** MuseScore's command line or LilyPond offline (D3). Without an install, Daniel can print the Verovio review
  page to PDF from the browser himself.

### 6.4 Where exports live

Next to the session: `state/arsenal/performance/<session>/export/`, with `take.musicxml`, `performance.mid` and
`quantized.mid`. This folder is **private and never committed**, like the log itself. Test fixtures for the writers
must be synthesized (scales, arpeggios, chord stacks built to section 3's rates), never copied from sessions.

---

## 7. Video: a score in the TikTok frame

- **Path A: the live ribbon in REC (v1).**
  - The ribbon is a band of tiles (section 5.3) with the playhead fixed at about 30-35% of the width. Closed bars slide
    left and the open bar grows at the playhead.
  - **9:16:** a band around y 1050-1350 under today's staff, or replacing it when the ribbon is on. Staff size s = 14-16
    shows one or two bars.
  - **16:9:** the right-hand staff box is too narrow, so the ribbon needs a full-width bottom band above the keyboard.
    Layout is the display lane's and Daniel's call (D4).
  - **Cost per frame:** one group transform. Cost per onset: one small texture upload.
  - **Honest caveat:** live notation is a guess that settles a bar late. On camera the open bar will visibly re-spell
    now and then. The crossfade softens this, but it cannot remove it.
- **Path B: replay re-render (v2, best for posting).**
  - After a take, the quantizer re-runs with hindsight: whole-take tempo map, hand split, spelling.
  - The page replays the take from the log with the ribbon fed by the corrected score and records a fresh MP4 through
    the same `recorder.js`.
  - The replay machinery already exists for passages (`replay.js`, `/api/piano/replay?session&at`). A full-take
    re-render is an extension, not a new system (medium confidence; `replay.js` was only skimmed in this lane).
  - Verovio's timemap offers another variant: a page view that scrolls in sync with the recorded audio.
- **Path C: a still.** One engraved page (Verovio or MuseScore PDF) as the final frame or cover. Cheap, and pleasant
  for "here is what I just played".
- **Aesthetic knobs:**
  - Bravura, the default and the same as the staff, vs Petaluma, handwritten (D6).
  - Note colours: `noteCss` per pitch, as the staff glows today, vs plain ink for readability at phone size.

---

## 8. Decisions for Daniel

| # | Decision | Recommendation | Why it needs him |
|---|---|---|---|
| D1 | Load **VexFlow 5.0.0 core** (MIT, 336,625 B) from jsDelivr, pinned and HEAD-checked like three.js, or vendor it under `arsenal/web/` | CDN-pin, following the three.js precedent; vendor only if offline use matters | New third-party runtime code in the page |
| D2 | Later: **Verovio 6.3.0** (LGPL-3.0-or-later, about 7.3 MB) for the review page, export check, MEI and timemap. Fallback if refused: OSMD 2.1.2 (BSD-3, 1.32 MB) as viewer only | Approve for v2, off the live page | Licence and size |
| D3 | Install **MuseScore Studio 4.x** and/or **LilyPond 2.26** (both GPL-3.0) for command-line PDF | Not for v1: open `take.musicxml` by hand. Revisit if PDF becomes routine | Software install |
| D4 | Where the score band sits in 9:16 and 16:9, and whether it replaces or joins the "now" staff while recording | The display lane proposes; Daniel picks | TikTok frame composition |
| D5 | Live-guess notation on camera (path A) vs re-rendered settled notation (path B) for posts | A for practice, B for posting | Taste |
| D6 | Music font: Bravura (current) vs Petaluma (handwritten, OFL, `@vexflow-fonts/petaluma@1.0.1`) | Bravura for v1; try Petaluma as a toggle | Look |
| D7 | MIDI and MusicXML writers in-house (recommended) vs `@tonejs/midi` / `midi-writer-js` (MIT) | In-house; both formats are small | Avoids a vendoring OK altogether |

---

## 9. Verification gates (each needs a dated receipt before it counts)

- **G1 (layout bench).** A lab page, e.g. a future `piano-lab-score.html`, never the live page during the jam build.
  - **Fixtures:** synthetic, built to section 3's rates: bars of 12, 24, 43 and 67 onsets; chord columns up to 10
    heads; cross-staff arpeggios; tuplets; pedal changes every bar.
  - **Measure p50/p95 for:** VexFlow canvas format plus draw of one bar; Verovio `loadData` of an 8-bar window plus
    `renderToSVG` plus rasterize; the tape painter.
  - **Pass:** VexFlow open-bar update p95 under 8 ms on this machine with the three.js scene running.
- **G2 (recording).** Ribbon on, a 60 s REC at 60 fps. The recorder's skipped-frame count must not rise against a
  ribbon-off control, and the MP4 must show the ribbon. This proves the canvas-only capture path.
- **G3 (taint).** If any SVG renderer is used on the page, the overlay texture upload must succeed from its rasterized
  output (no `SecurityError`). Test both a data URI and a blob URL.
- **G4 (export round trip).**
  - `take.musicxml` from a synthetic fixture must load in Verovio with no import warnings, and its timemap note count
    must equal the fixture's note count.
  - Once D3 is approved, MuseScore's `-o roundtrip.musicxml` re-export must keep note, tie, tuplet and pedal counts.
  - Opening in Dorico is by hand, with Daniel.
- **G5 (MIDI).** `performance.mid` re-read by an independent parser must give back every on/off/CC64 time within 1 ms
  of the log. `quantized.mid` note count must equal the MusicXML's sounding notes after tie merging.

---

## 10. Open questions

1. Can VexFlow 5's cjs core load as a plain script tag that defines a global, or does the import map need jsDelivr's
   `/+esm` bundle? One HEAD check plus one import in the lab page settles it.
2. Does Verovio's SVG embed every glyph, so it is safe to rasterize with no external font? Section 2 assumes yes, at
   medium confidence.
3. How do MuseScore 4.7 and Dorico 6 import `<senza-misura/>` bars and cross-staff `<staff>` changes inside one voice?
   Only testable after D3, or by hand in Dorico.
4. Is bar-local VexFlow formatting (section 5.3) visually acceptable, or does the ribbon need whole-system justification
   with a reflow of the last closed bar?
5. Does the transcription lane deliver a per-note staff and voice, or only a pitch split? Cross-staff drawing depends
   on it.

---

## 11. Sources

**VexFlow**
- npm registry, latest: https://registry.npmjs.org/vexflow/latest (5.0.0, MIT, exports `.`, `./core`, `./bravura`). Publish dates from `npm view vexflow time`.
- Releases: https://github.com/vexflow/vexflow/releases
- Getting started (CDN URLs, `loadFonts`, Canvas and SVG backends): https://vexflow.github.io/vexflow-examples/guides/getting-started/
- jsDelivr file sizes: https://data.jsdelivr.com/v1/packages/npm/vexflow@5.0.0?structure=flat
- Cross-stave voices: https://github.com/0xfe/vexflow/pull/1434 (merged 2022-10-16), https://github.com/0xfe/vexflow/issues/1373, https://github.com/0xfe/vexflow/pull/1409
- PedalMarking: http://www.vexflow.com/build/docs/pedalmarking.html
- Fonts: https://github.com/vexflow/vexflow-fonts, https://data.jsdelivr.com/v1/packages/npm/@vexflow-fonts/petaluma

**Verovio**
- https://registry.npmjs.org/verovio/latest (6.3.0, LGPL-3.0-or-later)
- https://data.jsdelivr.com/v1/packages/npm/verovio@6.3.0?structure=flat
- News: https://www.verovio.org/news.xhtml
- JS and WASM: https://book.verovio.org/installing-or-building-from-sources/javascript-and-webassembly.html
- Methods: https://book.verovio.org/toolkit-reference/toolkit-methods.html
- Options (`breaks`, `font`): https://book.verovio.org/toolkit-reference/toolkit-options.html
- Output formats (timemap, MIDI, MEI; MusicXML input only): https://book.verovio.org/toolkit-reference/output-formats.html

**OpenSheetMusicDisplay**
- https://registry.npmjs.org/opensheetmusicdisplay/latest (2.1.2, BSD-3-Clause, depends on vexflow 1.2.93)
- https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/releases
- https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/releases/tag/2.0.0
- https://data.jsdelivr.com/v1/packages/npm/opensheetmusicdisplay@2.1.2?structure=flat
- https://github.com/opensheetmusicdisplay/opensheetmusicdisplay

**abcjs**
- https://registry.npmjs.org/abcjs/latest (6.7.0, MIT)
- https://github.com/paulrosen/abcjs/blob/main/RELEASE.md
- https://github.com/paulrosen/abcjs/issues/57
- https://data.jsdelivr.com/v1/packages/npm/abcjs@6.7.0?structure=flat
- ABC pedal decorations (abcMIDI): https://abcmidi.sourceforge.io/

**Fonts and SMuFL**
- https://github.com/steinbergmedia/bravura
- https://www.smufl.org/fonts/
- https://data.jsdelivr.com/v1/packages/gh/steinbergmedia/bravura
- https://w3c.github.io/smufl/latest/specification/font-specific-metadata.html

**Offline engravers**
- LilyPond 2.26.0: https://github.com/lilypond/lilypond/releases/tag/v2.26.0
- musicxml2ly: https://lilypond.org/doc/v2.23/Documentation/usage/invoking-musicxml2ly
- MuseScore command line: https://handbook.musescore.org/appendix/command-line-usage
- MuseScore 4.6: https://musescore.org/en/4.6
- MuseScore 4.7.x: https://www.scoringnotes.com/news/musescore-studio-4-7-5/
- MuseScore MusicXML: https://handbook.musescore.org/file-management/working-with-musicxml-files
- MuseScore licence (GPL-3.0 text): https://api.github.com/repos/musescore/MuseScore/license

**Dorico**
- Dorico 6: https://blog.dorico.com/2025/04/dorico-6-released/
- MIDI import: https://www.steinberg.help/r/dorico-se/6.1/en/dorico/topics/project_file_handling/project_file_handling_midi_importing_t.html

**Formats**
- MusicXML 4.0: https://www.w3.org/2021/06/musicxml40/
- Pedal element: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pedal/
- MusicXML 4.1 progress: https://www.w3.org/community/music-notation/2026/08/11/musicxml-progress-update-august-11-2026/
- MNX: https://www.w3.org/community/music-notation/category/mnx/, https://www.w3.org/community/music-notation/2026/09/08/mnx-specification-working-group-meeting-september-8-2026/

**MIDI libraries (not recommended; listed as alternatives)**
- https://registry.npmjs.org/@tonejs/midi/latest
- https://registry.npmjs.org/midi-writer-js/latest

**Canvas tainting**
- Chrome 131 intent: https://groups.google.com/a/chromium.org/g/blink-dev/c/JpA2vmA9XT8
- MDN: https://developer.mozilla.org/en-US/docs/Web/HTML/How_to/CORS_enabled_image

**Prior art (offline audio to editable score in the browser, not live)**
- https://www.songscription.ai/

A note on method: a summary of the VexFlow GitHub releases page gave 5.0.0 a 2024 date. The npm registry's publish
time is 2025-03-05, and every date in this document comes from the registry.
