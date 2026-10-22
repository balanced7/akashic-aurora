# Evidence: shader params, the VFX Bench, Shader Lab and external-control hooks (2026-10-22)

The final report of a read-only Explore agent (sonnet), dispatched by Vandor for the A16 design docs
W295 (pads fire VFX) and W297 (shader parameters on faders and knobs). Persisted unedited per the
full-fidelity rule.

---

Evidence sweep of E:\AI-Setup (git history + file reads, py launcher used for the one script run). All citations verified against actual file contents.

## 1. The shader param schema

Lives in three files, all from commits ef5c2a3d (GREEN) / a904e925 (RED pin): `arsenal/params.py` (Python twin), `arsenal/web/lib/params.js` (JS twin), `arsenal/web/lib/params-ui.js` (control generator). Confirmed via `git show --stat ef5c2a3d` and `a904e925`.

Descriptor shape, from `arsenal/web/lib/params.js:12-14`:
```
{ id, group, label, type: "range" | "choice" | "toggle" | "colour" | "vec",
  unit, range: {min, max, step}, default, curve: "linear" | "log" | "exp", values: [{value, label}] (choices),
  help, recBlocked, order, uniform, derived (an expression of other params), cost (true if it changes GPU cost),
  source: {module, param, instance} }
```
Representative entries, `tests/fixtures/params/descriptors.json` (read via `py`):
```json
{"id": "intensity", "group": "light", "label": "Intensity", "type": "range", "unit": "ratio", "range": {"min": 0, "max": 2, "step": 0.01}, "default": 1}
{"id": "tint", "group": "light", "label": "Tint", "type": "colour", "unit": "colour", "default": [1, 0.5, 0.25]}
{"id": "rays", "group": "shape", "label": "Rays", "type": "toggle", "unit": "bool", "default": true, "recBlocked": true}
```
Surfaces generate controls from the schema via `params_from_module()` (`arsenal/params.py:678-725`, Python) / the JS equivalent, which turns a GLSL recipe's `params` header into descriptors with uniform names `u_<name>` (or `u_<instance>_<name>`). `renderParams(doc, descriptors, opts)` (`arsenal/web/lib/params-ui.js:40`) walks descriptors into DOM controls (grouped sections, unit shown, reset-to-default, cost badge, lock while recording). `params-ui.js:1-3` names its consumers: "the bench Inspector, the Studio drawer, First Light's patch panel, Play, Gyre and Wind." There's also an adapter from the older piano "looks registry" into this schema: `fromLooksDescriptor()` at `arsenal/web/lib/params.js:737-751`.

## 2. VFX Bench page

`scripts/vfx.html` (commits 5e40b68d GREEN, 2536ddb2 RED — confirmed via `git show --stat`). It renders a drag-and-drop effect chain/graph editor over the house GLSL library (`scripts/vfx-codegen.js` rebuilds its three code generators on the shared "modlib" composer, per 5e40b68d's commit message) plus a live-shaded stage driving `AgentAvatar` (`scripts/vfx.html:375`, "The bench drives the SAME AgentAvatar the console mounts").

Runtime parameter control: plain `<input type="range">` UI sliders built by a local `slider()` helper (`scripts/vfx.html:383-391`); each `input` event calls `set(parseFloat(...))` then `emit()`. No postMessage/WebSocket — I grepped `arsenal/web`, `scripts/vfx.html` for `new WebSocket|ws://|wss://` with zero hits.

Yes — there is a "look"/preset concept, explicitly named presets: a `<select id="presets">` (`scripts/vfx.html:342`) and name field "name this look" (`scripts/vfx.html:346`). `savePreset()`/`loadPreset()`/`refreshPresets()` (`scripts/vfx.html:566-603`) persist via HTTP, not localStorage, "ON PURPOSE" (comment at `scripts/vfx.html:566-568`): `fetch('/vfx/presets')` GET and POST to the same path, backed by `design/vfx-presets.json`. Server-side routes confirmed in `scripts/bifrost_ui.py:819` (GET) and `:1348` (POST). A preset's value bundles style/state/identity/params/tint/dials — this is a directly reusable "pad fires a look" target.

## 3. Shader Lab and the live switch

Confirmed via `git show --stat be0fc4c8`, `1a413b29`, `85af8e47` and reading `arsenal/web/shaderlab/README.md`.

be0fc4c8: the Workbench (Library/Stage/Inspector/Strip, `arsenal/web/lib/workbench/*`) ships view-only — SwiftShader stills + filmstrip only, no canvas, no WebGL context created while off.

1a413b29: the live path behind the switch adds a frame watchdog, growth-exponent proof, a scale ladder, per-subject refusals — still off by default (`arsenal/web/lib/workbench/stage.js`, `arsenal/shaders/lab_shot.mjs`).

85af8e47 / README "Still owed before the switch may be turned on" (quoted, `arsenal/web/shaderlab/README.md`):
- "A hiccup on a frame reading can still flatten the measured growth" — a slow pre-flight frame can make a steep shader look shallow; in simulation 84/392 runs drew a live frame over 500 ms (worst ~85 s).
- "Symmetric noise on the per-frame reading biases it low" once the smaller of two readings is kept.
- "Cheap subjects can stay at a lower scale than they could run" (usability cost, not a risk).
- "The 90 x 51 fallback draws frames that cannot change the verdict" for already-too-slow tiny frames.

The switch itself: on only when `/lab/?live=1` AND `localStorage['arsenal.shaderlab.live'] === 'on'` in that browser — both documented and enforced in `stage.js`'s `liveSwitch()`/`mustBeLive()` (README, "How it is kept" section).

## 4. First Light and piano visual-effect params

**First Light "Edit mode"** (`arsenal/web/edit/editor.js`, `inspector.js`, `mixer.js`) exposes clip/timeline metadata (codec, fps, placement) and keyboard shortcuts (`editor.js:26-39`, Space/S/Delete/Ctrl+Z/etc.) — I found **no** glow/intensity/hue params there (grepped `inspector.js`/`mixer.js`, zero hits).

**First Light's main page** (`arsenal/web/first-light.js`, NOT the editor) is where fader-drivable shader params actually live: a built-in GLSL effect exposes `uniform float u_hue` and `uniform float u_intensity` (`first-light.js:58`, declared list at `:463`), bound at `:568-569`, with `state.params = {hue: 0, intensity: 0.8}` (`:144`) and glow math `float glow = u_pulse * 0.35 * u_intensity` (`:104-105`). `arsenal/FIRST-LIGHT-SPEC.md:8` states the intent directly: "a knob on his Arturia KeyLab 88 mk3 turns the hue."

**Piano page** atmosphere/colour params live in the looks registry `arsenal/web/piano/looks/registry.js:136-138`: `intensity` ("Light & impact", range 0.25–1.4 step 0.05), `motion` (range 0.15–1), `journey`/"Camera drift" (range 0–1), plus choice-type `theme`, `weather`, `colour` (`:149`), `scheme`. Set at runtime by calling page methods (e.g. `page.setColourMode(value)`, `:159`) through the registry's `apply()` functions in verified stage order (`registry.js:10-20`), not by a generic slider widget — though the params.js adapter above can bridge them into the generated-control UI.

## 5. Aurora groups and the house GLSL library — named "looks"?

`git show --stat 1b489ac1` (aurora groups 1.3.0) and `bdd5c8fc` (GREEN, library batch B) confirm: `bdd5c8fc`'s commit message states "Groups: aurora-band, aurora-sheets, glow-xray, neon-line, studio-object, hex-neon, each a recipe whose params generate UI controls, uniforms named u_<recipe>_<param>." Files: `arsenal/web/glsl/groups/{aurora-band,aurora-sheets,glow-xray,hex-neon,neon-line,studio-object}.glsl`, indexed in `arsenal/web/glsl/index.json:100-123`. `b9bb784d` (batch A, 31 foundation modules: noise, colour/OKLCH, palettes "including the piano's circle of fifths", tone curves) is the underlying library these groups compose.

These are named GLSL **recipes**, each generating its own param set via the schema above — the closest thing to a reusable "look" by name, and a natural pad target (load recipe X, feed its generated params). But I found no separate "preset/scene" registry layered on top of the groups themselves (no `groups/presets.json` or similar) — the only explicit named-preset mechanism in this sweep is the VFX Bench's `/vfx/presets` (§2).

## 6. Existing external-control hooks

- **Web MIDI exists but only for note input**, not generic fader/knob→param mapping, on the piano pages: `arsenal/web/piano.js:3801-3803` (`navigator.requestMIDIAccess`), `onMidiMessage` (`:3869-3895`) handles only NoteOn/Off (0x90/0x80) and CC64 sustain / CC120/123 panic (`:3887-3889`) — no generic CC→param mapping.
- **First Light has exactly the hook the design doc needs**: a MIDI-Learn system mapping arbitrary CC numbers to `hue`/`intensity`. `arsenal/web/first-light.js`: `connectMIDI()` (`:763`, prefers an input named "KeyLab", `:771`), `onMidiMessage()` (`:794`) filters to CC (`status === 0xb0`), `armLearn()` (`:832`) arms learning for the next target in `learnQueue: ["hue", "intensity"]` (`:164`), writes `MIDI.mappings[target] = {cc, range}` (`:809`), persists to `localStorage["arsenal.firstlight.midiMap"]` (`:15`, `persistMappings` `:843`). Spec at `arsenal/FIRST-LIGHT-SPEC.md:357-362`. This is a real, working CC→shader-uniform bridge already in the repo.
- **Query params**: `?live=1` gates the Shader Lab live switch (`arsenal/web/lib/workbench/stage.js:127-139`, README); `?codegen=legacy` forces the VFX bench's old code path (`scripts/vfx.html:786,804-805`).
- **Keyboard shortcuts**: First Light Edit mode has an editing shortcut table (`editor.js:26-39`); VFX bench has only Ctrl+Z/Shift+Z/Y undo-redo and Ctrl+Enter-to-send (`scripts/vfx.html:2330-2342`) — no pad-style trigger shortcuts anywhere I found.
- **Message bus**: no WebSocket/postMessage control channel on any of these pages (grep came up empty). The one HTTP seam a local service could already drive is `/vfx/presets` GET/POST (`scripts/bifrost_ui.py:819,1348`) — poll-and-push, not push-notify.
- Separately, `arsenal/keylab/` (commit c37ff191, landed 2026-10-22, local-only per Daniel) is outbound hardware control (LED/LCD via WinMM/SysEx) for the KeyLab itself — not an inbound hook into these web pages, and distinct from Web MIDI input above.

Not found / explicitly absent, confirmed by search rather than assumed: no generic CC→param bus reaching the piano or VFX-bench pages; no preset/scene registry for the aurora groups beyond the VFX Bench's own; no WebSocket anywhere in `arsenal/web` or `scripts/vfx.html`.
