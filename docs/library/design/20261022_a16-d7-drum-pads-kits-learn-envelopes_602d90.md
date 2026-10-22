---
akashic_id: art_20261022_a16-d7-drum-pads-kits-learn-envelopes_602d90
akashic_sha: a3306a24be52
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d7-drum-pads-kits-learn-envelopes
gist: "A16 D7: drum kit maps in one tap, two-press learn, velocity and colour ADSR, banks as kits, the Pad Desk"
visibility: fleet
body_type: markdown
seats: [claude]
category: [tooling]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:21"
updated: "2026-10-22T14:29:21"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d7-drum-pads-kits-learn-envelopes_602d90 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d7-drum-pads-kits-learn-envelopes

# A16 D7: drum pads: kit maps in one tap, learn mode, velocity and colour envelopes, banks as kits

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 (light and mapping) and track R, T5 (the Pad Desk sampler, after lights) · Q12 · Builds on D0, D1 (DRUMS mode), D6 (colours).

## The ask
- Q12: "When I tried it last I had to click to some program where you click on a pad then have to manually
  select which midi not it represents the whole interface sucks and is cumbersome. I want us to be able to
  assign either midi notes easily for easy mapping of drumkits without having to remap or make a custom map in
  each drum app."
- "I use addictive Drums 2, and may get GGD for kontakt, i also want to try recreating fruity fpc, it can be
  used as a starting point but I think we can come up with something better with a quick color select and
  decay for color adsr."
- Learn mode (press a pad, then press the key whose note you want): "yes this exactly".
- Where the map lives: "Lets try both, wont hurt to know more about how things work".
- Velocity per pad: "All of the above with a default curve we decide on later that is easy to adjust, perhaps
  adsr window with handles".
- Banks: "Lets do different kits and perhaps different instruments".
- From the morning: "drag and drop samples into on top of the pad … easily select color, velocity controlls as
  well as adsr settings".

## What exists today (evidence)
- Pads send notes on channel 10. The default notes are pads 9-12 = 36-39, 5-8 = 40-43, 1-4 = 44-47
  (`protocol.PAD_NOTE`), on the printed grid 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4 (`protocol.GRID`).
- Live pad colour works only in the DAW bank (ids 82-93) in physical DAW mode (README). So **banks must be
  virtual** (held by the hub) to keep colour on all of them.
- The device-side program write (Arturia's MIDI Control Center way) is probe P18 and unexplored. Do pad notes
  change with the selector position? That is probe P17.
- The light budget: the governor allows at most 12 packets per 100 ms (governor.py). An envelope on 12 pads at
  once has to share that.
- Arturia's FL script exposes no pad remapping. Our FL script (D8) can see each pad note before it reaches a
  channel.

## Design

**A kit map** is a small JSON file: a name, 12 pads × 4 banks, and for each pad the following fields:
- `{note, channel, label, colour, velocity, light_env, choke}`
- `colour`: from the theme (D6), with an LED value.
- `velocity`: one of `fixed n`, `played`, or `curve <id>`.
- `light_env`: the colour ADSR.

**Built-in maps, one tap each:**
- **General MIDI drums.** These are the standard numbers: kick 36, snare 38, clap 39, closed hat 42, open hat
  46, crash 49, ride 51, toms 41/43/45/47/48/50.
- **Addictive Drums 2.** It is read from your AD2 install's own MIDI map, never typed from memory (probe
  P28).
- **GetGood Drums (Kontakt).** The same, when you have it.
- **FPC default.** Read from FL's FPC preset on your machine (P28).

Choosing a map is one press in DRUMS mode: dial through the maps, then click. Every pad recolours to show the
kit's pieces: kicks one colour, snares another, hats another, and so on.

**Learn mode (b): press a pad, then press the key.**
1. In DRUMS mode, hold the LEARN tab (a screen button). The pads go dim.
2. Tap a pad. It blinks, and the LCD says "Pad 5 → press a key".
3. Press any key on the keybed. That note is assigned, the pad flashes its new colour, and the LCD shows the
   note's name and the piece's name from the active map, for example "D1 · Snare".

Holding LEARN, you can do all 12 pads in 24 presses. Learn also accepts a note played *by the drum app*,
for example AD2's own pad preview sent to our input, for apps that tell you a piece by playing it.

**Where the map lives (c, "try both"):**
1. **Hub-side.** This works today with no unknowns. Pads arrive at the hub, which re-emits each mapped note.
   - Inside FL, our script (D8) remaps the pad note before the channel sees it, so no virtual port is needed.
   - For standalone apps (AD2 standalone, Kontakt standalone), the hub sends on a **virtual MIDI port**
     ("Aurora Pads"). Windows MIDI Services provides that; Daniel approved the SDK install. The apps listen to
     it.

   **Cost:** the hub must be running.
2. **Keyboard-side** (probe P18). Write the notes into an Arturia user program, so the pads send them with
   everything closed. To find out how, we watch what Arturia's MIDI Control Center sends when it changes one
   pad note, then replay that ourselves. That is a reverse-engineering lane under the house's
   reverse-engineering method: your hardware, your software. If it works, "Save to keyboard" becomes a button.
   **Caution:** user programs may not carry DAW-mode colour, so the probe also checks what the pads look like.

**Velocity, per pad (d, all of the above):**
- **Fixed:** always the same value.
- **Played:** passes your velocity straight through.
- **Curve:** your velocity goes through a curve with **two handles**. You drag them on the page, or set them on
  the device with knobs 1-4 (x and y of each handle). Turning a knob shows a fader-bar view on the LCD, and the
  page draws the full curve.

The default curve is picked later, together, and it is one file: change it once and every pad set to
"curve: default" follows.

**Colour ADSR (the "decay for color adsr"):** each pad's light has an envelope on a hit.
- Attack: how fast it reaches full.
- Decay: how fast it falls back.
- Sustain: the level it holds while the pad stays down.
- Release: the fade after you let go.

It is edited with the **same two-handle window** as velocity, plus a sustain line. The peak brightness follows
the hit velocity, so soft hits glow and hard hits flash.

The light budget is respected by design:
- the hub's envelope scheduler shares the governor's 12-per-100-ms across all active envelopes;
- it renders fewer brightness steps when many pads are decaying at once, and the shape is kept while the
  steps get coarser;
- the newest hit always gets its attack frame first.

If probe P13 shows the firmware can pulse a pad itself, sustained glows cost one packet instead of a stream.

**Banks (e, different kits and instruments):**
- **Four virtual banks** of 12, A-D, switched with screen-button tabs or the bank buttons (P2). The pads
  repaint instantly, inside one governor window.
- **Each bank is its own kit or instrument with its own destination.** For example:
  - A = AD2 (FL channel "AD2", or channel 10 on the virtual port);
  - B = GGD in Kontakt;
  - C = the Pad Desk (below);
  - D = an instrument, such as chord stabs or one-shots on a synth.

  In FL, our script routes each bank to its own FL channel; standalone, each bank gets its own MIDI channel on
  the virtual port.

**The Pad Desk:** the FPC-like sampler, done better. **Track R, after lights.**
- Drag samples from Explorer or First Light's library onto a pad on the Control Center page.
- Per pad: sample, start and end, pitch, amp ADSR, the colour (quick select: a swatch row on the page, or
  pads 9-12 recent colours plus faders as in D6), the colour ADSR, velocity layers (up to 4 samples split by
  velocity), and choke groups (an open hat cut by a closed hat).
- A kit saves as one folder: the samples plus the JSON.
- Playback runs in the sound room's engine (the R track), so it works with FL closed. It can also export the
  kit to FL as an FPC preset, or as Slicex/channels (the FL round-trip lane).

The Pad Desk's sound needs the R track, so the light, mapping, learn and envelope parts above ship first.

## Requirements
- R7.1 MUST: a kit map switches in one gesture (dial and click) and repaints the pads in one governor window.
- R7.2 MUST: the AD2, GGD and FPC maps come from files on Daniel's machine (P28), never from memory. GM ships
  built in.
- R7.3 MUST: learn mode takes exactly two presses per pad (the pad, then the key) and confirms on the LCD with
  the note and piece name.
- R7.4 MUST: hub-side mapping works inside FL (via D8) with no virtual port, and standalone via a virtual port.
- R7.5 MUST: velocity per pad offers fixed, played and curve. Curves have two handles and a shared default.
- R7.6 MUST: colour ADSR never pushes the device past the governor. Under load, steps get coarser and the
  shape is kept (pinned with a 12-pad drum roll on a fake clock).
- R7.7 MUST: four virtual banks, each with its own map and destination, all with live colour in DAW mode.
- R7.8 SHOULD: pad hit to mapped note out stays under 3 ms p95 on the host leg (drums are timing-critical).
- R7.9 SHOULD: keyboard-side programs ship as "Save to keyboard" if P18 succeeds.

## Deliverables
- D7.1 the kit map model, the built-in GM map and the bank switching. Accepted when pins are green in a clean
  worktree.
- D7.2 learn mode. Accepted on video: you map 12 pads to an AD2 kit in under a minute.
- D7.3 hub-side remap: FL through D8, and standalone through the virtual port. Accepted when AD2 plays the
  right pieces from the pads in FL and standalone.
- D7.4 the velocity and colour ADSR editor, on the page plus knobs. Accepted on video: a drum roll with
  visible light decay, and no freeze.
- D7.5 probe P18, the keyboard-side program write. Accepted with a dated receipt either way.
- D7.6 the Pad Desk (track R, after lights). Accepted when you drag samples onto pads and play a kit with FL
  closed, with the latency number beside it.

## Probes it depends on
- P2, P13, P17, P18.
- P28 (new): locate AD2's and FPC's note-map files on this machine with the find verb, and read one map from
  each.
- P29 (new): can our FL script change a pad note before the channel hears it? A one-pad drill, folded into the
  P23 JamProbe session.

## Open questions for Daniel
- The light on a hit: should the whole kit piece family flash (every hat pad when one hat is hit), or only the
  pad you hit?
- For the virtual port, is the name "Aurora Pads" fine?

## Out of scope
The sound room's engine (the R track has its own docs) and the Commons (Q13, still open).
