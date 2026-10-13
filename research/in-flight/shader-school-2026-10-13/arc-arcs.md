# Arc census: the house's concurrent creative arcs, how they relate, and what each one rebuilt

Reader: one of seven, shader school night, 2026-10-13. My slice is the whole family at once: the piano visualizer
(looks, glass, studio, story layer, lean light), the VFX bench, First Light and the media suite (Play, Edit mode,
`arsenal/media`), NOW PLAYING and the presentation family (`arsenal/present`), the study pages (Gyre, Crystal
studies, Chord tree, Wind), Moonwater and Solstice, the jam, the house-round pilot, the glider, the akashiclabs.io
site, and the cockpit (the aurora light bed, the agent avatar, the activity line).

Two sibling reports go deeper on the piano and should be read with this one; I cite them instead of repeating them:
`research/in-flight/shader-school-2026-10-13/arc-piano-core.md` (the `/piano` page and its modules) and
`research/in-flight/shader-school-2026-10-13/arc-piano-studies.md` (the four study pages).

Method: read-only. `git log`, `git status`, `git show --stat` and file reads; small greps for counting. No git
command that changes anything, no browser, no server, no GPU. Every claim carries a `file:line` or a commit hash.
Anything I concluded without reading it directly is marked **(inferred)**. No corpus code was opened; techniques are
described in words.

Two things moved while I was reading, and the report reflects the later state: the GLSL module core landed as
`5e127983` ("GREEN: the house GLSL module core and its browser twin", 2026-10-13), and `arsenal/modules/` went from
31 to 32 manifests.

---

## 0. The short version (for Daniel)

Over two months the house built about fifteen visual machines. Think of them as a row of home-built PCs in one
garage. Each one works, several are beautiful, and they were built fast by different hands on different nights. But
each has its **own power supply** (its own render loop), its **own sound card** (its own audio analyser), its **own
MIDI port**, its **own colour chip** (its own way of turning a note into a colour), its **own case paint** (its own
page colours and fonts), its **own recorder**, and its **own settings memory**. Where the house did standardise a
part, it standardised it **separately three or four times**, so the standards do not plug into each other.

Tonight's module core (`arsenal/shaders/modules.py`, its browser twin `arsenal/web/glsl/modlib.js`, commit
`5e127983`) is the first shared bus: one format, one resolver, one composer. It currently reads the bench's old
chunk folder in place (`arsenal/shaders/modules.py:38-41`) and the house library folder holds only the composer
itself (`arsenal/web/glsl/` contains just `modlib.js`). So the bus exists; almost nothing is plugged into it yet.

The numbers that matter most for "tweak one module and everything updates":

| Concept | How many separate implementations | Where to look |
| --- | --- | --- |
| Render engines | 4 GPU stacks (raw WebGL2 house template; three.js r186 ES modules; three.js r128 UMD; WebGL1 Shadertoy-style on the site) plus Canvas2D and server-side ffmpeg | section 3 |
| Note colour on the circle of fifths | at least 9 | section 6.1a |
| The classic sine hash (the `43758.5453` constant) | 18 files in this repo, plus the site | section 6.2 |
| Fractal noise (`fbm`, layered noise) | about 13 definitions | section 6.2 |
| Tone mapping (how bright light is squeezed into the screen's range) | 3 families, 5 different exposure settings | section 6.4 |
| Page colour and font systems | at least 10 | section 6.1c |
| Preset and settings stores | at least 10 formats | section 6.6 |
| Recorders and "take" ledgers | 3 browser recorders, 4 take or recording stores | section 6.8 |
| MIDI input | 6 | section 6.10 |
| Things that own a `requestAnimationFrame` loop | 22 files | section 6.12 |
| Whole-page forks of an old `piano.js` | 5 files, about 10,800 lines, 4 of them untracked | section 6.15 |

The good news is that the house has already invented, and proven, the four patterns a unification needs. They are
just each used in one place (section 5.3):

1. **A twin with a parity pin.** Python and JavaScript copies of the same logic, held byte-identical or
   rule-identical by a shared test fixture: the jam's tempo map (`arsenal/jam/__init__.py:6-8`), the live cadence
   judge (`arsenal/web/piano/cadence-live.js:17-20`), and now the module core (`arsenal/shaders/modules.py:21-24`).
2. **A pure module and a host.** No DOM, no three.js, node-tested, handed a read-only input object each frame:
   `lean.js`, `cadence-live.js`, `harmony-feel.js`, `moment.js`, `crystal-performance.mjs`, `solstice-signals.mjs`.
3. **A slot contract with a fuse.** The piano's Scheme and Instrument slots (`arsenal/PIANO-V2-SPEC.md:48-87`), which
   already host the crystal studies as instruments (`arsenal/web/piano/instruments/crystal-study.js:4-5`).
4. **Settings as data.** The piano's looks registry: every setting described once, with label, type, choices,
   apply order and read-back (`arsenal/web/piano/looks/registry.js:1-23`, `107-140`), already driving the Studio's
   Looks tab (`arsenal/web/piano/studio/studio.js:31`, `66`).

---

## 1. Sources read

- `git log --oneline -1500`, filtered for the visual arcs; `git show --stat db1b23d2`; `git log` on individual
  files for when they entered the repo; `git status` for what is untracked.
- Memory: `C:\Users\L5\.claude\memory\media-suite-project-2026-09-13.md`, `media-toolkit-vision-2026-10-11.md`,
  `presentation-primitive-family.md`, `story-layer-arc-2026-10-12.md`, `akashiclabs-site-era.md`,
  `shader-school-2026-10-13.md`.
- Specs: `arsenal/FIRST-LIGHT-SPEC.md`, `PLAY-NIGHT-SPEC.md`, `PIANO-V2-SPEC.md`, `SPECTACLE.md`,
  `VISUAL-QUALITY-BASELINE.md`; `arsenal/media/README.md`; `arsenal/web/piano/{GYRE,CRYSTAL-STUDIES,CHORD-TREE,WIND}.md`;
  `arsenal/web/house-round/README.md`; `design/CONTRACT.md`; `.claude/skills/shader-craft/SKILL.md`.
- Research: `research/reviewed/shader-school-2026-10-13/heimdall-unified-module-system-blind-half-b.md`,
  `research/in-flight/vfx-system-code-map-2026-09-12.md`, `research/in-flight/glider-prototype-2026-09-20/brief.md`.
- Code headers and targeted lines across `scripts/` (cockpit and bench), `arsenal/web/` (every page),
  `arsenal/present/`, `arsenal/jam/`, `arsenal/shaders/`, `arsenal/registry.py`, `arsenal/modules/*.json`,
  `design/vfx-*`, and `E:\akashiclabs-site\src`.
- `docs/ROADMAP.md` and `docs/JOURNEY.md`: neither mentions the visual arcs in any depth (a grep of ROADMAP for
  piano, vfx, shader, media, present, cockpit, glider and jam finds only unrelated lines; JOURNEY's entries stop
  well before September). The visual arcs live in memory files, specs and commit messages, not in the roadmap.

---

## 2. The arcs on one timeline

| Date | Arc | The milestone (source) |
| --- | --- | --- |
| 2026-08-01/02 | Cockpit | The activity line's "LIVE / FLAT / DOTTED" design from Daniil's 2026-08-01 push (`scripts/activity-line.js:7-20`); the VFX studio synthesis and plan (`research/in-flight/vfx-studio-synthesis-and-plan-2026-08-02.md`, library atoms `20260802_vfx-studio-synthesis-and-plan_*`) |
| 2026-08-02 onward | VFX bench | The chunk library's first sources are shaders Daniil pasted on 2026-08-02 (`design/vfx-chunks/tanh-tonemap.glsl:1`) |
| 2026-09-03 | VFX bench | Orrery v5, the snap-judge-iterate loop proven (`441ea350`) |
| 2026-09-09 | Cockpit | Aurora motion blur and avatar freeze fix landed (`7243003a`); shader-craft skill (`ee3f4f83`) |
| 2026-09-13 | Media suite | Contract approved; First Light (`d8fb56b4`); Play Night (`7e83349b`); the 3D piano for TikTok (`85987153`) |
| 2026-09-14/15 | Piano, jam | Jam space v1 with Asta's Spectacle, Moonwater, harmony modes, replay and conversation (`aaf9ca6f`); procedural instruments (`1cd1ea2c`); looks registry (`79eb5ab6`, 2026-09-16) |
| 2026-09-17 | Piano | "Instruments of light" round (`8a5e37f9`) |
| 2026-09-18 | Piano | Display resolution policy written (`7068dad4`), never wired (section 6.11) |
| 2026-09-20 | Glider | Glide physics GREEN (`96aeb105`) |
| 2026-09-21/22 | Studies | Gyre (`0d0cd33d`, 2026-09-22); the visual quality baseline from "the crystal piano studies, studio integration and Gyre" (`arsenal/VISUAL-QUALITY-BASELINE.md:3`) |
| 2026-09-22 | House-round | Conversation pilot (`arsenal/web/house-round/README.md:23` cites `logs/house-conversation-20260922/`); untracked |
| 2026-09-28 | Presentation | `arsenal/present`: one scene, seven targets, four built (`b6d5559d`) |
| 2026-09-01 (site) | akashiclabs.io | Site live (memory `akashiclabs-site-era.md:8`); aurora hero in "round 1" (`E:\akashiclabs-site`, commit `6605e32`) |
| 2026-10-07 | Studies, NOW PLAYING | Crystal studies, Chord tree, Wind and the flow library enter git in one sweep (`4d7c67b3`); NOW PLAYING designed, nothing built (`docs/library/design/20261007_now-playing-multilayer-live-hook_1328e1.md`, "Nothing is built yet") |
| 2026-10-09/11 | Piano | Crystal grand glass looks and Studio Glass menu (`c24a490c`); under-key light and runes (`ae841229`) |
| 2026-10-12 | Media | `arsenal/media` toolbox and First Light's Edit mode (`9fee42e7`..`1f998580`) |
| 2026-10-12/13 | Story layer, lean light | Live cadence judge (`9d6f29ff`); `lean.js` written, untracked |
| 2026-10-13 | Shader school | Private corpus door (`7c700590`); GLSL module core (`5e127983`) |

---

## 3. The engines: which arcs run on what

| Engine | Arcs on it | Evidence |
| --- | --- | --- |
| **Raw WebGL2, the house template** (`#version 300 es`, `precision highp`, a fullscreen triangle from `gl_VertexID`, no libraries) | Cockpit (aurora bed, avatar, activity line), VFX bench, First Light, Play | Shader-craft floor 1 (`.claude/skills/shader-craft/SKILL.md:38-41`); First Light "Chrome, WebGL2, no libraries" (`arsenal/FIRST-LIGHT-SPEC.md:249`, `310-313`); avatar and activity line vertex shader (`scripts/agent-avatar.js:43`, `scripts/activity-line.js:37`) |
| **three.js r186** as ES modules from jsDelivr, with `three/addons` | `/piano` and every piano module, Gyre, Crystal studies, Chord tree, Wind, Wind tunnel, all piano lab pages | Import maps: `arsenal/web/piano.html:24-25`, `piano-gyre.html:7`, `piano-crystal-studies.html:9`, `piano-chord-tree.html:9`, `piano-wind.html:4`, `piano-wind-tunnel.html:5` |
| **three.js r128** UMD build from cdnjs | The deck's 3D target | `arsenal/present/targets/three_js.py:11-15`, `31-33` |
| **WebGL1, Shadertoy convention** (`mainImage`, `iTime`, `iResolution`) | akashiclabs.io hero | `E:\akashiclabs-site\src\components\AuroraHero.astro:1-6`, `25-27`, `72` |
| **Canvas2D and DOM** | Edit mode timeline and mixer, piano glass overlay, jam deck, house-round, presentation slides and print | `arsenal/web/edit/mixer.js:122`; `arsenal/web/edit/timeline-view.js:23-31`; `arsenal/web/piano/deck.js:1-12`; `arsenal/web/house-round/README.md:3-9` |
| **Server-side ffmpeg / PyAV** | `arsenal/media`, Edit mode render, TikTok verb, First Light analysis | `arsenal/media/README.md:14-17`, `60-62`; `arsenal/FIRST-LIGHT-SPEC.md:216` |
| **No renderer yet** | Glider (physics only), NOW PLAYING (design only) | `arsenal/web/glider/` holds only `physics.js`; NOW PLAYING atom "Nothing is built yet" |

Why two worlds exist at all: the cockpit's rules (raw WebGL2, no three.js, no CDN, never a second GPU context) were
written for the Bifrost console on a machine with an AMD display-driver crash history
(`.claude/skills/shader-craft/SKILL.md:38-41`, `56-64`). On 2026-09-13 Daniel removed those prohibitions **for the
media suite only**: "3js or any 3d renderer we could use should be used if its the best, most stable and most reliable
option" (memory `media-suite-project-2026-09-13.md:15-17`). The Play spec records exactly which floors survived: the
craft floors stay, "Daniel's ruling removed only the cockpit's library and single-context rules"
(`arsenal/PLAY-NIGHT-SPEC.md:53`). So the split is principled, not accidental. It does mean a shared GLSL module has
to compose into two hosts: a raw fragment shader and a three.js `ShaderMaterial` string (Heimdall makes the same point,
`heimdall-unified-module-system-blind-half-b.md:81`).

---

## 4. Arc by arc

Each entry: purpose, status, render tech, params and presets, UI, and what it shares or duplicates.

### 4.1 The cockpit: aurora light bed, agent avatar, activity line

- **Purpose.** The Bifrost console's living background and status display. The bed is "the cockpit's animated light
  bed" behind the glass UI (`scripts/aurora-shader.js:3-5`). The avatar renders each agent's diagnosed state as an
  object: "the signature codebook rendered as an object" (`scripts/agent-avatar.js:3-6`). The activity line shows
  token emission as a waveform with three distinguishable readings, live, flat (measured zero) and dotted (not
  measured) (`scripts/activity-line.js:12-20`).
- **Status.** Live in the console; the oldest and most rule-governed arc. Motion blur and the avatar freeze fix landed
  2026-09-09 (`7243003a`).
- **Render tech.** Raw WebGL2. The bed is a ray-marched glowing medium with three swarms of six emitters and analytic
  trails (`scripts/aurora-shader.js:24-31`), rendered below display resolution on purpose (`aurora-shader.js:507-522`,
  default scale 0.5, never below 0.35), with ping-pong motion blur (`aurora-shader.js:93-103`). The avatar ray-marches
  a geodesic tiling, capped at 48 steps, `powerPreference: 'low-power'`, at most 6 animating at once, with an fps
  watchdog (`scripts/agent-avatar.js:20-35`). The activity line is five sine lines, "the cheapest thing on the page"
  (`scripts/activity-line.js:22-26`).
- **Params and presets.** Code constants plus a few runtime knobs: the bed's `u_speed`, `u_intensity`, `u_motion`
  (`aurora-shader.js:91-93`) and its `setState(0|1|2)` contract (`aurora-shader.js:13-16`); the avatar's identity
  presets `IDENT` lifted "verbatim" from the console's chip gradients (`agent-avatar.js:460-489`) and a style registry
  of two renderers, geodesic and marble (`agent-avatar.js:432`). The bench tunes the avatar's parameter codebook (4.2).
- **UI.** None of its own; the console mounts it through one house pattern: `isSupported()`, `start()`,
  `setState()`, `setRate()`, `destroy()` (`.claude/skills/shader-craft/SKILL.md:42-48`).
- **Shares.** The house template and the "one seam" mount pattern across all three modules (the activity line's header
  says so: `scripts/activity-line.js:28-34`). Colour identity from `design/refs/aurora-glass-tokens.css:46-49`.
- **Duplicates.** Its own noise (two different value-noise families and three `fbm` variants inside the one bed file,
  `aurora-shader.js:105-131`, `176-194`), its own superlinear-then-tanh finish (`aurora-shader.js:302-317`), its own
  blackbody colour table (`aurora-shader.js:133`), and its own swarm palette (`aurora-shader.js:38-43`). A second copy
  of the bed's noise lives in `scripts/bench-aurora.html:76`, `99` (its performance gate, per
  `.claude/skills/shader-craft/SKILL.md:134-135`).

### 4.2 The VFX bench

- **Purpose.** The house's shader workbench: compose chunks, tune the avatar, and let a text-only seat render
  through the open tab. "USE THE BENCH THAT IS ALREADY OPEN" so a command-line render cannot disagree with a clicked
  one (`scripts/vfx_render.py:8-18`).
- **Status.** Built August; dormant on 2026-09-12 (nothing listening on 8787, last used 2026-09-03 for orrery v5:
  `research/in-flight/vfx-system-code-map-2026-09-12.md:5`). Still the documented shader loop
  (`.claude/skills/shader-craft/SKILL.md:120-142`).
- **Render tech.** Raw WebGL2 page `scripts/vfx.html` (2,256 lines), served by `scripts/bifrost_ui.py` at `/vfx`
  (`bifrost_ui.py:817-845`) on port 8787 (`bifrost_ui.py:9`, `1628`). It drives **the same `AgentAvatar` the console
  mounts, "not a copy"** (`scripts/vfx.html:375-379`): the house's one existing example of a shared module with two
  callers.
- **Params and presets.** 31 chunk files in `design/vfx-chunks/`, each with a one-line `//!` JSON header naming kind,
  category, input and output ports, and a craft note (`design/vfx-chunks/hash31.glsl:1`,
  `design/vfx-chunks/tanh-tonemap.glsl:1`, `design/vfx-chunks/orbit-swarm.glsl:1`). (Heimdall's half says 33;
  `ls design/vfx-chunks` gives 31 today.) 20 sketches in `design/vfx-sketches/`. Groups (`design/vfx-groups.json:2-7`,
  one group, "filmic finish"), compositions (`design/vfx-compositions.json`, one, "aurora-plasma"), node graphs
  (`design/vfx-graphs.json`, "blend-demo"), and a preset file that is empty (`design/vfx-presets.json` is 2 bytes).
  The bench's settings bar (`design/vfx-bench.json`) pins it to the orrery sketch.
- **UI.** A three-column page: palette of chunks with thumbnails, a node graph, and a right column of parameters,
  presets, chat with Claude and a technique library (`scripts/vfx.html:255`, `328-372`). Sliders are generated from a
  small spec object `{label, min, max, step}` (`scripts/vfx.html:384-395`).
- **Shares.** The avatar module; chunk lessons are routed into recall-at-action (the 2026-09-12 code map,
  `vfx-system-code-map-2026-09-12.md:16-17`). First Light's shader cites five chunks it reused
  (`arsenal/web/shaders/first-light.meta.json`, `chunks_reused`).
- **Duplicates.** Its own WebM clip recorder (`scripts/vfx.html:1874-1904`); its own preset store
  (`design/vfx-presets.json` through `/vfx/presets`, `vfx.html:563-595`); its uniform list is written out three
  times inside the one page (`vfx.html:786-789`, `1291-1294`, `1572-1575`).

### 4.3 The media suite: First Light, Play, Edit mode, and `arsenal/media`

- **Purpose.** Daniel's Winamp-and-MilkDrop-inspired suite: play media, cut it, run it through shader effects that
  answer to audio and MIDI (memory `media-suite-project-2026-09-13.md:13`). First Light is the first slice: drag a
  clip, it plays through an effect, pulses with its own audio, a KeyLab knob turns the hue, every run is a take
  (`arsenal/FIRST-LIGHT-SPEC.md:6-10`). Play turns it into an instrument with a preset bank, live audio and macro
  knobs (`arsenal/PLAY-NIGHT-SPEC.md:7-10`). Edit mode adds drag-in, trim, mix and render
  (`arsenal/web/edit/editor.js:1-10`). `arsenal/media` is the agents' video toolbox (`arsenal/media/README.md:1-7`).
- **Status.** All four built and tested. First Light and Play 2026-09-13; Edit mode and the toolbox 2026-10-12
  (`1f998580`, `2d719f1b`).
- **Render tech.** Raw WebGL2 in Chrome; hardware video decode; the shader loaded at runtime from
  `arsenal/web/shaders/first-light.frag` with a built-in fallback effect (`arsenal/FIRST-LIGHT-SPEC.md:310-318`;
  the fallback source starts at `arsenal/web/first-light.js:49`). Play renders each preset into its own ping-pong
  pair, half-float when available, with crossfades (`arsenal/PLAY-NIGHT-SPEC.md:124-134`; `arsenal/web/play.js:613-629`).
  Edit mode is DOM and Canvas2D over `<video>` elements, with server-side ffmpeg for the render
  (`arsenal/media/README.md:60`).
- **Params and presets.** First Light: a documented uniform contract (`arsenal/FIRST-LIGHT-SPEC.md:320-335`). Play:
  presets are `.frag` files whose **line 2** is a `//!` JSON header naming up to eight macro knobs `u_k1..u_k8`
  (`arsenal/PLAY-NIGHT-SPEC.md:35-75`, `97`), parsed and checked by `arsenal/presets.py`. Two module manifests
  describe them in the house registry: `arsenal/modules/vfx.first-light-effect.json` and
  `arsenal/modules/vfx.preset-bank.json` (eight `k` params plus pulse, hue, intensity, crossfade). Export presets for
  video live in `arsenal/media/presets.json`.
- **UI.** The patch-bay identity Daniel loved: light and dark token tables, Archivo and JetBrains Mono, a 16:9 stage
  and a collapsible rack with Library, Patch, Map, HUD and Plan panels (`arsenal/FIRST-LIGHT-SPEC.md:251-296`).
  Edit mode adds Media, Inspector, Mixer and Export panels in the same rack (`arsenal/web/edit/editor.js:2-3`).
- **Shares.** The arsenal kernel (timebase, typed graph, plan, take ledger: `arsenal/FIRST-LIGHT-SPEC.md:51-160`);
  the module registry; the patch-bay tokens, which `/piano` copied (`arc-piano-core.md`, table row for `piano.css`)
  and Edit mode reads at runtime (`arsenal/web/edit/timeline-view.js:29-31`, `arsenal/web/edit/mixer.js:102-104`).
  Navi's preset `first-light.frag` is a port of the First Light effect (memory `media-suite-project-2026-09-13.md:59`).
- **Duplicates.** The First Light effect exists twice (`arsenal/web/shaders/first-light.frag` and
  `arsenal/web/presets/first-light.frag`). MIDI access, audio analysis and the slow-frame watchdog are written
  separately in `first-light.js` and `play.js` (sections 6.10, 6.11). Two ffmpeg finders with different search orders
  (`arsenal/media/README.md:62`, `67`).

### 4.4 The piano visualizer core: looks, glass, Studio, story layer, lean light

The sibling report covers this in depth (`arc-piano-core.md`). At the family altitude:

- **Purpose.** A 3D piano for TikTok that shows chords, notes and sheet music (memory
  `media-suite-project-2026-09-13.md:53`), grown into the house's main instrument: practice, jam, theory, story.
- **Status.** Live on 127.0.0.1:8793, the most worked-on surface in the house. `arsenal/web/piano.js` is 5,480 lines
  (`arc-piano-core.md`, file map).
- **Render tech.** three.js r186, Neutral tone mapping at exposure 1.0 (`arsenal/web/piano.js:444`), an
  UnrealBloom pass (`piano.js:478`), an unrecorded 2D glass canvas on top (`arc-piano-core.md`, `glass.js` row).
- **Params and presets.** The looks registry (`arsenal/web/piano/looks/registry.js:107-140`), saved looks with four
  starters and a server copy (`arsenal/web/piano/looks/store.js:1-6`, `arsenal/pianolooks.py`). Colour modes:
  pitch on the circle of fifths, velocity, and mono amber (`registry.js:58`).
- **UI.** Top bar, Studio drawer (Practice and Looks tabs), Atmosphere panel, deck drawer, conversation dock, workbench
  footer. The sibling counts five stores and several surfaces that set the same settings (`arc-piano-core.md`, 6.1
  and 6.4).
- **Story layer and lean light.** Pure modules that draw nothing: the live cadence judge, a rule-for-rule twin of
  `practice._cadence` (`arsenal/web/piano/cadence-live.js:1-20`, committed `9d6f29ff`), and the lean, which decides
  whether a voice leans home and lets `piano.js` paint it on the unrecorded glass
  (`arsenal/web/piano/lean.js:1-12`). `lean.js` records Daniel's 2026-10-13 answer to the story layer's gate
  question, "can you enable the lean visualization thing" (`lean.js:7`). It is **untracked** (`git status`).
- **Shares.** Theory helpers used across arcs: `spell.js` (Chord tree uses it: `arsenal/web/piano/CHORD-TREE.md`,
  "Controls and rendering"), `nashville.js` (the jam deck imports it: `arsenal/web/piano/deck.js:27`),
  `harmony-feel.js` and `moment.js` for every light instrument (commits `91a237c5`, `7f2ece9f`).
- **Duplicates.** See the sibling's section 9; at the family level, the piano is the source of the five lab forks
  (6.15) and of most of the colour duplication (6.1a).

### 4.5 Spectacle and Moonwater (the piano's atmosphere)

- **Purpose.** Worlds, weather, particles and water around the keys, drawn into the recorded canvas
  (`arsenal/SPECTACLE.md:1-6`). Moonwater is the lake world with a planar reflection of the real keyboard
  (`SPECTACLE.md:8-16`).
- **Status.** Landed 2026-09-15 in the jam integration (`aaf9ca6f`); Asta's build (memory
  `media-suite-project-2026-09-13.md:132`).
- **Render tech.** three.js `ShaderMaterial`s with inline GLSL concatenated from prefix strings
  (`arsenal/web/piano/moonwater.js:6-16`; `arsenal/web/piano/spectacle.js:21-22`).
- **Params and presets.** Six themes (`spectacle.js:11`), fixed quality tiers with internal sizes and particle counts
  (`spectacle.js:19`), and its own browser storage key `arsenal.piano.spectacle` (`spectacle.js:20`, `309`).
- **UI.** Its own Atmosphere panel with hand-written `<select>` and range inputs (`spectacle.js:336-347`).
- **Duplicates.** The panel hand-codes the same weather choices the looks registry declares (`spectacle.js:340` and
  `looks/registry.js:128-131`). Its noise exists three ways: `spectacle.js:21` (a sine-free float hash),
  `spectacle-worlds.js:51-53` (sine hash, value noise, `fbm`), and `moonwater.js:7-11` (a sine-free `hash31`, a 3D
  value noise and a three-octave `mistNoise`).

### 4.6 The instruments: procedural models, the Crystal grand, Instruments of light

- **Purpose.** The body around the keys: six procedural models (KeyLab 88 mk3, concert grand, upright, suitcase EP,
  vintage synth, crystal grand) (`1cd1ea2c`), four "Instruments of light" from the house round (`8a5e37f9`), and the
  three crystal studies promoted into the slot (`arsenal/web/piano/instruments/catalog.js:38-51`).
- **Status.** All registered in the Instrument menu (`catalog.js:38-51`). The Crystal grand gained glass looks, a
  Studio Glass menu (`c24a490c`), and an under-key velocity glow with runes (`ae841229`).
- **Render tech.** three.js modules behind the instrument contract (`arsenal/PIANO-V2-SPEC.md:48-87`; the sibling's
  "M. Plug-in contracts").
- **Shares.** The host's `ctx.noteColor` when it is offered.
- **Duplicates.** Every instrument carries its own fallback pitch colour in case the host does not offer one
  (`instruments/concert-grand.js:1159`, `instruments/glass-piano.js:1933`, `instruments/light-kimi-aurora.js:112`,
  `instruments/light-vandor-abyssal.js:639`, `instruments/light-vandor-ornithopter.js:573`). Ornithopter carries its
  own sine hash (`light-vandor-ornithopter.js:180`). Five soft point-sprite glow profiles live in the light
  instruments and schemes (section 6.3).

### 4.7 Gyre

- **Purpose.** "A standalone light sculpture with seven starting studies, a browser preset library and optional
  MIDI-driven shaping. It does not produce sound or listen to audio" (`arsenal/web/piano/GYRE.md:7`). Born from a
  drill hanging on a string (`0d0cd33d`).
- **Status.** Built 2026-09-22; Daniel's favourite recipes preserved in
  `arsenal/visual-references/2026-09-21/gyre-recipes.json` (`arsenal/VISUAL-QUALITY-BASELINE.md:43-52`).
- **Render tech.** three.js r186, ACES tone mapping at exposure 1.15 (`arsenal/web/piano-gyre.js:37`), no
  full-screen bloom ("Gyre achieves its look without a full-screen bloom pass", `VISUAL-QUALITY-BASELINE.md`,
  approach 5), its own GLSL sine hash and 1D noise (`piano-gyre.js:118-119`).
- **Params and presets.** The richest preset system outside the piano: versioned browser storage
  `piano.gyre.presets.v1` with full validation of ranges, choices, camera and flight state
  (`arsenal/web/piano/gyre-presets.mjs:5-41`). Five named palettes, tide, prism, ember, violet and opal
  (`piano-gyre.js:73`).
- **UI.** 22 range sliders written into the HTML (`grep` count in `arsenal/web/piano-gyre.html`); the sibling calls
  this the shared four-page shell "written four times" (`arc-piano-studies.md`, "Page shell and UI").
- **Duplicates.** Within the one arc, the palette list is written three times (`piano-gyre.js:23`, `piano-gyre.js:73`,
  `gyre-presets.mjs:7`). Its MIDI input is its own (`arsenal/web/piano/gyre-music.js:15-16`).

### 4.8 Crystal studies: Aether, Solstice, Nocturne

- **Purpose.** A look-development gallery for three glass piano forms (`arsenal/web/piano/CRYSTAL-STUDIES.md:1-12`),
  each with 352 instanced soft fireflies (`CRYSTAL-STUDIES.md:14`).
- **Status.** In git since `4d7c67b3` (2026-10-07). **Promoted**: the same sculptures are instruments in `/piano`
  through a 20-line adapter that hands them the host's note clock and render loop
  (`arsenal/web/piano/instruments/crystal-study.js:1-15`). This is the one place a study became a module.
- **Render tech.** three.js r186, Neutral tone mapping at exposure 1.08 (`arsenal/web/piano-crystal-studies.js:26`),
  UnrealBloom with its own settings (`piano-crystal-studies.js:82`). Solstice's overhead light is a 3x12 grid of
  pitch-class energies read by a diffuser material (`arsenal/web/piano/solstice-signals.mjs:6-10`,
  `solstice-canopy.js:5-8`).
- **Params and presets.** Query parameters only: `study=`, `resolution=`, `canopy=` (`CRYSTAL-STUDIES.md:3`); "does
  not ... register saved looks" (`CRYSTAL-STUDIES.md:5`).
- **Duplicates.** Its own pitch-colour table, a lerp between two colours ordered by fifths
  (`piano-crystal-studies.js:93-99`), and its own MIDI (`piano-crystal-studies.js:286-288`).

### 4.9 Chord tree ("Arbor")

- **Purpose.** A 3D chord builder: the trunk and limbs are one chord family, intervals are lighter shades of the
  root's hue (`arsenal/web/piano/CHORD-TREE.md:1-12`). Not connected to MIDI yet (`CHORD-TREE.md:3`).
- **Render tech.** three.js r186, ACES at exposure 1.08 (`arsenal/web/piano-chord-tree.js:30`), bloom
  (`piano-chord-tree.js:61`), OrbitControls (`piano-chord-tree.js:35-36`).
- **Params.** Root picker and extension switches; colour by root from a fifths wheel offset by 38 degrees
  (`arsenal/web/piano/chord-tree-model.mjs:7`), shaded by interval role (`piano-chord-tree.js:64`).
- **Shares.** `spell.js` (`CHORD-TREE.md`, "Controls and rendering"). **Duplicates.** Its own hue wheel, which
  starts at a different angle from `/piano`'s (6.1a).

### 4.10 Wind ("Violet Aero") and the wind tunnel; the flow library

- **Purpose.** Violet light flowing around a concept car; the tunnel evolves it into a small 3D fluid study
  (`arsenal/web/piano/WIND.md:1-12`). The solver, distance volume, forces and streamline tracing are a reusable
  library with their own README (`arsenal/web/lib/flow/README.md`).
- **Render tech.** three.js r186, ACES at exposure 1.12 (`arsenal/web/piano-wind.js:19-20`), a worker that owns
  simulation time (`WIND.md:8-10`).
- **Params and takes.** 4 sliders on the wind page and 6 on the tunnel (grep counts). Its own take system: flow clips
  recorded and replayed, stored in IndexedDB as `violet-flow-takes`
  (`arsenal/web/piano/flow-take-store.mjs:3`; controller `flow-take-controller.mjs:1-25`).
- **Shares.** The flow library is written renderer-neutral, and `arsenal/present/scene.py` cites "the flow-lib rule"
  as its model for staying renderer-blind (`arsenal/present/scene.py:3-5`): a methodology export across arcs.
- **Duplicates.** A fourth "take" concept (6.8).

### 4.11 The jam

- **Purpose.** Claude's backing band and a deck of concept cards beside the piano: cards, runs and a tempo map on the
  server (`arsenal/jam/__init__.py:1-10`), a drawer of cards on the page (`arsenal/web/piano/deck.js:1-12`), and a pure
  groove generator that produces the same events in the browser and under node (`arsenal/web/piano/groove.js:1-8`).
- **Status.** Landed 2026-09-15 (`aaf9ca6f`).
- **Visual relation.** The jam draws almost nothing itself. It hands ghost keys to the piano through a page hook
  (`deck.js:22`, `onGhosts`) and stays outside the recorded canvas (`deck.js:1-2`, `10-12`).
- **Shares.** The **twin with a parity pin** pattern: `tempomap.py` and `arsenal/web/piano/tempomap.js` run the same
  fixture file (`arsenal/jam/__init__.py:6-8`). Imports `nashville.js` (`deck.js:27`).
- **Duplicates.** Its own atomic file-store pattern (`arsenal/jam/cards.py:1-12`), which mirrors the looks store and
  the performance store **(inferred from the docstrings: "as PerformanceStore does", `cards.py:9`)**.

### 4.12 NOW PLAYING and the presentation family

- **NOW PLAYING.** Design only. Spotify now-playing on `/piano`, palette bleed from the album cover, an artist-lore
  theme, cited facts at musical moments, Claude as co-performer, 16 slices
  (`docs/library/design/20261007_now-playing-multilayer-live-hook_1328e1.md`, header and "Status"). Its companion
  atom on presentation grammar (`docs/library/design/20261007_presentation-grammar-screens-scenes_236d39.md`) treats
  screens as sources by treatments by placements (memory `media-suite-project-2026-09-13.md:378-382`). Nothing to
  unify yet; it is the largest future consumer of a shared palette module ("palette bleed").
- **`arsenal/present`.** One renderer-neutral scene format (`present.scene.v1`) and targets: HTML slides, a UI
  element, print, and a three.js gallery (`arsenal/present/scene.py:1-25`; `arsenal/present/targets/__init__.py:14`).
  Registered as `present.*` manifests in the same registry as the media modules (memory
  `presentation-primitive-family.md:13`).
- **Render tech.** HTML and CSS for slides; three.js **r128** UMD for the 3D target, every slide a textured plane
  (`arsenal/present/targets/three_js.py:1-15`).
- **Params and presets.** A token family by role: palette, type sizes, two font faces (IBM Plex Sans and JetBrains
  Mono) (`arsenal/present/targets/_core.py:24-36`), overridable per deck.
- **Duplicates.** A tenth colour system and a fourth font system (6.1c); a second three.js version (6.13).

### 4.13 House-round (conversation pilot)

- **Purpose.** A read-only reader that makes a selected house discussion navigable while keeping bodies,
  disagreements and provenance distinct (`arsenal/web/house-round/README.md:3`).
- **Status.** An uncommitted experiment by Codex, "not a replacement inbox" (`README.md:19-23`). **Untracked.**
- **Render tech.** DOM; a pure shared model used by both the page and a CLI (`README.md:9`).
- **Duplicates.** Its own token set (`--lavender`, `--mint`) in one line of CSS
  (`arsenal/web/house-round/style.css:1`). Pattern worth keeping: the page and the CLI share one pure model.

### 4.14 Glider

- **Purpose.** A glide-feel game prototype (Glyder 2 meets Sky, with Wipeout speed) (`cc6eab61`; brief
  `research/in-flight/glider-prototype-2026-09-20/brief.md`).
- **Status.** Physics only, pinned in node before any pixel: point-mass glide, stall as a lift drop, parabolic
  thermals (`arsenal/web/glider/physics.js:1-19`); "every constant lives in DEFAULTS" so pickups can swap the wing
  (`physics.js:13-16`). The brief's acceptance asks for 60 fps and a legible frame (`brief.md:109`). No renderer
  exists **(inferred from `arsenal/web/glider/` holding only `physics.js`)**.
- **Relation.** It shares nothing visual yet. It is the cleanest example of "params as data" in the house and the
  first arc that will need a game camera and a sky, both of which already exist in four other places (6.9, 6.14).

### 4.15 akashiclabs.io

- **Purpose.** The public lab site, built from library atoms (memory `akashiclabs-site-era.md:8`).
- **Render tech.** Astro; one WebGL1 hero, `AuroraHero.astro`, written in the Shadertoy convention so "this same
  engine seeds the shaders playground later" (`E:\akashiclabs-site\src\components\AuroraHero.astro:1-6`). DPR capped,
  paused when hidden, a still frame under reduced motion (`AuroraHero.astro:3-6`).
- **Params.** Hard-coded: "house preset 01 'curtains'", three curtains in green, sky blue and violet
  (`AuroraHero.astro:28`, `52-55`).
- **Duplicates.** A fresh sine hash, value noise and `fbm` (`AuroraHero.astro:29-36`). Its palette differs from the
  cockpit's aurora (cockpit swarms are periwinkle, violet and coral: `scripts/aurora-shader.js:38-43`), and its page
  tokens (`E:\akashiclabs-site\src\layouts\Base.astro:16-26`, `--aurora-a: #4ade80`, `--aurora-b: #38bdf8`) are a
  third aurora palette. Whether the site hero was adapted from the cockpit bed is **(inferred: the commit says "glass
  and glow language from the console", `6605e32`; the code is not a copy)**.

### 4.16 The lab forks: `piano-next.js` and `piano-lab-*.js`

- **What they are.** Five full copies of an older `piano.js`, used for judging and testing: `piano-next.js` (1,978
  lines), `piano-lab-res.js` (2,276), `piano-lab-judge-res.js` (2,277), `piano-lab-judge-head.js` (1,880),
  `piano-lab-vfx.js` (2,446). Each opens with the same header, "Piano — arsenal/web/piano.js (ES module)"
  (`arsenal/web/piano-lab-res.js:1`, `arsenal/web/piano-lab-vfx.js:1`).
- **How close.** `piano-lab-judge-res.js` differs from `piano-lab-res.js` in 7 lines; `piano-lab-judge-head.js` in
  448; `piano-lab-vfx.js` in 1,026; `piano-next.js` in 1,476 (`diff | grep -c '^[<>]'`). `piano-next.js` and today's
  `piano.js` differ in 4,846 lines.
- **Tracked?** Four of the five are untracked (`git status`: `piano-lab-res.js`, `piano-lab-judge-res.js`,
  `piano-lab-judge-head.js`, `piano-lab-vfx.js`). `PIANO-V2-SPEC.md:26` explains why `piano-next` exists: Daniel's
  page stays untouched and a new core is built beside it.
- **Why it matters.** These are about 10,800 lines that carry their own copy of the tone mapping and bloom
  (`piano-lab-res.js:398`, `583`, and so on) and every helper. A module change will not reach them, and the judging
  harnesses that depend on them will silently judge the old code **(inferred)**.

### 4.17 Shader school (tonight) and the module core

- **Corpus.** 336 Shadertoy shaders, private and gitignored, under `state/arsenal/shaders/corpus/`, with a door
  `py -m arsenal shader list|show|missing|ingest` (`arsenal/shaders/cli.py:1-10`; memory
  `shader-school-2026-10-13.md:18-20`).
- **Module core.** `arsenal/shaders/modules.py` (committed `5e127983`): a module is a `.glsl` file whose leading `//!`
  lines are one JSON header, the bench's chunk format extended to several lines (`modules.py:10-15`). Dependencies are
  read from the code (a function you call is a module you need) and from an explicit `needs` list
  (`modules.py:17-19`). Composition is a deterministic topological sort, and the browser twin must produce
  byte-identical text (`modules.py:21-24`). Each module becomes an `arsenal.module/v0` manifest with a `shader` block,
  so GLSL modules sit in the same registry as media and present modules (`modules.py:26-27`;
  `arsenal/__init__.py:9-11`).
- **What is plugged in.** The house library folder holds only the composer (`arsenal/web/glsl/` lists `modlib.js`); the
  core reads `design/vfx-chunks/` in place as its legacy source (`modules.py:38-41`). No live surface imports a module
  yet **(inferred from Heimdall's census, `heimdall-unified-module-system-blind-half-b.md:26`, and from the greps in
  section 6.2, which still find every inline copy)**.
- **Lab runtime.** A Shadertoy-style toy runtime and a headless harness are being built
  (`arsenal/web/shaderlab/toy-runtime.js`, `arsenal/shaders/headless.mjs`, `render.py`, `serve.py`), served on port
  8797, which refuses Daniel's 8793 outright (`arsenal/shaders/serve.py:39-40`). These are **untracked**.

---

## 5. How the arcs relate

### 5.1 Lineage (who grew out of whom)

```
 design/vfx-chunks (Aug)  ──reused──▶ first-light.frag (Sep 13) ──ported──▶ presets/first-light.frag (Play)
        │                                    │
        │                                    └── First Light page ──▶ Play ──▶ Edit mode (Oct 12)
        │                                                 │
        │                                                 └── "piano detour" (PLAY-NIGHT-SPEC.md:221) ──▶ /piano
        │                                                                                                  │
 cockpit aurora bed ──(language, not code)──▶ akashiclabs AuroraHero                                       │
 cockpit avatar ──same object──▶ VFX bench                                                                 │
                                                                                                           ▼
   /piano ──fork──▶ piano-next, piano-lab-* (5 copies)        /piano ──contracts──▶ schemes, instruments, Spectacle
   /piano ──patterns──▶ studies: Gyre, Crystal, Chord tree, Wind ──promoted──▶ instruments (aether, solstice, nocturne)
   /piano ──hooks──▶ jam deck (ghost keys), story layer, lean light
   flow library rule ──▶ arsenal/present scene format (renderer-blind)
```

Evidence for each edge: chunk reuse (`arsenal/web/shaders/first-light.meta.json`, `chunks_reused`); Navi's port
(memory `media-suite-project-2026-09-13.md:59`); the piano detour (`arsenal/PLAY-NIGHT-SPEC.md:221`); Edit mode inside
First Light (`arsenal/web/edit/editor.js:2-4`); the bench drives the console's avatar (`scripts/vfx.html:375-379`);
the forks' shared header (4.16); studies promoted (`instruments/crystal-study.js:4-5`); deck ghosts (`deck.js:9`, `22`);
present cites the flow-lib rule (`arsenal/present/scene.py:3-5`).

### 5.2 Organs that genuinely are shared today

- **The arsenal kernel and registry.** Timebase, typed graph, plan and take ledger, and `arsenal.module/v0` manifests,
  32 of them now covering browser, ffmpeg, media, present, vfx, Web Audio and Web MIDI modules (`ls arsenal/modules`;
  validator `arsenal/registry.py:21-40`).
- **Music theory.** `spell.js`, `nashville.js`, `harmony-feel.js`, `moment.js` serve the piano, its instruments, the
  Chord tree and the jam deck (4.4, 4.9, 4.11).
- **The GPU render lock.** `arsenal/lanes/gpu_lock.mjs`, adopted by the jam and Chrome verification lanes
  (`166d97b1`; protocol `arsenal/GPU-LOCK.md`).
- **The avatar**, shared by console and bench (4.2).
- **The instrument contract**, which already hosts the crystal studies (4.8).

### 5.3 Methods the house has proven, each in one place

| Pattern | Where it is proven | What it would buy everywhere |
| --- | --- | --- |
| Twin with a parity pin | Jam tempo map (`arsenal/jam/__init__.py:6-8`); cadence judge (`cadence-live.js:17-20`); module core (`modules.py:21-24`); groove under node (`groove.js:3-4`) | Python tools and pages that cannot disagree |
| Pure module and host | `lean.js:1-12`; `cadence-live.js:1-12`; `crystal-performance.mjs:1-3`; `solstice-signals.mjs:6-10` | Music-to-light signals written once, tested in node |
| One seam, house mount pattern | Cockpit modules (`.claude/skills/shader-craft/SKILL.md:42-48`) | One mount contract for every visual module |
| Slot contract with a fuse | Schemes and instruments (`PIANO-V2-SPEC.md:48-87`; `arc-piano-core.md`, section 0) | Swappable stages in every page |
| Settings as data, UI generated | Looks registry and Studio (`looks/registry.js:1-23`; `studio.js:31`, `66`) | Heimdall's "the UI is GENERATED from the manifest" (`heimdall-...-half-b.md:60`) |
| Machined floor, crafted ceiling | Shader-craft (`SKILL.md:8-11`); the press family (`c87e497c`) | Blind-checkable rules plus Daniel's taste gate |
| Render, then a number beside the image, then a pin | Bench loop (`SKILL.md:120-142`); visual quality baseline workflow (`VISUAL-QUALITY-BASELINE.md:56-66`) | One verification method across arcs |
| Blind panels and bake-offs | Synthesia bake-off (`26e0d012`); Instruments of light (`8a5e37f9`) | A repeatable way to choose between looks |

---

## 6. The duplication map

Each row is one concept, with every implementation I found. "Lab forks" (4.16) are excluded from counts unless
noted, because each of them duplicates everything.

### 6.1 Colour

**(a) A note's colour from its pitch, walking the circle of fifths.** At least nine implementations, and they do not
agree on the starting angle or the saturation:

| File:line | Variant |
| --- | --- |
| `arsenal/web/piano.js:322-326`, `349`, `380` | The canonical one: `fifthsIndex = (pc * 7) % 12`, hue `(200 + 30 * fifthsIndex) % 360` (starts at 200 degrees), cached per pitch class and velocity |
| `arsenal/web/piano/chord-tree-model.mjs:7` | Starts at 38 degrees, 30 degrees per step: the same C is a different colour here than on `/piano` |
| `arsenal/web/piano/harmonic-voices.js:75` | `fifthIndex(midi)/12` as a hue |
| `arsenal/web/piano/instruments/concert-grand.js:1159` | Fallback HSL starting at 0 degrees, saturation 0.9, lightness 0.5 |
| `arsenal/web/piano/instruments/glass-piano.js:1933` | Fallback, same numbers |
| `arsenal/web/piano/instruments/light-kimi-aurora.js:112` | Fallback, saturation 0.92, lightness 0.56 |
| `arsenal/web/piano/instruments/light-vandor-abyssal.js:639` | Fallback, 0.9 / 0.5 |
| `arsenal/web/piano/instruments/light-vandor-ornithopter.js:573` | Fallback, 0.9 / 0.5 |
| `arsenal/web/piano-crystal-studies.js:93-99` | A lerp between two colours ordered by fifths |
| `arsenal/web/piano.js:2904` | The replay's own variant "at 55% saturation" |
| `arsenal/web/piano/instruments/glass-piano.js:1163` (title text) and `arsenal/web/piano/moonwater.js:136` | The Steiner tone-zodiac reading and Moonwater's fifth glyphs: the same wheel as content |

**(b) Named palettes.** Each arc invented its own, with no shared register:

| Palette set | Where |
| --- | --- |
| Gyre: tide, prism, ember, violet, opal | `arsenal/web/piano-gyre.js:73` |
| Spectacle themes: moon, ember, nebula, winter, rain, city | `arsenal/web/piano/spectacle.js:11`; also `looks/registry.js:125-126` |
| Agent identities | `scripts/agent-avatar.js:460-489`, lifted from `design/refs/aurora-glass-tokens.css:46-49` |
| Cockpit swarm colours | `scripts/aurora-shader.js:38-43` |
| Cockpit blackbody colour table | `scripts/aurora-shader.js:133` |
| Activity line tint `#0381fe` | `scripts/activity-line.js:137` |
| Site curtains: green, sky blue, violet | `AuroraHero.astro:52-55` |
| Piano colour modes: pitch, velocity, mono amber | `arsenal/web/piano/looks/registry.js:58` |
| Bench chunk `identity-wash`, `channel-rotate` | `design/vfx-chunks/` |

The word "ember" means three different things: a Spectacle world (`registry.js:125`), a Gyre palette
(`piano-gyre.js:73`) and a Gyre preset (`arsenal/web/piano/gyre-motion.mjs:7`).

**(c) Page colours and fonts (design tokens).** At least ten systems:

| Token system | Where | Fonts |
| --- | --- | --- |
| Cockpit glass | `design/refs/aurora-glass-tokens.css:36-53`, roles `150-153` | SF Pro / Segoe / Inter, SF Mono / JetBrains Mono |
| Design contract spacing, type and role tokens | `design/CONTRACT.md:44-66` | 13px body on a 1.25 ratio |
| First Light patch bay | `arsenal/FIRST-LIGHT-SPEC.md:255-280`; `arsenal/web/first-light.css:9` (25 tokens) | Archivo, JetBrains Mono |
| Play | `arsenal/web/play.css:9` (22 tokens, same ground) | (inferred: same as First Light) |
| Piano | `arsenal/web/piano.css:8` (13 tokens, "copied from First Light" per `arc-piano-core.md`) | |
| Piano workbench | `arsenal/web/piano/workbench.css:3` (its own `--ground:#080d12`) | |
| Edit mode | reads First Light's tokens at runtime with hard-coded fallbacks (`arsenal/web/edit/timeline-view.js:29-31`) | |
| Study pages | one-line `:root` each: `piano-gyre.css:2`, `piano-crystal-studies.css:2`, `piano-chord-tree.css:2` | DM Sans |
| Report kit | `design/report-kit.css:25` (18 tokens) | |
| Presentation family | `arsenal/present/targets/_core.py:24-36` | IBM Plex Sans, JetBrains Mono |
| House-round | `arsenal/web/house-round/style.css:1` | Segoe UI |
| Site | `E:\akashiclabs-site\src\layouts\Base.astro:16-31` | system serif and sans |

Daniel's chord-lettering picks (Outfit, Raleway, Jost; memory `media-suite-project-2026-09-13.md:184-186`) are a
fifth font decision that lives in no token file.

### 6.2 Noise and hashing

| Concept | Implementations |
| --- | --- |
| The sine hash (`fract(sin(dot(...)) * 43758.5453)`) | 18 files in this repo: `scripts/aurora-shader.js` (3), `scripts/agent-avatar.js` (2), `scripts/bench-aurora.html` (2), `arsenal/web/piano-gyre.js:118`, `arsenal/web/piano/spectacle-worlds.js:51`, `arsenal/web/piano/instruments/light-vandor-ornithopter.js` (a variant, `:180`), `arsenal/web/shaders/first-light.frag:19`, `arsenal/web/presets/{first-light,chromatic-bloom,feedback-tunnel}.frag:31-33`, `design/vfx-chunks/{hash31,orbit-swarm,triangular-dither}.glsl`, `design/vfx-sketches/{aurora-bus,daniil-curtains,fibcore,fibshell,orrery}.frag`; plus `AuroraHero.astro:29` on the site |
| Sine-free hashes | `arsenal/web/piano/moonwater.js:7` (named `hash31`), `arsenal/web/piano/spectacle.js:21`, `arsenal/web/presets/glitch-blocks.frag:27`, `halftone-pop.frag:28` |
| Value noise | `aurora-shader.js:180-190`, `spectacle-worlds.js:52`, `moonwater.js:8`, `piano-gyre.js:119` (1D), `design/vfx-chunks/value-noise-3d.glsl`, `AuroraHero.astro:30-33` |
| Gradient noise | `aurora-shader.js:105-120` |
| Fractal noise (`fbm`) | `aurora-shader.js:123`, `194`; `agent-avatar.js:340`; `bench-aurora.html:76`, `99`; `spectacle-worlds.js:53`; `moonwater.js:11` (`mistNoise`); `design/vfx-chunks/value-noise-3d.glsl:7`; `design/vfx-sketches/aurora-bus.frag:73`, `daniil-curtains.frag:76`, `daniil-snowfield.frag:92`, `124`; `AuroraHero.astro:36` |

**A landmine for the module core.** `moonwater.js:7` defines a function named `hash31` with sine-free arithmetic,
while the bench chunk `hash31` (`design/vfx-chunks/hash31.glsl:2`) defines `h31` with the sine hash. The core resolves
dependencies by function name (`arsenal/shaders/modules.py:17-19`), so a naive extraction of Moonwater's noise would
either collide or silently swap the maths. The chunk's own note says its hash is "not good enough for anything that
must not band" (`hash31.glsl:1`).

### 6.3 Glow and bloom

| Form | Where |
| --- | --- |
| three.js UnrealBloom pass, with different settings each time | `piano.js:478` (0.45, 0.0, 0.9), `piano-chord-tree.js:61` (0.35, 0.5, 0.95), `piano-crystal-studies.js:82` (0.3, 0.35, 1.1), `piano-lab-instruments.js:127`, schemes `upright-roll.js`, `synth-heimdall.js`, `synth-navi.js` (grep), and every lab fork |
| Soft point-sprite profiles (`gl_PointCoord`) | 13 files: `piano.js`, `piano-gyre.js`, `piano-wind.js`, `spectacle.js` (3), `spectacle-worlds.js`, `moonwater.js`, `schemes/{neon-trails,synth-heimdall,synth-vandor,upright-roll}.js`, `instruments/{light-deepseek-orrery,light-vandor-abyssal,light-vandor-ornithopter}.js` |
| Additive blending | 21 files under `arsenal/web` (grep for `AdditiveBlending`, excluding forks) |
| Ray-marched glow (light accumulated along a ray) | `scripts/aurora-shader.js` (the medium), `scripts/agent-avatar.js` |
| Named glow helpers in sketches | `design/vfx-sketches/aurora-bus.frag:77`, `daniil-snowfield.frag:68`, `orrery.frag:89` |
| No bloom on purpose | Gyre (`VISUAL-QUALITY-BASELINE.md`, approach 5) |

### 6.4 Tone mapping and the finishing chain (tone, vignette, dither, hue rotation)

Tone mapping is how a renderer squeezes unlimited light into the screen's 0-to-1 range without flat white blobs.

| Family | Where |
| --- | --- |
| The `tanh` shoulder (raw WebGL2 surfaces), after a superlinear highlight | `scripts/aurora-shader.js:302-307`; `arsenal/web/shaders/first-light.frag:103`; chunk `design/vfx-chunks/tanh-tonemap.glsl`; the bench group "filmic finish" (`design/vfx-groups.json:2-7`) |
| A lifted-floor film curve | chunk `design/vfx-chunks/filmic-curve.glsl:1-3` (its note: pick this or a true black, not both) |
| three.js Neutral | `piano.js:444` (exposure 1.0), `piano-crystal-studies.js:26` (1.08), `piano-lab-instruments.js:101` (1.0), every lab fork |
| three.js ACES Filmic | `piano-chord-tree.js:30` (1.08), `piano-gyre.js:37` (1.15), `piano-wind.js:20` (1.12) |

So the piano and the crystal studies, which now render the same Aether, Solstice and Nocturne sculptures, use the
same curve at different exposures, and the three other studies use a different curve again.

| Finishing step | Where |
| --- | --- |
| Vignette (darkened corners) | chunk `vignette-cubic.glsl`; `aurora-shader.js:309`; `first-light.frag`; presets `feedback-tunnel.frag`, `first-light.frag`, `glitch-blocks.frag`; `piano-crystal-studies.html` (a CSS vignette, inferred from the grep hit) |
| Dither (tiny noise that hides colour banding) | chunk `triangular-dither.glsl`; `aurora-shader.js` (march jitter instead, `:317`); `first-light.frag`; `play.js` |
| Hue rotation through HSV | `first-light.js`, `play.js`, all 8 presets, `shaders/first-light.frag`, `agent-avatar.js` (grep `rgb2hsv|hsv2rgb`); First Light's meta records why the chunk `channel-rotate` was not used (`first-light.meta.json`, `chunks_deliberately_not_reused`) |

### 6.5 Feedback and history buffers (frames that remember the last frame)

`scripts/aurora-shader.js:101-103` (`u_history` ping-pong); `arsenal/web/play.js` (`u_prev`, a pair per preset,
`PLAY-NIGHT-SPEC.md:128-131`); 5 presets that read `u_prev`; three.js render targets in `piano.js`,
`piano-chord-tree.js`, `piano-crystal-studies.js`, `instruments/glass-piano.js` (grep `WebGLRenderTarget`); Gyre and
Wind keep light history as geometry, not as a texture (the sibling's "C. Light history", `arc-piano-studies.md`).
Three different rules for clearing history exist: the cockpit's floor 7 (`SKILL.md:82-86`), Play's "cleared ... on
resize, and on an epoch bump" (`PLAY-NIGHT-SPEC.md:83`), and Play's 8-bit fade rule (`PLAY-NIGHT-SPEC.md:112`).

### 6.6 Presets and settings stores

| Store | Format and location |
| --- | --- |
| Bench presets | `design/vfx-presets.json` via `/vfx/presets` (`scripts/vfx.html:563-595`); empty file |
| Bench groups, compositions, graphs | `design/vfx-groups.json`, `vfx-compositions.json`, `vfx-graphs.json` |
| Bench chunk headers | one-line `//!` JSON on line 1 (`design/vfx-chunks/*.glsl:1`) |
| Play presets | `//!` JSON on **line 2**, after `#version` (`arsenal/PLAY-NIGHT-SPEC.md:37-48`), parsed by `arsenal/presets.py` |
| Module manifests | `arsenal/modules/*.json`, `arsenal.module/v0` (`arsenal/registry.py:21-40`) |
| GLSL modules (tonight) | multi-line `//!` header, `arsenal.glsl-module/v1` (`arsenal/shaders/modules.py:10-15`; `arsenal/__init__.py:11`) |
| Piano looks | descriptor registry plus server store `state/arsenal/looks` and browser cache `arsenal.piano.looks.cache` (`looks/registry.js`, `looks/store.js:1-21`, `arsenal/pianolooks.py`) |
| Spectacle | `localStorage` `arsenal.piano.spectacle` (`spectacle.js:20`, `309`) |
| Piano instrument options, Studio | `arsenal.piano.instrument-options` (`piano.js:1297`), `arsenal.piano.studio` (`studio/studio.js:49`) |
| Gyre | `piano.gyre.presets.v1`, validated, versioned (`gyre-presets.mjs:5-41`); recipes in `arsenal/visual-references/2026-09-21/gyre-recipes.json` |
| Crystal studies | URL query only (`CRYSTAL-STUDIES.md:3`) |
| First Light, Play | MIDI maps and audio choice in `localStorage` (`first-light.js:15-16`; `play.js:23-24`) |
| Edit mode | `arsenal.edit.project`, `arsenal.edit.preset` (`edit/editor.js:23`, `edit/render.js:12`) |
| Video export | `arsenal/media/presets.json` |
| Presentation | per-deck `tokens` over family defaults (`arsenal/present/targets/_core.py:68-82`) |
| Glider | `DEFAULTS` object (`arsenal/web/glider/physics.js:20-28`) |

The `//!` header is the closest thing to a common language: the bench, Play and the module core all use it, at line 1,
line 2 and multi-line respectively. Heimdall's half proposes promoting it to the contract
(`heimdall-unified-module-system-blind-half-b.md:58`); the module core has done that for line-1 and multi-line headers
(`modules.py:10-15`). Whether it accepts Play's line-2 header is **(not read: I did not open `parse_header` in
`modules.py`)**.

### 6.7 Sliders and control builders

| Builder | Where |
| --- | --- |
| Spec-driven slider factory | `scripts/vfx.html:384-395` |
| Play macro knobs built in code | `arsenal/web/play.js:2274-2284` |
| Spectacle panel, hand-written HTML | `arsenal/web/piano/spectacle.js:336-347` |
| Studio Looks tab, generated from the registry | `arsenal/web/piano/studio/studio.js:31`, `66` |
| Edit mixer faders built in code | `arsenal/web/edit/mixer.js:35` |
| Static range inputs in HTML | `piano-gyre.html` (22), `piano-wind-tunnel.html` (6), `piano-wind.html` (4), `piano.html` (2), `piano-metronome.html` (2), `first-light.html` (1), `play.html` (1), `replay.html` (1) |
| Jam deck controls | `arsenal/web/piano/deck.js` (2 range inputs) |

Only one of these (the Studio) is generated from a description of the setting. The visual quality baseline asks for
exactly what a generator would enforce: "a small set of understandable controls", "discoverable reset and true
pause" (`VISUAL-QUALITY-BASELINE.md:15`, approach 7).

### 6.8 Recorders, takes and capture

| Thing | Where | State |
| --- | --- | --- |
| Piano REC: MediaRecorder on `canvas.captureStream(0)` with its own 60 fps pacer | `arsenal/web/piano.js:4054-4075` | Live |
| WebCodecs constant-frame-rate MP4 recorder with a MediaRecorder fallback | `arsenal/web/piano/recorder.js:162`, `833-840` | **Untracked and unused** by `piano.js` (`arc-piano-core.md`, section 0) |
| Bench WebM clip recorder | `scripts/vfx.html:1874-1904` | Live in the bench |
| First Light and Play take ledger | `arsenal/take.py:1-6`; routes `/api/take/open`, `/api/take/<id>/events|close` (`arsenal/serve.py:343-351`) | Live |
| Piano recordings upload | `POST /api/recordings` (`arsenal/serve.py:341`), saved to `E:/Video Output E/arsenal-renders` (memory `media-suite-project-2026-09-13.md:56`) | Live |
| Piano performance log | `/api/performance/*` (`arsenal/serve.py:325-355`) | Live |
| Wind flow takes in IndexedDB | `arsenal/web/piano/flow-take-store.mjs:3`, `11-18` | Live, browser-only |
| Edit mode projects and renders | `arsenal/web/edit/render.js`; `arsenal/media/README.md:60-61` | Live |
| TikTok verb (server ffmpeg) | `arsenal.tiktok` with its own ffmpeg finder (`arsenal/media/README.md:62`) | Live |
| Shader-school renders | `state/arsenal/shaders/renders/` (`ls`) | New tonight |

Gyre and the crystal studies save nothing to disk (`GYRE.md:11`, "Nothing is recorded to disk").

### 6.9 Cameras

`piano.js:472` (framing-driven perspective) plus `piano/gallery-camera.js:1-20` (OrbitControls for instrument hero
views); `piano.js:1789` (orthographic overlay camera); `piano-chord-tree.js:35-36`; `piano-crystal-studies.js:33-34`;
`piano-gyre.js:39-40` (plus ride, chase and pilot views, `gyre-presets.mjs:9`); `piano-wind.js:22-23`;
`arsenal/present/targets/three_js.py:5-8` (camera flights between slide planes); `scripts/aurora-shader.js:30` (a
fixed ray-march camera, `CAMZ` and `FOCAL`). Seven owners, field of view 37 to 39 degrees on the studies, no shared
camera rig. The visual quality baseline warns against "competing camera owners" (`VISUAL-QUALITY-BASELINE.md`,
approach 9).

### 6.10 Input: MIDI and audio

| Input | Implementations |
| --- | --- |
| Web MIDI access | `arsenal/web/first-light.js:764-768`, `arsenal/web/play.js:2023-2027`, `arsenal/web/piano.js:3790-3792`, `arsenal/web/piano/cues.js:1696-1697`, `arsenal/web/piano/gyre-music.js:15-16`, `arsenal/web/piano-crystal-studies.js:286-288` |
| Browser audio analysers | `arsenal/web/play.js:1481` (the MilkDrop-style relative normalisation, `PLAY-NIGHT-SPEC.md:150-156`), `arsenal/web/piano.js:4003-4008`, `arsenal/web/edit/playback.js:84` |
| Server audio features | `arsenal/analysis.py` (PyAV, `FIRST-LIGHT-SPEC.md:216`); `arsenal/media/audio.py`, `peaks.py` |
| Music-to-light signals (pure) | `harmony-feel.js`, `moment.js`, `spectacle-motion.js:8` (`harmonicColour`), `crystal-performance.mjs`, `solstice-signals.mjs`, `gyre-harmony.mjs`, `gyre-music.js`, `lean.js`, `cadence-live.js` (the sibling's "H. Music into signals", `arc-piano-studies.md`) |

Two separate MIDI module manifests exist in the registry (`arsenal/modules/webmidi.input.json`,
`webaudio.analyser.json`), but none of the six pages loads its MIDI through them **(inferred: none of the six call
sites imports a shared module; each calls `navigator.requestMIDIAccess` itself)**.

### 6.11 Frame budget: watchdogs, quality tiers, pixel ratio

| Mechanism | Where |
| --- | --- |
| Slow-frame watchdog that halves the backing scale | `arsenal/web/first-light.js:578-587`; `arsenal/web/play.js:1320-1355` (same rule, written twice) |
| FPS watchdog that freezes to a still | `scripts/agent-avatar.js:31-33`; floor 5 (`SKILL.md:65-71`) |
| Fixed undersampling | `scripts/aurora-shader.js:507-522` |
| Quality tiers with fixed internal sizes | `arsenal/web/piano/spectacle.js:19` |
| Display resolution policy, adaptive off unless asked | `arsenal/web/lib/raster-policy.js:32`, `161`; **used only by its test** (`tests/raster_policy.test.mjs`) |
| Pixel ratio forced to 1 and managed by hand | `piano.js:442`, `piano-chord-tree.js:28`, `piano-crystal-studies.js:25` ("Never multiply twice"), `piano-gyre.js:35`, `piano-wind.js:19` |
| Smooth preview (a 4K render shown small) | `9bbc4bf8` |

### 6.12 Render loops

22 files own a `requestAnimationFrame` loop (excluding forks and tests): `arsenal/web/edit/{editor,playback,timeline-view}.js`,
`first-light.js`, `piano/replay.js`, `piano/studio/{reorder,studio}.js`, `piano-chord-tree.js`,
`piano-crystal-studies.js`, `piano-gyre.js`, `piano-wind.js`, `piano.js`, `play.js`, `scripts/{activity-line,agent-avatar,aurora-shader,bifrost_viz,rail,timeline}.js`,
`scripts/{aurora-preview,bench-aurora,vfx}.html`. The design contract wants "One rAF scheduler for the whole page.
Modules subscribe; they do not each own a loop" (`design/CONTRACT.md:79`), and shader-craft floor 9 notes "today
each module owns its own rAF loop" (`SKILL.md:91-93`).

### 6.13 Engine versions, servers and ports

- three.js r186 on every piano page (section 3) and r128 in the deck target (`three_js.py:31`).
- Ports: 8787 Bifrost UI and the bench (`scripts/bifrost_ui.py:9`); 8793 Daniel's arsenal server
  (`arsenal/serve.py:776`); 8795 a test server for piano-next (`PIANO-V2-SPEC.md:27`); 8796 the replay companion
  (memory `media-suite-project-2026-09-13.md:130`); 8797 the shader lab (`arsenal/shaders/serve.py:39`); 8799 the
  studies' static server (`arsenal/web/piano/WIND.md:3`; `arsenal/web/house-round/README.md:5`). Six servers for one
  family of pages.

### 6.14 "Aurora" itself, rebuilt again and again

The concept of an aurora curtain has at least nine implementations: the cockpit bed (`scripts/aurora-shader.js`), its
perf twin (`scripts/bench-aurora.html`), `scripts/aurora-preview.html`, the bench sketches `aurora-bus.frag` and
`daniil-curtains.frag`, the bench composition "aurora-plasma" (`design/vfx-compositions.json`), Navi's Play preset
`arsenal/web/presets/aurora-ribbons.frag`, Navi's instrument `instruments/light-kimi-aurora.js`, the translucent
aurora behind Nocturne (`CRYSTAL-STUDIES.md:11`), and the site hero (`AuroraHero.astro`). It is the house's signature
look and has no single home.

### 6.15 Whole-file forks

See 4.16: five copies of an old `piano.js`, about 10,800 lines, four untracked. Also two copies of the First Light
effect (4.3), and the avatar's model is credited to a CC BY-NC-SA Shadertoy source inside a tracked file
(`scripts/agent-avatar.js:8-9`), a licence question the module core must carry (Heimdall flags the same,
`heimdall-...-half-b.md:105`; shader-craft notes it, `SKILL.md:117-118`).

---

## 7. The module systems that already exist

Heimdall counted three that do not talk (`heimdall-unified-module-system-blind-half-b.md:17-28`). Reading the code I
count six description formats, plus tonight's core:

1. **`arsenal.module/v0` manifests** (`arsenal/registry.py`; `arsenal/__init__.py:10`): typed ports, params with units
   and ranges, isolation, licence, latency, degradation, receipts. Validated. Used by media, present and two vfx modules.
2. **Bench chunk headers** (`design/vfx-chunks/*.glsl:1`): kind, category, ports, a craft note, order. Never
   machine-loaded until tonight.
3. **Bench JSON** (groups, compositions, graphs, an empty presets file): a thin shadow of the graph format.
4. **Play preset headers** (line 2 of each `.frag`, `PLAY-NIGHT-SPEC.md:37-48`): id, name, author, tags, up to eight
   knobs. Validated by `arsenal/presets.py`.
5. **The looks registry** (`looks/registry.js`): settings as descriptors with labels, choices, apply order and
   recording rules. The only one that drives a UI.
6. **Per-page validators** like Gyre's ranges and choices tables (`gyre-presets.mjs:6-9`).
7. **New: the GLSL module core** (`arsenal/shaders/modules.py`, `5e127983`): unifies 1 and 2 and emits format 1 with a
   `shader` block. Formats 3 to 6 are not yet connected to it.

---

## 8. Seams: clean places to cut the shared module system in

1. **The registry's manifest gate.** `arsenal/registry.py:21-40` is the one validator every module passes through;
   the core already targets it (`modules.py:26-27`).
2. **The house library folder.** `arsenal/web/glsl/` exists and holds only `modlib.js`: the first real modules (tone,
   noise, trail, as Heimdall proposes, `heimdall-...-half-b.md:86-93`) go here.
3. **First Light's effect loader** (`arsenal/web/first-light.js:49` onward for the fallback; the runtime fetch per
   `FIRST-LIGHT-SPEC.md:312`): already loads GLSL at runtime and already has a byte-compatible fallback. Note:
   Heimdall cites the fallback at `first-light.js:39-77`; it starts at line 49 today.
4. **Play's preset header.** The `//!` line is one step from the module header; Play is the natural place for the
   finishing chain (tone, vignette, dither) to be imported rather than retyped in eight presets.
5. **The three.js string concatenation seam.** Moonwater and Spectacle build materials from prefix strings
   (`moonwater.js:6-16`; `spectacle.js:21-22`). A composer output can be one of those strings, but see the `hash31`
   name collision (6.2).
6. **The host's `noteColor` and `ctx` objects.** The instrument contract already passes `ctx.noteColor`
   (`instruments/concert-grand.js:1159`); one palette module behind it ends the nine colour copies (6.1a).
7. **The looks registry as the UI generator.** Extend its descriptors to module params so every page's controls come
   from one place (`looks/registry.js:107-140`; the Studio already renders from it).
8. **The pure signal modules.** `harmony-feel.js`, `moment.js`, `crystal-performance.mjs`, `solstice-signals.mjs`,
   `lean.js`: already the right shape to be a shared "music to light" input bus.
9. **The instrument adapter** (`instruments/crystal-study.js:4-15`): the template for turning any study page into a
   module the piano can host.
10. **`arsenal/web/lib/`** (the flow library and the unused raster policy): the existing home for shared browser
    libraries, with a README that states the renderer-neutral rule.
11. **Design tokens.** `design/refs/aurora-glass-tokens.css` (cockpit), First Light's patch-bay tables, and
    `arsenal/present/targets/_core.py` are the three candidate sources for one token file; Edit mode already reads
    tokens at runtime (`edit/timeline-view.js:29-31`), which is the adapter shape.

---

## 9. Binding rules and taste found in the sources

- **The cockpit floors** (raw WebGL2, no three.js, no CDN, never a second GPU context, small avatars, one clock,
  static jitter, compile before shipping) govern the cockpit and the bench (`.claude/skills/shader-craft/SKILL.md:37-93`).
- **Daniel's media-suite ruling**, 2026-09-13: no forbidden-tool rules for the suite; "best, most stable, most
  reliable" wins (memory `media-suite-project-2026-09-13.md:15-17`). Play keeps the craft floors and drops only the
  library and single-context rules (`arsenal/PLAY-NIGHT-SPEC.md:53-60`).
- **Never open a GPU page in the Claude app's browser pane** (`arsenal/FIRST-LIGHT-SPEC.md:23`;
  `.claude/skills/shader-craft/SKILL.md:62-64`).
- **Daniel's live server is his**: never restart 8793 for tests (`arsenal/PIANO-V2-SPEC.md:27`); the shader lab
  refuses that port (`arsenal/shaders/serve.py:40`).
- **Colour means one thing wherever it is a diagnosis**; identity colours are lifted verbatim from the chip gradients
  (`SKILL.md:49-55`).
- **Taste ceiling is Daniel's gate** at milestones; "never claim the ceiling from the floor" (`SKILL.md:8-11`);
  "Beauty remains an authored judgment" (`VISUAL-QUALITY-BASELINE.md:19`).
- **The visual quality baseline**: fidelity, beauty, fluidity, elegance, performance (native pixels, 60 fps minimum,
  "Never silently lower resolution to earn an FPS claim"), trust (`VISUAL-QUALITY-BASELINE.md:8-17`).
- **The 60 fps clause and one scheduler** (`design/CONTRACT.md:68-80`).
- **Analogous palette, never a rainbow; HSV the short way round; superlinear then tanh** (`SKILL.md:101-112`).
- **Recordings capture only the canvas**; anything to be recorded must be drawn into it (`piano-lab-res.js:4-6`, the
  piano header shared by every fork); the lean and the glass stay off recordings unless switched on
  (`lean.js:4-7`).
- **Daniel's private data stays under `state/`** and never enters tracked files or commit messages (memory
  `story-layer-arc-2026-10-12.md:27-28`; `arsenal/PIANO-V2-SPEC.md:31`).
- **The corpus licence line**: Shadertoy code is mostly CC BY-NC-SA and never enters a tracked file (memory
  `shader-school-2026-10-13.md:20`). House-written modules are Apache-2.0 (memory `shader-school-2026-10-13.md:37-38`).
- **Story-layer rulings**: four tension ingredients, never one meter; words only in rests (memory
  `story-layer-arc-2026-10-12.md:22-23`; `lean.js:10-11`).
- **Ship one finished thing before the next** when threads multiply (memory `media-toolkit-vision-2026-10-11.md:45-47`).

---

## 10. Landmines for a unification

1. **Changing a shared module will change looks Daniel has already approved.** Tone mapping alone differs across
   surfaces (6.4); unifying it moves pixels on surfaces he called "floored" and "incredible". Every swap needs a
   before-and-after render and his eye (the ceiling gate).
2. **The `hash31` name collision** between Moonwater and the bench chunk (6.2).
3. **The "ember" name collision** across three meanings (6.1b).
4. **Two three.js versions** (r186 and r128). A module that targets three.js APIs must say which.
5. **Untracked work at risk**: `recorder.js`, `lean.js`, `latency.js`, `listen/dsp.js`, four lab forks, the house-round
   pilot, the shader lab runtime and server (`git status --untracked-files=all`). A `git clean` loses them.
6. **Forks drift silently.** The lab pages judge an old `piano.js` (4.16).
7. **Citations already drift.** Heimdall's half cites the First Light fallback at lines 39-77 (it is at 49) and 33
   chunks (there are 31). Any plan built on line numbers needs re-reading at build time.
8. **Licences inside tracked code.** The avatar's geodesic model is credited to a CC BY-NC-SA source
   (`scripts/agent-avatar.js:8-9`), and the cockpit bed credits a Shadertoy noise (`scripts/aurora-shader.js:176`). A
   module's licence field must reflect its real ancestry, not default to Apache-2.0 **(the second case is inferred
   risk; I did not check that shader's licence)**.
9. **The cockpit and the suite have different rulebooks** (section 3). A shared module must compose under the
   stricter one if the cockpit is to consume it.

---

## 11. Read versus inferred

Read directly: every `file:line` above, the commit hashes and dates, the `git status` untracked list, and the counts
from greps (sine hash, `fbm`, point sprites, additive blending, sliders, rAF loops, MIDI calls, tone mapping lines,
the fork diffs).

Inferred, and marked where used:
- That no live surface imports a module from the new core yet (no import of `arsenal/web/glsl` found by eye; I did not
  grep for every possible import form).
- That the glider has no renderer (only `physics.js` in its folder).
- That the jam's file stores mirror the looks and performance stores (from docstrings).
- That the site hero was inspired by, not copied from, the cockpit bed.
- That Play's line-2 header is or is not accepted by the module core's parser (not read).
- That the lab forks' judging harnesses now judge outdated code.
- That `piano-crystal-studies.html` carries a CSS vignette (a grep hit, not read).
- The licence risk of the bed's credited noise.
