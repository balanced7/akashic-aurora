---
akashic_id: art_20260716_w5-honest-heal-deepseek-blind-design-hal_934cc4
akashic_sha: 6f514486c943
status: draft
type: report
date: 2026-07-16
title: W5 Honest Heal — DeepSeek blind design half (2026-07-16)
gist: "Cites: night-build-brief-2026-07-16.md (§W5), boot-ux-reconciliation-2026-07-15.md (P5/F4), test_rb25_drill2_heal.py (H2/H2b contract). ## P"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-16T00:33:18"
updated: "2026-07-16T00:33:18"
---
<!-- GENERATED PROJECTION of art_20260716_w5-honest-heal-deepseek-blind-design-hal_934cc4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# W5 Honest Heal — DeepSeek blind design half (2026-07-16)

Cites: night-build-brief-2026-07-16.md (§W5), boot-ux-reconciliation-2026-07-15.md (P5/F4),
test_rb25_drill2_heal.py (H2/H2b contract).

## Prior Art (3 systems, synthesized)

### 1. Kubernetes Garbage Collection — ownerReferences

K8s objects declare `metadata.ownerReferences` pointing to their owning resource.
The GC controller uses this to distinguish:
- **Cascade-delete:** child deleted when owner is deleted (expected lifecycle).
- **Orphan:** child whose owner is gone — these are the anomaly. `kubectl delete --cascade=orphan` explicitly creates orphans; unexpected orphans (owner deleted without cascade) are a bug signal.
- **No owner:** a standalone resource — normal, not an orphan.

**Synthesis:** The ephemeral roster IS an ownerReference system. Each ephemeral key family has an "owner" (the subsystem that creates it: Bus, control, liveness, etc.), and its Redis-only existence is EXPECTED (like a Pod owned by a Deployment). A key with NO owner in the roster AND no File counterpart = a real orphan. A key WITH an owner in the roster = ephemeral-by-design, not an orphan.

### 2. fsck / lost+found — expected vs. unexpected inodes

`fsck` walks the filesystem and finds inodes with no directory entry. The key design insight: fsck doesn't flag EVERY unlinked inode as an error. It distinguishes:
- **Expected unlinked:** inodes that still have an open file descriptor (a process is using them) — these are temporarily unlinked, not orphans.
- **Unexpected unlinked:** inodes with zero link count AND no open fd — these go to `lost+found` and ARE errors.

**Synthesis:** The ephemeral roster is the "open file descriptor" — it proves a key is expected to be Redis-only. A key not in the roster and not in File = the `lost+found` case. This is the allowlist pattern: "everything NOT on this list is suspicious."

### 3. Cassandra anti-entropy / read-repair — Merkle tree reconciliation

Cassandra's anti-entropy compares Merkle trees between replicas to find divergent data. The critical design pattern: **you must know what the expected set IS before you can identify divergence.** Cassandra builds the Merkle tree from the full dataset; heal builds its "expected" set from File keys + the ephemeral roster.

**Synthesis:** The drift check should compute: `Redis keys − (File keys ∪ ephemeral roster)`. Only the remainder is a real orphan. This is the mathematical formulation: `missing_in_file` becomes `missing_in_file EXCEPT those in the ephemeral roster`. The roster is the "known-expected Redis-only set."

## Design

### The Ephemeral Roster (single source of truth)

One constant defines every key prefix pattern that is EXPECTED to exist only in Redis:

```
EPHEMERAL_PREFIXES: tuple[str] — in core/comm/packet_spec.py (R6: this file is the roster home)
```

Each prefix is a pattern that matches a family of keys created and managed by the transport/control subsystems. They exist ONLY in Redis because:
- They are TTL'd (presence, locks, control flags)
- They are stream entries read via cursor (inboxes)
- They are fragment reassembly slots (transient, recoverable)
- They are coordination primitives (nudge, steer, runner lock)
- They are telemetry (metrics, progress, stalled-tracking)

The roster is an ALLOWLIST: anything NOT matching a prefix AND missing from File = a real orphan.

### SAFETY property (the non-negotiable constraint)

> **The roster is an ALLOWLIST of known-ephemeral. Anything unmatched stays flagged as a real orphan. Never hide one.**

This means:
1. A new ephemeral subsystem added WITHOUT updating the roster → its keys get falsely flagged as orphans (LOUD, but safe — the operator investigates).
2. A key that matches the roster BUT also exists in File → STILL an orphan (the roster doesn't override File existence; File is truth).
3. The roster can ONLY grow — removing a prefix is a regression (silent suppression of real orphans).
4. The roster is a tuple (immutable, importable without side effects).

### Census: every Redis-only key family

| Prefix pattern | Subsystem | Why Redis-only |
|---|---|---|
| `{ns}:presence:*` | Bus.register() | TTL heartbeat, auto-expire |
| `{ns}:inbox:*` | Bus (legacy inbox) | Stream entries, cursor-tracked |
| `{ns}:bell:*` | Bus (doorbell) | Ephemeral pub/sub channel |
| `{ns}:work:inbox:*` | Bus (work lane) | Stream entries, lane cursor |
| `{ns}:sig:inbox:*` | Bus (sig lane) | Stream entries, lane cursor |
| `{ns}:trace` | Bus (trace lane) | Shared ring, QoS0/BE |
| `{ns}:reasm:*` | Bus (fragment reassembly) | Crash-recovery slots, self-cleaning |
| `{ns}:control:*` | control.py | Halt/pause/nudge flags, TTL'd |
| `{ns}:worklive:*` | liveness.py | TTL work-live tracking |
| `{ns}:runner:*` | runner_lock.py | Consumer seat locks, TTL'd |
| `{ns}:cursor:*` | Bus (read cursors) | Hash of stream positions |
| `{ns}:daemon:*` | bifrost_daemon.py | Daemon singleton lock |
| `{ns}:doctor_paged:*` | doctor.py | Pager suppression, TTL'd |
| `{ns}:turn_metrics:*` | turn_metrics.py | Turn-level metrics |
| `{ns}:progress:*` | liveness.py | Progress/heartbeat keys |
| `{ns}:expect:*` | expectations.py | Expectation tracking (T061) |
| `{ns}:intent:*` | intent.py | Intent keys |
| `{ns}:stalled_since:*` | doctor.py | Runner stall tracking |
| `{ns}:engine:*` | engine_vitals.py | Engine vitals data |

| NOT ephemeral (has/needs File counterpart) | Subsystem |
|---|---|
| `bifrost:coord:ledger` / `:v` | task_ledger.py |
| `{ns}:incarnation:*` | incarnation.py |
| All Store-backed keys (notes, lessons, etc.) | store.py / HybridStore |
| Promoter event log keys | promoter.py |

### The `is_trace_kind` piggyback

Per the night-brief's coordination protocol and Claude's W4 note: `packet_spec.py` gains an `is_trace_kind(kind)` function (single classification source for W4 + any future consumer). This is NOT part of W5 directly, but it rides in `packet_spec.py` alongside the ephemeral roster since R6 designates this file as the roster home.

### heal_report change

Current:
```python
orphans = self.check_drift().get("missing_in_file") or []
# all Redis-only keys flagged as orphans
```

Proposed:
```python
drift = self.check_drift()
raw_orphans = drift.get("missing_in_file") or []
# Filter: only keys NOT matching any ephemeral prefix are real orphans
known_ephemeral = set()
for key in raw_orphans:
    if any(fnmatch.fnmatch(key, pat) for pat in EPHEMERAL_PREFIXES):
        known_ephemeral.add(key)
real_orphans = [k for k in raw_orphans if k not in known_ephemeral]
# Report: real orphans LOUD (same as today), ephemeral count as an INFO line
if real_orphans:
    lines.append("[heal] ... real orphans ... INVESTIGATE")  # same as today
if known_ephemeral:
    lines.append(f"[heal] {len(known_ephemeral)} ephemeral-by-design key(s) "
                 f"(presence/inbox/control/lane/...) — expected, no action needed.")
```

### Edge cases

1. **Drill namespace:** A test with `BIFROST_NAMESPACE=rb25drill3` has ITS OWN ephemeral keys, and those prefixes are namespace-scoped (`{ns}:presence:*`). The roster patterns use `{ns}` as a placeholder that gets resolved to the actual namespace at runtime. So `check_drift` receives keys with the active namespace prefix; the roster check must resolve `{ns}` to the current namespace before matching.

2. **Empty roster:** If `EPHEMERAL_PREFIXES` is empty (or not importable), behavior is unchanged from today — all Redis-only keys are flagged. Fail-open: never hide a real orphan because the roster failed to load.

3. **Roster not importable:** `check_drift` wraps the import in try/except; on failure, reverts to current behavior (flag everything). Never suppress.

4. **Key that matches BOTH ephemeral roster AND exists in File:** This shouldn't happen (ephemeral keys aren't written to File Store), but if it does: treat it as a REAL orphan. The roster is an allowlist for "Redis-only IS expected"; File existence overrides that expectation.

## Pre-registered Pins

| Pin | What it tests | Verdict claim |
|-----|---------------|---------------|
| **W5-P1** | Redis-only key matching ephemeral roster → NOT in orphan report | EPHEMERAL-FILTERED |
| **W5-P2** | Redis-only key NOT in ephemeral roster → IS in orphan report (unchanged) | REAL-ORPHAN-LOUD |
| **W5-P3** | Key that matches roster BUT also exists in File → STILL an orphan (File wins) | FILE-OVERRIDES-ROSTER |
| **W5-P4** | In-sync backends + ephemeral keys → heal report has INFO line (not empty) | EPHEMERAL-COUNTED |
| **W5-P5** | Roster import fails → behavior unchanged (flag everything, fail-open) | FAIL-OPEN |
| **W5-P6** | New ephemeral prefix NOT in roster → flagged as orphan (allowlist gap = LOUD) | ALLOWLIST-GAP-LOUD |
| **W5-P7** | In-sync backends + NO ephemeral keys → heal report empty (no noise, today's behavior) | CLEAN-QUIET |
| **W5-P8** | Multiple ephemeral families present → single INFO line with total count | AGGREGATED-COUNT |

## Relationship to Claude's half

Claude's W5 note in the night brief: "ephemeral-namespace roster at ONE source (packet_spec.py — the R6 roster home); heal_report flags only durable-class orphans loud, ephemeral-by-design render as a count."

Open questions for reconciliation:
- Should the roster be a tuple of glob patterns or a set of literal prefix strings? (I propose glob patterns with `fnmatch` — some keys like `{ns}:engine:*` vs `{ns}:engine_vitals:*` may need the flexibility, but globs are more expensive.)
- Should `check_drift` itself be modified, or only `heal_report`? (I propose only `heal_report` — `check_drift` is the raw data; the interpretation layer is `heal_report`. This keeps the API surface unchanged.)
- What format for the INFO line? (Proposed: `N ephemeral-by-design key(s) (presence/inbox/control/lane/...) — expected, no action needed.`)
- Should `is_trace_kind` ride in this commit or separately? (I propose together — both are `packet_spec.py` changes and R6 designates it as the roster home.)
