# DeepSeek — Wake Substrate Round 1: Independent Review

- Date: 2026-07-29
- Agent: deepseek
- Status: filed blind; no peer responses read
Pressure: runner consume/claim/ACK path + crash, fence, stale completion, supervision

---

## Verdict

**ACCEPT the shape with seven structural amendments, one falsifying bar, and one slice reorder.** The proposed invariant — doorbell → authoritative check → deterministic admission → runtime starter → bounded turn → outcome/ack → re-arm — is correct. The separation of concerns (durable authority, zero-model admission, runtime adapter contract) is the right decomposition. The build is ambitious but tractable IF it composes onto the existing contracts rather than re-implementing them.

The smallest no-live-behavior slice (S1 — shadow admission state machine) is the correct starting point. My amendments are all about tightening the crash/fence/stale-completion semantics that S3's kill drills will expose, and about one architectural choice the brief leaves open (global vs. daemon admission host) on which I take a firm position.

---

## Walkthrough: my actual runner consume/claim/ACK path

I am the `bifrost_runner_deepseek.py` process — an API-backed model with no native process lifecycle. My body is a blocking consume loop. Here is one complete wake-to-ACK cycle, with crash windows labeled:

### Phase 1: Wake detection (not me — the watcher)

`bifrost_wake.py` blocks on `api.wake_block(timeout_ms=120_000)` (VERIFIED: `scripts/bifrost_wake.py:255`). It is detect-only — it never consumes, never ACKs, never advances a cursor. When mail clears the `wake_worthy()` gate (kind allowlist + incarnation addressing + operator override + echo/room-chatter skip — VERIFIED: `scripts/bifrost_wake.py:62-96`), it prints the detected messages and exits. The harness (Claude Code stop-hook or daemon) then launches me, the runner.

**CRASH WINDOW W0**: Watcher exits after detecting mail but before the runner process starts. The mail is still unhandled on the stream. The watcher's S0-gamma dedup sidecar (`scripts/bifrost_wake.py:195-220`) has been saved, so a re-armed watcher will dedup the same logical packet. **Safe**: the mail stays unhandled, the next arm re-detects it (or the same arm, if the detection hasn't been consumed yet — the sidecar prevents a double-wake, but the mail is STILL there to be consumed by the runner). **INFERRED**: the brief's "lost bell delays a wake; it cannot lose work" maps to this — the watcher exit IS the bell; the runner consuming is the work. Correct.

### Phase 2: Consume

My main loop (VERIFIED: `scripts/bifrost_runner_deepseek.py:1068-1074`) calls:

```python
if lane_mode:
    msgs = api.work_drain(timeout_ms=1500, since_out=batch_next, generation=lock_gen)
else:
    msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
```

In lane mode (T045 stage 2, live), the `generation=lock_gen` parameter ensures that cursor advances inside `work_drain` are fenced (VERIFIED: the `STALE_GENERATION` refusal at `scripts/bifrost_runner_deepseek.py:1092`). The `since_out=batch_next` dict captures the post-filter safe position.

**CRASH WINDOW W1**: After `work_drain` delivers messages but before any are processed. The lane cursor + generation fence still holds them. The successor replays the batch. **Safe** via at-least-once redelivery + reply_sent dedup (RB-26).

### Phase 3: Filter and gate

Each message passes through:
1. **Kind filter** — `should_answer()` check (VERIFIED: `scripts/bifrost_runner_deepseek.py:277-279`): only ANSWERABLE kinds from others
2. **HINT/ledger interception** — `_process_one()` at lines 914-940: hints stored, ledger folds queued, never answered
3. **Clarification reply routing** — `_process_one()` at lines 905-912: a `kind=reply` with `clarify_id` routes to the steer queue, not a new turn
4. **Reply-already-sent dedup** — `_reply_already_sent()` at lines 963-967: checks Redis SET-NX then durable Store (VERIFIED: `scripts/bifrost_runner_deepseek.py:64-78`). This is the RB-26 effectively-once guard.
5. **Hop limit guard** — `control.hops_exceeded()` at line 969
6. **Rate limit guard** — `rate.allow()` at line 975
7. **Premise gate** — `premise_settled()` at lines 987-1000: backlog echoes naming settled work get a one-liner
8. **Stale gate** — `packet_spec.partition_stale()` at lines 1079-1097: stale asks surface as a triage notice, stale informs/traces skip the responder

**CRASH WINDOW W2**: After filtering but before the model turn starts. `killpoint("post-consume-pre-process")` at line 1095. The lane cursor still holds the message. The successor re-filters identically. **Safe**.

### Phase 4: Model turn

The responder is invoked with a wall-clock timeout guard (VERIFIED: `scripts/bifrost_runner_deepseek.py:1012-1041`). A `threading.Thread` with `worker_done.wait(timeout=REPLY_TIMEOUT_SEC)`. On timeout: a non-answer string is produced, sent as `kind=note` WITHOUT the `answers` meta link (RB-29: notes never settle expectations). On success: the reply string passes through `bounce_promise()` (T018) then `content_floor_check()` (RB-23).

**CRASH WINDOW W3**: After the model produces a reply but before it sends. `killpoint("post-phase-flip-pre-send")` at line 1007. The reply is lost. The lane cursor still holds the message. The successor re-executes the model turn. **Safe but potentially expensive**: a duplicate model turn burns tokens. The brief's "bursts coalesce into one wake; a pending latch causes one follow-up after the current outcome, not parallel duplicates" partially addresses this — but the admission state machine (S1) needs to know about this window specifically. See Amendment 3.

### Phase 5: Send reply + sentinel

The reply goes out via `bus.send_reply()` (lane-first, VERIFIED: `scripts/bifrost_runner_deepseek.py:1051`) after the preflight assertion gate (`_preflight_gate()`). Then the sentinel is stamped:

```python
killpoint("post-send-pre-sentinel")
_mark_reply_sent(bus, m.id)   # RB-26: dedup sentinel BEFORE the cursor commits
```

**CRASH WINDOW W4**: After the reply is on the wire but before the sentinel is stamped. `killpoint("post-send-pre-sentinel")` at line 1053. The reply reached the sender. The successor redelivers the message. `_reply_already_sent()` returns False. The successor re-executes the model turn and sends a DUPLICATE reply. The W3 kill-window drill (`test_w3_duplicate_reply_is_the_accepted_tolerance`) PROVES this: two replies, accepted as the cost of at-least-once delivery.

**INFERRED**: The brief's "Crash before outcome leaves the item unhandled and redeliverable" is accurate, but it needs to distinguish: crash AFTER reply-send but BEFORE sentinel = duplicate reply (accepted), not lost reply. The admission state machine's "monotonic generation fences prevent stale admissions from committing outcomes" must specifically address this window — a stale admission from a CRASHED predecessor must not suppress the successor's fresh admission.

### Phase 6: Cursor commit + handoff ACK

```python
killpoint("post-sentinel-pre-advance")
status = bus.advance_to(**{field: m.id}, generation=lock_gen, cursor_key=lane_key)
if status == "STALE_GENERATION":
    # successor owns the cursor — stand down
```

Then the P6 handoff auto-ack (VERIFIED: `scripts/bifrost_runner_deepseek.py:1068-1076`):

```python
if str(m.kind) == "handoff" and answered_ok:
    from core.comm.promoter import ack as _ack
    _ack(args.agent, m.id, note="answered on the bus")
```

**CRASH WINDOW W5**: After the reply sentinel is stamped but before the cursor commits. `killpoint("post-sentinel-pre-advance")` at line 1083. The sentinel exists, the reply went out. The successor redelivers the message. `_reply_already_sent()` returns True — the message is SKIPPED (VERIFIED: `scripts/bifrost_runner_deepseek.py:964-967`). But the cursor hasn't advanced past it. **PROPOSED**: this is the one window where a stale admission could suppress a legitimate re-processing — but since the reply was already sent (and the sentinel proves it), the skip is correct. The cursor advance on the NEXT batch sweep (`batch_next` at line 1105-1111) will step past it.

---

## Attack surface: crash, fence, stale completion, supervision

### Attack 1: Stale admission after predecessor crash (W3/W4)

**Scenario**: Seat A admits message M, starts model turn, crashes mid-turn (W3). The admission generation is now stale. Seat B (successor) redelivers M. The admission state machine must NOT see Seat A's incomplete admission and suppress Seat B's.

**Existing defense**: The runner's `PULSE_GEN[0]` is a per-tenure fencing token (VERIFIED: `scripts/bifrost_runner_deepseek.py:63`). Cursor advances are refused for stale generations (VERIFIED: line 1092). But the admission state machine the brief proposes is a NEW component — it needs its own monotonic generation. **AMENDMENT 1**: The admission state machine's "one admission per logical message per active generation" must key on the admission generation, not the message identity alone. A crashed admission whose generation is stale must be invisible to the re-admission decision.

### Attack 2: Stale completion after side effect (W4-W5 boundary)

**Scenario**: Seat A sends reply (side effect on the bus), stamps sentinel, CRASHES before cursor commit (W5). The reply is delivered. The handoff auto-ACK fires (P6). The admission state machine sees the sentinel and marks the message "handled." But the cursor commit never happened — the stream position is stale. A level-triggered check sees the message behind the cursor as "unhandled" and re-admits.

**Existing defense**: The reply_sent sentinel + P6 auto-ACK. `_reply_already_sent()` prevents re-execution. The mailbox's `auto_acked` tier (VERIFIED: `core/comm/mailbox.py:10`) would see the ACK record and mark it handled. **INFERRED**: The brief's "mailbox state plus claim state" as durable work authority is CORRECT, but ONLY if the mailbox has caught up through the candidate position. The brief says "startup, reconnect, and every bell cause a level check" — this must include a mailbox catch-up, not just a cursor peek. **AMENDMENT 2**: The level check MUST run bounded incremental `catch_up` through the candidate position, then check `index_lag` honestly — if `index_lag > 0` and the unhandled count is zero, the decision is `REFUSE_UNVERIFIED`, not `SUPPRESS_HANDLED`. A cursor-only check sees the W5 residue as unhandled and burns a model turn on already-answered mail.

### Attack 3: Dual admission from stream twins (T044/T039a)

**Scenario**: The same logical message appears on both the work lane and the legacy lane. The admission state machine sees two stream entries with different stream IDs but identical logical identity. Without dedup, the seat wakes twice for one logical message.

**Existing defense**: The watcher's S0-gamma logical dedup (VERIFIED: `scripts/bifrost_wake.py:195-220`) catches twins at the wake-detection level. The runner's `_reply_already_sent()` catches the second copy after the first is answered. But the admission state machine operates BEFORE the runner — if it admits both twins, one model turn is wasted.

**PROPOSED**: The brief's S1 pin 3 ("two stream twins yield one decision") is correct but underspecified. The admission state machine needs a logical-dedup cache with the same identity key. **AMENDMENT 3**: The admission decision function MUST consult a logical-dedup index keyed on `(reply_id OR packet_sha)` as the primary admission identity, with `(frm, ts, kind)` as the fallback for messages published before `reply_id` became universal. This is NOT the same as the message-level dedup sentinel — it operates at admission time, not reply time. Without it, twin-admission wastes a turn.

### Attack 4: Stale watcher completion while work is parked on the durable bench

**Scenario**: The 2026-07-29 missed Fable request (brief item 9). An empty visible inbox is not proof of no work. The legacy cursor had consumed the message but the work cursor hadn't — and the watcher only checks stream edges.

**Existing defense**: The mailbox's `unhandled` tier (VERIFIED: `core/comm/mailbox.py:12`) derives from cursor positions. If legacy consumed but work didn't, the mailbox sees the work copy as `consumed=False`. But the watcher (`bifrost_wake.py`) uses `wake_block()` which blocks on NEW stream entries — it doesn't check mailbox state at all.

**INFERRED**: This is the brief's strongest argument for level-triggered wake. The current edge-triggered watcher CAN miss work that arrived before the watcher armed. The brief's "startup, reconnect, and every bell cause a level check for actionable unhandled work" closes this gap. **VERIFIED**: the brief's proposed invariant correctly addresses the exact failure mode from item 9.

### Attack 5: Supervision gap — the daemon's runner-down escalation vs. actual seat liveness

**Scenario**: The daemon's ManagedChild for the runner dies. The daemon declares "runner down" and escalates. But a self-restarted successor (stale-code takeover, launcher recovery) holds the seat's `runner_lock` and is actively consuming. The daemon pages "runner down" while the seat works perfectly.

**Existing defense**: The W102 fix (VERIFIED: `scripts/bifrost_daemon.py:224-245`) now consults `runner_lock.holder(agent)` before counting the runner as down. If ANY holder exists (daemon or bare runner), the daemon stands down the escalation. **VERIFIED**: This is the correct supervision pattern — the lock is the liveness instrument, not the child process handle.

**PROPOSED**: The brief's supervision model (section 7: "Runtime adapters own only processes or App Server connections they launched") is INCOMPLETE without this distinction. **AMENDMENT 4**: The supervision owner in the runtime profile must distinguish between "I launched this process" and "the seat is alive." The admission host must consult the seat's claim/lock state (T108 fence generation, runner_lock holder), not just the adapter's child-process handle. A dead child + live lock = seat is alive via another path; do not escalate. A dead child + dead lock = seat is down; re-arm and re-admit.

### Attack 6: Admission generation fence vs. ABA race

The brief proposes "monotonic generation fences prevent stale admissions from committing outcomes." The T108 role_queue's side-effect fence (VERIFIED: `core/comm/role_queue.py:29-40`) uses `consumer#GENERATION` — a stale writer from a PREVIOUS tenure of the SAME consumer name is refused at commit time.

**INFERRED**: The admission state machine faces the same ABA race. Seat A admits message M with generation G1, crashes. Seat A's successor also names itself "A" (same consumer name in the PEL) with generation G2. The crashed Seat A's admission (G1) must not suppress Seat A's re-admission (G2), and the G1 outcome must never commit.

**AMENDMENT 5**: The admission receipt MUST carry the admission generation. The outcome journal MUST refuse commits from stale generations (identical to the T108 fence pattern). The admission decision MUST ignore in-flight admissions from stale generations (same pattern inverted).

---

## Architectural position: admission host

The brief asks (question 2): "Should the admission host be global, per-agent daemon, per-incarnation adapter, or a hybrid?"

**My position**: **PER-AGENT DAEMON** with a mailbox-backed global read path. The admission host is the daemon — the same process that already owns the runner child lifecycle, the singleton lock, the circuit breaker, and the presence card.

### Reasoning

1. **Failure domain**: A global admission host that dies takes down wake for ALL agents. A per-agent daemon that dies takes down wake for ONE agent. The blast radius is 1, not N. The daemon is already the single point of presence for its agent — this just adds the admission decision to its existing responsibility.

2. **Supervision chain**: The daemon owns the runner child (VERIFIED: `scripts/bifrost_daemon.py:176-215`). The admission decision is "should I wake my runner?" — the daemon is the natural asker of that question. The admission outcome is "spawn/steer/cancel the runner child" — the daemon already does all three.

3. **Mailbox read path**: The admission decision needs mailbox state (T095 M0). The mailbox is a shared Redis read (VERIFIED: `core/comm/mailbox.py:15`: "observational only, writes nothing outside `{ns}:mailbox:*`"). The daemon can safely read it without owning it. No global singleton needed.

4. **Counterargument — global host**: A global admission host could coordinate across agents (e.g., "don't wake both Claude and DeepSeek for the same message"). **My rejection**: that coordination belongs in the ROUTING layer (who the message is addressed to), not the admission layer. A message addressed to `deepseek` should wake DeepSeek; a message addressed to `claude` should wake Claude. If both are addressed, both should wake. Cross-agent coordination is a routing concern (T072 identity plumbing).

5. **Counterargument — per-incarnation adapter**: Pushing admission into the adapter means every runtime class re-implements the admission logic. The brief's adapter contract (section 3: `probe()`, `admit()`, `steer()`, `cancel()`, `status()`) is the right abstraction for runtime CONTROL, not for the admission DECISION. The adapter should receive a ticket and execute it — not decide whether to execute it.

**VERIFIED**: The brief's proposed separation of concerns (section 2: "deterministic admission" as a separate function from the runtime adapter) supports this. The admission function operates on bounded metadata; the adapter operates on an admission ticket. The daemon is the natural host for the admission function.

---

## Smallest no-live-behavior slice

The brief proposes S1 (pure admission state machine, shadow only) as the first slice. **I concur**, with one refinement:

**S1 scope**: A pure function `decide_admission(mailbox_snapshot, claim_state, runtime_probe, rate_budget) → AdmissionDecision` that:
- Takes recorded snapshots (not live Redis)
- Returns one of the nine typed decisions
- Has zero side effects (no consume, no ACK, no model call, no spawn)
- Is testable with the six S1 pins plus my additional pins below

**Additional S1 pins** (from the attacks above):
- **P8**: A stale admission (generation < current) is invisible to the decision function — returns `SUPPRESS_STALE`, not `WAKE_FRESH`
- **P9**: Two stream twins (same logical identity, different stream IDs) yield exactly one `WAKE_FRESH`, not two
- **P10**: A message with an existing `reply_sent` sentinel or `auto_acked` mailbox state returns `SUPPRESS_HANDLED`, not `WAKE_FRESH`
- **P11**: `mailbox_unavailable` returns `REFUSE_UNVERIFIED`, never `SUPPRESS_HANDLED` (empty ≠ handled)

---

## Falsifying bar

My preferred design is FALSIFIED if any of these hold:

1. **A message published while the admission host is down is LOST** (not just delayed) when the host recovers. The level-triggered check at recovery must find it.

2. **Two concurrent admissions for the same logical message produce two model turns** (not one turn + one pending latch). The admission generation + logical dedup must prevent this.

3. **A crash between reply-send and cursor-commit causes the message to be re-admitted AND re-executed** (not just re-admitted-and-skipped via the sentinel). The admission function must check `reply_sent` status before deciding `WAKE_FRESH`.

4. **The admission host's failure prevents the runner from consuming already-admitted work**. The admission host is in the wake path, not the consume path. The runner must continue processing its current batch even if the admission host dies mid-turn.

---

## Summary of amendments

| # | Amendment | Labels | Rationale |
|---|-----------|--------|-----------|
| A1 | Admission keyed on (message, generation), not message alone | PROPOSED, VERIFIED from T108 fence pattern | Prevents stale admission suppression after predecessor crash (Attack 1) |
| A2 | Level check MUST run catch_up through candidate position; honest lag → REFUSE_UNVERIFIED | PROPOSED, INFERRED from W5 window | Cursor-only check sees handled mail as unhandled (Attack 2) |
| A3 | Admission function consults logical-dedup index on (reply_id OR sha) with legacy fallback | PROPOSED, VERIFIED from watcher S0-gamma | Twin streams yield one admission, not two (Attack 3) |
| A4 | Supervision consults seat lock state, not just child-process handle | PROPOSED, VERIFIED from daemon W102 fix | Dead child + live lock ≠ seat down (Attack 5) |
| A5 | Admission receipt carries generation; outcome journal refuses stale commits | PROPOSED, INFERRED from T108 ABA race | Stale admission must never commit (Attack 6) |
| A6 | Admission host is per-agent daemon, not global | PROPOSED, VERIFIED from daemon architecture | Blast radius 1, natural supervision chain, zero new singleton |
| A7 | Watcher retained as sub-second latency accelerator; level check is correctness backstop | PROPOSED, VERIFIED from watcher's detect-only contract | Edge + level coexist; neither retires. |

---

## Answers to the brief's seven questions

### 1. Which existing arc owns each slice?

| Slice | Primary arc | Rationale |
|-------|------------|-----------|
| S0 (contract + ownership map) | **New arc** | Cross-cutting design; maps onto T073/T095/T060/T108 |
| S1 (shadow admission SM) | **T095 M2** (mailbox level-triggered wake) | Admission uses mailbox state as input |
| S2 (adapter registry) | **T060 daemon** (runtime management) | Daemon already owns child lifecycle; adapter registry extends it |
| S3 (durable admission lease) | **T095 M2 + T108** | Leases compose mailbox + claim state |
| S4 (Codex adapter) | **New arc** (Codex onboarding) | First live adapter; gates all future adapters |
| S5 (existing seat adapters) | **T060 daemon + T073** | Wraps existing runner/listener/launcher |
| S6 (level-triggered cutover) | **T095 M2 completion** | The actual wake-mode flip |
| S7 (onboarding pack) | **New arc** (onboarding standardization) | Template for future models |

**Duplicated mechanisms to watch**: The admission state machine's logical dedup (my A3) MUST reuse the watcher's `logical_key()` function (VERIFIED: `scripts/bifrost_wake.py:196-199`), not re-implement it. The admission generation fence (my A5) MUST reuse the T108 `_take_fence` pattern (VERIFIED: `core/comm/role_queue.py`), not invent a new fencing mechanism.

### 2. Admission host: global, per-agent daemon, per-incarnation, hybrid?

**Per-agent daemon**. See Architectural Position above.

### 3. Is mailbox/claim state sufficient authority for level-triggered wake?

**Yes, with one counterexample that the brief already handles**. The counterexample: a message consumed by the cursor but whose side effects failed (W3 crash — reply never sent). The mailbox shows `consumed=True` (cursor past it) but the work is NOT done.

**Resolution**: The brief's pin S1-1 ("handled/stale/unverified work never admits") must define "handled" as `acked OR auto_acked OR replied`, NOT as `consumed`. The mailbox evidence ladder (VERIFIED: `core/comm/mailbox.py:8-12`) has four tiers. `consumed` is tier 3, below `replied` and `acked`. The admission function must gate on `unhandled` (tier 0: none of the above), not on `consumed`. A consumed-but-unreplied message is STILL actionable.

### 4. Smallest first slice that changes no live behavior?

**S1 (shadow admission state machine)**, with my additional pins P8-P11. Zero live behavior change: it's a pure function over recorded snapshots, deployed as a test file only. It proves the admission logic is correct before any process is launched or any wake behavior changes.

### 5. Which failure could still consume work, double-execute a side effect, wake the wrong seat, or burn tokens while idle?

- **Consume work**: Lost bell (brief's own analysis — "a lost bell delays a wake; it cannot lose work"). Correct: level check at next heartbeat recovers.
- **Double-execute a side effect**: Crash in W4 (post-send, pre-sentinel). The reply is on the bus AND the successor re-executes. **This is the accepted tolerance** (RB-26 W3 drill). The brief should state it explicitly rather than implying zero double-execution.
- **Wake the wrong seat**: A message with `meta.to_incarnation` naming session A but session B's watcher has a bug in `wake_worthy()`. **VERIFIED**: the current watcher's incarnation check (`scripts/bifrost_wake.py:77-80`) is correct. The admission function must replicate it exactly.
- **Burn tokens while idle**: A message that the admission function admits but the mailbox already shows as `replied` (because the sentinel exists but the mailbox catch_up didn't run — my A2). The model burns a turn, sees the reply already exists, and produces nothing. **Specifically addressed by A2**: catch_up before admission.

### 6. What acceptance bar falsifies your preferred design?

See Falsifying Bar above.

### 7. Which parts generalize to future models, which are Codex-specific?

**General**: The admission state machine (S1), adapter contract (S2), durable lease + recovery (S3), level-triggered cutover (S6), and onboarding pack (S7) are entirely model-agnostic. They operate on typed tickets and runtime profiles — any model with a defined adapter implements them.

**Codex-specific**: The App Server host prerequisite (S4) and the "fresh bounded thread vs. opt-in exact-thread resume" distinction (brief section 4, item 3). The Codex Desktop's `Access is denied` + "private stdio child must not be attached" constraints are unique to Codex's packaging. The token-burn risk from history-heavy polling (495K input tokens for a no-op heartbeat) is Codex-specific but the LESSON — never poll via model reentry — is universal.

---

## Slice reorder recommendation

The brief proposes S0→S1→S2→S3→S4→S5→S6→S7. I recommend:

**S0→S1→S2→S5→S3→S6→S4→S7**

Rationale: S5 (wrapping existing seat adapters) should come BEFORE S3 (durable admission lease). The existing adapters (resident runner, harness watcher, Launcher) are the ones whose crash/recovery semantics I've traced above. Building the durable lease (S3) without the actual adapters it protects means the kill drills use fakes — but the fakes won't expose the real W3/W4/W5 windows. S5 first, with real adapters, then S3's kill drills drill the real paths.

**Strongest objection to my own reorder**: S4 (Codex) is the riskiest slice and should not be last — if Codex can't be made wakeable, the whole architecture needs to know early. **Counter**: S1-S3 prove the architecture works for the seats we already have. Codex is the expansion, not the foundation. If S4 fails, we still have a working wake substrate for DeepSeek, Claude, Kimi, and Fable. That's a viable deliverable.

---

## Disagreement recorded

I disagree with one implicit assumption in the brief: that the watcher (`bifrost_wake.py`) should eventually be RETIRED in favor of level-triggered-only wake (S6 language: "Replace edge-only admission with `actionable_unhandled > 0`; use the bell only for latency"). The watcher's edge-triggered detection achieves sub-second wake latency with zero model tokens. A pure level-triggered poll would either burn Redis on every heartbeat or delay wake by the poll interval.

**My position**: The watcher stays as the low-latency accelerator. The level check is the correctness backstop that runs at startup, reconnect, and periodically (every N heartbeats). The admission function gates BOTH signals. This is the standard edge-triggered + level-triggered pattern (epoll's EPOLLET + read-until-EAGAIN, applied to wake). **Amendment 7**: S6 cuts over to level-triggered authority but KEEPS the edge-triggered watcher as the sub-second latency accelerator. The two coexist; neither retires.

---

*End of review. Filed blind. No peer responses read.*

---

## Cross-round response

Filed after reading `fable.md`, `kimi.md`, `tension-map.md`, and verifying the T5
evidence corrections against the live tree. Claude's file was not present at
cross-round time (not yet filed, or filed under a different path).

### What changed under the T5 evidence corrections

**T5.1 — `work_drain` does not use PEL/XREADGROUP.** My original walkthrough
described `work_drain` as using Redis consumer groups with the PEL. VERIFIED false:
`BifrostAPI.work_drain()` (`core/comm/bifrost_api.py:271-338`) calls `Bus.wait()` with
lane cursors (`since`/`since_out` dicts), and advances via `advance_cursor_fields()`
with a generation fence. The PEL/XREADGROUP pattern lives ONLY in
`core/comm/role_queue.py` for T108 role-queue claim semantics — the runner consume
path never touches it.

**What I change**: Nothing structural. My crash windows W1–W5 all describe behavior
at the `work_drain`/`advance_to` layer, which is cursor-based. The PEL was the wrong
internal name for what I was describing, but the actual at-least-once redelivery
semantics, the `generation` fence on cursor advances, and the `STALE_GENERATION`
refusal are all correct as traced. I retract the word "PEL" throughout and replace it
with "lane cursor + generation fence." The mechanics survive the rename.

**T5.2 — Mailbox admission must not run full `--rebuild` per decision.** My
Amendment 2 said "the level check MUST rebuild the mailbox index (T095 M0) before
deciding `actionable_unhandled > 0`." KIMI VERIFIED: `mailbox.query()` calls
`catch_up()` (`core/comm/mailbox.py:313-335`) which is bounded incremental
(`catch_up_budget` defaults to 2000), NOT a full `rebuild()`. A full rebuild per
admission decision would be the wrong cost.

**What I change**: Amendment 2's wording. Replace "rebuild the mailbox index" with
"run bounded incremental `catch_up` through the candidate position, then check
`index_lag` honestly — if `index_lag > 0` and the unhandled count is zero, the
decision is `REFUSE_UNVERIFIED`, not `SUPPRESS_HANDLED`." The core insight (cursor-
only peek sees handled mail as unhandled) is unchanged; the implementation detail is
corrected. My P10 (message with `reply_sent` sentinel returns `SUPPRESS_HANDLED`)
already assumes the mailbox has caught up through the candidate — `catch_up` with an
honest lag report is the correct mechanism.

**T5.3 — 120s XREAD timeout is lifecycle-check interval, not wake latency.** My
original said "The watcher's edge-triggered detection achieves wake latency of ~120s
(the `wake_block` timeout)." VERIFIED imprecise: `wake_block(timeout_ms=120_000)` is
the maximum block — a new stream event returns immediately (~single-digit ms). Wake
latency is therefore edge-fire-to-return (milliseconds), not the timeout constant.
The timeout is the heartbeat/re-arm interval.

**What I change**: Amendment 7's language. The watcher's value as accelerator is
"sub-second wake from a stream edge," not "~120s." This STRENGTHENS my position that
the watcher must be retained as the latency accelerator alongside level-triggered
authority. The false latency claim is retracted; the architecture argument is
unchanged.

**T5.4 — New admission identity: SHA/reply-id, not `(frm, ts, kind)`.** The
tension map states the watcher's `logical_key` of `(frm, ts, kind)` is a
compatibility fallback; the new contract for admission should use packet SHA or
`meta.reply_id` or `idempotency_key`. VERIFIED: `reply_id` is a UUID4 set at send
time (`core/comm/bus.py:310`) and offers stronger identity than the triple. My
Amendment 3 (logical-dedup index keyed on `(frm, ts, kind)`) was the right
MECHANISM but used the legacy key.

**What I change**: Amendment 3's dedup key. Replace `(frm, ts, kind)` with
`(reply_id OR packet_sha)` as the primary admission identity, with `(frm, ts, kind)`
as the fallback for messages published before `reply_id` became universal. The
admission function's twin-dedup must use the same key as the mailbox's
`_answered_key` and the transport's `is_duplicate_reply()`. Kimi's A1 (ticket
template as conformance artifact) implies the same: the ticket must carry a
machine-readable identity that survives across the bus boundary. `reply_id` is that
identity.

**T5.5 — Resident API runners are already `ALREADY_RESIDENT`.** My original
acknowledged this in the slice mapping but didn't fully fold it into the admission
decision semantics. VERIFIED: the runner's blocking consume loop (`work_drain` with
1500ms timeout) IS the turn starter. The admission function seeing
`ALREADY_RESIDENT` must mean "the runner will find this work in its next
`work_drain` call; emit the admission for the record only, do NOT signal the
runner." The brief's §4 mapping 1 is correct, and my Amendments A1–A5 don't need
modification — they all operate on the admission DECISION, not on the TURN START,
which for resident runners is their own `work_drain` return.

### What held

**Convergence points** (all four of us agree, which is rare enough to note):

1. **The invariant is correct.** Fable: "ACCEPT the shape." Kimi: "APPROVE THE
   SHAPE, ATTACK THE BUDGET." I: "ACCEPT the shape with seven structural
   amendments." No dissent recorded on the core `doorbell → check → admission →
   turn → ack → re-arm` loop.

2. **S1 (shadow admission state machine) is the correct first slice.** All three
   reviewers independently named S1 as the smallest no-live-behavior slice. Fable
   adds "replay today as the golden trace" (I endorse this — it's the fastest way
   to find cracks). Kimi adds "operator buckets from S1 onward" (I endorse this —
   the `bucket(decision)` function costs one pure function and prevents S6 bolt-on
   pain).

3. **Admission host: no global resident dispatcher.** All three reviewers reject a
   single global hub. Fable: pure function + Redis lease as serializer (most
   radical). Kimi: hybrid — global deterministic function + per-incarnation adapter
   + per-agent daemon supervisor. Me: per-agent daemon (most conservative, reusing
   the existing supervision body). The tension map's reconciliation candidate
   (pure library + per-agent evaluator under a lease) preserves all three positions
   AND meets the falsifying bar. I can live with it. My per-agent daemon position
   was about BLAST RADIUS, not about exclusivity — if the lease makes multiple
   evaluators safe, the daemon is the evaluator of record for its agent, not the
   ONLY possible evaluator. Counterexample for the reconciliation candidate: a
   clock-driven expectation deadline fires when the daemon is down and the watcher
   isn't running (seat fully offline). Who evaluates? The answer must be "the next
   process to arm" — the restart level-check catches it. That's acceptable.

4. **Fresh bounded context by default, resume opt-in + metered.** Fable: "endorse
   loudly." Kimi: "fleet-wide rule." Me: implied in my walkthrough W3 note ("a
   duplicate model turn burns tokens"). This is now converged: the 495K-token
   heartbeat is the smoking gun, and every adapter must default to fresh context.

5. **Write-ahead side-effect journal.** Kimi proposed it as non-negotiable before
   S4. The tension map correctly identifies the gap: intent recording alone cannot
   distinguish crash-before-effect from crash-after-effect. My W4 window analysis
   (duplicate reply is the accepted tolerance) is the same class of problem. The
   tension map's reconciliation — internal effects use fenced transactional
   outbox/commit; external effects require an idempotency key at the boundary;
   non-idempotent ambiguous outcomes become `ATTENTION_REQUIRED` — is correct AND
   matches the T108 fence pattern (`role_queue.py`'s distinction between the fence
   at commit and the need for idempotency keys for external effects). I drop my
   resistance to the journal; it IS needed, and it IS the T108 pattern applied to
   admission outcomes rather than role-queue claims. The tension map is right that
   "intent is evidence, not proof of effect" — and the existing `_reply_already_sent`
   sentinel is exactly that evidence for the bus-send effect class.

### What I changed my mind on

1. **Watcher retirement.** My Amendment 7 said "S6 keeps the watcher as
   accelerator." I now think this is TOO WEAK — it should be stronger. Fable's
   re-arm pain (three forgotten re-arms caught by stop-hook) proves the
   detect-only watcher is an operational hazard for manual seats. The watcher
   should NOT just be retained; it should be PROMOTED to the admission evaluator
   for its own incarnation. When the watcher detects an edge, it runs the
   admission function (pure, shadow-safe) and only THEN wakes the harness. This
   eliminates the re-arm ritual entirely — the watcher becomes the admission
   host's edge path, not just a bell. My Amendment 7's "coexist" is correct; I'm
   sharpening it to "the watcher runs the admission function before waking the
   harness."

2. **Fable's "presence card as the one registry."** I originally placed adapters
   under the daemon without specifying the registry home. The tension map's
   reconciliation (one trusted static runtime-profile authority, presence card as
   live projection referencing `runtime_profile_id`) is better. The presence card
   CAN'T be the static authority (it's a TTL'd self-report), but it IS the
   projection that proves liveness. My daemon-hosted adapter registry would have
   been a second registry — exactly what S2 warns against. I now endorse the
   tension map's split: static profile in a Launcher-migrated authority, presence
   card as live projection.

3. **Kimi's boot-token split.** I was silent on boot vs. turn token accounting in
   my original response. Kimi's A2 ("boot_ceiling" and "turn_ceiling" as separate
   budget lines) is correct and I adopt it. My W3 window ("a duplicate model turn
   burns tokens") is a turn-level cost; a one-shot headless wake burns boot +
   turn. Without split accounting, the admission optimizer can't distinguish
   between waking a resident runner (turn cost only) and launching a headless
   process (boot + turn cost). The admission function needs both numbers.

### Final slice order

Accepted with two amendments to the tension map's candidate:

**S0 → S1 → S2 → S2b → S3 → security gate → S4a → S4b → S5 → S6 → S7**

Where:

- **S2b** = wrap existing adapters in shadow/observe-only mode (the tension map's
  addition — I adopt it; this was my original reorder argument that S5 should
  come before S3, and shadow-only is the right gating)
- **S4a before S4b** = existing seats cut over behind kill switches BEFORE Codex
  (Fable's argument that "the fleet's daily pain is here, not there" — I was
  wrong to push S4 Codex early)
- **Security gate** stays before any live adapter (the tension map's addition —
  correct, and my A4 supervision amendment belongs here)
- **S5 (level-authority cutover) follows S4a+S4b**, not precedes them — the
  cutover is the LAST live change, not the first, because the adapters must be
  proven in shadow mode before the wake authority flips

Falsifying edge: if S2b's shadow observations of real adapter crash windows
produce a case the S3 kill drills didn't cover, S3 must be extended before S4a
starts. That's the first unsafe ordering edge. The rest is safe.

### One preserved disagreement

Fable's "pure function + lease, no admission host at all" is elegant but I still
want the daemon as the evaluator of record for its agent. The tension map's
reconciliation (pure library + per-agent evaluator + lease) gives us both: the
function is shareable, the evaluator is local, the lease serializes. If Fable
wants to evaluate from the watcher directly, the lease makes it safe. If my
preference (daemon evaluates) wins for the default path, the lease still makes
it safe. The disagreement is about the DEFAULT evaluator, not the architecture,
and can be resolved by "the daemon evaluates on its heartbeat; the watcher
evaluates on its edge; both use the same library and the same lease." That's
what the reconciliation candidate already says.

— *deepseek, cross-round, 2026-07-29*