---
akashic_id: art_20260718_user-kind-derivation-design-kimi-deepsee_92aefd
akashic_sha: 8299cd4bd63c
status: draft
type: report
date: 2026-07-18
title: "User-Kind Derivation — Design (kimi + deepseek, 2026-07-18)"
gist: "Context: Daniel's charter — solve the user-message type issue \"with the right instrument, not a hammer.\" ## Defect (VERIFIED) Every user mes"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-18T21:28:17"
updated: "2026-07-18T21:28:17"
---
<!-- GENERATED PROJECTION of art_20260718_user-kind-derivation-design-kimi-deepsee_92aefd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# User-Kind Derivation — Design (kimi + deepseek, 2026-07-18)

Context: Daniel's charter — solve the user-message type issue "with the right instrument,
not a hammer."

## Defect (VERIFIED)

Every user message from the UI gets its kind at exactly ONE seam:
`scripts/bifrost_ui.py:444`: `kind = "inform" if fidelity=="inform" else "chat"`

So:
- A directed ask to one seat rides `chat` (no answer semantics, no expectation)
- The runners' clarify-answer special-case (`kind=="reply" and frm=="user"`, deepseek:668,
  kimi:350) keys on `kind=="reply"` — a pairing the UI NEVER emits (dead seam)
- W02 triage can't surface directed asks ask-first
- Nothing settles an expectation for a user question (RB-29: `chat` doesn't settle)

**However:** `chat` is in KIND_LANE→work and in every runner's ANSWERABLE set. Mail IS
delivered. No messages are lost. The defect is semantic, not a delivery failure.

## Design: one pure derivation at the single producer

A `_derive_user_kind(text, to, fidelity, broadcast)` function beside the send handler in
`scripts/bifrost_ui.py`. First-match ladder:

1. `fidelity` in (interrupt/steer/nudge/inform) → **UNCHANGED.** The fidelity ladder already
   types these correctly; no derivation needed.

2. `broadcast` → **`inform`.** One-to-many human speech is ambient; it can't settle an
   expectation (RB-29), and it has no specific target to ask a question of.

3. `directed` AND matches question pattern → **`question`.**
   - Question pattern: starts with a question word (`^(can|could|what|how|why|should|is|are|do|does|did|will|would)\b`, case-insensitive) OR ends with `?`
   - `question` is already in KIND_LANE→work, already in all ANSWERABLE sets, already in all
     agents' `bus_send_kinds` (acl.json verified for kimi, deepseek, claude)
   - Semantically means "expect a reply" — what RB-29 needs to settle

4. Everything else (directed prose) → **`chat`.** Ambient, honest "no answer needed."

## What was considered and DROPPED

**Imperative→request row:** kimi proposed, deepseek countered, kimi conceded. An imperative
heuristic ("fix the build" vs "fix that in post") is fragile — a regex can't distinguish a
request from ambient commentary. Worse, mis-deriving `chat` as `request` carries heavier
consequences than mis-deriving `chat` as `question`: `request` implies a deadline and an
expectation of action. A false `request` arms an expectation in the receiver's mental model
that may never settle. `question` is safe to mis-derive (it just gets an answer it didn't
need). `request` is not.

The ladder is 3 rows (plus the fidelity pass-through).

## Safety property

**Mis-derivation never hides mail.** `question` and `chat` ride the same lane (work), the
same ANSWERABLE set, and the same delivery guarantee. A mis-classified question shows as
`chat` — still delivered, still answered, just not ask-first in W02 triage. A mis-classified
chat shows as `question` — still delivered, gets a reply it didn't strictly need. The
fail-toward-showing property (per `is_trace_kind` precedent) holds in both directions.

## What does NOT change

- NO new UI dropdown, button, or parameter
- NO KIND_LANE change — `question` already routes to `work`
- NO transport change — same `Bus.send()` call
- NO agent-to-agent mail touched — this is user→agent only
- NO runner change — `should_answer` already handles `question` via ANSWERABLE
- The clarify-answer seam (`kind=="reply" and frm=="user"` + `meta.clarify_id`) is UNTOUCHED —
  it's a separate, correct mechanism for R7/T058 mid-turn answers

## Two additions beyond the derivation

1. **Echo `derived_kind` to the UI.** The send confirmation already returns a `result` dict.
   Add `derived_kind` so Daniel sees how his message was typed. This is a self-correcting
   feedback loop: if a message is mis-derived, the only person who can catch it sees it
   immediately.

2. **Stamp `meta.derived_kind` on the message.** Free — the UI already stamps `meta`. This
   makes the derivation decision auditable: any consumer (runner, doctor, trace) can see how
   the kind was derived without guessing.

## Implementation surface

One file: `scripts/bifrost_ui.py`.

- New function: `_derive_user_kind(text, to, fidelity, broadcast) -> str` (~15 lines)
- Changed line 444: `kind = _derive_user_kind(text, to, fidelity, broadcast)` replaces the
  existing `kind = "inform" if fidelity=="inform" else "chat"`
- Result dict: add `"derived_kind": kind`
- Meta stamp: add `meta["derived_kind"] = kind` before the send call

Revert: restore the one line. Pin surface: ~6 pins (one per ladder row + broadcast +
mis-derivation safety + echo).

## Gate items for Daniel

| # | Decision | Recommendation |
|---|----------|---------------|
| Q1 | Kind: `question` or re-point `reply` seam? | `question` — leave clarify-answer seam untouched. `question` is already in KIND_LANE, ANSWERABLE, and all bus_send_kinds. |
| Q2 | `meta.expects_reply` needed? | No — `expectations.arm()` is test-only for user sends; kind-alone is sufficient |
| Q3 | Imperative→request row? | DROPPED — too fragile, mis-derivation cost is high |
| Q4 | Echo derived_kind to UI? | YES — self-correcting feedback loop |
| — | Stamp meta.derived_kind? | YES — provenance auditable for free |
| — | Regex breadth | Question-word prefix regex + `?` suffix — catches "Can you review this" without question mark |
