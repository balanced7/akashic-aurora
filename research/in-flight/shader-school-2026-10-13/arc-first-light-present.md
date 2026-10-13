# Arc census: First Light, the preset bank, the module registry, and present

Status: in-flight research (reader 7 of 7, shader school night) · Date: 2026-10-13 · Seat: claude (Vandor), census subagent
Scope as briefed: `arsenal/web/first-light.{html,js,css}`, `arsenal/web/presets/` and `arsenal/presets.py`,
`arsenal/FIRST-LIGHT-SPEC.md`, `arsenal/modules/*.json` with `arsenal/registry.py`, `graph.py`, `plan.py`,
`arsenal/present/`, `arsenal/web/edit/`, `arsenal/web/house-round/`, `arsenal/web/glider/`, `arsenal/web/lib/`.
Method: read every file in scope (headers and bodies; the 3,000-line `play.js` by targeted search), ran three read-only
Python calls (`presets.coupling_table()`, `presets.list_presets()`, `registry.load_registry()`), and read two dated
receipts under `state/arsenal/receipts/`. No browser, no server, no GPU, no git writes. Nothing from the shader corpus
(`state/arsenal/shaders/corpus`) was opened; every shader discussed here is house code.

Citations are `file:line`. Anything I concluded rather than read is marked **(inferred)**. Paths are relative to
`E:\AI-Setup` unless stated.

---

## 0. The answer in one paragraph

This arc already owns three of the four things "tweak one module and have everything update" needs: a **typed module
datasheet** (`arsenal.module/v0`, validated by `arsenal/registry.py:21-59`), a **graph with a loud plan** (`graph.py`,
`plan.py`), and a **renderer-neutral scene with per-target honesty tables** (`present.scene.v1`). What it lacks is the
fourth thing: **the running pages do not read those datasheets**. First Light hard-codes its uniform list, its pulse
formula and its MIDI ranges (`first-light.js:462-463`, `:633`, `:808`); its patch diagram is hand-drawn SVG
(`first-light.html:91-129`); the graph's binding options are shown to the planner but never to the page. On the shader
side, the same eight GLSL helpers are pasted into up to ten files each (section 9). Tonight a fifth system arrived that
is the missing linker: `arsenal/shaders/modules.py` plus its browser twin `arsenal/web/glsl/modlib.js`, which compose
GLSL modules deterministically and emit them as `arsenal.module/v0` manifests with a `shader` block that
`registry.py:52-58` already accepts. The cleanest cut is therefore: one uniform/param contract file, preset headers
mapped onto module params, pages that compose their helpers through `modlib.js` instead of pasting them, and one token
file that feeds the CSS, the present palette and the spectacle "worlds". Sections 10 and 13 give the cut points.

---

## 1. A hardware picture of what lives here

Think of the arsenal as a studio rack.

- **First Light** is one rack unit with a patch bay on its face: a clip goes in, through a decoder, through one effect
  card, out to the screen, while a MIDI knob and the clip's own audio turn the effect's dials
  (`FIRST-LIGHT-SPEC.md:6-10`). Every session is recorded as a "take" (a flight recorder log).
- **The preset bank** is a cartridge slot on a second unit (`/play`): each cartridge is one GLSL fragment shader file
  with a one-line label on line 2 that says its name, author and what its eight macro knobs do
  (`PLAY-NIGHT-SPEC.md:35-61`). The unit swaps cartridges live with a crossfade.
- **The uniform contract** is the cartridge **pinout**: the fixed list of named inputs every cartridge may read
  (`PLAY-NIGHT-SPEC.md:76-97`). Any cartridge wired to that pinout drops in, the way any CPU built for a socket drops
  into that socket.
- **The module registry** is the drawer of **datasheets**: one JSON file per component saying its pins (ports and
  types), its knobs (params with units and ranges), its licence, its declared latency and what it does when it fails
  (`FIRST-LIGHT-SPEC.md:93-101`).
- **The graph and the plan** are the **wiring diagram and the bill of materials**: the graph says what connects to what;
  the plan prints every place a payload crosses between engines (like data crossing PCIe into another device's memory,
  which costs a copy), every licence, and the summed declared latency (`plan.py:25-78`).
- **present** is a different product line using the same datasheet drawer: a slide deck is a "scene" (content plus
  layout roles, no pixels), and each output format (slides page, print, embeddable panel, three.js gallery) is a
  component whose datasheet says, per kind of content, what it **preserves, degrades or drops**
  (`modules/present.three-js.json:48-111`).

The rest of this report is the parts list.

---

## 2. First Light (the page)

### 2.1 What it is and how it renders

- Plain script, no libraries, root-relative fetches so any port works (`first-light.js:1-6`).
- **Render stack:** one WebGL2 context (`first-light.js:517`), a **fullscreen triangle** built from `gl_VertexID` with
  no vertex buffer (`:32-42`), the video uploaded each frame as a texture with `UNPACK_FLIP_Y_WEBGL` so `v_uv (0,0)` is
  the video's bottom-left (`:540-550`), one fragment program, one draw (`:552-576`).
- **Shader source:** fetched from a single hard-coded path `/web/shaders/first-light.frag` (`:487`). The page strips
  anything before `#version` because house shaders carry a `//!` header (`:493-495`). If fetch, compile or link fails it
  links a **built-in fallback effect** held as a JS string array (`:49-111`) and shows the compile log in the HUD
  (`:360-370`, `:498-513`). Spec rule: the page must still play with the shader missing (`FIRST-LIGHT-SPEC.md:392`).
- **Frame clock:** `requestVideoFrameCallback` with `metadata.mediaTime`, falling back to `requestAnimationFrame`
  (`first-light.js:1201-1213`). A "loop generation" stamp kills stale callback chains after a clip change
  (`:1194-1219`).
- **Performance guards:** device pixel ratio capped at 2 (`:25`, `:530`); a watchdog halves the backing scale after 20
  consecutive frames over twice the 60 Hz budget, floor 0.5 (`:23-26`, `:578-589`); on WebGL context loss the raw
  `<video>` is shown as a bypass and a `degraded` event is logged; on restore it rebuilds and bumps the epoch
  (`:1252-1268`).

### 2.2 The uniform contract (the pinout)

Declared in the spec (`FIRST-LIGHT-SPEC.md:320-334`): `u_video`, `u_res`, `u_video_res`, `u_time` (media seconds),
`u_pulse`, `u_hue` (degrees), `u_intensity`, `u_bass/u_mid/u_high/u_flux`. The page caches exactly these names
(`first-light.js:461-468`) and sets them every frame (`:562-573`). The shader letterboxes itself ("contain") from
`u_res` and `u_video_res` (`FIRST-LIGHT-SPEC.md:334`; implemented `web/shaders/first-light.frag:45-66`).

### 2.3 Signals: audio features, pulse, MIDI

- **Offline audio features** come from the server (`/api/analysis/<id>`, polled, `first-light.js:655-699`): rows of
  `rms, bass, mid, high, flux` at a 480-tick hop on a 1/48000 timebase (`FIRST-LIGHT-SPEC.md:231-246`). The page
  samples a row by media time (`first-light.js:616-626`).
- **Pulse envelope:** target `0.65*bass + 0.35*flux`, smoothed by a one-pole filter with **12 ms attack, 180 ms
  release** (`first-light.js:628-653`). This is a classic envelope follower (the same circuit as a compressor's
  side-chain detector). The weights and time constants are **hard-coded in the page** even though the graph file
  states them as data (`graphs/first-light.json:21-22`).
- **MIDI:** Web MIDI, prefers an input named KeyLab (`first-light.js:763-784`); control-change only (`:797-798`).
  "Learn" binds the next CC to `hue` then `intensity`, with ranges hard-coded `[0,360]` and `[0,1]` (`:164`, `:806-814`).
  Mappings persist in `localStorage` inside try/catch (`:240-254`, `:843-856`).
- **Knob-to-screen latency:** CC `event.timeStamp` to the next frame's `expectedDisplayTime`, last 200 samples,
  p50/p95 shown (`:1221-1227`, `:213-232`).

### 2.4 Time, epochs and takes

- An **epoch** is a numbered era of the media clock; it bumps on seek, on loop wrap (media time jumps back >0.5 s) and on
  WebGL restore, and every bump clears the smoothing state and drops queued events (`first-light.js:593-612`,
  `FIRST-LIGHT-SPEC.md:343-355`).
- **Take events** carry `t = {clock:"media", epoch, ticks, timebase:"1/90000"}` (`first-light.js:198-205`), are
  throttled to 10 Hz per key (`:892-908`), batched every 500 ms (`:945-978`), and the server refuses stale epochs with
  409 (`:953-956`). Takes close on `pagehide` via `sendBeacon` (`:990-1010`, `:1392-1394`).

### 2.5 The UI

- Layout: 16:9 stage left, collapsible rack right with Library, Patch, Map, HUD, Plan panels (`first-light.html:63-170`,
  `FIRST-LIGHT-SPEC.md:285-296`).
- **Patch panel** is a hand-drawn SVG with six nodes and three wire colours (video amber, audio teal, control rose) and
  "activity lights" that flash for 140 ms when a stage fires (`first-light.html:91-134`, `first-light.js:402-426`).
  It is **not generated from the graph**: adding a node to `graphs/first-light.json` changes nothing on screen.
- **Map panel** prints mappings as `map midi.cc(<n>) -> fx.<param> {range: ..}` (`first-light.js:872-873`). That
  string imitates the graph text form but the parser would refuse it: the text grammar's endpoint is
  `node.port[.feature]` with no parentheses (`graph.py:257`, `_NAME` at `:19`). **(verified by reading the regex; not
  executed)**
- **Plan panel** posts the filled graph to `/api/plan` and shows the plan text (`first-light.js:1014-1045`).
- **Look tokens:** dark default, light under `prefers-color-scheme`, nine colour tokens plus two font stacks and two
  radii (`first-light.css:7-40`, values from `FIRST-LIGHT-SPEC.md:255-283`). Fonts: Archivo (variable width) and
  JetBrains Mono (`first-light.html:10`).
- **Perform | Edit mode switch:** the page only flips `html[data-mode]`, shows `[data-edit-only]` containers, pauses
  the clip and fires a `CustomEvent("arsenal:mode")` (`first-light.js:1270-1295`). Edit mode is owned entirely by
  `web/edit/editor.js`, loaded as an ES module (`first-light.html:12`, `:174`).

### 2.6 The effect shader itself (`web/shaders/first-light.frag`, Navi)

House code, so I describe it plainly. In order: letterbox to contain with an early return in the bars (`:45-66`); a
breathing zoom about the centre driven by `u_pulse` times a slow sine (`:68-72`); chromatic aberration by sampling red
and blue at slightly different radial scales (`:73-85`); a pulse glow (`:87-89`); a perceptual hue rotation through HSV,
gated off near 0 degrees (`:91-95`); intensity scaling (`:97`); a superlinear highlight `col += col*col*0.85` then a
`tanh` shoulder (`:99-103`); static per-pixel dust keyed on `floor(gl_FragCoord)` so it never "crawls" from frame to
frame (`:105-111`); an aspect-normalised cubic vignette (`:113-118`).

Its sidecar `first-light.meta.json` is the best provenance record in this arc: it lists which bench chunks were reused
and how they were changed (`:7-37`), which chunk was deliberately not reused and why (channel-rotate shifts hue,
`:39-45`), what was built new (`:46-51`), and a uniform-by-uniform usage table (`:52-64`). This is exactly the shape
a module's credits/changes block should take.

Inconsistency: the shader's own comment says GLSL ES 3.00 has no vector overload of `tanh`
(`first-light.frag:100-103`), while the meta file records Vandor's correction that it does (`first-light.meta.json:18`,
`:69`). The code is correct either way; the comment is stale.

### 2.7 Tests and receipts

- `tests/test_arsenal_shader_first_light.py` (6 tests) pins `#version` on line 1 and every contract uniform declared
  (its docstring, lines 1-12).
- Kernel: `tests/test_arsenal_kernel.py` (18) and Heimdall's blind pins `tests/test_arsenal_pins_heimdall.py` (78).
  The reconciliation of those blind pins is written into the spec (`FIRST-LIGHT-SPEC.md:163-179`).
- Browser receipts: `state/arsenal/receipts/first-light-chrome-20260913-*.json` (four runs on 2026-09-13), produced by
  `arsenal/lanes/chrome_verify.mjs` (the regression baseline named at `PLAY-NIGHT-SPEC.md:15`).

---

## 3. The preset bank

### 3.1 Format (`PLAY-NIGHT-SPEC.md:35-74`, checked by `arsenal/presets.py`)

- One GLSL ES 3.00 fragment shader per file, `arsenal/web/presets/<id>.frag`.
- Line 1 exactly `#version 300 es`; line 2 `//! {json}` with `id` (equals file stem), `name`, `author`, `tags`,
  `params` (at most 8, each `{k: 1..8, name: 1-16 chars, default: 0..1}`) (`presets.py:41-113`).
- Body floors, checked textually: `highp` only, `precision highp float;`, `in vec2 v_uv;`, `out vec4 outColor;`,
  uniforms only from the v1 list with exact types, no uniform in a `for` loop bound (`presets.py:116-136`). Problems are
  **reported, never raised**, so the page can list a broken preset greyed out (`presets.py:5`).
- Craft floors the validator cannot check but the spec requires: no NaN/Inf, no per-frame noise crawl (never
  `hash(u_time)`), about 8 texture reads at most, good in silence and with video absent (`PLAY-NIGHT-SPEC.md:53-61`).

### 3.2 Uniforms v1 (the extended pinout, `PLAY-NIGHT-SPEC.md:76-97`; `presets.py:18-26`)

Adds to First Light: `u_prev` (this preset's own previous frame, for feedback trails), `u_audio` (a 512x2 texture: row 0
a log-spaced spectrum, row 1 the waveform), `u_media_time` (First Light's `u_time` meaning moved here; v1 `u_time` is a
never-pausing performance clock), `u_frame`, `u_has_video`, `u_beat` (decays as `exp(-dt/0.18)`), `u_level`, and eight
macro knobs `u_k1..u_k8`.

### 3.3 The runtime that plays the cartridges (`web/play.js`, read by search only)

- Hard-coded uniform list `UNIFORM_NAMES` (`play.js:57-60`), a built-in "Passthrough" preset with reserved id `builtin`
  (`:41`, `:78`, `:3100`), presets listed from `GET /api/presets` (`:841`) and compiled one by one (`:934`).
- **Feedback:** each preset owns a ping-pong pair of framebuffers, RGBA16F when the float-colour extensions exist,
  else RGBA8 (`:624-629`, `PLAY-NIGHT-SPEC.md:129-131`).
- **Crossfade:** both presets render for `xfade_ms` (default 600, max 5000; `play.js:34-35`) and a built-in blit shader
  mixes them with a smoothstep ease (`:161-165`).
- **Audio engine:** one `AnalyserNode`, FFT 2048, no smoothing (`:1482-1483`); **relative normalisation** per band
  (power over its own 1.5 s average, squashed by `r/(1+r)`, gated below -80 dB; `:1793-1806`,
  `PLAY-NIGHT-SPEC.md:150-153`) - the MilkDrop way of making "loud" mean "louder than recently"; **two beat
  detectors**, one for live power ratios (1.6x and rising, 180 ms refractory) and one for precomputed rows
  (`play.js:1902-1930`).

### 3.4 The eight presets, by technique (house code: Navi and Vandor)

| preset (author) | file:line | technique in plain words |
|---|---|---|
| aurora-ribbons (Navi) | `presets/aurora-ribbons.frag:50-124` | three travelling sine "ribbons" whose spatial frequency and height follow three taps of the spectrum texture; an always-on idle floor so silence still breathes; analogous indigo-to-coral palette; highlights-only `tanh` soft clip |
| chromatic-bloom (Navi) | `presets/chromatic-bloom.frag:51-154` | RGB channel offset fringe; generative mode draws drifting rings and bokeh discs analytically (`:91-112`); a two-tap feedback bloom (`:122-123`); light-leak bars swept by bass and pulse; saturation and warm bleed |
| feedback-tunnel (Navi) | `presets/feedback-tunnel.frag:53-124` | previous frame sampled through a zoom-and-rotate about the centre (`:60-63`), decayed by multiply then subtract one 8-bit step so trails fully clear (`:66-69`); a waveform ring plus spectrum petals injected at the mouth; hue applied only to fresh colour (`:103-104`); magnitude-preserving `tanh` compression (`:110-112`) |
| first-light (Navi) | `presets/first-light.frag:76` onward | the First Light effect re-cut for the v1 pinout (`:2` header) with a generative fallback field (`:58`) |
| glitch-blocks (Vandor) | `presets/glitch-blocks.frag:5-17`, `:108-151` | a block grid with static per-block hashes; displacement, scanline tears and RGB split that "slide" on smooth sines rather than re-rolling each frame; beat opens a burst; sine-free hash (`:27`); explicit note that `fwidth` would explode at displaced edges (`:65-67`) |
| halftone-pop (Vandor) | `presets/halftone-pop.frag:5-18`, `:83-132` | a rotated dot lattice where each pixel evaluates its 2x2 nearest dots so big dots merge cleanly (`:83-112`); soft posterise into a warm and a cool ramp blended in HSV; high band lights statically chosen "stars" (`:126`) |
| mirror-hue (Vandor) | `presets/mirror-hue.frag:5-17`, `:50-114` | K-wedge kaleidoscope fold by `abs(mod(angle))` (`:50-57`), mirror-repeat addressing so lookups never leave the frame (`:67`), a slow perceptual hue turn plus radial hue wave, a feedback swirl seeded by a waveform slice (`:80`) |
| scope-bars (Vandor) | `presets/scope-bars.frag:5-18`, `:56-132` | MilkDrop-style log spectrum bars with LED gaps and soft cell masks (`:76-109`), a waveform scope line (`:113-124`), rising feedback backdrop (`:56`) |

All eight declare exactly five params (k1..k5) and parse with zero problems (read-only `list_presets()` run). The
2026-09-13 receipt `state/arsenal/receipts/play-20260913-215734.json` records a pass on every check (presets listed,
every playable preset compiled as visualiser and over the clip, hardware decoder, dropped frames at most 0.5%, no page
exceptions).

### 3.5 The coupling census, and a blind spot in it

`presets.coupling()` counts how many of seven scalar audio uniforms a preset actually reads outside declarations and
flags the "whole-frame glow" idiom as cosmetic listening (`presets.py:147-201`). Tonight's read-only run:
first-light driven (6 distinct/8 refs), halftone-pop driven (5/5), chromatic-bloom listening (4/7), glitch-blocks
listening (4/4), feedback-tunnel listening (3/5), mirror-hue listening (3/3), scope-bars listening (2/2),
**aurora-ribbons "cosmetic" (2/2)**.

The blind spot: the census only looks at `AUDIO_UNIFORMS` (`presets.py:150`), which excludes the `u_audio` spectrum and
waveform texture. aurora-ribbons drives its whole geometry from three `u_audio` spectrum taps
(`aurora-ribbons.frag:65-67`) and scope-bars reads `u_audio` six times; both are under-reported. aurora-ribbons is also
the preset `VISUAL-QUALITY-BASELINE.md:54`, `:109` cites as a reference. The fix is to count `texture(u_audio, ...)`
reads as their own channel(s). **(the count of six for scope-bars is a grep of non-declaration lines; not a parse)**

---

## 4. The module registry, the graph and the plan

### 4.1 The datasheet (`arsenal.module/v0`)

- Fields: `id`, `version`, `protocol`, `engine` (one of `arsenal|browser|ffmpeg|gstreamer|mpv|external`), `inputs` and
  `outputs` (each `{port, type, caps?}`), `params` (each `{name, unit, range:[lo,hi]}`), `isolation`, `licence`,
  `latency_ms.base`, `degradation.on_failure`, `receipts`, `notes` (`FIRST-LIGHT-SPEC.md:97-101`;
  validated at `registry.py:21-59`; engines `:12`).
- Port types are a closed list (`mediatypes.py:6-25`). It has grown twice: `scene.deck`/`scene.slide` for present
  (`:18-19`) and, tonight, `vfx.float|vec2|vec3|vec4` for GLSL module ports (`:20-24`). "Caps" (capabilities: memory
  domain, colour primaries, sample rate...) are checked so that "unknown is not a yes" (`mediatypes.py:40-59`).
- **New tonight:** an optional `shader` block that must carry `api: "arsenal.glsl-module/v1"` and a `provides` list
  (`registry.py:52-58`, constant at `arsenal/__init__.py:11`). This is the bridge that lets a GLSL module sit in the
  same drawer as a decoder or a slide renderer.
- Read-only `load_registry()` tonight: **32 manifests, all valid**: 4 First Light kernel pieces (`file.clip`,
  `browser.decode`, `ffmpeg.audio-features`, `browser.present`), 2 VFX (`vfx.first-light-effect`, `vfx.preset-bank`),
  2 control/analysis (`webmidi.input`, `webaudio.analyser`), 17 `media.*`, 7 `present.*`. No `glsl.*` manifests are on
  disk yet; `modules.py` can generate them (`arsenal/shaders/modules.py:244-276`, door verb `manifests [--write]` at
  `:8`).
- The present family added two optional fields, `status` (exists|building|designed) and an `atoms` coverage table
  (`docs/presentation-primitives.md` section 1, "the family only adds `status` and an `atoms` table").

### 4.2 The two VFX datasheets

- `vfx.first-light-effect`: browser-memory video in, WebGL-memory video out; params `pulse ratio 0..1`, `hue deg
  0..360`, `intensity ratio 0..1`; bypass on failure (`modules/vfx.first-light-effect.json:1-19`).
- `vfx.preset-bank`: same ports; adds `xfade ms 0..5000` and `k1..k8 ratio 0..1` (`modules/vfx.preset-bank.json:8-21`).
  The bank is **one module for all eight presets**: individual presets are not registry entries, so the plan cannot say
  which preset is running or what its knobs mean. **(inferred from the manifest and `presets.py` having no registry
  hook)**

### 4.3 The graph (`arsenal.graph/v0`, `graph.py`)

- JSON is canonical; a one-statement-per-line text form (`mode`, `node`, `a.p -> b.p`, `a | b | c` chains, `map ... {range,
  smooth, precedence, learn}`) parses to the same JSON (`graph.py:253-339`, grammar at `FIRST-LIGHT-SPEC.md:128-136`).
- Validation refuses at connect time with sentences a person can act on: unknown module, wrong direction, type
  mismatch, caps mismatch, double-fed input, cycles, bad binding source/target/range/options (`graph.py:66-189`).
- **Unknown binding keys pass silently.** `graphs/first-light.json:21-22` and `graphs/play-night.json:20` carry a
  `mix: {bass: 0.65, flux: 0.35}` key that `_check_binding` never inspects (`graph.py:140-189`). It is data no runtime
  reads (section 2.3). **(verified by reading; no test asserts it either way that I found)**

### 4.4 The plan (`plan.py`)

- Lists nodes with engine, isolation and licence; marks every **copy** (a media payload crossing engines,
  `plan.py:38-53`); sums declared base latency along the longest path, labelled "declared, not measured" (`:73-96`);
  computes a licence profile (GPL-family vs core) and warns on `NOASSERTION` and "unverified" licences (`:57-63`).
- **The plan drops binding detail:** it keeps only `from`, `to`, `range` (`plan.py:55`), so `smooth`, `precedence`,
  `learn` and the stray `mix` never appear in the text First Light shows.

### 4.5 The two graphs

- `graphs/first-light.json`: clip feeds decode and features; decode -> fx -> screen; features bind to `fx.pulse`, two
  MIDI learns to `fx.hue` and `fx.intensity` (`:1-26`).
- `graphs/play-night.json`: clip -> decode -> bank -> screen; the Web Audio analyser binds `bank.pulse`; MIDI learns
  `hue`, `intensity`, `xfade`, `k1..k8` (`:1-33`).

---

## 5. present (the presentation primitive family)

### 5.1 The idea

A deck is a **scene**, not HTML: atoms with structured payloads placed into named regions of a template, measured in
logical units on one 1920x1080 canvas, coloured and sized by **role** (`arsenal/present/__init__.py:3-11`,
`scene.py:9-19`). Daniel's words that started it: "make these primitives be a part of a family ... keep layouts while
swapping the presentation format" (`present/__init__.py:5-6`).

- 15 atom kinds (`scene.py:37-38`), 7 templates as regions (`scene.py:71-95`), token roles for palette, type, face,
  tone, mark and background (`scene.py:43-52`).
- `validate()` refuses (E01-E09) and `lint()` warns (W01-W09) in actionable sentences (`scene.py:123-247`). Key refusal:
  a scene may not carry a pixel unit, a colour or any renderer key (`scene.py:100-104`; invariant I5,
  `docs/presentation-primitives.md` section 7).
- `scene.py` is **stdlib only, no arsenal imports, no renderer knowledge** (`scene.py:3-7`), the same rule as the flow
  library (`web/lib/flow/README.md:6`).

### 5.2 Targets and honesty tables

- Four built renderers registered in one map (`present/targets/__init__.py:18-23`): slides-html, ui-element,
  print-html (pdf), three-js. Three more designed only (3d-viz, sequence, video).
- Each target's manifest carries an `atoms` table saying, per atom kind, what it preserves, degrades or drops
  (e.g. `modules/present.three-js.json:48-111`), and a target that names none of the three for a kind the deck uses is
  refused (`scene.py:260-278`, invariant I6). This is the single most transferable idea in the arc: **a renderer
  declares its losses before it runs.**
- The door (`present/__main__.py`) validates, lints, checks coverage, refuses drop-only targets unless `--allow-drops`,
  offers `--dry` (prints per-slide preserve/degrade/drop and writes nothing), and writes a take JSON per render
  (`present/__main__.py:109-176`).

### 5.3 The three.js scene path (`present/targets/three_js.py`)

- One self-contained HTML page under 200 KB with exactly one external script, three.js **r128** UMD from cdnjs, with a
  jsDelivr fallback when `--verify-cdn` HEAD-checks fail (`three_js.py:30-64`, `:294-302`).
- Each slide is painted to an offscreen 2D canvas from a **draw list** (rect, line, text ops in logical units) computed
  in Python by `_paint.py` (`_paint.py:1-15`), then used as a `CanvasTexture` on a 16x9 plane; planes stand along an arc,
  textures are built lazily for the current slide and two neighbours (`three_js.py:115-130`, `:208-216`, `:235`).
- Camera flights between planes ease in-out over 650 ms plus 90 ms per slide skipped, with a "pull back" arc for fade
  and magic transitions and none for push (`three_js.py:232-254`). Click-to-fly by raycast (`:266-272`).
- The page script lives **inside a Python string** (`three_js.py:79-279`), so its text routine (word wrap, marks,
  letter-spacing, arrowheads) cannot be reused by any other three.js page. **(inferred: there is no shared JS module
  it imports)**
- Receipts on the manifest: pins and an audit (`modules/present.three-js.json:119-146`); the note says "No frame of the
  WebGL page has been measured" in GPU-backed Chrome (`:148`).

### 5.4 Tokens in present

Family defaults by role in Python: palette (`dark #13202B`, `accent #C8762E`, ...), type sizes by role, IBM Plex Sans
and JetBrains Mono, a per-role style table (weight, line height, face, letter-spacing) (`present/targets/_core.py:22-46`).
`surface()` resolves what each role means on a dark, light or accent background (`_core.py:85-97`) - a clean
implementation of "role, not colour".

---

## 6. The editor (`web/edit/`, First Light's Edit mode)

- A media timeline editor living inside the First Light page: program monitor on the stage, timeline dock, Media,
  Inspector, Mixer and Export panels (`edit/editor.js:1-11`).
- **Clean model/view split:** `timeline.js` is pure functions over the project document (`arsenal.media.timeline/v0`),
  no DOM, no fetch, no clock, every edit returns a new document, pinned by 26 node tests
  (`edit/timeline.js:1-23`, `tests/arsenal_edit_timeline.test.mjs`). The view never edits the document; every gesture
  ends in `onCommit(newDoc)` (`edit/timeline-view.js:7-8`).
- **One writer at a time** by revision; a 409 reloads the other writer's copy (`edit/editor.js:7-9`).
- **Tokens shared by reading CSS:** the timeline canvas and mixer read `--ground`, `--accent`, `--audio`, `--control`
  and friends from `getComputedStyle` at draw time (`edit/timeline-view.js:24-34`, `edit/mixer.js:102-104`), and
  `edit.css` is written against `first-light.css`'s tokens (`edit/edit.css:1-5`). This is the working proof that a
  canvas renderer can follow the CSS theme without a second palette.
- Measured performance is recorded in file headers (timeline redraw 1.5 ms mean on a 33-minute fitted timeline,
  `edit/timeline-view.js:10-13`; audio resync within 17 ms, `edit/playback.js:20-22`).
- Name collision to note: the editor's "presets" are export encoder presets (`edit/render.js:14`, default
  `youtube_4k60_fast`), unrelated to shader presets or piano looks.

---

## 7. house-round, glider, lib

- **house-round** (Codex pilot, 2026-09-22): a read-only conversation reader. A pure projection `model.mjs` shared by the
  browser and a CLI (`house-round/model.mjs:1`, `scripts/house_conversation.mjs:4`), schema validation that even checks
  quotations match their source body (`model.mjs:24-27`), 8 node tests. Its own token vocabulary (`--bg --panel --line
  --text --muted --lavender --mint`, `house-round/style.css:1`) shares nothing with First Light's. Not a VFX surface;
  relevant only as a UI-chrome and "pure model + thin view" precedent.
- **glider** (`glider/physics.js`): a point-mass glider in 2D. Lift and drag as coefficient times speed squared, a
  linear lift curve that drops past the stall angle, induced drag `Cd = CD0 + K*Cl^2`, thermals as a parabolic updraft
  column that enters as **wind** (it changes the air-relative velocity, while position advances by ground velocity)
  (`physics.js:8-11`, `:58-93`). Every constant is data in `DEFAULTS` so a pickup can swap the wing (`:13-16`, `:20-28`).
  13 hand-rolled checks in `tests/glider_physics.test.mjs`. No renderer yet. **(inferred: no page imports it; grep found
  only the test)**
- **lib/raster-policy.js**: the house's **resolution policy** as a pure module: the drawing buffer follows the display
  box times device pixel ratio, a pixel budget (4 Mpx) clamps with a stated reason, a legibility floor (0.5) beats the
  budget, a 10% hysteresis stops resize thrash, adaptive resolution is off by default and steps down faster than up
  (`raster-policy.js:1-35`, `:95-127`, `:148-235`). 37 checks in `tests/raster_policy.test.mjs`. First Light does not
  use it; it has its own DPR cap and watchdog (`first-light.js:23-26`, `:578-589`).
- **lib/flow/**: renderer-independent fluid primitives - signed-distance volume, a staggered (MAC) velocity grid with
  pressure projection, RK2 streamlines with arc-length resampling, an authored wake force, and a portable `.flowclip`
  recording format (`lib/flow/README.md:8-31`, `:93-135`). Used by the piano wind tunnel
  (`web/piano/wind-tunnel-worker.mjs:1-4`, `web/piano/flow-take-controller.mjs:1`). Rule worth keeping: "No Three.js
  imports, DOM, global timers, dependencies" (`README.md:6`).

---

## 8. The primitives, broken down and grouped by category

"Primitive" here means the smallest reusable idea, whether GLSL, JS or Python. Copies are counted across the files in
scope (plus `play.js`, which hosts the preset runtime). The right-hand column says where one shared module would live.

### A. Frame and coordinates
| primitive | where (copies) | shared home |
|---|---|---|
| fullscreen triangle from `gl_VertexID` | `first-light.js:32-42`, `play.js` (3 files incl. `shaderlab/_harness_probe.html`) | one JS constant in a shared WebGL host module |
| letterbox "contain" (video uv from screen uv) | `web/shaders/first-light.frag:45-66`, fallback `first-light.js:78-89`, `video_uv` in 6 presets + `play.js` + spec text `PLAY-NIGHT-SPEC.md:103-108` | GLSL module `video_uv` |
| aspect-correct centred point `p` | every preset's first lines, e.g. `feedback-tunnel.frag:56` | GLSL helper |
| logical frame and contain-rect (CSS side) | `lib/raster-policy.js:63-81` | already shared, unused by First Light |
| logical canvas 1920x1080, 128 margin | `present/scene.py:31-34` | present only |

### B. Colour
| primitive | where | shared home |
|---|---|---|
| RGB to HSV and back | 10 files (`first-light.js`, `play.js`, 7 presets, `web/shaders/first-light.frag`) | GLSL module |
| perceptual hue rotate | three names: `hsv_rotate` (`web/shaders/first-light.frag:38`), `hueRot` (`aurora-ribbons.frag:44`), inline (`first-light.js:98-102`, `feedback-tunnel.frag:98-99`) | one module, one name |
| "hue never inside feedback" rule | `PLAY-NIGHT-SPEC.md:117`, restated in 4 preset headers | a lint rule, not code |
| posterise with soft steps | `halftone-pop.frag:101-104`, `glitch-blocks.frag:141` | GLSL module |
| ramp palettes / role palettes | per preset; `SPECTACLE-DESIGN.md:74-81` "world" roles; present `_core.py:23-27` | token file (section 10) |

### C. Tone (keeping highlights from clipping)
| primitive | where | shared home |
|---|---|---|
| full `tanh` shoulder | `web/shaders/first-light.frag:103` (bench chunk `tanh-tonemap`) | GLSL module with a mode param |
| highlights-only soft clip (`min(c,0.8) + 0.2*tanh(over/0.2)`) | aurora-ribbons, chromatic-bloom, feedback-tunnel, mirror-hue, scope-bars (e.g. `scope-bars.frag:130-132`) | same module, second mode |
| magnitude-preserving `tanh` compress | `feedback-tunnel.frag:110-112` | same module, third mode |
| superlinear highlight | `web/shaders/first-light.frag:102` (chunk `superlinear-highlight`) | GLSL module |

### D. Noise and hashes
| primitive | where | shared home |
|---|---|---|
| sine hash `h31` | 4 files (`chromatic-bloom`, `feedback-tunnel`, `first-light` preset, `web/shaders/first-light.frag:19`) | GLSL module (chunk `hash31` exists) |
| sine-free `hash12` "stable for large inputs" | `glitch-blocks.frag:27`, `halftone-pop.frag:28` | GLSL module |
| static dust keyed on `floor(gl_FragCoord)` | `web/shaders/first-light.frag:108`, `halftone-pop.frag:123` | recipe |
| "wobble": smooth slide with hashed rate and phase | `glitch-blocks.frag:33-37` | GLSL module |

### E. Domain warps (moving the lookup, not the colour)
breathing zoom about centre (`web/shaders/first-light.frag:68-72`; chunk `zoom-pulse`), 2D rotation `rot()`
(`feedback-tunnel.frag:51`; chunk `rot2`), kaleidoscope fold (`mirror-hue.frag:50-57`; chunk `kaleido`), mirror-repeat
addressing (`mirror-hue.frag:67`), block displacement and scanline tears (`glitch-blocks.frag:108-128`), radial
chromatic offset (`web/shaders/first-light.frag:73-85`).

### F. Feedback and time
`u_prev` ping-pong with RGBA16F/RGBA8 fallback (`play.js:624-629`); decay by multiply **and** subtract one 8-bit step
(`PLAY-NIGHT-SPEC.md:111-113`, `feedback-tunnel.frag:66-69`); feedback through zoom+rotate (tunnel) or inward rotated
sample (mirror-hue swirl); crossfade blit with smoothstep ease (`play.js:161-165`); knobs set amounts never speeds,
because `u_time * knob` jumps when the knob moves (`PLAY-NIGHT-SPEC.md:118`; v2 idea of phase accumulators,
`:247`).

### G. Audio-reactive signals
envelope follower 12/180 ms (`first-light.js:628-653`); relative normalisation with 1.5 s average and silence gate
(`play.js:1793-1806`); two beat detectors (`play.js:1902-1930`); `u_audio` spectrum/waveform texture (`PLAY-NIGHT-SPEC.md:84`,
`play.js:1878`); offline features rows (`FIRST-LIGHT-SPEC.md:231-246`); coupling census (`presets.py:147-201`).

### H. Pattern generators
travelling sine ribbons (aurora), waveform ring plus spectrum petals (feedback-tunnel, mirror-hue), analytic rings and
bokeh discs (chromatic-bloom `:91-112`), 2x2-nearest halftone lattice (halftone-pop `:83-112`), log bars with LED gaps
(scope-bars `:76-98`), waveform scope line (scope-bars `:113-124`), gradient-grid-striped-sun test field
(glitch-blocks `:65-97`).

### I. Framing
aspect-normalised cubic vignette (`web/shaders/first-light.frag:113-118`; chunk `vignette-cubic`), soft tunnel depth
with a raised floor (`feedback-tunnel.frag:99`), static scanlines per device row (`glitch-blocks.frag:150-151`).

### J. Control and binding
macro knobs k1..k8 named per preset (`PLAY-NIGHT-SPEC.md:44-47`); module params with unit and range
(`registry.py:45-51`); MIDI learn and persistence (`first-light.js:832-856`); `map` statements with smoothing,
precedence and learn (`graph.py:266-296`); continuous vs trigger targets (`PLAY-NIGHT-SPEC.md:162-168`).

### K. Runtime robustness and performance
compile-fallback-with-log (`first-light.js:480-514`); broken-preset-listed-not-hidden (`presets.py:5`,
`PLAY-NIGHT-SPEC.md:127`); DPR cap and backing-scale watchdog (`first-light.js:23-26`, `:578-589`); resolution policy
(`lib/raster-policy.js`); context-loss bypass (`first-light.js:1252-1268`); one GPU render at a time
(`arsenal/GPU-LOCK.md:1-12`).

### L. Time and recording
exact time with epochs and clock maps (`FIRST-LIGHT-SPEC.md:53-80`); take ledger (`FIRST-LIGHT-SPEC.md:149-161`);
present's own take JSON (`present/__main__.py:159-168`); flow recordings (`lib/flow/README.md:93-135`).

### M. Presentation
scene / atoms / templates / token roles / targets with coverage tables (section 5).

### N. UI chrome
colour tokens, rack of panels, HUD rows, patch lights, mode switch, searchable library list (section 2.5); editor panels
reading CSS tokens into canvases (section 6).

### O. Simulation
glider point-mass aerodynamics (section 7); fluid grid, SDF, streamlines, flowclip (section 7).

---

## 9. Duplication (one concept, several implementations)

1. **The uniform contract in four places**: `presets.py:18-26` (Python dict), `play.js:57-60` (JS list),
   `first-light.js:461-463` (JS list, First Light subset), and the two spec tables (`FIRST-LIGHT-SPEC.md:320-332`,
   `PLAY-NIGHT-SPEC.md:80-97`). A new uniform needs four edits.
2. **GLSL helpers pasted per file**: RGB/HSV in 10 files, `video_uv` in 6 presets plus `play.js`, `h31` in 4,
   `hash12` in 2 (grep counts, section 8). The bench chunks they came from (`design/vfx-chunks/*.glsl`, 31 files) are
   referenced by name in `first-light.meta.json:7-37` but were inlined by hand.
3. **Hue rotation under three names** (section 8B) and **tone shoulder in three variants** (section 8C).
4. **The First Light effect twice**: `web/shaders/first-light.frag` (v0 pinout, bench-style header) and
   `web/presets/first-light.frag` (v1 pinout, preset header), plus the JS fallback at `first-light.js:49-111`.
5. **Three `//!` header dialects for one idea ("a GLSL file with a JSON label")**: bench/sketch (`name, kind, order,
   cat, in, out`; `web/shaders/first-light.frag:2`), preset (`id, name, author, tags, params{k,name,default}`;
   `presets.py:73-113`), and tonight's library module (`name, kind, cat, order, in, out, needs, params, license,
   credits, cost, note`; `web/glsl/modlib.js:12-14`).
6. **Three param schemas**: preset `{k, name, default}` with implicit range 0..1 and implicit uniform `u_k<k>`;
   module/v0 `{name, unit, range}` (`registry.py:45-51`); GLSL module `{name, unit, range, default, uniform, label,
   step}` (`shaders/modules.py:248-253`).
7. **Three token vocabularies, four copies**: the patch-bay block (`--ground --panel --ink --ink-2 --ink-3 --rule
   --accent --audio --control`) is copied with identical values into `first-light.css:7-40`, `play.css:9-37` and `piano.css:8-17` (piano adds `--rec`);
   house-round has its own (`style.css:1`); present has a Python role palette (`_core.py:23-27`); the spectacle worlds
   name roles in prose (`SPECTACLE-DESIGN.md:74-81`).
8. **Two three.js versions**: present pins **r128** UMD from cdnjs (`three_js.py:31-33`); the piano pages pin
   **0.186.0** ES modules from jsDelivr (`web/piano.html:20-25`, `web/piano-gyre.html:7`). Fifty-eight releases apart
   **(inferred consequence: colour management and API defaults differ, so a material or texture tuned in one will not
   look the same in the other)**.
9. **Two take writers**: `arsenal/take.py` TakeLedger (`FIRST-LIGHT-SPEC.md:149-161`) and present's ad-hoc take JSON
   (`present/__main__.py:159-168`).
10. **Two resolution policies**: First Light's DPR cap plus halving watchdog (`first-light.js:23-26`, `:578-589`) and
    `lib/raster-policy.js`.
11. **Two JS test styles**: `node --test` (timeline, flow, house-round) and a hand-rolled `check()` runner (raster
    policy `tests/raster_policy.test.mjs:25-30`, glider).
12. **Three different library paths in flight tonight** for the new GLSL library: `modules.py` reads
    `arsenal/web/glsl` (`shaders/modules.py:46`); the shader lab server serves `/lib/` from
    `arsenal/web/shaderlab/glsl/` (`shaders/serve.py:8`); `modlib.js`'s usage example imports `/glsl/modlib.js` and
    `/glsl/index.json` (`web/glsl/modlib.js:7-8`), and neither the arsenal server (static only under `/web/`,
    `serve.py:301`) nor the shader lab server (`/lab/`, `/lib/`, `shaders/serve.py:231`) has a `/glsl/` route.
    **(as read around 02:35; this is tonight's work and may already be moving)**

---

## 10. Seams: clean places to cut a shared module in

1. **The pinout file.** One JSON (say `arsenal/vfx/uniforms.v1.json`: name, GLSL type, unit, range, meaning, which
   surfaces feed it) read by `presets.py` (replacing `UNIFORMS`, `presets.py:18-26`), emitted as a JS module for
   `play.js:57-60` and `first-light.js:461-463`, and used to generate the spec tables. The validator already reports
   per-uniform type mismatches (`presets.py:125-133`), so the check survives the move unchanged.
2. **Preset header to module params.** Map each preset param `{k, name, default}` to `{name, unit:"ratio",
   range:[0,1], default, uniform:"u_k<k>", label:name}`, exactly the row shape `shaders/modules.py:248-253` emits. Then
   `presets.py` can call `manifest_for` style code to give **each preset its own registry entry** (`glsl.preset.<id>` or
   `vfx.preset.<id>`), and the plan can name the running preset and its knobs. The registry's `shader` block check
   (`registry.py:52-58`) needs no change.
3. **Compose instead of paste.** `play.js:934` (compilePreset) and `first-light.js:484-514` (setupEffect) are the two
   compile sites. Insert one step: read the preset's `needs` (or infer from calls, as `modules.py` does), ask
   `modlib.js` for the dependency-ordered prelude, splice it after the header and `precision` line, then compile. Presets
   would then keep only their `main()` and their own unique functions; `rgb2hsv`, `video_uv`, `h31`, `hash12`, `rot`,
   the tone curves and the vignette become library modules. The deterministic byte composer
   (`shaders/modules.py:26-29`) means a page and the CLI produce the same shader text.
4. **The uniform-setting loop.** `first-light.js:562-573` and `play.js` set uniforms by name from page state. If the
   pinout file says where each uniform's value comes from, one shared `bindUniforms(gl, program, sources)` can replace
   both loops. **(inferred design; the two loops were read, not unified)**
5. **The graph as the page's wiring.** First Light already fetches `/api/graph/first-light` (`first-light.js:1014-1022`).
   Reading `bindings[].mix` and `bindings[].smooth` there instead of the constants at `:633` and `:648` makes the graph
   executive; a validator line in `graph.py:_check_binding` for `mix` (keys must be feature names, weights numbers)
   closes the silent-pass gap. The patch SVG (`first-light.html:91-129`) can be generated from `nodes` and `edges` with
   the existing three wire colours keyed on port type.
6. **One token file, three readers.** A `tokens.json` with roles (ground, panel, ink tiers, rule, accent, audio,
   control, plus spectacle world roles) generating: the `:root` CSS blocks now copied three times
   (`first-light.css:7-40`, `play.css`, `piano.css`); present's `DEFAULT_PALETTE` (`_core.py:23-27`) as a named
   "deck" theme; and shader palette constants. The editor proves the canvas side needs nothing new: it reads CSS custom
   properties at draw time (`edit/timeline-view.js:24-34`).
7. **A shared WebGL host.** Fullscreen triangle, compile-with-log, fallback program, DPR policy (adopt
   `lib/raster-policy.js`), watchdog, context-loss bypass: today in `first-light.js:430-589`, `:1252-1268` and again in
   `play.js`. One `web/lib/gl-host.js` would serve First Light, Play, the shader lab and future pages.
8. **A shared canvas text painter for three.js.** Lift the page script out of the Python string
   (`present/targets/three_js.py:79-279`) into `web/lib/` so the piano scenes, the shader lab HUD and the deck gallery
   share word-wrap-with-marks and arrowheads, and pick **one** three.js version for both.
9. **One take writer.** Route present renders through `TakeLedger` so every surface's runs land in one ledger shape.
10. **present's honesty table for VFX targets.** The `atoms` preserve/degrade/drop table (`scene.py:260-278`) is the
    right shape for a VFX module rendered on different hosts (WebGL page, headless SwiftShader receipt, offline video
    render): each host declares, per technique category in section 8, what it preserves (feedback precision, float
    buffers, audio texture) and what it drops.

---

## 11. Binding rules, taste and constraints found in this arc

- Never open a WebGL page in the Claude app's built-in browser pane; it crashed the app on 2026-08-12
  (`FIRST-LIGHT-SPEC.md:23`; repeated at `present.three-js.json:148`, `three_js.py:14-15`).
- Server binds 127.0.0.1 only; media access limited to library roots; no path traversal (`FIRST-LIGHT-SPEC.md:24`,
  `PLAY-NIGHT-SPEC.md:14`).
- Exact time never passes through bare floats in Python; browser doubles are rounded to ticks at a stated timebase
  (`FIRST-LIGHT-SPEC.md:25`).
- Shaders: GLSL ES 3.00, `precision highp float;`, constant loop bounds, compile checked before use
  (`FIRST-LIGHT-SPEC.md:27`); `#version` on line 1, header on line 2 (`PLAY-NIGHT-SPEC.md:39-41`); highp only; no NaN or
  Inf; no per-frame crawl; about 8 texture reads; both video and visualiser modes, silence and loud
  (`PLAY-NIGHT-SPEC.md:53-61`).
- Hue rotation is perceptual (HSV), never an RGB lerp or channel swizzle (`first-light.js:44-48`,
  `first-light.meta.json:39-45`); hue never inside a feedback loop (`PLAY-NIGHT-SPEC.md:117`).
- A knob sets an amount or an angle, never a speed times time (`PLAY-NIGHT-SPEC.md:118`).
- Smooth fast signals before they drive geometry (`PLAY-NIGHT-SPEC.md:119`).
- Silence in visualiser mode must be alive and legible (`PLAY-NIGHT-SPEC.md:120`); "the quiet case is a complete
  composition" (`SPECTACLE-DESIGN.md:83`).
- Feedback decay uses multiply plus a one-step subtraction so an 8-bit buffer clears (`PLAY-NIGHT-SPEC.md:111-113`).
- A broken preset is listed with its problem, never hidden (`presets.py:5`, `PLAY-NIGHT-SPEC.md:127`).
- A live audio input is analysed only, never routed to the speakers (feedback risk) (`PLAY-NIGHT-SPEC.md:16`).
- "Unknown is not a yes" for caps and coverage (`mediatypes.py:43-44`, `scene.py:261-264`); a module without a receipt
  is presumed broken (`docs/presentation-primitives.md` invariant I10).
- Libraries: zero downloads for First Light (`FIRST-LIGHT-SPEC.md:12`); later, Daniel's media-suite ruling permits the
  best, most stable, most reliable option including three.js (`present.three-js.json:148`; memory note
  `media-suite-project-2026-09-13`).
- Visual quality baseline: native-resolution detail, sustained 60 fps with reported frame-time distribution, never
  silently lowering resolution to earn an FPS claim, presets that offer distinct compositions and recoverable
  discoveries, and "a palette swap alone does not fulfill a request for a new silhouette"
  (`VISUAL-QUALITY-BASELINE.md:10-17`, `:33`, `:35-37`). Inspect the actual render in motion; a passing suite is not
  visual evidence (`web/AGENTS.md`, lines 12-15).
- One headless GPU render at a time through the GPU lock, bursts under 3 minutes (`GPU-LOCK.md:3-6`, `:20-25`).
- Renderer-independent primitives carry no three.js, DOM or global timers (`lib/flow/README.md:6`); the scene carries no
  renderer knowledge (`present/scene.py:3-7`).
- Licence line for tonight: corpus code never enters a tracked file; techniques transfer, code does not
  (`arsenal/shaders/__init__.py:6-10`).

---

## 12. Defects and inconsistencies found (small, each with its fix)

| # | finding | evidence | fix |
|---|---|---|---|
| 1 | coupling census ignores the `u_audio` texture, so aurora-ribbons reads "cosmetic" and scope-bars is under-counted | `presets.py:150`; `aurora-ribbons.frag:65-67` | count `texture(u_audio, ...)` reads as spectrum/waveform channels |
| 2 | graph binding keys outside the known set pass silently (`mix`) | `graph.py:140-189`; `graphs/first-light.json:21-22` | validate `mix`, or refuse unknown keys |
| 3 | plan drops `smooth`, `precedence`, `learn`, `mix` | `plan.py:55` | carry them into `bindings` and `render_plan` |
| 4 | page hard-codes what the graph says (pulse weights, attack/release, learn ranges) | `first-light.js:633`, `:648`, `:808` | read from the fetched graph (seam 5) |
| 5 | map panel prints a statement the parser refuses (`midi.cc(74)`) | `first-light.js:872`; `graph.py:257` | print `map midi.cc -> fx.hue {range: 0..360, learn: true}` and keep the CC number in a comment |
| 6 | stale comment on `tanh` overloads | `web/shaders/first-light.frag:100-103` vs `first-light.meta.json:18` | correct the comment |
| 7 | library path divergence tonight | section 9 item 12 | pick one served path and one directory |
| 8 | patch diagram not derived from the graph | `first-light.html:91-129` | generate (seam 5) |

None of these were changed; this is a census.

---

## 13. A unification sketch for this arc (for the synthesis, not a decision)

1. **Pinout first** (seam 1): it is small, it touches four files, and every later step reads it.
2. **Library modules from the duplicates** (section 9 items 2-4): write house versions of `video_uv`, RGB/HSV and hue
   rotate, `h31` and `hash12`, `rot2`, the tone curve with three modes, cubic vignette, feedback decay, in
   `arsenal/web/glsl` with the module header, credits and Apache-2.0, then point presets at them via composition
   (seam 3). Byte-identical output before and after is the acceptance test for each preset (compose, diff against the
   current inlined helpers, compile under the existing `play_verify.mjs` receipt with the GPU lock).
3. **Each preset a registry citizen** (seam 2), so the plan, the Map panel and any future UI list presets and their
   knobs from one source.
4. **First Light reads its graph** (seam 5), which turns the graph from a description into the wiring.
5. **One token file and one WebGL host** (seams 6, 7); retire the three copied token blocks.
6. **present stays as is** and lends two ideas outward: the per-target preserve/degrade/drop table (seam 10) and the
   `--dry` "what will this lose" print.

Ordering note: steps 1 and 2 are independent of the UI; steps 4-5 are UI. Step 2 is where "tweak one module and have
everything update" becomes literally true for shaders.

---

## 14. Limits of this census

- `play.js` (117 KB) was read by targeted search, not end to end. `piano*.js` and the piano GLSL are other readers' arcs
  and appear here only as cross-references.
- No page was run. Every runtime claim comes from code and from the dated receipts named above; the receipts are
  2026-09-13 observations, not a fresh pass.
- `arsenal/shaders/modules.py` and `arsenal/web/glsl/modlib.js` were created tonight while this census ran; I read
  their headers and the manifest function only.
- I did not open `docs/deck-craft-playbook.md`, `arsenal/media/*`, or `design/vfx-chunks/*.glsl` bodies (only their
  file list).
