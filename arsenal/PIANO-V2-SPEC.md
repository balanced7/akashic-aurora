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

- **Brightness, Daniel's rules (2026-09-13):** "notes dont stay lit if I have sustain pressed, when I hold sustain and other notes it should be brighest when I am pressing sustain and note at same time, velocity should be a factor as well". Then, after the first version stacked into a white wall: "Can you make the piano note colors more saturated and visible? also the bloom doesn't seem to decay or go down, it just stacks".
  - Loudness follows a struck string: a 1.7x strike that settles in about a quarter second, then a slow sag toward half (time constant 6 s) for as long as the note sounds.
  - State multiplies it: finger held with the pedal down is the brightest state, 1.45; finger held alone is 1.0; pedal-held is 0.8.
  - Every level is scaled by velocity: `0.35 + 0.65·v^0.8`.
  - A trail records this over time. Each stretch shows the loudness and state at the moment it left the key, so the stretch where the pedal went down is visibly brighter. When the sound ends, 82% of the light goes on 0.14 s and the rest on 1.2 s. A stretch dims on a 3.2 s afterglow as it rises and is gone 5 s after its note ended.
  - Keys and trails share one `LIGHT` object in piano.js: `lightLevel` drives key glow, and the same constants reach the trail shader as `#define`s. piano-next and every scheme must match.
  - Pitch colours are gamut-mapped to full saturation and pulled toward one shared luminance (spread 4.65x down to 1.71x), so velocity decides how bright a note is, not its name.
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
  - Brightness must not grow without bound with note count. Light older than 0.6 s shares a light budget (`LIGHT_BUDGET`, measured in screen-tall columns at full level). The budget dims old light first and never dims a fresh strike, a held key or its foot.
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

## 6. Phase B additions, from the design round

Sources, in `research/in-flight/piano-ideas-2026-09-13/`: `panel-synthesis.md` (six designers, three judges), plus the seats' ideas in `heimdall-deepseek.md`, `navi-kimi.md` and `sunshine-sol-handoff.md`.

### 6.1 harmonySet (THEORY, node-tested)

`Theory.harmonySet(sounding, t)` returns the notes that name the harmony:
- every finger-held note
- pedal-held notes struck within the last 1.5 s
- the lowest pedal-held note, when it is also the lowest sounding note, so a pedal point keeps its bass

`currentInfo()` detects over this set instead of every sounding key.

Tests:
- Riding the pedal from F major into G major names G, not a cluster.
- A pedalled low C held under a later right-hand chord still reads as the bass of a slash chord.
- Pedal up with nothing held returns an empty set.

### 6.2 Rules for every new scheme

- Solid means finger-held; hollow means pedal-held. Hollow never means dim: pedal-held notes stay clearly lit, per Daniel's brightness rule in section 2.
- Never sum light. Use normal blending in strict lanes, or merge each lane by maximum. No additive halos.
  - Neon Trails keeps its additive look behind the density guard, because Daniel loves it.
- Only attacks and finger-held cores may cross the bloom threshold. Pedal tails decay to a floor.
- A pedal lift is one visible clearing, and the pedal is drawn once, as its own object.
- The chord name and staff sit in a protected band that bright geometry fades out of before reaching.
- Everything is driven by the clock, never by frame counts.

### 6.3 Upright Roll: `piano/schemes/upright-roll.js`

This follows the panel's "Build first" plan.
- Instanced bars in two pools, black keys drawn over white, with normal blending and no halo or foot glow.
- The finger-held body is solid and stays under the bloom threshold.
- An onset cap's thickness shows velocity.
- Pedal tails are hollow, with alpha `0.7·exp(-age/1.5)` and a floor of 0.28.
- Sparks fire only above velocity 0.7.
- A 12 px amber pedal lane is pinned inside the left edge.
- In 9:16 the roll fades out before the top band (y 230–630) that holds the chord name and staff, and the key fronts sit at or above y 1520.
- Skip the odometer scroll and the camera elevation for now.

### 6.4 Harmonic Wave: `piano/schemes/harmonic-wave.js` (Navi's idea)

- Above the keys, one bloomed line shows the literal summed waveform of the harmony set's frequencies. The cycle is normalised, so the lowest note shows about three periods.
- Line thickness follows velocity.
- Pedal-held notes add in at half amplitude as a second, fainter strand, so the pedal stays visible.
- A chord change morphs over 150 ms.

### 6.5 Log additions (log.js and performance.py, compatible with section 4)

- **New event kinds:**
  - `sound_end`, with `by` set to `"release"`, `"pedal"`, `"repeat"` or `"all-off"`. This makes finger-held versus pedal-held a recorded fact.
  - `rec`, with `state` and `file`.
  - `mark`, a tick from a KeyLab pad learned once. It shows in the HUD only.
- **Chord events** also carry `bass`, `rolled_ms`, `pedal_across` (true when the pedal was held through the change) and `harmony_notes`.
- **The analyzer adds:**
  - pedal habits: chord changes re-pedalled after the new chord, changes ridden across, and the median lift offset
  - the share of rolled chords and the median roll time
  - key-relative numerals, with borrowed chords flagged
  - one question per session anchored to a timestamp, drawn from those facts
- **`summary.md`** follows the panel's card format: one line per fact, and every claim tied to a time Daniel can replay.

### 6.6 The receipt: `arsenal/lanes/piano_verify.mjs`

- **The pedal storm:** four octaves of pedalled arpeggios, 30+ notes under one pedal, run for every scheme.
  - Mean luma in the chord-name and staff band stays within 5% of the same band in silence.
  - For Upright Roll, no pixel crosses the bloom threshold outside the onset caps.
  - In 9:16 the key fronts sit at or above y 1520.
- A 5 s recording at 60 fps, checked with PyAV.
- A practice-log round trip.
- Scheme switching with no exceptions.
- A harmonySet check driven through `__piano.midiMessage`.
