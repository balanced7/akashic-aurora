# House bake-off: a dedicated Synthesia mode

Opened by Vandor, 2026-09-15 about 08:45 EDT. Entries are due about 11:45 EDT.

## Why

Daniel, 2026-09-15, verbatim, after trying the current page (Harmonic Compass mode: a neon grid, pale teal columns, saturated keys):

> "This looks like a decent start, I feel we have lost the original synthesia magic though. How can we make it look nicer? can we all try at a dedicated synthesia lookinf mode like the original?"

Earlier the same night, verbatim:
- "Can we also try some non squigly note line themes and ideas, I really liked your original design and am wondering what a beefed up version of that will look like, its easier to visually understand. I know we can find a way of making it look incredible"
- Relayed by Asta: "there is a reason synthesia and guitar hero look so good, make something to wow me please."

Earlier asks that still bind, verbatim:
- "Can you make the piano note colors more saturated and visible? also the bloom doesn't seem to decay or go down, it just stacks"
- "when I hold sustain and other notes it should be brighest when I am pressing sustain and note at same time, velocity should be a factor as well"

The house reconciliation (`fences/piano-presentation/reconciliation.md`) already names the foundation: **time, with a point of contact.** Straight bars rise from the exact key that played them, and a bar's length is how long the note sounded.

## The contract (everyone builds in the same slot)

An entry is a **scheme module**, the original piano v2 scheme host from `arsenal/web/piano-next.js` (lines about 450-610, and PIANO-V2-SPEC.md section 1).

- **File:** `arsenal/web/piano/schemes/synth-<seat>.js`, with `<seat>` one of asta, rill, navi, heimdall, sunshine or vandor. It is an ES module with no imports: everything comes from ctx.
- **Default export:** `{ id: "synth-<seat>", name: "<a short name>", create(ctx) }`. The id must match the file name.
- **ctx fields:** `THREE, scene, camera, renderer, clock, keyX, isBlack, noteColor, noteCss, KEY {first, last}, RAIL_Y, TRAIL_Z, framing {id, width, height}`.
- **Instance methods** (all required):
  - `noteOn(midi, vel, t0)`
  - `noteRelease(midi, t)` — the finger comes up
  - `noteEnd(midi, t)` — the sound ends (pedal lifted or decayed)
  - `pedal(down, raw, t)`
  - `update(dt, t, frame)` — `frame.view.top` is the world y where rising things leave the picture; `frame.view.pointScale` is also provided
  - `resize(framing)`
  - `setActive(on)`
  - `dispose()`
- **Draw only the music.** Keys, camera, stage and the text overlay belong to the host.
- **Prior art to read first:** `piano/schemes/upright-roll.js` (with its harness) and `piano/schemes/neon-trails.js`.

**Try your entry live:** open `http://127.0.0.1:8793/web/piano-next.html` (or your own server), then in the console:

```js
const m = await import('/web/piano/schemes/synth-<seat>.js?' + Date.now());
__piano.registerScheme(m.default);
__piano.selectScheme('synth-<seat>');
```

If piano-next.html fails to boot on today's tree, report it to Vandor rather than editing the host. Vandor maintains the host and will add every entry to the scheme list for judging.

## What every entry must do (the Synthesia grammar)

1. **Bars from keys.** The bar starts at the exact key it came from, one lane per key, straight and not squiggly. The bar's length is the note's duration, and it rises at a steady speed.
2. **Point of contact.** On noteOn, in the same frame, there is a visible strike at the key edge (a flash, a cap or sparks), scaled by velocity.
3. **Repeats are beads.** Six Eb4 strikes in 2 s give six separate bars with gaps. Nothing restarts or merges.
4. **Finger versus pedal.** A finger-held note (noteOn to noteRelease) looks different from a pedal-held one (noteRelease to noteEnd): for example a solid core against a hollow or dimmer tail. Finger plus pedal is the brightest state.
5. **Colour is the note.** Use `noteColor(midi)` so the bar matches its key. It must be saturated and visible. Velocity changes the attack and the chroma, never turning bars white.
6. **Bloom decays.** Bloom only on the strike or cap, hugging its source, and never a stacked wash.
7. **Budget.** Ultra 1440p at 60 fps with about 250 live bars: pooled or instanced geometry, no per-note allocation in `update`, and no second render context (Heimdall's half).

Then make it **incredible** in your own way: materials, depth, lane glow, a hit line, reflections, speed. That part is yours.

## Dynamics: Daniel's newest ask (08:55 EDT)

After the "Staff & Voicing" view, Daniel wrote, verbatim: "I really like the velocity bars. Anything else you guys can think of as an intuitive way of showing the dynamicness of the playing will be much appreciated. perhaps we can have the peaks of the velocity bars glow."

The velocity bars are Asta's translucent per-note columns, whose height is how hard the note was struck. Every entry should:
- **Keep a velocity reading he recognises:** bar or cap height, or thickness, scaled by velocity, readable at a glance.
- **Make the peaks glow.** The peak cap is the one blooming part, and it decays; hard strikes glow more.
- **Add at least one more intuitive way to show dynamics.** For example:
  - a VU-style peak-hold marker that lingers about 1 s and then falls;
  - a phrase loudness ribbon beside the roll with pp to ff bands, showing crescendo and decrescendo over time;
  - a contact ripple sized by velocity;
  - a top-voice balance cue (is the melody singing over the chord?);
  - evenness in repeated notes and runs, shown as how much the bead brightness varies.

Say in your entry note which one you chose and why it reads intuitively.

## Deliverable

- The module file above.
- `research/in-flight/piano-synthesia-mode-2026-09-15/entry_<seat>.md`, at most one page: the idea in one sentence, what makes it Synthesia, what you'd add with more time, and anything you want the judges to watch for.
- **Sunshine**, whose guarded worktree cannot write here: send the module source and note to `claude` on Bifrost with `--kind handoff`, and Vandor will place them.
- **Heimdall and Navi:** a code entry is welcome. A precise design entry (the note alone, with exact geometry, colours and timings) is also accepted, and Vandor will build it as your module.

## Judging

1. **Same fixtures for every entry.** Vandor renders each one on the same synthetic fixtures (quiet Db6/9, hard Gbmaj13#11, six repeated Eb4, a pedalled arpeggio, and an 8-second pedalled progression with a melody), in portrait and landscape, and builds one side-by-side sheet.
2. **Blind panel.** Judges score on Daniel's words, Synthesia/Guitar Hero craft and practice legibility, without knowing which seat made which entry.
3. **Daniel plays each one live** in piano-next.html (a scheme selector in the menu) and picks. Grafts from runners-up are welcome.
4. **The winner** is ported into /piano as the dedicated **Synthesia mode**: the scheme host comes into piano.js as one shared slice.

## Rules

- Write only your own `synth-<seat>.js` and `entry_<seat>.md`. Do not edit piano.js, piano-next.js, spectacle files or other entries.
- No downloads or installs, and no servers on 8793 beyond reading the page. Headless browsers only, taking the GPU lock (`mkdir E:/AI-Setup/state/arsenal/gpu-render.lock`) around any render burst.
- Synthetic MIDI only; practice logs stay private.
- Send one bus line to `claude` when your entry is in.
