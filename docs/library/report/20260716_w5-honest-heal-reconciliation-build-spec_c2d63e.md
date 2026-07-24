---
akashic_id: art_20260716_w5-honest-heal-reconciliation-build-spec_c2d63e
akashic_sha: ca7ed8adb650
status: current
type: report
date: 2026-07-16
title: "W5 Honest Heal — Reconciliation & build spec (2026-07-16)"
gist: "analysis. Supersedes the header of `research/reviewed/deepseek-w5-heal-design-2026-07-16.md`. Reconciler: claude (Opus 4.8). SAFETY-CRITICAL"
tenant: solo
visibility: fleet
seats: []
category: [migration, identity, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260716_w5-honest-heal-deepseek-blind-design-hal_934cc4
    rel: cites
created: "2026-07-16T00:43:16"
updated: "2026-07-23T21:42:23"
---
<!-- GENERATED PROJECTION of art_20260716_w5-honest-heal-reconciliation-build-spec_c2d63e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# W5 Honest Heal — Reconciliation & build spec (2026-07-16)

analysis. Supersedes the header of `research/reviewed/deepseek-w5-heal-design-2026-07-16.md`.
Reconciler: claude (Opus 4.8). SAFETY-CRITICAL slice — full-fence tier.

## The empirical finding that reframes W5 (claude's independent contribution)

DeepSeek's half designed a roster of ephemeral-transport prefixes (allowlist → quiet). Correct
as far as it goes — but I ran the **actual keyspace census** before trusting any memory-based
roster, and it changes the shape of the problem.

`check_drift` (core/foundation/store.py:789) computes `missing_in_file = redis_keys − file_keys`
over the **HybridStore's own two backends**. But that Redis instance is **shared** by every
subsystem. So `missing_in_file` is really "every Redis key the Store's File backend doesn't have"
— which is three very different things, not one:

Actual census of the 4867 "orphans" (py check_drift, grouped by family):

| Class | Families (count) | Truth |
|---|---|---|
| **1. Ephemeral transport/control/telemetry** | bifrost:work 58, inbox 18, cursor 17, generation 17, turn_metrics 114, delta 61, presence/runner/lock/expect/trace…, + drill namespaces (rb25* , bifrost_t039a*/t045* ~hundreds) | never durable anywhere — correctly Redis-only |
| **2. Store-managed DURABLE families, Redis-ahead** | events:raw 2383, narr:beat 780, learn:experiment 191, mem:decisions, recall:use, lookback, knowledge_map | **the bulk (~3500).** These families ARE in File (File owns events:raw 1761, narr:beat 339, learn:experiment 91…) — Redis just has *more*. Durable-family drift, not unknown orphans |
| **3. True unknowns** | (whatever matches neither) | the real "investigate NOW" signal |

**Why deepseek's roster-only design is insufficient (the adversarial finding):** it quiets Class 1
(~a few hundred). Class 2 — the ~3500-key bulk — is NOT ephemeral, so the allowlist correctly
leaves it LOUD… which means the heal *still* cries "3500 orphans — a write that never reached the
durable side" about **durable knowledge families**. That's not just noise, it reads as data-loss.
The wolf-cry isn't fixed; it's made scarier. The census is what surfaces this — memory wouldn't.

## The reconciled design — 3-way classification (not binary)

`heal_report` classifies each `missing_in_file` key into exactly one of three buckets, using two
sources of truth that already exist:

1. **Ephemeral roster** (deepseek's half, adopted + credited) — explicit allowlist in
   `packet_spec.py` (R6 roster home) of families that are EXPECTED Redis-only from the Store's
   view: bus transport, presence/liveness, control/coord, telemetry, durable-elsewhere subsystems
   the Store doesn't own (coord:ledger, incarnation), and drill namespaces. → **quiet count line.**
2. **Store-managed durable families** — derived automatically from `self._file.keys("*")` (the
   families the Store actually owns durably). A key whose family is in File but is Redis-only =
   **durable-family drift** → **visible, calm** line: "N durable-family keys Redis-ahead (events,
   narr, learn…) — expected for append/TTL-trimmed families; investigate if growing." Self-
   configuring: no hand-maintained list of durable families, it reads the File key-space.
3. **Neither** → **LOUD** "UNKNOWN Redis-only key(s) — investigate" (today's behavior, but now
   only for genuine unknowns, not the whole 4867).

### Safety invariants (deepseek's, preserved + extended)

- Allowlist, never denylist: a family in NO bucket-1/2 source stays LOUD (Class 3). Never hide one.
- Fail-open: roster import fails OR `_file.keys()` raises → every orphan flagged LOUD (today's
  behavior). A broken classifier can only make the heal *louder*, never quieter.
- File is truth: a key that (impossibly) matches the roster but also lives in File is treated as
  Class 2 (durable), not silenced.
- Durable-family drift is VISIBLE, not hidden: the calm line still prints the count + top families,
  so an operator can spot an abnormal spike (fsck "lost+found is visible" principle) — it is not
  suppressed, only de-escalated from "INVESTIGATE" to "expected-ish, watch if growing".

## Open questions — resolved

1. **fnmatch globs vs literal prefixes?** — fnmatch. The census proves the need: `agent:*:events`
   and drill families like `bifrost_t039a_*:trace` have mid-string wildcards a prefix `startswith`
   can't express. Cost is a non-issue: heal runs once per boot; compile-once the patterns.
2. **Modify check_drift or only heal_report?** — heal_report only. `check_drift` stays the raw
   backend-diff (pure data, other callers untouched); classification is the interpretation layer.
3. **INFO line format?** — three lines, most-severe first: UNKNOWN (loud) → durable-drift (calm,
   top families + counts) → ephemeral (quiet count). Each carries a drill where actionable.
4. **is_trace_kind ride-along?** — ALREADY LANDED in the W4 commit (packet_spec.is_trace_kind on
   origin). Moot; deepseek should pull.

## A real finding this surfaces (not silenced — the point of W5)

Class 2 is ~3500 keys of durable knowledge (events:raw +2383, narr:beat +780, learn:experiment
+191) that are in Redis but not the Store's File backend. Most likely retention-lag /
append-heavy families where Redis holds more than the last File snapshot — but the magnitude
warrants a look. W5's calm line makes this **visible and watchable** instead of buried in a
4867-key wall. → propose follow-up **T082: audit durable-family Redis↔File drift** (is events:raw
File persistence lagging, or is check_drift's per-key granularity mismatched to how the event log
compacts?). W5 does NOT fix that — it makes it legible, which is the honest-heal contract.

## Build (claude lane; deepseek cross-verifies)

- `core/comm/packet_spec.py`: `EPHEMERAL_PREFIXES` tuple (fnmatch patterns, `{ns}` resolved at
  match time) + `is_ephemeral_key(key, ns)` helper. Empirically grounded from the census above.
- `core/foundation/store.py` `heal_report`: the 3-way classification, fail-open, family-grouped
  counts. `check_drift` untouched.
- Pins (deepseek's 8 adopted + claude additions for the durable-drift class):
  W5-P1 ephemeral→quiet · W5-P2 unknown→loud · W5-P3 file-family key→durable-drift not unknown ·
  W5-P4 durable-drift line present+calm · W5-P5 roster import fails→all loud (fail-open) ·
  W5-P6 allowlist gap→loud · W5-P7 in-sync→quiet · W5-P8 counts reconcile (ephemeral+durable+unknown
  == total, lossless) · W5-P9 durable family derived from _file (self-configuring) ·
  W5-P10 fnmatch mid-wildcard (agent:*:events) classified.

Nothing builds to `done` until deepseek cross-verifies the 3-way (especially: does the durable-
drift de-escalation ever hide a Class-3 unknown? — the one safety question to hammer).
