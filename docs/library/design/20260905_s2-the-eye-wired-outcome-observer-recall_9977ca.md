---
akashic_id: art_20260905_s2-the-eye-wired-outcome-observer-recall_9977ca
akashic_sha: e28aabbb2b1e
schema_version: 1
status: current
type: design
date: 2026-09-05
title: "S2: the Eye-wired outcome observer (recall's AAR)"
gist: "# S2 — the Eye-wired outcome OBSERVER (recall's AAR) Date: 2026-09-05 · Owner: claude (Vandor) · Operator ruling: build S2 first Parent: `re"
visibility: fleet
body_type: markdown
seats: []
category: [recall, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-05T22:16:50"
updated: "2026-09-05T22:16:50"
---
<!-- GENERATED PROJECTION of art_20260905_s2-the-eye-wired-outcome-observer-recall_9977ca -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# S2: the Eye-wired outcome observer (recall's AAR)

# S2 — the Eye-wired outcome OBSERVER (recall's AAR)

Date: 2026-09-05 · Owner: claude (Vandor) · Operator ruling: build S2 first
Parent: `research/in-flight/recall-redesign-from-synthesis-2026-09-05.md` (nine-arm synthesis)
Fence: Heimdall commissioned (bus `1788654097479-0`); his counters fold in before build.

## The problem, stated so it can be falsified

Recall's credit today is `helped | useful | engaged` — **self-report**, written by the seat that
was helped, plus narrow implicit FAIL→SUCCESS flips. In the synthesis's vocabulary that is
**work-as-disclosed**, and the gap between disclosed and done is exactly the phenomenon the
hollow-control audit names: surgical checklists documented at 100% and observed at 3.5%; EMR
self-report 89% vs OR video 47%.

We already measure the disclosed half well (`precision_audit` is blind, RAGAS-split, and
explicitly refuses the skim test). What we have never measured is **what the seat DID after the
lesson fired.** The transcript knows. THE EYE holds the transcript. Nobody has joined them.

**The AAR is the only intervention in the whole nine-arm round with two converging
meta-analyses (d = .67, 46 samples), and its power is not the conversation — it is the
OBJECTIVE RECORD.** Objective review media is one of only two consistently significant
moderators. The Eye is our gun-camera footage. This slice wires it in.

## The join already exists

`core/recall/at_action.py:849` — `mark_impression(session_id, target, sources)`, commented
verbatim *"Record that `sources` were surfaced for `target` this session (the outcome-join
key)."* So we already durably know **(lesson, action, session)**. The Eye answers **what
happened next in that session**. S2 is the join, plus a verdict, plus the honesty to say
"unknowable".

## THE CORE MOVE: the 19 ghosts are not one bucket

The lesson `cost_without_return_cannot_see_prevention` (which fired at me while designing this,
and is the reason this section exists) says a zero-credit lesson may be **silently working**: it
fired, the seat complied, no incident occurred, so there was nothing to credit. Mass-pruning
zero-credit would delete our best preventers — the classic reliability error of scoring a
barrier by the incidents it failed to stop.

Only an objective record can split them. For each impression, the observer returns one of:

| verdict | meaning | what it implies |
|---|---|---|
| `COMPLIED` | the lesson's prescribed shape appears in what the seat then did | **silent prevention — KEEP, this is the good ghost** |
| `VIOLATED` | the forbidden shape appears anyway | the fired-then-violated class (we have 8) — **candidate for promotion to a GATE (S1)** |
| `INAPPLICABLE` | the situation the lesson addresses never arose | **genuine noise — retire candidate** |
| `UNKNOWABLE` | transcript cannot settle it | **never counted in any rate** (see denominator law) |

A zero-credit lesson that is COMPLIED-heavy is a **silent preventer**. A zero-credit lesson that
is INAPPLICABLE-heavy is **noise**. Today both are called "ghost" and both would be pruned. That
single distinction is the slice's reason to exist.

## Authority boundary — fence r2 H-C1 (binding, discovered mid-design)

`core/fleet/verdicts.py:156` enforces: **adjudication is OPERATOR-ONLY by default**; a
resident-authored adjudication is REFUSED LOUDLY at the write door, because *"a two-record join
doesn't close self-grading."* This slice is bound by that ruling, and it sharpens the design:

- What this module produces are **OBSERVATIONS**, never verdicts. It reports what the transcript
  shows (`COMPLIED` / `VIOLATED` / `INAPPLICABLE` / `UNKNOWABLE`) with citations. That is a
  measurement, not a grade.
- **Retirement, keeping and promotion remain operator/conductor acts.** The observer proposes a
  split with evidence; a human rules. This is exactly the observation/judgment separation
  `shadow_shelf` was built for — and it is why the shelf's judgment register stays untouched by
  this slice's writer.
- The word "adjudicator" is deliberately dropped from the module name so the code cannot be read
  as claiming an authority the fence reserves.

This also satisfies the deeper reason the fence exists, which the synthesis states independently:
a recovery/scoring mechanism whose INPUT is produced by the component it grades cannot see its
own blind class (`rearm_actor_is_a_trigger_consumer_not_a_deadman`). Recall must not grade recall.

## Denominator law (non-negotiable)

From `a_rate_over_unadjudicated_claims_pays_players_to_flood`: **a rate's denominator is an
attack surface.** Therefore:

- precision denominator = `COMPLIED + VIOLATED + INAPPLICABLE`. **`UNKNOWABLE` is excluded from
  every rate and reported alongside it as coverage** — the `precision_audit` discipline
  ("UNLABELLED IS NOT NEGATIVE") carried forward verbatim.
- a verdict is only minted where the transcript SETTLES it. Starved, never 100%, on thin
  evidence. The observer must be able to confess its own blindness.
- no lesson may be retired on a sample whose `UNKNOWABLE` share exceeds the settled share.

## Architecture — observation and judgment stay separated

Sunshine's `core/recall/shadow_shelf.py` (T370 Slice 0) is the substrate and its shape is
exactly right for this: an **isolated observation register**, an **independent judgment
register**, a bounded deterministic reader, and *no* live-recall import, event log, or
canonical-memory writer. That separation is the point — the thing that OBSERVES compliance must
not be the thing that WRITES the lesson's fate, or we rebuild the self-report loop one layer up
(the same in-band-input defect as `rearm_actor_is_a_trigger_consumer_not_a_deadman`).

    impressions (mark_impression)  ─┐
                                    ├─► observer (READ-ONLY)   ─► shadow_shelf.observation
    THE EYE (transcript, read-only) ┘                                      │
                                                                          ▼
                                            curator/operator reads ─► judgment register
                                                                          │
                                                             (retire / keep / promote-to-gate)

**No auto-retirement in this slice.** The observer only observes and proposes; a human or the
curator's existing gated path acts. Reason: Leveson — a control that removes a necessary
deviation is itself the hazard, and we do not yet know this instrument's error rate.

## Pre-registered acceptance (RED pins first, per method baseline)

- **P1 — join integrity:** every observed row resolves to a real `(session, target, source)`
  impression and a real Eye event address; an unresolvable address REFUSES rather than guessing.
- **P2 — four verdicts, honest fourth:** on a transcript with no evidence either way the verdict
  is `UNKNOWABLE`, never `INAPPLICABLE`. (These are the two easiest to conflate and conflating
  them silently inflates precision.)
- **P3 — denominator law:** `UNKNOWABLE` never enters a rate; coverage is reported with every
  rate; a sample failing the coverage floor yields NO retirement proposal.
- **P4 — the ghost split is real:** on the current 19 zero-credit ghosts the observer
  partitions them into ≥1 `COMPLIED`-heavy (silent preventer, KEEP) and ≥1 `INAPPLICABLE`-heavy
  (noise, retire-candidate), with the transcript addresses cited for each. If it cannot separate
  them, the instrument has failed and the slice does not ship.
- **P5 — read-only boundary:** the observer imports no live recall path and writes only the
  observation register; a same-path write attempt refuses (inherits T370's contract).
- **P6 — replay determinism:** same impressions + same Eye state ⇒ byte-identical verdicts
  (seeded, re-auditable — `precision_audit`'s discipline).
- **P7 — no circular staleness:** verdicts derive from the TRANSCRIPT record, never from "do the
  named files still exist" (`namespace_filter_is_circular_resolution_test` forbids the circular
  resolution test as a validity filter).
- **P8 — authority refusal (fence r2 H-C1):** the observer never writes a judgment/verdict
  record; an attempt to write into the judgment register, or to author an adjudication as a
  resident identity, REFUSES loudly. Observations carry `authority=observation` explicitly.
- **P9 — terminal evidence:** a row that closes (retire-proposed) carries every field needed to
  re-audit it, in the closing record itself (`t196_terminal_events_carry_their_own_evidence`).

## Build order

1. RED pins P1–P8 committed alone (method baseline: RED before implementation).
2. `core/recall/outcome_observer.py` — the join + OBSERVATION, read-only, into shadow_shelf.
3. `agent_cli.py recall-outcomes` — render the ghost split with citations (the AAR surface).
4. Run it on the 19 ghosts; publish the split as the slice's receipt.

## Bounds

This measures COMPLIANCE, not correctness — a seat can comply with a wrong lesson. That is the
`precision_audit` complement, not a replacement: precision asks "should it have been shown",
this asks "did it change what happened". Both are needed and neither subsumes the other.
Prevention remains partially unobservable (the incident that did not happen leaves no trace);
`COMPLIED` is our best proxy and must be labelled as a proxy, never as proof.
