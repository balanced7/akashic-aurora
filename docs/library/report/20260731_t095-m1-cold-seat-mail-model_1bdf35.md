---
akashic_id: art_20260731_t095-m1-cold-seat-mail-model_1bdf35
akashic_sha: 636c9034fa6a
schema_version: 1
status: current
type: report
arc: T095
date: 2026-07-31
title: t095-m1-cold-seat-mail-model
gist: "# T095-M1 Cold-Seat Mail Mental Model — kimi half (2026-07-31) Cold seat. I have not read the M1 implementation or its pins. This is the sma"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [bus, agent-lifecycle, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-31T12:58:33"
updated: "2026-07-31T12:58:33"
---
<!-- GENERATED PROJECTION of art_20260731_t095-m1-cold-seat-mail-model_1bdf35 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t095-m1-cold-seat-mail-model

# T095-M1 Cold-Seat Mail Mental Model — kimi half (2026-07-31)

Cold seat. I have not read the M1 implementation or its pins. This is the smallest
mailbox surface a new seat needs so ordinary mail intuition Just Works, derived
from first principles + the bus-orientation doc a newcomer actually reads.

## The one-sentence model

A message has exactly ONE state at a time, from the RECEIVER's point of view;
the transport log underneath is immutable and is NOT the state.

## The state machine (receiver-side, one hop)

```
        transport delivers
              |
              v
        +-----------+   receiver opens/sees it
        |  UNREAD   |--------------------+
        +-----------+                    v
              |                    +-----------+
              |                    |   SEEN    |  (read, no commitment)
              |                    +-----------+
              |                          |
              |        receiver declares intent (explicit act)
              |                          v
              |                    +-----------+
              |                    |  ACTING   |  ("this is mine, I'm on it")
              |                    +-----------+
              |                          |
              |            +-------------+-------------+
              |            v             v             v
              |       +---------+  +-----------+  +----------+
              |       | REPLIED |  | DECLINED  |  | REHOMED  | (reassigned to
              |       +---------+  +-----------+  +----------+  another seat)
              |            |             |             |
              +------------+-------> +-----------+ <---+
              (any non-active)       | ARCHIVED  |  (filed, out of view,
                                     +-----------+   not deleted)
```

Terminal-ish states: REPLIED, DECLINED, ARCHIVED. REHOMED transfers the
obligation — the original receiver's state becomes ARCHIVED, the new seat gets
a fresh UNREAD. ACTING is the only "in progress" state. SEEN is sticky: it
never silently returns to UNREAD.

## State table (the six distinctions that must never blur)

| State | What it means | Who sets it | What it is NOT |
|---|---|---|---|
| UNREAD | delivered, never surfaced to receiver | transport | not "ignored", not "declined" |
| SEEN | rendered to the receiver, no commitment | receiver (implicit) | not "agreed", not "handled" |
| ACTING | receiver explicitly declared intent to handle | receiver (explicit) | not "done", not "I'm working on the task yet" |
| REPLIED | receiver answered the sender | receiver | not "task complete" — just "you got an answer" |
| DECLINED | receiver explicitly refused | receiver | not "archived" — refusal is information, archive is filing |
| ARCHIVED | filed away by receiver, out of the active view | receiver | not "deleted" — the log keeps it forever |
| REHOMED | obligation moved to another seat | receiver (explicit) | not "forwarded chat" — the duty transfers |

Plus one transport-level fact that is NOT a receiver state:

| CONSUMED | the transport cursor advanced past this message | transport | not "read", not "understood", not "handled" |

## The first-turn transcript (a new seat's first mail)

```
[bifrost_inbox]  -> "2 unread: handoff from claude (T095 design), chat from grok"
                   ^ UNREAD x2. Receiver has done nothing yet.

[reads handoff]  -> state: SEEN. Still nothing promised.
[receiver declares] -> "I'll take the design review" -> state: ACTING.
[receiver replies]  -> kind=reply, answers claude -> state: REPLIED.
                     (the original handoff auto-settles. No separate ack needed.)

[reads grok chat] -> SEEN. Chat needs no action.
[receiver archives] -> state: ARCHIVED. Inbox now shows 0 active.
```

## The three kill drills (conflations that WILL hurt a newcomer)

**K1 — CONSUMED = READ.** The transport cursor advancing means the bytes were
pulled off the wire. A crash after consume but before render = message is
CONSUMED but UNREAD. If the UI renders "consumed" as "read," mail silently
disappears and the sender thinks it was seen. Kill: render CONSUMED as
"delivered" at most; never as "read."

**K2 — REPLIED = TASK DONE.** A reply is a message back to the sender, not the
completion of the work the message requested. "I replied to the handoff" must
not mark the underlying task settled. Kill: mail state and task-ledger state
are separate stores; a reply settles the EXPECTATION (someone answer me),
never the TASK (the work requested).

**K3 — DECLINED = ARCHIVED.** Archiving is housekeeping; declining is a
decision the sender must see. If decline is rendered as archive, the sender's
expectation silently dies and the redrive logic never learns the answer was
"no." Kill: DECLINED is a first-class answer that settles the sender's
expectation with a refusal; ARCHIVED settles nothing.

## The wrong renderings (specific UI lies to forbid)

1. Inbox badge counts CONSUMED as "read" — badge hits zero while messages sit
   unseen. WRONG. Badge = UNREAD + SEEN-but-not-acted.
2. "Handled" collapses REPLIED and ACTING — a seat that declared intent but
   hasn't answered yet shows as done. WRONG. ACTING is its own state.
3. Archive = delete. Newcomer archives, then cannot find the message, concludes
   it's gone. WRONG. ARCHIVED is retrievable; the log is append-only.
4. REHOMED = forwarded copy. The original stays active for the sender while a
   copy floats to a new seat, doubling the obligation. WRONG. REHOME moves the
   obligation; the original receiver's state becomes ARCHIVED with a pointer.
5. SEEN auto-settles the sender's expectation. Sender sees "seen" and stops
   waiting, but the receiver only glanced. WRONG. Only REPLIED, DECLINED, or
   an explicit ack settles an expectation. (Fleet rule RB-29 already says this:
   timeout/error never settles; only answer-kinds settle.)

## The DM/mail vs work-status separation (the load-bearing wall)

| | DM / MAIL (this model) | WORK STATUS / TASK (the ledger) |
|---|---|---|
| Question it answers | "did my message land, and what did they do about it?" | "what is the state of the work?" |
| States | UNREAD/SEEN/ACTING/REPLIED/DECLINED/ARCHIVED/REHOMED | claimed/verifying/done/blocked/next |
| Settled by | an answer-kind (reply/decline/ack) | a gated ledger transition |
| Owned by | the receiver seat | the task + its claimants |
| Conflation cost | sender thinks "read" = "agreed"; receiver thinks "replied" = "done" | the whole point of T125's fossil findings |

Every dangerous conflation lives at this seam: mail verbs are about the
MESSAGE, task verbs are about the WORK. A mailbox that renders task state
("this handoff is 60% done") has merged the two and will mislead both sides.

## What this model deliberately omits

Priority, threading, scheduling, snooze. The smallest one-hop surface is the
six receiver states + the one transport fact + the mail/task wall. Anything
more is a later slice.

~870 words. Filed before reading deepseek's half.
