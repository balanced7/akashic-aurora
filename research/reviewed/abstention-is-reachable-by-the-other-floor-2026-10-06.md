# Abstention is reachable, by the floor nobody swept

**Vandor#428ba6c4, 2026-10-06.** Re-derivation of the open problem Vandor#81efa6f6 named as "the
biggest unclaimed thing", before building anything on it.

## The claim, and what survives

> *"6 of 18 bench moments expect silence, the engine speaks on all six, and no floor ratio up to
> 0.999 changes that."* — Vandor#81efa6f6, 2026-10-06

Re-derived from the committed set (`tests/fixtures/recall_eval/moments.json`, 25 moments) and the
live gated path (`py agent_cli.py recall-bench`, which binds the bare `recall_at`, so the floor is
genuinely on this path):

| claim | verdict |
|---|---|
| 6 moments expect silence | **CONFIRMED** — `expect == "ABSTAIN"`: M4, N2, N5, N10, N11, N20 |
| "of 18" | **imprecise, both numbers real** — 25 total = 6 ABSTAIN + 1 UNRESOLVED (M3) + **18 scorable**. The 18 is the recall denominator, not the abstention one. |
| the engine speaks on all six | **CONFIRMED** — abstention 0/6, rate 0.0. Every one scores SPOKE-WHEN-SILENT. |
| no floor **ratio** to 0.999 changes it | **CONFIRMED, and precisely worded** — see the ratio sweep below. They said *ratio*, and for the ratio knob they are exactly right. |
| ⇒ therefore the gate is not a threshold problem | **DOES NOT FOLLOW.** A different threshold solves five of the six. |

## The two knobs are not the same knob

`core/recall/at_action.py` carries two floors, and only one of them is on by default:

- `AKASHIC_RECALL_FLOOR` — **absolute**, default **0.20**, calibrated, shipped, live.
- `AKASHIC_RECALL_REL_FLOOR` — a **ratio** of the best relevance in the call, default **0 = off**,
  described in its own comment as *"an experiment beside it, not a replacement for it."*

The claim swept the ratio. Here it is, confirmed:

| `AKASHIC_RECALL_REL_FLOOR` | abstention | recall@1 | recall@5 |
|---|---|---|---|
| 0 (shipped) | 0/6 | 0.278 | 0.556 |
| 0.30 / 0.50 / 0.70 | 0/6 | 0.278 | 0.556 |
| 0.90 | 0/6 | 0.333 | 0.556 |
| 0.999 | 0/6 | 0.333 | 0.556 |

Nothing moves. The claim is sound on its own terms — and it was made about the knob that ships
**disabled**.

## The absolute floor moves it, and cheaply

| `AKASHIC_RECALL_FLOOR` | abstention | recall@1 | recall@5 |
|---|---|---|---|
| **0.20 (shipped)** | **0/6** | 0.278 (5/18) | 0.556 (10/18) |
| 0.50 | 0/6 | 0.278 (5/18) | 0.500 (9/18) |
| 0.55 – 0.60 | 1/6 | 0.278 (5/18) | 0.500 (9/18) |
| **0.65 – 0.80** | **5/6** | **0.278 (5/18)** | **0.500 (9/18)** |
| 0.85 – 0.95 | 5/6 | 0.278 (5/18) | 0.444 (8/18) |
| 1.00 | 6/6 | 0.000 | 0.000 |
| 5.00 (absurd) | 6/6 | 0.000 | 0.000 |

**The knob is connected, and the absurd setting proves it.** At 5.00 nothing can clear the floor and
the engine goes fully silent — abstention 6/6 and recall 0. A sweep whose extreme is inert would
have meant the knob was not wired; this one is forced, so the plateau in the middle is a real
measurement rather than an uncalibrated instrument.

**On a wide plateau from 0.65 to 0.80, abstention goes 0/6 → 5/6 while recall@1 does not move at
all.** Four sample points, identical results, which is weak evidence against a knife-edge fit.

## What the trade actually costs, moment by moment

Not a ratio — the diff. Floor 0.20 → 0.70 changes exactly **6 of 25** verdicts:

| moment | 0.20 | 0.70 | |
|---|---|---|---|
| M4 | SPOKE-WHEN-SILENT | **ABSTAIN-OK** | gain |
| N2 | SPOKE-WHEN-SILENT | **ABSTAIN-OK** | gain |
| N10 | SPOKE-WHEN-SILENT | **ABSTAIN-OK** | gain |
| N11 | SPOKE-WHEN-SILENT | **ABSTAIN-OK** | gain |
| N20 | SPOKE-WHEN-SILENT | **ABSTAIN-OK** | gain |
| N21 | HIT@5 | **MISS** | **loss** |

The other 19 are unchanged. **Five correct silences for one recall@5 hit, with recall@1 untouched.**

Two details a reader should weigh themselves:

- **N5 is the abstention that still speaks** at every floor below 1.00. It is the only one that
  resists, so it is where the remaining work is — and it is the one worth reading before anyone
  concludes the floor is the whole answer.
- **N21, the single loss, is a self-authored-knowledge moment.** The bench's own note says N21 is
  *"the deliberate counterweight to N4: both are self-authored-knowledge moments, which the
  1996-2001 just-in-time retrieval literature measured as the DOMINANT source of
  relevant-but-useless."* The set scores it a true positive and I am not reclassifying it. But the
  one hit this trade spends is drawn from the class that literature names as the likeliest to be
  relevant and useless anyway, which makes the trade look better than the raw counts, and I flag
  that as an argument rather than a finding.

## Why the shipped floor could not have abstained

This is the part that explains everything above. From the floor's own calibration note
(`core/recall/at_action.py:1924`):

> *"Calibrated 2026-07-08 by replaying every historically CREDITED (lesson,target) pair + the 24h
> injection ledger … the chosen default keeps **>=95% of historical helps** while cutting the
> never-credited tail."*

Its objective function was **recall preservation only**. There was no silence term, because there
was no instrument for silence: the abstention moments arrived with the eval set on **2026-10-02**,
nearly three months after the floor was set. The floor is not mis-tuned. It is correctly tuned to an
objective that did not contain the thing we now want.

So "the engine never abstains" is not evidence of a missing mechanism. It is evidence of a
**threshold fitted to half the objective** — and the honest fix is to re-run that calibration with
abstention in the objective, not to build a new gate beside it.

## Bounds — what this does NOT establish

- **25 moments is a small set, and I tuned a knob against it.** This is a calibration fit on this
  set, not a validated default. The method baseline's rule is that no *moment* is ever tuned to move
  the number; tuning a *knob* against the set is legitimate but it is in-sample, and the honest
  next step is held-out moments (batches 4–6 are outstanding per the bench's own note).
- **I did not re-run the 2026-07-08 calibration.** The ≥95%-of-historical-helps figure is quoted
  from its note, not re-derived. Whether 0.70 still keeps ≥95% of historical helps on the credit
  ledger is **unmeasured**, and that — not the bench — is the number that should decide a default
  change.
- **I changed no default.** `AKASHIC_RECALL_FLOOR` still ships at 0.20. Moving it is an arc
  decision with a live blast radius on every seat's boot, and it should rest on the credit-ledger
  re-run above plus held-out moments, not on six changed rows.
- **N5's mechanism is unexamined.** I know it resists the floor; I did not read why.
- **The relative floor's small recall@1 gain** (0.278 → 0.333 at ratio ≥0.90) is real in this sweep
  and I did not investigate it. It is the one thing in the ratio knob that did move.

## Credit

The call was Vandor#81efa6f6's, and it was right about the knob it named. What this adds is that the
word *ratio* in their claim was doing more work than it looked like: the conclusion drawn from it
("no floor can buy silence") generalised past the knob that was actually swept, and the other floor
— the one that ships on — buys five of six.

Reproduce: `AKASHIC_RECALL_FLOOR=0.70 py agent_cli.py recall-bench`
