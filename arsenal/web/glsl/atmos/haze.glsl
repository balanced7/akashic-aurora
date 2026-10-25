//! {"name": "atmos-haze", "kind": "helper", "cat": "G7", "family": "G", "version": "1.0.0", "order": 26,
//!  "license": "Apache-2.0",
//!  "credits": ["L. G. Henyey and J. L. Greenstein, 'Diffuse radiation in the Galaxy' (Astrophysical Journal 93, 1941, https://doi.org/10.1086/144246): the forward-scattering lobe that makes beams aimed at the crowd read brighter",
//!   "Christopher Kulla and Marcos Fajardo, 'Importance Sampling Techniques for Path Tracing in Participating Media' (EGSR 2012, https://www.arnoldrenderer.com/research/egsr2012_volume.pdf): equiangular sampling of the in-scatter from a point or spot light along a view ray",
//!   "Matt Pharr, Wenzel Jakob and Greg Humphreys, 'Physically Based Rendering', 4th ed., chapter 11 (https://pbr-book.org/4ed/Volume_Scattering): single scattering, transmittance and the radiance a thin slab adds",
//!   "Bart Wronski, 'Volumetric fog: unified compute shader based solution to atmospheric scattering' (SIGGRAPH 2014, https://bartwronski.com/publications/): haze that only shows light, lit per light, never an ambient wash"],
//!  "cost": {"class": "C1", "loop": "hazeCone 10 equiangular samples and hazeLamp 6 (constant bounds); every other part is straight-line", "tex": 0, "hashes": "hazeDensity 8 pcg3d; hazeFloorBand 8 pcg3d; hazeStreak 16 pcg4d; hazeDensity3 16 pcg4d; hazeStreak3 8 pcg4d; hazeCone 16 + 10 x 8 pcg4d; hazeLamp 16 pcg4d; hazeSheet3 24 pcg4d"},
//!  "contract": "Haze shows light; it never is light. Every part returns in-scattered light (linear, scene-referred, 1.0 = SDR white) that is EXACTLY zero where no light reaches: each profile has compact support (hazeBeam ends 8 widths from its axis, hazeSheet 2.2 half-angles from its centre, hazePoint and hazePool at 3 radii, hazeCone at 2.6 times its half-angle measure, hazeLamp at its reach), and there is no ambient term. Densities are 0..1: hazeDensity = exp(-max(y - floorY, 0) / hz.y) x (0.55 + 0.45 x two octaves of value noise at hz.x cells per unit drifting hz.zw units per second); hazeDensity3 is the same field in metres with the wind in x and z; hazeFloorBand is a low band, 1 at and below floorY, gone by a ragged top 0.7..1.3 thicknesses up, its billows rising; hazeStreak and hazeStreak3 are clumps stretched ALONG the rays from a light (clump = (along length, across angle in radians, contrast, outward drift per second)): 1 - contrast between clumps, 1 inside them, contrast faded out within 3 along-lengths of the light. The fields are static and move only by their drift terms (no reseed). hazeBeamCoords(p, root, dir, reach) = (signed perpendicular distance, distance along dir / reach, angle from dir seen from the root). hazePhase(towardViewer) = phaseHG(towardViewer, 0.6) / phaseHG(0, 0.6): 1 side-on, about 10.7 aimed 0.9 toward the viewer. hazeBeam: core line (Gaussian, about 1 px) x (0.05 + 0.95 dens), so it appears where there is haze and breaks into dashes across clumps (a faint thread remains in clean air), body (Gaussian, 0.35 widths) x dens x phase x 0.30, halo (exponential, one width, smooth on the axis) x (0.35 + 0.65 dens) x phase x 0.08; the core and body carry the light's own chroma unchanged; the root's first percent runs hot (glowHotCoreTo toward white, 6x at the root, e-folding over 1.2 per cent of the reach, so the pastel stretch between white root and coloured beam stays short); fall exp(-0.9 along), faded out over the last 20 per cent. hazeSheet: a soft angular plateau (0.5 at the half-angle, no outline) x (0.3 + 0.7 dens) x phase, a white-hot root (6x, e-folding over 3 per cent), fall exp(-1.4 along). hazePoint: (0.7 Gaussian + 0.3 exponential tail) x (0.35 + 0.65 dens), never 1/r^2. hazePool: an elliptical lit spot on a surface (no haze term). hazeTint turns the light's OKLCh hue by +20 degrees x dens (dens capped at 1.25). hazeCone: single scattering through a soft spot cone along the view ray segment [0, tMax], sigma = air.x x hazeDensity3 (linear between the segment ends) x hazeStreak3, HG phase g = 0.6 over the isotropic phase, transmittance exp(-0.035 air.x t), 10 stratified equiangular samples (jitter in [0, 1) shifts them), samples within 0.45 m of the apex whitened toward the light's peak; hazeLamp is the same for a point source of finite reach; hazeSheet3 is the analytic single scatter of a thin fan sheet (radiance falls as 1/r in the fan, an edge-on view is capped at a path of 1 / max(thickness, 0.05) per metre). Negative colours, levels and densities read as 0.",
//!  "note": "Haze is the cinema of a light show: beams appear only where there is something in the air to catch them, and the air takes the colour of whatever light is inside it. So nothing here paints the air: every part is a light's in-scatter, and the room stays black until a light crosses it. The three judges' failures fixed by construction: (1) mint and pastel beams: the core and body keep the light's full chroma and only the root whitens, the halo is a narrow bounded exponential (no wide glow washing blue air toward mint), multiplied by 0.35 + 0.65 x density as Look v2 2.4 asks; (2) round haze blobs: hazeStreak's clumps are stretched along the rays from each light, so a thin beam crossing a clump breaks into dashes that follow the beam, and the halo shows streaks parallel to it; size the clumps to 0.5..3 m (in a 2D scene a frame height is about 20..30 m at the cloud, so along 0.02..0.1 frame heights); (3) flat hard wedges: every cross-section is smooth with a soft edge and the light falls off along its length into a pool where it lands. The 2D parts take the caller's units (frame heights usually) and pixel widths; the 3D parts take metres and a view ray, so they drop into a ray-marched scene or a three.js ShaderMaterial unchanged (no three.js names inside). Levels: halo and haze 0.02..0.3 (dark and coloured, the OLED rule); held cores 2..4 in HDR, near 1 in SDR; roots 4..12. Wrong looks like a grey veil over the room (an ambient term, or a halo that never reaches zero), a mint or pastel beam over blue air (white in the body, or a wide halo), round blobs inside beams (isotropic clumps), crawling haze (a reseeded field, or t not wrapped by the host), or a hard edge at a beam's root (the start fade missing).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "atmos-haze.card",
//!  "twin": "arsenal/shaders/twins/haze.py", "status": "P1", "exemplars": [],
//!  "learn": ["VA 5.1", "VA 1.5", "house look-v2 2.2", "house qlimax-2014 1.5"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. A beam of light in a hall is invisible until it crosses smoke; what the eye sees is light scattered out of the
// beam toward it, in proportion to how much smoke is there and to which way the beam points (smoke throws light
// forward, like a dish antenna). Get three things right and a beam reads as light rather than as a painted wedge: the
// colour stays in the beam (white only where the lens blinds the camera), the smoke's texture shows inside the beam,
// and where there is no light there is nothing at all. Think of the haze as a dark room full of dust: the dust is
// always there, and it only lights up where a beam passes.

// ------------------------------------------------------------------------------------------- the 2D field (any units)

// Height haze in 0..1: densest at the floor, thinning by e per hz.y units up, and patchy (two octaves of value noise
// at hz.x cells per unit) without ever going clear. The field drifts hz.zw units per second.
float hazeDensity(vec2 p, float floorY, vec4 hz, float t) {
    float cells = max(hz.x, 1e-4);
    float lift = max(hz.y, 1e-4);
    vec2 q = (p - hz.zw * t) * cells;
    float n = 0.6667 * noiseValue2(q, 0x9E3779B9u) + 0.3333 * noiseValue2(2.03 * q + vec2(17.13, 5.71), 0x9E3779BAu);
    float height = exp(-max(p.y - floorY, 0.0) / lift);
    return height * (0.55 + 0.45 * (0.5 + 0.5 * n));
}

// A low CO2 / dry-ice band in 0..1: full at and below the floor line, gone by a ragged top 0.7..1.3 thicknesses up.
// Its billows rise at about an eighth of a thickness per second.
float hazeFloorBand(vec2 p, float floorY, float thickness, float t) {
    float th = max(thickness, 1e-4);
    float h = (p.y - floorY) / th;
    float billow = 0.5 + 0.5 * noiseValue2(vec2(p.x / (1.3 * th), 0.9 * h - 0.12 * t), 0x2545F491u);
    float top = 0.7 + 0.6 * billow;
    float body = 1.0 - smoothstep(0.15 * top, top, h);
    float grain = 0.5 + 0.5 * noiseValue2(vec2(p.x / (0.45 * th) + 0.03 * t, 2.2 * h - 0.3 * t), 0x2545F492u);
    return body * (0.7 + 0.3 * grain);
}

// Clumps stretched along the rays from a light at `root`, in 0..1. clump = (along length, across angle in radians,
// contrast 0..1, outward drift per second). The field is indexed by the direction from the root (so its streaks are
// radial and a beam from the root runs along them) and by the distance (so they are long along the beam and short
// across it); it is static in the world and does not turn when the beam does, so a sweeping beam passes through it.
float hazeStreak(vec2 p, vec2 root, vec4 clump, float t) {
    vec2 d = p - root;
    float r = length(d);
    vec2 u = d / max(r, 1e-6);
    float alongLen = max(clump.x, 1e-4);
    float acrossAngle = max(clump.y, 1e-4);
    vec3 q = vec3(u / acrossAngle, (r - clump.w * t) / alongLen);
    float n = 0.65 * noiseValue3(q, 0x3C6EF372u)
            + 0.35 * noiseValue3(q * vec3(2.0, 2.0, 1.7) + vec3(3.1, 7.7, 1.9), 0x3C6EF373u);
    float clumps = smoothstep(0.38, 0.62, 0.5 + 0.5 * n);
    float fade = smoothstep(0.5 * alongLen, 3.0 * alongLen, r);     // near the root the angular cells are sub-pixel
    return mix(1.0, clumps, clamp(clump.z, 0.0, 1.0) * fade);
}

// A beam's frame: (signed distance from its axis, distance along it over its reach, angle from its axis seen from the
// root). along < 0 is behind the root.
vec3 hazeBeamCoords(vec2 p, vec2 root, vec2 dir, float reach) {
    vec2 a = dir / max(length(dir), 1e-12);
    vec2 d = p - root;
    float along = dot(d, a);
    float perp = a.x * d.y - a.y * d.x;
    float guard = abs(along) + abs(perp) < 1e-12 ? 1e-12 : 0.0;      // atan(0, 0) is undefined in GLSL
    return vec3(perp, along / max(reach, 1e-6), atan(perp, along + guard));
}

// How much brighter a beam reads for leaning toward the viewer (towardViewer = the beam direction's component toward
// the eye, -1..1): the Henyey-Greenstein lobe at g = 0.6, normalised to 1 for a beam seen side-on.
float hazePhase(float towardViewer) {
    return phaseHG(towardViewer, 0.6) / phaseHG(0.0, 0.6);
}

// --------------------------------------------------------------------------------------------- 2D light in the haze

// A thin beam (a laser or a narrow shaft) in the haze. dPerpPx = distance from the axis in pixels; along = 0 at the
// root, 1 at the end; dens = the local density (hazeDensity x hazeStreak); widthPx = the halo width (6..20 px);
// phase = hazePhase. The core line and the body keep the light's chroma; only the root whitens. The line appears
// where there is haze (0.05 + 0.95 dens, Look v2 2.1: beams appear where there is haze), so a beam crossing clumps
// breaks into dashes; the halo keeps Look v2 2.4's 0.35 + 0.65 dens. A scene that wants a laser seen in clean air
// passes a higher density for it.
vec3 hazeBeam(float dPerpPx, float along, vec3 col, float level, float dens, float widthPx, float phase) {
    float w = max(widthPx, 1.0);
    float d = abs(dPerpPx);
    float coreW = max(0.9, 0.08 * w);
    float bodyW = 0.35 * w;
    float core = exp(-0.5 * (d / coreW) * (d / coreW));
    float body = exp(-(d / bodyW) * (d / bodyW));
    float halo = exp(-(sqrt(d * d + bodyW * bodyW) - bodyW) / w);    // exponential tail, smooth across the axis
    float reachOut = 1.0 - smoothstep(6.0 * w, 8.0 * w, d);          // exactly zero 8 widths out
    float start = smoothstep(-0.012, 0.012, along);
    float fall = exp(-0.9 * max(along, 0.0)) * (1.0 - smoothstep(0.8, 1.0, along)) * start;
    float haze = clamp(dens, 0.0, 1.0);
    float shown = 0.35 + 0.65 * haze;                                // Look v2 2.4: the halo's share of the haze
    float seen = 0.05 + 0.95 * haze;                                 // beams appear where there is haze: dashes
    float root = exp(-max(along, 0.0) / 0.012);
    vec3 tint = max(col, vec3(0.0));
    float scatter = max(phase, 0.0);
    vec3 line = tint * (core * seen);
    vec3 shaft = tint * (scatter * (0.30 * body * haze + 0.08 * halo * shown * (1.0 + 2.0 * root)));
    vec3 hot = glowHotCoreTo(tint, 6.0 * root, vec3(1.0)) * max(core, body);
    return max(level, 0.0) * fall * reachOut * (line + shaft + hot);
}

// A sheet of light (a laser fan or a wide shaft seen edge-on in 2D: a wedge from its root). angle = the pixel's angle
// from the sheet's centre line seen from the root; halfAngle = the half-spread at half brightness. A soft plateau, no
// outline at the edges, the haze's texture inside, a white-hot root, fading along its length.
vec3 hazeSheet(float angle, float halfAngle, float along, vec3 col, float level, float dens, float phase) {
    float hw = max(halfAngle, 1e-4);
    float a = abs(angle) / hw;
    float a2 = a * a;
    float across = (0.92 * exp(-0.693147 * a2 * a2) + 0.08 * exp(-max(a - 1.0, 0.0) / 0.6))
                 * (1.0 - smoothstep(1.7, 2.2, a));
    float start = smoothstep(-0.012, 0.012, along);
    float fall = exp(-1.4 * max(along, 0.0)) * (1.0 - smoothstep(0.8, 1.0, along)) * start;
    float haze = clamp(dens, 0.0, 1.0);
    float root = exp(-max(along, 0.0) / 0.03);
    vec3 tint = max(col, vec3(0.0));
    vec3 body = tint * (across * (0.3 + 0.7 * haze) * max(phase, 0.0));
    vec3 hot = glowHotCoreTo(tint, 6.0 * root, vec3(1.0)) * across;
    return max(level, 0.0) * fall * (body + hot);
}

// The haze glowing round a small source (a lens, an LED, a spark): a Gaussian with an exponential skirt, exactly zero
// beyond 3 radii. Never 1 / r^2, whose tail would light the whole frame.
vec3 hazePoint(vec2 p, vec2 c, float r, vec3 col, float level, float dens) {
    float x = length(p - c) / max(r, 1e-6);
    float glow = (0.7 * exp(-2.0 * x * x) + 0.3 * exp(-2.5 * x)) * (1.0 - smoothstep(2.0, 3.0, x));
    return max(col, vec3(0.0)) * (max(level, 0.0) * glow * (0.35 + 0.65 * clamp(dens, 0.0, 1.0)));
}

// The pool where a beam lands on a surface (radii r in x and y): surface light, so no haze term.
vec3 hazePool(vec2 p, vec2 c, vec2 r, vec3 col, float level) {
    float x = length((p - c) / max(r, vec2(1e-6)));
    float lit = (0.75 * exp(-2.0 * x * x) + 0.25 * exp(-3.0 * x)) * (1.0 - smoothstep(2.0, 3.0, x));
    return max(col, vec3(0.0)) * (max(level, 0.0) * lit);
}

// Dense CO2 lit by a beam reads pinker than the beam: turn the light's OKLCh hue by +20 degrees x density (at most
// 25), at constant lightness and chroma.
vec3 hazeTint(vec3 light, float dens) {
    return hueRotateOklch(max(light, vec3(0.0)), clamp(dens, 0.0, 1.25) * (20.0 / 360.0));
}

// ----------------------------------------------------------------------------------------------- the 3D field (metres)

// hazeDensity in metres: the same height haze and two octaves of value noise, the wind in x and z (hz.zw m/s).
float hazeDensity3(vec3 p, float floorY, vec4 hz, float t) {
    float cells = max(hz.x, 1e-4);
    float lift = max(hz.y, 1e-4);
    vec3 q = (p - vec3(hz.z, 0.0, hz.w) * t) * cells;
    float n = 0.6667 * noiseValue3(q, 0x9E3779B9u)
            + 0.3333 * noiseValue3(2.03 * q + vec3(17.13, 5.71, 11.3), 0x9E3779BAu);
    float height = exp(-max(p.y - floorY, 0.0) / lift);
    return height * (0.55 + 0.45 * (0.5 + 0.5 * n));
}

// hazeStreak in 3D: clumps stretched along the rays from the light at src (clump as in hazeStreak, lengths in metres).
float hazeStreak3(vec3 p, vec3 src, vec4 clump, float t) {
    vec3 d = p - src;
    float r = length(d);
    vec3 u = d / max(r, 1e-6);
    float alongLen = max(clump.x, 1e-4);
    float acrossAngle = max(clump.y, 1e-4);
    vec3 q = u / acrossAngle + vec3(0.48, 0.64, 0.6) * ((r - clump.w * t) / alongLen);
    float clumps = smoothstep(0.36, 0.64, 0.5 + 0.5 * noiseValue3(q, 0x3C6EF374u));
    float fade = smoothstep(0.5 * alongLen, 3.0 * alongLen, r);
    return mix(1.0, clumps, clamp(clump.z, 0.0, 1.0) * fade);
}

// A spot light's angular profile at p (0..1): 0.5 at halfAngle (radians, at most 0.8), a soft plateau inside, exactly
// zero past about 1.6 half-angles. Also the floor pool of a cone: profile / r^2 x cos(incidence).
float hazeConeProfile(vec3 p, vec3 apex, vec3 axis, float halfAngle) {
    vec3 v = p - apex;
    float cosA = dot(v, axis) / max(length(v) * length(axis), 1e-9);
    float s = (1.0 - cosA) / (1.0 - cos(clamp(halfAngle, 1e-3, 0.8)));
    return exp(-0.693147 * s * s) * (1.0 - smoothstep(2.0, 2.6, s));
}

// Single scattering of a spot cone (a moving head) along the view ray ro + rd t, t in [0, tMax]. air = (haze amount,
// floor height); hz the hazeDensity3 field; clump the hazeStreak3 clumps; jitter in [0, 1) per pixel (blue noise or a
// hash) hides the sampling. Equiangular samples put most of them near the lens, where the light is.
vec3 hazeCone(vec3 ro, vec3 rd, float tMax, vec3 apex, vec3 axis, float halfAngle, vec3 col, float level, vec2 air,
              vec4 hz, vec4 clump, float t, float jitter) {
    vec3 a = axis / max(length(axis), 1e-9);
    float oneMinusCosHw = 1.0 - cos(clamp(halfAngle, 1e-3, 0.8));
    float cosEdge = 1.0 - 2.6 * oneMinusCosHw;                       // the cone where the profile reaches zero
    vec3 co = ro - apex;
    float c2 = cosEdge * cosEdge;
    float da = dot(rd, a);
    float oa = dot(co, a);
    float qa = da * da - c2;                                         // (qa t^2 + 2 qh t + qc) = 0 on the cone
    float qh = da * oa - c2 * dot(rd, co);
    float qc = oa * oa - c2 * dot(co, co);
    if (abs(qa) < 1e-6) qa = qa < 0.0 ? -1e-6 : 1e-6;
    float spreadQ = qh * qh - qa * qc;
    if (spreadQ < 0.0) return vec3(0.0);
    float halfChord = sqrt(spreadQ);
    float ra = (-qh - halfChord) / qa;
    float rb = (halfChord - qh) / qa;
    float lo = min(ra, rb);
    float hi = max(ra, rb);
    float t0 = lo;
    float t1 = hi;
    if (qa > 0.0) {                         // the ray's direction is inside the opening: it ends inside one nappe
        if (da > 0.0) { t0 = hi; t1 = 1e4; } else { t0 = -1e4; t1 = lo; }
    } else if (oa + da * 0.5 * (lo + hi) < 0.0) {
        return vec3(0.0);                   // the chord is in the backward nappe
    }
    t0 = max(t0, 0.0);
    t1 = min(t1, min(tMax, 1e4));
    if (t1 <= t0) return vec3(0.0);
    float delta = dot(apex - ro, rd);
    float D = max(length(co + rd * delta), 0.06);                    // the lens has a size
    float thA = atan((t0 - delta) / D);
    float thB = atan((t1 - delta) / D);
    float dens0 = hazeDensity3(ro + rd * t0, air.y, hz, t);
    float dens1 = hazeDensity3(ro + rd * t1, air.y, hz, t);
    float amount = max(air.x, 0.0);
    vec3 tint = max(col, vec3(0.0));
    float peak = max(max(tint.r, tint.g), tint.b);
    vec3 gathered = vec3(0.0);
    for (int tap = 0; tap < 10; ++tap) {
        float u = (float(tap) + fract(jitter)) / 10.0;
        float ts = delta + D * tan(mix(thA, thB, u));
        vec3 p = ro + rd * ts;
        vec3 v = p - apex;
        float r = sqrt(D * D + (ts - delta) * (ts - delta));
        float s = (1.0 - dot(v, a) / r) / oneMinusCosHw;
        float prof = exp(-0.693147 * s * s) * (1.0 - smoothstep(2.0, 2.6, s));
        float k = clamp((ts - t0) / max(t1 - t0, 1e-6), 0.0, 1.0);
        float sigma = amount * mix(dens0, dens1, k) * hazeStreak3(p, apex, clump, t);
        float phase = phaseHG(dot(rd, -v / r), 0.6) / phaseIso();
        float through = exp(-0.035 * amount * ts);
        float nearLens = exp(-(r / 0.45) * (r / 0.45));
        gathered += mix(tint, vec3(peak), nearLens) * (sigma * prof * phase * through);
    }
    return gathered * (max(level, 0.0) * (thB - thA) / (10.0 * D));
}

// The analytic single scatter of a thin fan sheet: the plane through apex with this normal, centred on axis, spread
// halfAngle (radians, at half brightness) either side in the plane. One point per ray, no loop.
vec3 hazeSheet3(vec3 ro, vec3 rd, float tMax, vec3 apex, vec3 axis, vec3 normal, float halfAngle, float thickness,
                vec3 col, float level, vec2 air, vec4 hz, vec4 clump, float t) {
    vec3 n = normal / max(length(normal), 1e-9);
    float facing = dot(rd, n);
    if (abs(facing) < 1e-6) return vec3(0.0);
    float ts = dot(apex - ro, n) / facing;
    if (ts <= 0.0 || ts >= tMax) return vec3(0.0);
    vec3 p = ro + rd * ts;
    vec3 v = p - apex;
    float r = max(length(v), 0.06);
    float x = acos(clamp(dot(v, axis) / (r * max(length(axis), 1e-9)), -1.0, 1.0)) / clamp(halfAngle, 1e-3, 1.4);
    float x2 = x * x;
    float across = (0.92 * exp(-0.693147 * x2 * x2) + 0.08 * exp(-max(x - 1.0, 0.0) / 0.6))
                 * (1.0 - smoothstep(1.7, 2.2, x));
    float amount = max(air.x, 0.0);
    float sigma = amount * hazeDensity3(p, air.y, hz, t) * hazeStreak3(p, apex, clump, t);
    float phase = phaseHG(dot(rd, -v / r), 0.6) / phaseIso();
    float through = exp(-0.035 * amount * ts);
    float lean = max(abs(facing), max(thickness, 0.05));             // an edge-on sheet: a bright line, capped
    vec3 tint = max(col, vec3(0.0));
    float peak = max(max(tint.r, tint.g), tint.b);
    vec3 c = mix(tint, vec3(peak), exp(-(r / 0.45) * (r / 0.45)));
    return c * (max(level, 0.0) * sigma * across * phase * through / (r * lean));
}

// A point source of finite reach (an LED, a lamp) scattering in the haze along the view ray: equiangular samples over
// the part of the ray inside its reach, exactly zero outside it.
vec3 hazeLamp(vec3 ro, vec3 rd, float tMax, vec3 pos, float reach, vec3 col, float level, vec2 air, vec4 hz, float t,
              float jitter) {
    float R = max(reach, 1e-3);
    vec3 co = ro - pos;
    float delta = -dot(co, rd);
    float D2 = dot(co, co) - delta * delta;
    if (D2 >= R * R) return vec3(0.0);
    float chord = sqrt(R * R - D2);
    float t0 = max(delta - chord, 0.0);
    float t1 = min(delta + chord, tMax);
    if (t1 <= t0) return vec3(0.0);
    float D = max(sqrt(max(D2, 0.0)), 0.06);
    float thA = atan((t0 - delta) / D);
    float thB = atan((t1 - delta) / D);
    float dens0 = hazeDensity3(ro + rd * t0, air.y, hz, t);
    float dens1 = hazeDensity3(ro + rd * t1, air.y, hz, t);
    float amount = max(air.x, 0.0);
    vec3 tint = max(col, vec3(0.0));
    float peak = max(max(tint.r, tint.g), tint.b);
    vec3 gathered = vec3(0.0);
    for (int tap = 0; tap < 6; ++tap) {
        float u = (float(tap) + fract(jitter)) / 6.0;
        float ts = delta + D * tan(mix(thA, thB, u));
        vec3 v = ro + rd * ts - pos;
        float r = sqrt(D * D + (ts - delta) * (ts - delta));
        float reachOut = 1.0 - smoothstep(0.4 * R, R, r);
        float k = clamp((ts - t0) / max(t1 - t0, 1e-6), 0.0, 1.0);
        float sigma = amount * mix(dens0, dens1, k);
        float phase = phaseHG(dot(rd, -v / r), 0.6) / phaseIso();
        float through = exp(-0.035 * amount * ts);
        float nearLens = exp(-(r / 0.45) * (r / 0.45));
        gathered += mix(tint, vec3(peak), nearLens) * (sigma * reachOut * phase * through);
    }
    return gathered * (max(level, 0.0) * (thB - thA) / (6.0 * D));
}
