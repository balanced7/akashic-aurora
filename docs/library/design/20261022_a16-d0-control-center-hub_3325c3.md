---
akashic_id: art_20261022_a16-d0-control-center-hub_3325c3
akashic_sha: 00d694afccf2
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d0-control-center-hub
gist: "A16 D0: the Control Center hub, one process owns the KeyLab; intents, layers, leases, SSE, MCP door, dead-man"
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:18"
updated: "2026-10-22T14:29:18"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d0-control-center-hub_3325c3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d0-control-center-hub

# A16 D0: the Control Center hub (the spine the other eight docs lean on)

Status: draft for Daniel's "that's right" · Arc A16 KeyLab Control Center · Track K, work package T2.
Charter: fences/a16-charter/reconciliation.md (V3 boundary, V9 hub ruling). The siblings D1-D8 reference
this doc's names (intents, layers, leases, control events) instead of re-defining them.

## The ask
- "Lets do its own service but have it be reachable from the UI of the piano server (unless you have a better idea)" (Q6)
- "Yes mcp door" (Q10) · "As fast as we can go, we can play with timings later" (Q11)
- "We need to tie in our UI work to incorperate the keylab, and for the vfx page and arsenal pages to interact
  with the keylab display with menus and adaptive beautiful coloring."

## What exists today (evidence)
- Every tool opens the port itself: chordview and beatsync each open "KeyLab 88 mk3 DAW" and each drop DAW
  mode on exit (arsenal/keylab/chordview.py, beatsync.py). Two at once would stomp each other.
- The burst ceiling is now a guarantee per process: every SysEx passes `governor.BurstGovernor`
  (arsenal/keylab/governor.py, ce02387f). Across processes nothing enforces it. That is the hub's first job.
- The piano server is stdlib `ThreadingHTTPServer` with SSE, not WebSockets, on :8793; `POST /api/piano/cue`
  pushes into pages and is loopback-only (research/.../evidence-pages-server-themes-2026-10-22.md §1, §3).
- The piano page reads the keys through **Web MIDI in the browser**, matching `/keylab/i` and not `/daw/i`
  (arsenal/web/piano.js:3779-3801). Whether our WinMM input can share that port with it is untested.
- The VFX Bench is served by the Bifrost UI on :8790 (scripts/bifrost_ui.py, A12's file, which DeepSeek owns);
  Shader Lab is on :8797 and refuses 8793 (arsenal/shaders/serve.py).
- The house MCP-door pattern is a thin FastMCP module run over stdio or `--http` (arsenal/media/door.py:1-38).
- No house service supervisor exists; services start by hand or via .claude/launch.json.

## Design

**One process owns the device.** `py -m arsenal.keylab serve` starts the Control Center on its own port.
The default is 8794, refusing 8793 the way Shader Lab does. It is the only process that opens the DAW output.
Every other tool (chordview, beat, pages, OBS bridge, agents) becomes a **client**: clients post intents and
subscribe to events.

**Wire:** HTTP + SSE, the house idiom and stdlib only.
- `POST /api/intent`: claim, release, set a layer, show an LCD screen, bind a control.
- `GET /api/events`: an SSE stream of control moves, pad hits, lease changes, and beat and chord events.
- `GET /api/state`: the current scene, leases, bindings and health.

CORS is open to loopback origins only, so the piano page (:8793), the Bifrost UI (:8790) and Shader Lab
(:8797) can talk to it directly.

**Reachable from the piano UI:** the piano's Studio drawer gains a "KeyLab" tab. It is a thin client of the
hub: connection state, who holds the keyboard, mode tabs, and links to the preset maker (D6) and the pad desk
(D7). The hub also serves its own full page at `/`. Any change to the piano page is a cross-arc edge into
media-suite, and it lands as a small module plus a mount point, not as logic inside piano.js.

**The scene, in layers.** The light the device shows is composed, never fought over. Bottom to top:
1. `theme`: the base palette (D6);
2. `mode`: whatever the foreground lease holder paints (D1);
3. `overlay`: transient things, such as a beat flash, a VFX one-shot, or colour ADSR (D7);
4. `alert`: the hub's own warnings.

Each layer is 12 pads + 34 button LEDs + one LCD request. The compositor picks per element, top-most non-empty
wins, and hands the frame to the renderer. The renderer is `PadRenderer`, which sends only what changed,
through one `BurstGovernor`.

**The LCD gets its own lane:** one screen at a time, and popups expire back to the persistent screen.
Spacing is at least 60 ms until probe P14 says otherwise.

**The input plane.** The hub reads the device's control input. Probe P2 settles which port carries the
controls in DAW mode. The hub normalises every message into a control event:
`{control: "fader3"|"knob5"|"dial"|"dial_click"|"pad7"|"ctx2"|"play"…, kind: "abs"|"rel"|"press"|"release"|"touch", value, velocity, t}`.
Control numbers come from research/.../evidence-control-map-2026-10-22.md:
- faders CC 105-113, absolute, with touch CC 28-37;
- knobs CC 91-104, relative around 64, with touch CC 8-15 and 38;
- dial: turn CC 116, click CC 117;
- transport CC 20-27 and 40-44;
- screen buttons CC 45-52;
- pads on channel 10.

Events go to (1) the lease holder's bindings (D2) and (2) every SSE subscriber.

**Keys stay where they are.** The hub does not take the keybed away from the piano page. If probe P25 shows
WinMM and Web MIDI can share "KeyLab 88 mk3 MIDI", features that need the keys (chord view) open it alongside
the page. If they cannot, the hub reads the keys and re-broadcasts them on SSE, and the piano page's input path
is changed only with Daniel's yes, because it carries the practice log's receipt-time contract.

**Leases.** Defined in D1. They are process-local inside the hub, because the hub is the single arbiter, so
no Redis is needed. Each claim gets a fencing token, and a write carrying a stale token is refused.

**Dead-man.** If the hub dies, the device keeps its last latched colours. So:
- the hub writes a heartbeat file every second;
- on a clean exit it blacks out the pads, restores the LCD and sends `daw_connect(False)`;
- on start it calls `resync()`, then repaints the whole frame;
- a watchdog started with the hub blacks the pads out within 2 s of a missed heartbeat.

**The MCP door.** `py -m arsenal.keylab.door` follows the house pattern of arsenal/media/door.py. Its tools,
each mapped onto the HTTP API:
- `keylab_status`
- `keylab_claim` and `keylab_release`
- `keylab_pads`
- `keylab_lcd`
- `keylab_bind`
- `keylab_events_tail`

It is registered by hand, `claude mcp add keylab -- py -m arsenal.keylab.door`, and it never opens the port.

**Speed.** "As fast as we can go." Intent in, packet out: the target is p95 under 5 ms on the host leg, and the
device leg is about 10 ms (probe P21 measures it). The governor is the only thing allowed to slow a frame, and
when it does, the hub coalesces: last write wins per pad, and the coalesce count is recorded.

## Requirements
- R0.1 MUST: exactly one process opens "KeyLab 88 mk3 DAW" for output while the hub runs. A second hub refuses
  to start and names the holder.
- R0.2 MUST: every packet to the device passes one `BurstGovernor`, shared by all layers and clients.
- R0.3 MUST: the layer compositor is pure (frame in, frame out) and pinned without hardware.
- R0.4 MUST: intents from a client whose lease is not the foreground lease change only that client's own layer
  state. They never paint the mode layer.
- R0.5 MUST: control events reach SSE subscribers in arrival order, each stamped with its receipt time.
- R0.6 MUST: a clean exit leaves the device in a known state: pads dark, LCD handed back, DAW connection off.
- R0.7 MUST: the watchdog blacks out the pads within 2 s of a hub crash.
- R0.8 MUST: CORS allows loopback origins only, and the server binds 127.0.0.1.
- R0.9 SHOULD: host-leg latency, intent to packet, stays under 5 ms at p95 with three clients connected.
- R0.10 MUST: the hub never breaks the piano page's key input. If P25 says the input cannot be shared, the keys
  stay with the page until Daniel rules otherwise.
- R0.11 MUST: the MCP door holds no device handle, and every tool goes through the HTTP API.

## Deliverables
- D0.1 `arsenal/keylab/hub.py`, covering port ownership, the compositor, leases and the input plane. Accepted
  when its pins (fake WinMM sink, fake clock) are green in a clean worktree and a second hub refuses to start.
- D0.2 `arsenal/keylab/serve.py`: the HTTP + SSE server. Accepted when a page on :8793 receives a fader event
  within 5 ms p95 (receipt) and can set a pad.
- D0.3 chordview and beat become hub clients. Accepted when both run at once, the beat march underneath the
  chord view, with no DAW-mode drop on either exit (photo or video receipt).
- D0.4 the watchdog plus the kill drill. Accepted when you kill the hub mid-show and the pads go dark in 2 s or
  less (video receipt).
- D0.5 `arsenal/keylab/door.py`, the MCP door. Accepted when an agent claims the pads, paints a frame and
  releases, with no port opened in the door's process.
- D0.6 the KeyLab tab in the piano's Studio drawer: a small module and a mount point, a cross-arc edge with
  media-suite. Accepted when the tab shows the holder and the mode and switches a mode.

## Probes it depends on
- P1: FL and the hub on the DAW port.
- P2: the control census; which input port carries the controls.
- P14: LCD spacing.
- P21: key-to-light latency.
- P24 (new): the sustained burst window. The governor's 12 per 100 ms is conservative; ramp the sustained rate
  until a freeze, then back off by a third. A dated receipt.
- P25 (new): can our WinMM input and the piano page's Web MIDI hold "KeyLab 88 mk3 MIDI" at once? Open the
  piano page, start chordview, play, and check that both see the notes.

## Open questions for Daniel
- Port 8794 for the Control Center, or another number you like?
- Should the hub start automatically when the KeyLab is plugged in (a scheduled task watching the USB device),
  or only when something asks for it?

## Out of scope
Sound (the R track), the FL script's internals (D8), and the content of each mode (D1-D7).
