//! {"name": "atmos-haze", "kind": "helper", "cat": "G7", "family": "G", "version": "2.0.0", "order": 26,
//!  "license": "Apache-2.0",
//!  "credits": ["L. G. Henyey and J. L. Greenstein, 'Diffuse radiation in the Galaxy' (Astrophysical Journal 93, 1941, https://doi.org/10.1086/144246): the forward-scattering lobe that makes beams aimed at the crowd read brighter",
//!   "Christopher Kulla and Marcos Fajardo, 'Importance Sampling Techniques for Path Tracing in Participating Media' (EGSR 2012, https://www.arnoldrenderer.com/research/egsr2012_volume.pdf): equiangular sampling of the in-scatter from a point or spot light along a view ray",
//!   "Matt Pharr, Wenzel Jakob and Greg Humphreys, 'Physically Based Rendering', 4th ed., chapter 11 (https://pbr-book.org/4ed/Volume_Scattering) and chapter 2.4 (https://pbr-book.org/4ed/Monte_Carlo_Integration/Improving_Efficiency): single scattering, transmittance, and the balance heuristic for mixing two sampling strategies",
//!   "Bart Wronski, 'Volumetric fog: unified compute shader based solution to atmospheric scattering' (SIGGRAPH 2014, https://bartwronski.com/publications/): haze that only shows light, lit per light, never an ambient wash",
//!   "Robert Ulichney, 'The void-and-cluster method for dither array generation' (Proc. SPIE 1913, 1993, https://doi.org/10.1117/12.152707): the blue-noise table behind hazeBlueNoise, generated fresh for the house",
//!   "Milton Abramowitz and Irene Stegun, 'Handbook of Mathematical Functions' (1964), formula 7.1.26 (https://personal.math.ubc.ca/~cbm/aands/page_299.htm): the error-function fit that box-filters a moving beam over the shutter"],
//!  "cost": {"class": "C1", "loop": "hazeStreak 2 octaves, hazeCone 12 equiangular samples, hazeLamp 8, hazeRing3 12 (constant bounds); every other part is straight-line", "tex": 0, "hashes": "hazeDensity 8 pcg3d; hazeFloorBand 8 pcg3d; hazeStreak 8 pcg3d; hazeDensity3 16 pcg4d; hazeStreak3 8 pcg4d; hazeCone 32 + 12 x 8 pcg4d; hazeLamp 32 pcg4d; hazeRing3 32 pcg4d; hazeSheet3 24 pcg4d; hazeBlueNoise none (a 64-word table)"},
//!  "contract": "Haze shows light; it never is light. Every part returns in-scattered light (linear, scene-referred, 1.0 = SDR white) that is EXACTLY zero where no light reaches: each profile has compact support (hazeBeam ends 8 widths from its axis, hazeBeamSwept 8 widths plus half its sweep, hazeSheet 2.2 half-angles from its centre, hazePoint and hazePool at 3 radii, hazeRing 3 band half-widths plus its reach from the band, hazeCone at 2.6 times its half-angle measure, hazeLamp at its reach, hazeRing3 at its reach from the band), and there is no ambient term. Densities are 0..1: hazeDensity = exp(-max(y - floorY, 0) / hz.y) x (0.55 + 0.45 x two octaves of value noise at hz.x cells per unit drifting hz.zw units per second); hazeDensity3 is the same field in metres with the wind in x and z; hazeFloorBand is a low band, 1 at and below floorY, gone by a ragged top 0.7..1.3 thicknesses up, its billows rising. hazeStreak is dash-sized clumps stretched ALONG the rays from a light (clump = (dash length along the ray, cell width across it in radians, contrast, outward drift per second)): two octaves of value noise on (angle round the light in whole cells, so no seam; distance over the dash length), thresholded so about 40 per cent of the field is clump with a soft end of a few per cent of a dash; 1 - contrast between clumps, 1 inside them, the contrast faded in over 0.5..3 dash lengths from the light; hazeStreak3 is the 3D form (one octave, smoother). The fields are static and move only by their drift terms (no reseed). hazeBeamCoords(p, root, dir, reach) = (signed perpendicular distance, distance along dir / reach, angle from dir seen from the root). hazePhase(towardViewer) = phaseHG(towardViewer, 0.6) / phaseHG(0, 0.6): 1 side-on, about 10.7 aimed 0.9 toward the viewer. hazeBeam: core line (Gaussian, about 1 px) x (coreFloor + (1 - coreFloor) dens), so with a low floor it appears where there is haze and breaks into dashes across clumps, and with a high floor (a laser that must always show) it stays a line; body (Gaussian, 0.35 widths) x dens x phase x 0.30; halo (exponential, one width, smooth on the axis) x (0.35 + 0.65 dens) x phase x 0.08; the core and body carry the light's own chroma unchanged; the root's first percent runs hot (glowHotCoreTo toward white, 6x at the root, e-folding over 1.2 per cent of the reach); fall exp(-0.9 along), faded out over the last 20 per cent. hazeBeamSwept is hazeBeam averaged exactly over a shutter during which the beam's axis moved sweepPx across this pixel (the haze field is static in the world, so only the profile moves): the core and body are box-filtered in closed form (an error-function fit good to 2e-7), the halo by three Gauss-Legendre points; below a quarter pixel it is hazeBeam. hazeSheet: a soft angular plateau (0.5 at the half-angle, no outline) x (0.3 + 0.7 dens) x phase, a white-hot root (6x, e-folding over 3 per cent), fall exp(-1.4 along); its body colour is chosen by pale in 0..1: 0 the light's hue with its white part removed (the most saturated colour of that hue at the same peak: saturated), 1 the colour as given, raised by 1 + 3 x its white part (min channel / max channel), because a pale colour reads as light only when it is bright (pale-and-bright: spends headroom, so it wants HDR); the root stays white-hot either way. hazePoint: (0.7 Gaussian + 0.3 exponential tail) x (0.35 + 0.65 dens), never 1/r^2. hazePool: an elliptical lit spot on a surface (no haze term). hazeTint turns the light's OKLCh hue by +20 degrees x dens (dens capped at 1.25). hazeRing: the haze lit by an LED ring or an open arc of one (ring = (radius, band half-width, haze depth, reach); arc = (centre angle, half-span in radians; a half-span of pi or more is a closed ring)): the closed-form line integral of 1/distance^2 over the arc, softened by the haze depth (an area light seen through a slab of haze), normalised to 1 on a closed band, times a window that reaches exactly 0 at 3 half-widths plus the reach from the band, times dens; plus the band's own tight glow (as hazePoint, 0 beyond 3 half-widths). The inside of a ring is lit from every side, so it glows more than the outside at the same distance. hazeCone: single scattering through a soft spot cone along the view ray segment [0, tMax], sigma = air.x x hazeDensity3 (linear between the segment ends) x hazeStreak3, HG phase g = 0.6 over the isotropic phase, transmittance exp(-0.035 t) (the hall's visibility, about 28 m, independent of the haze amount, so more haze never dims a beam: the light is exactly proportional to air.x), 12 stratified equiangular samples (jitter in [0, 1) shifts them: pass hazeBlueNoise of the pixel), samples within 0.45 m of the apex whitened toward the light's peak; hazeLamp is the same for a point source of finite reach (8 samples); hazeRing3 is the same for a closed LED ring in metres (ring = (radius, band half-width, reach)): its irradiance in closed form (level / (nearest distance x farthest distance) to the ring, softened by the band, so far away it is a lamp of that level), 12 samples, half drawn as 1 / distance about where the ray crosses the ring's plane (an asinh map) and half uniform over the chord, mixed by the balance heuristic, phase taken toward the nearest point of the band; hazeSheet3 is the analytic single scatter of a thin fan sheet (radiance falls as 1/r in the fan, an edge-on view is capped at a path of 1 / max(thickness, 0.05) per metre). hazeBlueNoise(pixel) is a 16 x 16 void-and-cluster blue-noise threshold in (0, 1), tiled: as the per-pixel jitter it turns the estimators' error into fine grain with no crosshatch. Negative colours, levels and densities read as 0.",
//!  "note": "Haze is the cinema of a light show: beams appear only where there is something in the air to catch them, and the air takes the colour of whatever light is inside it. So nothing here paints the air: every part is a light's in-scatter, and the room stays black until a light crosses it. Fixed by construction: (1) mint and pastel beams: the core and body keep the light's full chroma and only the root whitens, the halo is a narrow bounded exponential, multiplied by 0.35 + 0.65 x density as Look v2 2.4 asks; (2) round haze blobs: hazeStreak's clumps are dash-sized and stretched along the rays from each light, so a thin beam crossing a cloud breaks into short dashes that follow the beam, and neighbouring lines of a fan break in step (the feathered rows of the Berlin frames); size the dashes to the frame (the Berlin cloud's dashes are about 0.012 frame heights long, so pass 0.012..0.02); (3) flat hard wedges: every cross-section is smooth with a soft edge and the light falls off along its length; (4) air that does not glow: an LED ring or band is an area light, and hazeRing / hazeRing3 light the room round it in its colour with a bounded falloff. Fans of many lines: draw only the nearest one or two lines of a fan per pixel (pick them by the pixel's angle from the root) and add one hazeSheet over the fan at the level of the halos between its lines; a moving fan's lines go through hazeBeamSwept with sweepPx = the angular speed x the shutter (1/60 s) x the distance from the root in pixels. The 2D parts take the caller's units (frame heights usually) and pixel widths; the 3D parts take metres and a view ray, so they drop into a ray-marched scene or a three.js ShaderMaterial unchanged (no three.js names inside). Levels: halo and haze 0.02..0.3 (dark and coloured, the OLED rule); held cores 2..4 in HDR, near 1 in SDR; roots 4..12; a ring's haze at the theme's air_Y (0.035 for a blue-violet ring). Wrong looks like a grey veil over the room (an ambient term, or a halo that never reaches zero), a mint or pastel beam over blue air (white in the body, or a wide halo), round blobs inside beams (isotropic clumps), a regular mesh of unbroken lines where a cloud should be (clumps too long or too soft, or a core floor too high), crawling haze (a reseeded field, or t not wrapped by the host), a crosshatch in the 3D air (a structured jitter such as interleaved gradient noise used alone), a dimmer room at more haze (extinction tied to the haze amount), or a hard edge at a beam's root (the start fade missing).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "atmos-haze.card",
//!  "twin": "arsenal/shaders/twins/haze.py", "status": "P1", "exemplars": [],
//!  "learn": ["VA 5.1", "VA 1.5", "house look-v2 2.2", "house qlimax-2014 1.5", "house qlimax-2014 3.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. A beam of light in a hall is invisible until it crosses smoke; what the eye sees is light scattered out of the
// beam toward it, in proportion to how much smoke is there and to which way the beam points (smoke throws light
// forward, like a dish antenna). Get three things right and a beam reads as light rather than as a painted wedge: the
// colour stays in the beam (white only where the lens blinds the camera), the smoke's texture shows inside the beam,
// and where there is no light there is nothing at all. Think of the haze as a dark room full of dust: the dust is
// always there, and it only lights up where a beam passes. A big LED ring is a lamp spread along a circle: the dust
// round it lights up in its colour, more inside the ring than outside, and fades to nothing before the corners.

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

// Dash-sized clumps stretched along the rays from a light at `root`, in 0..1. clump = (dash length along the ray,
// cell width across it as an angle in radians, contrast 0..1, outward drift per second). Two octaves of value noise
// on (the angle round the root, counted in whole cells so the circle closes without a seam; the distance from the root
// in dash lengths), cut so about 40 per cent of the field is clump. A beam from the root runs along the cells and
// breaks into dashes where it crosses them; neighbouring lines of a fan, closer than a cell, break in step. The field
// is static in the world and does not turn when the beam does, so a sweeping beam passes through it.
float hazeStreak(vec2 p, vec2 root, vec4 clump, float t) {
    vec2 d = p - root;
    float r = length(d);
    float dashLen = max(clump.x, 1e-4);
    float around = max(floor(6.2831853 / max(clump.y, 1e-4) + 0.5), 3.0);
    float guard = r < 1e-12 ? 1e-12 : 0.0;                                   // atan(0, 0) is undefined in GLSL
    float turn = (atan(d.y, d.x + guard) * 0.15915494 + 0.5) * around;     // 0..around, whole cells round the root
    vec2 q = vec2(turn, (r - clump.w * t) / dashLen);
    float n = 0.0;
    for (int octave = 0; octave < 2; ++octave) {
        float scale = octave == 0 ? 1.0 : 2.0;
        uint period = uint(around * scale + 0.5);
        vec2 qo = q * scale + (octave == 0 ? vec2(0.0) : vec2(0.5, 0.37));
        uvec2 cell = cellU2(qo);
        vec2 inCell = qo - floor(qo);
        uint x0 = cell.x % period;
        uint x1 = (cell.x + 1u) % period;
        uint stream = octave == 0 ? 0x3C6EF372u : 0x3C6EF373u;
        float c00 = 2.0 * u01(pcg3d(uvec3(x0, cell.y, stream)).x) - 1.0;
        float c10 = 2.0 * u01(pcg3d(uvec3(x1, cell.y, stream)).x) - 1.0;
        float c01 = 2.0 * u01(pcg3d(uvec3(x0, cell.y + 1u, stream)).x) - 1.0;
        float c11 = 2.0 * u01(pcg3d(uvec3(x1, cell.y + 1u, stream)).x) - 1.0;
        vec2 ease = inCell * inCell * inCell * (inCell * (inCell * 6.0 - 15.0) + 10.0);
        n += (octave == 0 ? 0.7 : 0.3) * mix(mix(c00, c10, ease.x), mix(c01, c11, ease.x), ease.y);
    }
    float clumps = smoothstep(0.46, 0.64, 0.5 + 0.5 * n);
    float width = r * max(clump.y, 1e-4) / dashLen;                         // a cell's width in dash lengths
    float fade = smoothstep(0.5 * dashLen, 3.0 * dashLen, r) * smoothstep(0.05, 0.12, width);   // no sub-pixel cells
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
// root, 1 at the end; dens = the local density (hazeDensity x hazeStreak); widthPx = the halo width (4..20 px);
// phase = hazePhase; coreFloor = how much of the core line shows in clean air (0.05: a beam seen only where there is
// haze, breaking into dashes across clumps; 0.6..1: a laser that must always show). The core line and the body keep
// the light's chroma; only the root whitens; the halo keeps Look v2 2.4's 0.35 + 0.65 dens.
vec3 hazeBeam(float dPerpPx, float along, vec3 col, float level, float dens, float widthPx, float phase,
              float coreFloor) {
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
    float lineFloor = clamp(coreFloor, 0.0, 1.0);
    float seen = lineFloor + (1.0 - lineFloor) * haze;               // beams appear where there is haze: dashes
    float root = exp(-max(along, 0.0) / 0.012);
    vec3 tint = max(col, vec3(0.0));
    float scatter = max(phase, 0.0);
    vec3 line = tint * (core * seen);
    vec3 shaft = tint * (scatter * (0.30 * body * haze + 0.08 * halo * shown * (1.0 + 2.0 * root)));
    vec3 hot = glowHotCoreTo(tint, 6.0 * root, vec3(1.0)) * max(core, body);
    return max(level, 0.0) * fall * reachOut * (line + shaft + hot);
}

// hazeBeam for a moving beam: the light averaged over a shutter during which the beam's axis crossed sweepPx pixels
// here (sweepPx = angular speed x shutter x distance from the root in pixels; dPerpPx is the distance at mid-shutter).
// The haze field is static in the world, so only the profile moves: the core and body Gaussians are box-filtered in
// closed form (Abramowitz and Stegun 7.1.26 for erf), the halo by three Gauss-Legendre points. Below a quarter pixel
// of sweep this is hazeBeam.
vec3 hazeBeamSwept(float dPerpPx, float sweepPx, float along, vec3 col, float level, float dens, float widthPx,
                   float phase, float coreFloor) {
    float s = abs(sweepPx);
    if (s < 0.25) return hazeBeam(dPerpPx, along, col, level, dens, widthPx, phase, coreFloor);
    float w = max(widthPx, 1.0);
    float coreW = max(0.9, 0.08 * w);
    float bodyW = 0.35 * w;
    float x0 = dPerpPx - 0.5 * s;
    float x1 = dPerpPx + 0.5 * s;
    vec4 z = vec4(x0, x1, x0, x1) / vec4(1.4142136 * coreW, 1.4142136 * coreW, bodyW, bodyW);
    vec4 az = abs(z);
    vec4 k = 1.0 / (1.0 + 0.3275911 * az);
    vec4 poly = k * (0.254829592 + k * (-0.284496736 + k * (1.421413741 + k * (-1.453152027 + k * 1.061405429))));
    vec4 erfz = sign(z) * (1.0 - poly * exp(-az * az));
    float core = max(1.2533141 * coreW * (erfz.y - erfz.x) / s, 0.0);        // sqrt(pi / 2) coreW (erf - erf) / s
    float body = max(0.88622693 * bodyW * (erfz.w - erfz.z) / s, 0.0);       // sqrt(pi) / 2 bodyW (erf - erf) / s
    float halo = 0.0;
    for (int node = 0; node < 3; ++node) {
        float at = dPerpPx + 0.5 * s * (node == 0 ? -0.7745967 : (node == 1 ? 0.0 : 0.7745967));
        float weight = node == 1 ? 0.44444444 : 0.27777778;
        halo += weight * exp(-(sqrt(at * at + bodyW * bodyW) - bodyW) / w);
    }
    float nearest = max(abs(dPerpPx) - 0.5 * s, 0.0);
    float reachOut = 1.0 - smoothstep(6.0 * w, 8.0 * w, nearest);
    float start = smoothstep(-0.012, 0.012, along);
    float fall = exp(-0.9 * max(along, 0.0)) * (1.0 - smoothstep(0.8, 1.0, along)) * start;
    float haze = clamp(dens, 0.0, 1.0);
    float shown = 0.35 + 0.65 * haze;
    float lineFloor = clamp(coreFloor, 0.0, 1.0);
    float seen = lineFloor + (1.0 - lineFloor) * haze;
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
// outline at the edges, the haze's texture inside, a white-hot root, fading along its length. pale picks the body's
// colour: 0 saturated (the hue with its white part removed), 1 pale-and-bright (the colour as given, lifted so a pale
// colour reads as light, not grey; that spends headroom).
vec3 hazeSheet(float angle, float halfAngle, float along, vec3 col, float level, float dens, float phase, float pale) {
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
    float top = max(tint.r, max(tint.g, tint.b));
    float low = min(tint.r, min(tint.g, tint.b));
    vec3 pure = top - low > 1e-6 ? (tint - low) * (top / (top - low)) : tint;     // the hue at the same peak, no white
    float pl = clamp(pale, 0.0, 1.0);
    vec3 bodyTint = mix(pure, tint * (1.0 + 3.0 * low / max(top, 1e-9)), pl);
    vec3 body = bodyTint * (across * (0.3 + 0.7 * haze) * max(phase, 0.0));
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

// The haze lit by an LED ring, or an open arc of one, centred at c. ring = (radius, band half-width, the depth of the
// haze in front of and behind the band, reach of the glow beyond the band); arc = (the arc's centre angle, its
// half-span, radians; a half-span of pi or more closes the ring). The ring is a lamp spread along a circle: the light
// reaching a point is the integral of 1 / distance^2 over the arc, which has a closed form (the depth softens it, the
// way a slab of haze sees the band from in front and behind). It is normalised to 1 on a closed band, so level is the
// haze's level next to the band; inside a ring every side lights the haze, so it glows more there than outside. A
// window takes it to exactly 0 at 3 half-widths plus the reach from the band, and the band's own tight glow sits on top.
vec3 hazeRing(vec2 p, vec2 c, vec4 ring, vec2 arc, vec3 col, float level, float dens) {
    vec2 v = p - c;
    float rho = length(v);
    float R = max(ring.x, 1e-4);
    float hw = max(ring.y, 1e-5);
    float depth = max(ring.z, hw);
    float reach = max(ring.w, 1e-4);
    float closeIn = (rho - R) * (rho - R) + depth * depth;                 // a - b of 1 / (a - b cos(psi))
    float farOut = (rho + R) * (rho + R) + depth * depth;                  // a + b
    float root = sqrt(closeIn * farOut);
    float turn = 6.2831853 / root;                                         // the closed ring's integral
    float span = turn;
    float e = abs(rho - R);                                                // distance to the band
    if (arc.y < 3.1415926) {
        float halfSpan = max(arc.y, 0.0);
        float guard = rho < 1e-12 ? 1e-12 : 0.0;
        float phi = atan(v.y, v.x + guard);
        float delta = mod(arc.x - phi + 3.1415927, 6.2831853) - 3.1415927;  // the arc's centre from p's angle
        float stretch = sqrt(farOut / closeIn);
        float xa = delta - halfSpan;
        float xb = delta + halfSpan;
        float ma = floor(xa * 0.15915494 + 0.5);
        float mb = floor(xb * 0.15915494 + 0.5);
        float ya = xa - 6.2831853 * ma;
        float yb = xb - 6.2831853 * mb;
        float ga = 2.0 / root * atan(stretch * sin(0.5 * ya), cos(0.5 * ya)) + ma * turn;
        float gb = 2.0 / root * atan(stretch * sin(0.5 * yb), cos(0.5 * yb)) + mb * turn;
        span = max(gb - ga, 0.0);
        if (abs(delta) > halfSpan) {
            vec2 endA = R * vec2(cos(arc.x - halfSpan), sin(arc.x - halfSpan));
            vec2 endB = R * vec2(cos(arc.x + halfSpan), sin(arc.x + halfSpan));
            e = min(length(v - endA), length(v - endB));
        }
    }
    float room = depth * R * span * 0.31830989;                            // 1 on a closed band
    float x = max(e - 3.0 * hw, 0.0) / reach;
    float window = 1.0 - smoothstep(0.0, 1.0, x);
    float u = e / hw;
    float band = (0.7 * exp(-2.0 * u * u) + 0.3 * exp(-2.5 * u)) * (1.0 - smoothstep(2.0, 3.0, u));
    float haze = clamp(dens, 0.0, 1.0);
    return max(col, vec3(0.0)) * (max(level, 0.0) * (room * window * haze + 0.5 * band * (0.35 + 0.65 * haze)));
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

// A per-pixel jitter in (0, 1) for the samplers below: a 16 x 16 blue-noise threshold table (void and cluster,
// generated fresh for the house), tiled. Neighbouring pixels get far-apart offsets with no pattern at any angle, so a
// few samples' error reads as fine grain instead of the crosshatch a structured jitter leaves.
float hazeBlueNoise(vec2 pixel) {
    const uint table[64] = uint[64](
        0x184C34A1u, 0x71CA3A97u, 0xAC820B52u, 0xDC69E605u, 0xCE73FCB5u, 0x30B755AEu, 0xF83CDD9Bu, 0x217BBE4Eu,
        0x278B0157u, 0xF27F07E7u, 0x2675C91Au, 0x40F01692u, 0x5DC3DF96u, 0x48D89141u, 0xB8588E65u, 0xCCA761D3u,
        0xA3156C2Du, 0xA6236BF7u, 0x1EDB02BFu, 0x800F3878u, 0x7D3BEEABu, 0x7ACB0CB9u, 0x9E43FD35u, 0x4DFAB2E4u,
        0xDA50C009u, 0xE8549831u, 0x516EAA17u, 0xD2678A2Au, 0x1C8C6F9Cu, 0xB63DF366u, 0xF1C6885Fu, 0x223FC108u,
        0xB1F92BEAu, 0x900681D0u, 0x95132FD7u, 0x83E0A85Bu, 0x104562C7u, 0xE528A54Bu, 0x3ECD7749u, 0x531476ECu,
        0xE1AD9304u, 0xBC60C874u, 0x6AAFFB1Du, 0xB437D125u, 0x8732CF7Cu, 0x9A39F61Fu, 0x00A05985u, 0xFE9D86BAu,
        0x5AEF1942u, 0xEB6D039Fu, 0x47E2330Eu, 0x642056F5u, 0x46BB70E9u, 0xB04FC2D9u, 0x8FC57ED6u, 0xA4DE1272u,
        0xA90A942Cu, 0x248D7929u, 0x2E1B6844u, 0xC44AB3D4u, 0xF484D55Eu, 0xFF11E363u, 0x5CEDBDA2u, 0x0D893699u);
    uvec2 cell = cellU2(pixel) & 15u;
    uint index = cell.y * 16u + cell.x;
    uint rank = (table[index >> 2u] >> ((index & 3u) * 8u)) & 255u;
    return (float(rank) + 0.5) / 256.0;
}

// Single scattering of a spot cone (a moving head) along the view ray ro + rd t, t in [0, tMax]. air = (haze amount,
// floor height); hz the hazeDensity3 field; clump the hazeStreak3 clumps; jitter in [0, 1) per pixel (hazeBlueNoise)
// hides the sampling. Equiangular samples put most of them near the lens, where the light is. The haze amount scales
// what the air scatters, never how far you see (the hall's 28 m), so more haze is never a dimmer beam.
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
    for (int tap = 0; tap < 12; ++tap) {
        float u = (float(tap) + fract(jitter)) / 12.0;
        float ts = delta + D * tan(mix(thA, thB, u));
        vec3 p = ro + rd * ts;
        vec3 v = p - apex;
        float r = sqrt(D * D + (ts - delta) * (ts - delta));
        float s = (1.0 - dot(v, a) / r) / oneMinusCosHw;
        float prof = exp(-0.693147 * s * s) * (1.0 - smoothstep(2.0, 2.6, s));
        float k = clamp((ts - t0) / max(t1 - t0, 1e-6), 0.0, 1.0);
        float sigma = amount * mix(dens0, dens1, k) * hazeStreak3(p, apex, clump, t);
        float phase = phaseHG(dot(rd, -v / r), 0.6) / phaseIso();
        float through = exp(-0.035 * ts);
        float nearLens = exp(-(r / 0.45) * (r / 0.45));
        gathered += mix(tint, vec3(peak), nearLens) * (sigma * prof * phase * through);
    }
    return gathered * (max(level, 0.0) * (thB - thA) / (12.0 * D));
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
    float through = exp(-0.035 * ts);
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
    for (int tap = 0; tap < 8; ++tap) {
        float u = (float(tap) + fract(jitter)) / 8.0;
        float ts = delta + D * tan(mix(thA, thB, u));
        vec3 v = ro + rd * ts - pos;
        float r = sqrt(D * D + (ts - delta) * (ts - delta));
        float reachOut = 1.0 - smoothstep(0.4 * R, R, r);
        float k = clamp((ts - t0) / max(t1 - t0, 1e-6), 0.0, 1.0);
        float sigma = amount * mix(dens0, dens1, k);
        float phase = phaseHG(dot(rd, -v / r), 0.6) / phaseIso();
        float through = exp(-0.035 * ts);
        float nearLens = exp(-(r / 0.45) * (r / 0.45));
        gathered += mix(tint, vec3(peak), nearLens) * (sigma * reachOut * phase * through);
    }
    return gathered * (max(level, 0.0) * (thB - thA) / (8.0 * D));
}

// A closed LED ring (a lamp spread along a circle: centre, the normal of its plane, ring = (radius, band half-width,
// reach of its glow beyond the band), metres) scattering in the haze along the view ray. Its irradiance has a closed
// form, level / (nearest distance x farthest distance to the circle), softened by the band, so far away it is a lamp
// of that level and close to the band it falls as 1 / distance like a long tube. Twelve samples over the ray's chord
// through the ring's bounding sphere: half drawn in proportion to 1 / distance about where the ray crosses the ring's
// plane (an asinh map: the light is there and falls like a tube's), half uniform (the tails), weighted by the balance
// heuristic, so the estimate stays unbiased. Exactly zero beyond the reach from the band.
vec3 hazeRing3(vec3 ro, vec3 rd, float tMax, vec3 centre, vec3 normal, vec3 ring, vec3 col, float level, vec2 air,
               vec4 hz, float t, float jitter) {
    vec3 n = normal / max(length(normal), 1e-9);
    // a radial for points on the ring's axis: square to n, taken against y unless n is nearly vertical, then z
    vec3 sideY = -vec3(n.z, 0.0, -n.x);                                  // n x y
    vec3 sideZ = vec3(n.y, -n.x, 0.0);                                   // n x z
    vec3 side = normalize(dot(sideY, sideY) > 0.01 ? sideY : sideZ);
    float R = max(ring.x, 1e-3);
    float hw = max(ring.y, 0.01);
    float reach = max(ring.z, 1e-3);
    float bound = R + reach;
    vec3 co = ro - centre;
    float mid = -dot(co, rd);
    float D2 = dot(co, co) - mid * mid;
    if (D2 >= bound * bound) return vec3(0.0);
    float chord = sqrt(bound * bound - D2);
    float t0 = max(mid - chord, 0.0);
    float t1 = min(mid + chord, tMax);
    if (t1 <= t0) return vec3(0.0);
    float facing = dot(rd, n);
    float tc = clamp(abs(facing) > 1e-4 ? -dot(co, n) / facing : mid, t0, t1);
    vec3 vc = co + rd * tc;
    float hc = dot(vc, n);
    float rhoC = length(vc - hc * n);
    float Dc = max(sqrt(hc * hc + (rhoC - R) * (rhoC - R)), hw);
    float sA = asinh((t0 - tc) / Dc);
    float sB = asinh((t1 - tc) / Dc);
    float chordLen = t1 - t0;
    float dens0 = hazeDensity3(ro + rd * t0, air.y, hz, t);
    float dens1 = hazeDensity3(ro + rd * t1, air.y, hz, t);
    float amount = max(air.x, 0.0);
    float inScatter = 0.0;
    for (int tap = 0; tap < 12; ++tap) {
        float u = (float(tap) + fract(jitter)) / 12.0;
        float ts = u < 0.5 ? tc + Dc * sinh(mix(sA, sB, 2.0 * u)) : mix(t0, t1, 2.0 * u - 1.0);
        float off = ts - tc;
        float pdf = 0.5 / (sqrt(off * off + Dc * Dc) * max(sB - sA, 1e-9)) + 0.5 / chordLen;
        vec3 v = co + rd * ts;
        float h = dot(v, n);
        vec3 inPlane = v - h * n;
        float rho = length(inPlane);
        float gap2 = h * h + (rho - R) * (rho - R);
        float irr = 1.0 / sqrt((gap2 + hw * hw) * (h * h + (rho + R) * (rho + R) + hw * hw));
        float window = 1.0 - smoothstep(0.35 * reach, reach, sqrt(gap2));
        vec3 toBand = v - R * (rho > 1e-6 ? inPlane / rho : side);
        float phase = phaseHG(dot(rd, -toBand / max(length(toBand), 1e-6)), 0.6) / phaseIso();
        float k = clamp((ts - t0) / chordLen, 0.0, 1.0);
        float sigma = amount * mix(dens0, dens1, k);
        inScatter += sigma * irr * window * phase * exp(-0.035 * ts) / pdf;
    }
    return max(col, vec3(0.0)) * (max(level, 0.0) * inScatter / 12.0);
}
