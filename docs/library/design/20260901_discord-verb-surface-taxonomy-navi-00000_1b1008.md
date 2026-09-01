---
akashic_id: art_20260901_discord-verb-surface-taxonomy-navi-00000_1b1008
akashic_sha: f47eba1245dc
schema_version: 1
status: current
type: design
date: 2026-09-01
title: discord-verb-surface-taxonomy-navi-000000
gist: "--- akashic_id: art_20260902_discord-verb-surface-taxonomy-navi akashic_sha: _pending_ schema_version: 1 status: draft type: design arc: eye"
visibility: fleet
body_type: transcript
seats: [kimi]
category: [library, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T11:45:15"
updated: "2026-09-01T11:45:15"
---
<!-- GENERATED PROJECTION of art_20260901_discord-verb-surface-taxonomy-navi-00000_1b1008 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# discord-verb-surface-taxonomy-navi-000000

---
akashic_id: art_20260902_discord-verb-surface-taxonomy-navi
akashic_sha: _pending_
schema_version: 1
status: draft
type: design
arc: eye-able-discord
date: 2026-09-02
title: discord-verb-surface-taxonomy-navi
gist: "The discord verb surface taxonomy (verbified notifications): send/read/ack/watch/status, each routing to a different MOMENT per the category law; composes with the sugar-only toolbelt registry, never mints unsupported capabilities"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [bus, ergonomics, ui]
origin: authored
settled: live
supersedes: null
superseded: null
citations: []
created: "2026-09-02T00:00:00"
updated: "2026-09-02T00:00:00"
---

# discord-verb-surface-taxonomy-navi

*Navi's verb taxonomy — "discord notifications and communications to be verbified" (Daniil, night-shift orders). Status: LIVE discussion. This is a DRAFT scaffold; the minted art_ id supersedes on ratification.*

## The one law: verbs are moments, not capabilities

The existing toolbelt registry (`core/toolbelt/registry.py`) is **sugar-only**: an alias is a *sequence of existing `agent_cli` verbs*, and minting a step whose verb the door doesn't know **refuses loudly** ("registry cannot mint capabilities"). So the discord verb surface is not a set of new `agent_cli` verbs — it is a **routing taxonomy over the *moments* a discord message passes through**, where each verb *resolves* to either (a) an existing `agent_cli` verb, or (b) the new shadow-record read path (`eye get discord:<id>`). The taxonomy says **which moment**, the registry says **which steps**. The two compose; neither invents a capability.

## The five verbs, one per moment

A message has a lifecycle, and each verb is that lifecycle's *named*, *queryable* surface. The category law applies: **each verb routes to a different moment, and never to a different thing it silently pretends is the same moment.**

| Verb | Moment it serves | Resolves to (existing door) | Category (aboutness) |
|---|---|---|---|
| **send** | The outbound relay — I push a word to Discord | `agent_cli` relay path / `webhook` send | `bus` — a word becomes an address |
| **read** | The inbound pull — what Discord said, not what I *assume* it said | `eye get discord:<stream_id>` (cite `verbatim`) | `recall` / `wiki` — reading the record, not the memory |
| **ack** | The receipt — machine-stamped, millisecond, no model | `discord_ladder` landed/thinking op → shadow `relay_outcome` | `ergonomics` — the 📨 rung, zero-token |
| **watch** | The liveness — is the feed pump actually pumping, or is the beat a lie | `status`/`doctor` feed-pump probe | `agent-lifecycle` — the messenger's death vs the service's verdict |
| **status** | The *state of a tracked message* — has my word been answered | `discord_ladder` stage (landed→thinking→answered/replied/dead) | `performance` — latency of a round-trip |

## The three laws each verb honors

### send — the word must carry its `idempotency_key` and `to_resolution`.

`send` routes the same seam `handle_message` does (T376 `discord:{message_id}`, derived not minted). A send without a declared `to_resolution` is a send that can't be audited — the :822 rule restated as a *verb law*: **a verb that addresses must record what it addressed.**

### read — `read` is not `memory`. `read` cites verbatim; `memory` paraphrases.

The single most load-bearing distinction: two verbs that look like "what did it say" but are different *categories*. `read` pulls the shadow record and returns `verbatim` (the citation primitive). `memory` (an existing recall verb) returns a paraphrase. `read` must never be satisfied by `memory` — the staleness law: a paraphrase of a transcript is a summary, and a summary is not a receipt.

### ack / watch / status — three verbs, three truth-tests, never conflated.

- **ack** is *machine truth* (the receipt exists — `discord_ladder` landed/is-thinking). Zero tokens, driven by durable queue state, never vibes.
- **watch** is *liveness truth* (the pump is alive). This is the `a_long_lived_process_holds_a_dead_connection` class — the beat can be fresh while the send path is a corpse, because beat and send don't share a connection. `watch` must answer "is the *send path* pumping," not "is the heartbeat fresh."
- **status** is *settlement truth* (did my word get answered). This is the strict answer-link law (`answered` = `meta.answers == tracked mid`, T139) — `status` never claims "answered" from a heuristic `replied`.

**The rule binding them:** the three truth-tests are *different observations*, and a verb that reports one while silently passing off another is the `heartbeat_placement_above_every_gate` lie. `watch` must not say `status`'s answer; `ack` must not say `watch`'s.

## Composition with the toolbelt registry (the families)

The existing registry casts verbs into **families** (SENTINELS / MONITORS / LIFEWORKERS / ENGINEERS / CARTOGRAPHERS / LIBRARIANS). The discord verbs map onto those families as *alaises-of-aliases* — `watch` is a MONITORS verb (it watches the living pulse), `read` is a CARTOGRAPHERS/LIBRARIANS verb (it cites the record), `status` is a MONITORS verb, `ack` is machinery (no family — it's the bottom rung, below model), `send` is an ENGINEERS/bus verb. The families already exist; the discord verbs *light them up at the discord seam*, they don't mint new families.

## The anti-fabrication law (carried from the registry)

Every verb entry carries `evidence: VERIFIED|INFER|GUESS` and `tested_against` (a pin id or null). **A discord verb that hasn't been pinned ships as GUESS and confesses it.** The shadow read path and the ladder stage path are both pinnable; the `watch` pump-probe is pinnable; `send` is pinnable. No verb ships as VERIFIED without its receipt — "receipts or it did not happen" applied to the verbs themselves.

## Open for the fence

- Whether `read` should resolve through **both** the eye shadow record AND the live bus stream, or shadow-only. Navi's prior: **shadow-only** for `read` (the shadow is the durable truth; reading the live stream re-introduces the race the shadow exists to kill), and a *separate* `peek` for live-bus (the existing `bifrost_inbox` style).
- Whether `status` on a *lever* (no bus id) should return `{"kind": "lever", "relay_outcome": "lever"}` rather than "no such message" — a lever message has a real lifecycle (it was executed or refused), it just has no bus id. Navi's prior: `status` must answer "what happened to the lever," not pretend there was no message.
