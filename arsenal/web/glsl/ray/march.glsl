//! {"name": "ray-march", "kind": "helper", "cat": "E3", "family": "E", "version": "1.0.1", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["John C. Hart, 'Sphere tracing: a geometric method for the antialiased ray tracing of implicit surfaces' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): the march, its convergence to the first surface, and the closest approach as a cone's coverage",
//!   "Benjamin Keinert, Matthias Innmann, Michael Saenger and Marc Stamminger, 'Enhanced sphere tracing' (STAG 2014, https://doi.org/10.2312/stag.20141233): over-relaxation with its overlap check, the best candidate, the screen-space epsilon, discontinuity reduction and the self-intersection-free secondary origin",
//!   "Inigo Quilez, 'Terrain raymarching' (https://iquilezles.org/articles/terrainmarching/): bracket the crossing between the last step above and the first below, then refine",
//!   "Alan Wolfe, 'Ray marching fog with blue noise' (https://blog.demofox.org/2020/05/10/ray-marching-fog-with-blue-noise/): a per-pixel start offset turns step banding into fine grain",
//!   "Xor, GM Shaders (https://mini.gmshaders.com/): the pass-through glow march that never stops at a surface"],
//!  "cost": {"class": "C2", "loop": "rmSphereTrace, rmRelaxed, rmBacktrack: min(maxSteps, 256) hook calls; rmBacktrack then at most min(bisectSteps, 16) more; rmRefine min(iters, 8)", "tex": 0, "hooks": 1},
//!  "hooks": ["float mapScene(vec3 p)"],
//!  "contract": "The marchers call the host's mapScene(p), a field that never overestimates (an sd or sb field) unless the marcher says otherwise; rd is unit length. rmEpsilon(t, pixelAngle, epsMin) = max(epsMin, 0.5 pixelAngle t): half a pixel's footprint, a constant error on screen. rmSphereTrace steps omega * d (omega clamped to [0.1, 1]; below 1 is under-relaxed for fields that lie a little) from tRange.x until d < rmEpsilon(t, pixelAngle, 1e-4) (a hit), t > tRange.y, or maxSteps calls (capped at 256). It returns vec4(t, steps, smallest d / t seen (clamped at 0), hit): on a miss .x is the t of that closest angular approach (Keinert's best candidate, the point to shade for a soft silhouette). The sign of the first sample is kept, so a ray starting inside a solid traces its inner wall. rmRelaxed is the same with over-relaxation, omega clamped to [1, 1.95]: whenever two consecutive unbounding spheres fail to overlap, or a relaxed step lands inside a solid (d < 0, which a head-on approach makes an exact tie of the overlap test), it steps back to the plain step and stays at 1, so it misses nothing rmSphereTrace would find, never reports a hit inside a solid that rmSphereTrace would not, and takes fewer steps along flat surfaces. rmBacktrack is for fields that may overestimate: it steps d, and when d turns negative it bisects between the last t outside and the first inside (bisectSteps, capped at 16) and reports the outside end, never a t inside the solid; same return layout. rmPassStep(d, passthrough, density) = max(passthrough + |d| / density, 1e-4), never zero, so a pass-through march crosses surfaces and keeps gathering light. rmHybridStep = max(sdf, adaptive). rmJitterStart = tStart + u dt. rmSecondaryOrigin = p + n * side * 2 max(epsMin, |fAtHit|) (side +1 out, -1 in). rmRefine repeats t += mapScene(ro + rd t) - 0.5 pixelAngle t (iters, capped at 8), pulling every hit onto the offset surface the epsilon describes.",
//!  "note": "The engine of every raymarched surface, and the part that can freeze this host: a march is steps times pixels times the cost of the scene, so every loop here has a literal cap, the cost is declared, and tRange should be clipped analytically first (rmClipToBox, ixPlane, ixSlabY). Pass camPixelAngle as pixelAngle so the hit threshold grows with distance: a fixed 0.001 wastes steps far away and sparkles. The fourth number (the smallest d / t) is free and worth three effects: silhouette antialiasing (aaConeCoverage), a closest-approach glow and a near-miss outline. If holes appear, the field over-reports: fix the field (a missing lipTwist, a non-unit normal) or use rmBacktrack; never hide it with t += d * 0.5. For a big march pass unrollBarrier(steps, iFrame) as maxSteps so the compiler keeps the loop a loop. Jitter the start with a STATIC mask (dthIgn of the pixel), never one that changes every frame. Wrong looks like a skin of floor colour hugging silhouettes (steps run out: raise maxSteps or clip tRange), distant objects dissolving into sky (a fixed epsilon), black speckle on shadowed surfaces (a secondary ray started on its own surface), or terraced contour lines in a texture (hits at uneven depths: rmRefine).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "ray-march.card", "twin": "arsenal/shaders/twins/ray.py",
//!  "status": "P0",
//!  "exemplars": ["XtyXzW", "llVXRd", "7d2fDW", "4lj3Ww", "4tcXRr", "ltdcW7", "XdcyDM", "WdB3Dw", "MdX3zr", "tsScDG", "WlVyRV", "XsSGDh", "ttScDc", "XsjXRm", "43jXWt"],
//!  "learn": ["SR 5.1", "SR 5.2", "SR 5.3", "SR 5.5", "SR 5.6", "SR 5.7", "VA 3.2", "VA 3.5", "PF 10.8"]}
// Apache-2.0, Akashic Aurora. Written fresh from the papers and articles credited above.
//
// WHY. A distance field says "nothing is closer than d", so a ray may jump d at once; repeat until d is smaller than
// what a pixel can show. That one idea (Hart's sphere tracing) drives every raymarched surface, and its failure modes
// (holes, halos, frozen frames) come from the same few details: the epsilon, the step cap, the step factor, the start.
// Written once here, with the closest angular approach recorded on the way, because antialiasing and glow both need it.

// The hit threshold at distance t: half a pixel's footprint, never below epsMin.
float rmEpsilon(float t, float pixelAngle, float epsMin) {
    float halfFootprint = 0.5 * pixelAngle * t;
    return max(epsMin, halfFootprint);
}

// Hart sphere tracing with a step factor and a hard cap. vec4(t, steps, smallest d / t, hit).
vec4 rmSphereTrace(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps) {
    float stride = clamp(omega, 0.1, 1.0);
    float t = tRange.x;
    float outward = 1.0;
    float closest = 1e10;
    float closestT = t;
    float calls = 0.0;
    float landed = 0.0;
    for (int trip = 0; trip < 256; trip++) {
        if (trip >= maxSteps) {
            break;
        }
        float d = mapScene(ro + rd * t);
        if (trip == 0 && d < 0.0) {
            outward = -1.0;                        // started inside: march the solid's inside out to its wall
        }
        d *= outward;
        calls += 1.0;
        float angular = d / max(t, 1e-6);         // how much clearance the ray has, as seen from its origin
        if (angular < closest) {
            closest = angular;
            closestT = t;
        }
        if (d < rmEpsilon(t, pixelAngle, 1e-4)) {
            landed = 1.0;
            break;
        }
        t += stride * d;
        if (t > tRange.y) {
            break;
        }
    }
    return vec4(landed > 0.5 ? t : closestT, calls, max(closest, 0.0), landed);
}

// Keinert's over-relaxed march: step omega * d while consecutive unbounding spheres overlap; the moment they do not (a
// gap between them where a surface could hide), or the step has landed inside a solid, go back to the plain step from
// the previous point and stay plain.
vec4 rmRelaxed(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps) {
    float stride = clamp(omega, 1.0, 1.95);
    float t = tRange.x;
    float outward = 1.0;
    float closest = 1e10;
    float closestT = t;
    float calls = 0.0;
    float landed = 0.0;
    float lastT = t;
    float lastRadius = 0.0;
    for (int trip = 0; trip < 256; trip++) {
        if (trip >= maxSteps) {
            break;
        }
        float d = mapScene(ro + rd * t);
        if (trip == 0 && d < 0.0) {
            outward = -1.0;
        }
        d *= outward;
        calls += 1.0;
        // A relaxed step that landed inside a solid (d < 0) is refused like a gap between the spheres: head on, the
        // overlap test ties exactly, and a negative d would otherwise pass as a hit inside the solid.
        if (stride > 1.0 && trip > 0 && (d < 0.0 || lastRadius + abs(d) < t - lastT)) {
            t = lastT + lastRadius;
            stride = 1.0;
            continue;
        }
        float angular = d / max(t, 1e-6);
        if (angular < closest) {
            closest = angular;
            closestT = t;
        }
        if (d < rmEpsilon(t, pixelAngle, 1e-4)) {
            landed = 1.0;
            break;
        }
        lastT = t;
        lastRadius = d;
        t += stride * d;
        if (t > tRange.y) {
            break;
        }
    }
    return vec4(landed > 0.5 ? t : closestT, calls, max(closest, 0.0), landed);
}

// For fields that may overestimate: step d; when d turns negative the ray has passed through a surface somewhere
// between the last t outside and this one, so bisect that bracket and report its outside end.
vec4 rmBacktrack(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, int maxSteps, int bisectSteps) {
    float t = tRange.x;
    float outward = 1.0;
    float closest = 1e10;
    float closestT = t;
    float calls = 0.0;
    float landed = 0.0;
    float lastT = t;
    for (int trip = 0; trip < 256; trip++) {
        if (trip >= maxSteps) {
            break;
        }
        float d = mapScene(ro + rd * t);
        if (trip == 0 && d < 0.0) {
            outward = -1.0;
        }
        d *= outward;
        calls += 1.0;
        if (d < 0.0) {
            float outsideT = lastT;
            float insideT = t;
            for (int halving = 0; halving < 16; halving++) {
                if (halving >= bisectSteps) {
                    break;
                }
                float middle = 0.5 * (outsideT + insideT);
                calls += 1.0;
                if (outward * mapScene(ro + rd * middle) < 0.0) {
                    insideT = middle;
                } else {
                    outsideT = middle;
                }
            }
            t = outsideT;
            landed = 1.0;
            closest = 0.0;
            break;
        }
        float angular = d / max(t, 1e-6);
        if (angular < closest) {
            closest = angular;
            closestT = t;
        }
        if (d < rmEpsilon(t, pixelAngle, 1e-4)) {
            landed = 1.0;
            break;
        }
        lastT = t;
        t += d;
        if (t > tRange.y) {
            break;
        }
    }
    return vec4(landed > 0.5 ? t : closestT, calls, max(closest, 0.0), landed);
}

// The step of a pass-through march: a fixed minimum plus the distance scaled down by density, never zero, so the ray
// crosses surfaces instead of stopping and lingers (gathering light) wherever it passes close to one.
float rmPassStep(float d, float passthrough, float density) {
    float lingering = passthrough + abs(d) / max(density, 1e-6);
    return max(lingering, 1e-4);
}

// Leap through empty space by the distance field, take the fixed volume step inside: one max().
float rmHybridStep(float sdf, float adaptive) {
    return max(sdf, adaptive);
}

// Start a fixed-step march u (0 to 1, from a STATIC per-pixel mask) of a step in: neighbouring pixels then sample
// different depths, and the banding of shared slices becomes fine grain.
float rmJitterStart(float tStart, float dt, float u) {
    return tStart + u * dt;
}

// A start for a shadow, reflection or refraction ray that cannot find its own surface at once: twice the larger of the
// floor and the hit's own residual distance along the normal, outward (side +1) or inward (side -1).
vec3 rmSecondaryOrigin(vec3 p, vec3 n, float fAtHit, float epsMin, float side) {
    float push = 2.0 * max(epsMin, abs(fAtHit));
    return p + n * (side * push);
}

// Keinert's discontinuity reduction: each hit stopped at a slightly different distance from the surface, and textures
// read from the hit point show those jumps as contour lines. A few fixed-point steps put every hit on the same offset
// surface, where mapScene equals the half-pixel epsilon.
float rmRefine(vec3 ro, vec3 rd, float t, float pixelAngle, int iters) {
    float settled = t;
    for (int pull = 0; pull < 8; pull++) {
        if (pull >= iters) {
            break;
        }
        settled += mapScene(ro + rd * settled) - 0.5 * pixelAngle * settled;
    }
    return settled;
}
