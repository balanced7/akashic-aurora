# Narrative spine — test & verification plan (build the right thing, slice by slice)

> Companion to `docs/narrative-spine-plan.md`. The rule: **a slice ships only when its
> acceptance bar is met on the fixture AND its robustness battery is green.** If a metric
> is below bar, we *iterate the slice* before advancing — marathon, not sprint. This is
> how we keep edge cases from compounding into the full stack.

## How we test (three layers per slice)

1. **Shape** — fast unit tests: does it have the right structure / round-trip / API?
2. **Robustness** — the standing battery (reused from `tests/test_robustness.py`):
   model-based fuzz, cross-backend equivalence (File vs Redis), corruption resilience,
   backward-compat loading, concurrency, and **isolation** (never touches canonical).
3. **Metric** — a *measurable* quality bar on a labeled fixture, using the **standard
   metric from the relevant research field** (so "compare to existing benchmarks" is real,
   not vibes). Heuristic slices set a baseline; later ML/LLM slices must **beat that
   baseline by a margin** (ablation) or they're not worth the complexity.

## Self-test mechanisms (the system checks itself)

- **Source-resolution** — every chapter/summary claim must resolve to a real Beat/source
  (our lossless-pointer invariant; checkable with *no* LLM). No orphan claims.
- **Determinism** — heuristic stages: same input → identical output (regenerate twice, diff).
- **Round-trip / reconstruction** — rebuild state from the Ledger/Store; cross-backend equality.
- **Faithfulness gate** — the Distiller writer→critic blocks lossy/hallucinated summaries.
- **Invariant assertions** — budget respected, chronological order, supersession excludes
  retired nodes, one-track-per-beat, bidirectional links consistent.
- **Golden fixture regression** — a small hand-labeled corpus we version; any drift fails CI.

## Shared assets (built once in Slice 2, reused everywhere)

- `tests/fixtures/narrative_fixture.py` — a small **hand-labeled** corpus: ~40–60 Beats
  across domains (ai-setup / research / stemroller / vision) with **gold** `{track, themes,
  chapter-boundaries, key edges}` + a handful of **QA pairs** ("what happened around X / why
  / what did it lead to"). This is our local benchmark — deterministic, fast, always available.
- `tests/narrative_metrics.py` — metric helpers: `ari()`, `nmi()`, `purity()`, `pk()`,
  `windowdiff()`, `boundary_f1()`, `faithfulness()`, `coverage()`, `precision_at_k()`.

## Metrics glossary (what each measures · its field)

| Metric | Measures | Field it comes from |
|---|---|---|
| **ARI / NMI / purity** | track/theme assignment vs gold clusters | conversation disentanglement; clustering |
| **P_k / WindowDiff / boundary-F1** | switch/chapter-boundary placement | topic segmentation |
| **faithfulness** | % summary claims that resolve to a source | summarization (SummaC/QAGS-style) |
| **coverage** | % high-weight Beats represented in summaries | timeline summarization |
| **chronological integrity** | events summarized in time order | Narrative Consolidation |
| **QA accuracy (EM/F1)** | answer "what/why/when" across the timeline | LoCoMo, QuALITY |
| **temporal-QA accuracy** | "what did we believe *as of* date X?" | Zep temporal reasoning |
| **NPMI coherence** | theme/topic internal coherence | topic modeling |

**Optional external datasets** (periodic reality-checks that our internal metrics track
published numbers — not per-slice gates): **irc-disentanglement** (Kummerfeld 2019) for
routing; **DialSeg-711** for segmentation; **LoCoMo** + **QuALITY** for long-horizon QA.

---

## Per-slice test arrays

### Slice 0 — schema + lexicon ✅
- **Bar:** 100% round-trip; 100% rejection of invented edge names.
- **Shape:** construct/round-trip Beat/Chapter/Track/Theme/Atlas; key helpers; weight clamp. ✅
- **Robustness:** `from_dict` with missing/extra/None/unicode/huge fields; invalid edge
  types rejected; backward-compat (load a Beat saved without new fields).
- **Invariants:** every `edge.type ∈ vocabulary`; serialization lossless; `validate_beat`
  catches all four problem classes.
- **Self-test:** `validate_beat` / `validate_edge`.

### Slice 1 — BeatLog / logging hooks ✅
- **Bar:** 100% of hook-eligible events (learn, commit) produce exactly one sourced Beat.
- **Shape:** emit/count/recent/in_window/weight. ✅
- **Robustness:** fuzz 1,000 random emits → `count==zcard`, timeline sorted, every source
  non-empty; concurrent emits (no lost Beats); garbage Beat JSON skipped on read;
  cross-backend (File vs Redis same timeline); isolation (tests never hit canonical).
- **Invariants:** every stored Beat has a non-empty source; timeline order == timestamp
  order; `recent` is newest-first.
- **Self-test:** re-read each Beat → `validate_beat` passes; `zcard == #beat keys`.

### Slice 2 — TrackRouter (heuristic)
- **Bar (the "right thing"):** on the fixture, **track-assignment ARI ≥ 0.70** and
  **switch WindowDiff ≤ 0.30** (boundary-F1 within ±1 Beat ≥ 0.6). This baseline is what
  Slice 6 (embeddings) must beat.
- **Shape:** commit-Beat touching `core/` → `ai-setup`; learning category → mapped track;
  active track persists; explicit/marker switch.
- **Robustness:** ambiguous Beat (no clear signal) → fallback track + flagged, not crash;
  rapidly alternating domains; unknown repo path → new/“unknown” track; empty/None signals;
  re-routing idempotent.
- **Metric+benchmark:** ARI/NMI/purity (disentanglement) for assignment; P_k/WindowDiff
  (segmentation) for switches — on `narrative_fixture`. Optional: irc-disentanglement subset.
- **Self-test:** exactly one track per Beat; switches monotonic in time; idempotent re-run.

### Slice 3 — Chronicler (per-track, heuristic)
- **Bar:** **faithfulness = 100%** (every chapter claim resolves to a Beat/source),
  **coverage ≥ 95%** of weight-≥4 Beats, **chronological integrity = 100%**, skeleton ≤ budget.
- **Shape:** chapter has title/span/beats/summary; storyline orders chapters; atlas lists
  tracks; renders `story.md` + `story.index.json`.
- **Robustness:** empty track; single-Beat chapter; huge window; over/under-segmentation
  tunables; **idempotent re-run** (same input → identical output); corrupt Beat skipped.
- **Metric+benchmark:** faithfulness (source-resolution, self-test) + optional LLM-NLI
  entailment (SummaC/QAGS-style); coverage; chronological integrity; optional ROUGE vs a
  few hand-written reference chapters.
- **Self-test:** regenerate twice → byte-identical; writer→critic gate; zero orphan claims.

### Slice 4 — the `story` verb
- **Bar:** from each fixture QA pair, the right chapter/Beat is reachable in **≤2 drills**;
  output within budget; ASCII-safe; errors teach on empty/bad input.
- **Shape:** `story` (Atlas), `--track`, `--at`, `--chapter`, `--beat`, `--json` return
  sane shapes; drill pointers resolve.
- **Robustness:** empty store; bad ids; huge story (budgeted); Windows cp1252; isolation.
- **Metric:** navigation success rate on QA pairs; output token budget; latency.
- **Self-test:** every pointer in output resolves (`recall`/`git`/`beat`); `--json` parses.

### Slice 5 — Themes
- **Bar:** theme-clustering **NMI ≥ 0.60** vs gold themes; every theme edge is
  `member_of`/`instance_of`.
- **Shape:** multi-label assignment; theme view gathers cross-track Beats.
- **Robustness:** Beat in many themes; empty theme; rename; cross-track membership.
- **Metric+benchmark:** purity/NMI vs gold; NPMI coherence.
- **Self-test:** theme view == union of member Beats; edge types valid.

### Slice 6 — embedding routing (Tier 1)
- **Bar (ablation gate):** on the *same* fixture, embeddings must **beat the Slice-2
  heuristic** by **≥0.1 ARI** (and not regress WindowDiff) — else we keep the heuristic
  (avoid complexity that doesn't pay). Cost/latency within budget.
- **Shape:** `relevance_fn` swap; per-track centroids; nearest-assign; novelty→new track;
  drift→switch.
- **Robustness:** cold start (no centroids); single-domain; near-duplicate domains;
  **threshold sensitivity sweep** (report stability).
- **Metric+benchmark:** ARI/NMI/WindowDiff vs heuristic baseline (auto-ablation report);
  optional full irc-disentanglement.
- **Self-test:** deterministic with fixed seed/embeddings; ablation table emitted each run.

### Slice 7 — bi-temporal + back-links + feed `boot`
- **Bar:** **temporal-QA accuracy ≥ baseline** ("what did we believe as of <date>?");
  back-link completeness = 100%; and the headline regression: a fresh agent's **"what's
  been done lately"** matches the generated narrative, **not** the stale docs (the original
  failure, now a guarded test).
- **Shape:** `valid_from/valid_to`; supersede sets old `valid_to` + `replaces` edge;
  learning↔chapter back-link; `boot` injects recent Atlas/Track.
- **Robustness:** superseded chapter excluded from "current" but present in history;
  "as-of-date" query; cyclic-edge guard.
- **Metric+benchmark:** temporal-QA (Zep-style); stale-recall regression test.
- **Self-test:** bidirectional-link consistency (A→B ⇒ B has backref); supersession monotonic.

### Slice 8 — evaluation harness
- **Bar:** `tests/test_narrative.py` runs the **whole battery** and prints a metrics table;
  all bars above met; regression-guarded.
- **External validation (optional):** run routing on irc-disentanglement, QA on LoCoMo /
  QuALITY → confirm our internal metrics track published numbers.

### Slice 9 — LLM writer/critic + naming (optional)
- **Bar:** faithfulness must **not drop** vs the heuristic (critic gate holds); summary
  quality up (LLM-judge or ROUGE if refs); names sensible; **graceful fallback** to
  heuristic when the LLM is unavailable.
- **Self-test:** writer→critic faithfulness gate; every LLM claim source-checked.

---

## The discipline (so we build the right thing)

- **Gate:** advance only when the slice's **Bar is met on the fixture** and the **robustness
  battery is green**. Below bar → iterate the slice.
- **Baselines first, upgrades must earn their keep:** the heuristic slice sets the number;
  the ML/LLM slice must beat it (ablation), or we don't ship the complexity.
- **The fixture is the contract:** if a real Beat exposes a case the fixture lacks, we add
  it to the fixture *first* (it becomes a permanent regression test), then fix the code.
- **Dogfood as the ultimate acceptance:** we chronicle our *own* build-out; the system
  passes when an agent can answer "what's been done, and why?" correctly from it.
