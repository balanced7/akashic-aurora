---
akashic_id: art_20260801_ui-motion-conversion-deepseek-ui_134385
akashic_sha: d5fce29d5cec
schema_version: 1
status: current
type: report
date: 2026-08-01
title: ui-motion-conversion-deepseek-ui
gist: "# UI motion budget — non-composited keyframe conversion (deepseek-ui) Status: current (2026-08-01). Verbatim capture from the PRIVATE uiwork"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [library, recall, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T19:40:39"
updated: "2026-08-01T19:40:39"
---
<!-- GENERATED PROJECTION of art_20260801_ui-motion-conversion-deepseek-ui_134385 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# ui-motion-conversion-deepseek-ui

# UI motion budget — non-composited keyframe conversion (deepseek-ui)

Status: current (2026-08-01). Verbatim capture from the PRIVATE uiwork namespace.

Author: deepseek-ui — a READ-ONLY seat (caps: read/bus.send/kb.recall/git.read).
It cannot file its own work; landed by claude#4389005f. Third instance today of the
no-exec filing gap (kimi, deepseek, now deepseek-ui).

Brief: design/CONTRACT.md v1 motion budget — convert the 11 keyframes animating
non-composited properties (box-shadow/filter/border/top/width) to transform+opacity.

Stream 1785626553246-0 · sha 2e63e27ff4c7f97e · 10816 chars

---

`rpulse` is dead code — defined, never applied. Now I have the full picture. Here's the conversion:

---

## Per-keyframe conversion

### 1. `chroma-breath` (lines 1158–1161) + `chroma-breath-c/d/u` (lines 1165–1167)

**Applied to:** `#ash-frame` — the composer's primary button (34×34px). This is the highest-value conversion because it runs *always* on an always-visible element.

**Technique:** `::after` ring that scales+fades. The markup needs `position:relative` (already present at line 1156). The `::after` ring replaces the expanding `box-shadow`; the `::before` (new) replaces the `inset` glow.

**REPLACE lines 1158–1167:**

```css
  /* chroma-breath — composited: ::before=inner glow, ::after=outer ring, both scale+fade */
  #ash-frame::before,#ash-frame::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none}
  #ash-frame::before{opacity:0; box-shadow:inset 0 0 6px 0 rgba(122,162,247,.08)}  /* sits still, only fades */
  #ash-frame::after{opacity:0; border-radius:inherit; border:2px solid transparent; transform:scale(.92)}
  @keyframes chroma-breathe-inner{0%,100%{opacity:0}50%{opacity:1}}
  @keyframes chroma-breathe-outer{0%,100%{opacity:.3;transform:scale(.92)}50%{opacity:.8;transform:scale(1.12)}}
  #ash-frame.chroma-claude::before{animation:chroma-breathe-inner 2.2s ease-in-out infinite; box-shadow:inset 0 0 8px 0 rgba(224,145,92,.12)}
  #ash-frame.chroma-claude::after{animation:chroma-breathe-outer 2.2s ease-in-out infinite; border-color:rgba(224,145,92,.42)}
  #ash-frame.chroma-deepseek::before{animation:chroma-breathe-inner 2.2s ease-in-out infinite; box-shadow:inset 0 0 8px 0 rgba(122,162,247,.14)}
  #ash-frame.chroma-deepseek::after{animation:chroma-breathe-outer 2.2s ease-in-out infinite; border-color:rgba(122,162,247,.48)}
  #ash-frame.chroma-user::before{animation:chroma-breathe-inner 2.2s ease-in-out infinite; box-shadow:inset 0 0 8px 0 rgba(95,211,155,.11)}
  #ash-frame.chroma-user::after{animation:chroma-breathe-outer 2.2s ease-in-out infinite; border-color:rgba(95,211,155,.38)}
```

**Visual fidelity caveat:** The original had both a growing outer *box-shadow* AND a growing inner *inset* glow. `::after` handles the outer ring (scale+fade border), `::before` handles the inner glow (fading its `box-shadow`). This means the inner glow pulses opacity but doesn't *grow*. The inner-glow growth is the one loss here — the inset shadow sits static at max size and only fades opacity. A true growing inset glow with transforms alone isn't possible on a single pseudo; adding a third element would require a real child. **The outer ring is preserved fully; the inner glow pulses but doesn't expand.** I'd call this an acceptable trade — the dominant visual signature (the colored halo ring) survives intact and is *more* legible at scale.

**Lines 1162–1164** (the `.chroma-*` rules that applied the old keyframes) are **absorbed** by the new block above — delete them.

### 2. `fpulseRed` (line 703) + `fpulseRing` (line 704)

**Applied to:** `.fpulse.red` + `.fpulse.red::after` — the fleet-pulse dot in the header. Only runs when the fleet is in alarm (red). This is ≤1 element at a time — not fleet-scaled.

**Technique:** The dot already has `::after` for the static ring. Convert both to `transform:scale` on `::after` only (the dot itself fades its shadow via `opacity`).

**REPLACE lines 701–705:**

```css
  .fpulse.red{background:var(--danger); box-shadow:0 0 10px rgba(240,102,110,.5)}
  .fpulse.red::after{border-color:rgba(240,102,110,.35); animation:fpulse-ring 1.2s ease-in-out infinite}
  @keyframes fpulse-ring{0%,100%{opacity:.5;transform:scale(1)}50%{opacity:1;transform:scale(1.5)}}
```

**Visual change:** The original `fpulseRed` pulsed the dot's `box-shadow` intensity (paint-only). The new version drops the dot's own animation entirely — the static `box-shadow` at 10px is close to the midpoint of the old pulse. The `::after` ring now scales+fades instead of growing its `inset` from -4px to -6px. **What's lost:** the dot's own box-shadow no longer breathes — only the ring does. If that matters, the dot's shadow could pulse via `opacity` on a `::before` on the dot, but that's a third pseudo for a 12px dot. I judge the single ring pulse sufficient for "fleet alarm."

Delete line 705 (`@media (prefers-reduced-motion:reduce)` guard) — the global floor at line ~724 already covers it.

### 3. `gpulse` (line 1096)

**Applied to:** `.gcard.nudged` and `.icube.nudged` — glass-card tiles and iso-cube tiles when an agent is nudged. Scales per-agent in the tile view. **FLAG: this is the one that scales with roster.** If you have 11 agents all nudged simultaneously, that's 11 concurrent animations. Still within the 24 ceiling, but worth noting.

**Technique:** `::after` ring that scales+fades.

**Requires markup:** `.gcard` already has no `::after` in use. `.icube-front` is the applied element; it is a child of `.icube-inner` (3D transform context). A pseudo on `.icube-front` works in 3D but may render oddly — test visually.

**REPLACE lines 1094–1096:**

```css
  .gcard.nudged{border-color:rgba(240,102,110,.4); position:relative}
  .gcard.nudged::after{content:""; position:absolute; inset:-3px; border-radius:inherit; border:2px solid transparent; pointer-events:none; animation:gpulse-ring 1.5s ease-in-out infinite}
  @keyframes gpulse-ring{0%,100%{opacity:.25;transform:scale(.96)}50%{opacity:.8;transform:scale(1.04)}}
```

For `.icube.nudged` (line 1133), same keyframe but different pseudo placement — the iso-cube front face is in a 3D transform context:

**REPLACE line 1133:**

```css
  .icube.nudged .icube-front{border-color:rgba(240,102,110,.55); position:relative}
  .icube.nudged .icube-front::after{content:""; position:absolute; inset:-4px; border-radius:inherit; border:2px solid rgba(240,102,110,.45); pointer-events:none; animation:gpulse-ring 1.5s ease-in-out infinite}
```

Reuse `gpulse-ring` from above. Delete the old 1096 `@keyframes gpulse`.

### 4. `rpulse` (line 947)

**DEAD CODE.** Defined at line 947, never applied to any selector. Delete it, no replacement.

### 5. `hudPulse` (line 862) — `filter: drop-shadow`

**Applied to:** `.hrow.just-started .hicon` — the icon inside a HUD row when an activity first starts. Runs briefly (0.55s, ease-out, one-shot). Not an infinite loop, so it doesn't hit the perf budget continuously — but `filter` still triggers a paint every frame it runs.

**Technique:** The icon is a `<span class="hicon">` with an emoji inside. `filter:drop-shadow` on text can be approximated with `text-shadow` (still paint, but cheaper than filter) OR with `opacity` + a subtle `transform:scale` pulse on the icon.

Since this is a one-shot (not infinite), the perf cost is negligible. **I recommend leaving it as-is** and noting it in the contract as exempt: one-shot `<1s` animations on `filter` that finish and never loop are not the 60fps problem. The contract's "never filter in a loop" rule doesn't technically apply.

But if you want purity, the equivalent:

```css
  @keyframes hudPulse{0%{opacity:.6;transform:scale(.9)}40%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:scale(1)}}
```

**Caveat:** this loses the neon-green glow color. The glow was the point — it signalled a *new* activity with aurora-neon. A plain scale pulse is generic. **I'd exempt this from conversion.**

### 6. `hudScan` (line 863) — `top` animation

**Applied to:** `#hud::after` — the sci-fi scan line sweeping down the HUD strip. **Layout every frame** — animating `top` from 0 to 100%.

**Technique:** Use `transform:translateY` instead. The `::after` is positioned absolute; `top:0` is the baseline, and we translate from 0 to the container's height.

**REPLACE lines 858–863:**

```css
  #hud::after{content:""; position:absolute; top:0; left:0;right:0; height:1px; pointer-events:none;
    background:var(--hud-scanline, rgba(255,255,255,.025));
    animation:hudScan 3.8s linear infinite}
  @keyframes hudScan{from{transform:translateY(0)}to{transform:translateY(100vh)}}
```

Wait — `100vh` is wrong. The `#hud` has `max-height:148px`. Using `100%` in a `translateY` refers to the element's own height (1px), not the parent's. The correct approach uses the parent's height: `translateY(148px)` for the max, or `calc(148px)`.

Better: since `#hud` is a flex column with variable height, we need to translate by the container's actual height. Pure CSS can't do `translateY(100% of parent)`. The workaround: animate `transform:translateY(0)` to `transform:translateY(148px)` (the max-height). The scan line will stop at 148px regardless of actual content height — close enough for a 1px subtle line.

```css
  @keyframes hudScan{from{transform:translateY(0)}to{transform:translateY(148px)}}
```

**Caveat:** If the HUD is collapsed (38px) or empty, the scan line overshoots into invisible space. Since the `#hud` has `overflow-y:auto`, the extra travel is clipped. Acceptable.

### 7. `pmeter` (presence-rail.js, line 32) — `width` + `margin-left`

**Applied to:** `.pmeter i` — a progress bar sweep inside the presence-rail cards. **Layout every frame.**

**Technique:** A fixed-width bar with `transform:translateX` sweeping across, masked by `overflow:hidden` on the parent.

**REPLACE in presence-rail.js lines 31–33:**

```css
    '@keyframes pmeter{0%,100%{transform:translateX(-72%)}50%{transform:translateX(15%)}}' +
```

And change `.pmeter i` from width-based to fixed-width:

```css
    '.pmeter i{display:block;height:100%;width:60%;border-radius:3px;background:linear-gradient(90deg,var(--deepseek,#7aa2f7),var(--user,#5fd39b));animation:pmeter 1.7s ease-in-out infinite}' +
```

The bar is 60% wide and sweeps from `-72%` (mostly off-screen left) to `+15%` (slightly past center). Since `.pmeter` has `overflow:hidden`, the ends clip naturally. The visual result is nearly identical to the width+pull sweep.

**Reduced-motion fallback** (line 33): change to `'.pmeter i{animation:none;transform:translateX(-15%)}'`.

---

## Motion budget flag

`gpulse` is the only animation that **scales with fleet size** — one per nudged agent in the tile/isocube view. At 11 agents all nudged, that's 11 of 24 budget. Manageable. All others are singleton elements (one fpulse, one ash-frame, one hud scan, one pmeter per rail card visible — and the rail is capped by viewport).

## Summary of lines to touch

| Keyframe | File | Lines to replace |
|---|---|---|
| chroma-breath + c/d/u | bifrost_ui.py | 1158–1167 (delete), new block after 1157 |
| fpulseRed + fpulseRing | bifrost_ui.py | 701–705 |
| gpulse | bifrost_ui.py | 1094–1096, 1133 |
| rpulse | bifrost_ui.py | 947 (delete) |
| hudPulse | bifrost_ui.py | 862 (recommend: exempt) |
| hudScan | bifrost_ui.py | 860, 863 |
| pmeter | presence-rail.js | 31–33 + the `.pmeter i` rule |
