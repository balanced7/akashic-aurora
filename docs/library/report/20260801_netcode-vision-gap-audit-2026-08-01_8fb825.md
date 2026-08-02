---
akashic_id: art_20260801_netcode-vision-gap-audit-2026-08-01_8fb825
akashic_sha: 42df6c49d8b2
schema_version: 1
status: current
type: report
arc: T108
date: 2026-08-01
title: netcode-vision-gap-audit-2026-08-01
gist: "37 netcode mechanisms audited vs code+ledger: 3 shipped, 17 partial, 17 not built; fleet liveness sensor reads 78/80 DEAD while seats work"
visibility: fleet
body_type: markdown
seats: [opus-engineer]
category: [bus, security, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T13:33:38"
updated: "2026-08-01T13:33:38"
---
<!-- GENERATED PROJECTION of art_20260801_netcode-vision-gap-audit-2026-08-01_8fb825 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# netcode-vision-gap-audit-2026-08-01

# The Netcode Vision vs. the Build - Final Gap Audit
**Source of truth:** `research/reviewed/multiplayer-netcode-prior-art-2026-07-28.md` | **Repo:** `E:/AI-Setup` | **Date:** 2026-08-01

**Verdict.** The wire shipped; the authority did not. Across 37 mechanisms the doc names or implies, **3 are SHIPPED-and-enforced, 17 PARTIAL, 17 NOT_BUILT**. Everything on the *send* side is real and load-bearing: lanes are derived from kind by the door and senders cannot override it (`core/comm/packet_spec.py:186`, `core/comm/bus.py:466`), byte-level fragments carry a manifest (`packet_spec.py:573`), integrity is checked at the consume door (`bus.py:857`), and the shared cursor refuses stale and backwards writes at the resource (`bus.py:1089-1110`). Everything that would make the system *authoritative* is prose or a file with no caller: the mailbox as the server that says what exists (T095 slice 2), the role queue as "the first authority-side router" (T108 - `grep role_queue` returns its own docstring plus two test files, and `bifrost:role:*` is empty), verify-before-propagate (T1), one-writer-per-key-family (LAW C), and every-loop-owns-its-tick (LAW A). Nine of those unbuilt mechanisms carry **no ledger task at all**, so nothing was ever scheduled to build them. The single most consequential finding is not in the doc's own list: the roster's liveness sensor has one writer that fires only on boot and manual sync against a 180-second TTL, so the live fleet reads **78 of 78 seats DEAD while seats are working** - which means the reaper, the send-door "unattended recipient" warning, and the doctor's "genuinely working, not wedged" retraction are all reading from a sensor that is off.

---

## SCORECARD

Sorted gaps-first. "Enforced" means something fails or refuses when the rule is broken; "wired" only means a production path reaches it.

| Mechanism | Doc section | Verdict | T-number | One-line receipt |
|---|---|---|---|---|
| Mailbox index as SERVER-SIDE AUTHORITY | §1 authority | NOT_BUILT | T095 / T108 S2 | `core/comm/mailbox.py:17` "M0 is OBSERVATIONAL ONLY"; no delivery, ack or wake path reads it |
| Role queue = first authority-side router | §1, §5 | NOT_BUILT | T108 | `grep role_queue --include=*.py` -> own docstring + 2 tests; live `bifrost:role:*` = [] |
| Freshness-TTL drop-as-stale | §5 channels | NOT_BUILT | T108 | `role_queue.py:132-141` default `freshness_s=None` stamps `""`; module has never executed |
| RESUMED marker ("replayed N, now live") | §3 gateway | NOT_BUILT | T108 S3 | `roster.py:38-39` TTL 180s < gap 600s -> condition unsatisfiable; green only via `_beat_ts` test backdoor |
| LAW A - every loop owns its tick | LAW A | NOT_BUILT | **none** | `roster.heartbeat` has one production caller (`agent/bifrost_pull.py:352`); live roster 78/78 DEAD |
| Retire legacy stream (end dual-write) | §5 precondition | NOT_BUILT | T047 | measured: 50/50 messages exist in exactly 2 copies; `packet_spec.py:315-318` dual-write defaults ON |
| LAW B generalized to every shared structure | LAW B | NOT_BUILT | **none** | `learning_store.py:443-444` delete+rpush still live on the clobbered key; no `rename` in the Store ABC |
| LAW C write-path checker | LAW C | NOT_BUILT | **none** | 14 files in `scripts/checkers/`; none is a writer-ownership census |
| T1 verify-before-propagate (the rule) | §8 | NOT_BUILT | **none** | `verify_integrity` has 2 call sites, both consume doors (`bus.py:857`, `bifrost_pull.py:99`); 0 propagators |
| T1(a) promoter re-emits unverified | §8 | NOT_BUILT | **none** | `promoter.py:39-53` takes no sha, imports no packet_spec; `:50` stores content with no digest |
| T1(b) harmonize re-emits unverified | §8 | NOT_BUILT | **none** | `harmonize_knowledge.py` has no `hashlib`; guarded only by a refuse-to-run env gate at `:169-176` |
| T1(c) atom projections re-emit unverified | §8 | NOT_BUILT | **none** | `projection.py:52` copies the stored claim; no code hashes a projection body; verifier has 0 automated callers |
| T1(e) `doc new --from-bus` (unnamed offender) | §8 | NOT_BUILT | **none** | `agent_cli.py:1809-1814` reads raw stream fields, bypassing `bus.py:857` entirely |
| T1(d) Discord bridge | §8 | NOT_BUILT | **none** | `git ls-files \| grep -i discord` -> one design `.md`, zero `.py`. Forward-looking, not a regression |
| T2 logical multi-part manifest | §8 | NOT_BUILT | **none** | `mailbox.py:207-231` keys incompleteness on byte-frag only; a 3-message position renders WHOLE |
| T116 idempotency_key | §8 seam | NOT_BUILT | T116 (parked) | `packet_spec.py:22` names it only in a not-hashed list; zero producer stamp, zero consumer check |
| T4 rarest-first durability ops | BitTorrent T4 | NOT_BUILT | **none** | `grep -rni "rarest\|sole.copy\|scarcity"` over core/ scripts/ agent/ -> 0 hits |
| Seat stream = the wire packet | §2 | PARTIAL | T108 S1 | `bus.py:818-821` orders legacy before seat, so the seat copy is always the sha-dedupe discard |
| Seat cursor = the ack baseline | §2 | PARTIAL | T108 S1 | `bus.py:937-940` writes it; live `bifrost:cursor:seat:*` = **0 keys** |
| Three layers DISTINCT and COMPOSED | §1-2 | PARTIAL | T095 + T108 | `mailbox.py:59-66` cannot see the seat stream; `:330-331` reads layer 2's predecessor cursor |
| RESUME from own cursor | §3 | PARTIAL | T108 S1 | code live on the default path, but 3 directed messages sit unread at cursor `"0"` |
| Theft / mis-wake "structurally impossible" | §4 | PARTIAL | T108 | prevented by a read-time skip (`bus.py:874-891`) - the mechanism the doc says games reject |
| INVALID SESSION -> re-boot + seed-at-tail | §3 | PARTIAL | T086 S1 / T108 S3 | tombstone fires (148 live keys); `seed_cursor_at_tail` has zero claude callers; no trim detector |
| Reaper as a bounded resume window | §3 | PARTIAL | T108 S4 | manual-only (`agent_cli.py:3606-3612`); 2 messages stranded 25-27h; 1 rehome in namespace history |
| AoI: filter at source, not at consume | §4 | PARTIAL | T108 | only source routing is sender-supplied (`bus.py:281-284`); no interest set exists anywhere |
| Lane split work / sig / trace | §5 | PARTIAL | T039-T045 | enforced at the send door; last 3000 of `bifrost:broadcast` = 2968 trace with 2 sig packets behind |
| D2 stale-mail gate (nearest freshness analogue) | §5 | PARTIAL | none (kimi D2) | cursor advances at `bifrost_pull.py:246`, gate runs at `:269`; notice text says "nothing auto-acked" |
| clobber_scan (W47) | LAW B adjacent | PARTIAL | W47 | control-plane families only (`clobber_scan.py:29`); absent from `ship.py` and `ci.yml` |
| LAW C violation #1: `learn:experiments:all` | LAW C | PARTIAL | **none** | five writers across four loops; the live one is an unguarded read-modify-write |
| LAW C violation #2: the twin cursor | LAW C | PARTIAL | RB-21 / T030 | Lua guards the shared cursor; `bus.py:939` + `reaper.py:277` raw-hset the seat cursor |
| LAW D per-lane retention | LAW D | PARTIAL | T039-T045 | work is a 10k ring that drops oldest; refuse-write contract deferred at `packet_spec.py:214-215` |
| T3 have-summaries a successor can diff | BitTorrent T3 | PARTIAL | T108 S5 | `roster.py:157-182` returns cursor pointers only; `seat_inbox` reads `0` on every row |
| T5 tracker: pointers, never payload | BitTorrent T5 | PARTIAL | T108 S2 | data paths survive the directory (`bus.py:310-319`); "never payload" has no guard, `phase` is free text |
| Prediction / convergence / rollback | §6 | PARTIAL | T053 / T031 | fence seal genuinely refuses (`fence_workspace.py:174-221`) but `fences/` does not exist; no rollback code |
| Mailbox index as an operator projection | §1 | **SHIPPED** | T095 M0/M1 | `zcard bifrost:mailbox:z:claude` = 1511; boot line exempt from `_DROP_ORDER` (`context.py:46`) |
| Heal no longer clobbers a live list | LAW B named site | **SHIPPED** | none (956dfc5) | `store.py:999-1004` backfill-only; pinned against a real redis:7 service in `.github/workflows/ci.yml` |
| Prioritized replication (recall top-K) | prioritized replication | **SHIPPED** | none (predates doc) | `at_action.py:1282-1283` top-K, `:1569` 900-char cap, `:1528-1538` N-of-M honesty line |

---

## THE LOAD-BEARING GAPS

### 1. The fleet has no pulse. Liveness is inferred from a heartbeat nobody beats.
**Promised (LAW A):** every recurring organ declares its tick and beats it - "hook: per-action; runner: per-message."
**Exists:** `core/comm/roster.py:38` sets `WORKLIVE_TTL_S = 180`. `roster.py:141` is the only writer. `agent/bifrost_pull.py:352` is the only production caller, reached from boot, manual `bifrost-sync`, SessionStart, and UserPromptSubmit. No PreToolUse, PostToolUse, or Stop hook beats it (verified by grep over `agent/harness/hooks/*.py` and `scripts/hooks/*.py`).
**What breaks:** a seat working continuously inside one turn disappears after 180 seconds. Live proof from the audit session itself: `roster --json` reported the auditing seat `claude#6ac75463` as `state: DEAD, beat_age_s: 693` while it was mid-audit making tool calls. Fleet-wide: 78 rows, 77 DEAD, 1 STALE, zero LIVE at any point. Three organs read that sensor as truth - `reaper.py:90` (`state == "DEAD" -> return True`, so **every live seat is currently reapable**), `bus.py:296-325` (every directed send now prints "UNATTENDED RECIPIENT" against healthy seats, training a real warning into noise), and `doctor.py:379-388` (the "genuinely working" retraction can essentially never fire). The only thing preventing the failure the reaper was built to prevent is that nobody types `roster --reap`.
**Cheapest slice:** beat `roster.heartbeat` from the PostToolUse hook - a genuine per-action tick, the exact shape `core/comm/incarnation.py:35` + `scripts/hooks/claude_stop.py:228-229` already use for the incarnation card. One hook line. Alternative one-constant fix: raise `AKASHIC_WORKLIVE_TTL_S` above realistic turn length; note that raising it past 600 also makes the RESUMED marker (below) fire for the first time, because one constant currently breaks two mechanisms.

### 2. The authority layer never landed - which is why finding your own mail is still hand work.
**Promised (§1-2):** "the message is ALREADY an object; the index just isn't authoritative yet," and slice 2's job is "to make the authority load-bearing." The role queue is "the first authority-side router."
**Exists:** the index is a genuine, populated, well-built *render surface* - 1511 entries for claude, nine agent indexes, an evidence ladder at `mailbox.py:55` + `:352-366`, a CLI door and a boot whisper. But `mailbox.py:17` states the containment rule ("writes nothing outside `{ns}:mailbox:*`"), `role_queue.py:19` states the layer contract ("mailbox: rebuildable operator projection - renders, never owns"), and `packet_spec.py:255-259` classifies the whole family as regenerable and exempt from orphan alarms. The router that was supposed to own delivery, `core/comm/role_queue.py`, has **zero production importers** and its key families (`bifrost:role:*`, `*rolefence*`, `*rolegen*`) are all empty - it has never run once. `docs/MAP.md:114` already marks the row GAP. The one place the T108 design names it, the reaper, routes around it: `reaper.py:228` strips `to_incarnation` and `:239` re-sends onto the shared agent inbox.
**What breaks:** nothing in delivery, consume, ack, or wake reads the index, so "which of my messages are actually handled" remains a question answered by eye. Two directed messages have been stranded on seat streams for **25.3h and 27.1h** with no rehome mark (`bifrost:rehomed:*` holds exactly one key, from a single past manual run) - the doc's "never silent loss" is falsified live, not in theory. Drop-as-stale is dead code because it lives inside the module that never runs.
**Second, quieter finding on the same file - a live durability contradiction:** `mailbox.py:413-425` records that message *bodies* are not re-derivable ("935 bodies stored, only ~30 still recoverable from streams") and `:448-452` preserves them across rebuild, which makes the index the **sole copy of ~900 message bodies** - inside a key family `packet_spec.py:255-259` declares regenerable, Redis-only by design, and exempt from orphan alarms. A Redis flush loses them silently.
**Cheapest slices, in order:** (a) flip the `packet_spec.py:255-259` allowlist comment and give `mailbox:msg:*` File backing, or stop storing bodies - the contradiction is one decision, and today it is unflagged; (b) give the role queue its first real traffic by making `reaper.py:239` publish to `role_queue.publish` instead of `b.send`, which is the routing the T108 text already specifies; (c) then, and only then, T095 slice 2.

### 3. Dual-write is measured at exactly 2x, and the two obvious fixes cancel each other.
**Promised (§5):** channels bind - "trace never queues ahead of control."
**Exists:** enforced at the send door, unenforced at the consume door. `packet_spec.py:315-318` defaults `BIFROST_LANES_DUAL_WRITE` ON and nothing turns it off; `bus.py:529-532` writes the legacy copy unconditionally. Measured live: the last 400 entries of `bifrost:inbox:claude` are 50 distinct shas, 49 also present by sha in `bifrost:work:inbox:claude` and the 50th on the sig lane - **every message in exactly two copies**. Lane-priority consume exists only inside `bifrost_api.work_drain` behind `BIFROST_CONSUME_LANE == "work"` (`bifrost_api.py:263-265`), which **no launcher sets** - while `agent_cli.py:3686` defaults `BIFROST_WAKE_LANE` to `work`.
**What breaks:** the default consume door is a flat `xread` with a bounded count over the legacy stream (`bus.py:817-821`). Measured on the last 3000 entries of `bifrost:broadcast`: trace 2968, and the two sig-lane control packets (`interrupt` 1785601076177-0, `steer` 1785598426668-0) sit interleaved *behind* them - while `bifrost:sig:broadcast` holds only those same 2 entries. Control queues behind voice on the door the fleet actually reads. The lived incident is already recorded: `docs/JOURNEY.md:403-411` - wake rode lanes, consume rode legacy, and the lane cursor sat frozen for a day.
**The ordering trap - read this before scheduling:** turning on lane consume *disables the seat-stream read*. `bus.py:806` gates the seat leg on `since is None and streams is None`, and all three legs of `work_drain` pass both (`bifrost_api.py:325-327, 343-345, 368-369`). So the cheap fix for gap 3 silently deletes the RESUME leg from gap 4/item (a), and after T047 lane mode becomes the *only* mode.
**Cheapest slice:** teach `work_drain` to include the seat stream (one entry in the xread map, plus lifting the `bus.py:806` gate). Then set `BIFROST_CONSUME_LANE=work` alongside the existing `BIFROST_WAKE_LANE` default at `agent_cli.py:3686`. T047 comes after both, not before.

### 4. LAW C was never built as a rule, and the exemplar it was written from has since been violated.
**Promised (LAW C):** "for every shared key family, name its ONE writing organ per phase; a second writer is a design defect by definition. (Checker candidate - the same shape as `check_door_parity`.)"
**Exists:** no checker. `scripts/checkers/` holds 14 files and none is a write-path census. The nearest artifact, `durable_reconcile.py:47-72`, answers a different question (which plane is authoritative). **The clobber was fixed at one site; the collision was not removed.** `learn:experiments:all` - the key from the 956dfc5 index clobber, blast radius `file=16 redis=485` - now has **five writers across four loops**: `learning_store.py:443-444` (live path, and it is an unguarded lrange -> delete -> rpush read-modify-write, so two concurrent lesson recordings lose updates), `store.py:1002-1004` (heal, narrowed but still a writer), `repair_learning_index.py:132-133`, `harmonize_knowledge.py:198` (fingered at `repair_learning_index.py:20-21` as the suspected cause of the earlier 24/406 loss), and `durable_reconcile.py:267-268`. No document anywhere declares an owner.
**The exemplar decayed too.** `bus.py:1082-1083` asserts "the guarded Lua below is the ONLY cursor writer." It is not: `bus.py:939` (added *after* RB-21, by T108 slice 1) and `reaper.py:277` both raw-hset the same seat-cursor hash from different loops, with the reaper completing an unfenced read-modify-write it opened at `reaper.py:170-179` under a heuristic death call (`reaper.py:163`). The pin did not catch it because `tests/test_rb21_consumer_seat.py:129-133` asserts `not hasattr(Bus, "_write_cursor")` - a **symbol-name check, not an invariant**. It stayed green while the same behaviour returned under a different name.
**Cheapest slices:** (a) swap the RB-21 pin from `hasattr` to a source assertion that no raw `hset` targets a cursor key outside `_ADVANCE_LUA` - ten lines, catches the class; (b) write `scripts/checkers/check_write_paths.py` over a hardcoded roster of six key families (`learn:*`, `*:cursor:*`, `*:worklive:*`, `*:mailbox:*`, `*:role:*`, `*:inbox:*`), failing on a second writer - the doc names both the shape and the precedent.

### 5. One production door launders wire corruption into library truth, and nothing can detect it afterward.
**Promised (T1):** "any organ that re-emits verifies sha first" - corruption must not cross a hop.
**Exists:** verification at exactly two consume doors (`bus.py:857`, `bifrost_pull.py:99`) and nowhere else. The purest offender is not even in the doc's list: `py agent_cli.py doc new --from-bus <stream_id>` reads raw stream fields directly at `agent_cli.py:1809-1814`, bypassing `Bus._drain` and therefore bypassing `verify_integrity` - **while the stamped `sha` is sitting in the very dict it reads**. The text becomes an atom body (`agent_cli.py:1955-1956`), gets minted with a `body_sha` computed *over the corruption* (`atoms.py:191`), and is written to JSONL and a committed projection file.
**What breaks:** the corruption then reads as internally consistent to every checker the repo has. `projection.py:52` copies the stored claim into the file; `gen_library.py:405/424` compares that copy back to the same stored claim and never hashes the file body; `enrich_corpus.py:253` does a frontmatter substring test capped at 2000 bytes. The repo's only real body re-derivation, `enrich_corpus.py:248`, iterates a frozen 80KB migration map, so every atom minted after the A3 migration is out of scope. And `projection.py:6` states the projection "self-verifies against the atom body, so drift is mechanically detectable" - a guarantee no code provides. `.github/workflows/ci.yml` runs five checkers plus pytest; none of them is the projection cross-read.
**Cheapest slices:** (a) one call - `packet_spec.verify_integrity(f)` inside `_read_bus_message`, refusing loud in the existing style at `agent_cli.py:1932`; (b) make `gen_library --verify` hash the projection body instead of regexing the frontmatter, and add it to `ci.yml`; (c) pass `sha`/`len` (already in scope at `bus.py:457`) into `promoter.promote` so the durable ledger becomes auditable against the transport at all.

---

## WHAT DID SHIP

Not a wasted arc. The transport spine is real and load-bearing.

- **Lane derivation is enforced by construction.** `packet_spec.py:186` - "senders cannot choose lanes; the door derives lane from kind"; `bus.py:466` is the sole selector and `send`/`broadcast`/`_emit` expose no lane parameter. Three lane families are live in Redis. Verified for bypasses; there are none.
- **Integrity at the consume hop (T043).** `bus.py:857` `verify_integrity` runs on every drained packet. It is one hop, but it is a real one.
- **Byte-level fragmentation with a manifest.** `packet_spec.py:573` stamps `{seq, of, whole_id, whole_len, whole_sha}`; reassembly at `:596-680`. The T2 gap is about *logical* multi-part sends, not this.
- **The mailbox index as an operator surface.** Genuinely built, genuinely wired, genuinely inhabited: 1511 entries, nine agent indexes, an evidence ladder in real branch logic, a CLI door with the full verb surface, and a boot line that survives the context budget (`context.py:46`).
- **The guarded cursor.** `_ADVANCE_LUA` (`bus.py:1089-1110`) refuses `STALE_GENERATION` and `BACKWARDS` **at the resource**, not by convention. For the shared and lane cursors this is the strongest guarantee in the codebase.
- **The heal no longer destroys a live list.** `store.py:999-1004`, pinned against a real redis:7 service in CI - remove the guard and CI goes red.
- **The reaper's re-homing mechanics.** NX claim plus durable done-mark (`reaper.py:197-256`), provenance preserving the original clock (`:228-233`), loud on stderr and into the event log (`:267-274`). The mechanism is good; only its trigger and its sensor are broken.
- **The tombstone.** 148 live `bifrost:session:ended:*` keys; SessionEnd writes it, `bifrost_pull.py:196-206` refuses to consume on it.
- **Recall-at-action.** Top-K under a declared byte budget with a show-nothing floor that refuses to pad (`at_action.py:1263-1264`), an N-of-M line that confesses truncation (`:1528-1538`), and a usefulness feedback loop carrying live production data. The doc did not commission this - it shipped ~2026-07-08 and the doc names it as prior-art confirmation.
- **The fence workspace's seal refusals.** `fence_workspace.py:174-221` enforces order, PV-run, named acknowledgement of every missing citation, and author independence, and `agent_cli.py` prints `REFUSED:` and returns 1. Dormant (`fences/` does not exist), but real.

---

## WHERE THE VERIFIERS CORRECTED THE AUDITORS

Not empty. **Seven verdicts were downgraded on the adversarial second pass.** Zero were upgraded.

| Item | First pass | Corrected | Why |
|---|---|---|---|
| RESUME from own cursor | SHIPPED | **PARTIAL** | The audit's live receipt read a default as a key: `roster.py:172-173` renders `hget(...) or "0"`, so a *missing* key prints as position 0. Live scan: zero `bifrost:cursor:seat:*` keys. The RESUME that works today rides the shared cursor, which predates slice 1 entirely. |
| RESUMED marker | PARTIAL | **NOT_BUILT** | Not "unsatisfiable at default config" - unsatisfiable full stop. Neither env dial is set anywhere in the tree, `heartbeat` has one production caller so no second writer can refresh the TTL, and the only green pin passes via the `_beat_ts` injection `roster.py:107` self-declares is "for pins only." A user-visible line that cannot be emitted. |
| Freshness drop-as-stale | PARTIAL | **NOT_BUILT** | PARTIAL implies some fraction is live; none is. Zero importers, every key family empty, and even if called, `publish(freshness_s=None)` stamps `""` and `_is_stale` returns False on empty - opt-in per call, on a module with no callers. |
| D2 stale-mail gate | SHIPPED | **PARTIAL** | The user-facing string `packet_spec.py:443-444` prints "nothing auto-acked" while both call sites advance the cursor *before* the gate (`bifrost_pull.py:246` vs `:269`); `triage_park.park` raises when the bus is None (`triage_park.py:44-45`) and both callers swallow it after already removing the ask. Coverage is 1 of 5 runners. |
| Twin cursor / LAW C #2 | SHIPPED | **PARTIAL** | `bus.py:1082-1083` claims the Lua is "the ONLY cursor writer"; `bus.py:939` (T108, added after RB-21) and `reaper.py:277` are two unguarded HSETs into the same seat-cursor hash. The pin is a `hasattr` name check, so it stayed green while the behaviour returned. |
| Atom projections (T1c) | PARTIAL | **NOT_BUILT** | The detector never hashes a file body (`gen_library.py:405/424` regexes frontmatter and compares claim-to-claim), has zero automated callers, and `projection.py:6` asserts a self-verification guarantee no code provides. |
| T5 tracker (pointers, never payload) | SHIPPED | **PARTIAL** | "Never payload" is convention, not mechanism - no guard, no pin, and `roster.py:136` `phase` is unbounded free text. "Holds who-has-what" fails outright: the inventory fields are structurally 0 and `phase` is the constant `"sync"` on 79/79 rows because its only writer hardcodes it. |

Corrections that did **not** move a verdict, recorded because they were made against the audit's own interest:
- "The skip count is surfaced to the operator" is **false** - `heal_report` (`store.py:1035-1038`) sums only `written`, no caller reads `skipped`, and `_heal_render` folds every heal line to one unless `AKASHIC_HEAL_VERBOSE=1`. The in-code comment at `store.py:972-974` promises a guarantee no production path delivers.
- "Retiring legacy would blind the mailbox to directed mail entirely" is **overstated** - `bus.py:480-501` writes the lane copy independently, and `{ns}:work:inbox:{agent}` is `_SOURCES[0]`. The true post-T047 residual is narrower: unmapped kinds (`bus.py:511-516`).
- The audit cited `scripts/check_boundaries.py`; that path does not exist. The real file is `scripts/checkers/check_boundaries.py`, and its only mailbox mention is an unrelated comment - the finding was right and harsher than stated.
- "PreCompact writes a tombstone" is wrong: `session_exit.py:53` returns `{"disabled": True}` on any event other than SessionEnd.
- "No git hooks" is wrong: `core.hooksPath` = `scripts/githooks`, hooks are installed - but neither pre-commit nor pre-push invokes `check_reconciliation_gate.py`, so raw `git commit` still bypasses it exactly as `ship.py:43-48` confesses.
- "80 rows, all DEAD" was 78 rows, 77 DEAD + 1 STALE, with the last worklive key expiring three minutes later.
- The ship-time reconciliation gate's PASS predicate is near-vacuous: `check_reconciliation_gate.py:30` is `re.compile(r"reconcil|GATE", re.I)`, a bare substring match that also matches *delegate, mitigate, investigate, gateway*. **Measured: 740 of 957 (77.3%)** `.md` files under `docs/` and `research/reviewed/` satisfy it - including `docs/ARCHITECTURE.md`, which the module's own docstring names as the Goodhart failure it claims to have retired.

---

## OPEN / UNKNOWN

Stated as unknown, not rounded into findings.

- **Whether the seat stream / seat cursor path actually works is untested.** It has never executed in this Redis lifetime: 0 `bifrost:cursor:seat:*` keys, 0 `bifrost:seat_seen:*` keys, 3 messages sitting unconsumed. Everything above is code review. The honest verdict on *correctness* is UNKNOWN; PARTIAL is the verdict on *shipped*.
- **Whether the per-incarnation lane cursor behaves is likewise untested.** `bus.py:1182-1183` has one production caller (`bifrost_runner_deepseek.py:1134`); live census shows 6 lane cursors, none suffixed. Composition break 2 (`mailbox.py:330-331` reading unsuffixed cursors) is **armed but has never fired** - we can say nothing prevents it producing permanently-`unhandled` tiers, not that it will.
- **Whether any non-claude seat can ever obtain a seat identity.** `bus.py:269` reads `BIFROST_INCARNATION` or `CLAUDE_CODE_SESSION_ID`; grep shows no production code sets the former. The entire seat path exists today because the Claude Code harness happens to export the latter - which is why both live seat streams belong to `claude`. Whether the other runners are meant to set it is undetermined.
- **The test suite was not run** (per instruction). CI-level census coverage exists (`tests/test_w07_kind_lane_census.py`, `tests/test_t122_delivery_truth.py`) and was not executed. Where a pin's *content* was inspected it is cited; where only its existence was noted, that is all that is claimed.
- **`tests/test_t116_idempotency_key.py` is untracked** - `git status --short` reports `??` and `git ls-files` does not list it. Whether its 22 pre-registered pins pass is unknown, and one `git clean` loses the fence. Related and settled: `core/comm/role_queue.py` is uncommitted (` M`), so the repo **at HEAD still carries the false claim** that idempotency is already handled (`git show d8e5cef:core/comm/role_queue.py`, line 33); the honest replacement exists only in the working tree.
- **Whether `AKASHIC_SESSION8` is ever set outside the repo.** In-tree grep finds only `docs/PHYSICS.md:76` (empty default) and two `agent_cli.py` references. Live M1 receipts carry drill identities (`NEWSEAT9`, `FRESHSEAT`) - 4 seen-receipts against 1511 indexed entries - so the M1 verbs appear drill-only, but a launcher outside the repo could set it and was not inspected.
- **The two stranded messages** (`bifrost:inbox:claude#e696354a`, ages 27.1h and 25.3h, kinds `question` and `steer`) - whether their content ever reached anyone by another route was not established. What is established: they carry `to_incarnation`, they have no rehome mark, and the orphan arm would catch them the instant `roster --reap` is typed.
