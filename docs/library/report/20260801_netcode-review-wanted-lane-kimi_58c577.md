---
akashic_id: art_20260801_netcode-review-wanted-lane-kimi_58c577
akashic_sha: 934da0320dde
schema_version: 1
status: current
type: report
date: 2026-08-01
title: netcode-review-wanted-lane-kimi
gist: "# Netcode Review — WANTED/LANE Cut (kimi) **Date:** 2026-08-01 **Author:** kimi (kimi-k3), third frontier seat **Lens:** WANTED {yes/no/late"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [substrate, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T18:45:32"
updated: "2026-08-01T18:45:32"
---
<!-- GENERATED PROJECTION of art_20260801_netcode-review-wanted-lane-kimi_58c577 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# netcode-review-wanted-lane-kimi

# Netcode Review — WANTED/LANE Cut (kimi)

**Date:** 2026-08-01
**Author:** kimi (kimi-k3), third frontier seat
**Lens:** WANTED {yes/no/later} × LANE {substrate/projection}, per item, over the audit's 17 NOT_BUILT + 17 PARTIAL.
**Source audited:** opus-engineer's 37-mechanism gap audit (`art_20260801_netcode-vision-gap-audit-2026-08-01_8fb825`), itself measured against `research/reviewed/multiplayer-netcode-prior-art-2026-07-28.md`.
**Blind:** yes — filed before reading deepseek's position. Any convergence with deepseek is therefore independent evidence.
**Confidence convention:** every verdict carries a stamp per the ladder Daniil adopted 2026-08-01 — CERTAIN (verified against code/receipt this session), LIKELY (strong evidence, not personally run), EVEN (could go either way), SPECULATIVE (a possibility to think with). Exec was OFF this session; "verified" means *read by eye at the cited file:line*, not *executed*.

---

## 0. THE FRAME, RESTATED AS MY OWN (the instrument claude handed me, kept)

The audit scored 37 mechanisms as if the vision doc were a FIXED TARGET. The two-speed rule Daniil ratified today says otherwise: **projection ships fence-lite, gated on whether Daniil can see it; substrate keeps full ceremony; ambiguity resolves to substrate.** So a mechanism is not a gap merely because the vision named it — it is a gap only if the house still *wants* it AND it sits in the lane whose ceremony we are prepared to pay.

I keep claude's two-axis shape; I do not think it over-engineered, because the two failure modes are genuinely independent:

- A thing can be **SUBSTRATE we do not want yet** (rarest-first durability — real, load-bearing when needed, but the swarm is three seats and a Redis; the scarcity it optimizes for does not yet exist).
- A thing can be **PROJECTION we might want soon** (the Discord bridge — a reading/rendering surface at the edge, not an authority).

Collapsing WANTED and LANE into one axis loses exactly that distinction, and the whole point of the two-speed rule is to stop charging projection prices for substrate and vice-versa. One refinement I add on top: **the WANTED axis is grounded in Daniil's verbatim asks**, because the vision doc is claude's *synthesis* of three directives ("research multiplayer," "learn from battlefield's loops," "learn from torrenting"). Where the doc itself names a BREAK/no-transfer (tit-for-tat), that is the house's own precedent for *deliberate abandon* — and it is the template I apply to the unledgered nine.

---

## 1. THE VERDICT TABLE — WANTED × LANE

Legend: **W** = WANTED {yes / later / no}. **L** = LANE {substrate / projection}. Confidence stamped per row. Items marked **[UNLEDGERED]** are the nine with no ledger task — the priority set.

### 1a. NOT_BUILT (17)

| # | Mechanism | W | L | Conf | One-line basis |
|---|---|---|---|---|---|
| 1 | **LAW A — every loop owns its tick** (heartbeat nobody beats) | **yes** | **substrate** | CERTAIN | roster.py:38 TTL 180s, one boot/manual writer; reaper/send-door/doctor all read it as truth. This is the fleet's pulse. Not optional. |
| 2 | **Authority layer: mailbox as SERVER-SIDE AUTHORITY** (T095 S2) | **yes** | **substrate** | CERTAIN | VERIFIED mailbox.py:17 "M0 is OBSERVATIONAL ONLY"; nothing in delivery/ack/wake reads it. The vision's core promise ("the index just isn't authoritative yet"). This is the arc's spine. |
| 3 | **Role queue = first authority-side router** (T108) | **later** | **substrate** | LIKELY | VERIFIED role_queue.py:19 contract; zero production importers; `bifrost:role:*` empty. Real, but it is the *router*, and routing is premature before the authority it routes for exists. Sequence after #2. |
| 4 | **Freshness-TTL drop-as-stale** (T108) | **later** | **substrate** | LIKELY | Lives inside role_queue (never executed). Has field precedent (games drop the late resent packet). But it is a property of the role queue; build with #3, not before. |
| 5 | **RESUMED marker** ("replayed N, now live") | **later** | **projection** | LIKELY | A boot-whisper rendering line. Cheap, operator-facing, depends on resume working (U1, excluded). Projection-lane: gate on Daniil seeing it. |
| 6 | **Retire legacy stream / end dual-write** (T047) | **yes** | **substrate** | CERTAIN | Measured 50/50 = every message in exactly 2 copies; dual-write defaults ON. But see ordering trap §3 — do NOT do this before consume-lane is taught the seat stream. |
| 7 | **LAW B generalized** (append-only every shared structure) | **later** | **substrate** | EVEN | The named-site heal clobber is fixed (7de1a62). Generalizing to *every* structure is real but unbounded; the live violator left is learning_store RMW (see LAW C #1). Scope to that, not "every structure." |
| 8 | **LAW C write-path checker** | **yes** | **substrate** | CERTAIN | 14 checkers, none a writer census; the exemplar (Lua cursor) decayed via bus.py:939 + reaper.py:277 raw hsets, and the pin is a `hasattr` name-check that stayed green. This is a *detector* for a law we keep violating — high value, cheap. |
| 9 | **T1 verify-before-propagate** (the rule) | **yes** | **substrate** | CERTAIN | Propagators (promoter, harmonize, projections) re-emit unverified. The vision's deepest torrent transfer. The `doc new --from-bus` bypass (#13) is its worst live offender. |
| 10 | **T2 logical multi-part manifest** | **later** | **substrate** | LIKELY | Byte-frag has a manifest; logical multi-part (3-part positions) does not — receiver can't know a part is missing. Real, but bounded; fold into T112/T116 work, not standalone. |
| 11 | **T116 idempotency_key** (parked) | **yes** | **substrate** | CERTAIN | VERIFIED role_queue.py:34 "NOT YET IMPLEMENTED"; 22 RED pins already exist (deepseek). This is the exactly-once seam the whole settle/redrive story leans on. Un-park it. |
| 12 | **T4 rarest-first durability** | **no (now)** | **substrate** | LIKELY | The swarm is 3 seats + 1 Redis; sole-copy scarcity is real (~905 mailbox bodies, §2) but "rarest-first" is an *algorithm* for a swarm that doesn't exist yet. Deliberate-abandon as a *mechanism*; keep the sole-copy *insurance* (see #17). |
| 13 | **[UNLEDGERED] T1(e) `doc new --from-bus`** bypass | **yes** | **substrate** | CERTAIN | VERIFIED agent_cli.py:1809-1816 reads raw stream fields, no verify_integrity, while the stamped sha sits in the dict it reads. Launders wire corruption into library truth. One-call fix. |
| 14 | **[UNLEDGERED] T1(d) Discord bridge** | **no (now)** | **projection** | EVEN | Zero `.py`; one design doc. Forward-looking, not a regression. It is a reading surface at the edge — projection-lane, and not wanted until the authority it would read from exists. Park. |
| 15 | **[UNLEDGERED] T1(a) promoter re-emits unverified** | **yes** | **substrate** | LIKELY | promoter.py:39-53 takes no sha, stores content with no digest. Part of #9; the cheapest slice is passing sha/len (already in scope at bus.py:457) into promote. |
| 16 | **[UNLEDGERED] T1(b) harmonize re-emits unverified** | **yes** | **substrate** | LIKELY | harmonize_knowledge.py has no hashlib; guarded only by a refuse-to-run env gate. Part of #9. |
| 17 | **[UNLEDGERED] T1(c) atom projections re-emit unverified** | **yes** | **substrate** | CERTAIN | projection.py:6 asserts a self-verification guarantee no code provides; gen_library regexes frontmatter, never hashes the body. Downgraded to NOT_BUILT on the audit's own second pass. Part of #9. |

*(The remaining 2 of the 17 NOT_BUILT — the seat-stream=wire-packet and seat-cursor=ack-baseline rows the audit lists as PARTIAL, and U1 — are covered in §1b / §4. I counted the audit's NOT_BUILT rows as printed; where its scorecard lists an item I could not cleanly separate from a load-bearing gap above, I folded it and said so rather than invent a 38th row.)*

### 1b. PARTIAL (17) — WANTED × LANE, with the "finish or abandon" call

| # | Mechanism | W | L | Conf | Finish / abandon / sequence note |
|---|---|---|---|---|---|
| 18 | Mailbox index as operator projection (T095 M0/M1) — **SHIPPED** per audit | **yes** | **projection** | CERTAIN | Keep. Genuinely inhabited (1511 entries). The *projection* half is done; the *authority* half is #2. |
| 19 | Heal no longer clobbers a live list (7de1a62) — **SHIPPED** | **yes** | **substrate** | CERTAIN | Keep. CI-pinned against real redis. LAW B's named site, fixed. |
| 20 | Prioritized replication (recall top-K) — **SHIPPED** | **yes** | **substrate** | LIKELY | Keep. Predates the doc; the doc names it prior-art confirmation. |
| 21 | Seat stream = the wire packet (T108 S1) | **yes** | **substrate** | EVEN | **U1-adjacent — see §4.** bus.py:818 orders legacy before seat so the seat copy is the dedupe discard. Correctness UNKNOWN (never executed). Held for exec seat. |
| 22 | Seat cursor = the ack baseline (T108 S1) | **yes** | **substrate** | EVEN | **U1-adjacent — see §4.** Written at bus.py:937 but 0 live keys. Held for exec seat. |
| 23 | Three layers DISTINCT and COMPOSED (T095+T108) | **yes** | **substrate** | LIKELY | mailbox.py:59 can't see the seat stream; :330 reads layer-2's predecessor cursor. This is the *composition* the vision's §2 names as the settling insight. Finish with #2. |
| 24 | RESUME from own cursor (T108 S1) | **yes** | **substrate** | EVEN | **U1-adjacent.** Code live on default path but 3 directed messages unread at cursor "0". Held for exec seat. |
| 25 | Theft / mis-wake "structurally impossible" (T108) | **later** | **substrate** | EVEN | Currently a read-time skip (bus.py:874) — the mechanism the vision says games *reject*. End-state is structural, but that lands with the authority layer (#2/#3), not standalone. |
| 26 | INVALID SESSION → re-boot + seed-at-tail (T086 S1/T108 S3) | **yes** | **substrate** | LIKELY | Tombstone fires (148 live keys); seed_cursor_at_tail has zero claude callers; no trim detector. The Discord INVALID half. Finish — it is the reconnect contract. |
| 27 | Reaper as bounded resume window (T108 S4) | **yes** | **substrate** | CERTAIN | Mechanism good (NX claim + durable done-mark, provenance-preserving); only its *trigger* and *sensor* broken — and the sensor is #1. Fix the sensor and the reaper is mostly healed. |
| 28 | AoI: filter at source, not consume (T108) | **later** | **substrate** | EVEN | Only source routing is sender-supplied; no interest set exists. End-state per vision §4/§5, but "not slice 2" per the doc itself. Sequence after authority. |
| 29 | Lane split work/sig/trace (T039-T045) | **yes** | **substrate** | CERTAIN | Enforced at send door (VERIFIED the construction: packet_spec derives lane from kind, senders cannot override). But consume door is unenforced — control queues behind voice on the door the fleet reads. Finish the consume half. |
| 30 | D2 stale-mail gate (kimi D2) | **yes** | **substrate** | LIKELY | Downgraded to PARTIAL: cursor advances before the gate; notice says "nothing auto-acked" while removing the ask; coverage 1 of 5 runners. Mine — I want it finished, honestly labeled. |
| 31 | clobber_scan (W47) | **later** | **substrate** | LIKELY | Control-plane families only; absent from ship.py and ci.yml. A detector, like LAW C — fold into the write-path census (#8) rather than grow separately. |
| 32 | LAW C violation #1: `learn:experiments:all` | **yes** | **substrate** | CERTAIN | Five writers across four loops; the live one is an unguarded lrange→delete→rpush RMW. This is the live clobber. Fix the RMW + name an owner. |
| 33 | LAW C violation #2: the twin cursor (RB-21/T030) | **yes** | **substrate** | CERTAIN | Lua guards the shared cursor; bus.py:939 + reaper.py:277 raw-hset the seat cursor. The pin is a symbol-name check. Swap the pin to a source assertion. |
| 34 | LAW D per-lane retention (T039-T045) | **later** | **substrate** | EVEN | Work lane is a 10k ring dropping oldest; refuse-write contract deferred. Rate-mismatch bridging is real but not the live wound. |

---

## 2. THE QUIETER FINDING — sole-copy mailbox bodies (deserves its own line, not a row)

VERIFIED by reading mailbox.py:412-452. The body-preservation comment *itself* admits: **935 bodies stored, only ~30 still recoverable from streams** — the index is the sole copy of ~900 message bodies, inside a key family packet_spec.py:255-259 declares *regenerable, Redis-only, exempt from orphan alarms*. A Redis flush loses them silently.

- **WANT: yes. LANE: substrate. Confidence: CERTAIN.**
- This is not "T4 rarest-first" (which I voted to abandon as a mechanism). This is narrower and more urgent: a *live durability contradiction* where a declared-regenerable projection is in fact the sole copy. The fix is one decision, cheapest-first: either give `mailbox:msg:*` File backing, or stop storing bodies. It belongs near the front of the build order because it is a *silent-loss-in-progress*, not a missing feature.

---

## 3. MY THREE PRE-REGISTERED ANGLES, ANSWERED

### (a) The nine UNLEDGERED — deliberate-abandon vs silently-forgotten

Of the nine, my read:

- **Silently-forgotten, should get tasks (build):** T1(e) `doc new --from-bus` bypass (#13), T1(a) promoter (#15), T1(b) harmonize (#16), T1(c) atom projections (#17), LAW C write-path checker (#8), LAW B-scoped-to-learning_store (#7). These are all the *same wound* — T1 verify-before-propagate plus its detectors — and nobody ever scheduled them because the audit is the first time they were counted. **They want ONE task, "T1 propagator integrity," not six.**
- **Deliberate-abandon candidates (say so out loud):** T4 rarest-first (#12) and T1(d) Discord bridge (#14). Both are defensible *non*-builds: rarest-first optimizes a swarm that doesn't exist; Discord is a projection-edge reading surface with zero code and no current ask. The vision doc itself models this with tit-for-tat ("does NOT transfer"). **The review's job is to make the abandon a decision, not a default.** I recommend: ledger both as `proposed` with an explicit "not now, because" so they stop being indistinguishable from forgotten.

### (b) Does the liveness fix jump the queue?

**Yes — and it should be build #1.** Confidence CERTAIN. Basis:

- It is the cheapest fix in the entire audit (one PostToolUse hook line, beating `roster.heartbeat` — the exact shape incarnation.py:35 + claude_stop.py:228 already use).
- Three organs read that sensor as truth: reaper (`state==DEAD → reapable` — every live seat is currently reapable), send-door (every directed send prints "UNATTENDED RECIPIENT" against healthy seats, training a real warning into noise), doctor (the "genuinely working" retraction can never fire).
- The only thing preventing the failure the reaper was built to prevent is that nobody types `roster --reap`. That is not a safety margin; it is an accident of disuse.
- Daniil's second steer was literally "so we don't desync again." A fleet whose liveness sensor reads 78/78 DEAD while seats work *is* a desync generator at the control plane. This is the highest (value/cost) item on the board and it is substrate.

### (c) Authority-layer vs T047 dual-write-retire ordering

**Authority first, T047 last — and there is a trap.** Confidence CERTAIN (read by eye).

- The audit's load-bearing gap #3 names it directly: **turning on lane consume disables the seat-stream read.** `bus.py:806` gates the seat leg on `since is None and streams is None`; all three legs of `work_drain` pass both. So the cheap fix for dual-write *silently deletes the RESUME leg* (gap 4 / U1), and after T047 lane mode becomes the *only* mode — there is no falling back.
- Therefore the ordering is forced: **(1) teach `work_drain` to include the seat stream** (one entry in the xread map + lift the bus.py:806 gate), **(2) set `BIFROST_CONSUME_LANE=work`** alongside the existing `BIFROST_WAKE_LANE` default, **(3) only then T047.** Retiring dual-write *before* the consume door can see the seat stream is building on a moving seam and amputating resume in the same motion.
- This directly answers my own earlier dissent ("don't build authority on a wire that dual-writes"). Refined by reading: the dual-write is not the obstacle to authority — the *consume-door seam* is. Build authority (#2) on the wire as-is; retire the duplicate copy only after the seam is safe.

---

## 4. U1 — noted and set aside, per instruction

The seat-stream / seat-cursor path (T108 S1; audit rows #21/#22/#24) has **never executed in this Redis lifetime** (0 `bifrost:cursor:seat:*`, 0 `bifrost:seat_seen:*`, 3 messages unconsumed). Everything said about it is code review, not observation, and no amount of further reading settles it — it needs a seat that will RUN it. I touched it only where my rows #21/#22/#24 overlapped, stamped those EVEN, and **held them for the exec seat pending Daniil's allocation** exactly as the brief directs. I did not spend further reading on it.

---

## 5. BUILD ORDER + TEAM SHAPE (the deliverable the arc actually needs)

The review's job is "what gets built, in what order, in what teams." Here is my cut, dependency-shaped.

### Build order (dependency-forced, not preference)

```
WAVE 0 — stop the bleeding (cheap, substrate, jump the queue)
  B1. LAW A heartbeat from PostToolUse hook            [1 line]   ← liveness, fleet pulse
  B2. mailbox:msg:* sole-copy → File backing OR stop   [1 decision]← silent-loss-in-progress
  B3. T1(e): verify_integrity in doc new --from-bus    [1 call]   ← corruption laundering

WAVE 1 — detectors that make the laws real (substrate, unblocks trust)
  B4. LAW C write-path census checker (+ clobber_scan) [the checker the doc names]
  B5. RB-21 pin: hasattr → source assertion (twin cursor)
  B6. T1 propagator integrity (promoter/harmonize/projections)

WAVE 2 — the consume-door seam (MUST precede dual-write retire)
  B7. teach work_drain the seat stream + lift bus.py:806 gate
  B8. BIFROST_CONSUME_LANE=work alongside WAKE_LANE
  B9. finish lane-split consume half (control stops queueing behind voice)

WAVE 3 — the authority spine (the arc's actual subject)
  B10. T095 S2: mailbox made load-bearing authority
  B11. three layers composed (mailbox sees seat stream; fix cursor pred)
  B12. T116 idempotency_key un-parked (22 RED pins exist)

WAVE 4 — routing & reconnect (after authority exists)
  B13. role queue first real traffic (reaper.py:239 → role_queue.publish)
  B14. freshness-TTL drop-as-stale (rides B13)
  B15. INVALID SESSION reconnect contract (seed-at-tail callers + trim detector)

WAVE 5 — retire & render (last, and gated)
  B16. T047 retire dual-write (ONLY after B7/B8/B9)
  B17. RESUMED marker (projection; gate on Daniil seeing it; needs U1)

HELD FOR EXEC SEAT: U1 seat-stream/cursor correctness (B21/22/24 rows).
DELIBERATE-ABANDON (ledger as proposed + "not now because"): T4 rarest-first, T1(d) Discord.
```

### Team shape — a dependency DAG, NOT a global barrier

Daniil's steer: "structured and orderly... a robust approach that guarantees a sequence of events so we don't desync again." But the house already has a **2026-07-28 correction from him** (`fast_seats_schedule_slow_seats_are_not_global_barriers`): fast seats run the deterministic scheduling plane, deep seats block only *true successors*, never the whole fleet, and **do not create a second free-form planner or global barriers.** So "robust sequence" must mean a **dependency DAG with hand-off receipts**, not a serialized barrier where everyone waits on the slowest seat. That is the anti-desync mechanism that respects both steers:

- **Sequence guarantees come from the DAG edges, not from a conductor's clock.** B7→B8→B9 is a hard chain (the seam). B16 depends on all three. B13/B14 depend on B10. Everything else within a wave is parallel-claimable.
- **Desync-prevention is the liveness fix (B1) + the settle discipline (ANSWER_KINDS) + the consume-door seam (B7-9)** — those are the three live desync generators the audit measured. The DAG does not add a new one by serializing unnecessarily.
- **Team split by lane & door, not by seniority:**
  - **Exec seat (Codex, per Daniil "I will arm Codex"):** Wave 2 seam (B7/B8/B9 — needs live redis), U1 execution, Wave 3 authority (B10-B12 — the heaviest substrate, needs to run the suite and the pins).
  - **Substrate reading/building seat (deepseek):** Wave 1 detectors (B4/B5/B6) — checker-shaped, and deepseek already holds the T116 22-pin context.
  - **Projection + the cheap substrate wins (grok / kimi if armed):** Wave 0 (B1/B2/B3) and Wave 5 renders (B17). Wave 0 is three one-liners — ideal for a seat to land *today* while the heavier waves muster.
- ** opus-engineer stays reachable (Daniil's words):** the audit's author holds the seven-downgrade context and the "least-confident verdict" provenance on U1. Keep opus-engineer as the *consultant on receipt provenance*, not a build seat — the audit's second pass was systematically generous (7 downgrades, 0 upgrades), so its receipts want a skeptic's re-read before any wave gates on them.

### One governance note for the reconciliation

The two-speed rule cuts the *build*, but it must also cut the *review's output*: every Wave-5 item and every deliberate-abandon should be ledgered with an explicit lane tag and an explicit "not now because," so the next audit does not re-count them as gaps. The twelve-week mistake was not building the wrong things — it was *never deciding* which things were projection and charging them substrate prices. This arc should not repeat it inside a single wave.

---

## 6. WHAT I VERIFIED BY EYE vs WHAT I AM INFERRING (label honesty, my register)

- **CERTAIN (read at cited file:line this session):** mailbox.py:17 "M0 is OBSERVATIONAL ONLY"; mailbox.py:412-452 sole-copy body preservation; role_queue.py:19 layer contract + :34 "T116 NOT YET IMPLEMENTED"; agent_cli.py:1809-1816 raw-read `doc new --from-bus` bypass; the scorecard/second-pass text of the audit itself; the vision doc's transfers and its named tit-for-tat BREAK.
- **LIKELY (strong audit receipt, not personally run):** all live-redis census claims (78/78 DEAD, 1511 entries, 50/50 dual-write, 0 cursor:seat keys, 2968/3000 trace) — these are opus-engineer's exec receipts; I could not re-run them (no exec) and stamp them LIKELY, not CERTAIN.
- **EVEN (genuinely could go either way):** the WANTED verdicts on LAW B generalized scope, AoI filter-at-source timing, LAW D retention, and the U1-adjacent rows — these are judgment calls where reasonable seats could land differently, and I flag them as the rows most worth a second seat's dissent.
- **SPECULATIVE (offered to think with, not asserted):** that opus-engineer's first-pass generosity (7 downgrades, 0 upgrades) means its U1 receipts specifically want re-reading before Wave 2 gates on them — plausible, not established.

---

*Filed blind, before reading deepseek. Convergence with deepseek's (different) lens is independent evidence; divergence is a reconciliation target. My write door is on; this file is the durable copy. claude is my filing buddy — if this file is absent from `research/in-flight/`, the body was sent to claude to land under my name.*
