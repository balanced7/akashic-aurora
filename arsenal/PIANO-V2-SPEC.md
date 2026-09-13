# Piano v2: sustain you can see, 60 fps recordings, schemes, and a practice log

Status: build contract, 2026-09-13 night. Extends the piano detour in `arsenal/PLAY-NIGHT-SPEC.md`.

Daniel, verbatim: "It looks awesome! can we also make it be sustain cc64 aware too? can we try a faster framerate of either 60 or monitor native. Can we try another visual scheme preset? we could have a piano and then have notes go up on a column up the screen, I want everyones ideas, perhaps if we log the notes as well you guys could eventually banter with me about music and music theory, there is a lot of stuff I do that I don't fully understand xD"

## What exists (read before building)

`arsenal/web/piano.js` is one ES module of about 1,690 lines on three.js r186. Its sections, in order:
- THEORY (pure; node-tested)
- colour, framing, key geometry, scene, keys
- trails: one instanced mesh; `trails.start/release/end`
- sparks: `burst`
- key motion, camera
- overlay: `drawLabel`, `drawStaff`
- the notes engine: `noteOn`, `noteOff`, `setSustain`, `allNotesOff`, with the `sounding` map
- MIDI: `onMidiMessage`
- computer keys, demo, audio input, recording (MediaRecorder), UI
- the loop (`renderFrame`)
- `window.__piano`

Sustain already exists at CC64 ≥ 64. It has no hysteresis, no polarity setting, and no on-screen state, and dense pedalled passages add up to a white wall that washes out the chord name and staff. The live render already runs at monitor refresh (about 240 Hz). The 30 fps limit is in recording: MediaRecorder picks H.264 Level 4.0, which caps 1080x1920 at about 30 fps.

## Hard rules

- **Daniel's page stays untouched.** Do not edit `arsenal/web/piano.html` or `arsenal/web/piano.js`. The new core is built as `arsenal/web/piano-next.html` and `piano-next.js`, served at `/web/piano-next.html`. Vandor swaps it in only after verification.
- **Server:** the running server on 127.0.0.1:8793 is Daniel's; never restart it. For live tests, start your own from the repo, for example `python -m arsenal serve --port 8795`, and stop it when done. Unit tests use ephemeral ports, as `tests/test_arsenal_serve.py` does.
- **Chrome:** always isolated, driven over CDP, with a temp `--user-data-dir` and `--mute-audio`. Always pass the three anti-throttling flags: `--disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling`. Use your assigned debug port, and close your Chrome when done. Never use the Claude app's browser pane.
- **Libraries:** only from jsDelivr, as ES modules, with an exact version you verified exists. Record the version in your report.
- **Git:** do not commit. Vandor commits after verification.
- **Privacy:** logs of Daniel's playing stay under `state/arsenal/` (git-ignored) and never leave the machine.

## Layout and owners

```
arsenal/web/piano-next.html, piano-next.js        [core]      copies of piano.html/js, rebuilt around the scheme host
arsenal/web/piano/schemes/neon-trails.js          [core]      today's trails + sparks, extracted behind the scheme interface
arsenal/web/piano/recorder.js                     [recorder]  WebCodecs 60 fps MP4, MediaRecorder fallback
arsenal/web/piano/recorder-test.html              [recorder]  a self-contained test page for the recorder
arsenal/web/piano/log.js                          [log]       browser client for the practice log
arsenal/performance.py                            [log]       session store + pure analyzer + CLI helpers
arsenal/serve.py (performance routes only), arsenal/__main__.py (performance subcommand only)   [log]
tests/test_arsenal_performance.py                 [log]
arsenal/web/piano/schemes/<new>.js                [scheme, phase B]  chosen from the ideas round
arsenal/lanes/piano_verify.mjs                    [phase B]   the piano receipt
```

## 1. The scheme interface (core)

A scheme is an ES module:

```js
export default {
  id: "neon-trails",                 // lowercase, digits, dashes
  name: "Neon Trails",
  create(ctx) { return instance; },
};
// ctx, provided by the core:
//   THREE, scene, camera, renderer, clock(), keyX(m), isBlack(m), noteColor(m, vel, target?), noteCss(m, vel, alpha?),
//   KEY: {first: 21, last: 108}, RAIL_Y, TRAIL_Z, framing: {id, width, height}
// instance:
//   noteOn(m, vel, t)          key pressed (m in 21..108, vel 1..127, t in page-clock seconds)
//   noteRelease(m, t)          key lifted while the pedal keeps the note sounding
//   noteEnd(m, t)              the sound ends: key up with pedal up, pedal lifted, a repeat strike, all-notes-off
//   pedal(down, value, t)      sustain changed (down after polarity and hysteresis; value is the raw 0..127)
//   update(dt, t, frame)       once per rendered frame, before the composer renders.
//                              frame = { info, sounding: Map<m, {held, vel, t0}>, pedalDown, framing }
//   resize(framing)            framing switched
//   setActive(on)              shown or hidden; a hidden scheme must not draw (it may keep state)
//   dispose()                  remove everything it added to the scene
```

Event guarantees from the core:
- every `noteOn` is followed by exactly one `noteEnd` for that strike
- a repeat strike ends the previous sound first
- `noteRelease` comes at most once per strike, and only before its `noteEnd`

The keys, camera, stage and overlay (chord name, staff) stay in the core and are shared by every scheme. Neon Trails must look and behave exactly like today's piano apart from the sustain changes below.

**Switching:**
- a scheme picker in the top bar, plus `S` to cycle
- persisted in localStorage `arsenal.piano.scheme`
- schemes load with dynamic `import()` from `./piano/schemes/<id>.js`, listed in a `SCHEMES` array in piano-next.js
- only the active scheme receives `update` and draws; every scheme receives note events, so switching mid-passage stays coherent

**`window.__piano` additions:** `schemes()` returns `[{id, name, active}]`; `selectScheme(id)` returns a promise of a boolean.

## 2. Sustain (core)

- **Hysteresis:** after polarity, the pedal is down at CC64 ≥ 64 and up below 40. Values from 40 to 63 keep the last state, so half-pedal chatter never flips it.
- **Polarity:**
  - The setting is `normal` or `inverted`, stored in localStorage `arsenal.piano.pedalPolarity`, with a top-bar toggle.
  - Inverted reads the value as `127 - value`.
  - Hint: if the first CC64 after binding an input reads down, and no note is played within 3 s, show a toast: "Pedal reads as held. If it isn't, flip Pedal polarity."
- **On screen:**
  - The overlay draws the sheet-music pedal mark (SMuFL `keyboardPedalPed` U+E650) beside the grand staff while the pedal is down.
  - On release it draws `keyboardPedalUp` (U+E655), which fades over 0.6 s.
  - Both are inside the recorded canvas.
  - The HUD shows the raw value and the down/up state.
- **Pedalled notes** (key up, still sounding):
  - keys keep a soft glow, as today
  - the staff draws their note heads hollow at 60% opacity, while held notes stay solid
  - the chord name still includes them, as today
- **No wash-out** (Neon Trails, and a rule for every scheme):
  - Brightness must not grow without bound with note count. Trail energy is scaled by `1 / sqrt(1 + heldAndSounding / 10)` through a per-frame uniform.
  - The overlay gets a soft dark readability plate behind the chord name and the staff, so they stay legible over any scheme.
  - **Acceptance:** during a dense pedalled synthetic passage (40 notes in 4 s across three octaves, pedal down throughout), mean luma inside the staff box stays below 0.6, and every note head on the staff is visible in the screenshot.
- **Recording:** see section 3. The pedal mark is part of the frame.

## 3. The recorder (recorder)

`arsenal/web/piano/recorder.js`:

```js
export async function createRecorder({ canvas, fps = 60, width, height, audioTrack = null, videoBitrate = 16_000_000 })
// resolves to:
//   kind: "webcodecs-mp4" | "mediarecorder"
//   start()
//   frame()                   call once per rendered frame after the canvas is drawn. The recorder paces to `fps`
//                             by wall clock and stamps frame n at n / fps seconds (constant frame rate)
//   stop()                    resolves to { blob, mime, kind, fps, frames, seconds, audio: bool, skipped }
//   stats()                   { frames, skipped, queue, kind }
```

**WebCodecs path:**
- **Video:** `VideoEncoder` with the first configuration that `VideoEncoder.isConfigSupported` accepts, trying `avc1.640033` (High 5.1), then `avc1.64002A` (High 4.2), then `avc1.4D0033`. Use `framerate: fps`, `bitrate: videoBitrate`, `hardwareAcceleration: "prefer-hardware"` and `avc: { format: "avc" }`. Insert a key frame every 2 s.
  - Frames come from `new VideoFrame(canvas, { timestamp: n * 1e6 / fps })`.
  - Backpressure: when `encodeQueueSize > 4`, skip the frame and count it in `skipped`. Never block the render loop.
- **Audio** (when `audioTrack` is given): `MediaStreamTrackProcessor` feeds `AudioEncoder`, AAC (`mp4a.40.2`) at 192 kbps if supported. Audio timestamps start at the first video frame's wall-clock time.
  - If AAC isn't supported, record video only and report `audio: false`. Don't silently switch containers.
- **Muxer:** MP4 via a pinned, verified jsDelivr ESM muxer (`mp4-muxer` or `mediabunny`), with the moov atom at the front.
- **Fallback:** if `VideoEncoder` is missing or no configuration is supported, wrap MediaRecorder as today and set `kind: "mediarecorder"`.

**Acceptance, using `recorder-test.html`** (an animated 1080x1920 canvas with a visible frame counter and moving bars):
1. Record 5 s at 60 fps in isolated Chrome and upload it through `POST /api/recordings?name=recorder-test` on your own server.
2. Check it with PyAV (Python 3.11): the codec is h264, `average_rate` is at least 58, there are at least 290 frames, and the duration is 5 s ± 0.25.
3. With Chrome's fake audio device the audio stream exists, and its duration is within 0.25 s of the video's.
4. Delete the test files afterwards.

**Budget:** recording must not drop the live render below 100 fps on this machine with nothing else on the GPU. Report it.

## 4. The practice log (log)

The goal: a local log of what Daniel plays, and a summary the agents can read, so they can talk music theory with him about his own playing.

**Client, `arsenal/web/piano/log.js`:**

```js
export function createPerformanceLog({ endpoint = "/api/performance", flushMs = 1000, idleCloseMs = 300000, meta = {} })
// returns:
//   noteOn(m, vel, t), noteOff(m, t), pedal(down, value, t), chord(info, t)
//     t in page-clock seconds; info = { name, notes: [names], root, bass } or null
//   flush(), stop()
//   session: string or null
```

- A session opens lazily on the first note. It closes after `idleCloseMs` with no events, and on `pagehide` (sendBeacon).
- Events batch every `flushMs`. A failed flush retries once, then drops the batch with a console warning, never an exception.
- **Events** (JSON) look like `{ "t_ms": int, "kind": "on"|"off"|"pedal"|"chord", ... }`:
  - `on`: `note`, `vel`
  - `off`: `note`
  - `pedal`: `down` (bool), `value` (int)
  - `chord`: `chord` (str or null), `notes` (list of str), `key` (str or null)
  - `t_ms` counts milliseconds since the session opened.

**Server, `arsenal/performance.py` + `serve.py` routes:**
- **`POST /api/performance/open`** takes `{meta}` and returns `{session}`.
  - The id format is `YYYYmmdd-HHMMSS-<8 hex>`.
  - It creates `state/arsenal/performance/<session>/session.json` (opened_at, meta, closed false, event_count 0) and `events.jsonl`.
- **`POST /api/performance/<session>/events`** takes `{events: [...]}` and returns `{accepted}`.
  - 400 for a malformed event, and nothing from that batch is written.
  - 409 if the session is closed, 404 if it is unknown.
- **`POST /api/performance/<session>/close`** writes `summary.json` and `summary.md`, then returns `{summary}`.
- **`GET /api/performance`** returns `{sessions: [{session, opened_at, closed, event_count, duration_s}]}`, newest first.
- **`GET /api/performance/<session>`** returns `{session, summary}`, with summary null until closed.
- `App(..., performance_root=None)` accepts the storage directory, so tests can use a temporary one.

**The analyzer, `summarize(events) -> dict`**, is pure and deterministic, with no theory invented beyond the numbers:
- **Basics:** duration, note count, notes per minute, lowest and highest note, pitch-class histogram
- **Key estimate:** Krumhansl-Kessler profiles over duration-weighted pitch classes, with the best key, its correlation, and the runner-up
- **Chords:**
  - a timeline that merges consecutive identical chord events, with durations
  - the top chords by time
  - chord-to-chord bigrams (progressions) with counts
- **Dynamics:** mean velocity, p10 and p90
- **Pedal:** percent of time down, presses per minute, mean down length
- **Timing:** an inter-onset-interval histogram, and a rough tempo from the most common IOI cluster between 60 and 200 BPM, labelled rough
- **Voicing:** mean notes per chord event, and mean spread in semitones from the lowest to highest sounding note

`summary.md` is a readable narrative built only from those numbers, ending with 3 to 5 questions for Daniel generated from the stats. Example: "You spent 38% of the session moving Fmaj9 → G9. What pulls you to that move?"

**CLI:**
- `py -m arsenal performance list`
- `py -m arsenal performance summary <session>` prints summary.md

**Acceptance:**
- pytest covers the analyzer on synthetic sessions (a C major I-V-vi-IV loop gives key C major with those four chords and their bigrams; pedal and dynamics numbers are exact on hand-built events)
- pytest also covers every route, including the 400, 404 and 409 cases
- a live round trip on your own server (open, events, close, summary.md exists) passes

## 5. Integration (phase B, after the ideas round)

Phase B builds the chosen scheme(s) into `piano/schemes/`, then wires the recorder (a 60/30 fps choice in the top bar), the log (on by default, with a visible "Logging" state and a toggle), and the schemes into piano-next.js. It then writes `arsenal/lanes/piano_verify.mjs` and runs the full receipt. Vandor swaps piano-next into piano after the receipt and review pass.
