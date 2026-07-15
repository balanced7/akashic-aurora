# T071-R1 VERDICT — deepseek verify — 2026-07-15

**Verdict: GREEN**. The boot relevance budget v1 @e72c8e2 implements my Part 5 ladder verbatim and the noise property holds.

## Pins (tests/test_t071_r1_relevance_budget.py)

| Pin | Test | Result |
|-----|------|--------|
| P1 | task-id match outranks everything | GREEN — "hit" w/ T077 token outranks fresher category match |
| P2 | constraint tier beats file-path | GREEN — RB-26 keyword-overlapping constraint outranks file-path match |
| P3 | file-path beats category | GREEN — same-file mention outranks same-domain advice |
| P4 | recency tiebreak | GREEN — same tier → newer wins |
| P5 | fixed cap survives 100-junk flood | GREEN — task-id hit stays #1 through 100 "attempt N" residue lessons; total chars ≤ 2000 |
| P6 | funnel credit multiplicative boost | GREEN — cited/useful lesson beats surfaced-and-ignored at equal tier via usefulness_factor |
| P7 | top hit guaranteed + clip confessed | GREEN — top hit always included even when over-budget; clipped line carries " ...[budget]" |
| P8 | zero-relevance floor | GREEN — zero-base lessons do not ride when any relevant lesson exists; irrelevant-only corpus gets ≤3 floor entries |
| — | kill switch | GREEN — AKASHIC_RELEVANCE_BUDGET=0 → legacy loader path |

## Flagged binds

### R1-a: Constraint bridge detector — CORRECT for v1

`base_score()` at `relevance_budget.py:82-84`: constraint tier fires on `category.startswith("constraint")` OR `RB-\d+` token in lesson text, AND keyword overlap with task. This is the bridge until R2 lifecycle tags land (where constraints get a proper `kind: constraint` tag). The double condition (constraint marker + keyword overlap) prevents every RB-tagged lesson from outranking a genuine task-id hit. The RB-token half catches legacy lessons that predate the "constraint" category convention. Sound bridge.

### R1-b: Multiplicative credit — CONFIRMED

`score()` at `relevance_budget.py:101`: `return (base + recency) * factor` where `factor = usefulness_factor(credit_fn(source))`. The multiplicative join means a noise-decayed lesson (surfaced-often-never-cited → factor 0.5x) can sink below a clean lower-tier lesson (factor 1.0x). An additive join (base + bonus) would never invert tiers. This is the correct mathematical expression of "proven useful beats speculative."

Zero new counters: `usefulness_factor` reads the EXISTING `recall:use:<source>` counters — `helped` and `surfaced` — already maintained by `core.recall.at_action`. The budget adds no write path.

### R1-c: Top-hit guarantee + confessed clip — CONFIRMED

`select_within_budget()` at lines 129-133: `if not out: out.append(entry)` — the first entry (highest-scoring) always ships regardless of budget. `render_entry()` at lines 111-113: clips at `max_chars` with explicit `"...[budget]"` suffix. Packet law honored: the clip is SAID, never silent.

### R1-d: Kill switch — CONFIRMED

`learning_loader.py:37`: `if os.getenv("AKASHIC_RELEVANCE_BUDGET", "1") != "0"` gates the budget path; on "0", falls through to `load_learnings_ranked_by_relevance()` — the legacy recency/Ranker loader. Fail-open: `except Exception: pass` also falls through to legacy. The kill switch is the OFF switch AND the error net.

## Noise-vote vs hard-filter call — JUDGMENT: correct

The design uses the funnel's `usefulness_factor` (multiplicative, range [0.5, 1.5]) to noise-vote residue down over time. A "hard-filter" alternative would maintain an ignore-list or ban-list of known noise lessons.

The soft approach is the right call for three reasons:

1. **Self-correcting.** A lesson like "r" (the one-character test residue) will be surfaced many times, never cited as helpful, and its `usefulness_factor` will decay to 0.5x — sinking it below real lessons. But if that lesson turned out to be useful after all (a citation appears), it climbs back. A hard-filter requires curation to reverse.

2. **No new mechanism.** `usefulness_factor` already exists in `core.recall.at_action` and is maintained by the recall path. The budget reads it; it does not create a new counter, a new curation queue, or a new operator decision point. The noise vote is a byproduct of normal use.

3. **Boot is not the whole surface.** A lesson that's noise-voted out of boot is still one `knowledge_recall` away. The budget PRIORITIZES, never censors. A hard-filter that removes a lesson from the recall index is a different and more dangerous operation.

The residual "category-coincident" noise (lessons in the `robustness` category that match the task's keywords purely by category coincidence) is the R2 lifecycle's problem — constraint-kind tagging and quarterly review gates will surface them for explicit demotion. The commit message correctly calls this out.

## R1b proposal: Same ladder over lookback layers

**JUDGMENT: Adopt.** The lookback ranking currently uses git-layer ordering (newest → oldest) as its primary sort, with the same `Ranker` for text relevance. This is vulnerable to the same noise problem: a stale layer that happens to match a keyword outranks a newer, genuinely relevant layer.

The same ladder (task-id 1.0 > constraint 0.8 > file-path 0.7 > category 0.5) with multiplicative funnel credit, applied to lookback's layer set, would give it the same anti-noise property. The D5 battery (`test_lookback.py` D5 — forge-origin commits outranked at the git-layer margin) is the ready-made RED pin for this slice.

**Recommendation**: T071-R1b should be its own small slice: wiring the relevance budget into the lookback ranking path, with D5 as the pre-registered RED pin. The infrastructure (ladder, credit, render) is already built — this is a one-seam wiring change.

## Suite: 9/9 GREEN (no Redis needed — FakeStore provides hermetic surface)
