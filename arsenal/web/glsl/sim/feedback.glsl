//! {"name": "sim-feedback", "kind": "helper", "cat": "J6", "family": "J", "version": "1.0.0", "order": 30,
//!  "license": "Apache-2.0",
//!  "credits": ["water, sims and feedback report, sections 1.4 and 2 (research/reviewed/shader-school-2026-10-13/water-sims-feedback.md): NaN poisoning and the stuck 8-bit residue",
//!   "GPU report, finding 6 (research/reviewed/shader-school-2026-10-13/gpu-perf-glsl.md): an 8-bit trail at 0.98 sticks near byte 24 or 25",
//!   "Ryan Geiss, MilkDrop's decay model (https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html): read last frame, darken, draw on top"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "simSanitize replaces every non-finite component with the fallback's (finiteOr) and clamps the rest to [-bound, bound]: one bad texel can neither poison a feedback loop nor grow without limit. fbDecay multiplies by keep and then moves one floorStep toward zero, stopping at zero, so a stored trail really reaches black: with keep 0.98 and floorStep 1/255 an 8-bit trail clears in under 200 frames where keep alone sticks near a tenth of full brightness forever. Both are per-step operations; keep must already be per frame (clkKeep turns a per-second keep into one).",
//!  "note": "The last two lines of any feedback step: decay what was there, add what is new, sanitise, write. The floor step is the cure for the ghost of everything ever drawn that an 8-bit buffer keeps; on a half-float buffer a smaller floor (or none) is fine. Derive keep from seconds, never per frame, or the trail is four times shorter at 240 Hz than at 60. Wrong looks like a faint permanent smear (no floor step), a black square that grows each frame (an unsanitised NaN), or a trail whose length changes with the display (a per-frame keep).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "sim-feedback.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0", "exemplars": ["43jXWt", "ldSfWV"],
//!  "learn": ["WS 1.4", "WS 2.2", "GP finding 6"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the reports credited above.
//
// WHY. A feedback buffer is a delay line: every frame reads the last one back, so whatever goes in comes round again.
// Two faults recur. A NaN is like a short circuit in that loop: it spreads to every neighbour that reads it and never
// leaves. And an 8-bit buffer is a staircase: multiply a step by 0.98 and it rounds back to itself once it is small
// enough, so the trail never reaches black. A sanitiser is the fuse; the floor step is the bleeder resistor that
// drains the last of the charge.

// The fuse: non-finite components become the fallback's, the rest stay inside [-bound, bound].
vec4 simSanitize(vec4 v, float bound, vec4 fallback) {
    return clamp(finiteOr(v, fallback), -bound, bound);
}

// One frame of decay: scale by keep, then take one floorStep off the magnitude, never crossing zero.
vec3 fbDecay(vec3 prev, float keep, float floorStep) {
    vec3 faded = max(abs(prev) * keep - floorStep, 0.0);
    return sign(prev) * faded;
}
