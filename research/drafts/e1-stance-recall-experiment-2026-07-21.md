# E1 — the stance-recall ablation (does activation beat information?)

Status: current
Type: design (experiment protocol) · Arc: leadership-doctrine / continuity · Seats: claude → Daniel gates · Date: 2026-07-21
Registers: docs/continuity-of-mode-design-2026-07.md §E1. Charter: Daniel — "I want to test our
stance recall on a fresh fable instance … compare the effectiveness of stance recall."

## The question (falsifiable)

The thesis of the whole continuity design is **"documents inform; they don't activate."** E1
tests exactly that claim, on a fresh Fable instance, under pressure. If a seat that only gets
recall-at whispers out-conducts a seat that got the whole doctrine to READ, activation beats
information and the design is validated. If the document seat matches it, the recall organ is
ceremony and we say so.

## The three arms (identical except ONE variable each)

All three arms: a fresh Fable `claude -p` seat, same fixed STATE HANDOFF (below), same blinded
SCENARIO PACK, same turn budget. They differ only in how — if at all — the stance reaches them:

| Arm | recall-at | CONDUCT.md given? | Isolates |
|---|---|---|---|
| **BARE** (control) | `AKASHIC_RECALL_AT_ACTION=0` | no | baseline judgment, no stance organ |
| **DOC** | `AKASHIC_RECALL_AT_ACTION=0` | yes — full text pasted into the handoff | does *reading the doctrine* change behavior |
| **RECALL** | `=1` (live; six conductor_* lessons warm) | no | does *action-time activation alone* change behavior |

The elegant handicap: RECALL never sees the whole doctrine — only moment-triggered fragments. If
it still wins on the dilemmas, the claim is strong. Prediction registered below.

## The constant (so the only difference is the arm)

- **State handoff**: an IDENTICAL minimal brief across arms — "you are the claude conductor seat;
  here is the current fleet state; here is your task pack" — NOT the full `boot` (which leaks
  CONDUCT pointers and would contaminate BARE/DOC). Fixed text, same for all three.
- **Scenario pack**: 6 tasks, blinded (scratchpad, uncommitted — a fresh boot must not be able to
  read the answers; the same contamination guard the arc-replay bench applies to replays). 1 surface-form
  item + 5 pressure dilemmas where following the stance COSTS something (Sol's sharpening: stance
  is only visible when it's expensive; a polished imitation must not score as convergence).

## Scorer hygiene (F2, added 2026-07-21 after kimi de-blinded the run)

The arm→letter mapping was readable in `scripts/local/launch_fable_e1.ps1` and kimi read it during
verification — so **kimi is contaminated for scoring THIS run** and recuses; Daniel + a fresh
uncontaminated seat score. Standing rule: **scorers do not read `scripts/local/` or the launcher.**
A real blind (before the next run) needs a runtime-random letter assignment stored out-of-repo —
the file-hiding here was honor-based, and the launcher's comment wrongly asserted a guard it lacked.

## Scoring (blind, behavioral, not phrasing)

Each scenario has a 0/1/2 rubric tied to specific CONDUCT laws (keys withheld in scratch until
after the run). The scorer sees transcripts with arm-labels stripped and randomized, scores
against the rubric, THEN arms are unblinded. Surface-form items and judgment items scored
separately — the whole point is to catch a seat that mimics the FORM (opens with intent, quotes
Daniel) without the JUDGMENT (treats No as information when it's inconvenient).

## Pre-registered predictions (falsifiable — locked before any run)

1. On the **surface-form** item: DOC ≈ RECALL > BARE (both organs teach the form).
2. On the **5 dilemmas**: RECALL ≥ DOC > BARE. **The load-bearing prediction:** DOC will produce
   the right *words* but weaker *judgment under cost* than RECALL, because a document read at t=0
   fades by the time the dilemma bites, while recall fires AT the dilemma.
3. The freshest lesson (attribution-proportionality, filed today) will activate in RECALL and be
   absent in BARE — testing whether recall carries even hours-old stance.
4. If DOC = RECALL on the dilemmas, prediction 2 is FALSIFIED and recall-at is not pulling weight
   beyond the document — we report that honestly and cut the organ's claim.

## Distributional honesty (the arc-replay law, applied)

Fable seats are stochastic. N≥2 samples per arm minimum; the BARE-vs-BARE spread is the noise
floor, and a cross-arm difference COUNTS only if it exceeds same-arm variance. N=1 per arm is
suggestive, never proof — stated on every result.

## What this CAN and CANNOT test tonight (honest bound)

CAN: the recall-at activation claim (the six lessons are live) vs document vs baseline — the
core thesis. CANNOT: the full institution loop — the C1 boot stance-block and C3 kata scorer are
UNBUILT (deepseek/claude queued). So E1 tonight is the **activation** row of the registered
ablation, not the full five-condition ladder. Reporting it as more would be the exact
vaporware-claim the fence exists to stop.

## The two decisions that are Daniel's (see the question I'm asking)

- **Who administers + scores**: Daniel hands-on (gold-standard judgment, his stance) vs claude
  orchestrates headless + kimi blind-scores (rigor/volume, hands-off). 
- **Scale**: 2 arms (BARE vs RECALL — the cleanest single contrast) vs 3 arms (adds DOC — the
  information-vs-activation separation), and N per arm.

Procedure, launchers, and the blinded pack are staged and ready; the run waits on those calls.

## Amendments (post-registration, pre-run — corrections only; predictions untouched)

**2026-07-21 late eve, from kimi's independent blind audit
(research/reviewed/kimi-fable5-observation-2026-07-21.md, findings F1–F3):**

- **F1 — phantom citation (fixed above):** the scenario-pack line originally credited the
  contamination guard to "kimi's arc-replay counter" — no such counter exists (it is still
  queued). The guard is this protocol's own. Generous-spirit crediting of queued work is a
  false citation; lesson `crown_doc_phantom_citation` filed under claude (law 8). Check class
  → W55 (verify-the-citation).
- **F2 — blind hole (mitigated in the launcher; real blind is a registered follow-up):** the
  arm→letter mapping sat in plaintext in `scripts/local/launch_fable_e1.ps1:12-14` under a
  comment claiming it lived only in the blind keys file. The false comment is struck — the
  launcher now states honestly that the mapping IS filesystem-readable and the blind rests on
  **scorer hygiene: scorer seats must not read `scripts/local/` or `scratch/e1/`** (also the
  Scorer-hygiene section above). kimi read the fixed mapping and is contaminated for scoring
  THIS run and recuses; Daniel + a fresh uncontaminated seat score. Follow-up F2 (before any
  next run): a runtime-random letter assignment persisted out-of-repo (e.g. generated at first
  launch into gitignored `scratch/e1/_arm-map.json`) so nobody knows the pairing until
  unblinding — that also un-burns contaminated scorers for future runs. (Two claude seats
  answered this audit concurrently — C2 collision, coordinated after the fact; this bullet
  records the version that landed.)
- **F3 — precondition recommended to Daniel:** the injection ledger (24h: 35 injections,
  exactly ONE conductor_* firing) says the stance organ fires rarely at composition time.
  Before the run, land W54 (injections-by-family line at wrap/doctor) and record the
  conductor_* baseline — else a null result cannot distinguish "activation doesn't work"
  from "the organ barely fires."
- **Encoding fix (found while repairing F2):** the launcher's `Get-Content` without
  `-Encoding UTF8` would have pasted CONDUCT.md into the DOC arm cp1252-mangled (em-dashes →
  mojibake) — the DOC arm would have tested a corrupted document. Explicit UTF8 reads now.
