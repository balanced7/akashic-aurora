//! {"name": "light-visibility", "kind": "helper", "cat": "F5", "family": "F", "version": "1.0.1", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'soft shadows in raymarched SDFs' (https://iquilezles.org/articles/rmshadows/): the penumbra from the nearest miss h / t along the shadow ray",
//!   "Sebastian Aaltonen, 'GPU-based clay simulation and ray-tracing tech in Claybook' (GDC 2018; retold in https://iquilezles.org/articles/rmshadows/): triangulating the closest approach between two unbounding spheres, fewer bands",
//!   "Alex Evans, 'Fast Approximations for Global Illumination on Dynamic Scenes' (SIGGRAPH 2006 course notes; retold in https://iquilezles.org/articles/nvscene2008/): occlusion from distance samples along the normal",
//!   "Inigo Quilez, 'Rendering Worlds with Two Triangles' (NVSCENE 2008, https://iquilezles.org/articles/nvscene2008/): five-tap AO along the normal"],
//!  "cost": {"class": "C2", "loop": "visSoftShadow: min(maxSteps, 64) scene evaluations at most (the loop's constant ceiling is 64); visAO: exactly 5", "tex": 0, "hooks": 1},
//!  "hooks": ["float mapScene(vec3 p)"],
//!  "contract": "The host defines float mapScene(vec3 p), a signed distance (negative inside). visSoftShadow(ro, rd, tRange, lightAngle, maxSteps) is the visibility in [0, 1] of a light of angular radius lightAngle (radians, clamped to [1e-4, 1.5]) seen along the unit direction rd from ro, marching t over tRange = (tmin, tmax): at each step the closest approach is triangulated from this step's and the last step's unbounding spheres (Aaltonen) where the step stayed inside the last sphere (its stride at most that sphere's radius) and the two spheres meet in a circle, and is Quilez's h / t everywhere else: on the first step, where a stride clamped up to the shortest left the last sphere behind (the spheres miss or barely touch, as on an open floor under a low light), and where the crossing lies within tmin of the start (a ray leaving its own surface); steps are clamped to [span / (8 n), 1.5 span / n] with n = clamp(maxSteps, 1, 64); a step at or inside a surface is full shadow; the result is smoothstepped. It is 1 in the open (including a floor lit from straight above, and an open floor under a light low enough that its whole disk is still above the horizon), 0 in an umbra, and its outer penumbra widens with the light's size and with the distance from the occluder. It estimates only the outer penumbra (inside the geometric shadow it is 0), and stops early when fully dark or past tmax. visAO(p, n, reach, falloff) samples mapScene at reach * (1..5) / 5 along the unit normal, takes each tap's missing room (h - mapScene) / h clamped to [0, 1], weights tap i by falloff^i (falloff clamped to [0, 1], reach floored at 1e-6) and returns 1 minus the weighted mean: exactly 1 on an open plane or a convex surface, falling into creases and contacts.",
//!  "note": "A distance field answers 'how much room is there around this point?', and that one answer gives shadows and occlusion almost for free per sample. Start the shadow ray off the surface (tmin, or ro nudged along the normal) or it shadows itself into speckles; light the KEY with the shadow and never with AO, and put AO on the fills (sky, bounce) only, which is Quilez's law: AO on a key reads 'horribly CG'. lightAngle is the light's real size: the sun is 0.0047 radians, a big soft box 0.1 to 0.3. visAO is the house's normalised five-tap form (each tap's shortfall as a fraction of its height), so 1 is fully open whatever the scene's scale and reach is in scene units: about the size of the creases you want to see. Both need a calibrated field: a bound that underestimates distance makes shadows too dark and too wide and AO too heavy. Budget them like memory reads: count mapScene calls per pixel. Wrong looks like speckled dark dots on lit faces (tmin too small), banded penumbrae or light leaking round corners (too few steps, too large a step), a shadow on a sunlit open floor (the degenerate leaving case not handled, or a low light triangulated across two spheres that do not overlap), or AO that darkens open ground (an uncalibrated field).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "light-visibility.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["XtyXzW", "llK3Dy", "cs2GWD", "ltdcW7"],
//!  "learn": ["SR 6.2", "SR 6.3", "LM 7.1", "LM 7.2", "LM 7.4", "LM 14.2", "study:XtyXzW 5.10", "study:XtyXzW 5.11"]}
// Apache-2.0, Akashic Aurora. Written fresh from the articles credited above.
//
// WHY. Walking a shadow ray toward the light, every step knows the radius of an empty ball around it. The ratio of
// that radius to the distance walked is roughly the angle by which the ray clears whatever is nearest: if that angle
// is smaller than the light's own angular radius, part of the light is hidden. Two consecutive empty balls overlap,
// and where their surfaces cross is a better guess of the true near-miss than either centre, which is Aaltonen's
// improvement: fewer bands where the steps are long.


// Visibility of a light of angular radius lightAngle along rd, from the scene the host defines in mapScene.
float visSoftShadow(vec3 ro, vec3 rd, vec2 tRange, float lightAngle, int maxSteps) {
    float tStart = max(tRange.x, 0.0);
    float tEnd = max(tRange.y, tStart);
    int budget = clamp(maxSteps, 1, 64);                     // 64: the loop's constant ceiling, below
    float span = tEnd - tStart;
    float shortest = span / (8.0 * float(budget));
    float longest = 1.5 * span / float(budget);
    float lightSlope = tan(clamp(lightAngle, 1e-4, 1.5));
    float seen = 1.0;
    float t = tStart;
    float roomBefore = 0.0;
    float lastStride = 0.0;
    for (int march = 0; march < 64; march++) {
        if (march >= budget || t >= tEnd) break;
        float room = mapScene(ro + rd * t);
        if (room <= 0.0) {
            seen = 0.0;
            break;
        }
        float clearAngle = room / max(t, 1e-6);                 // Quilez's h / t
        // Triangulate only where the step stayed inside the last empty ball (its stride was that ball's radius or
        // less) and the two balls meet in a circle. A step clamped UP to the shortest stride leaves the last ball
        // behind: the balls miss each other or barely touch, and the near miss collapses toward 0 (a black shadow on
        // an open floor under a low light).
        bool meet = lastStride > 0.0 && lastStride <= roomBefore && lastStride < roomBefore + room
                    && abs(room - roomBefore) < lastStride;
        if (meet) {
            // where the two balls' surfaces cross, measured back along the ray from here
            float back = (lastStride * lastStride + room * room - roomBefore * roomBefore) / (2.0 * lastStride);
            back = clamp(back, 0.0, room);
            float nearMiss = sqrt(max(room * room - back * back, 0.0));
            float fromStart = t - back;
            if (fromStart > tStart) {
                clearAngle = nearMiss / fromStart;
            }
        }
        seen = min(seen, clearAngle / lightSlope);
        if (seen < 0.004) break;
        roomBefore = room;
        lastStride = clamp(room, shortest, longest);
        t += lastStride;
    }
    seen = clamp(seen, 0.0, 1.0);
    return seen * seen * (3.0 - 2.0 * seen);
}

// Ambient occlusion from five distance taps along the normal; 1 is fully open.
float visAO(vec3 p, vec3 n, float reach, float falloff) {
    float tapSpacing = max(reach, 1e-6) / 5.0;
    float decay = clamp(falloff, 0.0, 1.0);
    float missing = 0.0;
    float trustSum = 0.0;
    float trust = 1.0;                                   // nearer taps count more: falloff^tap
    for (int tap = 1; tap <= 5; tap++) {
        float height = tapSpacing * float(tap);
        float room = mapScene(p + n * height);
        missing += trust * clamp((height - room) / height, 0.0, 1.0);
        trustSum += trust;
        trust *= decay;
    }
    return 1.0 - missing / trustSum;
}
