---
akashic_id: art_20260712_t040-packet-spec-v1-deepseek-blind-desig_cbdeba
akashic_sha: 7edd3c3e189a
status: draft
type: report
date: 2026-07-12
title: T040 Packet Spec v1 — DeepSeek blind design half
gist: "# T040 Packet Spec v1 — DeepSeek blind design half **Date:** 2026-07-12 **Class:** fenced dual design (charter at research/t040-packet-spec-"
tenant: solo
visibility: fleet
seats: []
category: [substrate, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_t040-packet-spec-v1-fenced-dual-design-b_a9669a
    rel: cites
  - target: art_20260712_t038-t039-implications-reconciliation-re_4966b0
    rel: cites
  - target: art_20260701_packet-substrate-slice-plan-lanes-latche_cc7456
    rel: cites
created: "2026-07-12T03:50:23"
updated: "2026-07-23T21:42:17"
---
<!-- GENERATED PROJECTION of art_20260712_t040-packet-spec-v1-deepseek-blind-desig_cbdeba -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T040 Packet Spec v1 — DeepSeek blind design half

# T040 Packet Spec v1 — DeepSeek blind design half

**Date:** 2026-07-12
**Class:** fenced dual design (charter at research/t040-packet-spec-brief-2026-07.md)
**Method:** blind from the brief + reconciliation rulings D1-D6 (LAW) + shared ground truth
**Refs:** D1-D6 at research/reviewed/t038t039-implications-reconciliation-2026-07-12.md · arc plan at docs/packet-substrate-slices-2026-07.md · live envelope at core/comm/bus.py:239-244 · L4 at core/comm/expectations.py · both implications halves · Daniel steers (t039-latch-refinement, t039-networking-lens, t038t039-packet-vision)

---

## 1. ENVELOPE HEADER — field-by-field spec (v=2)

Today's envelope (`bus.py:239-244`): `{frm, to, kind, content, ts, meta, parts}`. This is v=1 (implicit — no version field). v=2 adds the fields below. The migration rule (§4) ensures v=2 producers and v=1 consumers coexist.

Every field below names: type, required/optional, default, writer (who populates it), reader (who acts on it), validation door (where the check runs), and violation behavior.

---

### 1.1 `v` — version

| Property | Value |
|----------|-------|
| **Type** | `int` (1..255) |
| **Required** | YES |
| **Default** | `1` (absent = v=1 for backward compat; v=2 producers MUST set it) |
| **Writer** | Bus constructor / `_emit()` — the door stamps it |
| **Reader** | Every consumer. v=2 consumers parse v=2 fields; v=1 consumers ignore unknown fields |
| **Validation door** | Consume: if `v > MAX_SUPPORTED` (a registry dial defaulting to 2), the consumer DOWNGRADES — strips unknown fields, logs a warning `"[bus] message {mid} is v={v}, supported max {max} — downgrading to v={max}"`, and processes the known subset |
| **Violation** | Non-integer or < 1: REJECT at produce door (loud refusal, message not sent). Invalid version at consume: DOWNGRADE WITH WARNING, block only if the stripped fields are REQUIRED for the consumer's function (e.g., a latch consumer receiving a v=2 message with `latch[]` stripped cannot enforce the latch → LOUD refuse, not silent downgrade) |

**LAW reference:** D1 fail-direction split. The version downgrade is a DEPENDENCY (open degraded + loud). A consumer that NEEDS v=2 fields to enforce safety treats degradation as an enforcement-latch EXPIRY (fail CLOSED — refuse, loud, human-visible). The door's error line names which field was missing: `"[bus] REFUSED v=2 message {mid}: requires field '{field}' for enforcement, but consumer max version is {max}"`.

---

### 1.2 `flow` — flow identifier (OTel trace_id)

| Property | Value |
|----------|-------|
| **Type** | `str` (hex, exactly 32 chars — OTel trace-id format `00-{32hex}`) |
| **Required** | OPTIONAL |
| **Default** | Absent |
| **Writer** | Sender (on the FIRST message of a new flow). Subsequent messages in the same flow MUST carry the same `flow`. The flow-id persists across lanes — a reply in `work` carries the same `flow` as the request in `work` and the steer in `sig` |
| **Reader** | Consumer's context manager groups by `flow`. UI groups work-feed cards by `flow`. Recall funnel uses `flow` as the causal-chain anchor. Latch DAG uses `flow` for cross-lane scope |
| **Validation door** | Produce: if set, MUST match `^[a-f0-9]{32}$` (lowercase hex). Consume: absent → the message is its own root (implicit singleton flow). Present but bogus → DOWNGRADE (strip, warn, treat as root) |
| **Violation** | Invalid format: REJECT at produce door if sender attempts to set it. At consume: downgrade as described. A flow-addressed steer (§1.8) that arrives without a `flow` on its target is returned to sender with `FLOW_UNKNOWN` — the steer can't be scoped if the target has no flow | 

**Generation rule:** `flow` is minted by the sender via `uuid.uuid4().hex` (32 hex chars, lowercase). OTel tooling recognizes this as a valid trace-id when exported. The `00-` trace-flags prefix is added at export time (OTLP exporter), not stored in the envelope — the envelope is the canonical record; the export is a projection.

---

### 1.3 `lane` — target lane

| Property | Value |
|----------|-------|
| **Type** | `str` (from the lane roster: `work`, `sig`, `trace`, `test-*`) |
| **Required** | OPTIONAL (v=1 implicit: the single undifferentiated stream) |
| **Default** | Absent → the legacy bifrost stream |
| **Writer** | Bus constructor / `_emit()` — derived from the `kind` field by the lane router (pure function of `kind → lane`) |
| **Reader** | Consumer filters per-lane. Watcher watches `work` only. UI renders per-lane panels |
| **Validation door** | Produce: lane router MUST map kind to exactly one lane. Kind not in the lane router table → REJECT ("unknown kind '{kind}' — no lane mapping"). Consume: lane field present but unknown → DOWNGRADE (treat as legacy stream, warn) |
| **Violation** | Unknown lane at produce: REJECT (loud, message not sent). Unknown lane at consume: DOWNGRADE (warn, route to legacy stream). Mismatch between `lane` field and the stream the message actually landed on: LOUD WARNING at consume (indicates a misrouted message — the lane router and the stream assignment disagree; diagnostic, not reject) |

**Lane router table (v=1):**

| `kind` | `lane` |
|--------|--------|
| `chat`, `request`, `handoff`, `reply`, `note` | `work` |
| `trace` | `trace` |
| `nudge`, `steer`, `halt`, `pause`, `dispatch`, `query` | `sig` |
| Any kind starting with `test-` | `test-<namespace>` |

---

### 1.4 `class` — packet family (the kind taxonomy)

| Property | Value |
|----------|-------|
| **Type** | `str` (from the family roster, §2) |
| **Required** | OPTIONAL (v=1 implicit: kind-based routing only) |
| **Default** | Absent → consumer infers from `kind` (backward compat) |
| **Writer** | Sender (declares the packet's SEMANTIC family, distinct from the transport `kind`) |
| **Reader** | ACL door (per-family permissions). UI (per-family rendering). Substrate observer (per-family monitoring) |
| **Validation door** | Produce: if set, MUST be in the family roster. Consume: absent → family inferred from `kind` by a mapping table. Present but unknown → DOWNGRADE (warn, infer from kind) |
| **Violation** | Unknown family at produce: REJECT. Invalid family for the declared `kind` (e.g., `class=order` + `kind=chat`): LOUD WARNING at produce (accepted but flagged — the sender is confused; the observer reports it) |

**Family roster v1 (§2) is the authoritative source for valid `class` values.**

---

### 1.5 `ttl` — packet-level time-to-live

| Property | Value |
|----------|-------|
| **Type** | `int` (seconds, 0..86400) |
| **Required** | OPTIONAL |
| **Default** | Absent (no TTL — message persists until consumed or stream-trimmed) |
| **Writer** | Sender (declares the useful lifetime). The door MAY clamp (MIN_TTL=1, MAX_TTL=86400 via registry dials `PACKET_MIN_TTL`, `PACKET_MAX_TTL`) |
| **Reader** | Consumer checks: "is `now - ts > ttl`?" If yes, DROP the message (advance past it, no processing, emit `ttl_expired` event). Substrate observer can pre-filter expired packets |
| **Validation door** | Produce: clamp to min/max bounds (silent, LOUD if the sender asked for something outside bounds). Consume: TTL check at dequeue time — expired → DROP + event |
| **Violation** | TTL negative or non-integer: REJECT at produce. TTL expired at consume: DROP + `ttl_expired` event (not a failure — intended behavior; the sender asked for a deadline). TTL expired on a LATCHED message: the latch TTL is independent (§1.6); if the latch outlives the packet TTL, the packet is dropped but the latch still fires — the latch gates a CONDITION, not the packet itself |

---

### 1.6 `deadline_ts` — gRPC-style absolute deadline

| Property | Value |
|----------|-------|
| **Type** | `float` (Unix epoch seconds, UTC) |
| **Required** | OPTIONAL |
| **Default** | Absent (no sender deadline) |
| **Writer** | Sender (absolute time, set when arming an L4 expectation). The sender sets `deadline_ts = now + within_s` on the outgoing message AND arms the L4 expectation separately (L4 is the enforcing backstop) |
| **Reader** | Consumer checks BEFORE processing: "is `now > deadline_ts`?" If yes, ABORT processing, advance past message, send `DEADLINE_EXCEEDED` reply to sender. The consumer cooperates with the sender's deadline — wasted work is eliminated. L4 sweep remains the authoritative enforcement (catches messages where the consumer is down) |
| **Validation door** | Produce: if set, MUST be > `now` and ≤ `now + MAX_DEADLINE_S` (registry dial, default 86400). Clamping silent + LOUD. Consume: check at dequeue (the per-message check is cheap — one float compare) |
| **Violation** | Past deadline at produce: REJECT (the sender asked for a deadline already expired — likely a clock skew or a bug). Future deadline at produce: CLAMP to max. Past deadline at consume: ABORT + `DEADLINE_EXCEEDED` reply |

**Flow inheritance rule (adopted from Claude's half):** A message that carries a `deadline_ts` and creates a latch on a downstream message INHERITS a shortened deadline onto the downstream message: `deadline_child = min(deadline_parent, now + parent_remaining * FACTOR)` where FACTOR defaults to 0.8. This shrinks the budget down a causal chain — no downstream consumer gets the full deadline when the upstream already spent some of it.

---

### 1.7 `latch[]` — latch references

| Property | Value |
|----------|-------|
| **Type** | `List[LatchRef]` where `LatchRef = {id: str, type: "causal"|"reference", gate: str, ttl: int, from_lane: str, from_id: str}` |
| **Required** | OPTIONAL |
| **Default** | `[]` (no latches) |
| **Writer** | Sender (declares: "this message creates a latch"). The latch layer validates and stores the latch at produce time |
| **Reader** | Latch layer (validates DAG invariant, stores adjacency). Consumer (checks latch index before advancing). L4 engine (monitors TTL expiry) |
| **Validation door** | Produce: latch layer checks DAG INVARIANT (rejects cycle). Each `LatchRef` validated: `type` MUST be `causal` or `reference`, `gate` must be a valid lane:message-id pair, `ttl` must be within bounds. Consume: consumer checks `latch:<id>:fired = 1` before advancing past the latched message. Latch expired with unsatisfied dependency → per D1: enforcement-latch stays BLOCKED + LOUD; dependency-latch opens degraded + LOUD |
| **Violation** | Cycle: REJECT at produce (loud, cycle path named). Unknown latch-type: REJECT. TTL zero/negative: REJECT. Latch expired: per-class behavior per D1 (see §1.7.1) |

**§1.7.1 Latch-class failure direction (D1 — LAW):**

| Latch class | Expiry behavior | Example |
|-------------|-----------------|---------|
| **Enforcement** (method gates, test-attach, security barriers) | **FAIL CLOSED.** Message stays BLOCKED. LOUD event: `[latch] ENFORCEMENT LATCH {id} EXPIRED — message {mid} REMAINS BLOCKED, human resolution required`. The blocking is indefinite until operator action (flip the kill-switch or resolve manually). | "Review record for commit X not found — build blocked." |
| **Dependency** (data joins, context assembly, merge gates) | **FAIL OPEN degraded + LOUD.** Message UNBLOCKS. LOUD event: `[latch] DEPENDENCY LATCH {id} EXPIRED — proceeding with degraded data (dependency {gate} not satisfied)`. Consumer sees "proceeding degraded" and may abort or continue with partial data. | "Merge of chapters 1-3 waiting for chapter 4 — proceeding with chapters 1-3 only." |

---

### 1.8 `frag` — fragmentation header

| Property | Value |
|----------|-------|
| **Type** | `FragHeader = {seq: int, of: int, whole_id: str} | null` |
| **Required** | OPTIONAL |
| **Default** | `null` (not fragmented) |
| **Writer** | Send door (when the payload exceeds `BUS_MAX_MESSAGE_BYTES`, the door splits into N fragments with `seq=0..N-1`, `of=N`, `whole_id` = a UUID for reassembly) |
| **Reader** | Reassembly buffer per `whole_id` at the consumer. Consumer holds fragments until all `of` arrive or TTL expires |
| **Validation door** | Produce: `seq >= 0`, `seq < of`, `of >= 2`, `of <= MAX_FRAGMENTS` (registry dial, default 16). Whole_id must be a valid UUID. Any violation → REJECT (the door refuses to split; the sender gets an error: "message too large, split manually or reduce size"). Consume: `seq=N` arrived before `seq=N-1` → reassembly buffer queues out-of-order (TCP semantics, per-flow). Missing fragment after `FRAG_REASSEMBLY_TTL` (registry dial, default 300s) → LOUD `fragment_timeout` event, all fragments for that `whole_id` DROPPED, consumer advances past the gating message |
| **Violation** | Missing fragment timeout: LOUD event + DROP. Duplicate fragment (same seq): IGNORE (idempotent). Fragment with wrong `whole_id` in the reassembly buffer: LOUD + DROP (the sender is buggy; don't try to fix it) |

**Reassembly ownership:** Consumer-side only. The consumer owns the reassembly buffer (one per `whole_id`). The sender never reassembles — it only splits. A fragment that arrives at a consumer that doesn't have the reassembly buffer (new consumer, reboot) is queued; if the previous fragments are unavailable (stream-trimmed), the consumer emits `fragment_orphan` and DROPS the fragment — the full message must be re-sent.

---

### 1.9 `len` — declared payload length

| Property | Value |
|----------|-------|
| **Type** | `int` (bytes, UTF-8 encoded) |
| **Required** | YES (for v=2 messages) |
| **Default** | N/A (MUST be present in v=2) |
| **Writer** | Send door — computes `len(utf8_bytes(content + parts))` pre-serialization |
| **Reader** | Consume door — re-computes `len(utf8_bytes(content + parts))` from the received message and COMPARES. Mismatch → CORRUPT |
| **Validation door** | Consume: `computed_len != declared_len` → REJECT with `"[bus] INTEGRITY: message {mid} declared {declared} bytes, actual {actual} — DROPPED (corrupt in transit)"`. The message is not delivered to the consumer |
| **Violation** | Mismatch: DROP + integry event. The sender's `len` at v=2 and the consumer's check are the MTU + silent-clip defense. A message that was SILENTLY TRUNCATED (4K clip class) will fail the `len` check — the consumer-computed length will be SHORTER than declared. Same for a truncated `content` field or a corrupt `parts` entry |

---

### 1.10 `sha` — payload integrity hash

| Property | Value |
|----------|-------|
| **Type** | `str` (hex, exactly 64 chars — SHA-256) |
| **Required** | YES (for v=2 messages) |
| **Default** | N/A (MUST be present in v=2) |
| **Writer** | Send door — computes `SHA256(canonical_payload)` where `canonical_payload = concat(frm, to, kind, json_canonical(content), ts, json_canonical(meta), json_canonical(parts))` (field-order-stable serialization) |
| **Reader** | Consume door — recomputes SHA-256 from the received fields and COMPARES. Mismatch → CORRUPT |
| **Validation door** | Consume: `computed_sha != declared_sha` → REJECT with `"[bus] INTEGRITY: message {mid} SHA-256 mismatch — DROPPED (corrupt in transit)"`. Message not delivered |
| **Violation** | Mismatch: DROP + integrity event. The `sha` check catches: (a) content corruption, (b) field-level corruption (frm/to/kind changed in transit), (c) Redis AOF corruption, (d) the silent-clip class where content is truncated mid-JSON — the recomputed hash won't match. This is the CHECKSUM-AT-DOOR fix for the bug class that ate 3 knowledge_note writes and a 4K tool argument tonight |

**Canonical serialization order:** `frm` → `to` → `kind` → `content` → `ts` → `meta` → `parts`. `json_canonical(obj)` = `json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)`. This is field-order-stable and produces the same hash for logically-equivalent messages regardless of dict insertion order.

---

### 1.11 `idempotency_key` — safe-retry guard

| Property | Value |
|----------|-------|
| **Type** | `str` (opaque, max 128 chars) |
| **Required** | OPTIONAL |
| **Default** | Absent (no idempotency guard) |
| **Writer** | Sender (generates a unique key for this logical request — may be the message id itself, a UUID, or a content-hash) |
| **Reader** | Consumer's reply-sent sentinel (existing mechanism, `runner_lock` reply dedup). Token negotiation layer (deduplicates OFFER messages with the same key) |
| **Validation door** | Produce: length ≤ 128. Consume: sentinel check — if `sentinel:{idempotency_key}:reply_sent` exists, SKIP (the reply was already sent; effectively-once). If the sentinel doesn't exist yet, process normally and write the sentinel AFTER replying |
| **Violation** | Key too long: REJECT at produce. Key collision (two different messages with the same key): the sentinel prevents the second from being re-processed — this is INTENDED behavior, not a bug. The sender is responsible for generating unique keys. Collision due to sender bug → the second message gets a DUPLICATE reply (the sentinel's stored reply is re-sent). Collision due to malicious sender → idempotency keys are advisory between cooperating peers; the trust model assumes no adversarial senders on the `work` lane

---

## 2. KIND/FAMILY ROSTER v1

### 2.1 The roster

The roster is the authoritative set of `class` values. Registration in the T034 manifest (§2.4). Cap: **10 families** (start at 8, 2 reserved). Deletion ritual: remove from manifest + tombstone record + why-not-existing answer. No family may be added without a SPECIFIC consumer that needs the class to act on.

| # | Class | Kind(s) mapping | QoS | Lane | ACL floor | Ship v1? | Who reads it |
|---|-------|-----------------|-----|------|-----------|----------|--------------|
| 1 | `context-delta` | N/A (new kind) | QoS 1 | `work` | TRUSTED ONLY (super_admin) | **NO** (FM12 gate) | Runner context manager applies to live context |
| 2 | `steer` | `steer`, `nudge` (kind-level distinction) | QoS 1 | `sig` | `BUS_STEER` for steer, `BUS_NUDGE` for nudge | **YES** (existing) | Runner folds into current/next round |
| 3 | `dispatch` | `dispatch` (new kind) | QoS 1 | `sig` | `BUS_DISPATCH` (super_admin) | **YES** (new) | Agent accepts/declines; ledger-audited |
| 4 | `status` | `status` (new kind) | QoS 0 | `trace` | `BUS_SEND` (any non-quarantined) | **YES** (new) | UI, observer, fleet doctor |
| 5 | `test-attach` | `dispatch` with `test` payload | QoS 1 | `sig` | `BUS_DISPATCH` | **YES** (new) | Token holder runs attached tests; token release gated |
| 6 | `directive-attach` | `directive` (new kind) | QoS 1 | `sig` | `BUS_DIRECT` (admin+) | **YES** (new) | Token holder ACKs and obeys (narrow-only) |
| 7 | `query` / `answer` | `query`, `answer` (new kinds) | QoS 1 | `sig` | `BUS_SEND` for query, `BUS_SEND` for answer | **YES** (new) | Substrate answers fleet-state queries directly; agents answer domain queries |
| 8 | `ui-projection` | `ui` (new kind) | QoS 0 | `trace` | `BUS_SEND` (any non-quarantined) | **YES** (advisory only) | UI renders if understood; ignores silently if not |

**Reserved (v2):** `order` (autonomous task claim — needs T038 full negotiation first), `offer/counter/accept` (token negotiation families — ride `sig`, designed post-T040).

### 2.2 Family-ACL matrix

| ACL capability | Families permitted |
|----------------|-------------------|
| `BUS_SEND` (standard, non-quarantined) | `status`, `query`/`answer`, `ui-projection` (advisory) |
| `BUS_STEER` | `steer` (kind=steer) |
| `BUS_NUDGE` | `steer` (kind=nudge) |
| `BUS_DISPATCH` (super_admin) | `dispatch`, `test-attach` |
| `BUS_DIRECT` (admin+) | `directive-attach` |
| `BUS_CONTEXT` (super_admin only) | `context-delta` (v2 — not shipped in v1) |
| Quarantined | NONE (zero families — no send capability at all) |

### 2.3 Roster governance (T034 Goodhart-1 applied)

- **CAP:** 10 families. 8 shipped in v1, 2 reserved. Adding an 11th requires REMOVING one + tombstone record + justification.
- **REGISTRATION:** Each family is a T034 manifest entry: `dial key = "packet_family:{name}"`, `authority = "admin"`, `introduced = "T040"`, `deprecates = null`. The manifest IS the roster source of truth.
- **DELETION RITUAL:** A family is removed by setting `removed` with `date + reason` in the manifest. The name is NOT REUSED (tombstone). All consumers that reference the family MUST be updated before removal (the ship gate checks: zero references to removed family in any consumer source).
- **KIND-FAMILY VALIDATION:** Every `kind` maps to exactly one `class`. The mapping table is a T034 manifest entry. A `kind` without a mapping → REJECT at produce.

### 2.4 Where the roster lives

The roster is a T034 manifest entry: `packet_family_roster` — a dial of `kind = "table"` whose value is the current roster (class → {kinds, qos, lane, acl_floor, introduced}). The `agent_cli.py settings` verb shows the roster. The `agent_cli.py doctor` verb cross-references: "3 families in use today, 2 lanes active, roster cap 10 (70% free)." The roster is the single source of truth; consumers read from the manifest, not from hardcoded constants.

---

## 3. PER-LANE DELIVERY CONTRACT

| Lane | QoS class (MQTT) | DiffServ PHB | Seat discipline | Retention/trim | Wake participation | ACL floor (write) | ACL floor (read) |
|------|-----------------|--------------|-----------------|----------------|-------------------|--------------------|------------------|
| `work` | QoS 1 (at least once) | AF (Assured Forwarding) | RB-21 single-consumer, fenced generations | `maxlen=10000`, approximate XTRIM | YES — watcher watches `work` only | `BUS_SEND` (non-quarantined) | `BUS_SEND` |
| `sig` | QoS 1 (at least once) | EF (Expedited Forwarding) | Per-agent directed consumption, no consumer seat contention (halts/steers/dispatches are directed, not broadcast) | `maxlen=5000`, approximate XTRIM | NO — sig traffic never wakes the watcher | Authority-gated per family (§2.2) | `BUS_SEND` |
| `trace` | QoS 0 (at most once) | BE (Best Effort) | NO consumer seat — firehose-read, any agent can read any trace | `maxlen=5000`, approximate XTRIM, oldest dropped first | NO | `BUS_SEND` (any non-quarantined) | `BUS_SEND` |
| `test-*` | QoS 1 (at least once) | — (isolated) | Same as `work` within the test namespace | `maxlen=10000`, approximate XTRIM | YES (within namespace) | Test-harness only | Test-harness only |

### 3.1 Lane interaction rules

1. **`sig` is never blocked by `work` or `trace` volume.** Independent cursor, independent stream. The lane router writes `sig` messages to the `sig` stream, not the `work` stream.
2. **`trace` is lossy by design.** QoS 0: under XTRIM pressure, oldest trace entries are dropped. The trace lane is for observation, not coordination. No decision may depend on a trace message being delivered.
3. **`work` is the only lane with seat contention.** The RB-21 guarded cursor + fencing generations gate the `work` lane cursor only. `sig` and `trace` cursors advance independently without generation fencing.
4. **`test-*` lanes are production-invisible.** The production watcher NEVER subscribes to `test-*` patterns. The production consumer NEVER reads `test-*` lanes. Isolation is by lane pattern, not env var — remembering to set `BIFROST_NAMESPACE` is no longer required (the lane IS the isolation).

---

## 4. COMPATIBILITY + MIGRATION

### 4.1 The v=1 → v=2 rule

**DUAL-VERSION WINDOW:** v=2 producers and v=1 consumers coexist for one migration window. The rule:

- **v=2 producer sends a v=2 message:** Contains all v=2 fields (`v=2, flow, lane, class, ttl, deadline_ts, latch[], frag, len, sha, idempotency_key`).
- **v=1 consumer receives a v=2 message:** Sees fields it doesn't recognize (v=1 parser reads `frm, to, kind, content, ts, meta, parts`). Unknown fields are NOT stripped by the bus — they're transparent to the consumer. The consumer IGNORES unknown fields (standard JSON backward-compat). The consumer processes the known subset: `frm, to, kind, content, ts, meta, parts` — these fields are UNCHANGED between v=1 and v=2.
- **v=1 consumer does NOT see len/sha enforcement.** The v=1 parser doesn't validate `len` or `sha`. A v=1 consumer can receive a truncated message and not detect it. This is the MIGRATION WINDOW GAP — acceptable because: (a) the window is bounded (hours, not weeks), (b) v=1 consumers are being cut over, (c) the silent-clip class is rare and the migration reduces its window, not extends it.
- **v=2 consumer receives a v=1 message:** Sees `v` absent. Infers `v=1`. Fills defaults for all v=2 fields: `flow=null, lane=infer_from_kind(kind), class=infer_from_kind(kind), ttl=null, deadline_ts=null, latch=[], frag=null, len=null, sha=null, idempotency_key=null`. NO `len`/`sha` validation (no declared values to check against). The consumer processes with v=1 semantics.
- **CUTOVER:** When the last consumer is migrated to v=2, the v=1 path is retired. The dual-version window CLOSES. v=1 messages are no longer accepted at the produce door (REJECT: "[bus] v=1 messages are retired — upgrade producer to v=2"). The retirement is a ledger event.

### 4.2 Today's envelope → v=1 mapping

Today's `_emit()` produces:
```python
env = {"frm": ..., "to": ..., "kind": ..., "content": ..., "ts": ..., "meta": ..., "parts": ...}
```

This is v=1 (implicit). The migration:
1. Add `v=1` to the envelope (all existing messages become explicitly v=1).
2. v=2 producers add `v=2` + all v=2 fields. No existing consumer breaks (unknown fields ignored).
3. Cut consumers to v=2 one by one. Each consumer upgrade is a one-line change: `parser = PacketV2Parser()` instead of `parser = PacketV1Parser()`.
4. Retire v=1.

### 4.3 First cutover

**First producer to move:** The RUNNER (DeepSeek or Claude). The runner's `bus.send()` and `bus.broadcast()` calls are the highest-volume producers. Moving them first gives the largest population of v=2 messages → the fastest validation of the downgrade path.

**First consumer to prove the window:** The WATCHER. The watcher is the simplest consumer (reads, filters, exits on work mail). Upgrading it to v=2 and verifying it reads both v=1 and v=2 messages proves the dual-version window works. The watcher's v=2 parser checks `len`/`sha` on v=2 messages → if the checksum-at-door works, the silent-clip class is closed for the migration window at the watcher level.

**Cut order:** Watcher → UI → Runner → Fleet doctor → Chronicler → L4 sweep. Each cut is a one-line parser change. The entire migration is under one hour of actual work time.

---

## 5. THE RIDING BUILD DELIVERABLE (M3 pins ready)

### 5.1 Send-door MTU rejection

**Dial:** `BUS_MAX_MESSAGE_BYTES` (T034 manifest, authority=operator, default=65536, min=1024, max=1048576).

**Behavior:** `Bus._emit()` checks `len(serialized_message)` BEFORE calling `xadd`. If > `BUS_MAX_MESSAGE_BYTES`:
- REJECT: return `None` (send fails).
- LOUD: print to stderr `"[bus] REJECTED: message to '{to}' exceeds max size ({size} > {max} bytes). Split into parts, use -partN fragmentation, or reduce content."`.
- The sender sees `None` return from `send()`/`broadcast()`.

**M3 pin:** `test_mtu_rejection_at_send_door` — a message of 65537 bytes with default maxlen=65536 is rejected (send returns None). A message of 65535 bytes is accepted (send returns a mid). A message exactly at 65536 is accepted. All three bounds exercised.

### 5.2 len + sha integrity

**Dial:** `PACKET_INTEGRITY_ENABLED` (T034 manifest, authority=operator, default=True). When False (kill-switch), `len` and `sha` are neither written nor validated — the system degrades to v=1 integrity guarantees. The flip is provenance-tracked (T034 flip audit).

**Computation:** `len` and `sha` are computed at `_emit()` time. The canonical serialization order (§1.10) is a constant in `packet_integrity.py`. Both fields are stored in the Redis stream entry alongside the existing fields.

**Validation:** Consumer `inbox()` validates AFTER reading the stream entry, BEFORE returning it to the caller. Invalid → DROP + event. The message is never delivered to the consumer.

**M3 pins:**
- `test_len_check_catches_truncation` — plant a v=2 message with `len=1000`, modify the `content` field in Redis to be 500 bytes. Consumer drops it, integry event fires.
- `test_sha_check_catches_corruption` — plant a v=2 message with valid sha, flip one character in `content`. Consumer drops it.
- `test_integrity_kill_switch` — flip `PACKET_INTEGRITY_ENABLED=False`, corrupted message is delivered (degraded, loud). Flip back, corrupted message dropped.

### 5.3 -partN fragmentation formalization

**Behavior:** When a message exceeds `BUS_MAX_MESSAGE_BYTES` AND the sender has NOT opted into fragmentation (a `allow_frag=True` kwarg on `send()`/`broadcast()`), the send is REJECTED (§5.1). When `allow_frag=True`:
- The door splits `content` into N parts of ≤ `BUS_MAX_MESSAGE_BYTES` bytes each.
- Each fragment is sent as a separate v=2 message with `frag={seq, of, whole_id}`.
- The consumer reassembles using a per-`whole_id` buffer.
- Reassembly TTL: `FRAG_REASSEMBLY_TTL` (dial, default 300s). Missing fragment after TTL → DROP all fragments for that `whole_id` + `fragment_timeout` event.

**M3 pins:**
- `test_fragmentation_roundtrip` — send a 200KB message, it's split into 4 fragments, consumer reassembles to identical content.
- `test_missing_fragment_times_out` — send fragment 0/2, don't send fragment 1/2, wait TTL, fragment_timeout event fires, both fragments dropped.
- `test_frag_reassembly_ttl_honored` — fragment arrives at TTL-1s, reassembly succeeds; fragment arrives at TTL+1s, orphaned, dropped.

---

## 6. WHAT V1 REFUSES TO CONTAIN (the cut list)

| What | Why cut | When to reconsider |
|------|---------|---------------------|
| `context-delta` family | FM12: highest-privilege family. Needs trusted-producer gate, provenance headers, newborn-gauntlet probe, data-not-instructions doctrine — all v2 material | When T041 pluggable endpoints design opens; context-delta producer is the recall funnel behind the FM12 gate |
| Bundle-latches | Both halves deferred. No concrete use case. Causal-latches cover method enforcement | When a real incident shows causal insufficient (need atomic cross-lane consume) |
| Token negotiation families (`offer/counter/accept`) | T038 design opens AFTER T040; the families ride `sig` when the protocol is specified | Post-T038 design |
| `order` family (autonomous task claim) | Needs T038 negotiation as prerequisite | Post-T038 build |
| Flow-inherited deadline propagation | Adopted from Claude's half but deferred to v2 — needs latency measurement from live flows before the inheritance factor (0.8) is calibrated | When 100+ real flows have measurable latency distributions |
| Per-flow sequence numbers (FM-P1 guard) | Declared REQUIRED in the reconciliation as a packet-spec field, but v=1 flows have no sequence. Adding retroactively requires a flow-state key in Redis. Defer to v=2 (TRIVIAL to add — one int field — but needs flow-state infra) | When the first multi-lane consumer ships and reorder risk is real (today single-lane = no reorder) |
| OTLP export | The envelope carries OTel-shaped ids; exporting them to Jaeger/Tempo is Phase 4 (observers). The spec defines the SHAPE; the exporter is a separate slice | Phase 4 (pluggable endpoints) |
| `ui-projection` enforcement | Advisory only in v1. Non-advisory UI projection (where the UI MUST render the element) is an anti-pattern — the UI derives from observation | Reconsider if advisory proves insufficient for a specific operator need |

---

## 7. THREE PROBE QUESTIONS (a reviewer should ask any envelope spec)

**Q1: "What is the smallest valid v=2 message, and does it beat v=1 on that size?"**

Answer: Smallest v=2 message = `{v=2, frm="x", to="y", kind="chat", content="", ts="...", meta={}, parts=[], len=N, sha="...", latch=[], frag=null}`. Fields `flow`, `lane`, `class`, `ttl`, `deadline_ts`, `idempotency_key` are absent (optional). Compared to v=1: +`v`, +`len`, +`sha`, +`latch[]`, +`frag` ≈ +150 bytes overhead on a minimal message. For a 1KB chat message, that's ~15% overhead. Acceptable: the integrity fields (`len`+`sha`) earn their keep immediately (three silent-loss receipts tonight). The `latch[]` and `frag` overhead is zero when absent (empty list, null).

**Q2: "Can a v=2 message with an enforcement-latch be downgraded to v=1, and if so, does the latch survive?"**

Answer: If a v=2 message with `latch=[{type:"causal", ...}]` is consumed by a v=1 consumer, the latch field is IGNORED. The latch is NEVER STORED by the v=1 consumer. The downgrade is LOUD: `"[bus] WARNING: v=2 message {mid} has latch[] — downgrading to v=1, latch NOT enforced"`. The sender armed a latch that a downgraded consumer silently ignores → the enforcement hole is the EXACT size of the migration window. This is the gate that forces the window to be SHORT — every consumer that ignores latches is a hole in the enforcement surface.

**Q3: "What is the failure mode when the declared `len` is correct but the `sha` is wrong — or vice versa?"**

Answer: `len` mismatch means the payload size changed (truncation, expansion). `sha` mismatch means the payload CONTENT changed (corruption, bit-flip). Both are independent checks. If `len` matches but `sha` doesn't: the payload was replaced with different content of the same length (unlikely but possible with Redis AOF corruption). If `sha` matches but `len` doesn't: impossible — SHA-256 collision at different lengths is cryptographically infeasible; this would indicate a `len` computation bug, not corruption. The dual check catches: (a) silent truncation (`len` check), (b) content corruption (`sha` check), (c) computation bugs (disagreement between the two implicit signals). A message that fails EITHER check is DROPPED — not delivered, not downgraded. Integrity is binary.

---

*End of spec half. Reconciliation with Claude's sealed half pending.* |
