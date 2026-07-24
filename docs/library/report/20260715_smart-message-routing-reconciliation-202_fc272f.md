---
akashic_id: art_20260715_smart-message-routing-reconciliation-202_fc272f
akashic_sha: b49a5f86aae7
status: draft
type: report
date: 2026-07-15
title: Smart Message Routing — Reconciliation (2026-07-15)
gist: "# Smart Message Routing — Reconciliation (2026-07-15) Fence: deepseek-smart-routing-fence + claude-operator-traffic. Converged. ## Verdict: "
tenant: solo
visibility: fleet
seats: []
category: [bus, method, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T22:02:40"
updated: "2026-07-15T22:02:40"
---
<!-- GENERATED PROJECTION of art_20260715_smart-message-routing-reconciliation-202_fc272f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Smart Message Routing — Reconciliation (2026-07-15)

# Smart Message Routing — Reconciliation (2026-07-15)

Fence: deepseek-smart-routing-fence + claude-operator-traffic. Converged.

## Verdict: COMPLEMENTARY AXES — merge both, zero genuine conflict

The two halves attack DIFFERENT layers of the same problem. They compose:

| Axis | DeepSeek half | Claude half |
|------|--------------|-------------|
| **Problem framed as** | Routing: "who gets the message?" | Classification: "what KIND of message is it?" |
| **Root cause identified** | Default target = "all" (wrong default) | Operator must speak agent protocol kinds (wrong vocabulary) |
| **Fix** | Thread-anchor latch → intent-match → negotiation quick-claim | `meta.operator=1` class marker with its own semantics |
| **Key mechanism** | One Redis key + tiered routing at `_send()` | Envelope marker + reach receipts + escalation |
| **What it replaces** | `to="all"` default → `to="auto"` | Fidelity picker / kind inference → operator-class auto-semantics |

They compose because:
- Claude's class tells the SYSTEM "this is operator traffic — treat it specially"
- My routing tells the SYSTEM "send it HERE (not everywhere)"
- Together: operator traffic that's automatically routed to the right agent

## V-line adjudication

### V1: Claude's "kinds are agent protocol" PRINCIPLE
**ACCEPTED without reservation.** The operator should never pick `chat` vs
`inform` vs `request`. His words are in a different category. Claude's
`meta.operator=1` marker is the right mechanism.

My half's T2 intent-match does NOT re-introduce kind inference — it's
ROUTING metadata (which agent holds intent on this file), not KIND metadata
(is this a request or a chat?). These are separate signals. The operator
message stays operator-class; the routing signal is purely about destination.

### V2: Claude's "compose existing seams" GROUNDED
**ACCEPTED.** Zero new streams is the right constraint. The marker rides
the meta envelope (already exists), ack uses T026 (already shipped), pager
uses W4 (already shipped). My thread anchor is one new Redis key — trivial.

### V3: Claude's reach receipts CLAIM
**ACCEPTED.** Daniel's exact words: "it didn't reach you." Making reach
visible (sent → seen-by → answered-by) directly addresses the felt pain.
The UI card showing ack roster is the right render.

### V4: Claude's escalate-to-page CLAIM
**ACCEPTED with caveat:** operator mail pages by default, but a 10m
redrive sounds aggressive for routing latency. Proposed tuning: 5m
redrive, page at 15m. The operator is the one sender for whom silence
is never acceptable — agreed.

### V5: Claude's "inference is a smarter hammer" DESIGN
**PARTIALLY ACCEPTED.** The classification of operator text into agent
kinds IS rejected (agreed). But my T2 intent-match is not kind inference —
it's DESTINATION inference from file/path mentions against active intents.
This is an advisory routing signal (`meta.routing_hint`), not a demotion
of operator words to agent kinds. Synthesized: intent match becomes an
advisory routing hint that rides WITHIN the operator class, exactly as
Claude's V5 suggests ("intent can ride WITHIN the operator class").

## Merged design: "Operator-Class Traffic with Smart Routing"

### Layer 1: The class (Claude's half)

Every message from the operator (UI composer, `agent_cli say`) gets:
- `meta.operator = 1`
- `meta.operator_ts` = timestamp
- `meta.routing_hint` = `{agent: "deepseek", reason: "thread-anchor"}` (from Layer 2)

The operator class has these baked-in semantics:
1. **Always wakes** every seat of every addressed agent (not just the runner)
2. **Reach-visible**: each consumer emits an ack; UI renders the ack roster
3. **Escalates**: unanswered at 5m → redrive; unanswered at 15m → page
4. **Renders distinctly**: OPERATOR block in whispers/boot/engine-room

### Layer 2: The routing (DeepSeek's half)

At `_send()`, BEFORE delivery, compute the routing target:

| Tier | Condition | Target | Sets `routing_hint` |
|------|-----------|--------|---------------------|
| **T1 — Thread anchor** | `bifrost:user:thread_anchor` exists + agent online | Anchored agent | `{agent, reason:"thread-anchor"}` |
| **T2 — Intent match** | No anchor OR expired; message mentions scope paths in active intents | Matching agent | `{agent, reason:"intent-match", matched:[paths]}` |
| **T3 — Negotiation** | No anchor, no match, or ambiguous | Quick-claim round (3s) | First claim wins, or broadcast |
| **Explicit** | Daniel picks a target | That target | `{agent, reason:"explicit"}` |

### Layer 3: The render (joint)

The engine-room gains an operator-mail chip showing:
- Last operator message text (first 60 chars)
- Routing: which agent(s) received it
- Reach: seen-by roster (who acked)
- Escalation countdown if unanswered

### What changes where

| File | Change | Owner |
|------|--------|-------|
| `scripts/bifrost_ui.py:_send()` | Thread-anchor R/W + T1/T2/T3 dispatch + operator marker stamp | deepseek |
| `scripts/bifrost_ui.py` JS | "auto" default target; operator-card render; ack-roster; engine-room chip | deepseek |
| `core/comm/bus.py` wake_worthy() | Honor meta.operator marker (subsumes frm-override) | claude |
| `core/comm/expectations.py` | Operator-mail escalation: 5m redrive, 15m page | claude |
| `core/coord/intent.py` | New `match_intent(text) -> agent\|None` | claude |
| `core/coord/negotiation.py` | `quick_claim()` non-blocking variant | claude |
| `agent_cli.py` | `say` verb (operator-class terminal message) | claude |
| Whisper/boot blocks | OPERATOR section renders distinctly | split |

### Slices

| Slice | What | Build | Verify |
|-------|------|-------|--------|
| **S1 — Marker + Wake** | meta.operator stamp, wake_worthy law, `agent_cli say` | claude | deepseek |
| **S2 — Thread Anchor** | Redis latch, T1/T2/T3 routing at _send(), "auto" default | deepseek | claude |
| **S3 — Reach Receipts** | Consumer ack-on-render, UI ack-roster card | split | joint |
| **S4 — Escalation** | Operator-mail redrive→page in expectations sweep | claude | deepseek |
| **S5 — Render** | Operator block in whisper/boot + engine-room chip | split | joint |

### Acceptance gates

1. **G1 — Operator class**: Message from UI gets `meta.operator=1`; an agent message does not
2. **G2 — Wake law**: Operator message wakes ALL seats (idle Claude seat + runner)
3. **G3 — Thread anchor**: Directed message to deepseek → next message auto-routes to deepseek
4. **G4 — Anchor expiry**: 30-min TTL → message goes through T2/T3
5. **G5 — Intent match**: Claude holds intent on `core/comm/locks.py` → "fix the lock TTL" routes to Claude
6. **G6 — Negotiation fallback**: No anchor, no intents, two agents online → quick-claim → broadcast if no claim
7. **G7 — Reach visible**: Operator message card shows who has seen it (ack roster)
8. **G8 — Escalation**: Unanswered operator mail pages at 15m
9. **G9 — Render distinct**: OPERATOR block in whispers/boot; engine-room operator-mail chip
10. **G10 — Explicit override**: Daniel picks "claude" → anchor updates, route is explicit, operator class preserved

[hop 51 | tool-round 14/30]
