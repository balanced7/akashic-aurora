//! {"name": "atmos-aurora", "kind": "helper", "cat": "G8", "family": "G", "version": "1.0.0", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["Orion Sky Lawlor and Jon Genetti, 'Interactive Volume Rendering Aurora on the GPU' (WSCG 2011, https://www.cs.uaf.edu/~olawlor/papers/2010/aurora/lawlor_aurora_2010.pdf): emission as a footprint times a vertical profile, rising sharply at about 100 km",
//!   "NOAA Space Weather Prediction Center, 'Aurora: tutorial' (https://www.swpc.noaa.gov/content/aurora-tutorial): the green 557.7 nm body, the red 630 nm crown, the purple nitrogen fringe of active displays",
//!   "Chris Wyman, Peter-Pike Sloan and Peter Shirley, 'Simple Analytic Approximations to the CIE XYZ Color Matching Functions' (JCGT 2(2), 2013, https://jcgt.org/published/0002/02/01/): the line colours",
//!   "Valdex's Chromatic Aurora Curtains (https://www.shadertoy.com/view/ffG3Rc) and Mattenii's Aurora Lights (https://www.shadertoy.com/view/MsjfRG): rays as 1D noise along the curtain, colour bands in physical order"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0, "hashes": "4 pcg3d (auroraRays)"},
//!  "contract": "Altitudes in kilometres. auroraProfile(alt, lowerEdge, scaleH) is 0 at and below the hem, (1 - e^(-z/6)) e^(-z/scaleH) above it (z = alt - lowerEdge), divided by its own peak so its maximum is exactly 1, reached 6 ln((6 + scaleH) / 6) km above the hem (12.2 to 14.4 km for scaleH 40 to 60); far above it falls by e per scaleH. auroraLineColor(alt, energetic) is linear RGB, each emission line's spectral colour clipped into sRGB with its brightest channel 1, weighted by its share at that altitude: the 557.7 nm green (0.222, 1, 0) switching on between 92 and 108 km (oxygen's green state is quenched by collisions lower down) and fading out between 170 and 250 km, the 630 nm red (1, 0, 0) taking over between 160 and 260 km, and energetic (clamped to 0..1) times the purple nitrogen fringe (0.825, 0, 1), full below 96 km and gone by 112 km, so an energetic hem is purple under the green; it carries hue, not brightness. auroraRays(along, t, seed) is in [0, 1]: two rows of noiseValue2 along the curtain drifting at -0.21 and +0.53 units per second (the second 3.1 times finer), mixed and passed through smoothstep(0.5, 0.9): about half the curtain lies between rays (exactly 0), about one place in sixteen is a bright core (above 0.8), the mean is about 0.17; no height coordinate, so every ray runs the curtain's full height. Honest while along and t stay below about 2^20 (wrap t on the host).",
//!  "note": "The house's signature subject, built the physical way: brightness from auroraProfile, hue from auroraLineColor, texture from auroraRays, all multiplied together, added (never mixed) over the night sky, and shown through displayHueSafeGamma so the hue of many summed dim layers survives. A sharp hem and a soft fading top is what makes it read as aurora; the hem height wandering along the curtain (lowerEdge from a slow noise) makes it hang like fabric. scaleH is the naked-eye versus long-exposure dial: 30 to 40 km keeps the crown a faint red rumour, 80 or more paints the tall red tops of photographs. Use energetic sparingly for active displays. These are the physical colours; for the house's analogous palette, keep auroraProfile and auroraRays and recolour in OKLCH. Wrong looks like a curtain with a soft bottom and a hard top (the profile upside down), red at the bottom and green on top (colour order reversed), rays that lean or slide vertically (a height term crept into along), a pattern that freezes or crawls after an hour (t not wrapped), or a muddy grey where curtains overlap (gamma applied per channel).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "atmos-aurora.card",
//!  "twin": "arsenal/shaders/twins/atmos.py", "status": "P0", "exemplars": ["ttScDc", "MsjfRG", "ffG3Rc"],
//!  "learn": ["VA 7.1", "VA 7.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the physics and the public sources credited above.
//
// WHY. An aurora is light EMITTED by thin air 100 km up when electrons rain down the magnetic field lines: sheets
// about a kilometre thick and hundreds long, so it is optically thin (glow only adds) and its look is set by three
// things these parts model: how bright it is at each altitude (a sharp floor where the air becomes dense enough to stop
// the electrons, a long fade above), which oxygen and nitrogen lines glow at that altitude, and the fine rays along
// the field lines.

// Emission against altitude: 0 below the hem, a 6 km rise, a peak of exactly 1, then a fall by e per scaleHKm.
float auroraProfile(float altKm, float lowerEdgeKm, float scaleHKm) {
    const float riseKm = 6.0;                                // about the scale height of the air near 100 km
    float h = max(scaleHKm, 1e-3);
    float above = max(altKm - lowerEdgeKm, 0.0);
    float shape = (1.0 - exp(-above / riseKm)) * exp(-above / h);
    float settle = riseKm / (riseKm + h);                    // e^(-z / rise) where the shape peaks
    float peak = (1.0 - settle) * pow(settle, riseKm / h);
    return shape / peak;
}

// The hue of the emission at an altitude: green body, red crown, and (for energetic displays) a purple hem.
vec3 auroraLineColor(float altKm, float energetic) {
    const vec3 oxygenGreen = vec3(0.222, 1.0, 0.0);        // 557.7 nm through the CIE 1931 observer, clipped to sRGB
    const vec3 oxygenRed = vec3(1.0, vec2(0.0));           // 630.0 nm
    const vec3 nitrogenFringe = vec3(0.825, 0.0, 1.0);     // 427.8 nm violet plus 0.7 of the red near 670 nm
    float green = smoothstep(92.0, 108.0, altKm) * (1.0 - smoothstep(170.0, 250.0, altKm));   // quenched low down
    float red = smoothstep(160.0, 260.0, altKm);
    float fringe = clamp(energetic, 0.0, 1.0) * (1.0 - smoothstep(96.0, 112.0, altKm));      // the deepest electrons
    return green * oxygenGreen + red * oxygenRed + fringe * nitrogenFringe;
}

// Rays along the field lines: 1D noise along the curtain, drifting, thresholded into sparse bright columns.
float auroraRays(float along, float t, uint seed) {
    // a whole-number row of 2D value noise is exactly 1D value noise; rows 0 and 7 are independent
    float coarse = 0.5 + 0.5 * noiseValue2(vec2(along - 0.21 * t, 0.0), seed);
    float fine = 0.5 + 0.5 * noiseValue2(vec2(3.1 * along + 0.53 * t, 7.0), seed);
    return smoothstep(0.5, 0.9, 0.55 * coarse + 0.45 * fine);
}
