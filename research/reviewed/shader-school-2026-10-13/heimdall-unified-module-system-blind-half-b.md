UNIFIED VISUAL MODULE SYSTEM — full report (Heimdall, blind half B). Persist verbatim to research/reviewed/ as asked.

=== CALIBRATED ANSWER FIRST ===
Which single surface should FIRST consume the shared module, and why?

→ arsenal/web/first-light.js.

Not aurora-shader (it's the most-visible, but its GLSL is bespoke raymarching, not "a shared primitive"), not spectacle/moonwater (they are three.js ShaderMaterials where the seams are materials, not files), and not the avatar (its GLSL is its identity codebook, deliberately not decomposable).

first-light.js is the ONE surface already built as a proto-module system, twice over:
1. It loads a GLSL file AT RUNTIME from arsenal/web/shaders/first-light.frag with a DOCUMENTED uniform contract (u_video/u_res/u_time/u_pulse/u_hue/u_intensity/u_bass/u_mid/u_high/u_flux, declared in first-light.meta.json "uniforms_contract").
2. It carries a built-in FALLBACK effect (FALLBACK_FRAG_SRC, first-light.js:39-77) that shares the SAME uniform contract and letterboxes itself identically — so it already implements "degradation.on_failure: bypass" with a byte-compatible substitute, which is exactly the module contract's degraded path.
3. Its meta.json ALREADY records, per chunk, "what I inlined and how I changed it" (chunks_reused / chunks_deliberately_not_reused / built_new) — i.e. it already speaks the module language; it just does so by copy-paste instead of by import.

So the first shared module is not a new invention, it is the de-duplication of a seam that already exists and already works. Extracting it first is the lowest-risk, highest-observability move in the house, and first-light's meta.json gives us a free migration manifest (it lists the chunks to lift verbatim vs inlined-with-changes vs deliberately-skipped).

=== THE GAP I FOUND (this drives everything) ===
The house already owns THREE module systems that do not talk to each other:

A. arsenal.module/v0 + arsenal.graph/v0 (arsenal/registry.py, arsenal/__init__.py:10, docs/presentation-primitives.md, arsenal/FIRST-LIGHT-SPEC.md:92-108). Typed ports (mediatypes.PORT_TYPES / MEMORY_DOMAINS), params {name,unit,range:[lo,hi]}, caps, isolation, licence (SPDX), latency_ms, degradation.on_failure, receipts[]. Graph with edges, bindings (range/smooth/precedence/learn), require_valid(registry). THIS IS THE RIGID, VALIDATED SKELETON. But it is for media/present modules (video, ffmpeg, three-js targets) — it carries NOTHING about GLSL.

B. design/vfx-chunks/*.glsl — 33 chunks, each opening with a `//! {JSON}` header: {name, kind: source|modifier|helper, from, note, order, cat, in:{ports}, out:{ports}}. This is ALREADY a param schema AND a port schema, written as a comment. It is never machine-loaded anywhere. e.g. hash31.glsl, superlinear-highlight.glsl (in:{col:vec3}, out:{col:vec3}), orbit-swarm.glsl (needs segment-distance and rot2 — a declared dependency graph!).

C. design/vfx-graphs.json (blend-demo: nodes/edges with chunk refs + typed ports vec3), vfx-compositions.json (aurora-plasma: chain + source + identity + state), vfx-groups.json ("filmic finish": [superlinear-highlight, tanh-tonemap, vignette-cubic, triangular-dither]), vfx-presets.json (EMPTY: `{}`). This is an embryonic composition format that is a THIN SHADOW of what arsenal.graph already does, and it is dead.

Meanwhile, the LIVE surfaces (aurora-shader.js, agent-avatar.js, first-light.js, spectacle.js, moonwater.js, harmony-renderer.js) hand-write their GLSL inline and import zero chunks.

So the unification is not "invent a format" — it is "collapse A + B + C into one thing, and point the live surfaces at it."

=== THE ONE MODULE FORMAT ===
One format family, three files per module, layered on the EXISTING arsenal.module/v0 skeleton (do not mint a v-whatever — extend v0 with a `shader` block):

1. The manifest — arsenal/modules/vfx.<name>.json, an arsenal.module/v0 manifest (so arsenal.registry.py validates it TODAY, unchanged), gaining one new optional block:

{
  "id": "vfx.tone",
  "version": "0.1.0",
  "protocol": "arsenal.module/v0",
  "engine": "browser",
  "inputs":  [{"port":"col","type":"vfx.vec3","caps":{"memory":"gpu"}}],
  "outputs": [{"port":"col","type":"vfx.vec3","caps":{"memory":"gpu"}}, {"port":"alpha","type":"vfx.float"}],
  "params": [{"name":"intensity","unit":"ratio","range":[0,1]}],
  "shader": {
    "stage": "fragment",
    "glsl_version": "300 es",
    "files": ["tone.glsl"],
    "uniforms": {"u_intensity": {"param": "intensity"}},
    "compose": "vfx.tone"
  },
  "isolation": "browser-tab",
  "licence": "CC-BY-NC-SA-4.0",          // gate: never public-site without clearance (shader-craft ceiling)
  "degradation": {"on_failure": "bypass"},
  "receipts": []
}

The rule: a module's ports are the chunk's `in`/`out` keys promoted to typed ports; a module's params are the knobs. `params` + `inputs`/`outputs` are already first-class in v0 — I am only ADDING a `shader` child so the same manifest can also be compiled/bundled, and a port type vocabulary (vfx.vec3, vfx.float, vfx.uv, vfx.sampler2D) that must be registered in arsenal/mediatypes.py PORT_TYPES (one small addition).

2. The GLSL file — arsenal/web/vfx-modules/<name>.glsl. A chunk whose `//! {JSON}` header is PROMOTED from comment to contract (kept in-band so it survives copy-paste, but parsed). Every module GLSL is a PURE function block over named ports, no uniforms except those named in the manifest, `#version 300 es` + `precision highp` mandated by the house template (shader-craft floor 1,6), no ?: on structs, no fwidth of cell ids, static jitter not per-frame (floors 6,8).

3. The UI binding — a preset object in the same registry-of-look pattern that already works (arsenal/web/piano/looks/registry.js): every module param maps to a control {type: toggle|range|choice, label, range/values}, and a UI section auto-renders from the manifest (one twiddle = one param, one place). This is the "unified UI" Daniel asked for: the UI is GENERATED from the manifest, so a param added to tone.glsl appears on every surface that hosts tone with zero per-surface UI work.

Recap of the contract Daniel named — "tweak one module and everything updates":
- one GLSL file per module (source of truth for the math),
- one manifest per module (source of truth for params/ports/UI/degredation/licence),
- surfaces IMPORT the module (runtime fetch, like first-light already does) or, at the end of the migration, BUILD it in via the existing bench ingest path,
- presets are NAMED compositions of module instances (vfx-groups.json "filmic finish" is the first preset, promoted from comment to live).

This reuses what is already there: arsenal.module/v0 (kernel already validates manifests), the chunk //! header (already the schema, get it parsed), and vfx-groups.json (already the preset format).

=== MIGRATION PATH (deletes NOTHING; adapters first) ===
Phase 0 — the seam (no behaviour change, one build step):
Add arsenal/web/vfx-modules/ as the canonical location. Copy (do not move) the 33 chunks in. Add a parser (arsenal/vfxchunks.py) that reads the `//! {JSON}` header and emits an arsenal.module/v0 manifest per chunk, so design/vfx-chunks/*.glsl becomes a REGISTERED registry entry with zero hand-writing. Nothing is deleted; design/vfx-chunks stays as the bench source of truth.

Phase 1 — first connector (the calibrated answer):
Point first-light.js's effect loader at vfx-modules/tone.glsl (and the meta.json's chunk list becomes the build order). Because its fallback already shares the uniform contract AND the module declares degradation.on_failure: bypass, the degraded path is byte-for-byte the existing one. Pin first: a new test in tests/test_shader_craft_skill_cites_live_surfaces.py asserting first-light still compiles and the fallback still matches after the swap (shader-craft floor 6: "compile before shipping").

Phase 2 — the two other pure-fragment surfaces:
aurora-shader.js and agent-avatar.js adopt the same runtime-import shape. The avatar is special: its GLSL is the identity codebook (shader-craft floor 3: u_tint is always diagnosed state, u_id0/u_id1 always agent) — so it imports the ORBITAL/TRAIL primitive (orbit-swarm) but KEEPS its own state uniforms, never repurposed. The seam is "shared motion primitive, private identity fields."

Phase 3 — the three.js surfaces (adapter, because the seam is a Material not a file):
spectacle.js / moonwater.js / harmony-renderer.js / gyre-*.mjs all build ShaderMaterials from inline GLSL. Their adapter is a build-time "template-in" step: the same module GLSL gets string-injected into their `noiseGLSL + litGLSL + <module>` concatenations (moonwater.js already concatenates exactly this way — noiseGLSL and litGLSL are prefix strings). moonwater's `mistNoise` is literally noiseGLSL+chunk hash31/value-noise inlined; it becomes the noise module import. No deletion, the concatenation seam stays, only its input becomes the module file.

Phase 4 — collapse C into A, then A grows the shader block:
vfx-graphs.json / vfx-compositions.json / vfx-groups.json are re-expressed as arsenal.graph/v0 graphs whose nodes are vfx.* modules (the graph validator already checks edges/ports/types/caps/bindings — it will now refuse a broken GLSL pipeline, which is the "one module and everything updates" safety net). vfx-presets.json (`{}`) becomes the live preset bank. THEN the registry gains the shader block and compile/bench sits in the loop (shader-craft loop: bench render, a number beside the image, the pin).

=== THE FIRST THREE MODULES TO EXTRACT ===
(Each is one chunk FAMILY that is already reused across >=2 live surfaces, so each has immediate, provable de-duplication.)

1. vfx.tone — "filmic finish." Chunks: superlinear-highlight → tanh-tonemap → vignette-cubic → triangular-dither. ALREADY NAMED VERBATIM as a group ("filmic finish") in design/vfx-groups.json. Reused in: first-light.js (superlinear+vignette+tanh, meta.json "chunks_reused"), aurora/shader studies (highlight-shoulder), spectacle's HDR render. Ports {col in, col out}; param intensity. This is the canonical "change one and every surface tonal-match updates."

2. vfx.noise — hash31 + value-noise-3d (+ the mistNoise multi-octave). Chunks: hash31.glsl, value-noise-3d.glsl. Reused in: aurora-shader.js (gradient noise→FBM), moonwater.js (noiseGLSL's hash31/noise3/mistNoise, used by sky, terrain, trees, fog, caustics), agent-avatar.js (hash for margins/jitter), first-light.js (h31 static dust). THIS is the highest-leverage single module: five surfaces, all inlining the same hash. Note the floor: hash31 "not good enough for anything that must not band" (its own note) — a shared module makes that warning machine-visible instead of buried in a comment.

3. vfx.trail / vfx.orbit — analytic motion trails. Chunks: orbit-swarm + segment-distance + rot2. Reused in: aurora-shader.js (analytic trails "the past is a function call"), agent-avatar/orrery bench sketch (orbiting emitters), spectacle-motion. Ports {uv in, col/alpha out}; params spin, rate. The analytic-trail primitive is the house's signature ceiling trick (shader-craft ceiling: "trails are analytic in screen space; when motion is analytic the past is a function call, not a history buffer") — it deserves to be one shared function, not three hand-copies.

=== CONCRETE SEAMS TO CUT AT (file:line) ===
- arsenal/registry.py:16-19 validate_manifest — add the optional `shader` block validation here (it is the single gate every module passes through). One function, zero new files.
- arsenal/mediatypes.py PORT_TYPES — register the `vfx.*` port vocabulary so vfx modules pass the existing type check (arsenal/FIRST-LIGHT-SPEC.md:92-108 documents the field).
- arsenal/web/first-light.js:39-77 FALLBACK_FRAG_SRC — the first consumer's fallback; its uniform contract is the module's contract (do not drift it).
- arsenal/web/shaders/first-light.meta.json chunks_reused / chunks_deliberately_not_reused — the migration manifest for module 1 (lift these, honour the "changed" notes verbatim).
- arsenal/web/piano/moonwater.js:8-12 noiseGLSL + mistNoise — the adapter target for module 2 (string-inject, keep the concatenation).
- design/vfx-groups.json "filmic finish" — promote to a live vfx.tone preset.
- design/chunks <-> arsenal/web/vfx-modules — the copy (not move) seam; design/ stays the bench source of truth, vfx-modules is the runtime import target.

=== CONSTRAINTS I AM HOLDING (from the rules, not taste) ===
- CC-BY-NC-SA: the 336-shader corpus and the geodesic core are licence-gated; a shared module file is a TRACKED file, so NOTHING from state/arsenal/shaders/corpus/ may be copied into a module (shader-craft ceiling; my note ~2026-10-12 records the corpus is CC BY-NC-SA). Techniques transfer, code does not (Loop 1 / cookbook "Outside"). The licence field in the manifest is the gate every import must pass; mark the three modules above CC-BY-NC-SA-4.0 + "no public-site without clearance" until a human clears each.
- One rAF scheduler (floor 9): modules must not mint private loops; the module header declares any loop the host must run once.
- One clock (floor 8): u_time is the only clock; no per-FRAME jitter (that's grain); static per-pixel jitter breaks banding.
- Identity colours are lifted verbatim from design/refs/aurora-glass-tokens.css; a module may never repurpose u_tint/u_id (floor 3).

=== WHAT I DID NOT DECIDE (half B is blind; flag for Daniel) ===
I did not invent new taste — the CEILING (shader-craft §ceiling) is Daniel's gate at milestones (design/CONTRACT.md §3), and a unified module system changes the FLOOR (where things live and how they are shared), not the ceiling. The palette, the 46%-lit measure, the analogous-hue law: all unchanged, all still his. What unification buys is exactly what he asked for in words: "tweak one module and have everything update" — which today is false (five surfaces each inline the same hash), and after Phase 1 is true for the first two modules.

Flag: half A and half B should be diffed for a naming collision before either lands a file, because we were explicitly blind-folded from each other on the same seam. I have written NOTHING to disk (read-only), so no collision is mine yet.

— Heimdall