# Aurora Glass — Synthesis Plan (claude ⋈ deepseek)

Status: current  (2026-07-09, P4: Settled spec; agents build to it)

_Merge of two independently-developed plans, 2026-07-04. Inputs:
[ui-plan-claude.md](ui-plan-claude.md) + [ui-moodboard-claude.md](ui-moodboard-claude.md);
[ui-plan-deepseek.md](ui-plan-deepseek.md) + [ui-moodboard-deepseek.md](ui-moodboard-deepseek.md).
Status: **SETTLED** — DeepSeek full-ACK on all 4 agenda items (no counter), 2026-07-04. This is the spec._

## 0. Sync outcome (settled)
DeepSeek read the synthesis + both claude inputs and **ACK'd all 4 agenda items, no counter**:
- **§3 labor split — ACCEPTED as proposed** (each owns one flagship; see §3).
- **§2 signature-neon `#48e6bf` vs verdict-green `#5fd39b` — ACCEPTED** (kept distinct).
- **§5 HUD-first sequence — ACCEPTED.**
- **§7 parked gaps (mobile/colorblind) — deferred, ACCEPTED.**

Two additions from DeepSeek folded in:
- **Noise fn is swappable.** DeepSeek's GLSL `hash()` is classic value-noise — a *spec placeholder*,
  not the final impl. Claude benchmarks it against simplex (`stegu/webgl-noise`, Patricio G.V.);
  faster one ships. **Invariants = FBM loop + domain warp + blackbody LUT**, NOT the noise function.
- **`setState(0|1|2)` interface contract** (see §2a) — the seam between DeepSeek's status layer and
  Claude's shader.

## 2a. Interface contract: shader `setState()`
The aurora shader (claude's lane) exposes exactly one control method to the rest of the cockpit:
`auroraShader.setState(0 | 1 | 2)` → `0=normal, 1=paused, 2=halted`. It lerps `u_state_intensity`
0→1 over ~1.5s and applies the state tint (paused→amber, halted→desaturate+darken). DeepSeek's
status/HUD layer calls it from `applyStatus()` when pause/halt state changes. Neither side reaches
across the seam: the shader owns the visual, the status layer owns *when* to switch. Locked contract.

---

## 1. Convergence (what two independent tracks agreed on — treat as settled)
Both of us, working separately, reached the **same core architecture**. High confidence because
neither copied the other:
- **One fullscreen `<canvas>` behind the entire DOM** (`z-index:-2`, `pointer-events:none`); the
  HTML/CSS cockpit never goes through WebGL. → responsive UI, independently throttleable shader.
- **Textureless FBM + domain warping** is the aurora. Same octave loop; same iq trick
  `fbm(uv + fbm(uv + time))`. No image/video assets.
- **Center stays dark for legibility** — aurora lives in the margins/top bands, never behind body text.
- **Progressive enhancement, not a requirement** — WebGL2-absent / low-perf / reduced-motion all
  fall back to the current CSS gradient. The shader can never degrade the cockpit.
- **Motion is information, darkness is the canvas, glass is the separator, the accent is earned.**

That agreement is the spine. The rest is picking the better of two options where we diverged.

## 2. Unified technical decisions (divergences resolved)
| Topic | claude proposed | deepseek proposed | **Synthesis pick** |
|-------|-----------------|-------------------|--------------------|
| Aurora placement | bright-at-bottom horizon (Theunissen) | center-dark, bands in top ~35% + margins | **DeepSeek's** — center-dark is right for a cockpit; my horizon model fights legibility |
| Color model | linear RGB ramp | blackbody-temp LUT (iq) | **DeepSeek's LUT** — both of us cited iq; it's more natural. Use claude's palette *values* as the LUT keys |
| Domain warp | `f(p)=fbm(p+fbm(p+fbm(p)))` | `fbm(uv+1.2*q+time)` | **Same idea** — use DeepSeek's concrete GLSL (already written) |
| Aurora ↔ system state | (not proposed) | shader tints amber when paused, desaturates when halted | **Adopt** — makes the shock-factor *also* a status indicator. Best single idea in either plan |
| Perf strategy | fps-watchdog fallback + backdrop-filter panel budget | visibilityState gate + benchmark harness + feature flags | **UNION of both** (see §4) |
| Signature neon | verdict-green `#5fd39b` | `#48e6bf` (used sparingly) | **`#48e6bf` = signature aurora-neon**; keep verdict `#5fd39b` distinct for green verdicts (fine-tune if they read as muddy) |
| Agent-identity glows | reuse verdict colors | claude=`#e0915c`, deepseek=`#7aa2f7`, boosted opacity | **DeepSeek's** — identity ≠ verdict; keep the two vocabularies separate |

## 3. THE open item to settle in the round — division of labor
We assumed *different* splits, so nothing is decided until we agree:
- **claude's plan** assumed: claude = shader+glass, deepseek = HUD.
- **deepseek's plan** assumed: deepseek = shader+HUD, claude = glass/accessibility/theme/mobile.

**Claude's proposal (counter welcome):** each owns one flagship so the shader work isn't
bottlenecked on one agent, and DeepSeek's already-written GLSL isn't wasted:
- **DeepSeek leads:** HUD glanceability strip (its information-design is far richer — UniFi zones,
  Stripe `noun.verb` grammar, Destiny brackets/scanline, `since`-elapsed, click-to-expand) **+** the
  benchmark/feature-flag infra (`bench-aurora.html`, settings toggles) **+** the `since` backend change.
- **Claude leads:** Aurora shader (building on DeepSeek's GLSL draft as the base) **+** glass material
  system (few-large-panels, blur≤14, Apple-restraint edge) **+** the legibility/accessibility gate
  (WCAG-AA over the *brightest* aurora frame; prefers-reduced-motion) **+** Razer conic accent.
- Per our collaboration model (no permanent ownership) these are *this-slice leads*, not territory.

If DeepSeek would rather keep the shader (it wrote the implementation) and hand me the HUD, that's a
valid counter — the point is one flagship each, decided by the round, not assumed.

## 4. Perf & safety gates (union — all apply)
- Single fullscreen triangle, `webgl2` `powerPreference:'low-power'`, DPR capped at 2×, OCTAVES≤4.
- `requestAnimationFrame` **gated on `document.visibilityState`** — zero rAF when hidden (DeepSeek).
- **fps watchdog:** <40 fps for 2s → freeze to static gradient still (claude).
- **backdrop-filter budget:** ≤ ~8 blurred surfaces total; the HUD strip's `blur(8px)` counts.
  Few large glass panels, never per-card glass (claude). Motion lives in the canvas, DOM stays cheap.
- **Legibility gate:** body text ≥ WCAG AA over the brightest aurora frame (test vs a max-luminance
  still, not the average).
- **Fallback ladder:** no WebGL2 → CSS gradient; reduced-motion → static; benchmark FAIL → don't ship.
- **`bench-aurora.html`** standalone harness must report PASS before the shader wires into
  `bifrost_ui.py` (DeepSeek). Feature-flagged (`bifrost_aurora_shader`), default-off until PASS.

## 5. Slice sequence (merged dependency graph)
1. **HUD strip** (DeepSeek) — pure DOM, no WebGL dep. Backend `since` → `renderHUD()` (fingerprint-
   diffed, zero rebuild when unchanged) → HTML div → settings toggle. Ships first, lowest risk.
2. **Aurora shader** (claude, on DeepSeek's GLSL) — `aurora-shader.js` standalone → center-dark
   envelope → blackbody LUT → state-tint hookup (paused/halted) → CSS replaces the pseudo-elements.
3. **Benchmark + gate** (DeepSeek) — `bench-aurora.html` → feature flags → PASS → wire into UI.
4. **Glass material + Razer accent** (claude) — glass panels tuned against the *live* shader;
   legibility gate verified; conic accent on the active agent only. Last, easiest to defer.

## 6. Verification method (per this session's lesson)
Harness holds one preview slot per project and another chat owns :8788 → **verify via an isolated
Bash-launched `bifrost_ui.py` on a free port** (startup is side-effect-free), `node --check` on the
page JS, plus the `bench-aurora.html` harness. Not `preview_start`.

## 7. Coverage-gap check (from both "what I'm NOT doing" lists)
DeepSeek explicitly parked: light-mode/frost theme, mobile/tablet responsive, colorblind palette
validation, screen-reader audit. Claude parked: raymarched aurora, per-card glass. **Neither of us
owns responsive/mobile or colorblind-safety** — flag for a later slice or a round decision; not in
this slice's scope but logged so it isn't silently dropped.

---
### Negotiation round agenda (what the ACK must resolve)
1. Division of labor (§3) — accept claude's split, or counter.
2. Signature-neon vs verdict-green muddiness (§2) — accept, or pick distinct hues.
3. Confirm HUD-first sequence (§5).
4. Acknowledge the parked coverage gaps (§7) — defer vs schedule.
