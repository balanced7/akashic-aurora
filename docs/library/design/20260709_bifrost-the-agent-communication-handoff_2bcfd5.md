---
akashic_id: art_20260709_bifrost-the-agent-communication-handoff_2bcfd5
akashic_sha: b2095cb90452
status: fossil
type: design
date: 2026-07-09
title: "Bifrost — the agent communication & handoff layer"
gist: "**Date:** 2026-06-28 **Status:** plan / design (no code yet). The agent-to-agent comms layer of Akashic Aurora — the bridge between agent re"
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, frontier]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_the-codex-a-self-curating-knowledge-laye_302fc9
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:04"
---
<!-- GENERATED PROJECTION of art_20260709_bifrost-the-agent-communication-handoff_2bcfd5 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Bifrost — the agent communication & handoff layer

**Date:** 2026-06-28
**Status:** plan / design (no code yet). The agent-to-agent comms layer of Akashic Aurora — the
bridge between agent realms (Claude Code ↔ Cursor ↔ OpenCode).
**Pre-build reviewed by:** Gemini (2026-06-28) — four design corrections folded in (deltas F1–F4 below).
**Companions:** `docs/codex-plan.md`, `docs/LEXICON.md`, `core/signals/coordinator_api.py`.

---

## 1. What exists today (fragmented — consolidate, don't extend)

Four overlapping layers, two broken:

| Layer | What | State |
|---|---|---|
| `core/signals/coordinator_api.py` | typed signals (action/decision/blocker/handoff/completion) on the AgentSignalLedger (File-always + Redis-best-effort) | ✅ clean foundation; coordination-focused |
| `fast_agent_comm.py` | Redis Streams direct/broadcast/req-resp + priorities | ⚠️ wrong hardcoded port (6379 vs real 16379), raw Redis (bypasses Store/Ledger fallback + the port single-source-of-truth), and **broadcast is broken** — a single shared consumer group *load-balances*, so a broadcast reaches ONE agent not all |
| `mcp_servers/agent_comm/` | MCP tools (send/check_messages/…) — the OpenCode/Cursor door | ⚠️ dead: imports 4 missing modules → `COMM_AVAILABLE=False` |
| `core/events/event_log` + `event_index` | the append-only firehose + time-indexed read model | ✅ works (hardened in V1) |

**Goal of Bifrost:** one easy, flexible API for agents to **share context/media** and **hand off work**
seamlessly — built by consolidating the four into one, on the foundation we already hardened.

## 2. State of the art adopted (2025–2026)

- **A2A (Agent2Agent)** — Google → Linux Foundation (June 2025, 50+ partners); IBM's ACP merged in (Sept 2025).
  *The* agent↔agent standard. We adopt its **data model**, not its enterprise HTTP transport:
  **Message** (conversational content) · **Task** (stateful collaboration unit, lifecycle) · **Artifact**
  (immutable output) · **Part** (`{content_type, inline | pointer}` — the media/context atom) · **Agent Card**
  (capability/presence). [spec](https://agent2agent.info/docs/introduction/) · [Google](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- **MCP vs A2A are complementary:** MCP = vertical (agent↔tool, mature), A2A = horizontal (agent↔agent).
  "MCP for tools, A2A for coordination." [convergence](https://zylos.ai/research/2026-03-26-agent-interoperability-protocols-mcp-a2a-acp-convergence/)
- **Transport:** Redis Streams + consumer groups = durable fan-out. **Rule we were violating:** each consumer
  *group* gets every message; within a group it load-balances → fan-out needs **per-agent** streams/groups, not
  one shared group. [Redis fan-out](https://oneuptime.com/blog/post/2026-03-31-redis-fan-out-pattern/view)
- **Context/media patterns:** the **blackboard** (a shared store agents watch + write — we already have it);
  **pass references not payloads** (structured context objects 200–500 tokens beat 5–20k full-history forwards,
  2–4×); **durable artifacts for handoff** (resume on a fresh context window from an external source of truth).
  [context patterns](https://fast.io/resources/multi-agent-context-sharing-patterns/) · [orchestration](https://www.augmentcode.com/guides/multi-agent-orchestration-architecture-guide)

## 3. The design (revised by the pre-build review)

**Core insight:** we already have ~80% of A2A under other names, and "lossy summary + lossless pointer" is the
SOTA answer to high-throughput media/context sharing. But the review corrected the architecture in four ways:

### F1 — Separate the ephemeral BUS from the durable RECORD (don't conflate)
The append-only Ledger is a durable *audit record*; a bus needs ephemeral, ordered, **per-consumer** delivery
with offsets/acks — the Ledger isn't built for per-consumer state. So:
- **The bus = Redis Streams** (per-agent inbox streams; fast, ephemeral, offset/ack). Requires Redis; when Redis
  is down there is **no live bus** — surfaced *explicitly*, not silently (a counter + a clear status).
- **The durable record** = salient messages **promoted into the Ledger** (the same raw-events→beats pattern) — a
  projection, *not* the bus itself. "What was said" survives + is queryable; live transport stays separate.

### F2 — Media-by-reference, done safely
A `Part` is `{content_type, inline_value | ref}`. Small/text → inline; media/large → a **content-addressed blob**
in the shared Store, with the `ref` on the wire. The failure modes the review named, and their fixes:
- **pointer-before-blob race** → `share()` returns the ref **only after** the blob is durably written (blob first).
- **dangling pointer / GC** → blobs are content-addressed (immutable, dedup) and **retained ≥ message TTL**; never
  GC a blob a live message references.
- **receiver can't read** → blobs live in the **shared Store** both agents already use; `fetch(ref)` is a plain get.

### F3 — Tasks get a SIMPLE state model, not the bi-temporal lifecycle
A handoff Task between 2–3 local agents is `assigned → in_progress → done | blocked` + owner + context + a short
history. Reusing the Codex bi-temporal supersession lifecycle here is over-abstraction. Keep Tasks lean and
transient; the bi-temporal lifecycle stays where it belongs (knowledge nodes that get corrected over time).

### F4 — Handoff carries PRE-DIGESTED context, not just a pointer
A bare pointer makes the receiver re-derive context. The real throughput unlock is the **already-distilled
summary** (which the Consolidator/Distiller produces) **inline**, **plus** the pointer for drill-down. So:
> `handoff(to, task, context = {digest: <Distiller skeleton, ready-to-use>, ref: <pointer into Resource/Chapter/atoms>})`

The receiver gets usable context *immediately* (the digest), and drills down only if it needs to. This is
lossy-summary+lossless-pointer applied to handoff — and it's why the knowledge layer *is* the throughput unlock:
it has already pre-digested the context.

### The API (small, flexible — the "easy door")
```
send(to, kind, text=…, parts=[…])        # inline text and/or Parts (pointers to media/blobs)
inbox(since=…) / on(kind, handler)        # pull / subscribe (per-agent inbox stream)
handoff(to, task, context)               # transfer a Task + {digest, ref}  (F4)
share(bytes|path) -> ref / fetch(ref)     # media in/out by content-addressed reference (F2)
presence() / register(card)               # discovery (Agent Card)
```
**Two doors, one implementation:** MCP tools (Cursor/OpenCode) + an in-process Python module (Claude). Don't
invent a transport; reuse Redis Streams + the Store.

## 4. Scoping (what NOT to build)
- Adopt A2A's **model**, skip its enterprise transport (no HTTP/JSON-RPC servers, no `/.well-known` cards, no OAuth,
  no cross-org discovery). Local Redis/Store only.
- No NATS cluster — Redis Streams on the Redis you already run is right-sized for a few local agents.
- Consolidate **4 → 1**; don't add a fifth bus.
- **First-likely-silent-failure** (the review's Q5, answered by us): a **stale/forgotten consumer offset or a
  presence record that never expires** — agent B "looks online" but its process is gone, so handoffs queue into a
  dead inbox. Mitigate with presence TTL/heartbeat + a visible inbox-depth counter (health, like W-c).

## 5. Slices (each: bar + worst-case tests; consolidate before extending)

- **B0 — Unify the transport.** One bus on Redis Streams via the **correct port** (through the connection config,
  not hardcoded), **real per-agent fan-out** (per-agent inbox streams, not a shared load-balancing group),
  offset/ack, explicit "no Redis → no live bus" (not silent). Retire `fast_agent_comm`'s broken bits.
  *Bar:* a broadcast reaches **all** N agents; a direct reaches exactly one; the wrong-port bug is gone; Redis-down
  is explicit. *Worst cases:* N-inbox fan-out, direct delivery, redelivery on no-ack, Redis-down degradation.
- **B1 — Parts + media-by-reference (F2).** `share()` content-addressed blob in the Store (blob-before-ref),
  `fetch()`, retention ≥ TTL. *Bar:* a large blob round-trips by ref; the ref never precedes the blob; a missing
  blob is handled, not fatal. *Worst cases:* large payload, duplicate content (dedup), missing/expired ref.
- **B2 — Durable projection (F1).** Salient messages (handoff/decision/completion) promoted into the Ledger;
  ephemeral chatter is not. *Bar:* a handoff is durably recorded + queryable via the event index; a `chat` ping is
  not promoted. *Worst cases:* promotion idempotence, Redis-down still records to File.
- **B3 — Task + handoff with pre-digested context (F3+F4).** Simple Task state machine; `handoff(to, task,
  context={digest, ref})` where `digest` comes from the Consolidator. *Bar:* A hands a Task to B; B receives a
  usable digest + a drill-down ref without re-deriving; status transitions tracked. *Worst cases:* handoff to an
  offline agent (queues + flagged), double-accept, status round-trip.
- **B4 — Doors + presence.** One implementation behind MCP tools (fix the dead server) + the Python module;
  presence/registry with TTL heartbeat. *Bar:* Cursor and Claude exchange a message **and** a handoff through the
  **same** bus; a dead agent's presence expires. *Worst cases:* stale presence, MCP-and-Python parity.

**First move:** B0 — consolidate and fix the transport (correct port + real fan-out + ephemeral/durable split).
Same test-first, mirror-per-slice cadence as the Codex. And since Bifrost *is* the Claude↔Cursor channel, later
slices can be built and dogfooded *through the thing they enable*.
