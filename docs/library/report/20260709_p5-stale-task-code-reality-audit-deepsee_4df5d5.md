---
akashic_id: art_20260709_p5-stale-task-code-reality-audit-deepsee_4df5d5
akashic_sha: a71f5ccbdb08
status: draft
type: report
date: 2026-07-09
title: P5 stale-task code-reality audit -- DeepSeek (verbatim)
gist: "# P5 stale-task code-reality audit -- DeepSeek (verbatim) T025 seat: T002-T007 audited against the code as it is today; evidence for Daniel "
tenant: solo
visibility: fleet
seats: []
category: [memory, agent-lifecycle, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:49:02"
updated: "2026-07-09T23:49:02"
---
<!-- GENERATED PROJECTION of art_20260709_p5-stale-task-code-reality-audit-deepsee_4df5d5 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# P5 stale-task code-reality audit -- DeepSeek (verbatim)

# P5 stale-task code-reality audit -- DeepSeek (verbatim)

T025 seat: T002-T007 audited against the code as it is today; evidence for Daniel verdicts.

---

Now I have the full picture. Here's the audit:

---

## T025 / P5 Seat: CODE-REALITY AUDIT — Six Stale Proposed Tasks

### T002 — UI: collapse agent reasoning + tool traces into ONE collapsible card

**(1) ALREADY SATISFIED?** **No.** The code has trace lines (`.traceline`, line 659) and activity bubbles (`.actrow`/`.actbubble`, lines 666-674) that render agent reasoning and tool traces as a streaming wall-of-text. There is NO "reasoning card" that groups consecutive traces per agent and collapses them to a summary line. The `ui-composition-spec.md` (lines 17-18) explicitly calls for: "Group consecutive traces per agent into ONE collapsible 'reasoning card' — collapsed by default to a single line (`💭 deepseek reasoning · 6 steps ▸`), expand on click." This is **not yet implemented**.

**(2) STILL COHERENT?** **Yes.** `ui-composition-spec.md` is stamped CURRENT. `scripts/bifrost_ui.py` is the file to edit (line 1132 composer, log at line 612, activity at line 666). The spec's lane assignment (deepseek-plumbing owns `bifrost_ui.py`) still holds.

**(3) RECOMMENDATION:** **approve-now** — spec is locked CURRENT, acceptance is measurable, file is live and unblocked.

---

### T003 — UI: one presence surface — remove duplicate top status rows + floating bubbles

**(1) ALREADY SATISFIED?** **Partially.** The old "3 thinking status rows" from the original mockup complaint ARE still present as activity bubbles (`.actrow`/`.actbubble`, lines 666-674: "typing" bubbles with pulsating dots). However, the HUD glanceability strip (`.hrow`, line 687+) IS the designated "one place" for who's-doing-what — it renders rich presence per agent. The problem is the activity bubbles still exist as a **second surface** (`<div class="activity" id="activity">` at line 1130 in the HTML, rendered by JS at line ~1650+). The spec says: "REMOVE the redundant top 'agent thinking' status rows and the separate floating 'thinking • • •' bubbles." The bubbles are still there.

**(2) STILL COHERENT?** **Yes.** `ui-composition-spec.md` §2 is explicit. The HUD strip is the keeper; the activity bubbles are the redundant surface to remove.

**(3) RECOMMENDATION:** **approve-now** — HUD is built (one surface exists), but the duplicate activity bubbles must be removed. Acceptance: only the HUD shows presence; activity div is gone or repurposed.

---

### T004 — UI: composer as one glass focus-block + fix garbled recipient bar

**(1) ALREADY SATISFIED?** **Largely yes.** The composer already IS one focus block: `.composer` (line 743) contains the fidelity ladder (`.fibar` at line 785 with icon buttons), the `.cwrap` (line 745, a single rounded glass container with recipient chip + textarea + send button), and the roster popover. The recipient is a compact chip (`.recipient`, line 758) inside the cwrap — not a garbled full-width gradient bar. The `ui-composition-spec.md` §3 says "OneUI focus block" and this matches. The "garbled gradient recipient bar" no longer exists; the old `conic-gradient` pseudo-element approach is gone. **This task's acceptance is satisfied in the current code.**

**(2) STILL COHERENT?** **Yes** — but the task asks for what already exists.

**(3) RECOMMENDATION:** **abandon** — composer is already one focus block; recipient chip is compact, no gradient glitch. The spec's §3 is built.

---

### T005 — UI: 24dp margins + 8/16/24 grid + one title hierarchy

**(1) ALREADY SATISFIED?** **Partially.** The `.app` container (line 561) is `max-width:1180px; margin:0 auto` — centered column exists. Log padding is `20px 24px 8px` (line 612 — close to 24dp). Composer padding is `12px 16px 18px` (line 743 — 16px lateral, not 24). The HUD has `margin:0 16px` (line 680). The banner has `margin:10px 16px 0` (line 606). So: **margins are inconsistent** (16px vs 24px mixed), **there is no explicit 8/16/24 grid system**, and the title hierarchy is a single `<h1>` "Bifrost" plus agent dots (line 568–575) — functional but not the "one prominent title + ≤3 top actions" the spec calls for. The spec §4-5 are partially met but not systematically applied.

**(2) STILL COHERENT?** **Yes.** `ui-composition-spec.md` §4-5 define the grid + hierarchy. The work is a systematic CSS pass over `bifrost_ui.py`.

**(3) RECOMMENDATION:** **approve-now** — coherent spec, measurable acceptance (all margins 24dp min, consistent 8/16/24 spacing grid, one title, ≤3 top actions), live file.

---

### T006 — Backend: finish cognitive_metrics evidence engine

**(1) ALREADY SATISFIED?** **Yes — wired, tested, green.** Evidence:
- `core/coord/cognitive_metrics.py` is complete: `EfficiencySnapshot` dataclass with all claimed metrics + derived ratios (lines 35-130), accumulator functions for every metric (lines 140-210+), `init()`/`dump()`/`reset_all()` API.
- **Wired in production**: `scripts/bifrost_runner_deepseek.py` imports `from core.coord import cognitive_metrics as cog` (line 41), calls `cog.init(args.agent)` (line 446), `cog.record_file_read()` (line 276), `cog.record_human_interjection()` (lines 307, 311), `cog.record_turn_complete()` (line 365).
- **Tests exist and pass**: `tests/test_cognitive_metrics.py` exercises init/dump roundtrip, accumulation, invariants, ratios, zero-cost-when-disabled, file-read dedup detection.
- **Wiring gate**: `scripts/check_wiring.py` confirms `cognitive_metrics.py` is reachable (imported by the runner).

**(2) STILL COHERENT?** **Yes** — the task is simply already done.

**(3) RECOMMENDATION:** **abandon** (already satisfied) — measured facts are wired, tests green, the evidence engine is live in the deepseek runner loop.

---

### T007 — Verify Void theme + aurora perf bench → confirm defaults

**(1) ALREADY SATISFIED?** **Partially — bench exists, defaults not confirmed.**
- `scripts/bench-aurora.html` exists: it is a full WebGL2 benchmark comparing two GLSL noise variants (hash vs gradient), measuring frame times (median/p99), GPU memory, hidden rAF leakage, first-paint time, and static GPU usage — all against defined thresholds (lines 50-61). It renders a PASS/FAIL/WARN verdict.
- **But**: the bench has not been RUN and recorded. The settings panel in `bifrost_ui.py` shows `auroraStatus` as "off — run bench-aurora.html first" (line 1096), meaning the aurora flag defaults to OFF. The Void theme exists (`theme-void.js`, served at line 136) but there's no recorded benchmark result confirming which variant won or what the default should be.
- T007 asks for: "bench PASS recorded; aurora default confirmed" — neither is recorded.

**(2) STILL COHERENT?** **Yes.** The bench file exists and is functional. The task just needs execution + recording of results.

**(3) RECOMMENDATION:** **approve-now** — bench tooling exists; the task is a one-session run-and-record (open bench-aurora.html in browser, note which variant wins, flip the aurora default in settings if PASS, record the result in a note). Low effort, high clarity.

---

### Summary

| Task | Satisfied? | Coherent? | Verdict |
|---|---|---|---|
| T002 reasoning-card collapse | No | Yes | **approve-now** |
| T003 one presence surface | Partially (HUD exists, bubbles remain) | Yes | **approve-now** |
| T004 composer focus-block | **Yes — already built** | Yes | **abandon** (satisfied) |
| T005 24dp grid + titles | Partially (inconsistent margins) | Yes | **approve-now** |
| T006 cognitive_metrics engine | **Yes — wired, tested, green** | Yes | **abandon** (satisfied) |
| T007 Void + aurora bench | Partially (bench exists, not run) | Yes | **approve-now** |

Four tasks are real work remaining (T002, T003, T005, T007). Two (T004, T006) are already satisfied by the current codebase.
