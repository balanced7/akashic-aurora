# Full-vision fan-out pass 1 (5 evidence lanes, 3 lenses, synthesis)

> Provenance: Claude Code workflow `wlao8eoim`, run 2026-10-22 by claude (Vandor) for Daniel, reviewed by claude before filing.
> Raw per-lane results: `keylab-vision-pass1-2026-10-22.raw.json` in this folder. Status: research record, not a ruling.

# KeyLab Lit: The Complete Vision
*KeyLab 88 mk3 + sound-craft room + VFX, one instrument. Draft for Daniel to ratify, 2026-10-22.*

## North star

You own a studio's worth of sound: Kontakt 8, Serum 2, Analog Lab V, Addictive Drums 2, 2,687 stock FL WAVs, 81 Splice WAVs and 913 .flp projects (research/in-flight/fl-jam-bridge-2026-09-14/local-inventory.md:21-22,129-165; Projects folder counted read-only 2026-10-22). As of this morning you also own a keyboard the house can light and label: it named your chords live today (C:/Users/L5/.claude/memory/keylab-mk3-liberation-2026-10-22.md:11-21). This vision makes those one thing.

- **The KeyLab is the hands and the second screen.** Its pads, LCD and LEDs speak for every page you love: piano, First Light, Play, the VFX Bench. Its faders, encoders and buttons reach back into those pages "like changing dials in a game engine" (charters/daniel/INTERIORITY.md:117-119).
- **A low-latency native room** hosts your instruments and effect chains. It works on its own and alongside FL, and reads and writes FL's own preset files.
- **Everything shares one colour language** that adapts over seconds, never strobes, and treats the quiet state as a full composition (arsenal/SPECTACLE-DESIGN.md:3-6).

It matters to you for three reasons. It is your oldest want, beautiful live surfaces (project-origin-simon.md:17-25). It runs on your favourite pattern, "the second press is a question", which was born from a KeyLab reconnect (second-press-principle.md:11-20). And every session becomes something you can play, keep, give to Simon, and post.

The hardest part is already on disk. `arsenal/keylab/` holds the SysEx protocol confirmed on the hardware, a renderer that only resends pads that changed, five chord pad schemes, and beat sync from loopback audio. It is **untracked** (`git status`: `?? arsenal/keylab/`). It is in no atom, task or wish yet.

---

## 1. The pillars

Status: **B** = built · **P** = partly built · **N** = new. Size: S / M / L / XL.

### Pillar 1: The Hub. One owner of the light

**Purpose:** one process owns the device. It composites what every page wants and hands surfaces to whatever you are looking at. It never breaks the device's limits. Everything visible depends on this.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Land arsenal/keylab with a receipt | Commit by named paths. Add a report atom of the measured limits. Turn the inline selftests into pytest pins. | P | S | git status; memory:9 "Nothing committed yet" |
| KeyLab hub in `arsenal serve` :8793 | One MidiOut on "KeyLab 88 mk3 DAW". A paced writer thread wrapping PadRenderer. One device-wide budget of 12 packets per burst. Priority: popup > page > ambient. Automatic `resync()` after a foreign write. Clean shutdown next to `app.cues.close()`. | N | M | chordview.py:120-125, beatsync.py:118-123 (each drops DAW mode on exit); ledframe.py:1-45; serve.py:156-178,788-805 |
| Layer stack + intents API | Pages and CLIs POST intents, never raw bytes: a pad frame, LCD lines with per-line colour, button-LED roles, an attention flash. Compositing order: ambient/beat < page < practice overlay < popup. Only the delta is sent. | N | M | pianocue.py:1-20,190-310; d622ac §3 "a surface is a projection, never a store" |
| `keylab` SSE event kind | Hub state goes out on the cue SSE, so the on-screen twin and the device always agree. EVENT_KINDS is a closed tuple, so this is a deliberate extension. | N | S | pianocue.py EVENT_KINDS |
| Foreground leases per surface | Pads, LCD and button LEDs are leased separately. The visible tab beats a hidden one. Leases renew by polling and expire after 6 s. Closing a tab returns the surface to the ambient layer. A small LCD stub says who holds the light, then dims after 2 s. | N | M | bifrost_ui.py:224-285; cues.js:1063-1200 arbiter |
| Cross-origin bridge for /vfx | CORS + OPTIONS on `/api/keylab/*` for 127.0.0.1:8787 only, or a server-side proxy inside bifrost_ui. | N | S | serve.py:245-249,592-594 (no CORS anywhere today) |
| FL coexistence switch | A visible LCD mode: "FL drives" (the hub yields the port) or "Aurora drives". The house never fights FL silently. | N | M | protocol.py comment on FL's script; fact-check.md:143 |
| Control census | A guided capture. The LCD prompts "turn encoder 3" and the hub records CC, relative/absolute encoding and channel, in DAW and user mode, into a tracked control map. The 3D twin lights each control as it is captured. | P | S | __main__.py:280 monitor verb; keylab88mk3.js:9,41-45 |
| One pad-layout truth | One shared pad table, checked on the real unit, used by protocol.py, chordview and keylab88mk3.js. | N | S | Three layouts disagree: protocol.py:83-85 (MPC map), chordview.py:16,29-30 (3x4), keylab88mk3.js:34,520-525 (2x6) |
| Diagnostics with personality | Short LCD lines that retire once evidence clears them: "DAW mode? Prog + 6th btn", "FL has the light", "There it is". | N | S | second-press-principle.md:41-46 |
| Memory and uptime guard | The hub and the engine report commit and private bytes, give a gentle hint near the 82-92 h low-memory window, and refuse a 6 GB library without headroom, saying why. | N | S | ram-freeze-2026-09-24-fanout-on-day-four.md:11-13 |

### Pillar 2: The Light Language. Pads, LCD and colour that teaches

**Purpose:** 12 RGB pads, 34 button LEDs and the LCD become one readable harmonic alphabet. The colour is shared with every page, and it fits inside 7-bit colour and the burst ceiling.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Shared palette module with tone mapper | One pipeline: token → OKLCH → tone-map → sRGB → to7. Change a look on First Light and the KeyLab and piano change with it. Saved looks (Violet & rose, wide violet, Golden wings) become KeyLab presets. | N | L | shader-school-2026-10-13.md:11-16,79; arc-piano-studies.md:468 |
| noteColor on the hardware | Piano's OKLCH circle-of-fifths colours (hue 200 + 30 × fifths index, brightness evened across hues), converted linear → sRGB → 7-bit. A bench page shows each swatch next to a phone photo of the real pad. | P | M | piano.js:321-410; protocol.py:106 |
| Schema picker | ROLES / NOTES / QUALITY / SPLIT / FRAME, chosen from an LCD menu. The root is always white. The legend shows on first use, and afterwards only on a second press. | P | S | chordview.py:34-64 |
| Chord families as colour families | maj7 violet-rose, dom7 amber, m7 teal, half-dim dusk blue. Triads take a lighter tint, extensions a bright edge pad, altered tones a rose rim. Families come from harmony-feel measures, not suffix strings. | N | M | harmony-feel.js:160-180; your words "7ths make a chord be one color" |
| Living edges | In FRAME, the 8 border pads carry harmonic motion. Colour travels round the border over about 0.4 s, at most 8 packets, and the direction of travel shows the move up or down the fifths. | N | M | SPECTACLE-DESIGN.md:83-86; "the edges change color" |
| The lean on the pads | A leading tone's pad breathes toward its target's colour. Text-free, and off in recordings unless you turn it on. | P | S | piano/lean.js:1-7; dce896:54-62 |
| Note truth | One note is named as a note, two as an interval, three or more as a chord. There is one chord reader (page reader or the pianocue_voicing bridge), never a second namer. | N | S | W247 WISHLIST.md:1584; theory.py:1 "not a jazz oracle" |
| Live chord card (LCD) | A persistent F2L screen. Line 1 is the chord in its family colour; line 2 is the key, Nashville number and bass in the key's hue. Dims to 46% when idle. ASCII # and b (the page twin keeps Noto Music). | P | S | keylab88mk3.js:753-813 |
| Now Playing card | Title and artist scroll gently. BPM and key on line 2. The LCD and ambient pads take the album palette. | P | M | beatsync.py:5,26,106; 1328e1 S3 |
| Colour on three timescales | The palette drifts over minutes, the harmony family over seconds, beat brightness in under a second. No strobing. Loud means more momentum, not more white. | N | M | 1328e1:108-111,177-191; SPECTACLE-DESIGN.md:83-86,133-135 |
| Cleverer than the hardware | Most salient pad first (the root lands first). A dirty-pad queue shares the budget between layers. Brightness envelopes only on pads that matter. Button LEDs as extra pixels (ctx1-8 as beat bar or menu cursor, Hold following the pedal, Chord in the root colour). LCD colour as a 13th ambient light. Pre-snap to colours the LEDs render well. Temporal dither inside the budget. | P | M | keylab88mk3.js:578-745; protocol.py:48-57; README:55-59 |
| Pads as spectrum meter | An idle mode showing 12 bands of the room's output, warm lows and cool highs, at 15 fps, sending only changed pads. Soft passages keep their focal glow. | N | M | SPECTACLE-DESIGN.md:83-86 |

### Pillar 3: Beat, Time and the Chord Timeline

**Purpose:** the light locks to the pulse from Spotify, FL or your own hands. The house builds its own database of chord changes against time, so the pads can show what is coming, not only what is sounding.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Beat engine as hub producer | beatsync (WASAPI loopback + aubio) runs on a thread inside the hub instead of opening the port itself. It publishes beat, bar, BPM and confidence to the hub and the SSE. One clock for all. This replaces the duplicate NP S4 "Ears" plan. | P | M | beatsync.py:9-11,118-123 |
| March patterns | March round the frame, bar fill, downbeat bloom, ping-pong, chord pulse, off-beat sparkle. At most 4 changed pads per beat. ctx LEDs show the bar position; the Metronome LED marks the downbeat. | P | M | beatsync.py:58 cycle mode |
| Tap and hold tempo | Tap sets or corrects the tempo and its LED blinks on the beat. Hold shows BPM and confidence. Drives the jam tempomap, so Claude's groove plays in time. | N | S | protocol.py BUTTONS tap:4; jam/tempomap.py; piano/groove.js |
| FL transport mirror | Play, Stop, Rec and Metro LEDs mirror FL when FL drives, and start or stop the jam or take when Aurora drives. | N | M | protocol.py:48-57 |
| Heard-song timeline | During loopback, beat-stamped chord and key estimates go into state/ (gitignored), keyed by SMTC title. A second listen refines them, and a quiet as-of/confidence stamp shows it. | N | L | media-suite-project-2026-09-13.md:369,378-382; story-layer-arc-2026-10-12.md:28-29 |
| Chord sheet import, clean-room | You paste a sheet you are entitled to use. Only chord tokens and section labels are parsed and aligned by beat. No scraping, no lyrics stored. | N | M | UltimateChords inspiration; shader-school-2026-10-13.md:18-20 |
| Look-ahead on the pads | The next chord's pads glow at 20% half a beat early and land at full on the change. "next: Am7" appears in rests only. | N | M | story-layer-arc:11-12; dce896:54-62 |
| Your playing as timeline | roll/1 sessions replay on the pads and the twin together. Feelings first; no counts or grades in tracked files. | P | M | performance.py, roll.py; W248 WISHLIST.md:1608 |

### Pillar 4: The Controller and Teacher. Dials, menus, scenes, games

**Purpose:** every continuous control plays the VFX pages live. The menus show that a path exists. The instrument teaches you how to use it.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| `map <control> -> <parameter>` | The T399 F4 gesture. Hold a page parameter and turn a knob, or choose it from the LCD. The LCD confirms "ENC 3 -> pulse" in the parameter's colour. Saved per page and per mode. First Light's CC-learn becomes the shared path (no more per-page localStorage). | P | M | reconciliation.md:90-101; first-light.js:764-830; play.js:2023-2050 |
| VFX Bench strip layout | Faders 1-9 control sub, gap, thick, cube, hole, spin, pulse, sat and dim. Encoders 1-5 control round, star, wire, see and rate. The main encoder steps through the 9 avatar states, and each state's tint lights the pads. Bank± switches identity palettes and compose chains. | N | M | agent-avatar.js:443-458,574-592; vfx.html:403-415 |
| Soft takeover | A faint arrow colour shows until the physical fader crosses the value set on screen, so nothing jumps. Relative encoders never need pickup. | N | S | VISUAL-QUALITY-BASELINE.md:8-19 |
| Pads as scene launchers | 12 saved looks, each in its own dominant colour. A tap crossfades over seconds, velocity sets the fade time, and a hold previews on the LCD. | N | M | /api/piano/looks; SPECTACLE-DESIGN.md:83-86 |
| Menus that show a path exists | Dim ctx LEDs mean "leads somewhere". The first press shows the name, the second a whisper hint, the third the full picture. Main encoder scrolls; Back steps back. Menus project the H9 one-world mode schema, so a mode picked on the KeyLab is picked on every page. | N | L | second-press-principle.md:11-20,37-45; d622ac §3-4 |
| Musical spells | Chord shapes trigger effects through the map verb: maj7 opens the bloom, a dom7 builds tension, resolving releases it. | N | M | 236d39:107-157 |
| Shader Lab preview | Shader name and palette on the LCD and pads, read-only. Live control stays off until its safety review clears. | N | S | arsenal/shaders/serve.py:1-59 |
| What-does-this-do mode | Hold Settings and touch a control: the LCD names it and its binding, and the twin highlights it. A second touch shows more. Unused controls whisper once per session. Never during REC. | N | M | second-press-principle.md |
| Scale and Chord lighting | Scale lights the scale degrees, with the tonic white. Chord shows the diatonic chords one per pad, coloured by family, and a tap previews it. | N | M | protocol.py:48-57; INTERIORITY.md:14-31 |
| Echo and follow games | Chord echo, follow the lean, rhythm catch. No score. A miss gets a softer hint, never a red light. | N | L | INTERIORITY.md:469; dce896:31-34 |
| Cadence moments | On V→I, deceptive or ii-V: one slow pad sweep and the cadence name in a rest, once. | P | S | cadence-live.js:17-28 |
| Agent co-performer on pads | Claude's notes light in a cooler second palette beside your warm notes, two visible voices. The LCD says whose phrase it is. | P | M | cues.js:1757-1772 |

### Pillar 5: The Engine Room. Low-latency host, instruments and chains

**Purpose:** one supervised native process plays your instruments and chains at playable latency. It works with no FL open, and a misbehaving plugin cannot take FL or the machine down with it.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Carla engine, Python conducts | Headless Carla on Focusrite ASIO loads any VST3 you own and plays it from the keys. Python loads, routes, sets parameters and saves state; it never renders audio. | N | XL | memory:23 (~3-12 ms; "pure-Python realtime VSTi is a trap") |
| Pedalboard chain runner | Stock effects plus your VST3 effects (OTT, Rev PLATE-140, Kilohearts, Trash, Smooth Operator Pro), live through AudioStream or offline. The same object renders the bounce, so live and offline sound identical. | N | L | memory:23; local-inventory.md:140 |
| Latency receipt, leg by leg | A quiet strip: press → engine → ASIO out in ms, buffer, sample rate, p95, and a declared line for the hardware leg. One loopback drill turns that declared line into a measured one. | P | M | latency.js:1-15; target p95 <30 ms (media-suite-project:49) |
| Plugin crash shell + panic | Bridged or sandboxed slots. A crash greys the slot and leaves "[Serum 2] fell over, press to reload". A panic pad, or holding Stop, sends all-notes-off. | N | M | second-press-principle.md:18-20; gpu-driver-crashes-desktop-app.md |
| Instrument rack with sound cards | Cards with fingerprint art in OKLCH, macros, "played 3x this week" (gitignored), and a single "Play it" action. | N | L | project-origin-simon.md:17-25 |
| Macro map | 8 macros + volume on encoders and faders. Touching one pops the LCD with name, value and a coloured bar. One-click learn. Maps saved per plugin. | P | M | keylab88mk3.js:7-10; first-light.js CC-learn |
| Snapshots + morph fader | Snapshots A/B of instrument + chain. A fader morphs between them while the screen colour blends A-hue → B-hue. Double-tap recalls exactly. | N | M | studio.js:1-10 |
| Mutate with taste | 8 seeded neighbours on 8 lit pads, reproducible from the seed. Agent variation sets arrive unlabelled and are judged blind. | N | M | collaborative-means-iterative.md:10-14 |
| Kontakt-aware loading | Libraries listed by registry name. Load cost (RAM and time) measured on first load and shown afterwards. Plain vendor installs by default. | N | M | local-inventory.md:157-159 |
| Chain Bench diagram | Input → slots → output as patch cables in the patch-bay identity (aluminium, VU-amber, teal and rose cables, Archivo + JetBrains Mono). Cables glow with signal level. Drag to reorder. Bypassed slots stay drawn but dimmed. | N | L | media-suite-project-2026-09-13.md:29 ("I love it...") |
| Chain on the KeyLab | The LCD shows "CHAIN 3/5 OTT" in the slot's colour. ctx1-8 select slots and their LEDs show bypass. Encoders edit the slot. Back goes up a level. | N | M | protocol.py:226-275 |
| A/B by ear, blind | Two chains, loudness-matched so louder never wins. Blind mode reveals the answer and both LUFS after you pick. | P | M | arsenal/media/audio.py:1-20 |
| Per-slot latency/CPU budget | A thin bar under each slot and a total by the output. A slot over budget is called out once. | N | S | plugin-path.md §2.3 |
| Parallel and send chains | Dry/wet, New York compression and reverb send lanes, drawn as branching cables, each with a KeyLab fader. | N | M | FL Mixer preset names |

### Pillar 6: The Pad Sampler

**Purpose:** the 12 pads become a sampler whose light is the sound's identity. Hue says what it is, brightness says how hard, and the LED shows the decay.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| 12-pad kit, colour identity | Hue from centroid or pitch class, lightness evened across hues (LUMA_PULL). Kicks warm, hats cool. A quiet ember at rest. | N | L | piano.js:321-410; DAW bank 82-93 |
| Velocity light + layers | Flash brightness follows velocity, then decays along the sample's own envelope at 15 fps, sending only changed pads. Up to 4 velocity layers, shown as rings on the screen mirror. | P | M | ledframe.py; media-suite-project:180 (glowing peaks) |
| Per-pad ADSR, pitch, choke, loop | Select a pad and the encoders become A/D/S/R/Pitch/Start/Filter/Pan. The LCD draws a 2-line envelope glyph in the pad's colour. Choke groups share a tint. | N | M | INTERIORITY.md:117-119 |
| Fill pads from your sources | Browse FL stock, Splice, D:\Cymatics and FPC kits. Audition in time and in key. "Kit from this loop" slices to 12 pads by transients. | N | L | splice-and-sounds.md §0.6, §1, §2.3 |
| Chord pads | One chord of the key per pad, coloured by family, playable on any hosted instrument. | P | M | chordview schemes; W247 |
| Resample-to-pad | Hold Record and play. The phrase and its chain become a WAV on the next free pad, glowing in the source instrument's colour. | N | M | fact-check.md:96 (Record CC 22, on release) |
| Kit → FPC export | Writes an FPC .fst with GM mapping and envelopes. | N | M | splice-and-sounds.md §1 FPC rows |

### Pillar 7: FL Round-Trip, natively, both ways

**Purpose:** what you craft arrives in FL as if FL had made it, and your existing FL work comes into the room.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| .fst / .flp event reader | A stdlib parser for FLhd/FLdt. Shows each of the 9 mixer presets as a chain diagram: slot order, plugin names, levels, which state blocks are present. | N | L | Byte read of Piano 1.fst 2026-10-22: `46 4C 68 64`, "FL Studio 25.2.5", "Fruity Wrapper" |
| FL preset → room | Load any FL mixer preset live and play your guitar or piano chains outside FL. | N | L | your words, "works detached AND alongside FL" |
| Room → FL preset | "Send to FL" writes .fst into `Presets\Mixer presets\Aurora\`, carrying the exact VST3 state blob. | N | XL | arsenal/fl/vfx/README.md ("Nothing here writes into FL"; this is your call) |
| Channel presets round-trip | A hosted Kontakt or Serum sound becomes an FL channel preset with its state. | N | L | Channel presets folder exists, empty |
| .flp census + finder | 913 projects catalogued: tempo, key guess, plugins, chains, last opened. Query "every project using Gated Angy Pad". Chains can be pulled into the bench. | N | L | W228 WISHLIST.md:1364-1366 |
| Alongside-FL live bridge | The VFX Script "Claude Band" plays on FL's clock into your instruments, KeyLab knob → Pattern. FL stays master (FL has no Link). | P | M | arsenal/fl/vfx/README.md Status; fl-scripting.md §0.5 |
| Drag-out stems/MIDI/.fst | A drag handle on every bounce, kit and pattern. MIDI uses integer notes and GM roles, so FL's C5 naming quirk never bites. | P | S | splice-and-sounds.md §0.7; band.py:1-12 |
| FLP diff / template kit | A template skeleton plus "what Simon changed": slots, presets and tempo, read natively from both files. | N | L | the parser makes this cheap |

### Pillar 8: Memory and Showcase. Takes, library, content, sharing

**Purpose:** a good moment is never lost. Everything you make or own is browsable, beautiful and honest about its source, and any session can become a gift or a post.

| Feature | What it does | St | Sz | Evidence |
|---|---|---|---|---|
| Retro-record | A rolling 60 s buffer of audio and MIDI. Press Record after a happy accident and the LCD says "kept 0:47". | N | M | INTERIORITY.md:469 |
| Take ledger with lineage | take.json + append-only events.jsonl: instrument state, chain, kit, macro moves, seed. Re-render at higher quality or reopen as a live sound. | P | M | arsenal/take.py:1-6 |
| REC button = take | Starts the take and the page recording. Hints and diagnostics go silent and the lean stays off. Stop offers "make a short?". | P | M | take.py; dce896:54-62 |
| Bounce with QC receipt | WAV + LUFS, true peak, silence spans. Two-pass loudnorm in one click. | P | S | arsenal/media/audio.py:1-20 |
| Performance video takes | The canvas, the KeyLab mirror and room audio as a CFR H.264 MP4. | P | M | recorder.js:1-25 |
| Shorts with hardware in frame | 1080x1920: the /piano canvas over a shot of the real KeyLab, synced by the first note. | P | M | tiktok.py:1-6 |
| Stream overlay mode | LCD shows song, chord and BPM; a matching page overlay for streams. (This lens entry arrived truncated; scope beyond this is not specified.) | N | M | lens 2 P7 |
| Showcase attract mode | Pre-made shows (Violet & rose, Golden wings, patch-bay amber), never blank. Any key wakes the chord card. | N | M | second-press-principle.md:26-30 |
| Audio → MIDI + stems | UVR on the 9070 XT via DirectML; Transkun notes (0.91 F1 on your playing). Results load into the sampler. | P | L | media-toolkit-vision-2026-10-11.md |
| Library cards | Fingerprint art, BPM, key, your mood words, lineage ("from Piano 1.fst + OTT"), a small as-of/confidence stamp. | N | L | media-suite-project:369,378-382 |
| Audition in time and key | Stretched to the current BPM (FL or beatsync), pitched to the key, the way Splice Bridge does it, for your own sounds. | P | M | splice-and-sounds.md §3.1 |
| Browse from the KeyLab | The second press is a question: the category and its count, then preview of the top pick, then a short list of options. ctx buttons filter; LEDs tint by category. | N | M | second-press-principle.md:11-20 |
| Buildups and risers catalog | Sound + automation curve, previewed at tempo, landing on a bar line. | N | M | VFX band bar-line rule |
| Licence and provenance guard | Each card carries its source class. Refusals come with one-line reasons: no raw Splice redistribution, no Splice audio in training or embeddings. | N | S | splice-and-sounds.md §2.3; INTERIORITY.md:236-238 |
| Splice shopping list | Claude writes "find these"; you download in the Splice app; Documents\Splice is auto-indexed. | N | S | splice-and-sounds.md §0.2 (no API, automation banned) |
| Chain packs | A .aurora-chain bundle: JSON + .fst + plugin versions + a fallback chain of stock/free plugins + a 10 s preview + card art. | N | L | archero-style-game-vision.md:11-16 |
| Discord drop, outbound first | You name the channel and confirm each send. Inbound packs land in a quarantine shelf, previewed and never auto-loaded as plugins. | P | M | scripts/inbound_media.py; feedback-engage-with-tooling-dont-dismiss.md |
| Agent co-designers, blind | Seats propose chains for a brief as unlabelled cards. You audition on the pads and pick live; authorship is revealed after. | N | M | media-suite-project:241,269 |
| Sound-design episode recorder | One command records the canvas, chain and mirror, with macro callouts only in rests, one at a time, and exports through arsenal/media presets. | P | M | dce896:31-34,54-62 |

---

## 2. The spine: what makes it one thing

```
 pages (:8793 piano/FL/Play, :8787 /vfx, :8797 shaderlab) + CLIs + agents
        │ intents (pad frame / LCD lines / LED roles / attention)   ▲ SSE "keylab" + control events
        ▼                                                           │
 ┌──── KeyLab HUB (arsenal serve :8793) ────────────────────────────┐
 │ leases per surface → layer stack → shared palette (OKLCH→to7)   │
 │ → PadRenderer delta → paced writer (≤12 pkt/burst) → DAW port   │
 │ producers in-proc: beat engine, chord reader, now-playing       │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ control map / transport / meters
 ┌──── ENGINE ROOM (supervised native) ─────────────────────────────┐
 │ Carla: live instruments (ASIO)   Pedalboard: chains live+offline │
 │ Python conducts, never renders    record bus · take ledger       │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ FL INTEROP: FLhd/FLdt parser (.fst/.flp),
                                │ VFX Script/Patcher bridge, coexistence switch
```

**Device owner service.** A single Python KeyLab hub inside `arsenal serve` :8793 owns the DAW output. It is stdlib + ctypes WinMM, and beatsync's heavy dependencies load lazily. The code proves one owner is needed even if Windows allows many:

- the freeze budget covers the whole device;
- chordview and beatsync each send `daw_connect(False)` on exit (chordview.py:120-125, beatsync.py:118-123);
- PadRenderer assumes it is the only writer (ledframe.py:1-45);
- FL's Arturia script also writes to the port.

The design copies three existing patterns: CueHub fan-out (pianocue.py), the VFX renderer lease (bifrost_ui.py:224-285) and the cues.js tab arbiter. The current CLIs (`chordview`, `beat`, `show`) become producers instead of port openers.

**Scene model.** A scene is a stack of layers (ambient/beat < page < practice < popup), each owned by a lease holder, composited per surface (pads, LCD, button LEDs) and sent as a delta. Modes and menus are projections of the H9 one-world mode schema (d622ac §3-4), so "a surface is a projection, never a store". Saved looks (/api/piano/looks) are the scene presets.

**Audio engine split.** Live instruments run in Carla (C++, ASIO, bridged plugins, ~3-12 ms). Effects run in Pedalboard (live AudioStream and offline, one chain object). Python conducts only. This follows the research verdict at memory:23. Neither package is installed today: pedalboard and sounddevice are missing from py 3.11; numpy, aubio, pyaudiowpatch, soundfile and librosa are present.

**FL interop layer.** Three channels:
- **Files:** a stdlib FLhd/FLdt event parser and writer for .fst and .flp. Plugin-state blobs are decoded per plugin, and VST3 state passes through byte-exact.
- **Live:** the VFX Script band + Patcher on FL's clock (arsenal/fl/vfx).
- **Device:** the coexistence switch, "FL drives" or "Aurora drives".

**Web UI integration.**
- Pages never open SysEx. Today they all ask for `sysex:false` (piano.js:3803, cues.js:1697, first-light.js:768, play.js:2027, piano-lab-score.js:299), and /vfx has no MIDI code at all.
- Pages POST intents and listen on the cue SSE.
- /vfx reaches the hub through CORS limited to :8787, or a bifrost_ui proxy.
- One shared palette module replaces the three disagreeing CSS token vocabularies. It carries its tone mapper with it (arc-piano-studies.md:468).

**Agent door.** Agents are producers like any page:
- `py -m arsenal.keylab <verb>` for the hardware;
- `map <producer> -> <target>` (T399 F4) for bindings;
- an intents route + MCP door shaped like arsenal/media's;
- variation and chain proposals arrive unlabelled for blind judging.

Agents never hold the port.

**Confirmed hardware facts the spine rests on**

| Fact | Source |
|---|---|
| SysEx `F0 00 20 6B 7F 42 <payload> F7`; LED `[00,2,3,id,R,G,B,00]`, RGB 0..127, **req byte 0x00** (0x02 = white) | memory:11-12. The README still says the 0x02 default, so the README is stale (README:55). |
| Live pad colour only on the DAW bank, ids 82-93, only in **physical** DAW mode (Prog + 6th screen button). No SysEx mode switch. | memory:13 |
| About 36 packets in one burst freezes the device (power cycle); 12 is safe | memory:14 |
| LCD popups 23/24/25 dismiss in ~1 s; F2L (12) persists; ~15 fps colour animation is flicker-free | memory:15 |
| Input port "KeyLab 88 mk3 MIDI"; output port "KeyLab 88 mk3 DAW" | memory:16 |
| The ~10 ms flicker drift is the device's own LED cadence (host timer ~1.5 ms, SysEx send ~0.3 ms) | memory:17 |
| 12 RGB pads, 34 button LEDs, 9 faders, 9 encoders, main encoder | protocol.py:48-57,226-275; keylab88mk3.js:7-10 |
| FL drives a Focusrite USB ASIO interface at 48 kHz, buffer 256 | local-inventory.md:112 |
| .fst = FLhd/FLdt event stream with a Fruity Wrapper block | byte read 2026-10-22 |
| **Contested:** "only one process can hold the DAW output". WinMM opened both ports alongside FL on 10-07, and midisrv is documented as multi-client, but there is no receipt. | memory:16 vs fact-check.md:143 |

---

## 3. Placement in the house

**Where it lives:**
- Planning layer in force: the Estate Program (docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md), bound on 09-03 by the two-watch width cap and your appetite ranking A8 > A1 > A3 > A12 > A5. Concurrency rules come from docs/ORG.md: one build watch + one design watch; a third needs `pauses:` or your word.
- Recommended home: **arc A12 THE FACE** (appetite #4, "the founder's first love"), inside the existing media-suite map (docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md) as new tracks. **Not a new arc.** A new arc would need the full fence ceremony and your word.
- Housekeeping found on the way: fa48f2 still lists H1 as "FIRST" although H1 landed 10-08; ARCHITECTURE.md never mentions arsenal/; tasks.json has no arc field. All need refreshing.

**Proposed names (your pick, see Q3):**
- **K track: "KeyLab Lit"** covers the Hub, the Light Language, Beat/Timeline and the Controller (pillars 1-4).
- **R track: "The Engine Room"** covers the sound room, sampler, FL round-trip and the memory/showcase pillars (pillars 5-8).
- Umbrella alternative: one track, **"The Lit Console"**.

**What it absorbs or feeds**

| Existing arc / organ | Relationship | Cite |
|---|---|---|
| Piano VFX (arsenal/web/piano) | Feeds: noteColor, harmony-feel, lean, cadence-live and the twin become the device's source of truth | piano.js:321-410; keylab88mk3.js:578-813 |
| Now Playing S3 (palette bleed) / S5 (three timescales) | Absorbed into the Light Language. NP S4 "Ears" is replaced by the beat engine. | 1328e1:108-111,177-191 |
| Presentation grammar P2 screens / musical spells | Feeds: the KeyLab as an LED-wall surface | 236d39:107-157 |
| H9 one-world modes + floor | The menus are its projection | d622ac §3-4 |
| T399 contract F4 `map` verb | The controller binding mechanism | fences/media-arsenal-contract/reconciliation.md:90-101 |
| Story layer rulings | They bind all LCD callouts (feelings first, one at a time, in rests, canvas his) | dce896:31-34,54-62 |
| Media toolkit (arsenal/media) | Feeds: bounce QC, loudness, exports, shorts | media-toolkit-vision-2026-10-11.md |
| Presentation primitives (arsenal/present) | Feeds: showcase scenes, episode recorder | presentation-primitive-family.md |
| Shader school | Delivers its pending "shared colour templates" ask as the palette module | shader-school-2026-10-13.md:11-16,79 |
| FL jam bridge (research + arsenal/fl/vfx) | Absorbed into pillar 7 | fl-jam-bridge-2026-09-14/* |
| Second-press principle | First full application (menus, browse, what-does-this-do) | second-press-principle.md |
| Archero game vision | Fed later by the light-games layer | archero-style-game-vision.md |

**Existing wishes this resolves:** W247 and W248 (note truth, melody-deaf log), W228 (.flp find), W181/W182 (resolution, GPU idle; respected by the hub's 15 fps cap), W58/T007 (the Void theme as one palette token set). The WISHLIST has **zero** hits for keylab, arturia, vfx, sampler, vst, controller or colour. Filing your words from today as wishes is step zero of the brief.

---

## 4. Build sequence

Each wave ends in something you can play. UI waves run at the fast speed: light checks, judged by what you can see. You give one "that's right" on the brief before any visible build (CONDUCT.md L3).

| Wave | Contents | You can play with |
|---|---|---|
| **W0 Land and census** (S) | Commit arsenal/keylab by named paths (your approval). Report atom + pytest pins. Brief quoting your words; file the wishes. Control census. One pad-layout table. **Probes: P1 DAW-port sharing with FL, P4 7-bit vs palette, P5 req byte.** | chordview with the right pad layout; the twin filling in as you touch each control |
| **W1 The Hub** (M) | Hub in serve :8793, paced writer, layer stack, intents, `keylab` SSE kind, leases, diagnostics with personality, FL coexistence switch. chordview and beat become producers. **Probe P3: Web MIDI SysEx vs daemon latency.** | /piano lighting the pads while beat-march runs underneath, with no DAW-mode drops on exit |
| **W2 The Light Language** (M-L) | Shared palette module + tone mapper, noteColor→7-bit bench, schema picker, chord families, living edges, chord card, Now Playing card, beat engine producer, march patterns, three timescales, showcase attract mode | Spotify plays; the pads march; the LCD shows song, chord and BPM in album colours |
| **W3 The Controller** (M) | CORS bridge for /vfx, `map` verb, VFX Bench strip layout, soft takeover, scene launcher pads, menus v1 (second press), what-does-this-do, Shader Lab preview. **Today's ask lands here.** | Faders and encoders playing the VFX avatar live; pads launching looks; menus on the LCD |
| **W4 Engine Room core** (XL) | **First probes P6 Carla latency on your Focusrite and P7 ASIO single-client** (Carla download with your OK). Supervisor, latency receipt, panic, crash shell, memory guard, instrument rack, macro map, snapshots/morph | Press a key, hear Kontakt with FL closed, the latency p95 beside it |
| **W5 FL round-trip** (L-XL) | **First probe P8 .fst format.** Reader → chain diagram, import, a write-load-readback drill (RED first), export, channel presets, .flp census, drag-out | Open "Piano 1.fst" in the room, play through it, send an edit back to FL |
| **W6 Sampler + Chain Bench** (L) | Pedalboard runner (pip with your OK), chain diagram, chain on the KeyLab, blind A/B, per-slot budget, parallel lanes, 12-pad sampler, velocity light, ADSR, fill pads, chord pads, resample, FPC export, spectrum meter | A colour-identity drum kit on the pads; reorder a chain by dragging cables |
| **W7 Memory, timeline, content** (L) | Retro-record, take lineage, REC = take, bounce QC, library + KeyLab browse, licence guard, heard-song timeline, chord sheet import, look-ahead, games, cadence moments, co-performer, shorts, chain packs, Discord drop, blind co-designers, episode recorder | "kept 0:47"; next-chord glow on a song you love; a short with the real KeyLab in frame |

**Width:** K (W0-W3) and R (W4-W7) can run as the two watches, one build and one design. Any third thread needs your word (ORG.md). A running order gets published as soon as four or more threads are live.

---

## 5. Ratification questions

1. **Land it now?** Commit `arsenal/keylab/` as-is by named paths today, **or** after the W0 bench settles the req byte and the pad layout.
2. **Placement:** K and R tracks inside media-suite under A12, **or** a new arc (A16, with the fence ceremony) for the Engine Room, since sound-craft is arguably more than "the face".
3. **Name:** "KeyLab Lit" + "The Engine Room" as two tracks, **or** one umbrella, "The Lit Console", **or** your own name.
4. **Order:** light-first (W1-W3 answer today's ask: pages driving the KeyLab), **or** sound-first (W4 Engine Room probes start in parallel as the design watch).
5. **FL default:** when FL is open, "FL drives" (the hub yields automatically), **or** "Aurora drives" (you turn off FL's Arturia script and the house always owns the light).
6. **Hub home:** inside `arsenal serve` :8793 (one process, shares the cue hub), **or** its own daemon that survives page-server restarts.
7. **Touches outside the repo:** approve the Carla download, the `pedalboard` + `sounddevice` pip installs, and one `Presets\Mixer presets\Aurora\` folder in FL. Yes to each, **or** export to a drop folder you drag in by hand.
8. **Palette canon:** which colour vocabulary is the root of the shared module: piano's OKLCH noteColor family, the patch-bay identity, or the Aurora Void theme. The other two are derived from it.

---

## 6. Open probes

| # | Unknown | Cheapest test |
|---|---|---|
| P1 | Can FL's Arturia script and the hub share the DAW port? Memory:16 says one process; fact-check:143 says multi-client. | With FL open, the hub sends one pad colour. Watch whether FL overwrites it within 1 s and whether either side errors. Dated receipt. |
| P2 | DAW-mode control map (CC numbers, relative vs absolute encoders, ctx buttons) | `py -m arsenal.keylab monitor`, touch each control once (the W0 census) |
| P3 | Web MIDI SysEx direct vs the hub daemon | Time 100 intents POST → WinMM send (target < 16.7 ms p95). Compare one page with `sysex:true` (one permission prompt, no shared budget). Expectation: the hub wins on safety alone. |
| P4 | Full 7-bit live colour vs snapping to the 42-entry palette | Ramp R 0..127 on one pad in steps of 4 and take a phone photo. Count distinct levels. |
| P5 | req byte 0x00 vs 0x02 (README:55 is stale) | Send the same colour both ways to one pad and compare |
| P6 | Carla latency on your Focusrite | After the download, load Mini V4 bridged at buffer 64/128/256. Loopback a click out → in and measure the p95. |
| P7 | Is Focusrite ASIO single-client while FL holds it? | Start Carla with FL playing and note which side loses audio. If single-client, use the room only when FL is closed, or route through FL via the VFX bridge. |
| P8 | .fst plugin state = exact VST3 state? Does FL accept a written file? | Null round-trip: parse and rewrite Piano 1.fst byte-identical, load in FL. Then change one mix level, then compare the Fruity Wrapper chunk to Carla-saved state for the same plugin. |
| P9 | LCD payload grammar beyond popups and F2L (per-line colour, field tags) | Lift the field tags from KL3Display in Arturia's FL script and try each tag once on F2L |
| P10 | Kontakt 8 inside Carla bridged mode | Load one small library and play 30 s; then load a large one and record RAM and load time |
| P11 | Beat engine CPU while the engine room runs | Run beatsync loopback + Carla together for 10 min; watch audio dropouts and CPU |
| P12 | SMTC album art availability for palette bleed | Read the SMTC thumbnail for the current Spotify track once |

---

### Evidence gaps in this synthesis

- Only two lens visions arrived: Sound, and Instrument + Light. The Instrument lens's P7 was truncated in the middle of "Stream overlay mode".
- One evidence lane was blocked by a safety classifier and returned no findings.
- The third evidence front (prior art) was truncated. It contributed the Bitwig MIT KeyLab mk3 extension (updated 2026-10-21) and the saxofonbrian/keylab-mk3-sysex repo as protocol cross-checks. It also identified three gaps no product fills: controller pads driven by arbitrary system audio, a web app writing live to a keyboard's screen and lights, and .fst round-trip through a standalone host. With one shared harmonic colour language added, those are this vision's genuine novelty.
- Directly verified this pass: the keylab memory note, the arsenal/keylab file list and README, `git status` (untracked), and the existence of the cited design and map atoms (fa48f2, 1328e1, 236d39, d622ac, dce896, c432a7). All other line citations are carried from the lens and evidence reports and were not re-read.