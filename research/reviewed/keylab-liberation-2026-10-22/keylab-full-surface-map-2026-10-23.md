# KeyLab 88 mk3: the full surface (every control, every light, what each could do)

> Provenance: written 2026-10-23 (night) by claude (Vandor) for Daniel, in the "full surface" lane of the VJ-night
> workflow. Status: research record, not a ruling. Nothing was sent to the keyboard while writing it: the only
> device contact was a read-only `py -m arsenal.keylab ports` listing.
> Sources, all read in place: Arturia's FL Studio script for this keyboard
> (`C:\Users\L5\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\`: KL3Process, KL3Return,
> KL3Display, KL3Buttons, KL3Pages, KL3Plugin, KL3Connexion, LedId, ScreenId, ParamId, images_sub_enums,
> device_KL3, `device_KeyLab mk3 MIDI`, and its PDF guide), the device file
> `C:\ProgramData\Arturia\MIDI Control Center\Resources\KeyLab3 88.json` and the factory template
> `...\Templates\KeyLab 3 88\Factory\Default.keylab388` (decoded field by field for this document),
> `arsenal/keylab/` (README receipts, protocol.py, probe.py, beathand.py, chordview.py), the receipts in
> `state/arsenal/keylab/receipts/`, and the earlier records in this folder
> (`keylab-mk3-surface-map-2026-10-22.md`, `keylab-mk3-sysex-protocol-2026-10-22.md`,
> `evidence-control-map-2026-10-22.md`, `evidence-shader-params-vfx-2026-10-22.md`) plus design docs D2, D3, D4.
> Facts (numbers, ids) are taken from Arturia's files; none of their code is copied here.

## How to read this in one minute

The keyboard talks to the computer through **two USB MIDI ports** in each direction: **"KeyLab 88 mk3 MIDI"** and
**"KeyLab 88 mk3 DAW"**. It also runs in one of two broad modes:

- **MIDI mode**: the Arturia program or one of the User programs. Faders, knobs and pads send the plain numbers
  stored in the program (you can edit them in Arturia's MIDI Control Center). The factory numbers are below.
- **DAW mode**: the DAW program (Prog + the 6th screen button), with the pad selector in the middle. Faders,
  knobs and buttons send a fixed "control surface" map that Arturia's DAW scripts expect. Only here do the pads
  and buttons take live colour from the computer.

Every row says how sure we are:

- **CONFIRMED**: seen on your unit, with a dated receipt (your eyes, or a tool's measurement).
- **INFERRED**: read from Arturia's FL script, the device file or the factory template. Very likely true, never
  yet seen on your unit.
- **UNKNOWN**: nothing we have says. Only a test will tell.

Important caveat for the whole DAW column: those numbers are what the device sends when its global **"DAW
Protocol"** setting is **FL Studio** (the device file lists 11 choices: Live, Logic Pro, Cubase, FL Studio, Bitwig,
Pro Tools, Reaper, Studio One, Reason, MCU, HUI). FL's script connects and works on your unit, so the setting is
almost certainly FL Studio (INFERRED). A different setting would change the DAW column.

## Glossary (short)

| Word | Plain meaning |
|---|---|
| Port | One of the two named USB pipes ("MIDI" and "DAW"). Each control talks on one of them. |
| Channel | 16 lanes inside each port. Your keys use channel 1, the pads channel 10. |
| Note On / Off | "This key or pad went down / up". Carries a note number (0-127) and a velocity. |
| Velocity | How hard you hit, 1-127. The curve that turns force into a number is a global setting. |
| Aftertouch / pressure | Pressing harder **after** the hit. "Channel" aftertouch is one value for the whole keyboard; "poly" aftertouch is one value per key or pad. |
| CC (control change) | A numbered knob/fader/button message: "control 105 is now at 87". |
| Absolute | The control sends where it **is** (a fader at 3/4 sends about 95). |
| Relative | The control sends how far it **moved** (64 = no move; above 64 = clockwise, below = counter-clockwise). Knobs that never end work this way. |
| Touch CC | The faders and knobs feel your finger. Touching sends its own CC, before anything moves. |
| SysEx | Long, maker-specific messages. Arturia's start `F0 00 20 6B 7F 42` and end `F7`. We use them to colour lights and write the screen. |
| LED id | The number the colour message uses to pick a light: 0-33 buttons, 34-93 pads. |
| Pad selector | The 3-position pad mode control on the device: left Arturia Program, middle DAW, right Default (your words, 2026-10-22). |
| Pickup | A fader "catches" a value only when it crosses it, so nothing jumps (FL's script does not do this; design D2 does). |
| Governor | Our speed limit on light messages: at most 12 per 100 ms. About 36 at once froze the device. |
| SSE | The one-way live feed the VJ engine serves on `127.0.0.1:8794/api/events`; pages listen to it. |
| Uniform | A number a shader reads each frame (colour, intensity, speed). Faders and knobs are meant to drive these. |

---

## Part 1. The map

Row ids (K1, F2, ...) are used by the morning census in Part 3.

### Keys (88)

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| K1 | 88 keys, note on/off | MIDI port, ch 1 (Part 1's channel), Note On / Off; A0-C8 = notes 21-108 at octave 0 | Same: the keys stay on the MIDI port in DAW mode | **CONFIRMED** (2026-10-22: chordview read your chords live from the MIDI port, ch 1, in DAW mode; README "Ports" row). Note range **INFERRED** | VJ `note`/`hit`/`chord` events; chord tools (chordview, the piano page); FL plays the selected channel |
| K2 | Key velocity | 1-127; global Key Velocity curve {Linear, Log, Exp, Fixed, Custom} plus a Fixed value | Same | Arrives: **CONFIRMED** (every note-on chordview read carries it). Which curve is set: **UNKNOWN** | Hit size, particle burst, bloom; a "hard hit = flash" threshold |
| K3 | Key aftertouch | Device file has Key Aftertouch curve, Part Aftertouch On/Off, Aftertouch Min/Max/Sensitivity, so the keys sense pressure. Most likely channel pressure (one value, `Dn vv`) on the part channel | Same, MIDI port (INFERRED) | **INFERRED** that it exists; message form and whether it is switched on: **UNKNOWN** | Lean into a chord to swell glow or bloom, hold a visual "breathing"; vibrato-like shader wobble |
| K4 | Octave - / + | Shifts the notes the keys send, -3 to +3 octaves (Part setting). LED ids 32 / 33 | Same | Effect **INFERRED**; whether pressing sends anything to the computer: **UNKNOWN** | A scene "zoom" if it reaches us; otherwise just keep chord views octave-blind (they already are) |
| K5 | Transpose - / + | Shifts by semitones (Part setting -11..+11). LED ids 30 / 31 | Same | Effect **INFERRED**; sends anything: **UNKNOWN** | Chord tools name what is **sent**, so a transpose renames the chord; show "Trans +2" on the screen if it reaches us |
| K6 | Parts / split | Part 1 and Part 2 each have lowest/highest key, channel, octave, semitone, and per-part switches for wheels, aftertouch, Hold, Chord, Arp, Scale | Same | Settings **INFERRED** (device file); how you pick a part on the panel (there is no "Part" LED id): **UNKNOWN** | Split the keyboard: left hand drives scenes (bass zone = scene select), right hand plays the chord the visuals read |

### Wheels

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| W1 | Pitch wheel | Pitch bend (`En lsb msb`, 14-bit, centre 8192), active channel, MIDI port | Pitch bend. FL's DAW-port script registers a pitch-bend handler, so it may also appear on the DAW port | Numbers **INFERRED**; which port in DAW mode: **UNKNOWN** | Hue bend, chromatic split, camera tilt that springs back to centre |
| W2 | Mod wheel | CC 1, 0-127 (factory; can be set to RPN/NRPN in a User program) | CC 1 (FL's DAW-port script handles CC 1 too) | **INFERRED**; port in DAW mode **UNKNOWN** | Turbulence, grain, motion amount: a "how wild" lever that stays where you leave it |

### Pedal inputs (the 88 has four jacks' worth of settings)

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| S1 | Sustain | CC 64, gate (0 off / 127 on; Toggle is an option) | Same, MIDI port (FL's script never handles CC 64) | A pedal is plugged in and was pressed ("sustain doesn't have any effect though", you, 2026-10-22; CC 64 handling shipped that day). The CC number on the wire: **INFERRED** | Chord tools: notes held by the pedal count (already built). VJ: freeze the frame / hold the scene |
| S2 | Expression | CC 11, continuous 0-127 | Same | Numbers **INFERRED**; whether a pedal is plugged in: **UNKNOWN** | Foot crossfade between two scenes; master intensity with both hands busy |
| S3 | Aux 1 | Global "Aux Pedal": type {Off, Control, Switched Control, Note, Program Change}, channel, CC or note, values | Same | Setting exists **INFERRED**; factory default and whether a pedal is connected: **UNKNOWN** | Strobe, blackout, next scene (a footswitch is perfect for "next") |
| S4 | Aux 2 | Global "Aux 2 Pedal", same options (this is the only surface difference between the 88 and the 49/61) | Same | As S3 | Second footswitch: previous scene, or tap tempo |

### Pads (12 physical pads, 3 across x 4 down: printed `9 5 1 / 10 6 2 / 11 7 3 / 12 8 4`)
> **Erratum, 2026-10-23:** this layout is the 2026-10-22 photo read sideways. On the unit the pads are 4 across x 3 down, `1 2 3 4 / 5 6 7 8 / 9 10 11 12` (Daniel at the device); see [erratum-pad-grid-2026-10-23.md](erratum-pad-grid-2026-10-23.md).

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| P1 | Pad hit, selector middle, FL running | (n/a) | **DAW port, ch 10, Note On notes 0-11**. FL's script reads notes 0-7 as sequencer steps and 8-11 as page select, so pad *n* is most likely note *n*-1 | Notes on the DAW port: **CONFIRMED** (2026-10-23, beathand: "pad hit = note 11 on channel 10"; receipt `hand-20261023-002520.json` holds 1,115 taps with notes 2-11, which beathand only accepts from the DAW port). Exact pad-to-note order: **INFERRED** | The VJ's trigger pads; tap tempo (built: beathand) |
| P2 | Pad hit, selector middle, FL closed (we connect) | (n/a) | **UNKNOWN**. FL sends an extra "pad MIDI port" setting at start (property 0x14 = 1) that we never send, so without FL the pads may stay on the MIDI port with notes 36-47 | **UNKNOWN** | Decides what the VJ engine listens for when FL is closed |
| P3 | Pad hit, selector left or right | MIDI port, ch 10. Bank A: pads 1-4 = notes 44-47, 5-8 = 40-43, 9-12 = 36-39 (36-47 in all). Bank B +12 (48-59), C +24 (60-71), D +36 (72-83) | (n/a) | **INFERRED** (factory template; FL remaps these to FPC and Drumaxx) | Drum kits (D7), 48 looks across 4 banks (D3) |
| P4 | Pad velocity | 1-127 through the global Pad Velocity curve {Linear, Log, Exp, Fixed, Custom}; Pads Sensitivity {Low, Medium, High} | Same | Arrives: **CONFIRMED** (beathand counts only note-ons with velocity > 0). Curve and sensitivity set: **UNKNOWN** | "Velocity shapes effects" (your VJ ask): soft = glow, hard = burst |
| P5 | Pad pressure | Device file has a Pad Aftertouch curve and pad Aftertouch Min/Max, so the pads sense pressure. Poly (one value per pad, `An`) or channel (`Dn`): unknown | Same; FL's script never reads it | Exists **INFERRED**; form and port: **UNKNOWN** | Hold a pad and squeeze to sustain and grow the effect; release to fade ("hold sustains") |
| P6 | Bank - / Bank + | Steps the pads through banks A-D (each bank its own notes and stored colour). LED ids 17 / 16 | Unknown whether the DAW bank is part of the cycle | Bank function **INFERRED**; whether pressing reaches the computer: **UNKNOWN** | Bank = scene set, if it reaches us; otherwise screen-button tabs (D3) |
| P7 | Pad selector (3 positions) | Left = Arturia Program, right = Default | Middle = DAW (live colour needs it) | Positions: **CONFIRMED** (your words and the live colour tests, 2026-10-22). Whether moving it sends anything, and which notes each position sends: **UNKNOWN** (probe step `p17`) | Detect "pads left DAW mode" and say so on the screen instead of going dark silently |
| P8 | What FL does with pads | Banks A-D notes go to FPC or Drumaxx when that is the selected channel | **Pads 1-8 toggle step-sequencer steps on release; 9-12 switch the step page** | **INFERRED** from FL's script (and recorded as a hazard in memory 2026-10-23) | A VJ hazard: with FL's script on, DAW pads 1-8 write into your pattern. Use banks A-D for VJ while FL runs, or give our own FL script (D8) a "VJ" handoff mode |

### Faders (9) and their touch sensors

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| F1 | Faders 1-8 | MIDI port, CC **73, 75, 79, 72, 80, 81, 82, 83**, absolute 0-127, active channel | DAW port, ch 1, CC **105-112**, absolute 0-127 | **INFERRED** both (template; FL script) | Shader uniforms (intensity, hue, speed, glow, grain...), the VJ mixer of layers, a colour picker (3 faders = lightness, chroma, hue) |
| F2 | Fader 9 | CC **85** | CC **113** | **INFERRED** | Master intensity or master fade-to-black; or the scroll bar for long lists (D4) |
| F3 | Fader touch | Template says Touch Sensitive = On; what touch sends in MIDI mode: unknown | CC **28, 29, 30, 31, 33, 34, 35, 36** for faders 1-8 (32 is skipped), CC **37** for fader 9; most likely 127 on touch, 0 on release | DAW **INFERRED**; MIDI **UNKNOWN** | "Peek": touch shows the target name and value on the screen before you move anything; touch-and-pick binding (D2) |
| F4 | Fader resolution | 7-bit (0-127). A User program can set a fader to RPN/NRPN; whether that gives 14-bit values | 7-bit | 7-bit **INFERRED**; NRPN 14-bit **UNKNOWN** | If NRPN is truly 14-bit, shader moves get 128 times finer (no stepping on slow fades) |

### Knobs (9 endless encoders) and their touch sensors

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| N1 | Knobs 1-8 | MIDI port, CC **74, 71, 76, 77, 93, 18, 19, 16**. Factory "Global Mode" = **Absolute** 0-127; options Relative Main / Alt 1 / Alt 2 | DAW port, ch 1, CC **91, 92, 94, 95, 96, 97, 102, 103**, **relative**: 64 + n clockwise, 64 - n counter-clockwise | **INFERRED** both | The best shader control there is: relative means no jumps, ever. Fine trim of the fader's uniform, or 8 more uniforms |
| N2 | Knob 9 | CC **17** | CC **104**, relative | **INFERRED** | Global hue rotation, scene speed |
| N3 | Knob touch | Template: Touch Sensitive = On; MIDI-mode message unknown | CC **8-15** for knobs 1-8, CC **38** for knob 9 | DAW **INFERRED**; MIDI **UNKNOWN** | Peek and bind, as F3; "second press" help on a long touch |
| N4 | Turn speed (acceleration) | Global Acceleration {Slow, Medium, Fast}: faster turns send bigger steps | Same | Setting **INFERRED**; the actual step sizes: **UNKNOWN** | Map step size to the descriptor's `step` so a slow turn is precise and a fast spin sweeps |

### Main dial and Back

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| D1 | Dial turn | CC **114**, active channel; Acceleration Medium | CC **116**, relative. FL's script only acts on 65-72 (clockwise) and 55-63 (counter-clockwise) and ignores speed | **INFERRED** | Browse scenes, looks, presets, the chord history; with our own acceleration (D4) |
| D2 | Dial click | CC **115**, switched 0 / 127 | CC **117** (FL acts on press only) | **INFERRED** | "Load this scene" / commit |
| D3 | Back (beside the dial) | Fixed function, message unknown | CC **40**. LED id 29 | DAW **INFERRED**; MIDI **UNKNOWN** | Up a menu level, undo the last scene change |

### Transport and command buttons (12, all with RGB LEDs)

In MIDI mode these are fixed-function (not in the editable surface); what they send there is **UNKNOWN** for all
twelve. The DAW column is FL's script map. FL acts on some only on release (Play, Record, Metronome, Loop) and
Undo / Redo only on press.

| # | Button | DAW mode CC | LED id | Evidence (DAW) | What we could do with it |
|---|---|---|---|---|---|
| T1 | Play | 21 | 6 | **INFERRED** | Start the VJ show / timeline; Play LED pulses on the beat |
| T2 | Stop | 20 | 7 | **INFERRED** | Freeze or blackout |
| T3 | Record | 22 | 5 | **INFERRED** | Start capturing the VJ show (events + audio on one clock) |
| T4 | Tap | 23 | 4 | **INFERRED** | Tap tempo for the beat engine (better than a pad). With FL open it also sets FL's tempo |
| T5 | Loop | 24 | 8 ("Repeat") | **INFERRED** | Loop the current 4-bar visual phrase |
| T6 | Rewind | 25 | 9 ("Backward") | **INFERRED** | Previous scene |
| T7 | Fast forward | 26 | 10 ("Forward") | **INFERRED** | Next scene |
| T8 | Metronome | 27 | 11 | **INFERRED** | Toggle the beat flash; LED blinks with the tracked beat |
| T9 | Save | 41 | 15 | **INFERRED** | Save the current look as a preset |
| T10 | Quantize | 42 | 14 | **INFERRED** | Snap scene changes to the next bar |
| T11 | Undo | 43 | 13 | **INFERRED** | Undo the last look change |
| T12 | Redo | 44 | 12 | **INFERRED** | Redo |

### Screen buttons (8 contextual buttons around the screen)

| # | Control | MIDI mode | DAW mode | Evidence | What we could do with it |
|---|---|---|---|---|---|
| C1 | Screen buttons 1-8 | Buttons 5-8: CC **60, 61, 62, 63**, switched 0 / 127, each with a stored colour (editable). Buttons 1-4: fixed function | CC **45-52** for buttons 1-8 (FL: Device, Mixer, prev / next pattern, Mute, Solo, unused, Arm). LED ids 21-28 | **INFERRED** both | Eight scene tabs, labelled on the screen (see Y6), the active one lit in its scene colour |
| C2 | Long press | Unknown | Unknown | **UNKNOWN** | A second layer of 8 tabs |
| C3 | Prog + 6th screen button | Enters the DAW program | (that is how you get here) | **CONFIRMED** (README; used every session) | Never bind Prog: it changes the keyboard's mode |

### Mode, menu and performance buttons

| # | Button | What it does on the device | Sends to the computer? | LED id | Evidence | What we could do with it |
|---|---|---|---|---|---|---|
| G1 | Prog | Picks the program (Arturia, DAW, User 1-6) | Unknown | 19 | Function **CONFIRMED** (C3); sends **UNKNOWN** | Leave alone (mode changes) |
| G2 | Settings | Device settings menu | Unknown; FL's script never uses it | 18 | **UNKNOWN** | Candidate "mode pin" button for our hub (D1), if it reaches us |
| G3 | MIDI | MIDI settings (parts, channels) | Unknown; unused by FL | 20 | **UNKNOWN** | Candidate mode pin |
| G4 | Hold | Latches held notes (per-part switch) | Unknown | 0 | Function **INFERRED**; sends **UNKNOWN** | If it reaches us: "hold the current look"; the LED shows it |
| G5 | Chord | Chord memory: one key plays a stored chord | Unknown | 1 | As G4 | Chord tools see the full chord it plays (good); show "Chord mode" on screen |
| G6 | Scale | Snaps keys to a scale | Unknown | 2 | As G4 | Our key detector could light this LED in the detected key's colour |
| G7 | Arp | Arpeggiator: held chord becomes a note stream | Unknown | 3 | As G4 | Arp notes make great particle trains; chord tools must read the held set, not the stream |
| G8 | Shift | No Shift appears anywhere: not in the LED list, not in the device file, not in FL's script | (n/a) | (none) | **UNKNOWN** (probably no such button) | (none) |

The device file also lists a global **"Apply MIDI FX"** switch and **"Arp Tolerance"**; whether Hold / Chord /
Scale / Arp change what reaches the computer depends on them (UNKNOWN).

### Output: the pad and button lights

| # | Light | How to set it | Evidence | What we could do with it |
|---|---|---|---|---|
| L1 | DAW-bank pads, LED ids 82-93 (pads 1-12) | `F0 00 20 6B 7F 42 00 02 03 <id> R G B 00 F7`, R/G/B 0-127; only with the selector in the middle (DAW) | **CONFIRMED** 2026-10-22 ("Keylab Unlocked!!!!!"; the 12-colour photo; chordview and beat light them live) | Everything visual on the device: chord roles, beat march, scene palette, pad previews |
| L2 | Request byte | 0x00 renders colour; 0x02 lights white and ignores colour; 0x04 (Bitwig's) untested | 0x00 / 0x02 **CONFIRMED** 2026-10-22; 0x04 **UNKNOWN** (probe `p5`) | Use 0x00 only |
| L3 | Speed limit | About 36 messages in one burst froze the device (power cycle). 12 per 100 ms is safe; send only changed pads | **CONFIRMED** 2026-10-22 | The governor already enforces it for every sender |
| L4 | Colour rendering | Saturated blue, purple, magenta, pink and red read clearly; amber, yellow, orange, lime wash toward white | **CONFIRMED** 2026-10-22 (photo) | Pick scene colours from the clear side; the gamut probe (`gamut`) will measure a safe table |
| L5 | Colour depth | 7 bits per channel on the wire; whether the hardware snaps to its stored 42-colour palette | **UNKNOWN** (probe `gamut`) | Smooth fades vs stepped fades on the pads |
| L6 | Banks A-D pad ids 34-81 | Same message. FL lights banks A and B dim blue at start and bank A in FPC's colours | Outside DAW position the pads ignore colour: **CONFIRMED** (README). Whether ids 34-81 ever render live: **UNKNOWN** | If they do, VJ pads could stay coloured while FL keeps the DAW bank |
| L7 | 34 button LEDs, ids 0-33 | Same message, full RGB. FL lights Play green, Record red, Loop amber, the rest grey | **INFERRED** (we have never lit a button) | Transport LEDs as beat lights; screen-button LEDs as scene colours; Scale LED as the key colour |
| L8 | Blink / pulse states | Arturia's code has no blink command; we blink by sending | **UNKNOWN** (probe idea P13) | Software blinking is fine within the speed limit |
| L9 | Stored colours (MCC) | 42-colour palette, per pad per bank, and a bank colour (factory: A white, B violet, C rose, D orange-red); written only by store / recall | **INFERRED** (template) | Make banks A-D look right when our software is not running |

LED id table (from Arturia's LedId): 0 Hold · 1 Chord · 2 Scale · 3 Arp · 4 Tap · 5 Record · 6 Play · 7 Stop ·
8 Loop ("Repeat") · 9 Rewind · 10 Fast forward · 11 Metronome · 12 Redo · 13 Undo · 14 Quantize · 15 Save ·
16 Bank + · 17 Bank - · 18 Settings · 19 Prog · 20 MIDI · 21-28 screen buttons 1-8 · 29 Back · 30 Transpose - ·
31 Transpose + · 32 Octave - · 33 Octave + · 34-45 pads bank A · 46-57 bank B · 58-69 bank C · 70-81 bank D ·
82-93 pads DAW bank.

### Output: the screen (3.5 inch, 320 x 480, colour)

The screen is a **layout engine, not a picture frame**: the computer picks one of the firmware's layouts and fills
in text (ASCII, up to 32 characters a line), colours (RGB 0-127 per line), a 0-127 bar, an icon number, or button
labels. No command for raw pixels exists in Arturia's list (INFERRED). That sets the ceiling for "realtime output
to screen": names, colours, bars and icons, updated about every 60 ms, not video.

Message: `F0 00 20 6B 7F 42 00 02 04 <screen id> <tagged fields> F7`.

| # | Screen id(s) | What it draws | Evidence | What we could do with it |
|---|---|---|---|---|
| Y1 | 12 | Two lines, full screen, each line its own colour; **stays up** | **CONFIRMED** 2026-10-22 ("beautifully, flawlessly rendered, 0 ficker!") | Chord name + function, scene name + BPM; the probe's question screen |
| Y2 | 23 (also 24, 25) | One-, two- and three-line popups; dismiss after about 1 s | 23 **CONFIRMED** ("Hello Daniel flashed for 1 second"); 24 and 25 sit in the same README row but the quoted receipt is for one popup | Flash a scene change or a bound target |
| Y3 | (timing) | A 60 ms colour cycle rendered with no flicker; faster spacing untested | 60 ms **CONFIRMED**; 20-40 ms **UNKNOWN** (probe `lcdspeed`) | The screen's frame rate ceiling for the VJ |
| Y4 | 28 knob, 29 fader | Parameter name, value text and a live 0-127 bar | **INFERRED** (`protocol.screen_param` is built; probe `screens` checks it) | **The shader screen**: touch a fader, see "Glow 64%" with a bar |
| Y5 | 30 pad, 31 full popup with icon, 10 / 11 one line (normal / inverted), 13 two lines inverted, 14 two lines big, 15 / 16 icon + 1 / 2 lines, 26 / 27 icon popups, 0 screen properties | Arturia's script draws all of these in FL | **INFERRED** | Big chord name (14), icon + scene name (16), "Connected"-style title card (31) |
| Y6 | 1-8 (labels), 9 (clear all) | A label above or below each screen button: type, line count, colour type, icon, RGB colour, two short text lines. Label slots 0-3 sit on buttons 5-8, slots 4-7 on buttons 1-4 | **INFERRED** (FL labels "PLUGIN", "MIXER" and mute / solo / arm icons this way) | Name the eight scene tabs on the screen itself |
| Y7 | (icons) | 86 large built-in icons (instrument types, Arturia instruments, FL logo, transport and edit symbols) and 22 small ones (arrows, mute, solo, arm, heart, search, mixer) | **INFERRED** (Arturia's icon list) | Scene icons without drawing anything |
| Y8 | 17, 18-19 carousels, 20-22 lists, 32 rename, 33 curve editor, 34 pitch wheel, 35 parameter gauge, 36 icon two sides, 37 welcome, 39 colour picker, 40 browser, 41-42 line keyboard, 45 three lines, 46 two small lines | Named in Arturia's list, never drawn by their FL script | **UNKNOWN** (probes P16 / P26 need a tiny verb first) | A real scrolling list for scenes (20-22), a native colour picker (39), a browser (40): big wins if they render |
| Y9 | 38 boot, 43 pedal calibration, 44 bootloader | Device procedures | **UNKNOWN; do not send** | None. Keep these out of every probe |

### Device-level facts

| # | Fact | Evidence | Why it matters |
|---|---|---|---|
| V1 | Two inputs and two outputs, "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW"; the Windows MIDI Service (midisrv) is running | **CONFIRMED** (measured 2026-10-22, and again 2026-10-23 for this record) | The VJ engine should open both inputs |
| V2 | FL and our tools share the DAW port; our pad colour lands and stays while FL's script is connected | **CONFIRMED** (probe P1, 2026-10-22 21:45) | Guest mode works: paint pads, never send connect / disconnect while FL is open |
| V3 | DAW handshake: `F0 00 20 6B 7F 42 00 02 05 01 F7` connect, `... 05 00 F7` disconnect. FL connects when its script loads and disconnects when FL closes | Bytes **CONFIRMED** (used live); FL's timing **INFERRED** | Only one side should own connect. Tonight that is FL |
| V4 | Device "DAW Protocol" global setting (11 choices) decides the DAW-mode map | **INFERRED** | If it is ever set to MCU or HUI, every DAW number above changes |
| V5 | Property messages (`00 02 00 ...`): FL sends "pad MIDI port" (item 0x14 = 1) at start, and "link" on / off for knob and fader slots 0-7 on touch and release | **INFERRED**; their visible effect **UNKNOWN** | Explains why FL's pads arrive on the DAW port; might switch the device's own value popups off |
| V6 | Identity: FL's script declares hardware ids `00 20 6B 02 00 0A 02 / 04 / 08 7F 7F 7F 7F` (the three mk3 sizes) | **INFERRED**; which one is the 88: **UNKNOWN** | A standard "who are you" request would let the engine recognise the 88 for sure |
| V7 | Five-pin MIDI in and out with routing switches (MIDI in to USB, USB to MIDI out, in to out, apply MIDI FX) | **INFERRED** (device file) | Hardware synths could join the show |
| V8 | Settings: display brightness, sleep after 5 / 15 / 30 min, each also as a **"Vegas"** variant (the device's own idle light show), welcome page, low-power mode | **INFERRED** (device file) | Our idle show should beat Vegas mode, and screen brightness is a knob for dark rooms |
| V9 | "Arturia mode" (Prog + Arturia, or dial click on an Arturia plugin): a matching connect message exists but FL's script never sends it | **UNKNOWN** which port and map it uses | Avoid while the VJ runs |

**Count:** 81 rows. **CONFIRMED** in full: 7 (C3, L1, L3, L4, Y1, V1, V2). **Partly confirmed** (one half
receipted, the other not): 12 (K1, K2, S1, P1, P4, P7, G1, L2, L6, Y2, Y3, V3). **INFERRED**: 40. **UNKNOWN**: 22.
Every fader, knob, dial, transport and screen-button number is INFERRED: that is what the morning census fixes.

---

## Part 2. What the map means for tonight's three goals

1. **FL's script already owns most DAW-mode controls.** While it runs, faders 1-8 move mixer volumes or plugin
   parameters, knobs pan, fader 9 / knob 9 set the selected track, Tap sets FL's tempo, screen buttons mute, solo
   and arm, the dial navigates, and DAW pads 1-8 write steps into your pattern. So the VJ can own the surface
   cleanly in three ways: with FL closed; with FL open but the VJ reading only keys, wheels, pedals and banks A-D;
   or, the real answer, our own FL script (design D8, your "custom script where we drive") with a **VJ hand-off
   mode** that leaves the faders, knobs and pads to us. Your ruling already says the faders should be
   unassociated by default.
2. **Two number maps, one engine.** Faders send 73, 75, 79... in MIDI mode and 105-113 in DAW mode; knobs are
   absolute in one and relative in the other. The VJ engine should open both inputs and translate both maps into
   one "fader 3 moved" event, so it works in whatever program the keyboard is in.
3. **Shaders from the KeyLab: the wire already half exists.** The param schema (`arsenal/web/lib/params.js`) gives
   every shader parameter a range, step and curve; First Light already has MIDI learn (a CC drives `hue` or
   `intensity`, `arsenal/web/first-light.js:763-843`); `protocol.screen_param` builds the fader / knob screen. The
   missing piece is design D2's small page helper (`arsenal/web/lib/keylab-client.js`, not built): it takes the VJ
   engine's `ctl` events, applies pickup for faders and step-per-click for knobs, and calls the page's own setter.
   The VFX Bench (`scripts/vfx.html`) is A12's file, so it gets a mount snippet, not an edit. Knobs are the
   shader-friendly control (relative, no jumps); faders need pickup.
4. **The screen's ceiling is text, colour, bars, icons and labels.** "Refined realtime output to screen" means
   using all of them well (Y1-Y7), at 60 ms or slower, and proving the native list and colour-picker screens (Y8).

---

## Part 3. The morning census (about 10 minutes, seven stops)

Goal: turn the INFERRED and UNKNOWN rows into CONFIRMED, faders and knobs first. You never type a number; the
screen asks, you answer on the pads (pad 1 = yes, pad 2 = no, pad 4 = skip), and every message is saved.

**Before you start (1 minute)**
- **Save and close FL Studio.** With FL's script running, every fader and button you touch would also act in FL
  (mixer, tempo, your pattern), and the probe sends the DAW connect and disconnect that FL owns while it is open.
- Plug in any pedals you own (sustain, expression, footswitches).
- Pad selector to the **middle** (DAW). Press **Prog + the 6th screen button** (DAW program).
- Open the Terminal panel beside this chat (so Vandor can read the output) and run `Set-Location E:\AI-Setup`.

Commands that stream use `py -u` so you see each message live while `Tee-Object` saves a copy. Files land in
`state\arsenal\keylab\receipts\`.

### Stop 1: The Sliders (about 4 minutes) — unlocks F1-F3, N1-N3, D1-D3, T1-T12, C1-C2, G2, G3, G8, Y4

```
py -m arsenal.keylab probe --only census,screens
```

- It first lights pads 1, 2 and 4 one at a time: hit each lit pad (this teaches it your yes / no / skip).
- Then the screen walks you through 13 short windows. Do exactly what it says, one control at a time: faders 1-9,
  touch fader 1 without moving it, knobs 1-9, the dial slowly right, fast right, slowly left, three clicks, each
  transport button, Back / Save / Quantize / Undo / Redo, screen buttons 1-8 in order, Bank - / + Settings MIDI
  Transpose - / +, hold screen button 8 for 2 s, and Shift if you find one. If Settings or MIDI opens a menu on
  the device, press Back to leave it.
- Then it draws a knob screen and a fader screen: answer pad 1 if you saw a bar and the word "Intensity".
- Receipt: `probe-<time>.json`, every message with its port, number and value.

### Stop 2: Do the faders talk without the handshake? (30 seconds) — unlocks part of V3

The probe just disconnected. Run this and move fader 1 up and down:

```
py -u -m arsenal.keylab monitor --port daw --secs 15 | Tee-Object state\arsenal\keylab\receipts\census-daw-nohandshake.txt
```

Lines with `CC d1=105` mean the VJ engine can listen without ever sending connect. Silence means it must connect.

### Stop 3: The Pads (1 minute) — unlocks P1, P2, P4, P5, P6, W1, W2 (DAW-port half)

```
py -m arsenal.keylab connect
py -u -m arsenal.keylab monitor --port daw --secs 40 | Tee-Object state\arsenal\keylab\receipts\census-daw-pads.txt
```

Within the 40 seconds: hit pads 1 to 12 in order, slowly; hold pad 1 and press hard for 2 seconds; press Bank +
then Bank -; move the pitch wheel and the mod wheel once. Nothing shows here? Stop 4 will catch the same controls
on the other port.

### Stop 4: The Expressive Bits (1.5 minutes) — unlocks K3-K5, G4-G7, W1, W2, S1-S4

```
py -u -m arsenal.keylab monitor --secs 60 | Tee-Object state\arsenal\keylab\receipts\census-midi-expressive.txt
```

In order: pitch wheel up and down; mod wheel up and down; hold one key and lean into it; each pedal you own
(sustain press, expression heel-to-toe, each footswitch); Octave + then a key, Octave - back; Transpose + then a
key, Transpose - back; Hold, Chord, Scale and Arp each on, play a key, then off again.

### Stop 5: The Selector (1 minute) — unlocks P3, P7

```
py -m arsenal.keylab probe --only p17
```

Hit the three lit pads again, then follow the screen: selector **left**, hit pad 1; **right**, hit pad 1;
**middle**, hit pad 1; answer "back in the middle?" with pad 1.

### Stop 6: MIDI Mode (1.5 minutes) — unlocks the whole MIDI-mode column of F1-F3, N1-N3, D1-D3, C1

Press **Prog** and pick the **Arturia** program (or User 1) on the screen. Then:

```
py -u -m arsenal.keylab monitor --secs 30 | Tee-Object state\arsenal\keylab\receipts\census-midi-mode.txt
```

Move fader 1 and fader 9; turn knob 1 right then left; touch knob 2 without turning; turn the dial right, left,
click it; press screen buttons 5, 6, 7, 8, then 1, 2, 3, 4. Afterwards: **Prog + the 6th screen button** to come
back to DAW.

### Stop 7: One look at the buttons (30 seconds) — unlocks L7

```
py -m arsenal.keylab led play red
py -m arsenal.keylab led chord blue
py -m arsenal.keylab disconnect
```

Is Play red and Chord blue? Tell Vandor yes or no (a photo is even better). Then reopen FL.

**Scoreboard.** All seven stops together settle about 50 of the 74 rows that are not yet fully confirmed (an
answer of "nothing arrives" settles a row too). Stop 1 alone moves the faders, the
knobs, the dial and every button into hard numbers, which is all the VJ engine and the shader helper need to be
built against real data instead of Arturia's script. Not in this census (still owed from W0, separate session):
the colour gamut photos (`gamut`), screen speed (`lcdspeed`), the burst kill drill (`burst`), and the native list,
colour-picker and browser screens (Y8, which need a small new verb first).

---

## Part 4. Demonstrations of the Arturia we could build

Each idea lists the controls it uses, what already exists, and what it still needs (including which census rows
must be CONFIRMED first).

1. **The Shader Desk.** Faders 1-8 drive the eight main uniforms of whatever look is on screen, knobs trim them,
   fader 9 is master intensity. Touching a control shows "Glow 64%" with a bar on the KeyLab screen; the screen
   buttons' LEDs take the look's colours.
   *Uses:* F1-F3, N1-N3, Y4, L7. *Built:* param schema, First Light's MIDI learn, `protocol.screen_param`, the VJ
   engine's `ctl` events (tonight). *Needs:* `keylab-client.js` with pickup (D2), census Stop 1 and 6.
2. **Scene Deck.** The eight screen buttons are eight VJ scenes, each named on the screen above its button with an
   icon (Y6, Y7) and lit in the scene's colour; the dial browses more scenes, dial click loads, Back returns.
   *Uses:* C1, D1-D3, Y6, Y7, L7. *Built:* scenes in the VJ page (tonight), SetLed. *Needs:* a label builder in
   `protocol.py` (the fields are listed in Y6), Stop 1.
3. **Chord Oracle on the screen.** Line 1: the chord name in its quality colour, big (screen 14). Line 2: its
   function in the current key (Roman or Nashville number), and the pads show each tone's role.
   *Uses:* K1, S1, Y1 / Y5, L1. *Built:* `chordview` (names chords, five pad schemes, sustain); the piano page's
   much stronger detector (`Theory.detect` with key bias in `arsenal/web/piano.js`, plus `keysig.js`,
   `nashville.js`, `spell.js`, `chordread.js`). *Needs:* one shared detector (move the naming into the VJ page
   and send results back, or port the piano's rules to Python).
4. **Key Finder lights.** A running key estimate lights the in-key pads dimly as a scale ring; out-of-key notes
   flash; the Scale button LED glows in the key's colour; the screen says "D-flat major, 82 %".
   *Uses:* K1, L1, L7 (Scale LED). *Built:* `keysig.js` on the piano page, chordview's pad mapping. *Needs:* the
   shared detector from idea 3, Stop 7 for the button LED.
5. **Touch-to-Peek.** Touch any fader or knob without moving it: the screen shows what it controls and its value.
   Keep touching for a second and it shows the help line (your second-press principle).
   *Uses:* F3, N3, Y2 / Y4. *Built:* the screen builders, the param schema's `help` field. *Needs:* touch CCs
   confirmed (Stop 1 and 6).
6. **Velocity Bloom.** Key velocity sets the size of each burst on the VJ page, key pressure keeps it glowing,
   the pitch wheel bends the hue and springs back, the mod wheel sets turbulence.
   *Uses:* K1-K3, W1, W2. *Built:* the VJ engine's `note` / `hit` events (tonight), the piano page's visuals.
   *Needs:* aftertouch and wheel ports confirmed (Stop 3 and 4).
7. **The VJ Drum Kit.** Pads fire looks: tap = one-shot whose size is the velocity, hold = sustain, squeeze =
   grow, release = fade; a choke pad kills the others; banks A-D give 48 looks. Each pad shows its look's colour.
   *Uses:* P1-P6, L1. *Built:* the VJ engine's pad events and `POST /api/pads` (tonight), the delta renderer and
   governor, design D3. *Needs:* P2 and P5 answered (Stop 3), and a safe pad bank while FL runs (P8).
8. **Beat-locked lights with a real Tap button.** The pads march to the music (built: `beat`, house tracker
   `beat_a`); the Tap button sets the tempo by hand; Metronome and Play LEDs blink on the beat; the screen shows
   "128 BPM · locked".
   *Uses:* T4, T8, T1, L1, L7, Y1. *Built:* `beat`, `beathand` (pad taps and fader nudge), `beatref`. *Needs:*
   T4 confirmed (Stop 1); with FL open the Tap button also changes FL's tempo, so this wants FL closed or our own
   FL script.
9. **Foot Control.** Sustain freezes the frame, the expression pedal crossfades between two scenes, footswitch 1 is
   strobe, footswitch 2 is next scene: both hands stay on the keys.
   *Uses:* S1-S4. *Built:* sustain handling in chordview, the VJ engine's `pedal` event (tonight). *Needs:* Stop 4,
   and to know which pedals you own.
10. **Colour Picker on the faders** (your preset-maker idea). Three faders pick lightness, chroma and hue; the
    pads preview the colour (snapped to what the LEDs can show); the screen shows the swatch, or the device's own
    colour-picker screen if it renders; Save stores it, a pad steps to the next colour.
    *Uses:* F1, P1, L1, Y1 / Y8 (screen 39), T9. *Built:* the param schema's colour type, design D6. *Needs:* the
    gamut probe for the safe-colour table, the Y8 probe for screen 39.
11. **The Browser.** The dial scrolls every saved look (VFX Bench presets in `design/vfx-presets.json`, the GLSL
    groups, piano looks) with acceleration; the pads preview each one's palette; click loads; Back returns.
    *Uses:* D1-D3, L1, Y1 or Y8 (native list 20-22). *Built:* the bench's `/vfx/presets`, the GLSL group index,
    design D4. *Needs:* Stop 1 for the dial; the list-screen probe for the native widget.
12. **Spectrum pads.** Twelve pads become a twelve-band meter of whatever is playing (low bands warm-safe red,
    highs blue), at most 15 frames a second; the screen shows song, BPM and energy.
    *Uses:* L1, Y1. *Built:* WASAPI loopback in `beatsync`, the governor, now-playing lookup. *Needs:* nothing
    from the census: buildable today.
13. **Chord-to-shader.** The chord's quality picks the shader palette (major rose, minor blue, dominant green,
    diminished violet: the colours chordview already uses), the root rotates the hue, added tones (7ths, 9ths)
    add sparkle or grain.
    *Uses:* K1, S1. *Built:* `QUALITY_COLORS` in `chordview.py`, the VJ engine's `chord` event (tonight). *Needs:*
    a page-side mapping only.
14. **Vegas, but ours.** An idle show that beats the device's built-in "Vegas" sleep mode (V8): slow house-palette
    waves on the pads, a gentle colour title card on the screen, and it wakes the moment you touch a key.
    *Uses:* L1, Y1, Y5. *Built:* `show`, `rainbow`, the delta renderer. *Needs:* nothing: buildable today.
15. **Practice lights.** The pads hint the next chord of a progression (dim suggestion lights that leave on the
    next bar); the screen shows the target and turns green when you play it.
    *Uses:* K1, L1, Y1. *Built:* the piano page's chord-tree model and `cadence-live.js`. *Needs:* the shared
    detector from idea 3.
16. **The Mirror.** The piano page's 3D KeyLab twin (`arsenal/web/piano/instruments/keylab88mk3.js`) moves its
    faders, knobs and pads with the real ones, so viewers of a stream see your hands on the device.
    *Uses:* everything above. *Built:* the twin model (its pad layout is still 2 x 6; the real grid is 3 x 4, see
    `protocol.GRID`). *Needs:* the census numbers and the VJ engine's `ctl` / `pad` feed.
17. **Show recorder.** Record arms a capture of every control event alongside the audio, on one clock, so a
    performance can be replayed, edited and rendered to video later.
    *Uses:* T3, all inputs. *Built:* `beat --save` already keeps audio and taps on one clock; the piano page's
    recorder. *Needs:* T3 confirmed, and events written by the VJ engine.

## Open after this record (for whoever picks it up)

- The census receipts, once you have run them, turn this map's INFERRED rows into CONFIRMED rows. This file is the
  2026-10-23 record; a dated successor should carry the updated map rather than editing this one.
- Three questions only you can answer: which pedals you own (S2-S4), whether a Part / split button exists on your
  panel (K6), and whether you want FL closed during VJ sets or our own FL script with a VJ hand-off mode first (P8).
