# Instruments of light: a house design round (brief)

*Conductor: Vandor. Opened 2026-09-17 around 00:40 EDT. Entries due **14:00 EDT 2026-09-17**. Daniel plays every entry live in /piano's Instrument menu and picks. This round can have many winners: he wants to experiment with all kinds of instruments.*

## Daniel's words, verbatim

> "I really love the grand and the crystal grand! the strings changing color in brightness also looks magical!! Can we riff on that and make it even better? The color decay doesn't fully match the sustain of the length of the note so I think the decay should be slower and have a higher floor.
>
> I think we can experiment with all kinds of pianos and strings! that idea really resonated with me, we could have a cool laser harp or some futuristic looking piano. the strings could be bands of light being struck with hammers where the feel looks realistic and is responsive to velocity and the sustain pedal. I am really curious what you all will come up with!"

> "Try to surprise me with your own unique designs and theme ideas! I am really curious what creative thing you all will come up with!
> Notes that are lower could have more of a blur and vibration similar to the wings in the helicopters from the movie dune"

## What to make

**One instrument module each**, and more than one is welcome: an instrument you would be proud to see Daniel play.

- **Starting points, not limits:** a laser harp, a futuristic piano, strings as bands of light struck by hammers.
- **Surprise is explicitly asked for.** Bring your own idea and your own theme.
- **Three qualities every entry needs:**
  - the strike looks and feels physical;
  - it answers velocity and the sustain pedal truthfully;
  - low notes carry more vibration and blur than high ones. Think of the Dune ornithopter wings: a soft translucent blur envelope, never a sharp jittering line.

The concert grand and crystal grand are being tuned tonight so the string light lasts as long as the note sounds and the bass strings vibrate with that wing-blur. Read `arsenal/web/piano/instruments/concert-grand.js` and `glass-piano.js` as the reference for how an instrument sits on the page.

Daniel added two more ideas while the round was opening. They are part of the brief:

> "certain chords and chord combinations can change the color or rendering of things, for things to look organic and real and not like a sprite, unless the theme is sprite based. I am sure there are some really clever 3d demo tricks we can use that are low cost but look astounding."
>
> "If we could visually represent the lushness and vibrance or simplicity of certain chords or relationships between bass note and solo, I think it would be cool if we had a way of capturing that dance"

### Harmony in the material

The chord should change how things are made, not only their colour.

- **A lush chord** (maj9, 13#11, a wide pedalled voicing) should make the instrument feel alive and rich: softer light, more motion, iridescence, depth.
- **A simple chord** (an open fifth, a plain triad) should make it clean, still and clear.
- **A tense chord** (an altered dominant, a cluster) should strain, crackle or tighten.
- **Motion must look organic**, never like a sprite pasted on top, unless your theme is deliberately sprite-based and owns that choice.

And, in Daniel's words again:

> "lush chords could emit a wind or fog or something and the colors can possibly change with the chord tensions and feels. Whatever other ideas you have for creative interpretations and presentations for this, go right ahead"

- **Lush chords breathe something out:** wind through the strings, fog rolling off the instrument, haze that the light catches.
- **Colour follows the feel.** The note colour stays the note's identity. Around it the atmosphere can warm, cool, darken or clear with tension, brightness and simplicity.
- **Creative interpretation is invited.** Surprise him.

### The dance between the bass and the solo

Show the relationship between the lowest voice and the melody line as something you can watch move. Some ways in:

- **a filament** that stretches as they spread apart;
- **a braid** that twists when they move in contrary motion;
- **a pull** that tightens as they converge;
- **a colour** that follows how consonant the interval between them is.

### The shared helper: `arsenal/web/piano/harmony-feel.js`

Being built tonight, so no one reinvents it.

```js
import { createHarmonyFeel } from "../harmony-feel.js";
const feel = createHarmonyFeel();        // one per instrument
const f = feel.update(state, dt, t);     // every frame; one object refreshed in place
f.voices  // { count, bass, top, solo, spread }            solo = the melody voice over the chord
f.colour  // { simplicity, lushness, tension, brightness, openness }   each 0..1, smoothed (attack ~0.12 s, release ~0.6 s)
f.dance   // { interval, family, consonance, motion ('contrary'|'similar'|'parallel'|'oblique'|'static'), pull, stretch, phase }
f.events  // { chordChanged, bassMoved, soloMoved }  true only on the frame it happens
```

### The energy of the moment

Daniel again, verbatim:

> "When a chord feels really intense it can start building some kind of artifact, then when the chord changes it can change. some way of visually changing the overall energy level and feel depending on pace and flow. where the visuals creatively display the density and relationship of notes and can measure the emotional feel of the moment. just throwing ideas out there ^__^"

- **An intense chord builds something.** While a tense or lush chord is held and the energy stays up, a structure grows: crystal, a storm cell, a sculpture of light, a knot. **When the chord changes, it releases** by shattering, blooming, dissolving or transforming into the next thing. The artifact is the visual memory of that chord.
- **Overall energy and feel follow pace and flow:**
  - how many notes, how hard and how wide;
  - how steady or free the timing;
  - how connected or detached the playing.

  The whole instrument's world can breathe with it: calm and spacious, restless, surging, spent.
- **Show density and relationships**, not just individual notes.
- **Read the feel of the moment.** This is an estimate of the music's character from its features, not a claim about Daniel's own emotions.

A second shared helper, **`arsenal/web/piano/moment.js`**, is built after `harmony-feel.js` lands. It pairs with it:

```js
import { createMoment } from "../moment.js";
const moment = createMoment();               // one per instrument, next to a harmony-feel instance
const m = moment.update(state, dt, t, f);    // f = feel.update(...); one object refreshed in place
m.energy     // 0..1: note rate, velocity, register spread and pedal wash, smoothed over ~2 s
m.pace       // notes per second, smoothed
m.pulse      // 0..1: steady timing (1) vs free rubato (0)
m.flow       // 0..1: connected and legato (1) vs detached and staccato (0)
m.density    // 0..1: distinct notes sounding or struck in the recent window
m.intensity  // 0..1: builds while a tense or lush chord is held with energy up; decays after release
m.artifact   // { growth 0..1, seed (new on every chord change), age, released (true on the frame a built-up chord changes), releaseStrength 0..1 }
m.arc        // 'resting' | 'building' | 'peak' | 'sustaining' | 'releasing'
m.mood       // { valence -1..1 (bright/consonant .. dark/tense), arousal 0..1, label: 'calm' | 'tender' | 'yearning' | 'searching' | 'playful' | 'tense' | 'dark' | 'triumphant' }
m.events     // { build, peak, release, restart }: true only on the frame it happens
```

Build against this interface now. If your entry needs a field that isn't here, say so on the bus before 09:00.

### Low-cost tricks that look astounding

These are suggestions from the demoscene toolbox, not requirements. Each looks organic at little cost.

- **Vertex-shader displacement with layered simplex or curl noise:** organic motion with no per-vertex CPU work.
- **Fresnel rim light plus wrap lighting:** fake translucency and subsurface glow.
- **Thin-film iridescence:** a hue ramp driven by the fresnel term. Lushness can drive it.
- **Matcaps:** rich materials without extra lights. Adding scene lights also costs shader programs, per the house dispose rule.
- **Small raymarched SDF volumes inside one box or quad shader:** glowing cores and plasma, with a low step count and blue-noise dither.
- **Fake volumetrics:** a few stacked noise-textured translucent quads with a soft depth fade, not flat billboards.
- **Curl-noise GPU particles:** instanced points, or the house's `GPUComputationRenderer`.
- **A half-resolution ping-pong feedback buffer:** trails, smoke and motion blur.
- **Phase-offset ghost copies:** the Dune wing-blur envelope.
- **Dithered alpha:** avoids transparency sorting trouble.
- **Chromatic aberration or a bloom kick only on strikes:** never sustained.

## The contract

A module is `arsenal/web/piano/instruments/<id>.js`. Use the id `light-<seat>-<name>`, for example `light-navi-aurora`. It exports

```js
export default { id, name, create(ctx) }
// create(ctx) returns { group, update(dt, t, state), resize(framing), setActive(on), dispose() }
```

### What `ctx` gives you

`THREE`, `scene`, `camera`, `renderer`, `clock`, `keyX(midi)`, `isBlack(midi)`, `noteColor(midi, vel)`, `noteCss`, `KEY`, `framing`, `options`, and the page's layout constants. Read the header of the instrument host in `arsenal/web/piano.js` (around line 1180) for the exact list.

### What `update(dt, t, state)` gets

| Field | What it is |
|---|---|
| `state.pressed` | Map, midi to entry: notes whose finger is down |
| `state.pedal` | boolean: the damper pedal |
| `state.chord` | the page's current chord reading |
| `state.notes` | recent strikes `{ midi, vel, t }`, newest last |
| **`state.sounding`** | **new tonight.** Map, midi to `{ vel, t0, held, pedal, tRelease, strike }`, for exactly the notes the page considers sounding. `held` means the finger is down, `pedal` means only the damper pedal holds it, and `strike` increments on every strike including re-strikes. Read-only and refreshed every frame. |

**Use `state.sounding` to make light and vibration last exactly as long as the sound.** Until it merges, guard with `state.sounding ?? null` and fall back to `pressed` plus `pedal`.

## House rules

These were learned the hard way in the Synthesia bake-off.

1. **Draw only your instrument.** Never write to the host camera, renderer settings, fog, scene background or layers.
2. **Colour stays the note's colour, saturated.**
   - Nothing clips to white, even in a 10-note fortissimo chord.
   - Only a strike's flash may cross the bloom threshold (about 0.9 luma). Sustained light stays below it and never stacks.
3. **Velocity must be legible:** brightness, size or motion must rise with velocity, and a soft note still reads.
4. **The sustain pedal must be truthful:**
   - a note held by the pedal keeps its life;
   - a note released with the pedal up damps within about 0.3 s, with a visible fade rather than a snap;
   - the pedal alone never animates unstruck strings.
5. **Performance:**
   - p95 frame time at 16:9 Ultra with a 10-note pedalled chord must stay within 2 ms of the concert grand;
   - no allocation inside `update`;
   - a fixed number of draw calls.
6. **`dispose()` must return geometries, textures and shader programs to baseline.** The page checks this.
7. **Nothing downloaded at runtime:** no models, textures or fonts from the network. Everything is built in code.
8. **Both framings (9:16 and 16:9) must look composed**, and the keyboard's keys must still read.

## How to enter

- **Files:** write your module to `arsenal/web/piano/instruments/light-<seat>-<name>.js`, and a one-page note to `research/in-flight/piano-light-instruments-2026-09-17/entry_<seat>.md`. The note covers the idea, the strike, velocity and pedal behaviour, what low notes do, and your tuning constants.
- **Loading:** entries are not in the Instrument menu until Vandor registers them, so your file never loads into Daniel's live page before it is ready.
- **Design entry instead:** if your seat cannot write this repo or cannot run a browser, send a precise design entry on the bus and Vandor's lane will build and render it. That's the same way Sunshine's Afterglow Roll was built.
- **The verification lane:** you do not need a browser. Send `render please light-<seat>-<name>` on the bus and Vandor's lane renders your module on the shared fixtures below. You get back stills, strips and measurements (brightness against sound, velocity legibility, frame time, dispose) within about an hour.
  - **Use it early.** In the last round, entries that were never rendered shipped black bars and washed-out strikes that nobody could see.
  - **A mid-round render** of every file already present runs at **09:00 EDT**, and the results go back to each seat.

## Shared fixtures (the same for every entry)

1. **Single strikes:** A0, C2, C4, C6, C8 at velocities 30, 70 and 120, each held 4 s.
2. **A low pedalled chord** (A0 E1 A1 C#2 E2), v110, held 8 s by the pedal after the fingers lift at 0.5 s.
3. **A pedal lift mid-chord:** a C major chord pedalled for 3 s, then the pedal lifts while the fingers stay down on two of the notes.
4. **A staccato run** of C4 to C6 at v90, each note 0.12 s.
5. **A glissando** A0 to C8 in 2 s, pedal down.
6. **Fast repeats:** Eb4 eight times in 2 s at v90.

## Judging

- **The panel:** blind judges on the rendered fixtures, with four lenses:
  - **Daniel's magic:** would he say "magical"?
  - **Strike realism:** hammer feel and velocity.
  - **Sustain truth:** light and motion follow the sound.
  - **Craft and performance.**
- **Measurements** sit alongside the panel's scores.
- **The pick is Daniel's.** He plays every entry live and chooses which instruments stay.
