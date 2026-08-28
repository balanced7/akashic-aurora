# T370 shadow shelf Slice 0 — implementation receipt

**Run date:** 2026-08-28 UTC
**Driver / implementation owner:** Sunshine
**Independent reconciler:** Vandor
**Authority:** offline substrate evidence only; this receipt does not authorize live wiring

## What was exercised

`core.recall.shadow_shelf` is a standard-library-only observation/judgment substrate. It has no
production caller and imports no live recall detector, model, Bifrost, Discord, EventLog writer,
canonical Store writer, or task-ledger writer. The dated `check_wiring` exception records that
intentional built-ahead state and expires on 2026-09-30. Its exit condition is a separately
reviewed adapter that asks the real production detector and hands terminal slots into this module,
or deletion if the pilot is rejected.

Rill was not assigned, messaged, interrupted, or used for acceptance work.

## Test receipt

The pre-production RED gate is commit `f9d77b69`. After implementation:

```text
py -m pytest tests/test_t370_shadow_shelf_storage_red.py \
  tests/test_t370_shadow_shelf_reader_red.py -q
.....................................                                    [100%]
37 passed
```

The first implementation pass produced 36 passes and one false RED. Two adjacent registry pins
reused the same contract tuple while requiring the process-lifetime registry to both refuse and
accept its second name. Each node passed alone; the combined file failed. The correction gave the
same-name conflict pin a distinct local tuple. No production reset or alias weakening was added.

The built-not-wired guard was also exercised directly:

```text
py scripts/checkers/check_wiring.py
PASS: every core/ module is wired to a production path
      (21 known-standalone exception(s)); no NEW unwired public function
      (119 on the frozen backlog).
```

The checker still emits five pre-existing stale-backlog warnings. A focused wiring-oracle run
produced 25 passes and one pre-existing failure:

```text
tests/test_t159_oracle_field_of_view.py::test_k14_narrowing_the_universe_hides_nothing
```

That failure names `core/comm/remote_relay.py` and `core/coord/shift_loop.py`, which are now reachable
but still present in the old exception backlog. The new shadow-shelf entry is genuinely unreachable
and remains covered by the module-level gate, so it is not one of the K14 blind spots.

## Bounded load and kill/restart drill

A deterministic temp-directory replay wrote 2,000 complete envelopes with four bounded references
per emitted slot. Every fifth challenger was deliberately silent. No canonical or communication
surface was available to the drill.

| Persisted rows | DB bytes | WAL bytes | Physical bytes per envelope | Elapsed write time |
|---:|---:|---:|---:|---:|
| 1 | 4,096 | 78,312 | 82,408.00 | 0.82 ms |
| 10 | 4,096 | 263,712 | 26,780.80 | 3.01 ms |
| 100 | 4,096 | 2,130,072 | 21,341.68 | 19.72 ms |
| 500 | 843,776 | 4,136,512 | 9,960.58 | 102.62 ms |
| 1,000 | 1,925,120 | 4,136,512 | 6,061.63 | 210.25 ms |
| 2,000 | 5,365,760 | 4,152,992 | 4,759.38 | 430.90 ms |

At the sampled scale, rows grew 20x from 100 to 2,000 while DB+WAL bytes grew 4.46x. This falsifies
superlinear amplification for this fixture and range; it is not a production traffic estimate.
The measured WAL remained below the 100 MiB pause threshold. A bounded disagreements-first peek
returned exactly 25 rows in 34.309 ms, with disagreements first.

The injected before-commit kill produced:

```text
rows after injected kill:          0
rows after close/restart:          0
rows after idempotent retry:       1 complete cohort
```

## What this does and does not clear

Slice 0 clears the isolated substrate questions exercised by the 37 pins: contract identity,
complete cohort atomicity, visible terminal silence/error/abstention, bounded output, separated
judgment authority, denominator-bearing counters, loud read states, known-wrong controls, visible
compaction, resource reporting, and deterministic no-writer replay.

It does **not** clear live shadowing. The durable eligible-event denominator is still unidentified;
the previously observed 538 and 42 injection counts are TEMP-directory-lifetime telemetry, not
daily rates. The champion is still a fingerprinted fixture rather than the current detector. M9
therefore remains with Vandor: identify the durable event source and reconcile measured writes/day
before any adapter, watcher, hook, or hot-path import is proposed.

## Independent acceptance

Vandor returned **ACCEPT** read-only in Bifrost reply `1787882451422-0`; he edited nothing. He reran
all 37 preregistered pins and independently verified from source that:

- the module's standard-library-only dependency cone makes the no-live-writer boundary structural;
- no promotion, usefulness, or graduation surface exists;
- the fixture champion and TEMP-lifetime 538/42 observations are labeled without borrowed
  production authority;
- M9 remains sequenced before any adapter, watcher, hook, or hot-path import; and
- the 2026-09-30 `check_wiring` expiry is executable enforcement rather than prose decoration.

He identified one non-blocking process defect: the fixture-collision correction to the sealed RED
file rode in the same commit as the implementation. The diff did not weaken an assertion, and
DeepSeek independently confirmed the exact process-lifetime collision, but an outside reader has to
inspect that diff to distinguish the correction from a moved goalpost. Future sealed-pin corrections
must land in their own commit before the implementation that passes them.

## Scratch mutation receipt — five critical pins bind

Vandor explicitly scoped his ACCEPT: he had not mutation-tested. Sol then loaded five scratch copies
of the committed module through a temp-only `sitecustomize`, changed one invariant per copy, and ran
only the pin intended to catch it. Production files and imports were untouched.

| Scratch mutation | Expected binding pin | Observed result |
|---|---|---|
| all-error comparison returns `agreement` | exact six-state matrix | pin failed on `agreement != unavailable` |
| disable the 8 KiB candidate cap | oversize becomes visible error | pin failed on `emitted != error` |
| skip the injected `before_commit` fault | zero-or-complete kill behavior | pin failed because `Kill` was not raised |
| return every cohort as a control | known-wrong control discrimination | pin failed because organic agreement leaked in |
| allow judgment over an observation DB path | separate authority planes | pin failed because construction did not refuse |

All five mutants were killed by their intended pin (five expected non-zero pytest exits). The six
scratch source files, six generated bytecode files, and their two exact temp directories were then
removed. This strengthens causal binding for five load-bearing invariants; it is not a claim that
every line or every pin has mutation coverage.
