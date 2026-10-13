//! {"name": "neon-line", "kind": "recipe", "cat": "F9", "family": "F", "version": "1.0.0", "order": 60,
//!  "license": "Apache-2.0",
//!  "credits": ["Emil Persson, 'Graphics Gems for Games', phone-wire AA (https://www.humus.name/Articles/Persson_GraphicsGemsForGames.pdf): a line never drawn thinner than a pixel, dimmed by its true width instead",
//!   "Hendrik Antoon Lorentz and the Cauchy distribution (https://en.wikipedia.org/wiki/Cauchy_distribution): the needle core with long tails that sum into bloom",
//!   "Discoteq 2 study (https://www.shadertoy.com/view/DtXfDr, supah): detuned pinned strings, and a blur that grows toward the edges as a free depth cue (the technique, read in words; no code taken)",
//!   "Oscillo Donut study (https://www.shadertoy.com/view/ldSfWV): a Lorentzian beam whose tails become the glow (read in words)",
//!   "HAL 4000 study (https://www.shadertoy.com/view/MtXczn, Manwe): max, not add, keeps crossing lines crisp (read in words)",
//!   "Starship study (https://www.shadertoy.com/view/l3cfW4, Xor): a hot core whitens while the tail keeps its colour (read in words)"],
//!  "cost": {"class": "C1", "loop": "none inside the recipe (C0 per line); a host that samples a curve pays one neonPathStep per segment it visits, and one neonLine per curve", "tex": 0},
//!  "entry": "vec3 neonLine(vec3 acc, float d, float px, vec3 tint, float energy, float depth, float widthPx, float haloPx, int profile, float coreHeat, int combine, float defocus, int view)",
//!  "params": [
//!   {"name": "widthPx", "label": "Core width", "unit": "px", "range": [0.5, 8], "default": 1.6, "step": 0.1, "group": "line",
//!    "uniform": "u_neonLine_widthPx", "help": "The hot core's width in screen pixels, the same at every distance and zoom. Below one pixel the line stays one pixel wide and dims instead of breaking up."},
//!   {"name": "haloPx", "label": "Halo", "unit": "px", "range": [0, 64], "default": 14, "step": 0.5, "group": "line",
//!    "uniform": "u_neonLine_haloPx", "help": "How far the glow reaches, in screen pixels. 0 is a bare wire."},
//!   {"name": "profile", "label": "Halo shape", "unit": "choice", "group": "line", "default": 0, "uniform": "u_neonLine_profile",
//!    "choices": [{"value": 0, "label": "Two Gaussians (the house light line)"}, {"value": 1, "label": "Lorentzian (needle core, long tails)"},
//!                {"value": 2, "label": "Inverse power (hot hairline)"}, {"value": 3, "label": "Wire only (no halo)"}],
//!    "help": "How the glow falls away. The Lorentzian's long tails pile up into bloom where many lines meet; the inverse power is a sharp hairline with a soft skirt."},
//!   {"name": "coreHeat", "label": "Core heat", "unit": "ratio", "range": [0, 4], "default": 1.6, "step": 0.05, "group": "light",
//!    "uniform": "u_neonLine_coreHeat", "help": "How far a bright core whitens, like a filament: 0 keeps the core the line's own colour. Heat scales with each line's energy, so a soft note keeps its colour and a hard one runs white-hot."},
//!   {"name": "combine", "label": "Crossings", "unit": "choice", "group": "light", "default": 0, "uniform": "u_neonLine_combine",
//!    "choices": [{"value": 0, "label": "Max (crisp, never white)"}, {"value": 1, "label": "Add (light on light)"}],
//!    "help": "What happens where lines cross. Max keeps a crossing as bright as one line, so a tangle never blooms to white; Add sums the light, as overlapping emitters really do."},
//!   {"name": "defocus", "label": "Defocus with depth", "unit": "ratio", "range": [0, 1], "default": 0.35, "step": 0.01, "group": "depth",
//!    "uniform": "u_neonLine_defocus", "help": "How much a line spreads where the host says it is deep (far, or out toward the edges): up to four times wider at 1, with the same total light, so depth reads without anything getting brighter."},
//!   {"name": "view", "label": "Debug view", "unit": "choice", "group": "debug", "default": 0, "uniform": "u_neonLine_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "Core coverage alone"}, {"value": 2, "label": "Halo alone"}],
//!    "help": "Core coverage shows the antialiased pen in white (its width should not change with the canvas); Halo shows the glow without the core."}],
//!  "contract": "neonLine(acc, d, px, tint, energy, depth, ...) adds one line's light to acc and returns it, in linear HDR (tonemap after). d is the distance to the line in the caller's units (sd2Segment, the nearest of a polyline's segments from neonPathStep, or any exact 2D distance) and px one pixel in the same units; every width is in pixels, so the line keeps its screen width at any scale. The light is energy * (core colour * core + tint * 0.55 * halo), where core = aaWire(|d|, widthPx * b, px) / b and halo = neonProfile(|d| / px, haloPx * b, profile) / b, with b = 1 + 3 defocus depth (defocus and depth clamped to [0, 1]): defocus widens a line up to four times and keeps its total light. The core colour is glowHotCore(tint, h) / h with h = coreHeat * energy (the tint itself when h is 0): its brightest channel is always the tint's, and the others climb toward it as h passes 1; the halo keeps the tint exactly. combine 0 takes the per-channel max with acc, 1 adds. neonProfile(dPx, haloPx, profile) is 1 at the line and falls with x = dPx / haloPx: profile 0 is (e^(-24 x^2) + 0.18 e^(-3 x^2)) / 1.18, 1 is (1/16) / (1/16 + x^2), 2 is (0.35 / (x + 0.35))^2, 3 (and haloPx <= 0) is no halo; any other value is profile 0. neonPathStep(p, a, b, s, best) keeps the nearer of best.x and the distance from p to the segment a..b, with the curve parameter at the nearest point (s.x at a to s.y at b) in .y. view 1 returns the core coverage in white, view 2 the halo alone. Everything is finite and non-negative for finite input.",
//!  "note": "The group with the most copies in the house: the piano trails, every study's strip and its core-plus-halo profile (seven copies with different constants), the activity line. Draw a curve by sampling it into segments with neonPathStep and shading the nearest ONCE (shading each segment and adding beads the joints); give each line its own energy (velocity) and depth (distance, or how far toward the frame's edge it runs, Discoteq's free depth cue). Keep tints analogous and let heat do the whitening: a coral line among cool ones is the accent. Max is the default because the house never lets crossings bloom to white; Add is for sparse emitters behind a density guard. Wrong looks like lines that thicken on a bigger canvas (a width in scene units, not pixels), hairlines that break into dashes (a step instead of the wire), cores that go white at every energy (heat not scaled by energy), halos that change hue (the halo whitened too), or bright beads at polyline joints (segments shaded and added one by one).",
//!  "debug": ["core", "halo"],
//!  "targets": {"glsl": "300es", "needs": []}, "card": "neon-line.card",
//!  "twin": "arsenal/shaders/twins/neon_line.py", "status": "P0",
//!  "exemplars": ["DtXfDr", "ldSfWV", "MtXczn", "XsjXRm", "l3cfW4", "7d2fDW"],
//!  "learn": ["atlas 16.4", "craft secret 6", "craft secret 7", "craft secret 21", "study:DtXfDr 4.3", "study:ldSfWV 5.3", "study:MtXczn 5.2", "study:l3cfW4 5.7"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. A neon tube is a hot thread inside a glow: the eye reads the thread's sharpness as "thin" and the glow's spread
// as "bright". So the two are drawn by different rules. The thread is a pen of fixed screen width (an antialiased
// wire), the glow a falloff measured in pixels, and only the thread runs white-hot. Like a guitar amplifier's clean
// channel and its reverb: the note stays crisp while the room around it fills.

// The halo's shape: 1 at the line, falling with the distance measured in halo widths.
float neonProfile(float dPx, float haloPx, int profile) {
    if (haloPx <= 0.0 || profile == 3) {
        return 0.0;                                          // a bare wire
    }
    float x = max(dPx, 0.0) / haloPx;
    if (profile == 1) {
        return glowLorentz(x, 0.0625);                       // half height at a quarter of the halo
    }
    if (profile == 2) {
        return shpInvPower(x + 0.35, 0.35, 2.0);             // (0.35 / (x + 0.35))^2, exactly 1 at the line
    }
    return glowTwoGauss(x, vec4(24.0, 1.0, 3.0, 0.18)) / 1.18;   // the house light line, normalised to 1
}

// One segment of a sampled curve: the nearer of what was found so far and this segment, with the curve parameter at
// the nearest point (s.x at a, s.y at b), so a host can fade the ends, colour along the path or brighten a head.
vec2 neonPathStep(vec2 p, vec2 a, vec2 b, vec2 s, vec2 best) {
    vec2 here = sd2Segment(p, a, b);
    return here.x < best.x ? vec2(here.x, mix(s.x, s.y, here.y)) : best;
}

// One line's light, combined into acc by max (crisp crossings) or add (light on light).
vec3 neonLine(vec3 acc, float d, float px, vec3 tint, float energy, float depth, float widthPx, float haloPx,
              int profile, float coreHeat, int combine, float defocus, int view) {
    float pixel = max(px, 1e-6);
    float spread = 1.0 + 3.0 * clamp(defocus, 0.0, 1.0) * clamp(depth, 0.0, 1.0);   // wider, by the same light
    float across = abs(d);
    float core = aaWire(across, max(widthPx, 0.0) * spread, pixel) / spread;
    float halo = neonProfile(across / pixel, max(haloPx, 0.0) * spread, profile) / spread;
    vec3 hue = max(tint, vec3(0.0));
    float power = max(energy, 0.0);
    float heat = max(coreHeat, 0.0) * power;               // a hard note runs hotter than a soft one
    vec3 coreColour = heat > 1e-4 ? glowHotCore(hue, heat) / heat : hue;
    vec3 light;
    if (view == 1) {
        light = vec3(core);
    } else if (view == 2) {
        light = hue * (0.55 * power * halo);
    } else {
        light = power * (coreColour * core + hue * (0.55 * halo));
    }
    return combine == 1 ? cmpAdd(acc, light) : cmpMax(acc, light);
}
