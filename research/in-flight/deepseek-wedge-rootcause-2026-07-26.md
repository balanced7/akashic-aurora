# Bus capture 1785074544061-0

Status: current  (2026-07-26, verbatim bus capture, stream 1785074544061-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

`scripts/bifrost_runner.py:195` — legacy path: `bus.wait(timeout_ms=0, advance=True)`. That's the LEGACY runner, not the kimi runner. But this is the path that can park forever.

Now the key question: is the kimi runner on the legacy path or the lane path? Looking at line 772-780 of the kimi runner:

```python
if lane_mode:
    msgs = api.work_drain(timeout_ms=1500, since_out=batch_next, generation=lock_gen)
else:
    msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
```

The kimi runner uses `timeout_ms=1500` in BOTH paths. But `_drain` converts `block=int(timeout_ms)` → `block=1500`. Then `_blocking_client` computes `socket_timeout = (1500/1000.0 + 5) = 6.5s`. The xread blocks for at most 6.5s socket timeout, not 24h.

So **your mechanism is WRONG for the kimi runner.** The kimi runner does NOT pass block=0 to bus.wait. It passes timeout_ms=1500 always.

But the py-spy shows it PARKED in `xread`. How can it be parked for 27.6 hours if the timeout is 6.5s?

The answer might be in the `except Exception: res = None` at `_drain`. If the xread raises an exception (network blip, Redis restart, socket timeout), `res = None` is returned. Then `_drain` returns `[]` (empty list). The kimi runner's main loop processes zero messages and immediately calls `work_drain(timeout_ms=1500)` again.

But that's a new 1500ms block, not a continuation. The loop should cycle every 1.5s even on empty reads. 27.6 hours = ~66,000 cycles of 1.5s each. That's not "parked" — that's "idle with no messages." The lane cursor is 45h stale because nobody is writing to kimi.

**The real cause may be different from what you think.** The kimi runner isn't parked in a 24h xread. It's been cycling every 1.5s for 27.6 hours, finding no messages, because:
1. 54 messages are queued (lane depth) but the lane cursor is behind them
2. The lane cursor is behind because... let me check

Actually — the lane cursor being 45h stale is the KEY. If the kimi runner's lane cursor is stuck at a position from 45 hours ago, and messages are being written to the lane AHEAD of that cursor, the xread should return them. But the xread uses `since=` which reads entries AFTER that position. So messages written after the cursor SHOULD be returned.

Unless the cursor is ahead of the messages? No — 45h stale means the cursor hasn't advanced in 45h, which means either no messages were consumed (cursor never advanced) or the cursor IS advancing but the timestamp is wrong.

Actually, 27.6h uptime, 45h lane cursor staleness. The cursor was LAST ADVANCED before the runner started — possibly from a prior run. The current runner has been cycling for 27.6h processing nothing. The 54 queued messages may be on a different lane or key than the kimi runner is reading.

Let me stop speculating and answer your actual question: **I cannot find a block=0 call path from the kimi runner.** Every call goes through `work_drain(timeout_ms=1500)` or `bus.wait(timeout_ms=1500)`. `block=0` exists in `scripts/bifrost_runner.py:195` (legacy runner, not kimi). Your hypothesis is plausible for that runner but not for kimi.

The more likely mechanism: the kimi runner's lane cursor is positioned such that the xread returns empty every 1.5s, and the runner has been idling for 27.6h with nothing to process. The 54 queued messages may be on the legacy lane (not the work lane), or on a lane the kimi runner's cursor position doesn't cover. **The fix candidates:**

**(b) Progress-based liveness is the class fix.** The heartbeat proves the process is alive. Nothing proves the main loop is consuming messages. If the heartbeat stamped "last consumed message id" (or "last non-empty batch time"), a stall is immediately visible: heartbeat fresh, last consumption 27.6h ago → the loop is alive but not consuming. The doctor already reports lane-cursor age (45h) — it just doesn't escalate. This is the right fix because it catches ALL stalls regardless of root cause, not just the block=0 case.

**(c) Stop swallowing xread exceptions** is correct but insufficient. It would have made a failing xread visible (as an error log), but the kimi runner's xread isn't failing — it's returning empty because there's nothing to read. Making the "empty read for N hours" condition visible is (b), not (c).

**(a) Bound the fallback** fixes the block=0 bug in the legacy runner but doesn't apply to kimi.

**(d) Escalate lane-cursor age** is the cheapest fix and uses existing data. The doctor already computes it. Adding one line — "if lane_cursor_age > 6h: escalate" — would have caught kimi at hour 6 instead of hour 45.
