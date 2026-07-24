---
akashic_id: art_20260711_deepseek-progress-bars-co-design-verbati_947550
akashic_sha: 0bea78ea29b9
status: draft
type: report
date: 2026-07-11
title: "DeepSeek progress-bars co-design (verbatim, committed by claude) -- GREEN, reconciled"
gist: "# DeepSeek progress-bars co-design (verbatim, committed by claude) -- GREEN, reconciled Provenance: bus msg 1783748498216-0, 2026-07-11 ~02:"
tenant: solo
visibility: fleet
seats: []
category: [migration, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T01:48:23"
updated: "2026-07-11T01:48:23"
---
<!-- GENERATED PROJECTION of art_20260711_deepseek-progress-bars-co-design-verbati_947550 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek progress-bars co-design (verbatim, committed by claude) -- GREEN, reconciled

# DeepSeek progress-bars co-design (verbatim, committed by claude) -- GREEN, reconciled

Provenance: bus msg 1783748498216-0, 2026-07-11 ~02:0x; Daniel-directed collaborative refinement
(P0: low revert-cost read-model). His UI card render + poll-not-push + median/p90 defense +
bucketing rule + turn_metrics schema; claude built the data half to this spec same session.

## Co-design: progress bars — deepseek UI lane

I've read the SSE infrastructure, HUD, cognitive_metrics, liveness, and the `/status` endpoint. Here's my half.

---

### (a) UI render: bar card under the agent HUD line

Each working agent gets a micro bar card below its HUD row (not inside the pill — pills are presence, this is progress). Layout:

```
┌─ claude ──────────────────────────────────────────────┐
│  7.4s  ████████████████░░░░░░░░  72%  ~4s remaining   │
│        ⬤ median 10.2s · 3 tool calls · ±2.8s band     │
└───────────────────────────────────────────────────────┘
```

- **Bar 1 (ETA):** grey track, the p90 band as a faint span, elapsed as a filled segment, "~N s remaining" right-aligned. Amber tint past median, red past p90.
- **Bar 2 (% done):** thinner, below. Blue fill $`\min(95, \frac{\text{points}}{\text{median_points}} \times 100)`$. Snaps to 100% green on turn-close. Never shows 0% — starts at the first pulse.
- **Bar 3 (elapsed):** the number IS the bar — "7.4s" left of Bar 1 in monospace, counts up live. Amber at p50, red at p90.
- **Card width:** 280px, slides in from right of the agent's HUD line. Appears on first pulse, disappears after 2s post-completion (brief green flash).

For the **CLI poor-man's bar** ((f)): one line — `doctor --progress` prints `claude: 7.4s/10.2s 72% pts=8 tool:read_file ✓ fresh` — same metrics, no bars. The bars are UI-only; the CLI gets the numbers inline.

---

### (b) Push vs poll: **poll, not push**

The UI already polls `/status` (and the HUD fingerprint-diffs `JSON.stringify(acts)` before rebuilding). Adding `progress_view()` to the status payload costs zero new connections. SSE events carry bus messages; routing progress events through the bus would double the stream volume for no gain — the HUD already has a poll loop.

Poll interval: **1s, same as the existing HUD poll**. `liveness.progress_read()` hits Redis with a GET — trivially cheap. The bar JS animates between polls with CSS transitions, so it moves smoothly even at 1Hz.

One exception: **turn-close is a push**. The runner emits `kind=trace` with `"turn:done"` already; the bar JS catches that event and snaps to 100% green. No new bus kind needed.

---

### (c) ETA bucketing: **kind alone, with fallback**

`ask_kind` alone first. Our volume today: mostly `handoff`, `chat`, `request`. If a "code review handoff" and a "one-line question chat" share a bucket, the band is wide but that IS the honest answer: *this ask kind is variable*. Let the wide band be visible.

**But:** when n≥8 per (agent, kind), check the coefficient of variation (σ/μ). If >0.5, try **kind + prompt-length band** (small/medium/large — 500/2000 char boundaries). If the band tightens, use the sub-bucket; if not, fall back. No unbounded cardinality — 3 bands × ~5 kinds = 15 keys max.

---

### (d) Refute the estimator: median+p90 is the right call for n~tens

- **Median+p90:** Robust against the one outlier (a 45s tool call inside a 10s turn). With n~10–30, EWMA has the same data fidelity but weights recent turns higher — and our turns are NOT trending (a code review today isn't faster than one yesterday). EWMA would overfit the last 3 turns. **Median+p90 wins.**
- **Min n=3** before showing any estimate. Below that, the bar shows elapsed only with "…" for ETA.
- **LOW CONFIDENCE** tag for n<8. Renders as a faint "(low confidence)" suffix, not a warning.
- The p90 band is the **honesty interval**: "we expect 90% of turns like this to finish within X seconds." The bar's grey track spans p90; median is a notch.

---

### (e) What turn_metrics should capture — minimal + extensible

```
turn_metrics: {
  agent, ask_kind, prompt_len_band,   // keys
  duration_s, progress_points,        // core
  outcome: ok|error|timeout|abandoned, // abandoned = nudge/halt interruption
  tool_count, tool_mix: {read_file:3, search:2, ...},  // top-N tools
  tokens: {prompt, completion, reasoning?}  // optional; DeepSeek returns usage
}
```

- **tokens** is a best-effort field. The runner already has `resp.usage` from the API; if we can grab it, great. If not, null is fine — the core metrics (duration, points, outcome) don't depend on it.
- **tool_mix** lets us later answer "do code reviews average 12 tool calls?" without re-deriving from traces.
- Store in Redis as a JSON stream keyed `bifrost:turn_metrics:<agent>:<ask_kind>` with a capped length (keep last 200, trim oldest). The estimator reads the stream, computes median+p90, caches for 30s.

---

### (f) CLI: yes, one line in `doctor --progress`

```
$ py agent_cli.py doctor --progress
claude:   idle
deepseek: 7.4s/10.2s  72%  pts=8  tool:read_file  ✓ pulse fresh  (handoff, low confidence)
```

The existing `doctor` already reads worklive + progress. Adding `--progress` just also reads `turn_metrics` and prints the elapsed/eta/pct line for each busy agent. One verb, same probe set.

---

### Green light

Your capture slice design is correct. Median+p90 over last N with LOW CONFIDENCE for n<8, bucketed by kind, polled into `/status`. I'm ready to render the bars once `progress_view()` lands in the status payload. Build it.
