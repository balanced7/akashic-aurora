---
name: shader-craft
description: Use when cockpit motion is wrong — avatar frozen, console slow, fps drops, black canvas, banding, crawling grain, shredded rows — or when editing the light bed (scripts/aurora-shader.js), the agent avatar (scripts/agent-avatar.js), the activity line, a design/vfx-sketches/*.frag sketch, or the VFX bench. Use when asked for glow, fog, swarms, particles, trails, "shock factor", or a more alive background. Use BEFORE accepting outside shader code (Shadertoy, a skills pack) and before calling a shader change done.
---

# Shader craft

**Iron Law: a shader ships as a machined floor with a crafted ceiling. The floor is checked
blind; the ceiling is seen.** The floor is every rule below that a text-only seat can verify
from code and numbers. The ceiling is taste, and taste is Daniel's gate at milestones
(`design/CONTRACT.md` §3). Never claim the ceiling from the floor.

## When someone says… (the rule, in ten seconds)
| Someone says | The rule | Where |
|---|---|---|
| "the avatar froze" | A still avatar is the designed safe state: the watchdog holds the last frame after ~2.5 s of back-to-back slow frames, and a hidden tab does zero GPU work. Read the slow-frame streak, never a frames-over-wall-clock fps. A capped or disabled avatar snaps to its state; it does not ease. | Floor 5 · cookbook "Watchdog" |
| "the console got slow" | Cost is pixel count × march steps × emitters, on a host with an AMD display-driver crash history: keep the canvas small, cap the steps, undersample the background (never the subject), never open a second GPU context. | Floor 4 · cookbook "Cost" |
| "make the background more alive" | Change the cause, not three symptoms; put motion on rates that never line up; then run the loop: bench render, a number beside the image, a pin, fps from a visible window. | Ceiling · The loop |
| "black canvas" | Either `isSupported()` refused (no WebGL2, or the OS asked for reduced motion) or the program did not compile. The canvas's data attribute says which; compile before eyeballing. | Floor 2, 6 · cookbook "Module" |
| "banding" / "crawling grain" | Banding wants static per-pixel jitter; per-FRAME jitter IS the grain. `mediump` bands our hashes; `highp` always. | Floor 8 · cookbook "Jitter" |
| "streaks" / "rows shredded" in a tiling | A derivative was taken of a cell id. A tiling's edges are antialiased from a continuous coordinate; a marched silhouette by cone tracking. | Floor 6 · cookbook "Derivatives" |
| "same picture twice, for a diff" | A feedback effect (motion blur) is not a function of time: clear the history, settle a fixed number of frames, then capture. `--t` alone is not a still. | Floor 8 · cookbook "Still" |
| "here's a Shadertoy I like" | Ingest it through the bench, which says what it changed and what will not work. Techniques transfer; code, copy, brand and assets do not. License gate before public use. | Loop 1 · cookbook "Outside" |

## Where the craft lives (the comments ARE the spec — read them before touching anything)
- `scripts/aurora-shader.js` — the light bed: a ray-marched participating medium, three swarms
  of six emitters, analytic trails, ping-pong motion blur. Its comment blocks are the design record.
- `scripts/agent-avatar.js` — the geodesic avatar: the signature codebook rendered as an object;
  a style registry; the STATE TABLE is the codebook made visible.
- `scripts/activity-line.js` — the fleet's voice as a waveform: LIVE / FLAT / DOTTED.
- `design/vfx-sketches/*.frag` and `scripts/vfx.html` — the bench and its sketches.
- `design/CONTRACT.md` — tokens, the 60fps clause, the axis law, the loop.
- Lessons this skill folds back: `fibshell_shader_two_defect_classes`,
  `rAF_throttle_reads_as_fps_freeze`, `claude_embedded_preview_crash_trigger_2026_08_12`,
  `hud_fingerprint_diff_pattern`. Craft study III (library, 2026-09-02) holds the polish arc.

## The floor — mechanical, blind-checkable (symptom first, mechanism second)
1. **Every shader starts from the house template; nobody retypes the setup.** Raw WebGL2
   (`#version 300 es`, `precision highp float;` always, `out vec4 outColor;`, a fullscreen
   triangle from `gl_VertexID`), no Three.js, no CDN, no build step. A sketch takes `u_res` and
   `u_time`; a module is a standalone file that `scripts/bifrost_ui.py` serves from a static route.
2. **One seam, one house pattern, and the fallback never disappears early.**
   `if (X.isSupported()) { x = new X(canvas); x.start(); }`, then `setState(...)`,
   `setRate(0..1)`, `destroy()`. `isSupported()` is false without WebGL2 or under
   `prefers-reduced-motion`; the CSS fallback stays until `start()` has succeeded and returns on
   `destroy()`. The status layer owns WHEN (and calls `setState` only when the polled data's
   fingerprint changed); the shader owns the visual; neither reaches across. DeepSeek owns the
   mount in `bifrost_ui.py`; you author the module and hand over a snippet.
3. **A colour means one thing wherever it is a diagnosis.** In the avatar's style registry
   `u_tint` is always the diagnosed state and `u_id0`/`u_id1` always the agent; a style may
   render them any way and may never repurpose them. The activity line's tint is a display
   colour the status layer sets (`setTint`), not a diagnosis. Identity colours are lifted
   verbatim from the chip gradients (`design/refs/aurora-glass-tokens.css`, the `.av`
   gradients); a second scheme splits the design system in two. Alarm and warn roles never
   touch a nominal element.
4. **Slow means too many pixels, steps or emitters, on a machine that crashes when pushed.**
   This host has a documented AMD display-driver TDR history. Avatars are small (a ~64px
   canvas, a 48-step cap, `powerPreference:'low-power'`) and render at native device pixels:
   the subject is never undersampled (`AKASHIC_AVATAR_SCALE`, dpr capped at 2). Past MAX_LIVE
   instances the rest hold a still. The bed renders BELOW display resolution on purpose
   (`AKASHIC_AURORA_SCALE`) because a soft field has no edges to lose. A hidden tab does zero
   GPU work. Never open a second GPU context to look at your own work: the bench renders
   through the tab that is already open, and the harness Browser preview of a shader page
   killed Claude Desktop on 2026-08-12.
5. **A frozen avatar is the watchdog doing its job, or a watchdog lying.** It counts
   consecutive slow frames while rAF is actually firing (per-frame gaps), never frames over
   wall-clock, because a hidden tab stops rAF while the clock keeps running; it resets on
   `start()` and `visibilitychange`; when it trips it holds the last frame. Never latch an
   animation off from a wall-clock sample; never take the console down with you. A capped or
   disabled avatar SNAPS to its target state: easing needs a loop it no longer has, and a
   still that believes it changed is a lie.
6. **Shredded rows, a staircase silhouette, stray geometry and a shader that will not compile
   all have one-line causes.** Derivatives only on continuous values: `fwidth` of a cell id
   shreds whole rows, so a tiling's edge width comes from `length(fwidth(surfacePos))`,
   clamped. A marched silhouette is antialiased by cone tracking (the closest angular approach
   `d/t` per step), never by resolution alone: hit/miss is a boolean and the boolean IS the
   staircase. A nearest-cell search window is sized for QUERIES, and the brute-force sweep is
   the ground truth a clever window must match. Array sizes are injected from ONE JS constant (a
   duplicated count reads past the uploaded data and draws stray geometry). Loop bounds are
   constant; `if/else`, never `?:` on struct types. Compile before shipping; eyeballing does not
   catch a compile error.
7. **Motion blur that smears wrong or flashes black is a feedback rule broken.** A frame
   cannot sample the texture it renders into: two history textures, read one, write the other,
   swap; rebuild both on resize and gate the first read so a black history is never mixed in.
   At `u_motion` ≈ 0 the whole offscreen round trip is skipped and the path is byte-for-byte
   the old crisp one.
8. **Grain that crawls, and a "still" that is not one.** `u_time` is the one clock. Static
   per-pixel jitter breaks march banding; per-FRAME jitter is crawling film grain (removed at
   Daniel's request, not turned down). A temporal-accumulation effect is not a function of t: a
   reproducible still means cleared history plus a fixed settle, never a seek.
9. **Motion budget: follow `design/CONTRACT.md` §1, the 60fps clause.** The one thing it does
   not say: today each module owns its own rAF loop and the contract wants one scheduler, so a
   new loop is declared in the module header, never added quietly.

## The ceiling — taste, in our own words (Daniel's gate)
- Simulate the cause, not three symptoms: marching a medium gives bloom, god rays and the
  radial streak in one pass, and it cannot disagree with itself.
- One pass over the emitters lights the medium AND displaces it; the wake is a lit hollow.
- Threshold high. Fog has emptiness between banks; a black background stays black where nothing
  lights it: no ambient, no floor wash. Measured, not vibed: 46% of the screen lit was wrong.
- Analogous palette, never a rainbow: neighbours on the wheel, lower saturation, wider
  luminance, the palette's OWN hues. Two cool swarms against one warm accent, and coral is the accent.
- Colour eases through HSV the short way round: an RGB lerp from violet to green passes through
  grey-brown mud, and every intermediate frame looked like a fault.
- Trails are analytic in screen space, attenuated by the transmittance the march measured; when
  motion is analytic the past is a function call, not a history buffer.
- Identity lives in the body, state in the lines. Thinking (internal: barely turns, breathes
  hard) and tool use (external: spins fast, breathes little) differ in KIND of motion before the
  hue resolves. Grey means we cannot see. FLAT is measured-zero; DOTTED is unmeasured.
- Drift on incommensurate rates so nothing repeats; a loop teaches its period in thirty seconds.
- Superlinear highlight, then the tanh shoulder, in that order; vignette normalised by the real
  corner distance. Undersample soft low-frequency fields, never the subject.
- Spend the march once: tetrahedral normals (four map calls, not six); a see-through back layer
  is a closed-form ray-sphere solve, never a second march; a body morph is a radius-in-direction
  swap under an unchanged tiling, so `u_cube = 0` is bit-identical to the sphere.
- Planned, not built (craft study III): blue-noise dither on dark gradients, overdrive into a
  tonemap, a cursor-shifted spectral field, draw-in and draw-out ceremony. The geodesic core is
  CC-BY-NC-SA and gated before any public-site use.

## The loop — how a shader change is allowed to ship
1. Sketch in the bench: save `design/vfx-sketches/<name>.frag`. A pasted shader goes through
   `py scripts/vfx_render.py ingest --name <n> --file <f>`; the translation lives in
   `scripts/vfx_ingest.py`, which says what it changed and what will not work. A scratch
   compile links the new program before deleting the old: a failed experiment costs the
   experiment and nothing else, and sketches never enter the mountable styles.
2. Render through the open tab: `py scripts/vfx_render.py thumb --chunk <c> --t 1.0 --say "..."`,
   `sheet --frames 12 --from 0 --to 8`, `grid --a <p> ... --b <q> ... --t 2.0`,
   `state --state thinking --identity claude`. PNGs land in `design/vfx-snaps/`; `--say` posts
   beside the image so a blind seat and a sighted one look at the same picture.
3. Numbers next to the image, never as a gate: `scripts/vfx_probe_chroma.py` (luminance-only
   metrics were identical to sixteen digits across three visibly different renders).
4. Cockpit changes: `py scripts/ui_shot.py --label before` then `--label after` (`--fps` for
   real frame timing) at the two contract viewports, into `artifacts/ui/`. FPS only from a
   visible window or a trace; report no number you did not observe. The bed's perf gate is
   `scripts/bench-aurora.html`.
5. Pin the contract RED first: a seam change without a pin is not a change. Live pins:
   `tests/test_hero_avatar_mount_is_race_free.py`, `tests/test_vfx_ingest.py`,
   `tests/test_vfx_feed_and_lease.py`, `tests/test_shader_craft_skill_cites_live_surfaces.py`
   (this skill's own currency: every path it names exists, every line the cookbook quotes is
   still in its file).
6. Land per `verified-done`. File `learn` for every defect class you meet; a new class is a
   lesson AND a line in this file. Wishes go to `docs/WISHLIST.md` the moment friction is felt.

## Red-flag phrases (each one means STOP)
- "Looks right" (compile it, render it, read the number) · "Should be 60fps" (no fps you did not see)
- "Just a little grain" (it crawls) · "One more raymarcher won't hurt" (MAX_LIVE; the TDR)
- "I'll preview it in the harness browser" (it killed the desktop app once)
- "Same pixels at the same t" about a feedback effect (only after clear plus settle)
- "The header comment says so" (the avatar's header said half-res for weeks after the code went
  native; read `_resize`, not the bullet — and fix the bullet)
- The language traps (`mediump`, a count in two places, `fwidth` of a cell id, `?:` on a
  struct) are listed under "Traps" in the cookbook.

## Why this feeds the loop
The console was built by a seat that had never seen a rendered pixel, and an open-loop
controller cannot converge on a target it never observes (`design/CONTRACT.md`). Every rule above
is a measurement that replaced a vibe. Keep it that way: this skill is the fold-back for shaders,
exactly what `learn` is for everything else.

Reference: `references/house-glsl-cookbook.md` — part A for the operator (cost, palette, the
bench, a true still, outside shaders), part B for the author (the patterns, quoted from our own
code with their source lines, so the pin can say when the code has moved on and the page has not).
