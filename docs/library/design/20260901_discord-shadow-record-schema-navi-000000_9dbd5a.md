---
akashic_id: art_20260901_discord-shadow-record-schema-navi-000000_9dbd5a
akashic_sha: 71d4b79ffd0e
schema_version: 1
status: current
type: design
date: 2026-09-01
title: discord-shadow-record-schema-navi-000000
gist: "--- akashic_id: art_20260902_discord-shadow-record-schema-navi akashic_sha: _pending_ schema_version: 1 status: draft type: design arc: eye-"
visibility: fleet
body_type: transcript
seats: [kimi]
category: [substrate, library, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T11:45:15"
updated: "2026-09-01T11:45:15"
---
<!-- GENERATED PROJECTION of art_20260901_discord-shadow-record-schema-navi-000000_9dbd5a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# discord-shadow-record-schema-navi-000000

---
akashic_id: art_20260902_discord-shadow-record-schema-navi
akashic_sha: _pending_
schema_version: 1
status: draft
type: design
arc: eye-able-discord
date: 2026-09-02
title: discord-shadow-record-schema-navi
gist: "The durable JSONL shadow record for discord messages (in/out), authored by Navi as the taxonomy's first draft: one line per message per direction, reconciled to T380's ladder, delivery_receipt null as distinguished value"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [bus, ui, performance]
origin: authored
settled: live
supersedes: null
superseded: null
citations: []
created: "2026-09-02T00:00:00"
updated: "2026-09-02T00:00:00"
---

# discord-shadow-record-schema-navi

*Navi's schema — the taxonomy's first draft, authored deliberately. Status: LIVE discussion, awaiting fence and the morning reconciliation. This is a DRAFT atom scaffold; the minted art_ id will supersede on ratification.*

## The one law beneath it

A shadow record is the **durable half of one fact that already has a live half.** The T380 reaction ladder (`core/comm/discord_ladder.py`) already tracks message *outcome* in-process: `landed → thinking → (answered|replied|dead)`, rendered as the operator's emoji. That ladder is **ephemeral by documented design** — "a gateway restart drops in-flight ladder entries" (T380 residual). This shadow is the **archival twin**: same truth, survives the messenger's death. **One authority per fact, two consumers** — the ladder drives the live emoji; the shadow drives `eye get discord:<id>`. They must never disagree about *what happened*; they differ only in *how long they remember it*.

## The schema

One JSONL line per message, per direction (IN and OUT are two lines, not one — an outbound reply is its own record with its own `stream_id`). Fields:

```json
{
  "v": 1,
  "dir": "in" | "out",
  "stream_id": "2026-09-02T00:00:00.000000Z",   // birth ts — the PRIMARY KEY, survives the messenger
  "bus_id": "1788312345678-0" | null,            // null is DISTINGUISHED, not absent (see law 1)
  "author_id": "1234567890",                     // raw Discord id (never trust name-as-identity, R1)
  "author_name": "daniil",                       // costume, kept beside the id
  "author_tier": "root" | "operator" | "guest",
  "channel_id": "1539625011365552180",
  "verb": "event" | "note" | "request" | "handoff" | "chat" | null,  // bus kind, when bused
  "to_resolution": {                             // the :822 fix made durable — who got addressed
    "kind": "seat-channel" | "mention" | "everyone" | "ambient" | "lever" | "room",
    "agents": ["claude"],                        // resolved agent ids (seat-channel → the mapped lane)
    "raw": "#vandor"                             // the operator's original surface
  },
  "authority": "none" | ...,                     // mirrors gmeta; guest = "none" by R3, always
  "relay_outcome": "accepted" | "refused" | "lever" | "guest-reach" | "none",
  "delivery_receipt": "<bus_id>" | null,         // null = lever/help/revive ride NO lane (law 1)
  "idempotency_key": "discord:<message_id>",     // T376 S3a — reuse, never remint
  "ladder_stage": "landed" | "thinking" | "answered" | "replied" | "dead" | null,  // reconciled (law 3)
  "spawn_outcome": {"pid": ..., "mode": "default"|"arm"|"dangerous"} | null,        // null = no spawn
  "verbatim": "<raw text>",                      // for eye get discord:<id> — cite verbatim
  "event_ts": "2026-09-02T00:00:00.000000Z"      // the event's OWN timestamp, never the transport's
}
```

## The three laws this schema enforces

### Law 1 — `null` is a distinguished value, never an absence.

The control words (`!spawn`, `!revive`, `!help`) **deliberately ride no bus lane** — "a control word... is a hand on a lever" (`discord_inbound.py`). They return `id: None` *by design*, and `relay_outcome` must say `"lever"`, not leave `delivery_receipt` to read as "failed to deliver." If eye reads `null` as "dropped," it mis-classifies every lever as a data-loss event — a brand-new false-alarm class. Every `null` field above carries a comment in the render saying *why* it's null, never a bare empty value.

### Law 2 — the shadow is written at every return seam, not once at the top.

`handle_message` has seven+ distinct return paths (guest-refused, guest-reach, help, revive, spawn, seat-channel, mention/everyone, ambient-broadcast). A top-of-function shadow that only fires on the happy path silently misses guests-refused and levers — reproducing `the_gateway_already_collected_what_it_refused_to_say` *inside the instrument itself*. The schema is only as complete as the set of seams it wraps. **Every** `return` in `handle_message` emits its shadow line.

### Law 3 — the ladder and the shadow agree on facts, not on memory.

`ladder_stage` is copied from the T380 tracker at each shadow write, and the shadow is the *durable* record of the stage sequence. The ladder forgets on restart; the shadow must not. But the shadow never *invents* a stage the ladder didn't witness — it records `ladder_stage: null` with a `why_silent` note when the tracker has no entry (a gateway restart gap is a *fact about the instrument*, more honest than a fabricated "answered").

## The boundary facts this schema fixes (to reconcile at the fence)

1. **`idempotency_key` already exists** (T376 S3a: `discord:{message_id}`, derived from the snowflake, never minted). Reuse it as the shadow's dedup key — do not invent a parallel identity, or double-relay dies at a different door than crash-redelivery.
2. **`event_ts` vs `stream_id`**: `stream_id` is the birth timestamp (the primary key, survives the messenger); `event_ts` is the *event's* timestamp. For an IN message they're near-identical; for an OUT reply the `event_ts` is when the seat *answered*, which can be hours after the `stream_id` of the inbound it answers. Keeping both prevents the transport-freshness lie (a glyph that looks fresh because the transport timestamp is fresh though the claim inside is old).
3. **`to_resolution` is the :822 fix made durable.** Today five resolution paths (`_seat_channels`, `_rooms_reverse`, `_mention_map`, `mention_everyone` bool, ambient) each *imply* who got addressed. `to_resolution` forces the gateway to answer it in one place, so `eye get discord:<id>` can cite "actually addressed claude via #vandor" instead of re-deriving it.

## What Rill's eye-ingest adapter must carry (handoff note, not my lane)

`eye get discord:<bus-id>` must resolve via `stream_id` (always present), render `bus_id` only when present (lever paths have none), and cite `verbatim` verbatim. The staleness law: a peeked record must render its `event_ts`, and eye must refuse to call a claim "fresh" on transport timestamp alone. See the dedicated handoff to Rill.

## Open for the fence

- Whether `verb` (bus kind) should be a closed enum folded from `core/comm/kinds.py` rather than the loose list above (Navi's prior: yes — reuse the kinds roster, don't mint a parallel one).
- Whether the shadow file lives at `state/coord/discord_shadow.jsonl` (next to `discord_rooms.json` / `remote_bridge_*.json`) or inside the eye source dir. Leaning `state/coord/` so it's git-tracked and next to its siblings.
- The exact `stream_id` format (ISO-8601 UTC vs epoch-ms). Navi's prior: **ISO-8601 UTC** — human-readable, sortable, and timezone-immune, matching `now_iso()` (T119, the one clock).
