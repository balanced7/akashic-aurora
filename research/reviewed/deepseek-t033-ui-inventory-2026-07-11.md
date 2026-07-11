# DeepSeek T033 built-vs-spec inventory (verbatim, committed by claude)

Provenance: bus msg 1783749850451-0 (condensed) + streamed working log (full walk), 2026-07-11
~02:3x. Code-forward half of the T033 fence; claude visual half + fresh OneUI/HIG cache +
reconciliation next session; Daniel rules on spec-vs-vision deltas.

## Condensed (his bus verdict)

The inventory is on the bus. Here's the condensed version for our shared log:

---

## T033 — DeepSeek's Half: Built-vs-Spec Inventory COMPLETE

### FILE: `scripts/bifrost_ui.py` — 2,733 lines; ~2,200 embedded PAGE string

### The Six Composition Spec Items

| # | Spec Item | Status | Line Evidence |
|---|-----------|--------|---------------|
| 1 | Collapse reasoning into ONE card | **NOT BUILT** — T002 unclaimed; traces stream as wall of `.traceline` divs | ~659, ~1202 |
| 2 | One presence surface | **DRIFTED** — THREE surfaces: pills, HUD strip, activity bubbles | ~1630, ~1278, ~1232 |
| 3 | Composer = one focus block | **PARTIAL** — ladder is separate div above `.cwrap` | ~1079 vs ~1073 |
| 4 | 24dp consistent margins | **PARTIAL** — max-width:1180px exists but padding is 14/16/20/24 mix | ~530 |
| 5 | ≤3 top actions | **DRIFTED** — 8 visible header elements | header HTML |
| 6 | Keep (dark/aurora/glass/Razer) | **MOSTLY BUILT** — bench-aurora.html missing, Void unverified | ~538 |

### Unsanctioned Growth: ~2,000+ lines the July 5 spec never anticipated
Launcher panel, fleet pulse, episode system, slide deck cards, presentation registry V2, ash selector, negotiation, narration, file dropzone, settings panel. Each named with line refs in the bus message.

### Port: Not drift
Default is 8787 (line 482). Docstring says 8787. `reload_ui` tool says 8788. "8792" is likely runtime, not hardcoded.

### Top-5 Fixes (Daniel-visible impact / LoC)
1. **CUT HUD + activity** (~250 lines removed) — instant visual calm
2. **T002: collapse reasoning cards** (~50 lines) — the #1 spec restraint
3. **Composer into ONE block** (~30 lines) — highest coherence win
4. **Header overflow menu** (~40 lines) — 8→3 visible actions
5. **Normalize 24dp margins** (~20 CSS values) — cheapest polish

### M8: Spec Items I Believe Are Wrong/Stale
1. **Pills > bubbles** for presence — the spec's "keep message avatars" is the inferior surface
2. **≤3 actions is stale** — predates launcher, episodes, fleet pulse
3. **blur≤14 is wrong** — actual blur(26) looks better on dark-mode; Apple HIG uses ~30
4. **bench-aurora.html as separate file is wrong mechanism** — should be inline benchmark + localStorage flag

## Full walk (streamed log)

ful. Let me now also check my inbox for any messages from Claude, and then summarize my findings here.
DeepSeek: The inventory is on the bus. Here's the condensed version for our shared log:

---

## T033 — DeepSeek's Half: Built-vs-Spec Inventory COMPLETE

### FILE: `scripts/bifrost_ui.py` — 2,733 lines; ~2,200 embedded PAGE string

### The Six Composition Spec Items

| # | Spec Item | Status | Line Evidence |
|---|-----------|--------|---------------|
| 1 | Collapse reasoning into ONE card | **NOT BUILT** — T002 unclaimed; traces stream as wall of `.traceline` divs | ~659, ~1202 |
| 2 | One presence surface | **DRIFTED** — THREE surfaces: pills, HUD strip, activity bubbles | ~1630, ~1278, ~1232 |
| 3 | Composer = one focus block | **PARTIAL** — ladder is separate div above `.cwrap` | ~1079 vs ~1073 |
| 4 | 24dp consistent margins | **PARTIAL** — max-width:1180px exists but padding is 14/16/20/24 mix | ~530 |
| 5 | ≤3 top actions | **DRIFTED** — 8 visible header elements | header HTML |
| 6 | Keep (dark/aurora/glass/Razer) | **MOSTLY BUILT** — bench-aurora.html missing, Void unverified | ~538 |

### Unsanctioned Growth: ~2,000+ lines the July 5 spec never anticipated
Launcher panel, fleet pulse, episode system, slide deck cards, presentation registry V2, ash selector, negotiation, narration, file dropzone, settings panel. Each named with line refs in the bus message.

### Port: Not drift
Default is 8787 (line 482). Docstring says 8787. `reload_ui` tool says 8788. "8792" is likely runtime, not hardcoded.

### Top-5 Fixes (Daniel-visible impact / LoC)
1. **CUT HUD + activity** (~250 lines removed) — instant visual calm
2. **T002: collapse reasoning cards** (~50 lines) — the #1 spec restraint
3. **Composer into ONE block** (~30 lines) — highest coherence win
4. **Header overflow menu** (~40 lines) — 8→3 visible actions
5. **Normalize 24dp margins** (~20 CSS values) — cheapest polish

### M8: Spec Items I Believe Are Wrong/Stale
1. **Pills > bubbles** for presence — the spec's "keep message avatars" is the inferior surface
2. **≤3 actions is stale** — predates launcher, episodes, fleet pulse
3. **blur≤14 is wrong** — actual blur(26) looks better on dark-mode; Apple HIG uses ~30
4. **bench-aurora.html as separate file is wrong mechanism** — should be inline benchmark + localStorage flag