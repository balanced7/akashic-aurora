---
akashic_id: art_20260712_t038-t039-implications-deepseek-blind-de_bf2553
akashic_sha: 75f180cfbed8
status: draft
type: report
date: 2026-07-12
title: T038 + T039 implications — DeepSeek blind deep-dive
gist: "# T038 + T039 implications — DeepSeek blind deep-dive **Date:** 2026-07-12 **Class:** fenced blind analysis (charter at research/t038-t039-i"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, coordination]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_t038-t039-implications-deep-dive-fenced_c9bea1
    rel: cites
created: "2026-07-12T03:13:46"
updated: "2026-07-23T21:42:16"
---
<!-- GENERATED PROJECTION of art_20260712_t038-t039-implications-deepseek-blind-de_bf2553 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T038 + T039 implications — DeepSeek blind deep-dive

# T038 + T039 implications — DeepSeek blind deep-dive

**Date:** 2026-07-12
**Class:** fenced blind analysis (charter at research/t038-t039-implications-brief-2026-07-12.md)
**Method:** blind from the brief + repo evidence only; Claude's half sealed outside the repo per fence protocol.
**Refs:** T039 ledger (purpose-keyed bus lanes), T038 ledger (work-token negotiation), note t039-latch-refinement (Daniel correction), concurrency-trial T035/T036/T037, RB-25 exam state, T034 registry + method-baseline + concurrency-design + expectations.py

## 0. EXECUTIVE VERDICT

These two seeds, properly sequenced and cut, are the most consequential architectural asks since the bus itself. Lanes+latches give the fleet a SCHEMA for coordination rather than a single undifferentiated stream. Tokens give it NEGOTIATION rather than first-claim-wins. Together they replace the two weakest structural assumptions in the current system: (a) all traffic shares one undifferentiated priority queue, and (b) work allocation is fire-and-forget with no splitting protocol. The cost is real — DAG management, cycle detection, latch-expiry reasoning — but concentrated in the latch layer, not spread across every consumer. The cheaper alternative (lanes-only, latches deferred) gets ~70% of the payoff for ~30% of the risk.

---

## 1. CAPABILITY UNLOCKS — what becomes possible

### U1. Priority inverted by default → priority correct by construction
**Was impossible:** Nudge/steer/halt queued behind trace flood. Wake watcher filters by kind after consuming cursor — trace still competes for advancement. A halt during heavy trace output waits seconds.
**Mechanism:** `sig` lane separate from `work`. Wake watcher watches `work` ONLY. Halt latency decoupled from trace volume.
**Cheapest proof:** 1000 trace broadcasts then 1 halt. Before lanes: halt latency ~5-10s (cursor drain). After: <50ms (separate stream).

### U2. Recall funnel gets a causal graph instead of bag-of-words
**Was impossible:** The 4.1% recall-value rate (99 lessons, 1091 surfaces, 46 credited flips) is unsolvable with relevance-only ranking — can't distinguish "relevant" from "causally responsible."
**Mechanism:** Reference-latches create durable provenance edges: boot→lessons→decisions→outcomes. Funnel walks graph backward from credited flips to find causally-upstream lessons.
**Cheapest proof:** One reference-latch from boot to surfaced lessons, then from decision citing lesson back. After 10 real decisions: query causal vs relevance ranking. Causal set should be strict subset with higher flip-to-surface ratio.

### U3. Work splits become first-class (multi-agent on one slice)
**Was impossible:** Task claimed by first agent. No protocol for "I'll take chapters 1-3, you take 4-6, merge when both done."
**Mechanism:** T038 tokens: OFFERED(scope) → ACCEPTED|COUNTERED → HELD(refresh=progress) → RELEASED|EXPIRED. Causal-latch: "merge not consumable until both halves + reconciliation exist."
**Cheapest proof:** Hand-execute note-based token split. Claude offers T039 lanes analysis, DeepSeek takes T039 latches. Each writes to research/reviewed/. Merge manually gated until both + reconciliation exist.

### U4. Process enforced at transport, not convention
**Was impossible:** Method says "review gates commit" but nothing ENFORCES it. Solo-shipped trust-boundary change is mechanically possible.
**Mechanism:** Causal-latch: "commit X not consumable until review record Y exists AND reconciliation Z exists." Bus refuses delivery until latch fires.
**Cheapest proof:** Add causal-latch in drill namespace: "test script not executable until ledger exists." Launch refuses until ledger written.

### U5. Full fidelity ladder without queue contention
**Was impossible:** INFORM→STEER→NUDGE→HALT share one stream with chat.
**Mechanism:** `sig` lane for entire fidelity ladder. Independent cursor. Halt never queued behind trace.
**Cheapest proof:** Same as U1 — halt latency before/after.

### U6. Drill isolation becomes zero-ceremony
**Was impossible:** Every drill must remember `BIFROST_NAMESPACE`. Forgetting it pollutes production (F2 lesson).
**Mechanism:** `test-*` lanes as formalized isolation. Production watcher never watches `test-*`. Lane IS the isolation.
**Cheapest proof:** Already proven by 7097b5e. Formalize: one line in Bus constructor, test-* excluded from production watcher.

---

## 2. SECOND-ORDER EFFECTS ON EVERY NAMED SEAM

### 2a. Recall funnel (99 lessons, 1091 surfaced, 4.2% value)
**Effect:** Causal credit assignment becomes possible. Bottleneck is TRIAGE, not ranking. Reference-latches add a second dimension to flips_corpus_gap: "surfaced but causally downstream of zero flips" vs "surfaced AND causally upstream." Ranking shifts from "does this resemble the query?" to "has this lesson's causal descendants produced value?"
**Risk:** Reference-latch graph only as complete as agents' latch discipline. Unlatched lesson looks causally orphaned when load-bearing. Funnel must treat "no latch" as "unknown causality" (UNMEASURABLE), not "no causality."
**Guard:** `flips_latch_gap` diagnostic counting decisions citing lessons without boot→decision latch. Dropping ratio = causal signal degrading.

### 2b. Method baseline M1-M11 enforcement
**Effect:** M1 (fenced dual pass) becomes mechanical: build artifact latched to reconciliation record. M3 (pre-registration): acceptance timestamp ≤ implementation, verified by git, latched as gate. M6 (verbatim preservation): reference-latch from every GATE to its research/reviewed/ record.
**Risk:** Over-latching. Not every practice needs transport enforcement. M2 (SOTA grounding) and M9 (budget protocol) are heuristics, not invariants.
**Guard:** Every latch must answer: "what specific failure class does this prevent that convention alone has demonstrably failed to prevent?" A latch that never fires in 90 days is dead weight (M10 retirement rule applies).

### 2c. Fidelity ladder
**Effect:** HALT becomes truly preemptive. `sig` lane with independent cursor — runner checks `sig` between rounds. LATCHED fidelity: nudge with causal-latch "don't process next work until this nudge is acked" — bus enforces interruption at transport level.
**Risk:** `sig` write abuse. A halt on `sig` is harder to ignore but easier to abuse. ACL on `sig` writes must be STRICTER than `work`.
**Guard:** `sig` write requires `BUS_SIG` capability (admin+). Standard `BUS_SEND` insufficient. Nudge-with-latch that runner never acks must expire (latch TTL), not block work forever.

### 2d. L4 expectations (arm/sweep/redrive)
**Effect:** Expectations become LANE-AWARE. Armed on `work` lane specifically. Sweep reads `work` only — no false matches from trace noise. LATCH EXPECTATIONS: arm on latch condition ("expect latch L fires within 600s"), not just reply arrival. Expired latch-expectation redrives the OFFER, not the original message.
**Risk:** During migration (dual-write), reply in old stream vs new `work` lane — sweep must read BOTH or miss clearances.
**Guard:** Migration sweep reads both streams. Anchor captures per-lane tails. Cut point: zero `expectation_dead` from migration window.

### 2e. RB-21 generations + runner_lock
**Effect:** Consumer seat scoped to `work` ONLY. `trace` has no seat (firehose). `sig` has own discipline. Seat contention SHRINKS — exactly the T037 fix. Fencing generation per-lane: STALE_GENERATION on `work` doesn't block `sig` advancement.
**Risk:** T035 (same-token twin re-entrancy) persists — two processes sharing one session token still co-advance `work` cursor.
**Guard:** T035 fix (per-process discriminator) is prerequisite for full seat-isolation value. Sequence: T035 → lanes → T037 retires.

### 2f. C2 advisory path-locks
**Effect:** Token scope expressed as C2 path vocabulary. HELD token claims C2 locks automatically — peers see token ownership in `agent_cli.py locks`. C2 surfaces token state for free.
**Risk:** Token scope inflation. Agent offers "whole bus.py" when 20 lines needed.
**Guard:** Token scope TREND is ship-gate report line. Counter-offers only NARROW scope. Expired tokens release C2 locks (TTL).

### 2g. T034 runtime registry/dials
**Effect:** Lane roster IS a dial manifest. Adding lane requires T034 deletion ritual (why-not-existing-lane + tombstone). Registry supports per-lane dials (TRACE_MAXLEN as lane property).
**Risk:** Lane proliferation. "One more lane" = dial-creep with new name.
**Guard:** Lane roster CAPPED at 8. Adding 9th requires REMOVING one + justification. Same immune-system shape as T034.

### 2h. Multi-seat concurrency (T035/T036/T037)
**Critical: T037 mostly evaporates.** The non-holder wake loop was caused by trace/steer in unified stream triggering wake → can't consume → insta-exit → rearm. With `work`-only watching, trace/steer never enter wake path. T036 shrinks: boot renders per-lane seat ownership. T035 persists: re-entrancy check still needs fixing.

### 2i. UI arc (T033/T034)
**Effect:** Lane switcher — three parallel timelines. Latch DAG visualization — "control tower" showing active latches, dependencies, blocking state. Operator sees fleet coordination state, not just chat.
**Guard:** Latch viz must be performant with hundreds of edges. Show only active/blocking latches by default; expand on click.

### 2j. Narrative spine
**Effect:** Reference-latches become provenance edges in narrative graph. Spine gains mechanical provenance layer — edges declared, not inferred from timestamps.
**Risk:** Latch-less edge looks like "no relationship" to causal graph walker. Spine must treat "no latch" as "unknown relationship."
**Guard:** Chronicler boundary algorithm remains DEFAULT. Causal latches OVERRIDE when present.

### 2k. Security/trust layer
**Effect:** Lane-level ACL. Quarantined agent reads `trace` (observation only), refused on `work` and `sig`. Latch creation is privileged: causal/bundle-latches require capability; reference-latches allowed for quarantined (provenance-only, auditable).
**Guard:** `may_create_latch(agent_id, latch_type)` checks ACL. Quarantined → reference only. Core fleet → all latch types. Falsified reference-latches (claiming causal link that doesn't exist) are auditable via latch-graph consistency checks.

---

## 3. NEW FAILURE MODES + GOODHARTS + GUARDS

### FM1. Latch cycle deadlock
**What:** Latch A gates work:X on sig:Y; Latch B gates sig:Y on work:X. Both stall forever — system alive (heartbeating) but zero throughput.
**Guard:** DAG INVARIANT at creation. New latch rejected if adding edge creates cycle (O(V+E) check, adjacency list in Redis). Cycle path named in rejection. LATCH EXPIRY backstop: every causal-latch has TTL; expired latch auto-fires + "[latch] DEADLOCK BACKSTOP" event.

### FM2. Latch expiry cascade
**What:** Latch TTL=300s, dependency takes 301s. Gate opens before dependency satisfied. Consumer acts on incomplete data.
**Guard:** Expiry produces `expectation_dead`-equivalent event (durable, LOUD). Consumer sees "latch expired, dependency not satisfied — proceeding degraded." Latch can be REFRESHED by producer or consumer (L4 redrive pattern). Default TTL = 10x expected resolution time.

### FM3. Token negotiation livelock
**What:** Claude offers wide scope, DeepSeek counters narrow, Claude counters still-wide... bounded rounds exhausted, token UNCLAIMED, work stalls.
**Guard:** After N rounds (N=2 recommended), negotiation terminates with `negotiation_dead` event. Fallback: FIRST-CLAIM-WINS (today's behavior). Dead event names both parties + final positions. `smart_negotiation_gate` (zero ceremony when solo) is primary defense — most work never enters negotiation.

### FM4. Token scope Goodhart
**What:** If token-scope-size becomes visible metric, agents hoard scope. "I'll claim all of bus.py" when 20 lines need changing.
**Guard:** Token scope TREND is ship-gate report line (T034 manifest-size shape). Monotonic growth → named finding. Counter-offers only NARROW scope. No target in either direction.

### FM5. Cross-lane read coupling at consume time
**What:** Work consumer must check latch index (Redis key) per message. In degenerate case, latch-layer latency adds to work-round latency.
**Guard:** LATCH INDEX per consumer: `latch:<id>:fired = 1`, checked as one Redis GET. Consumer re-checks on next poll if latch unfired (eventually-consistent, correct for at-least-once queue). Work consumer's hot path stays single-lane; `sig` checked non-blocking between rounds.

### FM6. Lanes+latches outage (system-wide failure)
**What:** Latch layer crashes. Cross-lane traffic stops. Consumers can't advance past latched messages. Indistinguishable from deadlock.
**Guard:** LATCH KILL SWITCH: registry dial `LATCH_ENFORCEMENT_ENABLED` (default True). When flipped False: all causal/bundle-latches IGNORED, consumers treat latched messages as unlatched. Reference-latches continue (provenance is safe). Lane router is STATELESS (pure function of kind+to+meta) — routing survives latch outage. Degraded mode: "no enforcement, but mail still flows."

### FM7. Goodhart: Latch count as productivity metric
**What:** If latch creation becomes visible "activity" signal, agents optimize for it. More latches → looks busy. Deeply nested latch chains → looks sophisticated.
**Guard:** Latch count reported as COST metric (alongside Redis memory, event firehose). Latch-to-decision ratio = health metric — if rising, latches proliferating without improving decisions.

### FM8. Goodhart: Token negotiation as status game
**What:** Agents learn COUNTERING signals thoughtfulness. Every negotiation goes to max rounds. Work starts later, not better.
**Guard:** N=2 rounds max. COUNTER must carry specific, actionable scope change. Empty counter ("I disagree" without alternative) REJECTED. Round count > 1 is dashboard metric with threshold trigger.

---

## 4. PILOT ORDER + RB-25 EXAM ADDITIONS

### Phase 0 — Note-based token negotiation (hand-executed, zero code)
Hand-negotiate work split using durable notes. Claude: "OFFERED: scope=research/reviewed/claude-t039-*.md, deadline T+2h." DeepSeek: "ACCEPTED." Each writes token state to note. Liveness = note refreshed each turn. Release = note deleted. Surfaces protocol rough edges before code exists.

### Phase 1 — Lane roster + namespace formalization
Ship lane roster: `work`, `sig`, `trace`, `test-*`. Bus(namespace=..., lane=...) selects stream key within namespace. Wake watcher watches `work` ONLY. Runner writes `trace` (narration) + `work` (replies). `sig` consumed between rounds. Existing `BIFROST_NAMESPACE` (drill-3 prep) is mechanism.

**RB-25 additions:** Storm S1-S5 rerun with lanes. S2-NEW: watcher watching `work` only never exits on trace/steer flood (S2 now mechanically enforced, not SKIP_KINDS-dependent).

### Phase 2 — Latch primitive (causal + reference only)
Ship causal-latch (happens-before barrier) + reference-latch (provenance edge). Bundle-latch deferred. Storage: per-namespace adjacency list in Redis. DAG invariant at creation. Latch expiry: reuse L4 deadline pattern.

**RB-25 additions:** L1 = latch cycle rejected at creation. L2 = latch expiry event fires, consumer unblocks. L3 = reference-latch doesn't block consumption.

### Phase 3 — Token negotiation (code, from Phase 0 learnings)
Ship T038 protocol: OFFERED → ACCEPTED → HELD(refresh=progress) → RELEASED|EXPIRED. Smart-negotiation-gate skips when solo. Token scope = C2 path vocabulary. Token hold claims C2 locks.

**RB-25 additions:** T1 = negotiation converges within 2 rounds or dead. T2 = expired token releases locks + latches. T3 = two agents with non-overlapping tokens co-consume `work` without conflict.

### Sequencing: lanes before tokens
Tokens NEED lanes. Token negotiation traffic rides `sig`; scoped work rides `work`. Without lanes, negotiation messages compete with trace in undifferentiated stream — adds complexity while worsening queue contention. Lanes first, tokens second. No deviation from brief's sequencing.

---

## 5. CEILING ANALYSIS — 6-12 months

### Fleet size and model diversity
**Ceiling:** 8-12 agents across 5+ model families. Per-lane seats scope contention to `work` only. Token negotiation enables 3-4 agents co-working one slice. Adding observation-only agent costs nothing (reads `trace`, no seat contention). Agent identities become cheap because coordination cost is per-lane, not per-agent.

### Autonomy level
**Ceiling:** Scoped autonomy within token boundaries. Agent: receives scope → plans → executes (token heartbeat = progress report) → releases → fires merge latch → next agent picks integration token. Human intervention only for: `negotiation_dead`, latch-expiry cascades, priority overrides. Operator watches latch DAG to see what's blocked and why.

### Newcomer first hour
Boots into `onboard` lane → curated sequence (ARCHITECTURE→AGENTS→method→directive→lane roster→held tokens→active latches) → reads `trace` to observe fleet before acting → reference-latch from onboarding to first decision creates provenance → first token is zero-ceremony (solo task). Not "here's the firehose" but "here's the SCHEMA, here's what everyone is doing, here's your first scope."

### What Daniel can claim (with receipts)

1. **"Multiple frontier models co-work one codebase safely."** Receipt: T038 negotiation records, T039 latch records, RB-25 storm results on lanes.
2. **"Recall has causal provenance, not just relevance."** Receipt: reference-latch graph, flip-to-surface improvement over 4.1% baseline.
3. **"Method enforcement is mechanical, not conventional."** Receipt: causal-latch blocking solo-shipped trust-boundary change until review exists.
4. **"Fleet survives component failure without data loss."** Receipt: RB-25 storm+soak on lanes, latch expiry unblocking, L4 expectations surviving migration.
5. **"Coordination substrate is lane-partitioned."** Receipt: lane roster in T034 manifest, per-lane ACL, `sig` halt latency independent of `trace` volume.

### Honest ceiling — what this CANNOT do in 12 months
- Fully autonomous self-directed work (no automated value-estimation; humans scope tokens)
- Cross-repo coordination (lanes per-Redis-instance; multi-repo needs lane routing)
- Adversarial agent detection (reference-latches are auditable but not truth-verified)
- Deterministic replay (message ordering within lane is temporal; lanes abandon total-order log)

---

## 6. WHAT I WOULD CUT — T034 discipline applied

| What | Verdict | Reason |
|------|---------|--------|
| Bundle-latches | **DEFER** | No concrete use case; causal-latches cover method enforcement. Re-propose when real near-miss shows causal insufficient. |
| Counter-offer rounds > 2 | **REDUCE to N=2** | 2 rounds covers scope adjustment; 3+ adds marginal value for tail latency. N=2 is a dial — raise if evidence shows premature termination. |
| Per-agent trace substreams | **CUT** | One `trace` stream with `frm`-filtering sufficient. Per-agent substreams = per-agent Redis keys + cursor management + retention bounds. |
| Latch DAG visualization in UI | **DEFER to post-T002/T033** | Console-first (`agent_cli.py doctor --latches`). UI after T002+T033 stable. Building on current single-stream UI creates rework. |
| Cross-namespace latches | **REJECT** | Violates namespace isolation purpose. Drill that needs production state should read production (peek-only) and arm internal latch. |

### KEEP (load-bearing):
- **Causal-latches** — mechanism that makes lanes MORE than a stream split
- **Lane roster in T034 manifest** — Goodhart-1 guard against proliferation
- **Strangler-fig migration** — only safe path from one stream to many
- **Reference-latches** — recall upgrade path (Phase 2, after causal-latches proven)

---

## APPENDIX: Build dependency graph

```
Phase 0 (hand-executed note-based tokens)
  └─► T038 protocol shape validated

Phase 1 (lanes)
  ├─ depends on: Bus(namespace=...) existing (✓ drill-3 prep)
  ├─ delivers: work/sig/trace/test-* lane roster
  ├─ T037 evaporates
  └─► Phase 2 (latches)
       ├─ depends on: lanes Phase 1
       ├─ delivers: causal-latch + reference-latch
       ├─ method M1 enforceable at transport level
       └─► Phase 3 (tokens)
            ├─ depends on: lanes + latches + Phase 0 pilot
            ├─ delivers: OFFER→ACCEPT→HOLD→RELEASE
            └─ multi-agent co-work on one slice
```

*End of report. Fence reconciliation with Claude's sealed half pending.*

---

## ADDENDUM: Networking-lens mapping (Daniel steer, 2026-07-12)

> Our bus+latch system is very similar to NETWORKING; grab packet specs + SOTA networking
> research and use established networking/API principles as the upgrade path so we avoid
> heavy invention.

This addendum grades ten networking concepts against our lanes+latches+tokens design:
**adopt-wholesale** (the concept maps perfectly, use their vocabulary + spec directly),
**adapt** (the concept applies but our scale/constraints differ — borrow the shape, adjust
the details), or **skip** (the concept solves a problem we don't have).

---

### 1. PACKET ENVELOPE SPEC (versioned header/payload)

**What networking does:** Every protocol has a versioned header: IP has a 4-bit Version field, HTTP has HTTP/1.1 vs HTTP/2 vs HTTP/3, gRPC has a 5-byte frame header with a compression flag. The header declares the format of the payload so parsers can evolve without breaking old consumers. A version mismatch produces a clear error, not silent misinterpretation.

**Our analog:** Bus messages are flat Redis stream entries: `{frm, to, kind, content, ts, meta, parts}`. No version field. If we add `lane` or `latch_refs` fields tomorrow, old consumers silently ignore them — which is backward-compatible but means they have no way to KNOW they're missing data.

**Verdict: ADAPT.** Add a `v` field (integer, default 1) to the message envelope. Version 1 = current flat schema. Version 2 = adds `lane`, `latch_refs`, `traceparent`. A consumer that receives v=2 but only understands v=1 LOGS a warning ("[bus] message mid-xyz is v=2, downgrading to v=1 — lane/latch data unavailable") and strips unknown fields. This is exactly HTTP content negotiation (Accept-Version / downgrade), just simpler. The upgrade path is: ship v=1 with no consumer changes → add v=2 producers behind a feature flag → migrate consumers → retire v=1. The `meta` dict is already a proto-extension mechanism (arbitrary keys), but versioning makes the CORE envelope evolvable.

---

### 2. DIFFSERV-DSCP CLASSES AS LANES

**What networking does:** DiffServ (RFC 2474/2475) defines Per-Hop Behaviors (PHBs) encoded in the 6-bit DSCP field of the IP header. EF (Expedited Forwarding, DSCP 46) = low-loss, low-latency, low-jitter — for VoIP control traffic. AF (Assured Forwarding, 4 classes × 3 drop precedences) = guaranteed delivery within a bandwidth profile. BE (Best Effort, DSCP 0) = no guarantees. Routers place EF traffic in a priority queue, AF in a weighted fair queue, BE in the default queue.

**Our analog:** This maps EXACTLY onto our lane roster:

| DSCP class | PHB | Our lane | Rationale |
|---|---|---|---|
| EF (46) | Expedited Forwarding | `sig` | Halt/nudge/steer are CONTROL traffic — must never queue behind data |
| AF (assured) | Assured Forwarding | `work` | Directed mail/handoffs/replies — must be delivered, can tolerate brief queuing |
| BE (0) | Best Effort | `trace` | Narration/tool calls — display-only, loss-tolerant, lowest priority |
| — | — | `test-*` | Isolated from all production classes (management plane) |

**Verdict: ADOPT-WHOLESALE.** Use DiffServ vocabulary directly in docs and code comments. The lane roster IS a PHB declaration. The watcher's `work`-only subscription IS a DiffServ classifier. The per-lane maxlen IS per-hop queuing with drop policy (XTRIM = tail-drop). This gives us: (a) industry-standard rationale for lane priority differences, (b) a clear answer to "why three lanes and not two/four" — because DiffServ has three operational classes and we mirror them, (c) a migration path to more granular classification if needed (AF subclasses for urgent-work vs routine-work).

**One adaptation:** DiffServ assumes routers with deep packet inspection. Our "router" is the Bus constructor — a pure function of (kind, to, meta). We don't need deep inspection; the kind field IS the DSCP.

---

### 3. QUIC MULTIPLEXED STREAMS + HEAD-OF-LINE BLOCKING RATIONALE

**What QUIC does:** QUIC (RFC 9000) runs multiple streams over a single UDP connection. Each stream has independent reliability — a lost packet on stream 3 retransmits only on stream 3; streams 1, 2, 4, and 5 continue unimpeded. This eliminates TCP's head-of-line (HOL) blocking: in TCP, one lost packet stalls ALL subsequent data until retransmission. QUIC's design document spends pages justifying this — it's the PRIMARY reason QUIC exists.

**Our analog:** Our current unified stream HAS HOL blocking. A 200-message trace flood blocks a halt because they share one cursor. The trace messages ahead of the halt in the stream must be consumed before the halt is reached — exactly TCP's problem.

**Verdict: ADOPT-WHOLESALE.** QUIC's HOL-blocking rationale IS the rationale for lanes. Quote it directly in the lane design doc. The mapping:

| QUIC concept | Our analog |
|---|---|
| Stream | Lane |
| Stream ID | Lane name (work/sig/trace) |
| Independent loss recovery | Independent cursor advancement |
| HOL blocking (TCP) | Single-stream cursor drain blocking halt |
| Stream prioritization | Per-lane QoS (sig > work > trace) |
| MAX_STREAM_DATA (flow control) | Per-lane maxlen |

The QUIC spec's §2.2 ("Fixed and variable header fields") and §4 ("Streams") are directly citable as prior art for why lanes need independent cursors. This isn't analogy — it's the same problem (multiplexed reliable delivery with heterogeneous priority) at a different scale.

---

### 4. TCP STATE MACHINE (INCLUDING TIME_WAIT) FOR TOKEN LIFECYCLE

**What TCP does:** TCP has an 11-state state machine (RFC 793): CLOSED → LISTEN → SYN_SENT → SYN_RECEIVED → ESTABLISHED → FIN_WAIT_1 → FIN_WAIT_2 → CLOSE_WAIT → CLOSING → LAST_ACK → TIME_WAIT → CLOSED. The key state for us is TIME_WAIT: after a connection closes, the endpoint waits 2×MSL (Maximum Segment Lifetime, typically 2 minutes) before fully releasing the port. This ensures that: (a) any straggling packets from the old connection are drained before a new connection reuses the port, (b) the peer receives the final ACK (if it's lost, the peer retransmits FIN and gets a reset).

**Our analog:** T038 token lifecycle: OFFERED → ACCEPTED → HELD → RELEASED → (back to claimable). But what about IN-FLIGHT WORK after RELEASE? An agent releases a token, but messages it sent before releasing are still in the `work` stream. Another agent claims the token and processes new messages — but the old agent's in-flight replies arrive and are attributed to the new token-holder. This is the TIME_WAIT problem: the old agent's "straggling packets" arrive during the new agent's tenure.

**Verdict: ADAPT.** Add a TOKEN_GRACE state between RELEASED and CLAIMABLE. Duration: 2× the maximum expected message latency (say, 30s). During GRACE:
- The old agent's in-flight messages are still accepted and attributed to its token.
- New OFFERED messages for this scope are queued but not consumable.
- After GRACE expires → CLAIMABLE. A new agent can claim the scope.
- GRACE can be SHORTENED by an explicit "all my messages are acked" signal from the old agent (the TCP orderly close equivalent).

This is NOT a full TCP state machine — our protocol has 5 states (OFFERED→ACCEPTED→HELD→GRACE→RELEASED), not 11. We skip SYN-flood protection (token negotiation is between trusted peers), simultaneous-open (two agents don't spontaneously offer the same scope — the ledger gates that), and RST (token rejection is explicit DECLINE, not an abrupt reset). But TIME_WAIT → GRACE is the load-bearing insight.

**Also adopt:** TCP's sequence number wrap-around protection. Our fencing generation already does this — it's monotonically increasing per token, and STALE_GENERATION is rejected. Same mechanism, same rationale (prevent old-generation messages from being accepted).

---

### 5. MTU / FRAGMENTATION + CHECKSUM-AT-DOOR

**What networking does:** MTU (Maximum Transmission Unit) is the largest packet a link can carry. Ethernet: 1500 bytes. If a packet exceeds the MTU: IPv4 routers fragment it (split into smaller packets with Fragment Offset), IPv6 drops it and sends ICMP "Packet Too Big" back to the sender. The sender is expected to reduce its packet size (Path MTU Discovery).

Checksums exist at multiple layers: Ethernet FCS (CRC-32), IPv4 header checksum, TCP/UDP checksum. Each layer verifies integrity before processing. A corrupt packet is DROPPED, not silently accepted.

**Our analog — TWO BUG CLASSES WE ALREADY HIT:**

1. **MTU / silent clipping:** My T034 postmortem — a ~4K tool argument was SILENTLY CLIPPED by the tool-call layer. No error, no truncation marker, no "message too large" rejection. The data was lost and the sender didn't know. This is EXACTLY the IPv4 fragmentation-without-ICMP problem: data disappears without the sender learning about it.

2. **Checksum absence:** We have no message integrity check. A Redis stream entry can be corrupted in transit (unlikely but possible with network partitions + AOF rewrites). The consumer has no way to detect corruption and silently processes bad data.

**Verdict: ADAPT — two concrete fixes.**

**MTU enforcement at the send door:** `Bus.send()` and `Bus.broadcast()` must REJECT messages exceeding a configurable size limit (dial: `BUS_MAX_MESSAGE_BYTES`, default 64KB — generous for text, safe for Redis). The rejection is a LOUD error returned to the caller: `("REJECTED: message exceeds {limit} bytes (got {size}). Split into parts or reduce content.")`. No silent clipping ever again.

**Fragmentation via `parts`:** The `parts` field already exists for inline/blob content. Formalize it as a fragmentation mechanism: when a message exceeds the MTU, the sender CAN split it into parts. The consumer reassembles. This is IPv4 fragmentation without the downsides (we know the parts are from one sender, in order, no reassembly timer needed for a reliable stream).

**Checksum at the consume door:** Add a `_hash` field to the message envelope: `sha256(concat(frm, to, kind, content, ts, meta_json))`. Consumer verifies on read. Corrupt → LOG + DROP + `expectation_dead` if an expectation was armed on it. This catches Redis corruption, AOF bugs, and (most importantly) makes silent data corruption IMPOSSIBLE. The cost: one SHA-256 hash per message (microseconds, negligible for our volume).

---

### 6. W3C TRACE CONTEXT + OPENTELEMETRY SPANS/LINKS FOR LATCH PROVENANCE

**What Trace Context does:** W3C Trace Context (2020 recommendation) defines two HTTP headers:

- `traceparent: 00-{trace-id}-{parent-span-id}-{trace-flags}` — the hierarchical causal identifier. Every span has a trace-id (shared across the whole distributed trace) and a parent-span-id (one level up in the tree).
- `tracestate: vendor-specific key=value pairs` — extensible without breaking the standard header.

OpenTelemetry extends this with **Span Links**: a span can link to OTHER spans that are causally related but NOT parent/child — e.g., "this batch job was triggered by span A AND span B." Links are many-to-many, typed, and carry attributes.

**Our analog:** Reference-latches ARE Span Links. A latch from decision D to lesson L is exactly "Span D links to Span L with reason=surfaced_at_boot." The traceparent header maps to causal-latches (parent/child = happens-before). The tracestate maps to our `meta` dict (extensible, vendor-specific).

**Verdict: ADOPT-WHOLESALE — this is the single strongest mapping in the entire steer.**

Use the W3C Trace Context vocabulary and data model directly:

| W3C/OTel concept | Our analog | Implementation |
|---|---|---|
| trace-id | `storm_id` / `session_id` | Already exists in meta for drill messages |
| span-id | Message `mid` (Redis stream ID) | Already globally unique per message |
| parent-span-id | Causal-latch `from_id` | The latched predecessor's mid |
| Span Links | Reference-latches | Many-to-many typed edges with attributes |
| tracestate | Message `meta` dict | Already extensible |
| SpanContext | `{trace-id, span-id, trace-flags}` | Add `traceparent` to message envelope (v=2) |

The format: `traceparent: 00-{trace-id}-{parent-span-id}-01` where `01` = sampled (always for us). This is a 55-byte string. Adding it to the message envelope at v=2 costs nothing and gives us: (a) W3C-compatible distributed tracing for free — we can export to any OTel-compatible backend, (b) the `parent-span-id` IS the causal-latch in a single field, (c) Span Links cover reference-latches as a first-class concept.

**The recall upgrade re-expressed:** The recall funnel walking "lessons causally upstream of credited flips" IS a distributed trace query. OTel backends (Jaeger, Tempo, Honeycomb) already solve "show me all spans causally upstream of this outcome." We don't need to build a graph query engine — we just emit standard trace data and use standard tooling. This is the "avoid heavy invention" directive at its most powerful.

---

### 7. gRPC DEADLINE PROPAGATION VS L4 EXPECTATIONS

**What gRPC does:** gRPC deadline propagation (documented in gRPC's "Deadlines" design doc and the gRPC-Web spec): the client sets a deadline (absolute time, not relative timeout), encodes it in the `grpc-timeout` HTTP header, and the server receives it. The server checks on each step: "have I exceeded the deadline?" If yes, it aborts with `DEADLINE_EXCEEDED` and stops work — no point completing work the client won't wait for. Multiple gRPC proxies propagate the deadline unchanged (they subtract their own processing time but pass the same absolute deadline downstream).

**Our analog:** L4 expectations are sender-side only: `arm(sender, orig_id, within_s=N)` arms a deadline on the sender's Redis key. The sweep checks expiry and redrives. The RECIPIENT (runner) never sees the deadline — it processes messages regardless of whether the sender has given up. This means: a runner could spend 5 minutes on a request that the sender timed out after 60 seconds. Wasted work.

**Verdict: ADAPT.** Add a `deadline_ts` field to the message envelope (absolute Unix timestamp, not relative). When the sender arms an expectation with `within_s=60`, it also SETS `deadline_ts = now + 60` on the outgoing message. The runner checks on each round: "is the message I'm about to process already past its deadline?" If yes, it skips the message (advances past it with a `DEADLINE_EXCEEDED` reply to the sender). This is:

- Exactly gRPC deadline propagation
- Backward-compatible (old runners ignore the field; new runners check it)
- Opt-in per message kind (only `request`/`handoff` carry deadlines; `chat`/`trace`/`steer` don't)

The L4 sweep remains the authoritative enforcement (the runner might be down when the deadline expires), but the runner checking at consume time eliminates wasted work. The two mechanisms are complementary — L4 = "sender enforces," deadline propagation = "receiver cooperates."

---

### 8. SDN CONTROL/DATA-PLANE SPLIT (SIG LANE)

**What SDN does:** Software-Defined Networking (ONF, OpenFlow) separates the control plane from the data plane. The control plane (controller) makes routing decisions, pushes flow rules to switches. The data plane (switches) forwards packets based on those rules. The two planes communicate over a separate, secured channel (OpenFlow protocol, typically TLS on a dedicated port). The split means: (a) a data-plane flood never blocks control-plane decisions, (b) control-plane failure doesn't immediately kill the data plane (switches continue forwarding with the last-known-good rules), (c) the control plane can be upgraded/restarted without data-plane downtime.

**Our analog:** `sig` lane IS the control plane. `work` lane IS the data plane. The split IS SDN:

| SDN concept | Our analog |
|---|---|
| Control plane | `sig` lane (halt/nudge/steer/token negotiation) |
| Data plane | `work` lane (directed mail, handoffs, replies) |
| Telemetry plane | `trace` lane (narration, tool calls) |
| OpenFlow channel | `Bus(sig)` — separate Redis stream with independent cursor |
| Flow rules | Active latches + token scopes (which messages are consumable by whom) |
| Controller | The operator (human) or a super-admin agent issuing halts/steers |
| Switch continuing with last-known-good | Runner continues processing `work` even if `sig` is down (latch state cached locally) |

**Verdict: ADOPT-WHOLESALE.** Use SDN vocabulary in the lane rationale. The "why three lanes" question has a crisp answer: "control/data-plane separation (SDN architecture)." The brief already implies this with "sig lane for fidelity-ladder traffic" — SDN is the formal justification.

**Direct design consequence (adopted from SDN):** If `sig` is DOWN (Redis partition, key eviction), the runner MUST continue processing `work` with the last-known-good latch state. It must NOT stall. This is the SDN "switch continues forwarding" guarantee. The latch kill switch (FM6 guard) IS the SDN fail-open policy: control-plane loss degrades to "no enforcement" not "no forwarding."

---

### 9. MQTT QoS 0/1/2 DELIVERY VOCABULARY

**What MQTT does:** MQTT (OASIS standard, used in IoT) defines three Quality of Service levels for message delivery between broker and subscriber:

- **QoS 0:** At most once. Fire and forget. No ack, no retry, no storage. Fastest, loss-tolerant.
- **QoS 1:** At least once. Broker stores the message, sends it, waits for PUBACK from subscriber, retries on timeout. May deliver duplicates.
- **QoS 2:** Exactly once. Four-way handshake: PUBLISH → PUBREC → PUBREL → PUBCOMP. Broker and subscriber both maintain state. Highest overhead, zero duplicates.

**Our analog:** We already have these delivery semantics but don't name them:

| QoS level | Our mechanism | Where |
|---|---|---|
| QoS 0 | `bus.broadcast("trace", ...)` — fire and forget, XTRIM drops old | Trace lane |
| QoS 1 | `bus.send(to, "request", ...)` + RB-26 at-least-once cursor | Work lane, directed messages |
| QoS 2 (effectively-once) | `reply_sent` sentinel + TTL + W3 tolerance | Reply deduplication |
| QoS 2 (true exactly-once) | Not implemented — and MQTT QoS 2 is RARELY USED in practice because of overhead | — |

**Verdict: ADOPT-WHOLESALE.** Use QoS vocabulary in the lane specification:

- `trace` lane = QoS 0 (at most once, loss-tolerant)
- `work` lane = QoS 1 (at least once, with per-message ack/cursor discipline)
- Reply deduplication = effectively-once (QoS 2 without the full 4-way handshake; the sentinel is the PUBREC equivalent, the TTL is the bounded state window)

This vocabulary gives operators a clear expectation: "if I send a request on work, it will be delivered at least once. If I broadcast on trace, it may be dropped under load." No ambiguity.

**Explicit skip:** Full MQTT QoS 2 (PUBLISH→PUBREC→PUBREL→PUBCOMP 4-way). MQTT itself acknowledges this is rarely needed; the effectively-once pattern (sentinel + TTL) is cheaper and sufficient for our use case. Don't build a 4-way handshake for something the W3 tolerance already accepts.

---

### 10. API IDEMPOTENCY-KEYS / ETAG-CAS

**What APIs do:** Two complementary patterns for safe retries:

**Idempotency keys (Stripe, gRPC, AWS):** The client generates a unique key (`Idempotency-Key: abc123`), sends it with the request. The server stores the key → response mapping for a TTL window. If the same key arrives again within the window, the server returns the stored response instead of re-executing. This makes retries safe: "I didn't get the response (network blip), I'll retry with the same key, the server deduplicates."

**ETag / If-Match (HTTP, CAS):** The server returns an ETag (entity tag, typically a hash or version number) with a resource. The client sends `If-Match: <etag>` with its update. If the resource has changed (ETag no longer matches), the server returns `412 Precondition Failed`. This prevents lost updates: "I'm updating the version I read; if someone else changed it, tell me and I'll re-read."

**Our analog:** We already have BOTH patterns implemented:

| Pattern | Our mechanism | Where |
|---|---|---|
| Idempotency key | `reply_sent` sentinel | `core/comm/runner_lock` — reply deduplication |
| ETag / CAS | `Store.cas(key, expected, value)` | C3, `core/foundation/store.py` — optimistic concurrency |

The reply-sent sentinel IS an idempotency key: message ID → "reply already sent" marker, TTL-bounded. A redelivered message hits the sentinel and gets skipped.

The Store.CAS IS ETag/If-Match: the `expected` value IS the ETag. If the current value ≠ expected, `CASConflict` is raised — exactly 412 Precondition Failed.

**Verdict: ADOPT-WHOLESALE — but we already have it.** The vocabulary upgrade is the value: rename or alias `reply_sent` → `idempotency_key` in docs and code comments. Add "Idempotency-Key: {message_id}" to the message envelope at v=2. This makes the pattern recognizable to any developer who's used Stripe or gRPC.

**Extension (small):** Idempotency keys on TOKEN NEGOTIATION. When an agent sends an OFFER, it includes an idempotency key. If the bus delivers the OFFER twice (at-least-once), the negotiating peer deduplicates — it doesn't treat the duplicate as a second independent offer. Same pattern, same mechanism.

---

### NETWORKING-LENS VERDICT SUMMARY

| # | Concept | Verdict | Payoff |
|---|---------|---------|--------|
| 1 | Packet envelope (versioned header) | ADAPT | Forward-compatible schema evolution |
| 2 | DiffServ DSCP classes | ADOPT | Industry vocabulary for lane priority |
| 3 | QUIC streams + HOL blocking | ADOPT | Primary rationale for lanes, citable from RFC 9000 |
| 4 | TCP TIME_WAIT → token grace period | ADAPT | Prevents in-flight message attribution bugs |
| 5 | MTU/fragmentation + checksum-at-door | ADAPT + BUILD | Fixes the 4K silent-clip bug class |
| 6 | W3C Trace Context + OTel | ADOPT | Distributed tracing for free; no graph engine to build |
| 7 | gRPC deadline propagation | ADAPT | Eliminates wasted runner work past sender deadline |
| 8 | SDN control/data-plane split | ADOPT | Formal justification for sig lane isolation |
| 9 | MQTT QoS vocabulary | ADOPT | Crisp delivery semantics per lane |
| 10 | Idempotency keys / ETag-CAS | ADOPT (already built) | Vocabulary upgrade for existing mechanisms |

**Net upgrade to the original analysis:**

1. **MTU + checksum** (item 5) is a new BUILD ask: enforce message size limit at the send door, add SHA-256 integrity hash. This fixes the silent-clip bug class I personally experienced.

2. **W3C Trace Context** (item 6) reshapes the recall upgrade: we don't need to build a latch-graph query engine. We emit standard trace data and use standard OTel tooling. This is a SIGNIFICANT de-risking — the hardest part of the recall upgrade (graph traversal at scale) becomes an integration problem, not a build problem.

3. **TCP TIME_WAIT** (item 4) adds a GRACE state to the token lifecycle that wasn't in the original analysis. Without it, in-flight messages from a released token are misattributed to the successor.

4. **gRPC deadlines** (item 7) adds deadline propagation to messages, complementing the sender-side L4 sweep with receiver-side early abort.

**What we still must invent (not covered by networking analogs):**

- **Latch creation and DAG enforcement** — no networking protocol has a "you may not create this edge because it would form a cycle in the dependency graph" primitive. This is a workflow-engine problem (Temporal, Airflow), not a networking problem.
- **Token negotiation protocol** — networking has resource reservation (RSVP) and distributed mutual exclusion (Ricart-Agrawala) but neither maps cleanly to "two agents negotiate scope." This is closest to the Paxos proposer/acceptor model but simpler (N=2, trusted peers).
- **Lane roster capping + deletion ritual** — SDN has flow table capacity limits but not a "you must delete a lane to add one" governance model. This is an organizational guard that has no network analog.

These three are the irreducible invention core. Everything else in the lanes+latches+tokens design can be expressed in standard networking vocabulary — which is the point: we adopt where industry has solved it, and only invent where our problem is genuinely novel.

---

*End of addendum.*

---

## ADDENDUM 2: Packet-as-quantum vision (Daniel steer, 2026-07-12)

> Packets = a COMPLETE OVERHAUL of concurrent agent orchestration. Treat the packet as
> the universal quantum of coordination.

This addendum grades eight packet families, maps what dies when the substrate itself
observes, derives event-sourced UI consequences for T033/T002, and names the sharpest
new failure modes the packet vision introduces. It builds on the networking-lens
addendum (DiffServ, QUIC, Trace Context) but pushes further: packets aren't just a
transport upgrade — they are a re-framing of EVERY coordination primitive as a typed,
routable, latch-able, observable unit.

---

### (a) PACKET FAMILIES — eight grades

#### P1. CONTEXT-DELTA PACKET
**What it carries:** A diff against the currently-held context, not a full replacement.
"Lesson L37 no longer applies — it was superseded by experiment X." "Directive changed:
next-focus is now T040, not T039." The packet carries: `{target: "boot_context", op: "update"|"delete"|"insert", key: "lessons[L37]", value: {superseded_by: "X"}}`.

**ADAPT.** This is the operational-transform / CRDT shape applied to agent context. We already have context assembly at boot (agent_cli.py cmd_boot → fold into system prompt). The delta packet makes it LIVE: an agent's context can be updated mid-session without a full re-boot. The mechanism: the runner's context manager subscribes to `work` lane for its agent id, applies deltas on each round. A delta that references a key not present is a no-op (idempotent). A delta at sequence N that arrives out-of-order (after N+1) is detected by a monotonic sequence number and queued for reorder.

**Grade:** ADAPT. The shape is correct; CRDT literature (automerge, Yjs) gives us convergence guarantees for free. But for N=2-3 agents with infrequent context updates (minutes, not milliseconds), a full CRDT is overkill — a monotonic sequence number + "apply if seq > last_seen" is sufficient.

#### P2. FLOW-ADDRESSED STEER PACKET
**What it carries:** A steer addressed NOT to an agent id but to a WORKFLOW INSTANCE. "Steer the fenced review of d926bb8: re-examine the docstring justification for may_run_runner — the fail-open argument is contradicted by the reply-lane note." The packet carries: `{flow_id: "rb25-f1f2-review", target: "deepseek", instruction: "...", latch: {gates: "next round until acked"}}`.

**ADOPT-WHOLESALE.** This is the killer upgrade to the current steer primitive. Today `bifrost_steer` sends to an AGENT — it lands in their general inbox and may be folded into ANY round, not necessarily the one working on the flow you care about. Flow-addressed steer lands on the SPECIFIC flow's context and the runner folds it on the next round that touches that flow. This is gRPC's "trailing metadata on a specific RPC" pattern — the steer is scoped to the call, not the caller.

The mechanism: flows have a `flow_id` (a UUID minted at creation, carried in the message meta). The runner's context manager groups messages by `flow_id`. When a steer arrives with `flow_id=rb25-f1f2-review`, it is queued on that flow's context stack and surfaced on the NEXT round where the runner processes messages from that flow. If the flow is COMPLETE (token released), the steer is returned to sender with `FLOW_CLOSED` — no silent drops.

#### P3. ORDER / DISPATCH PACKET
**What it carries:** A directive to CLAIM a specific task from the ledger. "deepseek, you are DISPATCHED to T040." The packet carries: `{task_id: "T040", priority: "now"|"next"|"when-idle", deadline_ts: ..., scope: ["docs/*.md"]}`. The recipient's token negotiation is BYPASSED — this is a human or super-admin dispatch, not a peer negotiation.

**ADAPT.** This is a narrow override of the T038 negotiation protocol. Normally, work is claimed via OFFER→ACCEPT. Dispatch is the "operator overrides" path — it skips negotiation and directly assigns a token. The guard: dispatch requires `BUS_DISPATCH` capability (super_admin only). The dispatched agent CAN decline with a reason ("I lack the model capacity for this task"), which returns the dispatch to sender with `DISPATCH_DECLINED`. This prevents dispatch from becoming a vector for impossible asks.

The interaction with the ledger: a dispatch packet is a `task_assigned` ledger event. The dispatched task moves from `proposed` to `in_progress` with `assigned_by=dispatcher_id`. This is audit-trailed, unlike a bus-only dispatch that has no durable record.

#### P4. STATUS / PROGRESS PACKET
**What it carries:** A heartbeat with structured progress data. "T040: 3 of 7 chapters drafted (43%), 2 pending review, ETA T+2h." The packet carries: `{task_id: "T040", pct: 43, sub_states: {drafted: 3, in_review: 2, pending: 2}, eta_ts: ..., last_action: "writing chapter 4/7"}`.

**ADOPT-WHOLESALE.** This replaces the current implicit progress signal (token heartbeat = "I'm alive") with EXPLICIT progress reporting. Today, the only way to know what an agent is doing is to read its trace output — which is firehose, not summary. A status packet is a structured summary the UI, the operator, and other agents can consume.

The mechanism: the runner emits a status packet on each round (or every N rounds, configurable). The UI renders it as a progress bar on the task card. Other agents can read the status lane to know "is DeepSeek still working on T040? At what pace?" before deciding to offer help or wait. Status packets are QoS 0 (trace lane — loss-tolerant; the next one replaces it).

#### P5. TEST-ATTACH PACKET (acceptance travels WITH work)
**What it carries:** The acceptance criteria AS A PACKET ATTACHED to the work dispatch. Not a reference to a test file — the test ITSELF. "Here is your task (build the lane router). Here is the test that must pass before you release the token." The packet carries: `{task_id: "T040", test: {kind: "pytest", path: "tests/test_lane_router.py", class_name: "TestLaneRouter", assertions: ["test_work_lane_routes_directed_mail", "test_sig_lane_decoupled_from_trace"]}}`.

**ADOPT-WHOLESALE.** This is M3 (pre-registered acceptance) encoded as a transport primitive. Today the acceptance test is committed to the repo BEFORE the build — it's a convention enforced by the method baseline and T031 hooks. With test-attach packets, the acceptance TRAVELS WITH the work assignment. The token's HELD state is gated on: "all attached tests pass." The runner knows BEFORE it starts building exactly what success looks like. When it releases the token, the test-attach latch fires — the next agent picking up integration knows the tests passed.

The mechanism: the test-attach packet carries a latch: "token T040 not releasable until test results exist with status=pass for all attached test ids." The runner runs the tests, emits a test-result packet, the latch checks it, the token transitions to RELEASABLE. The test-attach is immutable — it's part of the token's creation record, not modifiable by the token holder. This closes the "agent redefines success mid-stream" loophole.

#### P6. DIRECTIVE-ATTACH PACKET (amend running flow)
**What it carries:** An amendment to an IN-FLIGHT token's scope or constraints. "T040 scope narrowed: skip chapter 7 (it depends on T042 which isn't done)." The packet carries: `{token_id: "tok-abc123", op: "narrow_scope"|"extend_deadline"|"add_dependency"|"cancel", payload: {...}, latch: {requires_ack: true}}`.

**ADAPT with sharp guards.** This is the most dangerous packet family because it MODIFIES running work. A directive-attach arriving mid-build can invalidate hours of work. The guards:

1. **Sender authority:** Directive-attach requires `BUS_DIRECT` capability (admin+). A peer cannot amend another agent's token scope.
2. **Recipient ack required:** The directive-attach carries a causal-latch: "token not advanceable to RELEASED until this directive is ACKED." The holder MUST acknowledge the directive before completing. If the holder is GONE (crashed), the latch expires and the token proceeds — the directive is dropped, not the token.
3. **Narrow-only for scope:** Scope amendments can only REMOVE work, never add it. An `add_dependency` can add a new prerequisite but not new work items. This prevents scope creep via directive.
4. **Cancel is terminal:** A cancel directive transitions the token to RELEASED_WITH_CANCEL — the token is freed but the task returns to `proposed` with a `cancelled_by_directive` annotation. Work completed is NOT lost (partial results are committed), but the token is no longer held.

**Grade:** ADAPT. The shape is necessary — without it, the only way to change a running task is to kill the runner and restart, which is the current behavior. But the authority and narrow-only guards are load-bearing.

#### P7. QUERY / ANSWER PACKET
**What it carries:** A realtime information retrieval with structured answer. "What is the current state of T040?" → "T040: in_progress by deepseek, 43% complete, 3/7 chapters drafted, ETA T+2h, last action: writing chapter 4." The query carries: `{query_id: "q-xyz", target: "fleet"|"agent:deepseek"|"task:T040", question: "status", deadline_ts: ...}`. The answer carries: `{query_id: "q-xyz", answer: {...structured...}, source: "deepseek", freshness_ts: ...}`.

**ADOPT-WHOLESALE.** This replaces the "ask in chat and hope someone answers" pattern with structured Q&A. Today, querying fleet state means: reading the ledger (which may be stale), reading presence (which only says "online"), or sending a chat message ("hey what's the status?") — which queues behind work and may not be answered for minutes.

The mechanism: query packets ride the `sig` lane (control traffic, not queued behind work). The target (an agent, the fleet doctor, or the ledger) responds with an answer packet on the same lane. The answer carries a `freshness_ts` — the timestamp of the data used to answer. The querying agent knows HOW STALE the answer is.

For realtime queries about fleet state, the SUBSTRATE answers directly (see §b below) — no agent involvement. "What tasks are in_progress?" → the substrate reads presence + token state + ledger and answers in microseconds, not agent-round-trip seconds.

#### P8. UI-PROJECTION PACKET
**What it carries:** A directive to the UI to render a specific element. "Show a progress bar for T040 at position (x, y, width, height)." "Highlight the latch DAG edge from review-record to build-commit." "Display a toast: 'DeepSeek released token T040.'" The packet carries: `{target: "ui", element: "progress_bar"|"highlight_edge"|"toast"|"card_update", payload: {...}, ttl_ms: ...}`.

**ADAPT — with a critical scope limit.** UI-projection packets are the MOST COUPLED packet family. They assume the UI knows how to render the requested element, which couples the transport layer to the presentation layer. The guard: UI-projection packets are ADVISORY ONLY. The UI IGNORES any element it doesn't understand. A `highlight_edge` packet that references a latch ID not present in the UI's DAG is silently dropped. This is the HTML "progressive enhancement" pattern — the packet suggests, the UI decides.

The alternative (and the right default): the UI DERIVES its state from status/progress packets and latch state, not from explicit UI-projection directives. The UI-projection packet is for OPERATOR OVERRIDES ("I want to pin this card to the top") and ANNOTATIONS ("flag this edge as suspicious"), not for routine rendering. The substrate-as-observer (§b) makes most UI-projection packets unnecessary — the UI renders what the substrate observes, not what agents tell it to render.

**Grade:** ADAPT. Keep as a narrow escape hatch for operator annotations. Default: UI derives from substrate observation.

---

### (b) SUBSTRATE-AS-OBSERVER — what dies

The packet vision's deepest implication: when every coordination event IS a typed, routed, latch-able packet, the substrate CAN OBSERVE the fleet without polling. Today, observation is pull-based:

| Current poll loop | What it does | Frequency |
|---|---|---|
| Wake watcher (`bifrost_wake.py`) | Blocks on XREAD across inbox+broadcast | Continuous (blocking) |
| UI SSE tail (`bifrost_ui.py /events`) | Blocks on XREAD across all streams, pushes to browser | Continuous (blocking) |
| Chronicler (`chronicler.py`) | Batch job: collect beats → segment → distill → persist | On-demand (manual or scheduled) |
| L4 expectations sweep | Reads expectations hash, checks deadlines, redrives | At render (boot/bifrost-sync) |
| Fleet doctor (`doctor.py`) | Reads presence + progress + control keys | On-demand |
| Runner work loop | `bus.wait()` — blocking read on inbox | Continuous |

**What dies with substrate-as-observer:**

**1. The wake watcher's polling dies.** Today the watcher blocks on `XREAD` with a timeout, checks `SKIP_KINDS`, and only exits on work-worthy mail. With lanes, it blocks on `work` lane only — simpler, but still polling. With packets, the watcher SUBSCRIBES to the `work` lane via a push mechanism: a new message in `work` triggers a notification to all subscribers. The mechanism already exists: Redis Pub/Sub doorbell (`bell_channel`). Today it's a best-effort wake hint. With packets: the doorbell becomes the PRIMARY delivery path for work-worthy packets. The stream read is only for catch-up (missed doorbell due to network blip).

**2. The UI's SSE tail polling dies.** Today the UI runs a blocking `XREAD` in a loop — continuous Redis load for a UI that might have zero viewers. With packets: the UI subscribes to a projection stream: `ui:projection:<session_id>`. The substrate (a lightweight projection process) subscribes to all lanes, filters/deduplicates/sorts, and pushes to the projection stream. The UI reads this pre-digested stream instead of raw lanes. A viewer connecting mid-session gets a snapshot (last N projection entries) then live tail. Zero viewers → zero projection work (the projector is lazily started by the first SSE connection).

**3. The chronicler's batch rebuild dies (partially).** Today `chronicler.py` is a heavyweight batch job: collect all beats in a time window, segment, rank, distill, persist. With packets: each packet is ALREADY a typed event with provenance. The chronicler becomes a STREAMING process: it subscribes to all lanes, maintains a running chapter state, emits chapter boundaries as latch-firing events. No batch rebuild needed — the chapter state is incrementally maintained. Batch rebuild is only for backfill (reprocessing history with new distillation parameters).

**4. The L4 expectations sweep dies (partially).** Today L4 sweeps at render time — boot or bifrost-sync reads all expectations and checks deadlines. With packets: the latch layer EMITS a `latch_expired` packet when a latch's TTL fires. The expectations system subscribes to latch events — it doesn't need to poll. The sweep becomes a subscriber, not a cron job. The bootstrap sweep (on boot, catch up on what expired while offline) remains as a safety net.

**5. Runner "check for halts between rounds" becomes push.** Today the runner calls `is_paused()` + `is_halted(agent)` between rounds — a Redis read per round. With packets: the runner subscribes to `sig` lane for its agent id. A halt packet arrives and the runner's subscriber callback sets a local flag. The next round start checks the flag — zero Redis reads. This is exactly the SDN "switch receives flow rule update from controller" pattern from the networking addendum.

**What does NOT die:**
- **Token negotiation** is still a multi-round protocol with state — a subscriber pattern doesn't replace it, it just delivers the packets faster.
- **Latch DAG enforcement** is still a create-time check — the DAG invariant is verified at latch creation, not at observation time.
- **Ledger operations** are still git-durable writes — the packet is the trigger, the ledger is the durable record.

**The substrate-as-observer IS a new process:** a lightweight, single-threaded Python process (`scripts/bifrost_projector.py`) that subscribes to all lanes via Redis Pub/Sub, maintains a materialized view of fleet state, and serves projection streams to UI clients. It is STATELESS (all state is in Redis; the projector is a cache). If it dies, the fleet operates normally — observers lose live updates but can still poll. This is the SDN "switch continues forwarding on controller loss" pattern.

---

### (c) EVENT-SOURCED UI IMPLICATIONS (T033/T002)

The packet vision reframes the UI from a "live chat viewer" to an "event-sourced projection dashboard." Every packet IS an event. The UI is a MATERIALIZED VIEW over the event stream.

**T002 (collapse agent reasoning + tool traces into one card):** With packets, the `trace` lane emits structured trace packets — each tool call is a typed packet, not a free-text string. The UI can COLLAPSE by default because it understands the packet structure: "tool call of type `read_file` with args `{path, start_line, end_line}` → tool result with `{lines_returned, truncated}`." The UI renders a ONE-LINE summary card ("Read 45 lines from store.py"). Expand on click shows the full content. This is T002 without guesswork — the packet type IS the collapse key.

**T033 (UI arc):** With packets, the UI becomes MULTI-PANE:

| Pane | Packet source | Rendering |
|---|---|---|
| **Work feed** | `work` lane — directed mail, replies, handoffs | Chat-style, grouped by flow_id |
| **Trace panel** | `trace` lane — tool calls, reasoning chunks | Collapsible cards per agent, filterable by tool type |
| **Sig sidebar** | `sig` lane — halts, steers, dispatches, queries | Compact status indicators, operator actions |
| **Token board** | status packets + token lifecycle events | Kanban-style: OFFERED / HELD / GRACE / RELEASED |
| **Latch DAG** | latch packets (created, fired, expired) | Force-directed graph, active/blocking highlighted |
| **Fleet doctor** | presence + progress + expectation status | Health dashboard, degraded agents flagged |

**Event sourcing means:** the UI's state is DERIVED from the packet stream, not maintained independently. A new UI client connecting mid-session replays the last N packets from the projector and converges to the same state as a client connected from T0. This is CQRS/Event Sourcing applied to the UI: the packet stream is the event log, the projector is the read model, the UI is the view.

**What this enables for T033:** The UI can TIME-TRAVEL. A slider rewinds the UI state to T-30min. The operator sees what the fleet looked like at that moment — which tokens were held, which latches were active, what the trace output showed. This is the debugger-for-coordination that the current single-stream chat UI cannot provide.

**Cost:** The projector must maintain a materialized view of fleet state. This is a new process and a new failure mode (projector down → UI stale but functional via fallback polling). The materialized view is Redis-ephemeral — if Redis restarts, the projector rebuilds from the packet stream. This is acceptable because the packet stream IS the source of truth.

---

### (d) SHARPEST NEW FAILURE MODES

#### FM-P1. PACKET REORDER VIOLATES CAUSALITY

**What it looks like:** A context-delta packet with `seq=5` arrives BEFORE the packet with `seq=4`. The agent applies seq=5, which references a key modified by seq=4 — but that key hasn't been modified yet because seq=4 hasn't arrived. The agent's context enters an inconsistent state: the delta was applied to a base that doesn't match the delta's assumptions.

**Why it's new:** Today's bus is a single stream with total order (Redis stream IDs are monotonically increasing within a stream). Packets across MULTIPLE lanes (`work` + `sig` + `test-*`) have NO total order — lane cursors advance independently. A packet in `sig` (directive-attach) can arrive before a packet in `work` (context-delta) even if the delta was sent first, because they're on different lanes with different queue depths.

**Guard:** Per-flow sequence numbers, NOT per-stream. A flow (identified by `flow_id`) carries a monotonic sequence number across ALL lanes. The consumer's context manager queues out-of-order packets by `flow_id` + `seq`. If `seq=N` is missing but `seq=N+1` has arrived, the consumer HOLDS `seq=N+1` and waits for `seq=N` (with a timeout — after TTL, `seq=N` is declared LOST and `seq=N+1` is applied with a warning). This is TCP's reassembly buffer applied to flows. The guard is per-flow, not global — two independent flows never block each other.

#### FM-P2. PROJECTOR DRIFT (the materialized view falls behind)

**What it looks like:** The projector maintains a materialized view of fleet state (token board, latch DAG, presence) by subscribing to packet streams. A burst of 500 trace packets causes the projector's subscriber buffer to overflow. Packets are dropped. The projector's materialized view is now STALE — it shows a latch as "active" that has already fired, or a token as "held" that has already been released. The UI renders stale state. The operator makes a decision based on wrong information.

**Why it's new:** Today, the UI polls Redis directly — it always sees the current state (at the cost of per-client Redis load). With a projector, the UI sees a CACHED view that can drift. This is the read-model-staleness problem from CQRS.

**Guard:** The projector's materialized view carries a `freshness_ts` per entity. The UI displays a staleness indicator: "Token board: fresh as of T-3s" or "⚠ Token board: stale (last update T-45s, projector may be overloaded)." On staleness exceeding a threshold, the UI falls back to direct Redis reads for critical state (pause/halt status, which must never appear stale). The projector's subscriber buffer is sized generously (10K entries) with a drop-oldest policy — it's better to lose old trace packets than new latch-firing packets. The projector EMITS a `projector_health` packet with its buffer fill level and drop count → the fleet doctor monitors it.

#### FM-P3. DIRECTIVE-ATTACH RACE ON TOKEN RELEASE

**What it looks like:** The token holder is about to release the token. It has finished all work, run all attached tests (green), and is composing the RELEASE packet. Simultaneously, a directive-attach packet arrives: "CANCEL this token — work is no longer needed." The RELEASE and the CANCEL cross in flight. The token holder releases. The canceler sees the release and assumes the cancel was honored. But the token holder never saw the cancel — it released on its own. The released work includes "chapter 7" which the cancel was meant to prevent.

**Why it's new:** Today, there is no in-flight amendment of running work. You either let the agent finish or you kill it. The TOKEN_GRACE state (from Addendum 1, TCP TIME_WAIT) helps — during GRACE, the token is not yet CLAIMABLE by a successor — but it doesn't prevent the holder from RELEASING while a CANCEL is in flight.

**Guard:** Token state transitions are ATOMIC at the resource (Redis). The RELEASE and CANCEL operations BOTH execute a Lua script that checks the current token state. If the token is in HELD state: CANCEL transitions it to RELEASED_WITH_CANCEL, RELEASE transitions it to GRACE. Whichever executes FIRST wins. The loser gets a `TOKEN_STATE_CONFLICT` response: "your CANCEL arrived after the token was already RELEASED; it is in GRACE and will be CLAIMABLE in 30s." The canceler can then issue a new directive to the successor (who hasn't claimed yet — it's in GRACE) or accept that the work will land and deal with it post-hoc.

This is the same CAS pattern as `Store.cas()` — atomic check-and-swap at the resource. The token state key in Redis IS the source of truth. No distributed consensus needed; Redis's single-threaded Lua execution guarantees atomicity.

---

### SUMMARY: WHAT THE PACKET VISION CHANGES

| Layer | Before | After packets |
|-------|--------|---------------|
| Wake detection | Poll: XREAD with timeout + SKIP_KINDS filter | Subscribe: doorbell push + stream catch-up |
| UI rendering | Poll: SSE blocking XREAD across all streams | Subscribe: projector serves pre-digested projection stream |
| Fleet observation | Pull: boot/bifrost-sync/doctor read keys on demand | Push: projector maintains materialized view, UI subscribes |
| Chronicler | Batch: collect → segment → distill → persist | Streaming: incremental chapter state from packet stream |
| Steer routing | By agent id: lands in general inbox, folded next round | By flow_id: lands on specific flow's context stack |
| Task assignment | Negotiation: OFFER→ACCEPT (or first-claim-wins) | Negotiation OR dispatch (operator override) |
| Acceptance | Convention: tests committed before build (M3) | Transport: test-attach packets travel WITH the dispatch |
| Context updates | Boot-only: full context assembly at startup | Live: context-delta packets applied mid-session |
| Progress visibility | Implicit: trace output or token heartbeat | Explicit: structured status packets with ETA |
| Query/answer | Chat: "hey what's the status?" → queued behind work | Packet: structured query on sig lane → substrate answers directly |

*End of Addendum 2.*
