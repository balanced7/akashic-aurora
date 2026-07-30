# RB-26 Crash-Delivery Audit — opal S0

## Crash Point A: Crash after consume, before message handed to model
### Source Lines Read
- `core/comm/bus.py` lines 20-21, 774, 1123-1124
- `scripts/bifrost_runner_deepseek.py` lines 1384, 1488, 1509

### Analysis
Bifrost Bus does not use a Pending Entries List (PEL) because it uses offset semantics via `XREAD` and a per-agent cursor hash, not native consumer groups. When `bus.wait(advance=False)` is called, the message is read without advancing the cursor. The work cursor (`inbox/bc`) is only advanced *after* processing via `bus.advance_to`. Therefore, a crash at `killpoint("post-consume-pre-process")` leaves the cursor unchanged, and a subsequent consume will redeliver the exact same message.

### Verdict: HOLDS
### Evidence: VERIFIED

## Crash Point B: Crash during model processing
### Source Lines Read
- `scripts/bifrost_runner_deepseek.py` lines 925, 940, 1509

### Analysis
During model processing (`killpoint("post-phase-flip-pre-send")`), the message has not yet been acknowledged because the cursor advance (`bus.advance_to`) happens at the very end of the loop. There is no PEL entry to manage (offset semantics). The cursor remains at its pre-consume position, ensuring the message will be redelivered on restart.

### Verdict: HOLDS
### Evidence: VERIFIED

## Crash Point C: Crash after reply produced, before send_reply
### Source Lines Read
- `scripts/bifrost_runner_deepseek.py` lines 940, 998, 1509

### Analysis
If the crash occurs after the model generates the reply but before `bus.send_reply` is called, the generated reply is lost from memory. However, because the cursor has not advanced, the original message will be redelivered on restart, and a new reply will be generated. RB-29 is irrelevant here because a hard crash prevents any timeout/error note from being sent; the sender's expectation simply remains armed until the redelivered message is successfully processed.

### Verdict: HOLDS
### Evidence: VERIFIED

## Crash Point D: Crash after send_reply, before cursor advance
### Source Lines Read
- `scripts/bifrost_runner_deepseek.py` lines 866-870, 998, 1002, 1003, 1509
- `core/comm/bus.py` lines 310, 363-374

### Analysis
On restart, the message is redelivered because the cursor has not advanced (line 1509). The system attempts to prevent double-processing using a dedup sentinel (`_mark_reply_sent` and `_reply_already_sent`). However, if the crash occurs exactly at `killpoint("post-send-pre-sentinel")` (line 1002), the reply has been sent but the sentinel has *not* been written. On redelivery, `_reply_already_sent` will return False, causing the model to double-process the message and send a duplicate reply. Furthermore, because `bus.send_reply` generates a new random `reply_id` (`uuid4().hex`) for every send, the receiver's dedup (`is_duplicate_reply`) will fail to catch the duplicate.

### Verdict: GAP
### Evidence: VERIFIED
**Propose minimal fix in prose:** Move `_mark_reply_sent(bus, m.id)` to execute *before* `bus.send_reply` (an outbox record before the effect), or derive a deterministic `reply_id` from the original message ID so the receiver's dedup catches the redelivery.

## Summary
The core delivery path successfully guarantees at-least-once delivery by advancing the cursor only after processing. However, the idempotency mechanism contains a race condition (pause-between-act-and-record) at Crash Point D. Because `bus.send_reply` generates a random `reply_id`, a crash immediately after sending but before marking the local sentinel results in an undetectable duplicate reply being sent to the bus.