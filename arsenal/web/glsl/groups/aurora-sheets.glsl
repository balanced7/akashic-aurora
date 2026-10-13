//! {"name": "aurora-sheets", "kind": "recipe", "cat": "G8", "family": "G", "version": "1.3.0", "order": 61,
//!  "license": "Apache-2.0",
//!  "credits": ["nimitz, 'Auroras' (https://www.shadertoy.com/view/XtGGRt): stacked horizontal sheets reading one 2D triangle-wave footprint, spaced by a power of their index, a running average up the stack, a bowl in place of a flat plane (the technique, read in words; no code taken)",
//!   "Valdex, 'Chromatic Aurora Curtains' (https://www.shadertoy.com/view/ffG3Rc): the same stack dressed: static per-pixel jitter, hue by sheet kept apart from brightness, an analogous cyan-blue-indigo set (the technique, read in words; no code taken)",
//!   "alro, 'AURORA' (https://www.shadertoy.com/view/ttScDc): the footprint kept to a long arc across the sky (a window around an arc line), a green body under a red-magenta crown, a level of detail that smooths what a pixel cannot hold (the technique, read in words; no code taken)",
//!   "Orion Sky Lawlor and Jon Genetti, 'Interactive Volume Rendering Aurora on the GPU' (WSCG 2011, https://www.cs.uaf.edu/~olawlor/papers/2010/aurora/lawlor_aurora_2010.pdf): a curtain as footprint times altitude profile, and gamma on the colour's magnitude",
//!   "Alan Wolfe, 'Ray marching fog with blue noise' (https://blog.demofox.org/2020/05/10/ray-marching-fog-with-blue-noise/): a static per-pixel start offset turns the stepping between slices into fine grain"],
//!  "cost": {"class": "C2", "loop": "layers <= 48 sheets, each one noiseTriangle2 of 3 octaves, auroraRays (2 value noises), one hash21 and two auroraProfile, and in the fringe's few sheets a hash33 and one more auroraProfile; once per pixel a warpFbm2 (3 fBm) and a hash22, and with the fringe on a second warpFbm2 (the fold gate)", "tex": 0, "hooks": 2},
//!  "hooks": ["float mapScene(vec3 p)", "float densityAt(vec3 p)"],
//!  "entry": "vec3 auroraSheets(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, float clock, float intensity, float hemHeight, float curtainWidth, float fold, float rays, float fringe, int palette, float sky, float lake, int layers, int view)",
//!  "params": [
//!   {"name": "intensity", "label": "Intensity", "unit": "ratio", "range": [0, 3], "default": 1.2, "step": 0.01, "group": "light", "uniform": "u_auroraSheets_intensity",
//!    "help": "How much light the curtains emit. Lifted on a curve, so doubling it brightens them by about 1.7 times; a hot spot's weakest channel eases toward a ceiling, the whole colour with it, so it never goes white."},
//!   {"name": "hemHeight", "label": "Hem height", "unit": "world", "range": [0.5, 2.5], "default": 1, "step": 0.01, "group": "shape", "uniform": "u_auroraSheets_hemHeight",
//!    "help": "The world height of the lowest sheet, the curtains' sharp lower edge. The stack rises 0.32 of this above it; keep the eye below it. Higher (or narrower curtains) packs more arcs toward the horizon."},
//!   {"name": "curtainWidth", "label": "Curtain width", "unit": "world", "range": [0.4, 3], "default": 0.8, "step": 0.01, "group": "shape", "uniform": "u_auroraSheets_curtainWidth",
//!    "help": "The scale of the footprint on the ground plan: larger is fewer, broader arcs."},
//!   {"name": "fold", "label": "Folds", "unit": "ratio", "range": [0, 1], "default": 0.5, "step": 0.01, "group": "shape", "uniform": "u_auroraSheets_fold",
//!    "help": "How far a slow warped field pushes the arcs back and forth in depth: 0 straight arcs, 1 deep folds and ripples."},
//!   {"name": "rays", "label": "Rays", "unit": "ratio", "range": [0, 1], "default": 0.8, "step": 0.01, "group": "shape", "uniform": "u_auroraSheets_rays",
//!    "help": "How strongly sparse bright columns run straight up the curtains, darker curtain between them."},
//!   {"name": "fringe", "label": "Energetic fringe", "unit": "ratio", "range": [0, 1], "default": 0, "step": 0.01, "group": "colour", "uniform": "u_auroraSheets_fringe",
//!    "help": "The lower border of an active display, a thin coloured edge of its own at the bottom of the stack (up to 6 km), lit only along each arc's energetic stretches (short pieces that come and go, about 14 per cent of each arc's length at 0.35, 30 at 1) and never where a fold is seen edge-on: nitrogen purple in the physical palette, coral in the house ones. 0 is a quiet night. Where a near arc's fringe crosses a far arc's body, the fringe gives way (added, the two read as silver, then white)."},
//!   {"name": "palette", "label": "Palette", "unit": "choice", "default": 1, "group": "colour", "uniform": "u_auroraSheets_palette",
//!    "choices": [{"value": 0, "label": "House (ice cyan, periwinkle, violet; coral hem)"},
//!                {"value": 1, "label": "Physical (oxygen green, red crown)"},
//!                {"value": 2, "label": "Chromatic (cyan, electric blue, indigo)"}],
//!    "help": "Colour by sheet height. Physical, the default, is the emission lines in their true order: oxygen's green body, its red crown. House is analogous with one warm accent."},
//!   {"name": "sky", "label": "Sky", "unit": "ratio", "range": [0, 1], "default": 1, "step": 0.01, "group": "light", "uniform": "u_auroraSheets_sky",
//!    "help": "The house pre-dawn sky behind the curtains. 0 leaves black, for a host that composites its own backdrop."},
//!   {"name": "lake", "label": "Lake", "unit": "ratio", "range": [0, 1], "default": 0.55, "step": 0.01, "group": "scene", "uniform": "u_auroraSheets_lake",
//!    "help": "Below the horizon, a still lake mirrors the sky and the curtains at this strength. 0 leaves the horizon colour for a host's own ground. Free: a pixel reads either the sky or its mirror."},
//!   {"name": "layers", "label": "Layers", "unit": "count", "range": [8, 48], "default": 36, "step": 1, "group": "quality", "uniform": "u_auroraSheets_layers", "cost": true,
//!    "help": "Sheets in the stack. The cost is linear in it; the exposure is not (the stack is normalised), so fewer layers only show more grain (about 3 codes of 8 bits at 26, 1.5 at 36)."},
//!   {"name": "view", "label": "View", "unit": "choice", "default": 0, "group": "debug", "uniform": "u_auroraSheets_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "Layer index as colour"}, {"value": 2, "label": "Footprint alone"},
//!                {"value": 3, "label": "Running average off"}, {"value": 4, "label": "Jitter off"}],
//!    "help": "Debug views (atlas 16.3): which sheet the light comes from, the 2D footprint every sheet reads (at the hem), the stack without its smoothing, and without its static jitter (shows the stepping)."}],
//!  "contract": "auroraSheets returns scene-linear light (>= 0, finite) for the pixel's camera ray rd = camRay(pixel, res, basis, focal): the house sky (the band's skyGradient, times sky) plus, added, a stack of emitting sheets. Below the horizon (rd.y < 0) with lake <= 0 it is the sky's own colour there; with lake > 0 it is lake times exactly what the mirrored direction (rd.x, -rd.y, rd.z) shows above (a still lake at the eye). layers is read 1 to 48. Sheet i sits at world height marchStepPoly(i, hemHeight, spacing, 1.35), the top one 0.32 hemHeight above the hem, and each pixel reads it rmJitterStart(h, the gap to the next, u) higher, u = dthIgn(pixel + floor(64 hash22(floor(pixel / 2)))): IGN with its phase scrambled per 2 x 2 tile, static, so the stepping becomes still grain and not IGN's diagonal hatching. Each sheet is met by ixPlane along the bowed ray (rd.x, 2 rd.y + 0.4, rd.z), t = (h - ro.y) / (2 rd.y + 0.4): finite at the horizon (a bowl, never a streak to infinity). The eye must sit below hemHeight. The footprint at spot = (ro.xz + rd.xz t) / curtainWidth is a few long arcs: arc = 0.9 spot.y + 0.5 fold bend + 0.5 fold (n - 0.5) + 0.004 clock, lane = |arc - round(arc)|, each arc a thin curtain (0.009 / b) exp(-(lane / b)^2) with b = length(0.009, 0.9 reach, 0.9 gap), reach being the plan depth one pixel spans on the hem's sheet (2 |rd.z| (hemHeight - ro.y) / (2 rd.y + 0.4)^2 / curtainWidth times 2 / (res.y focal)) and gap the plan depth to the next sheet; so an arc widens, keeping its light, until a pixel and a sheet gap both hold it. Over each arc the filament field's creases glow within exp(-(lane / 0.2)^2): n = noiseTriangle2(0.18 spot.x, 1.6 spot.y + 0.9 fold bend) (3 octaves, churned at 0.035 clock), lit by shpInvPower(n + 0.012, 0.12, 3), carved by shpRemap (0.15 .. 1.15 to 0 .. 1) and floored at 0, soft-capped at 3.3, and faded to 0.02 as one pixel spans more than half a crease (1 - smoothstep(0.3, 0.8, 4 reach)). The footprint is (creases + 1.5 curtain) times a strength 0.35 + 0.65 hash21(round(arc), 3) per arc. bend is warpFbm2 read once at the hem. Rays are read where each sheet is met, so each stands straight up its curtain: the footprint times (1 - rays) + rays (0.08 + 2.4 auroraRays(9 spot.x, 0.3 clock)). Each sheet's light is its hue times that; a running average up the stack, drape = mix(sheet, drape, 2^(-16 / layers)), removes the stepping; the drapes are weighted by auroraProfile(106 + 160 frac, 106 + F, 35 km), frac being the sheet's height in the stack, and the sum is divided by the sum of auroraProfile(106 + 160 frac, 106, 35 km), so the exposure does not depend on layers (within 20 per cent from 16 to 48, measured). The fringe, F = 6 fringe km thick, is its own emitter in the bottom of the stack: its sheets stay out of the drape, and the brightest of them (never their sum: a fold seen edge-on stacks them all on one pixel, and a sum would follow the layer count) gives fringeTint times 4.8 times the footprint rayed halfway, (1 - rays / 2) + rays / 2 (0.08 + 2.4 ray) (rayed fully, it broke into crumbs a ray wide), times smoothstep(0, 0.25, fringe) (1 - smoothstep(F / 2, F, 160 frac)) auroraProfile(alt, 106, 2.5 km) times the arc's energetic stretches (aurora-band's, on a = 3 plan x / hemHeight - 0.05 clock, plan x = spot.x curtainWidth, with dice hash33(floor(a), round(arc), 13): about 14 per cent of each arc's length at 0.35, 30 at 1, no piece longer than 0.7 of a cell at any clock, a cell about 140 px of 480 on the near arcs at the top of a frame framed to 40 degrees, a size in the world so the pieces keep still under a moving eye) times the fold gate, 1 - smoothstep(4, 6, standing), standing being how many card pixels (1 / 270 of the frame's height) the arc's band stands on screen at the hem: 2 length(0.009, 0.9 reach) over the change of its smooth part (0.9 spot.y + 0.5 fold bend, no filament ripple) one card pixel up the frame, that ray mirrored too below the horizon, met on the hem's sheet and its own bend read there (only with the fringe on). A fold seen edge-on stands tall, and its lower border is a floor seen from below: a fringe there was a blob up to 10 px across. The tint is auroraLineColor(90, 1) for palette 1 and the house coral token otherwise. It is added to the stack's light times 1 - smoothstep(0, 0.004, luminance(light) / its peak): it shows against the dark sky and gives way where any drape lies behind it (a near arc's edge across a far arc's body summed to (0.96, 0.96, 0.95); half given way at 0.01, it read as a third pixel of edge). Hue: palette 1 is auroraLineColor(106 + 160 frac, 0) (green body, red crown); 0 and 2 are palRamp3(1.8 frac). The light is then multiplied by 2 intensity and smoothstep(0, 0.16, rd.y) (distant curtains fade into the horizon), lifted by displayHueSafeGamma(., 1.25), and held under white as in aurora-band: past 0.2 the weakest channel eases toward 0.35, the whole colour scaled with it (the tanh's argument clamped at 10). clock is the host's motion clock, as in aurora-band (the Play rule); every rate is slow and none commensurate. view 1 returns dbgHeatRamp of the light-weighted mean height in the stack (dark the hem, white the top) times the light; view 2 the footprint at the hem's sheet as grey; view 3 the stack without its running average; view 4 without its jitter. Hooks: the recipe calls neither, but composing ray-march (for rmJitterStart) and volume-march (for marchStepPoly) obliges every host to define float mapScene(vec3 p) and float densityAt(vec3 p), because WebGL refuses a program whose defined functions call undefined ones; a sky host defines them empty (return 1e9; and return 0.0;). The house rule: arsenal/web/glsl/README.md, Hooks.",
//!  "note": "The aurora with parallax: a curtain is a 2D pattern on the ground plan extruded straight up, so stack a few dozen transparent sheets, print the same footprint on each and look up through them; each crease shows on every sheet a little higher on the screen, and the copies merge into a drape with a crisp hem. Volume rendering at 2D prices, and correct from below, for the piano Spectacle, First Light and the site hero. Keep the footprint to a few long arcs, thin curtains across the view that meander and ripple, with the filament creases glowing only near them: a free creased field reads as scattered smudges with dark eyes. Read the rays on every sheet where that sheet is met, never once per pixel (that leans them out from the frame's centre). Let an arc widen to what a pixel and a sheet gap can hold, and fade the creases a pixel cannot: the far curtains blur instead of breaking into speckle. Draw the energetic fringe in pieces along the arcs (cells, each lit over a piece of its own, so no piece outgrows its cell at any clock) and let it give way to any drape behind it and wherever a fold is seen edge-on: along every arc it is an outline, over a far arc's green it reads white, and under an edge-on fold it is a floor seen from below, a coloured blob. Keep the churn slow (the sky must still be the same sky a second later), the jitter static and scrambled (plain IGN hatches), and spend layers where the eye looks (marchStepPoly crowds them at the bright hem). The lake is free: a pixel reads either the sky or its mirror. Finish with the house tail (tmSuperlinear, then displayOut's tanh). Wrong looks like a fog over the whole sky (the footprint not carved), a coloured line along every arc, white where arcs cross or a coloured blob under a fold (the fringe everywhere, added over a body, or on an edge-on fold's floor), streaks running to the horizon (a flat plane instead of the bowl), horizontal steps through every curtain (view 4, the jitter off), a regular diagonal hatching (unscrambled IGN), grain that crawls (a clock in the jitter), rays fanning out from below the horizon (rays read at the hem), a sky that reshapes in a second (the churn too fast), speckle toward the horizon (no level of detail), or soft bright smudges high in the frame (the camera looking too high: overhead the footprint is near and enormous; frame the sky from the horizon to about 40 degrees).",
//!  "debug": ["layer-index", "footprint", "no-average", "no-jitter"],
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "aurora-sheets.card",
//!  "twin": "arsenal/shaders/twins/groups_aurora.py", "status": "P0",
//!  "exemplars": ["ffG3Rc", "ttScDc"],
//!  "learn": ["VA 7.2 family B", "VA 7.1", "study:ffG3Rc 5.3", "study:ffG3Rc 5.4", "study:ttScDc 5.8", "study:ttScDc 5.16", "craft secret 12", "craft secret 22"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. A curtain is a 2D pattern on the ground plan extruded straight up. Stack a few dozen transparent sheets one
// above another, print the same pattern on each, and look up through them: each glowing line shows on every sheet, a
// little higher on the screen each time, and the copies merge into a tall drape with a crisp hem. Volume rendering at
// 2D prices. Hardware picture: a stack of thin-film layers, each with the same mask, read at an angle.

// The sky (or its mirror in a lake) plus the stacked curtains, in scene-linear light. Params after `clock` are the
// header's knobs, in order.
vec3 auroraSheets(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, float clock, float intensity, float hemHeight,
                  float curtainWidth, float fold, float rays, float fringe, int palette, float sky, float lake,
                  int layers, int view) {
    const vec3 zenith = vec3(0.0006, 0.0009, 0.0034);        // the band's sky: near black, a dim blue horizon
    const vec3 horizonGlow = vec3(0.0016, 0.0024, 0.0068);
    const vec3 dawnRose = vec3(0.0110, 0.0052, 0.0100);
    const vec3 toSun = vec3(0.4741, -0.0569, -0.8786);
    const vec3 coral = vec3(0.7454, 0.1683, 0.0782);          // the house accent token, linear (--wb-coral, #e0724f)
    const vec3 zenithward = vec3(0.0, 1.0, 0.0);
    const float edgeKm = 106.0;                               // the lowest sheet's altitude, as in the band
    vec3 rd = camRay(pixel, res, basis, focal);
    bool water = rd.y < 0.0;
    if (water && lake <= 0.0) {
        return max(sky, 0.0) * skyGradient(rd, toSun, zenith, horizonGlow, dawnRose);
    }
    // below the horizon the lake shows the sky above, mirrored: one read, either way
    vec3 look = water ? vec3(rd.x, -rd.y, rd.z) : rd;
    float reflectance = water ? lake : 1.0;
    vec3 backdrop = max(sky, 0.0) * skyGradient(look, toSun, zenith, horizonGlow, dawnRose);
    bool physical = palette == 1;
    bool chromatic = palette == 2;
    vec3 hemColour = chromatic ? vec3(0.0, 0.3801, 0.6921) : vec3(0.1873, 0.7106, 0.8689);
    vec3 bodyColour = chromatic ? vec3(0.0072, 0.1193, 1.0) : vec3(0.1960, 0.3672, 0.9331);
    vec3 crownColour = chromatic ? vec3(0.0835, 0.0272, 0.8276) : vec3(0.3424, 0.2049, 0.9331);
    // the energetic fringe, as in the band: nitrogen purple (physical) or coral, in the bottom 6 km x fringe, lit only
    // along each arc's energetic stretches
    const vec3 luma = vec3(0.2126, 0.7152, 0.0722);
    vec3 fringeTint = physical ? auroraLineColor(90.0, 1.0) : coral;
    float fringeAmount = clamp(fringe, 0.0, 1.0);
    float fringeOn = smoothstep(0.0, 0.25, fringeAmount);
    float fringeKm = max(6.0 * fringeAmount, 0.01);
    float fringeLuma = 4.8 * dot(fringeTint, luma);
    float stretchSize = 0.65 + 0.35 * fringeAmount;           // a stretch's length, cells, over 0.3 + 0.4 dice
    float stretchShare = 0.4 + 0.4 * fringeAmount;            // the share of its life cycle a cell is lit
    float rayMix = clamp(rays, 0.0, 1.0);

    int count = clamp(layers, 1, 48);
    float width = max(curtainWidth, 0.05);
    float hem = max(hemHeight, 0.05);
    // the bowl: the planes are met along a ray whose climb is lifted, so the stack reaches the horizon at a finite
    // distance (compressed, never streaked to infinity)
    vec3 bowed = vec3(look.x, 2.0 * look.y + 0.4, look.z);
    // static per-pixel jitter: the stepping between sheets becomes still grain. IGN's phase is scrambled per
    // 2 x 2 tile: plain IGN is one long diagonal ramp folded 53 times, and in a still stack its lines show as a
    // regular hatching
    float jitter = (view == 2 || view == 4) ? 0.0 : dthIgn(pixel + floor(64.0 * hash22(floor(0.5 * pixel))));
    // the fold field, read once at the hem: it is broad, so it barely changes across one stack
    vec2 hemSpot = (ro.xz + look.xz * max(ixPlane(ro, bowed, zenithward, -hem), 0.0)) / width;
    float bend = warpFbm2(vec2(0.35 * hemSpot.x + 0.011 * clock, 0.8 * hemSpot.y - 0.007 * clock), 1.0, 3, 23u);
    // how much plan depth one pixel spans on the hem's sheet (the bowl packs depth together toward the horizon): the
    // footprint's finest creases fade to their mean past about half a crease a pixel, and every arc is at least that
    // thick, so a far curtain blurs instead of breaking into speckle
    float reach = 2.0 * abs(look.z) * (hem - ro.y) / max(bowed.y * bowed.y, 1e-6) / width * (2.0 / (res.y * focal));
    float fine = 1.0 - smoothstep(0.3, 0.8, 4.0 * reach);
    // where an arc is seen edge-on (a fold running along the line of sight) its band at the hem stands tall on
    // screen, and its lower border is a floor seen from below, not an edge: a fringe there is a blob up to 10 px
    // across. How tall: the band's width at the hem over how much the arc's smooth part (no filament ripple) changes
    // one card pixel (1 / 270 of the frame) up, read on the hem's sheet with that ray's own bend. The fringe gives way
    // from 4 to 6 card pixels. Read only with the fringe on (a second warpFbm2 per pixel)
    float foldGate = 1.0;
    if (fringeOn > 0.0) {
        vec3 upRay = camRay(pixel + vec2(0.0, res.y / 270.0), res, basis, focal);
        vec3 upLook = water ? vec3(upRay.x, -upRay.y, upRay.z) : upRay;
        vec3 upBowed = vec3(upLook.x, 2.0 * upLook.y + 0.4, upLook.z);
        vec2 upSpot = (ro.xz + upLook.xz * max(ixPlane(ro, upBowed, zenithward, -hem), 0.0)) / width;
        float upBend = warpFbm2(vec2(0.35 * upSpot.x + 0.011 * clock, 0.8 * upSpot.y - 0.007 * clock), 1.0, 3, 23u);
        float arcStep = abs(0.9 * (upSpot.y - hemSpot.y) + 0.5 * fold * (upBend - bend));
        float standing = 2.0 * length(vec2(0.009, 0.9 * reach)) / max(arcStep, 1e-6);
        foldGate = 1.0 - smoothstep(4.0, 6.0, standing);
    }
    float top = 0.32 * hem;                                   // the stack's height above its hem
    float spacing = top / pow(float(max(count - 1, 1)), 1.35);
    float keep = exp2(-16.0 / float(count));                  // the smoothing covers the same height at any count
    vec3 drape = vec3(0.0);
    vec3 light = vec3(0.0);
    vec3 fringeLight = vec3(0.0);
    float fringePeak = 0.0;
    float weights = 0.0;
    float heightSum = 0.0;
    float strandSum = 0.0;
    for (int sheetIndex = 0; sheetIndex < 48; ++sheetIndex) {
        if (sheetIndex >= count) {
            break;
        }
        // the sheet's height: dense at the bright hem, sparse in the faint top, read a static fraction of a gap higher
        float base = marchStepPoly(sheetIndex, hem, spacing, 1.35);
        float rise = marchStepPoly(sheetIndex + 1, hem, spacing, 1.35) - base;
        float h = rmJitterStart(base, rise, jitter);
        vec2 spot = (ro.xz + look.xz * ixPlane(ro, bowed, zenithward, -h)) / width;
        // the plan depth between this sheet and the next along the pixel's ray: an arc at least that thick is met
        // by both, so the stack shows one drape, not a pile of lines
        float gap = abs(look.z) * rise / max(bowed.y, 1e-6) / width;
        // the footprint: a few long arcs, thin curtains along lines of constant depth that meander with the fold
        // field and ripple with the filament field, each its own strength; the filament field's creases (carved: only
        // they glow) lit near the arcs
        float n = noiseTriangle2(vec2(0.18 * spot.x, 1.6 * spot.y + 0.9 * fold * bend), 0.035 * clock, 3);
        float strands = max(shpRemap(shpInvPower(n + 0.012, 0.12, 3.0), 0.15, 1.15, 0.0, 1.0), 0.0);
        strands = mix(0.02, strands / (1.0 + 0.3 * strands), fine);
        float arc = 0.9 * spot.y + 0.5 * fold * bend + 0.5 * fold * (n - 0.5) + 0.004 * clock;
        float lane = abs(arc - floor(arc + 0.5));
        float blur = length(vec3(0.009, 0.9 * reach, 0.9 * gap));
        float curtain = (0.009 / blur) * exp(-(lane / blur) * (lane / blur));
        float strength = 0.35 + 0.65 * hash21(vec2(floor(arc + 0.5), 3.0));
        float foot = (exp(-(lane / 0.2) * (lane / 0.2)) * strands + 1.5 * curtain) * strength;
        if (view == 2) {
            return vec3(0.3 * foot);
        }
        // rays: columns along the curtain, read where THIS sheet is met, so each ray stands straight up its curtain
        float ray = auroraRays(9.0 * spot.x, 0.3 * clock, 5u);
        float lit = foot * ((1.0 - rayMix) + rayMix * (0.08 + 2.4 * ray));
        float frac = (h - hem) / top;                         // 0 at the hem, 1 at the top sheet
        float alt = edgeKm + 160.0 * frac;
        vec3 hue;
        if (physical) {
            hue = auroraLineColor(alt, 0.0);
        } else {
            hue = palRamp3(1.8 * frac, hemColour, bodyColour, crownColour);    // the crown colour by just past half way
        }
        // the energetic fringe: its own thin emitter in the bottom fringeKm of the stack, the body above it (never a
        // tint over the body: near-complements summed on one pixel read as silver); its sheets stay out of the drape
        float layer = fringeOn * (1.0 - smoothstep(0.5 * fringeKm, fringeKm, 160.0 * frac));
        vec3 sheet = hue * (lit * (1.0 - layer));
        drape = view == 3 ? sheet : mix(sheet, drape, keep);  // a one-pole low-pass up the stack: no stepping
        float w = auroraProfile(alt, edgeKm, 35.0);           // a sharp rise at the hem, an exponential top
        float body = auroraProfile(alt, edgeKm + fringeKm, 35.0);
        light = cmpAdd(light, drape * body);
        if (layer > 0.0) {
            // lit only along the arc's energetic stretches, as in the band: cells along the arc, three per unit of
            // plan x over the hem's height (a size in the world, so they keep still under a moving eye; the near arcs
            // at the top of a frame framed to 40 degrees show a cell as about 140 px of 480), each arc its own dice,
            // each cell lit over one stretch of its own on its own slow life cycle, drifting slowly: drawn along the
            // whole of every arc it reads as a glowing outline. The brightest fringe sheet, never their sum: a fold
            // seen edge-on stacks every fringe sheet on one pixel (a hot blob), and a sum would make the fringe's
            // exposure follow the layer count
            float stretchAt = 3.0 * spot.x * width / hem - 0.05 * clock;
            float stretchCell = floor(stretchAt);
            vec3 dice = hash33(vec3(stretchCell, floor(arc + 0.5), 13.0));
            float stretchLength = (0.3 + 0.4 * dice.y) * stretchSize;
            float stretchStart = 0.5 + (dice.z - 0.5) * (0.8 - stretchLength) - 0.5 * stretchLength;
            float inCell = stretchAt - stretchCell;
            float life = fract(dice.x + clock / 120.0);
            float energetic = smoothstep(stretchStart, stretchStart + 0.08, inCell)
                              * (1.0 - smoothstep(stretchStart + stretchLength - 0.08, stretchStart + stretchLength,
                                                  inCell))
                              * smoothstep(0.0, 0.1, life) * (1.0 - smoothstep(stretchShare - 0.1, stretchShare, life));
            // the rays only halfway: under full rays the fringe broke into crumbs a ray wide
            float edgeLit = foot * ((1.0 - 0.5 * rayMix) + 0.5 * rayMix * (0.08 + 2.4 * ray));
            float energy = edgeLit * layer * energetic * foldGate;
            fringeLight = max(fringeLight, fringeTint * (4.8 * energy * auroraProfile(alt, edgeKm, 2.5)));
            fringePeak = max(fringePeak, fringeLuma * energy);
        }
        weights += w;
        heightSum += frac * lit * w;
        strandSum += lit * w;
    }
    weights = max(weights, 1e-6);
    if (view == 1) {
        return dbgHeatRamp(heightSum / max(strandSum, 1e-6)) * min(strandSum / weights, 1.0);
    }
    // the fringe shows against the dark sky and gives way where any drape (a far arc's body behind a near arc's edge)
    // passes 0.4 per cent of its own peak: purple or coral summed with green or cyan reads as silver, then white, and
    // a fringe half given way still reads as a third pixel of edge (0.4 per cent rather than 1 is a safety margin that
    // no pin needs: the twin's SHEET_FRINGE_YIELD gives the measurement)
    light += fringeLight * (1.0 - smoothstep(0.0, 0.004, dot(light, luma) / max(fringePeak, 1e-9)));
    // normalised by the stack's weights, so a quality tier changes cost, not exposure; then the glow lift
    // distant curtains near the horizon fade (a long, dim path through the lower air)
    float horizonFade = smoothstep(0.0, 0.16, look.y);
    light = displayHueSafeGamma((2.0 * max(intensity, 0.0) * horizonFade / weights) * light, 1.25);
    // the ceiling under white, as in the band: past 0.2 the weakest channel eases toward 0.35, the colour with it
    float weakest = min(light.r, min(light.g, light.b));
    if (weakest > 0.2) {                                      // tanh's argument clamped, as tmTanh does (tone.glsl)
        light *= (0.2 + 0.15 * tanh(min((weakest - 0.2) / 0.15, 10.0))) / weakest;
    }
    return reflectance * cmpAdd(backdrop, light);
}
