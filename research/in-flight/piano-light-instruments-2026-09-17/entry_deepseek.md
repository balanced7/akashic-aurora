# Entry — Orrery of Light (light-deepseek-orrery)

*Seat: deepseek. Filed 2026-09-17 for the "Instruments of light" round.*

## The idea

**"The room listens."** Not a piano case, but an open vertical ring — an *orrery cage* of thin dark
rails — around the keybed, and a **fan of light-bands** that rise away from the player like a harp
strung for an audience of stars. The bands *are* the strings; hammers of light strike them from below.
The body stays near-invisible (three thin rails, ~0.55 alpha) so the light owns the whole stage, and the
host's keys keep reading through the cage.

It is a harp and a piano at once: each of the 88 notes is a glowing band (1/2/3 per note, mirroring real
stringing), fanning from the treble (near, shallow) to the bass (far, deep), like a grand's overstrung
harp laid open to the sky.

## Strike — physical, velocity-truthful

- A hammer shank **knocks up from below** the band and rebounds to a back-check; its rise speed tracks
  velocity (0.4 → 2.4 world units/sec from pp → ff), so a hard strike *looks* like a hard strike.
- On strike, the band **bows out along its length in a travelling wavefront** — the first half-cycle of a
  struck string — starting at the base and flying to the tip at velocity-scaled speed.
- A **bloom flash** is permitted *only* on the strike frame, scaled by velocity². Soft strikes are a small
  cool plume; hard strikes a hot wide plume. The hammer tip takes the note colour.

## Sustain truth

Driven by `state.sounding` when present (`{vel, t0, held, pedal, tRelease, strike}`), falling back to
`pressed` + `pedal` (guarded, so it works both before and after the new field lands):

- **Held** → glowing floor.
- **Pedalled (finger lifted)** → keeps its life but cools/thins ~15%, so you can *see* that only the pedal
  is holding it.
- **Pedal-up release** → damps in ~0.3 s as a **visible travelling fade** (the wave dies outward from the
  strike point), never a snap.
- The pedal alone **never lights an unstruck band**.

## Low notes = ornithopter wing blur

`noteBlur(m) = clamp((76 - m) / 55)` rises smoothly from 0 (C8, crisp line) to 1 (A0, full wing). The band
fragment folds **3 phase-offset vibration harmonics** weighted by blur, and the band width rises toward the
bass (0.40 vs 0.19). Bass notes beat slow and wide like a wing; treble is a crisp line. A soft translucent
envelope, never a sharp jitter.

## The surprises (my own)

1. **Lush chords breathe wind & fog.** Lushness (estimated from voice count × spread × voicing, until
   harmony-feel lands and can replace it) exhales **hair-thin light motes** that drift up and **sway the
   bands laterally** like wind through strings. Simple chords hold the room crystalline-still.
2. **Tense chords crackle.** Clusters / altered dominants (detected as ≥3 voices within a 4-semitone span)
   make the bands *strain* and the air emit a dry crackle of short bright sparks.
3. **The bass–solo dance, visible.** A braided filament hangs between the lowest sounding note's band and
   the highest (the melody). As they part it stretches and thins; in **contrary motion it twists into a
   helix**; the tighter they converge the brighter it pulls; its colour follows the **interval's
   consonance** (dissonant → hot orange-violet, consonant → cool, near the note colour). One voice wraps it
   into a mote.

## Tuning constants

| What | Value |
|---|---|
| Band rise | y 1.1 → 40 (fan), depth z −1.5 → −6.5 treble→bass |
| Strike flash tau | 0.09 s |
| Plume travel | 0.5–3.0 u/s (velocity) |
| Damp (pedal up) | 0.30 s (visible fade) |
| Pedal-hold decay | 1.3 s (slow cool) |
| Pedalled note cooling | ×0.85 |
| Ghost harmonics | 3 (wing envelope) |
| Bloom cap (sustained) | 0.82 luma; strike-only can cross 0.9 |
| Fog motes | 240; crackle sparks | 96 |
| Filament segments | 96 (ribbon, taper ×0.4–1.0) |

## Craft / performance

- No downloads; everything built in code. **Fixed draw calls**: instanced bands (1), instanced hammers (1),
  filament ribbon (1), fog + crackle point clouds (2), cage lines (3). No scene lights, no fog, no
  background writes.
- **No per-frame allocation** (preallocated `Float32Array`/`Uint8Array` scratch; `Map.forEach`).
- Colour stays `noteColor`, saturated; only the strike flash may cross the bloom threshold (~0.9 luma);
  sustained light is luma-capped at 0.82 and never stacks (a 10-note chord sums the vector then normalises).
- `dispose()` returns geometries, textures and shader programs to baseline.
- Both 9:16 and 16:9 composed (portrait pulls the fan ~1.5 u tighter in depth).
