# KeyLab 88 mk3 surface map (15-agent RE swarm: device JSON, templates, firmware, arsenal model, web)

> Provenance: Claude Code workflow `w1liu0xo1`, run 2026-10-22 by claude (Vandor) for Daniel, reviewed by claude before filing.
> Raw per-lane results: `keylab-mk3-surface-map-2026-10-22.raw.json` in this folder. Status: research record, not a ruling.

# KeyLab 88 mk3 — Surface Map & Build Report

*Synthesis of 7 verified fronts. Every claim tagged `mk3-confirmed` / `mk2-only` / `unclear`, and `LIVE` (host sets in real time) vs `STORED` (MCC store/recall only) wherever color or screen is involved. Open items framed as next-probes.*

**Device identity (mk3-confirmed).** Arturia KeyLab 88 mk3, 2024 gen-3. Device def: `C:/ProgramData/Arturia/MIDI Control Center/Resources/KeyLab3 88.json` — `name="KeyLab 3 88"`, `protocol="arturia_v4"`, `projectId=50`, `templateExtension=".keylab388"`, firmware `*.kl3`; `SKU="keylab-88-mk3"`, `usbProductId=718` live under `$.alternatives[0]` (not root). **Trap:** `productId="42"` and `familyId="0200"` are FAMILY-WIDE (mk1 `KeyLab_49_61.json`, mkII `KeyLab_mkII.json`, mk3 all share them) — NOT mk3 discriminators. A tool keying on productId 42 would also match the mkII. Key on `protocol=arturia_v4` + `.keylab388` + `.kl3`. The file literally named `KeyLab3.json` is the **49/61** mk3 (alt sku `keylab-49-mk3`/`keylab-61-mk3`, ext `.keylab3`); the 88 is the separate `KeyLab3 88.json`. `Keylab3_Essential.json` (Essential Mk3) is `protocol="arturia_v3"` — a DIFFERENT dialect; do not carry any 88 result onto it. mkII (`.led` firmware, `arturia_v2`) left untouched throughout.

---

## 1. CONTROL SURFACE (mk3-confirmed)

MCC-editable surface = **43 controls** (`KeyLab3 88.json $.controls`, `$.fields` count 976):

- **Keyboard** 88 keys; **Pitch wheel**, **Mod wheel**, **Sustain**, **Expression** (the 88 adds a second aux pedal — `globalFields` has `Aux Pedal` + `Aux 2 Pedal` vs the 49/61's single `Auxiliary Input`; this is the ONLY surface difference between 49/61 and 88, 963 vs 976 fields).
- **9 Encoders** + **Main encoder** (Tweak: rotate/click).
- **9 Faders**.
- **12 RGB pads × 4 banks (A/B/C/D) = 48 editable cells**, each its own itemType with its own note/CC/color. Pad note defaults (MPC layout, observed in `Default.keylab388` bank A): pads 1–4 = **44–47**, 5–8 = **40–43**, 9–12 = **36–39**; banks octave-shift 44/56/68/80. Default MIDI channel = **Ch.10** (drum). Each pad is a pure MIDI trigger: `Type ∈ {Off, Note, Switched Control, Program Change}`. **There is NO per-pad ADSR / envelope / sample field anywhere in the pad block** (fields 210–221 + Name).
- **4 screen/display soft-buttons** (DisplayButton5–8) — the only screen controls in the editable surface.
- **NOT in the editable surface** (fixed-function, firmware-driven): Transport, Chord, Scale, Arp, Hold, Oct, Trans, Prog, Bank, Settings, DisplayButton1–4. (Chord/Scale/Arp/Hold ARE present as per-Part toggles in `globalFields` Part 1/Part 2.)

**Velocity is GLOBAL, not per-pad.** `globalFields`: Global Curves → `Pad Velocity {Linear,Log,Exp,Fixed,Custom}`, `Pad Aftertouch`; PAD Settings → `Pads Sensitivity {LOW,MED,HIGH}`, Aftertouch Min/Max. The `Pads` aggregate itemType (id 93) owns `Velocity Curve`/`Aftertouch Curve` — one setting for all pads, still not per-individual-pad.

**Memories:** 8 slots `[Arturia, DAW, User 1..6]`; slots 1,2 locked/hidden; `force_store_recall_to_working_memory=1`. Device's ONLY declared actions: **`store`, `recall`** (no `sync`).

**Hardware spec (mk3-confirmed via Arturia product page, host-led-crux front):** 3.5" **320×480** full-color screen with 8 contextual buttons; 12 velocity/pressure-sensitive RGB pads.

---

## 2. COLOR VERDICT — the headline

The naive files-only answer was "unknown, needs hardware." The **firmware strings change that** — split the verdict by target:

### Screen live-draw — **GREEN** (host sets LIVE over SysEx)
Firmware `C:/Users/L5/Downloads/KeyLab3_FW__1_5_0.kl3` contains an INBOUND SysEx parser for the LCD. Header bytes **`F0 00 20 6B 7F 42`** confirmed at offsets 0xb47f8, 0x31a7f0, 0x581114 (`00 20 6B` = Arturia mfr id). Inbound parse diagnostics prove the device receives and parses host-sent screen commands: `"unknow parameter in button of SysEx42 Display"` @0xc22b0, `"unknow parameter in screen properties"` @0xc22f4, `"unknow screen Id in SysEx42 Display"` @0xc2400, `"Color param is too short, stopping parser"` @0xc224c; screen IDs `kl3::WidePopup/GenericFullscreen/SmallPopup/EmptyScreen/BigPopup` @0xc0eb4–0xc117c. Present in both 1.5.0 and 1.2.1 images. This is host→device real-time **screen** drawing with colored on-screen buttons + text. **Scope: LCD only — no `pad` token in this parser region.** Caveat: parser existence is firmware-proven; an end-to-end render still deserves a bench capture to confirm the command set.

### Pad LEDs in DAW mode via MCU/HUI/CC — **GREEN** (host lights pads LIVE)
Firmware confirms a live pad-LED driver fed by host contexts: `"PadLedDispatch opened"` @0xb6c18, `"PadLedCtx"` @0x748468, `"LedStrip queue is full !"` @0x865988, `"DAWControl opened"` @0x748816, `"TrackControlMCUHUI opened"` @0x748964. So the host **can** light pads in real time through the MCU/HUI/CC feedback channel in DAW mode.

### Arbitrary per-pad RGB (Launchpad programmer-mode style: any pad, any of ≥42 colors, anytime, independent of the DAW protocol and of store/recall) — **YELLOW**
This is THE VFX question and the evidence cannot yet settle it. Negative firmware check (all count 0 in 1.5.0): `programmer`, `Programmer`, `PadRGB`, `pad rgb`, `set pad`, `SetPad` — **no Launchpad-style arbitrary-pad command string exists**. The `arturia_v4` param-write wire format is compiled into MCC/firmware, not in any readable config. Pads demonstrably CAN be lit live (driver confirmed), but whether color is host-*selectable per pad* or fixed-per-DAW-function, and whether any path exists outside MCU/HUI, is undecidable from strings. **Must bench-test.**

### MCC pad-color editing — **STORED-ONLY** (not a live path)
Color is two stored params per cell: `Colour` (Bank=0/Custom=1, paramId 210) + `Custom Colour` (STATIC_COLOR_LIST idx 0–41, paramId 211, shown only when Colour=Custom). Written only via `store`/`recall` into memory slots. `KeyLab3 88.json $.actions=["store","recall"]`; MCC.exe strings: `"Synchronization unsupported for this device. Prefer using Store/Recall."`, `"overwrite the working memory"`. Proof color persists: `Default.keylab388` key `100_283` interpretation — and in template terms `29_210=0, 29_211=40` (pad1 bankA = Bank mode, custom idx white). **Do NOT read store/recall ability as evidence for or against live SysEx — different channel.** The 42-index palette is the ceiling for *stored* color; whether a *live* path is clamped to 42 or allows 24-bit is unknown.

**Bottom line for Daniel:** Screen VFX = go now (GREEN). Pad-light VFX in DAW mode = go now (GREEN, via MCU/HUI/CC — color may be function-bound). Free-form "chord-on-pads, any color any pad" = YELLOW, one hardware capture away from a yes/no.

---

## 3. CONFIG FORMAT — `.keylab388` (mk3-confirmed, generate programmatically)

Files: `Templates/KeyLab 3 88/Factory/Default.keylab388` (899 keys, 14876 B), `.../Komplete Kontrol.keylab388` (14894 B).

- **Encoding:** UTF-8, **CRLF**, **tab-indented**, flat object. **NOT strict JSON — trailing comma before the final `}`.** Head: `{\r\n\t"device": "KeyLab 3 88",\r\n\t"version": "1.0.6",`. Tail: `...\r\n}` after a trailing comma. → custom-serialize or post-process (append `,` before close; a strict `json.dumps` will not round-trip).
- **Keys:** `"<group>_<paramId>": int` and `"STRING_<group>_<paramId>": "text"`.
- **Pad cells:** each pad = 4 consecutive groups (banks A/B/C/D). **Pad1 = groups 29–32.** Within a pad-bank group, paramId offsets:
  `210 Colour · 211 Custom Colour · 212 Type · 213 Note · 214 CC Number · 215 Program Number · 216 MIDI Channel · 217 Option · 218 Off Value · 219 On Value · 220 Bank LSB · 221 Bank MSB`.
- **Set a pad color (stored):** `"<grp>_210": 1` (Custom) + `"<grp>_211": <0..41>`. If `_210=0` (Bank) the custom index is ignored.
- **Palette (42 fixed ARGB `0xAARRGGBB`, alpha always FF):** 0=red `FF0000`, 8=green `01FF00`, 18=magenta `FF00FF`, 23=blue `0000FF`, 40=white `FFFFFF`, 41=grey `D0D0D0`. Same list drives button colour (paramId 790).
- **Trap:** the `10` on every default pad is `_216 MIDI Channel = Ch.10`, NOT a color.
- **Global:** `"0_1"` velocity curve (`5`=Global in `Default`); `deviceGlobalParametersId=64`; 5 custom curves.
- **Caveat on "defaults":** the schema `default` key read `null`; values like NOTE 44 / On 127 are *observed in the `Default.keylab388` template*, not a declared default — treat as sample, not spec.
- **Device schema reference:** `KeyLab3 88.json $.fields` (976, paramId→{name,type,list/min/max}), `$.controls` (43). Firmware image: `keylab-3-88_Firmware_Update_1.1.1.572.kl3` (7.2 MB, UNENCRYPTED — plaintext C++ symbols, fully analyzable).

---

## 4. FL STUDIO BUILD PATH (concrete)

Daniel = FL producer, non-programmer; Vandor drives the code. Core constraint from §1: **the hardware pads carry no sample/ADSR** — they are MIDI triggers only. So the instrument lives in software, and the keyboard is a controller + a light surface.

**(a) Sexy drag-drop pad sampler (per-pad color/velocity/ADSR).** Recommended: **standalone companion app + virtual MIDI port**, not a VST, not an FL MIDI script.
- Virtual port: **loopMIDI** (Windows) creates a port that bridges hardware ↔ app ↔ FL.
- The app owns the sampler (per-pad sample, ADSR, velocity curve, color UI) and the audio engine (or routes MIDI into FL's native **FPC**, which already does drag-drop + per-pad). Pads fire Note On (default Ch.10, notes 36–47 MPC) → app maps to voices.
- Why not VST: FL's custom-GUI VST path is heavy for a non-programmer workflow and awkward for drag-drop; why not FL MIDI scripting: too limited for a rich sampler UI and can't own a polished drag-drop surface.
- Stack fit: this is a natural extension of the existing web/Three.js arsenal (`arsenal/web/piano/...`) → Electron or a local web app with Web MIDI is the lowest-friction, best-looking route and reuses `keylab88mk3.js`.

**(b) Live LED feedback.** Two real channels, both firmware-confirmed, both gated by one code fix:
- **Screen:** send SysEx `F0 00 20 6B 7F 42 ...` (SysEx42 Display) — GREEN, but exact payload grammar needs one capture to lock down.
- **Pads:** MCU/HUI/CC feedback in DAW mode — GREEN for lighting, color-selectability YELLOW.
- **MUST-FIX code blocker:** both Web MIDI entry points request `sysex:false` (`piano.js:3803`, `piano/cues.js:1697`). No SysEx pad/screen control is reachable until these flip to `sysex:true` + a permission re-grant. An `output.send([status,d1,d2])` path already exists (`piano/cues.js:1536`) — confirmed in software, but it has never been shown to light a real pad, and today it can't carry SysEx.

---

## 5. THREE-FEATURE FEASIBILITY

**(a) Drag-drop sampler onto pads — GREEN.** Entirely software-side; hardware just sends Note On. No device limitation blocks it. Use loopMIDI + standalone app (or FL FPC). Per-pad notes/channels are fully known (§1, §3).

**(b) Color + velocity + ADSR UI — GREEN with one caveat.** Build it in the companion app's own state — nothing stops a rich UI. The caveat is *what maps back to hardware*: ADSR and per-pad velocity are **software-only** (hardware velocity is global, `globalFields` Pad Velocity; no per-pad ADSR exists). Pad **color** can be pushed to the app's virtual pads live today; pushing it to the *physical* pad LEDs live is the YELLOW item in (c).

**(c) Chord-on-pads VFX mode — YELLOW (virtual GREEN, physical YELLOW).** The software model is already built and verified: `arsenal/web/piano/instruments/keylab88mk3.js` models 12 pads as 2 InstancedMeshes in 2 rows of 6 (pitch-class order), two-layer backlit (body ×0.35 + HDR rim ×2.3), colored by `ctx.noteColor(60+pc, velocity)`, with an attack/release envelope and a chord-root LED; chord source of truth is `state.chord {name,nns,key}` from `piano.js lookChord`/`Theory.detect`; the 480×320-style screen canvas and 12-pitch-class-dot mask (`drawScreen`) are reusable for the physical screen. So **on-screen VFX = GREEN now.** Driving the **physical** pad LEDs with chord colors is YELLOW pending the one capture: whether arbitrary per-pad RGB is host-settable outside MCU/HUI. *Cross-family flags to carry:* the real 88's 2×6 pad geometry is only `[U]` in `spec.md:44` (count 12 is firm, physical/MIDI order is not); and `spec.md:86`'s "backlit through translucent edges" / tops-lit detail is `[R]` from one reviewer who may have described the **Essential Mk3**, so don't harden it as mk3-88.

---

## 6. HARDWARE TEST PLAN (settle every YELLOW)

Tools: **Protokol** (Arturia's own, free) or **MIDI-OX**, plus MCC and loopMIDI. Connect the KeyLab 88 mk3 over USB.

**Probe 1 — Capture a stored color-set SysEx (settles the MCC path + reveals the wire format).**
1. Open Protokol, enable SysEx view, select the KeyLab's USB-MIDI *and* "DAW/MCU" ports (log both).
2. Open MCC, connect to the KeyLab, open a User template.
3. Change ONE pad's Custom Colour (e.g. pad 1 → red idx 0 → green idx 8). Watch Protokol **before pressing Store**. → If a SysEx/param-write appears on color change *without* Store, that's a candidate **live** path (capture the exact bytes). If nothing appears until Store, the color only moves on store/recall (confirms stored-only, matches files).
4. Press Store to a User slot; capture the burst. Diff the two captures to isolate the color field.

**Probe 2 — The VFX question: can the host light an arbitrary pad an arbitrary color LIVE?**
1. In MCC/device, switch the keyboard to a **DAW mode** (MCU or HUI). Via loopMIDI, feed the KeyLab from a DAW or a tiny script.
2. Observe which pad LEDs the host lights and whether color is choosable or fixed-per-function (watch the `PadLedDispatch`/MCU feedback). Capture the messages the host sends that change a pad LED.
3. Separately, replay the Probe-1 color SysEx (if any) *outside* MCC via MIDI-OX "Send SysEx" and see if a pad re-lights with no Store. → A pad lighting from a replayed message with no store = **GREEN for free-form pad VFX**; nothing = stays YELLOW/likely MCU-bound.

**Probe 3 — Screen live-draw (upgrade firmware-inferred → observed).**
Send a minimal SysEx42 Display message `F0 00 20 6B 7F 42 ...` from MIDI-OX and watch the LCD. Start from the parser's screen IDs (WidePopup/SmallPopup/BigPopup/GenericFullscreen/EmptyScreen). Confirms the host can draw text/colored buttons live and lets you map the payload grammar.

**Probe 4 — Grounding checks.**
- Tap each default pad with Protokol open: confirm notes 36–47 and that `_216=10` really transmits on **MIDI Ch.10** (rule out an off-by-one vs `Active=0` in the list).
- Photograph/measure the physical pad grid: confirm 2×6 and the physical→MIDI order (settles `spec.md:44 [U]`).
- Note idle pad/button colors with nothing pressed (settles the idle-rim model).
- Confirm tops-lit vs edges-only on the real pads (settles the `[R]`/Essential-Mk3 ambiguity in `spec.md:86`).

**Probe 5 — Code prerequisite before any live test from the arsenal.** Flip `sysex:false → true` at `piano.js:3803` and `piano/cues.js:1697`, re-grant the Web MIDI SysEx permission, then retry the existing `output.send` path (`cues.js:1536`) against a captured command.

---

## What the evidence CANNOT yet show (next-probes, not verdicts)

1. **Free-form per-pad live RGB** — no firmware token for it (`programmer`/`PadRGB`/`set pad` all absent), but pads provably light live in DAW mode. Probe 1+2 decide it. *This is the single pivot for the chord-on-pads dream.*
2. **Live color depth** — stored model is 42 indices; a live path's depth (42-clamped vs 24-bit) is unknown. Probe 2.
3. **SysEx42 payload grammar** — screen parser is confirmed *inbound*; the exact command set is not yet mapped. Probe 3.
4. **arturia_v4 param-write wire format** — compiled into MCC/firmware, in no readable config; reverse from capture or from `keylab-3-88_..._572.kl3`.
5. **Physical pad geometry/order** on the 88 (count 12 firm; layout `[U]`). Probe 4.
6. **Essential Mk3** runs `arturia_v3` — a separate answer; never carry an 88 result onto it.

The two files that must never be conflated: `KeyLab3 88.json` (the 88, `arturia_v4`, `.keylab388`) is the only device source here; `KeyLab3.json` is the 49/61; `Keylab3_Essential.json` is `arturia_v3`; `KeyLab_mkII.json` is a different generation (`arturia_v2`, `.led`) and was not used for any claim.