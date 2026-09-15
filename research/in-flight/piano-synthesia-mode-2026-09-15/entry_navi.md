# Entry — Navi: "Bead & Beam"

**The idea in one sentence.** The strike cap is the in-focus object and the rising bar is its light-trail wake — every note is a bead of light that detaches from its key and draws a straight beam behind it exactly as long as the note sounded.

## What makes it Synthesia

The original Synthesia magic is **time with a point of contact**, and the bar is the horizontal axis of that. My take keeps the native grammar — bars rising from their exact keys, length = duration, one lane per key — and then makes the *contact* the hero instead of the bar.

- **Bead cap.** On `noteOn`, the same frame, a rounded bead lands at the key edge. Its brightness **is** the velocity — a hard strike flares, a gentle press glows. The flash is an exponential that dies over ~0.16 s, so the bloom **decays**, it never stacks.
- **Finger vs pedal.** Finger-held = a solid luminous core (brighter on the axis, dimmer at the rim). Pedal-held = a hollow tube whose outline fades to a floor. The moment your finger is down *and* the pedal is down is the brightest state, by construction — exactly Daniel's "brightest when I am pressing sustain and note at the same time."
- **Colour is the note, saturated, never white.** I relight the host's `noteColor(midi, vel)` in OKLab so velocity moves *lightness* and *chroma only* — hue is untouched. Hard velocity is brighter **and more saturated**, soft velocity dimmer. There is no path to white.
- **Repeats are beads.** Every strike gets its own slot; six Eb4 in 2 s render six beads with gaps. Nothing merges or restarts.
- **Bloom hugs the source.** Only the bead cap and its ghost cross the host's 0.9-luma bloom threshold; bodies, tails and the hit line clamp below it. Dense chords brighten at the contacts, never wash the frame.

## Navi's twist — the moved-note thread

Two flourishes:

1. **The hit line rides *behind* the cap**, a fixed ~0.055 s in time. This is a *lag*, not a second line: the white stroke sits just below the bead, and the gap between them grows with speed. The eye reads "the note is *travelling*" — the one cue flat Guitar Hero bars erase, and the thing that makes a fast run feel alive rather than playable.
2. **After-image streaks.** Each bead leaves a short fading wake of ghost quads behind it, so a fast run reads as a *streak of light*, not six disconnected dots — while still being six cleanly separate beads.

## Geometry, colour, timings (for the judges / Vandor's port)

- `SPEED = 5.6` world-units/s (one unit = one white-key pitch).
- Bar width: white `0.72`, black `0.40` world units; full-height beads on every key, straight.
- Cap half-height `0.10 + 0.24·v`; cap flash `1 + 1.6·exp(−age/0.16)`.
- Body lightness `0.46 + 0.36·v^0.8` (clamped under 0.8 luma); cap lightness `0.90 + 0.08·v`, chroma boost 0.62×; tail lightness 0.80.
- Pedal tail: outline decays `max(0.30, 0.72·exp(−tailAge/1.5))`; fill `0.06`.
- Hit line: `0.055 ± 0.020` s behind the cap, blended as `+0.9·white·(1 − ended)`.
- Ghosts: `GHOST_TAU 0.30 s`, `GHOST_H 0.10` world units tall (a streak, not a zero-height quad), spawned every 0.02 s while sounding, fading to nothing — ~7 deep per note.
- Cap strike ceiling `CAP_LUMA_MAX 2.2` luma: a hard hit saturates instead of washing to white (heat 1 measured 29–36% washed-out strike pixels — now capped).
- Finger + pedal = brightest state: live (unended) cap and body get a `×(1 + 0.30·uPedal)` lift; the pedal floor is tracked in `pedal(down, raw, t)` and fed to `uPedal`.
- Peak-hold needle: `HOLD_H 0.012` world units (a true hairline, ~2 px, not the ~10 px dotted row heat 1 saw), hold `0.5 s` then fall `0.5 s`; clamped under the bloom threshold.
- Top fade band (host overlay): now follows the active framing — 9:16 → `650–860 px`; 16:9 → `470–600 px`, applied in `applyFraming` from `resize` and `update` (heat 1 was stuck on 9:16, so landscape bars stopped near y 660).
- Ghosts + ribbon + needle all clamp under the bloom threshold (`uBodyMax`); the ribbon now carries `bandFade` so it fades inside the protected band instead of crossing it.

## Budget

Two instanced meshes (white 384 + black 256 slots) and one ghost pool (768), all recycled; zero per-frame allocation; positions come from the clock, not frame counts; premultiplied blending, no second render context. 250 live bars is well inside the pools.

## With more time

The after-image wake is the natural next step — a proper per-lane motion blur, or the bead leaving a *ribbon* of its own colour that trails a beat behind (the "moved-note thread" as a literal thread). A subtle reflection of the beads on the lacquered keybed would ground the note in the instrument rather than floating the light.

## Watch for

The hit line's lag: it should read as the note **moving**, not as double-vision. If it ever reads as a second line, the right fix is to shorten `HIT_LAG`, not to remove it. And confirm the bloom decayed on a six-Eb4 run — the contacts should flare and release, never stack into a hot bar.

## Dynamics (Daniel's newest ask — peaks glow + more)

**Peak glow.** The bead cap is now the one blooming part, and its bloom is **the velocity squared**, riding the same exponential decay as the flash (`flash + 0.9·v²·exp(−age/0.16)`). A hard strike blooms hotter and fades; a gentle press only glows. It never stacks, it never whites — it is a decayed peak, exactly the "peaks of the velocity bars glow" Daniel asked for.

**Named choice 1 — the VU peak-hold marker.** On every strike a thin luminous *needle* flickers at the bead's peak height — its height *is* the velocity (a hard strike parks a higher needle). It holds ~0.5 s, then **falls back toward the key** over ~0.5 s and fades. I chose this because Daniel already reads velocity as cap height; the peak-hold just extends that reading one beat into the past, so "how hard was that last strike" stays readable after the bar has risen out of frame. It is the literal VU-meter metaphor he's describing, transposed onto each note instead of a single global meter.

**Named choice 2 (beyond the list) — the phrase loudness ribbon.** A slim strip pinned at the **left edge**, `pp` at the bottom warming to `ff` at the top, with a live dot riding it. The dot is a fast-attack / slow-decay follower over recent strike velocities, so a **crescendo climbs the ribbon** and a decrescendo sinks back. I added this because the peak glow and peak-hold both read *single-note* dynamics; the ribbon reads the **phrase** — the swells and falls that make a run musical. Note-level loudness and phrase-level loudness are different things, and the ribbon gives the eye the second one at zero per-note cost.

Both are screen-true additions that cost nothing per frame (the needle is pooled instanced geometry positioned from the clock; the ribbon is a single full-screen quad carved in the fragment shader).

## Heat 1 fixes (scored 5.50; measured defects addressed before the final heat)

All six measurer-flagged defects are fixed in `synth-navi.js`, verified against the cited line ranges:

1. **16:9 band never applied** — `resize()` now runs `applyFraming(framing)`, which switches `uFadeEnd/uFadeStart` to the `BAND[id]` for the active aspect (`update()` also re-checks `frame.framing`). Landscape bars now fade into the 470–600 px band instead of stopping near y 660.
2. **Ghosts zero height** — the ghost vertex now folds `position.y` into `yy` with `GHOST_H 0.10`, so each after-image quad has real height and reads as a streak.
3. **Ribbon crossed the protected band** — the ribbon fragment now multiplies by `bandFade(gl_FragCoord.y)` and discards inside the band.
4. **`pedal()` empty** — it now tracks `pedalDown` and drives `uPedal`; on a pedal-held repeat, `noteOn` force-closes the prior bar so repeats read as separate beads, and finger+pedal gets a `×(1+0.30)` brightness lift (the brightest state).
5. **Peak-hold needle ~10 px / dotted, crossing bloom** — `HOLD_H` cut 0.06→0.012 (hairline), hold shortened 1.0/0.6→0.5/0.5, and the `×1.4` removed with a `uBodyMax` clamp; the ribbon also clamps, so no non-cap pixels cross the 0.9-luma threshold.
6. **1 s cap glow, 50k px halo, washed 29–36% strikes** — cap strike brightness is clamped by `CAP_LUMA_MAX 2.2` so hard hits saturate instead of washing to white; the ghost's `×1.4` bloom multiplier was removed (under-threshold), killing the soft-note halo; the 1 s glow was the needle's old hold time, now 0.5 s.

