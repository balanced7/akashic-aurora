//! {"name": "glow-xray", "kind": "recipe", "cat": "F9", "family": "F", "version": "1.0.0", "order": 60,
//!  "license": "Apache-2.0",
//!  "credits": ["tdhooper, 'Bubble rings' (https://www.shadertoy.com/view/WdB3Dw): never stop at the surface; the step budget is the opacity; hue indexed by ray length separates the transparent layers; a narrow spark on the walls against a wide wash where the ray lingers (the technique, read in words; no code taken)",
//!   "XT95 (Anatole Duprat), 'Flame' (https://www.shadertoy.com/view/MdX3zr): brightness from how long the ray loitered (the technique, read in words; no code taken)",
//!   "glkt, 'Alien Core' (https://www.shadertoy.com/view/4tcXRr): the glow is the step count (the technique, read in words; no code taken)",
//!   "Xor, the GM Shaders volumetric tutorial (https://mini.gmshaders.com/): the pass-through march and its per-step glow",
//!   "Inigo Quilez, 'Palettes' (https://iquilezles.org/articles/palettes/): the cosine palette that colours by depth"],
//!  "cost": {"class": "C2", "loop": "budget <= 160 steps, one mapScene call each, plus one for the start (or one for the field-slice view)", "tex": 0, "hooks": 1},
//!  "hooks": ["float mapScene(vec3 p)"],
//!  "entry": "vec3 glowXray(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, int budget, float passthrough, float density, float sparkWidth, int palette, float hueSpeed, float rim, int view)",
//!  "params": [
//!   {"name": "budget", "label": "Budget", "unit": "count", "range": [16, 160], "default": 96, "step": 1, "group": "quality", "uniform": "u_glowXray_budget", "cost": true,
//!    "help": "Steps per ray, and so the opacity: a short budget stops rays after a few walls (fogged glass), a long one shows the back of the scene. Cost is linear in it."},
//!   {"name": "passthrough", "label": "Passthrough", "unit": "world", "range": [0.002, 0.1], "default": 0.012, "step": 0.001, "group": "march", "uniform": "u_glowXray_passthrough",
//!    "help": "The smallest step, taken while crossing a wall. Smaller resolves thinner sparks and spends more of the budget per wall."},
//!   {"name": "density", "label": "Linger", "unit": "ratio", "range": [1, 8], "default": 3, "step": 0.1, "group": "march", "uniform": "u_glowXray_density",
//!    "help": "How much the march slows as it nears a surface (the distance is divided by this). Higher lingers longer, gathering more light near walls."},
//!   {"name": "sparkWidth", "label": "Spark width", "unit": "world", "range": [0.004, 0.2], "default": 0.015, "step": 0.001, "group": "light", "uniform": "u_glowXray_sparkWidth",
//!    "help": "The thickness of the glowing skin on every surface. Each crossing of a wall adds the same light whatever the width (about a sixth of a unit, head on)."},
//!   {"name": "palette", "label": "Palette", "unit": "choice", "default": 0, "group": "colour", "uniform": "u_glowXray_palette",
//!    "choices": [{"value": 0, "label": "House (periwinkle, violet, a rose turn; coral wash)"}, {"value": 1, "label": "Ember (red, orange, gold)"},
//!                {"value": 2, "label": "Ice (aqua to blue)"}],
//!    "help": "The cosine palette the depth runs through, and the wash's colour."},
//!   {"name": "hueSpeed", "label": "Depth hue", "unit": "turns", "range": [0, 2], "default": 0.35, "step": 0.01, "group": "colour", "uniform": "u_glowXray_hueSpeed",
//!    "help": "Palette turns per world unit of ray length: front and back walls take different colours, like chromatic depth glasses. 0 is one colour."},
//!   {"name": "rim", "label": "Wash", "unit": "ratio", "range": [0, 1], "default": 0.35, "step": 0.01, "group": "light", "uniform": "u_glowXray_rim",
//!    "help": "A wide wash from how long each ray loitered near surfaces: silhouettes and folds light themselves, with no normals."},
//!   {"name": "view", "label": "View", "unit": "choice", "default": 0, "group": "debug", "uniform": "u_glowXray_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "Steps heat"}, {"value": 2, "label": "Field slice"}],
//!    "help": "Debug views (atlas 16.6): how much of the budget each ray spent, or the distance field on the plane through the origin facing the camera."}],
//!  "contract": "glowXray returns scene-linear light (>= 0, finite) for the camera ray rd = camRay(pixel, res, basis, focal) through the host's mapScene, a pass-through march that never stops at a surface. The scene must lie within 6 units of the origin: a ray stops once t passes length(ro) + 6, or after min(budget, 160) steps. It starts rmJitterStart(0, first step, dthIgn(pixel)) in, the first step being rmPassStep(mapScene(ro), passthrough, density): a static fraction of a step, which survives to every wall because the steps shrink with the distance, so walls never band and the grain never crawls. Each step is rmPassStep(d, passthrough, density) = max(passthrough + |d| / density, 1e-4) and adds palCosLinear(hueSpeed (t - length(ro)), palette) times glowEmitStep(exp(-|d| / sparkWidth), step, 0.08 / sparkWidth): a sum over steps of the skin's integral, so a head-on crossing of a thin wall adds about 0.16 times the colour whatever sparkWidth, and halving the steps changes the light by under 12 per cent (measured). Depth 0 (the origin's distance) is the palette's centre. Every step within 4 sparkWidth of a surface counts as loitering; the wash adds rim times glowStepCount(loitering steps, budget, 1.5) times the palette's wash colour (coral for House, deep red for Ember, blue for Ice). With rim 0, more budget never dims a pixel. view 1 returns dbgHeatCount(steps taken, budget); view 2 returns dbgSlice of mapScene on the plane through the origin that faces the camera (a line every 0.25), one mapScene call and no march. The host's scene is the hook float mapScene(vec3 p); a field that over-reports moves where the steps fall but never stops the march.",
//!  "note": "X-ray glass, flame and sinew: light that comes from the march itself, not from lights, for avatar states, bench sketches and cockpit accents. Every step adds the glow of how close it passed, so walls light themselves, walls seen edge-on most of all (a rim with no normals); hue by depth separates the transparent layers like chromatic depth glasses; and the step budget is the opacity: rays that cross many walls run out before the back of the scene, which reads as fogged glass. Keep the scene within a few units of the origin and let thin shells and tubes do the drawing (opOnion, thin tori): a solid body glows as a blob. The palette's centre sits at the origin's depth, so the House palette stays cool (periwinkle and violet) around the scene, with rose only far in front or behind, and the coral wash marks where rays loitered. Finish with displayOut's tanh. Wrong looks like rings across a shell (a start jitter that does not scale with the step), a white blob (the spark too wide for the shells, or the gain doubled), glow that changes when passthrough changes (1/d per step where the integral was meant), or a hard cut where the glow ends (the scene reaching past 6 units from the origin).",
//!  "debug": ["steps", "field-slice"],
//!  "targets": {"glsl": "300es", "needs": []}, "card": "glow-xray.card",
//!  "twin": "arsenal/shaders/twins/groups_glow.py", "status": "P0",
//!  "exemplars": ["WdB3Dw", "MdX3zr", "4tcXRr"],
//!  "learn": ["LM 12.2", "study:WdB3Dw 5.8", "study:WdB3Dw 5.12", "study:MdX3zr 6.1", "craft secret 2"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. An ordinary marcher stops at the first surface and asks a light how bright it is. This one never stops: it
// slows as it nears a wall, crosses it, and speeds up on the other side, and every step adds the glow of how close it
// passed. No lights, no normals. Like a Geiger counter riding the ray: it clicks most where the ray lingers, near walls
// and above all along walls seen edge-on, and it runs out of film after `budget` clicks, which is what makes the far
// walls fade (the budget is the opacity).

// The scene the host defines as mapScene, seen as x-ray glass, in scene-linear light. Params after `focal` are the
// header's knobs, in order.
vec3 glowXray(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, int budget, float passthrough, float density,
              float sparkWidth, int palette, float hueSpeed, float rim, int view) {
    vec3 rd = camRay(pixel, res, basis, focal);
    if (view == 2) {
        // the field on the plane through the origin that faces the camera (dbgSlice reads its own derivatives, so
        // every pixel evaluates it, never inside a branch)
        float onPlane = max(ixPlane(ro, rd, basis[2], 0.0), 0.0);
        return dbgSlice(mapScene(ro + rd * onPlane), 0.25);
    }
    // the cosine palette (display coefficients, decoded to light by palCosLinear) and the wash colour, by choice
    vec3 pa = vec3(0.55, 0.45, 0.85);
    vec3 pb = vec3(0.40, 0.30, 0.15);
    vec3 pc = vec3(0.7);
    vec3 pd = vec3(0.497, 0.617, 0.917);                     // depth 0 (the origin's distance) is periwinkle
    vec3 washColour = vec3(0.9331, 0.2330, 0.1473);           // coral, the house accent
    if (palette == 1) {
        pa = vec3(0.55, 0.25, 0.10);
        pb = vec3(0.45, 0.25, 0.10);
        pc = vec3(1.0);
        pd = vec3(0.0, 0.08, 0.18);
        washColour = vec3(0.60, 0.06, 0.02);
    } else if (palette == 2) {
        pa = vec3(0.25, 0.60, 0.85);
        pb = vec3(0.25, 0.30, 0.15);
        pc = vec3(1.0);
        pd = vec3(0.55, 0.50, 0.45);
        washColour = vec3(0.10, 0.25, 0.90);
    }
    int steps = clamp(budget, 1, 160);
    float width = max(sparkWidth, 1e-4);
    float centre = length(ro);                                 // depth is measured from the origin's distance
    float far = centre + 6.0;                                  // the scene lives within 6 units of the origin
    // start a static fraction of the FIRST step in: steps shrink in proportion to the distance as the ray nears a
    // wall, so that fraction survives to every wall (a fixed offset would shrink to nothing and leave rings)
    float t = rmJitterStart(0.0, rmPassStep(mapScene(ro), passthrough, density), dthIgn(pixel));
    vec3 spark = vec3(0.0);
    float loiter = 0.0;
    float used = 0.0;
    for (int click = 0; click < 160; ++click) {
        if (click >= steps || t > far) {
            break;
        }
        float d = mapScene(ro + rd * t);
        float stride = rmPassStep(d, passthrough, density);
        // a thin glowing skin on every surface, integrated over the step (so the step size does not set the light),
        // coloured by how far in front of or behind the origin it lies
        float skin = exp(-abs(d) / width);
        spark += palCosLinear(hueSpeed * (t - centre), pa, pb, pc, pd) * glowEmitStep(skin, stride, 0.08 / width);
        loiter += abs(d) < 4.0 * width ? 1.0 : 0.0;
        used += 1.0;
        t += stride;
    }
    if (view == 1) {
        return dbgHeatCount(used, float(steps));
    }
    // the wash: how much of the budget the ray spent near surfaces, as a soft light of its own colour
    vec3 wash = max(rim, 0.0) * glowStepCount(loiter, float(steps), 1.5) * washColour;
    return spark + wash;
}
