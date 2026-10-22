---
akashic_id: art_20261022_a16-d8-fl-script-handoff_3384d8
akashic_sha: 557a047c6466
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d8-fl-script-handoff
gist: "A16 D8: our own FL script: we drive pads/screen/lights, FL keeps transport, faders free, three handoff modes"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:22"
updated: "2026-10-22T14:29:22"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d8-fl-script-handoff_3384d8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d8-fl-script-handoff

# A16 D8: our own FL script: we drive the surface, FL keeps transport, faders stay free

Status: draft for Daniel's "that's right" · Arc A16 · Track K (light-side handoff) feeding R (FL round-trip) · Wish W266 · Q5 · Builds on D0 (hub), D1 (leases), D2 (bindings), D7 (pad remap).

## The ask
- "If arturia refuses to build actually useful FL studio integration, we will build it ourselves."
- Q5: "lets make a custom modified script that has various handoff modes so we can have a one stop shop for
  all solution that doesnt require tip toing around fl"
- Then: "Lets do A custom script where we drive but fl integration works, i dont like all the aspects of the
  default integration so we can riff on the details"
- And: "Lets let the play pause controls work with FL but the fades for mixer is dumb, i want them
  unassociated so I can link them to whatever by default."

## What exists today (evidence)
- **Arturia's script** (in Daniel's FL user folder, Settings\Hardware\Arturia KeyLab mk3):
  - sends DAW connect on init and disconnect on deinit;
  - binds transport CC 20-27 and 40-44, faders to mixer strips, knobs to plugin parameters, and the screen
    buttons CC 45-52 to focus, preset and mute/solo/arm;
  - repaints pads and LEDs;
  - uses no Shift combos;
  - runs a second script on the MIDI port that forwards CCs to Arturia plugins.

  Source: research/.../evidence-control-map-2026-10-22.md §1-6.
- W266 (docs/WISHLIST.md:1781) gates our script behind the JamProbe drill (P23), because FL 26.1.3 lists
  freezes when scripts call FL functions.
- **Licence:** Arturia's file is their code. We read it for facts (numbers, ids, message shapes) and write our
  own, so the script can live in the public repo (reconciliation V10).
- **Probe P1** is still open: can FL and the hub both hold the DAW port?

## Design

**One script, house-authored:** `device_AuroraKeyLab.py`. It is installed into your FL user folder under
Settings\Hardware\Aurora KeyLab\, and you pick it in FL's MIDI settings in place of Arturia's for the DAW
port. Arturia's own files are left untouched, so switching back is one dropdown.

**What it does, by default (your rules):**
- **Transport works with FL:** play/stop, record, loop, metronome, tap, rewind/fast-forward, undo/redo and save,
  the way you'd expect.
- **Faders and knobs are unbound.** They are forwarded to the hub as control events, and you bind them to
  anything (D2), including an FL mixer track or plugin parameter if you want one: the script exposes FL
  targets the hub can bind to.
- **Pads, screen and lights are ours.** The script does not paint them. The hub does, so the KeyLab looks the
  same in FL as out of it. Pad notes go through D7's mapping, per bank, to the FL channel each bank targets.
- **Things worth keeping from FL,** offered as hub targets and modes rather than forced:
  - the selected channel's name on the LCD;
  - FL's pattern list for PERFORM mode (D1);
  - the beat indicator as a tab-LED pulse;
  - the mixer track colours as a theme source.

**Handoff modes**, switched from a screen-button tab or the pin combo's long press (D1):
1. **Aurora drives (default):** the hub owns pads, screen and lights; FL keeps transport.
2. **FL drives:** our script paints FL's state itself, for the times the hub isn't running. The script detects
   the hub's heartbeat. If there is none for 2 s, it takes over with a basic FL view; when the hub returns, it
   hands back.
3. **Aurora only:** FL ignores the keyboard entirely (for sound-room sessions with FL open in the background).

**Who writes to the port when FL is open (the P1 question):**
- **Shared:** if Windows MIDI Services lets FL and the hub share the DAW port, the hub writes directly and the
  script only reports.
- **Exclusive:** if FL holds the port, **the script becomes the hub's driver while FL runs.** The hub sends
  its frames to the script over a virtual MIDI port ("Aurora Link"), and the script writes them to the
  device, through its own copy of the burst governor.
- **Either way,** exactly one writer at a time, and the LCD shows which path is live.

**Talking to the hub.** FL's embedded Python is limited, so the link is MIDI, not sockets. Probe P30 checks
what FL's Python can import. Over the link:
- control events go out as short messages on "Aurora Link";
- frames and requests come back as SysEx;
- the script uses only FL's documented scripting modules.

Every FL call the script makes is first drilled in the JamProbe session (P23), one call at a time, because of
the 26.1.3 freeze reports.

**Riffing on the details.** This doc fixes only the defaults above. Everything else is a **binding or a
mode, not code:**
- the knobs follow the focused plugin;
- the screen buttons focus the mixer.

So we riff by changing presets, not by editing the script.

## Requirements
- R8.1 MUST: the script is house-authored. It contains no code copied from Arturia's files, and an
  attribution note says what was learned from where.
- R8.2 MUST: transport reaches FL. Faders and knobs reach the hub, unbound by default.
- R8.3 MUST: exactly one writer to the device at a time, shown on the LCD, in all three handoff modes.
- R8.4 MUST: the script's own writes pass a burst governor (12 per 100 ms, or P24's measured window).
- R8.5 MUST: when the hub's heartbeat is missing for 2 s, FL-drives takes over; when it returns, the script
  hands back.
- R8.6 MUST: every FL scripting call the script makes has passed the JamProbe drill (P23) before it ships.
- R8.7 MUST: install and uninstall leave Arturia's files untouched, and switching back is one dropdown.
- R8.8 SHOULD: pad-to-FL-channel latency through the remap stays under 3 ms p95.

## Deliverables
- D8.1 P1 and P23 receipts: shared vs exclusive, and which FL calls are safe, with you present. Accepted with
  dated receipts.
- D8.2 the script skeleton: transport, unbound forwarding, the heartbeat handoff. Accepted on video: transport
  drives FL, a fader moves a First Light uniform through the hub with FL open, and killing the hub hands the
  keyboard to FL within 2 s.
- D8.3 pad remap per bank to FL channels (with D7). Accepted when AD2 in FL plays from bank A while bank D plays
  a synth channel.
- D8.4 PERFORM mode on FL patterns (with D1). Accepted when a pad queues a pattern on the next bar.
- D8.5 the install verb `py -m arsenal.keylab fl-install` (and `fl-uninstall`). Accepted when a fresh install is
  visible in FL's MIDI settings and an uninstall leaves no trace.

## Probes it depends on
- P1: is the port shared or exclusive?
- P23: the FL freeze drill.
- P29: changing a pad note before the channel sees it (D7).
- P30 (new): which modules FL's embedded Python can import (MIDI only, or more?).

## Open questions for Daniel
- When the hub isn't running, what should "FL drives" show on the pads: FL's channel colours, or just dark?
- Do you want the LCD to show FL's selected channel name by default, or only on request?

## Out of scope
The .fst/.flp readers and writers and the mixer-preset round-trip (the R track's FL lane, W5 in the vision).
