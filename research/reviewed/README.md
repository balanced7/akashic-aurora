# research/reviewed/ — catalog (auto-generated)

Fenced evidence: reviews, audits, walk transcripts, frontier sweeps. Every file here has been through at least one adversarial pass. Reconciled designs graduate to `docs/`; the reviewed artifact stays as evidence.

**Generated:** 2026-10-07 06:46 UTC · **Source:** `scripts/generators/gen_library.py` · **Never hand-edit.**

---

## Current files (2)

| File | Type | Arc | Date | Description |
|------|------|-----|------|-------------|
| [`research/reviewed/recall-redesign-peer-research-2026-07-26.md`](research/reviewed/recall-redesign-peer-research-2026-07-26.md) | research | — | — | Recall redesign — peer research (claude's lane) |
| [`research/reviewed/storage-engine-sweep-2026-07-26.md`](research/reviewed/storage-engine-sweep-2026-07-26.md) | research | — | — | Storage engine sweep — claude's half |

<details>
<summary>Archived / superseded (154 file(s))</summary>

| File | Status | Type | Date |
|------|--------|------|------|
| [`research/reviewed/task-to-model-admission-proposal-2026-07-28.md`](research/reviewed/task-to-model-admission-proposal-2026-07-28.md) | ⚪ **PROPOSAL — Daniel gate required.** This document authorizes no automatic | untyped | 2026-07-28 |
| [`research/reviewed/build-plan-claude-half-2026-07-28.md`](research/reviewed/build-plan-claude-half-2026-07-28.md) | ⚪ current | 2026-07-28 ~03:00 | filed BEFORE any peer plan arrived (fence honest; note: | untyped | — |
| [`research/reviewed/build-queue-synthesis-2026-07-28.md`](research/reviewed/build-queue-synthesis-2026-07-28.md) | ⚪ current | 2026-07-28 ~03:30 | AWAITING DANIEL'S GATE | untyped | — |
| [`research/reviewed/cell-architecture-kimi-handoffs-2026-07-27.md`](research/reviewed/cell-architecture-kimi-handoffs-2026-07-27.md) | ⚪ current | 2026-07-27 ~21:35 local | untyped | — |
| [`research/reviewed/cell-architecture-round1-2026-07-27.md`](research/reviewed/cell-architecture-round1-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/deepseek-door-probe-attack-2026-07-26.md`](research/reviewed/deepseek-door-probe-attack-2026-07-26.md) | ⚪ current  (2026-07-26, verbatim bus capture, stream 1785085830546-0) | untyped | — |
| [`research/reviewed/deepseek-recall-validity-close-2026-07-27.md`](research/reviewed/deepseek-recall-validity-close-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/deepseek-recall-validity-round1-2026-07-27.md`](research/reviewed/deepseek-recall-validity-round1-2026-07-27.md) | ⚪ current | 2026-07-27 | arc: recall-validity (Daniel overnight mandate) | untyped | — |
| [`research/reviewed/demand-census-reconciliation-2026-07-28.md`](research/reviewed/demand-census-reconciliation-2026-07-28.md) | ⚪ current | 2026-07-28 | claude reconciling kimi + deepseek (blind: deepseek judged | untyped | — |
| [`research/reviewed/discord-bifrost-bridge-design-2026-07-27.md`](research/reviewed/discord-bifrost-bridge-design-2026-07-27.md) | ⚪ current | 2026-07-27 | claude#7d0ede0e | NOT BUILT, awaiting Daniel's gate | untyped | — |
| [`research/reviewed/explore-round1-deepseek-2026-07-27.md`](research/reviewed/explore-round1-deepseek-2026-07-27.md) | ⚪ current | 2026-07-27 | arc: recall-validity, Daniel-funded 3-seat rounds | untyped | — |
| [`research/reviewed/explore-round2-deepseek-2026-07-27.md`](research/reviewed/explore-round2-deepseek-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/fence-lite-standing-fixes-deepseek-2026-07-28.md`](research/reviewed/fence-lite-standing-fixes-deepseek-2026-07-28.md) | ⚪ not started. My named Q1 lines (`scripts/bifrost_runner_deepseek.py:1171`, `:1210`, `:1216`) still use agent-keyed `lane_cursor_key()`. The migration is: pass `args.session` (the sid8) to `lane_cursor_key()` → `bifrost:cursor:lane:deepseek#<sid8>`. One parameter. The batch loop works unchanged. I'll file this as my lane work alongside the S2 roster build. Not blocking — my runner runs solo today, so the per-incarnation cursor is a no-op until I spawn a twin. But it should ship before the roster, because the roster's per-seat heartbeat key uses the same incarnation dimension. | untyped | — |
| [`research/reviewed/fleet-debate-reconciliation-2026-07-28.md`](research/reviewed/fleet-debate-reconciliation-2026-07-28.md) | ⚪ current | 2026-07-28 | claude reconciling; verbatim halves in | untyped | — |
| [`research/reviewed/frontier-heimdall-batch-verification-2026-08-17.md`](research/reviewed/frontier-heimdall-batch-verification-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786993101104-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-continuity-2026-08-17.md`](research/reviewed/frontier-heimdall-continuity-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786983232234-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-name-collision-scan-2026-08-17.md`](research/reviewed/frontier-heimdall-name-collision-scan-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786986442669-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-r2-read-state-2026-08-17.md`](research/reviewed/frontier-heimdall-r2-read-state-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786979965221-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-read-state-fence-2026-08-17.md`](research/reviewed/frontier-heimdall-read-state-fence-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786979279551-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-t275-verification-2026-08-17.md`](research/reviewed/frontier-heimdall-t275-verification-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786989825714-0) | untyped | — |
| [`research/reviewed/frontier-heimdall-t340-t339-close-2026-08-17.md`](research/reviewed/frontier-heimdall-t340-t339-close-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1787000317009-0) | untyped | — |
| [`research/reviewed/frontier-navi-r2-read-state-2026-08-17.md`](research/reviewed/frontier-navi-r2-read-state-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786979961081-0) | untyped | — |
| [`research/reviewed/frontier-navi-read-state-fence-2026-08-17.md`](research/reviewed/frontier-navi-read-state-fence-2026-08-17.md) | ⚪ current  (2026-08-17, verbatim bus capture, stream 1786979503013-0) | untyped | — |
| [`research/reviewed/index-blindness-RECURRENCE-2026-07-27.md`](research/reviewed/index-blindness-RECURRENCE-2026-07-27.md) | ⚪ current | 2026-07-27 ~21:05 local | found by claude (fresh Opus 5 seat) | untyped | — |
| [`research/reviewed/kimi-method-and-recall-2026-07-27.md`](research/reviewed/kimi-method-and-recall-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/lookback-battery-broken-by-sprawl-migration-2026-07-28.md`](research/reviewed/lookback-battery-broken-by-sprawl-migration-2026-07-28.md) | ⚪ current | 2026-07-28 | claude | found while gating Sol's stream-wedge repair | untyped | — |
| [`research/reviewed/multiplayer-netcode-prior-art-2026-07-28.md`](research/reviewed/multiplayer-netcode-prior-art-2026-07-28.md) | ⚪ current | 2026-07-28 | claude | Daniel's directive, verbatim: "research how multiplayer | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/README.md`](research/reviewed/origin-prelog-2026-04-11/README.md) | ⚪ current  ·  Type: report  ·  Recovered 2026-08-17 by claude (Vandor) | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/SOURCE-MANIFEST.md`](research/reviewed/origin-prelog-2026-04-11/SOURCE-MANIFEST.md) | ⚪ current · Type: report · Author: claude (Vandor) | untyped | — |
| [`research/reviewed/pathway-positions-2026-07-27.md`](research/reviewed/pathway-positions-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/precision-audit-calibration-deepseek-2026-07-27.md`](research/reviewed/precision-audit-calibration-deepseek-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/precision-audit-kimi-confession-2026-07-27.md`](research/reviewed/precision-audit-kimi-confession-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/precision-audit-labels-deepseek-2026-07-27.md`](research/reviewed/precision-audit-labels-deepseek-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/precision-audit-labels-kimi-2026-07-27.md`](research/reviewed/precision-audit-labels-kimi-2026-07-27.md) | ⚪ current | 2026-07-27 | THIRD LABELLER (Daniel asked for this at session start) | untyped | — |
| [`research/reviewed/precision-audit-verdict-2026-07-27.md`](research/reviewed/precision-audit-verdict-2026-07-27.md) | ⚪ current | 2026-07-27 | claude (fresh Opus 5 seat) + deepseek | untyped | — |
| [`research/reviewed/prior-art-fields-claude-2026-07-27.md`](research/reviewed/prior-art-fields-claude-2026-07-27.md) | ⚪ current | 2026-07-27 | claude (fresh Opus 5 seat) | untyped | — |
| [`research/reviewed/prior-art-kimi-independent-2026-07-27.md`](research/reviewed/prior-art-kimi-independent-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/prior-art-round-replies-2026-07-27.md`](research/reviewed/prior-art-round-replies-2026-07-27.md) | ⚪ current | 2026-07-27 | asks sent by claude, neither seat shown claude's candidates | untyped | — |
| [`research/reviewed/prior-art-synthesis-2026-07-27.md`](research/reviewed/prior-art-synthesis-2026-07-27.md) | ⚪ current | 2026-07-27 | claude, integrating claude + deepseek + kimi | untyped | — |
| [`research/reviewed/ship-gate-baseline-policy-kimi-2026-07-27.md`](research/reviewed/ship-gate-baseline-policy-kimi-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/signals-that-reach-nobody-2026-07-28.md`](research/reviewed/signals-that-reach-nobody-2026-07-28.md) | ⚪ current | 2026-07-28 | claude | written after the fourth instance, not before the first | untyped | — |
| [`research/reviewed/slice1-override-rate-deepseek-2026-07-27.md`](research/reviewed/slice1-override-rate-deepseek-2026-07-27.md) | ⚪ current | 2026-07-27 | untyped | — |
| [`research/reviewed/sol-bifrost-connection-guide-2026-07-28.md`](research/reviewed/sol-bifrost-connection-guide-2026-07-28.md) | ⚪ current | 2026-07-28 | claude, at Daniel's ask ("sol is figuring out how to connect to | untyped | — |
| [`research/reviewed/tempo-doctrine-2026-07-28.md`](research/reviewed/tempo-doctrine-2026-07-28.md) | ⚪ current | 2026-07-28 ~06:30 | synthesized from deepseek + kimi fenced positions | untyped | — |
| [`research/reviewed/twin-seat-misdelivery-diagnosis-2026-07-27.md`](research/reviewed/twin-seat-misdelivery-diagnosis-2026-07-27.md) | ⚪ current | 2026-07-27 | claude#7d0ede0e (fresh seat), diagnosing live | untyped | — |
| [`research/reviewed/README.md`](research/reviewed/README.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/abstention-is-reachable-by-the-other-floor-2026-10-06.md`](research/reviewed/abstention-is-reachable-by-the-other-floor-2026-10-06.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/build-plan-peer-halves-2026-07-28.md`](research/reviewed/build-plan-peer-halves-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/ci-tree-differential-census-2026-07-25.md`](research/reviewed/ci-tree-differential-census-2026-07-25.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/coarse-join-key-two-fenced-attacks-2026-10-06.md`](research/reviewed/coarse-join-key-two-fenced-attacks-2026-10-06.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/context-leverage-prior-art-2026-08-11.md`](research/reviewed/context-leverage-prior-art-2026-08-11.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/deepseek-system-inventory-p1-foundation-events-2026-07-26.md`](research/reviewed/deepseek-system-inventory-p1-foundation-events-2026-07-26.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/deepseek-system-inventory-p2-comm-2026-07-26.md`](research/reviewed/deepseek-system-inventory-p2-comm-2026-07-26.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/deepseek-system-inventory-p3-coord-trust-fleet-2026-07-26.md`](research/reviewed/deepseek-system-inventory-p3-coord-trust-fleet-2026-07-26.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/deepseek-system-inventory-p4-recall-learning-narrative-2026-07-26.md`](research/reviewed/deepseek-system-inventory-p4-recall-learning-narrative-2026-07-26.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/demand-census-deepseek-judge-2026-07-28.md`](research/reviewed/demand-census-deepseek-judge-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/demand-census-kimi-judge-2026-07-28.md`](research/reviewed/demand-census-kimi-judge-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/dsh-integration-briefing-for-serge-2026-08-24.md`](research/reviewed/dsh-integration-briefing-for-serge-2026-08-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-build-vs-buy-postmortems-2026-09-24.md`](research/reviewed/duckdb-build-vs-buy-postmortems-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-deep-dive-synthesis-2026-09-24.md`](research/reviewed/duckdb-deep-dive-synthesis-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-fanout-index-2026-09-24.md`](research/reviewed/duckdb-fanout-index-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-json-ingest-evidence-2026-09-24.md`](research/reviewed/duckdb-json-ingest-evidence-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-alternatives-2026-09-24.md`](research/reviewed/duckdb-lane-alternatives-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-benchmarks-2026-09-24.md`](research/reviewed/duckdb-lane-benchmarks-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-capabilities-2026-09-24.md`](research/reviewed/duckdb-lane-capabilities-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-concurrency-2026-09-24.md`](research/reviewed/duckdb-lane-concurrency-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-ecosystem-2026-09-24.md`](research/reviewed/duckdb-lane-ecosystem-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-fit-2026-09-24.md`](research/reviewed/duckdb-lane-fit-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-memory-ops-2026-09-24.md`](research/reviewed/duckdb-lane-memory-ops-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-retrieval-2026-09-24.md`](research/reviewed/duckdb-lane-retrieval-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-schema-2026-09-24.md`](research/reviewed/duckdb-lane-schema-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-lane-skeptic-2026-09-24.md`](research/reviewed/duckdb-lane-skeptic-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-licenses-2026-09-24.md`](research/reviewed/duckdb-licenses-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-local-benchmarks-and-census-2026-09-24.md`](research/reviewed/duckdb-local-benchmarks-and-census-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/duckdb-operational-limits-2026-09-24.md`](research/reviewed/duckdb-operational-limits-2026-09-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/fence-lite-s2-roster-kimi-2026-07-28.md`](research/reviewed/fence-lite-s2-roster-kimi-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/fence-lite-s4-reaper-kimi-2026-07-28.md`](research/reviewed/fence-lite-s4-reaper-kimi-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/fence-lite-standing-fixes-kimi-2026-07-28.md`](research/reviewed/fence-lite-standing-fixes-kimi-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/fleet-debate-round1-2026-07-28.md`](research/reviewed/fleet-debate-round1-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/fleet-debate-round2-2026-07-28.md`](research/reviewed/fleet-debate-round2-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/frontier-coordination-engine-exchange-2026-08-05.md`](research/reviewed/frontier-coordination-engine-exchange-2026-08-05.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/frontier-kimi-t323-s2-counters-2026-08-16.md`](research/reviewed/frontier-kimi-t323-s2-counters-2026-08-16.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/gemini-aurora-architecture-review-2026-08-11.md`](research/reviewed/gemini-aurora-architecture-review-2026-08-11.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/handoff-vandor-2026-10-06-morning.md`](research/reviewed/handoff-vandor-2026-10-06-morning.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/handoff-vandor-2026-10-06-night.md`](research/reviewed/handoff-vandor-2026-10-06-night.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/handoff-vandor-2026-10-06-screenspace.md`](research/reviewed/handoff-vandor-2026-10-06-screenspace.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/hybrid-retrieval-fence-2026-08-11.md`](research/reviewed/hybrid-retrieval-fence-2026-08-11.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/knowledge-plane-census-2026-10-03.md`](research/reviewed/knowledge-plane-census-2026-10-03.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/merged-record-wire-census-2026-08-05.md`](research/reviewed/merged-record-wire-census-2026-08-05.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/mnemosyne-comparative-review-2026-09-25.md`](research/reviewed/mnemosyne-comparative-review-2026-09-25.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/mnemosyne-exchange-for-serge-2026-10-03.md`](research/reviewed/mnemosyne-exchange-for-serge-2026-10-03.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/mnemosyne-five-dimension-read-2026-10-03.md`](research/reviewed/mnemosyne-five-dimension-read-2026-10-03.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/mnemosyne-operational-notebook-critique-2026-09-27.md`](research/reviewed/mnemosyne-operational-notebook-critique-2026-09-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/mnemosyne-provenance-archaeology-2026-10-03.md`](research/reviewed/mnemosyne-provenance-archaeology-2026-10-03.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/opal-s0-delivery-crash-audit-2026-07-29.md`](research/reviewed/opal-s0-delivery-crash-audit-2026-07-29.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/opal-s0-first-light-2026-07-29.md`](research/reviewed/opal-s0-first-light-2026-07-29.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-2026-04-13/README.md`](research/reviewed/origin-2026-04-13/README.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/april-redis-recovered.md`](research/reviewed/origin-prelog-2026-04-11/april-redis-recovered.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/BOOK-FAN-MANIFEST.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/BOOK-FAN-MANIFEST.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/FAN-COVERAGE-MANIFEST.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/FAN-COVERAGE-MANIFEST.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/book-adversarial-growth-refutation.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/book-adversarial-growth-refutation.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/book-partition-13-windows.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/book-partition-13-windows.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/book-the-42-day-silence.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/book-the-42-day-silence.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/partition-shard0-first48h_shard2-lateapril.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/partition-shard0-first48h_shard2-lateapril.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/partition-shard3-mayjune-partial.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/partition-shard3-mayjune-partial.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/refuter-round1-truncated-pack.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/refuter-round1-truncated-pack.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/fan-reports/refuter-round2-complete-48h-corpus.md`](research/reviewed/origin-prelog-2026-04-11/fan-reports/refuter-round2-complete-48h-corpus.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/operator-all.md`](research/reviewed/origin-prelog-2026-04-11/operator-all.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/operator-pre-aurora.md`](research/reviewed/origin-prelog-2026-04-11/operator-pre-aurora.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/origin-prelog-2026-04-11/operator-spine-2026-04-11_2026-08-16.md`](research/reviewed/origin-prelog-2026-04-11/operator-spine-2026-04-11_2026-08-16.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/outside-review-hudgins-emi-index-card-2026-09-03.md`](research/reviewed/outside-review-hudgins-emi-index-card-2026-09-03.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/peer-oss-2026-07-25-lint-taxonomy-and-agent-memory.md`](research/reviewed/peer-oss-2026-07-25-lint-taxonomy-and-agent-memory.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/critique-accuracy-first.md`](research/reviewed/piano-beat-and-score-2026-09-27/critique-accuracy-first.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/critique-realtime-first.md`](research/reviewed/piano-beat-and-score-2026-09-27/critique-realtime-first.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/critique-shortest-path.md`](research/reviewed/piano-beat-and-score-2026-09-27/critique-shortest-path.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/design-accuracy-first.md`](research/reviewed/piano-beat-and-score-2026-09-27/design-accuracy-first.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/design-realtime-first.md`](research/reviewed/piano-beat-and-score-2026-09-27/design-realtime-first.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/design-shortest-path.md`](research/reviewed/piano-beat-and-score-2026-09-27/design-shortest-path.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/ground-notation.md`](research/reviewed/piano-beat-and-score-2026-09-27/ground-notation.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/ground-quantization-feel.md`](research/reviewed/piano-beat-and-score-2026-09-27/ground-quantization-feel.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/ground-realtime.md`](research/reviewed/piano-beat-and-score-2026-09-27/ground-realtime.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/piano-beat-and-score-2026-09-27/ground-tempo-induction.md`](research/reviewed/piano-beat-and-score-2026-09-27/ground-tempo-induction.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/poison-message-crash-loop-2026-07-28.md`](research/reviewed/poison-message-crash-loop-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/portability-fan-2026-08-24.md`](research/reviewed/portability-fan-2026-08-24.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/precision-audit-fence-deepseek-2026-07-27.md`](research/reviewed/precision-audit-fence-deepseek-2026-07-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/precision-audit-labels-claude-2026-07-27.md`](research/reviewed/precision-audit-labels-claude-2026-07-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/precision-audit-status-2026-07-27.md`](research/reviewed/precision-audit-status-2026-07-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/prior-art-hard-negatives-and-situational-relevance-2026-10-02.md`](research/reviewed/prior-art-hard-negatives-and-situational-relevance-2026-10-02.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/prior-art-proactive-retrieval-when-to-fire-2026-10-02.md`](research/reviewed/prior-art-proactive-retrieval-when-to-fire-2026-10-02.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/prior-art-retrieval-abstention-2026-10-02.md`](research/reviewed/prior-art-retrieval-abstention-2026-10-02.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/prior-art-score-calibration-2026-10-02.md`](research/reviewed/prior-art-score-calibration-2026-10-02.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/season1-first-llm-played-round-2026-08-05.md`](research/reviewed/season1-first-llm-played-round-2026-08-05.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/semi-signal-paper-trader-heimdall-counter-2026-08-22.md`](research/reviewed/semi-signal-paper-trader-heimdall-counter-2026-08-22.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/simon-first-contact-review-2026-08-21.md`](research/reviewed/simon-first-contact-review-2026-08-21.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/simon-tooling-stack-2026-10-05-six-dimension-review.md`](research/reviewed/simon-tooling-stack-2026-10-05-six-dimension-review.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/simon-tooling-stack-2026-10-05-verified-latent-bugs.md`](research/reviewed/simon-tooling-stack-2026-10-05-verified-latent-bugs.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/slice1-override-rate-round1-2026-07-27.md`](research/reviewed/slice1-override-rate-round1-2026-07-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/slide6-heimdall-half-2026-08-15.md`](research/reviewed/slide6-heimdall-half-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/slide6-navi-half-2026-08-15.md`](research/reviewed/slide6-navi-half-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/sol-bifrost-collaboration-first-2026-08-05.md`](research/reviewed/sol-bifrost-collaboration-first-2026-08-05.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/spectrum-heimdall-crossexam-2026-08-15.md`](research/reviewed/spectrum-heimdall-crossexam-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/spectrum-heimdall-half-2026-08-15.md`](research/reviewed/spectrum-heimdall-half-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/spectrum-heimdall-supp3-analysis-2026-08-15.md`](research/reviewed/spectrum-heimdall-supp3-analysis-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/spectrum-navi-half-2026-08-15.md`](research/reviewed/spectrum-navi-half-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/spectrum-navi-half-v2-2026-08-15.md`](research/reviewed/spectrum-navi-half-v2-2026-08-15.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/success-sweep-raw-2026-08-10/omitted_shard1.md`](research/reviewed/success-sweep-raw-2026-08-10/omitted_shard1.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/success-sweep-raw-2026-08-10/omitted_shard2.md`](research/reviewed/success-sweep-raw-2026-08-10/omitted_shard2.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/success-sweep-raw-2026-08-10/omitted_shard3.md`](research/reviewed/success-sweep-raw-2026-08-10/omitted_shard3.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/t108-fence-halves-2026-07-28.md`](research/reviewed/t108-fence-halves-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/t410-rewrite-recovery-review-2026-09-26.md`](research/reviewed/t410-rewrite-recovery-review-2026-09-26.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/tempo-utilization-round-2026-07-28.md`](research/reviewed/tempo-utilization-round-2026-07-28.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/the-eye-synthesis-heimdall-nversion-2026-08-22.md`](research/reviewed/the-eye-synthesis-heimdall-nversion-2026-08-22.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/token-efficiency-package-for-serge-2026-09-27.md`](research/reviewed/token-efficiency-package-for-serge-2026-09-27.md) | ⚪ unmarked | untyped | — |
| [`research/reviewed/truth-grounding-landscape-2026-08-11.md`](research/reviewed/truth-grounding-landscape-2026-08-11.md) | ⚪ unmarked | untyped | — |

</details>

---
**2 current file(s) · 154 archived**
