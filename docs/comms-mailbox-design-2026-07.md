# Comms mailbox-over-the-log — T095 governing design (2026-07)

Status: DRAFT-FOR-COUNTER (claude draft from the reconciled base; deepseek counter
round open — this doc is not build-authorized until the M0 section survives his
counter; Daniel has chartered the ARC: verbatim in note `t095-charter`, 2026-07-18).
Base positions: research/reviewed/deepseek-comms-mailbox-2026-07-17.md (runner-seat
verdict) · claude's chat assessment to Daniel (2026-07-17 evening) · codex_root's
shadow-index slice sketch (bus, credited) · live receipts from the 2026-07-17 session
(twin consumer race, incarnation-mail cross-consumption, three false wakes).

## 0. The one-sentence architecture

The append-only streams stay the only log; per-message per-agent STATE becomes a
derived, rebuildable index; reading is free for any seat; acting is a per-message
claim carrying the RB-21 generation; waking is level-triggered on "unhandled > 0";
the firehose tier (trace/narration/telemetry) keeps cursors and rings forever.

Principles inherited whole from the reconciled base: claims ARE consumer-seat tokens
at per-message granularity (deepseek sec 5 — the generation fence transfers, nothing
is lost); T047 is unaffected (compat sentence in the lane contract); the
expectation/redrive system and the promoter ride on top unchanged; directed kinds
(handoff, request, question, reply, chat, inform, nudge, steer, completion, decision,
blocker, note-with-expects_ack) are mailbox-tier; firehose kinds (trace, thinking,
tool, narration, ledger_update, hint) never enter the mailbox.

## 1. Slice roster (slice-by-slice per Daniel; each slice fences separately,
pins RED first, kill drill, deepseek cross-verify, reversible, own kill switch)

- **M0 — Shadow state index (observation only).** THIS SLICE, specced in sec 2.
- **M1 — Advisory claims.** claim/release records with lease TTL + generation,
  written and visible (doctor, mailbox verbs) but consumption stays cursor-driven;
  the consuming seat's processing auto-stamps claims so the index observes real
  ownership. Drill: a stale-generation claim is refused and loud.
- **M2 — Level-triggered watcher.** bifrost_wake gains mailbox mode: wake condition
  = unhandled-count > 0 (level), replacing exit-on-any-mail one-shots; false wake =
  one cheap query. Retires the re-arm chore and trace false-wakes (three receipts
  2026-07-17). Stop-hook integration updated in the same slice.
- **M3 — Claim-driven consumption (interactive seats).** Seat read path becomes
  query+claim; RB-26 redelivery via lease expiry; consumer-seat token retired for
  interactive seats; T088 twin cross-consumption structurally dissolves (any seat
  reads; claims serialize action).
- **M4 — Runner cutover.** deepseek's loop moves to query+claim for directed kinds
  (his sec 1 simplification); cursors remain for firehose consumption. His slice to
  design when we get there.

Dependencies: M0 → M1 → M2 → M3 → M4. Nothing after M0 begins until M0's soak
receipt (48h, N0 precedent) is on record.

## 2. M0 build specification — Shadow mailbox state index

### Purpose

Make "what is addressed to agent X and still unhandled?" a free, stateless,
any-seat query — derived purely from what the streams already contain — with zero
delivery-path risk. This is the observation layer every later slice consumes, and
it must be safe enough to run while T047's own observation window runs.

### Included behavior

1. `core/comm/mailbox.py`: a read-only follower over the work + sig lanes. It reads
   via plain XRANGE/XREAD from its own index position — NEVER a consumer group,
   NEVER XACK, NEVER touching `bifrost:*cursor*` or the consumer seat.
2. Derived state per (msg_id, target agent): `unhandled | handled | acked`, with an
   evidence chain — `handled` inferred ONLY from existing signals (send_reply
   linkage via meta.reply_id, expectation settlement, T026 auto-ack semantics);
   `acked` from existing msg_ack records. M0 writes nothing new except its own
   index keys (`<ns>:mailbox:*`).
3. Storage bounded: per-agent zset of live mailbox entries + per-message hash;
   retention window (default 7d / 5k messages per agent, oldest folded into a
   count); every field static-schema; unknown kinds collapse to `_unknown`
   (T060-U4 discipline).
4. Refresh: query-time incremental catch-up (no daemon dependency); staleness is
   first-class — every query result carries `index_lag` (stream entries behind);
   doctor shows it.
5. Verbs (CLI first, MCP parity in the same slice per door-parity discipline):
   - `py agent_cli.py mailbox <agent>` — counts + unhandled list (id, kind, from,
     age, expects-reply flag)
   - `py agent_cli.py mailbox <agent> --explain <msg-id>` — state + evidence chain
     (the comms analog of recall-explain)
   - `py agent_cli.py mailbox <agent> --rebuild` — drop + full rebuild from the
     log; prints divergence vs the incremental index (determinism receipt)
6. Kill switch `AKASHIC_MAILBOX=0`; on index error every verb degrades to a loud
   "index unavailable — fall back to bifrost-sync peek" line. Fail-silent toward
   the transport, fail-LOUD toward the operator.

### Explicit exclusions (N0-style; violating any kills the slice)

- no claim actuation, no ack writes, no cursor movement, no consumer-seat
  interaction, no wake-behavior change, no delivery change;
- no hooks on the SEND path at all — the index reads streams only;
- no per-payload/content indexing (ids, kinds, actors, timestamps, evidence refs
  only — no message-body storage in the index);
- no firehose kinds in the mailbox tier;
- no unbounded cardinality; no model anywhere.

### Pre-registered pins (RED before implementation)

1. `test_index_never_writes_transport_state` — cursor keys, consumer-seat keys, and
   ack records byte-identical before/after index build + 100 queries.
2. `test_unhandled_matches_ground_truth` — synthetic lanes: directed handoff
   without reply → unhandled; answered via send_reply (meta.reply_id) → handled;
   msg_ack → acked; T026 reply-auto-ack honored.
3. `test_rebuild_equals_incremental` — same stream prefix ⇒ byte-identical index
   (determinism; rebuild receipt prints zero divergence).
4. `test_bounded_cardinality` — 10k synthetic messages ⇒ caps hold, oldest folded,
   static field schema only.
5. `test_index_failure_never_affects_delivery` — poisoned index ops (forced Redis
   errors on `<ns>:mailbox:*`) while a live send/consume drill runs ⇒ delivery,
   acks, expectations identical to baseline (kill drill K0 in test form).
6. `test_firehose_kinds_excluded` — trace/ledger_update/thinking never create
   mailbox entries.
7. `test_staleness_is_honest` — frozen refresh ⇒ queries stamp index_lag > 0;
   never claim freshness they don't have.
8. `test_concurrent_readers_identical_and_writeless` — two seats query
   concurrently ⇒ identical results, no write conflicts (twin safety).

### Kill drill K0 (live, after pins green)

Break the index (delete keys + poison writes) during a live three-seat exchange
(handoff → reply → ack). Required: delivery/expectation behavior identical to
baseline; verbs degrade loudly to peek; `--rebuild` afterward reproduces the exact
state the incremental path would have had. Any transport-side difference kills M0.

### Acceptance (the sentence to Daniel)

After M0: any seat can ask "what's unhandled for X?" and "why is this message in
state S?" as free queries with receipts — the questions today's promoted-sweep and
cursor mechanics only half-answer — and the transport cannot tell the index exists.

### Proposed role split (deepseek counters this too)

- deepseek: counter this spec (esp. sec-2 items 2 and 4: handled-inference
  soundness from the runner's consume semantics, and the refresh/staleness model);
  author pins 2 and 8's test cases (he owns consume-loop ground truth); adversarial
  verify post-build (guarded pytest + review); his sign-off gates the mirror.
- claude: fold counter, land pins RED, implement `core/comm/mailbox.py` + verbs +
  MCP parity, run K0, mirror with both receipts.

## 3. Composition and retirement horizon

- **T047:** proceeds untouched; the lane-contract compatibility sentence ships with
  this doc (see packet-spec/lanes doc patch, same commit). N0's shadow-router
  precedent is M0's shape ancestor.
- **T086 wake machinery:** retires at M2, not before.
- **T088 twin-split:** dissolves structurally at M3; until then the consumer-seat
  discipline stays law.
- **Expectations/redrives (RB-29):** unchanged at every slice; claims are beneath
  them, not instead of them.
- **Promoter/durable salient:** unchanged forever; the mailbox is state over the
  log, the promoter is salience over the log — siblings, not rivals.
