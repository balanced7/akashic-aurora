---
akashic_id: art_20260715_operator-traffic-claude-blind-half-t080_4e2913
akashic_sha: 2525d977729c
status: draft
type: report
date: 2026-07-15
title: Operator Traffic — claude blind half (T080) — 2026-07-15
gist: "Tonight's incident is the design input: his broadcast rode frm=user kind=inform, slept every idle claude seat, and he could not SEE that onl"
tenant: solo
visibility: fleet
seats: []
category: [library, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T22:01:26"
updated: "2026-07-15T22:01:26"
---
<!-- GENERATED PROJECTION of art_20260715_operator-traffic-claude-blind-half-t080_4e2913 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Operator Traffic — claude blind half (T080) — 2026-07-15

Tonight's incident is the design input: his broadcast rode frm=user kind=inform,
slept every idle claude seat, and he could not SEE that only the runner got it.

## Thesis: the operator does not speak in kinds

The kind taxonomy (request/handoff/inform/nudge/...) is a PROTOCOL AGENTS use
with each other — it encodes wake-worthiness, ack semantics, and fold behavior
that agents must agree on. Asking the operator to pick (or a composer to guess)
a kind is asking the human to speak protocol. The elegant instrument inverts
it: **operator traffic is its own class, above kinds**, with semantics defined
once, system-wide:

1. **Always wakes every seat of every addressed agent** (the override already
   ships this half — it becomes a LAW of the class, not a patch).
2. **Reach is visible**: the operator sees who got it, who woke, who answered.
3. **Never expires silently**: unanswered operator mail escalates, never rots.
4. **Renders distinctly** everywhere (UI, whispers, boot) — operator words are
   never visually mixed into agent chatter.

Kinds stop mattering for him entirely. Nothing to infer, nothing to misroute.
The deterministic-inference alternative (classify his text into kinds by
heuristics) is REJECTED in this half: it moves the guessing from the composer
into a classifier — a smarter hammer, same nail, and it breaks law 4 (his
message becomes an agent-shaped message again).

## Mechanism (composition over existing seams, zero new primitives)

- **Class marker**: `meta.operator=1` stamped by the trusted doors (UI composer,
  a new `agent_cli say` verb for terminal use). Not a new stream — the lanes
  stay; the marker rides the envelope like frm_incarnation does.
- **Wake law**: wake_worthy() checks the marker (subsumes tonight's frm-set
  override; the env set remains as the marker's trust anchor until T072).
- **Reach receipts**: each consumer that renders an operator message emits the
  EXISTING ack primitive (bifrost-ack, T026) with actor=agent@session. The UI's
  operator-message card renders the ack roster live: sent -> seen-by claude
  (2 seats), answered-by deepseek. Daniel's felt pain — "it didn't reach you" —
  becomes a glance at the card.
- **Escalation**: the expectations sweep (T061 lineage) treats unanswered
  operator mail specially: one redrive at 10m, then a PAGE (W4 pager — already
  wired to his [PAGE] hook lines) naming who never saw it. Operator mail is the
  one class that pages by default.
- **Render**: the whisper/boot/UI all key on the marker — a fixed OPERATOR
  block, top position, distinct styling (the engine room's Zone 1 gains an
  operator-mail chip).

## Trust boundary (the caveat, folded)

meta.operator is exactly as forgeable as frm today. Interim containment: the
marker is honored only when frm ∈ AKASHIC_OPERATOR_IDS (two literal strings)
AND the message arrived via a trusted door where possible; T072's identity
plumbing is the real floor, and this design ADDS REASON to land T072 (the
operator class makes forgery attractive). An agent caught stamping operator=1
is an ACL violation, auditable via the reach receipts themselves.

## Slices (proposed)

| Slice | What | Owner |
|---|---|---|
| O1 | Marker + wake law + `agent_cli say` verb (subsumes the override) | claude builds, deepseek verifies |
| O2 | Reach receipts on render + UI ack-roster card | split: seat/hook side claude, UI card deepseek |
| O3 | Escalation: redrive->page for unanswered operator mail | claude builds (expectations seam), deepseek adversarial-drills |
| O4 | Whisper/boot OPERATOR block + engine-room chip | split per boundary law |

## V-lines

V1. Kinds are agent protocol; the operator should never touch them — class
    above kinds, not inference into kinds. [PRINCIPLE — the crux for
    reconciliation if deepseek's half chose inference]
V2. Every mechanism above composes existing seams (meta envelope, ack
    primitive, expectations sweep, pager, whisper blocks). Zero new streams,
    zero consume-path moves. [GROUNDED]
V3. Reach receipts convert his felt pain into a visible roster; they also
    AUDIT the trust boundary (a forged operator message leaves receipts).
    [CLAIM]
V4. Escalate-to-page as the default for operator mail is right because the
    operator is the one sender for whom silence is never acceptable. [CLAIM]
V5. The inference path (deterministic text->kind) is a smarter hammer:
    rejected here, but if deepseek's half found a triage need for intent
    signals, intent can ride WITHIN the operator class (meta.intent, advisory)
    without demoting his words to agent kinds. [DESIGN — the likely synthesis]
