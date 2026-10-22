---
akashic_id: art_20261022_a16-d5-obs-from-the-keylab_004bd4
akashic_sha: bb4931c33105
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d5-obs-from-the-keylab
gist: "A16 D5: OBS from the KeyLab: scenes on pads, REC LED mirrors OBS, chapters with fallback, stream overlay"
visibility: fleet
body_type: markdown
seats: [claude]
category: [security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:20"
updated: "2026-10-22T14:29:20"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d5-obs-from-the-keylab_004bd4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d5-obs-from-the-keylab

# A16 D5: OBS from the KeyLab

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Wish W293 · Builds on D0, D1 (OBS mode), D2 (bindings).

## The ask
- "Can you think of how to tie in obs integration"
- "help our efforts of making engaging content" (the beat/chord research, earlier the same day)

## What exists today (evidence)
- **OBS Studio 32.2.2 is installed.** Its obs-websocket plugin is present, but its **server is off**
  (`server_enabled: false`), on port 4455, with auth required (research/.../evidence-obs-and-leases-2026-10-22.md §A1-2).
- **obs-websocket v5 offers:**
  - `SetCurrentProgramScene`;
  - `StartRecord` / `StopRecord` / `ToggleRecord` / `GetRecordStatus`;
  - `StartStream` / `StopStream`;
  - `CreateRecordChapter`, which works **only for Hybrid MP4** output since OBS 30.2;
  - the events `RecordStateChanged` and `CurrentProgramSceneChanged` (§A3).
- **Client licences:** `obsws-python` is GPL-3.0-only, so it is out. `simpleobsws` and `obs-websocket-py` are
  MIT (§A4).
- **The house already knows OBS's output files:** the filename stamps, the 6-track audio map and the encoder
  tag are parsed by arsenal/media (parse.py:24-34, probe.py:398). The house has no OBS remote control (§A5).

## Design

**The bridge** is a hub client, `arsenal/keylab/obs.py`, using `simpleobsws` (MIT). It connects to
127.0.0.1:4455. The password is read from `.secrets/obs.json`, which you fill once. The hub never reads OBS's
own config file and never logs the password. If OBS isn't running or the server is off, the LCD says so in one
line and nothing else changes.

**OBS mode (D1):** while OBS holds the lease, or as a tab you switch to:
- **Pads are scenes.** The first 12 scenes in OBS's scene list map to pads 1-12, coloured by your
  per-scene choice (D6), or by name hash until you pick. The live scene is bright and the preview scene
  breathes.
- **The transport row** drives OBS in this mode:
  - Record toggles recording;
  - Play starts and stops the stream, behind a long press so it is never accidental;
  - Tap drops a chapter marker.

  Outside OBS mode, transport goes to FL, as you ruled.
- **The REC LED mirrors OBS's real state** from `RecordStateChanged`, never from the button press. It is red
  while recording, breathing while starting or stopping, and off when stopped. If FL is also recording,
  "recording anywhere" stays red, and the LCD says which.
- **The LCD** shows the scene name and the recording time.
- **Chapter markers:**
  - **Supported output:** OBS uses Hybrid MP4. A marker lands with the current chord and song as its name, if
    the beat lane knows them.
  - **Any other format:** OBS refuses the marker, so the LCD warns you once, and the hub also logs a sidecar
    marker file next to the recording, which arsenal/media can read later. You still get chapters in the
    editor, either way.
- **Faders can bind to OBS source volumes or filter values** through D2, only if you bind them. Nothing is
  bound by default.

**The overlay.** The hub serves `/overlay`, a transparent page that you add once as an OBS **Browser Source**.
It shows the current chord, the song and artist (SMTC), and the BPM, with a pulse on the beat, all live over
SSE. It is styled from the current theme, and every element can be switched off.

## Requirements
- R5.1 MUST: use an MIT or Apache licensed obs-websocket client, never obsws-python.
- R5.2 MUST: the password lives in `.secrets/obs.json` only. It never reaches a log, the bus, the LCD or an
  event.
- R5.3 MUST: the REC LED and the LCD reflect OBS's reported state (events), not our requests.
- R5.4 MUST: streaming starts only on a deliberate gesture (a long press), never from a single tap.
- R5.5 MUST: a chapter request on a non-Hybrid-MP4 recording warns once and writes the sidecar marker
  instead.
- R5.6 MUST: when OBS is off or unreachable, the bridge stays quiet apart from one LCD line. No retry storm:
  back-off reconnects, at most one every 10 s.
- R5.7 SHOULD: the pad-to-scene switch reaches OBS's program in under 50 ms at p95 (OBS's own transition time
  excluded).
- R5.8 SHOULD: the overlay costs zero GPU when idle (CSS only, no canvas loop).

## Deliverables
- D5.1 obs.py and its pins. Against a fake obs-websocket server, the pins cover state mirroring, the long-press
  stream guard, the chapter fallback and the reconnect back-off. Accepted when they are green in a clean
  worktree.
- D5.2 OBS mode on the device. Accepted on video: you switch three scenes from the pads, start a recording
  (the REC LED goes red only once OBS says so), and drop a chapter.
- D5.3 the overlay page. Accepted with a screenshot of it in OBS during a take, with chord and BPM live.
- D5.4 sidecar markers read by arsenal/media. Accepted when First Light's Edit mode shows the markers on the
  take.

## Your one-time steps (only you can do these)
1. In OBS: Tools → WebSocket Server Settings → enable the server, and copy the password.
2. Put the password in `E:\AI-Setup\.secrets\obs.json`, as `{"password": "..."}`. Nothing asks you for it
   again.
3. Optional: set Settings → Output → Recording Format to **Hybrid MP4** so chapters land inside the file.

## Probes it depends on
- P27 (new): with the server on, does `CreateRecordChapter` succeed on your current recording format? Note
  the format name.
- P2: the transport CCs on this unit.

## Open questions for Daniel
- When you hit Record in OBS mode, should FL also start recording, so audio stems line up with the video, or
  stay separate?
- Overlay content: chord + song + BPM to start. Anything else you want on stream (the key, a mini keyboard,
  the pad grid)?

## Out of scope
Editing recordings (First Light's job) and streaming platform settings.
