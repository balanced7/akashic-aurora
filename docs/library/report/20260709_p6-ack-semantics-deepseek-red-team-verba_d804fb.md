---
akashic_id: art_20260709_p6-ack-semantics-deepseek-red-team-verba_d804fb
akashic_sha: e3d9f6621bc8
status: draft
type: report
date: 2026-07-09
title: P6 ack semantics -- DeepSeek red-team (verbatim)
gist: "# P6 ack semantics -- DeepSeek red-team (verbatim) T026 seat: C4 author red-teams the build spec. --- Now I have the full picture. Here's th"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:56:52"
updated: "2026-07-09T23:56:52"
---
<!-- GENERATED PROJECTION of art_20260709_p6-ack-semantics-deepseek-red-team-verba_d804fb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# P6 ack semantics -- DeepSeek red-team (verbatim)

# P6 ack semantics -- DeepSeek red-team (verbatim)

T026 seat: C4 author red-teams the build spec.

---

Now I have the full picture. Here's the red-team:

---

## T026 / P6 Seat: ACK SEMANTICS RED-TEAM

### 1. AUTO-ACK BOUNDARY: reply-sent as the handled bar — right?

**The bar is correct but the edges are sharp.** A dispatched reply IS the strongest signal that the message was handled — the agent read it, reasoned, and produced an answer. But three cases challenge "reply-sent = handled":

- **Refusal / cannot-do:** A reply that says "I cannot do this" IS handling — the agent received, understood, and responded with its capabilities. That's a legitimate outcome. The bar should be "a real reply was dispatched" — refusal is a real reply. The only replies that should NOT count as handled are **error-bounce replies** (runner crashed mid-reply, sent an auto-generated `[error]` note at line 470–476). The distinction: if `out` starts with `(deepseek runner error:` or `(deepseek runner timed out` — those are NOT handling; everything else is.

- **Bounce-reprompt path (T018, the promise problem):** The runner's FIRST reply ends as a promise ("Let me fold this into..."), then the reprompt worker extracts the deliverable. With reply-sent as the bar, the FIRST reply (the promise) would auto-ack — leaving the handoff marked "handled" when only a promise was delivered. **Fix:** the runner must NOT ack on the first reply if the reprompt path is taken; ack only on the FINAL reply after reprompts are exhausted. The promise detector already exists in the runner's reply path — gate the ack behind it.

- **Broadcast handoff answered by broadcast:** If a `kind=handoff, to=*` is sent, and deepseek answers by broadcast (`bus.broadcast("reply", out)` at line 357), who acked? The sender gets the reply (broadcast reaches them), but every other recipient also got the handoff and never answered. **One ack per respondent, not one per recipient.** Broadcast acks should be gated: only runners that actually produced a reply ack. The sender's expectation is "someone handled this" — a single ack (from any respondent) satisfies that. The UNHANDLED flag should clear as soon as ANY ack lands on a broadcast.

### 2. WHO MAY ACK: only the addressee?

**Addressee-primary, but delegate-ack is a real pattern.** Claude acks a handoff sent TO deepseek when claude handles it on deepseek's behalf — this is called "I handled this for them." That's legitimate and should be allowed, but with a crucial rule: **the ack event MUST record `by` (who acked), `for` (who it was addressed to), and `on_behalf` (True when ack-by ≠ addressee).** Without recording `for`, a delegate-ack could mask that the actual addressee never saw it.

**Multiple acks per message: allow, last-wins for the flag.** "Handled" is a settled state — once any legitimate ack exists, the flag is clear. But multiple acks are useful forensically: if alice sends a broadcast handoff, bob and carol both answer — two acks let `promoted()` show "handled by bob AND carol." The UNHANDLED flag flips off on the FIRST ack; subsequent acks are recording-only.

**Constraint:** an agent should NOT ack its own message (self-ack = meaningless). The ack promoter must enforce `ack.by != msg.frm`.

### 3. UNHANDLED FLAG: 6h default sane?

**6h works for the current fleet rhythm but has two gaps:**

- **Broadcasts age differently than directed.** A directed handoff with a clear addressee should have a shorter UNHANDLED window — 2h is enough for the fleet's cadence (runners operate in minutes, not hours). A broadcast handoff has ambiguous ownership, so the longer 6h window makes sense. **Split the default: 2h for directed, 6h for broadcast.**

- **DONE-ledger correlation should auto-suppress.** If a handoff was about T016 and the ledger shows T016 is now `done`, the handoff is implicitly handled — the work got done, possibly without a runner ever sending a reply to that specific message. The UNHANDLED flag should check: does ANY ledger task referenced in the handoff content now have status `done` or `abandoned`? If yes → suppress the flag. This catches the case where the handoff triggered work that completed through a different channel (the human closed the task, another agent did it without the bus, etc.).

**Stale threshold tuning:** The flag applies to `kind=handoff` messages primarily — `decision`/`completion`/`blocker` are informative, not asks. An unhandled `blocker` at 6h is a genuine alarm; an unhandled `completion` at 6h is noise. **Only flag `handoff` and `blocker` as UNHANDLED; `decision`/`completion` are fire-and-forget.**

### 4. What the four live incidents demand that acks would still MISS

- **Eaten reply (zombie watcher):** A stale `bifrost_wake` process consumed the reply from deepseek's inbox before the real consumer saw it. Acks don't help here — the reply WAS dispatched (the runner would have acked), but the consumer never saw it. **Acks prove sending, not receipt.** Fix: the watcher-detection guard (T017) is the defense; acks are orthogonal.

- **Eaten reply (backlog skip):** The runner's startup drain advanced the cursor past multiple queued messages but only answered the oldest. The runner would ack the one it answered — but the skipped messages remain silently unhandled. **Acks per-message expose this:** if 3 handoffs landed and only 1 was acked, the other 2 are visible as UNHANDLED. Without per-message acks, the silence is invisible.

- **Drain-swallowed spec (pipe freeze):** The runner froze mid-task (stdout pipe full), never produced a reply. No ack was sent — the message correctly shows UNHANDLED. Acks work here: the absence of an ack is the signal. **But the flag alone doesn't tell you WHY it's unhandled** (pipe freeze vs. agent offline vs. loop-guard). The UNHANDLED flag should link to the runner's last known state (from `liveness.py:worklive`) — "last seen: handling, then went dark" tells a different story than "never picked up."

- **Re-wake loop (consume-then-arm):** The watcher re-fired on the same message because the cursor wasn't advanced. This is a consumption bug, not an ack bug. But the loop could generate duplicate acks if the runner answered the same message twice. **Idempotent ack:** the promoter must enforce `(msg_id, ack_by)` uniqueness — a second ack for the same message from the same agent is a no-op (logged, not duplicated).
