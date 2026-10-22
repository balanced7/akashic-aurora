# KeyLab 88 mk3 — Surface Map & SysEx Protocol (v2, cross-verified)

Two independent passes agree: (1) Vandor read Arturia's own **FL Studio script** (readable Python, `…\Settings\Hardware\Arturia KeyLab mk3\`); (2) a 15-agent RE swarm read the device JSON, firmware bytes, `.keylab388` templates, our arsenal model, and community sources. Legal: Daniel's own hardware and files.
Status 2026-10-22: **envelope + handshake + per-pad RGB + screen parser = confirmed from source.** Physical pad response, live color depth, exact screen payload = one bench session away.

## ⚠ Device-file identity (don't conflate the family)
- **Your 88** = `C:/ProgramData/Arturia/MIDI Control Center/Resources/KeyLab3 88.json` — `protocol="arturia_v4"`, templateExt `.keylab388`, firmware `*.kl3`, SKU `keylab-88-mk3`.
- `KeyLab3.json` (no "88") = the **49/61** mk3 (`.keylab3`). `Keylab3_Essential.json` = **Essential Mk3**, `arturia_v3` (a different dialect — never carry an 88 result onto it). `KeyLab_mkII.json` = older gen, `arturia_v2`, `.led`.
- `productId=42` and `familyId=0200` are **family-wide** (also match the mkII) — NOT mk3 proof. Discriminate on `arturia_v4` + `.keylab388` + `.kl3`. (The `42` byte in the SysEx header below is still exactly what the mk3 FL script emits.)

## The envelope  (KL3Dispatch.py:66 — and firmware screen-parser header agrees)
```
F0 00 20 6B 7F 42  <payload>  F7
```
`00 20 6B` = Arturia mfr id · `7F 42` = device selector · `F0…F7` = SysEx bounds.
Firmware confirms the device PARSES this inbound (header found at firmware offsets 0xb47f8 / 0x31a7f0 / 0x581114; screen diagnostic strings "unknow screen Id in SysEx42 Display", "Color param is too short, stopping parser").

## Payload grammar  `[ reqByte, context, param, target, args… ]`
- **reqByte**: `0x00` or `0x02` observed (ack/cable flag? — test both)
- **context** (eIntegrationPatchId): `eArturia=1 · eDaw=2 · eVCol=13`
- **param** (eParamId): `eProperties=0 · eValue=1 · eString=2 · eSetLed=3 · eDisplay=4 · eConnection=5 · eBank=6 · eProgram=7 · eSoftConnection=8`

## Arm DAW mode  (KL3Connexion.py — the gate that makes LED/screen commands land)
```
enter : F0 00 20 6B 7F 42 00 02 05 01 F7        # req, eDaw, eConnection, 01
leave : F0 00 20 6B 7F 42 00 02 05 00 F7
```

## Set a pad/LED color, LIVE  (KL3Return.py:208 — Arturia's own code; THIS is the arturia_v4 param-write the swarm couldn't find in the binaries)
```
[ req, eDaw(2), eSetLed(3), <ledId>, R, G, B, 0x00 ]        # R,G,B each 0..127 (7-bit)
```
Example — pad 1 bank A, full green:
```
F0 00 20 6B 7F 42 02 02 03 22 00 7F 00 00 F7     # 0x22 = 34 = ePad1BankA
```
Colors come from `getPadColor()` (FL channel color → RGB triple), sent as three independent bytes ⇒ near-arbitrary color, NOT snapped to the 42-index palette *in the live path* (bench-confirm the hardware doesn't re-quantize).

## LED / pad id map  (LedId.py, eLedId)  — 0..93, eLastEntry 94
Buttons 0–33 (Hold0 Chord1 Scale2 Arp3 Tap4 Record5 Play6 Stop7 Repeat8 Backward9 Forward10 Metronome11 Redo12 Undo13 Quantize14 Save15 BankP16 BankM17 Settings18 Prog19 MIDI20 Contextual1-8=21-28 Back29 TranspM30 TranspP31 OctM32 OctP33).
Pads: Bank A 34–45 · Bank B 46–57 · Bank C 58–69 · Bank D 70–81 · Bank Daw 82–93.

## Screen (chord name + graphics)  — 🟢 firmware-confirmed inbound parser
`param = eDisplay(4)`; layouts in ScreenId.py (eScreenPad=30, eScreenColorPicker=39, eScreenParamGauge=35, 1L/2L/3L text, popups, list, browser…). Firmware screen IDs: WidePopup/SmallPopup/BigPopup/GenericFullscreen/EmptyScreen. Exact text payload bytes = read KL3Display.py (15 KB) / one bench capture.

## COLOR VERDICT (reconciled)
- **Screen live-draw** — 🟢 GREEN (firmware parser).
- **Pad LEDs lit live in DAW mode** — 🟢 GREEN (firmware `PadLedDispatch`/`PadLedCtx`/`DAWControl`/`TrackControlMCUHUI`) AND the FL `eSetLed` path.
- **Free-form per-pad arbitrary RGB** — 🟢 *very likely* (FL script does exactly this via `eSetLed`); bench confirms physical response + color depth. **This is the chord-on-pads pivot — and we're on the good side of it.**
- **MCC pad-color editing** — 🟡 STORED-ONLY (palette idx 0–41, via store/recall into a memory slot; a separate channel — not evidence about the live path).

## CONFIG FORMAT — `.keylab388` (generate programmatically)
`Templates/KeyLab 3 88/Factory/Default.keylab388`. UTF-8, **CRLF**, **tab-indented**, flat object, **NOT strict JSON — trailing comma before final `}`** (custom-serialize or post-process). Keys `"<group>_<paramId>": int` and `"STRING_<group>_<paramId>": "text"`.
Pad cells: **Pad 1 = groups 29–32** (banks A/B/C/D), then consecutive. Per-bank paramId offsets:
`210 Colour(Bank=0/Custom=1) · 211 Custom Colour(0–41) · 212 Type · 213 Note · 214 CC · 215 Program · 216 MIDI Channel · 217 Option · 218 Off Value · 219 On Value · 220 Bank LSB · 221 Bank MSB`.
Stored pad color = `"<grp>_210":1` + `"<grp>_211":<0-41>`. Pad note defaults (MPC, Ch.10): pads 1–4=44–47, 5–8=40–43, 9–12=36–39; banks octave-shift.

## HARDWARE CONSTRAINTS (build around these)
- **Velocity is GLOBAL**, not per-pad (globalFields Pad Velocity {Linear,Log,Exp,Fixed,Custom}; Sensitivity {LOW,MED,HIGH}).
- **No per-pad ADSR / no sample field on the hardware** — pads are pure MIDI triggers. ⇒ the sampler, per-pad velocity, and ADSR all live in OUR software.

## BUILD PATH (recommended)
Standalone **companion app + loopMIDI virtual port** (not a VST, not an FL MIDI script). App owns the sampler UI (per-pad sample/color/velocity/ADSR) + audio (or routes MIDI into FL's **FPC**). Pads fire Note On (Ch.10, notes 36–47) → app voices; app sends `eSetLed`/`eDisplay` SysEx back for pad+screen VFX. Lowest-friction + best-looking + reuses the Three.js arsenal (`arsenal/web/piano/instruments/keylab88mk3.js`, already models 12 pads + chord reactions): **Electron / local web app + Web MIDI**.
**CODE BLOCKER (fix first):** arsenal Web MIDI requests `sysex:false` at `piano.js:3803` and `piano/cues.js:1697` → flip to `sysex:true` + re-grant permission, or no SysEx can flow. Send path already exists: `piano/cues.js:1536`.

## BENCH TEST PLAN (settles every remaining unknown; tools: Protokol or MIDI-OX + MCC + loopMIDI)
1. **Capture a stored color-set**: in MCC change ONE pad's Custom Colour with Protokol (SysEx view) open; note if anything crosses the wire BEFORE Store (candidate live path) vs only on Store. Diff captures to isolate the color field.
2. **The VFX question**: switch to a DAW mode; replay our `eSetLed` pad-green bytes via MIDI-OX "Send SysEx" and watch the pad. Lights with no Store = 🟢 free-form pad VFX confirmed; also note whether color is full-range or clamped.
3. **Screen**: send a minimal `F0 00 20 6B 7F 42 … F7` Display message; confirm text/graphics draw; map the payload.
4. **Grounding**: tap each pad (confirm notes 36–47, Ch.10); photograph the pad grid (confirm 2×6 and physical→MIDI order — spec.md:44 is `[U]`); note idle colors; confirm tops-lit vs edges-only (spec.md:86 `[R]` may describe the Essential Mk3).
5. **Prereq**: flip the `sysex:false→true` blocker above before any live arsenal test.

## OPEN (next-probes, not verdicts)
Physical pad response · live color depth (42-clamp vs 7-bit) · exact SysEx42 Display payload · reqByte 0x00 vs 0x02 semantics · physical pad geometry/order · (Essential Mk3 is a separate `arturia_v3` answer).
