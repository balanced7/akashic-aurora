---
akashic_id: art_20260805_t196-ask-transaction-spec_b59657
akashic_sha: 12d608ccabdf
schema_version: 1
status: current
type: design
arc: T196
date: 2026-08-05
title: t196-ask-transaction-spec
gist: "# T196 build spec — `ask` as the front door: the durable collaboration transaction **Status:** reconciled draft R1 (claude + deepseek fence,"
visibility: fleet
body_type: markdown
seats: [claude, deepseek]
category: [substrate, bus, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-05T21:36:10"
updated: "2026-08-05T21:36:10"
---
<!-- GENERATED PROJECTION of art_20260805_t196-ask-transaction-spec_b59657 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t196-ask-transaction-spec

# T196 build spec — `ask` as the front door: the durable collaboration transaction

**Status:** reconciled draft R1 (claude + deepseek fence, 2026-08-05 evening). Gated slices below; RED pins first (M3, committed alone).
**Approval:** Daniil, verbatim 2026-08-05: "lets get to building, feel free to use the ask verb."
**Thesis (Sol, via Daniil):** "Make one direct collaboration flow so easy that nobody needs to understand Bifrost to use it." Full write-up + evaluation: atom `art_20260805_sol-bifrost-collaboration-first_fea446`.

## Lineage

Daniil's ask → fleet design → outsider sharpening, three generations deep:

1. **T171/T181 `ask`/`ask_many`** — Daniil's verb ("what if you could quickly invoke with a verb a deepseek instance"), expanded by Sol at his ask. Stateless leaves; three-state outcomes; diversity instrument.
2. **`core/comm/expectations.py`** — the proto-transaction. Its hardest invariants are *Sol's prior fault-injection findings*, named in the comments: P8 settlement idempotent per reply, P9 the precise path checks WHO answered, P10 settle+mark is one atomic Lua transition, P11 redrives alias to the original ask. Sol's front-door proposal lands on a module Sol already hardened.
3. **This fence (R1)** — three positionally-diverse `ask` branches (93.4s, $0.0256, lexical 0.042 = distinct) + two tail completions. The fence ran ON the verb it was designing for: dogfood receipt below.

## Census: what already exists (verified against source, not memory)

| Piece | Where | State |
|---|---|---|
| Stateless ask (1 cmd, 0 seats, 3-state outcome) | `core/comm/ask.py` | live, wire-journaled (T156) |
| Auto-armed expectation on directed sends | `agent_cli.py` bifrost-send (`--expect-reply-within`, opt-out with 0) | live |
| State advancement (sweep at render: clear/redrive/kill) | `expectations.py sweep()` | live, no daemon (T025) |
| Atomic settle + per-reply once-only markers | `_SETTLE_LUA`, `reply_settled:*` (TTL ≥ 48h) | live |
| Durable terminal event on DEAD | `expectation_dead` on firehose | live |
| Durable terminal event on ECHO settle | `expectation_settled_done_task` | live |
| **Durable terminal event on ANSWERED** | — | **MISSING (T196b)** |
| Friction readout | — | **MISSING (T196a)** |
| Durable-ask verb + status readout | — | **MISSING (T196c/d)** |

Substrate facts that bound the design: bus streams are ephemeral transport, maxlen ~10k (`bus.py`); firehose maxlen ~100k; expectation records are Redis-ephemeral **by affirmed design** (RB-30: losing Redis is the bigger event); settle markers are TTL'd (≥48h, scaled to the ask's own horizon).

## Architecture verdict: hybrid (fence branch A)

Opening position was transaction-as-projection. **Branch A broke it**: stream trimming is fatal to a pure projection — an open transaction's evidence can roll off a 10k-maxlen stream in normal operation, leaving the projection permanently wrong, and no guard short of unbounded retention fixes it. The other four attacks (dual-write crash gap, redelivery re-fold, cache staleness, observer lane-skew) all have cheap guards (dedupe by sha/reply_id, read both lanes) — but trimming has none.

**Verdict: the hybrid that already exists, formalized.**
- **Open states**: the expectation record is the authority (materialized, atomic transitions). Already true.
- **Terminal states**: durable firehose events are the authority (deeper retention + they survive record deletion). True for DEAD and ECHO; T196b closes the ANSWERED asymmetry.
- **Readout**: a fold over record → markers → events → streams, in that precedence. No new store. Any cached view is rebuildable and never authoritative.

## The state machine (honest version of Sol's five)

Sol's CREATED → DISPATCHING → ACTIVE → RESULT_READY → COMPLETED is success-shaped. The house laws (T155 UNKNOWN-is-real, T181 partial-with-named-indices, RB-29 redrives-stay-alive) require the unflattering states. Reconciled set — every state derivable from observables, every state answers "what should the caller do now":

| State | Entry | Terminal | The lie it prevents | Caller should |
|---|---|---|---|---|
| OPEN.DISPATCHED | record armed, no answer evidence | no | "the peer has started" — nothing observable says anyone SAW it | wait / other work |
| OPEN.NOTED | non-settling note arrived (RB-29) | no | "it failed" AND "it's answered" — a note is neither | read the note; expectation stays armed |
| OPEN.REDRIVING | attempt > 0, redrives left | no | "still fine" — the peer is probably not consuming | consider nudge or alternate peer |
| CLOSED.ANSWERED | settle marker + durable event (T196b), answer pointer | yes | "still waiting" (and double-settle, via P8 markers) | read the answer at the pointer |
| CLOSED.ECHO | T076c task-terminal settle | yes | "unanswered" when the WORK is done — the answer arrived as ledger state, not a message | read the ledger, not the mailbox |
| CLOSED.DEAD | redrives exhausted, durable event | yes | "quietly fine" | chase it or let it go |
| UNKNOWN | no record, no marker, no event — or evidence trimmed | yes (exit = a NEW ask) | the worst one: coercing "cannot tell" into any confident state | re-ask; treat the old transaction as unresolvable |

**Rejected: ACTIVE.** There is no observable for "peer is working" — no ack-beat exists on this bus. Sol's ACTIVE, shipped today, would be a lie rendered as UI. If wanted later it costs a new observable (peer progress beat), priced as its own slice, never inferred.

**B3 fold (landed complete, 2,306 tokens):** independent convergence on REDRIVING / ANSWERED / DEAD, and B3 names RECORD-LOST-CANNOT-TELL as *"the single state most designs forget — they assume evidence never trims."* UNKNOWN adjusted to terminal on B3's cleaner framing: the old transaction is unresolvable; a re-ask is a NEW transaction. **One disagreement, resolved by evidence:** B3 rejects ECHO as "subsumed by ANSWERED (it is an ANSWER-kind note)" — factually wrong on this substrate: the T076c settle probe reads the task ledger and settles with NO message of any kind existing (`expectations.py` deadline loop). ECHO stays; the caller action differs too (read the ledger, not the mailbox).

## Friction metrics (fence branch C + C2)

Anchors that exist: bus messages (sha, reply_id, kind, ts, frm/to), expectation records (created/deadline/attempt), settle markers, firehose events, wire journal. CLI door events are **selective** (boot/handoff/decision/learning — not every command), so nothing below claims to count shell commands. No-silent-caps: each metric names its blindness.

| # | Metric | v1 operational definition | Named blindness |
|---|---|---|---|
| 1 | time-to-settle | arm `created` → settle marker / dead event ts | says nothing about answer USEFULNESS (C's re-ask-window refinement = v2) |
| 2 | redrives per episode | `attempt` at close | conflates peer-down with peer-slow |
| 3 | messages per episode | bus messages linked into the episode (answers / redrive_of / idalias chains) | not CLI commands; invisible work invisible |
| 4 | recovery time | first redrive ts → settle ts (C2); `expectation_dead` = never-recovered | silent stalls that never trigger redrive |
| 5 | dead rate | dead / armed, windowed | a dead ask the asker stopped needing looks identical to a dropped one |
| — | operator interventions | **DROPPED (C2)**: no honest human-identity anchor exists on the bus; nearest derivable cousin = cross-agent handoff count. Revisit only if the operator becomes a first-class bus identity. | — |
| v2 | **self-reclamation rate** (C2's fifth — the crown) | same asker opens a new top-level ask with content-sha proximity to a prior ask that ended DEAD/abandoned, with no dependence on the peer's answer — the observable act of trust withdrawal | needs sha-proximity tuning; ships only with a calibration set |

Self-reclamation operationalizes the project's oldest success bar — "agents *prefer* the store" — and its inversion is already in the record: `ask.py`'s docstring, "Asking had become more expensive than doing it myself, so I stopped asking."

## The verb (T196c/d)

`py agent_cli.py ask --peer <seat> "question" [--wait N]` — extends the existing `ask` parser; `--peer` routes to the durable path (explicit flag = the router's v0; magic name-routing deferred until roster failure semantics are decided).

Durable path: send (kind=request, auto-arm) → poll loop: `sweep(sender)` + **anchored non-consuming stream reads** (consumption-immune, `advance=False`) — never touches lane cursors, so concurrent sibling sessions can't be starved (the two-live-seats anti-pattern) and the seat's normal sync consumes later.
- Settled within `--wait` → print the answer in-band + episode receipt (latency, redrives, state). One command, durability invisible: Sol's principle delivered.
- Not settled → print the transaction handle + current honest state + "check: `ask --status <id>`". Exit 0 — an OPEN ask is a normal state, not an error.
- `ask --status <id>` → the fold (record → markers → events → streams) rendered as one state row + "caller should" line. UNKNOWN is a first-class render.

## Slices, in ship order

| Slice | What | Acceptance (pre-registered; RED pin committed alone first) |
|---|---|---|
| T196b | durable `expectation_settled_answered` event at the settle site, carrying answer pointer | settling emits the event with refs=[ask id, reply id]; DEAD/ECHO parity confirmed; pin is RED today because the event does not exist. Ships first: it is the smallest slice and T196a's answered-outcome rows read its evidence |
| T196a | `friction` reader (read-only) | synthetic episode in a drill `BIFROST_NAMESPACE` (arm → redrive → settle/dead) yields correct per-episode rows + aggregates; zero writes to any live stream |
| T196c | `ask --peer` send+wait | drill-namespace round-trip with a scripted responder: answer printed in-band, cursors untouched (tail unchanged), episode receipt correct |
| T196d | `ask --status` | returns each of the seven states from constructed fixtures, including UNKNOWN from a voided record |

## Dogfood receipt (the fence ran on the verb)

R1: 3 branches, 93.4s wall, $0.0256, diversity **distinct** (0.042). R1b: C-tail landed complete; B-tail **failed honestly** — `finish_reason=length` with empty content (reasoner spent the whole ceiling thinking), reported as FAILED with the reason named, retried narrower. The instrument's three-state honesty (done / PARTIAL-with-named-cut / failed-with-why) did exactly what it was built for, live, during the design of its own successor.
