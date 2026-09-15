# A1 brief: any-keyboard MIDI for /piano (alpha release, phase 1)

*For: Navi (build), Vandor (review and commit). Evidence: [census.md](census.md), section 2. Plan: [plan.md](plan.md). Do not start until Vandor posts "final heat done" on the bus, because the bake-off harness serves piano.js live.*

## Why

Daniel wants the alpha "designed to work with any midi keyboard or midi USB adapter". Web MIDI already handles hot-plug, velocity-0 note-offs, sustain and panic. The gaps are the defaults tuned to Daniel's Arturia KeyLab 88 mk3, and a MIDI status nobody can see.

## Scope

1. **Visible status.**
   - Show the MIDI state in the top bar, not only in the hidden HUD (`piano.js:3399,3974`; `piano.html:132`). The states: connected device name / no device yet / Web MIDI unavailable / permission blocked.
   - Clicking the status opens the device picker.
2. **Browser banners.** Each is dismissible and shown once:
   - **Safari:** no Web MIDI ("use Chrome or Edge").
   - **Firefox:** needs the site permission add-on.
   - **Permission denied:** how to re-allow it.
   - **No device:** "plug in a USB MIDI keyboard or adapter; computer keys and Demo work meanwhile".
3. **Deterministic device choice** (`piano.js:3334-3380`).
   - Prefer hardware ports over virtual or loopback ones (names containing loopMIDI, IAC, Virtual, Through, Midi Through, DAW).
   - Otherwise take the first port in a stable sort.
   - Remember the choice by name. If more than one candidate exists, show the picker rather than guessing.
   - Keep the KeyLab preference only in the house profile.
4. **Channel filter** (`piano.js:3405`). The default is omni. Add an "ignore channel 10 (drum pads)" toggle, on by default in alpha and off in house, plus a single-channel option. Persist all of it in localStorage.
5. **Sustain polarity invert** (`piano.js:3411`).
   - An auto-detect hint: if CC64 reads 127 at rest for more than 2 s with no notes, offer "Your pedal seems reversed — invert?".
   - A manual toggle, persisted.
6. **MIDI diagnostics panel.** Promote the hidden HUD readout (`piano.js:3417`): the last 20 messages as bytes and decoded, per-channel activity dots, and the device list.
7. **Neutral copy in the alpha profile.**
   - "Play the KeyLab" and "88 keys" (`piano.html:31,149`) become "Play your keyboard".
   - Read the profile from `GET /api/profile` (A0). Until A0 lands, default to the house copy.

## Out of scope

- MPE (channel, note) keying and CC66/CC67: LATER.
- Any server change (A0).
- Scheme or instrument visuals.

## Tests and verification

- **Unit (node):** feed synthetic MIDI byte streams through the page's `midiMessage` path.
  - A 49-key range (C2-C6) and a 61-key range.
  - Channel 10 pads, ignored by default in alpha, visible in house.
  - An inverted pedal (CC64 127 at rest) with invert on and off.
  - Note-on velocity 0 as note-off on several channels.
  - Two devices hot-plugged in either order, with the choice remembered.
- **Page:**
  - headless screenshots of each banner and of the diagnostics panel, portrait and landscape;
  - house behaviour unchanged: the existing piano tests pass (piano_keysig, theory_chordread, nashville_js, piano_spell), and the classic frame hashes match when the alpha profile is off.
- **GPU work:** headless only, under the GPU lock, bursts under 3 minutes. Never `chrome.exe --version`. Never touch port 8793.

## Rules

- Take the advisory lock on `arsenal/web/piano.js` (and piano.html/css) before editing, and release it when done; LS6 sheet-music work also needs that file.
- Keep the change additive and flag-gated. Do not delete functionality.
- No git state changes and no `scripts/mirror.py`. Vandor commits.
- Report back on the bus with: files, test counts, screenshot paths, and any keyboard behaviour you could not test synthetically. Daniel will try a second real keyboard in the A5 drill.
