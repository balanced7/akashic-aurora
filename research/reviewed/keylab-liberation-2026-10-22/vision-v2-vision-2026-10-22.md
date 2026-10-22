---
akashic_id: TBD (minted by `doc new`)
akashic_sha: TBD
schema_version: 1
status: draft
type: design
arc: media-suite
date: 2026-10-22
title: keylab-lit-vision-v2
gist: "KeyLab Lit v2: KeyLab 88 mk3 + sound room + VFX as one instrument. 11 pillars, hub spine, 9 waves, ratification questions, probes. UNRATIFIED"
visibility: fleet
body_type: markdown
seats: [claude]
category: [ui, ergonomics, method]
origin: authored
settled: proposed
supersedes: null
superseded: null
citations:
  - target: art_20261007_design-night-roadmap-2026-10-07_fa48f2
  - target: art_20261007_now-playing-multilayer-live-hook_1328e1
  - target: art_20261007_presentation-grammar-screens-scenes_236d39
  - target: art_20261008_one-world-ui-core-reconciled-spec_d622ac
  - target: art_20261013_story-layer-v1-reconciled-design_dce896
created: "2026-10-22T00:00:00"
updated: "2026-10-22T00:00:00"
---

> **DRAFT, UNRATIFIED.** This is vision v2. Nothing here gets built until Daniel says "that's right" on the brief (CONDUCT.md:26-27, L3 applies to every build, not only visible ones). The arc label `media-suite` is a proposal (see Q2).

# KeyLab Lit: The Complete Vision (v2)

**Daniel, 2026-10-22 (verbatim):** "I want the full vision, no shortcuts or hedges, every feature you could think of and want."

**Abbreviations.**
- **kl-mem** = `C:/Users/L5/.claude/memory/keylab-mk3-liberation-2026-10-22.md`
- **fljb/** = `research/in-flight/fl-jam-bridge-2026-09-14/`
- **[ev] unverified** = a web or prior-art claim from the evidence front. Nobody in this pass re-read it, so treat it as something to probe, not as fact.
- Status: **B** built · **P** partly built · **N** new. Size: S / M / L / XL.
- Line numbers in `arsenal/keylab/*` were read on 2026-10-22. Those files are untracked and still changing.

## What changed since pass 1

| Change | Why |
|---|---|
| The pad grid is the printed **9-5-1** layout, 3 across by 4 down. The FRAME border is **10 pads**, not 8. | Daniel's photo; chordview.py:27-38 |
| Warm colours move to saturated reds, roses and magentas. dom7 is no longer amber. | Amber, yellow, orange and lime photograph almost white on these LEDs. |
| 3 new pillars: **9 The Door**, **10 Trust**, **11 The Commons** | Recovers the house lens that pass 1 dropped and gives a home to every missing ask |
| New in Pillar 6: Pad Desk, Pad Learn, AD2 kit map, a swatch picker | Asks 5-8 were partly or wholly missing |
| New in Pillar 3: BPM seed-and-refine, an accuracy bench, timeline locked to track position | Asks 18-19 |
| Every corrected citation is fixed. Three wish links are dropped (W228, W58, W181/W182 "resolves"). | Fact-check verdicts |
| A licence finding: beatsync imports aubio-ledfx, which is **GPLv3+**, into an Apache-2.0 public repo | Installed package metadata, read 2026-10-22 |

## North star

You own a studio's worth of sound, all counted on disk:
- **Instruments:** Kontakt 8, Serum 2, Analog Lab V and Addictive Drums 2. All four .vst3 files exist (fljb/local-inventory.md:21,132-135,146,151,164-165).
- **Samples:** 2,687 stock FL WAVs (fljb/splice-and-sounds.md:17, recounted 2026-10-22) and 82 Splice WAVs (81 when counted on 09-14; local-inventory.md:22).
- **Projects:** 913 .flp files, of which about 231 are not autosaves (Projects folder recount, 2026-10-22).
- **The keyboard:** as of this morning the house can light it and label it. It named your chords live (kl-mem:11-19).

This vision makes all of that one thing.

- **The KeyLab is your hands and your second screen.** Its pads, LCD and LEDs speak for every page you love: piano, First Light, Play and the VFX Bench. Its faders, encoders and buttons reach back into those pages "like changing dials in a game engine" (charters/daniel/INTERIORITY.md:117-118).
- **A low-latency native room** hosts your instruments and effect chains. It runs on its own or alongside FL, and it reads and writes FL's own preset files.
- **One colour language covers everything.** It changes over seconds, never strobes, and stays inside the colours these LEDs can actually show. The quiet state is a complete composition (arsenal/SPECTACLE-DESIGN.md:83-86).

**Why it matters to you:**
- It is your oldest want: beautiful live surfaces (project-origin-simon.md:3,17-25).
- It runs on your favourite pattern, "the second press is a question", which was born from a KeyLab reconnect (second-press-principle.md:11,13,18-19).
- Every session becomes something you can play, keep, give to Simon and post.
- And it answers the feeling that started it all: "really guilty about having a $1300 keyboard and not using any of its fancy functions."

**The hardest part is already on disk.** `arsenal/keylab/` holds:
- the SysEx protocol, confirmed on the hardware;
- a renderer that resends only the pads that changed;
- five chord pad schemes;
- beat sync from loopback audio.

It is **untracked** (`git status`: `?? arsenal/keylab/`). No atom, task or wish mentions it yet.

## What the hardware told us today

| Fact | Source |
|---|---|
| SysEx is `F0 00 20 6B 7F 42 <payload> F7`. The LED message is `[00,2,3,id,R,G,B,00]` with RGB 0..127. The **req byte is 0x00**; 0x02 turns the pad white. | kl-mem:14 (the README fix is already in hand) |
| Live pad colour works only on the DAW bank (ids 82-93), and only in **physical** DAW mode (Prog + 6th screen button). SysEx cannot switch modes. | kl-mem:15 |
| The pad mode selector has three positions: **left = Arturia Program, middle = DAW, right = Default**. Live colour needs the middle position. | Daniel, 2026-10-22 |
| **The pad grid is 3 across by 4 down, printed 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4** | chordview.py:27-36 (photo of the 12-colour test) |
| **Warm, low-saturation colours (amber, yellow, orange, lime) photograph almost white.** Saturated blue, purple, magenta, pink and red read clearly. | Daniel's photo, 2026-10-22 |
| A burst of about 36 packets freezes the device and needs a power cycle. 12 is safe, and that is the device ceiling. PadRenderer's own default is a burst of 10 with a 4x gap after it. | kl-mem:16; ledframe.py:21-45 |
| **Popups (23/24/25) dismiss after about 1 s. The full-screen F2L (12) persists.** A 100-frame colour cycle at 60 ms spacing ran with zero flicker. | kl-mem:17; Daniel's session |
| On a single-pad flicker test the host hit every target rate up to 120 Hz. The device looked even at low rates, and uneven but usable at higher ones. The ~10 ms drift is the device's own LED cadence. | kl-mem:19 |
| Keys arrive on "KeyLab 88 mk3 MIDI". LEDs and the LCD go out on "KeyLab 88 mk3 DAW". | kl-mem:18 |
| **Contested:** "only one process can hold the DAW output" (kl-mem:18). Windows MIDI Services ports are documented as multi-client, which would make a collision a **silent clobber** rather than a "busy" error [ev] unverified. | fljb/fact-check.md:143; probe P1 |
| The surface has 12 RGB pads, 34 button LEDs, 9 faders, 9 encoders and a main encoder | protocol.py:48-55; keylab88mk3.js:7-10 |
| FL drives the Focusrite USB ASIO interface at 48 kHz. The "256" buffer is the FL Studio ASIO driver's setting, and the real ASIO buffer is unverified. | Registry; fljb/fl-scripting.md:208 |
| A .fst file is an FLhd/FLdt event stream. It carries "FL Studio 25.2.5.531" and "Fruity Wrapper" as UTF-16 strings. | Byte read of Piano 1.fst, re-checked 2026-10-22 |
| Live chord naming worked on the first try. Forwarding notes to the GS Wavetable synth plays them (`--sound`). Sustain (CC64) was fixed the same day. | chordview.py:88-110 |

---

## 1. The pillars

### Pillar 1: The Hub. One owner of the light

**Purpose:** one process owns the device. It composites what every page wants, hands each surface to whatever you are looking at, and never breaks the device's limits. Everything visible depends on it.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Land arsenal/keylab with a receipt | **Make the licence call first** (aubio-ledfx is GPLv3+; Pillar 10). Then commit by named paths. Add a report atom of the measured limits and turn the inline selftests into pytest pins. | P | S | git status; kl-mem:11; beatsync.py:7,61 |
| KeyLab hub in `arsenal serve` :8793 | One MidiOut on "KeyLab 88 mk3 DAW". A paced writer thread wraps PadRenderer. Priority order: popup > page > ambient. It runs `resync()` automatically after a foreign write and shuts down cleanly next to `app.cues.close()`. | N | M | chordview.py:130 and beatsync.py:122 each send `daw_connect(False)` on exit; ledframe.py:1-11,21-45,51; serve.py:156-178, :804 |
| **Global burst governor** | One token bucket for the whole device. Last write wins per pad, and the coalesce count is recorded. The **LCD gets its own lane**, spaced at 60 ms or more. "The LCD never goes dark because two pages got excited at once." | N | S | kl-mem:16; 60 ms LCD rule from saxofonbrian [ev] unverified (probe P14) |
| Layer stack + intents API | Pages and CLIs POST intents, never raw bytes: a pad frame, LCD lines with per-line colour, button-LED roles, an attention flash. Layers stack ambient/beat < page < practice < popup, and only the delta is sent. | N | M | pianocue.py:191-304 (CueHub); d622ac:67 §1 rule 1, "a surface is a projection, never a store" |
| **One governed scene: `keylab.scene.v1`** | Holds pads[12] (rgb, role, source), button roles, LCD lines with per-line rgb and screen, the menu tree, mode, palette id, tempo and phase, and lease holders. The validator refuses in sentences, the way `present.scene.v1` does, and the scene projects into the one-world journal. | N | M | d622ac:67; present.scene.v1 |
| `keylab` SSE event kind | Hub state goes out on the cue SSE, so the twin and the device always agree. EVENT_KINDS is a closed tuple, so adding this is a deliberate extension. | N | S | pianocue.py:65, enforced :229-230 |
| **Input plane: named events** | `enc3 +2`, `fader7 0.61` and `ctx4 long-press` go out on SSE. Pages subscribe by name, never by raw CC. One map on the server replaces every per-page localStorage CC-learn. | N | M | first-light.js:844-848 (localStorage today) |
| Foreground leases per surface | Pads, LCD and button LEDs are leased separately, and the visible tab beats a hidden one. Leases renew by polling and expire after 6 s. A small LCD stub says who holds the light, then dims after 2 s. | N | M | bifrost_ui.py:224-285 (VFX_LEASE_TTL 6.0); cues.js:1072-1210 |
| **Producers become clients** | `chordview`, `beat` and `show` stop opening the port and post to the hub instead. If the hub is down, they fall back to a lock file that names its owner (the GPU-LOCK pattern). The verbs are rerouted, never deleted. | N | S | feedback_dont_delete_functionality |
| Cross-origin bridge for /vfx | Add CORS and OPTIONS on `/api/keylab/*` for 127.0.0.1:8787 only, or proxy through bifrost_ui. | N | S | serve.py:239-249 has no do_OPTIONS. The Origin check at :592-594 lets :8787 through, but no CORS headers are sent. |
| FL coexistence switch | A visible LCD mode, "FL drives" or "Aurora drives". The hub detects FL's script repainting the LEDs at init() and offers **Yield** (the hub goes input-only) or **Hold** on the soft keys. The house never fights FL silently. | N | M | kl-mem:18; probe P1 |
| **KeyLab Atlas** ("I want us to understand our full surface") | Click any control on the twin to see what it sends in Program, DAW and Default modes, plus Chord, Scale and Arp. Covers the 6 user programs, MCU/HUI, touch-sensitive encoders and faders, pad pressure, and the Arturia-mode (00 01 04) vs DAW-mode (00 02 04) protocol families. Every fact carries a dated receipt. | P | M | __main__.py:273,469 (`monitor`); the families and pressure are [ev] unverified |
| **`learn-map` verb** (the control census) | The LCD prompts "turn encoder 3" and the hub records the CC, its encoding and its channel. The same verb lights the pads one at a time for you to tap. The 3D twin lights each control as it is captured. The result is written to a **tracked** control map. | P | S | keylab88mk3.js:9,41-45 |
| One pad-layout truth | One shared table holding the photo-confirmed 9-5-1 grid. chordview, the twin and the scene all import it, and a pin enforces it. | P | S | chordview.py:27-38 is correct. keylab88mk3.js:34,519 still draws 2x6 [U]. protocol.py:83-85 PAD_NOTE is the note map the grid builds on, not a conflict. |
| Twin parity tick | The twin shows "hardware in sync · 2 s ago" using the age of the last receipt. The twin screen uses the Outfit font, with `?font=raleway|jost` to switch. | N | S | keylab88mk3.js:672-744 |
| Diagnostics with personality | Short LCD lines that retire once the evidence clears them: "DAW mode? Prog + 6th btn", "FL has the light", "There it is". | N | S | second-press-principle.md:37-46 |
| Memory and uptime guard | The hub and the engine report commit and private bytes. They hint gently near the 82-92 h low-memory window and refuse a 6 GB library without headroom, saying why. | N | S | ram-freeze-2026-09-24-fanout-on-day-four.md:13 |

### Pillar 2: The Light Language. Pads, LCD and colour that teaches

**Purpose:** the 12 pads, 34 button LEDs and the LCD become one readable harmonic alphabet. Every page shares it, and it fits inside 7-bit colour, the burst ceiling, and **the colours these LEDs can actually render**.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Shared palette module with tone mapper | One pipeline: token → OKLCH → tone map → **LED_SAFE snap** → sRGB → to7. Change a look on First Light and the KeyLab and piano change with it. Your saved looks (Violet & rose, wide violet, Golden wings) become KeyLab presets. | N | L | shader-school-2026-10-13.md:11-15,79; research/in-flight/shader-school-2026-10-13/arc-piano-studies.md:468-469 |
| **Measured LED gamut** | Photograph a ramp to produce `LED_SAFE` and snap every token to it before to7. Warm meanings move to saturated red, rose and magenta, which also matches your violet-and-rose favourite. | N | S | Today's photo; probe P4 |
| **LED-true preview** | The twin, and any page that shows a pad colour, renders the snapped colour, so a page never promises a colour the pad cannot make. | N | S | follows from the gamut |
| noteColor on the hardware | Piano's OKLCH circle-of-fifths colours (hue 200 + 30 × fifths index, brightness evened by LUMA_PULL) run through the tone map, because noteColor returns linear RGB that can go above 1. A bench page shows each swatch next to a phone photo of the real pad. | P | M | piano.js:326,349,376,380-398; protocol.py:106 |
| Schema picker, now six | ROLES / NOTES / QUALITY / SPLIT / FRAME, plus **FUNCTION**: colour by harmonic function in the key (Hookpad's idea, remapped away from yellow and orange). Picked from an LCD menu. The legend shows on first use and after that only on a second press. | P | S | chordview.py:41-66; Hookpad [ev] unverified |
| **Root marking without white-on-warm** | Today the root is pure white (chordview.py:51). In QUALITY a major chord is (255,180,0), so it reads as three white pads. In ROLES the minor and major thirds, (255,150,0) and (255,200,0), are **the very tone that names the quality, and they cannot be told apart from the white root**. Fix: when warm hues are in play, mark the root by brightness, a slow pulse or its position, and recolour the warm entries. | P | S | chordview.py:18-25,51 (verified defect) |
| Chord families as colour families ("it would be cool for 7ths to make a chord be one color on the pads") | maj7 violet-rose, dom7 **saturated red** (moved off amber), m7 teal, half-diminished dusk blue. Triads take a lighter tint, extensions a bright edge pad, altered tones a rose rim. Families come from harmony-feel's measures, not from suffix strings. | N | M | harmony-feel.js:160-179 |
| Living edges ("or perhaps the edges change color") | In FRAME the **10 border pads** carry harmonic motion; only 6 and 7 are interior. Colour travels the loop 9→5→1→2→3→4→8→12→11→10 over about 0.4 s, at most 10 packets, which fits under 12. The direction of travel shows movement up or down the fifths. "a region resoponsible for quality, one for note": the border is quality and the centre pair is the note region. | P | M | chordview.py:38; SPECTACLE-DESIGN.md:83-86 |
| **Shape dictionary** ("the pads changed color and shaper per chord too!!!") | The 9-5-1 grid has real geometry. Columns are chromatic (left C-D#, middle E-G, right G#-B), and **every row is an augmented triad** (9,5,1 = C,E,G#). One step right is +4 semitones, one step down is +1. Wrapping right returns to the same row; wrapping down lands in the next column. So every chord quality is **one fixed shape on the wrapped grid, whatever its root**. For example, a major chord is: root, then one column right (+4), then three rows down from there (+7). The legend shows "major = this shape" and the games ask you to find shapes. | N | M | protocol.py:85 PAD_NOTE (arithmetic verified) |
| Harmony modes on pads | Tonnetz and Stained-glass views of the current harmony | N | M | lens 1 P8 |
| The lean on the pads | A leading tone's pad breathes toward its target's colour. No text, and off in recordings unless you switch it on. Shown only if you answer the story layer's gate question. | P | S | piano/lean.js:1-10; dce896:61,108-109 |
| Note truth | One note is named as a note, two as an interval, three or more as a chord (`kind: note|interval|chord`). There is one chord reader, never a second namer. | N | S | W247 WISHLIST.md:1584; theory.py:1 "not a jazz oracle" |
| Live chord card (LCD) | A persistent F2L screen. Line 1 is the chord in its family colour. Line 2 is the key, Nashville number and bass in the key's hue. Dims to 46% when idle. Uses ASCII # and b (the page twin keeps Noto Music). | P | S | keylab88mk3.js:63 (SCREEN_IDLE 0.46; its comment wrongly says 50%), :672-744 |
| Now Playing card | Title and artist scroll gently, with BPM and key on line 2. The LCD and the ambient pads take the album palette, snapped to LED_SAFE. | P | M | beatsync.py SMTC; 1328e1:177-180 (S3) |
| Colour on three timescales | The palette drifts over minutes, the harmony family over seconds, and beat brightness changes in under a second. No strobing. Loud means more momentum, not more white. | N | M | 1328e1:108-111,191; SPECTACLE-DESIGN.md:83-86 |
| Cleverer than the hardware ("perhaps we can be more clever than the hardware") | The most salient pad goes first (the root lands first). A dirty-pad queue shares the budget between layers. Brightness envelopes run only on pads that matter. Button LEDs serve as extra pixels: ctx1-8 as a beat bar or menu cursor, Hold following the pedal, Chord in the root colour. The LCD colour acts as a 13th ambient light. Temporal dither stays inside the budget. **Probe the device-side BlinkState (BLINK1-3, PULSING):** if the firmware honours it, beat lights cost one packet per change instead of a stream. | P | M | keylab88mk3.js; protocol.py:48-55; BlinkState from the Bitwig MIT extension [ev] unverified (P13) |
| **Stability ladder + "shimmer"** ("test higher and lower so we can track stability, even if its not perfect it could be used for illustrative effect") | A dated curve of the Hz levels you judge clean, uneven or broken. Then a **shimmer** effect class that uses the uneven band on purpose, for risers and tension only and never at rest. You hear a build and see the pads shimmer up into the drop. | N | S | __main__.py ledbench; kl-mem:19 |
| **Test pattern named on the LCD** ("say what test pattern its in") | ledbench writes an F2L line for each level: "RATE L3 · 20 Hz", "SPACING 4 ms", "BURST n=14". Today the level shows only as lit white pads. | N | S | __main__.py:352-358 |
| **LED-wall treatment** ("can we make it be a renderable window for our VFX?") | The 12 pads plus 34 LEDs become a downsampled projection of the foreground page's palette and motion, at 15 fps or less. The quiet state is still a full composition. | N | M | 236d39:120 (LED wall) |
| Pads as spectrum meter | An idle mode laid out as **3 columns (low, mid, high) × 4 rows of level**, not 12 bands in reading order. Lows are rose-red and highs cyan (no warm-to-white). 15 fps, changed pads only. Soft passages keep their focal glow. | N | M | GRID; SPECTACLE-DESIGN.md:83-86 |

### Pillar 3: Beat, Time and the Chord Timeline

**Purpose:** the light locks to the pulse from Spotify, FL or your own hands. The house builds its own database of chord changes against time, so the pads can show what is coming as well as what is sounding. In your words: "an eventual goal of tying into ultimatechords and building our own db showing chord changes in time with the music".

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Beat engine as hub producer | beatsync (WASAPI loopback + aubio) runs on a hub thread instead of opening the port itself. It publishes beat, bar, BPM and confidence to the hub and the SSE, so everything shares one clock. It replaces the duplicate NP S4 "Ears" plan. | P | M | beatsync.py:9-11,118-123; 1328e1:186-190 |
| **BPM seed-and-refine** ("starting bpm being the one sourced from multiple db's") | Seed the detector from the candidate tempo sources that agree, then let loopback refine it. The LCD shows "92 · 2 sources · heard 91.8 · conf 0.86". Which sources exist needs a probe; Spotify's BPM API is closed to new apps. | N | M | kl-mem:21; probe P20 |
| **BPM accuracy bench** ("Can you keep refining the bpm detect and accuracy?") | Ground truth comes from your own FL bounces (the .flp tempo is known) plus agreement with tap tempo. Half- and double-tempo errors, which aubio is known to make, are scored separately. Kept as a dated accuracy curve. | N | M | beatsync.py:11 |
| March patterns ("I want the led lights to march to the beat changing color as it clicks through") | March round the 10-pad frame, bar fill, downbeat bloom, ping-pong, chord pulse, off-beat sparkle. At most 4 changed pads per beat. ctx LEDs show bar position and the Metronome LED marks the downbeat. | P | M | beatsync.py:58 (cycle mode) |
| Tap and hold tempo | Tap sets or corrects the tempo, and its LED blinks on the beat. Hold shows BPM and confidence. It drives the jam tempomap, so Claude's groove plays in time. | N | S | protocol.py:48-54 (tap:4) |
| FL transport mirror | Play, Stop, Rec and Metro LEDs mirror FL when FL drives. When Aurora drives, they start and stop the jam or take. | N | M | protocol.py:48-54 |
| **Timeline locked to track position** ("know the bpm and track position") | When you seek in Spotify, the look-ahead pads re-sync. Reading the SMTC timeline position is an inference and needs probe P19. | N | M | beatsync.py SMTC |
| Heard-song timeline | During loopback, beat-stamped rows are stored: time, beat phase, key, Nashville number, kind, source, song id. They live in a private store keyed by SMTC title. A second listen refines them, and a quiet as-of/confidence stamp shows that. | N | L | media-suite-project-2026-09-13.md:369,378-382 (the stamp) |
| Bar-grid view | A scrolling beat-synced bar grid with a moving cursor on the page, and a 2-bar text window on the LCD: `\| Cmaj7 \| Am9 \| Dm7 G13 \|` | N | M | Chordify [ev] unverified |
| Chord sheet import, clean-room | You paste a sheet you are entitled to use. Only chord tokens and section labels are parsed and aligned by beat. No scraping and no lyrics stored. UltimateChords' terms get checked first. | N | M | your UltimateChords ask |
| Look-ahead on the pads | The next chord's pads glow at 20% half a beat early and land at full on the change. "next: Am7" appears only in rests. On your own bounces an offline pass lets the lights anticipate the drop. | N | M | dce896:59; LedFx lookahead [ev] unverified |
| Your playing as timeline | roll/1 sessions replay on the pads and the twin together. Feelings first: no counts or grades in tracked files. | P | M | W248 WISHLIST.md:1608; dce896:60 |

### Pillar 4: The Controller and Teacher. Dials, menus, modes, games

**Purpose:** every continuous control plays the VFX pages live. The menus show that a path exists. The instrument teaches you how to use it, which cures the guilt directly.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| `map <control> -> <parameter>` | The T399 F4 gesture. Hold a page parameter and turn a knob, or choose it from the LCD. The LCD confirms "ENC 3 -> pulse" in the parameter's colour. Saved per page and per mode on the hub's input plane. | P | M | fences/media-arsenal-contract/reconciliation.md:90-101; first-light.js:764-850; play.js:2070,2084-2110 |
| **First Light and Play bound to the hub** | First Light: a knob turns the hue, a fader sets intensity, and the preset name pops up for about 1 s. Play: the encoders move macros and the pads light as macro scenes. | P | M | first-light.js:806-848; play.js:307 |
| VFX Bench strip layout ("use the keylab as a vfx device with all the faders and buttons") | Faders 1-9 control sub, gap, thick, cube, hole, spin, pulse, sat and dim. Encoders 1-5 control round, star, wire, see and rate. The main encoder steps through the 9 avatar states, and each state's tint lights the pads. Bank± switches identity palettes. | N | M | agent-avatar.js:574-591 (11 PARAMS + 3 DIALS), :437-457 (9 states); vfx.html:403-414 builds its sliders from that manifest |
| Soft takeover | A faint arrow colour shows until the physical fader crosses the value set on screen, so nothing jumps. Relative encoders never need pickup. | N | S | arsenal/VISUAL-QUALITY-BASELINE.md:8-19 |
| Pads as scene launchers | 12 saved looks, each in its own dominant colour. A tap crossfades over seconds, velocity sets the fade time, and holding a pad previews the look on the LCD. | N | M | /api/piano/looks |
| Menus that show a path exists ("interact with the keylab display with menus and adaptive beautiful coloring") | Built on the **native LCD list widget** (title 0x28, items 0x15, cursor), so menus scroll like the KeyLab's own. Dim ctx LEDs mean "this leads somewhere". The first press shows the name, the second a whispered hint, the third the full picture. Main encoder scrolls, Back steps back. Menus project the H9 one-world mode schema. | N | L | second-press-principle.md:11,13,18-19; d622ac:90 (§3); list widget [ev] unverified (P16) |
| **Legend node in every menu** | What is bound, what is not, and why. "Half of the battle is knowing what the given bounds for a thing are." | N | S | INTERIORITY.md:236-238 |
| **Modes as saved tunings of the whole instrument** | Hunt, Explore, Ship, Heads-down, Init, Perform and Practice. Each one tunes pads, LCD, menus and page visuals together. The mode name sits on LCD line 1 and a ctx long-press cycles modes. The severity floor cannot be switched off. Ships with the modes pre-made. | N | M | d622ac:90,108 (§3-4) |
| **Second-press hints on unbound controls** | "enc 3 · unbound" → "hold ctx8 to learn" → the full picture → "There it is." | N | S | second-press-principle.md |
| Page presence cards | The LCD briefly shows which page holds the light and what it offers | N | S | lens 1 P8 |
| Musical spells | A progression, riff or key change casts a spell through the map verb. Our proposed mapping: maj7 opens the bloom, dom7 builds tension, a resolution releases it. The atom itself sets no chord-to-effect mapping. | N | M | 236d39:157 |
| Shader Lab preview | Shader name and palette on the LCD and pads, read-only. Live control stays off until its safety review clears. | N | S | arsenal/shaders/serve.py:1,58 |
| What-does-this-do mode | Hold Settings and touch a control: the LCD names it and its binding, and the twin highlights it. A second touch shows more. Unused controls whisper once per session, never during REC. | N | M | second-press-principle.md |
| Scale and Chord lighting | Scale mode: the root takes the active colour, scale notes are dimmed, off-scale notes are dark. Chord mode: one diatonic chord per pad, coloured by family, and a tap previews it. | N | M | Push scale grammar [ev] unverified |
| Echo and follow games | Chord echo, follow the lean, rhythm catch, find the shape. No score. A miss gets a softer hint, never a red light. | N | L | INTERIORITY.md:29 (despised grades); dce896:60 (no grades) |
| Cadence moments | On V→I, a deceptive cadence or a ii-V: one slow pad sweep, and the cadence name in a rest, once | P | S | cadence-live.js:17-28 |
| Agent co-performer on pads | Claude's notes glow **moonlight**, never a pitch colour, capped at 0.75 of your light, so there are two visible voices. The LCD says whose phrase it is. | P | M | piano.js:537-595, :658-662 |
| **Duet suggestion lights** | Dim "suggestion" pads offer a next chord. You can ignore them, and they leave on the next bar. | N | S | lens P4 |
| **The instrument teaches itself** | A **KeyLab tour episode**: an arsenal/present scene where each control lights on the device and the twin as it is introduced; it works as a lesson and as a short. A **one-page cheat card** generated from the control map, reprinted whenever bindings change. The KeyLab as a **Forest Walk**, one surface per week (pads, LCD menus, encoders, the Engine Room) with predict-before-look and a teach-back close. | N | M | forest-walks-practice.md; your "guilty about ... not using any of its fancy functions" |

### Pillar 5: The Engine Room. Low-latency host, instruments and chains

**Purpose:** "low latency audio play space, where we can craft sounds and IMPORT them to FL". One supervised native process plays your instruments and chains at playable latency. It works with FL closed, and a misbehaving plugin cannot take FL or the machine down with it.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Carla engine, Python conducts ("so you can invoke kontakt and the piano with effects vst's and EQ's") | Headless Carla on Focusrite ASIO loads any VST3 you own and plays it from the keys. Python loads, routes, sets parameters and saves state, and never renders audio. Carla runs **out of process** (licence, Pillar 10). | N | XL | kl-mem:23 (~3-12 ms; "pure-Python realtime VSTi is a trap") |
| Pedalboard chain runner | Stock effects plus your VST3 effects (OTT, Rev PLATE-140, Kilohearts, Trash, Smooth Operator Pro), live through AudioStream or offline. The same chain object renders the bounce, so live and offline sound identical. | N | L | kl-mem:23; fljb/local-inventory.md:140 |
| Latency receipt, leg by leg | A quiet strip: press → engine → ASIO out in ms, plus buffer, sample rate and p95, with a declared line for the hardware leg. One loopback drill turns that declared line into a measured one. | P | M | piano/latency.js:1-15; target p95 < 30 ms (media-suite-project-2026-09-13.md:49) |
| Plugin crash shell + panic | Bridged or sandboxed slots. A crash greys the slot and leaves "[Serum 2] fell over, press to reload". A panic pad, or holding Stop, sends all-notes-off. | N | M | second-press-principle.md:18-19 |
| Instrument rack with sound cards | Cards with fingerprint art in OKLCH, macros, "played 3x this week" (private), and a single "Play it" action. **Colour belongs to the sound:** it is set once and carried to the pads, the LCD accent and the card. | N | L | Maschine [ev] unverified |
| Macro map | 8 macros + volume on encoders and faders. Touching one opens the **native knob/fader popup** (0x1C / 0x1E) with name, value and a coloured bar. One-click learn, saved per plugin. **NKS pages:** where a plugin ships NKS presets, the vendor's named encoder pages are used ready-made. | P | M | keylab88mk3.js:7-10; popups and NKS NICA [ev] unverified (P15) |
| **The room speaks the scene** | Plugin parameters become LCD menu trees through `keylab.scene.v1` | N | M | Pillar 1 scene |
| Snapshots + morph fader | Snapshots A and B of instrument + chain. A fader morphs between them while the screen colour blends from A's hue to B's. A double-tap recalls exactly. | N | M | studio.js:1-10 |
| Mutate with taste | 8 seeded neighbours on 8 lit pads, reproducible from the seed. Agent variation sets arrive unlabelled and are judged blind. | N | M | collaborative-means-iterative.md:10-14 |
| Kontakt-aware loading | Libraries listed by registry name. Load cost (RAM and time) measured on first load and shown afterwards. Plain vendor installs by default. | N | M | local-inventory.md:157-159 |
| Chain Bench diagram | Input → slots → output drawn as patch cables in the patch-bay identity (aluminium, VU-amber, teal and rose cables, Archivo + JetBrains Mono). Cables glow with signal level. Drag to reorder. Bypassed slots stay drawn but dimmed. VU-amber stays **on screen only**; on the LEDs it maps to rose. | N | L | media-suite-project-2026-09-13.md:29 ("I love it and thats a beautiful presentation and color scheme!!!!") |
| Chain on the KeyLab | The LCD shows "CHAIN 3/5 OTT" in the slot's colour. ctx1-8 select slots and their LEDs show bypass. Encoders edit the slot and Back goes up a level. | N | M | protocol.py:225-275 |
| **Mixer strip mode** | Faders become the room's (or FL's) mixer strips. The LCD shows the strip name and level, and the pads show meters. | N | M | lens 1 P9 |
| **Preset browser on the LCD** | Browse FL mixer presets and room chains from the KeyLab. The second press asks "import to FL?". | N | S | lens 1 P9 |
| A/B by ear, blind | Two chains, loudness-matched so the louder one never wins. Blind mode reveals the answer and both LUFS after you pick. | P | M | arsenal/media/audio.py:1-15 |
| Per-slot latency/CPU budget | A thin bar under each slot and a total by the output. A slot over budget is called out once. | N | S | fljb/plugin-path.md §2.3 |
| Parallel and send chains | Dry/wet, New York compression and reverb send lanes, drawn as branching cables, each with a KeyLab fader | N | M | FL mixer preset names |

### Pillar 6: The Pad Sampler and Pad Desk

**Purpose:** "how can we make it easy to assign whatever I want to the drum pads". The 12 pads become a sampler whose light is the sound's identity. Hue says what it is, brightness says how hard it was hit, and the LED shows the decay. "their app sucks", so this one doesn't.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| **Pad Desk page** ("a sexy ui that I can just drag and drop samples into on top of the pad") | A 3x4 grid in the printed 9-5-1 layout. Drop a WAV on a pad and **the real pad lights the moment you drop**. Each pad shows its name, colour, velocity curve and envelope. | N | M | GRID |
| **Swatch picker, LED-safe** ("easily select color") | Auto-colour is the default and never forced. You can pick from swatches limited to LED_SAFE, each one next to a phone photo of the real pad. | N | S | Pillar 2 gamut |
| 12-pad kit, colour identity | Hue from the spectral centroid or pitch class, lightness evened across hues (LUMA_PULL). **Kicks rose-red, hats cyan**, with no warm-to-white. A quiet ember at rest. | N | L | piano.js:376; DAW bank 82-93 |
| Velocity light + layers + **curve editor** ("velocity controlls") | Flash brightness follows velocity, then decays along the sample's own envelope at 15 fps, changed pads only. Up to 4 velocity layers, shown as rings on the screen mirror. Velocity curves are drawn and edited by drag. | P | M | ledframe.py; media-suite-project-2026-09-13.md:187 (glowing peaks) |
| Per-pad ADSR, pitch, choke, loop ("as well as adsr settings") | Select a pad and the encoders become A/D/S/R, Pitch, Start, Filter and Pan. The Desk has **draggable ADSR handles**. The LCD draws a 2-line envelope glyph in the pad's colour. Choke groups share a tint. | N | M | INTERIORITY.md:117-118 |
| **Pad Learn gesture** ("shift button ... play a piano note then tap a pad and then the pad will trigger that note") | Hold the ctx key the LCD labels LEARN, play a key, then tap a pad. The LCD says "pad 9 = D#3" and the pad takes that note's colour. The hub remaps the pad and re-emits it on the loopback port. **To "Should we make our own vst?": no VST is needed for the remap.** FL has no MIDI-effect slot, so a VST would have to load as an instrument anyway. | N | S | fljb/fl-jam-bridge-plan.md:230 |
| **Device-side pad programs** (probe) | Write pad notes into an Arturia user program, so the mapping works with Aurora closed. "the manual bund method" may mean this; Q12 asks you. | N | M | probe P18 |
| **AD2 kit map** ("map addictive drums notes to specific pads") | Pick AD2's GM map preset, and each pad shows its AD2 piece name ("Kick", "Snare", "HH closed") on the LCD and the Desk. Pad hits go out as integer GM notes through the hub to a loopback port into FL/AD2. The loopback needs the Windows MIDI Services SDK download and your OK. | N | M | fljb/splice-and-sounds.md:18; fljb/virtual-midi-and-sync.md:12-24 |
| **Pad-mode awareness** ("there are ways of switching modes and pad banks / functions ... I want us to expose them") | The LCD tells you which position the selector is in (left Program, middle DAW, right Default) and that live colour needs the middle one. Pad banks and functions are listed in the Atlas and switchable where the protocol allows. | N | S | Today's selector fact; probe P17 |
| Fill pads from your sources | Browse FL stock, Splice, D:\Cymatics and FPC kits. Audition in time and in key. "Kit from this loop" slices a loop to 12 pads by transients. | N | L | splice-and-sounds.md:17,34-35,68-76 |
| Chord pads | One chord of the key per pad, coloured by family and laid out by the shape dictionary, playable on any hosted instrument | P | M | chordview schemes; W247 |
| Resample-to-pad | Hold Record and play. The phrase and its chain become a WAV on the next free pad, glowing in the source instrument's colour. | N | M | fljb/fact-check.md:96 (Record CC 22, on release) |
| Kit → FPC export | Writes an FPC .fst with GM mapping and envelopes | N | M | splice-and-sounds.md:34-35 |

### Pillar 7: FL Round-Trip, natively, both ways

**Purpose:** "If arturia refuses to build actually useful FL studio integration, we will build it ourselves." What you craft arrives in FL as if FL had made it, and your existing FL work comes into the room.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| **`device_AuroraKeyLab.py`, our own FL controller script** | Puts the selected FL channel name on the LCD and the mixer-track colours on the pads (LED_SAFE). Encoders follow the focused plugin, and the ctx LEDs follow FL's beat indicator (`OnUpdateBeatIndicator`). Everything is forwarded to the hub. **Ships only after the JamProbe drill**, because FL 26.1.3 lists freezes when scripts call FL functions. | N | L | fljb/fl-scripting.md:28 (no custom script yet), :74 (#22368), :113 (JamProbe) |
| .fst / .flp event reader | A stdlib FLhd/FLdt parser. Shows each of the 9 mixer presets as a chain diagram: slot order, plugin names, levels, and which state blocks are present. | N | L | Piano 1.fst byte read (FLhd, FLdt, "FL Studio 25.2.5.531", "Fruity Wrapper"); 9 .fst in Mixer presets |
| FL preset → room ("there are preset files in FL for the mixer, we can make it easy to import and export, or just read and interact with natively") | Load any FL mixer preset live and play your guitar or piano chains outside FL | N | L | your words |
| Room → FL preset | "Send to FL" writes .fst into `Presets\Mixer presets\Aurora\`, carrying the exact VST3 state blob. Writing into FL is your call (Q7). | N | XL | arsenal/fl/vfx/README.md:6 ("Nothing here writes into FL or Documents.") |
| Channel presets round-trip | A hosted Kontakt or Serum sound becomes an FL channel preset with its state | N | L | The Channel presets folder exists |
| .flp census + finder | Catalogues **913 .flp files (about 231 not autosaves)**: tempo, key guess, plugins, chains, last opened. Query "every project using Gated Angy Pad". **It also mines song-form structure** for Pillar 8. | N | L | Projects recount, 2026-10-22 |
| Alongside-FL live bridge | The **"Arsenal band"** VFX Script plays on FL's clock into your instruments, KeyLab knob → Pattern. FL stays the master clock, since FL has no Link. Not yet run inside FL. | P | M | arsenal/fl/vfx/README.md:1,3; fljb/fl-scripting.md:16 |
| Drag-out stems/MIDI/.fst | A drag handle on every bounce, kit and pattern. MIDI uses integer notes and GM roles, so FL's C5 naming quirk never bites. | P | S | splice-and-sounds.md:18 |
| FLP diff / template kit | A template skeleton plus "what Simon changed": slots, presets and tempo, read natively from both files | N | L | The parser makes this cheap |

### Pillar 8: Memory and Showcase. Takes, library, content, sharing

**Purpose:** "this research is important and will help our efforts of making engaging content". A good moment is never lost. Everything you make or own can be browsed, looks beautiful and is honest about where it came from. Any session can become a gift or a post.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Retro-record | A rolling 60 s buffer of audio and MIDI. Press Record after a happy accident and the LCD says "kept 0:47". | N | M | new |
| Take ledger with lineage | take.json + an append-only events.jsonl: instrument state, chain, kit, macro moves, seed. Re-render a take at higher quality or reopen it as a live sound. | P | M | arsenal/take.py:1-6 |
| REC button = take | Starts the take and the page recording. Hints and diagnostics go silent and the lean stays off. Stop offers "make a short?". | P | M | take.py; dce896:59-61 |
| Bounce with QC receipt | WAV + LUFS, true peak and silence spans. Two-pass loudnorm in one click. | P | S | arsenal/media/audio.py:1-15 |
| Performance video takes | The canvas, the KeyLab mirror and room audio, as a CFR H.264 MP4 | P | M | piano/recorder.js:1-25 |
| **Session capture into arsenal/media** | Twin + page + optional camera + audio → catalog → contact sheet → First Light Edit, with per-platform presets | P | M | media-toolkit-vision-2026-10-11.md |
| Shorts with hardware in frame | 1080x1920: the /piano canvas over a shot of the real KeyLab, synced on the first note | P | M | arsenal/tiktok.py:1-6 |
| **KeyLab atoms in present** | `present.scene.v1` gains a keylab atom kind, so a deck like "how the KeyLab learned to name chords" builds itself from receipts | N | M | presentation-primitive-family.md |
| Stream overlay mode | The LCD shows song, chord and BPM, with a matching page overlay for streams. The lens entry for this arrived truncated, so its scope beyond that is not specified. | N | M | lens 2 P7 |
| Showcase attract mode | Pre-made shows (Violet & rose, Golden wings, patch-bay), never blank. **It walks its own menus** while the VFX encoders animate on screen. Any key wakes the chord card. | N | M | second-press-principle.md |
| Audio → MIDI + stems | UVR on the 9070 XT via DirectML, plus Transkun notes (0.91 F1 on your playing). Results load into the sampler. | P | L | media-toolkit-vision-2026-10-11.md |
| Library cards | Fingerprint art, BPM, key, your mood words, lineage ("from Piano 1.fst + OTT") and a small as-of/confidence stamp | N | L | media-suite-project-2026-09-13.md:369,378-382 |
| Audition in time and key | Your own sounds are stretched to the current BPM (from FL or beatsync) and pitched to the key, the way Splice Bridge does it | P | M | splice-and-sounds.md:83-93 |
| **Splice-ify your own sounds** ("how to 'Splice-ify' sound chains and buildups / structure") | Splice's core loop applied to your library: search by key, BPM and mood, **preview in your project's key and tempo**, drag into FL | N | M | splice-and-sounds.md:83-93 |
| Browse from the KeyLab | The second press is a question. First the category and its count, then a preview of the top pick, then a short list. ctx buttons filter, and the LEDs tint by category. | N | M | second-press-principle.md:11,13 |
| Buildups and risers catalog | A buildup is a 4, 8 or 16-bar unit: a sound plus automation curves (filter sweep, riser, snare-roll density) with an **energy-curve thumbnail**. Previewed at tempo and landed on a bar line. | N | M | arsenal/fl/vfx bar-line rule |
| **Structure cards** | Song-form skeletons (intro 8 / build 16 / drop 16) **mined from your own .flp playlists**, your own forms first. Each card shows section blocks and the energy curve, and drags out as patterns + automation clips. On the KeyLab, pads launch sections, a fader rides the build's automation live, and the pads shimmer toward the drop and land on the bar line. | N | L | Pillar 7 census |
| Licence and provenance guard | Every card carries its source class. Refusals come with one-line reasons: no raw Splice redistribution, no Splice audio in AI training. "No embeddings" is the research doc's own implication, not Splice's wording. | N | S | splice-and-sounds.md:68-76 |
| Splice shopping list | Claude writes "find these", you download in the Splice app, and Documents\Splice is indexed automatically. Splice has no API, and its terms ban automation. | N | S | splice-and-sounds.md:13 |
| Chain packs | A .aurora-chain bundle: JSON + .fst + plugin versions + a fallback chain of stock/free plugins + a 10 s preview + card art | N | L | archero-style-game-vision.md:11-16 |
| Discord drop, outbound first | You name the channel and confirm each send. Inbound packs land on a quarantine shelf, previewed and never auto-loaded as plugins. | P | M | scripts/inbound_media.py |
| Agent co-designers, blind | Seats propose chains and buildups for a brief as unlabelled cards. You audition on the pads and pick live, and authorship is revealed afterwards. | N | M | media-suite-project-2026-09-13.md:241,269 |
| Sound-design episode recorder | One command records canvas, chain and mirror. Macro callouts appear only in rests, one at a time. Exports through the arsenal/media presets. | P | M | dce896:59-60 |

### Pillar 9: The Door. Agents, attention and media

**Purpose:** agents can play the instrument through a governed door, never by holding the port. The house can ask for your attention at the right moment and in the right way. Your photos reach the house in one hop.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| **arsenal-keylab MCP door** | `keylab_state`, `keylab_show(text, colour)`, `keylab_pads(frame)`, `keylab_popup`, `keylab_menu(tree)`, `keylab_listen(events, secs)`, `keylab_palette(id)`. Every answer carries `blind` (for example "cannot see whether DAW mode is physically on") and a `receipt` path. Registering it is your call (Q10). | N | M | arsenal/media MCP door shape |
| **New CLI verbs** ("make verbs for interfacing with the keylab and triggering midi and colors") | `keylab state`, `keylab facts` (pinned constants with as-of dates), `keylab learn-map`, `keylab palette <name>`, `keylab snap` (a picture of the current state for a contact sheet) | P | S | __main__.py verbs today |
| **Attributed agent touch** | The holder's callsign colour edges the grid, and LCD line 2 reads "Vandor" or "Asta" | N | S | fleet-callsigns.md |
| **Physical HALT + time-boxed grants** | Long-press Back to reclaim every surface; a popup says "yours again". The ladder is INFORM (LCD whisper), STEER (pads), INTERRUPT (popup), HALT (you). Agent leases are time-boxed. | N | S | bifrost-fidelity-ladder.md; security-schema.md |
| **Attention verb** ("if you have something that requres my attention at a specific point in time i can acknowledge it and select an option or click to launch") | `py agent_cli.py attention --at 21:30 --ask "Commit arsenal/keylab?" --option yes --option later --launch /piano`. It surfaces at that time on the console, on Discord, and as an LCD popup with the options on the ctx soft keys. One pad breathes, and the reminder escalates gently by second-press rules if ignored. The answer is recorded with the asker. core/comm/ask.py asks a model, not the operator, so this is new. | N | M | second-press-principle.md |
| **Click-to-launch options** | An option can be a URL (`/first-light?preset=violet-rose`), a verb or an FL project, opened from Discord, the console or a KeyLab soft key | N | S | attention verb |
| **REC and rest guard** | Attention requests queue while FL or the piano is recording and land in the next rest | N | S | dce896:59 |
| **Discord pump survives 429** | A drill with a dated receipt. This is open in the wake ladder. | N | S | MEMORY.md, wake-ladder entry |
| **Wake message carries the media path** ("how can the wake message also give you a direct link to the media file so you can just ingest it immediately") | The wake text carries each attachment's local path, which retires the "latest created file" crutch. Keep W165's collision-safe names. | P | S | scripts/inbound_media.py; WISHLIST.md:1144 (W165) |
| **Photo → palette → keyboard** | You send a photo on Discord. Within seconds it is a named look on the pads, LCD and pages, snapped to LED_SAFE. The reverse direction is `keylab snap` → an arsenal/media contact sheet. | N | M | inbound_media.py |

### Pillar 10: Trust. Receipts, budgets, failure, provenance, backup

**Purpose:** every claim about the KeyLab has a dated receipt you can find. Every limit sits on one visible card. Every failure has a designed response. Every dependency is licence-clean.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| **Pinned device facts** | A facts table in code (each fact with its as-of date and receipt) plus the `keylab facts` verb | N | S | the hardware facts table above |
| **pytest with a fake WinMM sink** | A property test that no mix of N producers ever goes over 12 packets per window, a lease-handoff test, **the CC64 sustain RED/GREEN pin**, and **a GRID pin** (chordview, the twin and the scene must agree) | N | S | chordview.py:109-110 (CC64); tests/ has no keylab tests today |
| **Drills with dated receipts** | FL coexistence. Freeze recovery: exceed the budget in bench mode, power-cycle, the hub detects the reconnect and replays via `resync()`. Server restart restores DAW mode and the frame. Pad-mode selector moved mid-session. Hub-death blackout. LCD 60 ms spacing. **Colour-latency camera drill:** 240 fps phone video with key and pad in frame, frames counted. | N | M | discord-fidelity-and-drill-doctrine.md |
| **Receipts are committed** | Small dated receipts go into a `state/drills/` negation in .gitignore, or into report atoms. A durable claim whose proof sits on a gitignored path cannot be checked. | N | S | lesson drill_receipts_live_on_a_gitignored_path |
| **Budget card on the twin** | Pads ≤ 12 per burst · LCD ≥ 60 ms apart · pad frames ≤ 15 fps · key → light: host leg measured, device leg about 10 ms (target is Q11) · audio p95 < 30 ms · page idle GPU = zero work · hub CPU/RAM watched against the 82-92 h window · beat engine + Carla together = P11 | N | S | kl-mem:16,19; media-suite-project-2026-09-13.md:49 |
| Session receipts + live overlay | Packets, max burst, coalesces, fps and lease history | N | S | — |
| **GPU idle guard** | The hub pushes deltas, and pages run no rAF loop for the pads. A bench in real Chrome asserts no GPU rise at idle. This **respects** W181/W182, which are parked at your instruction, and does not resolve them. | N | S | WISHLIST.md:1201,1203 |
| **Failure modes designed** | **Device freeze**: if keybed input stops while the hub is sending, the console and Discord say "power-cycle me". **Hub crash**: a watchdog blacks the pads out within 2 s rather than freezing them on a stale chord (Push's dead-man rule [ev]). **Selector moved off DAW**: detected if the pad notes differ by mode (P17) and said on the LCD and console. **FL repaints at init**: the coexistence switch. **USB replug**: wire `resync()` to H1 Rescan. **Half/double tempo**: the accuracy bench. **Loopback missing after reboot**: a named diagnostic. **Plugin licence lapses**: the slot shows the hole and offers the fallback chain. | N | M | ledframe.py:51; beatsync.py:11 |
| **Privacy rule** | Data about your playing stays only in gitignored private state. The public record holds method, architecture and rulings. | P | S | dce896 privacy paragraph |
| **Licence ledger** | **Verified:** beatsync imports aubio-ledfx, whose installed metadata says GPLv3+, inside the Apache-2.0 public repo (Q9). Carla, Pedalboard and PyFLP are GPL [ev] unverified, so run them out of process or reimplement. Bitwig and saxofonbrian are MIT: credit them in research/reviewed/, never as a headline. Arturia's script is a source of facts only and is never redistributed. UltimateChords: check the terms first. Shader Lab CC BY-NC-SA material stays out of tracked files. | P | S | beatsync.py:7,61; attribution-proportionality.md |
| **Backup split** | **Commit** the non-private device config: control map, pad layout, palettes, modes and facts. **Private backup with a restore drill**: takes, the chord timeline, kits, saved looks and macro maps, as a dated archive in a location you choose. Snapshot restore has no receipt, so it is presumed broken. | N | S | backup-and-recovery.md |

### Pillar 11: The Commons (gated, later)

**Purpose:** "can you imagine the workflows and collaboration?" Share what you make, and let any KeyLab owner have what you have. Your words, published understated. **Hosting and public voice are your gate.** It depends on the Pillar 7 parser, and nothing here is pulled into W0-W3.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| **FLP template site** ("a music collaboration site where users can upload flp templates") | Upload an .flp and a card appears with a stem preview, tempo, key, plugin list and chain diagram. Uploads are quarantined and plugins are never auto-loaded. | N | XL | Pillar 7 parser |
| **DAW conversion kit** ("download a project file in their preferred daw like ableton or reason") | "Download as": FL .flp / Ableton .als (gzip XML with audio and MIDI clips and stock devices) / DAWproject / **Universal** (per-channel stems, integer-note MIDI per channel, tempo map, markers, a chain recipe card). Which DAWs read DAWproject, and Reason's format, are unverified (P22). | N | XL | — |
| **Plugin translation table** | FL stock → the nearest stock device. Third-party VST3 → its state blob if the recipient owns the plugin, otherwise a rendered stem. Splice samples → a "find these" list, never the raw files. Includes the provenance guard and the "what Simon changed" diff. | N | L | splice-and-sounds.md:68-76 |
| **Alpha kit for any KeyLab mk3 owner** | One-click install, the learn-map wizard on the LCD, a gallery of modes and palettes, and "connect your own assistant" through the MCP door. Arturia's script is a facts source only. | N | L | lens 1 ("free alpha for any MIDI keyboard") |
| **"The moat is the integration"** | Public text written from your words and kept understated. "Trust the gates, not the author." | N | S | public-voice-calibration.md |

---

## 2. The spine: what makes it one thing

```
 pages (:8793 piano/FL/Play, :8787 /vfx, :8797 shaderlab) + CLIs + agents (MCP door)
   │ intents (pad frame / LCD lines / LED roles / attention)   ▲ SSE "keylab": state +
   ▼                                                           │ named input events
 ┌──── KeyLab HUB (arsenal serve :8793) ─────────────────────────────┐
 │ leases per surface → keylab.scene.v1 layer stack                  │
 │ → shared palette (OKLCH → tone map → LED_SAFE → to7)              │
 │ → burst governor: pad lane ≤12/burst · LCD lane ≥60 ms            │
 │ → PadRenderer delta → paced writer → "KeyLab 88 mk3 DAW"          │
 │ input plane: "KeyLab 88 mk3 MIDI" → named events → map            │
 │ producers in-proc: beat engine, chord reader, now-playing         │
 │ watchdog: dead-man blackout · heartbeat · resync on replug        │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │ control map / transport / meters
 ┌──── ENGINE ROOM (supervised native, out of process) ──────────────┐
 │ Carla: live instruments (ASIO)  Pedalboard: chains live + offline │
 │ Python conducts, never renders   record bus · take ledger         │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │ FL INTEROP: FLhd/FLdt parser (.fst/.flp),
                                 │ device_AuroraKeyLab.py, Arsenal band VFX Script,
                                 │ coexistence switch, loopback port (SDK, your OK)
```

**Device owner service.** One Python KeyLab hub inside `arsenal serve` :8793 owns the DAW output. It is stdlib + ctypes WinMM, and beatsync's heavy dependencies load lazily. The code already shows that one owner is needed, even if Windows allows many:
- the freeze budget covers the whole device;
- chordview and beatsync each send `daw_connect(False)` on exit (chordview.py:130, beatsync.py:122);
- PadRenderer assumes it is the only writer (ledframe.py:1-11);
- FL's Arturia script also writes to the port;
- if the ports are multi-client, collisions are silent [ev] unverified.

The hub copies three patterns the house already has: CueHub fan-out (pianocue.py:191-304), the VFX renderer lease (bifrost_ui.py:224-285) and the cues.js tab arbiter (cues.js:1072-1210).

**Scene model.** `keylab.scene.v1` is a stack of layers (ambient/beat < page < practice < popup). Each layer is owned by a lease holder and composited per surface: pads, LCD and button LEDs. Only the delta is sent. Modes and menus are projections of the H9 one-world mode schema (d622ac §3-4, lines 90 and 108), under d622ac's §1 rule 1: "a surface is a projection, never a store" (line 67). Saved looks (/api/piano/looks) are the scene presets.

**Audio engine split.** Live instruments run in Carla (C++, ASIO, bridged plugins, about 3-12 ms). Effects run in Pedalboard (live AudioStream and offline, with one chain object). Python only conducts (kl-mem:23). Neither is installed today: pedalboard and sounddevice are missing from py 3.11, while numpy, aubio, pyaudiowpatch, soundfile and librosa are present.

**FL interop layer.** Four channels:
- **Files:** a stdlib FLhd/FLdt parser and writer.
- **Live:** the Arsenal band VFX Script + Patcher on FL's clock.
- **Script:** `device_AuroraKeyLab.py`, after the JamProbe drill.
- **Device:** the coexistence switch and the loopback port.

**Web UI integration.**
- **No page requests SysEx today.** piano.js:3803 and piano/cues.js:1697 pass `{sysex:false}`. first-light.js:768, play.js:2027 and piano-lab-score.js:299 call `requestMIDIAccess()` with no options, which also defaults to no SysEx. piano-next.js:1347, piano-lab-res.js:1519, piano-lab-vfx.js:1871, piano-lab-judge-head.js:1318, piano-lab-judge-res.js:1520, piano-crystal-studies.js:288 and piano/gyre-music.js:16 pass `sysex:false` as well.
- /vfx has no MIDI code at all (scripts/vfx.html, scripts/agent-avatar.js).
- Pages POST intents and listen on the cue SSE. /vfx reaches the hub through CORS limited to :8787, or through a bifrost_ui proxy.
- One shared palette module replaces the three CSS token vocabularies that disagree today. It carries its tone mapper with it (arc-piano-studies.md:468-469).

**Agent door.** Agents are producers like any page:
- `py -m arsenal.keylab <verb>` for the hardware;
- `map <producer> -> <target>` (T399 F4) for bindings;
- the intents route + the arsenal-keylab MCP door;
- variation proposals arrive unlabelled.

Agents never hold the port. You hold HALT.

---

## 3. Placement in the house

**What is in force:**
- **The plan:** the Estate Program (docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md). Its A12 THE FACE is "the Bifrost UI, the founder's first love" (:79).
- **Your appetite ranking:** A8 > A1 > A3 > A12 > A5 (ruling 375c23:10,33). A12 is #4.
- **The width cap:** one build watch + one design watch, never two builds. A third active round needs `pauses:` or your recorded word (docs/ORG.md:9-12,154-156), reaffirmed by ruling 369243:38-42.
- **The running-order rule:** at about 4 or more live threads, publish now / next / after unprompted (memory sequence-visibly-when-threads-multiply.md:18).

**Proposed home (our proposal, not existing structure):**
- New tracks in the **media-suite** arc, through a successor map to fa48f2 (that map's arc is media-suite).
- No house document puts media-suite under A12 today. Whether KeyLab Lit counts toward A12 "THE FACE" is your call (Q2).
- Not a new arc unless you say so; a new arc needs the fence ceremony.

**Track names (Q3):**
- **K "KeyLab Lit"** = pillars 1-4 + 9 + 10.
- **R "The Engine Room"** = pillars 5-8.
- **C "The Commons"** = pillar 11, gated.
- Or one umbrella, **"The Lit Console"**.

**What it absorbs or feeds**

| Existing arc / organ | Relationship | Cite |
|---|---|---|
| Piano VFX (arsenal/web/piano) | Feeds the device: noteColor, harmony-feel, lean, cadence-live, moonlight co-performer, the twin | piano.js:326-398,537-595; keylab88mk3.js |
| Now Playing S3 / S5 | Absorbed into the Light Language. NP S4 "Ears" is replaced by the beat engine. | 1328e1:108-111,177-180,186-191 |
| Presentation grammar (LED wall, spells) | Feeds the LED-wall treatment and the musical spells | 236d39:107-145,157 |
| H9 one-world modes + floor | Menus and modes project it | d622ac:67,90,108 |
| T399 contract F4 `map` | The binding mechanism | fences/media-arsenal-contract/reconciliation.md:90-101 |
| Story layer rulings | Bind every LCD callout: one at a time, in rests; feelings first; no grades; the canvas stays yours | dce896:52-62 |
| Media toolkit (arsenal/media) | Feeds bounce QC, loudness, exports, shorts, session capture | media-toolkit-vision-2026-10-11.md |
| Presentation primitives (arsenal/present) | Feeds showcase scenes, the tour episode, KeyLab atoms | presentation-primitive-family.md |
| Shader school | Its pending "shared colour templates" are delivered as the palette module | shader-school-2026-10-13.md:11-15,79 |
| FL jam bridge (research + arsenal/fl/vfx) | Absorbed into pillars 6-7 | fljb/* |
| Second-press principle | Its first full application: menus, browse, what-does-this-do, unbound hints, attention escalation | second-press-principle.md |
| Forest Walks | The KeyLab becomes a walk subject | forest-walks-practice.md |
| Archero game vision | Fed later by the light-games layer | archero-style-game-vision.md |

**Existing wishes:**
- **Resolves:** W247 (note truth, WISHLIST.md:1584) and W248 (melody-deaf log, :1608).
- **Respects, does not resolve:** W181/W182 (Bifrost UI resolution and GPU idle, both parked, :1201,1203).
- **Related:** W165 (inbound-media name collisions, :1144).
- **Dropped from pass 1:** W228 (a subprocess decode bug, not .flp) and W58 (an aurora canvas bug, not a palette).
- The WISHLIST has zero hits for keylab, arturia, vfx, sampler, vst, controller, colour or color. Filing today's asks is step zero.

---

## 4. Build sequence

Each wave ends in something you can play. UI waves run fast, judged by what you can see. Nothing starts before your "that's right" on the brief.

| Wave | Contents | You can play with |
|---|---|---|
| **W0 Land and census** (S) | **Licence call on aubio (Q9)**, then commit arsenal/keylab by named paths (your approval). Report atom + pinned facts + pytest pins (CC64, GRID, the burst property). Brief + wishes + successor map + published running order. Twin re-laid to 9-5-1. Warm-to-white fix in chordview. LED-gamut photo. Stability ladder receipt. ledbench LCD line. learn-map / Atlas v0. **Probes P1, P2, P4, P5, P13, P14, P17.** | chordview with honest colours on the real grid; the twin filling in as you touch each control; "RATE L3 · 20 Hz" on the LCD |
| **W1 The Hub** (M) | Hub in serve :8793: governor, layer stack, `keylab.scene.v1`, intents, `keylab` SSE kind, input plane, leases, producers as clients, FL coexistence switch, dead-man + heartbeat, diagnostics with personality. **Probe P3.** | /piano lighting the pads while the beat march runs underneath, with no DAW-mode drops on exit |
| **W2 The Light Language** (M-L) | Palette module + LED_SAFE + LED-true preview, noteColor bench, six schemes, shape dictionary, chord families, living edges, chord card, Now Playing card, beat engine, BPM seed-and-refine v0, march patterns, three timescales, LED-wall, shimmer, attract mode | Spotify plays, the pads march, and the LCD shows song, chord and BPM in album colours |
| **W3 The Controller + the Door** (M) | CORS bridge, `map`, First Light/Play/VFX strip bound, soft takeover, scene pads, menus v1 on the native list widget, legend node, modes, unbound hints, what-does-this-do, Shader Lab preview, **attention verb + wake media path**, MCP door (registration is your call), HALT, tour episode + cheat card. **Today's "tie in our UI work" ask lands here.** | Faders playing the VFX avatar live; menus on the LCD; an attention popup you answer with a soft key |
| **W4 Engine Room core** (XL) | **First probes P6 and P7** (the Carla download needs your OK). Then supervisor, latency receipt, panic, crash shell, memory guard, instrument rack, macro map with native popups, snapshots/morph, mixer strip, preset browser. | Press a key and hear Kontakt with FL closed, with the latency p95 beside it |
| **W5 FL round-trip** (L-XL) | **First probe P8.** Reader → chain diagram, import, a write-load-readback drill (RED first), export, channel presets, .flp census including structure mining, drag-out. JamProbe drill → `device_AuroraKeyLab.py`. | Open "Piano 1.fst" in the room, play through it, send an edit back to FL; the LCD naming FL's selected channel |
| **W6 Sampler + Chain Bench + Pad Desk** (L) | Pedalboard runner (pip with your OK), chain diagram, chain on the KeyLab, blind A/B, slot budgets, parallel lanes. Pad Desk, swatch picker, velocity curves, ADSR handles, Pad Learn, AD2 kit map (loopback SDK with your OK), pad-mode awareness, fill pads, chord pads, resample, FPC export, spectrum meter. | Drop a WAV on a pad and watch it light; pad 9 = D#3 by gesture; AD2's kick on the pad you chose |
| **W7 Memory, timeline, content** (L) | Retro-record, take lineage, REC = take, bounce QC, session capture, library + KeyLab browse, Splice-ify, buildups, structure cards, licence guard, heard-song timeline, bar grid, position lock, sheet import, look-ahead, BPM accuracy bench, games, cadence moments, duet lights, shorts, KeyLab atoms in present, chain packs, Discord drop, blind co-designers, episode recorder | "kept 0:47"; a next-chord glow on a song you love; a short with the real KeyLab in frame |
| **W8 The Commons** (gated) | FLP site, conversion kit, plugin translation, alpha kit, public text. Starts only after the W5 parser and your hosting and voice gate. | A friend downloads your template as .als |

**Running order (published now, per the house rule):**
- **Now:** W0 land + W1 hub.
- **Next:** W2-W3, menus and colour on /piano and /vfx.
- **After:** the attention verb (in W3), the chord timeline, the content kit.

New ideas join this queue in your order, and none get dropped. `pauses:` none while K is the build watch and R runs probes only as the design watch. Any third thread names what it pauses or waits for your word (ORG.md:9-12,154).

---

## 5. Ratification questions

1. **Land it now?** Commit `arsenal/keylab/` by named paths today (after Q9), **or** after the W0 bench settles the pad layout and the colours.
2. **Placement:** K and R tracks in media-suite through a successor map to fa48f2, counted toward **A12** (your #4), **or** kept in media-suite only, **or** a new arc (A16, with the fence ceremony) for the Engine Room.
3. **Name:** "KeyLab Lit" + "The Engine Room" (+ "The Commons"), **or** one umbrella, "The Lit Console", **or** your own name.
4. **Order:** light-first (W1-W3 answer "tie in our UI work"), **or** sound-first (W4 probes start in parallel as the design watch).
5. **FL default:** when FL is open, "FL drives" (the hub yields automatically), **or** "Aurora drives" (FL's Arturia script is turned off), **or**, after W5, our own `device_AuroraKeyLab.py` replaces Arturia's.
6. **Hub home:** inside `arsenal serve` :8793 (one process, shares the cue hub), **or** its own daemon that survives page-server restarts.
7. **Touches outside the repo:** the Carla download, the `pedalboard` + `sounddevice` pip installs, the Windows MIDI Services SDK (loopback), and one `Presets\Mixer presets\Aurora\` folder in FL. Yes to each, **or** export to a drop folder you drag in by hand.
8. **Palette canon:** which vocabulary is the root of the shared module, all of them inside LED_SAFE: piano's OKLCH noteColor, the patch-bay identity, or the Aurora Void theme.
9. **aubio-ledfx (GPLv3+) in the Apache-2.0 repo:** keep it as an optional runtime dependency and say so, **or** run the beat engine out of process, **or** replace it with a permissive detector.
10. **MCP door:** register arsenal-keylab for agents, **or** keep it CLI-only for now.
11. **Key → light target:** what p95 from key press to pad light feels instant to you (the device leg alone is about 10 ms)?
12. **"the manual bund method":** did you mean writing pads into the KeyLab's own stored programs (so it works with Aurora closed), **or** something else?
13. **The Commons:** public hosting and voice. Not now, **or** a private alpha with Simon first.

## 6. Open probes

| # | Unknown | Cheapest test |
|---|---|---|
| P1 | Can FL's Arturia script and the hub share the DAW port, or do they silently clobber each other? kl-mem:18 says one process; Windows MIDI Services docs say multi-client [ev]. | With FL open, the hub sends one pad colour. Watch whether FL overwrites it within 1 s and whether either side errors. Dated receipt. |
| P2 | DAW-mode control map (CC numbers, relative vs absolute encoders, ctx buttons) | `py -m arsenal.keylab monitor`, touching each control once (the W0 census) |
| P3 | Web MIDI SysEx direct vs the hub | Time 100 intents POST → WinMM send (target < 16.7 ms p95). Compare one page using `sysex:true`. Expectation: the hub wins on safety alone. |
| P4 | 7-bit levels and the **LED-safe gamut** | Ramp R, G, B and the warm hues 0..127 in steps of 4 on one pad and photograph each. Count the distinct levels and mark where colours wash to white. Output: `LED_SAFE`. |
| P5 | LED first byte: 0x04 (Bitwig's) vs our confirmed 0x00 [ev] | Send the same colour both ways to one pad and compare |
| P6 | Carla latency on your Focusrite | After the download, load Mini V4 bridged at buffer 64/128/256. Loop a click from out to in and measure the p95. |
| P7 | Is Focusrite ASIO single-client while FL holds it? | Start Carla with FL playing and note which side loses audio |
| P8 | Is .fst plugin state the exact VST3 state? Does FL accept a file we wrote? | Null round-trip of Piano 1.fst, byte-identical, then load it in FL. Change one level and compare the Fruity Wrapper chunk with Carla's saved state. |
| P9 | LCD grammar beyond popups and F2L (per-line colour, field tags) | Lift the tags from KL3Display in Arturia's FL script and try each once |
| P10 | Kontakt 8 in Carla bridged mode | One small library for 30 s, then a large one, recording RAM and load time |
| P11 | Beat engine CPU while the Engine Room runs | 10 min of beatsync + Carla together, watching for dropouts and CPU |
| P12 | SMTC album art for palette bleed | Read the thumbnail once for the current Spotify track |
| P13 | Does the firmware honour BlinkState (BLINK1-3, PULSING)? [ev] | Send each state once to one button LED and one pad |
| P14 | Must LCD packets be ≥ 60 ms apart, or one is dropped? [ev] | Send F2L updates at 20/40/60/80 ms spacing and count the visible updates |
| P15 | Native knob (0x1C) and fader (0x1E) popups [ev] | Send each once with a name and a value |
| P16 | Native LCD list widget (title 0x28, items 0x15, cursor) [ev] | Render a 5-item list and scroll it |
| P17 | Do pad notes differ by selector position (Program / DAW / Default)? | Monitor a pad hit in each position |
| P18 | Can pad notes be written into an Arturia user program (the MCC way)? | Read one user program, change one pad note, read it back |
| P19 | Can SMTC give the timeline position for Spotify? | Read the position twice, 5 s apart, during playback and after a seek |
| P20 | Which tempo databases can be queried for a track's starting BPM? | List the candidates, query 10 known songs, compare against tap tempo |
| P21 | Key → light latency on the hardware leg | A 240 fps phone video with key and pad in frame, frames counted, dated receipt |
| P22 | Which DAWs read DAWproject? What is Reason's project format? | A documentation check, then one export opened in a trial DAW |
| P23 | Does FL 26.1.3 freeze when our script calls FL functions? | The 30-line `device_JamProbe.py` drill (fl-scripting.md:113), with you present |

### Evidence notes
- **Verified first-hand in this pass:**
  - chordview.py: GRID, BORDER, colours, root white, CC64, daw_connect;
  - protocol.py:83-85 and :106, and the PAD_NOTE geometry;
  - __main__.py ledbench (:340-365) and the monitor verb (:273, :469);
  - keylab88mk3.js:34,63,519,672;
  - pianocue.py:65,229-230;
  - beatsync's aubio import, plus the installed aubio-ledfx metadata (GPLv3+);
  - the Piano 1.fst bytes;
  - fl-scripting.md:28,74,113, splice-and-sounds.md:16-18, virtual-midi-and-sync.md:12-24, fl-jam-bridge-plan.md:230;
  - INTERIORITY.md:29 and :236-238, 236d39:120, and kl-mem:11-25.
- All other citations carry the fact-check pass's verdicts and its corrected lines.
- Everything tagged [ev] is a web or prior-art claim this pass did not re-verify.
- The prior-art protocol references are the Bitwig KeyLab mk3 extension (MIT, updated 2026-10-21) and saxofonbrian/keylab-mk3-sysex (MIT). Credit both in research/reviewed/, never on this page's headline.
