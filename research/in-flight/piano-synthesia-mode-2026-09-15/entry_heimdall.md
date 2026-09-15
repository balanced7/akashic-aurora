# Entry — Heimdall: "Glow Echo"

**The idea in one sentence.** Keep the straight velocity bars and make their caps the one blooming part — then let each peak lift off as a fading needle-ghost that climbs toward the top of the frame, so the *hardness* of a strike stays readable after the bar itself has risen out of view.

## What makes it Synthesia

The house reconciliation already names the foundation: **time, with a point of contact**. I keep the native grammar untouched — straight bars from the exact key, length = duration, one lane per key — and put all the velocity information in the **cap**, which is what Daniel said he already recognises ("I really like the velocity bars").

- **Bars from keys.** Every strike is a fresh slot; six Eb4 in 2 s render six separate bars with gaps. Nothing merges or restarts.
- **Point of contact.** On `noteOn`, the same frame, a rounded cap lands at the key edge. Its **height is the velocity** (`0.10 + 0.26·v`), laid on top of the translucent velocity columns — the exact reading he already trusts.
- **Finger vs pedal.** Finger-held = solid core (brighter on the axis, dimmer at the rim). Pedal-held = hollow tail that decays to a floor. The pedal is now a *live state*: while it is down it brightens every sounding body (×1.28), so finger *and* pedal together is the brightest state by construction — Daniel's "brightest when I am pressing sustain and note at the same time." Lifting the pedal ends every pedal tail at the lift instant, and a re-struck note pulls its previous sound's end back by a small bead gap, so six Eb4 under pedal render six *separate* bars, never one merged run.
- **Colour is the note, saturated, never white.** I relight the host's `noteColor(midi, vel)` in OKLab so velocity moves *lightness* and *chroma only* — hue untouched. The cap's chroma is *boosted* by velocity (`1.0 + 0.55·v`) rather than desaturated, so a hard strike is a *deeper* note colour, never a white wash. There is no path to white.
- **Bloom decays.** Only the cap and its echo cross the host's 0.9-luma threshold; bodies, tails and the lane clamp below it. Bloom hugs its source and rides an exponential, so it fades — it never stacks into a hot bar.

## The peaks glow (Daniel's ask, verbatim)

The cap is the one blooming part. Its bloom is **velocity squared** riding `exp(-age/0.34)`, and now that velocity term drives the cap's actual brightness — `(0.28 + 0.72·v²)·(1 + 1.4·e^(-age/0.16))` — so a hard strike blooms hotter and then the glow dies out; a gentle press only glows. This is "the peaks of the velocity bars glow" taken literally — the peak *decays*, exactly the liveliness he asked for, with harder strikes glowing more (brightness vs velocity is now strongly positive, not flat).

## Named choice — the glow echo (beyond the brief's list)

On every strike above a quiet floor, a thin luminous **ghost needle** lifts off the cap, climbs toward the top of the frame for ~0.8 s, and dims on a pure exponential. Its birth brightness is `v²`, and it *blooms* — its colour is pushed above the host's 0.9 threshold by `(1 + 0.9·v²)`, so a hard strike leaves a genuinely glowing, faster-rising, larger mark, while a soft one stays below the bloom line. There is nothing that sums, so it obeys the bloom discipline and can never become a wash.

**Why it reads intuitively.** Daniel already reads velocity as cap height — but a cap only sits at the key edge for a fraction of a second before the bar climbs out of frame. The echo keeps that *same* height-reading alive one beat into the past: as the bar rises away, its ghost stays legible, so "how hard was that last strike" survives into the phrase. It is a per-note VU needle rather than a single global meter (which would collapse a chord of mixed velocities into one number). I deliberately chose it *instead of* the phrase-ribbon/peak-hold I saw others were taking, to add a distinct layer: the echo reads dynamics **through time**, not just at the instant or as one global swerve.

## Geometry, colour, timings (for the judges / Vandor's port)

- `SPEED = 6.0` world-units/s (one unit = one white-key pitch).
- Bar width: white `0.72`, black `0.40` world units; straight, full-height.
- Cap height `0.10 + 0.26·v`; cap flash `1 + 1.4·exp(-age/0.16)`; cap glow `0.28 + 0.72·v²` (velocity term, rides the same exponential); bloom decay τ `0.34 s`.
- Body lightness `0.46 + 0.36·v^0.8` (clamped under 0.8 luma); pedal boost `×1.28` while down; cap lightness `0.80` with chroma `1.0 + 0.55·v` (clamped below bloom threshold, the velocity glow supplies the bloom); tail lightness `0.80`.
- Pedal tail: outline `max(0.28, 0.68·exp(-tailAge/1.5))`, fill `0.06`; bead gap `0.06 s` on re-strike.
- Echo: life `0.8·(0.75 + 0.5·v)` s, rise `2.4·(0.6 + 0.55·v)` world-units/s (climb speed is a second velocity channel), sideways sway `0.14·sin(2.2·age + seed)`, point scale `0.20 + 0.85·v`, bloom push `1 + 0.9·v²`; born only above `v > 0.12`.
- Top fade band (host overlay): 9:16 → `650–860 px`; 16:9 → `470–600 px`, screen-space so it holds under any camera.

## Budget

Two instanced bar pools (white 384 + black 256) and one echo point cloud (512), all recycled; zero per-frame allocation; every position comes from the clock (`uNow` and event times), never frame counts; premultiplied blending; no second render context. 250 live bars is well inside the pools.

## With more time

The echo is the natural seed for a *phrase-level* read I deliberately did not ship here: a short running-average "loudness ribbon" at the left edge that the echoes already imply. More usefully: make the echo's *climb speed* a second velocity channel (harder = a faster-rising ghost) so the needle's motion, not just its brightness, carries the dynamic. And a subtle reflection of the caps on the lacquered keybed would ground the contact in the instrument.

## Watch for

The echo should read as the *glow of the strike*, not as a second cap — it is slightly hotter and slightly desaturated for that reason; if it ever reads as double-vision, the fix is to shorten `ECHO_LIFE`, not to remove it. And confirm the bloom *decayed* on a hard six-Eb4 run: contacts should flare and release, never stack. The four heat-1 measured defects are all addressed: brightness now tracks velocity (positive r), the echo genuinely blooms above the threshold, the pedal brightens held bodies and ends tails on lift with a bead gap on re-strike (so pedalled repeats are separate bars), and the strike is chroma-boosted rather than washed to white.
