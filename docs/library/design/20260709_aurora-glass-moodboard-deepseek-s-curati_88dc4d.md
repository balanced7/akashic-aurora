---
akashic_id: art_20260709_aurora-glass-moodboard-deepseek-s-curati_88dc4d
akashic_sha: 8ef94e75b4ed
status: fossil
type: design
date: 2026-07-09
title: "Aurora Glass Moodboard — DeepSeek's Curation"
gist: "> **Role for this parallel task**: Engine/motion primitives + HUD information design. > My curated references lean into the tech stack (WebG"
tenant: solo
visibility: fleet
seats: []
category: [ui, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_aurora-glass-moodboard-deepseek-s-curati_88dc4d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Aurora Glass Moodboard — DeepSeek's Curation

> **Role for this parallel task**: Engine/motion primitives + HUD information design.
> My curated references lean into the tech stack (WebGL shader architecture, performance benchmarks, GLSL noise primitives), the hardware-anchor design language (Razer's conic-accent geometry + Chroma RGB), and HUD glanceability patterns from sci-fi game UI / mission-control dashboards. Claude is covering the softer Apple/glass side.

---

## Reference 1: Razer Synapse/Chroma Hardware Design Language

**Source**: Razer Blade laptops, Razer Huntsman keyboards, Razer Synapse 3 software UI, Razer Chroma RGB ecosystem. Observable in every product shot and the Synapse control panel.

**What to steal**:
- **Conic accent geometry**: Razer's products universally use a distinct ~12° angular chamfer at edges. Not rounded, not sharp-90° — a precise bevel that catches light asymmetrically. Translates to CSS as `border-radius: 2px 14px 14px 14px` or the equivalent `clip-path` — a single sharp corner opposite three rounded ones. This is the "Razer accent" we already prototyped in the bubble corners (`border-radius: 4px 14px 14px 14px`).
- **Chroma RGB as semantic state**: Razer maps colors to device zones with meaning — green for online/active, cyan for standby, red for alert. We already do this (green=online, amber=paused, red=halt/nudge) but haven't yet made it *ambient*. The next step: the `--glow` radial gradients should shift chroma based on system state (paused → shift toward amber; halted-agent → bleed that agent's danger color into the background glow).
- **Matte black + neon contrast**: The hardware chassis is matte black anodized aluminum; the neon-green USB ports and Chroma strips create extreme contrast. Our `--bg: #0a0b0f` is correct but the glow colors need more saturation — the current `--glow2: rgba(122,162,247,.20)` is too muted for that "Razer neon" pop. Target 0.28-0.35 opacity and higher saturation for the accent glows.

**Palette notes**:
- Razer green: `#44d62c` (the iconic), but they use it sparingly — accent-only. We should reserve a single neon accent for the "shock factor" element (the HUD strip's active indicator).
- Chroma default cycle: `#ff0044` → `#44d62c` → `#0066ff` → `#ffcc00` (they won't sue; these are standard color wheel primaries). Our aurora palette (`claude=#e0915c, deepseek=#7aa2f7, user=#5fd39b`) is more tasteful and differentiated — keep our palette but take the *contrast ratio* from Razer.

**Motion notes**:
- Razer Chroma effects: "Wave" (gradient sweep across zones), "Reactive" (flash on event), "Spectrum Cycling" (slow hue rotation). Spectrum cycling maps perfectly to our `@keyframes ladderSweep` for the fidelity selector border. Consider a slow spectrum cycle (12-16s period) on the `.logo` conic gradient as an idle "breathing" indicator — subtle, not distracting.

---

## Reference 2: WebGL Aurora Borealis Shader (FBM Noise + Curtain Model)

**Source**: [pulkitxm/claude-directory: aurora-borealis-shader](https://github.com/pulkitxm/claude-directory/blob/main/shaders/aurora-borealis-shader/README.md) (Three.js + GLSL), and the classic [Shadertoy aurora examples](https://www.shadertoy.com/) by iq and others.

**What to steal**:
- **FBM (Fractional Brownian Motion) noise** as the single textureless primitive. No image assets, no video — pure math. 4-5 octaves of simplex noise at decreasing amplitude/increasing frequency produce the characteristic aurora "curtain" texture. The key insight for our use case: the noise domain is 2D (screen UV) + 1D time, so the shader is a single fullscreen quad with a fragment shader — no geometry, no textures, no mesh. This is the lightest possible GPU workload for a background effect.
- **Curtain shaping**: Multiply the noise field by a vertical envelope function (e.g., `smoothstep` along Y to create bands, weighted toward the top 40% of the viewport). The aurora doesn't fill the screen — it's concentrated in bands. For our cockpit, shape it to the *margins* (top edge, left/right bleed) so the center remains dark for content legibility.
- **Color mixing**: GLSL `mix()` between a deep green (`#0a3d2e`), teal (`#1a6b5c`), violet (`#4a2c8a`), and the background black, driven by noise value. Our palette should map: `deepseek=#7aa2f7` for the dominant band, `claude=#e0915c` as a secondary warm accent, `aurora-green=#48e6bf` for the transition zone.
- **Motion**: Displace the noise sampling coordinates over time — typically `uv.y + time * 0.05` for vertical drift, plus a sinusoidal horizontal wobble (`uv.x + sin(uv.y * 3.0 + time * 0.3) * 0.02`). The motion should be slow enough to not distract from text, fast enough to register as alive. Target: a full "breath" cycle of 8-12 seconds.

**Performance**: A single fullscreen quad with 5-octave FBM runs at 60fps even on integrated GPUs. The constraint is NOT the GPU — it's avoiding a `requestAnimationFrame` loop that burns CPU/battery when the tab is backgrounded. We MUST gate the render loop on `document.visibilityState` and throttle to 30fps when not visible.

**Palette notes**: The aurora green (`#48e6bf`) should be our "signature" shock-factor color — the one that someone sees in a screenshot and immediately associates with us. Use it sparingly: the aurora bands, the active HUD indicator, and the `.logo` glow. Never use it for body text.

---

## Reference 3: Ubiquiti UniFi Console — Network Dashboard as "Cockpit"

**Source**: UniFi Network Controller (self-hosted or Cloud Key), the dashboard view with topology map and device cards. Widely praised for information density without clutter.

**What to steal**:
- **Glanceability by zone**: The UniFi dashboard divides the screen into horizontal bands — summary stats (top), device grid (middle), alerts (bottom). Each band answers one question at a glance. Our HUD strip should follow this: ONE horizontal strip, positioned above the message log, answering "who's doing what right now?"
- **Status semantics**: UniFi uses a 3-color system: green (adopted/online), yellow (adopting/pending), red (disconnected/error). We already have `--user, --amber, --danger` — the HUD strip should use these exclusively. No purple, no cyan for status — reserve those for agent identity.
- **Compact device cards**: UniFi's device list uses icon + name + IP + status dot + throughput sparkline — all in ~40px height. Our HUD strip should target 28-36px per agent row, showing: agent-avatar → current-action-icon → action-verb → detail-truncation → elapsed-time-badge.
- **The "adoption" animation**: When a new device appears on UniFi, it pulses amber then transitions to green. Our HUD strip should have the same micro-animation: a new agent appearing online → brief glow pulse (0.4s) → settle to steady state.

**Palette**: UniFi is flat/material — we're glass/aurora. Take the *layout pattern* and the *status semantics*, not the visual skin.

---

## Reference 4: Destiny 2 / The Division — Sci-Fi HUD Minimalism

**Source**: Destiny 2 (Bungie) — the Director screen, the character inventory HUD, the mission-end summary. Tom Clancy's The Division (Massive Entertainment) — the orange holographic UI, the ISAC terminal.

**What to steal**:
- **Angular bracket framing**: Destiny 2 uses thin diagonal line segments as "brackets" around HUD elements — never full rectangles, just corner accents. This screams "sci-fi HUD" without the clutter of full borders. Implementation: `border-image` or pseudo-elements with `linear-gradient` to draw only the corners of each HUD element. The Razer angular chamfer + Destiny brackets = our signature frame style.
- **Data density with breathing room**: The Division's ISAC interface packs a lot of data but every element has generous internal padding and a 1px glow separator. Our HUD strip should use `letter-spacing: 0.5px` and generous `padding: 8px 14px` per element — never cramped.
- **The "scan line" motif**: A subtle horizontal line sweep across HUD elements, as if being scanned. This is the single most recognizable sci-fi HUD trope and it's cheap: a CSS `linear-gradient` animation on a pseudo-element, 1px tall, sweeping top-to-bottom over 3-4 seconds. Use it sparingly — only on the HUD strip, not on message content.
- **Faction colors as UI**: Destiny assigns colors to factions (Vanguard=blue, Crucible=red, Gambit=green) and these *saturate* the UI in those contexts. Our equivalent: when a user selects "deepseek" as the target recipient, the composer border and HUD strip tilt toward deepseek-blue; when targeting "claude", shift toward claude-amber. The selected target should *tint* the cockpit — not just a label, but ambient color.

**Palette**: The Division's orange holographic UI (`#f47920` on black) is iconic but one-note. Destiny's faction-color saturation is more applicable to our multi-agent setup.

**Motion**: HUD elements in Destiny have a 0.1-0.2s "snap" ease — fast enough to feel instant, slow enough to register. Our CSS transitions should use `cubic-bezier(0.2, 0.9, 0.3, 1.1)` (the slight overshoot we're already using) for state transitions, and `cubic-bezier(0.4, 0, 0.2, 1)` (Material standard deceleration) for element appearances.

---

## Reference 5: Stripe Dashboard — Agent "Activity Feed" as Timeline

**Source**: Stripe Dashboard — the Developers > Events & Logs view, the payment timeline. Has solved the problem of: "show me what happened, who did it, and whether it succeeded, without making me read prose."

**What to steal**:
- **Event verb taxonomy**: Stripe events are `noun.verb_past_tense` — `charge.succeeded`, `payout.failed`. Our HUD strip should use the same compact grammar: `deepseek.reading | core/comm/bus.py`, `claude.writing | scripts/bifrost_ui.py`, `deepseek.searching | "aurora shader benchmark"`. Verb + target, nothing more.
- **Inline status icons**: Stripe uses a green checkmark or red X inline in the event row — no separate status column. Our HUD rows should show the action icon (📖⚙️🔍✍️) as the leading element, then the verb, then the detail.
- **Relative timestamps**: "2 min ago", "just now". Our elapsed-time badge should use the same — `12s`, `1.4m`, not absolute timestamps.
- **The "expand for detail" chevron**: Stripe lets you click an event to see the full JSON payload. Our HUD strip rows should be clickable — expanding to show the full tool input/output inline (like our existing trace lines but cleaner).

**Palette**: Stripe is blue+white corporate. Ignore their palette; steal only the event-feed information design.

---

## Reference 6: Shadertoy Classic — "Aurora" by iq (Inigo Quilez)

**Source**: [Shadertoy: Aurora by iq](https://www.shadertoy.com/view/XtXXz8) (or similar). Inigo Quilez's work defines the state of the art for procedural sky effects in a single fragment shader.

**What to steal**:
- **Domain warping**: Instead of straight FBM, apply a domain warp — sample the noise at `fbm(uv + fbm(uv + time))`. This creates the characteristic "folded curtain" look of real aurora. An extra FBM sample adds ~10% GPU cost but transforms the output from "cloud noise" to "aurora." Worth it.
- **Color temperature**: iq's aurora uses color *temperature* as the mix axis, not RGB channels directly. Map noise value → blackbody temperature → RGB via a 1D lookup (3-4 keys: 1500K deep red → 4000K green-cyan → 8000K violet → background black). This is physically motivated and produces more natural color transitions than linear RGB mixing.
- **Rayleigh-like vertical falloff**: The aurora intensity should follow an exponential falloff from its peak altitude, scaled by `1.0 / cos(zenith_angle)`. In practice for a flat screen: `intensity *= exp(-abs(y - peak_y) * falloff_rate)`. Creates the characteristic "curtain bottom" brightness with a diffuse top.

**Performance note**: iq's shaders target 60fps on mid-range GPUs. Our use case is simpler (background only, no geometry) so we can afford the domain warp.

---

## Palette Synthesis: The Aurora Glass Palette

| Role | Color | Usage |
|------|-------|-------|
| `--aurora-deep` | `#0a0b0f` | Base background (99% black, not pure) |
| `--aurora-glass` | `rgba(18,20,28,0.55)` | Panel/header backgrounds |
| `--aurora-glow-ds` | `rgba(122,162,247,0.28)` | DeepSeek glow (boost from .20) |
| `--aurora-glow-cl` | `rgba(224,145,92,0.24)` | Claude glow (boost from .16) |
| `--aurora-glow-green` | `rgba(72,230,191,0.22)` | Aurora signature green |
| `--aurora-glow-violet` | `rgba(157,124,247,0.20)` | Aurora edge violet |
| `--aurora-neon` | `#48e6bf` | Shock-factor accent (HUD active, logo pulse) — use SPARINGLY |
| `--razer-accent-angle` | `clip-path` or `border-radius` asymmetry | The 12° chamfer signature |
| `--hud-bracket` | `rgba(122,162,247,0.18)` | Sci-fi corner brackets |
| `--hud-scanline` | `rgba(255,255,255,0.03)` | Subtle HUD scan-line sweep |

---

## Motion Language Synthesis

| Motion | Duration | Easing | Trigger |
|--------|----------|--------|---------|
| Agent status change | 0.4s pulse | `ease-out` | Online/offline/halt transition |
| HUD element appearance | 0.25s | `cubic-bezier(0.2,0.9,0.3,1.1)` | New activity appears |
| Composer focus glow | 0.2s | `ease-out` | Input focused |
| Target-select tint shift | 0.35s | `cubic-bezier(0.4,0,0.2,1)` | Recipient changed |
| Aurora shader cycle | 8-12s | continuous (sinusoidal) | Always (gated on visibility) |
| Scan line sweep | 3-4s | linear | Always (HUD strip only) |
| Fidelity border sweep | 4s | linear (conic-gradient spin) | When fidelity selector active |
| Glass-card expand | 0.22s | `cubic-bezier(0.2,0.9,0.3,1.1)` | Card click |

---

## Principles (from these references)

1. **Darkness is the canvas.** The background must stay *very* dark (`--bg: #0a0b0f`). The aurora adds atmosphere, not illumination. Text must remain readable at all times — never put aurora bands behind body text.
2. **The accent is earned.** Razer green (`#48e6bf`) appears ONLY when something demands attention — a new message, an agent state change, a halt notification. It is not decorative.
3. **Motion is information, not decoration.** Every animation maps to a semantic state change. If it moves without a reason, it's noise.
4. **Glanceability beats detail.** The HUD strip answers "who's doing what" in under 200ms of visual scan. Details are one click away.
5. **Glass is the material, not the message.** The frosted glass (`backdrop-filter: blur(12px)`) provides depth without obscuring content. It separates layers (header vs content vs composer) without heavy borders — the blur IS the separator.
6. **WebGL is the shock factor, not the UI.** The aurora shader runs on a single `<canvas>` behind the entire DOM. The UI (HTML/CSS) does NOT go through WebGL. This separation means the UI stays responsive (no WebGL texture-readback costs) and the shader can be throttled/paused independently.
