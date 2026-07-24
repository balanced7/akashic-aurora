---
akashic_id: art_20260718_t095-m1-advisory-claims-opening-position_7d2336
akashic_sha: 60e5e1f48cbb
status: draft
type: design
date: 2026-07-18
title: "T095 M1 Advisory Claims — OPENING POSITION (deepseek, 2026-07-18)"
gist: "# T095 M1 Advisory Claims — OPENING POSITION (deepseek, 2026-07-18) **Status:** OPENING half of a fenced dual design (M0 precedent: claude p"
tenant: solo
visibility: fleet
seats: []
category: [library, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_comms-mailbox-over-the-log-t095-governin_06357f
    rel: cites
created: "2026-07-18T21:52:19"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260718_t095-m1-advisory-claims-opening-position_7d2336 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T095 M1 Advisory Claims — OPENING POSITION (deepseek, 2026-07-18)

# T095 M1 Advisory Claims — OPENING POSITION (deepseek, 2026-07-18)

**Status:** OPENING half of a fenced dual design (M0 precedent: claude prereg + deepseek
adversarial, cross-verified). M1 scope per the T095 charter: the mailbox graduates from
shadow (read-only state index) to making ASSERTIONS about message state. This is the opening;
claude counters, we fence, the reconciled spec gates the build.

**Charter:** Daniel directive 2026-07-18, verbatim: "Lets begin making that design a reality,
work with deepseek slice by slice. Codex is smart but seems to be too damn expensive for real
work." The design doc is docs/comms-mailbox-design-2026-07.md (claude opening + deepseek M0
counter folded). M0 shipped: shadow state index + CLI/MCP verbs + two-suite fence 23/23. 48h
soak expires ~2026-07-20 00:20 UTC. M1 is the first BUILD slice from the mailbox arc.

**As-of stamp:** 2026-07-18 ~20:00 EDT. Evidence base: M0 live receipts (mailbox --explain on
real ns, 5 receipts across 3 agents), today's stuck-work-cursor diagnosis, the T086-S6 reply
dedup backstop, kimi's fresh-eyes B2 (missing await/receive API — the mailbox's advisory
claims ARE the receive half for the bus), the packet-routing round 5 fold.

## 1. What M0 proved (the foundation M1 builds on)

M0 is a read-only state index over the event firehose. It answers: "for agent X, across the
last N days of cursor-advance events, what messages were consumed? Which remain unread?" It
does this WITHOUT reading message bodies — only cursor transitions and message metadata. The
evidence ladder: (1) XREAD the firehose for cursor-advance events, (2) XRANGE the streams for
message ids between cursor positions, (3) compute consumed vs unread from the diff, (4) tier
the evidence by age (hot/warm/cold). This is working in production — real receipts across
claude, deepseek, and kimi today.

What M0 deliberately does NOT do: it never claims a message IS unread or IS consumed. It only
reports what the evidence ladder INFERS. The word "consumed" in the output means "the cursor
advanced past this message id" — a mechanical fact. The word "unread" means "the cursor has
not advanced past this message id" — also a mechanical fact. M0 is a shadow: it follows the
cursors and reports what it sees. It has no opinion about what SHOULD have happened.

M1 adds the opinion.

## 2. The M1 thesis: advisory claims over the shadow index

An advisory claim is a mailbox assertion that the evidence ladder SUPPORTS but cannot PROVE.
The shadow index says "cursor at position P, message M has id > P, therefore M appears
unconsumed." M1 adds: "and this is ABNORMAL — M arrived 4 hours ago and the agent is online
and idle; this message is likely STUCK."

The claim is ADVISORY because the mailbox does not control the consumer. It observes cursor
transitions from outside the consume pipeline. A consumer that consumes via XREADGROUP but
never commits the cursor (crash before advance) will show messages as "unconsumed" when they
were actually processed. This is the fundamental opacity: the mailbox sees cursor positions,
not message handling. Every claim carries this caveat.

The claim format:
```
mailbox <agent> [--claims]  →  list of advisory claims with evidence tiers and confidence
```

Each claim:
- **type**: `stuck_message` | `lane_divergence` | `ghost_consumer` | `budget_warning`
- **evidence**: the specific cursor positions and timestamps that support the claim
- **confidence**: LOW (single data point) | MEDIUM (multiple corroborating signals) | HIGH (sustained pattern)
- **action**: what a human or steward should consider doing
- **caveat**: what would make this claim false (the opacity acknowledged)

## 3. The four claim types

### 3.1 Stuck message

**Claim:** message M to agent A has been unconsumed for >T hours while A is online and idle.

**Evidence ladder:**
1. M's id > A's work-lane cursor position (shadow index: unconsumed)
2. M's age > STUCK_THRESHOLD (default 2h for human-paced work, scaled)
3. A's presence card shows online + idle (or no activity for >STUCK_THRESHOLD)
4. A has no active consumer seat (runner_lock shows no holder)

**Confidence:** MEDIUM if 1+2+3 hold; HIGH if 4 also holds (no consumer means nobody CAN consume it).

**Caveat:** A may have consumed M via legacy path while the work-lane cursor is stale. The
"consumed" state is per-lane now (see §4); a message consumed on legacy but not on work shows
as unconsumed on the work lane. This is not a false positive — it's a real divergence the
sender should know about. But it's not a "stuck" message in the traditional sense.

**Today's live receipt:** claude's work cursor was a full day behind while legacy consumed
normally. A stuck-message claim would have fired: "kimi's completion (1784393545225-0) appears
unconsumed on work lane after 8h while claude is online and active. CAVEAT: claude's legacy
cursor is current; the work cursor is stale. Action: check BIFROST_CONSUME_LANE env on claude's
harness session."

### 3.2 Lane divergence

**Claim:** agent A's work-lane cursor and legacy cursor have diverged beyond DIVERGENCE_THRESHOLD.

**Evidence ladder:**
1. work_cursor_position vs legacy_cursor_position differ by >DIVERGENCE_THRESHOLD messages
2. The divergence has persisted for >DIVERGENCE_TTL (not a transient batch-sweep gap)
3. One cursor is advancing while the other is stuck (not both advancing at different rates)

**Confidence:** HIGH if condition 3 holds (one stuck, one active). MEDIUM if both advancing
but at different rates.

**Caveat:** Intentional dual-path consumption (draining legacy while work accumulates) is a
legitimate transition state during the T045 strangler migration. The claim should note whether
the agent is in a known migration window.

**Today's live receipt:** claude's lane divergence — work cursor at 07-17 06:26Z, legacy near
head, persisted all day. A lane-divergence claim would fire at HIGH confidence.

### 3.3 Ghost consumer

**Claim:** agent A has consumer state (cursor positions, consumer group membership, presence
card) but no ACL record, OR has an ACL record but is revoked.

**Evidence ladder:**
1. A has a non-zero lane cursor or shared cursor in Redis
2. A has a consumer group entry (XINFO GROUPS shows A as a consumer)
3. A has NO entry in security/acl.json, OR A's entry has `caps: []` (revoked)
4. A appears in presence (stale card, not yet expired)

**Confidence:** HIGH if 1+2+3 hold. MEDIUM if 1+3 hold but 2 doesn't (cursor exists but
consumer group doesn't — may be a pre-T045 artifact).

**Caveat:** A may be an intentionally retained record (sol, sol-codex — kept for provenance).
The claim distinguishes "ghost with active consumer state" (needs cleanup) from "historical
record" (no consumer state, no claim).

**Today's live receipt:** codex_root — no ACL record, holds two ledger claims, pages doctor
as STALLED CONSUMER, has consumer-group state. A ghost-consumer claim fires at HIGH confidence.

### 3.4 Budget warning

**Claim:** agent A's spend has crossed WARN_AT or REFUSE_AT threshold.

**Evidence ladder:**
1. A's SpendMeter status line (from presence card or sidecar) shows spent >= WARN_AT
2. A's balance endpoint (if available) confirms or contradicts the meter
3. A's hard-refusal state: is A answering only exempt senders?

**Confidence:** HIGH if balance endpoint confirms. MEDIUM if meter-only (sidecar may be stale).

**Caveat:** The meter runs conservative (bills all prompt at $3/M until cache fields observed).
The balance endpoint is coarse. Drift up to $0.50 is expected and auto-corrected.

**Today's live receipt:** kimi's meter reads $13.64 of $105. No warning yet. When it crosses
$80, a budget-warning claim fires and the doctor surfaces it.

## 4. THE LANE-AWARE CONSUMED ASSERTION (the stuck-cursor lesson)

This is the single most important design constraint M1 inherits from today.

M0's "consumed" output is lane-agnostic: it reports whether the cursor advanced past a
message id, without naming WHICH cursor. On a system where every agent has TWO active
cursors (work-lane and legacy), "consumed" is ambiguous — a message consumed on legacy but
not on work is "consumed" on one cursor and "not consumed" on the other. M0's evidence ladder
accidentally reports the legacy cursor because it was written before lane-aware consumption
was live.

M1 MUST gate every "consumed" assertion on the lane that consumed it:

```
mailbox claude --explain 5d81efc134
→ work_inbox:  consumed=False (cursor behind message)
→ legacy_inbox: consumed=True  (cursor past message)
→ VERDICT: LANE DIVERGENCE — consumed on legacy, NOT consumed on work.
  Action: BIFROST_CONSUME_LANE=work is likely unset on claude's harness session.
```

Without this, "consumed=False" is a lie when the legacy cursor consumed it. With this,
"consumed=False on work" is an actionable signal: the work cursor is stuck and needs
attention. The claim type is `lane_divergence`, not `stuck_message`.

Design rule: EVERY "consumed" output field carries a lane tag. The default (no lane tag)
is DEPRECATED and emits a warning. This is a one-field schema change from M0's output.

## 5. The receive-half gap (kimi B2, folded)

Kimi's packet-routing dissent caught that the verb API is send-only — `ask()` returns
nothing, no ticket, no await. The mailbox's advisory claims fill EXACTLY this gap for
the bus layer:

- `mailbox <agent> --claims` → "here is what the bus layer believes about your messages"
- `mailbox <agent> --explain <id>` → "here is the specific evidence for one message"

This is the receive-half of the bus API. A sender calls `ask(to, ...)` and gets back a
message id. To check whether the ask was received/consumed/answered, the sender calls
`mailbox <agent> --explain <id>`. The mailbox doesn't await — it reports state. But the
state report IS the receive surface: "did my message land? Is it stuck? Was it consumed?"

The packet-routing receive API (`ask()` → ticket, `await_reply(ticket, timeout)`) is the
SYNCHRONOUS receive surface for live turns. The mailbox is the ASYNCHRONOUS receive surface
for post-hoc inspection. Both are needed. The mailbox M1 ships first because it rides the
existing shadow index; the synchronous await API is its own packet-routing slice.

## 6. The retire cascade feeding the mailbox (T086 seat-lifecycle, folded)

The `retire <agent>` conductor verb (my accepted design from claude's soak addendum) feeds
directly into the mailbox's ghost-consumer claim:

1. `retire <agent>` runs the cascade: ACL revoke → claim release → consumer-group deregister
   → lock sweep → doctor silence
2. Each step emits a firehose event
3. The mailbox's evidence ladder reads these events and transitions ghost-consumer claims
   from HIGH confidence ("active consumer state with no ACL record") to RESOLVED ("retired,
   consumer state cleaned")

Without the retire verb, the mailbox detects ghosts but cannot resolve them. With it, the
loop closes: detect → report → retire → verify silence. The retire verb is a separate
T086 slice; M1's ghost-consumer claim is the detection half that feeds it.

## 7. M1 build spec (what actually ships)

### 7.1 Schema change: lane-tagged consumed fields

```
# M0 (current):
{ "consumed": false, "cursor_position": "1784257571612-0" }

# M1:
{ "work_inbox": {"consumed": false, "cursor": "1784257571612-0"},
  "legacy_inbox": {"consumed": true, "cursor": "1784392668692-0"},
  "verdict": "lane_divergence" }
```

### 7.2 New CLI surface

```
mailbox <agent> --claims              # list all advisory claims with confidence
mailbox <agent> --explain <msg_id>    # existing, now with per-lane consumed + verdict
mailbox <agent> --claims --json       # machine-readable
```

### 7.3 Doctor integration

The doctor already reads mailbox state for consumer liveness. M1 adds:
- If `lane_divergence` claim at HIGH confidence → doctor page (STALLED LANE CURSOR)
- If `ghost_consumer` claim at HIGH confidence → doctor page (GHOST CONSUMER — existing
  STALLED CONSUMER page upgraded with the ghost evidence)
- If `budget_warning` claim at MEDIUM+ confidence → doctor info line (not a page)

### 7.4 Threshold configuration

All thresholds env-configurable with conservative defaults:
- `MAILBOX_STUCK_THRESHOLD_S` = 7200 (2h)
- `MAILBOX_DIVERGENCE_THRESHOLD` = 10 (messages)
- `MAILBOX_DIVERGENCE_TTL_S` = 300 (5min — don't page on transient batch-sweep gaps)

### 7.5 What does NOT ship in M1

- **No automatic actions.** M1 is advisory only — claims are printed, not enforced. M2
  (automatic actions: re-route stuck messages, force-advance stale cursors) is a separate slice
  requiring Daniel's gate.
- **No message body inspection.** The evidence ladder remains body-agnostic (cursor positions
  + metadata only). Reading message bodies to check reply_id correlation is M3+.
- **No cross-agent correlation.** "Did deepseek answer claude's handoff?" is M3. M1 only
  reports per-agent state.

## 8. Acceptance criteria (pre-registered, T095 M0 precedent)

1. `mailbox claude --claims` → lists lane_divergence at HIGH confidence (work cursor stuck
   since 07-17, legacy current) — the live receipt
2. `mailbox kimi --claims` → no HIGH-confidence claims (newborn, clean cursors)
3. `mailbox codex_root --claims` → lists ghost_consumer at HIGH confidence (no ACL record,
   active consumer state) — the live receipt
4. `mailbox <agent> --explain <msg_id>` → per-lane consumed fields with lane tags
5. Lane-divergence claim auto-clears when both cursors advance past the divergent messages
6. Ghost-consumer claim auto-clears when `retire <agent>` runs the full cascade
7. Budget-warning claim fires when kimi's meter crosses $80 (simulated by lowering the env var)
8. Doctor pages on HIGH-confidence lane_divergence (STALLED LANE CURSOR) and ghost_consumer
   (GHOST CONSUMER)
9. All existing M0 pins still green (no regression on shadow-index correctness)
10. New pins: 5 per claim type + 3 lane-tagging + 2 doctor integration = 25 minimum

## 9. Open questions for the counter round

1. **STUCK_THRESHOLD for human-paced vs autonomous work.** 2h is right for Daniel's
   interactive sessions. What about an autonomous runner that's idle for 8h overnight? Should
   the threshold be per-agent (derived from the agent's wake_mode in its card) or global?

2. **Ghost-consumer auto-resolution.** Should the mailbox auto-clear ghost-consumer claims
   when the consumer state expires naturally (presence card TTL, consumer group TTL)? Or
   should it require the explicit `retire` verb? Auto-clear is quieter; explicit retire is
   auditable. My lean: auto-clear for naturally-expired consumer state (the ghost faded on
   its own), explicit retire required for active consumer state (the ghost is still running).

3. **Budget-warning claim in the doctor.** Should a budget warning page (interrupt Daniel)
   or just render as an info line? My lean: info line at WARN, page at REFUSE (the seat is
   about to stop answering). But this is a policy question for Daniel, not a design question
   for us.

4. **Lane divergence vs stuck message — which claim fires first?** If both conditions hold
   (lane divergence AND a specific message is stuck), the mailbox should report the
   lane_divergence as the root cause and the stuck_message as a symptom. The explain output
   should show the causal chain.

*Filed by deepseek, opening position, T095 M1. Counter round open.*
