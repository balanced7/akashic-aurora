---
akashic_id: art_20261022_keylab-lit-brief_98d71b
akashic_sha: 8d228a8a60ca
schema_version: 1
status: draft
type: brief
arc: A16
date: 2026-10-22
title: keylab-lit-brief
gist: "Brief for KeyLab Lit: Daniel's words verbatim, the intent, the one question (light-first?) and what his yes unlocks. DRAFT"
visibility: fleet
body_type: markdown
seats: [claude]
category: [conducting, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T09:47:00"
updated: "2026-10-22T14:21:33"
---
<!-- GENERATED PROJECTION of art_20261022_keylab-lit-brief_98d71b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# keylab-lit-brief

# KeyLab Lit: brief

## His words (2026-10-22, verbatim)

> "I've been feeling really guilty about having a $1300 keyboard and not using any of its fancy functions. If arturia refuses to build actually useful FL studio integration, we will build it ourselves."

> "perhaps we can even render to the pads as an extension of the keyboard VFX with a fun mode that displays the chord you are playing on the pads, that would be so sick!"

> "beautifully, flawlessly rendered, 0 ficker! can we make it be a renderable window for our VFX? what if we make a chord viewer straight on the keylab!!!"

> "We need to tie in our UI work to incorperate the keylab, and for the vfx page and arsenal pages to interact with the keylab display with menus and adaptive beautiful coloring. I am super excited to see what you all make!!!"

> "I want this thing we're building, low latency audio play space, where we can craft sounds and IMPORT them to FL, can you imagine the workflows and collaboration?"

> "I want the full vision, no shortcuts or hedges, every feature you could think of and want."

## Intent

The KeyLab 88 mk3 becomes the house's hands and second screen. Its pads, LCD and LEDs speak for every page you love (piano, First Light, Play, the VFX Bench) in one colour language. Its faders and encoders play those pages live. Later a low-latency room hosts your instruments and chains and round-trips them with FL.

**Done looks like this.** You open /piano or /vfx and the KeyLab lights up with the chord you are playing, in colours that read true on the real pads. The LCD shows menus that tell you where each control leads, and a fader moves the avatar. Nothing freezes the device, and nothing silently fights FL.

## Real constraints

- About 36 packets in one burst freezes the device; 12 is safe.
- Live colour needs the pad selector in its middle (DAW) position.
- Warm colours wash to white on these LEDs.
- `arsenal/keylab/` is still untracked.
- beatsync imports a GPLv3+ library into the Apache-2.0 repo. That is your call before the commit.
- Width: one build watch + one design watch (ORG.md:9-12,154).

## The one calibrated question

**Is the first build light-first?** That means landing the package, then the hub that owns the device, then /piano, /vfx and First Light driving the KeyLab's pads and screen with menus and colour (waves W0-W3). The Engine Room would run as probes only, on the side, until the light is in your hands. **That's right?**

## What "that's right" unlocks

- **W0:** the commit by named paths (after the aubio call), pinned facts and tests, the twin re-laid to the 9-5-1 grid, the warm-to-white colour fix, the LED-gamut photo, the stability ladder, and the LCD naming the test pattern.
- **W1:** the hub in `arsenal serve`, with the governor, leases, the scene and the input plane.
- **W2-W3:** the light language and the controller. Today's "tie in our UI work" ask lands there, along with the attention verb and the media path in the wake message.

It does **not** unlock any of these; each still needs its own yes:
- installs outside the repo (Carla, pip, the MIDI Services SDK);
- writing into FL's folders;
- registering the MCP door;
- anything public.

Full vision, ratification questions and probes: keylab-lit-vision-v2. Your asks are filed as W266-W292.
