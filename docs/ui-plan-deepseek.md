# Aurora Glass UI Build Plan — DeepSeek's Slice

Status: historical  (2026-07-09, P4: Parallel plan; synthesis supersedes)

> **My lane** (per negotiation round): HUD glanceability strip + benchmark/feature-flag infra + `since` backend + shader parameter controls.
> **Claude's lane**: Aurora shader (building on my GLSL draft) + glass material + legibility/accessibility gate + Razer conic accent.
> **Merge target**: `docs/ui-plan-synthesis.md` — AGREED spec; both agents build from it.
> **Inspiration**: shaderpark.com (interactive parameter controls, remix culture, layered noise) + awwwards.com GLSL sites (hero shader pattern, palette discipline, state-as-signature, performance as award criterion).

---

## Slice 1: WebGL Aurora Background Shader

**What**: Replace the CSS `radial-gradient` + `conic-gradient` pseudo-element background with a single full-viewport `<canvas>` running a fragment shader (GLSL, compiled to WebGL). The shader uses FBM noise + domain warping to produce a slow-moving aurora curtain.

**Why**: This is the "shock factor" — the one visual element that makes a screenshot instantly recognizable. CSS gradients (even with animated `conic-gradient` and `blur(60px)`) cannot produce the organic folded-curtain look of real aurora. WebGL can, and it's essentially free on modern hardware (a fullscreen quad at 60fps uses ~2% GPU on integrated graphics).

### 1.1 Shader Architecture

```
┌─────────────────────────────────────────────────┐
│  <canvas id="aurora-canvas">                     │
│  position: fixed; inset: 0; z-index: -2;         │
│  pointer-events: none;                           │
│                                                  │
│  Fragment shader (per-pixel):                    │
│    1. UV → screen-space coordinates              │
│    2. Domain-warp: warp = fbm(uv + 0.2*time)    │
│    3. fbm(uv + warp + vertical_drift) → value    │
│    4. Envelope: vertical band mask (top 35%)     │
│    5. Color map: value → blackbody temp → RGB    │
│    6. Alpha blend with --aurora-deep background  │
│    7. Fragment discard if below noise floor      │
│                                                  │
│  N bands (default=2):                            │
│    Band 0: peak at y=0.15, green→violet          │
│    Band 1: peak at y=0.28, blue→teal (fainter)   │
│                                                  │
│  Uniforms (per frame):                           │
│    u_time (seconds, monotonically increasing)    │
│    u_resolution (vec2, canvas width/height)       │
│    u_state (int: 0=normal, 1=paused, 2=halted)  │
│    u_state_intensity (float, lerps with state)   │
└─────────────────────────────────────────────────┘
```

### 1.2 GLSL Noise Primitives

**Simplex-like 2D noise** (avoiding the patent-encumbered 3D simplex). Use a hash-based gradient noise with smooth interpolation — the standard approach is:

```glsl
// Hash function (stable across GPUs)
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// 2D value noise with smoothstep interpolation
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);  // smoothstep

    return mix(
        mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
        mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x),
        f.y
    );
}
```

**FBM (4 octaves)**:
```glsl
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 4; i++) {
        value += amplitude * noise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}
```

**Domain warping** (the "aurora" look):
```glsl
vec2 q = vec2(
    fbm(uv + vec2(0.0, u_time * 0.03)),
    fbm(uv + vec2(5.2, 1.3) + u_time * 0.04)
);
float aurora = fbm(uv + 1.2 * q + vec2(0.0, u_time * 0.02));
```

### 1.3 Vertical Envelope (Curtain Shaping)

```glsl
// Two aurora bands at different altitudes
float band1 = smoothstep(0.05, 0.20, uv.y) * (1.0 - smoothstep(0.20, 0.40, uv.y));
float band2 = smoothstep(0.15, 0.35, uv.y) * (1.0 - smoothstep(0.35, 0.55, uv.y)) * 0.6;

// Add horizontal variation (the curtain "pleats")
float curtain = aurora * (band1 + band2);

// Clamp: aurora never reaches below y=0.55 (keeps text area dark)
curtain *= 1.0 - smoothstep(0.45, 0.55, uv.y);
```

### 1.4 Color Mapping (Blackbody Temperature LUT)

Rather than linear RGB mixing, use a temperature-based color ramp:

```glsl
vec3 auroraColor(float t) {
    // t in [0,1] maps through:
    // 0.0 → deep background (transparent black)
    // 0.3 → teal    (8000K)  -- deepseek signature
    // 0.5 → green   (5500K)  -- aurora green
    // 0.7 → violet  (12000K) -- edge shimmer
    // 1.0 → deep background (fades out at top)

    vec3 teal   = vec3(0.29, 0.42, 0.46);   // #4a6b75 → muted deepseek
    vec3 green  = vec3(0.28, 0.90, 0.75);   // #48e6bf → aurora green
    vec3 violet = vec3(0.46, 0.18, 0.54);   // #752e8a → edge violet

    // Piecewise mix
    if (t < 0.3) return mix(vec3(0.0), teal, t / 0.3);
    if (t < 0.5) return mix(teal, green, (t - 0.3) / 0.2);
    if (t < 0.7) return mix(green, violet, (t - 0.5) / 0.2);
    return mix(violet, vec3(0.0), (t - 0.7) / 0.3);
}
```

### 1.5 State-Driven Color Shifts

When the system state changes (paused, halted, agent-nudged), the shader adapts:

```glsl
// u_state: 0=normal, 1=paused, 2=halted
// u_state_intensity: lerps 0→1 over ~1.5s when state changes

// Paused: shift aurora toward amber
vec3 paused_tint = vec3(0.94, 0.70, 0.27);  // #f0b246 amber
color = mix(color, paused_tint, u_state_intensity * float(u_state == 1) * 0.4);

// Halted: desaturate + darken
color = mix(color, color * 0.3, u_state_intensity * float(u_state == 2) * 0.7);
```

### 1.6 JavaScript Driver

```javascript
// aurora-shader.js — self-contained, no dependencies
class AuroraShader {
    constructor(canvas) {
        this.canvas = canvas;
        this.gl = canvas.getContext('webgl2', {
            alpha: true,
            antialias: false,
            powerPreference: 'low-power',  // don't wake the dGPU
            preserveDrawingBuffer: false
        });
        this.state = 0;       // 0=normal, 1=paused, 2=halted
        this.stateTarget = 0;
        this.stateLerp = 1.0; // 1.0 = fully at target
        this.startTime = performance.now() / 1000;
        this.animating = true;
        this._compile();
        this._resize();
        this._bindVisibility();
        window.addEventListener('resize', () => this._resize());
    }

    setState(state) {
        this.stateTarget = state;
        if (this.stateTarget !== this.state) {
            this.state = this.stateTarget;
            this.stateLerp = 0.0;
        }
    }

    _compile() {
        // Compile vertex + fragment shaders, link program, get uniform locations
        // Vertex: fullscreen triangle (no vertex buffer needed — use gl_VertexID)
        // Fragment: the aurora shader above
    }

    _resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2); // cap at 2x
        this.canvas.width = this.canvas.clientWidth * dpr;
        this.canvas.height = this.canvas.clientHeight * dpr;
        this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }

    _bindVisibility() {
        document.addEventListener('visibilitychange', () => {
            this.animating = !document.hidden;
            if (this.animating) this._tick();
        });
    }

    _tick() {
        if (!this.animating) return;
        requestAnimationFrame(() => this._tick());

        const time = performance.now() / 1000 - this.startTime;

        // Lerp state intensity
        this.stateLerp = Math.min(1.0, this.stateLerp + 0.016 / 1.5); // 1.5s transition

        this.gl.uniform1f(this.u_time, time);
        this.gl.uniform1i(this.u_state, this.state);
        this.gl.uniform1f(this.u_state_intensity, this.stateLerp);

        this.gl.drawArrays(this.gl.TRIANGLES, 0, 3);
    }

    start() { this.animating = true; this._tick(); }
    stop() { this.animating = false; }
}
```

### 1.7 CSS Integration

```css
/* Remove existing body::before and body::after pseudo-elements */
/* Replace with: */
#aurora-canvas {
    position: fixed;
    inset: 0;
    z-index: -2;
    pointer-events: none;
    opacity: 0.85;  /* let the dark bg show through for depth */
}
/* body::after (noise texture overlay) stays — it adds grain atop the shader */
```

### 1.8 Benchmark Gate (PASS/FAIL)

**Before merging**, the shader must pass these benchmarks (automated):

| Test | Target | Threshold | Measurement |
|------|--------|-----------|-------------|
| Frame time (median) | < 4ms | FAIL if > 8ms | `performance.now()` delta over 120 frames |
| Frame time (p99) | < 12ms | FAIL if > 20ms | 99th percentile |
| GPU memory | < 4MB | FAIL if > 8MB | `gl.getExtension('WEBGL_debug_renderer_info')` or estimation |
| Composite-only when hidden | 0 rAF calls | FAIL if > 0 | Counter in `_tick()` during `document.hidden` |
| First-paint time | < 200ms | WARN if > 400ms | Time from `new AuroraShader()` to first frame on screen |
| Static scene GPU usage | < 5% | WARN if > 10% | Chrome DevTools Performance panel (manual) |

**Benchmark script**: `scripts/bench-aurora.html` — a standalone page that loads the shader, runs 5 seconds of measurement, and reports PASS/FAIL. This is gated in CI — the shader doesn't ship to `bifrost_ui.py` until the benchmark passes.

**Fallback**: If the benchmark fails (or WebGL2 isn't available), fall back to the current CSS gradient background. The shader is a progressive enhancement, not a requirement.

---

## Slice 2: HUD "Who's Doing What" Glanceability Strip

**What**: A horizontal strip between the header and the message log showing, at a glance, what each online agent is currently doing. Compact (28-36px per agent row), icon-led, with state-driven animations.

**Why**: Currently, finding out what an agent is doing requires scanning the activity area at the bottom of the log (which scrolls away) or the pills (which only show online/offline). The HUD strip is always visible and answers the question in one glance. This is the "mission control" UX pattern from UniFi, Destiny, and Stripe.

### 2.1 Layout

```
┌─ header ───────────────────────────────────────────────────────┐
│ ⏣ Bifrost live agent console          [pills] [⚙] [🚀] [⏸]  │
├─ HUD strip ────────────────────────────────────────────────────┤
│ 📖 deepseek  reading  core/comm/bus.py         12s            │ ← 36px
│ 💭 claude    thinking "aurora color mapping"    2.4m           │
│ ⚡ deepseek  running  pytest tests/test_bus.py   8s            │
│ 💤 claude    idle                                             │
├─ message log ──────────────────────────────────────────────────┤
│ ...                                                            │
└─ composer ─────────────────────────────────────────────────────┘
```

Each row:
- **Icon** (16px emoji or SVG): Maps to the activity state — 📖 reading, ✍️ writing, 🔍 searching, ⚙️ running, 💭 thinking, 🧠 recalling, 💤 idle
- **Agent name** (bold, agent-colored): `deepseek` in `--deepseek` blue, `claude` in `--claude` amber
- **Verb** (muted): Present-tense action — "reading", "writing", "thinking", "idle"
- **Detail** (faint, monospace, truncated): The target — filename, search query, command
- **Elapsed** (faint, right-aligned): Time since this activity started — `12s`, `1.4m`, `just now`

### 2.2 Data Source

The `/status` endpoint already returns `activities`:
```json
{
  "activities": {
    "deepseek": {"state": "reading", "detail": "core/comm/bus.py", "since": "2026-07-04T19:32:12Z"},
    "claude": {"state": "thinking", "detail": "aurora color mapping", "since": "2026-07-04T19:29:45Z"}
  }
}
```

We need to add a `since` timestamp to the activity tracking in `core/comm/control.py` (or wherever activities are set) — currently it only tracks `state` and `detail`. The `since` field enables the elapsed-time badge.

### 2.3 CSS Design

```css
#hud-strip {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin: 0 16px;
    padding: 8px 0;
    border-bottom: 1px solid var(--glass-line);
    background: linear-gradient(
        to bottom,
        var(--glass),
        transparent
    );
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    max-height: 148px; /* ~4 rows visible; scroll if more */
    overflow-y: auto;
    transition: max-height 0.3s ease;
}

/* Collapsed state: only active agents shown */
#hud-strip.collapsed {
    max-height: 40px; /* single row peek */
}
```

### 2.4 Row Micro-animations

```css
.hud-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    font-size: 13px;
    height: 32px;
    animation: hudSlideIn 0.28s cubic-bezier(0.2, 0.9, 0.3, 1.1);
    transition: background 0.2s, opacity 0.25s;
}

/* New activity: brief glow pulse on the leading icon */
.hud-row.just-started .hud-icon {
    animation: hudGlowPulse 0.6s ease-out;
}

/* Stale activity (>5 min no change): fade slightly */
.hud-row.stale {
    opacity: 0.55;
}

/* Scan line: a 1px translucent sweep across the strip */
#hud-strip::after {
    content: "";
    position: absolute;
    left: 0; right: 0; height: 1px;
    background: var(--hud-scanline);
    animation: hudScan 3.5s linear infinite;
    pointer-events: none;
}

@keyframes hudSlideIn {
    from { opacity: 0; transform: translateX(-8px); }
    to   { opacity: 1; transform: translateX(0); }
}

@keyframes hudGlowPulse {
    0%   { filter: drop-shadow(0 0 2px var(--aurora-neon)); }
    100% { filter: drop-shadow(0 0 0px transparent); }
}

@keyframes hudScan {
    from { top: 0; }
    to   { top: 100%; }
}
```

### 2.5 JavaScript Renderer

```javascript
// Called from applyStatus() when activities change
function renderHUD(activities) {
    const strip = document.getElementById('hud-strip');
    if (!strip) return;

    const rows = Object.entries(activities || {})
        .filter(([agent, act]) => act && act.state)
        .sort((a, b) => {
            // Active first, then idle, then stale
            const order = { thinking: 0, reading: 0, writing: 0, searching: 0,
                           running: 0, recalling: 0, working: 0, idle: 1 };
            return (order[a[1].state] || 2) - (order[b[1].state] || 2);
        })
        .map(([agent, act]) => {
            const icon = ICON[act.state] || '⚡';
            const verb = VERB[act.state] || act.state;
            const detail = act.detail || '';
            const elapsed = act.since ? elapsedTime(act.since) : '';
            const stale = act.since && (Date.now() - new Date(act.since).getTime()) > 300000;
            return {
                agent, icon, verb, detail, elapsed, stale,
                cls: cls(agent)
            };
        });

    // Diff against current DOM to minimize rebuilds
    const currentIds = new Set(rows.map(r => r.agent));
    const existingIds = new Set(
        [...strip.children].map(el => el.dataset.agent)
    );

    // Remove rows for agents no longer active
    [...strip.children].forEach(el => {
        if (!currentIds.has(el.dataset.agent)) {
            el.style.opacity = '0';
            el.style.transform = 'translateX(-12px)';
            setTimeout(() => el.remove(), 250);
        }
    });

    // Add/update rows
    rows.forEach((row, i) => {
        let el = strip.querySelector(`[data-agent="${row.agent}"]`);
        if (!el) {
            el = document.createElement('div');
            el.className = 'hud-row';
            el.dataset.agent = row.agent;
            strip.appendChild(el);
        }

        const staleClass = row.stale ? ' stale' : '';
        el.className = `hud-row${staleClass}`;
        el.innerHTML = `
            <span class="hud-icon">${row.icon}</span>
            <span class="hud-agent ${row.cls}">${esc(row.agent)}</span>
            <span class="hud-verb">${esc(row.verb)}</span>
            <span class="hud-detail">${esc(row.detail)}</span>
            <span class="hud-elapsed">${row.elapsed}</span>
        `;
    });

    // Show/hide strip
    strip.style.display = rows.length ? 'flex' : 'none';
}

function elapsedTime(since) {
    const seconds = Math.floor((Date.now() - new Date(since).getTime()) / 1000);
    if (seconds < 10) return 'just now';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
}
```

### 2.6 Interaction Design

- **Hover**: Row background shifts to `var(--panel2)`, detail text expands (remove `text-overflow:ellipsis` on hover).
- **Click**: Expands to show a 2-line trace of the last 3 actions from that agent (like a mini-log inline). Uses the existing trace data from the SSE stream.
- **Right-click**: Context menu with "Message this agent" / "Steer this agent" / "Halt this agent" — same actions as the glass-card expand menu.
- **Collapse toggle**: A small `⌃` / `⌄` button at the right edge of the strip toggles between full (all active) and collapsed (first active only, 40px height). Default: full.

### 2.7 Integration Points

**Backend change needed**: `core/comm/control.py` (or wherever `get_activities()` lives) must include a `since` timestamp with each activity record. This is a ~5-line change — store `time.time()` or an ISO timestamp when activity state is set.

**Frontend**: `applyStatus()` already receives `s.activities`. Add a `renderHUD(s.activities)` call at the end of `applyStatus()`, after the fingerprint check (so it only renders when activities actually changed).

**HTML**: Add `<div id="hud-strip"></div>` between the banner and the message log in the `PAGE` string.

---

## Slice 3: Benchmark & Gating Infrastructure

**What**: A standalone benchmark page + a CI gate that prevents the aurora shader from shipping if it fails performance thresholds.

### 3.1 `scripts/bench-aurora.html`

A self-contained HTML page that:
1. Creates a full-viewport canvas
2. Instantiates the AuroraShader
3. Runs a 5-second measurement window (warmup 2s + measure 3s)
4. Reports frame-time median, p99, and GPU memory estimate
5. Displays PASS/FAIL with specific failing thresholds

### 3.2 CI Gate

Add to `scripts/mirror.py` or a pre-commit hook:
```python
# Pseudo: if docs/ui-plan-deepseek.md changed and mentions "shipping the shader",
# check that scripts/bench-aurora.html exists and last run was PASS.
# This is a manual gate for now — automated CI needs a headless WebGL runner.
```

For now, the gate is: **this build plan itself is the spec**. The shader implementation must include the benchmark page, and the benchmark must pass before the shader is wired into `bifrost_ui.py`.

---

## Slice 4: Progressive Rollout & Feature Flags

### 4.1 Shader Feature Flag

```javascript
// LocalStorage flag — default OFF until benchmark passes locally
const AURORA_ENABLED = localStorage.getItem('bifrost_aurora_shader') === '1';
// Also check WebGL2 support
const WEBGL2_SUPPORTED = (() => {
    try { return !!document.createElement('canvas').getContext('webgl2'); }
    catch(e) { return false; }
})();

if (AURORA_ENABLED && WEBGL2_SUPPORTED) {
    new AuroraShader(document.getElementById('aurora-canvas')).start();
}
```

### 4.2 HUD Feature Flag

```javascript
const HUD_ENABLED = localStorage.getItem('bifrost_hud_strip') !== '0'; // default ON
// The HUD has no performance risk — it's pure DOM. Default ON.
```

### 4.3 Settings Panel Integration

Add to the existing settings panel (`#setp`):
- "Aurora Shader" toggle (on/off) — writes to `bifrost_aurora_shader`
- "HUD Strip" toggle (on/off) — writes to `bifrost_hud_strip`

---

## Implementation Order (Dependency Graph)

```
1. Slice 2.1-2.6: HUD Strip (no dependencies, pure DOM)
   └── Backend: add `since` to activities
   └── Frontend: renderHUD(), HTML div, applyStatus integration
   └── Settings panel toggle

2. Slice 1.1-1.7: Aurora Shader (depends on nothing except WebGL2)
   └── aurora-shader.js (standalone)
   └── CSS integration (replace pseudo-elements)
   └── State integration (pass paused/halted to shader)

3. Slice 3.1-3.2: Benchmark & Gate
   └── scripts/bench-aurora.html
   └── Feature flags + settings panel
   └── Benchmark PASS → wire shader into bifrost_ui.py

4. Slice 4: Progressive rollout
   └── Default-off → benchmark PASS → default-on for WebGL2 users
```

---

## What I'm NOT Doing (Claude's Lane — assumed)

- Glass material refinement (backdrop-filter tuning, light/dark theme variants)
- Accessibility audit (contrast ratios, prefers-reduced-motion, screen-reader)
- Apple VisionOS/HIG alignment
- Frost theme (light mode) variants
- Message rendering improvements (the `markdown` variant is already adequate)
- Mobile/tablet responsive layout
- Color blindness simulation and palette validation

These are documented here so the negotiation round can assign clear ownership and detect coverage gaps.

---

## Success Criteria (Merge-Ready Checklist)

- [ ] Aurora shader renders at 60fps on integrated GPU (Intel UHD 620 or equivalent)
- [ ] Aurora shader pauses when tab is hidden (zero CPU/GPU usage)
- [ ] Aurora shader falls back to CSS gradients when WebGL2 unavailable
- [ ] HUD strip shows accurate, real-time agent activity
- [ ] HUD strip rows animate smoothly on state changes
- [ ] HUD strip is keyboard-navigable (tab through rows)
- [ ] Both features have settings-panel toggles that persist across sessions
- [ ] `bench-aurora.html` reports PASS on developer machine
- [ ] No regression: existing UI (pills, messages, composer, launcher) functions unchanged
- [ ] No layout shift: HUD strip has reserved space even when empty (prevents log jump)

---

## Slice 5: Shader Parameter Controls (from Shaderpark.com inspiration)

**What**: When the aurora shader is enabled, surface real-time controls in the settings panel (`#setp`) that directly manipulate shader uniforms — no recompilation, no page reload.

**Why**: Shaderpark.com's signature UX is the inline parameter panel — hover/tap to reveal sliders that modify the shader live. This turns the aurora from a fixed background into a user-tunable environment. It also makes debugging and demoing the shader trivial (no code edits to try a different speed).

### 5.1 Controls

| Control | Type | Range | Default | Uniform |
|---------|------|-------|---------|---------|
| Drift Speed | range slider | 0.25× – 2× | 1× | `u_time` multiplier |
| Intensity | range slider | 0.2 – 1.0 | 0.85 | fragment alpha multiplier |
| Palette | radio group | aurora / warm / mono | aurora | switches color LUT branch |

### 5.2 Implementation

```javascript
// Settings panel HTML additions (only visible when AURORA_ENABLED)
<div id="aurora-controls" style="display:none">
  <label>Aurora speed <input type="range" id="aurora-speed" min="0.25" max="2" step="0.05" value="1"></label>
  <label>Aurora intensity <input type="range" id="aurora-intensity" min="0.2" max="1" step="0.05" value="0.85"></label>
  <fieldset>
    <legend>Palette</legend>
    <label><input type="radio" name="aurora-palette" value="aurora" checked> Aurora (green/teal/violet)</label>
    <label><input type="radio" name="aurora-palette" value="warm"> Warm (amber/rose/gold)</label>
    <label><input type="radio" name="aurora-palette" value="mono"> Mono (deepseek blue)</label>
  </fieldset>
</div>
```

```javascript
// Live uniform update (no shader recompilation)
document.getElementById('aurora-speed').addEventListener('input', function(e) {
  if (window._auroraShader) window._auroraShader.setSpeed(parseFloat(e.target.value));
  localStorage.setItem('bifrost_aurora_speed', e.target.value);
});
document.getElementById('aurora-intensity').addEventListener('input', function(e) {
  if (window._auroraShader) window._auroraShader.setIntensity(parseFloat(e.target.value));
  localStorage.setItem('bifrost_aurora_intensity', e.target.value);
});
document.querySelectorAll('[name="aurora-palette"]').forEach(function(r) {
  r.addEventListener('change', function() {
    if (window._auroraShader) window._auroraShader.setPalette(this.value);
    localStorage.setItem('bifrost_aurora_palette', this.value);
  });
});
```

### 5.3 Shader-Side

```glsl
// Additional uniforms
uniform float u_speed;       // multiplier on u_time (default 1.0)
uniform float u_intensity;   // fragment alpha multiplier (default 0.85)
uniform int u_palette;       // 0=aurora, 1=warm, 2=mono

// In fragment shader:
float time = u_time * u_speed;     // scaled time for all noise lookups
// ... after color computation:
color *= u_intensity;

// Palette switching
vec3 paletteAurora(float t) { /* existing blackbody LUT */ }
vec3 paletteWarm(float t)   { /* amber/rose/gold LUT */ }
vec3 paletteMono(float t)   { /* single-hue deepseek-blue LUT */ }

vec3 auroraColor = (u_palette == 0) ? paletteAurora(t) :
                   (u_palette == 1) ? paletteWarm(t) :
                                      paletteMono(t);
```

### 5.4 Persistence

All three values persist in `localStorage` and restore on page load. Defaults: speed=1, intensity=0.85, palette=aurora.

---

## Slice 6: Standalone Demo Mode (from Shaderpark remix culture)

**What**: `scripts/bench-aurora.html` doubles as a standalone demo that anyone can open in a browser — no server, no Bifrost, no dependencies beyond `aurora-shader.js`.

**Why**: Shaderpark's "remix" culture means every shader is forkable. Our aurora should be the same — a self-contained artifact someone could embed in their own project. The benchmark page is the natural home for this.

### 6.1 Features

- Full-viewport aurora running at 60fps
- FPS counter (top-right, monospace, translucent)
- Parameter sliders overlay (bottom-center, glass-panel, auto-hides after 5s of no interaction)
- "Copy GLSL" button (copies the fragment shader source to clipboard)
- "View Source" link (opens `aurora-shader.js` in a new tab)
- State simulation buttons (Normal / Paused / Halted) to demo the state-tint feature

### 6.2 Layout

```
┌─────────────────────────────────────────────────────────┐
│                                              [FPS: 60]  │
│                                                         │
│                    (aurora canvas)                       │
│                                                         │
│  ┌─ glass panel (auto-hides) ────────────────────────┐  │
│  │  Speed: [═══════╪════════] 1.0×                    │  │
│  │  Intensity: [══════════╪═══] 0.85                  │  │
│  │  Palette: ◉ aurora  ○ warm  ○ mono                │  │
│  │  State:   [Normal] [Paused] [Halted]               │  │
│  │  [Copy GLSL]  [View Source]                        │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 6.3 No Build Step

`bench-aurora.html` is a single self-contained HTML file. It loads `aurora-shader.js` via a relative `<script>` tag. No bundler, no npm, no build step — consistent with the rest of the Bifrost UI philosophy.

---

## Implementation Order (Updated)

```
1. Slice 2.1-2.6: HUD Strip (no dependencies, pure DOM)
   └── Backend: `since` already exists (ts field in set_activity) — zero backend change
   └── Frontend: renderHUD(), HTML div, applyStatus integration, elapsed-time from ts
   └── Settings panel toggle

2. Slice 1.1-1.8: Aurora Shader (Claude's slice, built on my GLSL draft)
   └── aurora-shader.js (standalone, includes vignette pass + palette LUTs)
   └── CSS integration (replace pseudo-elements)
   └── State integration (pass paused/halted to shader)
   └── Radial vignette pass (from Awwwards hero pattern)

3. Slice 3.1-3.2: Benchmark & Gate
   └── scripts/bench-aurora.html (standalone demo + perf harness)
   └── Feature flags + settings panel
   └── Benchmark PASS → wire shader into bifrost_ui.py

4. Slice 5: Shader Parameter Controls
   └── Speed/intensity/palette sliders in settings panel
   └── Live uniform update (no recompilation)
   └── localStorage persistence

5. Slice 4: Progressive rollout
   └── Default-off → benchmark PASS → default-on for WebGL2 users

6. Slice 6: Standalone Demo Polish
   └── auto-hide controls overlay, Copy GLSL, state simulation buttons
   └── (can ship independently — doesn't block anything)
```

---

## Success Criteria (Updated)

- [x] ~~Add `since` to activities~~ **already exists** — `ts` field in `set_activity()` / `get_activities()` / `/status`
- [ ] Aurora shader renders at 60fps on integrated GPU (Intel UHD 620 or equivalent)
- [ ] Aurora shader pauses when tab is hidden (zero CPU/GPU usage)
- [ ] Aurora shader falls back to CSS gradients when WebGL2 unavailable
- [ ] Aurora shader has radial vignette pass for center-text legibility
- [ ] Aurora shader palette restricted to our 5 named colors (no ad-hoc RGB)
- [ ] HUD strip shows accurate, real-time agent activity with elapsed-time badges
- [ ] HUD strip rows animate smoothly on state changes
- [ ] HUD strip is keyboard-navigable (tab through rows)
- [ ] Both features have settings-panel toggles that persist across sessions
- [ ] Shader speed/intensity/palette controls functional and persisted
- [ ] `bench-aurora.html` reports PASS on developer machine AND works as standalone demo
- [ ] No regression: existing UI (pills, messages, composer, launcher) functions unchanged
- [ ] No layout shift: HUD strip has reserved space even when empty (prevents log jump)
