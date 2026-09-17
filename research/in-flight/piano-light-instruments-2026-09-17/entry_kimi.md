# Aurora Harp — entry_kimi

**Module:** `arsenal/web/piano/instruments/light-kimi-aurora.js` · **id:** `light-kimi-aurora` · **name:** Aurora Harp

## The idea

A laser harp re-imagined not as thin laser filaments but as **bands of light**: 88 vertical translucent ribbons, each carrying its own note's saturated colour, floating above the host's keys. It is the "strings whose material is light" Daniel asked for, plus a surprise: **the material itself breathes with the chord**. The theme is *an aurora at night over a keyboard* — warm fog, thin-film iridescence, and a glowing filament that dances between the bass and the melody.

Three pieces carry the design:

1. **The band** — a wide ribbon of a note's colour, with a soft glowing core and gentle translucent edges. Low notes are broad and slow; high notes are tight and fast (one `ban(midi)` lerp drives it all, no special casing).
2. **The spectral hammer** — a small lens of focused light that dives from a soft emitter rail onto the band on every strike, the way a real hammer throws. The moment it lands, it launches a **phase-offset ghost envelope** (the Dune ornithopter trick): a travelling wave ripples up the band, never a spot that just lights up.
3. **The bass–solo braid** — a filament threads from the lowest sounding note to the melody (highest) voice, drawn between the two bands' bases. It twines into a braid as they spread / move in contrary motion, and its colour follows the interval's **consonance**: octave/fifth = warm gold, third = rose, discord = a strained cold indigo.

## Strike realism

- Velocity throws the hammer **faster** (fall speed scales with velocity) and the lens **larger**.
- The flash is the only thing that crosses the bloom threshold (~0.9 luma); the sustained band stays below it. A 10-note fortissimo chord does not clip to white — colour stays the note's colour, saturated.
- A `ppp` strike still reads: `VEL_LO = 0.16` floors the ripple and flash so a soft note is a thin, quiet band with a slow, small ripple.

## Velocity truthfulness

Everything legible rises with velocity: band brightness (`0.55 + 0.45·vel`), ripple amplitude (`VEL_LO + 0.84·vel`), flash (`vel² · FLASH_GAIN + VEL_LO`), hammer size and fall speed.

## Sustain-pedal truthfulness

- Everything lives exactly as long as `state.sounding` (I read `state.sounding ?? null` and fall back to `state.pressed + state.pedal`). A note held by the pedal keeps its band alive.
- The pedal makes the blur **breathe wider** — the band's width target while sounding is `1 + 1.7·ban(midi)`, and it relaxes back to 1 on release.
- Lifting the pedal with the key up damps over `FALL_TAU = 0.28 s` in a **visible fade**, never a snap.
- The pedal alone never animates an unstruck string (only `state.sounding` entries light a band).

## Low notes (the Dune wings)

`ban(midi) = (midi − 21) / 87`, 0 at A0, 1 at C8, drives the blur: A0's band is `0.05 + 0.29·blur` wide and its ripple is slow and deep; C8's is tight and fast. The ripple is a sine envelope in the shader (`sin(uTime·9 − vU·5 − phase·2π)`), so low notes read as a soft translucent blur, never a sharp jittering line.

## The dance (material follows the chord)

Computed inline from the sounding set (no dependency on the not-yet-landed `harmony-feel.js`; that helper can be dropped in later):

| Chord feel | What the material does |
|---|---|
| **Lush** (≥4 voices, wide voicing) | Fog swells in over ~1.4 s (3 stacked noise quads, fake volumetrics); warm haze (`uHaze`) tints the bands; thin-film **iridescence** shimmer (`.14` gain) ripples across them |
| **Simple** (open fifth / ≤2 notes) | Fog sinks over ~0.8 s; bands go clean, still, bright |
| **Tense** (pitch-class cluster or ♯/♭/alt/dim in the chord name) | Palette cools (haze and fog negate toward blue); the braid twists harder (`twirl` scales with `1 − consonance`) |

Colour follows the feel, but **each band keeps its own note colour** — the atmosphere warms/cools/darkens around it, never repainting it.

## Performance

- **No allocation inside `update`**: all scratch arrays (`usedNotes`, `seenPC`, matrices, colours) are sized in `create()`.
- **Fixed draw calls: 6** — 1 band `InstancedMesh` (88 instances) + 1 lens `InstancedMesh` (88) + 3 fog quads + 1 braid `Line`.
- `dispose()` returns every geometry, material, texture and program to baseline.
- Nothing downloaded: fog texture and all geometry are built in code.
- Both framings stay composed: the bands own the sky (`BAND_TOP` 13.2), the fog is centred behind the span, and the host's keys stay read (the keyboard is host-owned, untouched).

## Tuning constants (for the panel)

`FLASH_GAIN=2.1` · `FLASH_TAU=0.09s` · `FALL_TAU=0.28s` · `RIPPLE_DECAY=0.55/s` · `VEL_LO=0.16` · `FOG_TAU_IN=1.4s` · `FOG_TAU_OUT=0.8s` · band half-width `0.05..0.34` · blur `1 + 1.7·ban` · braid `96` points, `twirl = 2.5·(0.4 + 0.6·(1−consonance))`.
