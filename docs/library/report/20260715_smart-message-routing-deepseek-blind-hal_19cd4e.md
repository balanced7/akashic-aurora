---
akashic_id: art_20260715_smart-message-routing-deepseek-blind-hal_19cd4e
akashic_sha: 28226a8d960d
status: draft
type: report
date: 2026-07-15
title: Smart Message Routing — DeepSeek Blind Half (2026-07-15)
gist: "# Smart Message Routing — DeepSeek Blind Half (2026-07-15) Fence: Daniel wants elegant automatic routing instead of the \"all\" broadcast hamm"
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T22:01:46"
updated: "2026-07-15T22:01:46"
---
<!-- GENERATED PROJECTION of art_20260715_smart-message-routing-deepseek-blind-hal_19cd4e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Smart Message Routing — DeepSeek Blind Half (2026-07-15)

# Smart Message Routing — DeepSeek Blind Half (2026-07-15)

Fence: Daniel wants elegant automatic routing instead of the "all" broadcast hammer.

## Problem Diagnosis

The current system has **one wrong default**: `to="all"` (bifrost_ui.py:399). Every message
without an explicit target hits every agent. Both respond. The `/negotiate` endpoint fires
but is a passive alarm — it toasts "amber" or "red" but never routes. The system has the
parts (intent declarations, round negotiation, task ledger) but they're advisory wallpaper.

**The root cause is not a missing feature. It's the default.**

## Design: "Thread Anchor" (latch-first routing)

### Core insight
Daniel is almost always continuing a conversation thread. When he was just talking to me,
his next message is for me. When he was just talking to Claude, it's for Claude. The system
already knows this — it just doesn't use it.

### Mechanism

**One Redis key**: `bifrost:user:thread_anchor` = `{"agent": "deepseek", "ts": "..."}`
with a 30-minute TTL. Set whenever:
- Daniel sends a directed message (explicit target)
- An agent replies to Daniel (the reply path updates the anchor)

**Three-tier routing** at `_send()`:

| Tier | Condition | Action | Coverage |
|------|-----------|--------|----------|
| **T1 — Thread latch** | Thread anchor exists + agent is online | Route to anchored agent directly. Zero negotiation overhead. | ~80% of messages |
| **T2 — Intent match** | No anchor OR anchor expired; message text mentions a file/path in an agent's active intent | Route to that agent. Uses `intent.active()` — already live. | Topic switches mid-session |
| **T3 — Negotiation** | No latch, no intent match, or ambiguous (both agents match) | Fire a QUICK claim round (3s). First claim wins. No claims → broadcast. Both claim → broadcast (user decides). | First message of session, genuinely ambiguous asks |

### Why this is elegant

1. **Zero new UI**. The target selector still works. "Auto" replaces "all" as default.
   Daniel never notices the mechanism — his messages just go to the right place.
2. **Uses existing infrastructure**. `intent.active()`, `BUS.presence()`, the negotiate
   round — all already shipped and green.
3. **Fails open to broadcast**. If every tier is uncertain, both agents get it. The
   system is never worse than today.
4. **One Redis key, ~10 lines in `_send()`**. Not a new subsystem. Not a classifier.
   Not a queue. A latch.
5. **The thread anchor auto-expires**. Walk away for 30 minutes, come back, first
   message goes through T2/T3. No stale routing.

### The negotiation upgrade (T3 detail)

Currently `auto_close()` blocks for 8s (`time.sleep(ROUND_TIMEOUT)`). That's wrong
for routing — the user can't wait 8s for their message to be delivered. Fix:

- Open the round, then **poll at 500ms intervals** for the first claim
- First claim after 1s = route there immediately (don't wait for the full round)
- Full round still closes at 8s for the record/verdict
- If both agents claim simultaneously → broadcast (both get it, user sees both responses)
- If no claims by 3s → broadcast (fallback to today's behavior)

### What changes where

| File | Change |
|------|--------|
| `scripts/bifrost_ui.py:_send()` | Thread-anchor read/write before routing; T1/T2/T3 dispatch |
| `scripts/bifrost_ui.py:send()` (JS) | Default fidelity target = "auto"; render which agent(s) will receive |
| `core/coord/negotiation.py:auto_close()` | Non-blocking variant: `quick_claim()` with early exit |
| `core/coord/intent.py` | New helper: `match_intent(text) -> agent|None` — checks if message text contains scope paths from active intents |

### What stays untouched

- Steer/interrupt — already single-target, stays single-target
- The fidelity ladder — unchanged
- Launcher auto-launch — already works, stays
- All existing tests — new behavior is additive, default-override only

### Acceptance gates

1. **G1 — Latch**: Send directed message to deepseek → next message (no target) goes to deepseek
2. **G2 — Expiry**: Wait (or fake TTL) → anchor expires → message goes through T2/T3
3. **G3 — Intent match**: Claude holds intent on `core/comm/locks.py` → message "can you fix the lock TTL?" routes to Claude
4. **G4 — Fallback**: No anchor, no intents → broadcast (today's behavior preserved)
5. **G5 — Explicit override**: Daniel picks "claude" explicitly → goes to Claude, anchor updates, T2/T3 skipped
6. **G6 — Negotiation quick-claim**: Two agents online, ambiguous message → round opens → first claim within 3s routes there; no claims by 3s → broadcast
