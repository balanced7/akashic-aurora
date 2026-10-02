---
akashic_id: art_20260902_craft-study-saffron-shader-excavation-av_06fbfb
akashic_sha: b0ce799438cb
schema_version: 1
status: current
type: design
date: 2026-09-02
title: craft-study-saffron-shader-excavation-avatar-plan
gist: "# Craft study III: Saffron's shader excavated — and the avatar's polish arc - **Date:** 2026-09-02 (late, Vandor seat) - **Purpose:** Operat"
visibility: fleet
body_type: markdown
seats: []
category: [agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-02T23:45:20"
updated: "2026-09-02T23:45:20"
---
<!-- GENERATED PROJECTION of art_20260902_craft-study-saffron-shader-excavation-av_06fbfb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# craft-study-saffron-shader-excavation-avatar-plan

# Craft study III: Saffron's shader excavated — and the avatar's polish arc

- **Date:** 2026-09-02 (late, Vandor seat)
- **Purpose:** Operator asked for (1) the hero's mouse-over behavior, (2) the WebGL behind "that cool RGB look," (3) how this feeds fixing our AI avatar's appearance — deferred until now because infrastructure ate every cycle. This study answers all three at the construction level: the analysis is from their shipped bundle (shader source recovered from the Nuxt chunks), not from pixels.
- **Companions:** the settled DOM study (`ad853e`) and craft study II (`763748`, The Watch + motion layer).
- **Ethics line:** techniques transfer; code, copy, brand, assets do not. Shader *architecture* documented here is for reimplementation in our own idiom, never copy-paste.

---

## Part 1 — The construction, excavated

**Stack confirmed from the bundle:** Nuxt + **Three.js** (full PMREM/WebGLProgram machinery in the 1.1MB main chunk) + **Lenis** smooth scroll + **GSAP/ScrollTrigger** choreography + DatoCMS content. Five canvases: one full-viewport WebGL2 (the thread hero), three small 2D `js-slide-fade` canvases, one full-page 2D grain overlay (`pointer-events-none`).

**The bloom scrub is not video and not WebGL.** The crocus is a **JPEG frame sequence** (`flower/frame_0001.jpg` → ~40+ frames) scrubbed by scroll onto a canvas — the classic Apple AirPods-page technique. Museum captions swap at scrub thresholds. This is the single most re-priceable finding for us (see Part 3).

**The hero chunk (`D2lS0hw6.js`, 340KB) carries the thread.** Recovered shader architecture:

### The thread's geometry (vertex stage)
- The strand is **instanced segments along a path**, each instance carrying an `aProgress` attribute (0→1 along the thread).
- Mouse sway: `np.x += uMouse.x * 0.07 * pow(aProgress, 2.0)` (and `.y * 0.04`). The **tip sways quadratically more than the root** — the thread bends like a frond, planted at its origin, alive at its end. Displacement is tiny (0.04–0.07 world units): felt, not seen.

### The "RGB look" (fragment stage) — the actual recipe
1. **The body is a painted texture** (`uTxt`) with a **pre-blurred twin** (`uTxtBlur`); they're mixed by `smoothstep(0.45, 0.0, vProgress)` — soft/glowy near the root, sharp at the tip. Depth-of-field along the strand for the price of one extra texture, zero postprocess.
2. **The spectrum lives in SCREEN SPACE, not on the object.** Two ramps: `d1` horizontal and `d2` vertical smoothsteps over `vScreenPos`, each **shifted by the mouse** (`uMouse * vec2(0.3, 0.6)`). Then `mixFactor = sin(d1 * π)` turns each ramp into a hue *wave* peaking mid-screen. Color = `mix(uColorA, uColorB, mixFactor)` and `mix(uColorB, uColorC, mixFactor2)` — a **three-stop gradient field the thread swims through**. Wherever the strand crosses the screen it picks up the local hue — and **moving the mouse slides the whole spectral field**, so hue itself is cursor-coupled. This is why it feels alive: the cursor doesn't move a highlight; it moves the weather.
3. **Overlay-blend + overdrive into tonemapping**: `blendOverlay(final.rgb, color)`, then `*= (1.0 + color)`, a second overlay at 0.45 opacity, then `*= 3.0` — deliberately overdriven, then Three's `tonemapping_fragment` (filmic/ACES) compresses it into that saturated luminous glow. **The "bloom" is tonemapped overexposure, not a bloom pass.**
4. **Blue-noise dither** (`uBlueNoiseTxt`, sampled at `gl_FragCoord * 0.005`, `nf = 1.0 - noise * 0.7`) — kills banding on dark gradients and adds filmic texture. This is why their blacks look expensive.
5. **Draw-on/draw-off by progress**: `enter = smoothstep(0.0, 0.1, vProgress)` (rgb) with a tighter alpha ramp — the strand *grows in* with a soft leading edge; exit mirrors it. Materialization as shader, not opacity tween.
6. Scene plumbing: explicit `renderOrder` (hallway −10 / default 0 / hero +10) and **stencil ids for coin/emblem/hallway** — layered composition, one scene.

### The hover grammar elsewhere on page 1
- CSS is nearly silent: essentially one rule — **`hover:text-gold`** (nav/links ignite to saffron `rgb(255,188,9)`).
- Everything else physical (thread sway, spectral slide) is JS→uniform. Buttons are pills at inverted contrast (bone bg / black text) with standard transitions. The lesson: **one accent-ignition rule for text + one physics response on the identity element** beats a dozen bespoke hover effects.

---

## Part 2 — Our avatar: what it is, what it lacks

**`scripts/agent-avatar.js`** — the geodesic agent avatar: small WebGL2 canvas (~64px, half-res, low-power, 48-step cap, FPS watchdog, MAX_LIVE=6, TDR-safe by design for this machine's documented AMD history). A subdivided icosahedron of hex tiles whose motion/density/color are driven by **diagnosed agent state** (`composing|tool|idle|wedged|throttled|dead|unsensed`) + `setRate(0..1)`. Uniform surface already rich: `u_sub, u_gap, u_spin, u_pulse, u_sat, u_tint, u_dim, u_wire, u_id0/u_id1` (identity gradient — WHO), `u_round, u_star, u_see, u_thick, u_cube, u_hole` (sphere→cube→torus morphs). The state machine is the product; the *look* never got its craft pass.

**⚠️ LICENSE GATE (must clear before any public-site use):** the geodesic core is adapted from Shadertoy `llVXRd` (Matt Zucker tiling + knighty mirroring), **CC-BY-NC-SA**. Console-internal use is one thing; akashiclabs.io is public and the repo is Apache-2.0 — NC (non-commercial) is arguable for a portfolio, SA (share-alike) is viral against Apache. The house has already once purged third-party IP from git history on principle. **Options:** (a) keep llVXRd-derived code console-only, build the site avatar clean-room; (b) reimplement geodesic tiling from first principles / permissively-licensed sources and carry proper attribution docs; (c) operator gets/negotiates alternate basis. Decision belongs to Daniil; default recommendation = (b), it's a well-understood construction.

### The five transfers (Saffron → avatar), all TDR-safe
1. **Screen/local-space spectral field, cursor-shifted.** Drive the identity gradient (`u_id0→u_id1`) not as a static ramp but as a **field the avatar sits in**, with a `u_mouse` shift term. The avatar visibly *notices* the visitor's cursor — attention rendered as hue weather. For an entity whose whole job is attention, this is the correct metaphor.
2. **Blue-noise dither everywhere dark.** One 64px blue-noise texture shared by avatar + site hero + any dark gradient. Kills the banding that currently cheapens dark WebGL work. Trivial cost.
3. **Texture + pre-blurred twin for the halo.** The avatar's glow/coma via a blurred sprite pass composited in-shader — no postprocess bloom pass, no extra render targets (TDR-safe glow).
4. **Overdrive → tonemap.** Push emissive through 2–3× overdrive into a filmic tonemap curve inside the fragment shader. "Lit from within" instead of "tinted."
5. **Enter/exit as progress ceremony.** Boot = draw-in (tiles assemble, tight alpha lead), death/stop = draw-out. State transitions get *ceremony* via the existing state machine — `wedged` could glitch the field, `dead` desaturates and freezes (u_sat already exists for this).

### Where the avatar lives (fold targets)
- **Console:** presence indicators per seat (already the design intent — "the signature codebook rendered as an object").
- **Site:** the **residents cast page** (A4 mine item `residents-cast-page`) — each resident as their geodesic signature with their identity gradient: Vandor amber, Heimdall periwinkle, Navi her hue, Sunshine, Rill. The cast page becomes the avatar's public debut, downstream of the license gate.
- **Shaders playground** (A4 mine item) — the avatar's uniform surface exposed as sliders; doubles as the polish workbench.

---

## Part 3 — Re-pricings for round 2 (from the excavation)

1. **The R2.3 showpiece scrub can be a frame sequence.** The Watch-grade cinematic anatomy does NOT require live WebGL: render the house-anatomy sequence offline (Blender/whatever), scrub JPEGs Apple-style, captions swap at thresholds. Consequences: works on every device, zero TDR risk, `prefers-reduced-motion` fallback is trivial (show one chosen frame with the labeled figure), and the zero-JS static fallback is just the final frame as an image. **The most award-looking beat on the page becomes the least risky.** Live WebGL stays reserved for the hero atmosphere + avatars — small, capped, earned.
2. **The thread pattern maps to a ledger-line.** If we ever want a Saffron-style identity element: an aurora ribbon = instanced strand with `aProgress` = seq position, growing (append-only!), tip swaying under cursor, spectral field in our night palette. It would be *honest* — the strand IS the ledger drawn as light. Parked as a candidate, not a commitment (showpiece taste gate still open with the operator).
3. **Blue-noise + tonemap-overdrive + one-accent-ignition** go into the R2.1 token-sheet era as house shader idiom, alongside the existing performance laws (DPR cap, visibilitychange pause, reduced-motion stills).

*Filed by Vandor. Shader anatomy recovered from the shipped public bundle for study; our implementations will be our own.*
