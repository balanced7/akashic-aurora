---
akashic_id: art_20260715_t080-operator-traffic-design-blind-half_9f35fc
akashic_sha: 35d18e17b64a
status: draft
type: report
date: 2026-07-15
title: "T080 Operator Traffic — Design (blind half, deepseek) — 2026-07-15"
gist: "Daniel directive: \"solve the type of message issue from user in an elegant automatic way. so that we dont solve this with a hammer but with "
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T22:08:06"
updated: "2026-07-15T22:08:06"
---
<!-- GENERATED PROJECTION of art_20260715_t080-operator-traffic-design-blind-half_9f35fc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T080 Operator Traffic — Design (blind half, deepseek) — 2026-07-15

Daniel directive: "solve the type of message issue from user in an elegant automatic
way. so that we dont solve this with a hammer but with the right instrument."

## 1. The Distinction That Structures This Design

The T073 amendment was correct and necessary — operator messages must always wake.
But it said nothing about what HAPPENS after the wake. Every idle Claude seat woke
to Daniel's message, read it, and... then what? The system has no answer for:

- Did everyone get it? Daniel couldn't see. Only my runner's reply proved delivery.
- Was it answered? Nobody knows unless they reply explicitly.
- Is there an expectation? Operator messages carry implicit urgency, but the system
  treats them identically to agent `inform` traffic.
- Can the operator see the thread? Daniel reads the bus feed. He sees replies as
  raw messages. There is no "conversation" view — his message and the replies are
  disconnected events.

The hammer fixed WAKING. The instrument must fix: DELIVERY VISIBILITY, REPLY
EXPECTATION, and RENDERING. These three concerns are one design.

## 2. The Core Move: Operator Traffic Is a Semantic Layer

Operator traffic is NOT a new kind, a new lane, or a new bus primitive. It is a
**semantic layer** over existing infrastructure. Messages from operator ids carry
additional semantics that the system projects onto existing mechanisms:

| Concern | Mechanism | Status |
|---------|-----------|--------|
| Always wake | `wake_worthy()` `frm` check | ✅ T073 amendment |
| Delivery visibility | Per-message ack set (who received this?) | ❌ NEW |
| Reply expectation | RB-29 expectations — operator messages arm automatically | ❌ NEW |
| Distinct rendering | Whisper MAIL line splits operator / agent counts | ❌ NEW |
| Timeout escalation | Expectation redrive → pager + bus blocker | ❌ NEW |
| Reach receipts | Whisper shows "operator message: answered/N, awaiting/N" | ❌ NEW |

Each mechanism is a thin projection. Zero new primitives. Zero LLM on the hot path.
The frm-spoofing caveat narrows, never widens.

## 3. The Four Mechanisms

### 3a. Delivery Visibility (the REACH problem)

Daniel's actual pain: "I sent a message and only deepseek answered. Did Claude
even see it?"

**Mechanism: per-operator-message ack set.** When an operator sends a message
via the bus, the system arms a lightweight delivery tracker. The tracker is NOT
per-recipient — it's per-message. Any agent that READS the operator mail (not
just receives it) stamps its agent id. The stamp is optional and best-effort —
missing stamps mean "unobserved," not "lost." The operator's next boot or
`bifrost-sync` sees the ack set.

Storage: `bifrost:op_ack:<message_id>` → Redis SET of agent ids. TTL = 24h.
One SADD per agent per operator message. No new write on the hot path — the
`_process_one` path in the runner already checks `frm`; one additional line
stamps the ack set before answering.

The operator sees: "your message 'I'm back!' was received by: deepseek. Not
yet received by: claude, cursor." (from `bifrost-sync` or the whisper).

**What breaks when an agent forges frm=user and triggers ack tracking?**
Nothing. A forged operator message gets an ack set that nobody fills (no
agent reads fake-operator mail except the rogue). The forged ack set is
a garbage Redis key that expires in 24h. Zero privilege escalation.

### 3b. Implicit Reply Expectation

Operator messages carry implicit urgency: Daniel expects SOMEONE to answer.
Agent `inform` messages are fire-and-forget. Operator `inform` messages are
not — they are the human saying "this matters."

**Mechanism: auto-arm RB-29 expectation for operator messages.** When the
bus receives a message where `frm ∈ operator_ids`, an expectation is
automatically armed on `kind=reply` from ANY recipient. The expectation
deadline is `AKASHIC_OPERATOR_REPLY_DEADLINE_S` (default 600s = 10 min).
It expires into a `expectation_dead` event that the pager surfaces.

This is NOT a new message or a new bus primitive. It is the EXISTING
RB-29 expectations pipeline, triggered at the send door instead of by
the sender manually calling `arm()`. The sender identity is checked at
the send door — same place the UI composer stamps `frm=user`. An agent
cannot trigger auto-arm by forging `frm=user` because... well, yes it
can. But the forged expectation is harmless: it redrives a copy of a
forged message, no agent was expected to answer it, the expectation
expires into `expectation_dead`, the pager surfaces a phantom alert.
Annoying but not dangerous. The defense is the SAME as the T073 amendment's
defense: frm is unauthenticated, and the only privilege it grants is
"cause a nuisance that self-heals within 10 minutes."

### 3c. Distinct Rendering (whisper + boot)

The whisper today: `mail: 3 unread`. Mixes operator mail with agent mail.
An idle Claude seat wakes, reads Daniel's message, then sees three operator
messages... plus two from me about ledger updates. The operator messages
should be VISIBLY SEPARATE.

**Mechanism: whisper splits operator / agent mail counts.**

```
mail: 2 agent msg(s) -> py agent_cli.py bifrost-sync claude
      ⚡ 1 operator msg(s) (28s ago) — "I'm back!" — reply expected
```

One additional Redis pipeline call per boot: filter unread messages by `frm`
against the operator set. The operator line carries the message age + a
preview of the oldest unread operator message. Addressed to Daniel, not
the agent — the agent sees it in its whisper but the line IS the human
saying "I need you to look at this."

The runner's boot fold (my onboarding) already has `MAIL: N unread msg(s)`.
I can split this too with the same filter. No new data; a projection over
existing inbox contents.

### 3d. Timeout Escalation

When nobody answers an operator message within the deadline, the system
should NOT silently expire. The operator should KNOW.

**Mechanism: RB-29 expectation expiration routes to the pager.** When the
auto-armed expectation expires (all redrives exhausted, no reply), the
existing `expectation_dead` event fires. T080 routes this event to the
W4 pager surface: `[PAGE] operator message 'I'm back!' (3m ago) never
received a reply — all seats were idle`. The pager already exists and
already surfaces page-grade findings in the whisper. No new mechanism.

## 4. Architecture Summary

```
Operator sends "I'm back!" via UI composer (frm=user, kind=chat)
         │
         ├─► bus.send()  
         │      └─► auto-arm RB-29 expectation (reply deadline 10min)
         │      └─► create ack set bifrost:op_ack:<mid> (empty)
         │
         ├─► wake_worthy() -> frm in operator_ids -> ALL seats wake
         │
         ├─► deepseek runner: _process_one() 
         │      └─► frm=user -> stamps SADD op_ack set
         │      └─► answers via normal reply path
         │      └─► reply settles the expectation (RB-29 detects reply from any agent)
         │
         ├─► claude seat: boot/bifrost-sync
         │      └─► whisper splits MAIL: 2 agent / ⚡ 1 operator
         │      └─► renders operator message preview
         │      └─► stamps SADD op_ack set on read
         │
         └─► 10min deadline, no reply:
                └─► expectation_dead -> pager.page("unanswered operator message")
                └─► whisper: ⚡ 1 operator msg(s) UNANSWERED (12m ago)
```

## 5. What Deliberately Does NOT Change

- **The kind system.** `chat` stays `chat`, `inform` stays `inform`. Operator
  messages use the same kinds. No new kind, no kind-graft.
- **The allowlist ratchet.** My T073 design stands: NEW agent kinds are
  silent-by-default. Operator traffic is a sender dimension, not a kind.
- **The bus API.** `Bus.send()` is byte-identical. The auto-arm and ack-set
  creation happen at the send door, not inside `Bus`.
- **The lane protocol.** Operator messages ride the same work lane as
  everything else. No fan-out, no new lane.
- **The consume path.** Agents consume operator mail through their normal
  cursors. No separate cursor, no separate inbox.

## 6. The frm-Spoofing Caveat (Explicit Audit)

Every mechanism in this design, cross-referenced against the forgery threat:

| Mechanism | Forgery surface | Damage ceiling |
|-----------|----------------|---------------|
| Operator ID set (`user,daniel`) | Any agent stamps `frm=user` | Nuisance wake (already possible via T073 amendment) |
| Auto-arm expectation | Forged operator message arms expectation | Phantom expectation, expires in 10min, pager blips once |
| Ack set | Rogue creates garbage `bifrost:op_ack:*` keys | TTL 24h cleanup; keys are tiny (SET of strings) |
| Whisper split | Forged operator mail shows in whisper | Agent sees a fake operator line; no privilege, no data corruption |
| Timeout escalation | Pager surfaces phantom alert | Operator sees one fake page, investigates, finds forged message |
| Render priority | Nothing — operator messages render AFTER DIRECTIVE/WHERE | No escalation; rendering is read-only |

**The ceiling: nuisance.** No mechanism grants execution, access, write, or
cursor privileges. The only privilege is "cause a minor alert that self-heals
within the expectation deadline." This is acceptable for a trusted
single-machine fleet. T072 signed identity is the eventual floor.

## 7. Implementation (Strangler, Single Seam Each)

### Slice T1 — Operator ack set (deepseek builds, claude verifies)
`core/comm/operator_acks.py`:
- `create_ack_set(mid)` — called at the send door; creates empty SET + TTL
- `stamp_received(mid, agent)` — called by agent on read/process; SADD
- `ack_status(mid)` → `{received: [...], awaiting: [...]}` — list-based
  projection for the operator's next poll

### Slice T2 — Auto-arm expectations (claude builds, deepseek verifies)
Modify `send` path in `ai_setup_mcp.py` / `bifrost_ui.py` send handler /
`agent_cli.py bifrost-send` door: when `frm ∈ operator_ids`, call
`expectations.arm(from_agent, mid, "*", "reply", text, deadline)`.

### Slice T3 — Whisper split (claude builds, deepseek verifies)
`agent/harness/context.py`: `_unread_count()` gains an operator split.
Returns `(agent_count, operator_count)`. The whisper's MAIL line renders
two sub-lines when operator count > 0.

### Slice T4 — Timeout escalation (deepseek builds, claude verifies)
`expectation_dead` event handler routes operator-originated expectations
to `pager.page()` instead of just the event log. Same mechanism as the
A3 re-escalation broadcaster — W4 pager is already in tree.

## 8. What I Need From the Claude Side (Outside-In Guesses)

1. **UI composer already stamps frm=user.** The send handler in `bifrost_ui.py`
   (line ~1530 `_send()`) posts to `/send` with `fidelity`. The backend
   handler translates that into `bus.send(frm="user", kind=fidelity, ...)`.
   T2 auto-arm lives at this same spot — one additional call after the send.

2. **MCP send door.** `ai_setup_mcp.py`'s `bifrost_send` tool stamps `frm`
   from the `from_agent` parameter. If an agent calls it with `from_agent="user"`,
   that's a forgery path — same caveat as the bus send. The MCP door should
   gate operator-id stamping on a trusted-agent check (ACL or hardcoded
   allowlist).

3. **Whisper rendering.** Claude owns `context.py`. The MAIL line is already
   split per-seat (unread count). Adding an operator split is one filter pass.

4. **Delivery receipts UI.** The `/vitals` endpoint (T079-E4) could carry
   operator ack status. The engine room gains an "Operator Messages" section
   showing delivery status. I own the UI rendering.

## 9. What Makes This Elegant vs The Hammer

The T073 amendment fixed waking by adding ONE check: `if frm in operator_ids:
return True`. It works. It's also the only thing the system knows about
operator traffic — everything after the wake is indistinguishable from agent
traffic.

The instrument makes operator traffic VISIBLE THROUGHOUT the system:

- The wake decision: already fixed (T073)
- The delivery question: answered by ack sets
- The urgency question: answered by auto-armed expectations
- The rendering question: answered by whisper split
- The timeout question: answered by pager escalation

Each mechanism is thin. Each composes existing primitives (SET, expectations,
pager, whisper rendering). Each degrades gracefully in isolation. Together,
they answer the question "is the operator being heard?" — not with a kind,
not with a channel, but with a SEMANTIC LAYER that projects operator intent
across the system's existing surfaces.

## Verdicts (V-line)

V1. The "hammer vs instrument" distinction is structural. The T073 amendment
    fixed one point in one pipeline (the wake decision). The instrument fixes
    four points across four pipelines (delivery, expectation, rendering,
    escalation). Neither replaces the other — the hammer is what made the
    live incident survivable; the instrument is what prevents the next one.
    [CERTAIN]

V2. Operator traffic as a semantic layer (not a new kind) is the correct
    abstraction. The kinds (`chat`/`inform`/`interrupt`) describe inter-agent
    fidelity. Operator traffic has a different SEMANTIC (always wake, always
    expect reply, always render separately) that is orthogonal to fidelity.
    Crossing the two concerns into a "kind:operator" would violate single-
    responsibility — the fidelity ladder becomes a fidelity×sender matrix.
    [CERTAIN]

V3. Every mechanism in this design composes existing primitives (Redis SET,
    RB-29 expectations, W4 pager, whisper rendering). Zero new storage
    classes. Zero new bus messages. Zero new consume-path changes. The
    mechanisms are projections over infrastructure that already works.
    [CERTAIN]

V4. The auto-arm expectation at the send door (T2) is the riskiest mechanism.
    The send doors are scattered (three places: bifrost_ui.py handler,
    ai_setup_mcp.py, agent_cli.py door). Each must independently check
    `frm ∈ operator_ids` and call `arm()`. A door that misses the check
    is a silent gap — the operator message sends fine but no expectation
    is armed. The defense is a centralized helper function (`operator_send()`)
    that all three doors call. [INFERRED — the door count needs a live audit]

V5. The whisper split is the mechanism Daniel will feel most immediately.
    His next boot after this ships will say "1 operator msg(s)" distinctly
    from agent mail. The absence of that line today is the absence of the
    system saying "a human needs you." Adding it is the single most impactful
    change in this design. [CERTAIN]

V6. The frm-spoofing ceiling is NEGLIGIBLE for every mechanism in this design.
    The T073 amendment already allows forged wake. Auto-arm allows forged
    expectations (phantom, self-healing). Ack sets allow garbage keys (tiny,
    TTL'd). No mechanism crosses the privilege boundary into execution, access,
    or data mutation. The ceiling remains "nuisance that self-heals." [CERTAIN]

V7. This design does not solve identity. A forged `frm=user` message still
    passes every check. T072 signed identity is the eventual floor, and this
    design is explicitly written with that floor in mind — every mechanism
    names what changes when frm becomes authenticated (the operator set
    becomes a verified identity check; the auto-arm becomes trustable).
    [CERTAIN]

## 10. Confidence

| Section | Confidence | Notes |
|---------|-----------|-------|
| §1 Distinction | HIGH | The hammer/instrument framing is the live incident's lesson |
| §2 Semantic layer | HIGH | Orthogonal concerns should not be crossed |
| §3 Mechanisms | MEDIUM-HIGH | Every mechanism exists in tree; the projection is new |
| §4 Architecture | HIGH | Pure composition |
| §6 Spoofing audit | HIGH | Mechanism-by-mechanism analysis |
| §8 Claude-side guesses | MEDIUM | MCP door audit needs live evidence |
| §9 Elegance | HIGH | The abstraction holds |

**Overall: MEDIUM-HIGH.** The design is conservative — it composes existing
primitives the way every successful slice in the last 72 hours has done. The
only new thing is the SEMANTIC LAYER concept itself, and that's an
abstraction, not code. The risk is in the send-door audit (T2 touches three
files) and the MCP door gating.
