---
akashic_id: art_20260712_rb-25-drill-2-store-divergence-heal-live_b93ed8
akashic_sha: 19e3bd18b940
status: draft
type: report
date: 2026-07-12
title: "RB-25 Drill 2 -- store-divergence heal: live transcript (2026-07-12)"
gist: "# RB-25 Drill 2 -- store-divergence heal: live transcript (2026-07-12) Isolated on REDIS_DB=15 + temp file (the live notes/ledger are never "
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-12T01:57:16"
updated: "2026-07-12T01:57:16"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-drill-2-store-divergence-heal-live_b93ed8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-25 Drill 2 -- store-divergence heal: live transcript (2026-07-12)

# RB-25 Drill 2 -- store-divergence heal: live transcript (2026-07-12)

Isolated on REDIS_DB=15 + temp file (the live notes/ledger are never a drill target).
Bars H1/H2/H2b/H4 all met; the H2b render gap (boot was silent about missing_in_file)
was found + fixed -- HybridStore.heal_report(), wired into cmd_boot. Pins:
tests/test_rb25_drill2_heal.py (5/5).

---

```
=== RB-25 DRILL 2 LIVE: store-divergence heal ===
SETUP DRIFT: File-ahead=['rb25d2rec:file-ahead']  Redis-orphan(missing_in_file)=['rb25d2rec:redis-orphan']
--- operator heal_report() (exactly what boot now prints) ---
  [heal] Redis was behind -- backfilled 1 key-structure(s) from the durable File (File is source of truth).
  [heal] 1 Redis-only key(s) have NO File record and are NOT backfilled (File is truth): rb25d2rec:redis-orphan. Investigate -- an orphan is a write that never reached the durable side.
H1 case(a) in Redis after heal: FILE_TRUTH
H2b case(b) in File after heal: None  (None = File untouched, correct)
H2b gap still reported by check_drift: ['rb25d2rec:redis-orphan']
H4 re-run heal (healed side now quiet, orphan still flagged): ['[heal] 1 Redis-only key(s) have NO File record and are NOT backfilled (File is truth): rb25d2rec:redis-orphan. Investigate -- an orphan is a write that never reached the durable side.']
=== DRILL 2 COMPLETE -- H1/H2/H2b/H4 all met ===
```
