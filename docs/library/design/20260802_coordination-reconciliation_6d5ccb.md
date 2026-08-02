---
akashic_id: art_20260802_coordination-reconciliation_6d5ccb
akashic_sha: 4528a090b48f
schema_version: 1
status: current
type: design
date: 2026-08-02
title: coordination-reconciliation
gist: "# Coordination redesign — RECONCILIATION (at Daniil's gate) Status: current (2026-08-02, claude#30e6af5c). Synthesis of SIX inputs: the desi"
visibility: fleet
body_type: markdown
seats: []
category: [coordination, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T03:19:02"
updated: "2026-08-02T03:19:02"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-reconciliation_6d5ccb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-reconciliation

# Coordination redesign — RECONCILIATION (at Daniil's gate)

Status: current (2026-08-02, claude#30e6af5c). Synthesis of SIX inputs: the design
(Daniil+claude), deepseek mechanism review, kimi premise review (blind of deepseek),
deepseek gateway wire review, kimi gateway follow-up, deepseek empirical probe battery
(6/6 probes, 8 live API calls, raw captures in wire-capture-deepseek-2026-08-02/).
NOTHING BUILDS BEFORE DANIIL'S WORD. Dissents carried verbatim; nothing below is watered.

## THE HEADLINE: the design survived, and both reviewers made it stronger

No reviewer rejected the architecture. Both found real wounds. Every wound has a
concrete repair, folded in below. The empirical battery corrected THREE claims its own
author had filed from code-reading — the strongest possible argument for Daniil's
"measure the things that move where they move."

## CONFIRMED REFUTATION (kimi), absorbed — the disease taxonomy was incomplete

kimi, verbatim: "tonight's own corpus contains a failure that is NOT two paths
disagreeing... claude read kimi trace messages surfacing during a stream drain, reported
kimi LIVE... There was only ONE path (the stream content), read once, believed...
**one authoritative surface, believed past its evidentiary scope.**" And: "the doc's
strongest assets, the sensor plane and the metal tap, are precisely the parts the
convergence frame does not predict or justify; they are the design implicitly admitting
the frame is incomplete."

ABSORBED: the diagnosis is now TWO disease classes. (a) two paths that disagree →
converge them (one lane, one cursor shape, one definition of done). (b) one path
believed past its warrant → every authoritative read binds to a chokepoint-captured or
metal-level corroborant; UNRECOGNIZED/dark renders first-class. kimi's warning made
concrete: "the board is the truth" must never mean "the board is the ONLY truth" — a
stale position row believed with authority is the drain-traces failure wearing a new coat.

## NAMES — kimi's lexicon audit wins on two of four

- CONTRACT → **GRAMMAR** (charter is RESERVED for standing agreements per the 2026-07-21
  ruling; "a grammar is not a contract" — kimi).
- STANDING → **POSITION** ("the object IS state-by-key about what is now... a position is
  exactly what the fields hold" — kimi). My name lost; the argument was better.
- **ENGAGEMENT** stands. **BOARD** stands but names ONLY the render, never the store —
  the vocabulary itself now enforces the two-speed split.
- Every incarnation pointer is two-level (`incarnation_ref`, never bare `agent`) — the
  one-level-naming bug class must not be re-imported at the state layer.

## NEW RISKS RATIFIED INTO THE DESIGN

1. EPOCH AMBIGUITY (kimi, missing from the original list): "a row that is accurate,
   current, and about a dead incarnation." Leases retire crashes; nothing retires
   SUPERSESSION (Fable→Opus mid-round, seat id unchanged, is the receipt). Repair:
   position rows carry incarnation_ref + the metal cross-check retires rows whose
   incarnation no longer exists.
2. SIGNATURE DRIFT ROTS FIRST AND SILENT (kimi, re-ranked above blackboard rot):
   "plausible, dated, committed, wrong." Repair — three parts, all adopted:
   self-expiring signatures (valid_through = wall-clock AND harness/runner version
   tuple; expired renders UNRECOGNIZED(stale-codebook)); version-tuple tripwire flips
   the seat's panel to UNCALIBRATED (panel state, not warning); the codebook itself gets
   a metal cross-check (codebook says dead + process exists = diagnose the CODEBOOK).
3. COVERAGE-SHAPED DEBT (kimi, gateway): "a fail-open sensor cannot see its own bypass,
   so coverage — not traffic — is the signal that must be rendered, cross-checked, and
   never self-reported." gateway_coverage: sensed|unsensed|unknown is a first-class
   column; unsensed alarms at the wedged tier; cross-checked wire-vs-ledger-vs-process
   (no cooperation needed). X-Akashic-Agent gets a loud unknown-<conn-id> default, never
   nearest-seat inference. Keys-live-only-in-gateway (bypass becomes impossible, not
   loud) approved as its own future slice, not v1.
4. THE THREE LEASES ARE NOT DUPLICATES (deepseek): seat/file/work-item are different
   resources. The law: the position's claim field IS the runner_lock holder — same key,
   one writer; claim_expires DERIVES from the lock TTL. A parallel field that can
   diverge is forbidden.
5. SINGLE-WRITER-PER-FIELD IS MECHANICALLY ENFORCED (deepseek): per-field HSET is
   atomic (confirmed), but the rule dies if enforced by convention — key-prefix ACL or
   Lua refusal at the write door.

## EMPIRICAL CORRECTIONS (the probe battery vs its own round 1)

| Claim (round 1, code-read) | Wire truth (probed) | Design consequence |
|---|---|---|
| logprobs won't work under stream | WORKS — per-token, INCLUDING reasoning tokens (DeepSeek extension) | confidence/entropy column is REAL; capture when requested |
| keepalive comments exist, SDK swallows them | ZERO on wire; DeepSeek sends none | keepalive_count field DELETED; stall = last_chunk_at + TCP read timeout only |
| reasoning_content may ride model_extra | always delta.reasoning_content; model_extra always {} | gateway reads ONE path; the fallback is dead code for this provider |
| rate-limit headers vary | NONE on 200s; 429-reactive only; x-ds-trace-id only extra | rate-limit telemetry DELETED for DeepSeek; observe 429s |
| TTFT confounds queue/prefill/cache | confirmed; cache delta ~50ms = noise at small prompts; cache_hit_tokens=0 even on identical repeat | TTFT never diagnoses cache; prompt_cache_hit_tokens>0 is the ONLY cache signal |
| — (new) | thinking consumes max_tokens BEFORE content: completion_tokens=0, reasoning_tokens=8 | reasoning_tokens tracked separately ALWAYS; a consumer reading completion_tokens=0 would think nothing happened |
| — (new) | final chunk carries finish_reason AND usage together; content="" not null; truncated mid-tool-call = PARTIAL args | finish_reason relayed always; PARTIAL tool-call flag at the gateway |

## TWO-SPEED SPLIT (kimi's table, adopted whole)

SUBSTRATE (full ceremony): sensor taps; the codebook ("doctrine rendered as data");
position store + lease; engagement artifact; HEADS-DOWN MASKING — the highest-ceremony
item in the design ("the one piece that can withhold the operator's own fleet from him");
alert computation; every deletion (dual-write, redrives, wake-arm). PROJECTION
(fence-lite, Daniil-visible): the BOARD render — ships FIRST; alert render; the UI glow
layer (addendum 2). THE LINE, drawn where tonight's wake-loop class lives: level-triggered
READ is projection; the moment it advances a cursor it pays substrate price.

## COLD-SEAT REPAIR (kimi's law, adopted as the write path's invariant)

Every engagement/position transition is EMITTED AS A LEDGER EVENT FIRST; the position
store is rebuilt-by-construction from the ledger; every rendered row carries the ledger
cursor it was projected from. The board can rot, burn, and be rebuilt losing nothing.
Boot names open engagements involving the booting seat — "discovery-by-alarm is not
discovery" (kimi).

## BUILD ORDER PROPOSED AT THE GATE (each slice RED-first per M3)

0. SENSOR HASH slice-1 (deepseek's, probe-amended field list; both taps — socket AND
   tool-dispatch; zero bus changes)
0.5 CODEBOOK v0 (3 signatures + self-expiry + version tripwire, one calibration drill)
1. BOARD RENDER over sensor hash (PROJECTION, ships first, Daniil sees it) + UI glow
   grammar (addendum 2: hue=state, glow=rate, badge=position; brightness decays with
   signal age; unsensed is a color, not darkness)
2. POSITION store (ledger-first, lease=runner_lock, mechanical single-writer)
3. ENGAGEMENT v1 (fence type only, two participants, declare-and-accept, wall-clock+
   turns expiry, drain-before-advance gate)
4. HEADS-DOWN last (pre-registered operator-breakthrough kill drill BEFORE any masking
   ships)
Gateway rides 0 as the socket tap's implementation (fail-open /health bypass, no
retries, 1:1 SSE passthrough, gateway_coverage column). Keys-in-gateway: own slice,
later, Daniil's call.

## DECISIONS AT DANIIL'S GATE

(1) Ratify names: GRAMMAR / ENGAGEMENT / POSITION / BOARD-as-render-only.
(2) Approve build order 0 → 4 (or reorder).
(3) Mint T-numbers: sensor plane+gateway, codebook, board render+UI, position store,
    engagement v1. (T095 is the lineage for 2-3; unpark-vs-supersede is his call.)
(4) Keys-in-gateway future slice: yes/no/later.
(5) kimi spend: past warn ($171.97/$225) — further kimi rounds are his wallet call.
