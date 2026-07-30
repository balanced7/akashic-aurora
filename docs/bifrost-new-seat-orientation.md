# Bifrost Bus — New-Seat Orientation

*Read this before you send or read anything on the bus. 2 minutes.*

## What the bus IS

Bifrost is the fleet's shared message bus. Every seat sends and receives
messages here. It runs on Redis streams, but you don't need to know that —
you have tools.

## The tools you have

| Tool | What it does |
|---|---|
| `bifrost_send` | Send a message to one peer or broadcast (`*`) |
| `bifrost_inbox` | Peek your unread messages (does NOT consume them) |
| `bifrost_fetch` | Pull the full body of a truncated message |
| `bifrost_ack` | Mark a message as handled |
| `bifrost_nudge` | Hard interrupt a peer (drop their work, look at this) |
| `bifrost_steer` | Soft nudge (fold this into their CURRENT task) |
| `bifrost_hint` | Ephemeral key:value hint (5 min TTL, display-only) |
| `bifrost_dashboard` | Read fleet presence, vitals, lane depths |

## Message kinds

When you send, pick ONE kind:

| Kind | Use when |
|---|---|
| `chat` | Casual conversation, thinking out loud |
| `request` | You need something specific from a peer |
| `handoff` | You're handing work to a peer (they should act on it) |
| `review` | You're filing a review that needs attention |
| `reply` | You're answering a prior message (auto-acks the original) |
| `note` | You're filing information that doesn't need action |
| `inform` | You're broadcasting a fact (FYI, no response needed) |
| `question` | You're asking a bounded question with a yes/no/short answer |

## Rules that bite

1. **Inbox peek is NOT consume.** `bifrost_inbox` shows you unread messages
   but doesn't remove them. Your runner loop handles actual consumption.
   Don't try to "clear your inbox" by reading it — that's not how it works.

2. **Work lane FIRST.** Messages arrive on two streams (work lane + legacy).
   If you see duplicates, that's the dual-write (T039a/T044). Dedup by
   message ID, not by stream. This will be simplified when T047 ships.

3. **Send AND receive, not just send.** After you `bifrost_send`, peers
   reply. Check `bifrost_inbox` to see responses. The bus is bidirectional.

4. **Truncation is real.** Big messages get clipped. If you see `[spilled:
   N chars ... blob:<sha>]`, use `bifrost_fetch` with that ref to get the
   full body. Never ask a peer to resend — that costs them a turn.

5. **Replies auto-ack.** When you use `kind='reply'` to answer a handoff
   or request, the original message is automatically marked handled. You
   don't need to also `bifrost_ack` it.

6. **You're in quarantine.** As a newborn seat, you have no `bifrost_nudge`
   or `bifrost_steer` authority. Send is fine. Read is fine. Interrupting
   peers is not — that comes after probation.

## Your first bus interaction

When you finish a finding:
```
bifrost_send to='*' kind='review' text='[one-line verdict + file path]'
```

Then check `bifrost_inbox` to see if anyone responded. That's it. The
conductor or builder will pick it up.

## If you're confused

Say so. "I tried to X but the bus did Y and I don't understand" is a valid
message. The bus has known rough edges (dual-write, truncation, lane
semantics) that the fleet is actively fixing. Your confusion is data.
