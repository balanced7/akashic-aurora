# M1-BRIEF — lesson-publication-design

## CHARTER

Daniil's ask, verbatim (2026-08-25):

> "How can we make our non sensitive recall lessons be obtainable via github so that other
> akashic aurora instances can benefit? If we classify our current ones and make a system
> that auto files them into the correct bucket for scope and sensitivity that could help.
> I am not certain of the whole shape of the idea but what do you think?"

And earlier the same day:

> "can we go though our lessons and take out anything sensitive so we can put them on
> github. What would it take to comb over the corpus and give serges team what they need?"

He has named two axes — **scope** and **sensitivity** — and said himself he is unsure of
the whole shape. Treat both as PROPOSALS TO BE TESTED, not requirements to implement. If
one axis is wrong, or there is a third, say so.

## INPUTS (measured 2026-08-25; verify anything you lean on)

- **1,115 lessons** in the store.
- Each record carries 15 fields: `actual, agent_id, anti_pattern, category, confidence,
  domain, expected, experiment_name, metrics, recommendation, root_cause, source, success,
  timestamp, what_tried`.
- A pre-push **secrets scanner already exists** and runs on every push (last run: 3,203
  tracked files scanned, 1 allowlisted hit).
- The house already runs a **projection pattern**: atoms are truth, `docs/library/**` are
  read-only regenerated renders (`py agent_cli.py doc adopt`).
- Lessons enter through ONE door: `py agent_cli.py learn <agent> --experiment NAME
  --tried ... --result ... --recommend ...`.
- Intended consumers: other Akashic Aurora instances, and specifically **Serge's team**,
  who run a peer fleet.

Constraints that already carry receipts:

- `token_redaction_cannot_clean_a_dossier`
- `archaeology_republishes_whatever_the_past_leaked`
- `a_write_door_must_OFFER_a_field_or_it_stays_empty` — 0 anti-patterns came from a missing
  flag, not from unwillingness.
- **Publishing is a ONE-WAY DOOR.** A wrongly released record cannot be recalled. This
  asymmetry should drive the design.

## RULES OF ENGAGEMENT

1. Prescribed PROCESS, not persona. Do not adopt a character; follow the steps.
2. Mark every claim **VERIFIED** (you checked it) / **INFER** (your read) / **GUESS**.
3. Where you disagree with the ask's framing, say so plainly. "No" is information.
4. Cite receipts for measured claims; do not cite identifiers from memory.
5. **INDEPENDENCE IS THE POINT.** The conductor's synthesis is deliberately NOT in this
   brief. I have an answer and am withholding it, because halves that read my view produce
   agreement rather than evidence — measured here on 2026-08-24, when two seats
   independently produced near-identical analyses thirteen minutes apart and neither
   noticed until the store's dedup caught it. **Do not ask me what I think before you
   seal, and do not read the other half.**

## THE QUESTION

How should Aurora publish its 1,115 lessons to GitHub so that peer instances (and Serge's
team) can benefit — classified by scope and sensitivity — given that publishing is a
one-way door?

Sub-questions worth taking a position on:

- Are scope and sensitivity the right axes? Are they independent, or one ladder?
- What may be classified automatically, and what must never be?
- Is the unit of publication the LESSON, or something smaller?
- What does a peer instance actually need in order to USE a foreign lesson?
- What is the cost, in hours and in risk, of the first publishable batch?

## OUTPUT CONTRACT

Your half must contain, in this order:

1. **MECHANISM** — what you would build, concrete enough to cost.
2. **WHAT IT CANNOT DO** — what it would wrongly release, and what it would wrongly
   withhold. Both directions.
3. **ONE FALSIFIER** — the sentence that, if true, means your design failed.
4. **COST** — hours for the first publishable batch, and what is ongoing.
5. **DISSENT** — anything in the ask's framing you would change, or "none".

## SEAT NOTE (independence)

half_a and half_b are sealed before either is read. The reconciliation is the conductor's
and happens only after both seals.
