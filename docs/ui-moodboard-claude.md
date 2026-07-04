# Aurora Glass — Supporting Art & References (claude track)

_Gathered 2026-07-04 for the parallel UI-design task. Companion: [ui-plan-claude.md](ui-plan-claude.md).
DeepSeek's independent set: ui-moodboard-deepseek.md. Synthesis: ui-plan-synthesis.md._

## Direction (recap, so the references have a target)
Dark frosted glass + neon aurora + Razer conic accent. Anchors: **Ubiquity** (dense-but-calm
telemetry), **Apple** (Liquid Glass depth/restraint), **Razer** (neon energy, conic motion).
The "shock factor" remaining item = a **WebGL aurora shader** (single canvas, FBM noise, replacing
the CSS background) + a **HUD glanceability strip** (who's-doing-what at a glance).

---

## Reference set — source + what to steal

### A. The aurora itself (shader art)
1. **Shadertoy "Auroras" — shadertoy.com/view/XtGGRt** — the canonical look: vertical curtains,
   color banding (green→violet), soft vertical falloff. *Steal:* the silhouette and palette ramp.
   *Reject:* it raymarches a 2D noise map extruded volumetrically — too expensive for an always-on
   background. We flatten it to a **2D FBM curtain**, no raymarch (see plan Slice A perf gate).
2. **Book of Shaders ch.13 (FBM) — thebookofshaders.com/13/** — the actual algorithm we build on:
   ```glsl
   for (int i = 0; i < OCTAVES; i++) { value += amplitude * noise(st); st *= 2.0; amplitude *= 0.5; }
   ```
   *Steal:* **Inigo Quilez domain-warping** `f(p) = fbm(p + fbm(p + fbm(p)))` — this is what makes
   the curtain *flow and ripple* instead of sitting static. One extra `u_time` term in the inner
   warp = animation for near-free. Also `abs(noise())` (turbulence) for the sharp aurora "ribs".
3. **stegu/webgl-noise — stegu.github.io/webgl-noise** + **Patricio G.V. GLSL noise gist**
   (gist 670c22f3966e662d2f83) — drop-in simplex/Perlin GLSL, no texture lookups (mobile-safe).
   *Steal:* `snoise(vec2)` verbatim; it's the noise() the FBM loop calls.
4. **Roy Theunissen — "Aurora Borealis: A Breakdown"** (blog.roytheunissen.com, 2022-09-17) —
   art-direction breakdown. *Steal:* vertical gradient mask (bright at horizon, fade up), additive
   color blending, gentle horizontal drift. This is the "how do I make noise *read* as aurora" doc.

### B. The glass (frosted layer over the shader)
5. **"Dark Glassmorphism: the aesthetic that will define UI in 2026"** (Medium, MustBeWebCode) +
   **everydayux — Apple Liquid Glass** — 2025/26 dark-glass is *moody, dark-mode-native*, built on
   **ambient gradient orbs**: vibrant blobs (deep purple, neon blue, hot pink) floating BEHIND the
   glass. *Steal:* our aurora shader **is** the ambient light source — the glass panels catch its
   glow. That's the whole trick: one animated light bed, many static glass readers on top.
   *Constraint (critical):* `backdrop-filter: blur()` is GPU-heavy — "50 glass cards = fans spin
   up." Ties to our existing lesson (static-aurora perf fix). Mitigation: **few large glass panels,
   not many small ones**; blur ≤ ~14px; the *motion* lives in the single canvas, the DOM stays cheap.
6. **Apple Liquid Glass (WWDC 2025, iOS 26 / macOS Tahoe)** — the restraint anchor: depth via
   translucency + a thin bright edge, NOT heavy shadow. *Steal:* 1px inner highlight border
   (`inset 0 1px 0 rgba(255,255,255,.12)`), low-opacity fills, saturation bump (`saturate(1.2)`)
   so the aurora color bleeds through richly.

### C. The Razer accent (energy)
7. **Razer Chroma Design Guide — chroma.razer.com/ChromaGuide** + **Gradient editor
   (chroma.razer.com/ChromaEditor/gradient)** — Razer's language is **color-stop gradients in
   motion**: points/"stops", each a different hue, animated along a path. *Steal:* the **conic
   accent** on active/focus elements (the recipient avatar ring, the runner indicator) — a
   `conic-gradient` sweep that rotates on the currently-active agent. One accent, used sparingly,
   is the Razer "signature" without turning the cockpit into an RGB gamer toy.

---

## Palette (near-black bed, neon light-leaks)
| Role | Value | Use |
|------|-------|-----|
| Void | `#06070d` | base canvas below the aurora |
| Aurora green | `#5fd39b` | primary curtain band (matches our existing green verdict) |
| Aurora cyan | `#7aa2f7` | mid band (matches deepseek avatar) |
| Aurora violet | `#9d7cf7` | upper band fade |
| Hot-pink leak | `#f0666e` | sparse accent / red-verdict / alert (matches existing red) |
| Glass fill | `rgba(20,24,38,.42)` | panel background over the shader |
| Glass edge | `rgba(255,255,255,.12)` | 1px inner highlight |

Deliberately reuses our existing verdict colors (green/amber/red) so the aesthetic and the
signalling vocabulary are the same language.

## Motion language
- **Aurora:** slow vertical drift + domain-warp ripple, ~0.05–0.1 u_time scale. Hypnotic, not busy.
- **Glass:** static. Motion is the light bed showing THROUGH it, never the panels themselves.
- **Accent:** conic sweep only on the *active* agent (runner/steer target). Everything else is calm.

## The one big idea the references converge on
**Separate the moving light from the readable surface.** id-tech/Doom lesson (main thread stays
cheap) + dark-glass 2026 (ambient orbs behind glass) + our own static-aurora perf fix all point the
same way: **one cheap animated canvas as the light source; the DOM/glass is static and reads it.**
That resolves the tension between "shock factor" (motion) and "glanceable cockpit" (calm/legible).

## Sources
- [Shadertoy Auroras](https://www.shadertoy.com/view/XtGGRt) · [Book of Shaders FBM](https://thebookofshaders.com/13/) · [webgl-noise](https://stegu.github.io/webgl-noise/webdemo/) · [GLSL noise gist](https://gist.github.com/patriciogonzalezvivo/670c22f3966e662d2f83)
- [Aurora breakdown (Theunissen)](https://blog.roytheunissen.com/2022/09/17/aurora-borealis-a-breakdown/) · [Dark Glassmorphism 2026](https://medium.com/@developer_89726/dark-glassmorphism-the-aesthetic-that-will-define-ui-in-2026-93aa4153088f) · [Apple Liquid Glass](https://www.everydayux.net/glassmorphism-apple-liquid-glass-interface-design/)
- [Razer Chroma Design Guide](https://chroma.razer.com/ChromaGuide/) · [Razer gradient editor](https://chroma.razer.com/ChromaEditor/gradient/)
