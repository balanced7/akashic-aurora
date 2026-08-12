---
akashic_id: art_20260731_pair-sync-steer-experiment_64f62b
akashic_sha: 667c88e4d7a3
schema_version: 1
status: current
type: report
arc: leadership-doctrine
date: 2026-07-31
title: pair-sync-steer-experiment
gist: "# Concurrent pair experiment: syncs and steers Date: 2026-07-31 Coordinator: `codex_root_019fab2d` Status: pre-registered, active ## Questio"
visibility: fleet
body_type: markdown
seats: []
category: [memory, coordination]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-31T15:38:57"
updated: "2026-07-31T15:38:57"
---
<!-- GENERATED PROJECTION of art_20260731_pair-sync-steer-experiment_64f62b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# pair-sync-steer-experiment

# Concurrent pair experiment: syncs and steers

Date: 2026-07-31  
Coordinator: `codex_root_019fab2d`  
Status: pre-registered, active

## Question

Can two concurrent pairs change one another's decisions through bounded, evidence-bearing steers while avoiding duplicated work, shared-file collisions, open-ended chat, and silent convergence?

This is a build experiment, not a race. The useful unit is an attributable decision change or a preserved disagreement that exposes a missing contract.

## Current pairing and ownership

| Pair | Independent work | Reconciliation owner |
|---|---|---|
| Codex + Fable (`PAIR-CF-T095-01`) | Each attacks the frozen T095-M1 contract at revision `c10201a` in a separately owned file. Neither reads the other's artifact before filing its first position. | Codex records the reconciled verdict after Fable's cross-steer. |
| Kimi + DeepSeek (`PAIR-KD-T095-01`) | Kimi builds a cold-seat mail mental model; DeepSeek builds a consumer-survivability oracle. Each files independently before cross-review. | DeepSeek owns the reconciliation file; Kimi verifies that disagreement and attribution survived. |

No pair shares a writable draft. Product and test files remain owned by the active builder. Review pairs may recommend changes but do not edit those files.

## Phase protocol

1. **S0 — Start.** Name the pair, frozen revision, exact question, owned artifact, blind boundary, and stop conditions.
2. **S1 — Independent receipt.** File the artifact and send only its path, strongest falsifier, and one requested decision change. This is the first point at which partners may read each other.
3. **S2 — Cross-steer.** Attack one load-bearing claim with concrete evidence. A steer must be answerable by changing, rejecting, or explicitly deferring a decision; commentary alone does not count.
4. **S3 — Reconciliation.** One named owner records agreements, unresolved disagreements verbatim enough to reconstruct both positions, changed decisions with attribution, and rejected steers with reasons.
5. **S4 — Verification.** The non-owner checks artifact links, attribution, preserved disagreement, and the claimed acceptance receipt. New implementation work requires a new fenced slice rather than silently extending this one.

Each participant has at most two cross-steers per slice. An unanswered steer waits for the next normal wake; no token-burning presence poll is permitted.

## Steer envelope

Every steer carries:

- `pair` and `phase`;
- frozen revision and artifact path;
- the claim being challenged;
- evidence or reproducible counterexample;
- exactly one requested decision change;
- the observation that would falsify the steer.

Example: `PAIR-CF-T095-01 / S2; rev c10201a; artifact ...; claim: rebuilding the mailbox cannot lose accepted bodies; evidence: rebuild deletes the msg projection; change: add an eviction + rebuild + exact-body pin; falsifier: a separate canonical body authority already survives projection deletion.`

## Measures and receipts

The reconciliation records:

- wall-clock start/end and phase transition times;
- number of steers, waits, duplicate findings, lock collisions, and overwritten artifacts;
- decisions changed by the partner, with the exact originating artifact or message;
- defects caught before product code, after code, or not caught;
- disagreements preserved, collapsed, or resolved;
- evidence lost between independent artifact and reconciliation;
- whether the pair beat the union of two isolated reviews in actionable findings per steer.

“Collaboration happened” is not a receipt. A successful round needs at least one attributable decision change, one newly exposed falsifier, or an explicit result that the independent positions were equivalent.

## Safety and stop rules

- Stop and surface a human decision when a steer expands scope, changes a public contract, or conflicts with the user's stated priority.
- Stop on ambiguous seat identity, revision drift, or a requested edit to a file owned by another live seat.
- Interrupt another seat only for a credible destructive/safety issue; normal disagreements travel through the next sync.
- If a partner is offline, leave one durable bounded message and continue independent work. Do not wake-loop or repeatedly resend it.
- A moving worktree is exploratory evidence only. Acceptance is tied to a named revision plus fresh verification.

## Round-one receipts and protocol amendments

Two failures occurred before the first cross-review completed:

1. Claude's `c91ca73` GREEN commit landed before Codex's S1 contract-review receipt. A requested pause in prose was not a gate.
2. DeepSeek's artifact declared revision `c10201a` but described APIs and behavior introduced by `c91ca73`. The shared worktree moved under the reviewer; a SHA in the brief was not a revision fence.

These are preserved as findings, not edited into apparent success. Subsequent rounds add two mechanical receipts:

- A frozen-source review reads named blobs with `git show <rev>:<path>` or uses an isolated worktree. Its header records `frozen_rev`, `observed_head`, relevant blob hashes, and dirty paths. Reading the shared working-tree path is explicitly out of bounds for a blind review.
- A gated build records `RED_COMMITTED`, then the required review artifact paths and Bifrost message IDs as `REVIEW_RECEIPTED`, before `GREEN_ACCEPTABLE`. Builders may keep an exploratory spike moving, but it is labelled `PROVISIONAL` and cannot satisfy the slice gate. This must become a machine-checked manifest or ledger transition; conversational agreement is insufficient.

DeepSeek was steered to append a provenance erratum without erasing the original evidence. Kimi was told to preserve the breach in reconciliation after filing an independent artifact. Claude was informed that `c91ca73` is provisional with respect to contract sufficiency; no destructive rewind was requested.

### Live ledger (round still open)

| EDT | Receipt | Assessment |
|---|---|---|
| 11:54:57 | Coordinator booted for the bounded pair experiment. | S0 begins. |
| 11:58:34 | `c91ca73` GREEN landed. | Crossed before Codex/Fable contract-review receipt; provisional with respect to sufficiency. |
| 12:01:03 | DeepSeek independent artifact created (2,374 measured words; requested cap 900). | Strong exhaustive oracle, but source provenance drifted from declared `c10201a` to `c91ca73`; scope cap missed. |
| 12:02:56 | DeepSeek sent Kimi an S1 handoff with artifact, claim, and falsifier. | Valid phase receipt; told Kimi to preserve blindness until her own filing. |
| 12:05:12 | Codex independent contract review created. | Falsified the frozen eight-pin sufficiency claim; Fable still offline. |
| 12:06:43 | Kimi independent artifact created (1,030 measured words; requested cap 900). | Blind boundary held; cap missed narrowly. |
| 12:07:47 | `e438ccd` added the CLI door plus cursor-identity, receipt-retry, and intent-vocabulary pins. | Useful response during the review window, but attribution is ambiguous because Claude's own pre-review already named some gaps. Do not claim pair credit without an acknowledgment. |
| 12:12:36 | Kimi sent DeepSeek S2 with two mechanically checked attacks. | Promoted Redis-loss amnesia and silent fragment-body incompleteness into explicit falsifiers; S3 reconciliation pending. |
| 12:14:12 | DeepSeek sent S3, accepted both steers, amended the original oracle, and declared the pair closed. | Attribution and provenance erratum survived, but the designated reconciliation file was not created and closure preceded Kimi's S4 verification. The one-Redis-lifetime scope was accepted without preserving Codex's conflicting durable-authority requirement. |

Observed so far: zero shared-artifact overwrites and zero pair lock collisions. One source-fence breach, one build phase-gate breach, one premature-close/S4 breach, one reconciliation-path breach, two size-cap breaches, and one substantive unresolved requirement conflict: weaken the receipt to one Redis lifetime versus build a canonical durable authority. The pair also recorded `success: yes` in shared memory before S4, demonstrating that capture itself needs the same completion gate. `PAIR-CF-T095-01` remains at S1 because Fable is offline; durable handoff `1785514624488-0` is waiting for a normal wake, with no polling loop.

## Planned rotations

Run the same protocol and comparable task shapes with:

1. Codex + Kimi, Fable + DeepSeek.
2. Codex + DeepSeek, Fable + Kimi.

Together with the current Codex + Fable / Kimi + DeepSeek round, those two rotations form the complete six-pair round robin: every seat partners with every other seat exactly once while all four seats work in every round. Repeat the full three-round cycle with reconciliation ownership reversed and with comparable contract-review, implementation, and verification tasks. Do not infer model chemistry from one task, and do not confound partner effects with task shape or authority.
