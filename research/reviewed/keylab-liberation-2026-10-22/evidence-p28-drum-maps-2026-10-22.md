# Evidence: probe P28, the drum note maps on Daniel's machine (2026-10-22)

The final report of a read-only Explore agent (sonnet), dispatched by Vandor for A16 design doc D7 (drum pads).
Persisted unedited per the full-fidelity rule.

One reader's note from Vandor. The snare row reads "C#1–B0 | 37–47". Under the PDF's own convention
(C1 = 36), note 47 is B1, so "B0" there is a slip in the condensed table. The note NUMBERS are the authority.
Before the AD2 preset ships, its notes are re-read from page 1-2 of the PDF row by row.

---

## 1. Addictive Drums 2 — default MIDI keymap

Source: `C:\Users\L5\Documents\Addictive Drums 2\App\ADBV0002\Manuals\Addictive Drums 2 Keymap.pdf` (4 pages, dated June 2, 2021; read in full).

**Octave convention:** The PDF labels note 60 as "C3" and note 36 as "C1" (p.1–2: "C3 | 60 | Ride 1 | Tip", "C1 | 36 | Kick"). This is the C3=60/"Yamaha-Roland" convention (middle C = C3), NOT the common C4=60 (Steinberg/Logic) convention — be aware when re-mapping to another device that labels middle C as C4.

**Core kit-piece table** (note name / MIDI# / piece / stroke, condensed from the full 0–107 table on pp.1–4; "-" rows with no piece omitted):

| Note | MIDI | Piece | Stroke |
|---|---|---|---|
| C1 | 36 | Kick | — |
| C#1–B0 | 37–47 | Snare (main) | Rimshot, Open Hit, Rimshot(dbl), Open Hit(dbl), Shallow Rimshot, SideStick, Shallow Hit, RimClick, Hit A (Flexi 1) |
| D0–B0 | 26–35 | Snare | brushes-only sweeps/taps |
| C2 | 48 | HiHat | Pedal Closed |
| C#2/D2 | 49/50 | HiHat | Closed 1 Tip / Shaft |
| D#2/E2 | 51/52 | HiHat | Closed 2 Tip / Shaft |
| F2 | 53 | HiHat | Closed Bell |
| F#2–A2 | 54–57 | HiHat | Open A–D |
| A#2 | 58 | HiHat | Open Bell |
| B2 | 59 | HiHat | Pedal Open |
| C3 | 60 | Ride 1 | Tip (softer) |
| C#3/D3 | 61/62 | Ride 1 | Bell / Shaft (stronger) |
| D#3 | 63 | Ride 1 | Choke |
| F3/F#3 | 65/66 | Tom 4 | Open Hit / Rimshot |
| G3/G#3 | 67/68 | Tom 3 | Open Hit / Rimshot |
| A3/A#3 | 69/70 | Tom 2 | Open Hit / Rimshot |
| B3/C4 | 71/72 | Tom 1 | Open Hit / Rimshot |
| C#4–E4 | 73–76 | Flexi 1 | Hit B/C/D (misc percussion) |
| D#4 | 75 | Snare | Sticks |
| F4/F#4 | 77/78 | Cymbal 1 | Hit / Choke |
| G4/G#4 | 79/80 | Cymbal 2 | Hit / Choke |
| A4/A#4 | 81/82 | Cymbal 3 | Hit / Choke |
| C5 | 84 | Ride 2 | Tip (softer) |
| C#5/D5 | 85/86 | Ride 2 | Bell / Shaft (stronger) |
| D#5 | 87 | Ride 2 | Choke |
| F5/F#5 | 89/90 | Cymbal 4 | Hit / Choke |
| G5/G#5 | 91/92 | Cymbal 5 | Hit / Choke |
| A5/A#5 | 93/94 | Cymbal 6 | Hit / Choke |
| C6–G6 | 96–103 | Flexi 2 / Flexi 3 | Hit A–D (extra percussion) |

Below note 24 and above note 107 are unassigned, except low CC-style zone: A-2=9 HiHat CC Bell, G-2=7 HiHat CC Shaft, F#-2=6 Snare CCpos, E-2=4 Ride1 CCpos, D#-2=3 Ride2 CCpos (p.4).

**On-disk map files found** (via `py agent_cli.py find "midimap"/"keymap"/"MIDI map"/".map"` plus shallow listings of the requested AD2 folders):
- No file matched "midimap"/"MIDI map" inside the AD2 folders.
- `C:\Users\L5\Documents\Addictive Drums 2\External MIDI Files\GM\GM.AD2Map` — plain ASCII `{ key = value, ... }` format. This is an **input remap table for importing General-MIDI drum MIDI files**, not the native output map above. Its key structure: `MAP_KeyMap_036 = 1`, `MAP_KeyMap_038 = 3`, `MAP_KeyMap_040 = 2`, … (127 entries, index = incoming GM note number, value = AD2 internal stroke-type index 0–61), plus hi-hat/ride/snare position-controller and velocity-curve settings.
- `C:\Users\L5\Documents\Addictive Drums 2\00100\Pyle PTED06.AD2Map` — same format/structure, a third-party e-drum-module (Pyle PTED06) input map, user-saved under preset folder `00100`.
- `C:\ProgramData\XLN Audio\Addictive Drums 2\App\config.txt` and `...\LuaSystem` exist but are app config, not note maps.
- `C:\Program Files\XLN Audio\Addictive Drums 2` contains only the installer/icon, no map files.

## 2. FL Studio FPC — default pad layout

- `C:\Program Files\Image-Line\FL Studio 2026\Plugins\Fruity\Generators\FPC\FPC_Info.rtf` contains only one line: "A pad-based drum synthesizer." — no note map.
- `...\FPC\Data\MIDI\GM Drums.txt` lists GM percussion names 1–61 (High Q … Open Surdo) but is a name reference list, not a per-pad assignment.
- `...\FPC\Data\*.notelayout` (default.notelayout, FIRE.notelayout, Launchkey.notelayout, padKontrol.notelayout, "starts at C5.notelayout", trigger finger.notelayout) are binary/encoded, not human-readable text — confirmed by reading them (garbled bytes, not plain numbers).
- Preset files under `...\Data\Patches\Plugin presets\Generators\FPC\*.fst` (Default.fst, Acoustic/*, Electronic/*, Multi audio output/*) are binary FL "FLhd/FLdt" chunked preset files (verified via hex dump: `464c 6864` "FLhd" header) — not decoded, per instructions.
- `C:\Users\L5\Documents\Image-Line\FPC` only has empty Data subfolders (Envelopes/LFO/Maps/Samples) and a placeholder.txt — no user map files.
- No `.htm/.html/.pdf` manual documenting FPC's default note-per-pad assignment was found anywhere under the FL Studio 2025/2026 installs.

**UNCONFIRMED:** FPC's default 16-pad→MIDI-note assignment and any built-in GM-mapped preset are not documented in any local file found. Do not use a remembered note number for this.

## 3. GetGood Drums / Kontakt

- Kontakt **is installed**: `C:\Program Files\Native Instruments\Kontakt 8\Kontakt 8.exe`, VST3 at `C:\Program Files\Common Files\VST3\Kontakt 8.vst3`.
- GetGood Drums brand is present only as **"GetGood Drums The Nolly Bass Library"** at `D:\Libraries\GetGood Drums The Nolly Bass Library` — this is a bass-guitar library, not a drum library.
- No dedicated GGD *drum* Kontakt library (e.g., Elevate/Imperial/Modern & Massive) was found. All other `D:\Libraries\*KONTAKT*` entries are strings/brass/piano/vocal/guitar libraries (8Dio, Audio Imperia, Spitfire, ProjectSAM, etc.) — none are drum libraries.

**Conclusion for the KeyLab pad presets:** Use AD2's documented note map above (C3=60 convention) as the confirmed source. FPC's default pad notes are UNCONFIRMED from local files — do not derive KeyLab drum-pad presets for FPC from memory; if needed, open FPC itself to read the live assignment. No GGD/Kontakt drum library exists on this machine to map instead.
