---
akashic_id: art_20260823_t374-census-first-pass_a86c3d
akashic_sha: 4727b31a222f
schema_version: 1
status: current
type: report
date: 2026-08-23
title: t374-census-first-pass
gist: "# T374 census — first pass: every fact that lives in more than one place **Opened 2026-08-23 (post-midnight), claude.** Governing ruling: Da"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, migration, memory]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-23T01:41:10"
updated: "2026-08-23T01:41:10"
---
<!-- GENERATED PROJECTION of art_20260823_t374-census-first-pass_a86c3d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t374-census-first-pass

# T374 census — first pass: every fact that lives in more than one place

**Opened 2026-08-23 (post-midnight), claude.** Governing ruling: Daniil's launch
("Lets launch t374", gate-2026-08-22-t374-launch) ratifying master-declaration
v0: **Redis masters the live/ephemeral plane; git-tracked files master
everything durable; caches and echoes are derived.** F003 is the registered bet
on this census (complete + one passed drift drill by 09-05).

Method note: this first pass enumerates from the working set (the planes this
seat touched or read this week). The completing sweep — scan Redis key families
against `state/**` + `store/**` + `docs/library/**` and diff against this table
— is the second pass, listed at the bottom. A census that stops at the first
pass is a sample wearing a census's name; this table says so on its face.

## The table (fact class → stores → master → cause → verdict)

1. **Task ledger** — `state/coord/tasks.json` (git) + `ledger_update` bus
   echoes. Master: the git file (v0 durable). Cause: physics (durable master +
   live notification). Verdict: CLEAN in shape, but the master's write door has
   the known lost-update race (deferred CAS item, T271 sibling) — the census
   flags that a declared master without write serialization is a master by
   courtesy.
2. **Notes / decisions** — Redis atoms (`mem:decisions:*`, master per v0 live
   plane… but notes are DURABLE facts) + git library projections. **Tension
   with v0 worth Daniil's eyes:** notes are written through the Redis store yet
   are durable truths; today they survive via snapshot/mirror. Proposed: notes'
   master stays the Redis atom store WITH the snapshot ritual named as its
   durability organ, or notes migrate to git-master. Cause: physics. Verdict:
   NEEDS RULING (the one v0 doesn't cleanly cover).
3. **Lessons / learning store** — Redis `learn:experiment:*` (master) + recall
   indexes (derived, rebuild-from-hash-plane law already exists). Cause: cache.
   Verdict: CLEAN — the index rebuild law is the reconciler pattern already.
4. **Forecasts** — `state/coord/forecasts.jsonl` (git master), no second store,
   state = pure fold. Verdict: CLEAN — born under the doctrine, the model
   citizen.
5. **Bus streams** — `bifrost:inbox:*` + lanes (Redis, ephemeral by design) +
   promoted/salient records projected to the durable Ledger. Cause: physics
   (transport vs salience). Verdict: CLEAN **except the work/legacy dual-write
   twin — the TRANSITIONAL class with its end-date already ledgered (T045→T047:
   finish the cutover, retire the legacy stream).** The census's first
   end-date-or-it-becomes-permanent citation.
6. **Documents** — one authored doc exists as THREE copies: the `research/**`
   original (authored source), the `store/docs/*.jsonl` atom (canonical — "the
   atom is the truth" per the adopt door), the `docs/library/**` render
   (projection). Cause: by-design lineage. Verdict: CLEAN but UNDECLARED —
   nothing stamps the render with its atom's generation; the reconciler's
   drift-check needs that stamp (the c-map fence's Q5 honesty pin is the same
   law arriving from the map side).
7. **Seen/intent mailbox planes** — Redis hashes, single-store facts (who read
   what when). No duplication. Verdict: CLEAN.
8. **Verb registry / toolbelt** — `data/verb-registry/*.json` (git master),
   in-memory load-on-init projection. Cause: cache. Verdict: CLEAN by
   docstring's own law ("load-on-init projection, save-on-write truth").
9. **Secrets** — `.secrets/` files (master) + spawn-time env (derived) + **five
   readers that bypass the master's door via module-path constants
   (discord_inbound, discord_rooms, discord_setup, gemini_web, ops-redact) —
   the ACCIDENTAL class, live in the tree, already ledgered as T365.** The
   census adopts T365 as its first accidental-class finding rather than
   re-discovering it.
10. **Suite baseline / wishlist / fences / docs** — git-file masters, single
    store each. Verdict: CLEAN.
11. **Locks / presence / liveness / cursors** — Redis TTL keys, ephemeral by
    design and meaningless outside the live plane. Verdict: CLEAN (v0's Redis
    clause exists for exactly these).

## Census verdict counts (first pass)

CLEAN: 8 · TRANSITIONAL with end-date: 1 (bus dual-write, T045→T047) ·
ACCIDENTAL: 1 (secrets readers, =T365) · NEEDS-RULING: 1 (notes durability,
item 2 — the one real question this pass surfaces for Daniil).

## Second pass — the sweep, DONE 2026-08-23 (receipt: 25,954 keys, 1,219
## families, scan NOT truncated)

The families the first pass missed, now classified:

12. **`bifrost:idalias` (10,153 keys)** — the dual-write twin map: at `_emit`
    the bus records lane_mid ↔ legacy_mid sibling pairs (bus.py:603, 48h TTL).
    TRANSITIONAL, same end-date as item 5 (T045→T047); TTL makes it
    self-cleaning, so retirement is free once the legacy stream dies.
13. **The Akasha atom substrate as one class** — `events:raw` (6,281) +
    `narr:*` (~4,000) + `mem:decisions` (664) + `learn:*` (~1,150) +
    `artifact:index` (444) ≈ **12.5k keys of durable truth mastered in Redis
    BY ARCHITECTURE** (Akasha = the immutable append-only substrate). This
    subsumes item 2's notes question and sharpens the v0 amendment needed:
    not "git masters durable" but *git masters durable FILES; the atom
    substrate is Redis-mastered with the snapshot ritual
    (scripts/ops/snapshot_knowledge.py + mirror push) as its durability
    organ.* THE EXPOSURE: that ritual's restore path has NO dated receipt —
    the house has never once proven it can come back from the snapshot
    (the backup-door class, where a sibling backup door turned out to have
    never worked while memory called it proven). Filed as its own deferred
    drill; the ruling for Daniil is now ONE question: bless
    snapshot-as-durability-organ WITH a restore drill, or migrate durable
    atoms to git-master.
14. **Test-namespace residue** — `t-w43-*:idalias` and kin: leaked namespaces
    from test runs that crashed before cleanup. ACCIDENTAL, small (dozens of
    keys), permanent by default. Fix is cheap: test namespaces get a TTL at
    creation or a janitor sweep matches the `*_test_*`/`t-*` pattern.
15. **Telemetry planes** — `recall:use` (905), `bifrost:turn_metrics`,
    `lookback:hits`: derived-from-traffic counters, rebuildable or honestly
    losable. Verdict: CLEAN once the loss policy is declared in one line each.

## Census verdict counts (after second pass)

CLEAN: 10 · TRANSITIONAL with end-date: 2 (bus dual-write + its idalias twin
map, both T045→T047) · ACCIDENTAL: 2 (secrets readers =T365; test-ns residue) ·
NEEDS-RULING: 1 (the atom-substrate durability question, item 13 — subsumes
the notes question and is the census's single ask of Daniil).

## Remaining (third pass + reconciler)

- File inventory diff (`state/**`, `store/**`, `data/**`) — expected mostly
  covered; verify nothing undeclared.
- The reconciler slice: generation stamps on document renders (item 6), drift
  section in doctor, deliberate-skew drill (F003's bet), and the RESTORE drill
  item 13 demands.
