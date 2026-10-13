# The Unified Module System (draft)

**Status:** draft for Daniel's gate and for tonight's build, 2026-10-13 (shader school night).
**Written by:** Vandor (the claude seat), from the seven house census reports (`arc-*.md` in this folder), the eight
research reports (`research/reviewed/shader-school-2026-10-13/`), Heimdall's blind half B (same folder), the 42 private
study notes, and a read of the code that landed tonight (`arsenal/shaders/modules.py`, `arsenal/web/glsl/modlib.js`,
`arsenal/registry.py`, `arsenal/web/shaderlab/toy-runtime.js`, `arsenal/shaders/render.py`, `arsenal/shaders/serve.py`,
`arsenal/web/piano/looks/registry.js`).
**Companion:** `primitive-atlas-draft.md` (the parts list this machine builds and ships).

Daniel's words, tonight, verbatim: *"Lets import them all into our vfx tooling as well and then break down the
primitives and group them by category, expand and refine the tooling and ui ... synthesize across our concurrent
creative arcs so we can have reusable structures, methodology and a unified ui across all of them ... this way we can
tweak one module and have everything update."*

---

## 0. The answer on one page

The house already owns almost every part of this machine. What it lacks is the wiring between them, so today a change
to one visual idea has to be made in up to eighteen places, and C is a different colour on different surfaces.

Think of it as a workshop that builds many different instruments, which until now has hand-soldered every board:

| workshop | the house system | where it lives |
|---|---|---|
| one parts room with datasheets | **the module library**: GLSL files with a machine-readable header | `arsenal/web/glsl/` (tonight: empty but for the composer) |
| one bill-of-materials tool | **the composer**: reads the headers and code, resolves dependencies, emits the exact text a board needs, byte-identical in Python and in the browser | `arsenal/shaders/modules.py` + `arsenal/web/glsl/modlib.js` (landed tonight) |
| one front-panel generator | **the param schema**: each knob declared once (unit, range, default), and every page's controls generated from it | new: `arsenal/web/lib/params.js`, `params-ui.js`, `arsenal/params.py` |
| saved settings for a front panel | **presets**: named sets of knob values over named modules, live by default, frozen in every receipt | generalise `arsenal/web/piano/looks/` + `arsenal/pianolooks.py` |
| one chassis for multi-board instruments | **the multipass runtime**: Shadertoy's pass model, already written | `arsenal/web/shaderlab/toy-runtime.js` (exists) + a live host |
| one test bench with an oscilloscope | **capture and headless render**: every picture comes with a receipt that names the modules and their versions | `arsenal/shaders/render.py` + `headless.mjs` (exist) |
| a parts catalogue of instruments we admire | **the Shelf**: the 42 loved shaders imported into the tooling as study subjects, licence-safe, under `state/` | new: `arsenal/shaders/shelf.py` |
| a change notice when a part is revised | **the impact report**: which surfaces' shaders change when a module changes, with before and after renders | new: `py -m arsenal shader lib impact` |

**"Tweak one module and have everything update"** then means: edit `arsenal/web/glsl/<family>/<name>.glsl`; every
surface that composes it recomposes it (the page and the CLI cannot disagree, by a byte-for-byte parity pin); the
impact report lists every surface whose shader text changed and renders each one before and after; surfaces Daniel has
approved show the change as a pending update he accepts with one look, so nothing he signed off moves silently.

**Migration deletes nothing.** Each surface adopts the library in two separate steps. First its own inline helpers move
into `arsenal/web/glsl/legacy/` with their exact maths, and its pixels do not move (proved by hash). Only then, and only
with Daniel's gate, does it upgrade a legacy part to the canonical one.

**Tonight's build order** (section 15): reconcile names and write the atlas as data (S0); teach the composer structs,
constants, hooks and quarantine (S1); fix the legacy name clash and give the lint teeth (S2); write batch A of the parts
(foundations, colour, the finish) with CPU twins and test cards (S3a), then batch B and the six P0 groups (S3b); the
param schema and generated UI (S4); the VFX bench as the first consumer, with zero pixel change (S5); the Shelf (S6); the
surface registry and impact report (S7). First Light is the first product surface, tomorrow with Daniel (S8).

---

## 1. What exists tonight (inventory)

| piece | file | state | what it already does | what it lacks |
|---|---|---|---|---|
| module composer | `arsenal/shaders/modules.py` | committed tonight (5e127983) | parses the `//!` JSON header (one line or several), reads dependencies from the code (a call to a function another module defines), topological sort with ties broken by (order, name), `compose`, `prelude`, `lint`, `manifests`; the verbs `lib list`, `lib show`, `lib compose`, `lib lint` and `lib manifests` | structs and global constants are not providers; no host hooks; one name clash takes the whole library down; lint exempts every legacy chunk |
| browser twin | `arsenal/web/glsl/modlib.js` | committed tonight (5e127983) | the same algorithm in the page; `tests/test_glsl_modules.py` and `tests/glsl_modlib_parity.mjs` pin the two byte-identical | `loadLibrary('/glsl/index.json')` expects an index nobody writes; no server routes `/glsl/` |
| the library | `arsenal/web/glsl/` | empty (its README is written but untracked) | README with conventions | every module |
| legacy chunks | `design/vfx-chunks/*.glsl` (31) | live in the bench | the `//!` one-line header the format grew from | dependencies in prose; a time-seeded dither; a provenance line naming an all-rights-reserved source |
| module registry | `arsenal/registry.py`, `arsenal/modules/*.json` (32 manifests) | live | validates arsenal.module/v0, including the optional `shader` block | GLSL modules are not yet written into it |
| multipass runtime | `arsenal/web/shaderlab/toy-runtime.js` | written tonight, **untracked** | Shadertoy's interface: Common prepended, Buffers A-D in float ping-pong, Cube A, Image; keyboard and audio textures; deterministic `advance()` from a reset; mapped error logs | house documents (only corpus JSON today); a live host; the real audio sample rate (it binds 44,100) |
| headless render | `arsenal/shaders/render.py` + `headless.mjs` | written tonight, **untracked** | SwiftShader only, refuses hardware renderers, takes the GPU lock, bursts under three minutes, receipts (`arsenal.shader-render/v1`), contact sheets, a corpus `check` census | subjects other than corpus shaders and loose files |
| shader lab server | `arsenal/shaders/serve.py` | written tonight, **untracked** | loopback only, read-only, refuses port 8793, serves `/lab/`, `/corpus/`, `/jobs/` | `/lib/` points at `arsenal/web/shaderlab/glsl/`, which does not exist; no `/glsl/` route |
| dissector | `arsenal/shaders/dissect.py` + `glsl.py` (+ `census.py`) | written tonight, **untracked** | tags techniques by the shape of the maths with file:line evidence and a cost estimate | a mapping from its tags to atlas categories |
| looks registry | `arsenal/web/piano/looks/registry.js`, `store.js`, `arsenal/pianolooks.py` | live on /piano | frozen setting descriptors (id, group, label, type, choices or range, recording lock, apply order, read, apply) drive the Studio drawer; the store has revision numbers, offline pending operations, 409 replay, loopback-only access and atomic writes | it is piano-only; three other surfaces keep their own copies of the same choice lists |
| the VFX bench | `scripts/vfx.html` + `scripts/bifrost_ui.py` routes | dormant since 2026-09-03 | a chain and a typed node graph over the chunks, sliders from a parameter manifest, snapshot, contact sheet, grid and webm capture, a CLI job queue with a renderer lease | three hand-written code generators that disagree; chunks borrow the avatar's uniforms (one slider moves three modules); the mask wire reads colour |
| raster policy | `arsenal/web/lib/raster-policy.js` | unplugged | separates the display raster from the capture tier | a caller |

The census found six description formats that do not talk to each other (module manifests, bench chunk headers, bench
groups/compositions/graphs, Play preset headers, the piano looks registry, per-page validators) and at least ten preset
stores. Everything below collapses them onto the first two pieces in the table, which are already pinned to agree.

**Untracked work at risk.** As of this draft, `git status` (read-only) shows the shader harness, lab server, dissector,
census, shader lab runtime, the library README and their tests untracked (`arsenal/shaders/{render,serve,dissect,glsl,census}.py`,
`headless.mjs`, `arsenal/web/shaderlab/`, `arsenal/web/glsl/README.md`, `tests/test_shader_harness.py`,
`tests/shaderlab_runtime.test.mjs`). This system builds on all of them, so landing them (after review, through the
verified-done gate, by the sole committer) is a precondition of S1, not an afterthought.

---

## 2. Principles (binding on every slice)

1. **One source per concept.** A function, a knob, a colour or a list of choices is written once. A copy that records
   where it was copied from still drifts silently (`arsenal/web/piano/instruments/catalog.js:1-35`).
2. **Deterministic bytes.** The same request composes the same text in every door. The composed text's hash is the
   identity of a shader; receipts carry it.
3. **Adapters first, upgrades second.** Adopting the library never moves a pixel. Improving a part is a separate,
   gated step with before and after renders.
4. **Pixels on approved looks move only through Daniel's gate.** The machined floor is checked blind; the crafted
   ceiling is seen, and taste is his (shader-craft iron law).
5. **Analytic before iterative; cost is declared.** Every part states its cost class; every loop has a constant
   ceiling; a module that owns a render loop says so in its header.
6. **The licence line has teeth.** No corpus code in any tracked file, enforced by a test, not by memory.
7. **Every picture carries its receipt.** Renderer, size, time, modules with versions, params, preset, composed hash.
8. **Fail loudly, degrade gracefully.** A broken module is named and bypassed; the page still plays with its built-in
   fallback and says so (First Light's rule).

---

## 3. The module format

A module is a `.glsl` file under `arsenal/web/glsl/<family>/`. Its leading `//!` lines are one JSON object (the bench's
header format since 2026-08-02, extended to several lines); the rest is GLSL ES 3.00 without `#version`, `precision` or
`main` (the host template owns those). Module names are kebab-case and unique; function names follow the atlas's naming
law and are unique across the library and the legacy chunks.

### 3.1 Kinds

| kind | body | composable | example |
|---|---|---|---|
| `helper` | functions and structs, pure: everything through arguments, no uniforms | yes | `noise/value.glsl` |
| `const` | global constants | yes | `core/const.glsl` |
| `recipe` | a group: functions that wire helpers, with declared params that become UI controls | yes | `groups/aurora-sheets.glsl`, `post/display-out.glsl` |
| `legacy` | a helper reproducing a surface's existing maths exactly, renamed to avoid clashes | yes | `legacy/hash-sine.glsl` |
| `source`, `modifier`, `domain`, `blend`, `mask` | bench snippets: statement blocks in the bench's block-scope convention (section 3.4) | no (a chain compiler places them; their helpers form a prelude) | `design/vfx-chunks/*` |
| `pass` | a render pass for the multipass runtime: a `mainImage` body plus declared inputs and outputs | no (the runtime places it) | `groups/feedback-trail.pass.glsl` (P1) |

### 3.2 Header fields

| field | required for | meaning |
|---|---|---|
| `name` | all | unique module name (kebab-case) |
| `kind` | all | section 3.1 |
| `cat`, `family` | all | the atlas category id (for example `B3`) and family letter; the library tree and the atlas tool group by these |
| `version` | all library modules | semantic version; a change to a body bumps it (`lib lint` checks the bump against git) |
| `order` | optional | tie-break between unrelated modules (helpers 10-30, recipes 50+) |
| `license` | library | `Apache-2.0` for house code; a legacy twin of third-party ancestry names it and sets `"public": false` |
| `credits` | library | who taught the technique, with a pointer; `[]` only for genuinely original work |
| `cost` | library | `{"class": "C0".."C4", "loop": "octaves <= 8", "tex": 0, "hooks": 1}` |
| `contract` | library | one sentence: what it promises and when it stops being honest |
| `note` | library | the craft note: when to reach for it and what it looks like when it is wrong |
| `needs` | optional | modules or functions needed but not called by name |
| `hooks` | if it calls host functions | GLSL prototypes the host must define, for example `"float mapScene(vec3 p)"`; the composer emits them once, before the first user |
| `targets` | library | what the code requires: `{"glsl": "300es", "needs": ["uint", "texelFetch", "derivatives"]}`; the composer refuses to compose for a target that lacks a need, and says which module and why |
| `params` | recipes | `[{name, label, unit, range: [lo, hi], default, step, curve, group, help, choices?, derived?}]`; each maps to one argument of the entry function in header order |
| `entry` | recipes | the function a host calls, for example `"vec3 auroraSheets(vec3 ro, vec3 rd, float t, ...params)"` |
| `in`, `out` | optional | typed ports (`vec3`, `float`, `uv`, `mask`, `sampler2D`) when the module can sit in a bench graph |
| `debug` | library | named debug views the module supports, for example `["layers", "footprint", "no-jitter"]` |
| `card` | library | the test card: a tiny recipe (or a named standard card) that visualises the module for its thumbnail and its compile check |
| `exemplars` | optional | loved-shader ids that teach the technique (ids only; never their code) |
| `learn` | optional | pointers into the research reports, for example `"NP 7.1"` |
| `twin` | where one exists | the CPU twin, for example `"arsenal/shaders/twins/noise.py:fbm3"` |
| `status` | optional | `P0`, `P1` or `P2`, from the atlas |

A minimal helper, written fresh for this document (bodies omitted here; the shipped module is
`arsenal/web/glsl/core/shaping.glsl`):

```glsl
//! {"name": "shaping-core", "kind": "helper", "cat": "A5", "family": "A", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'useful little functions': the curve family"],
//!  "cost": {"class": "C0", "tex": 0},
//!  "contract": "Each curve maps [0,1] into [0,1] (shpLinstep clamps; shpRemap does not).",
//!  "note": "Shape after the noise, never before: contrast is a decision, not a property of the field.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "standard:curve-plot", "twin": "arsenal/shaders/twins/shaping.py"}
float shpLinstep(float a, float b, float x);                 // 0 at a, 1 at b, a straight ramp between, held outside
float shpRemap(float v, float a, float b, float c, float d); // the straight line through (a, c) and (b, d), not clamped
```

A recipe header (body omitted):

```glsl
//! {"name": "aurora-sheets", "kind": "recipe", "cat": "G8", "family": "G", "version": "0.1.0", "order": 60,
//!  "license": "Apache-2.0", "credits": ["technique family B of VA 7.2 (stacked sheets over one 2D footprint)"],
//!  "cost": {"class": "C2", "loop": "layers <= 48", "tex": 0},
//!  "entry": "vec3 auroraSheets(vec3 ro, vec3 rd, float t, vec2 pixel, float intensity, float hemHeight, float fold, float rays, float layers)",
//!  "params": [
//!   {"name": "intensity", "label": "Intensity", "unit": "ratio", "range": [0, 2], "default": 1, "step": 0.01, "group": "light"},
//!   {"name": "hemHeight", "label": "Hem height", "unit": "world", "range": [0.5, 4], "default": 1.2, "group": "shape"},
//!   {"name": "fold", "label": "Folds", "unit": "ratio", "range": [0, 1], "default": 0.4, "group": "shape"},
//!   {"name": "rays", "label": "Rays", "unit": "ratio", "range": [0, 1], "default": 0.6, "group": "shape"},
//!   {"name": "layers", "label": "Layers", "unit": "count", "range": [8, 48], "default": 26, "step": 1, "group": "quality", "cost": true}],
//!  "debug": ["layer-index", "footprint", "no-average", "no-jitter"], "exemplars": ["ffG3Rc", "ttScDc"], "learn": ["VA 7.2"]}
```

### 3.3 Units vocabulary

`ratio` (0..1 or a multiplier), `px` (device pixels), `world` (scene units), `rad`, `turns`, `deg`, `hz`, `sec`,
`per-sec` (a rate; knobs set amounts and angles, never speeds multiplied by `u_time`, per the Play rule), `stops`,
`kelvin`, `nm`, `db`, `count`, `bits`, `bool`, `choice`, `colour` (always a linear-light value in the shader; the UI
shows and picks it in OKLCH). The unit decides the control (a slider, a hue wheel, a stepper, a toggle), its formatter
and its URL encoding.

### 3.4 The bench's block-scope convention, written into the spec

A snippet runs inside a block in the chain compiler's `main`. It reads and writes these variables, and nothing else
crosses blocks: `vec2 uv` (the bench frame), `vec3 col`, `float alpha`, `vec3 colB` (the second input of a blend),
`float m` (a mask). Kinds constrain direction: a `source` writes `col` and `alpha`; a `modifier` reads and writes
`col`; a `domain` reads and writes `uv`; a `blend` reads `col` and `colB` and writes `col`; a `mask` writes `m` only. A
mask can never enter a colour port (the bench's own rule; its graph code currently breaks it, census defect D1).

---

## 4. The compose mechanism

### 4.1 What stays

The resolver in `modules.py`/`modlib.js` is right and stays: dependencies read from the code plus `needs`; a
deterministic topological sort; the twin parity pin; refusing to compose a snippet.

### 4.2 Extensions (slice S1, both twins, one parity pin)

1. **Structs and constants are providers.** `struct VolAccum { ... };` provides `VolAccum`; `const float PI = ...;`
   provides `PI`. A module that uses a provided type or constant anywhere (not only as a call) depends on its provider.
   Both twins scan identifier tokens (comments stripped) against the struct and constant providers.
2. **Hooks become prototypes.** A module that declares `hooks` gets those prototypes emitted once, in a `// hooks`
   block placed before the first module that needs them. GLSL ES 3.00 allows a function to be declared before it is
   defined, so the host defines `mapScene` after the prelude, where it can itself call library parts. An unresolved
   call that is not a declared hook is a lint error, so a typo cannot pass as a hook.
3. **Quarantine instead of collapse.** `load_library(strict=True)` (CI and `lib lint`) raises on a name clash as
   today; `strict=False` (every page and every render) quarantines the later module in path order, lists it in
   `library.problems`, and loads the rest. One bad file can no longer blank every surface.
4. **Targets.** `compose(names, target="webgl2"|"three-r186"|"toy"|"webgl1")` refuses a module whose `targets.needs`
   the target lacks, naming the module and the missing need (the "loud plan" habit of `arsenal/graph.py`).
5. **The composed header.** Output starts with `// arsenal.glsl-module/v1 compose: <modules in order>` (as today) plus
   `// sha256: <hash of the body that follows>` and `// modules: name@version ...`, so a receipt can name exactly what
   ran.
6. **An index for pages.** `py -m arsenal shader lib index --write` writes `arsenal/web/glsl/index.json`
   (`{api, files: [{path, sha256}]}`), which `modlib.loadLibrary` already expects; a test fails if the index is stale.
7. **Routes.** `arsenal/shaders/serve.py` points `LIB` at `arsenal/web/glsl/` and also serves it at `/glsl/` (the path
   in modlib's own usage note). The Bifrost console needs the same static route for the bench (DeepSeek owns
   `scripts/bifrost_ui.py`; Vandor authors the snippet and hands it over, per the house boundary).

### 4.3 How a host uses it

```text
page or CLI                    composer                                  host
--------------------------     -------------------------------------     ------------------------------------------
names = recipe + helpers  -->  resolve (deps from code, structs,     --> template line 1..n (#version, precision,
target = webgl2 | three         consts, needs) -> order                    uniforms generated from params)
                               emit hooks block once                  --> + composed prelude (sha256 in its header)
                               refuse snippets / missing targets      --> + host code (defines the hooks, calls entry)
                               -> text + manifest of what ran         --> + main / mainImage
```

For three.js surfaces (the piano, studies, Moonwater, Spectacle) the composed prelude is the string they already
concatenate (`moonwater.js:6-16`, `spectacle.js:21-22` and `:179`, `gyre-light-rays.mjs:6` with its `common` option).
Three.js r186 on WebGL2 accepts GLSL ES 3.00 syntax when the material sets `glslVersion: THREE.GLSL3`; modules that need
`uint` declare it, so a three.js material without GLSL3 is refused by name rather than failing to compile.

---

## 5. Params and the generated UI

### 5.1 One descriptor shape

The looks registry's descriptor (`registry.js:107-177`) is the proven shape; the param schema generalises it so a
module param and a look setting are the same kind of object:

```text
{ id, group, label, type: "range" | "choice" | "toggle" | "colour" | "vec",
  unit, range: {min, max, step}, default, curve: "linear" | "log" | "exp", values (choices),
  help, recBlocked, order, uniform, derived (an expression of other params), cost (true if it changes cost) }
```

- `paramsFromModule(header, instanceId)` turns a recipe's `params` into descriptors whose uniforms are namespaced per
  instance (`u_<instance>_<name>`). This ends the bench's parameter-bus leak, where one slider (`u_sub`) moved
  kaleidoscope folds, tile count and hex density at once.
- A single-instance surface may bind short names (`u_intensity`), declared once in its surface entry (section 10).
- `validate(descriptors, values)` exists twice (JS `arsenal/web/lib/params.js`, Python `arsenal/params.py`) with one
  shared fixture file of verdicts that both must reproduce (the twin habit).
- A URL codec, a formatter (unit-aware) and MIDI learn ranges come from the same descriptor, replacing the three
  descriptions of every Gyre parameter (HTML attributes, validator ranges, a URL parser that reads the HTML back).

### 5.2 The generated controls

`arsenal/web/lib/params-ui.js` renders descriptors into controls with the house tokens: grouped sections, a reset to
default on each control, the unit beside every number (the axis law: label, unit, hover explanation, and a dead state
that looks dead), cost-marked controls badged, recording-locked controls disabled with the house refusal text, and a
blur after pointer clicks so letter keys return to the note keyboard (the Studio house rule). Every page that shows
knobs renders through it: the bench Inspector, the Studio drawer, First Light's patch panel, Play's knobs, the Gyre and
Wind sliders.

### 5.3 The unified UI (the Workbench layout)

One layout, built from shared components in `arsenal/web/lib/workbench/`, used by the bench first and offered to every
surface's settings drawer:

```text
+-------------------+--------------------------------------------+---------------------+
| LIBRARY           | STAGE                                      | INSPECTOR           |
| families >        |  the one canvas (ShaderHost)               |  params-ui for the  |
|  categories >     |  debug view switch: off / heat / slice /   |  selected node or   |
|   modules (card,  |  NaN-range / cells / footprint / layers    |  group; presets;    |
|   cost, status)   |  numbers beside the image, never as a gate |  receipt of what    |
| groups            |                                            |  ran (modules@ver,  |
| SHELF (42 loved)  |                                            |  composed sha)      |
+-------------------+--------------------------------------------+---------------------+
| STRIP: takes and renders (contact sheets, before/after for an impact report), each with its receipt          |
+---------------------------------------------------------------------------------------------------------------+
```

Live thumbnails stay rendered images (sprite strips from the capture service), not N live WebGL windows: the studio plan
of 2026-08-02 rules out many live contexts on this host, and the shader-craft floor forbids a second GPU context to look
at our own work.

---

## 6. Presets

### 6.1 The format

A preset is `{api: "arsenal.preset/v1", id, name (Daniel's own words), surface, modules: [{name, version}],
values: {paramId: value}, mode: "live" | "pinned", notes, created, rev}`. It holds visual settings only (the looks
registry rule: never key lock, reader or playing preferences).

### 6.2 Live, pinned, and the receipt

Daniel asked for live behaviour ("tweak one module and have everything update"); the bench's rule says editing a group
must never change a saved picture. Both hold if three things are kept distinct:

- **Presets are live by default.** A preset names modules, not their text, so it follows improvements.
- **Approved looks are gated.** A surface entry marked `approved` (section 10) shows a module change as a pending update
  with before and after renders; accepting it is one action. Until then it composes the previous version, which the
  library keeps addressable by content hash (`state/arsenal/glsl-archive/<name>/<sha>.glsl`, written by `lib index`).
- **Takes are pinned forever.** Every render and recording saves its composed source (our own code, a few kilobytes)
  beside its receipt under `state/`, so a saved picture can always be reproduced exactly.

### 6.3 The store

The piano's store already has the hard parts: revision numbers, 409 replay by id, offline pending operations,
loopback-only access, atomic fsync-and-replace writes (`store.js:179-218`, `pianolooks.py:59-84, 193-219`). Generalising
it per surface schema (P1) replaces the per-origin browser libraries (Gyre's presets live in browser storage and differ
between ports 8799 and 8793) with one server-side store, global by default, with reorder handles and his preset names
(rulings R13).

---

## 7. The runtime: one host, one multipass engine

### 7.1 ShaderHost (live pages, raw WebGL2)

Today three cockpit modules each carry their own compile helper, resize policy, upload code, watchdog and render loop,
with three different watchdog policies and diverging resolution semantics (`scripts/aurora-shader.js`,
`scripts/agent-avatar.js`, `scripts/activity-line.js`), and First Light and Play carry a fourth and fifth. The census
counted 22 files that each own a `requestAnimationFrame` loop against the contract's one-scheduler rule
(`design/CONTRACT.md:79`).

`arsenal/web/lib/shader-host.js` (P1, extracted from `agent-avatar.js:647-833` as the reference) gives every raw-WebGL2
surface one chassis:

- the house template (`#version 300 es` on line 1, `precision highp float;`, `out vec4 outColor;`, a fullscreen
  triangle from `gl_VertexID`), compile with a mapped log, and the built-in fallback kept until `start()` succeeds;
- uniforms generated and bound from param descriptors (section 5), plus the house uniforms (`u_res`, `u_time`,
  `u_dt`, `u_frame`, `u_mouse`);
- one controllable clock with a host-side wrap period that time-driven noises respect (the multi-day stutter fix,
  NP recommendation 2), and per-second rates only;
- one watchdog policy (the avatar's: count consecutive slow frames while rAF is firing; reset on `start()` and
  `visibilitychange`; hold the last frame when tripped);
- zero GPU work in a hidden tab; `prefers-reduced-motion` respected by `isSupported()`;
- resolution through `arsenal/web/lib/raster-policy.js` (plugged in at last): the subject at native device pixels,
  soft fields allowed to undersample, never silently lower resolution to earn a frame-rate claim;
- registration with one page scheduler (`arsenal/web/lib/frame-scheduler.js`) instead of a private loop;
- an optional pass list (section 7.2) for feedback and simulations;
- debug-view switching by a uniform (`u_debug`) that every module's `debug` list maps onto.

The cockpit's one-seam pattern stays exactly as the skill states it (`isSupported()`, `new X(canvas)`, `start()`,
`setState`, `setRate`, `destroy()`); ShaderHost is what is behind it.

### 7.2 The multipass engine: one runtime for corpus and house

`toy-runtime.js` already runs Shadertoy's pass model faithfully: Common prepended, Buffers A-D ping-ponging in float
targets, Cube A, Image, keyboard and audio textures, a deterministic `advance()` from a reset (the still rule). Rather
than write a second engine, the house speaks the same document shape:

- **A house toy** (`arsenal.toy/v1`) is a JSON file shaped like a saved Shadertoy shader (a render-pass list with
  inputs and outputs) plus a header: `uses` (library modules), `params` (descriptors), `licence: "Apache-2.0"`, and
  `bindings` for host inputs (the piano's note texture, the audio texture, a video).
- At load, the runtime sets **Common = the composed prelude of `uses`** (plus any common code of the toy's own). The
  runtime already prepends Common to every pass, so every pass sees the same library at the same version.
- Params become uniforms in every pass through the same binder as ShaderHost.
- Two runtime fixes the research found: bind the real `AudioContext.sampleRate` to `iSampleRate` (today a constant
  44,100: 1.47 semitones off at 48 kHz, GP finding 4), and keep float targets or subtract a decay floor (an 8-bit trail
  never fully fades, GP finding 6).
- Live use: ShaderHost wraps `createToy` when a surface declares passes. Headless use: `render.html` as today.

### 7.3 Three.js surfaces

They keep their renderer (Daniel's media-suite ruling: the best, most stable and most reliable tool wins, three.js
included). The library reaches them as text: `ctx.glsl.compose(names, {target: 'three-r186'})` in the scheme and
instrument context (`piano.js:1290-1294`), and the composed string fed into the concatenation seams they already have.
Stage, bloom and tone-mapping settings come from one stage kit (P1, `arsenal/web/lib/render/stage.mjs`, from
`piano.js:439-529`) that exposes the bloom threshold as a readable number instead of comment folklore (schemes assume
0.9; Spectacle sets 0.94).

### 7.4 The honesty table

Present's scene already makes each output target declare, per kind of content, what it preserves, degrades or drops
before it runs (`arsenal/present/scene.py:260-278`). The module system reuses it per target:

| target | preserves | degrades | drops |
|---|---|---|---|
| `webgl2` (cockpit, bench, First Light, Play) | everything in the library | modules declaring `derivatives` inside loops (ANGLE's Direct3D compiler unrolls; use explicit gradients) | nothing |
| `three-r186` | everything, with `glslVersion: THREE.GLSL3` | `pass` modules (three.js render targets are wired by hand) | modules needing `uint` when a material is not GLSL3 (refused by name) |
| `toy` (shader lab, headless receipts on SwiftShader) | everything | timing (SwiftShader's numbers say nothing about the GPU) | nothing |
| `webgl1` (the akashiclabs site, P2) | C0 maths, palettes, tone curves | derivatives (need an extension) | the integer hash family (falls back to the legacy sine twin), `texelFetch`, float targets |

---

## 8. Capture and headless render

`py -m arsenal shader render` already turns a corpus id or a loose `.frag` into PNGs with a receipt, on SwiftShader,
under the GPU lock, in bursts under three minutes. It grows **subjects**, so every unit of the system can be pictured
by the same door:

| subject | what is rendered | default renderer |
|---|---|---|
| `module:<name>` | the module's test card (`card` in its header) | SwiftShader |
| `group:<name> [--preset P]` | the recipe in a minimal host at the preset's values | SwiftShader |
| `toy:<path>` | a house toy document | SwiftShader |
| `surface:<id>` | a registered surface's composed shader in its own template, where the surface allows headless | SwiftShader |
| `corpus:<id>` (today's behaviour) | a corpus shader, for study only | SwiftShader, always, refused on hardware |

Renderer policy, three tiers, matching the census: **SwiftShader** (CPU; every corpus render, every CI check, every
test card; no hardware risk); **GPU headless** (house subjects only, under `state/arsenal/gpu-render.lock`, headless with
the anti-throttling flags, bursts under three minutes, never port 8793); **the open tab** (the cockpit through
`scripts/vfx_render.py` and its job lease, the only way to see a cockpit module on the GPU without a second context).

Every receipt (`arsenal.shader-render/v1`, moving to the one shape in `arsenal/media/receipt.py`) adds: the composed
sha256, `modules: [name@version]`, params and preset, target, renderer string, buffer size, the t list and the settle
frames. **Before and after** is a first-class job: `--against <git ref>` renders the same subject from the module text at
that ref (read with `git show`, never by checking anything out) and writes a labelled side-by-side contact sheet, which
is what the impact report shows Daniel.

Numbers beside the image, never as a gate: the floors tool and the probes run on each frame and print beside it; taste
stays Daniel's (shader-craft iron law; `design/CONTRACT.md` section 3).

---

## 9. Import: the Shelf (the 42 loved shaders in the tooling, licence-safe)

"Import them all into our vfx tooling" cannot mean copying their code into the bench: `design/vfx-sketches/` is
tracked, and the corpus is other people's work (286 of 335 corpus shaders are CC BY-NC-SA, and Warping carries an
all-rights-reserved header the corpus meta misses). The bench's own ingest door writes into that tracked folder, so it
needs a `state/` root before any corpus import (census seam 7). The Shelf is the safe form of the import:

- **`arsenal/shaders/shelf.py`** (verb `py -m arsenal shader shelf build` / `list` / `show <id>`) writes
  `state/arsenal/shaders/shelf/index.json` (gitignored). Per loved shader it joins: title, author, licence (with the
  restrictive-header correction), a `study_only` flag; the dissector's technique tags mapped to atlas categories
  (a tag-to-category table lives in `arsenal/shaders/atlas.json`); the study note's path and its technique headings;
  the atlas groups it exemplifies and the parts it teaches best (atlas section 19); and the SwiftShader filmstrip
  `render`/`filmstrip` already produce under `state/`.
- **The lab server serves it** at `/shelf/index.json` (loopback only, as the corpus already is).
- **The bench gets a Shelf tab** (P1 UI): a card per shader with its filmstrip, its licence badge, its tags as
  links into the Library tree, and two actions: "open the study note" and "compare with a house group", which renders
  the original's filmstrip (SwiftShader, `state/`) beside the house recipe's filmstrip at the same t values (Daniel's
  2026-08-02 ask: render the original next to ours). A `study_only` shader shows its study note and no images.
- **Rebuilding, not porting.** The way a loved look enters the house is a new recipe written from the atlas's parts
  and the study note's description, credited in its header, Apache-2.0, never a translation of the original's text.
  The licence-line test (section 14) enforces it.

The Shelf is the import Daniel asked for in the only form the licence line allows: every loved shader is browsable,
dissected, linked to the parts and groups that rebuild it, and comparable side by side with our version.

---

## 10. How every surface consumes it

A **surface registry**, `arsenal/shaders/surfaces.json`, lists every consumer: `{id, file, engine, target, compose
(module names), legacy (its legacy modules), params binding, approval: "approved" | "bench" | "experimental", headless:
true|false, owner note}`. `py -m arsenal shader surface list|show` prints it; `lib impact` reads it. Tonight it holds the
bench and the shader lab as live consumers and every census surface below as `not yet adopted`.

| surface | engine | today's seam (from the census) | adoption | first modules | gate | slice |
|---|---|---|---|---|---|---|
| **VFX bench** (`scripts/vfx.html`) | raw WebGL2 | three code generators: `buildGLSL` :768-804, `buildGraphGLSL` :1250-1301, `thumbShaderFor` :1522-1583; slider builder :399-410 | lift the three into `scripts/vfx-codegen.js` built on modlib; old functions kept behind `?codegen=legacy` | the legacy chunks as they are, then the library | none (no approved looks) | S5 |
| **bench header readers** (`scripts/bifrost_ui.py:543-562`, `core/learning/vfx_chunk_lessons.py:36-53`) | Python | read line 1 only | call `arsenal.shaders.modules.parse_module` | — | none; must land before any multi-line header enters `design/vfx-chunks` | S2 (snippet to DeepSeek for `bifrost_ui.py`) |
| **Shader lab** (`toy-runtime.js`, `render.html`) | toy | corpus JSON only | house toys: Common = composed prelude | all of batch A | none | S3, S6 |
| **First Light** (`arsenal/web/first-light.js`, `shaders/first-light.frag`) | raw WebGL2 | runtime loader + byte-compatible fallback (`first-light.js:49`), uniforms :461-463, compile at `setupEffect` :484-514, pulse constants :633 and :648, `first-light.meta.json` lists chunks reused | legacy twins of its inline helpers, prelude spliced at `setupEffect`; later read bindings from `graphs/first-light.json` instead of constants | `legacy/hsv`, `legacy/hash-sine`, `finish` (legacy-cockpit preset) | approved look: pixels must not move at adoption | S8 (tomorrow) |
| **Play presets** (`arsenal/web/play.js:934`, `presets/*.frag`) | raw WebGL2 | `rgb2hsv`, `video_uv`, `h31` and a tone shoulder pasted per preset; the `//!` header on line 2 | each preset's header gains `uses`; prelude spliced at `compilePreset`; one pinout file for the uniform contract | `legacy/hsv`, `uvContain`, `finish` | approved presets: byte-diff plus the `play_verify` receipt under the lock | P1 |
| **Cockpit light bed** (`scripts/aurora-shader.js`) | raw WebGL2 | inline noise and tone (:304-315), the only ping-pong machinery in the house (:537-659), naive fog integration (VA 12 note 1) | ShaderHost + legacy twins; the energy-conserving integration is a separate ceiling change for Daniel | `legacy/hash-sine`, `volume/integrate` (gated), `finish` | approved; the bed's idle behaviour is a parked wish (W182) | P1 |
| **Agent avatar** (`scripts/agent-avatar.js`) | raw WebGL2 | geodesic core with CC BY-NC-SA ancestry; identity codebook | shared helpers only (hash, tone, normals, cone coverage); identity and state uniforms stay private (`u_tint`, `u_id0`, `u_id1` never repurposed); a clean-room `domFoldIcosa` replaces the gated core when Daniel chooses | `ray/normals`, `ray/aa3`, `finish` | approved; licence gate before public use | P1 |
| **Activity line** (`scripts/activity-line.js`) | raw WebGL2 | own compile and DPR policy; ignores reduced motion | ShaderHost; neon-line group | `groups/neon-line` | approved | P2 |
| **/piano** (`arsenal/web/piano.js`, schemes, instruments, Spectacle, Moonwater) | three.js r186 | LIGHT as JS with generated #defines (:701-719); scheme context (:1290-1294); Moonwater and Spectacle prefix strings; nine pitch-colour copies | `ctx.glsl.compose` in the scheme and instrument context; `palPitchFifths` as the GLSL twin of the OKLCH palette with a three-language parity test; `musNote` texture from one note bus | `colour/palette`, `input/music`, `legacy/hash-hoskins` (Moonwater) | approved looks; never restart port 8793; recording rules (nothing changes while REC runs) | P1 |
| **Piano studies** (Gyre, Wind, Crystal, Chord tree) | three.js r186 | `createRayMeshes(THREE, {common, ...})` at `gyre-light-rays.mjs:6`; strip extrusion ×4, core-plus-halo ×7, soft-box PMREM ×5 | `common` = composed prelude; `glowTwoGauss` and the neon-line group replace the profile copies | `light/glow`, `groups/neon-line`, `light/env` | approved studies | P1 |
| **present three.js target** (`arsenal/present/targets/three_js.py`) | three.js r128 UMD | page script inside a Python string | after the house settles on one three.js version | `finish` | — | P2 |
| **akashiclabs site** (`E:\akashiclabs-site`, `AuroraHero.astro`) | WebGL1 | its own aurora and sine hash | `webgl1` target of the aurora band tier | `groups/aurora-band` | public: licence-clean modules only | P2 |
| **Edit mode and media** (`arsenal/media`, `arsenal/web/edit/`) | ffmpeg, Canvas2D | colour maths re-decided per tool | the CPU twins double as one colour-science module (`arsenal/shaders/twins/colour.py`) for floors and probes (sRGB, Rec.709 luminance, OKLab chroma) | twins only | — | P1 |

**Through the surfaces, one change.** Once a surface is in the registry, its composed prelude is a function of the
library; a module edit changes exactly the surfaces whose composed hash changes, the impact report names them, and the
renders show what moved.

---

## 11. Migration without deleting anything

The method has four steps per surface, and each step has a pin before it lands.

1. **Register.** Add the surface to `surfaces.json` as `not yet adopted`, with its file, engine and the line ranges of
   its inline GLSL helpers. No behaviour change.
2. **Lift to legacy twins.** Its inline helpers move, byte for byte in their maths, into
   `arsenal/web/glsl/legacy/<surface>-<topic>.glsl`, renamed where a name would clash (Moonwater's `hash31` becomes
   `hashHoskins31`). The surface composes them instead of pasting them. **Acceptance:** the composed shader differs from
   the old one only by helper order and names (a normalised diff), and a render at fixed t is pixel-identical (frame
   hash), on SwiftShader for headless-capable surfaces and through the open tab or the GPU lane under the lock otherwise.
   The old inline text stays in the file behind a switch (`?glsl=inline`) until the pin has held for a week; removing
   it is Daniel's call (the house rule: ask before deleting functionality).
3. **Upgrade, gated.** A legacy part is swapped for its canonical part (sine hash to PCG, HSV to OKLCH, naive to
   energy-conserving integration). This moves pixels by design. `lib impact` renders before and after for every affected
   surface; Daniel accepts or declines per surface; a declined surface keeps the legacy twin, which is a supported state,
   not debt.
4. **Share.** The surface's knobs move onto the param schema (its UI generated), its presets into the store, its loop
   into the scheduler. Each is a separate slice with its own pin.

What is never done: deleting a lab fork, a legacy chunk, a fallback, or a surface's inline path without Daniel saying
so; editing a product file to prototype (prototypes are runtime overrides); touching port 8793.

---

## 12. The house rules this system keeps

| rule | source | how the system keeps it |
|---|---|---|
| Every shader starts from the house template: `#version 300 es` line 1, `precision highp`, `out vec4 outColor`, fullscreen triangle; no three.js, CDN or build step **in the cockpit** | `.claude/skills/shader-craft/SKILL.md` floor 1 | modules are fragments; ShaderHost owns the template; lint refuses `#version`, `precision`, `mediump` in a module; the cockpit composes at run time with modlib (no build step) |
| One seam, one house pattern; the fallback never disappears early | floor 2 | ShaderHost implements the pattern; First Light's built-in fallback stays |
| A colour means one thing where it is a diagnosis; identity colours from the chip gradients; `u_tint`, `u_id0`, `u_id1` never repurposed | floor 3; `design/CONTRACT.md:62-66` | the avatar adopts helpers only; identity stays private uniforms |
| Slow means pixels × steps × emitters on a host with a driver-crash history; never a second GPU context to look at our own work | floor 4 | `cost` class on every module; constant loop ceilings; live thumbnails are rendered images; capture goes through the open tab or the lock |
| The watchdog counts consecutive slow frames while rAF fires; holds the last frame | floor 5 | one watchdog policy in ShaderHost |
| Derivatives only of continuous values; cone-tracked silhouettes; counts from one constant; constant loop bounds; `if/else`, never `?:` on structs; compile before shipping | floor 6 | lint checks; `aaConeCoverage`; `unrollBarrier`; every module's card compiles on SwiftShader in a test |
| Feedback needs two textures, rebuilt on resize, first read gated | floor 7 | toy-runtime's ping-pong; `pass` modules only through the runtime |
| `u_time` is the one clock; jitter static per pixel; a still of a feedback effect is cleared history plus a fixed settle | floor 8 | `dthIgn`/`dthR2` static; `dthIgnFrame` behind an "accumulating host" flag; lint flags time in a hash; `advance()` from a reset |
| One rAF scheduler; at most 24 concurrently animating elements; reduced motion disables ambient motion | floor 9; `design/CONTRACT.md:68-82` | `frame-scheduler.js`; modules declare loops in their header |
| One headless GPU render at a time under the lock, bursts under three minutes; never `chrome --version`; never port 8793 | `arsenal/GPU-LOCK.md` | render.py and headless.mjs already hold it; the GPU tier is opt-in per subject |
| Never open a WebGL page in the Claude app's browser pane | `arsenal/FIRST-LIGHT-SPEC.md:23`; skill line 62-64 | nothing in this system opens one; verification is headless or Daniel's own Chrome |
| Corpus code never enters a tracked file; techniques transfer, code does not | `arsenal/shaders/__init__.py:6-10`; tonight's licence line | the Shelf lives in `state/`; the licence-line test scans every tracked GLSL and JS file against corpus shingles |
| Machined floor checked blind; crafted ceiling seen; taste is Daniel's gate | skill iron law; `design/CONTRACT.md` section 3 | numbers beside the image; approved surfaces gated in `surfaces.json`; upgrades only through before and after |
| Visual quality baseline: fidelity, beauty, fluidity, elegance, performance (native pixels, 60 fps floor, never silently lower resolution), trust | `arsenal/VISUAL-QUALITY-BASELINE.md:10-17` | raster policy in ShaderHost; receipts record the drawing-buffer size; frame times only from a visible window or a trace |
| Inspect the actual render in motion before calling visual work done | `arsenal/web/AGENTS.md` | a slice that changes a visible surface ends with Daniel's (or a sighted) review, never a passing suite alone |
| Daniel's rulings: no forbidden tools in the media suite (R1); sustain brightness (R2); light decays, bloom never stacks to white (R3); un-aliased, adaptive, 60 fps or native (R4); spectacle Full by default with a one-click toggle (R5); primitives as a family that keep layouts across formats (R7); precise internals, elegant presentation (R8); reuse primitives dynamically (R9); a strike adds, never restarts (R10); one module updates everything, with verbs for every action (R11); restraint on the recorded canvas (R12); global dashboards and gentle hints (R13) | `arc-daniel-voice.md` | targets per module (R1); `envStrikeSag` and `musLight` (R2, R3, R10); C2 antialiasing parts and raster policy (R4); a global spectacle dial over group intensities (R5); groups as the family (R7, R9); the impact report (R11); the verbs in section 13 (R11); the protect mask and recording locks (R12); the global preset store (R13) |
| Ask before deleting functionality; fix in place | memory, `feedback_dont_delete_functionality` | section 11 |
| Claude is the sole committer; DeepSeek fences every stage; DeepSeek owns `bifrost_ui.py` | memory | lanes in section 15 |

---

## 13. The verbs

Daniel asked for verbs for every action. Existing verbs keep their names (tests pin them); new ones join the same door.

| verb | does | status |
|---|---|---|
| `py -m arsenal shader lib list` | every module, by category | exists |
| `py -m arsenal shader lib show <name>` | header, provides, resolved dependencies | exists |
| `py -m arsenal shader lib compose <name>... [--target T]` | the composed text, with its hash | exists; `--target` new (S1) |
| `py -m arsenal shader lib lint [--strict]` | the floors a text-only seat can check; warnings for legacy chunks | exists; teeth new (S2) |
| `py -m arsenal shader lib manifests [--write]` | each module as an arsenal.module/v0 manifest | exists |
| `py -m arsenal shader lib index [--write]` | `arsenal/web/glsl/index.json` for pages, plus the content-addressed archive | new (S1) |
| `py -m arsenal shader lib new <family>/<name> [--recipe]` | scaffold a module with a full header, a twin stub and a card | new (S3) |
| `py -m arsenal shader lib uses <name>` | reverse dependencies: modules, groups, presets and surfaces that use it | new (S7) |
| `py -m arsenal shader lib impact <name> [--against REF] [--render]` | which surfaces' composed hashes change, and optional before and after renders | new (S7) |
| `py -m arsenal shader lib twin <name> [--values]` | run the CPU twin and print reference values | new (S3) |
| `py -m arsenal shader lib card <name>` | render the module's test card (SwiftShader, under the lock) | new (S3) |
| `py -m arsenal shader atlas [--family F] [--status P0] [--built]` | the atlas from `atlas.json` and the headers: planned versus built | new (S0) |
| `py -m arsenal shader group list` / `show` / `render <name> [--preset P]` | groups (recipes) and their renders | new (S3b) |
| `py -m arsenal shader preset list` / `show` / `diff` / `apply` | presets across surfaces | P1 |
| `py -m arsenal shader surface list` / `show` / `hash` | the surface registry and each surface's composed hash | new (S7) |
| `py -m arsenal shader shelf build` / `list` / `show <id>` | the loved shaders in the tooling | new (S6) |
| `py -m arsenal shader dissect <id> --atlas` | dissection tags mapped to atlas categories and parts | new (S6) |
| `py -m arsenal shader render <subject> ...` | renders with receipts; subjects `module:`, `group:`, `toy:`, `surface:`, `corpus:` | exists for corpus and files; subjects new (S3b) |
| `py -m arsenal shader check`, `filmstrip`, `serve`, `ingest`, `list`, `show`, `missing`, `harvest-js` | unchanged | exist |

---

## 14. Tests (pre-registered)

Each is written red before the mechanism it pins (the house method; floors commits of 2026-09-17).

| test file | asserts | slice |
|---|---|---|
| `tests/test_glsl_atlas.py` | `arsenal/shaders/atlas.json` parses; category ids unique; every planned function name unique across the atlas and the legacy chunks' provides; every exemplar is an id in the loved set when the corpus is present; every built module's `cat` exists in the atlas | S0 |
| `tests/test_glsl_modules.py` (extended) | structs and constants resolve as dependencies; hooks emitted once before the first user; an unresolved non-hook call is a lint error; strict load raises on a clash, lenient load quarantines the newcomer and composes the rest; `--target` refuses a module whose needs the target lacks | S1 |
| `tests/glsl_modlib_parity.mjs` (extended) | the browser twin produces byte-identical output for the new fixture (struct, const, hook, quarantine, target) | S1 |
| `tests/test_glsl_index.py` | `index.json` matches the files and their sha256; stale index fails | S1 |
| `tests/test_shader_serve_routes.py` | `/glsl/` and `/lib/` serve `arsenal/web/glsl/`; traversal still refused; port 8793 still refused | S1 |
| `tests/test_glsl_lint_teeth.py` | lint warns on `design/vfx-chunks/triangular-dither.glsl` (time-seeded hash), errors on the same pattern in a library module; flags `fwidth` of a floor-derived id, non-constant loop bounds without `unrollBarrier`, `mediump`, a missing `cost`, a param without unit, range or default | S2 |
| `tests/test_vfx_legacy_rename.py` | after the legacy `fbm3`/`vn` rename, the bench chunks that call them compose to text that differs only by the identifiers; the provenance line no longer names the all-rights-reserved source | S2 |
| `tests/test_glsl_naming_law.py` | no function provided twice across library and chunks (strict load succeeds); prefixes match the family table; every module has `license`, `credits`, `cost`, `contract`, `card` | S3 |
| `tests/test_glsl_twins.py` | CPU twins against reference values: `pcg3d` bit-exact on fixed vectors; sRGB round trip under 1e-6; OKLab round trip under 1e-5 in gamut; `oklchClip` never changes hue by more than 1e-4 turns; tone curves at fixed points; `palPitchFifths` equals the Python twin and the piano's JS palette within 1/255 per channel for every pitch class | S3a |
| `tests/test_glsl_cards.py` (slow, under the lock, SwiftShader) | every module's card compiles; renders non-flat; `dbgRangeScope` finds no NaN or Inf; one burst under three minutes | S3a, S3b |
| `tests/test_glsl_groups.py` (slow) | each P0 group renders at 480×270, t in {0, 2, 4} with receipts naming modules and composed hash; floors (not dead, not blown) pass; numbers printed beside each frame, never gating taste | S3b |
| `tests/test_glsl_licence_line.py` | no tracked file under `arsenal/web/glsl/`, `design/`, `scripts/` or `arsenal/web/` shares a run of 12 normalised tokens with any corpus pass (skipped if the corpus is absent; runs that are only a function declaration are exempt, because signatures such as `sdCapsule(vec3 p, vec3 a, vec3 b, float r)` are the field's common tongue; a short allowlist of declared textbook idioms, each with its public source). A dry run tonight over both draft documents found 11 such runs, all signatures, and no code | S3a |
| `tests/params_schema.test.mjs` + `tests/test_params_schema.py` | the JS and Python validators agree on a shared fixture of descriptors and values; URL codec round trips; namespaced uniforms are deterministic; the looks registry's descriptors validate under the schema through the adapter | S4 |
| `tests/vfx_codegen_parity.test.mjs` | for every chunk, group, composition and graph in `design/vfx-*.json`, the modlib-backed code generators produce GLSL byte-identical to the legacy generators, except a declared list (the mask-port fix) | S5 |
| `tests/test_shader_shelf.py` | on a synthetic corpus: every entry complete; a study-only entry has no image paths; nothing written outside `state/`; with the real corpus, all 42 loved shaders listed with at least one atlas link | S6 |
| `tests/test_glsl_impact.py` | changing a fixture module flips exactly the surfaces whose composed hash changes; `lib uses` lists the reverse closure | S7 |
| `tests/test_first_light_adoption.py` | the composed First Light effect differs from the inline one only by helper relocation; fallback unchanged; uniform contract unchanged | S8 |

The existing pins stay green throughout: `tests/test_shader_craft_skill_cites_live_surfaces.py` (the skill's currency),
`tests/test_vfx_ingest.py`, `tests/test_vfx_feed_and_lease.py` (pinned names `_VFX_LEASE`, `_VFX_FEED`, `_VFX_JOBS`...),
`tests/shaderlab_runtime.test.mjs`, `tests/test_shader_harness.py`, `tests/piano_looks_registry.test.mjs`.

---

## 15. Build order for tonight

Each slice names its files, its acceptance (pre-registered: the test is written and seen red before the mechanism),
and its stop condition. Slices S0 to S4 are the night's commitment; S5 to S7 are the strong goal; S8 waits for Daniel
because it touches an approved look. Every slice ends with the verified-done gate and a receipt that separates what was
observed, what is proposed and what is unverified.

**Lanes (suggested; the conductor decides).** Vandor writes S0 and S1, reviews everything, and is the sole committer.
Heimdall fences every stage (a blind review of each slice's acceptance before its code and of its diff after; his
reports persisted verbatim) and receives the `bifrost_ui.py` snippet he owns. Navi takes module batches in S3 as
proposals (module files plus twins under a lane-namespaced scratch folder) that Vandor lands after review. Fan out for
evidence (cards, twins, renders); keep judgement (naming, contracts, what moves pixels) with one seat.

### Before S0: land tonight's untracked harness

- **Files:** the untracked shader harness listed in section 1 (render, serve, dissect, glsl, census, headless, the
  shader lab runtime, the library README, their tests).
- **Acceptance:** their own tests green (`tests/test_shader_harness.py`, `tests/shaderlab_runtime.test.mjs` and the
  dissector's tests); a review pass by Heimdall; committed by the sole committer through the verified-done gate. No
  corpus text in any of them (the licence-line test of S3a runs over them too once it exists).

### S0. Names and the atlas as data (about 45 minutes)

- **Files:** `arsenal/shaders/atlas.json` (families, categories, planned parts with signature, contract, cost class,
  status, exemplar ids, learn pointers, and a tag-to-category table for the dissector; our own words only);
  `arsenal/shaders/atlas.py` (load, query, the `atlas` verb).
- **Acceptance:** `tests/test_glsl_atlas.py` red, then green. `py -m arsenal shader atlas --status P0` lists 184 rows
  matching the atlas draft. The collision ledger (atlas 1.1) is encoded: no planned function name appears twice and
  none collides with a legacy chunk except `fbm3`, which is flagged for S2.
- **Stop if:** the naming law needs a decision only Daniel can make (none expected).

### S1. Composer extensions, both twins (about 2 hours)

- **Files:** `arsenal/shaders/modules.py`, `arsenal/web/glsl/modlib.js` (structs and constants as providers; hooks to
  prototypes; strict and lenient loading with quarantine; `--target`; composed hash and module versions in the output
  header; the `index` verb and archive), `arsenal/shaders/serve.py` (`LIB` points at `arsenal/web/glsl/`, plus a
  `/glsl/` route), and a Bifrost static-route snippet for Heimdall.
- **Acceptance:** the S1 rows of section 14, red first; the existing `tests/test_glsl_modules.py` and the parity pin
  stay green; `py -m arsenal shader lib list` still lists the 31 chunks with no change in their composed text.
- **Stop if:** parity cannot be held byte-identical for a feature: drop the feature from both twins rather than let them
  differ.

### S2. Legacy rename and lint with teeth (about 1 hour)

- **Files:** `design/vfx-chunks/value-noise-3d.glsl` (functions renamed `benchVn` and `benchFbm3`, provenance line
  corrected to "standard lattice value noise"), its two callers `noise-mask.glsl` and `plasma-field.glsl`;
  `arsenal/shaders/modules.py` lint (warnings for legacy chunks, errors for library modules); the header-reader snippet
  for `scripts/bifrost_ui.py:543-562` (to Heimdall) and the edit to `core/learning/vfx_chunk_lessons.py:36-53`.
- **Acceptance:** `tests/test_glsl_lint_teeth.py` and `tests/test_vfx_legacy_rename.py` red then green;
  `py -m arsenal shader lib lint` exits 0 and prints `triangular-dither` among its warnings with the reason "time-seeded
  hash: per-frame crawl (floor 8)".
- **Stop if:** a saved bench composition stores chunk text rather than names (then the rename is a no-op for it, which
  is fine; record it).

### S3a. Batch A modules: foundations, colour and the finish (about 3 to 4 hours with fan-out)

- **Files:** the 31 batch-A files of atlas section 18 under `arsenal/web/glsl/`; CPU twins in
  `arsenal/shaders/twins/` (`hash.py`, `noise.py`, `shaping.py`, `colour.py`, `tone.py`, `palette.py`); standard cards
  in `arsenal/web/glsl/cards/` (curve plot, field and histogram, hue-exposure test card, ramp test card).
- **Acceptance:** `tests/test_glsl_naming_law.py`, `tests/test_glsl_twins.py` and `tests/test_glsl_licence_line.py` red
  then green; `py -m arsenal shader lib lint --strict` clean; `tests/test_glsl_cards.py` (SwiftShader, one burst under
  the lock): every batch-A card compiles, is not flat, has no NaN.
- **Stop if:** a card fails to compile on SwiftShader and the cause is not found in 15 minutes: quarantine that module
  (lenient load proves the rest still compose) and move on.

### S3b. Batch B modules and the six P0 groups (stretch; about 4 hours with fan-out)

- **Files:** the 34 batch-B files; the six recipes in `arsenal/web/glsl/groups/`; `render.py` subjects `module:`,
  `group:`, `toy:`.
- **Acceptance:** S3a's tests extended to batch B; `tests/test_glsl_groups.py` renders each group at 480×270, t in
  {0, 2, 4}, receipts under `state/arsenal/shaders/renders/groups/` naming modules and composed hash; floors print beside
  each frame. Taste is not claimed: the contact sheet waits for Daniel.
- **Stop if:** the night runs short: batch A alone is a complete win (atlas section 18).

### S4. Param schema and generated controls (about 2 hours)

- **Files:** `arsenal/web/lib/params.js`, `arsenal/web/lib/params-ui.js`, `arsenal/params.py`, a shared fixture
  `tests/fixtures/params/descriptors.json`; an adapter from the looks registry's descriptors (no change to the Studio).
- **Acceptance:** `tests/params_schema.test.mjs` and `tests/test_params_schema.py` red then green, agreeing on every
  verdict in the fixture; descriptors generated from the `aurora-sheets` and `display-out` headers render in a node
  test DOM (jsdom-free: a fake document object, the way the looks registry is tested) with the right units and ranges.
- **Stop if:** jsdom-free rendering proves impractical: ship the validator and codec, leave the DOM renderer for P1.

### S5. The bench as first consumer, zero pixel change (about 2 hours)

- **Files:** `scripts/vfx-codegen.js` (the three generators lifted from `scripts/vfx.html`, rebuilt on modlib, the
  legacy generators kept and selectable by `?codegen=legacy`), `scripts/vfx.html` (imports it).
- **Acceptance:** `tests/vfx_codegen_parity.test.mjs` red then green over every chunk, group, composition and graph;
  the only declared difference is the mask-port fix (the mask wire now feeds `m`, not colour), which ships behind the new
  path with its own diff in the receipt. No GPU render needed: identical text compiles identically.
- **Stop if:** an existing saved graph produces different text for a reason other than the declared fix: keep
  `codegen=legacy` as the default and record the case.

### S6. The Shelf (about 1.5 hours)

- **Files:** `arsenal/shaders/shelf.py`, the `shelf` verb, `dissect --atlas`, the `/shelf/index.json` route.
- **Acceptance:** `tests/test_shader_shelf.py` red then green; `py -m arsenal shader shelf list` prints 42 loved
  shaders, each with licence, at least one atlas group and its study note path; Warping shows `study_only` and no
  images; `git status --short` (read-only) shows nothing new outside `state/` apart from the tracked code files of this
  slice.
- **Stop if:** filmstrips are missing for some shaders: list them as `not rendered`; rendering them is a separate,
  locked, SwiftShader burst.

### S7. Surface registry and the impact report (about 1.5 hours)

- **Files:** `arsenal/shaders/surfaces.json` (bench and shader lab live; every census surface as `not yet adopted`
  with its seam's file and lines), the `surface`, `lib uses` and `lib impact` verbs; `--against REF` reading module
  text with `git show` (read-only).
- **Acceptance:** `tests/test_glsl_impact.py` red then green; `py -m arsenal shader lib impact display-out` lists the
  bench and the shader lab and nothing else tonight.

### S8. First Light adoption (tomorrow, with Daniel)

- **Files:** legacy twins of First Light's inline helpers; `first-light.js` splices the prelude at `setupEffect`;
  the inline path kept behind `?glsl=inline`.
- **Acceptance:** `tests/test_first_light_adoption.py`; a fixed-t frame hash identical before and after (SwiftShader
  through the harness, or the `play_verify` lane under the GPU lock on a test port, never 8793); then Daniel looks at
  it in motion in his own Chrome (the visual baseline requires the render seen in motion).

### What not to do tonight

- Move a pixel on an approved look (the piano, the cockpit bed, the avatar, First Light, Play presets, the studies).
- Render on the GPU outside the lock, open any WebGL page in the app's browser pane, or touch port 8793.
- Copy corpus code (including the CC0 and MIT shaders) into a tracked file.
- Delete a lab fork, a legacy chunk, a fallback or an inline path.
- Mint a third header dialect: everything uses the `//!` multi-line JSON header the composer already reads.

---

## 16. Decisions for Daniel

One calibrated question first, because it decides how "everything updates" behaves:

> **When we improve a shared module, should a look you have already approved update by itself, or show you a before
> and after first?** My recommendation: update by itself everywhere you have not approved anything, and show a
> one-click before and after on looks you have approved. That keeps your rule that approved work does not move behind
> your back, and still means one tweak reaches everything the moment you say yes.

Then, each with renders side by side when they are ready:

1. The display transform per surface (tanh for glow fields; PBR Neutral or AgX for lit 3D; ACES only on purpose).
2. Swapping the sine hash for the integer hash, surface by surface.
3. Hue rotation through OKLCH instead of HSV (the house rule says "perceptual"; OKLCH is the honest form).
4. A very dark tinted ground versus pure black (atlas section 20).
5. Where the unified Workbench lives first: the bench page in the Bifrost console (8787), which already drives the
   console's own avatar, is the proposal.
6. The cockpit bed's fog integration (energy-conserving is about 35% dimmer in dense banks and stops depending on step
   size; a ceiling change).
7. Whether the avatar's geodesic core is rebuilt clean-room from `domFoldIcosa` before any public use.

---

## 17. Reconciliation with Heimdall's blind half B

Heimdall wrote his half blind to tonight's code. Where we agree, the system follows him; where the landed code or the
census settled a point differently, this table says which way and why.

| question | Heimdall (half B) | this draft | why |
|---|---|---|---|
| one format layered on arsenal.module/v0 with a `shader` block | yes | yes | `arsenal/registry.py` already validates the block; `manifest_for` already emits it |
| where modules live | `arsenal/web/vfx-modules/` | `arsenal/web/glsl/` | the composer landed there tonight with its README and parity pin |
| manifest ids | `vfx.<name>` | `glsl.<name>` | `manifest_for` emits `glsl.<name>`; `vfx.*` stays for whole-effect manifests (`vfx.first-light-effect`, `vfx.preset-bank`) |
| licence field of house modules | CC-BY-NC-SA-4.0 until cleared | Apache-2.0, written fresh | house modules carry no corpus code; the licence-line test proves it; corpus ancestry is confined to legacy twins marked `public: false` |
| copy the 33 chunks into the new folder | yes (copy, not move) | no: read them in place | `modules.py` already reads `design/vfx-chunks/` in place; a copy would be the first drift |
| first consumer | First Light | the bench codegen first (S5, zero pixel risk), First Light as the first product surface (S8) | the bench proves the composer against every saved chunk, group and graph with no approved look at stake; First Light is still the right first product surface for his reasons (runtime loader, byte-compatible fallback, a migration manifest in its meta file) |
| the first three modules | tone (filmic finish), noise (hash and value noise), trail (orbit swarm) | finish (with a static dither replacing the crawling one), the integer hash plus a legacy sine twin, then the neon-line group; the analytic trail is P1 | the "filmic finish" group ends in a time-seeded dither that breaks floor 8; the trail has three implementations with different maths, so it needs its own parity work |
| port types in `mediatypes.PORT_TYPES` (`vfx.vec3`, ...) | register them | agree (needed before `in`/`out` ports pass `validate_manifest`); part of S1 | — |
| collapse the bench JSON stores into arsenal.graph/v0 | phase 4 | agree, after the take strip and render ledger (studio plan) | the census found three saves in the bench's whole life: the gesture, not the storage shape, is the bottleneck |
| flag a naming collision between the halves | asked | done: the atlas collision ledger (section 1.1) covers the research reports, the legacy chunks and Moonwater's `hash31` | — |

---

## 18. Glossary (plain words for the terms above)

- **Composer:** the tool that, given the names of modules, gathers everything they need in the right order and emits
  one block of GLSL text.
- **Twin:** the same algorithm written twice (Python and JavaScript, or GLSL and Python) with a test that holds them
  to the same output.
- **Hook:** a function a library part calls but the host defines, like a socket on a board (`mapScene`).
- **Legacy twin:** a module that reproduces a surface's existing maths exactly, so the surface can join the library
  without changing a pixel.
- **Card:** a tiny test picture a module draws of itself, used for its thumbnail and its compile check.
- **Surface:** any page or program that draws with the library (the bench, First Light, the piano, the cockpit).
- **Impact report:** the list of surfaces whose shader text changes when a module changes, with before and after
  renders.
- **SwiftShader:** a GPU emulated on the CPU; slow, but it cannot crash the display driver, so it is the house's safe
  renderer for checks and for other people's shaders.
- **The GPU lock:** a file-based lock that lets only one headless GPU render run at a time on this machine.
