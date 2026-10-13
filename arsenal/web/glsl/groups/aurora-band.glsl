//! {"name": "aurora-band", "kind": "recipe", "cat": "G8", "family": "G", "version": "1.3.0", "order": 60,
//!  "license": "Apache-2.0",
//!  "credits": ["Mattenii, 'Aurora Lights' (https://www.shadertoy.com/view/MsjfRG): the painted band; narrow noise, steep transfer; a vertical stretch that turns folds into rays; colour bands by height; brightness that breathes along the curtain on two timescales (the technique, read in words; no code taken)",
//!   "albertelwin, 'AuroraBorealis' (https://www.shadertoy.com/view/MdBfzR): a curtain that breathes in phase along its length; and its lesson in reverse, a symmetric band that needs a sharp lower hem (the technique, read in words; no code taken)",
//!   "alro, 'AURORA' (https://www.shadertoy.com/view/ttScDc): the hem as the floor where the emission starts, nothing beneath it, a green body under a red-magenta crown, motion on rates that never line up (the technique, read in words; no code taken)",
//!   "Valdex, 'Chromatic Aurora Curtains' (https://www.shadertoy.com/view/ffG3Rc): hue separated from brightness, an analogous cyan-blue-indigo set, a faint lift of the drape's tail (the technique, read in words; no code taken)",
//!   "Orion Sky Lawlor and Jon Genetti, 'Interactive Volume Rendering Aurora on the GPU' (WSCG 2011, https://www.cs.uaf.edu/~olawlor/papers/2010/aurora/lawlor_aurora_2010.pdf): emission as footprint times altitude profile, and gamma on the colour's magnitude so summed dim emission keeps its hue",
//!   "NOAA Space Weather Prediction Center, 'Aurora: tutorial' (https://www.swpc.noaa.gov/content/aurora-tutorial): the green body, the red crown and the pink-purple lower border of an active display"],
//!  "cost": {"class": "C1", "loop": "none of its own; per curtain (up to 3): noiseTriangle2 4 octaves, three warpFbm2 (one of 1 octave, two of 3), auroraRays 2 value noises, seven envBreath (the gaps, low-passed), one hash33 (the fringe's energetic stretches), three auroraProfile, palRamp3 or auroraLineColor once", "tex": 0},
//!  "entry": "vec3 auroraBand(vec2 pixel, vec2 res, float clock, float intensity, float hemHeight, float curtainWidth, float fold, float rays, float fringe, int palette, float sky, int curtains, int view)",
//!  "params": [
//!   {"name": "intensity", "label": "Intensity", "unit": "ratio", "range": [0, 3], "default": 1.2, "step": 0.01, "group": "light", "uniform": "u_auroraBand_intensity",
//!    "help": "How much light the curtains emit. The drape's faint tail is lifted on a curve, so doubling this brightens them by about 1.7 times, never to a flat white: a hot spot's weakest channel eases toward a ceiling, the whole colour with it, so it stays coloured."},
//!   {"name": "hemHeight", "label": "Hem height", "unit": "world", "range": [0.1, 1.6], "default": 0.6, "step": 0.01, "group": "shape", "uniform": "u_auroraBand_hemHeight",
//!    "help": "Where the nearest curtain's sharp lower edge hangs at the sides of the frame, measured up from the bottom (the frame is 2 units tall). The edge arcs a little higher left of centre and sways slowly."},
//!   {"name": "curtainWidth", "label": "Curtain width", "unit": "world", "range": [0.3, 3], "default": 1, "step": 0.01, "group": "shape", "uniform": "u_auroraBand_curtainWidth",
//!    "help": "The horizontal scale of the folds and rays: larger is a nearer, broader curtain; smaller a farther, finer one."},
//!   {"name": "fold", "label": "Folds", "unit": "ratio", "range": [0, 1], "default": 0.5, "step": 0.01, "group": "shape", "uniform": "u_auroraBand_fold",
//!    "help": "How much the fabric is pushed sideways by a slow warped field: 0 hangs straight, 1 swirls. Folds seen edge-on gather light."},
//!   {"name": "rays", "label": "Rays", "unit": "ratio", "range": [0, 1], "default": 0.75, "step": 0.01, "group": "shape", "uniform": "u_auroraBand_rays",
//!    "help": "How strongly sparse bright columns run up the curtain (the field-aligned rays), darker fabric between them; a ray reaches higher than the drape around it."},
//!   {"name": "fringe", "label": "Energetic fringe", "unit": "ratio", "range": [0, 1], "default": 0, "step": 0.01, "group": "colour", "uniform": "u_auroraBand_fringe",
//!    "help": "The lower border of an active display, a thin coloured edge of its own under the curtain (as thick near as far, and up to 1 / 200 of the frame's height: at 480 x 270, 1.35 px at 1 and about 0.5 at 0.35), lit only along the curtain's energetic stretches (short pieces that come and go, about 14 per cent of its length at 0.35, 30 at 1) and giving way to any drape behind it: nitrogen purple in the physical palette, coral in the house ones. 0 is a quiet night."},
//!   {"name": "palette", "label": "Palette", "unit": "choice", "default": 1, "group": "colour", "uniform": "u_auroraBand_palette",
//!    "choices": [{"value": 0, "label": "House (ice cyan, periwinkle, violet; coral hem)"},
//!                {"value": 1, "label": "Physical (oxygen green, red crown)"},
//!                {"value": 2, "label": "Chromatic (cyan, electric blue, indigo)"}],
//!    "help": "Colour by height. Physical, the default, is the emission lines in their true order: oxygen's green body, its red crown. House is analogous with one warm accent."},
//!   {"name": "sky", "label": "Sky", "unit": "ratio", "range": [0, 1], "default": 1, "step": 0.01, "group": "light", "uniform": "u_auroraBand_sky",
//!    "help": "The house pre-dawn sky behind the curtain. 0 leaves black, for a host that composites its own backdrop."},
//!   {"name": "curtains", "label": "Curtains", "unit": "count", "range": [1, 3], "default": 2, "step": 1, "group": "shape", "uniform": "u_auroraBand_curtains", "cost": true,
//!    "help": "How many curtains hang one behind the other, each farther one higher, finer and dimmer. Each costs one more read of the fabric."},
//!   {"name": "view", "label": "View", "unit": "choice", "default": 0, "group": "debug", "uniform": "u_auroraBand_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "Fabric alone"}, {"value": 2, "label": "Colour by height"}],
//!    "help": "Debug views: the shaped filament fabric as grey, or the colour and brightness by height without the fabric or the breathing."}],
//!  "contract": "auroraBand returns scene-linear light (>= 0, finite) for the pixel: the house sky (skyGradient: a near-black zenith, a dim blue horizon at the bottom edge of the frame, a faint rose where a sun waits 3 degrees under the horizon ahead and to the right, times sky) plus, added (cmpAdd), up to three painted curtains (curtains is read 0 to 3; 0 leaves the sky). The frame is uvCentered (2 units tall); u = x / aspect runs -1 to 1 across it. A zoom gradient depth = 2^(0.55 u) makes every curtain recede to the right. Curtain k (0 the nearest) is drawn at scale depth (1 + 0.8 k) with share 1 / (1 + 1.5 k) of the light, on its own stretch of fabric; its hem hangs at -1 + hemHeight + 0.42 k + (0.08 sway + 0.06 (1 - c^2)) / (1 + 0.8 k) - 0.18 (depth - 1), sway being warpFbm2 of one octave (within 1) and c = (u + 0.25) / 1.25 (an arc cresting left of centre). Height above the hem, times the scale, maps to altitude at 300 km per unit, the hem at 106 km; the lower edge is ragged by up to 6 km along a filament crease (edge = 106 + 12 (n - 0.5)), and below it the curtain adds exactly nothing (auroraProfile is 0 at and under its edge). The fringe is its own emitter between the edge and the body: fringeTint times 1.6 smoothstep(0, 0.25, fringe) (1 - smoothstep(F / 2, F, alt - edge)) auroraProfile((alt - edge) / s, 0, 2.5 km), s being the curtain's scale and F = max(3 fringe s, 0.01) km, so it stands fringe / 200 of the frame's height at every depth, 1.35 px at 480 x 270 at fringe 1 (it stood 2.7 / s px at 480 x 270, 4 px on the near left); the tint is auroraLineColor(90, 1) (the nitrogen purple alone) for palette 1 and the house coral token #e0724f otherwise; the body begins at edge + F, so the two never light the same altitude. The body is hue times (auroraProfile(alt, edge + F, mix(35, 70, rays x ray)) + 1.5 auroraProfile(alt, edge + F, 4 km)): it fades by e every 35 km, a ray's core every 70 km, over its own thin bright lower border. Both are multiplied by the fabric and by the gap gate: smoothstep(0.1, 0.75, envBreath(0.31 along + 0.5 k)) (real gaps along the curtain, each curtain half a wave out of step) read seven times over 0.2 frame units across x and weighted 1 2 3 4 3 2 1 / 16, so a curtain's end fades from a gap to half of full over at least 8 px at 480 x 270 (read once, a fast patch crossing the threshold ended it in a wall). The fringe is further multiplied by its energetic stretches: a = 3 s x - 0.05 clock (x the frame's) cut into cells, dice d = hash33(floor(a), k, 13), each cell lit from b = 0.5 + (d.z - 0.5)(0.8 - L) - L / 2 to b + L of it, L = (0.3 + 0.4 d.y)(0.65 + 0.35 fringe), its ends smoothstepped over 0.08, and for the first 0.4 + 0.4 fringe of its own 120 s life cycle fract(d.x + clock / 120), smoothstepped in and out over 0.1 of it. They cover about 14 per cent of the curtain's length at 0.35, 30 at 1, and no piece is longer than 0.7 of a cell at any clock (a cell spans a third of a unit of s x, whatever the curtain width: about 107 px of 480 on the near curtain's left, 45 at the centre): a thin coloured edge in pieces at every clock, never along the whole of every hem. The fabric is ((0.08 + strands) times the ray gain times the gather) soft-capped by f / (1 + 0.25 f): strands are noiseTriangle2 (4 octaves, churned at 0.08 clock) on the folded address, lit by shpInvPower(n + 0.02, 0.2, 2.4) and soft-capped at 3.3; the ray gain is (1 - rays) + rays (0.08 + 2.4 ray), ray = auroraRays(2.3 folded, 0.3 clock); the address is pushed sideways by 0.55 fold warpFbm2, and gather = min(1 / |its stretch|, 2.2) brightens the fabric where a fold is seen edge-on. Hue is a separate factor: palette 1 is auroraLineColor(alt, 0) (green body, red crown); 0 and 2 are palRamp3 from the hem colour at 106 km to the crown colour at 216 km. Bodies and fringes are summed apart; the fringes' sum is multiplied by 1 - smoothstep(0, 0.05, luminance(bodies) / their peak), the peak being the sum of 1.6 luminance(fringeTint) share fabric gate stretches, so a fringe shows against the dark sky and gives way where any drape (a nearer curtain's, over a farther curtain's edge) passes a twentieth of it: near-complements summed on one pixel read as silver, then white. The sum goes through displayHueSafeGamma(intensity times sum, 1.25): the aurora's light scales exactly as intensity^0.8 and keeps its hue, until its weakest channel passes 0.2, where the whole colour is scaled so that channel eases toward 0.35 (0.2 + 0.15 tanh(min((w - 0.2) / 0.15, 10)), the argument clamped as tmTanh's is): hue and saturation kept, so with the house tail and the cards' brightest star on top no pixel's weakest channel passes 0.9 at any knob setting. clock is seconds of the host's motion clock: every rate lives inside the recipe (all slow, none commensurate), so a host that offers a drift speed integrates it into clock and never multiplies time by it (the Play rule); wrap clock below about 1e4. view 1 returns a quarter of the summed fabric as grey, with no sky; view 2 returns the sky plus (hue times the body profile plus the fringe) times intensity, with no fabric, breathing, stretches or yield. Painted on the sky: no parallax (aurora-sheets has it).",
//!  "note": "The cheapest whole aurora, a stage backdrop for the cockpit light bed, a hero strip or a thumbnail: a few field reads per curtain, no march. What makes it read as aurora and not as a lit skyline: a SHARP lower edge with nothing at all beneath it (the stars show through), brightness falling off softly upward, vertical rays and folds rising from that edge, a green body under a red crown, and slow motion on rates that never line up. It is built the way the loved bands are built: a soft noise made narrow and then carved by a steep curve (contrast is decided after the noise), stretched tall so its creases become rays, a fold field whose edge-on stretches gather light, hue chosen by height and kept apart from brightness, and a breathing along the curtain with real gaps. The hem sways as one smooth octave on a broad arc: a fractal edge reads as mountains. A farther curtain hangs higher, so its hem shows inside the nearer one's drape instead of as a second skyline under it. The energetic fringe is a thin layer under the body, never a tint over it: coral or nitrogen purple summed with ice cyan or green on the same pixels reads as silver; so it also gives way where another curtain's drape lies behind it, and it lights only the curtain's energetic stretches, the way a real lower border does: drawn along the whole of every hem it is an outline. Cut the stretches into cells along the curtain, each lit over a piece of its own that never reaches the cell's ends: a smooth noise through a threshold joins its lit runs into half the frame at most clocks, though it looks short at a few. Keep the fringe as thick on screen near as far (its layer scaled with the curtain's depth): a layer of fixed kilometres is thickest on the near left, where the curtain is drawn largest. The gaps along a curtain are low-passed across the frame, so a curtain fades out instead of ending in a wall. A hot spot is scaled down as a whole colour once its weakest channel nears white: the display curve's per-channel shoulder would otherwise bleach it. Finish with the house tail (tmSuperlinear at 0.85, then displayOut's tanh) and a static dither; the card adds a black ridge and static stars, which a host may want too. Wrong looks like rows of hills with glowing outlines (light under the hem, or the fringe along every hem), a silver or white hem (the fringe on a body's pixels), curtains ending in straight vertical walls (the gaps read once), a soft bottom with a hard top (the profile upside down), a curtain that slides as a rigid picture (the warp not turning), mud where the hem meets the fringe (colours mixed instead of separated), or a pale wash over the whole sky (black stays black).",
//!  "debug": ["fabric", "colour-by-height"],
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "aurora-band.card",
//!  "twin": "arsenal/shaders/twins/groups_aurora.py", "status": "P0",
//!  "exemplars": ["MsjfRG", "MdBfzR", "ttScDc", "ffG3Rc"],
//!  "learn": ["VA 7.1", "VA 7.2 family A", "VA 7.3", "study:MsjfRG 6.1", "study:MdBfzR", "study:ttScDc 6.2", "craft secret 3", "craft secret 20"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. A stage painter's aurora: no 3D at all, just a backdrop where every pixel asks "how high above the curtain's
// hem am I, and how much fabric is here?". The hem is the one hard edge (where the falling electrons stop), so it comes
// from the physical profile; the fabric is a narrow filament noise stretched tall; the colour is a function of height
// alone, multiplied in after the brightness, the way a colour television keys hue over a luminance signal.

// The sky plus the painted curtains, in scene-linear light. Params after `clock` are the header's knobs, in order.
vec3 auroraBand(vec2 pixel, vec2 res, float clock, float intensity, float hemHeight, float curtainWidth, float fold,
                float rays, float fringe, int palette, float sky, int curtains, int view) {
    const vec3 zenith = vec3(0.0006, 0.0009, 0.0034);        // near black: no ambient wash
    const vec3 horizonGlow = vec3(0.0016, 0.0024, 0.0068);
    const vec3 dawnRose = vec3(0.0110, 0.0052, 0.0100);       // a sun a few degrees under the horizon, ahead right
    const vec3 toSun = vec3(0.4741, -0.0569, -0.8786);
    const vec3 coral = vec3(0.7454, 0.1683, 0.0782);          // the house accent token, linear (--wb-coral, #e0724f)
    const float edgeKm = 106.0;                               // the lower edge: oxygen's green is awake there
    vec2 p = uvCentered(pixel, res);
    float u = p.x / max(res.x / res.y, 1e-3);                 // -1 at the left edge of the frame, 1 at the right
    float width = max(curtainWidth, 0.05);
    // the sky: a direction whose elevation is 0 at the bottom edge of the frame
    vec3 skyward = normalize(vec3(p.x, 1.0 + p.y, -1.6));
    vec3 backdrop = max(sky, 0.0) * skyGradient(skyward, toSun, zenith, horizonGlow, dawnRose);
    bool physical = palette == 1;
    bool chromatic = palette == 2;
    vec3 hemColour = chromatic ? vec3(0.0, 0.3801, 0.6921) : vec3(0.1873, 0.7106, 0.8689);
    vec3 bodyColour = chromatic ? vec3(0.0072, 0.1193, 1.0) : vec3(0.1960, 0.3672, 0.9331);
    vec3 crownColour = chromatic ? vec3(0.0835, 0.0272, 0.8276) : vec3(0.3424, 0.2049, 0.9331);
    // the energetic fringe: nitrogen purple for the physical palette (auroraLineColor at 90 km, where nothing else
    // glows), the house coral otherwise, in a layer at the very bottom 3 km x fringe thick at unit depth (times each
    // curtain's scale, so it stands the same height on screen near and far), lit only along the curtain's energetic
    // stretches
    const vec3 luma = vec3(0.2126, 0.7152, 0.0722);
    vec3 fringeTint = physical ? auroraLineColor(90.0, 1.0) : coral;
    float fringeAmount = clamp(fringe, 0.0, 1.0);
    float fringeOn = smoothstep(0.0, 0.25, fringeAmount);
    float fringeLuma = 1.6 * dot(fringeTint, luma);
    float stretchSize = 0.65 + 0.35 * fringeAmount;           // a stretch's length, cells, over 0.3 + 0.4 dice
    float stretchShare = 0.4 + 0.4 * fringeAmount;            // the share of its life cycle a cell is lit
    float rayMix = clamp(rays, 0.0, 1.0);
    // cheap depth: a zoom gradient across the frame, so a curtain recedes to the right (finer, shorter, lower)
    float depth = exp2(0.55 * u);
    float push = 0.55 * fold;
    vec3 bodyLight = vec3(0.0);
    vec3 fringeLight = vec3(0.0);
    float fringePeak = 0.0;
    float fabricSum = 0.0;
    for (int curtain = 0; curtain < 3; ++curtain) {
        if (curtain >= curtains) {
            break;
        }
        // each curtain behind the first hangs higher, finer, shorter and dimmer, on its own stretch of fabric
        float k = float(curtain);
        float scale = depth * (1.0 + 0.8 * k);
        float share = 1.0 / (1.0 + 1.5 * k);
        float along = p.x * scale / width + 17.3 * k;
        // where the hem hangs: a broad arc cresting left of centre, swaying slowly like fabric on a line. One smooth
        // octave: a skyline is fractal and reads as hills; a hem is not
        float sway = warpFbm2(vec2(0.7 * along + 0.013 * clock, 0.021 * clock + 1.7), 0.9, 1, 7u);
        float crest = (u + 0.25) / 1.25;
        float hem = -1.0 + hemHeight + 0.42 * k + 0.08 * sway / (1.0 + 0.8 * k) - 0.18 * (depth - 1.0)
                    + 0.06 * (1.0 - crest * crest) / (1.0 + 0.8 * k);
        float above = (p.y - hem) * scale;
        // the folds: the fabric's address pushed sideways by a slow warped field; where the push runs against the
        // curtain the fabric is seen edge-on and gathers light (one over the stretch, read 0.03 along)
        vec2 foldAt = vec2(0.9 * along - 0.017 * clock, 0.35 * above + 0.011 * clock + 3.7);
        float bend = warpFbm2(foldAt, 1.1, 3, 19u);
        float stretch = 1.0 + push * (warpFbm2(foldAt + vec2(0.027, 0.0), 1.1, 3, 19u) - bend) / 0.03;
        float gather = min(1.0 / max(abs(stretch), 1e-3), 2.2);
        float folded = along + push * bend;
        // the fabric: filament noise stretched tall, its creases lit by a steep curve and soft-capped so crossings
        // hold, over a faint drape; rays as sparse columns up the whole height, with darker fabric between them
        float n = noiseTriangle2(vec2(2.2 * folded, 0.8 * above), 0.08 * clock, 4);
        float strands = shpInvPower(n + 0.02, 0.2, 2.4);
        strands = strands / (1.0 + 0.3 * strands);
        float ray = auroraRays(2.3 * folded, 0.3 * clock, 3u);              // rays drift slowly along the curtain
        float rayGain = (1.0 - rayMix) + rayMix * (0.08 + 2.4 * ray);
        float fabric = (0.08 + strands) * rayGain * gather;
        fabric = fabric / (1.0 + 0.25 * fabric);                   // where a crease, a ray and a fold meet: no hot spot
        fabricSum += share * fabric;
        // height: the lower edge ragged by up to 6 km along the creases, and NOTHING below it (auroraProfile is 0 at
        // and under its edge). The energetic fringe is a thin emitter of its own between the edge and the body, which
        // begins where the fringe ends: never a tint over the body (near-complements summed on one pixel read as
        // silver). The body fades by e every 35 km, a ray's core every 70 km (rays outreach the drape), plus the
        // lower border's own thin bright layer, one-sided like the rest
        float alt = edgeKm + 300.0 * above;
        float edge = edgeKm + 12.0 * (n - 0.5);
        float fringeKm = max(3.0 * fringeAmount * scale, 0.01);   // fringe / 200 of the frame's height at any depth
        float start = edge + fringeKm;
        float profile = auroraProfile(alt, start, mix(35.0, 70.0, rayMix * ray))
                        + 1.5 * auroraProfile(alt, start, 4.0);
        float low = 1.6 * fringeOn * (1.0 - smoothstep(0.5 * fringeKm, fringeKm, alt - edge))
                    * auroraProfile((alt - edge) / scale, 0.0, 2.5);
        // hue by height, kept apart from brightness
        vec3 hue;
        if (physical) {
            hue = auroraLineColor(alt, 0.0);
        } else {
            hue = palRamp3((alt - edgeKm) / 110.0, hemColour, bodyColour, crownColour);
        }
        if (view == 2) {
            bodyLight += share * hue * profile;
            fringeLight += share * fringeTint * low;
            continue;
        }
        // breathing along the curtain: a slow body with faster, brighter patches, and real gaps between them, each
        // curtain half a wave out of step with the one before. Low-passed along the frame (seven reads over 0.2 frame
        // units, weighted 1 2 3 4 3 2 1): read once, a fast patch crossing the threshold ends a curtain in a wall
        float breathAt = 0.31 * along + 0.5 * k;
        float breathPerUnit = 0.31 * scale / width;
        float gate = 0.0;
        for (int tap = 0; tap < 7; ++tap) {
            float offset = (float(tap) / 6.0 - 0.5) * 0.2;
            gate += (4.0 - abs(float(tap) - 3.0))
                    * smoothstep(0.1, 0.75, envBreath(breathAt + breathPerUnit * offset, clock, vec2(0.017, 0.053)));
        }
        gate /= 16.0;
        // the fringe lights only the curtain's energetic stretches: cells along it, three per unit of frame x times the
        // scale (a fixed length on screen at this depth, whatever the curtain's width), each lit over one stretch of
        // its own that never reaches the cell's ends and on its own slow life cycle, the whole drifting slowly along.
        // No piece outgrows its cell: a noise through a threshold joined its lit runs into most of the frame, and
        // drawn along the whole of every hem the fringe reads as a glowing outline
        float stretchAt = 3.0 * p.x * scale - 0.05 * clock;
        float stretchCell = floor(stretchAt);
        vec3 dice = hash33(vec3(stretchCell, k, 13.0));
        float stretchLength = (0.3 + 0.4 * dice.y) * stretchSize;
        float stretchStart = 0.5 + (dice.z - 0.5) * (0.8 - stretchLength) - 0.5 * stretchLength;
        float inCell = stretchAt - stretchCell;
        float life = fract(dice.x + clock / 120.0);
        float energetic = smoothstep(stretchStart, stretchStart + 0.08, inCell)
                          * (1.0 - smoothstep(stretchStart + stretchLength - 0.08, stretchStart + stretchLength, inCell))
                          * smoothstep(0.0, 0.1, life) * (1.0 - smoothstep(stretchShare - 0.1, stretchShare, life));
        bodyLight += share * hue * (profile * fabric * gate);
        float energy = share * fabric * gate * energetic;
        fringeLight += fringeTint * (energy * low);
        fringePeak += fringeLuma * energy;
    }
    if (view == 1) {
        return vec3(0.25 * fabricSum);
    }
    // the fringe shows against the dark sky and gives way where any drape (a nearer curtain's, crossing a farther
    // curtain's edge) passes a twentieth of its own peak: coral or purple summed with cyan or green reads as silver
    if (view != 2) {
        fringeLight *= 1.0 - smoothstep(0.0, 0.05, dot(bodyLight, luma) / max(fringePeak, 1e-9));
    }
    // the glow lift: faint drape raised, hot cores eased, hue untouched; the curtains add, never mix (optically thin)
    vec3 glow = displayHueSafeGamma(max(intensity, 0.0) * (bodyLight + fringeLight), 1.25);
    // the ceiling under white: past 0.2 the weakest channel eases toward 0.35 on a tanh shoulder, the whole colour
    // scaled with it, so a hot spot stays coloured through the display curve
    float weakest = min(glow.r, min(glow.g, glow.b));
    if (weakest > 0.2) {                                      // tanh's argument clamped, as tmTanh does (tone.glsl)
        glow *= (0.2 + 0.15 * tanh(min((weakest - 0.2) / 0.15, 10.0))) / weakest;
    }
    return cmpAdd(backdrop, glow);
}
