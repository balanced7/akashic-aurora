# KeyLab vision pass 1: completeness review

**Scope and method.** I was read-only throughout and wrote no files. I re-read these myself: chordview.py (lines 1-70), protocol.py (lines 78-90), `__main__.py` (cmd_ledbench, lines 326-395 and 485-496), keylab88mk3.js (grep for the pad layout), the installed metadata for aubio-ledfx, the keylab memory note, backup-and-recovery.md, and the fl-jam-bridge research files (grepped). Web claims taken from the prior-art front (Bitwig, saxofonbrian, NI, Push, Novation and others) come from the evidence JSON and I did not re-verify them. They are marked [ev].

---

## A. Ask coverage

Status values: COVERED, PARTIAL or MISSING. "P1 L49" means pass-1 line 49.

| # | Ask (short) | Pass-1 answer | Status | What to add (what Daniel sees, hears or does) |
|---|---|---|---|---|
| 1 | "we will build [FL integration] ourselves" | FL coexistence switch (L34), transport mirror (L68), VFX Script bridge (L139) | **PARTIAL** | Pass 1 can only yield to Arturia's script or hold the port. It never replaces the script. Add **`device_AuroraKeyLab.py`, our own FL controller script**. With it, the LCD shows the selected FL channel name, and the pads take the mixer-track colours. Encoders follow the focused plugin and the ctx LEDs follow FL's beat indicator (`OnUpdateBeatIndicator`). It forwards everything to the hub. FL's hardware folder has no custom script yet (fl-scripting.md:28). FL 26.1.3 has freeze bugs when scripts call FL functions (fl-scripting.md:74), so it ships after the JamProbe drill (fl-scripting.md:113). |
| 2 | "understand our full surface", the whole Arturia suite | Control census (L35), probe P9 LCD grammar | **PARTIAL** | The census only covers DAW mode and user mode. Add a **KeyLab Atlas page**: click any control on the twin and see what it sends in each pad mode (Arturia Program / DAW / Default), plus Chord, Scale and Arp. Also cover the 6 user programs, MCU/HUI, touch-sensitive encoders and faders, pad pressure [ev], and the Arturia-mode (00 01 04) vs DAW-mode (00 02 04) protocol families [ev]. Each fact carries a dated receipt. |
| 3 | FLP template site + DAW conversion kit | FLP diff / template kit (L141) | **PARTIAL** | There is no site and no conversion at all. See E1. |
| 4 | "Splice-ify sound chains and buildups / structure" | Chain packs (L164), buildups catalog (L161), library cards (L158) | **PARTIAL** | "Structure" is missing: song-form skeletons mined from his 913 .flp files. See E2. |
| 5 | Drag samples to pads, ADSR, map Addictive Drums notes to pads | Pillar 6 (L120-126), FPC export (L126) | **PARTIAL** | Addictive Drums 2 mapping is absent. Add an **AD2 kit map**: pick AD2's GM map preset (splice-and-sounds.md:18) and each pad shows its AD2 piece name ("Kick", "Snare", "HH closed") on the LCD and on the Pad Desk. Pad hits go out as integer GM notes through the hub to a loopback port feeding FL/AD2. That loopback needs the Windows MIDI Services SDK download and Daniel's OK (virtual-midi-and-sync.md:12-24). |
| 6 | "shift + play note + tap pad = pad triggers that note"; "should we make our own vst?" | none | **MISSING** | Add a **Pad Learn gesture**: hold the ctx key labelled LEARN on the LCD, play a key, tap a pad. The LCD says "pad 9 = D#3" and the pad takes that note's colour. The hub remaps the pad to the note and re-emits it on the loopback port. Answer to the VST question: no VST is needed for the remap. FL has no MIDI-effect slot, so a VST would load as an instrument (fl-jam-bridge-plan.md:230). Optional extra: a **probe** for writing pad notes into an Arturia user program (the MCC way), so the mapping works with Aurora closed. |
| 7 | Drop samples on pads, "easily select color", velocity, ADSR | Colour identity (L120), velocity light (L121), ADSR (L122) | **PARTIAL** | In pass 1 colour is automatic, but he asked to *select* it. Add a **swatch picker limited to LED-safe colours**, each swatch shown next to a phone photo of the real pad. Add a velocity-curve editor and draggable ADSR handles. Auto-colour is the default, never forced. |
| 8 | "sexy ui ... drag and drop on top of the pad ... with the manual bund method as well"; expose modes and pad banks | Fill pads (L123), control census | **PARTIAL** | Add a **Pad Desk page**: a 3x4 grid in the printed 9-5-1 layout, drop a WAV onto a pad, and the pad on the real KeyLab lights the moment he drops. "manual bund method" is ambiguous. I read it as also writing to the device's own stored programs. That needs the user-program probe from row 6 to be confirmed with him. Add **pad-mode awareness**: the LCD tells him which mode the selector is in (left Program, middle DAW, right Default) and that live colour needs the middle position. |
| 9 | Render the playing chord on the pads | chordview schemes (L48), chord card (L53) | COVERED | Use the grid geometry from D8 (chord shapes). |
| 10 | Verbs for MIDI and colour; latency and rate tests; the onboard display | Agent door in one line (L215-219), Cleverer than the hardware (L56) | **PARTIAL** | No LED latency test exists. The host can only time up to the send. The hardware leg needs a **240 fps phone-video drill**: key and pad in frame, count frames, dated receipt. The latency strip (L101) covers audio only. The verbs and MCP door are thin (see B). |
| 11 | Learn the real send limits; "more clever than the hardware" | Cleverer than the hardware (L56), probe P4 | **PARTIAL** | Add a **device-side pulse/blink probe**. Bitwig's MIT source defines BlinkState {BLINK1-3, PULSING} [ev]. If the firmware honours it, beat lights cost one packet per change instead of a stream. That is the cleverer route. |
| 12 | Flicker: "test higher and lower ... track stability ... illustrative effect" | none | **MISSING** | Add a **stability ladder receipt**: a dated curve of the Hz levels he judged clean, uneven or broken. Then add a **"shimmer" effect class** that uses the uneven band on purpose, for risers and tension only and never at rest. He hears a build and sees the pads shimmer up into the drop. |
| 13 | "say what test pattern it's in on the main [LCD]" | none | **MISSING** | ledbench shows the level number as lit white pads, not on the LCD (`__main__.py:352-358`). Add an F2L line per level: "RATE L3 · 20 Hz", "SPACING 4 ms", "BURST n=14". |
| 14 | "renderable window for our VFX"; chord viewer on the KeyLab | LED-wall is one cite only; spectrum meter (L57) | **PARTIAL** | Recover the house lens's **LED-wall treatment** (B). It makes the 12 pads + 34 LEDs a downsampled render target of any page, at 15 fps or less. |
| 15 | Colour and *shape* per chord; "cool representations" | Schema picker, families, living edges (L48-50) | PARTIAL | Shape is never designed as such. Add the **torus shape dictionary** (D8). |
| 16 | Sustain had no effect (fixed same day) | Hold LED follows pedal (L56) | PARTIAL | Pin the CC64 fix as a RED/GREEN pytest so it cannot regress silently. |
| 17 | 7ths = one colour, edges change, a quality region and a note region | Chord families (L49), FRAME / living edges (L50) | COVERED, with a defect | L50 says "8 border pads". On the confirmed grid the border is **10 pads**, everything except 6 and 7 (`chordview.py:38`). L49 makes dom7 **amber**, which washes to white on these LEDs (D7). |
| 18 | Spotify now playing, BPM, **track position**, LEDs march, UltimateChords, own chord DB | Now Playing card (L54), beat engine (L65), heard-song timeline (L69), clean-room sheet import (L70) | PARTIAL | Track position is never used. Add **position-locked timeline playback**: when he seeks in Spotify, the look-ahead pads re-sync. The SMTC timeline-position read is my inference and needs a probe. |
| 19 | "poll a db ... starting bpm sourced from multiple dbs ... keep refining bpm detect" | none | **MISSING** | Add a **BPM seed-and-refine engine**. Candidate tempo sources need probing; Spotify's API is dead (memory). Seed the detector from where they agree, then let loopback refine. The LCD shows "92 · 2 sources · heard 91.8 · conf 0.86". Add an **accuracy bench**: his own FL bounces, whose .flp tempo is ground truth, plus tap-tempo agreement. Score half- and double-tempo errors, which aubio is known to make (beatsync.py:11). Track it as a dated accuracy curve. |
| 20 | "engaging content" | Pillar 8 | COVERED | Add the KeyLab tour episode (B). |
| 21 | Attention verb | "attention flash" intent only (L30) | **MISSING** | See B, P5. |
| 22 | Media ergonomics: direct media link in the wake message | inbound_media.py named only as a citation (L165) | **MISSING** | See B, P5: the wake message carries the media path, and photo → palette. |
| 23 | Host VSTs (Kontakt, piano, EQ) | Pillar 5 | COVERED | |
| 24 | Low-latency play space, IMPORT to FL | Pillars 5 and 7 | COVERED | |
| 25 | KeyLab as a VFX device | Pillar 4 | COVERED | |
| 26 | Effect chains + FL mixer presets, detached and with FL | Pillars 5 and 7 | COVERED | Lens 1 P9 also had a **Mixer strip mode** and a **preset browser on the LCD** ("import to FL?" on the second press), and pass 1 dropped both. |
| 27 | UI tie-in: VFX and arsenal pages drive the LCD with menus and adaptive colour | Pillars 1 and 4, CORS bridge | COVERED | Use the native LCD list widget (C). Lens 1 P8 also had **page presence cards** and **harmony modes on pads** (Tonnetz, Stained glass), and pass 1 dropped both. |
| 28 | Full vision, fan-out, structure into projects, multiple passes | Section 3 placement | PARTIAL | The house lens was lost, and this pass recovers it. Add the published running order card (B, P0). |

---

## B. House lens recovery (absent or thinner in pass 1)

Each entry gives the lens's own description and what pass 1 kept.

**P0 Land, then place**
- **Brief in his words + successor map.** Run `doc new --type brief --title keylab-display-tie-in --arc media-suite`, quoting today's asks verbatim. A successor map supersedes fa48f2, because there is no revise verb. W247 folds into track K's acceptance. Pass 1 has a single line on this.
- **Published running order.** An unprompted now / next / after card with a `pauses:` line. The lens's order is: now = land the package + hub; next = menus and colour on /piano and /vfx; after = attention verb, chord DB, content kit. Pass 1 only promises to publish it "once four or more threads are live". Daniel would see the card on the console and on Discord.
- **Wishlist seeding with named frictions.** The DAW-mode input map was never captured. Three pad layouts disagree. There is no :8787→:8793 path. theory.py is a second chord namer.

**P1 Device owner**
- **Global burst governor.** One token bucket, with last write wins per pad and a coalesce count recorded. "The LCD never goes dark because two pages got excited at once."
- **Producers become clients, with a fallback lock file that names its owner** (the GPU-LOCK pattern). The verbs are kept and re-routed, never deleted.
- **Input plane: named events.** `enc3 +2`, `fader7 0.61`, `ctx4 long-press` go out on SSE. Pages subscribe by name, never by raw CC, and one server-side map replaces the localStorage CC-learn. Pass 1 has the map verb but not the named-event plane.
- **`learn-map` verb.** The LCD prompts "press encoder 1", and the same verb lights pads one by one for Daniel to tap. It writes `state/keylab/inputmap.json` (see D5: this should be committed, not left in state/).
- **FL coexistence detail.** Detect FL's script repainting the LEDs with 0x00 at init(), then offer "Yield to FL" (the hub goes input-only) or "Hold" on the soft keys.

**P2 One governed scene**
- **`keylab.scene.v1` schema.** pads[12] with rgb, role and source; buttons {role: rgb}; lcd lines, per-line rgb and screen; menu tree; mode; palette id; tempo and phase; lease holders. The validator gives sentence-shaped refusals like `present.scene.v1`, and the scene projects into the one-world journal. Pass 1 only has the prose "a scene is a stack of layers".
- **Twin parity with a "hardware in sync" tick** showing the age of the last receipt. The twin's screen uses the Outfit font, switchable with `?font=raleway|jost`. Also note the twin is still 2x6 (`keylab88mk3.js:34,519`, verified).
- **One chord truth with `kind: note|interval|chord`.** Pass 1 has this (L52).
- **Modes as saved tunings of the whole instrument.** Hunt, Explore, Ship, Heads-down, Init, Perform and Practice, each a tuning of pads, LCD, menus and page visuals together. The mode name sits on LCD line 1, a ctx long-press cycles modes, and a severity floor cannot be switched off. The modes ship pre-made. **Absent from pass 1.**

**P3 Menus and colour**
- **The legend node in every menu**: what is bound, what is not, and why (INTERIORITY "given bounds").
- **First Light and Play bound to the hub.** First Light: a knob turns the hue, intensity sits on a fader, and the preset name pops for about 1 s. Play: encoders move macros and the pads light as the macro scenes. Pass 1 mentions only CC-learn.
- **Piano page mirrored**, with the lean shown only if he answers its gate question. This is partly in pass 1.
- **Second-press hints on the device.** "enc 3 · unbound" → "hold ctx8 to learn" → the full picture → "There it is." Pass 1 applies this to menus but not to unbound controls.
- **LED-wall treatment.** The pads + 34 LEDs become a downsampled projection of the foreground page's palette and motion, and the quiet state is a full composition. **Absent, and it answers ask 14.**

**P4 Verbs + MCP door** (pass 1 has one paragraph, L215-221)
- **arsenal-keylab MCP door**: `keylab_state`, `keylab_show(text, colour)`, `keylab_pads(frame)`, `keylab_popup`, `keylab_menu(tree)`, `keylab_listen(events, secs)`, `keylab_palette(id)`. Every answer carries `blind` (for example "cannot see whether DAW mode is physically on") and a `receipt` path. Registering it is Daniel's call.
- **New CLI verbs**: `keylab state`, `keylab facts` (pinned constants with as-of dates), `keylab learn-map`, `keylab palette <name>`.
- **Attributed agent touch.** The holder's callsign colour edges the grid, and LCD line 2 reads "Vandor" or "Asta". **Absent.**
- **Physical HALT + time-boxed grants.** A long-press of Back reclaims every surface and pops "yours again". The ladder runs INFORM (LCD whisper), STEER (pads), INTERRUPT (popup), HALT (Daniel). **Absent; HALT has zero hits in pass 1.**
- **Duet suggestion lights**: dim "suggestion" pads for a next chord. Pass 1 has the co-performer but not the suggestion lights.

**P5 Attention and media** (all absent; asks 21 and 22)
- **Attention verb.** `py agent_cli.py attention --at 21:30 --ask "Commit arsenal/keylab?" --option yes --option later --launch /piano`. It surfaces at that time on the console, on Discord, and as an LCD popup with the options on ctx soft keys. One pad breathes and escalates gently by second-press rules if ignored. The answer is recorded with the asker. core/comm/ask.py asks a model, not the operator, so this is new.
- **Click-to-launch options**: a URL (`/first-light?preset=violet-rose`), a verb, or an FL project, opened from Discord, the console or a KeyLab soft key.
- **REC and rest guard.** Attentions queue while FL or the piano is recording and land in the next rest.
- **Discord pump survives 429**, with a drill receipt. This is open in the wake-ladder memory.
- **Photo → palette → keyboard.** He sends a photo on Discord, inbound_media.py fetches it, and within seconds it is a named look on the pads, LCD and pages. The reverse is `keylab snap` → an arsenal/media contact sheet. Daniel's actual ask ("wake message gives you a direct link") also needs the wake text itself to carry the attachment's local path, retiring the "latest created file" crutch.

**P6 Receipts and drills**
- **Pinned device facts table** in code, plus the `keylab facts` verb.
- **pytest with a fake WinMM sink, plus a property test**: no mix of N producers ever exceeds 12 packets per window. A second test covers lease handoff.
- **Three drills**: FL coexistence; freeze recovery (exceed the budget in bench mode, power-cycle, the hub detects the reconnect and replays via `resync()`); server restart restores DAW mode and the frame.
- **Session receipts + a live latency overlay.** Packets, max burst, coalesces, fps and lease history.
- **GPU idle guard.** The hub pushes deltas and pages run no rAF loop for the pads. The lens asks for a bench asserting no GPU rise at idle, tested in real Chrome. Pass 1 only "respects" W181/W182.
- **Privacy rule**: playing data stays only in the gitignored state/. Pass 1 has it implicitly, with zero hits for "privacy".

**P7 Content pipeline**
- **Chord timeline DB fields**: time, beat phase, key, Nashville number, kind, source, song id. Pages scrub it as a timeline.
- **Session capture into arsenal/media**: twin + page + optional camera + audio → catalog → contact sheet → First Light Edit, with per-platform presets.
- **KeyLab atoms in present.** `present.scene.v1` gains a keylab atom kind, so a deck like "how the KeyLab learned to name chords" builds from receipts. **Absent.**
- **Attract mode walks its own menus** while the VFX encoders animate on screen. Pass 1's version is static shows.

**P8 Platform**
- **Sound space speaks the scene**: plugin parameters become LCD menu trees.
- **"The moat is the integration"**: public text from his words, understated. **Absent.**
- **Alpha kit for any KeyLab mk3 owner**: one-click install, the learn-map wizard on the LCD, a mode and palette gallery, and "connect your own assistant" via the MCP door. Arturia's script is a facts source only and is never redistributed. Pass 1 has none of this; lens 1 had a "free alpha for any MIDI keyboard".

---

## C. Prior-art adoptions [ev]

| Product | Best idea to adopt | Where it fits | What Daniel gets |
|---|---|---|---|
| **NI NKS / Kontrol S MK3** | NICA chunk in .nksf (MessagePack) = ready-made encoder pages per plugin; one agent owns screens and lights | Pillar 5 macro map; hub (already the pattern) | Load Serum 2 or a Kontakt patch and the encoders already show the vendor's named pages. No learning step for any plugin with NKS presets. |
| **Maschine MK3** | Colour belongs to the sound: set once, carried to pads, screen and page | Pillar 5 instrument rack + Pillar 6 | A hosted instrument has one identity colour on its pads, the LCD accent and its card. |
| **Push 2/3** | Scale grammar (root takes the active colour, scale notes white, off-scale dark); **2 s dead-man blackout** | Pillar 2 Scale lighting; D3 failure modes | If the hub dies, the pads go dark instead of freezing on a stale chord. |
| **Launchpad X / Launchkey MK4 / Components** | Device-side flash and pulse synced to clock; stationary vs temporary displays; Chord Map with 8 diatonic chords | Pillar 3 march patterns (via the BlinkState probe); LCD grammar | Beat lights that cost almost no packets. |
| **Apollo Studio** | Author light shows on the virtual twin away from the hardware | Twin / attract mode | Daniel can compose a pad show on the twin with the keyboard off, then play it on the hardware. |
| **Scaler / Captain** | Chord candidates ranked *with reasons*; one progression feeds every generator | One chord truth; second press on the chord card | First press shows "Cmaj7"; second press shows "or Em/C, because...". |
| **Hookpad** | **Colour = harmonic function in the key** (I red … vii° pink) | A sixth chordview scheme, FUNCTION | Pads re-colour by role in the key when the key changes. Hookpad's yellow and orange need remapping (D7). |
| **Chordify** | Beat-synced bar grid with a moving cursor | Heard-song timeline page; LCD text form `\| Cmaj7 \| Am9 \| Dm7 G13 \|` | A scrolling bar grid on the page and a 2-bar text window on the LCD. |
| **Synthesia / SynthesiaKontrol (MIT)** | A device-neutral **light-intent stream** (pitch class, role, colour token, hold), with adapters per device | The intents API contract | The same stream later drives a WLED strip or Hue without touching the pages. |
| **LedFx / WLED SR / Hue** | Broadcast the analysis, not the pixels; *virtuals* spanning devices; named transitions (Dissolve, Iris…); **lookahead from a known track** | Beat engine publishes features; transitions on the scene launcher (L83); look-ahead (L71) for local files via an offline pass | On his own bounce, the lights anticipate the drop. |
| **Carla** | OSC remote + out-of-process bridges | Pillar 5 (already chosen); OSC as the Python conducting channel | A crashing VST never takes the room down. |
| **Pedalboard / DawDreamer** | State as bytes (raw_state, .vstpreset; `load_vst3_preset`) | Pillar 7 P8 null round-trip | Byte-exact chain state across FL, the room and packs. |
| **Bitwig KeyLab mk3 extension (MIT, 2026-10-21)** | Second protocol reference. Screen targets 0x0A, 0x0C, popups 0x17-0x19, **knob popup 0x1C, fader popup 0x1E**. LED first byte **0x04** (ours: 0x02 in FL-derived code, 0x00 confirmed live). BlinkState. "Lights as functions of state, flushed on change" | Probes: replace P5 (0x00 is already confirmed in memory) with **0x04 vs 0x00** and **BlinkState honoured?**; use the native knob and fader popups for the macro map | Turning an encoder shows a real knob popup, not a text line. |
| **saxofonbrian/keylab-mk3-sysex (MIT)** | **List widget** (title 0x28, items 0x15, cursor); button packet with RGB + label; **screen packets must be ≥60 ms apart or one is dropped** | LCD menu grammar uses the native list, not 2 hand-drawn lines; the hub's paced writer gets a separate LCD lane at 60 ms or more | Menus scroll like the KeyLab's own UI. LCD updates never silently vanish. |
| **Arturia MCC / Analog Lab** | The two protocol families ignore each other, so Analog Lab can coexist; touch-to-reveal popups | Atlas (A2); the coexistence probe | Analog Lab and Aurora can both be live. |
| **Windows MIDI Services + Chrome 124 prompt** | Ports are multi-client, so collisions are *silent drops*, not "busy" errors (MidiSrv was running on 10-22) | Strengthens the hub argument; reframes probe P1 | "Contested: one process" becomes "many can open the port, and they will silently clobber each other". |

---

## D. Cross-cutting gaps

**D1. Testing and drills in house style.**
- Receipts sit on gitignored paths. Pass 1 puts heard-song data in state/, and the house lens puts receipts in `state/keylab/receipts`. A durable claim with proof on a gitignored path is unfalsifiable (lesson `drill_receipts_live_on_a_gitignored_path`). Commit small dated receipts, either through a `state/drills/` negation in .gitignore or as report atoms.
- Missing pins:
  - sustain CC64 RED/GREEN;
  - a GRID pin (chordview, the twin and the scene must agree; today the twin is still 2x6);
  - an LED-gamut photo receipt;
  - the colour-latency camera drill (A10);
  - a BlinkState probe;
  - an LCD 60 ms spacing drill;
  - the hub-death blackout drill.
- No drill covers the user moving the pad-mode selector out of DAW mode mid-session.

**D2. Performance budgets.** No single budget card exists. It should be visible on the twin:

| Item | Budget |
|---|---|
| Pad packets | ≤12 per burst |
| LCD packets | ≥60 ms apart [ev] |
| Pad frames | ≤15 fps |
| Key → light | host leg measured (p95 target: Daniel's call); device leg about 10 ms cadence (memory) |
| Audio p95 | <30 ms |
| Page idle GPU | 0 work |
| Hub CPU and RAM | Not set; the 82-92 h window applies (L38) |
| Beat engine + Carla together | Probe P11 |

**D3. Failure modes not designed.**
- **Device freeze.** The host cannot see it. Add a heartbeat: if keybed input stops while the hub is sending, it shows "power-cycle me" on the console and Discord.
- **Hub crash.** The pads freeze on a stale chord. Adopt Push's dead-man rule, implemented by a watchdog that clears.
- **Pad-mode selector moved off DAW.** Colours silently stop. Detect it, if the incoming pad notes differ by mode (probe), and show it on the LCD and console.
- **FL repaints the LEDs at init.**
- **USB replug.** H1 Rescan exists, but `resync()` is not wired to it.
- **Beat detector half/double tempo.**
- **Loopback port missing** after a reboot.
- **A plugin licence lapses**, so a chain loads with a hole. The chain pack's fallback chain covers sharing, not his own sessions.

**D4. Licensing and provenance.**
- **Verified:** beatsync already imports aubio-ledfx, whose installed metadata says GPLv3+, inside the Apache-2.0 public repo. Pass 1's licence guard (L162) covers only Splice.
- Carla, Pedalboard and PyFLP are GPL [ev]. They should run out of process or be reimplemented, and the call is Daniel's.
- Bitwig and saxofonbrian are MIT. Credit them in research/reviewed/, never as a headline (attribution-proportionality).
- Arturia's script: facts only, never redistributed.
- UltimateChords: terms check first.
- Shader Lab: CC BY-NC-SA material stays out of tracked files.

**D5. Backup.** These are all state/-only (gitignored) or unspecified:
- takes;
- the chord timeline;
- the input map;
- kits;
- saved looks (storage path not verified);
- per-plugin macro maps.

Snapshot restore has no dated receipt and is presumed broken (backup-and-recovery memory). Proposed split:
- **Commit (non-private device config):** the control map, pad layout, palettes, modes and facts.
- **Private backup with a restore drill:** takes, the timeline and kits, as a dated archive at a location of his choosing.

**D6. Teaching Daniel the instrument.**
- Pass 1 has what-does-this-do (L87) and games, but no first-run path.
- Add the lens-1 **KeyLab tour episode**: an arsenal/present scene where each control lights on the device and the twin as it is introduced. It works as a lesson and as a short.
- Add a **one-page cheat card** generated from the control map, which reprints whenever bindings change.
- Make the KeyLab a **Forest Walk** (memory: weekly ritual): one surface per week (pads, LCD menus, encoders, the Engine Room), with predict-before-look and a teach-back close.

This is the direct cure for "guilty about not using its fancy functions".

**D7. Colour accessibility on these LEDs (verified defect).** Warm colours photograph near white, yet the live code and pass 1 lean on them:
- `chordview.py:22`: QUALITY_COLORS major triad (255,180,0), maj7 (255,150,40), 6 (255,200,0), add9 (255,120,0).
- `chordview.py:18-20`: ROLE_COLORS minor 3rd (255,150,0), major 3rd (255,200,0), 9th (150,255,0) lime.
- The root is pure white (`chordview.py:47-48`).

So in QUALITY a major chord reads as three white pads. In ROLES the **third, the very tone that names the quality, is indistinguishable from the white root.** Pass 1 adds more warm colours: dom7 amber (L49), kicks warm and warm lows (L57, L120), VU-amber patch bay (L108), "patch-bay amber" and Golden wings showcases (L156).

Fix:
- **Measured LED gamut.** A photographed ramp becomes `LED_SAFE` in the palette module, and every token is snapped to it before to7.
- Warm meanings move to saturated red, rose and magenta, which also match his violet-and-rose favourite.
- Mark the root by brightness, a pulse or its position instead of white whenever warm hues are present.
- Encode redundantly by shape (D8).
- Add an **"LED-true" preview on the twin** so pages never show a colour the pad cannot make.

**D8. The confirmed 9-5-1 grid is not exploited.**
- **Border.** It is 10 pads (`chordview.py:38`), so L50's "8 border pads / at most 8 packets" is wrong. The march loop is 9→5→1→2→3→4→8→12→11→10.
- **Geometry (verified).** From `PAD_NOTE` (`protocol.py:85`):
  - columns are chromatic: left C–D#, middle E–G, right G#–B;
  - **each row is an augmented triad** (9,5,1 = C, E, G#).
- **Chord shapes.** A major triad is root → one column right (+4) → plus 3 rows down on the next column (+7). Wrapped, every chord quality is **one fixed shape on a 3x4 torus**, whatever its root.
- **Feature.** Add a **Shape dictionary**: the legend shows "major = this shape", and games ask him to find the shape. This is what he saw today as "colour and shape per chord".
- **Twin.** It must render this 3x4 layout, not 2x6.
- **Spectrum meter.** Map it as 3 columns (low, mid, high) × 4 rows of level rather than 12 bands in reading order.

---

## E. Related ideas from this morning

**E1. FLP template site + DAW conversion kit (ask 3).**
- **Home:** a later **Commons** track under the platform angle. Its gate is Daniel's, as public voice and hosting. It shares one dependency with Pillar 7: the FLhd/FLdt parser.
- **What he sees:** upload an .flp, and a card appears with a stem preview, tempo, key, plugin list and the chain diagram. Visitors pick **"Download as: FL .flp / Ableton .als / DAWproject / Universal"**.
- **Conversion tiers:**
  - **Universal** (every DAW, Reason included): per-channel stems, MIDI per channel with integer notes, a tempo map, markers and a chain recipe card.
  - **DAWproject:** an open format, for the DAWs that read it.
  - **.als:** gzip XML, generated with audio and MIDI clips and stock devices.

  Which DAWs read DAWproject, and Reason's format, are unverified; probe both.
- **Plugin translation table:**
  - FL stock → nearest stock device;
  - third-party VST3 → its state blob if the recipient owns the plugin, else a rendered stem;
  - Splice samples → a "find these" slot list, never the raw files.
- **Also needed:** the provenance guard, the "what Simon changed" diff (L141), and quarantine for uploads (never auto-load plugins).

**E2. Splice-ify sound chains and buildups/structure (ask 4).**
- **Home:** Pillar 8 library, extended. It feeds from the Pillar 7 .flp census.
- **Chains:** already chain packs (L164). Add Splice's core loop for his own sounds: search by key, BPM and mood, then **preview in his project's key and tempo**, then drag into FL.
- **Buildups:** a buildup is a 4, 8 or 16-bar unit (sound + automation curves: filter sweep, riser, snare-roll density) with an **energy-curve thumbnail**.
- **Structure:** song-form skeletons (intro 8 / build 16 / drop 16) **mined from his 913 .flp playlists**, his own forms first. Each card shows section blocks and the energy curve. Drag it out as patterns + automation clips.
- **On the KeyLab:** pads launch sections, a fader rides the build's automation live, and the pads brighten and shimmer (A12) toward the drop and land on the bar line.
- **Agent seats** propose buildups blind (L166).

**Placement summary.** E1 is a new gated track that depends on the W5 parser and must not be pulled into W0-W3. E2 belongs in W7, with the "structure" census pulled forward into W5's .flp census.